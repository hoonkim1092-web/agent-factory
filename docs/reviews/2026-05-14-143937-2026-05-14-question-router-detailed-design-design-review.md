# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:39
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `paused_hitl` cannot skip Stage 1~3 with the proposed control flow
   - Section: "`paused_hitl 흐름`: ... `project_pipeline.py`가 plan_verifier 진입 전 `gate.is_execution_open()` 체크해서 paused면 plan_verifier/structural_gate 모두 skip" and "Stage 1~3 건너뜀 (§7.1 변경 후 코드 `:1095k` 분기)"
   - Issue: The proposed insertion in `core/work_item_generator.py` only runs `StageRouter` before cleanup, then continues into Stage 1 at `core/work_item_generator.py:1104`. `ApprovalGate.initialize()` is not called until `core/work_item_generator.py:1233-1234`, after Stage 1~3 have already completed. `core/project_pipeline.py:959-981` calls `generate_work_items()` and then immediately enters plan verification; there is no gate check before Stage 1~3 because `generate_work_items()` does not return until after those stages.
   - Suggestion: Add an explicit pause branch immediately after Stage 0. Either return the partial `dict[str, str]` plus a durable pause marker that `project_pipeline.py` checks before plan verification, or initialize/update the gate before Stage 1 and have `generate_work_items()` return early when `stage0.paused_hitl` is true.

2. [High] The concrete `CliChatRequest` adapter uses a non-existent API
   - Section: "`req = CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=int(timeout_sec), response_format={\"type\": \"json\"})`"
   - Issue: Current `core/providers/cli.py:30-39` defines `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id='', timeout_sec=0, auto_approve=False)`. It has no `messages` or `response_format` fields. This design will fail at construction before any provider call.
   - Suggestion: Rewrite `QuestionRouterLLMCaller` against the actual dataclass: choose `model`, pass schema instructions via `system_prompt`, pass serialized questions/context via `task_input`, include `workspace` and `run_id`, and enforce JSON in prompt/parsing rather than `response_format`.

3. [High] Budget math is wrong; `800s` is not enough for the stated path
   - Section: "`TOTAL_BUDGET | 600s | 780s (new_project) / 690s (others)`" and "`TOTAL_BUDGET 800s로 확장 권장`"
   - Issue: Existing budgets are `90 + 400 + 110 = 600` in `core/work_item_generator.py:29-34`. The design adds Goal Clarification `90s` and Brainstorming `180s`, so `new_project` becomes `870s`, not `780s`; non-new-project becomes `780s`, not `690s`. The proposed `800s` cap still under-budgets `new_project` by at least 70 seconds before overhead.
   - Suggestion: Correct the table and acceptance criteria. Either set the budget to at least `900s`, reduce/parallelize Stage 0 calls, or define Stage 0 as consuming existing carry-over rather than adding to total runtime.

4. [High] Frozen build impact is missing for new dynamic modules and YAML resources
   - Section: "`core/control/stage_router.py 신규`", "`core/control/question_router.py 신규`", "`core/control/stage_artifacts.py 신규`", "`core/control/questions/goal_clarification.yaml 신규`"
   - Issue: `af.spec:27-32` includes `datas` for `skills`, `config`, `policy.yaml`, and `core/research/packs`, but not `core/control/questions`. `af.spec:33+` has explicit hiddenimports, but no `core.control.stage_router`, `core.control.question_router`, `core.control.stage_artifacts`, `core.control.verdicts`, or `core.control.context_scanner`. Because the design imports `StageRouter` dynamically inside `generate_work_items()`, PyInstaller can miss it and the YAML files in `dist/af/af.exe`.
   - Suggestion: Add a frozen-build section requiring hiddenimports for every new `core.control.*` module and `datas=[('core/control/questions', 'core/control/questions')]`, plus a bundled executable smoke test that loads both YAML schemas.

5. [High] The design reintroduces invalid `blast_radius` tokens it says were removed
   - Section: "`security` (blast_radius) → BlockCause", "`data` (blast_radius) → BlockCause", but later "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`" and "`blast_radius=\"security\"`"
   - Issue: The document correctly states valid tokens are `isolated`, `module`, `cross_module`, `system_wide`, and existing `tests/test_approval_gate_domain_review.py` explicitly guards against invalid `local`/`system`. But §9.8 and §8.3 still use `local`, `security`, and `data` as `blast_radius` values.
   - Suggestion: Replace the P5 matrix with `{isolated, module, cross_module, system_wide}`. Model security/data through `BlockCause.POLICY_VIOLATION` / `BlockCause.SAFETY` or `risk_level`, not `blast_radius`.

6. [Medium] `assumptions.md` locking is specified by reference, but no usable file append API exists
   - Section: "`assumptions.md` ... `core/control/run_ledger.py:20` `_append_lock` 패턴 재사용 + lock 파일 + msvcrt/fcntl locking"
   - Issue: `RunLedger.append()` only appends to `.af_runtime/control/run_ledger.jsonl` (`core/control/run_ledger.py:92-124`). The proposed `append_assumption()` writes ledger metadata, not `<work_dir>/assumptions.md`. Also the current lock implementation uses `msvcrt`; it does not implement `fcntl` despite the design claiming Windows/POSIX locking.
   - Suggestion: Define a concrete `append_locked_text(path, line)` helper or extend `core/file_io.py`, then use it for `assumptions.md`. If POSIX support is required, implement and test `fcntl` rather than assuming RunLedger already has it.

### Missing from Design

- Exact `project_pipeline.py` gate-check location and behavior after `generate_work_items()` returns a paused Stage 0 result.
- `af.spec` hiddenimports and `datas` updates for frozen builds.
- Corrected runtime budget math and cron impact after adding 270s to `new_project`.
- Concrete resume entry point for paused HITL; §10 leaves it unresolved, but §8 treats it as an E2E pass path.
- A real adapter contract for `CliChatRequest` using current fields.

### Positive Observations

- The design correctly verifies that `work_kind` and `blast_radius` currently reach `ApprovalGate` but are not used for Stage branching.
- Separating `QuestionRouter` side-effect-free classification from `StageRouter` artifact/ledger writes is architecturally consistent with the existing control-plane layering.