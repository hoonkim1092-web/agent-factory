# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-26 01:27
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This touches executable verification behavior and creates command strings that later flow into `shell=True`.

### Findings

1. [Critical] Fallback pytest command is built from unsanitized scope and reaches `shell=True`
   - File: `core/planner.py:223`
   - Code: `verify_cmds.append(f"python -m pytest {test} -v")`
   - Issue: `spec.scope` is user/interview-derived. `_test_file_for()` can turn a crafted scope like `core/foo.py;echo.py` into `tests/test_foo.py;echo.py`, and `core/dogfood.py:259-261` later runs verification strings with `subprocess.run(cmd, shell=True, ...)`.
   - Suggestion: Store verification commands as structured argv lists, or strictly validate generated test paths against a safe path regex plus workspace-relative allowlist before creating command strings.

2. [High] Test-only scope still produces no verification command
   - File: `core/planner.py:221`
   - Code: `test = _test_file_for(item)`
   - Issue: `_test_file_for()` only maps `core/*.py` and `scripts/*.py`. A valid test-only scope like `tests/test_utils.py` returns `None`, so the fallback leaves `verification_requirements=[]`. `core/dogfood.py:948-953` then fails any non-empty plan with “no verification commands defined.”
   - Suggestion: Treat `tests/test_*.py` or any safe `tests/*.py` scope as directly runnable: `python -m pytest <test_file> -v`.

3. [High] Windows-style scope paths bypass fallback verification and core artifact handling
   - File: `core/planner.py:77`
   - Code: `p = Path(target)`
   - Issue: `core/spec_compiler.py:132` accepts both `/` and `\` tokens, but planner mixes platform-specific `Path()` with forward-slash-only checks at `core/planner.py:164`. On non-Windows runners, `core\\foo.py` will not map to `tests/test_foo.py`; on all platforms, `Master_Blueprint.md` injection only matches `core/foo.py`.
   - Suggestion: Normalize scope paths once, replacing backslashes with `/`, rejecting absolute/parent traversal paths, then use the normalized form for test derivation and artifact rules.

### Comparison with Known Issues

- This repeats the known C4-adjacent shell execution risk: planner command strings eventually flow to dogfood’s `shell=True` runner.
- It also repeats the AF-specific Windows/Unix path handling concern noted in the checklist.
- `af.spec` hiddenimport is not a new issue here because `core.planner` is already present.

### Positive Observations

- The fallback is narrowly scoped to cases where premortem produced no runnable commands.
- The new planner test captures the intended comment-only premortem behavior, so the regression target is explicit.