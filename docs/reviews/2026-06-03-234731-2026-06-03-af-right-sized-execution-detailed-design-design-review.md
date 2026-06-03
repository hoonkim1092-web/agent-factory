# Design Review: 2026-06-03-af-right-sized-execution-detailed-design

> Source: docs/2026-06-03-af-right-sized-execution-detailed-design.md
> Date: 2026-06-03 23:47
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Empty scope can route to light and complete as a no-op
   - Section: `B | classify 시점에 실제 diff 없음 → 의도 scope를 _scope_from_intent(task)로 추출해 changed_files로 전달` and `R-FB-NOSCOPE | scope=[] ... floor Tier3 검사 skip`
   - Issue: The design says “scope 0건 = fallback full” in the decision table, but the proposed router code does not enforce that. `_apply_safety_floors()` only checks `if changed_files and _max_tier(changed_files) >= 3`. Current `core/spec_compiler.py:101` `_scope_from_intent()` returns `[]` for natural tasks without explicit file paths; this is also asserted in `tests/test_spec_compiler.py:248`. In the proposed light path, `compile_spec({"task_input": state.task}, None, None)` would produce empty `scope`, `build_plan()` can produce no implementation/verification steps, `_run_implement_phase()` returns `ok=True`, and VERIFY does not block when `steps=[]`.
   - Suggestion: Make `changed_files is None or []` fail closed to full/fallback unless an explicit trusted scope source exists. Add an acceptance test for a no-path task that must call `_run_develop_full`.

2. [Critical] Tier3 floor uses the wrong blast-radius API
   - Section: `def _max_tier(changed_files: list[str]) -> int: ... classify_path (path-only) 사용`
   - Issue: `scripts/blast_radius.py:120` `classify_path()` is path-only and returns Tier2 for sensitive core files whose Tier3 status comes from content scanning. Verified current behavior: `core/providers/cli.py` is `classify_path=2` but `classify_with_content=3`; same for `core/dogfood.py`. This directly contradicts the design’s test case `R-FLOOR-TIER3 | scope=core/providers/cli.py(Tier3)`.
   - Suggestion: Use `classify_with_content(rel_path, workspace)` for existing files. For missing/new files, define a conservative fallback rule instead of silently treating them as Tier2.

3. [High] Light path drops the existing DEVELOP isolation environment guards
   - Section: `_run_develop_light ... AI codegen → _run_implement_phase 재사용`
   - Issue: Current `core/dogfood.py:1626` `_run_develop_phase()` wraps the full pipeline with `_ISO_ENV_KEYS`: `AF_DISABLE_REGISTRY_WRITE`, `AF_SELF_RUN`, `AGENT_PROJECT_ROOT`, `AF_SKIP_DOMAIN_REVIEW` at `core/dogfood.py:1618-1644`. The proposed `_run_develop_light()` calls `_run_implement_phase()` directly and does not apply those guards. That reopens source/global write paths such as `core/registry_manager.py` registry writes and skill lookup behavior controlled by `AF_SELF_RUN`.
   - Suggestion: Extract the env guard into a shared context manager and wrap both `_run_develop_full()` and `_run_develop_light()` with it. Add tests that env vars are set during light execution and restored afterward.

4. [High] Schema validation is not fail-closed for unknown stages
   - Section: `_validate_raw`: `required_stages = STAGE_VOCAB 교집합 (미지 stage 무시), 빈 리스트면 fallback`
   - Issue: Ignoring unknown stages can under-route. If the LLM returns `["plan", "implement", "test", "deploy"]`, the invalid `deploy` is discarded and the remaining subset passes `is_light()`. For a router whose purpose is safety gating, malformed stage output should not be normalized into a lighter route.
   - Suggestion: Treat any unknown stage as schema failure and return fallback/full. Keep normalization only for ordering valid stages.

5. [Medium] Light path loses existing research/spec context
   - Section: `_run_develop_light`: `spec = compile_spec({"task_input": state.task}, None, None)`
   - Issue: Existing dogfood phases have `_run_research_phase()` and `_run_spec_phase()` paths that collect scope files and compile constraints/success criteria (`core/dogfood.py:1329-1410`). The proposed light path bypasses interview artifacts, research evidence, constraints, and clarification scope. This makes premortem/planner decisions weaker exactly when the router is trying to safely reduce work.
   - Suggestion: Reuse any existing state artifacts when present (`interview_path`, `research_path`, `spec_path`) before falling back to bare `task_input`. If none exist, require explicit scope or full route.

### Missing from Design

- A fail-closed rule for `changed_files=[]` / unknown scope.
- A content-based Tier3 classification plan using `classify_with_content()`.
- Shared isolation/env-guard handling for light and full DEVELOP paths.
- Tests proving light cannot complete with no changed files and no verification.
- Frozen build import impact beyond adding `core.right_sized_router`; `scripts.blast_radius` dependency should also be checked for PyInstaller behavior.

### Positive Observations

- The design correctly keeps `ControlPlaneLLM.generate_json()` as read-only via `allow_file_edit=False`, matching `core/control_plane_llm.py:122-124`.
- Persisting `route_decision` on `DogfoodState` is useful for auditability and restart diagnostics.