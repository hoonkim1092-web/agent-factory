# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-05-21 15:07
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings, but one High-severity fail-open hazard plus two Medium drift/test-coverage gaps. Diff is safe to merge once the type-guard for `round_count` and the `MAX_ROUNDS` import are added; the test pin can ship in the same PR.

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] `round_count` parse can raise → gate fails open in hook path
- **Critic**: not flagged
- **Cross**: "`int(state.get("round_count", 0))` raises on `round_count: null`; `check_pending_review.py:110-113` guards this with `except (TypeError, ValueError)` but `is_gate_blocked()` does not. `hook_runner.py:326-329` catches and treats as PASS → stale queue bypasses the gate."
- **Judgment**: Verified against code. `scripts/hook_runner.py:326-329` explicitly fail-opens on any exception from `is_gate_blocked()`. `scripts/check_pending_review.py:109-113` already uses the guarded-parse pattern, so the asymmetry is real. Severity escalated to High because the failure mode is a silent gate bypass on malformed state — same class as G1's drift hazard.
- **Action Required**: Extract `_round_count(state) -> int` helper using the same `try/except (TypeError, ValueError)` pattern as `check_pending_review.py:109-113`, and call it at `scripts/review_gate.py:282`. Add a test: malformed state with `round_count: null` returns `(True, "stale-review")` rather than raising.

#### 2. [ACCEPT] [Medium] Magic number `5` duplicates `MAX_ROUNDS` instead of importing it
- **Critic**: "`MAX_ROUNDS = 5` is the SSoT in `check_pending_review.py:30`. Hardcoding `5` in `review_gate.py:282` re-introduces the drift G1 calls out. Fixes value but not coupling."
- **Cross**: not flagged
- **Judgment**: Confirmed — `check_pending_review.py:30` defines `MAX_ROUNDS = 5`; `review_gate.py:282` now hardcodes `5`. The diff's own infrastructure-gap-analysis doc (§94-100) explicitly recommends "상수 참조로 개선 권고". The existing `t3_classifier` import block at L94-97 already establishes the `scripts/` fallback pattern.
- **Action Required**: `from check_pending_review import MAX_ROUNDS as _MAX_ROUNDS` (mirror the existing `t3_classifier` import-with-fallback block) and use `< _MAX_ROUNDS`. Critic finding #4 (stale comment) auto-resolves once this lands.

#### 3. [ACCEPT] [Medium] No regression test pins the new boundary at 3 or 4
- **Critic**: "`test_t8_block_verdict_checked_even_when_rounds_capped` exercises `round_count=5` only. The diff also changes behavior at `{2,3,4}`: previously fell through to `verdict-block`, now reports `stale-review`. A future flip back to `< 2` or to `<= 5` would not fail any test."
- **Cross**: not flagged (ran existing suite, 62 pass — does not assess coverage of the new boundary)
- **Judgment**: Correct. The change is the load-bearing semantic of this PR; tests must lock it in.
- **Action Required**: Add `test_t8b_stale_review_blocks_below_cap` parametrized over `round_count ∈ {2,3,4}` asserting `(True, "stale-review")`; keep the existing `round_count=5` assertion that stale+BLOCK reports `verdict-block:*`.

#### 4. [HOLD] [Low] CLI guidance order is unconditional regardless of `blast_tier`
- **Critic**: "`scripts/review_gate.py:535-538` prints the 3-agent chain unconditionally, but `_agents_for_tier()` branches to `af-test-runner` only (Tier 1) or `af-critic → af-test-runner` (T3-skip). Visible inconsistency with `_required_tiers_for`."
- **Cross**: explicitly REJECTed a related concern, but on different grounds (the order change does not break `record_review_done` / `is_gate_blocked` semantics — not the same point).
- **Judgment**: Pre-existing issue, not introduced by this diff. The diff line is correct in the most common path (Tier 2~3). Tier-branching the CLI message is a separate follow-up; merging it into this commit expands scope.
- **Question for Author**: Land this as a follow-up, or fold it in now? If folding: promote `_agents_for_tier` to a shared module so `review_gate._cli` can call it on the loaded state.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `round_count` parse fails open on null/invalid | High | ACCEPT | Cross |
| 2 | Magic `5` should import `MAX_ROUNDS` | Medium | ACCEPT | Critic |
| 3 | No regression test for new boundary | Medium | ACCEPT | Critic |
| 4 | CLI order string ignores `blast_tier` | Low | HOLD | Critic |

### Recommendations
- Block-equivalent before merge: fix #1 (type-guard) and #2 (import `MAX_ROUNDS`) — both are one-liner classes of fix that the diff's own gap-analysis doc anticipates.
- Same PR: add the boundary tests from #3 (`round_count ∈ {2,3,4}` → `stale-review`; `round_count=5` stale+BLOCK → `verdict-block:*`; new `round_count=None` → `stale-review` without raising).
- Decide #4 explicitly: fold-in or file follow-up. The diff's CLI line is now coherent with the hook-side string at `check_pending_review.py:60` for the common path; the tier-branching is a separate G7 cleanup.
- T3 advisory from the critic stands: this touches review-gate threshold semantics and warrants the cross-review pass that produced the High finding above.