# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 16:18
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] `paused_hitl` caller handling is specified but not actually integrated with the current caller flow
   - Section: "`ProjectPipeline`는 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지해 plan verification을 건너뛴다." / "`af-runner / af-test-runner 미실행`"
   - Issue: Current [core/project_pipeline.py:959](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959) calls `generate_work_items()`, then immediately enters plan verification at [core/project_pipeline.py:970](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:970), T1 structural gate at [core/project_pipeline.py:1021](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1021), and document cross-review at [core/project_pipeline.py:1053](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1053). There is no existing branch that detects `paused-hitl.md` before these gates. If Stage 1~3 are skipped, these QA paths may review/refine incomplete Stage 0 artifacts.
   - Suggestion: Add a concrete `ProjectPipeline.prepare()` branch immediately after `generate_work_items()` that checks `"paused-hitl.md" in work_item_files` or parsed gate status `paused_hitl`, skips plan verification/T1/cross-review, records an incomplete prepared state, and returns a reportable `paused_hitl` result instead of continuing normal preparation.

2. [High] Frozen build plan omits non-Python YAML resources
   - Section: "`af.spec hiddenimports 반영`" and "`core.control.stage_router`, `core.control.question_router`, `core.control.stage_artifacts`, `core.control.verdicts`, `core.control.context_scanner`"
   - Issue: The design adds `core/control/questions/goal_clarification.yaml` and `brainstorming.yaml`, but §12 only lists hidden imports. Current [af.spec:27](/D:/hoonProJect/worktrees/agent-factory/af.spec:27) bundles `skills`, `config`, `policy.yaml`, and `core/research/packs`; it does not include `core/control/questions`. `dist/af/af.exe` can import the new router but fail to load schemas.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `datas`, or require `importlib.resources` loading with explicit PyInstaller data collection. Add a frozen smoke test that loads both active YAML schemas.

3. [High] Ledger hard-fail requirement conflicts with current `RunLedger.append()` behavior
   - Section: "`assumptions.md` append 실패 → Stage 0 warning이 아니라 hard fail" and "`run_ledger paused_hitl event`"
   - Issue: Current [core/control/run_ledger.py:92](/D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:92) `append()` catches all exceptions and only prints at [core/control/run_ledger.py:123](/D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:123). StageRouter cannot know that mandatory `paused_hitl`, `schema_drift`, or assumption events failed.
   - Suggestion: Change the design to require a strict append API, e.g. `append(..., fail_closed=True)` or `append_checked()` that raises on write failure. Add tests for append failure and cross-process lock failure.

4. [Medium] DomainVerdict matrix is not tied to the actual `ApprovalGate` call path
   - Section: "`DomainVerdict와 blast_radius 매트릭스로 gate 판단`" / "`NEEDS_ADR | cross_module, system_wide | ADR 생성 + pause`"
   - Issue: Current domain gate logic only runs during `ApprovalGate.approve()` at [core/approval_gate.py:228](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:228), not during `generate_work_items()` or `ProjectPipeline.prepare()`. `execute()` only checks `is_execution_open()` at [core/project_pipeline.py:1265](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1265), which returns generic `approval_required`. The design does not state where `NEEDS_ADR + cross_module` becomes a pause before normal pipeline work continues.
   - Suggestion: Specify whether StageRouter calls ApprovalGate decision logic during prepare, or whether `ApprovalGate.initialize()` records a paused/blocking status consumed by `ProjectPipeline`. Include exact status values and caller return reasons.

5. [Medium] LLM adapter contract is still too abstract for the current provider API
   - Section: "`QuestionRouter`는 직접 `control_plane_llm.py`를 호출하지 않는다. adapter를 둔다." / "`timeout_sec은 실제 CLI/provider 호출까지 전달되어야 한다.`"
   - Issue: Current provider API is [core/providers/cli.py:31](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31) `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id, timeout_sec)`. The proposed `QuestionRouterLLMCaller.batch_route()` does not define provider selection, `workspace`, `run_id`, model resolution, JSON parsing, API fallback, or partial provider failure behavior.
   - Suggestion: Define the adapter against `CliChatRequest` or `ControlPlaneLLM.generate_json()` explicitly, including provider ordering, timeout propagation, invalid JSON handling, and whether partial batch results can proceed.

### Missing from Design

- Exact `ProjectPipeline` return contract for `paused_hitl`: status, report path, whether `PreparedProject` is created, and how later resume finds it.
- `af.spec` `datas` update for `core/control/questions/*.yaml`.
- Strict ledger write API or verified append path.
- Parser contract for `block_cause` in `domain-review.md`, including invalid/missing/multiple values.
- Compatibility plan for existing `core/clarification.py` so Stage 0 does not duplicate or diverge from existing clarification behavior.

### Positive Observations

- The design correctly preserves `generate_work_items()` as a `dict[str, str]` file-path map instead of returning a new state object, which matches [core/project_pipeline.py:975](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:975) and [core/project_pipeline.py:1125](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1125).
- The blast-radius token set is aligned with existing `ImpactProfile.blast_radius` values in [core/control/change_impact.py:35](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:35).