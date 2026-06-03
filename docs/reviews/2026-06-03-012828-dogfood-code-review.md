# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-06-03 01:28
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

At least 4 High findings. Must fix before merge.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] `result.get()` called without None-guard on `pipeline.run()` return
- **Critic**: "`pipeline.run()` is typed `Any`. If it returns `None`, `None.get("changed_files")` → `AttributeError`. No None-guard between line 1645 and line 1655."
- **Cross**: Not flagged as None-guard specifically, but corroborates that `ProjectPipeline.run()` returns no `changed_files` in production (`core/project_pipeline.py:1391-1409`), making the fallback path the live path — meaning line 1655 runs on every real invocation.
- **Judgment**: Strong. The diff shows `result = pipeline.run(...)` on line 1641 with no guard before `result.get(...)` on line 1655. `pipeline.run()` can return `None` on early exit. Cross confirms production always hits this line.
- **Action Required**: Change `result = pipeline.run(...)` to `result = pipeline.run(...) or {}` on the assignment line, eliminating the `AttributeError` risk.

---

#### 2. [ACCEPT] [High] Git fallback only captures committed changes; misses staged/untracked files
- **Critic**: Not explicitly flagged as a scope gap (flags the bare-`except` cascade instead).
- **Cross**: "Falls back to `git diff --name-only base_ref HEAD`, which only captures committed changes. `finalize_dogfood_result()` stages tracked dirty and untracked files… If the pipeline leaves normal worktree edits for FINALIZE to commit, `state.develop_changed_paths` stays empty, `build_merge_policy()` has no allowlist, and MERGE rejects the run."
- **Judgment**: Accepted on Cross evidence alone — strong. The diff shows the fallback at lines 1663–1669 using only `base_ref..HEAD`. FINALIZE's commit model (`core/dogfood.py:992-1039`) operates on staged dirty + untracked files not yet committed. These are invisible to `base_ref..HEAD`. This causes a legitimate run to be BLOCKED at merge due to an empty allowlist — a correctness failure, not just a logging gap.
- **Action Required**: Expand fallback to combine: `git diff --name-only base_ref HEAD` (committed) + `git diff --name-only HEAD` (staged) + `git diff --name-only` (unstaged) + `git ls-files --others --exclude-standard` (untracked). Normalize and deduplicate paths.

---

#### 3. [ACCEPT] [High] `_check_merge_policy`: empty `allowed_paths` + changed files now hard-denies (silent breaking change)
- **Critic**: "Prior semantics: `allowed_paths=[]` → loop skipped → all files pass. New semantics: empty `allowed_paths` + any `changed_files` → hard deny. Any caller that relied on `MergePolicy(allowed_paths=[])` as permissive is now silently broken. The old docstring explicitly documented permissive empty-list behavior."
- **Cross**: Not flagged.
- **Judgment**: Accepted on Critic evidence alone — strong. The diff shows the new guard at lines 1129–1130: `if not policy.allowed_paths and changed_files: return False, "no allowed_paths configured: deny-all when files changed"`. The removed docstring text (`"Constructing a bare MergePolicy elsewhere leaves allowed_paths empty, which disables the allowed-path gate"`) confirms this inverts a documented contract. Finding #2 above (empty paths from incomplete fallback) feeds directly into this guard, making the two interact to block legitimate runs.
- **Action Required**: Either (a) gate deny on an explicit `policy.deny_if_unconfigured` flag and log WARN for unconfigured state, or (b) audit every `MergePolicy(allowed_paths=[])` callsite before the new semantics ship. At minimum, the deny reason must distinguish "intentionally empty" from "fallback failed to populate."

---

#### 4. [ACCEPT] [High] `except Exception: pass` in git fallback silently cascades to merge denial
- **Critic**: "If `_git(["diff", ...])` fails (invalid `base_ref`, git binary missing, permission error, detached HEAD), `changed` stays `[]`, `build_merge_policy` produces `allowed_paths=[]`, and the new deny-all guard blocks the merge entirely. The run transitions to BLOCKED with no logged reason pointing back to the git failure."
- **Cross**: Partially corroborates — confirms that empty `develop_changed_paths` → empty allowlist → MERGE rejects with "no allowed_paths configured" (the exact deny-all path from Finding #3).
- **Judgment**: Accepted. Findings #3 and #4 compose into a silent failure chain: git exception → `changed=[]` → empty allowlist → deny-all fires with a policy-sounding message that obscures the real root cause. The bare `except: pass` at line 1663 is the entry point of this chain.
- **Action Required**: Replace `except Exception: pass` with `except Exception as exc: logger.warning("git diff fallback failed: %s", exc)`. When `changed` is still empty after the logged failure, set `state.last_failure` to include the git error before returning, so the deny-all message at merge is traceable.

---

#### 5. [ACCEPT] [Medium] `os.environ` mutation is process-global and not thread-safe
- **Critic**: "Between `os.environ[k] = v` writes and the `finally` restore, any concurrently executing `_run_develop_phase` in another thread reads the mutated env. `run_all` does not appear to serialize DEVELOP invocations across threads."
- **Cross**: Not flagged.
- **Judgment**: Accepted. The diff clearly shows the env-mutation block at lines 1636–1651. `try/finally` is correctly unconditional (Critic also notes this positive), but the window between set and restore is unguarded for concurrent callers. Medium rather than High because `run_all` does not appear to run DEVELOP concurrently today — but the code does not enforce that and is one parallel-invocation away from a race.
- **Action Required**: Use subprocess-level env override (`env={**os.environ, **overrides}`) passed to `pipeline.run()` if `ProjectPipeline` supports it, or add a module-level `threading.Lock` around the mutation block.

---

#### 6. [ACCEPT] [Medium] Silent worktree fallback defeats isolation without warning
- **Critic**: "`worktree = state.worktree_workspace or state.source_workspace` — if ISOLATE didn't set `worktree_workspace`, the pipeline runs against the live source workspace. `AF_DISABLE_REGISTRY_WRITE=1` is set, but file writes are unrestricted. `develop_changed_paths` will include source-tree mutations, which become the merge allowlist."
- **Cross**: Not flagged.
- **Judgment**: Accepted. The diff shows line 1635 with the silent fallback. The `pipeline is None` guard already exists on line 1633 as a precedent for asserting preconditions — the worktree condition is equally load-bearing.
- **Action Required**: Assert `state.worktree_workspace` is non-empty at function entry (matching the `pipeline is None` pattern), or at minimum log a `logger.warning("worktree_workspace unset: running pipeline in source workspace — isolation violated")` before the fallback fires.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `result.get()` without None-guard | High | ACCEPT | Both |
| 2 | Git fallback misses staged/untracked | High | ACCEPT | Cross |
| 3 | Empty `allowed_paths` now hard-denies (breaking) | High | ACCEPT | Critic |
| 4 | `except: pass` cascades silently to deny-all | High | ACCEPT | Both (corroborated) |
| 5 | `os.environ` mutation not thread-safe | Medium | ACCEPT | Critic |
| 6 | Silent worktree fallback defeats isolation | Medium | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 first** (`result = pipeline.run(...) or {}`): it's a one-liner and unblocks every production DEVELOP invocation from an imminent `AttributeError`.
- **Fix #2 + #4 together**: expand the git fallback scope AND log the exception — both touch the same 6-line fallback block and the fixes compose cleanly.
- **Fix #3 last in this set**: the deny-all guard design decision (flag vs. WARN) requires author intent confirmation before changing — but must be resolved before merge since #2 and #4 produce the exact empty-allowlist input that triggers it.
- **#5 and #6** can ship as a follow-up if the High findings are prioritized, but both should be tracked as explicit TODOs with test cases before this branch merges to main.
- The positive observation from Critic stands: the `try/finally` env restoration is correctly unconditional — preserve that structure when implementing #5's subprocess-env fix.