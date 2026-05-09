# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 17:45
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High/Medium findings confirmed by evidence. No Critical issues, but two crash-path bugs and one functional data-loss bug require attention before the next milestone.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] `KeyError` crash if `source_id` absent from `_pack_web` source
- **Critic**: "`s["source_id"]` raises `KeyError`; all other fields in the same comprehension use `.get()`, making the inconsistency conspicuous."
- **Cross**: not flagged directly, but the diff is unambiguous
- **Judgment**: The diff shows every other field in the new `_pack_web` branch uses `.get()` except this one. `source_id` is not guaranteed present in a Tavily/web source dict — confirmed by the fallback branch which uses `f"web_{i:03d}"` instead. Single-reviewer flag, but evidence is decisive.
- **Action Required**: Replace `s["source_id"]` with `s.get("source_id") or f"web_{j:03d}"` using `enumerate(_pack_web, 1)`.

---

#### 2. [ACCEPT] [High] Local/LLM source citations silently dropped from emitted evidence
- **Critic**: not flagged
- **Cross**: "claims citing `local_001` or `llm_001` are rewritten to a fallback web source or `""`. Direct probe with only `local_001` produced `sources: []` and claim `source_id: ""`."
- **Judgment**: The diff introduces `_pack_web = [s for s in ... if s.get("source_type") == "web"]`. `_build_source_pack()` creates `web_###`, `local_###`, and `llm_###` sources; `_synthesize_structured_evidence()` instructs the LLM to cite all of them. The emitted `sources` list and `valid_source_ids` set are then built only from web entries — any non-web citation falls to `fallback_sid` (a web source) or `""`. This is a functional data-loss bug: evidence files misrepresent the actual source basis of claims. Cross reviewer verified with a live probe.
- **Action Required**: Build `sources` from all `source_pack["sources"]` entries (not just `source_type == "web"`), preserving `source_type`, `authority_level`, title/url, and relevance/trust metadata. Add a test where `source_backed_claims` cites `local_001`.

---

#### 3. [ACCEPT] [Medium] `float()` raises `ValueError` on non-numeric `relevance_score`
- **Critic**: "`or 0.0` guards only falsy values. If `relevance_score` is `"N/A"` or `"high"`, `float()` raises `ValueError`."
- **Cross**: not flagged
- **Judgment**: Single-reviewer, but the code evidence is clear. `s.get("relevance_score") or 0.0` short-circuits for falsy values, but a non-empty non-numeric string passes through to `float()` which raises. The fallback branch uses `ref.get("trust_score", 0.0)` with no conversion — inconsistent safety within the same function.
- **Action Required**: Guard with `isinstance`: `float(v) if isinstance(v := s.get("relevance_score"), (int, float)) else 0.0`.

---

#### 4. [HOLD] [Medium] Non-atomic `write_text` in `_emit_coverage_report` (M10 pattern)
- **Critic**: "Direct `.write_text()` without `tempfile + os.replace`. Pre-existing M10 pattern. This diff modifies the function but does not fix it."
- **Cross**: not flagged
- **Judgment**: Pre-existing issue, not introduced by this diff. The diff only adds `workspace` param routing — the non-atomic write was already there. Fixing M10 is out of scope for this change set.
- **Question for Author**: Is there a tracked M10 sweep ticket? If yes, defer. If M10 repair is expected to land with this PR, it needs to be added.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `KeyError` on missing `source_id` in `_pack_web` | High | ACCEPT | Critic |
| 2 | Local/LLM citations dropped from emitted evidence | High | ACCEPT | Cross |
| 3 | `float()` `ValueError` on non-numeric `relevance_score` | Medium | ACCEPT | Critic |
| 4 | Non-atomic `write_text` in `_emit_coverage_report` | Medium | HOLD | Critic |

---

### Recommendations

- **Fix #1 (KeyError)**: Use `enumerate(_pack_web, 1)` and `s.get("source_id") or f"web_{j:03d}"` — two-line change.
- **Fix #2 (local/LLM dropped)**: Widen `_pack_web` filter to include all source types, or build a separate `sources` list from the full `source_pack["sources"]`. Add a test covering `local_001` citation round-trip.
- **Fix #3 (ValueError)**: Wrap `float()` with `isinstance` guard on the `relevance_score` value.
- **Defer #4 (M10)**: Track under the existing M10 sweep, not this PR, unless the author intended to fix it here.
- **Test gap**: `TestB4EmitEvidenceFiles` currently passes 2 tests (web IDs only). Add a case with `local_001` or `llm_001` as the cited source ID.