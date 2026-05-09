# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 10:04
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] `evidence_quality_warn` migration lacks required `workspace` / `project_slug` context
   - Section: "`core/research_verifier.py:362-366` ... `WarningRegistry.record(rule_id=\"evidence_quality_warn\", affected_phase=\"scope\", count=len(gaps), extra={...})`"
   - Issue: [core/research_verifier.py](/Users/hoon/workTree/agent-factory/core/research_verifier.py:362) only has `evidence_fn`, `task_input`, and verifier result context. It does not know `target_workspace` or `slug`, while §4.0 requires `WarningRegistry(workspace=target_workspace)` and `record(project_slug=...)`. The actual caller with that context is [core/project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:759).
   - Suggestion: Move `evidence_quality_warn` registry recording to `ProjectPipeline.prepare_brief()` immediately after `verify_with_retry()` returns `_vr`, or explicitly extend `ResearchVerifier.verify_with_retry()` with `workspace` and `project_slug`. Caller-side recording is cleaner and avoids coupling verifier code to runtime storage.

2. [High] Frozen build packaging is omitted for new dynamically used modules
   - Section: "P1 PR scope ... `core/warning_registry.py` 신설 ... `core/escalation_evaluator.py` stub 신설"
   - Issue: [af.spec](/Users/hoon/workTree/agent-factory/af.spec:31) maintains explicit `hiddenimports` for core modules, including nearby modules such as `core.work_item_telemetry`, `core.research_verifier`, and `core.plan_verifier`, but the P1 scope does not include `af.spec` updates. The checklist explicitly requires frozen `dist/af/af.exe` compatibility.
   - Suggestion: Add `core.warning_registry` and `core.escalation_evaluator` to `af.spec` hiddenimports, and include a frozen-build import smoke test or at least a PyInstaller analysis check in the P1 acceptance list.

3. [High] Approval-gate link wiring is underspecified for `target_path` split mode
   - Section: "`runtime/warnings/`는 항상 workspace 하위 ... doc_root, cwd 아님" and "`approval-gate.md`의 `## Review Notes` 섹션에 ... `runtime/warnings/<slug>/_decision.md`"
   - Issue: In [core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:948), documents can be written under `doc_root = target_path`, while telemetry remains under `workspace`. The gate is created as `ApprovalGate(doc_root, slug)` at [core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:1061), so `ApprovalGate` only knows the document root, not the AF workspace where `_decision.md` lives. A plain relative link `runtime/warnings/<slug>/_decision.md` will point under `doc_root`, not `workspace`, in multi-PC / external target modes.
   - Suggestion: Specify an API change such as `ApprovalGate(doc_root, slug, runtime_workspace=target_workspace)` or pass `decision_report_path` into `initialize()`. Render a path relative from `approval-gate.md` to the actual workspace file, or use an explicit absolute path policy.

4. [Medium] `_summary.json` schema contradicts phase-split acceptance
   - Section: "`_summary.json` 포맷" shows `"e2e_command_missing": {"count": 21, "first_ts": "...", "last_ts": "...", "severity": "warn"}`
   - Section: "Acceptance #2: `by_rule.e2e_command_missing.by_phase` 분포가 표시된다"
   - Issue: The design requires phase-grouped records for `e2e_command_missing`, but the summary schema has no `by_phase`. P2 escalation depends on phase-aware counts, so implementers will either invent a schema or omit the acceptance.
   - Suggestion: Define `by_phase` explicitly, e.g. `"by_phase": {"scope": {"count": 5, "severity": "warn"}, "build": {"count": 16, "severity": "warn"}}`, and update `summarize()` acceptance to match.

5. [Medium] P1/P2 activation wording is still inconsistent
   - Section: §0 says P2 activates `e2e_command_missing` for "`build/verify/code_review/cross_validate`"
   - Section: §5.1 policy includes `affected_phase_in: [build, integrate, code_review, cross_validate, verify]`
   - Issue: `integrate` is omitted in §0 but included in the actual policy. Since `_PHASE_ORDER` includes `integrate` at [core/project_task_board.py](/Users/hoon/workTree/agent-factory/core/project_task_board.py:17), this inconsistency can produce different implementation behavior depending on which section is followed.
   - Suggestion: Update §0 to exactly match the policy list: `build/integrate/code_review/cross_validate/verify`.

### Missing from Design

- `af.spec` hiddenimports update for `core.warning_registry` and `core.escalation_evaluator`.
- Exact approval-gate API change for linking a workspace-owned `_decision.md` from a possibly separate `doc_root`.
- Explicit `_summary.json.by_rule.<rule>.by_phase` schema.
- Concrete callsite for `evidence_quality_warn` that has both `target_workspace` and `slug`.
- Test covering `target_path` external document root plus workspace-owned warning storage.

### Positive Observations

- The design correctly aligns `affected_phase` with `_PHASE_ORDER` in `core/project_task_board.py`, avoiding the previous non-existent `design/test/integration` phase problem.
- The owner drift plan records from the caller side instead of inside `detect_owner_drift()`, which avoids importing registry code into `core/project_task_board.py` and preserves the helper’s layering.