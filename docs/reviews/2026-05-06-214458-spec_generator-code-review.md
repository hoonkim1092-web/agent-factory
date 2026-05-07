# Code Review: spec_generator

> Source: core/spec_generator.py
> Date: 2026-05-06 21:44
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High-severity findings exist in `core/spec_generator.py` and `core/project_pipeline.py`. The C3/C4 implementation produces structurally incorrect ADR and traceability documents without any error signal. No finding reaches explicit Critical, but findings #1–#4 together represent a correctness-critical cluster that must be fixed before the output is trusted downstream.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] Silent exception swallowing produces authoritative-looking fallback documents
- **Critic**: `except Exception: pass` in `_call_llm` (line 114–115) and `_call_llm_raw` (line 127–128) swallows all errors silently
- **Cross**: `_call_llm_raw()` exceptions are swallowed; ADR generation returns an "Accepted" fallback decision written as authoritative by `project_pipeline.py:879`
- **Judgment**: Both reviewers independently flag the same lines. Cross reviewer adds the downstream consequence: the pipeline writes the fallback ADR without marking it as a placeholder, so consumers cannot distinguish a real decision from a silent failure. This is the pattern already catalogued in `docs/reviews/2026-05-06-193949-spec_generator-code-review.md` but now affecting decision records.
- **Action Required**: `except Exception as e: logger.warning("spec LLM call failed: %s", e)`. Fallback ADRs must carry `Status: Proposed` (not `Accepted`) or be skipped entirely when no LLM output exists.

---

#### 2. [ACCEPT] [High] ADR/traceability reads wrong evidence file → `claims=[]`, `sources=[]`
- **Critic**: not flagged
- **Cross**: `_load_evidence(target_workspace, slug)` derives slug from `slug_from_brief(project_brief)`, but the researcher writes evidence files using `safe_id(task_input)[:40]`. When `goal` ≠ `task_input`, C3/C4 silently get empty evidence.
- **Judgment**: Single-reviewer but strong code evidence — two different slug functions at researcher write-path (`researcher.py:1069`) and pipeline load-path (`project_pipeline.py:233`). Structural mismatch means the happy path only works when `goal == task_input` verbatim. All other cases produce silent empty-evidence documents.
- **Action Required**: Either (a) pass evidence from `prepared_brief.research_evidence` directly into ADR/traceability generation, or (b) standardize the B4 evidence filename to use the same `slug_from_brief()` slug that P2 artifacts use.

---

#### 3. [ACCEPT] [High] `_match_task` falls back to `tasks[0]` — false traceability
- **Critic**: `return tasks[0].get("task_id", "T001") if tasks else "T001"` (line 261) maps any unmatched claim to the first task regardless of relevance
- **Cross**: `_match_task()` searches `description`/`name` but project board tasks use `task_id`, `title`, `instruction`. No match ever fires → every claim lands on `tasks[0]`
- **Judgment**: Agreed by both reviewers; Cross adds that the field mismatch makes the fallback the *default path*, not the exception. Traceability tables are structurally incorrect for the vast majority of claims.
- **Action Required**: Match against `instruction`, `title`, `acceptance`, `module_id`, `owner_role`. Emit `"UNMAPPED"` (not `tasks[0]`) on failure so verification tooling can catch it.

---

#### 4. [ACCEPT] [High] `_match_spec` false default + missing section anchors
- **Critic**: `best_score=0` start means unmatched claims always map to `"rules-spec.md"` (line 249–254) — wrong traceability
- **Cross**: `_match_spec()` returns only filenames (e.g., `rules-spec.md`) but the design contract requires anchored references (`rules-spec.md#betting-rounds`); D2 requires anchors to resolve to real headers
- **Judgment**: Critic catches the incorrect default; Cross catches the missing anchor depth. Both address `_match_spec` inadequacy and are merged. Combined impact: every unmatched claim silently maps to `rules-spec.md` with no section, satisfying no part of the traceability contract.
- **Action Required**: (a) Return `"UNMAPPED"` when `best_score == 0`. (b) Return `<filename>#<section-slug>` instead of bare filenames, or parse generated spec headers and map claims to real anchors.

---

#### 5. [ACCEPT] [Medium] `_call_llm` duplicates `_call_llm_raw`
- **Critic**: Both methods are identical in logic; `_call_llm` never uses `self`; bug fixes require changes in two places
- **Cross**: not flagged
- **Judgment**: The code evidence is clear — lines 106–116 and 119–129 are structurally identical. Medium severity (no correctness impact now, but maintenance hazard as the silent-exception fix from finding #1 must be applied twice).
- **Action Required**: Delegate `_call_llm` to `_call_llm_raw(prompt, f"# {title}\n\n(spec generation unavailable)\n")`.

---

#### 6. [ACCEPT] [Medium] `__import__("datetime")` inline pattern
- **Critic**: Line 140 uses `__import__("datetime").date.today().isoformat()`; reduces IDE discoverability and may bypass PyInstaller `hiddenimports` auto-detection in frozen builds
- **Cross**: not flagged
- **Judgment**: Single-reviewer. The correctness risk is build-environment specific (PyInstaller frozen builds), but the pattern is clearly non-idiomatic. Low effort to fix.
- **Action Required**: Add `import datetime` at the module top; replace with `datetime.date.today().isoformat()`.

---

#### 7. [ACCEPT] [Medium] Magic slice constants `5`, `8`, `6` with no rationale
- **Critic**: `sources[:5]`, `claims[:8]`, `claims[:6]` appear in `_format_evidence` and `_fallback_adr` with no explanation for why they differ
- **Cross**: not flagged
- **Judgment**: Single-reviewer, clear code evidence. Different limits for the same data in two paths will produce inconsistent outputs. Low risk but non-obvious.
- **Action Required**: Extract module-level constants `_MAX_EVIDENCE_SOURCES = 5`, `_MAX_EVIDENCE_CLAIMS = 8` and document the distinction (or unify).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Silent exception → authoritative fallback ADR | High | ACCEPT | Both |
| 2 | Wrong evidence file slug → empty claims/sources | High | ACCEPT | Cross |
| 3 | `_match_task` falls back to `tasks[0]` | High | ACCEPT | Both |
| 4 | `_match_spec` false default + missing anchors | High | ACCEPT | Both |
| 5 | `_call_llm` duplicates `_call_llm_raw` | Medium | ACCEPT | Critic |
| 6 | `__import__("datetime")` inline pattern | Medium | ACCEPT | Critic |
| 7 | Magic slice constants without rationale | Medium | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 first**: Add `logger.warning(...)` in both `except` blocks; change fallback ADR `Status` to `Proposed`. This is the only change that prevents silent data corruption visible to end users.
- **Fix #2 next**: Align evidence file slug strategy across researcher write-path and pipeline load-path. Until this is fixed, C3/C4 are always running on empty evidence.
- **Fix #3 and #4 together**: Both are in `_match_task` / `_match_spec` — single PR. Replace all false defaults with `"UNMAPPED"` sentinel. Add anchor support to `_match_spec`.
- **Fix #5 as part of #1**: When applying the logger fix, consolidate `_call_llm` → `_call_llm_raw` delegation to avoid applying the same fix twice.
- **Defer #6 and #7** to a cleanup commit; no correctness impact.
- **Add regression tests** for LLM-failure path (finding #1) and mismatched-slug path (finding #2) before closing this work item.