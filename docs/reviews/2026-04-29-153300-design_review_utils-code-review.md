# Code Review: design_review_utils

> Source: core/design_review_utils.py
> Date: 2026-04-29 15:33
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

Verified both Cross findings against the actual code. `docs/patterns/2026-04-18-external-api-3tier.md` exists and `is_design_doc()` returns True for it after this change, while the design-gate spec at `docs/2026-04-21-design-doc-review-gate.md:45` explicitly excludes `docs/patterns/*.md`. Also confirmed there is no automatic `af-doc-qa` trigger anywhere — only an agent definition, not a hook — so work-item edits now have zero auto-review coverage.

## Final Code Review

### Verdict: WARN

Two real defects exist but neither is Critical. The dated-doc INCLUDE silently swallows `docs/patterns/*.md` against an explicit spec exclusion, and the new work-items EXCLUDE removes auto-review coverage with no compensating trigger path. Both should be fixed in this PR or in an immediate follow-up; the change is otherwise correct (EXCLUDE-before-INCLUDE ordering is sound).

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] `docs/patterns/**` misclassified as design docs
- **Critic**: not flagged
- **Cross**: New `docs/**/20??-??-??-*.md` matches `docs/patterns/2026-04-18-external-api-3tier.md`, but design-gate spec excludes `docs/patterns/*.md`.
- **Judgment**: Verified. `is_design_doc(.../docs/patterns/2026-04-18-external-api-3tier.md)` returns `True` after this diff. Spec at `docs/2026-04-21-design-doc-review-gate.md:42-45` explicitly lists `docs/patterns/*.md` as non-design ("짧은 참조성 패턴 노트, 단일 설계문서 엄격도 불요"). `design_review_trigger.py:73-81` would now enqueue a review for that file on every edit.
- **Action Required**: Add to `EXCLUDE_PATTERNS` in `core/design_review_utils.py:43-53`:
  ```python
  "docs/patterns/**",
  "docs/patterns/*",
  ```

#### 2. [ACCEPT] [Medium] Work-item edits lose all automatic review coverage
- **Critic**: not flagged
- **Cross**: New `docs/work-items/**` exclusion removes work-items from the only PostToolUse auto-trigger; no compensating `af-doc-qa` hook exists.
- **Judgment**: Verified. Before the diff, `docs/work-items/<slug>/feature-plan.md` matched `docs/**/*feature*.md` → 2-agent design review (wrong agent set per CLAUDE.md, but at least *some* automatic review). After the diff, `is_design_doc()` returns False and `design_review_trigger.py:73-91` only branches on design/code paths. A grep across `.githooks/`, `scripts/`, `core/`, `hook_runner.py`, `.claude/` finds zero references to an automatic `af-doc-qa-pending` queue or `is_work_item_doc()` function. The comment at line 50 ("별도 경로(af-doc-qa 3-agent)로 처리됨") describes a path that does not exist yet.
- **Action Required**: Either (a) implement the `is_work_item_doc()` branch in `design_review_trigger.py` that emits a `[af-doc-qa-pending]` signal before this exclusion ships, or (b) keep the exclusion but file a tracked TODO/issue and add a brief comment that auto-coverage is intentionally pending.

#### 3. [ACCEPT] [Medium] No regression test for new INCLUDE/EXCLUDE branches
- **Critic**: Repo has no test exercising `is_design_doc()`. New patterns interact non-trivially with existing keyword globs.
- **Cross**: not flagged directly, but Findings #1/#2 above are exactly the kind of regression a test would catch.
- **Judgment**: Both Cross findings are evidence that this code path is undertested. A test fixture covering positive (`docs/2026-04-29-foo.md`), exclude (`docs/work-items/x/feature-plan.md`, `docs/patterns/2026-04-18-x.md`, `docs/reviews/...md`), and near-miss negative (`docs/2026-readme.md`) cases would have caught Finding #1 immediately.
- **Action Required**: Add `tests/test_design_review_utils.py` with the cases above, including the patterns/work-items branches.

#### 4. [HOLD] [Low] Redundant flat dated pattern + `20??` century literal
- **Critic**: Flat `docs/20??-??-??-*.md` is redundant given `_matches_glob` semantics (the recursive form already matches root-level files). `20??` silently expires in year 2100.
- **Cross**: not flagged.
- **Judgment**: The redundancy is real but mirrors existing surrounding patterns (lines 33-36 are also flat/recursive pairs), so it's stylistic consistency rather than a defect. The 2100 expiry is 75 years out — non-actionable.
- **Question for Author**: Keep stylistic symmetry as-is? Optional widen to `2???-??-??-*.md` if you want to harden now.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `docs/patterns/**` misclassified | Medium | ACCEPT | Cross |
| 2 | Work-items lose auto-review coverage | Medium | ACCEPT | Cross |
| 3 | No regression test for new branches | Medium | ACCEPT | Critic |
| 4 | Flat redundancy + 2100 expiry | Low | HOLD | Critic |

### Recommendations

1. **Block merge until Finding #1 is fixed** — add `docs/patterns/**` and `docs/patterns/*` to `EXCLUDE_PATTERNS`. One-line change, directly contradicts existing spec.
2. **Decide Finding #2 in this PR** — either implement `is_work_item_doc()` auto-trigger, or add a tracked TODO comment so the coverage gap is intentional and documented, not silent.
3. **Add `tests/test_design_review_utils.py`** with positive/exclude/negative fixtures including patterns and work-items — closes Finding #3 and prevents future regressions of #1/#2.
4. Cross-reviewer's REJECTED concern about `docs/reviews/**` is correctly rejected (already excluded at lines 48-49 with EXCLUDE precedence).