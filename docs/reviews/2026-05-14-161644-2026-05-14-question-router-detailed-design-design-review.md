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

1. [Critical] `paused_hitl` can be auto-approved and executed through `ProjectPipeline.run()`
   - Section: "`paused_hitl`는 성공이 아니다... runner_continued = false" / "`ProjectPipeline`는 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지하고... af-runner / af-test-runner 미실행"
   - Issue: Existing `ProjectPipeline.run()` unconditionally calls `_gate.approve(approver="auto", run_id=prepared.run_id)` before `execute()` at `core/project_pipeline.py:1508-1512`. `ApprovalGate.approve()` has no guard for `status == "paused_hitl"` at `core/approval_gate.py:179+`; it can rewrite the gate to `status="approved"` and `execution_open=True`. This defeats the design’s paused contract.
   - Suggestion: Design must require `ApprovalGate.approve()` to refuse `paused_hitl`, and `ProjectPipeline.run()` must detect `paused-hitl.md` before auto-approval and return an incomplete/pending result.

2. [High] Caller handling is underspecified for the actual `prepare_documents()` path
   - Section: "`ProjectPipeline`는 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지하고 plan verification을 건너뛴다."
   - Issue: The real caller runs PlanVerifier immediately after `generate_work_items()` at `core/project_pipeline.py:970-1011`, then structural gate, T1 QA, document review, planning file assembly. The design states the behavior but does not specify the exact early-return location or result shape. A paused file map will still flow into verification unless implementation adds a branch before line 970.
   - Suggestion: Add a concrete patch contract: immediately after `generate_work_items()` at `core/project_pipeline.py:959-968`, if `"paused-hitl.md"` exists in returned paths, skip lines `970-1116`, build `PreparedProject` with `paused_hitl=True` metadata, and make `execute()` return `reason="paused_hitl"` before approval checks.

3. [High] Return map key names conflict with existing filename-key convention
   - Section: paused example returns `{ "approval_gate": ".../approval-gate.md", "domain_review": ".../domain-review.md", ... }`
   - Issue: Current generator returns keys like `"feature-plan.md"` and `"approval-gate.md"` at `core/work_item_generator.py:1118,1173,1235`. `ProjectPipeline` has logic that checks `if _doc_name.endswith(".md") and _doc_name != "approval-gate.md"` at `core/project_pipeline.py:1060-1062`. If Stage 0 returns underscore keys (`domain_review`, `project_goal`, `paused_hitl`), existing document handling silently treats them differently.
   - Suggestion: Use filename keys consistently: `"approval-gate.md"`, `"domain-review.md"`, `"project-goal.md"`, `"context-scan.md"`, `"assumptions.md"`, `"paused-hitl.md"`.

4. [High] Frozen build misses YAML data packaging
   - Section: "추가 대상: `core.control.stage_router`, ... `core.control.context_scanner`" and "af.spec hiddenimports 반영"
   - Issue: The design adds `core/control/questions/goal_clarification.yaml` and `brainstorming.yaml`, but `af.spec` only packages `skills`, `config`, `policy.yaml`, and `core/research/packs` as datas at `af.spec:27-32`. Hiddenimports do not include YAML data files, so frozen `dist/af/af.exe` can import the router but fail loading question schemas.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `af.spec` datas and include a frozen smoke test that loads both YAML schemas.

5. [Medium] LLM timeout contract requires changing an existing callee, not just adding an adapter
   - Section: "`timeout_sec`는 실제 CLI/provider 호출까지 전달되어야 한다. 기존 hardcoded timeout_sec=300 경로를 우회하거나 확장한다."
   - Issue: `ControlPlaneLLM._generate_via_cli()` hardcodes `timeout_sec=300` in `CliChatRequest` at `core/control_plane_llm.py:114-124`; public `generate()` / `generate_json()` accept no timeout. A `QuestionRouterLLMCaller.batch_route(... timeout_sec)` cannot propagate timeout unless the design changes `ControlPlaneLLM` signatures or bypasses it.
   - Suggestion: Specify one approach: add optional `timeout_sec` to `ControlPlaneLLM.generate/generate_json/_generate_via_cli`, or make the adapter call `execute_cli_chat()` directly.

6. [Medium] Atomic write policy conflicts with current shared helper
   - Section: "domain-review.md ... approval-gate.md temp file → atomic replace"
   - Issue: Existing `core.file_io.write_text()` is non-atomic (`open(..., "w")`) at `core/file_io.py:117-120`, and both `ApprovalGate.initialize()` and normal work-item generation use it. The design says artifacts must be atomic but does not state whether to replace `write_text()` globally or add a new helper.
   - Suggestion: Define `atomic_write_text(path, content)` in `core/file_io.py`, use it for Stage 0 artifacts and `approval-gate.md`, and avoid changing all existing writes unless intentionally scoped.

### Missing from Design

- Exact `ProjectPipeline.run()` behavior for paused HITL auto-approval.
- Exact early-return location in `prepare_documents()` before PlanVerifier/T1 QA/document review.
- Frozen build `datas` packaging for `core/control/questions/*.yaml`.
- Resume input format and where user HITL answers are stored before Stage 0 re-run.
- Tests for `ProjectPipeline.run()` ensuring paused HITL does not call `execute()` or `DynamicOrchestrator`.

### Positive Observations

- The design correctly preserves `generate_work_items()` as `dict[str, str]`, matching current callers at `core/project_pipeline.py:975` and planning file assembly at `core/project_pipeline.py:1118-1125`.
- It correctly identifies the current `ApprovalGate.initialize()` hardcoded `status="review_pending"` and `execution_open=False` behavior and proposes a backward-compatible signature extension.