# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:43
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] LLM adapter cannot run against current provider API
   - Section: "`QuestionRouterCliLLMCaller` ... `provider: str = \"claude\"` ... `CliChatRequest(... messages=..., response_format=...)`"
   - Issue: Current [core/providers/cli.py](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31) defines `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id="", timeout_sec=0, auto_approve=False)`. It has no `messages` or `response_format`. Also valid provider IDs are `claude_cli`, `gemini_cli`, `codex_cli`, not `"claude"` ([core/providers/registry.py](/D:/hoonProJect/worktrees/agent-factory/core/providers/registry.py:8)).
   - Suggestion: Rewrite §6.1 around the real dataclass: resolve provider via `parse_provider_list()` / active provider settings, choose model via registry defaults, pass schema instructions in `system_prompt`, serialized questions/context in `task_input`, include `workspace` and `run_id`, and parse JSON from `execute_cli_chat()` output.

2. [High] Stage 0 pause/block does not actually stop Stage 1-3
   - Section: "`1095e: stage0 = StageRouter(...).run(...)`", "`1095m: files = _collect_stage0_files(...)`", "`paused_hitl 상태는 별도 채널 ... 반환 dict는 정상 구조`"
   - Issue: The proposed insertion in [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1072) collects Stage 0 files but then continues directly into cleanup and Stage 1-3 generation. §8.3 says "Stage 1~3은 진입하지 않음", but §7.1 has no branch for `stage0.paused_hitl` or `stage0.block_decisions`. ApprovalGate is initialized only after Stage 3 at [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1238), so it is too late to prevent plan/spec/design/task generation.
   - Suggestion: Define an explicit pre-Stage1 stop path. Either initialize a Stage 0 gate before Stage 1-3 and return only Stage 0 artifacts, or raise/return a typed `StageZeroPaused`/`StageZeroBlocked` result that `project_pipeline.prepare_documents()` handles before plan/spec/design generation.

3. [High] `gate.is_execution_open()` cannot distinguish paused HITL from normal review-pending
   - Section: "`paused 상태는 ApprovalGate.is_execution_open() 채널로 흘림`", "`project_pipeline.py 가 plan_verifier 진입 전 gate.is_execution_open() 체크해서 paused면 ... skip`"
   - Issue: Current [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:156) `initialize()` always writes `execution_open=False` for every new work item. It receives only `work_item_id`, `run_id`, `work_kind`, and `blast_radius`; no `paused_hitl` flag or paused question IDs. A naïve `is_execution_open()` check after `gate.initialize()` would skip plan verification for every approval-mode work item, not only HITL-paused ones.
   - Suggestion: Add explicit gate metadata such as `stage0_status: ready|paused_hitl|blocked` and `paused_hitl_ids`, or have `project_pipeline` read `RunLedger.state == "paused_hitl"` rather than using `execution_open` as an overloaded signal.

4. [High] `work_kind` / `blast_radius` have no live source in the project pipeline path
   - Section: "`core/project_pipeline.py:970-971` 호출 시 `work_kind=str(project_brief.get(\"work_kind\") or \"\")` 전달", "`core/control/intake.py ... 그대로`"
   - Issue: [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:818) currently writes `requested_role`, `route`, and `generated_at` into `project_brief`, but not `work_kind` or `blast_radius`. `ControlPlaneIntake.normalize()` produces those fields, but repo search shows no caller of `normalize()` in the project path; [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:710) only calls the private `_recall_from_memory()`. StageRouter will usually receive empty strings.
   - Suggestion: Add a concrete integration point before `generate_work_items()`: call `ControlPlaneIntake.normalize(task_input, target_workspace, route, board=task_board)` or a side-effect-free extraction API, then write `work_kind` and `change_impact["blast_radius"]` into `project_brief`.

5. [Medium] Frozen build section omits YAML data bundling
   - Section: "`af.spec hiddenimports 추가 대상` ... five `core.control.*` modules"
   - Issue: §9.12 covers hiddenimports, but the new runtime schemas live under `core/control/questions/*.yaml`. Current [af.spec](/D:/hoonProJect/worktrees/agent-factory/af.spec:27) bundles `skills`, `config`, `policy.yaml`, and `core/research/packs`, but not `core/control/questions`. `QuestionRouter(schema_path: Path)` will fail in `dist/af/af.exe` if those files are not included or loaded via package resources.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `datas`, or switch the design to `importlib.resources` and document the PyInstaller-compatible resource path.

6. [Medium] Acceptance tests still use invalid historical blast-radius tokens
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`"
   - Issue: Earlier §1.5 correctly says valid tokens are `isolated|module|cross_module|system_wide`, and [tests/test_approval_gate_domain_review.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_review.py:5) explicitly rejects `"local"`. The P5 checklist reintroduces `local`, `security`, and `data`, which conflicts with the design’s corrected taxonomy and will produce misleading tests.
   - Suggestion: Replace with `NEEDS_ADR × {isolated, module, cross_module, system_wide}` plus separate BlockCause tests for `POLICY_VIOLATION` / `SAFETY`.

### Missing from Design

- A precise `ProjectPipeline` code path for paused resume. §8.3 says `start_run()` or equivalent, but this repo exposes `prepare_brief()`, `prepare_documents()`, `prepare()`, and launcher orchestration; no concrete method or ledger query contract is specified.
- A side-effect boundary for `ControlPlaneIntake.normalize()`. Calling it directly opens ledger/state-machine entries; the design needs to say whether Stage 0 should accept those side effects or extract classification into a smaller API.
- A concrete schema/resource path strategy for frozen builds and multi-PC paths.

### Positive Observations

- The design correctly identifies the current `generate_work_items()` path and line-level placement around [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1072), instead of proposing a detached subsystem.
- Separating `QuestionRouter` as a side-effect-free classifier from `StageRouter` as the artifact/ledger writer is consistent with the project’s control-plane layering.