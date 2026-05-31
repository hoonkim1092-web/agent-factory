# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-05-31 15:22
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This changes review policy/gate behavior and Tier 3 routing.

### Findings

1. [High] Telemetry skip bypasses per-change T3 requirement and critic advisory
   - File: `scripts/review_gate.py:298`
   - Code: `if _telemetry_skip_enacted(state):`
   - Issue: `_required_tiers_for()` can return `[1, 2]` solely from historical telemetry, even when `state["t3_required"]` is `True` or af-critic later records `t3_required: yes/unknown`. That violates the advisory contract: `yes` and `unknown` require Tier 3.
   - Suggestion: Gate telemetry skip with the current diff decision and advisory, e.g. require `state.get("t3_required") is False` and do not skip when `_critic_t3_advisory(state)` is `"yes"` or `"unknown"`.

2. [High] Stale telemetry skip authorization can survive telemetry failures
   - File: `scripts/enqueue_agent_review.py:156`
   - Code: `if telemetry_decision is not None:`
   - Issue: If an existing queue has `t3_telemetry_skip: {"skip": true}` and a later enqueue cannot import/run `review_metrics_logger`, the old skip decision remains in state because failures set `telemetry_decision = None` and `_do_update()` leaves the old field untouched.
   - Suggestion: On telemetry failure, overwrite with `{"skip": false, "reason": "telemetry-unavailable", "metrics": {}}` or remove `t3_telemetry_skip`.

3. [Medium] Data-sufficiency span can be padded by non-T3 records
   - File: `scripts/review_metrics_logger.py:450`
   - Code: `first_ts = datetime.fromisoformat(records[0]["ts"])`
   - Issue: `compute_t3_telemetry_skip()` checks `commits_with_t3`, but computes the 7-day span from all metric records, not the T3 sample. Old/new T1 or T2 records can satisfy `span_days >= 7` while the actual T3 commits are clustered in a short window, authorizing a premature skip.
   - Suggestion: Compute span from timestamps of the T3 records used in `t3_order`, ideally sorted by parsed timestamp.

4. [Medium] Pending-review prompt mislabels telemetry skips as cosmetic-only
   - File: `scripts/check_pending_review.py:61`
   - Code: `"Tier 2 cosmetic-only → deterministic classifier가 Tier 3를 생략했습니다."`
   - Issue: `t3_skip_allowed` is now true for telemetry skips as well as deterministic cosmetic skips. The prompt tells operators the change is cosmetic-only when the skip may actually be historical telemetry-based.
   - Suggestion: Distinguish skip reasons from state, or use neutral text such as “Tier 3 skip is currently allowed by gate policy.”

### Comparison with Known Issues

- This change repeats known review-gate bypass risk patterns from `code-review.md`: fail-open/silent fallback behavior and policy-gate drift.
- The atomic-write pattern is preserved for `pending_agent_review.json`.
- The prior concern that `scripts/review_metrics_logger.py` was missing from ALWAYS-Tier-3 is fixed in the current tree.

### Positive Observations

- The new ALWAYS-Tier-3 path normalizes Windows backslashes before matching.
- Telemetry thresholds are named constants rather than embedded magic numbers.