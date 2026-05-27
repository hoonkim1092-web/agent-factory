# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-28 00:52
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This touches dogfood isolation/finalize behavior and git cleanup/merge gating, so Tier 3 is required.

### Findings

1. [High] Dirty-source guard now ignores real whitespace changes
   - File: `core/dogfood.py:564`
   - Code: `r2 = _git(["diff", "-b", "--", filepath], cwd=cwd, check=False)`
   - Issue: The fallback runs whenever `--ignore-cr-at-eol` returns a non-empty diff, not only when the option is unsupported. `git diff -b` ignores real whitespace changes, including indentation-only Python changes. That makes `_is_crlf_only_diff()` return true for changes that are not CRLF-only.
   - Suggestion: Only fallback when the first git command fails because `--ignore-cr-at-eol` is unsupported. If the first command returns `0` with output, return `False`.

2. [High] Isolation can start from a dirty source workspace
   - File: `core/dogfood.py:600`
   - Code: `real_dirty = [f for f in dirty_files if not _is_crlf_only_diff(f, src)]`
   - Issue: Because `_is_crlf_only_diff()` now treats `git diff -b`-empty files as CRLF-only, `prepare_isolated_worktree()` can allow a source workspace with real whitespace/indentation edits. The dogfood worktree is created from `HEAD`, so those local edits are silently excluded from the run.
   - Suggestion: Keep the dirty-workspace predicate narrow: CRLF-only should mean no diff under `--ignore-cr-at-eol`, not “no diff under whitespace-ignore.”

3. [High] Finalize can omit real implementation changes from the dogfood commit
   - File: `core/dogfood.py:703`
   - Code: `crlf_only = {f for f in all_dirty if _is_crlf_only_diff(f, wt)}`
   - Issue: Finalize filters files through the widened predicate before staging. Real whitespace-only changes can be classified as CRLF-only, skipped by `stage_files`, and omitted from the commit/report. I ran the focused dogfood isolation tests and `test_finalize_crlf_only_files_excluded_from_scope_violations` now fails because `core/utils.py` is not staged.
   - Suggestion: Restore the narrow CRLF filter and add a regression test where `--ignore-cr-at-eol` emits a real diff while `-b` would be empty.

### Comparison with Known Issues

- `docs/code_review/code-review.md` flags silent fallback patterns and dogfood/worktree isolation as high-risk areas. This change repeats that pattern: a broad fallback hides real git diff output.
- The known review notes also emphasize AF frozen/build and Windows path concerns. The goal here is Windows compatibility, but the fallback changes semantics across all platforms instead of detecting the specific Windows Git incompatibility.

### Positive Observations

- The git calls still use list arguments with `shell=False` through `_git`, so this does not introduce shell injection.
- The change is localized to one helper, so the fix can be tightly scoped.

Validation run:

`pytest tests/test_dogfood_isolation.py::test_prepare_isolated_worktree_real_dirty_blocks tests/test_dogfood_isolation.py::test_finalize_crlf_only_files_excluded_from_scope_violations -q`

Result: 2 failed.