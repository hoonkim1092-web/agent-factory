# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:14
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This is meaningful behavior: it adds/changes executable planning logic and packaging surface.

### Findings

1. [High] Verification step drops the commands it is supposed to execute
   - File: `core/planner.py:178`
   - Code: `step = PlanStep(... tests_required=[], artifacts=["verification_report.md"], depends_on=list(impl_ids))`
   - Issue: `_build_verification_step()` receives `commands`, but only uses them to decide whether to create a step. The `PlanStep` itself contains no command list, so a consumer executing the plan cannot know what verification checks belong to that step.
   - Suggestion: Add a structured field such as `verification_commands: list[str]` to `PlanStep`, or put these commands in a dedicated verification payload referenced by the step.

2. [High] Research-gap unresolved detection can be falsely cleared by the fixed prefix
   - File: `core/planner.py:118`
   - Code: `risk_tokens = set(_WORD_RE.findall(risk.description.lower()))`
   - Issue: The token set includes `"unanswered"`, `"research"`, and `"question"` from the boilerplate prefix. A scope like `core/research_brief.py` can overlap on `"research"` and incorrectly mark an unrelated gap as resolved.
   - Suggestion: Strip `"Unanswered research question: "` before tokenizing, or store the raw question separately in `PremortomRisk`.

3. [Medium] New planner module is missing from frozen-build hiddenimports
   - File: `af.spec:97`
   - Code: `'core.research_brief', 'core.spec_compiler', 'core.premortem',`
   - Issue: `core.planner` sits beside these Step 4/5 modules but is not listed. This repeats the known AF pattern M9: new `core/*.py` modules can be omitted from PyInstaller hiddenimports and then fail only in `dist/af/af.exe`.
   - Suggestion: Add `'core.planner',` near `core.premortem` and run the frozen build/import smoke path.

4. [Medium] Planner API is currently orphaned from the execution path
   - File: `core/planner.py:194`
   - Code: `def build_plan(spec: CompiledSpec, premortem: PremortomResult) -> ExecutablePlan:`
   - Issue: `rg` found only tests importing `core.planner`; `core/project_pipeline.py:883-888` still calls `ProjectPlanningDirector.plan()` and `enrich_role_plan()` directly. No production caller compiles spec, runs premortem, then builds this executable plan.
   - Suggestion: Wire `build_plan()` into the intended `compile_spec()` / `run_premortem()` flow, or mark the module experimental until consumed.

### Comparison with Known Issues

- This repeats the known `af.spec` hiddenimports risk from code-review.md M9.
- No non-atomic writes, shell execution, thread joins, global caches, or async cleanup paths are introduced in `core/planner.py`.
- The related premortem module still emits command strings; this planner change preserves those strings at top level but does not attach them to the executable verification step.

### Positive Observations

- `PlanStep` and `ExecutablePlan` are simple dataclasses with serializable `to_dict()` methods.
- Focused verification passed: `python -m py_compile core\planner.py tests\test_planner.py` and `pytest -q tests\test_planner.py` both passed, with 33 planner tests passing.