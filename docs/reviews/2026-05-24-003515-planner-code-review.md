# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:35
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This change adds executable planning behavior and propagates verification command strings, so it is meaningful behavior and touches a future command execution boundary.

### Findings

1. [High] Executable command strings are propagated from untrusted scope data
   - File: `core/planner.py:190`
   - Code: `commands=list(commands),`
   - Issue: `PlanStep.commands` now preserves premortem command strings in an executable plan. The callee builds at least one command from `CompiledSpec.scope` (`core/premortem.py:88`: `command=f"python -m py_compile {targets}"`), and scope comes from interview artifacts (`core/spec_compiler.py:118`: `scope = _str_list(src.get("scope"))`). If Step 7 later runs these strings via shell, scope like `core/foo.py; bad_command` becomes command injection.
   - Suggestion: Store structured argv lists instead of shell strings, validate scope entries as repo-relative paths, and require future executors to use `subprocess.run(argv, shell=False)`.

2. [Medium] Planner is not wired into any production flow
   - File: `core/planner.py:200`
   - Code: `def build_plan(spec: CompiledSpec, premortem: PremortomResult) -> ExecutablePlan:`
   - Issue: Direct reference search finds `build_plan()` used by `tests/test_planner.py` and docs/review artifacts only. No CLI, pipeline, interview, spec compiler, or premortem path calls it, so the new “executable plan” behavior is dead in normal AF execution.
   - Suggestion: Wire `build_plan()` after `compile_spec()` and `run_premortem()` in the intended planning path, persist/pass the `ExecutablePlan`, and add an integration test.

3. [Medium] Research gaps can be incorrectly marked resolved by incidental token overlap
   - File: `core/planner.py:124`
   - Code: `if not risk_tokens & scope_tokens:`
   - Issue: Any single shared token suppresses an unresolved risk. Common tokens from file paths or questions, such as `core`, `test`, `policy`, or `module`, can make an unrelated research gap appear resolved just because that word appears in a scope path.
   - Suggestion: Use a stopword list plus a minimum significant-token overlap, or track which research gap was explicitly addressed instead of inferring resolution from scope strings.

### Comparison with Known Issues

- The known AF frozen-build issue (`af.spec` missing hiddenimports) is addressed: `af.spec:101` includes `'core.planner'`.
- The change introduces a C4-adjacent pattern: command strings are not executed here, but they are now serialized into the plan as executable payloads.
- I did not see non-atomic writes, thread joins, shared async state, global cache growth, or bare `except: pass` in `core/planner.py`.

### Positive Observations

- `PlanStep` and `ExecutablePlan` use dataclass `default_factory`, avoiding shared mutable defaults.
- Focused verification passes: `pytest -q tests/test_planner.py` reports `36 passed`.