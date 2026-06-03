# Design Review: 2026-06-03-af-right-sized-execution-decision

> Source: docs/2026-06-03-af-right-sized-execution-decision.md
> Date: 2026-06-03 23:19
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: WARN

### Findings

1. [High] “Native light” path is not implementable as described
   - Section: "`required_stages⊆{plan,implement,test}&고신뢰 → 네이티브 light, else → ProjectPipeline.run()`"
   - Issue: The current dogfood machine has no native `plan -> implement -> test` entrypoint. Active phases are only `PENDING -> ISOLATE -> DEVELOP -> VERIFY -> REVIEW -> FINALIZE -> MERGE` in [core/dogfood.py](D:/warkSpaces/agent-factory/core/dogfood.py:103). `_run_implement_phase()` exists, but it is legacy and needs a `plan_dict`; the design references `build_plan`, but no such dogfood helper exists.
   - Suggestion: Define the exact light-path API before implementation, e.g. `run_light_develop(state, plan_builder)` that returns the same normalized shape as `_run_develop_phase()` expects: `ok`, `steps`, `verification_requirements`, `changed_files`.

2. [High] Isolation enum conflicts with dogfood source-write invariant
   - Section: "`isolation: none | source | worktree | dogfood`"
   - Issue: Dogfood currently always creates an isolated worktree before DEVELOP, and `_cwd()` falls back to `source_workspace` if `worktree_workspace` is unset or not ready in [core/dogfood.py](D:/warkSpaces/agent-factory/core/dogfood.py:187). Introducing `none` or `source` for self-run tasks risks re-opening the source-write leak this document says was closed.
   - Suggestion: For Agent Factory self-modification, remove `none/source` from allowed outcomes or hard-floor them to `worktree` before any executable path is chosen. Persist the overridden decision in state.

3. [Medium] LLM router output has no validation contract
   - Section: "`ControlPlaneLLM.generate_json()` ... `RouteDecision{isolation, required_stages, review_depth, confidence, reason}`"
   - Issue: `ControlPlaneLLM.generate_json()` returns a raw `dict` and returns `{}` on provider failure in [core/control_plane_llm.py](D:/warkSpaces/agent-factory/core/control_plane_llm.py:161). The CLI path ignores `output_schema`, so invalid enum values, missing confidence, or `required_stages="full"` as a string can leak into routing unless the new module adds strict parsing.
   - Suggestion: Make `core/right_sized_router.py` own validation: normalize stages, reject unknown enum values, clamp confidence, require non-empty reason, and convert all invalid/empty results to full fallback.

4. [Medium] Blast-radius floor overstates what the current classifier detects
   - Section: "`scripts/blast_radius.py` tier 재사용: Tier3 파일(core/provider/permission/hook/auth/merge)는 코드양이 작아도 design+review+cross_review 강제 포함"
   - Issue: Current Tier 3 path rules are mostly scripts, hooks, build/deploy files, and prefixes in [scripts/blast_radius.py](D:/warkSpaces/agent-factory/scripts/blast_radius.py:47). General `core/providers/*`, permission, auth, or merge-sensitive code is not a Tier 3 path unless content regex happens to match.
   - Suggestion: Either update `scripts/blast_radius.py` Tier 3 paths/prefixes for the claimed sensitive areas, or change the design to say it will use `classify_with_content()` plus an explicit new sensitive-path list.

5. [Medium] Frozen build impact is missing
   - Section: "`Step 1 core/right_sized_router.py — classify(task, workspace, *, changed_files=None)`"
   - Issue: Adding `core/right_sized_router.py` requires `af.spec` hiddenimports coverage. `af.spec` manually lists core modules in [af.spec](D:/warkSpaces/agent-factory/af.spec:33), and new core files are not automatically collected.
   - Suggestion: Add `core.right_sized_router` to `af.spec`, and add a frozen-build smoke check or at least an import test for the module.

### Missing from Design

- Exact plan-builder source for native light mode.
- How route decisions are persisted in `dogfood_state.json` / `phase_trace.jsonl`.
- Validation schema for `RouteDecision`.
- Behavior when classification succeeds but changed files are unavailable before implementation.
- Frozen build handling for `core/right_sized_router.py` and any `scripts.blast_radius` import.
- Tests for Windows path normalization in `changed_files`.

### Positive Observations

- The design correctly treats LLM routing as advisory and specifies fail-closed fallback to full/worktree.
- It explicitly preserves the T3 source-write isolation invariant, which matches the current dogfood worktree model.