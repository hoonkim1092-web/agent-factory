# Code Review: design_review_utils

> Source: core/design_review_utils.py
> Date: 2026-04-29 15:08
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. One accepted High-actionability gap (missing test coverage) plus one Medium asymmetry concern that has weak counter-evidence — mergeable with documented follow-ups.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] No test coverage for new dated-doc classifier branch
- **Critic**: not flagged
- **Cross**: "INCLUDE_PATTERNS now includes `docs/20??-??-??-*.md`, but no tests exercise `is_design_doc()` or this root dated-doc case." `rg` confirmed no references.
- **Judgment**: Strong evidence (grep-verified) and the function is the gating predicate at `scripts/design_review_trigger.py:73` and `core/hooks/design_review_hook.py:116,157`. A regression here silently disables design-review enqueue.
- **Action Required**: Add `tests/test_design_review_utils.py` with at least: `docs/2026-04-21-foo.md → True`, `docs/code_review/code-review.md → False`, `docs/reviews/2026-04-29-...-design-review.md → False`, `docs/features/whatever.md → True`.

#### 2. [HOLD] [Medium] Flat-only pattern omits subdirectory dated docs (asymmetric with `*design*`/`*feature*`)
- **Critic**: `?`/`*` don't cross `/`, so `docs/reviews/2026-04-29-...md` won't match. Other keyword patterns have both flat (`docs/*X*`) and deep (`docs/**/*X*`) variants; the new pattern has flat only.
- **Cross**: Implicitly rejects the deep-variant concern — `CLAUDE.md:36-41` and `docs/2026-04-21-design-doc-review-gate.md:36-46` define single design docs as `docs/YYYY-MM-DD-*.md` (root), not deeper.
- **Judgment**: Reviewers contradict. Diff evidence: behavior is root-only by design (review outputs in `docs/reviews/` should NOT re-trigger design review — would loop). But the asymmetry with existing flat/deep pairs is a real readability hazard for future contributors.
- **Question for Author**: Is root-only intentional (no `docs/**/20??-??-??-*.md`)? If yes, add a one-line comment beside line 37 stating "subdirectory dated docs deliberately excluded — review outputs and work-item folders use separate pipelines." If no, add the deep variant.

#### 3. [ACCEPT] [Low] Comment cross-references CLAUDE.md (drift risk)
- **Critic**: Comment says "CLAUDE.md 문서 규칙 대응"; if the naming convention in CLAUDE.md changes, the comment goes stale silently.
- **Cross**: not flagged
- **Judgment**: Single-reviewer Low-severity stylistic concern; evidence is the comment text itself. Cheap to fix.
- **Action Required** (optional): Drop the CLAUDE.md reference; commit message already carries policy traceability.

#### 4. [HOLD] [Low] Pattern accepts non-calendar dates (e.g., `20AB-ZZ-QQ-...`)
- **Critic**: `?` matches any character; pattern is a discovery heuristic, not a date validator.
- **Cross**: not flagged
- **Judgment**: Theoretical only — no caller uses this for validation, just discovery. No action unless re-purposed.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Missing test coverage for `is_design_doc` + new pattern | Medium | ACCEPT | Cross |
| 2 | Flat-only pattern asymmetry vs `*design*`/`*feature*` | Medium | HOLD | Critic vs Cross |
| 3 | Comment encodes CLAUDE.md policy (drift risk) | Low | ACCEPT | Critic |
| 4 | Pattern matches non-calendar `20??` dates | Low | HOLD | Critic |

---

### Recommendations
- **Required before next commit on this area**: Add `tests/test_design_review_utils.py` with the four cases listed in Finding #1.
- **Clarify intent**: Either add `docs/**/20??-??-??-*.md` (deep variant) or add a one-line comment at `core/design_review_utils.py:37` explicitly stating subdirectory exclusion is intentional.
- **Optional polish**: Trim the `CLAUDE.md` reference from the comment to avoid future drift.
- **No action**: Finding #4 (non-calendar `20??` dates) — purely theoretical given current usage.