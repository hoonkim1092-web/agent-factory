# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-28 01:10
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This touches dogfood IMPLEMENT telemetry around git state and worktree behavior, which is meaningful execution behavior.

### Findings

1. [High] Retry worktrees miss edits to pre-existing untracked files
   - File: `core/dogfood.py:1227`
   - Code: `_new_untracked = _post_untracked - _pre_untracked`
   - Issue: `retry_run()` reuses the same worktree, so an untracked file created by a failed prior IMPLEMENT can already exist before the next IMPLEMENT. If the retry edits that file, it remains in both sets and is omitted from `actual_changed`. I reproduced this in a temp git repo: pre-existing `retry_file.py` was edited during IMPLEMENT and `actual_changed` returned `[]`.
   - Suggestion: Track untracked file content/mtime snapshots, or include all post-run untracked files with a separate `preexisting_untracked` field so retry edits are not silently hidden.

2. [High] IMPLEMENT failures can still advance to VERIFY/FINALIZE
   - File: `core/dogfood.py:1471`
   - Code: `if not impl_result.get("ok") and not impl_result.get("executed"):`
   - Issue: The caller only blocks failed IMPLEMENT when nothing executed. A command can fail after creating a new untracked file; with this change, `actual_changed` may correctly report it, but `run_all()` still proceeds to VERIFY/REVIEW/FINALIZE. That repeats the known “IMPLEMENT failure ignored” pattern in dogfood reviews.
   - Suggestion: Treat `not impl_result.get("ok")` as a retry/block signal, or pass failures into REVIEW before any finalize/merge path can run.

3. [Critical] Dogfood artifacts still use non-atomic JSON writes
   - File: `core/dogfood.py:1604`
   - Code: `path.write_text(json.dumps(data, indent=2), encoding="utf-8")`
   - Issue: `plan.json`, `merge_report.json`, and other dogfood artifacts can be truncated on crash or interruption. This is explicitly called out in the known review checklist as a critical pattern. It is especially risky for `merge_report.json`, because `merge_dogfood_branch()` silently ignores parse failures and may continue with empty policy inputs.
   - Suggestion: Write to a temp file in the same directory, flush/fsync, then `os.replace()`.

### Comparison with Known Issues

- The change addresses the prior accepted issue that `_run_implement_phase().actual_changed` missed newly created untracked files.
- It still repeats nearby known patterns: silent fallback around git/report failures, non-atomic JSON artifact writes, and dogfood merge/implementation paths where telemetry exists but is not enforced.

### Positive Observations

- The new git calls use argument lists, not shell strings, so this does not introduce shell injection.
- Capturing pre/post untracked sets fixes the simple first-attempt “new untracked file” telemetry gap and has a focused regression test.