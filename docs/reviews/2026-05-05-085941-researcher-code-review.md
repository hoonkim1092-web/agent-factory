# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-05 08:59
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

The Cross Review experienced a fatal provider error (stdin read failure, session `019df56a`) and produced no findings. All three findings below come solely from the Critic. Per aggregation rule #2 — "only one reviewer, evidence is strong" — all three are ACCEPTED: the Critic supplies file+line references, concrete false-positive examples, and Finding #1 is a confirmed carryover BLOCK from the previous review round.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] `_detect_domain` substring match misclassifies any code question as poker domain

- **Critic**: `if any(tok in text for tok in self._POKER_TOKENS)` at `core/research_router.py:264` — `"turn" ⊂ "return"`, `"ante" ⊂ "antecedent"`, `"river" ⊂ "deliver"` — every Python function question triggers poker domain.
- **Cross**: Provider error — no input.
- **Judgment**: ACCEPT. This is a confirmed, unfixed carryover BLOCK. The token set was introduced in this diff without the word-boundary guard. Any question mentioning `return` (virtually every programming question) deterministically routes to poker domain. The fix pattern (`re.split(r"\W+", text)` → word set) already exists in `_extract_domain_tokens` in the same file — it just wasn't applied here.
- **Action Required**: Replace the substring loop with a word-set intersection for ASCII tokens; retain substring match only for Korean tokens (no word boundaries in Korean script).

```python
_words = set(_re.split(r"\W+", text))
if _words & self._ASCII_POKER_TOKENS or any(tok in text for tok in self._KOREAN_POKER_TOKENS):
    return "poker"
```

---

#### 2. [ACCEPT] [Medium] `_is_sufficient` domain_checklist repeats identical substring anti-pattern

- **Critic**: `core/researcher.py:634` — `sum(1 for item in domain_checklist if item.lower() in joined)` — when P1 activates the checklist, items like `"turn"` or `"blind"` over-count matches against `"return"` / `"blindly"`, causing `_is_sufficient` to return `True` prematurely and skip needed web research.
- **Cross**: Not flagged.
- **Judgment**: ACCEPT. Latent but inevitable — the code path exists and the same anti-pattern is being introduced twice in the same diff. The Critic's fix (convert `joined` to a word set before matching) is minimal and correct.
- **Action Required**: `joined_words = set(_re.split(r"\W+", joined))`; use `item.lower() in joined_words` for the match check.

---

#### 3. [ACCEPT] [Medium] `_collect_local_references` domain-token post-filter can zero out all refs

- **Critic**: `core/researcher.py:337–345` — domain filter runs after `refs[:limit]` is sliced; if tokens are overly selective (terse excerpts, short headings), filter produces `[]`, `_is_sufficient` sees `len(local_refs) < 2`, and falls through to web even though valid local refs existed in the pre-filter set.
- **Cross**: Not flagged.
- **Judgment**: ACCEPT. The logic flow is clearly described and the edge case (all refs filtered out) is real: the fix is a one-liner fallback with no behavior change for the normal path.
- **Action Required**: `return (filtered or refs)[:limit]` — if filtering eliminates everything, fall back to unfiltered refs rather than returning an empty list.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_detect_domain` substring match → poker false positive | High | ACCEPT | Critic |
| 2 | `_is_sufficient` checklist repeats substring anti-pattern | Medium | ACCEPT | Critic |
| 3 | `_collect_local_references` post-filter can zero out refs | Medium | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 first** — it is the BLOCK condition and the fix is a one-function rewrite with an existing pattern in the same file (`_extract_domain_tokens`).
- **Fix #2 immediately after** — it is the same anti-pattern; fix both in one commit to avoid a third review round on the same issue.
- **Fix #3 in the same commit** — the fallback is a one-liner and has no risk of behavior regression on the normal (non-empty) path.
- **Cross Review provider must be restored** before the next review cycle — a single-reviewer gate provides no cross-verification coverage. Re-run with a working Codex session after the fixes are applied.
- After fixes, re-run `af-test-runner` to confirm `_detect_domain` and `_is_sufficient` unit paths pass with inputs containing `return`, `blindly`, and `antecedent`.