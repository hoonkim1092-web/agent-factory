# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-07 17:37
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Three High-severity issues will silently degrade or bypass intended behavior without raising exceptions. All are fixable with small, targeted changes.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] Silent `except Exception` makes build failures invisible

- **Critic**: "Every failure — ImportError, AttributeError, TypeError — silently returns None. No logging at any level. `QualityContractBuildError` is imported but never caught."
- **Cross**: Not explicitly flagged but acknowledged: "I intentionally did not repeat the already-recorded critic findings around silent exception swallowing."
- **Judgment**: Clear code evidence at `core/researcher.py:615-617`. Any programming error in `WorkSpecExtractor`, `QualityContractBuilder`, or `ChecklistMerger` silently degrades to the domain manifest fallback. `QualityContractBuildError` import at line 604 confirms the intent to catch it specifically was never completed.
- **Action Required**: Catch `QualityContractBuildError` explicitly; log unexpected exceptions before swallowing:
  ```python
  except QualityContractBuildError:
      return None
  except Exception:
      logger.warning("_build_quality_contract failed unexpectedly", exc_info=True)
      return None
  ```

#### 2. [ACCEPT] [High] Empty-keywords guard is too narrow — `_domain_checklist = []` bypasses hardcoded fallback

- **Critic**: "If `_quality_contract` is not None but `keywords_for_gap_check()` returns `[]`, `_domain_checklist` is `[]` and the guard `if _quality_contract is None and not _domain_checklist` is never entered."
- **Cross**: Not flagged.
- **Judgment**: The diff at `core/researcher.py:972-976` shows the condition is `_quality_contract is None and not _domain_checklist`. If the contract exists but returns an empty keyword list, the recovery loop runs with an empty checklist, `_identify_unmet_gaps()` returns nothing, and the loop exits as if all evidence is satisfied — silent short-circuit. Evidence is unambiguous from code structure.
- **Action Required**: Widen the guard to check only the list value:
  ```python
  if not _domain_checklist:
      _domain_checklist = ["requirements_coverage", "architecture_rationale"]
  ```

#### 3. [ACCEPT] [High] QualityContract blocks can be bypassed when `domain == ""`

- **Critic**: Not flagged.
- **Cross**: "A domainless archive plan can return `sufficiency_gate_passed=False` and `unmet_gaps_count=13` while `coverage_report_present=False`, so `ProjectPipeline._coverage_blocked()` returns `False`."
- **Judgment**: Cross verified through `core/project_pipeline.py:924` that the pipeline only blocks on `coverage_report.block`. Since `_emit_coverage_report()` at `core/researcher.py:724` returns `{}` when `domain == ""`, a failing QualityContract check with unmet gaps passes the pipeline gate. Cross verified the B1 integration test patches `_emit_coverage_report` to `{}` — the test itself masks this defect. Strong evidence, single reviewer but definitively traced.
- **Action Required**: When `_quality_contract` is present, emit a coverage report with `domain="general"` (or `"quality_contract"`) rather than relying on `research_plan.domain`. Ensure `block`, `missing`, and `match_rate` fields are populated so `ProjectPipeline._coverage_blocked()` can act on them.

#### 4. [ACCEPT] [Medium] `QualityContractBuildError` import is dead code

- **Critic**: "Imported at line 604, never referenced. Signals intent that was never implemented."
- **Cross**: Not flagged.
- **Judgment**: Import is visible in the diff (`from core.research.quality_contract import QualityContractBuilder, QualityContractBuildError`). Since Finding #1 already requires adding the specific catch clause, these two fixes must be applied together.
- **Action Required**: Fix simultaneously with Finding #1 — add the `except QualityContractBuildError` clause, making the import live.

#### 5. [ACCEPT] [Medium] Magic strings in hardcoded fallback checklist

- **Critic**: "No indication why `requirements_coverage` and `architecture_rationale` were chosen or what they map to in the gap-check system."
- **Cross**: Not flagged.
- **Judgment**: The diff shows `_domain_checklist = ["requirements_coverage", "architecture_rationale"]` at line 977 with no named constant or comment. Matches the established pattern M4 from the review checklist. Once Finding #2 is fixed, this fallback becomes reachable in more cases, increasing the maintenance surface.
- **Action Required**: Extract to a module-level constant:
  ```python
  _FALLBACK_GAP_KEYWORDS = ["requirements_coverage", "architecture_rationale"]
  ```

#### 6. [ACCEPT] [Low] Inconsistent defensive reads for `research_plan.domain`

- **Critic**: "New path uses `getattr(research_plan, 'domain', '') or ''` — defensive. Fallback path uses `self._load_domain_manifest(research_plan.domain)` — direct access."
- **Cross**: Not flagged.
- **Judgment**: Pre-existing asymmetry, not introduced by this diff. Low priority; no action needed now.
- **Action Required**: None required. Document the asymmetry in a comment if the function is touched again.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Silent `except Exception` swallows all build failures | High | ACCEPT | Critic (Cross confirmed) |
| 2 | Empty-keywords guard too narrow — `[]` checklist bypasses fallback | High | ACCEPT | Critic |
| 3 | QualityContract block bypassed when `domain == ""` | High | ACCEPT | Cross |
| 4 | `QualityContractBuildError` import is dead code | Medium | ACCEPT | Critic |
| 5 | Magic strings in hardcoded fallback checklist | Medium | ACCEPT | Critic |
| 6 | Inconsistent defensive reads for `research_plan.domain` | Low | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 + #4 together**: Add `except QualityContractBuildError: return None` and `except Exception: logger.warning(..., exc_info=True)` — this makes the dead import live and removes the invisible failure mode in one edit.
- **Fix #2**: Change `if _quality_contract is None and not _domain_checklist:` → `if not _domain_checklist:` — one-line change, high impact.
- **Fix #3**: When `_quality_contract` is not None, construct a real coverage report using a sentinel domain (`"general"`) so `ProjectPipeline._coverage_blocked()` can act on it. Add a test that runs with `research_plan.domain == ""` and asserts the pipeline blocks when `unmet_gaps > 0`.
- **Fix #5**: Extract `_FALLBACK_GAP_KEYWORDS` constant — do this as part of the Fix #2 edit.
- **Fix #6**: No action now; note the asymmetry in a comment if the function is edited again.
- The B1 integration test currently patches `_emit_coverage_report` to `{}` — update or add a complementary test that does not patch it to catch the domain-empty bypass (Finding #3).