# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-28 01:09
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This touches `core/dogfood.py` behavior in the dogfood execution pipeline.

### Findings

1. [Medium] Pre-existing untracked files changed during IMPLEMENT are still invisible
   - File: `core/dogfood.py:1227`
   - Code: `_new_untracked = _post_untracked - _pre_untracked`
   - Issue: The fix only reports newly appearing untracked paths. If a retry or resumed run starts with an untracked file already present, and IMPLEMENT modifies that file, it will not appear in `actual_changed`. That makes the implement trace incomplete for dirty retry worktrees.
   - Suggestion: For untracked paths that exist both before and after, capture a lightweight fingerprint before execution, such as size + mtime or content hash, and include paths whose fingerprint changed.

2. [Low] Git command failures are treated as empty untracked sets
   - File: `core/dogfood.py:1183`
   - Code: `_git(["ls-files", "--others", "--exclude-standard"], cwd=cwd, check=False).stdout.splitlines()`
   - Issue: With `check=False`, a failed `git ls-files` call does not raise. The code will silently treat stdout as empty, so a transient git failure can produce a false “no untracked changes” result.
   - Suggestion: Store the result, check `returncode`, and add an implementation failure or diagnostic when git cannot enumerate untracked files.

3. [Low] Regression test is order-coupled to incidental git call count
   - File: `tests/test_dogfood.py:813`
   - Code: `if call_count["n"] <= 2:  # rev-parse is 1st, ls-files pre is 2nd`
   - Issue: The test depends on the total number and ordering of all `_git` calls. Adding an unrelated git call before post-change detection can make the mock return the wrong untracked set and fail for the wrong reason.
   - Suggestion: Track only `ls-files --others` invocations with a separate counter, or return based on an explicit phase marker.

### Comparison with Known Issues

- This change does not add non-atomic writes, shell injection, thread joins, global caches, or provider-specific assumptions.
- It is adjacent to the known “silent fallback” pattern: git enumeration failures can be hidden because `check=False` results are not inspected.
- Existing `core/dogfood.py` still contains broad best-effort `except Exception: pass` paths in final docs sync, but this diff does not introduce those.

### Positive Observations

- The production change uses `git ls-files --others --exclude-standard`, so ignored build/cache files are not pulled into `actual_changed`.
- A focused regression test was added for the main bug: newly created untracked files now appear in `actual_changed`.

Verification: `pytest -q tests/test_dogfood.py::test_run_implement_new_untracked_file_included_in_actual_changed` passed.