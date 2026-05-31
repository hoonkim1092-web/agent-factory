# Code Review: review_metrics_logger

> Source: scripts/review_metrics_logger.py
> Date: 2026-05-31 15:15
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change affects review-gate routing behavior and can suppress Tier 3 review.

### Findings

1. [High] Recent T3 BLOCK can be missed after a same-commit rerun
   - File: `scripts/review_metrics_logger.py:413`
   - Code: `if tier == 3 and sha not in t3_seen:`
   - Issue: `t3_order` records the first T3 appearance per commit, while `by_commit[sha][3]` stores the last T3 record. If an old commit gets a later T3 rerun that BLOCKs, the BLOCK verdict is attached to an old `sha` position and can fall outside `recent_shas`. I reproduced this: 12 clean commits plus a latest rerun BLOCK for the first SHA returns `{"skip": True, "reason": "t3-redundant"}`.
   - Suggestion: Build the recent window from the latest T3 record timestamps, not first-seen SHA order. Store `(ts, sha, record)` for each commit’s final T3 record, sort by parsed `ts`, then check the last `T3_SKIP_RECENT_WINDOW`.

2. [High] Span gate can be satisfied by non-T3 records
   - File: `scripts/review_metrics_logger.py:444`
   - Code: `first_ts = datetime.fromisoformat(records[0]["ts"])`
   - Issue: The sufficiency gate is meant to prove enough Tier 3 telemetry exists over at least 7 days, but it uses the first and last record across all tiers. Ten T3 commits from a single day plus unrelated T1 records spanning 8 days authorizes `skip=True`.
   - Suggestion: Compute `span_days` from records that actually contribute to the T3 sample, preferably the final T3 record per commit after timestamp sorting.

3. [High] Malformed metrics lines fail open for skip decisions
   - File: `scripts/review_metrics_logger.py:399`
   - Code: `records = _load_records(workspace)`
   - Issue: `_load_records()` silently drops invalid JSON lines (`except Exception: pass` at `scripts/review_metrics_logger.py:221`). That was tolerable for a best-effort report, but this new function uses the lossy result to authorize skipping Tier 3. A truncated or malformed T3 BLOCK line can disappear, lowering `recent_block` and `block_only_rate`.
   - Suggestion: Add a strict loader path for `compute_t3_telemetry_skip()`: if any metrics line cannot parse or lacks required fields, return `skip=False` with a reason like `metrics-corrupt`.

4. [High] The new Tier 3 skip policy file is not Always-T3 protected
   - File: `scripts/review_gate.py:147`
   - Code: `_ALWAYS_TIER3_PATTERNS: tuple[re.Pattern[str], ...] = tuple(`
   - Issue: `scripts/review_metrics_logger.py` now contains the Tier 3 skip authorization logic, but it is not in `_ALWAYS_TIER3_PATTERNS`. Future edits to thresholds or skip logic can themselves be reviewed without Tier 3 when telemetry skip is active.
   - Suggestion: Add `r"scripts/review_metrics_logger\.py$"` to `_ALWAYS_TIER3_PATTERNS` and add a regression test proving this file requires `[1, 2, 3]`.

### Comparison with Known Issues

- The change repeats the known timestamp-span weakness documented around `review_metrics_logger.span_days` being file-order dependent, but now promotes it from report guidance into gate behavior.
- It also repeats the known silent-fallback pattern: parse failures are swallowed, which can now affect Tier 3 skip authorization.
- The recent code-review log already flags the Always-T3 protection gap for `review_metrics_logger.py`; this change still leaves that risk open.

### Positive Observations

- The skip decision is fail-closed for no data and insufficient sample count.
- The caller freezes the telemetry decision into queue state, which avoids recomputing different required tiers mid-review.