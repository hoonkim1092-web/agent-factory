# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-05-31 15:12
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This changes review-gate policy and Tier 3 skipping behavior.

### Findings

1. [High] Telemetry skip overrides af-critic’s explicit T3 advisory
   - File: `scripts/review_gate.py:297`
   - Code: `if _telemetry_skip_enacted(state): return [1, 2]`
   - Issue: This skip path does not consult `af-critic`’s `t3_required` value. If af-critic records `t3_required: yes` or `unknown`, `_required_tiers_for()` can still drop Tier 3 whenever telemetry says skip. That contradicts the T3 advisory contract where `yes` and `unknown` require Tier 3.
   - Suggestion: Make telemetry skip conditional on no contrary critic advisory, e.g. only allow it before critic exists or when `_critic_t3_advisory(state) == "no"`. If advisory is `yes` or `unknown`, force `[1, 2, 3]`.

2. [High] Stale telemetry skip can persist after telemetry computation fails
   - File: `scripts/enqueue_agent_review.py:232`
   - Code: `except Exception: telemetry_decision = None`
   - Issue: `_do_update()` only writes `data["t3_telemetry_skip"]` when `telemetry_decision is not None`. If a prior queue state has `{"skip": true}` and `review_metrics_logger` import/parse fails later, the old authorization remains in state, and `review_gate.py:297` can keep skipping Tier 3.
   - Suggestion: Fail closed by clearing or replacing `t3_telemetry_skip` on telemetry failure, e.g. `{"skip": False, "reason": "telemetry-unavailable"}`. Avoid silent retention of prior skip state.

3. [High] The new Tier 3 skip decision module is not in the always-Tier-3 risk list
   - File: `scripts/review_gate.py:149`
   - Code: `r"scripts/hook_runner\.py$", ... r"scripts/build_review_bundle\.py$",`
   - Issue: `scripts/review_metrics_logger.py` now contains `compute_t3_telemetry_skip()`, which decides whether Tier 3 may be skipped, but it is absent from `_ALWAYS_TIER3_PATTERNS`. A future change to skip thresholds or logic in that file can itself be reviewed without Tier 3 when telemetry skip is active.
   - Suggestion: Add `r"scripts/review_metrics_logger\.py$"` to `_ALWAYS_TIER3_PATTERNS`, and add a regression test proving changes to that file require `[1, 2, 3]`.

### Comparison with Known Issues

- This repeats a known silent-fallback pattern: broad `except Exception: ... pass/None` in hook/gate paths can hide real failures and fail open.
- The change touches review policy/gates, so it matches the project’s own “always Tier 3” risk category. The new telemetry decision file should be protected like `review_gate.py` and `hook_runner.py`.

### Positive Observations

- The gate still uses atomic writes for queue state via `tempfile.mkstemp()` plus `os.replace()`.
- The always-Tier-3 override is placed before both deterministic and telemetry skip paths, which is the right ordering for protected files that are actually listed.