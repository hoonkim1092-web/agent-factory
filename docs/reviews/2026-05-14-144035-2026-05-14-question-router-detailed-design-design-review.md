# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:40
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Stage 0 pause does not actually stop Stage 1-3
   - Section: "`paused_hitl 상태는 별도 채널 (run_ledger + gate)로 처리`" / "`Stage 1~3 건너뜀`"
   - Issue: The proposed insertion is inside `generate_work_items()` before Stage 1, but the current function immediately runs Stage 1, Stage 2, and Stage 3 after that point. `ApprovalGate.initialize()` happens only after all documents are generated at [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1233). `project_pipeline.py` also runs `PlanVerifier` immediately after `generate_work_items()` returns at [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:970). A `paused_hitl` ledger entry alone will not prevent expensive LLM stages or plan verification.
   - Suggestion: Make Stage 0 return a structured status before Stage 1 starts. If `paused_hitl` or `BLOCK`, return only Stage 0 artifacts from `generate_work_items()` or raise a typed pause exception that `ProjectPipeline.prepare_documents()` handles before verifier/structural gates.

2. [Critical] `work_kind` / `blast_radius` source is still missing on the project path
   - Section: "`core/project_pipeline.py:970-971 | 호출 시 work_kind=str(project_brief.get('work_kind') or '') 전달`"
   - Issue: The design relies on `work_kind` and `blast_radius`, but current `ProjectPipeline.prepare_brief()` never writes those fields into `project_brief`; it only stores `route` and calls private memory recall. `ControlPlaneIntake.normalize()` is the actual producer of `NormalizedRequest.work_kind` and `change_impact['blast_radius']` at [core/control/intake.py](D:/hoonProJect/worktrees/agent-factory/core/control/intake.py:93), but repo search shows no main pipeline caller. `RequestRouter.route()` returns only `pipeline`, `intent`, `confidence`, `reasoning`, `risk_level` at [core/request_router.py](D:/hoonProJect/worktrees/agent-factory/core/request_router.py:108).
   - Suggestion: Add a concrete source of truth before `generate_work_items()`: call `ControlPlaneIntake.normalize(task_input, target_workspace, route, board=task_board)` in `prepare_documents()`, then pass `normalized.work_kind` and `normalized.change_impact['blast_radius']`. Also account for normalize side effects: ledger open, state machine init, issue context.

3. [High] Proposed CLI LLM adapter is not implementable with current `CliChatRequest`
   - Section: "`CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=..., response_format={'type':'json'})`"
   - Issue: Current `CliChatRequest` has fields `provider_id`, `model`, `system_prompt`, `task_input`, `workspace`, `run_id`, `timeout_sec`, `auto_approve` only at [core/providers/cli.py](D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:30). It does not accept `messages` or `response_format`. The design also defaults provider to `"claude"`, while registry/provider IDs use values like `claude_cli`.
   - Suggestion: Define `QuestionRouterCliLLMCaller` against the real dataclass: resolve provider via `core.providers.registry`, pass `system_prompt`, `task_input`, `workspace`, `model`, and `timeout_sec`, then parse JSON from `result["text"]`.

4. [High] Budget extension is specified but not wired to the actual scheduler
   - Section: "`TOTAL_BUDGET 800s로 확장 권장`" / "`P7 ... TOTAL_BUDGET 800s 내 완료`"
   - Issue: [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:29) still defines `TOTAL_BUDGET = 600.0`, and Stage 1-3 budgets sum to 600. The design adds 90/180 seconds for Stage 0 but does not specify how `TOTAL_BUDGET`, `STAGE_BUDGET`, cron timeout, or `generate_work_items()` deadline propagation changes.
   - Suggestion: Add an explicit budget patch: `TOTAL_BUDGET = 800`, Stage 0 sub-budget constants, and tests proving new_project and maintenance paths cannot overrun the global deadline.

5. [Medium] Test plan reintroduces invalid blast radius tokens
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`"
   - Issue: The same document correctly says valid blast radius tokens are `isolated`, `module`, `cross_module`, `system_wide`, derived from [core/control/change_impact.py](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16). `local`, `security`, and `data` are invalid as blast radius values; tests using them would conflict with `tests/test_approval_gate_domain_review.py`, which explicitly rejects invalid tokens.
   - Suggestion: Replace with `{isolated, module, cross_module, system_wide}`. Keep `security` and `data` only as `BlockCause` or domain concern inputs.

6. [Medium] Existing clarification flow collision is not resolved
   - Section: "`Goal Clarification QR`" and "`Stage 0 진입`"
   - Issue: The project already has a clarification phase in `agent_launcher.py` before document generation at [agent_launcher.py](D:/hoonProJect/worktrees/agent-factory/agent_launcher.py:363), backed by [core/clarification.py](D:/hoonProJect/worktrees/agent-factory/core/clarification.py:62). The new Stage 0 goal clarification creates a second question system with different schema, storage, and HITL semantics.
   - Suggestion: State whether Stage 0 replaces `core.clarification`, wraps it, or is limited to non-approval modes. Otherwise users may get duplicate questions and divergent `project_brief` mutations.

### Missing from Design

- Exact `ControlPlaneIntake.normalize()` integration point and how to avoid duplicate run ledger/state-machine entries.
- Concrete paused/BLOCK control flow that exits before Stage 1 LLM calls.
- Frozen bundle data inclusion for `core/control/questions/*.yaml`; hiddenimports are listed, but `af.spec` `datas` currently has no questions directory.
- Resume command or entrypoint behavior after `paused_hitl`, including how user answers are written back into artifacts.

### Positive Observations

- The design correctly identifies `af.spec` hiddenimports as mandatory for new `core.control.*` modules.
- The correction from YAML-embedded `schema_hash` to artifact/ledger-only hashes removes the prior self-referential drift problem.