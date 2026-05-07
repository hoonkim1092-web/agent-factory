# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 17:17
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Three High/Medium issues require action before merge; two are data-integrity bugs that silently produce broken evidence files. 49 tests pass per Cross verification.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] Claim fallback still emits `S001` IDs — cross-reference break
- **Critic**: Not re-flagged in current round (was BLOCK in prior session)
- **Cross**: "fallback branches at `core/researcher.py:672,675` still generate `S###`; `claims[].source_id` does not exist in `sources[]`"
- **Judgment**: The new `_pack_web` path writes `web_001`-format IDs into `sources[]`, but two fallback expressions at lines 672/675 still produce `S{i:03d}`. Any evidence file that hits the fallback has structurally invalid cross-references. Strong code evidence; unambiguous data-integrity defect.
- **Action Required**: Replace both fallback expressions with `sources[min(i, len(sources)) - 1]["source_id"]` when `sources` is non-empty, else `""`.

#### 2. [ACCEPT] [High] `s["source_id"]` bare key access — silent evidence loss on KeyError
- **Critic**: "`_pack_web` filter only checks `source_type == 'web'`; `source_id` key existence not guaranteed. KeyError is caught by outer `try` → entire evidence file skipped silently."
- **Cross**: Not flagged separately (subsumed under fallback analysis)
- **Judgment**: Line 647 `s["source_id"]` raises `KeyError` if any source from `_build_source_pack()` lacks `source_id`. The outer `except Exception: pass` block (line 1082) swallows it. One malformed upstream source silently drops the whole evidence file. Single reviewer but code evidence is unambiguous.
- **Action Required**: Change to `s.get("source_id") or f"web_{i:03d}"` using `enumerate(_pack_web, 1)`.

#### 3. [ACCEPT] [Medium] `trust_score` overwritten with `relevance_score` — authority signal lost
- **Critic**: Listed `round(float(s.get("relevance_score") or 0.0), 3)` as a positive observation (float normalization), missed semantic mismatch
- **Cross**: "authority trust from whitelisted domains at lines 376–389 is not preserved in `_build_source_pack()`; `trust_score = relevance_score` lets high-ranked non-authority sources appear trusted"
- **Judgment**: Reviewers contradict on this point. Diff confirms `trust_score: round(float(s.get("relevance_score") or 0.0), 3)` at line 648. `relevance_score` is retrieval ranking; `trust_score` is domain-authority signal computed separately. Semantically different fields merged into one key — downstream consumers relying on `trust_score` for authority gating will get wrong values. Cross evidence is stronger; ACCEPT.
- **Action Required**: Preserve `trust_score` in `_build_source_pack()` for web sources. Use `s.get("trust_score") or round(float(s.get("relevance_score") or 0.0), 3)` as fallback chain in `_emit_evidence_files()`.

#### 4. [ACCEPT] [Medium] Recovery-round `web_refs` silently discarded when `_pack_web` is populated
- **Critic**: "`source_pack` is built before recovery loop; URLs added by recovery rounds are completely ignored when `_pack_web` branch is taken. LLM claims referencing recovery sources point to non-existent IDs."
- **Cross**: Not flagged
- **Judgment**: Single reviewer, but the code path is clear from the diff: `if _pack_web:` uses only `source_pack`-derived sources; `web_refs` (which accumulates recovery-round results) is fully discarded in that branch. Structural correctness issue with moderate blast radius.
- **Action Required**: Merge `web_refs` entries not already present in `_pack_web` (by URL) into `sources`, assigning `web_{len(_pack_web)+i:03d}` IDs.

#### 5. [ACCEPT] [Medium] Non-atomic JSON writes for evidence/coverage artifacts
- **Critic**: Noted as pre-existing pattern, not newly introduced
- **Cross**: "New `docs/research/*-evidence.json` / `*-coverage.json` artifacts follow the known non-atomic write pattern; `core/dashboard.py:108-115` already has a safe atomic helper"
- **Judgment**: Code-review.md lists this as a known recurring issue. These are new files being written with `Path.write_text()` directly (lines 684–687, 736–738). A crash mid-write corrupts the artifact. An atomic helper already exists in the codebase — reusing it is low effort.
- **Action Required**: Use temp-file + `os.replace()` pattern (cf. `core/dashboard.py:108-115`) for both JSON outputs.

#### 6. [ACCEPT] [Low] No warning when `source_pack` provided but `_pack_web` is empty
- **Critic**: "`source_type == 'web'` filter silently falls back to `web_refs` if `_build_source_pack()` uses a different type string (`'tavily'`, `None`, etc.). No diagnostic emitted."
- **Cross**: Not flagged
- **Judgment**: Single reviewer. The diagnostic gap is real — if `source_type` values drift, the H2 fix becomes a silent no-op with no observable signal. Low blast radius but masks future regressions.
- **Action Required**: Add `logger.warning("source_pack present but _pack_web empty — falling back to web_refs")` when `source_pack` is non-empty but `_pack_web` is `[]`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Claim fallback `S001` IDs break cross-reference | High | ACCEPT | Cross + prior Critic |
| 2 | `s["source_id"]` bare access → silent evidence loss | High | ACCEPT | Critic |
| 3 | `trust_score` overwritten with `relevance_score` | Medium | ACCEPT | Cross |
| 4 | Recovery-round `web_refs` discarded in `_pack_web` branch | Medium | ACCEPT | Critic |
| 5 | Non-atomic JSON writes for new artifacts | Medium | ACCEPT | Cross |
| 6 | No warning when `source_pack` yields empty `_pack_web` | Low | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 first** (line 672/675): the `S001` fallback is the most likely to corrupt production evidence files since it fires whenever LLM omits `source_ids`.
- **Fix #2 together with #1** (line 647): both are in `_emit_evidence_files()` — one edit session.
- **Fix #3** (line 648): one-line change; `s.get("trust_score") or round(...)` pattern is already established in the else-branch.
- **Fix #4**: requires a merge step after the `if _pack_web:` block — medium complexity; pair with #1/#2.
- **Fix #5**: extract or reuse the existing atomic write helper from `core/dashboard.py` — two call sites to update.
- **Fix #6**: add a single `logger.warning(...)` line — lowest effort, highest diagnostic value.
- Cross-verified: 49 tests pass. After fixes, re-run `test_research_p1_quality_gate.py` to confirm no regression.