# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-25 01:42
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change touches subprocess execution, git merge behavior, destructive cleanup, policy gates, runtime persistence, and meaningful dogfood behavior.

### Findings

1. [Critical] Plan commands still execute through `shell=True`
   - File: `core/dogfood.py:260`
   - Code: `subprocess.run(cmd, shell=True, cwd=cwd,`
   - Issue: Dogfood executes command strings from plan artifacts through the shell. Worktree isolation reduces source pollution, but it does not prevent shell injection or destructive shell behavior from model-produced plan commands.
   - Suggestion: Change plan commands to structured argv arrays and run with `shell=False`. Add an approval/classification gate for shell-only or destructive commands.

2. [High] Missing or corrupt merge report bypasses denied-path policy
   - File: `core/dogfood.py:597`
   - Code: `if report_path.exists():`
   - Issue: If `merge_report.json` is missing, `changed_files` remains `[]`, so `_check_merge_policy()` cannot enforce denied paths before merging.
   - Suggestion: Treat missing report as policy rejection, or recompute changed files from git using `git diff --name-only state.base_ref state.dogfood_commit`.

3. [High] Corrupt merge report is silently ignored
   - File: `core/dogfood.py:601`
   - Code: `except Exception:`
   - Issue: JSON parse/read failures are swallowed with `pass`, causing the same denied-path bypass and hiding runtime corruption.
   - Suggestion: Record `last_failure`, block the merge, or recompute changed files with explicit error context.

4. [High] Conflict precheck mutates the source worktree
   - File: `core/dogfood.py:614`
   - Code: `_git(["merge", "--no-commit", "--no-ff", state.dogfood_branch], cwd=src)`
   - Issue: The “dry run” merge modifies the source index/worktree before `reset --merge`. If the process crashes between lines 614 and 623, the maintainer’s source checkout can be left in an in-progress merge.
   - Suggestion: Use an isolated temporary worktree for conflict checks, or rely on a single actual merge with robust recovery for `MERGE_HEAD`/unmerged index state.

5. [Medium] Phase artifacts are written non-atomically
   - File: `core/dogfood.py:1102`
   - Code: `path.write_text(json.dumps(data, indent=2), encoding="utf-8")`
   - Issue: `interview.json`, `plan.json`, and `merge_report.json` can be truncated or partially written on crash. This repeats the project’s known non-atomic JSON write pattern.
   - Suggestion: Use a unique temp file in the target directory plus `os.replace()`/`Path.replace()`, preferably through a shared file I/O helper.

### Comparison with Known Issues

- This change partially addresses the known dogfood workspace pollution issue by adding git worktree isolation.
- It repeats known C4 shell execution risk via `shell=True`.
- It repeats known C2/M10 non-atomic JSON artifact write risk.
- It repeats the known silent fallback pattern with `except Exception: pass`.
- `af.spec` already includes `core.dogfood`, so no hiddenimport issue found here.

### Positive Observations

- `run_id` validation prevents path traversal in persisted dogfood state paths.
- The source dirty check before worktree creation is a useful guard against accidental source checkout mutation before implementation starts.