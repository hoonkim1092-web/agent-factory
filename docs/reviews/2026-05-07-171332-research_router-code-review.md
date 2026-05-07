# Code Review: research_router

> Source: core/research_router.py
> Date: 2026-05-07 17:13
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High-severity false-positive risk in substring matching, plus a medium-severity escalation data-loss issue. No Critical findings; can merge with documented risks if accepted.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] Substring matching causes false positives for common English tokens
- **Critic**: "`"turn"` matches `"return"/"tournament"`, `"river"` matches `"driver"/"delivered"`, `"ante"` matches `"antenna"/"antecedent"` — any research request containing these substrings is misrouted to the poker domain."
- **Cross**: Not flagged.
- **Judgment**: Evidence is concrete and diff-traceable. `core/research_router.py:263` changed `tok in words` (exact word-set membership) to `tok in text_lower` (substring scan). The three tokens above are frequent English substrings. A query like `"anticipate user turn-over rate"` now returns `domain="poker"`, triggering the poker checklist overlay downstream (`project_pipeline.py:896`).
- **Action Required**: Restore word-boundary semantics. Either revert Change 2 entirely (see Finding 2), or for CJK tokens that require substring matching use a split approach:
  ```python
  import re
  def _detect_domain(self, request: str) -> str:
      text_lower = (request or "").lower()
      for tok in self._POKER_TOKENS:
          if tok.isascii():
              if re.search(r'\b' + re.escape(tok) + r'\b', text_lower):
                  return "poker"
          else:
              if tok in text_lower:
                  return "poker"
      return ""
  ```

---

#### 2. [ACCEPT] [Medium] Change 2 is a regressive rewrite — Change 1 alone fixes the original bug
- **Critic**: "Python 3 `\w` is Unicode-aware. `re.findall(r\"[\\w']+\", \"홀덤 포커\")` → `[\"홀덤\", \"포커\"]`. The `"홀덤"` miss was caused by the token not being in `_POKER_TOKENS`, not by the tokenizer. Change 1 (`"홀덤"` addition) fully resolves the bug."
- **Cross**: Not flagged.
- **Judgment**: Verifiable by inspection — Python 3 `re` uses `re.UNICODE` by default and `\w` matches `[a-zA-Z0-9_]` plus Unicode word characters including Hangul. The root cause of the original bug was a missing token, not a tokenizer limitation. Change 2 introduces new risk (Finding 1) without fixing anything Change 1 doesn't already fix.
- **Action Required**: Roll back Change 2 and keep Change 1. If the ASCII/CJK split from Finding 1 is adopted instead, remove the now-unused `import re` inside the function and hoist it to module level.

---

#### 3. [ACCEPT] [Medium] Escalation path drops router signal scores from the final research plan
- **Critic**: Not flagged.
- **Cross**: "When `detect_complexity_gaps()` escalates, the recursive `collect_project_evidence()` call does not pass the original `research_plan`. The callee creates `ResearchPlan.for_mode(escalated_mode)` with `scores=None`, so `scores={}` in the serialized plan. `project_pipeline.py:890` injects this into `project_brief`, losing the signal data that caused escalation."
- **Judgment**: Cross provides a concrete call chain: `researcher.py:1060` (recursive call) → `research_router.py:94` (`scores` defaults to `{}`) → `researcher.py:1048` (serialization) → `project_pipeline.py:890` (injection). This is outside the diff but is a pre-existing gap exposed by the D3 escalation changes. Strong evidence with file+line citations.
- **Action Required**: In `collect_project_evidence()`, pass the current `research_plan` into the recursive call, or preserve `scores` from the initial plan when constructing the escalated `ResearchPlan`:
  ```python
  escalated_plan = ResearchPlan.for_mode(
      escalated_mode,
      scores=initial_plan.scores,  # preserve signal data
      secondary_modes=initial_plan.secondary_modes,
  )
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Substring matching → false positive domain detection | High | ACCEPT | Critic |
| 2 | Change 2 is unnecessary regression (regex handles CJK) | Medium | ACCEPT | Critic |
| 3 | Escalation drops router scores from final research plan | Medium | ACCEPT | Cross |

---

### Recommendations

- **Must fix before shipping**: Revert the `tok in text_lower` substring switch (Finding 2) OR apply the ASCII/CJK split guard (Finding 1). Both resolve the same root problem; pick one.
- **Keep Change 1 (`"홀덤"` addition)**: This is the correct, minimal fix for the original bug.
- **Address Finding 3 separately**: The escalation score-drop is a pre-existing gap, not introduced by this diff. File a follow-up ticket and fix in the `collect_project_evidence()` recursive call path.
- **Module-level `import re`**: If regex is retained, move the import to the top of the file (currently it was inside the function body — removing it was directionally correct, but only if regex is truly eliminated).