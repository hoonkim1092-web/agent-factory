# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-07 17:42
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

One Critical finding (confirmed test regression) + three High findings. Must fix before merge.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [Critical] `keywords_for_gap_check()` flat list → exponential recovery searches

- **Critic**: "not flagged"
- **Cross**: `keywords_for_gap_check()` returns every keyword across all items as a flat list. `_identify_unmet_gaps()` treats each entry as an independently required gap. One item with `match_keywords=["requirements","specification","scope"]` generates 3 separate required gaps. **Confirmed test regression**: `test_b1_max_rounds_cap` — web calls reached `190`, expected `<= 16`.
- **Judgment**: Only cross flagged it, but the evidence is decisive — an existing regression test fails. The architectural mismatch is confirmed: `match_keywords` was designed as *alternatives for one item*, not as *independent checklist items*.
- **Action Required**: Change `keywords_for_gap_check()` to return one representative string per `ChecklistItem` (e.g., `item.id`), or change `_identify_unmet_gaps()` to treat an item as matched when *any* of its `match_keywords` is present. The flat-keyword approach must not be used as input to a per-keyword gap check.

---

#### 2. [ACCEPT] [High] `except Exception: return None` — silent swallow + intent gap from dead import

- **Critic**: `_build_quality_contract()` L614 swallows all exceptions including API errors, rate limits, and `AttributeError` with no log trace. Callers cannot distinguish "no packs available" from "LLM call failed." Repeats H3 pattern. `QualityContractBuildError` is imported at L602 but never appears in the function body — the unused import is evidence the author intended `except QualityContractBuildError: return None` as the expected path.
- **Cross**: "not flagged"
- **Judgment**: Code evidence is unambiguous. The bare `except` silently drops every error class. The dead import makes the intent gap self-documenting.
- **Action Required**: Either use `except QualityContractBuildError: return None` for the expected path and re-raise (or log + return `None`) for others; or add `logging.getLogger(__name__).warning(...)` before `return None` and remove the dead import.

---

#### 3. [ACCEPT] [High] `ChecklistMerger.merge()` can return `[]`, silently bypassing fallback

- **Critic**: If every YAML entry has `id=""` or `id` absent, L19 `if not item.id: continue` skips all items and `merge()` returns `[]`. At the call site, `_quality_contract is None` is `False` (QC object exists), so the condition `if _quality_contract is None and not _domain_checklist:` never triggers. The hardcoded fallback is unreachable. Gap checking is silently disabled.
- **Cross**: "not flagged"
- **Judgment**: The docstring explicitly states Rule 5 ("최종 체크리스트는 반드시 비어 있지 않아야 한다"), which is unimplemented. The logic path from non-empty YAML input → empty `merge()` output → silent gap-check skip is a real scenario (mismatched domain, absent `id` keys in pack YAML).
- **Action Required**: Two options: (A) enforce in `merge()` — raise `QualityContractBuildError` when result is empty; (B) fix the caller condition to `if not _domain_checklist:` (removing the `_quality_contract is None` guard), so the hardcoded fallback triggers even when a QC object exists but returned an empty checklist.

---

#### 4. [ACCEPT] [High] Domainless `QualityContract` failures invisible to downstream gate

- **Critic**: "not flagged"
- **Cross**: `_emit_coverage_report()` returns `{}` when `domain == ""`. `ProjectPipeline` enforces coverage only when `project_brief["research_plan"]["domain"]` is set. A domainless contract can return `unmet_gaps=["game loop"]` with no `coverage_report`, making the new contract signal invisible to the rest of the pipeline.
- **Judgment**: Cross provided specific file and line evidence (`core/researcher.py:724`, `core/project_pipeline.py:895-929`). The gap between QualityContract producing signals and the pipeline gate acting on them is a structural issue introduced by this diff.
- **Action Required**: Emit a general quality-contract report even when `domain == ""`, or add a separate `quality_contract_report` / `quality_contract_block` field that `ProjectPipeline` enforces independently of domain-spec coverage.

---

#### 5. [ACCEPT] [Medium] LLM call in recovery loop hot path has no timeout guard

- **Critic**: `WorkSpecExtractor.extract()` is a synchronous LLM call on every `archive_research` invocation. Prior code path (`_load_domain_manifest`) was a pure YAML read. No timeout guard visible in `execute_requirement_prompt`. Combined with Finding 2's silent swallow, a hung LLM call stalls the pipeline with no error surfaced.
- **Cross**: "not flagged"
- **Judgment**: The concern is architectural — a new LLM call was introduced into a hot path without timeout guarantees. Severity is Medium because it degrades rather than corrupts.
- **Action Required**: Verify `execute_requirement_prompt` has internal timeout, or wrap the call with a deadline.

---

#### 6. [ACCEPT] [Medium] Magic string fallback checklist — no named constant

- **Critic**: `_domain_checklist = ["requirements_coverage", "architecture_rationale"]` at L978. Two bare string literals with no comment explaining the choice. Repeats M4 pattern (magic-number anti-pattern from code-review.md).
- **Cross**: "not flagged"
- **Judgment**: Low blast radius but a documented repeat pattern.
- **Action Required**: `_DEGRADED_CHECKLIST = ["requirements_coverage", "architecture_rationale"]` at module level; reference the constant at L978.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Keyword flattening → recovery regression (190 calls) | Critical | ACCEPT | Cross |
| 2 | Silent `except Exception` + dead import intent gap | High | ACCEPT | Critic |
| 3 | `merge()` empty result bypasses fallback silently | High | ACCEPT | Critic |
| 4 | Domainless QC invisible to downstream gate | High | ACCEPT | Cross |
| 5 | LLM call in hot path without timeout | Medium | ACCEPT | Critic |
| 6 | Magic string fallback checklist | Medium | ACCEPT | Critic |

---

### Recommendations

1. **Fix #1 first** — it is the only confirmed test regression and determines whether the keyword API contract is item-level or keyword-level. Fixing it will likely change how #3 should be fixed.
2. **Fix #2 and #3 together** — both are in `_build_quality_contract` / `ChecklistMerger`. The dead import removal and the empty-checklist guard are a natural single commit.
3. **Fix #4** — structural gap between QC signal and pipeline gate; requires changes in `_emit_coverage_report` or `ProjectPipeline`.
4. **#5 and #6** can be deferred post-BLOCK fixes, but address before next milestone.
5. After fixes: re-run `pytest tests/test_research_system_regression.py` to verify `test_b1_max_rounds_cap` passes at ≤ 16 web calls.