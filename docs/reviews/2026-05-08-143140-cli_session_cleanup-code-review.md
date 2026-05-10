# Code Review: cli_session_cleanup

> Source: core/cli_session_cleanup.py
> Date: 2026-05-08 14:31
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The Critic received no diff and could not contribute findings. All findings below originate solely from the Cross Review. Three ACCEPT issues exist — none are Critical, but Finding #1 is a functional gap (the module's stated purpose is unreachable) and Finding #2 undermines the fail-open contract. Both warrant fixing before production use.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] `cleanup_stale_sessions()` is a dead path — never called
- **Critic**: Not flagged (no diff available)
- **Cross**: Module docstring claims the function is called once on `generate_work_items()` entry, but `core/work_item_generator.py:740–831` contains no such call. No call sites found anywhere.
- **Judgment**: The module's entire stated purpose is unreachable. This is a functional correctness issue, not a style nit — the cleanup feature simply does not run.
- **Action Required**: Add `cleanup_stale_sessions(workspace, days=30)` wrapped in `try/except` at the start of `generate_work_items()`, with debug-level logging of the deleted count.

---

#### 2. [ACCEPT] [Medium] Fail-open contract not honored at the directory-iteration level
- **Critic**: Not flagged (no diff available)
- **Cross**: `cli_session_cleanup.py:46–48` increments `deleted` after `rmtree(ignore_errors=True)` without confirming the directory is gone. Separately, exceptions from `iterdir()` (root traversal) propagate uncaught, breaking the "never affects main flow" guarantee.
- **Judgment**: Two distinct holes: a silent false-count and an uncaught propagation path. Either can violate the stated contract.
- **Action Required**: (a) Wrap the entire function body in `try/except Exception: return 0`. (b) Replace `rmtree(ignore_errors=True)` + unconditional `deleted += 1` with a post-delete `exists()` check, or use `ignore_errors=False` and catch per-entry.

---

#### 3. [ACCEPT] [Medium] No test coverage for any cleanup path
- **Critic**: Not flagged (no diff available)
- **Cross**: `cleanup_stale_sessions` has zero callers and zero tests. Existing test files (`test_resume_brief.py`, `test_cli_session_adapter.py`) do not touch the cleanup path.
- **Judgment**: Combined with Finding #1, the function is both uncalled and untested — no regression protection exists.
- **Action Required**: Add minimum 3 tests: TTL-based deletion, IO/permission exception → fail-open (returns 0), and integration test verifying `generate_work_items()` triggers cleanup once.

---

#### 4. [HOLD] [Low] 30-day TTL may conflict with continuity snapshot reads
- **Critic**: Not flagged
- **Cross**: `core/continuity/resume_brief.py:58` and `core/control/continuity_snapshot.py:210` both read from `cli_sessions` JSON files. Cleanup could delete the most-recent state file a continuity read depends on.
- **Judgment**: Requires a policy decision the reviewers cannot make unilaterally — either "keep the newest 1 state file per provider regardless of TTL" or "accept that sessions older than 30 days lose continuity." Cannot resolve from code alone.
- **Question for Author**: What is the intended behavior when cleanup removes the only state file for an active provider? Should the newest file per provider be exempt from TTL?

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `cleanup_stale_sessions()` never called (dead path) | High | ACCEPT | Cross |
| 2 | Fail-open contract broken at iterdir + false delete count | Medium | ACCEPT | Cross |
| 3 | No test coverage for cleanup paths | Medium | ACCEPT | Cross |
| 4 | 30-day TTL vs continuity snapshot reads | Low | HOLD | Cross |

---

### Recommendations

- **Fix #1 first**: Wire the call into `generate_work_items()` — without this, findings #2 and #3 are moot in production.
- **Fix #2 alongside #1**: Wrap the entire function in a top-level `try/except` and fix the false-count before the function is reachable.
- **Fix #3 before merge**: At minimum the fail-open test; the integration test for `generate_work_items()` call can follow in the same PR.
- **Resolve #4 with a one-line policy comment** in the module or `NEXT_STEPS.md` before the feature is considered production-ready. Codex path collision (the rejected Finding #4 from Cross) is confirmed safe — no action needed there.