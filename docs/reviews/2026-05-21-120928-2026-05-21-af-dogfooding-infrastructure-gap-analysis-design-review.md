# Design Review: 2026-05-21-af-dogfooding-infrastructure-gap-analysis

> Source: docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md
> Date: 2026-05-21 12:09
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: WARN

### Findings

1. [High] Step 0(b) only updates one producer, but the same agent order is hard-coded in multiple callers
   - Section: “G7 agent 실행 순서 정합 … `check_pending_review.py:60` … `check_pending_review.py:56`”
   - Issue: The design scopes the fix to `scripts/check_pending_review.py`, but actual user-facing/caller sites also encode `af-test-runner → af-critic → af-cross-review`: `scripts/blast_radius.py:206-207`, `scripts/hook_runner.py:317-320`, `scripts/review_gate.py:535-538`, and `.githooks/pre-commit:65`. Updating only `_agents_for_tier()` leaves commit-block and helper output contradicting CLAUDE.md.
   - Suggestion: Define one canonical order helper or explicitly update all output sites above. Add regression tests for emitted instruction strings, not only `_agents_for_tier()`.

2. [High] Review-first order is underspecified for deterministic T3-skip re-prompting
   - Section: “check_pending_review.py:56 t3_skip 분기 … review-first 채택 시: `af-critic → af-test-runner`”
   - Issue: Current T3 skip is stateful: `scripts/review_gate.py:_required_tiers_for()` returns `[1,2]` before af-critic advisory, but after `record_review_done()` records `t3_required=yes|unknown`, it clears `fired_at` and expands back to `[1,2,3]`. The design does not define the expected prompt sequence once af-critic runs first and changes required tiers.
   - Suggestion: Add acceptance tests for `t3_required=no`, `yes`, and `unknown`, proving `check_pending_review.py` re-prompts for `af-cross-review` when needed and does not loop.

3. [Medium] Windows concurrency risk is acknowledged nowhere
   - Section: “Step 0 — 정책 정합 … G1/G7/G8”
   - Issue: `scripts/review_gate.py:_state_lock()` explicitly falls back to no-op on Windows. This project is currently on Windows, and the design changes scripts that read/write `.af_review_queue/pending_agent_review.json` via `check_pending_review.py`, `enqueue_agent_review.py`, and `record_review_done()`. Concurrent hook/agent writes can still race despite atomic replace.
   - Suggestion: Either defer concurrency as an explicit known risk, or add Windows-safe locking and tests that interleave `check_pending_review` with `record_review_done`.

4. [Medium] G8 verification is too shallow for the actual hook behavior
   - Section: “cmd 수정 후 검증: hook output에서 ‘af-cross-review 1개만’ 안내 확인”
   - Issue: `scripts/check_design_pending.py` only prints after queue JSON exists, `timestamp` passes `MIN_BATCH_INTERVAL_SEC`, and `.design_review_fired.json` does not suppress it. A simple string/unit check can miss the real UserPromptSubmit path.
   - Suggestion: Add a fixture-driven test that creates `.af_review_queue/pending/design/*.json`, forces the quiet interval, runs `check_design_pending.main()`, and asserts the emitted line contains only `af-cross-review`.

5. [Low] G1 max-rounds change needs one source of truth
   - Section: “G1 max_rounds … `check_pending_review.py:30 MAX_ROUNDS = 2` … `review_gate.py:282` literal `2`”
   - Issue: The document correctly identifies two literals, but the proposed options still allow future drift because `review_gate.py` does not import `MAX_ROUNDS`.
   - Suggestion: Move the cap into a shared constant or helper used by both scripts, then update CLAUDE.md or code to match.

### Missing from Design
- Explicit caller/callee update list for G7: `blast_radius.required_agents()`, `hook_runner._pre_bash_review_gate()`, `review_gate._cli()`, `.githooks/pre-commit`.
- Windows locking behavior for `.af_review_queue`.
- Regression tests for user-facing hook output strings.
- Recovery behavior if a partially updated queue has old `fired_at` plus new review order.

### Positive Observations
- The G/R split maps to real entrypoints: `.githooks/pre-commit → scripts/review_gate.py` vs `agent_launcher.py --workspace`.
- The document correctly rejects the stale `review_gate.py:214 round_count<2` claim and points to the current `check_pending_review.py`/`review_gate.py` locations.