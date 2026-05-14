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

1. [Critical] LLM adapter uses a non-existent `CliChatRequest` API
   - Section: "`CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=int(timeout_sec), response_format={...})`"
   - Issue: [core/providers/cli.py](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31) defines `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id, timeout_sec, auto_approve)`. There is no `messages` or `response_format` field, and default `provider="claude"` is invalid because `get_cli_provider_spec()` expects IDs like `claude_cli`, `gemini_cli`, `codex_cli`.
   - Suggestion: Rewrite §6.1 against the real constructor, following [core/control_plane_llm.py](/D:/hoonProJect/worktrees/agent-factory/core/control_plane_llm.py:114): resolve provider IDs, set `model`, put JSON instructions in `system_prompt`, put batch prompt in `task_input`, pass `workspace`, and test unsupported provider IDs.

2. [High] `paused_hitl` routing is conflated with normal approval-gate closed state
   - Section: "`paused 상태는 ApprovalGate.is_execution_open() 채널로 흘림`" and "`project_pipeline이 plan_verifier 진입 전 gate 체크해서 분기`"
   - Issue: [ApprovalGate.initialize()](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:151) always writes `execution_open=False` for every work item, not only HITL pauses. If [project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:972) checks `gate.is_execution_open()` immediately after `generate_work_items()`, it will treat every newly generated work item as paused and skip verification.
   - Suggestion: Use an explicit Stage 0 status channel, e.g. `RunLedger` latest `state="paused_hitl"` for the same `run_id`, or an `approval-gate.md` metadata field like `stage0_status: paused_hitl|ready|blocked`. Do not infer HITL from `execution_open`.

3. [High] Stage 0 terminal states do not stop Stage 1-3 generation
   - Section: "`StageRouter(...).run(...)`" inserted at `work_item_generator.py:1094` and "`paused_hitl 상태는 별도 채널 ... 반환 dict는 정상 구조`"
   - Issue: The proposed insertion point is before Stage 1, but the shown control flow still continues into `_exec_stage1`, `_exec_stage2`, and `_exec_stage3` in [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1108). A HITL/BLOCK result would still spend plan/spec/design/task LLM budget and write downstream artifacts.
   - Suggestion: Define explicit behavior in §7.1: if `stage0.paused_hitl` or `stage0.domain_verdict == BLOCK`, return only Stage 0 artifact paths after initializing a gate/status marker, and do not enter Stage 1-3.

4. [High] The assumptions append plan relies on a flawed cross-process lock pattern
   - Section: "`assumptions.md append ... run_ledger.py:20 _append_lock 패턴 재사용 + lock 파일 + msvcrt/fcntl locking`"
   - Issue: [RunLedger.append()](/D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:92) does not use `fcntl` on POSIX, and on Windows an `OSError` from `msvcrt.locking(...LK_NBLCK...)` sets `acquired=False` and proceeds to write unlocked. Reusing this for `assumptions.md` does not actually guarantee cross-process append safety.
   - Suggestion: Either implement a real blocking file lock helper in `core/file_lock.py` and reuse it for both ledger and assumptions, or scope MVP to single-process append and remove the cross-process safety claim.

5. [Medium] ApprovalGate migration section still contains stale tokens and wrong env var
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`" and "`AF_SKIP_REVIEW_GATE=1 환경변수 우회`"
   - Issue: The same document says valid `blast_radius` tokens are only `isolated|module|cross_module|system_wide`, and current tests/code use `AF_SKIP_DOMAIN_REVIEW`, not `AF_SKIP_REVIEW_GATE` ([tests/test_approval_gate_domain_gate.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_gate.py:184), [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:233)).
   - Suggestion: Change §9.8 to the four valid tokens and correct §7.2 migration table to `AF_SKIP_DOMAIN_REVIEW`.

### Missing from Design

- A precise paused/block state contract between `StageRouter`, `generate_work_items()`, `ApprovalGate`, and `ProjectPipeline`.
- Real `CliChatRequest` integration details, including provider ID selection and workspace/model handling.
- A real concurrency strategy for `assumptions.md` and ledger writes, not just reuse of the existing incomplete lock.
- Frozen build data inclusion for YAML files under `core/control/questions/`; hiddenimports only cover Python modules.

### Positive Observations

- The design correctly identifies `af.spec` hiddenimports as mandatory for new `core.control.*` modules.
- It grounds the `blast_radius` taxonomy in the current `ChangeImpactProfiler` tokens instead of inventing new categories.