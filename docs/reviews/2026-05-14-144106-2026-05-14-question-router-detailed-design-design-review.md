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

1. [Critical] `paused_hitl` cannot stop Stage 1-3 in the proposed control flow
   - Section: "`Stage Router 진입 ... :1094 직후`" and "`project_pipeline ... plan_verifier 진입 전 gate.is_execution_open() 체크 → False면 plan/structural/cross-review 모두 skip`"
   - Issue: Current [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1072) runs Stage 1-3 immediately after the proposed insertion point and only creates `ApprovalGate` at [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1238). Current [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:963) calls `generate_work_items()` and then runs `PlanVerifier` directly; there is no `gate.is_execution_open()` check before plan/structural gates.
   - Suggestion: Design must specify an explicit early-exit contract after `StageRouter.run()`, or move approval-gate initialization/checking before Stage 1. If keeping `dict[str, str]`, add concrete `ProjectPipeline.prepare_documents()` branching after `generate_work_items()` before `PlanVerifier`.

2. [High] `ApprovalGate.initialize()` does not recognize paused/block state
   - Section: "`gate.initialize()` 호출 시 paused 상태 인식 → `execution_open=false`"
   - Issue: Current [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:156) only renders `approval-gate.md` with `status="review_pending"` and `execution_open=False`. Domain review logic exists in `approve()` at [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:229), not in `initialize()`. RunLedger `paused_hitl` entries are not read by ApprovalGate.
   - Suggestion: Add a concrete `initialize(stage0_result=...)` or `apply_stage0_status()` contract, including exact persisted fields in `approval-gate.md` and how `is_execution_open()` distinguishes normal pending approval from HITL pause/block.

3. [High] LLM adapter signature does not match the real provider API
   - Section: "`CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=int(timeout_sec), response_format={...})`"
   - Issue: Current [core/providers/cli.py](D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31) `CliChatRequest` requires `provider_id`, `model`, `system_prompt`, `task_input`, and `workspace`. It has no `messages` or `response_format` fields. The sample also defaults provider to `"claude"`, while registry/provider IDs use CLI IDs such as `claude_cli`.
   - Suggestion: Rewrite §6.1 against the actual `CliChatRequest` contract: `provider_id="claude_cli"`, explicit `model`, `system_prompt`, `task_input`, `workspace`, `run_id`, and `timeout_sec`.

4. [High] P5 test plan still uses invalid blast-radius tokens
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`"
   - Issue: The same document says `local`, `security`, and `data` were removed from `blast_radius` (§1.5). Existing [tests/test_approval_gate_domain_review.py](D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_review.py:24) explicitly rejects invalid `local` and `system` tokens.
   - Suggestion: Replace P5 acceptance with `{isolated, module, cross_module, system_wide}` and add separate tests for `BlockCause.POLICY_VIOLATION` / `SAFETY`.

5. [Medium] Frozen build plan omits YAML data files
   - Section: "`af.spec hiddenimports 추가 대상 ... core.control.stage_router ... question_router ... context_scanner`"
   - Issue: Hidden imports cover Python modules only. New `core/control/questions/*.yaml` files will not be bundled by PyInstaller unless added to `datas` or loaded via bundled resources. Current [af.spec](D:/hoonProJect/worktrees/agent-factory/af.spec:33) has explicit hiddenimports but no `core/control/questions` data inclusion.
   - Suggestion: Add `datas=[('core/control/questions/*.yaml', 'core/control/questions')]` or use `importlib.resources` with a PyInstaller-compatible data collection rule.

6. [Medium] Assumption append locking is overstated and partly private
   - Section: "`assumptions.md append ... run_ledger.py:20 _append_lock 패턴 재사용 + lock 파일 + msvcrt/fcntl locking`"
   - Issue: Current [core/control/run_ledger.py](D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:102) uses `_append_lock` plus `msvcrt`; there is no `fcntl` path. On Unix, `ImportError` makes `acquired=False`, then the write still proceeds unlocked. `_append_lock` is also private module state, not a reusable public artifact append API.
   - Suggestion: Either add a public `append_jsonl_locked(path, line)` helper with Windows and POSIX locking, or write assumptions only through `RunLedger.append()` and generate `assumptions.md` from ledger state.

### Missing from Design

- Exact `ProjectPipeline.prepare_documents()` changes required to pause before plan verifier and structural gates.
- Exact persisted `approval-gate.md` fields for `paused_hitl`, `block_decision`, and schema drift.
- Frozen build data-file packaging for `goal_clarification.yaml` and `brainstorming.yaml`.
- Failure behavior when `RunLedger.append()` silently catches exceptions.
- Concrete resume input path/parser contract for `hitl-response.md`.

### Positive Observations

- The design correctly identifies the existing Stage 0 insertion point near [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1094) and preserves the public `generate_work_items()` return type.
- The schema-hash self-reference issue is handled well by removing `schema_hash` from YAML and recording the computed hash only in artifacts/ledger.