# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-05 08:45
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

The Cross Review failed with a provider error (OpenAI Codex stdin parse failure) — no findings were produced. All findings below are sourced from the Critic and verified against the diff.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] `lstrip("www.")` strips characters, not a prefix — `wsop.com` whitelist entry breaks

- **Critic:** `lstrip("www.")` strips any character in `{'w', '.'}` from the left, consuming the leading 'w' of `wsop` in `www.wsop.com`, yielding `"sop.com"` — which does not match any whitelist entry.
- **Cross:** Not flagged (provider error).
- **Judgment:** Confirmed from diff line `url_host = url.split("//")[-1].split("/")[0].lstrip("www.")`. `str.lstrip` is documented to strip a *character set*, not a string prefix. `www.wsop.com` is the only whitelist domain whose base starts with a strippable character, making it silently broken today.
- **Action Required:** Replace with `removeprefix("www.")` (Python 3.9+, consistent with `requires-python = ">=3.9"`):
  ```python
  raw_host = url.split("//")[-1].split("/")[0]
  url_host = raw_host.removeprefix("www.")
  ```

---

#### 2. [ACCEPT] [High] `list[str] | None` union syntax is a Python 3.10 runtime feature; crashes on Python 3.9

- **Critic:** `domain_checklist: list[str] | None = None` at `researcher.py:602` evaluates `types.GenericAlias.__or__(NoneType)` at class-definition time. This raises `TypeError` on Python 3.9, crashing the entire import of `researcher.py`.
- **Cross:** Not flagged (provider error).
- **Judgment:** `pyproject.toml` declares `requires-python = ">=3.9"`. The `|` operator on generic aliases (PEP 604) became available at runtime in Python 3.10. The diff introduces this pattern for the first time in `researcher.py`. Without `from __future__ import annotations`, it is a hard import-time crash on any Python 3.9 environment.
- **Action Required:** Either add `from __future__ import annotations` at the top of the file, or use `Optional`:
  ```python
  from typing import Optional
  domain_checklist: Optional[list[str]] = None,
  ```

---

#### 3. [ACCEPT] [Medium] Domain-token post-filter applied after `limit` cap silently returns fewer than `limit` refs

- **Critic:** Loop caps at `limit` items, then `domain_tokens` filter discards non-matching ones. If all collected items fail the token check, the function returns 0 results even though deeper roots might have matched.
- **Cross:** Not flagged (provider error).
- **Judgment:** Verified in diff at lines `330–345`. The `refs[:limit]` at the end further truncates but doesn't help — the damage is done in the loop. Callers (`_research`) fall through to web search only when `local_refs` is empty, so returning 0 local refs does trigger fallback — but silently discards potentially valid deeper local refs without explanation.
- **Action Required:** Document that `_collect_local_references` may return 0–limit items and that the caller's fallback handles the 0-result case, OR over-collect before filtering:
  ```python
  # collect up to limit * 3 candidates, then filter and trim
  if len(refs) >= limit * 3:
      break
  ```

---

#### 4. [ACCEPT] [Medium] Magic number `0.7` for domain checklist pass threshold

- **Critic:** The 70% coverage threshold in `_is_sufficient` at line `637` is undocumented and unnamed.
- **Cross:** Not flagged (provider error).
- **Judgment:** Minor maintainability issue. Confirmed in diff. Any future tuning requires a grep for `0.7` across the file.
- **Action Required:**
  ```python
  _DOMAIN_CHECKLIST_COVERAGE_THRESHOLD = 0.7
  ...
  if matched < len(domain_checklist) * _DOMAIN_CHECKLIST_COVERAGE_THRESHOLD:
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `lstrip("www.")` breaks `wsop.com` whitelist | High | ACCEPT | Critic |
| 2 | `list[str] \| None` crashes Python 3.9 at import | High | ACCEPT | Critic |
| 3 | Post-filter after limit cap returns < limit results | Medium | ACCEPT | Critic |
| 4 | Magic number `0.7` coverage threshold | Medium | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 immediately:** `removeprefix("www.")` — one-line change, no imports needed (Python 3.9+).
- **Fix #2 immediately:** Add `from __future__ import annotations` at the top of `researcher.py` — zero behavioral change, fixes all current and future `X | Y` annotations in the file at once.
- **Fix #3 before P1 activation:** The current P0 `domain_tokens` filter is already live. Document the 0-result-is-expected behavior or adjust collection window.
- **Fix #4 before P1 activation:** Extract constant before `domain_checklist` logic is exercised in production.
- **Cross Review:** Rerun `af-cross-review` after fixes — provider error means the second opinion is missing. Both High findings stand without contradiction, but the cross-review gap should be closed before merge.