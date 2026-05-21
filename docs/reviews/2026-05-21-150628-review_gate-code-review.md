# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-05-21 15:06
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This change touches review-gate / hook policy behavior.

### Findings

1. [High] Review-order migration is incomplete
   - File: `scripts/blast_radius.py:205`
   - Code: `return ["af-test-runner", "af-critic", "af-cross-review"]`
   - Issue: `review_gate.py`, `hook_runner.py`, `.githooks/pre-commit`, and `check_pending_review.py` now tell users to run `af-critic → af-cross-review → af-test-runner`, but `required_agents()` still emits the old order. Its regression test also preserves the old contract at `tests/test_review_gate_phase0.py:332-333`.
   - Suggestion: Update `required_agents()` and its tests to the review-first order, or introduce a single shared ordered-agent helper used by all emitters.

2. [Medium] `MAX_ROUNDS` policy is duplicated as a literal
   - File: `scripts/review_gate.py:279`
   - Code: `if int(state.get("round_count", 0)) < 5:`
   - Issue: `scripts/check_pending_review.py:28` defines `MAX_ROUNDS = 5`, but the gate enforcement hard-codes the same value independently. This repeats the known magic-number drift pattern from `code-review.md` and was exactly the class of mismatch this change is trying to fix.
   - Suggestion: Import `MAX_ROUNDS` from `check_pending_review.py`, or move it to a small shared policy module used by both scripts.

3. [Medium] T3-skip guidance can re-prompt completed agents after critic-first expansion
   - File: `scripts/check_pending_review.py:181`
   - Code: `agent_list, instruction = _agents_for_tier(blast_tier, t3_skip_allowed)`
   - Issue: The new critic-first order interacts poorly with `_required_tiers_for()`: before af-critic advisory, cosmetic candidates can require `[1, 2]`; after af-critic records `t3_required=yes|unknown`, `review_gate.py:346-347` clears `fired_at` and expands back to `[1, 2, 3]`. The prompt then prints the full static list again, including agents already completed in the current queue.
   - Suggestion: Build the displayed agent list from `required_tiers - completed_reviews`, preserving the configured order, instead of using only `blast_tier`.

### Comparison with Known Issues

- The `review_gate.py:279` literal repeats the known `code-review.md` magic-number maintainability pattern.
- No new non-atomic write pattern was introduced in this diff; `_save_state()` still uses `tempfile + os.replace`.
- No shell-injection pattern was introduced; subprocess usage inspected here remains list-based.

### Positive Observations

- The BLOCK-verdict fall-through behavior remains intact after the cap change; capped stale reviews still continue to verdict inspection.
- The user-facing commit-block strings were updated consistently across `review_gate.py`, `hook_runner.py`, and `.githooks/pre-commit`.