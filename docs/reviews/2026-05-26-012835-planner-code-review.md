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

This change affects executable verification behavior and creates command strings that later flow into a shell runner.

### Findings

1. [Critical] Fallback pytest command is built from scope-derived text and reaches `shell=True`
   - File: `core/planner.py:223`
   - Code: `verify_cmds.append(f"python -m pytest {test} -v")`
   - Issue: `spec.scope` is interview/user-derived. `_test_file_for()` derives `test` from that value without validating it as a safe repo-relative path. A crafted scope such as `core/foo.py&whoami.py` can produce a command containing shell metacharacters, and `core/dogfood.py:259-261` later executes plan commands with `subprocess.run(cmd, shell=True, ...)`.
   - Suggestion: Store commands as structured argv lists, or at minimum validate `scope` against a strict repo-relative path allowlist and execute with `shell=False`.

2. [High] Test-only scope still produces no verification command
   - File: `core/planner.py:78`
   - Code: `if p.suffix == ".py" and p.parent.name in ("core", "scripts"):`
   - Issue: The fallback only maps `core/*.py` and `scripts/*.py` to tests. A valid scope like `tests/test_utils.py` creates an implementation step but no verification command, so `core/dogfood.py:948-953` blocks the run with “no verification commands defined.”
   - Suggestion: Treat safe `tests/test_*.py` scope items as directly runnable, e.g. `python -m pytest tests/test_utils.py -v`.

3. [High] Windows-style `core\*.py` scope misses Blueprint artifact tracking
   - File: `core/planner.py:164`
   - Code: `if re.match(r"core/[^/]+\.py$", item):`
   - Issue: AF runs heavily on Windows, and upstream scope extraction accepts backslashes. `core\utils.py` can still get a pytest fallback via `Path`, but it will not add `Master_Blueprint.md` to artifacts because this regex only accepts `/`. That can bypass the project’s core-module Blueprint sync rule.
   - Suggestion: Normalize scope paths to POSIX form before planning, or match both separators with `core[/\\][^/\\]+\.py$`.

### Comparison with Known Issues

- The diff repeats the known C4-adjacent shell execution risk: planner emits command strings that dogfood executes via `shell=True`.
- `af.spec` already includes `core.planner`, so the frozen hiddenimport pattern is not repeated here.
- The Windows path issue matches the AF-specific path-handling checklist.

### Positive Observations

- The fallback is narrowly scoped to cases where premortem produced no executable commands.
- Focused tests pass: `python -m pytest tests\test_planner.py -q` → `38 passed`.