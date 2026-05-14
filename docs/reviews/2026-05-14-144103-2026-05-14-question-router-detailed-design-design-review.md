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

1. [Critical] `CliChatRequest` adapter code does not match the real provider API
   - Section: "`CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=int(timeout_sec), response_format={...})`" ([design](/D:/hoonProJect/worktrees/agent-factory/docs/2026-05-14-question-router-detailed-design.md:536))
   - Issue: Real `CliChatRequest` has required fields `model`, `system_prompt`, `task_input`, `workspace`; it has no `messages` or `response_format` fields ([core/providers/cli.py](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:30)). This will raise `TypeError` before Stage 0 can call any LLM.
   - Suggestion: Rewrite §6.1 around the actual `CliChatRequest` contract, following `ControlPlaneLLM._generate_via_cli()` usage ([core/control_plane_llm.py](/D:/hoonProJect/worktrees/agent-factory/core/control_plane_llm.py:114)). Use provider IDs like `claude_cli`, not `"claude"`.

2. [Critical] Paused HITL skip path is asserted but not wired into the real `ProjectPipeline`
   - Section: "`project_pipeline ... gate.is_execution_open() 체크 → False면 plan/structural/cross-review 모두 skip`" ([design](/D:/hoonProJect/worktrees/agent-factory/docs/2026-05-14-question-router-detailed-design.md:838))
   - Issue: Current `ProjectPipeline.prepare()` calls `generate_work_items()` and then immediately runs `PlanVerifier`, structural gates, T1 QA, and document cross-review before it creates `PreparedProject` or checks `gate.is_execution_open()` ([core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959), [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:970)). `is_execution_open()` is only checked later in execution ([core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1270)). The proposed channel cannot skip those prepare-time QA steps.
   - Suggestion: Add an explicit Stage 0 pause signal before plan verification, either by returning a typed wrapper from `generate_work_items()` or by checking a newly written paused marker immediately after `generate_work_items()` in `prepare()`. Do not rely on `PreparedProject.gate()` because it is created too late.

3. [High] ApprovalGate cannot “recognize paused state” during `initialize()`
   - Section: "`gate.initialize()` 호출 시 paused 상태 인식 → `execution_open=false`" ([design](/D:/hoonProJect/worktrees/agent-factory/docs/2026-05-14-question-router-detailed-design.md:837))
   - Issue: `ApprovalGate.initialize()` currently only renders `approval-gate.md` with `execution_open=False` for every work item, paused or not ([core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:155)). It accepts only `work_item_id`, `run_id`, `work_kind`, and `blast_radius`; no `paused_hitl`, `paused_hitl_ids`, or block cause metadata is passed.
   - Suggestion: Add explicit paused metadata to `ApprovalGate.initialize()` or write a separate Stage 0 status file that `project_pipeline.py` reads before QA. Otherwise paused and normal “awaiting approval” states are indistinguishable.

4. [High] Assumption append locking is based on a misread of `RunLedger`
   - Section: "`assumptions.md` ... `core/control/run_ledger.py:20` `_append_lock` 패턴 재사용 + lock 파일 + msvcrt/fcntl locking" ([design](/D:/hoonProJect/worktrees/agent-factory/docs/2026-05-14-question-router-detailed-design.md:460))
   - Issue: The real `RunLedger` lock only attempts `msvcrt.locking`; there is no `fcntl` branch, and on non-Windows it sets `acquired=False` then still writes without cross-process locking ([core/control/run_ledger.py](/D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:104)). Also `append_assumption()` only appends to `run_ledger.jsonl`; it does not define a locked append helper for `<work_dir>/assumptions.md`.
   - Suggestion: Define a concrete `append_assumption_markdown()` helper with Windows and POSIX locking, or explicitly scope Stage 0 assumptions writes to single-process Windows only. Do not cite `RunLedger` as cross-platform-safe until it actually is.

5. [Medium] Test plan contradicts the project’s current env var
   - Section: "`test_skip_env_bypasses_domain_gate` ... `AF_SKIP_REVIEW_GATE=1`" ([design](/D:/hoonProJect/worktrees/agent-factory/docs/2026-05-14-question-router-detailed-design.md:742))
   - Issue: The actual code and tests use `AF_SKIP_DOMAIN_REVIEW`, not `AF_SKIP_REVIEW_GATE` ([core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:231), [tests/test_approval_gate_domain_gate.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_gate.py:184)). Implementers following the doc will update the wrong compatibility test.
   - Suggestion: Replace `AF_SKIP_REVIEW_GATE` with `AF_SKIP_DOMAIN_REVIEW` or explicitly design a migration if a new env var is intended.

6. [Medium] Acceptance criteria still use removed blast-radius tokens
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`" ([design](/D:/hoonProJect/worktrees/agent-factory/docs/2026-05-14-question-router-detailed-design.md:975))
   - Issue: The same document says valid blast radius tokens are `isolated|module|cross_module|system_wide`, matching `ChangeImpactProfiler` ([core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16)). `local`, `security`, and `data` are invalid for this axis.
   - Suggestion: Change P5 tests to `{isolated, module, cross_module, system_wide}` and add separate `BlockCause` tests for `POLICY_VIOLATION` / `SAFETY`.

### Missing from Design

- Exact `ProjectPipeline.prepare()` insertion point for paused HITL before `PlanVerifier`.
- Concrete schema/status persisted by `ApprovalGate` or Stage 0 to distinguish `paused_hitl` from ordinary approval pending.
- Real provider adapter contract using `CliChatRequest(model, system_prompt, task_input, workspace, timeout_sec)`.
- Cross-platform append implementation for `assumptions.md`, not just a reference to `RunLedger`.
- Resume conflict policy when multiple `paused_hitl` entries exist for the same workspace/run.

### Positive Observations

- The design correctly identifies the existing `generate_work_items()` return type risk and tries to preserve `dict[str, str]`, which protects current callers around `work_item_files.values()`.
- The frozen build section explicitly lists new `core.control.*` modules for `af.spec` hiddenimports, matching the project’s PyInstaller risk profile.