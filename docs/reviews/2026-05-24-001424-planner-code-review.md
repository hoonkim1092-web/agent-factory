# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:14
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

### Findings

1. [Medium] New `core/*.py` module is missing from frozen build hiddenimports
   - File: `af.spec:96`
   - Code: `'core.interview',`
   - Issue: `core/planner.py` is a new core module, but `af.spec` lists `core.research_brief`, `core.spec_compiler`, and `core.premortem` without `core.planner`. Frozen `dist/af/af.exe` builds can miss dynamically imported modules unless hiddenimports are kept current.
   - Suggestion: Add `'core.planner',` next to `'core.premortem',`.

2. [High] Planner is not wired into any production caller
   - File: `core/planner.py:194`
   - Code: `def build_plan(spec: CompiledSpec, premortem: PremortomResult) -> ExecutablePlan:`
   - Issue: `rg` found `build_plan()` imported only by `tests/test_planner.py`; no CLI, pipeline, interview, spec, or premortem path produces or consumes `ExecutablePlan`. This means the new Step 6 behavior is dead code in normal AF execution.
   - Suggestion: Wire `build_plan()` after `compile_spec()` and `run_premortem()` in the intended pipeline path, or explicitly mark this module experimental and exclude it from shipped behavior.

3. [Medium] Verification step drops the executable commands from the step payload
   - File: `core/planner.py:178`
   - Code: `step = PlanStep(`
   - Issue: `_build_verification_step(commands, ...)` uses `commands` only to decide whether a verification step exists. The `PlanStep` itself stores no commands, so a downstream executor reading `steps` cannot know what to run without also special-casing top-level `verification_requirements`.
   - Suggestion: Add a structured field such as `verification_commands: list[str]` to `PlanStep`, or store these commands in a clearly named step artifact/payload used by executors.

### Comparison with Known Issues

- This repeats the known AF hiddenimports risk for new `core/*.py` files noted in `code-review.md` as M9.
- The no-production-caller issue matches the project’s known dead-code pattern.
- The previous planner review’s whitespace tokenization failure appears fixed: `_unresolved_risks()` now uses `_WORD_RE`.

### Positive Observations

- `pytest -q tests\test_planner.py` passes: 33 tests passed.
- The plan ordering is explicit: investigation steps precede implementation, and implementation steps depend on investigation IDs.