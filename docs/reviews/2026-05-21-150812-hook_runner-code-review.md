# Code Review: hook_runner

> Source: scripts/hook_runner.py
> Date: 2026-05-21 15:08
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

### Findings

1. [High] `required_agents()` still emits the old review order
   - File: `scripts/blast_radius.py:205`
   - Code: `return ["af-test-runner", "af-critic", "af-cross-review"]`
   - Issue: The staged change updates `check_pending_review.py`, `hook_runner.py`, `review_gate.py`, `.githooks/pre-commit`, and Blueprint text to the review-first order, but this live helper still returns test-first order. Its CLI prints `agents=...`, so users/tools can still receive contradictory routing.
   - Suggestion: Change tier 2/3 return to `["af-critic", "af-cross-review", "af-test-runner"]`, or better centralize the ordered agent list in one module and reuse it from all emitters.

2. [Medium] Regression test preserves the stale helper contract
   - File: `tests/test_review_gate_phase0.py:332`
   - Code: `assert required_agents(2) == ["af-test-runner", "af-critic", "af-cross-review"]`
   - Issue: The test suite still asserts the old order, so it will protect the inconsistency above instead of catching it. This directly conflicts with the new Blueprint line and hook messages.
   - Suggestion: Update expected tier 2/3 order to `["af-critic", "af-cross-review", "af-test-runner"]` and add a CLI/output assertion if `blast_radius.py` is intended to be user-facing.

3. [Medium] `MAX_ROUNDS` policy is duplicated as a literal in the gate
   - File: `scripts/review_gate.py:279`
   - Code: `if int(state.get("round_count", 0)) < 5:`
   - Issue: `scripts/check_pending_review.py:28` defines `MAX_ROUNDS = 5`, but the enforcement side uses a separate hardcoded `5`. This repeats the exact kind of hook/gate policy drift this change is trying to fix; future edits can make prompt emission and commit blocking disagree again.
   - Suggestion: Move `MAX_ROUNDS` to a shared gate constants module or define it in `review_gate.py` and import it from `check_pending_review.py`. Add a test that checks the cap value used by both paths.

### Comparison with Known Issues

- This change addresses the known G7/G1/G8 policy drift noted in `code-review.md` and recent review docs, but only partially.
- It repeats the known “caller/message inventory incomplete” pattern: `blast_radius.required_agents()` and its regression test still encode `af-test-runner → af-critic → af-cross-review`.
- The duplicated `MAX_ROUNDS` literal is a medium maintainability risk matching the checklist’s magic-number/policy-drift concern.

### Positive Observations

- `hook_runner.py`, `review_gate.py`, `.githooks/pre-commit`, and Blueprint user-facing messages were updated consistently to the review-first order.
- The round-cap behavior test was updated from `2` to `5` for the stale-plus-BLOCK path, preserving the important invariant that BLOCK verdicts still block after the cap.