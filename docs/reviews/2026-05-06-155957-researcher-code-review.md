# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 15:59
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

At least 3 High-severity correctness/integrity issues require fixes before merge. The critic identified 2 BLOCK items (recovery loop logic + non-atomic writes); the cross review confirmed related gaps and added 2 additional High findings independently.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] RecoverySearchLoop never re-evaluates sufficiency after gap search

- **Critic**: Recovery loop runs `_max_rounds` unconditionally — after `web_refs.extend(...)`, sufficiency is never re-checked, so even fully-resolved gaps continue to trigger extra rounds.
- **Cross**: "not flagged directly" — but Finding #3 (gap matching doesn't reuse manifest keywords) is the root cause that makes this worse: even if refs now contain the keywords, `_identify_unmet_gaps()` may still report them unmet.
- **Judgment**: The diff confirms the loop structure (`for gap in _unmet: web_refs.extend(...); _recovery_rounds += 1`) never breaks on resolved state. After `web_refs.extend(...)`, the loop simply increments and re-enters without calling `_is_sufficient` or `_identify_unmet_gaps` again. The critic's fix — call `_identify_unmet_gaps(local_refs, web_refs, ...)` after the extend, and `break` if empty — is correct and minimal.
- **Action Required**: After the `for gap in _unmet:` block, add: `if not self._identify_unmet_gaps(local_refs, web_refs, _domain_checklist): sufficient = True; break`

---

#### 2. [ACCEPT] [High] Non-atomic file writes in `_emit_evidence_files` and `_emit_coverage_report`

- **Critic**: Direct `.write_text()` at lines 661–663, 712–713, 723 can produce partially-written JSON/MD files if the process is interrupted mid-write. Proposes `.tmp` → `os.replace()` pattern.
- **Cross**: Not flagged.
- **Judgment**: Evidence is strong from the diff alone. Lines 661–663 (`_emit_evidence_files`) and 712–713 + 723 (`_emit_coverage_report`) both do direct `.write_text()` on the final path with no guard. On Windows, a crash during write leaves a corrupt file that will silently fail JSON parsing on the next run. The `.tmp` → `os.replace()` pattern is the standard fix and costs nothing to apply. One reviewer is sufficient when the evidence is unambiguous.
- **Action Required**: Replace all three `write_text(...)` calls with: write to `path.with_suffix('.tmp')`, then `os.replace(tmp_path, final_path)`.

---

#### 3. [ACCEPT] [High] `_domain_checklist` never set for `requires_web=True` modes — coverage report silently returns `{}`

- **Critic**: Not explicitly flagged (critic focused on the loop and write-atomicity).
- **Cross**: ACCEPT — "`_domain_checklist` is only loaded in the `else` branch, so `fresh_lookup`, `deep_source_research`, and `live_project_analysis` never emit domain coverage… `_emit_coverage_report` at 1043–1046 returns `{}`."
- **Judgment**: The diff confirms: `_domain_checklist = self._load_domain_manifest(...)` is only inside the `else` block (line ~922). The `requires_web` branch (lines 900–917) never assigns it. The variable is initialized to `None` at line 897. All web-required modes silently skip domain coverage. Strong evidence, single reviewer but unambiguous.
- **Action Required**: Move `_domain_checklist = self._load_domain_manifest(research_plan.domain)` to before the `if research_plan.requires_web:` branch so it applies to all modes.

---

#### 4. [ACCEPT] [High] Evidence JSON loses structured claim citations — dict claims stringified

- **Critic**: Not flagged.
- **Cross**: ACCEPT — "`_emit_evidence_files()` treats `source_backed_claims` as plain strings… dict claim becomes a stringified dict and citation data is not preserved… `ResearchVerifier._evaluate_4_metric()` reads `c.get('source_ids')`."
- **Judgment**: The diff line `"claim": str(claim_text)` at line ~649 confirms this. When `claim_text` is a dict (the structured form from `_synthesize_structured_evidence`), `str(claim_text)` produces a Python repr string like `"{'claim': '...', 'source_ids': [...]}"`. The verifier then calls `.get("source_ids")` on this mangled string — always returning `None`. Data integrity failure is silent and downstream. Single reviewer, evidence is conclusive.
- **Action Required**: In `_emit_evidence_files`, normalize: if `claim_text` is a dict, extract `claim_text["claim"]` and `claim_text.get("source_ids", [])`. If string, wrap as `{"claim": claim_text, "source_ids": []}`. Map `source_ids` to real source objects from the `sources` list.

---

#### 5. [ACCEPT] [Medium] `_identify_unmet_gaps` and `_is_sufficient` use raw field names; `_emit_coverage_report` uses `match_keywords`

- **Critic**: Partially overlaps with Finding #1 (same root contributes to loop not terminating correctly).
- **Cross**: ACCEPT — "fields such as `blind_structure` or `side_pot` can remain unmatched even when manifest keywords are present… triggers unnecessary recovery searches and leaves `sufficiency_gate_passed=False` while coverage would say matched."
- **Judgment**: Both reviewers touch this area. `_identify_unmet_gaps()` (diff line ~626) uses `item.replace("_", " ") not in joined` — plain underscore-to-space replacement. `_emit_coverage_report()` correctly loads `match_keywords` from the YAML and uses `any(kw.lower() in joined for kw in keywords)`. The inconsistency means the loop can report gaps that the coverage report would count as matched, causing unnecessary web calls and incorrect `sufficient=False` state. Classified Medium because it degrades accuracy rather than causing data corruption.
- **Action Required**: Extract a shared `_field_matches(field, joined, match_keywords)` helper. Use it in both `_identify_unmet_gaps()` and `_is_sufficient()`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | RecoverySearchLoop never re-evaluates sufficiency after gap search | High | ACCEPT | Both (critic: direct; cross: root cause) |
| 2 | Non-atomic `write_text()` in evidence/coverage emitters | High | ACCEPT | Critic only |
| 3 | `_domain_checklist` not loaded for `requires_web=True` modes | High | ACCEPT | Cross only |
| 4 | Dict claims stringified → citation data lost in evidence JSON | High | ACCEPT | Cross only |
| 5 | Gap/sufficiency keyword logic inconsistent with coverage report | Medium | ACCEPT | Both |

---

### Recommendations

1. **Fix #1 first** — add post-extend sufficiency re-check in the recovery loop (`researcher.py:941` area). This is the smallest, most surgical change and unblocks the loop termination bug.
2. **Fix #3 alongside #1** — move `_load_domain_manifest()` call above the `requires_web` branch (~line 897). One-line move, no logic change.
3. **Fix #4** — normalize claim extraction in `_emit_evidence_files()`. Check `isinstance(claim_text, dict)` before `str()`. Preserves existing behavior for string claims.
4. **Fix #2** — apply `.tmp` → `os.replace()` to all three `write_text()` calls. No logic change, pure reliability improvement.
5. **Fix #5 last** — extract `_field_matches()` helper and wire into `_identify_unmet_gaps()` and `_is_sufficient()`. Requires touching three call sites; do after the others are stable.
6. Finding #4 (Reject: caller signature) is correctly rejected — no action needed.