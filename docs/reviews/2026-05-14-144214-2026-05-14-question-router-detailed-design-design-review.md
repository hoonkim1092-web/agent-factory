# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:42
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Stage 0 pause cannot stop Stage 1~3 as designed
   - Section: "`StageRouter... line 1095...`", "`paused 상태는 ApprovalGate.is_execution_open() 채널로 알림`", "`project_pipeline.py 가 plan_verifier 진입 전 gate.is_execution_open() 체크`"
   - Issue: Current [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1104) enters Stage 1 immediately after the proposed insertion point, and only creates the approval gate at [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1233), after Stage 1~3 already ran. [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:970) goes directly into plan verification after `generate_work_items()` returns; the only `gate.is_execution_open()` check is in execute phase at [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1265).
   - Suggestion: Make `StageRouter.run()` return before Stage 1 when `paused_hitl` or BLOCK occurs, or move gate initialization/check before Stage 1. Do not rely on `ApprovalGate` after Stage 1~3 generation.

2. [High] `QuestionRouterCliLLMCaller` does not match the real provider API
   - Section: "`CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=..., response_format={...})`" and "`def __init__(self, provider: str = \"claude\")`"
   - Issue: Current [core/providers/cli.py](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31) defines `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id, timeout_sec, auto_approve)`. It has no `messages` or `response_format`. Valid provider IDs are `claude_cli`, `gemini_cli`, `codex_cli`, not `"claude"` ([core/providers/cli.py](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:65)).
   - Suggestion: Redefine the adapter around the actual dataclass: choose provider via registry, set `model`, `system_prompt`, `task_input`, `workspace`, `run_id`, and parse JSON from the returned dict.

3. [High] `work_kind` / `blast_radius` will usually be empty in the project pipeline path
   - Section: "`project_pipeline.py:970-971 호출 시 work_kind=str(project_brief.get(\"work_kind\") or \"\") 전달`" and "`StageRouter.run(work_kind, blast_radius, ...)`"
   - Issue: [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:815) writes `requested_role`, `route`, and `generated_at` into `project_brief`, but does not call `ControlPlaneIntake.normalize()` or store `work_kind` / `blast_radius`. `ControlPlaneIntake.normalize()` computes them at [core/control/intake.py](/D:/hoonProJect/worktrees/agent-factory/core/control/intake.py:94) and [core/control/intake.py](/D:/hoonProJect/worktrees/agent-factory/core/control/intake.py:114), but this path is not integrated.
   - Suggestion: Before `generate_work_items()`, call `ControlPlaneIntake.normalize(task_input, target_workspace, route, board=task_board)` or another explicit classifier, then persist `work_kind` and `blast_radius` into `project_brief`.

4. [High] Frozen build plan misses YAML data files
   - Section: "`af.spec hiddenimports 추가 대상` ... `core.control.stage_router`, `question_router`, `stage_artifacts`, `verdicts`, `context_scanner`"
   - Issue: The design adds `core/control/questions/goal_clarification.yaml` and `brainstorming.yaml`, but §9.12 only requires hiddenimports. Current [af.spec](/D:/hoonProJect/worktrees/agent-factory/af.spec:27) `datas` includes `skills`, `config`, `policy.yaml`, and `core/research/packs`, not `core/control/questions`. Frozen `dist/af/af.exe` can import code but fail loading YAML by path.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `datas`, or use PyInstaller-safe package resource loading and test it in the frozen smoke test.

5. [Medium] ApprovalGate ADR/WARN behavior is specified without an implementation owner
   - Section: "`NEEDS_ADR × module → ADR 자동 생성 + WARN + 진행`" and "`self.last_warning = \"needs_adr_proceed\"`"
   - Issue: [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:130) has `last_block_reason` only, no `last_warning`. `approve()` does not generate ADRs, and §10.2 says OQ5 is still “P5 unit test에서 결정.” The E2E path depends on behavior that has no owner or concrete file change.
   - Suggestion: Assign ADR creation explicitly to `StageRouter`, `work_item_generator`, or `ApprovalGate`, and add the concrete output path/event before accepting the design.

6. [Medium] P5 acceptance criteria contradict the corrected blast-radius taxonomy
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`"
   - Issue: §1.5 says valid blast-radius tokens are `isolated`, `module`, `cross_module`, `system_wide`, and moves `security` / `data` to BlockCause/risk axes. The P5 test list still uses the rejected v1 tokens.
   - Suggestion: Replace with `{isolated, module, cross_module, system_wide}` plus separate BlockCause tests for `POLICY_VIOLATION` / `SAFETY`.

7. [Medium] RunLedger locking claim overstates current Unix safety
   - Section: "`RunLedger ... cross-process safe 패턴(_append_lock + lock 파일 + msvcrt.locking Windows/fcntl POSIX)`"
   - Issue: Current [core/control/run_ledger.py](/D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:101) uses `_append_lock` and `msvcrt.locking`; on non-Windows it catches `ImportError` and proceeds without `fcntl`. The design’s portability claim is false.
   - Suggestion: Either add `fcntl.flock` in RunLedger first, or scope the assumption append guarantee to Windows/in-process only.

### Missing from Design

- Concrete pre-Stage-1 stop path for `paused_hitl`, `BLOCK`, and schema drift.
- How `project_brief.work_kind` and `project_brief.blast_radius` are populated in the normal `ProjectPipeline.prepare_documents()` path.
- Frozen bundle resource loading for `core/control/questions/*.yaml`.
- Concrete ADR generation owner/path for `NEEDS_ADR`.
- Provider failover behavior when the selected CLI is unavailable or returns non-JSON.

### Positive Observations

- The v2 document correctly separates `QuestionRouter` as a side-effect-free classifier from `StageRouter` as the artifact/ledger writer.
- The corrected blast-radius taxonomy matches [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:35): `isolated | module | cross_module | system_wide`.