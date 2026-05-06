# Code Review: hook_runner

> Source: scripts/hook_runner.py
> Date: 2026-05-01 11:16
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Two reviewers aligned on the structural correctness of the change (gate blocking via `verdict=fail` is intact). Stale documentation and a dead-code question remain unresolved.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Medium] Stale NEXT_STEPS.md documents removed behavior
- **Critic**: Not flagged
- **Cross**: "`NEXT_STEPS.md:66` still says `_apply_test_gap_verdict()` downgrades `blast_tier` to 1 on FAIL" — explicitly accepted
- **Judgment**: Cross reviewer examined `NEXT_STEPS.md` directly. The diff confirms the downgrade call is gone. The docs now describe behavior the code no longer performs, which will mislead future contributors.
- **Action Required**: Update `NEXT_STEPS.md:66` to state the Phase 1 invariant — test-gap FAIL forces `verdict=fail`; `blast_tier` stays owned by `blast_radius.py` + `enqueue_agent_review.py`.

#### 2. [HOLD] [Medium] `downgrade_blast_tier` dead-code status in `review_gate.py`
- **Critic**: "Previously the only call site was this removed block — dead code, violates Phase 1 invariant"
- **Cross**: "review_gate.py:293–306 deprecates `downgrade_blast_tier()` by raising `NotImplementedError`" — implies `review_gate.py` was separately updated
- **Judgment**: The two reviews diverge on the actual state of `review_gate.py`. The diff does not include that file. If Cross is correct and `NotImplementedError` was added, the function is explicitly tombstoned (good). If Critic is correct and the function is silently reachable, it violates the documented invariant.
- **Question for Author**: Was `review_gate.py` updated in this same commit or a prior one? Run `grep -r downgrade_blast_tier scripts/` to confirm no live call site remains and that `NotImplementedError` is in place.

#### 3. [REJECT] [High→PASS] blast_tier escalation silently lost on test-gap FAIL
- **Critic**: "If `max-merge` only aggregates tiers from static analysis, test-gap FAILs will silently stop influencing the final blast tier"
- **Cross**: Explicitly rejects — "`_apply_test_gap_verdict()` still returns `fail`; `record_review_done()` receives it; `review_gate.is_gate_blocked()` treats `fail` like `block`. Gate still blocks on missing tiers." Also confirmed by `tests/test_phase1_blast_tier_invariant.py` passing.
- **Judgment**: Cross reviewer traced the full call chain (`hook_runner.py:341 → record_review_done → is_gate_blocked`) and has test coverage evidence. The gate enforcement mechanism is `verdict=fail`, not `blast_tier` mutation — the critic's concern assumes `blast_tier` is the gate signal, but it is not. Finding is rejected on code evidence.

---

### Summary Table

| # | Title | Severity | Decision | Source |
|---|-------|----------|----------|--------|
| 1 | Stale NEXT_STEPS.md documents removed behavior | Medium | ACCEPT | Cross only |
| 2 | `downgrade_blast_tier` dead-code status | Medium | HOLD | Critic (Cross partially contradicts) |
| 3 | blast_tier escalation lost on test-gap FAIL | High→Pass | REJECT | Cross rejects with test evidence |

---

### Recommendations

- **Fix now**: Update `NEXT_STEPS.md:66` with Phase 1 invariant description (5-minute edit, no code risk).
- **Verify before close**: Run `grep -rn downgrade_blast_tier scripts/` and confirm either (a) `NotImplementedError` is present in `review_gate.py`, or (b) the function has been deleted. Post the result as a follow-up comment to resolve the HOLD.
- **No code changes required** for the blast_tier gate concern — Cross reviewer's test coverage (`test_phase1_blast_tier_invariant.py`) is sufficient evidence.