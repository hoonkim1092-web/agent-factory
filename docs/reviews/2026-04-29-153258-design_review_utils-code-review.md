# Code Review: design_review_utils

> Source: core/design_review_utils.py
> Date: 2026-04-29 15:32
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff is small and crash-safe (no I/O, no concurrency), but the new recursive INCLUDE pattern overreaches into multiple non-design subdirectories, and the new work-item EXCLUDE drops a trigger path with no replacement. Both reviewers independently land on the same root cause (pattern scope expansion without matching exclusions), with concrete repro evidence. No Critical findings → not a BLOCK, but the scope/trigger gaps must be fixed before this becomes load-bearing.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Recursive dated-doc INCLUDE captures non-design subdirectories
- **Critic**: Flags `docs/참고/YYYY-MM-DD-*.md` (external project analyses, per saved user memory rule). Traced `_matches_glob` and confirmed match; 6 existing files would falsely enqueue af-critic + af-cross-review on next edit.
- **Cross**: Flags `docs/patterns/2026-04-18-external-api-3tier.md`. `docs/2026-04-21-design-doc-review-gate.md:190` explicitly classifies `docs/patterns/` as `other`. Empirical probe: `is_design_doc(...)` returns `True`.
- **Judgment**: Two distinct directories, same underlying defect — the diff added a recursive `docs/**/20??-??-??-*.md` include without enumerating the subdirectories the project treats as non-design. EXCLUDE_PATTERNS in the diff covers `archive/`, `code_review/`, `reviews/`, `work-items/` only. Both findings are corroborated by file-system evidence.
- **Action Required**: Add to `EXCLUDE_PATTERNS`:
  ```python
  "docs/참고/**", "docs/참고/*",
  "docs/patterns/**", "docs/patterns/*",
  ```

#### 2. [ACCEPT] [High] Work-item edits lose the automatic review trigger with no replacement path
- **Critic**: Not flagged.
- **Cross**: `docs/work-items/**` is excluded from `is_design_doc()`, but `scripts/design_review_trigger.py:72-89` only branches on `is_design_doc()` / `is_code_file()`. CLAUDE.md mandates `af-doc-qa + af-critic + af-cross-review` for work-item sets — the diff silently disables that trigger.
- **Judgment**: Strong evidence; reading the trigger code confirms there is no `is_work_item_doc()` branch, and the local settings hook routes through this same trigger. The exclusion comment ("af-doc-qa 3-agent로 처리됨") implies routing exists, but it does not.
- **Action Required**: Either (a) keep work-items in `is_design_doc()` until the document pipeline lands, OR (b) add `is_work_item_doc()` plus the `review_type="document"` branch in `scripts/design_review_trigger.py`. Severity escalated to High because this regresses a CLAUDE.md-mandated review path.

#### 3. [ACCEPT] [Medium] Date glob `20??-??-??` accepts non-digit characters
- **Critic**: `fnmatch` `?` matches any single char; `20ab-cd-ef-foo.md` would classify as a dated design doc.
- **Cross**: Not flagged.
- **Judgment**: True for `fnmatch.fnmatch` semantics. Low real-world hit rate (writers follow naming rules), but defense-in-depth is cheap.
- **Action Required**: Replace with character classes — `"docs/**/20[0-9][0-9]-[0-1][0-9]-[0-3][0-9]-*.md"` (mirror in flat pattern if retained).

#### 4. [ACCEPT] [Medium] No test coverage for new INCLUDE/EXCLUDE branches
- **Critic**: Diff adds 4 pattern entries with no test; CI cannot catch findings #1 or #3.
- **Cross**: Echoes the same gap (suggests classifier tests for `docs/patterns/2026-*.md`).
- **Judgment**: Both reviewers converge. Code is data-table-driven and untested.
- **Action Required**: Add `tests/test_design_review_utils.py::test_is_design_doc_dated_patterns` covering: flat dated doc, nested dated doc, excluded `docs/work-items/...`, excluded `docs/참고/...`, excluded `docs/patterns/...`. The 참고/patterns assertions will fail until #1 is fixed — that's the regression net.

#### 5. [ACCEPT] [Low] Flat pattern `docs/20??-??-??-*.md` is redundant under custom matcher
- **Critic**: Traced `_matches_glob` (lines 102-119) — recursive pattern already covers the flat case at `i=0`. Comment ("flat/recursive 쌍을 모두 등록 ... 동일한 대칭") is misleading.
- **Cross**: Not flagged.
- **Judgment**: Correct trace. No bug; cosmetic/maintenance concern only.
- **Action Required**: Either drop the flat entry and update the comment, or keep it as stylistic mirroring of the keyword patterns and annotate as such.

---

### Cross's REJECTed item (not carried forward)
Cross self-rejected the `enqueue(review_type=...)` backward-compat concern after confirming `review_type: str = "design"` default keeps existing callers green. Confirmed against the diff — no aggregation needed.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Recursive dated-doc include captures `docs/참고/`, `docs/patterns/` | High | ACCEPT | Both (different dirs, same defect) |
| 2 | Work-item edits lose review trigger | High | ACCEPT | Cross |
| 3 | Date glob accepts non-digit chars | Medium | ACCEPT | Critic |
| 4 | No test coverage for new patterns | Medium | ACCEPT | Both |
| 5 | Flat pattern redundant under `_matches_glob` | Low | ACCEPT | Critic |

---

### Recommendations

1. **Same-PR fixes** (don't ship without these):
   - Add `docs/참고/**`, `docs/참고/*`, `docs/patterns/**`, `docs/patterns/*` to `EXCLUDE_PATTERNS`.
   - Decide work-item routing: re-include in `is_design_doc()` until the doc pipeline exists, or wire `is_work_item_doc()` + `review_type="document"` branch in `scripts/design_review_trigger.py:72-89`.
   - Add `tests/test_design_review_utils.py` with the 5-case matrix above.

2. **Tighten matcher** (same PR or fast-follow):
   - Swap `?` for `[0-9]`/`[0-1][0-9]`/`[0-3][0-9]` in date globs.

3. **Cosmetic** (optional):
   - Drop the redundant flat dated-doc entry or annotate as stylistic.