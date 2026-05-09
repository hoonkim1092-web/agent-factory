# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 17:22
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Four High/Medium issues exist — two are crash-path bugs that produce silent data loss via outer try-catch absorption, one is a data-integrity cross-reference break, and one is a known non-atomic write pattern. Tests pass but do not cover these paths.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] Fallback claim IDs emit `S001` — sources list now uses `web_001`
- **Critic**: Not flagged in this round (was BLOCK in prior session; Critic notes H2 fix is complete on the `sources[]` side).
- **Cross**: "fallback branches at `core/researcher.py:672,675` still generate `S{i:03d}`; `claims[].source_id` does not exist in `sources[]`"
- **Judgment**: The diff correctly rewrites `sources[]` to `web_{i:03d}` format, but the claim-assignment fallback at lines 672/675 (not touched by this diff) still produces `S001`. Any evidence file that hits the fallback path emits structurally invalid cross-references. Strong code evidence — the two ID schemes are visibly incompatible.
- **Action Required**: Replace both fallback expressions in the `claims` loop with `sources[min(i, len(sources)) - 1]["source_id"]` (guarded by `if sources`). Add a test asserting every `claim["source_id"]` appears in `{s["source_id"] for s in sources}`.

---

#### 2. [ACCEPT] [High] `s["source_id"]` — non-defensive dict access causes KeyError
- **Critic**: "`source_id` 키 존재는 검증하지 않는다. 누락 시 KeyError가 발생하고, outer try 블록에 흡수되어 B4/B5 모두 조용히 미기록된다."
- **Cross**: Not flagged independently (Cross accepted the `source_id` field as expected, but Finding 1 implies it may not always be present in fallback paths).
- **Judgment**: The new `_pack_web` branch accesses `s["source_id"]` directly. The filter only checks `source_type == "web"` — it does not guarantee `source_id` is present. A missing key throws `KeyError`, which is caught by the outer `try` at the call site (`core/researcher.py:1063`), silently suppressing both B4 and B5 writes. Single-reviewer flag, but the code evidence is unambiguous.
- **Action Required**: Change `s["source_id"]` to `s.get("source_id", f"web_{i:03d}")` using an enumerated loop: `for i, s in enumerate(_pack_web, 1)`.

---

#### 3. [ACCEPT] [High] `trust_score` — float() crash risk + semantic overwrite
- **Critic**: "`s.get("relevance_score") or 0.0` passes truthy non-numeric strings (e.g. `"high"`, `"N/A"`) directly to `float()`, raising `ValueError`. Same outer try absorbs it → silent B4 loss."
- **Cross**: "emitted `trust_score` comes from `source_pack.relevance_score` (Tavily retrieval relevance), not from the authority-domain trust score computed in `_collect_web_references()`. A relevant non-authority source can appear trusted."
- **Judgment**: Two distinct defects on the same line. Critic identifies a crash path; Cross identifies a semantic correctness issue. Both are independently valid. Merged at High because the crash path triggers silent data loss via the same outer try.
- **Action Required**: (a) Wrap the float conversion: `try: float(s.get("relevance_score") or 0) except (ValueError, TypeError): 0.0`. (b) Preserve the authority `trust_score` in `_build_source_pack()` for web sources and prefer `s.get("trust_score", <relevance_fallback>)` in `_emit_evidence_files`.

---

#### 4. [ACCEPT] [Medium] Non-atomic `write_text` in `_emit_coverage_report` — known M10 pattern
- **Critic**: "`(out_dir / f"{slug}-coverage.json").write_text(...)` is non-atomic. Process termination mid-write leaves a truncated file. Same pattern as `project_pipeline.py:135`, already listed in code-review.md §3.3 M10."
- **Cross**: Not flagged.
- **Judgment**: This diff touched `_emit_coverage_report` (changed the `out_dir` path). It did not fix the non-atomic write, re-introducing the M10 pattern in modified code. Single reviewer, but the evidence is concrete and the fix is established.
- **Action Required**: Apply `tempfile.NamedTemporaryFile` + `os.replace()` to both `write_text` calls in `_emit_coverage_report`, consistent with prior H5a fixes elsewhere.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Fallback claim IDs emit `S001` — cross-reference break | High | ACCEPT | Cross |
| 2 | `s["source_id"]` KeyError → silent B4/B5 loss | High | ACCEPT | Critic |
| 3 | `float()` crash + trust_score semantic overwrite | High | ACCEPT | Both |
| 4 | Non-atomic `write_text` in `_emit_coverage_report` (M10) | Medium | ACCEPT | Critic |

---

### Recommendations

1. **Fix #1 first** — it is a data-integrity defect in the claim cross-reference structure; add a test for `claim.source_id ∈ {s.source_id for s in sources}`.
2. **Fix #2 alongside #1** — both are in `_pack_web` branch; enumerate with fallback ID in a single pass.
3. **Fix #3 in two parts**: guard `float()` conversion; then thread authority `trust_score` through `_build_source_pack()`.
4. **Fix #4 opportunistically** — apply `os.replace()` atomic pattern to `_emit_coverage_report` write calls to clear the standing M10 debt.
5. **Verify `target_workspace=None` is a real call path** — Critic notes the `workspace or os.getcwd()` fallback permits `None`; confirm this is intentional or tighten to `Path(workspace)` with a precondition check.