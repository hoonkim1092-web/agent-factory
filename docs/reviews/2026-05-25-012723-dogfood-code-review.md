# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-25 01:27
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change touches subprocess execution, git merge behavior, destructive file operations, policy gates, runtime persistence, and meaningful dogfood behavior.

### Findings

1. [High] `dogfood status` can no longer find default runs
   - File: `agent_launcher.py:1017`
   - Code: `rt_ws = _default_runtime_workspace(workspace)`
   - Issue: `core.dogfood._default_runtime_workspace()` was changed to accept `run_id`, not `workspace`, but the CLI status caller still passes the workspace path. Runs created without `--runtime-workspace` are saved under `~/.af-dogfood/<run_id>/runtime`, while status now looks under a path derived from the workspace string.
   - Suggestion: Change status to call `_default_runtime_workspace(args.run_id)`, or expose a stable helper like `runtime_workspace_for_run(run_id)` and update CLI tests.

2. [High] Manual merge mode creates an infinite `run_all()` loop
   - File: `core/dogfood.py:908`
   - Code: `if merge_mode == "manual":`
   - Issue: The manual branch sets `merge_status = "ready"` but leaves `state.phase` as `MERGE`. `run_all()` loops while `not state.is_terminal()`, so it repeatedly re-enters MERGE forever.
   - Suggestion: Either make manual mode a terminal/waiting phase, return from `run_all()` when manual merge is ready, or set `state.phase` to a defined terminal state and provide a separate resume/merge command.

3. [Critical] Merge policy can be bypassed when `merge_report.json` is missing or corrupt
   - File: `core/dogfood.py:599`
   - Code: `report = json.loads(report_path.read_text(encoding="utf-8"))`
   - Issue: If the merge report is missing or unreadable, `changed_files` stays `[]`, the exception is silently swallowed, and `_check_merge_policy()` cannot enforce denied paths such as `skills/registry.yaml` before merging the dogfood branch.
   - Suggestion: Treat missing/corrupt merge reports as policy rejection, or recompute changed files from git with `git diff --name-only state.base_ref state.dogfood_commit`.

4. [Critical] Conflict check mutates the source worktree before the real merge
   - File: `core/dogfood.py:614`
   - Code: `_git(["merge", "--no-commit", "--no-ff", state.dogfood_branch], cwd=src)`
   - Issue: The “dry-run” conflict check performs a real merge into the user’s source checkout, then resets. If the process exits between merge and reset, the source repo can be left in an in-progress merge or with index/worktree changes.
   - Suggestion: Use a scratch worktree for conflict checks, or use non-mutating git plumbing such as `git merge-tree` where available.

5. [Critical] Artifact writes are non-atomic
   - File: `core/dogfood.py:1100`
   - Code: `path.write_text(json.dumps(data, indent=2), encoding="utf-8")`
   - Issue: `_write_json()` is used for phase artifacts and `merge_report.json`. A crash during write can corrupt artifacts, and a corrupt merge report is especially dangerous because merge policy currently falls back silently.
   - Suggestion: Use a unique tempfile in the same directory, flush/fsync if needed, then `os.replace()`.

6. [Critical] Planner/verification commands still execute through `shell=True`
   - File: `core/dogfood.py:260`
   - Code: `cmd, shell=True, cwd=cwd,`
   - Issue: Dogfood executes command strings originating from plan/premortem data. Worktree isolation reduces source checkout pollution, but does not mitigate shell injection or destructive shell behavior.
   - Suggestion: Move plan commands to structured argv lists, run with `shell=False`, and add an approval/classification gate before execution.

### Comparison with Known Issues

- The change repeats known review patterns from `docs/code_review/code-review.md`: shell execution with `shell=True`, non-atomic JSON writes, silent fallback via swallowed exceptions, and destructive git/file operations.
- It partially addresses the previous dogfood isolation concern by moving execution cwd to a worktree, but the merge lifecycle reintroduces source-worktree mutation during the conflict check.
- `af.spec` already includes `core.dogfood`, so no new hiddenimport issue was found for this file.

### Positive Observations

- `run_id` validation blocks path separators and dots before constructing runtime paths.
- Git commands are passed as argv lists through `_git()`, avoiding shell interpolation for the new worktree and merge commands.