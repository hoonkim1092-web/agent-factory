# Code Review: checklist_merger

> Source: core/research/checklist_merger.py
> Date: 2026-05-07 17:28
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

WARN — No Critical findings. Four Medium and one High issue exist. All are contract violations (documented rules not enforced) or data-loss paths. Merge is possible with documented risks, but the High finding (silent data loss) and the two unenforced contract rules (Findings 2, 3) are strong candidates for a follow-up fix before this code handles production data.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Silent data loss for duplicate IDs from non-overlay sources

- **Critic**: "When `item.source` is `artifact_pack`/`capability_pack` and `item.id` already exists in `merged`, the item falls through both branches with no action — silently lost."
- **Cross**: "`QualityContractBuilder.build()` appends base, artifact, and capability packs sequentially — duplicate IDs across packs silently drop the later pack's `acceptance`, `priority`, `match_keywords`."
- **Judgment**: Both reviewers independently identified the same code path at `checklist_merger.py:29-34`. The `if/elif` logic only handles `domain_overlay` and `llm_addition`; any other source with a duplicate ID exits the `else` branch with no write. Given `QualityContractBuilder` stacks base → artifact → capability packs in order, an artifact pack that intentionally refines a base item via shared ID is silently ignored. This is confirmed data loss, not a hypothetical.
- **Action Required**: Either add an explicit `else: pass  # first-wins intentional for pack sources` with a `logging.warning(...)` call, or merge `acceptance`/`priority`/`match_keywords` from artifact/capability duplicates the same way overlays are handled. At minimum, add a `logger.warning` so the loss is observable.

---

#### 2. [ACCEPT] [Medium] `domain_overlay` can silently downgrade `required=True` on non-base items

- **Critic**: "The `llm_addition` guard only blocks downgrading when `existing.source == 'base_pack'`; `artifact_pack`/`capability_pack` items with `required=True` can have their `required` set to `False` by a domain overlay."
- **Cross**: Not flagged.
- **Judgment**: Single-reviewer, but the code evidence is strong. The guard at line 26-28 explicitly checks `existing.source != "base_pack"` before preserving `required`, meaning the protection is narrower than the docstring implies. The docstring rule 3 only mentions `llm_addition`, but the same logic should logically apply to all required items. This is accepted because the asymmetry is unambiguous in the diff and the risk (an overlay silently relaxing a contract rule) is real.
- **Action Required**: Decide intent and document it. If domain_overlay should respect `required=True` on all sources: change guard to `if existing.required and not item.required: continue`. If intentional for base-only: add docstring Rule 3b: "domain_overlay은 base_pack의 required=True만 보호한다."

---

#### 3. [ACCEPT] [Medium] `llm_addition` items accepted without `reason` (Rule 4 unenforced)

- **Critic**: "Class docstring states 'llm_addition은 reason 필드가 있어야 한다' but no assertion or check exists."
- **Cross**: "`QualityContractItem.reason` is marked required for `llm_addition` in `quality_contract.py:22`; a `QualityContractItem(source='llm_addition', reason='')` passes through unchanged."
- **Judgment**: Both reviewers found this. The contract is explicitly documented and the enforcement code is simply absent. `reason=""` is the default, so any caller that forgets to set it silently violates the rule. Cross review adds downstream context: missing `reason` degrades auditability of LLM-generated checklist additions.
- **Action Required**: Add validation before inserting any `llm_addition` item: `if item.source == "llm_addition" and not item.reason.strip(): raise ValueError(f"llm_addition item '{item.id}' missing required 'reason'")`.

---

#### 4. [ACCEPT] [Medium] `merge()` can return `[]` (Rule 5 unenforced)

- **Critic**: "`return list(merged.values())` can return `[]`; `QualityContractBuildError` exists for this case but is unused."
- **Cross**: "`core/researcher.py:971-975` trusts a non-`None` `QualityContract`; if `contract.checklist` is empty, `keywords_for_gap_check()` returns `[]` and the fallback at line 976 does not run."
- **Judgment**: Both reviewers found this; Cross adds concrete downstream impact — the researcher silently treats an empty contract as valid, bypassing its own fallback logic. This is a latent correctness bug, not just a contract violation.
- **Action Required**: Before `return`, add: `if not merged: raise QualityContractBuildError("ChecklistMerger produced an empty checklist")`. This triggers the existing fallback path in `researcher.py`.

---

#### 5. [ACCEPT] [Medium] `af.spec` hiddenimports missing for `core.research.*`

- **Critic**: "Per project rule M9, every new `core/*.py` must be added to `af.spec` hiddenimports. `core.research.checklist_merger`, `core.research.quality_contract`, `core.research.work_spec`, `core.research.__init__` all need entries."
- **Cross**: Not flagged (focused on runtime logic, not build config).
- **Judgment**: Single-reviewer, but this is a stated project rule (M9) with a known failure mode (silent crash in frozen builds). The `core/research/` directory is untracked/new per git status, confirming these modules are missing from build config. Accepted on rule-compliance grounds alone.
- **Action Required**: Add to `af.spec` hiddenimports: `'core.research'`, `'core.research.checklist_merger'`, `'core.research.quality_contract'`, `'core.research.work_spec'`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Silent data loss for non-overlay duplicate IDs | High | ACCEPT | Both |
| 2 | `domain_overlay` can downgrade non-base `required=True` | Medium | ACCEPT | Critic |
| 3 | `llm_addition` accepted without `reason` (Rule 4) | Medium | ACCEPT | Both |
| 4 | `merge()` can return `[]` (Rule 5) | Medium | ACCEPT | Both |
| 5 | `af.spec` hiddenimports missing for `core.research.*` | Medium | ACCEPT | Critic |

---

### Recommendations

- **Fix first (before production data)**: Finding 1 (silent data loss) and Findings 3+4 (unenforced contract rules) — these are the three issues most likely to produce wrong output silently.
- **Finding 2**: Resolve by documentation or code — either path is acceptable, but the current state is ambiguous.
- **Finding 5**: Add `af.spec` entries in the same commit that introduces `core/research/` to prevent frozen-build crashes on the next release.
- Cross review confirmed 14 tests pass; the existing test suite does not cover the empty-result path or `llm_addition` reason validation — add focused unit tests for both when fixing Findings 3 and 4.