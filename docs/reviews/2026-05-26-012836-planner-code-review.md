# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-26 01:28
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change affects executable verification behavior and generated shell command strings.

### Findings

1. [Critical] Fallback pytest command can become shell injection in dogfood execution
   - File: `core/planner.py:223`
   - Code: `verify_cmds.append(f"python -m pytest {test} -v")`
   - Issue: `test` is derived from `spec.scope`, which can come from interview/project input. A scope item like `core/foo;whoami.py` yields `tests/test_foo;whoami.py`, then dogfood executes it through `subprocess.run(cmd, shell=True)` at `core/dogfood.py:260`. This repeats the known C4 shell-injection pattern.
   - Suggestion: Store verification commands as structured argv lists, or validate `spec.scope` against workspace-relative safe paths before command construction and execute with `shell=False`.

2. [High] Manual/comment-only risks are converted into passing automated verification
   - File: `core/planner.py:217`
   - Code: `if not verify_cmds:`
   - Issue: `_collect_verification_commands()` intentionally drops comment-only risk checks like `# Validate assumption`. The new fallback treats that as “no commands” and injects pytest instead. In dogfood, verify falls back to `plan_dict["verification_requirements"]`, so a manual assumption/research risk can pass just because pytest passes, without the risk being resolved.
   - Suggestion: Only apply fallback when `premortem.risks` is empty. If risks exist but only contain comment/manual checks, emit an explicit blocking manual verification requirement or keep verification empty so the existing guard fails.

3. [High] Scope extraction regression can erase directory-level work before planner sees it
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t) and not t.startswith("//")]`
   - Issue: The current diff also changes planner input generation. Directory/package scope answers such as `core/providers/` or wildcard answers like `core/providers/*.py` now produce no scope because `_PATH_TOKEN_RE` requires a concrete known-extension file. That feeds `build_plan()` with an empty `spec.scope`, so no implementation steps or fallback pytest commands are generated.
   - Suggestion: Accept safe workspace-relative directories/globs as scope items, or preserve the original answer as a scope target when it is a valid repo-relative directory.

### Comparison with Known Issues

- The fallback command repeats the known shell-command risk pattern from `code-review.md` C4, especially because `core/dogfood.py` still uses `shell=True`.
- The change does not introduce non-atomic writes or thread/coroutine cleanup issues in `core/planner.py`.
- Frozen build compatibility for `core.planner` appears already handled via `af.spec`.

### Positive Observations

- `tests/test_planner.py` was updated for the new fallback behavior, and `python -m pytest -q tests\test_planner.py` passes: 38 tests.
- The fallback only uses `_test_file_for()` and does not blindly generate pytest commands for every arbitrary non-Python target.