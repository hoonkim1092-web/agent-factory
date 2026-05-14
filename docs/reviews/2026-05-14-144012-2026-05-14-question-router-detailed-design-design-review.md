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

1. [Critical] LLM adapter does not match the real provider API
   - Section: "`class QuestionRouterCliLLMCaller` ... `def __init__(self, provider: str = \"claude\")`" and "`CliChatRequest(provider_id=self._provider, messages=..., response_format=...)`"
   - Issue: This cannot run against current [core/providers/cli.py](D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31). `CliChatRequest` requires `provider_id`, `model`, `system_prompt`, `task_input`, and `workspace`; it has no `messages` or `response_format`. Also valid provider IDs are `claude_cli`, `gemini_cli`, `codex_cli`, not `"claude"` ([core/providers/registry.py](D:/hoonProJect/worktrees/agent-factory/core/providers/registry.py:8)).
   - Suggestion: Define the adapter against the existing `CliChatRequest` shape, use `detect_available_cli_providers()` / `default_chat_model_for_provider()`, and preserve multi-provider failover instead of hardcoding one provider.

2. [High] `paused_hitl` flow is placed after the wrong control boundary
   - Section: "`paused 상태는 ApprovalGate.is_execution_open() 채널로 흘림`" and "`project_pipeline.py 가 plan_verifier 진입 전 gate.is_execution_open() 체크`"
   - Issue: Current `generate_work_items()` creates Stage 1-3 outputs before `ApprovalGate.initialize()` at [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1108) and [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1238). Current `ProjectPipeline` runs `PlanVerifier` immediately after `generate_work_items()` returns ([core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:963)); the gate check is in execute, much later ([core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1270). The proposed pause cannot stop Stage 1-3 or plan verification as written.
   - Suggestion: Either create and mark `approval-gate.md` immediately after Stage 0 and return before Stage 1, or change `generate_work_items()` to return a typed status that `ProjectPipeline.prepare()` handles before `PlanVerifier`.

3. [High] Stage 0 file collection will be overwritten by existing code
   - Section: "`files: dict[str, str] = _collect_stage0_files(work_dir, stage0)`"
   - Issue: The proposed insertion is before the existing `files: dict[str, str] = {}` initialization in [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1102). If implemented literally, Stage 0 artifact paths are discarded and downstream consumers will not see `context-scan.md`, `project-goal.md`, `domain-review.md`, or `assumptions.md`.
   - Suggestion: Move the original `files = {}` before Stage 0 and update it in place, or collect Stage 0 files after the existing initialization.

4. [High] `schema_hash` policy contradicts itself
   - Section: "`schema_hash 필드 없음`", "`YAML 원본 자동 수정 금지`", later "`brainstorming.yaml 의 schema_hash 값 vs raw bytes hash 불일치`", and OQ8 "`startup 시 계산해 파일에 기록`"
   - Issue: §4.2 correctly removes YAML self-hash drift, but §8.6, §9.6, and OQ8 reintroduce YAML `schema_hash` and startup file writes. That recreates the perpetual drift problem the design says it fixed.
   - Suggestion: Remove YAML `schema_hash` from §8.6, §9.6, and OQ8. Drift should compare prior artifact/ledger hash vs current raw YAML hash only.

5. [Medium] Frozen build impact is missing
   - Section: "`core/control/stage_router.py 신규`", "`question_router.py 신규`", "`stage_artifacts.py 신규`", "`context_scanner.py 신규`"
   - Issue: `af.spec` manually lists hidden imports and currently has no `core.control.*` entries except unrelated `core.control_plane_llm` ([af.spec](D:/hoonProJect/worktrees/agent-factory/af.spec:33)). The design does not mention updating `af.spec`, despite adding dynamically imported modules under `core/control`.
   - Suggestion: Add explicit hiddenimports for the new modules or `collect_submodules("core.control")`, then verify `dist/af/af.exe`.

6. [Medium] Budget acceptance does not match current budget enforcement
   - Section: "`TOTAL_BUDGET 800s 내 완료`"
   - Issue: Current `TOTAL_BUDGET = 600.0` exists but is not used as a global deadline; execution uses per-stage budgets from `STAGE_BUDGET` ([core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:29)). Adding Stage 0 time and changing the constant alone will not enforce an 800s cap.
   - Suggestion: Add a real absolute deadline spanning Stage 0-3, or change the acceptance criterion to per-stage timeout behavior.

### Missing from Design

- Exact `ProjectPipeline.prepare()` changes for pausing before `PlanVerifier`.
- Frozen build updates for `af.spec`.
- Resume entrypoint for `paused_hitl`; OQ6 leaves this undecided while P7 requires integration coverage.
- Concrete provider failover behavior for unavailable CLI providers.
- How `last_warning="needs_adr_proceed"` is stored or exposed, since `ApprovalGate` currently only has `last_block_reason`.

### Positive Observations

- The design correctly identifies the valid blast radius taxonomy: `isolated`, `module`, `cross_module`, `system_wide`.
- The decision to keep `QuestionRouter` side-effect free and move file/ledger writes into `StageRouter` is architecturally consistent with the existing control-plane layering.