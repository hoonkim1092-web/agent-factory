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

This adds a new `core/*.py` behavior module and tests, so it is semantic and packaging-relevant.

### Findings

1. [Medium] New core module is missing from frozen hiddenimports
   - File: `af.spec:98`
   - Code: `'core.spec_compiler',`
     `'core.premortem',`
   - Issue: `core/planner.py` is a new untracked `core/*.py` module, but `af.spec` includes `core.spec_compiler` and `core.premortem` without `core.planner`. AF’s known review checklist explicitly calls this out as a frozen-build compatibility risk. If the planner is imported dynamically or wired later, `dist/af/af.exe` can miss it.
   - Suggestion: Add `'core.planner',` next to the Step 4/5 modules in `af.spec`, and run the frozen build/import smoke path.

2. [High] Planner is not wired into any runtime caller
   - File: `core/planner.py:194`
   - Code: `def build_plan(spec: CompiledSpec, premortem: PremortomResult) -> ExecutablePlan:`
   - Issue: Repository search found only `tests/test_planner.py` importing `core.planner`; no CLI, pipeline, interview, spec compiler, premortem, or project flow calls `build_plan()`. The module claims to add executable plan generation, but shipped behavior never produces or consumes the plan.
   - Suggestion: Wire `build_plan()` into the intended flow after `compile_spec()` and `run_premortem()`, persist or pass the `ExecutablePlan`, and cover that integration path with a test.

3. [Medium] Verification step loses the commands it tells the executor to run
   - File: `core/planner.py:178`
   - Code: `step = PlanStep(`
     `action="Run verification checks from premortem",`
     `tests_required=[],`
     `artifacts=["verification_report.md"],`
   - Issue: `_collect_verification_commands()` gathers concrete commands, and `ExecutablePlan.verification_requirements` stores them top-level, but the actual verification `PlanStep` contains none of them. A consumer walking `steps` cannot know what checks belong to the verification step.
   - Suggestion: Add a command field to `PlanStep`, populate `tests_required` with verification commands, or make the verification step action/artifacts explicitly reference the concrete commands.

4. [Medium] Research-gap resolution heuristic can produce false negatives
   - File: `core/planner.py:118`
   - Code: `risk_tokens = set(_WORD_RE.findall(risk.description.lower()))`
     `if not risk_tokens & scope_tokens:`
   - Issue: The token set includes boilerplate from `"Unanswered research question: ..."`. Any scope containing words like `research` or `question` can mark an unrelated gap as resolved. That can hide unresolved research risks before implementation.
   - Suggestion: Strip the known prefix before tokenizing and ignore generic stopwords, or compare only against normalized gap terms/evidence references.

### Comparison with Known Issues

- This repeats known AF pattern `M9`: new `core/*.py` files must be added to `af.spec` hiddenimports for frozen compatibility.
- No evidence of the critical known patterns: no non-atomic writes, shell invocation, thread joins, global mutable cache, or async shared-state mutation in this file.
- The no-runtime-caller issue is closest to the known dead-code category.

### Positive Observations

- The planner keeps investigation steps before implementation steps and makes implementation depend on investigation IDs.
- The module has focused unit coverage for serialization, step ordering, approval extraction, and verification command collection.