# Code Review: enqueue_agent_review

> Source: scripts/enqueue_agent_review.py
> Date: 2026-04-30 08:31
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Critic review unavailable (stream idle timeout — partial response only). Verdict relies on Cross review + diff inspection. The change fixes the prior race window by adopting `review_gate._state_lock`, but introduces a new latency risk (full content classification inside the locked section vs. 3s hook caller timeout) and lacks regression coverage for the metadata-preservation guarantee that motivated the change.

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [Medium] Content classification inside locked section may exceed 3s hook caller timeout
- **Critic**: not flagged (review aborted by stream idle timeout)
- **Cross**: `_do_update()` holds the shared `_state_lock` while reclassifying every queued file via `classify_with_content()` (`scripts/blast_radius.py:184`), which scans file contents. Caller `hook_runner._post_edit_enqueue` kills the subprocess after 3s (`scripts/hook_runner.py:143`) and fails open.
- **Judgment**: Code evidence supports the concern. The diff classifies *every file in `data["files"]`* under the lock — queue size grows unboundedly across rounds, and content scans are I/O-bound. Combined with potential contention against `record_review_done()` writers, the locked critical section can plausibly exceed 3s on slow FS or large queues, causing silent enqueue loss (hooks fail open).
- **Action Required**: Minimize locked work. Either (a) classify only the newly edited `rel` outside the lock, then `blast_tier = max(existing, new_tier)` inside a short locked merge, or (b) compute all tiers outside the lock and only do RMW merge inside. Add a regression test simulating a slow classifier vs. the 3s caller timeout.

#### 2. [ACCEPT] [Low] No regression test for metadata preservation across enqueue
- **Critic**: not flagged (review aborted)
- **Cross**: The change's stated safety claim is preserving `reviews`, `round_count`, `last_round_summary`, `round_started_at`, `fired_at` while enqueueing, but `tests/test_pending_review.py:185+` only covers marker creation, non-review skip, `updated_at`, dedupe, accumulation, JSON validity — none load a marker pre-populated with completed review metadata.
- **Judgment**: Valid gap. The lock-based fix protects against concurrent clobbering, but a unit-test boundary that asserts "after enqueue, only `files`/`updated_at`/`blast_tier` mutate; `round_count`/`reviews`/`round_started_at`/`fired_at` survive byte-for-byte" is missing. Without it, future refactors of `_do_update()` can silently regress the invariant.
- **Action Required**: Add a test that seeds a marker with full review metadata, enqueues an additional file, then asserts metadata fields are unchanged and `blast_tier`/`files`/`updated_at` updated correctly.

### Cross-only REJECTED finding (recorded for transparency)

- **[REJECT] Importing private `review_gate._state_lock`** — Cross self-rejected. Correct: enqueue and `record_review_done` mutate the same marker, so they must share the same lock. The boundary is intentional.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | Lock-held content classify vs 3s caller timeout | Medium | ACCEPT | Cross only (Critic timed out) |
| 2 | Missing metadata-preservation regression test | Low | ACCEPT | Cross only (Critic timed out) |

### Recommendations

- Move per-file `classify_with_content()` work outside the `_state_lock` critical section; keep only the JSON RMW merge inside the lock.
- Add a regression test in `tests/test_pending_review.py` that seeds `reviews`, `round_count`, `last_round_summary`, `round_started_at`, `fired_at` and asserts they survive an enqueue round.
- Re-run critic review (the original critic call hit a stream idle timeout — only the cross signal informed this verdict). If critic surfaces a Critical, escalate to BLOCK before merge.
- Phase 0 policy: WARN is advisory — merge is permitted with the two follow-ups tracked, but the timeout risk is the kind that surfaces only under load, so prefer fixing #1 in this PR.