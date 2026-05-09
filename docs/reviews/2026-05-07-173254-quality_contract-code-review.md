# Code Review: quality_contract

> Source: core/research/quality_contract.py
> Date: 2026-05-07 17:32
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Cross Finding #1 provides concrete test-failure evidence: `test_b1_max_rounds_cap` triggers 148 web calls against an expected ≤16 cap — an existing regression caused by this diff's interface boundary.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [Critical] `keywords_for_gap_check()` synonym explosion breaks B1 regression test
- **Critic**: "not flagged"
- **Cross**: "`keywords_for_gap_check()` flattens every `match_keywords` synonym into one list; callers treat each element as an independent required gap. `test_b1_max_rounds_cap` fails: expected web calls ≤16, actual 148."
- **Judgment**: Sole Cross finding, but the test-failure evidence is definitive — this diff actively broke an existing regression guard. A poker contract yields ~95 keywords from 16 items; `researcher.py:971-984` passes that list into `_is_sufficient()` / `_identify_unmet_gaps()` unchanged, multiplying recovery iterations by 6×.
- **Action Required**: Return structured data from `keywords_for_gap_check()` — either `dict[str, list[str]]` (item_id → keywords) so callers can match `any(kw in text)` per item, or return `QualityContractItem` objects directly. Caller-side loop must iterate items, not flattened keywords.

---

#### 2. [ACCEPT] [High] Optional items promoted into mandatory coverage / recovery gates
- **Critic**: "not flagged"
- **Cross**: "`keywords_for_gap_check()` ignores `required_items()` helper; `test_strategy`, `edge_case_rules`, `concurrency_handling` become part of the 70% sufficiency threshold at `researcher.py:807-814` and the `block` signal at `researcher.py:741-748`."
- **Judgment**: Sole Cross finding, but the code path is traced precisely. `QualityContract.required_items()` exists specifically to distinguish mandatory from optional; bypassing it inflates the mandatory coverage bar with items that should only appear in the report.
- **Action Required**: In `researcher.py`, replace `qc.keywords_for_gap_check()` with a construct based on `qc.required_items()` for all coverage threshold and gap-recovery inputs. Optional items may remain in `_emit_coverage_report()` for diagnostic output only.

---

#### 3. [ACCEPT] [High] `_PACKS_DIR` frozen-build incompatibility (`__file__` pattern)
- **Critic**: "`quality_contract.py:67` — `Path(__file__).parent / 'packs'` fails in PyInstaller freeze; `packs/*.yaml` not in `af.spec` datas → `_load_pack()` returns `[]` → silent Phase 5 deactivation. Matches known C2 pattern."
- **Cross**: "not flagged"
- **Judgment**: Critic-only, but matches the documented C2 recurrence pattern and the code path is unambiguous. `af.spec` has no `datas` entry for `core/research/packs`.
- **Action Required**:
  ```python
  import sys
  _HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
  _PACKS_DIR = _HERE / "core" / "research" / "packs"
  ```
  Add `('core/research/packs', 'core/research/packs')` to `af.spec` `datas`.

---

#### 4. [ACCEPT] [High] `af.spec` hiddenimports missing new research modules
- **Critic**: "`core.research.work_spec`, `core.research.quality_contract`, `core.research.checklist_merger` absent from `af.spec` hiddenimports. Lazy imports inside `try` blocks are not traced by PyInstaller → `ImportError` → `except Exception: return None` → silent degradation. Matches known M9 debt."
- **Cross**: "not flagged"
- **Judgment**: Critic-only, but the rule is explicit in CLAUDE.md: "새 `core/*.py` 파일은 `af.spec` hiddenimports에 반드시 추가." Three new modules were added; none are in the spec.
- **Action Required**: Add to `af.spec` hiddenimports:
  ```
  'core.research.work_spec',
  'core.research.quality_contract',
  'core.research.checklist_merger',
  ```

---

#### 5. [ACCEPT] [Medium] User input `str.format()` injection in `work_spec.py`
- **Critic**: "`work_spec.py:59` — `self._PROMPT.format(request=request)` raises `KeyError`/`ValueError` when `request` contains literal `{`/`}`. Silently swallowed by `except Exception: return None`. Poker-domain input (`{bluff}`, `{call}`) reliably triggers this."
- **Cross**: "not flagged"
- **Judgment**: Critic-only, but the failure mode is exact and reproducible for the project's primary target domain (홀덤).
- **Action Required**:
  ```python
  prompt = self._PROMPT.format(request=request.replace("{", "{{").replace("}", "}}"))
  ```

---

#### 6. [ACCEPT] [Medium] Bare `except Exception: return None` — silent Phase 5 deactivation
- **Critic**: "`researcher.py:613` — absorbs `ImportError`, `AttributeError`, `yaml.YAMLError`, `QualityContractBuildError` with no log. Identical to H3 pattern (ise_redesigner silent fallback)."
- **Cross**: "not flagged"
- **Judgment**: Critic-only, but the H3 precedent is documented in code-review.md and the path is clear. Findings #3–5 above all collapse into this sink undetectably.
- **Action Required**:
  ```python
  except Exception as e:
      logger.debug("_build_quality_contract failed, degrading: %s", e)
      return None
  ```

---

#### 7. [HOLD] [Low] `_detect_domain` deprecated wrapper — caller in `researcher.py` not updated
- **Critic**: "`researcher.py:928` still calls `ResearchRouter()._detect_domain()` directly; deprecated wrapper cannot be removed until that caller is updated to `_detect_domain_hints()`."
- **Cross**: "not flagged"
- **Judgment**: Critic-only, low severity. Fix is one-line, but it touches `researcher.py` which has active churn. Safe to defer unless a separate PR touches that path.
- **Question for Author**: Is `_detect_domain_hints()` a drop-in replacement for all existing callers, or does the return-type differ?

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `keywords_for_gap_check()` synonym explosion — B1 test fails | Critical | ACCEPT | Cross |
| 2 | Optional items in mandatory coverage gates | High | ACCEPT | Cross |
| 3 | `_PACKS_DIR` frozen-build `__file__` | High | ACCEPT | Critic |
| 4 | `af.spec` hiddenimports missing | High | ACCEPT | Critic |
| 5 | `str.format()` injection in `work_spec.py` | Medium | ACCEPT | Critic |
| 6 | Silent `except Exception: return None` | Medium | ACCEPT | Critic |
| 7 | `_detect_domain` deprecated wrapper leftover | Low | HOLD | Critic |

---

### Recommendations

- **Must fix before merge**: Finding #1 (broken test), Finding #2 (optional/required gate confusion) — these are interface contract bugs introduced by this diff.
- **Must fix for frozen build**: Findings #3 and #4 — CLAUDE.md explicitly requires `af.spec` updates for every new `core/*.py`; this is overdue.
- **Fix in same PR**: Finding #5 (format injection) and #6 (add debug log to silent catch) — both are single-line changes that protect the same code path.
- **Defer**: Finding #7 — track in `NEXT_STEPS.md`, fix when `researcher.py:928` area is next touched.