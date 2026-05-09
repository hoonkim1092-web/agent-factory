# Code Review: web_search

> Source: core/web_search.py
> Date: 2026-05-03 09:52
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

The Cross Review failed with a provider error (no content returned). Verdict is based solely on the Critic Review, which is sufficient to BLOCK given two independent HIGH findings with strong diff evidence.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Breaking field rename — `"content"` key dropped without caller migration
- **Critic**: "`content` renamed to `excerpt`/`content_full`; downstream consumers get `None`/`KeyError` silently"
- **Cross**: Not available (provider error)
- **Judgment**: Accepted on single-source — evidence is unambiguous in the diff. `-"content": item.get("content", "")[:500]` is deleted; any caller doing `result["content"]` or `result.get("content")` now gets `None` with no crash. The `researcher.py` file is explicitly named as a likely consumer and is **not patched in this diff**.
- **Action Required**: Either add `"content": full[:200]` as a backward-compat alias in the same dict, or grep `core/` for `\["content"\]` / `\.get\("content"\)` and patch all call sites in this commit before merging.

#### 2. [ACCEPT] [High] Silent exception swallow in `tavily_extract()` — failure indistinguishable from empty result
- **Critic**: "`except Exception: print(...); return []` hides auth errors, timeouts, quota exhaustion"
- **Cross**: Not available (provider error)
- **Judgment**: Accepted. This directly repeats the H3 anti-pattern already documented in `code-review.md §3.2`. The diff at lines 122–124 shows the bare `except` with `return []`. A caller receiving `[]` has no way to know whether extraction found nothing or the API call completely failed.
- **Action Required**: Raise a typed exception (e.g. `TavilyExtractError(str(e)) from e`) or return a failure sentinel. At minimum replace `print()` with `logging.warning(..., exc_info=True)` so the stack trace is preserved.

#### 3. [ACCEPT] [Medium] Reversed `content`/`raw_content` fallback priority between the two functions
- **Critic**: "`tavily_search` prefers `content`, `tavily_extract` prefers `raw_content` — same URL deduped across both will yield different `content_full`"
- **Cross**: Not available
- **Judgment**: Accepted. Both lines are visible in the diff: line 77 (`content or raw_content`) vs line 141 (`raw_content or content`). No comment explains the reversal. Any deduplication or merge of results from both paths will be non-deterministic per-field.
- **Action Required**: Pick one canonical order. If Extract API guarantees `raw_content` is richer, document that in a comment and apply the same order in `tavily_search`. Otherwise default to `content or raw_content` in both.

#### 4. [ACCEPT] [Medium] `score=1.0` hardcoded — artificially top-ranks all extracted results
- **Critic**: "Magic numbers `urls[:5]`, `timeout=30`, `score=1.0`; `score=1.0` corrupts downstream relevance ranking"
- **Cross**: Not available
- **Judgment**: Accepted on the `score` issue specifically. The diff at line 145 shows `"score": 1.0` hardcoded. Any downstream ranker that sorts by score will place every `tavily_extract` result above organic search results (which have real scores ≤ 1.0). `urls[:5]` and `timeout=30` are lower risk (runtime policy, not correctness) but still warrant named constants.
- **Action Required**: Return `0.0` or a distinct sentinel (e.g. `None`) for "unscored" extracted results. Define `_EXTRACT_MAX_URLS = 5` and `_EXTRACT_TIMEOUT_S = 30` as module-level constants.

#### 5. [HOLD] [Low] `af.spec` `hiddenimports` coverage for `tavily_extract`
- **Critic**: "`core/web_search.py` may not be listed in `af.spec hiddenimports`; new function uses `urllib`/`json` (stdlib, safe now but worth verifying)"
- **Cross**: Not available
- **Judgment**: Hold — `af.spec` is not in this diff. The Critic acknowledges stdlib-only imports are safe. Risk is future, not present.
- **Question for Author**: Is `core.web_search` already present in `af.spec hiddenimports`? If yes, this is PASS. If no, add it.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Breaking `"content"` field rename without caller migration | High | ACCEPT | Critic |
| 2 | Silent exception swallow in `tavily_extract()` | High | ACCEPT | Critic |
| 3 | Reversed `content`/`raw_content` fallback order | Medium | ACCEPT | Critic |
| 4 | `score=1.0` corrupts relevance ranking | Medium | ACCEPT | Critic |
| 5 | `af.spec` hiddenimports coverage | Low | HOLD | Critic |

---

### Recommendations

- **Before re-submitting**: Fix findings #1 and #2 — these are blockers. #1 requires a grep audit of `core/researcher.py` and any Research Router consumers for `"content"` key access. #2 requires replacing the bare `except` with a typed raise or at minimum `logging.warning(..., exc_info=True)`.
- **In the same commit**: Standardize fallback order (#3) and replace `score=1.0` with `0.0` or `None` (#4). Name the magic constants.
- **Post-merge follow-up**: Verify `core.web_search` is in `af.spec hiddenimports` (#5 HOLD).
- **Cross Review gap**: The OpenAI Codex provider errored out. Consider re-running the cross-review after fixes — the broken field rename (#1) is the kind of structural issue a fresh-context reviewer is most likely to catch independently.