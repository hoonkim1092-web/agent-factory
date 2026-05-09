# Code Review: research_router

> Source: core/research_router.py
> Date: 2026-05-05 08:54
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Cross Review failed to execute (provider error — OpenAI Codex session aborted before output). Verdict derived solely from Critic review + direct diff analysis.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] `"turn"` substring matches `"return"` — false poker domain on any programming question

- **Critic**: `tok in text` substring match causes `"turn"` ⊂ `"return"`, `"ante"` ⊂ `"antecedent"`, `"flop"` ⊂ `"floppy"`, `"blind"` ⊂ `"blindside"`
- **Cross**: Not flagged (provider error)
- **Judgment**: Diff confirms the implementation at `research_router.py:261-269`. `any(tok in text ...)` is unambiguously substring matching. `"return"` appears in virtually every programming question. The bug is deterministic, not probabilistic. Accepted on critic evidence alone.
- **Action Required**: Split text into word tokens before matching ASCII tokens:
  ```python
  _ASCII_POKER_TOKENS = frozenset({
      "poker", "hold'em", "holdem", "blind", "blinds",
      "all-in", "allin", "flop", "turn", "river", "ante", "showdown",
  })
  _KO_POKER_TOKENS = frozenset({"포커"})

  def _detect_domain(self, request: str) -> str:
      text = (request or "").lower()
      words = set(re.split(r"[\s\W]+", text))
      if words & self._ASCII_POKER_TOKENS or any(tok in text for tok in self._KO_POKER_TOKENS):
          return "poker"
      return ""
  ```

#### 2. [ACCEPT] [Medium] `requires_research`/`research_depth` derivation duplicated verbatim in `for_mode()` and `_select_mode()`

- **Critic**: Identical block at lines 109-117 and 312-320. Threshold divergence is silent — any future change must be applied twice.
- **Cross**: Not flagged (provider error)
- **Judgment**: Diff confirms both blocks are character-for-character identical. Pattern matches the known M5 copy-paste class in `code-review.md`. Medium, not High, because no current divergence exists — but the maintenance trap is real.
- **Action Required**: Extract `@staticmethod _derive_research_flags(mode: str, scores: dict) -> tuple[bool, str]` and call from both methods.

#### 3. [ACCEPT] [Medium] `for_mode()` missing `domain` parameter — invisible save/restore contract for callers

- **Critic**: `for_mode()` always produces `domain=""`. Current `researcher.py:752-754` correctly saves/restores, but the contract is invisible to future callsites.
- **Cross**: Not flagged (provider error)
- **Judgment**: Diff confirms `domain=""` hardcoded in `_select_mode()` return at line 330, with comment explaining the intent. The current fix works but is fragile. Accepted as Medium — not High because the current callsite is correct.
- **Action Required**: Add `domain: str = ""` parameter to `for_mode()` signature and pass it through to the constructor.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `"turn"` substring matches `"return"` — false poker domain | High | ACCEPT | Critic |
| 2 | `requires_research`/`research_depth` duplicated in two paths | Medium | ACCEPT | Critic |
| 3 | `for_mode()` missing `domain` param — invisible contract | Medium | ACCEPT | Critic |

---

### Recommendations

1. **Must fix before merge**: Replace `tok in text` with word-boundary matching in `_detect_domain()`. The `"return"` collision makes the poker domain detector fire on essentially all programming questions.
2. **Should fix**: Extract `_derive_research_flags()` static method to eliminate the duplicated derivation block.
3. **Should fix**: Add `domain: str = ""` to `for_mode()` to make the save/restore contract explicit in the API.
4. **Cross Review gap**: Re-run cross review after fixes — the Codex provider errored out this round. Finding 1 is severe enough to BLOCK regardless, but cross verification of findings 2-3 is still pending.