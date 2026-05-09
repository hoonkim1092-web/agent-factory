# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 09:51
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] Warning storage has no workspace/root contract
   - Section: "`runtime/warnings/`", "`core/warning_registry.py`: `record()`, `summarize(slug)`, `load_global(rule_id)`"
   - Issue: The design never says whether `runtime/warnings` lives under `workspace`, `doc_root`, repo root, or cwd. Current code already separates `workspace` and `doc_root`: [core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:948) writes work-items under `target_path` when present, while telemetry writes under `workspace/runtime` at [core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:1042). `project_pipeline` also carries `doc_root` separately at [core/project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:946). A `record(project_slug=...)` API cannot reliably locate the correct warnings directory in multi-PC or `target_path` runs.
   - Suggestion: Make path ownership explicit: `WarningRegistry(workspace: str)` or `record(workspace=target_workspace, doc_root=doc_root, project_slug=...)`. State whether decision links in `approval-gate.md` point to `workspace/runtime/...` or `doc_root/runtime/...`.

2. [High] P1 evaluator stub contradicts the acceptance contract
   - Section: "`core/escalation_evaluator.py` **stub만**: `evaluate(record) -> EscalationDecision` 시그니처만 정의, body는 `pass`"
   - Issue: §10 says P1 stub “모두 False”, and P2 tests depend on `EscalationDecision.block=False/True`. A Python body of `pass` returns `None`, so any caller that expects `.block`, `.severity`, or a report object will fail or need extra `None` handling. This undermines the “P1 no BLOCK but code structure ready” goal.
   - Suggestion: In P1, define `EscalationDecision(block=False, severity="warn", reason="inactive_phase")` and return it for every record. Reserve policy evaluation for P2/P4, but do not return `None`.

3. [Medium] `_summary.json` schema cannot satisfy the stated acceptance
   - Section: "`_summary.json` 포맷" shows `by_rule.e2e_command_missing: {"count": 21, ...}`
   - Section: "Acceptance #2: `by_rule.e2e_command_missing.by_phase` 분포가 표시된다"
   - Issue: The proposed `_summary.json` has no `by_phase` field, but phase-split records are central to P2 blocking. Without `by_phase`, the CLI summary either cannot meet §10 or must invent an undocumented output shape.
   - Suggestion: Add `by_phase` to each rule summary, for example: `"by_phase": {"scope": 5, "build": 16}`. Add this to both §4.3 and the CLI test expectations.

4. [Medium] Frozen build impact is omitted
   - Section: "P1 PR scope: `core/warning_registry.py`, `core/escalation_evaluator.py`, `config/escalation_policy.yaml`"
   - Issue: The new modules are not listed in [af.spec](/Users/hoon/workTree/agent-factory/af.spec:33). The project already maintains explicit hidden imports for core modules, including `core.work_item_telemetry` and `core.plan_verifier` at [af.spec](/Users/hoon/workTree/agent-factory/af.spec:75). Frozen `dist/af/af.exe` compatibility is in the review checklist, but the design does not state whether `core.warning_registry` and `core.escalation_evaluator` need hiddenimports.
   - Suggestion: Add an `af.spec` item to §7.3 for both new modules. `config/` is already included as data at [af.spec](/Users/hoon/workTree/agent-factory/af.spec:29), so only confirm the YAML path remains under `config/`.

5. [Medium] Research warning callsite lacks slug/workspace data
   - Section: "`core/research_verifier.py:362-366` ... `WarningRegistry.record(rule_id=\"evidence_quality_warn\", affected_phase=\"scope\", ...)`"
   - Issue: `ResearchVerifier()` is constructed without slug/workspace at [core/project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:725), and `verify_with_retry()` is called with only `evidence_fn` and `task_input` at [core/project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:756). The verifier cannot fill required `project_slug` or choose a storage root unless the registry falls back to global cwd state.
   - Suggestion: Record `evidence_quality_warn` in `project_pipeline` after `_vr` is returned, where `slug` and `target_workspace` are available, or extend `ResearchVerifier`/`verify_with_retry` with explicit `workspace` and `project_slug`.

### Missing from Design

- Exact registry path resolution rule for `workspace` vs `doc_root` vs cwd.
- `EscalationDecision` dataclass fields and no-op P1 return semantics.
- `_summary.json.by_rule.<rule>.by_phase` schema.
- `af.spec` hiddenimports update for frozen builds.
- Tests for `target_path` projects and frozen-style path behavior.

### Positive Observations

- The design correctly keeps `affected_phase` aligned with `_PHASE_ORDER` in [core/project_task_board.py](/Users/hoon/workTree/agent-factory/core/project_task_board.py:12), avoiding the prior phase mismatch.
- The `detect_owner_drift()` migration chooses the caller-side recording point, which avoids importing registry code into [core/project_task_board.py](/Users/hoon/workTree/agent-factory/core/project_task_board.py:227) and keeps layering cleaner.