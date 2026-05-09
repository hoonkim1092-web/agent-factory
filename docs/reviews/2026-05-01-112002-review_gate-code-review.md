# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-05-01 11:20
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. High and Medium issues exist — can merge with documented risks.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] Docstring claims "quiet failure" but `NotImplementedError` propagates
- **Critic**: "함수 정의는 기존 call site가 조용히 실패하도록 보존하되 본문은 NotImplementedError — self-contradictory"
- **Cross**: Not flagged (cross reviewer confirmed zero live callers, but did not evaluate the docstring claim itself)
- **Judgment**: The diff shows the docstring explicitly states the function is preserved "기존 call site가 조용히 실패하도록" — but `raise NotImplementedError` is a hard crash, not quiet failure. The original code used `try/except Exception` + `stderr` print, which was genuine quiet failure. Even with zero current callers, the docstring sets a false contract. Strong single-source finding with direct diff evidence.
- **Action Required**: Either (a) replace `raise NotImplementedError(...)` with `warnings.warn("downgrade_blast_tier is deprecated", DeprecationWarning, stacklevel=2); return` to honor the "quiet failure" claim, or (b) remove "조용히 실패하도록" from the docstring and keep the hard raise as an intentional tripwire.

#### 2. [ACCEPT] [Medium] NEXT_STEPS.md:66 still documents the behavior this diff removes
- **Critic**: "Line 66 describes the original blast_tier=1 downgrade path; prior review cycle accepted fix as Action Required but it was not applied in this diff"
- **Cross**: Not flagged
- **Judgment**: Verifiable by reading the diff context — the docstring change in `downgrade_blast_tier()` explicitly marks the function DEPRECATED (Phase 1), yet NEXT_STEPS.md line 66 still reads as if `downgrade_blast_tier()` + `_apply_test_gap_verdict()` blast_tier=1 path is active. Creates contributor confusion. Prior review cycle had already flagged this as Action Required.
- **Action Required**: Update NEXT_STEPS.md line 66 to reflect Phase 1 reversal, e.g.: `"P1 blast_tier invariant: downgrade_blast_tier() deprecated (NotImplementedError stub) + _apply_test_gap_verdict() forces verdict=fail without touching blast_tier"`.

#### 3. [ACCEPT] [Medium] Dead function preserved without cleanup tracking artifact
- **Critic**: "Docstring defers cleanup to a future commit but no NEXT_STEPS entry, TODO with issue number, or CI check exists"
- **Cross**: Not flagged (confirmed dead code, but did not evaluate whether tracking exists)
- **Judgment**: The diff's own docstring says "삭제는 별도 cleanup commit (Phase 1 scope 외)" — a self-declared deferred action with no mechanism to ensure it happens. Cross review confirmed zero live call sites, which makes this purely a process finding. Pattern matches existing dead-code accumulation flagged in code-review.md §3.3.
- **Action Required**: Add one of: (a) a NEXT_STEPS.md 미완료 entry: `"delete downgrade_blast_tier() + grep check in CI after Phase 1 merge"`, or (b) an inline `# TODO(phase1-cleanup): remove this function after test_phase1_blast_tier_invariant.py is green on main`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Docstring "quiet failure" vs. `NotImplementedError` contradiction | High | ACCEPT | Critic only |
| 2 | NEXT_STEPS.md:66 stale — still documents deprecated blast_tier downgrade | Medium | ACCEPT | Critic only |
| 3 | Dead function with no cleanup tracking artifact | Medium | ACCEPT | Critic only |

Cross Review's 3 initial concerns (live callers, blocking signal, tier behavior) were all self-rejected with strong evidence — none elevated to final findings.

---

### Recommendations

- **Before merge**: Fix Finding 1 (docstring contradiction on `downgrade_blast_tier`) — it is the only High finding and takes < 1 line to resolve.
- **Before merge**: Fix Finding 2 (NEXT_STEPS.md line 66 stale entry) — already flagged as Action Required in a prior review cycle; leaving it again accumulates review debt.
- **Acceptable post-merge**: Finding 3 (cleanup tracking) can be resolved by adding the NEXT_STEPS entry immediately after merge; it does not affect runtime behavior.
- **Positive**: The invariant breadcrumbing across all three gate functions (`_required_tiers_for`, `is_gate_blocked`, `record_review_done`) is well-executed. The actual blocking path (verdict=fail → `is_gate_blocked`) is correct and fully test-covered per cross review's verification (42 passed).