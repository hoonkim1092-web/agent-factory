# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 09:49
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Registry storage has no workspace/root contract
   - Section: "`runtime/warnings/`" and "`core/warning_registry.py`: `record()`, `summarize(slug)`, `load_global(rule_id)`"
   - Issue: The proposed API has `project_slug` but no `workspace` or runtime root. Current project runtime convention is workspace-scoped `.af_runtime` via [core/continuity/runtime_paths.py](/Users/hoon/workTree/agent-factory/core/continuity/runtime_paths.py:9). Without a workspace argument, implementation will likely write relative to process CWD or repo root, which breaks multi-PC/frozen execution and can collide when different workspaces reuse the same slug.
   - Suggestion: Define `record(workspace: str | Path, ...)` and store under `workspace_runtime_dir(workspace) / "warnings"`. If choosing `runtime/` intentionally, document why it differs from `.af_runtime` and how frozen `dist/af/af.exe` resolves it.

2. [High] P1 approval-gate wiring is underspecified and internally inconsistent
   - Section: "`P1에서 wiring`", "`initialize() / apply_verification_verdict() 시 link 자동 주입`", and P4 row "`approval_gate 링크 wiring`"
   - Issue: The design says both P1 and P4 own approval-gate link wiring. Current [ApprovalGate.initialize()](/Users/hoon/workTree/agent-factory/core/approval_gate.py:90), [apply_verification_verdict()](/Users/hoon/workTree/agent-factory/core/approval_gate.py:213), and [_render()](/Users/hoon/workTree/agent-factory/core/approval_gate.py:330) have no `decision_report_link` parameter or registry context. Also `approve()` and `invalidate()` re-render review notes, so a naïve injected link can be dropped or duplicated.
   - Suggestion: Make P1 explicitly own a small API such as `decision_report_link: str = ""` or `ensure_decision_report_link()`, and require idempotence across `initialize()`, `approve()`, `invalidate()`, and `apply_verification_verdict()`. Move the P4 “approval_gate 링크 wiring” row to P1 or narrow P4 to BLOCK decision updates only.

3. [High] Two migration callsites lack the identifiers needed to record correctly
   - Section: "`evidence_quality_warn` ... `WarningRegistry.record(...)`" and "`plan_verifier_warn` ... `WarningRegistry.record(...)`"
   - Issue: [core/research_verifier.py](/Users/hoon/workTree/agent-factory/core/research_verifier.py:362) appends `_warnings` inside `ResearchVerifier` but has no `workspace` or `slug` in that method scope. [PlanVerifier](/Users/hoon/workTree/agent-factory/core/plan_verifier.py:42) also has only `workspace`, while the actual slug is in [project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:948). The design gives record calls but not the data flow needed to populate `project_slug` and storage root.
   - Suggestion: Record `plan_verifier_warn` in `project_pipeline.py` after `_plan_result` is final. For research, either record in the pipeline where slug/workspace exist after verifier returns, or extend `ResearchVerifier` constructor/signature deliberately and update all callers.

4. [Medium] Frozen build impact is missing
   - Section: P1 PR scope lists new modules but omits `af.spec`
   - Issue: The project has explicit hiddenimports in [af.spec](/Users/hoon/workTree/agent-factory/af.spec:60), including nearby modules like `core.research_verifier` and `core.work_item_telemetry`, but not the proposed `core.warning_registry` or `core.escalation_evaluator`. Because the design also says registry calls are fire-and-forget and likely lazy-imported from callsites, PyInstaller can miss them.
   - Suggestion: Add `core.warning_registry` and `core.escalation_evaluator` to `af.spec` P1 scope and acceptance tests for frozen smoke import.

5. [Medium] `.gitignore` policy is not implementable as written
   - Section: "`runtime/warnings/<slug>/` — gitignore" and "`runtime/warnings/_index.json` — commit 대상"
   - Issue: `<slug>` is documentation syntax, not a gitignore glob. Also ignoring `runtime/warnings/` broadly would hide `_index.json` unless explicitly unignored. Current [.gitignore](/Users/hoon/workTree/agent-factory/.gitignore:1) has no runtime warnings rules.
   - Suggestion: Specify exact patterns, e.g. `runtime/warnings/*/`, `runtime/warnings/_global/`, `!runtime/warnings/_index.json`, `!runtime/warnings/.gitkeep`, or the `.af_runtime` equivalent if Finding 1 is fixed that way.

6. [Medium] `_summary.json` update timing conflicts with acceptance
   - Section: "`_summary.json` 갱신은 lazy (10건마다 1회 또는 run 종료 시점)" and acceptance "`python -m core.warning_registry summary --slug=<slug>`"
   - Issue: If summary is lazy, tests or CLI calls immediately after a single record can read stale or missing `_summary.json`. The design does not say whether `summary` recomputes from jsonl or trusts `_summary.json`.
   - Suggestion: Define `summarize(slug)` as recomputing from jsonl when `_summary.json` is stale/missing, or remove lazy summary from P1.

### Missing from Design

- Exact `WarningRegistry.record()` signature, including `workspace`, `run_id`, and default severity handling.
- Path normalization rules for Windows and frozen builds.
- `af.spec` hiddenimports update.
- Idempotent approval-gate link preservation across all gate re-render paths.
- Tests for `approve()`/`invalidate()` retaining the decision link.
- A concrete strategy for research verifier slug/workspace propagation.

### Positive Observations

- The phase grouping fix for `e2e_command_missing` matches the current task schema and avoids scope-phase false blocks.
- The design correctly preserves existing logger and `_warnings` behavior instead of replacing user-visible warnings.