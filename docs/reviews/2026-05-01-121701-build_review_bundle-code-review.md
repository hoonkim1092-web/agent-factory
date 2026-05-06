# Code Review: build_review_bundle

> Source: scripts/build_review_bundle.py
> Date: 2026-05-01 12:17
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Critic received an empty diff and issued no findings. Cross reviewer explored the live codebase independently and found 2 confirmed defects with reproduction evidence. Both are accepted under Rule 2 (single reviewer, strong evidence). No Critical findings → WARN.

---

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [High] Non-string `files` entries crash hook with unhandled AttributeError
- **Critic**: not flagged (empty diff)
- **Cross**: `_load_pending()` filters truthy values but not `isinstance(str)`. `_resolve_paths()` calls `.endswith(".py")` on any truthy value, raising `AttributeError`. Reproduced with `{"files": [1]}`. Violates the script's exit-0 contract.
- **Judgment**: Strong evidence — reproduction confirmed, specific line cited (`build_review_bundle.py:42`), test gap documented (`test_build_review_bundle.py:36` only covers `None`/empty). Accepted.
- **Action Required**: Change `_load_pending()` filter to `isinstance(f, str) and f`. Add regression test for mixed-type entries (`["core/foo.py", 1, {}, []]`) asserting exit code 0.

#### 2. [ACCEPT] [Medium] Race condition allows older bundle to overwrite newer queue snapshot
- **Critic**: not flagged (empty diff)
- **Cross**: `hook_runner.py:151` can launch concurrent bundle subprocesses. An older process reading `[A]` can finish after a newer process reading `[A,B]`, silently discarding the newer snapshot. `review_gate._state_lock()` exists for RMW safety but is not used around snapshot+save in `build_review_bundle.py:62`.
- **Judgment**: Evidence is solid — lock mechanism exists and is used in adjacent paths (`enqueue_agent_review.py:138`), but not here. Concrete lost-update scenario described. Accepted.
- **Action Required**: Either (a) capture `updated_at`/hash of `pending_agent_review.json` before build, re-read before `save()`, skip/abort if changed; or (b) wrap snapshot+save inside `_state_lock()` if build latency is acceptable.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Non-string entries crash hook (AttributeError) | High | ACCEPT | Cross |
| 2 | Race condition on bundle overwrite | Medium | ACCEPT | Cross |

---

### Recommendations

- Fix `_load_pending()` type guard first — it's a crash-on-bad-input bug with an exit-0 contract violation.
- Add the regression test for mixed-type `files` entries before merging.
- For the race condition, the lightweight fix (hash-check before save) is lower risk than holding `_state_lock()` across the full build; prefer that unless the build is very fast.
- Note: Tier 3 classification for `build_review_bundle.py` is already correct via `subprocess.run` content match — no path-pin change needed (rejected finding #3 confirmed correct behavior).