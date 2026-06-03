# Design Review: 2026-06-03-af-right-sized-execution-detailed-design

> Source: docs/2026-06-03-af-right-sized-execution-detailed-design.md
> Date: 2026-06-03 23:57
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] Tier3 acceptance example is false with current `blast_radius`
   - Section: "`core/providers/cli.py`(Tier3)" and "sensitive 파일 변경 task (예: `core/providers/cli.py` Tier3) → blast_radius floor로 **full pipeline**."
   - Issue: `scripts/blast_radius.py` path-only Tier3 pins/prefixes do not include `core/providers/cli.py` or `core/providers/`. `classify_path()` will return default Tier2 unless content scanning is used, but the design explicitly says `_max_tier()` uses `classify_path` only.
   - Suggestion: Either add `core/providers/cli.py`/`core/providers/` to `_TIER3_PATHS`/`_TIER3_PREFIXES`, or change router floor to `classify_with_content(rel_path, workspace)` and update frozen-build/test expectations.

2. [High] Self-modification floor may be ineffective in dogfood worktrees
   - Section: "`route = classify(state.task, state._cwd(), changed_files=scope)`" and "`workspace가 agent-factory 소스이고 scope가 core/·.githooks/·af.spec 등을 건드리면 True`"
   - Issue: after ISOLATE, `state._cwd()` is `%USERPROFILE%/.af-dogfood/<run>/worktree`, not `D:\warkSpaces\agent-factory`. If `_is_self_modification()` checks that `workspace` is the source repo path, the floor can fail in the exact dogfood path where it is introduced.
   - Suggestion: Make `_is_self_modification()` path-root independent: decide self-mod from normalized repo-relative `changed_files`, or pass `state.source_workspace` separately to `classify`.

3. [High] `scope=[]` behavior is contradictory
   - Section: "`scope=[] ... → **light 거부, full fallback**" vs test "`R-FB-NOSCOPE | scope=[] 빈 리스트 | floor Tier3 검사 skip, 저신뢰 취급 검증`"
   - Issue: the public `classify()` contract says empty `changed_files` is low-confidence/fallback, but §4.1 still calls `classify(... changed_files=scope)` and then separately gates `if route.is_light() and scope`. That means `classify()` may return light for no-scope and dogfood silently overrides to full. Tests can pass while router semantics remain unsafe for future callers.
   - Suggestion: Put the no-scope fallback inside `core/right_sized_router.classify()` itself and assert `source=="fallback"`/`is_light()==False` in `R-FB-NOSCOPE`.

4. [Medium] Light-path cost/behavior estimate understates actual work
   - Section: "light 경로 = `compile_spec(...) → run_premortem → build_plan → _run_implement_phase → _run_verify_phase`" and "light 경로의 유일한 LLM 호출은 `_run_implement_phase` 내부 `_ai_executor`(codegen 1~N회) + `_router_llm.generate_json`"
   - Issue: current `_run_implement_phase()` executes every plan step with `commands`, and only commandless steps go to `_ai_executor`. `build_plan()` can create investigation and verification command steps from `run_premortem()`. So light path may run shell/pytest commands during DEVELOP before VERIFY, not just AI codegen.
   - Suggestion: Split `_run_implement_phase` into “AI implementation only” vs “execute command steps”, or explicitly accept duplicate command execution and update cost/failure scenarios.

5. [Medium] Provider failure fallback is specified, but retry/caching cost is not bounded
   - Section: "DEVELOP마다 generate_json 1회 추가" and fallback triggers include "`_router_llm.generate_json` 예외"
   - Issue: `ControlPlaneLLM.generate_json()` can try multiple CLI providers with 300s timeout each before API fallback. A router failure could add minutes before falling back to full pipeline, which defeats “right-sized execution” under provider outage.
   - Suggestion: Add a router-specific timeout/budget, e.g. env-configured max seconds and max providers, and test CLI timeout/failure fallback.

6. [Low] `compile_spec({"task_input": state.task}, None, None)` loses explicit success criteria
   - Section: "`spec = compile_spec({\"task_input\": state.task}, None, None)`" and "`state.completion_criteria = list(spec.success_criteria)`"
   - Issue: with only `task_input`, `CompiledSpec.success_criteria` is usually empty. `DogfoodState.completion_criteria` will be overwritten with `[]`, weakening later state/report semantics.
   - Suggestion: Preserve existing `state.completion_criteria` if `spec.success_criteria` is empty, or derive minimal criteria from the route/task.

### Missing from Design

- Concrete implementation of `_is_self_modification()` for worktree vs source-root paths.
- Router timeout and provider outage budget.
- Explicit Windows path normalization in `right_sized_router` before calling `blast_radius.classify_path`.
- Frozen-build validation that `scripts.blast_radius` is packaged/importable, not only `core.right_sized_router`.
- A concurrency story for module-level `_router_llm` injection in parallel tests/runs.

### Positive Observations

- The design correctly identifies that light and full paths must share `_ISO_ENV_KEYS`; current `dogfood.py` relies on those guards around `pipeline.run`.
- The plan to persist `route_decision` in `DogfoodState.to_dict/from_dict` directly addresses diagnosability for misroutes and fallback reasons.