# Code Review: hook_runner

> Source: scripts/hook_runner.py
> Date: 2026-05-21 15:10
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This touches hooks, review gates, commit policy, and agent-routing behavior.

### Findings

1. [High] Review-first order migration is incomplete
   - File: `scripts/blast_radius.py:205`
   - Code: `return ["af-test-runner", "af-critic", "af-cross-review"]`
   - Issue: `hook_runner.py`, `review_gate.py`, `.githooks/pre-commit`, and `check_pending_review.py` now tell users to run `af-critic → af-cross-review → af-test-runner`, but `blast_radius.required_agents()` still returns the old test-first order. Its regression test also preserves the old contract at `tests/test_review_gate_phase0.py:332-333`.
   - Suggestion: Update `required_agents()` and its tests to the new canonical order, or centralize agent order in one shared constant used by all emitters.

2. [High] Malformed `round_count` can still fail-open the commit gate
   - File: `scripts/review_gate.py:279`
   - Code: `if int(state.get("round_count", 0)) < 5:`
   - Issue: If the queue state contains `round_count: null` or another non-int value, `int(...)` raises. `hook_runner.py:325-329` catches all exceptions from `is_gate_blocked()` and treats them as PASS, so a malformed pending queue can bypass the commit gate.
   - Suggestion: Use the guarded parse pattern already present in `check_pending_review.py:107-113`, default invalid values to `0`, and add a regression test for corrupt `round_count`.

3. [Medium] Max-round policy is duplicated as a raw literal
   - File: `scripts/review_gate.py:279`
   - Code: `if int(state.get("round_count", 0)) < 5:`
   - Issue: `check_pending_review.py` defines `MAX_ROUNDS = 5`, but `review_gate.py` uses a separate hardcoded `5`. This change is explicitly correcting a prior drift from `2` to `5`, but leaves the same drift mechanism in place.
   - Suggestion: Move the cap to a shared constant or define `MAX_ROUNDS` in `review_gate.py` and make tests reference that constant instead of embedding `5`.

### Comparison with Known Issues

- Repeats known review patterns around gate drift and hardcoded policy values. The code-review checklist calls out magic numbers and silent fallback.
- The malformed-state path matches the known “silent fallback hides real errors” class: `hook_runner.py` fail-opens on any `is_gate_blocked()` exception.
- The caller/callee inventory issue matches recent known findings: updating only visible prompt strings leaves helper APIs and tests with contradictory routing.

### Positive Observations

- The changed user-facing strings in `hook_runner.py`, `review_gate.py`, `.githooks/pre-commit`, and `check_pending_review.py` are internally consistent.
- The change keeps subprocess usage as argv lists with `shell=False`, so it does not introduce shell injection in `hook_runner.py`.