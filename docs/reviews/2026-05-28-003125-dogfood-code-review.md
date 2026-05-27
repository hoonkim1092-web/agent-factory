# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-28 00:31
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This changes dogfood worktree isolation behavior and dirty-worktree policy, which is meaningful behavior around git state and merge safety.

### Findings

1. [High] Staged source changes bypass the dirty-worktree gate
   - File: `core/dogfood.py:597`
   - Code: `real_dirty = [f for f in dirty_files if not _is_crlf_only_diff(f, src)]`
   - Issue: `_is_crlf_only_diff()` checks only `git diff --ignore-cr-at-eol -- <file>`, which excludes staged/index changes. A staged real edit appears in `git status --porcelain --untracked-files=no` as `M  path`, but `git diff -- path` can be empty, so this change treats it as CRLF-only and allows dogfood isolation to proceed while the source workspace is dirty.
   - Suggestion: Check both unstaged and staged diffs, e.g. `git diff --ignore-cr-at-eol -- path` and `git diff --cached --ignore-cr-at-eol -- path`, and only ignore the file when both are empty.

2. [High] Rename/copy status lines can be misclassified as CRLF-only noise
   - File: `core/dogfood.py:596`
   - Code: `dirty_files = [line[3:] for line in dirty.stdout.strip().splitlines() if line.strip()]`
   - Issue: Porcelain rename/copy entries use formats like `R  old.py -> new.py`. Passing the whole `old.py -> new.py` string as a path to `_is_crlf_only_diff()` does not inspect either real path, so real staged renames/copies can be filtered out as if they were harmless EOL noise.
   - Suggestion: Use `git status --porcelain=v1 -z` or `--porcelain=v2 -z` and parse rename records explicitly, or avoid path parsing entirely by comparing aggregate dirty output with aggregate `git diff --ignore-cr-at-eol` plus `--cached`.

3. [Medium] Isolation and merge dirty policies are now inconsistent
   - File: `core/dogfood.py:795`
   - Code: `dirty = _git(["status", "--porcelain", "--untracked-files=no"], cwd=state.source_workspace, check=False)`
   - Issue: `prepare_isolated_worktree()` now permits CRLF-only dirty files, but `_check_merge_policy()` still rejects any tracked dirty status. A run can pass isolation, execute the full dogfood pipeline, then fail auto-merge with `source_workspace is dirty` for the same CRLF-only noise the new isolation rule intentionally ignored.
   - Suggestion: Centralize the dirty-source policy in one helper, e.g. `_tracked_real_dirty_files(cwd)`, and use it in both isolation and merge policy checks.

### Comparison with Known Issues

The known review notes emphasize worktree/frozen-build safety and dirty state handling. This change directly touches the worktree isolation gate and repeats the project’s broader pattern of partial safety checks being applied in one phase but not the corresponding later phase.

It does not address the documented non-atomic JSON write pattern in `core/dogfood.py:_write_json`, and it adds no tests for staged changes, renames, or merge-policy parity.

### Positive Observations

- The change narrows CRLF handling through `git diff --ignore-cr-at-eol` instead of broadly ignoring whitespace.
- Git commands continue to use argument lists via `_git()`, avoiding shell string construction for worktree operations.