# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:41
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `paused_hitl` flow cannot skip Stage 1~3 or prepare-time QA
   - Section: "`project_pipeline | plan_verifier 진입 전 gate.is_execution_open() 체크 → False면 plan/structural/cross-review 모두 skip`" and "`Stage 1~3은 진입하지 않음`"
   - Issue: This does not match the current call flow. `generate_work_items()` runs Stage 1, Stage 2, and Stage 3 unconditionally after the proposed StageRouter insertion point, and only initializes `ApprovalGate` near the end. See [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1094), [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1109), [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1238). Also, `project_pipeline.py` runs plan verifier and structural gates immediately after `generate_work_items()`; `gate.is_execution_open()` is only checked later in `execute()`, not before prepare-time QA. See [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:970) and [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1264).
   - Suggestion: Move Stage 0 orchestration out of `generate_work_items()` into `ProjectPipeline` before work-item generation, or make `generate_work_items()` explicitly return early on `stage0.paused_hitl` after creating a paused gate and Stage 0 artifacts. Then add an explicit prepare-time branch that skips plan verifier / structural gate / cross-review for `paused_hitl`.

2. [High] Proposed LLM adapter will not instantiate the real CLI request object
   - Section:
     ```python
     req = CliChatRequest(
         provider_id=self._provider,
         messages=[{"role": "user", "content": prompt}],
         timeout_sec=int(timeout_sec),
         response_format={"type": "json"},
     )
     ```
   - Issue: `CliChatRequest` has no `messages` or `response_format` fields. It requires `provider_id`, `model`, `system_prompt`, `task_input`, and `workspace`. See [core/providers/cli.py](D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31). The default provider `"claude"` is also not a valid provider ID for `execute_cli_chat`; valid IDs are `claude_cli`, `gemini_cli`, `codex_cli` in [core/providers/registry.py](D:/hoonProJect/worktrees/agent-factory/core/providers/registry.py:8).
   - Suggestion: Change the design to build `CliChatRequest(provider_id="claude_cli", model=default_chat_model_for_provider(...), system_prompt=..., task_input=..., workspace=..., timeout_sec=...)`, or define a separate Stage 0 LLM wrapper that adapts to the existing provider registry.

3. [High] ApprovalGate behavior is specified as if new state exists, but the design does not add it
   - Section: "`self.last_warning = \"needs_adr_proceed\"`" and "`approval_gate | NEEDS_ADR × module → ADR 자동 생성 + WARN + 진행`"
   - Issue: `ApprovalGate` currently has `last_block_reason` only; no `last_warning`, no paused state, no ADR creation hook, and no representation of `paused_hitl` in `approval-gate.md`. `initialize()` always writes `execution_open=False` with `status=review_pending`, which is indistinguishable from normal user approval pending. See [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:156) and [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:229).
   - Suggestion: Add an explicit gate state contract before implementation: e.g. `status: paused_hitl`, `stage0_pause_reason`, `paused_question_ids`, and an `approve()` rule that cannot accidentally open execution while HITL answers are missing. Define where ADR auto-creation happens; it is not an `ApprovalGate` capability today.

4. [Medium] Blast radius acceptance tests reintroduce invalid tokens
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`"
   - Issue: The same document correctly states the valid taxonomy is `isolated | module | cross_module | system_wide`, and existing tests explicitly reject `"local"` and `"system"` tokens. `security` and `data` are described as `BlockCause` axes, not blast radius values. See [tests/test_approval_gate_domain_review.py](D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_review.py:4) and [core/control/change_impact.py](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16).
   - Suggestion: Replace the P5 matrix with `NEEDS_ADR × {isolated, module, cross_module, system_wide}`. Test `security` / `data` only through `BlockCause` or `domain_concerns`.

5. [Medium] Frozen build plan covers hidden imports but misses YAML data files
   - Section: "`af.spec hiddenimports 추가 대상: core.control.stage_router, question_router, stage_artifacts, verdicts, context_scanner`"
   - Issue: Stage 0 depends on runtime YAML files under `core/control/questions/*.yaml`, but `af.spec` currently includes data only for `skills`, `config`, `policy.yaml`, and `core/research/packs`. Hidden imports will not bundle question YAMLs. See [af.spec](D:/hoonProJect/worktrees/agent-factory/af.spec:27).
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `datas`, and include a frozen smoke test that loads both `goal_clarification.yaml` and `brainstorming.yaml`.

6. [Medium] Assumption append locking is overstated
   - Section: "`assumptions.md append ... RunLedger의 cross-process safe 패턴(_append_lock + lock 파일 + msvcrt/fcntl locking)을 재사용`"
   - Issue: Current `RunLedger.append()` only attempts `msvcrt`; on non-Windows or lock acquisition failure it writes without a cross-process lock. There is no `fcntl` path in the actual code. See [core/control/run_ledger.py](D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:101).
   - Suggestion: Define and implement a reusable blocking cross-platform file-lock helper before using it for `assumptions.md`. Also specify whether `assumptions.md` is append-only markdown, JSONL, or both, because mixed markdown + JSONL complicates safe resume parsing.

### Missing from Design

- Exact prepare-time paused return contract from `ProjectPipeline`: result shape, CLI message, and whether the run is counted as incomplete or blocked.
- Concrete resume entrypoint: the document says `ProjectPipeline` will handle it, but not which method reads `paused_hitl`, where HITL answers are stored, or how duplicate resumes are prevented.
- `af.spec` `datas` changes for `core/control/questions/*.yaml`.
- A migration plan for existing `tests/test_approval_gate_domain_gate.py`, which currently asserts `NEEDS_ADR` passes for `system_wide`.
- A real timeout integration plan for `TOTAL_BUDGET`; current `TOTAL_BUDGET = 600.0` is defined but not used as the stage scheduler’s governing deadline.

### Positive Observations

- The design correctly verifies current `work_kind` / `blast_radius` propagation from `project_pipeline.py` into `generate_work_items()` and then into `ApprovalGate`.
- The correction to raw-bytes schema hashing avoids the self-referential YAML hash drift problem.