# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 17:16
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

> **Note**: Critic Review failed (API 500 error). Verdict is based solely on Cross Review findings. Finding 1 alone is sufficient to BLOCK — the evidence is unambiguous from the diff.

---

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [High] `source_pack` non-web sources silently excluded from evidence output

- **Critic**: not available (API error)
- **Cross**: "`_emit_evidence_files()` filters to `source_type == "web"` only, but LLM is prompted with all source types including `local_001`, `llm_001`. A claim with `source_ids: ["local_001"]` will be written with no matching entry in `sources`."
- **Judgment**: Code evidence is unambiguous. `_build_source_pack()` emits `local_001` (line 423) and `llm_001` (line 439). `_synthesize_structured_evidence()` passes all `sources[:6]` to the LLM (lines 466–505). But the new `_pack_web` filter at line 641 drops non-web entries. This creates a broken cross-reference in `evidence.json` where claims cite source IDs that don't exist in the `sources` array.
- **Action Required**: Replace the web-only filter with the full source list:
  ```python
  # Instead of:
  _pack_web = [s for s in (...) if s.get("source_type") == "web"]
  
  # Use all source types:
  _pack_all = (source_pack or {}).get("sources") or []
  if _pack_all:
      sources = [
          {
              "source_id": s["source_id"],
              "url": s.get("url", ""),
              "title": s.get("title", ""),
              "trust_score": round(float(s.get("relevance_score") or 0.0), 3),
              "retrieval_method": s.get("retrieval_method", "tavily_search"),
              "fetched_at": now_iso(),
          }
          for s in _pack_all
      ]
  ```

---

#### 2. [ACCEPT] [Medium] Authority `trust_score` silently replaced with Tavily relevance score

- **Critic**: not available (API error)
- **Cross**: "`_build_source_pack()` only stores `relevance_score` from Tavily (`ref["score"]` at line 417), discarding the authority whitelist `trust_score` computed at line 388. Once `_emit_evidence_files()` uses `_pack_web`, original authority metadata is gone."
- **Judgment**: Confirmed from diff — the `source_pack` path writes `trust_score: round(float(s.get("relevance_score") or 0.0), 3)` (line 648), which is Tavily's search relevance, not domain authority. The old path correctly used `ref.get("trust_score", 0.0)` computed from `_AUTHORITY_DOMAINS_POKER`. These are semantically different metrics and the field name `trust_score` becomes misleading.
- **Action Required**: Preserve `trust_score` in `_build_source_pack()` and surface both values in the evidence output:
  ```python
  # In _build_source_pack() web entry:
  "trust_score": ref.get("trust_score", 0.0),
  "relevance_score": ref.get("score", 0.0),
  
  # In _emit_evidence_files() source dict:
  "trust_score": s.get("trust_score", 0.0),
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | non-web sources excluded, breaking claim cross-reference | High | ACCEPT | Cross |
| 2 | authority `trust_score` silently replaced with relevance score | Medium | ACCEPT | Cross |

---

### Recommendations

1. **Fix Finding 1 first** — it's a correctness bug: emit all source types from `source_pack`, not just `web`. This matches the LLM prompt contract.
2. **Fix Finding 2** — carry `trust_score` through `_build_source_pack()` so authority scoring isn't lost in the `source_pack` path.
3. **Re-run Critic Review** — the API error means only one reviewer's perspective is captured. If the Critic flags additional issues, another round will be needed.