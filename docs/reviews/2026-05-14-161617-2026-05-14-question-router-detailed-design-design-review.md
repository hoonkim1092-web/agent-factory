# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 16:16
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `paused_hitl` can still be auto-approved through legacy `ProjectPipeline.run()`
   - Section: "`paused_hitl` ... `af-runner / af-test-runner 미실행`" and "`ProjectPipeline는 paused-hitl.md 또는 approval-gate.md metadata를 감지해 plan verification을 건너뛴다.`"
   - Issue: Current `core/project_pipeline.py:1508-1513` always calls `_gate.approve(approver="auto")` and then `execute()` in `run()`. Current `core/approval_gate.py:155-177` has no `status`/`execution_open` parameters, and `approve()` does not reject a future `paused_hitl` status. A paused work item can therefore be converted to `execution_open: true` by the compatibility path.
   - Suggestion: Specify and test one hard rule: `ApprovalGate.approve()` must refuse `status=paused_hitl`, and `ProjectPipeline.run()` must return an incomplete/paused result without auto-approval or `execute()` when `paused-hitl.md` exists.

2. [High] Frozen build design covers Python imports but not YAML schema resources
   - Section: "`af.spec hiddenimports 반영`" with new modules `core.control.stage_router`, `question_router`, `stage_artifacts`, `verdicts`, `context_scanner`
   - Issue: The design adds `core/control/questions/goal_clarification.yaml` and `brainstorming.yaml`, but only mentions hiddenimports. Current `af.spec:27-31` bundles `skills`, `config`, `policy.yaml`, and `core/research/packs`; it does not bundle `core/control/questions`. `dist/af/af.exe` can import the router but fail loading schemas.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `datas`, or require `importlib.resources`-based loading plus a frozen smoke test that loads both YAML files.

3. [High] Ledger “hard fail” requirement conflicts with current `RunLedger.append()` behavior
   - Section: "`assumptions.md ... append 실패 시 ... hard fail`" and "`paused_hitl event`, `schema_drift event`"
   - Issue: Current `core/control/run_ledger.py:92-124` catches all append exceptions and only prints `[RunLedger] append failed`. If StageRouter uses `RunLedger.append()` for mandatory `paused_hitl`, assumption, or schema drift events, the design’s audit guarantees silently fail.
   - Suggestion: Define a strict ledger API, e.g. `append_strict()` returning/raising on failure, and require Stage 0 to use it for assumptions and pause/schema-drift events. Keep current best-effort append only for non-critical telemetry.

4. [Medium] Atomic write requirement is not connected to the actual `ApprovalGate` writer
   - Section: "`approval-gate.md` ... temp file → atomic replace" and paused branch "`gate.initialize(... status='paused_hitl', execution_open=False)`"
   - Issue: `approval-gate.md` is written by `ApprovalGate.initialize()`, which currently calls `write_text()` at `core/approval_gate.py:176`. `write_text()` in `core/file_io.py:117-120` is a direct truncate/write, not atomic. The design says StageRouter writes atomically, but paused flow delegates this artifact to ApprovalGate.
   - Suggestion: Add an explicit implementation requirement to replace ApprovalGate’s writes with a shared `atomic_write_text()` helper, or have StageRouter render/write the paused gate artifact itself.

5. [Medium] New artifacts store machine-specific paths without a portability contract
   - Section: "`ContextScanArtifact.work_dir: str`", `relevant_files`, `existing_tests`, and "`PausedHitlArtifact.resume_entrypoint: str`"
   - Issue: The project already has multi-PC path sensitivity; `ProjectPipeline` converts planning paths through `to_portable_path()` at `core/project_pipeline.py:1120-1125`. The new artifact schemas do not say whether paths are absolute, workspace-relative, doc-root-relative, or portable. This can break resume on another PC or under frozen/source path differences.
   - Suggestion: Require all persisted artifact paths to be project-root/doc-root relative, with runtime-only absolute paths kept out of markdown artifacts.

### Missing from Design

- Explicit `ProjectPipeline.run()` compatibility behavior for `paused_hitl`.
- `ApprovalGate.approve()` refusal semantics for paused/blocked statuses.
- `af.spec` `datas` packaging for YAML schemas.
- Strict ledger append API or failure propagation plan.
- Path portability rules for Stage 0 artifacts and resume metadata.

### Positive Observations

- The design correctly keeps `QuestionRouter` side-effect free and assigns artifact/ledger writes to `StageRouter`.
- It correctly preserves the existing `generate_work_items() -> dict[str, str]` return contract instead of introducing a new status object into current callers.