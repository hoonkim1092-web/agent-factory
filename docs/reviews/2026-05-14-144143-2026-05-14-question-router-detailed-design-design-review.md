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

1. [Critical] LLM adapter constructor does not match real `CliChatRequest`
   - Section: "`QuestionRouterCliLLMCaller` ... `CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=..., response_format=...)`"
   - Issue: Current [core/providers/cli.py](D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31) defines `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id="", timeout_sec=0, auto_approve=False)`. It has no `messages` or `response_format`, and provider ids are `*_cli` style, not `"claude"`. This design will raise `TypeError` before any LLM call.
   - Suggestion: Rewrite §6.1 using the real fields: `provider_id="claude_cli"`, `model=""`, `system_prompt=...`, `task_input=prompt`, `workspace=context["workspace"]`, `timeout_sec=int(timeout_sec)`. Drop `response_format` unless `core/providers/cli.py` is explicitly changed.

2. [Critical] `paused_hitl` cannot stop Stage 1-3 in the proposed insertion point
   - Section: "`:1094` 직후 Stage Router 진입" and "`paused 상태면 ApprovalGate.is_execution_open() 채널로 알림`"
   - Issue: In [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1094), the proposed Stage 0 insertion happens before Stage 1, but the gate is not initialized until [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1238), after Stage 1-3 have already generated files. [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:970) only gets control after `generate_work_items()` returns, so a `paused_hitl` ledger entry will not prevent Stage 1-3 execution.
   - Suggestion: Make `StageRouter.run()` return a hard control signal before Stage 1. If `paused_hitl=True` or `block_decisions` exist, initialize/update the gate immediately, add the Stage 0 files to `files`, and return before `_exec_stage1()`.

3. [High] ProjectPipeline auto-approval path bypasses the planned pause channel
   - Section: "`ProjectPipeline 시작 시 RunLedger에서 가장 최근 state='paused_hitl' entry 검색`" and "`gate.is_execution_open() 체크해서 paused면 plan_verifier/structural_gate 모두 skip`"
   - Issue: Current [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1517) initializes a missing gate and immediately calls `_gate.approve(approver="auto", ...)`. There is no existing paused-ledger lookup before this, and no shown code change for this path. This can reopen a paused item unless the design changes `run()`/`prepare()` explicitly.
   - Suggestion: Add a concrete `ProjectPipeline` change: before auto-approve, query `RunLedger` for latest `paused_hitl` for the slug/run, verify schema drift, and return/raise a paused result without calling `approve()`.

4. [High] Frozen build plan omits YAML data files
   - Section: "`af.spec hiddenimports 추가 대상: core.control.stage_router ... core.control.context_scanner`"
   - Issue: Hidden imports only cover Python modules. The new schemas live under `core/control/questions/*.yaml`; current [af.spec](D:/hoonProJect/worktrees/agent-factory/af.spec:33) `datas` does not include that directory. In `dist/af/af.exe`, `QuestionRouter(schema_path=Path("core/control/questions/..."))` can fail even if imports work.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` or equivalent `collect_data_files` to `datas`, and add a frozen smoke test that loads both `goal_clarification.yaml` and `brainstorming.yaml`.

5. [High] ApprovalGate matrix change is underspecified for `cross_module`
   - Section: "`_HIGH_BLAST = ('cross_module', 'system_wide')`" and "`cross_module / system_wide → pause`"
   - Issue: Current [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:229) only enters the domain gate when `blast_radius == "system_wide"`. The snippet changes logic inside that block but does not explicitly remove or widen the outer condition. If implemented literally, `cross_module` never reads `domain-review.md`, contradicting §7.2.
   - Suggestion: Specify the outer condition replacement: domain review should run when `blast_radius in ("cross_module", "system_wide")` or when the Stage 0 result includes a domain-review artifact.

6. [Medium] Acceptance checklist reintroduces invalid blast-radius tokens
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`"
   - Issue: §1.5 says valid tokens are `isolated | module | cross_module | system_wide`, and current [core/control/change_impact.py](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16) confirms that. The P5 checklist still asks for `local`, `security`, and `data`, which existing tests explicitly reject in [tests/test_approval_gate_domain_review.py](D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_review.py:24).
   - Suggestion: Replace with `{isolated, module, cross_module, system_wide}` plus separate tests for `BlockCause.POLICY_VIOLATION` / `SAFETY`.

7. [Medium] `schema_hash` meaning is inconsistent across artifacts
   - Section: "`QuestionRouter.compute_schema_hash(yaml_bytes)`" vs "`ContextScanArtifact.schema_hash: raw markdown SHA-256`"
   - Issue: §4.2 defines schema hash as raw YAML bytes for drift detection, but §5.1 says `ContextScanArtifact.schema_hash` is raw markdown SHA-256. That breaks the resume drift check in §8.6 because artifacts and ledger entries would not be comparable.
   - Suggestion: Split fields: `question_schema_hash` for YAML schema drift and `content_hash` for rendered markdown integrity.

### Missing from Design

- Exact `ProjectPipeline` changes for paused resume and auto-approve bypass.
- `af.spec` data-file packaging for `core/control/questions/*.yaml`.
- Concrete ADR creation path for `NEEDS_ADR` and `BLOCK`; §10.2 still leaves OQ5 partly unresolved.
- A current-code-compatible `QuestionRouterCliLLMCaller` signature.
- A precise gate state format for paused HITL in `approval-gate.md`.

### Positive Observations

- The design correctly identifies the real blast-radius taxonomy from `core/control/change_impact.py`.
- The plan to keep `QuestionRouter` side-effect free and put file/ledger writes in `StageRouter` is architecturally consistent with the existing `core/control` split.