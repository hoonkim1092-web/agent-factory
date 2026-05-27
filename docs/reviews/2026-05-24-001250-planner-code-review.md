# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:12
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

1. [High] Current planner tests fail on unresolved risk detection
   - File: `core/planner.py:113`
   - Code: `words = set(risk.description.lower().split())`
   - Issue: `_unresolved_risks()` tokenizes by whitespace only, so `core/retry_policy.py` is one token and does not match `retry`. The included test `test_unresolved_risks_gap_resolved_by_scope` currently fails.
   - Suggestion: Reuse the project tokenizer from `core.research_brief._tokenize()` or split paths/underscores/punctuation before comparing tokens.

2. [Medium] New core module is missing from frozen build hiddenimports
   - File: `af.spec:96`
   - Code: `'core.interview',`
   - Issue: `af.spec` includes nearby `core.research_brief`, `core.spec_compiler`, and `core.premortem`, but not new `core.planner`. This repeats the known AF pattern M9: new `core/*.py` modules can be omitted from PyInstaller hiddenimports.
   - Suggestion: Add `'core.planner',` beside `core.premortem`.

3. [High] Planner is not wired into any production caller
   - File: `core/planner.py:189`
   - Code: `def build_plan(spec: CompiledSpec, premortem: PremortomResult) -> ExecutablePlan:`
   - Issue: `rg` found only `tests/test_planner.py` importing `core.planner`; no CLI, pipeline, interview, spec, or premortem path calls `build_plan()`. The change adds plan generation but no executable path produces or consumes it.
   - Suggestion: Wire `build_plan()` into the intended Step 4/5 flow after `compile_spec()` and `run_premortem()`, or mark it explicitly experimental and exclude it from shipped behavior.

4. [Medium] Verification step drops the actual commands
   - File: `core/planner.py:165`
   - Code: `def _build_verification_step(commands: list[str],`
   - Issue: `commands` is only used to decide whether a verification step exists; the resulting `PlanStep` contains no command list, only `artifacts=["verification_report.md"]`. A step executor cannot know what to run from the step itself.
   - Suggestion: Add a `commands`/`verification_commands` field to `PlanStep`, or store the commands in `tests_required`/a structured verification payload.

### Comparison with Known Issues

- This change repeats the known `af.spec` hiddenimports risk for new `core/*.py` files.
- No shell execution, non-atomic writes, thread joins, global cache growth, or async cleanup issues were introduced in `core/planner.py`.
- The “no production caller” concern is similar to the known dead-code review pattern.

### Positive Observations

- The planner keeps data models simple and serializable via `to_dict()`.
- Investigation steps are ordered before implementation steps, and implementation steps correctly depend on investigation IDs.

Verification run: `python -m py_compile core\planner.py tests\test_planner.py` passed; `pytest -q tests\test_planner.py` failed with 1 failing test.