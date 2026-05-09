# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-07 17:37
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Reason: Cross Review confirmed a regression test failure (`test_b1_max_rounds_cap_preventsInfiniteLoop`): 190 web calls vs expected ≤ 16. A broken regression cap on a loop that guards against infinite execution is a pre-merge blocker regardless of other severity levels.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] Silent `except Exception` swallows all failures and blocks pipeline gate signaling
- **Critic**: "Every exception collapses silently to `None`; caller cannot distinguish degradation from a bug. Same H3 pattern fixed in `ise_redesigner.py`."
- **Cross**: "When `_build_quality_contract()` returns `None`, `_emit_coverage_report()` returns `{}` and `_coverage_blocked()` never sees a blocking signal; degraded path is informational only."
- **Judgment**: Both reviewers flag the same failure mode from different angles — Critic targets exception granularity, Cross targets the downstream gate consequence. Combined, the issue is: a structural build failure (wrong domain YAML, bad merge result, missing module) silently produces `None`, and nothing downstream signals a block. Code evidence: diff line `except Exception: return None` with no logging, and `_coverage_blocked()` at `core/project_pipeline.py:277` only checks `coverage_report.block`.
- **Action Required**:
  ```python
  except (QualityContractBuildError, ValueError):
      return None  # expected degraded path
  except Exception as e:
      logging.getLogger(__name__).warning("_build_quality_contract unexpected failure: %s", e)
      return None
  ```
  And in the `_quality_contract is None` branch, emit `coverage_report={"block": True, "reason": "quality_contract_build_failed"}` or teach `_coverage_blocked()` to treat `quality_contract_status=="degraded"` as blocking.

---

#### 2. [ACCEPT] [High] Flattened keywords break recovery loop cap — regression test fails
- **Critic**: "not flagged"
- **Cross**: "`keywords_for_gap_check()` flattens every `match_keywords` synonym as an independent checklist item. A 23-item contract produced 134 gap-check strings; regression test `test_b1_max_rounds_cap_preventsInfiniteLoop` failed: 190 web calls, expected ≤ 16."
- **Judgment**: ACCEPT unconditionally — this is a confirmed test failure on a loop-cap regression guard. The root cause is at `core/research/quality_contract.py:51` where keywords are flattened before being returned by `keywords_for_gap_check()`. Evidence: concrete pytest output from Cross Review verification run.
- **Action Required**: `_identify_unmet_gaps()` must receive grouped contract items (one entry per checklist item, not per synonym). `keywords_for_gap_check()` should return one identifier per item with its synonyms as match alternatives, not a flat list. Add a per-round web-call cap.

---

#### 3. [ACCEPT] [High] Non-None contract with empty checklist bypasses hardcoded fallback
- **Critic**: "Guard is `_quality_contract is None and not _domain_checklist` — if contract is not None but `keywords_for_gap_check()` returns `[]`, the condition is False; fallback never reached; `_domain_checklist = []` → `_identify_unmet_gaps()` returns no gaps → recovery loop exits immediately."
- **Cross**: "not flagged explicitly, but Finding #1 describes the empty path; tied to the known merge-empty-list bug."
- **Judgment**: ACCEPT — evidence is direct from the diff:
  ```python
  if _quality_contract is None and not _domain_checklist:   # ← guard tied to identity, not content
      _domain_checklist = ["requirements_coverage", "architecture_rationale"]
  ```
  If `_quality_contract` is not `None` and `merge()` produces an empty list (known bug), the fallback silently does nothing and the entire gap-check loop becomes a no-op.
- **Action Required**: Decouple guard from contract identity:
  ```python
  if not _domain_checklist:
      _domain_checklist = ["requirements_coverage", "architecture_rationale"]
  ```

---

#### 4. [ACCEPT] [Medium] QualityContract is skipped for the highest-impact research modes
- **Critic**: "not flagged"
- **Cross**: "`_build_quality_contract()` only runs in the final `else` branch. Any plan with `requires_web=True` bypasses it entirely — those are exactly fresh/deep/live modes most likely to need quality checks."
- **Judgment**: ACCEPT — the diff confirms `_build_quality_contract()` is added only inside the `else` block at line 970. `ResearchRouter.plan()` sets `requires_web=True` for fresh/deep/live modes, meaning the new Phase 5 path is structurally dead for the highest-value use cases. Design gap with clear code evidence.
- **Action Required**: Build the quality contract before the mode branch when `research_plan.domain` is present; use it for final gap/coverage evaluation in both `requires_web` and recovery-loop paths.

---

#### 5. [ACCEPT] [Medium] `QualityContractBuildError` is imported but never caught
- **Critic**: "Imported alongside `QualityContractBuilder` but never referenced — not caught, not re-raised, not type-checked. Signals intent that isn't implemented."
- **Cross**: "not flagged"
- **Judgment**: ACCEPT — the diff clearly shows `from core.research.quality_contract import QualityContractBuilder, QualityContractBuildError` with `QualityContractBuildError` unused in the method body. Once Finding #1's fix lands, this becomes the intended catch target; until then it is misleading dead code.
- **Action Required**: Either remove from import, or add `except QualityContractBuildError: return None` as part of Finding #1's fix.

---

#### 6. [ACCEPT] [Medium] Four new `core/research/` modules likely absent from `af.spec` hiddenimports
- **Critic**: "In a frozen build, lazy `from core.research.work_spec import ...` inside the `try` block raises `ModuleNotFoundError` — silently caught by `except Exception: return None` — entire Phase 5 becomes a no-op in production without any error surfacing."
- **Cross**: "not flagged"
- **Judgment**: ACCEPT — known M9 pattern from `code-review.md`. Git status shows all four files as newly added (`A`). The interaction with Finding #1's bare except means the frozen build silently degrades; the feature ships but does nothing in `dist/af.exe`.
- **Action Required**: Add to `af.spec` hiddenimports:
  ```python
  'core.research',
  'core.research.work_spec',
  'core.research.quality_contract',
  'core.research.checklist_merger',
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Silent exception + no pipeline gate signal | High | ACCEPT | Both |
| 2 | Flattened keywords break loop cap (regression) | High | ACCEPT | Cross |
| 3 | Empty checklist bypasses fallback guard | High | ACCEPT | Critic |
| 4 | QualityContract skipped for `requires_web` modes | Medium | ACCEPT | Cross |
| 5 | `QualityContractBuildError` dead import | Medium | ACCEPT | Critic |
| 6 | `core/research/*` absent from `af.spec` | Medium | ACCEPT | Critic |

---

### Recommendations

- **Before merge (BLOCK)**: Fix Finding #2 first — it breaks an existing regression cap test. The fix must change how `keywords_for_gap_check()` output is consumed by `_identify_unmet_gaps()`, not just add a cap.
- **Bundle with #2 fix**: Apply Finding #3's guard change (`if not _domain_checklist:`) since it's a one-line surgical fix.
- **Bundle with #1 fix**: Narrow the `except` clause and add the degraded gate signal in the same commit; import cleanup (#5) comes for free.
- **Separate commit**: Add `core/research/*` to `af.spec` hiddenimports (#6) — build-only change, no logic risk.
- **Design follow-up (#4)**: The `requires_web=True` bypass is a structural gap; address in a dedicated design + implementation pass, not as a hotfix.