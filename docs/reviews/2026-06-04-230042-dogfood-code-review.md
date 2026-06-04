# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-06-04 23:00
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

Reviewed latest `core/dogfood.py` change: commit `f208b632`. The working tree contains no uncommitted `dogfood.py` diff.

### T3 Advisory

`t3_required: yes`

- Changes affect shell execution, routing gates, isolation, and automatic merges.

### Findings

1. [Critical] Changed filenames are interpolated into shell commands
   - File: `core/dogfood.py:1685`
   - Code: `return ["python -m pytest " + " ".join(test_files) + " -q --tb=short"]`
   - Issue: Git-derived filenames are concatenated without quoting and later executed through PowerShell or `shell=True` at line 1822. A filename such as `tests/test_ok.py; Write-Output PWNED` injects an additional command. Filenames containing spaces also break verification.
   - Suggestion: Represent commands as structured argv lists and execute with `shell=False`. Never concatenate filenames into shell strings.

2. [Critical] Light routing permits writes outside the isolated worktree
   - File: `core/dogfood.py:1780`
   - Code: `scope = _intended_scope(state.task)`
   - Issue: `_intended_scope()` accepts absolute and traversal paths. For example, `edit /tmp/outside.py` produces `["/tmp/outside.py"]`. The light path passes this scope into the planner and AI executor, where absolute artifacts can be modified outside the worktree. Git merge policy cannot detect or roll back those writes.
   - Suggestion: Resolve every scope path against the worktree, reject absolute paths and `..`, and verify the resolved path remains inside the worktree before routing or execution.

3. [High] Safety floors use incomplete intended scope instead of actual changes
   - File: `core/dogfood.py:1781`
   - Code: `route = classify(state.task, state._cwd(), changed_files=scope)`
   - Issue: `scope` only contains explicit path tokens extracted from task text. A task mentioning `scripts/utils.py` can be routed light even if implementation later modifies Tier-3 hooks, gates, or deployment files. No post-implementation classification reruns safety floors against `actual_changed`.
   - Suggestion: Reclassify `develop_changed_paths` after implementation. Block or rerun the full pipeline when actual changes require stronger stages.

4. [High] Git inspection failures can silently produce a passing VERIFY
   - File: `core/dogfood.py:1660`
   - Code: `except Exception: pass`
   - Issue: Both changed-file fallback probes silently swallow failures. This can produce `changed=[]`; normalization then creates no synthetic steps or verification commands. `_run_verify_phase()` consequently returns `passed=True` without running anything.
   - Suggestion: Fail closed when Git inspection fails. Record the exception and require at least one verification command before allowing DEVELOP to succeed.

5. [High] Process-wide isolation environment is concurrency-unsafe
   - File: `core/dogfood.py:1635`
   - Code: `prior: dict[str, str | None] = {k: os.environ.get(k) for k in _ISO_ENV_KEYS}`
   - Issue: Concurrent dogfood runs mutate and restore the same global environment variables. One run can execute with another run’s `AGENT_PROJECT_ROOT` or prematurely lose `AF_DISABLE_REGISTRY_WRITE`.
   - Suggestion: Pass an explicit environment/configuration object to callees, or serialize this context with a process-wide lock.

### Comparison with Known Issues

- Repeats known C4 shell-injection behavior through generated command strings and `shell=True`.
- Repeats known H3 silent-fallback behavior using broad `except Exception: pass`.
- The external-write risk matches prior dogfood design-review concerns: worktrees isolate Git changes, not arbitrary filesystem writes.

### Positive Observations

- `route_decision` is persisted for later auditing.
- `core.right_sized_router` was added to `af.spec`, avoiding the known hidden-import failure.
- Isolation environment restoration uses `finally`.
- Relevant tests pass: `168 passed`.