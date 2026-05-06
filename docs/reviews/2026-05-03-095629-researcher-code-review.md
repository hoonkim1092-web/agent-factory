# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-03 09:56
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The Cross Review failed with a provider error (OpenAI Codex session aborted at stdin read). All aggregation is based on the Critic Review alone, with each finding verified against the diff. No Critical-severity issues found; three independent High findings exist.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `agent_role_hints` silently dropped in `_merge_project_brief_evidence()`
- **Critic**: Copy loop at line 822 enumerates 8 keys but omits `"agent_role_hints"`, which `_synthesize_structured_evidence()` emits at line 478.
- **Cross**: Not flagged (provider error).
- **Judgment**: ACCEPT. Diff confirms `_synthesize_structured_evidence()` returns `"agent_role_hints": []` in both success and fallback paths, but the downstream copy loop never includes it. Any consumer calling `data["agent_role_hints"]` will get `None` or `KeyError`. Evidence is unambiguous.
- **Action Required**: Add `"agent_role_hints"` to the key tuple at `researcher.py:822-826`.

---

#### 2. [ACCEPT] [High] Silent `except Exception:` swallows auth/infra failures
- **Critic**: Broad `except Exception:` at line 471–484 returns a zero-value dict with no log entry, making auth failures indistinguishable from successful empty results. Matches known pattern H3.
- **Cross**: Not flagged (provider error).
- **Judgment**: ACCEPT. Diff confirms the bare `except Exception:` block with no logging. This is a recurrence of H3 from `ise_redesigner.py` — same fix applies here.
- **Action Required**: Add `logger.warning("structured_evidence_failed: %s", e)` inside the `except` clause. Consider splitting `except (json.JSONDecodeError, ValueError, KeyError)` from `except Exception` if LLM unavailability should be a hard error.

---

#### 3. [ACCEPT] [High] `content_full` populated with `excerpt` for local and llm_prior refs
- **Critic**: Lines 382 and 398 assign `ref.get("excerpt", "")` to `content_full`, defeating the purpose of the field as untruncated content.
- **Cross**: Not flagged (provider error).
- **Judgment**: ACCEPT. Diff shows `"content_full": ref.get("excerpt", "")` for both `local_refs` and `llm_prior_refs` blocks. The LLM synthesizer then slices these to `[:200]`, meaning consumers expecting richer text silently receive truncated data.
- **Action Required**: For local refs, use `ref.get("content_full") or ref.get("content") or ref.get("excerpt", "")`. Same cascade for llm_prior refs.

---

#### 4. [ACCEPT] [Medium] Inline imports outside `try` block — `ImportError` bypasses graceful fallback
- **Critic**: `from core.requirement_llm import ...` and `from core.utils import ...` at lines 460–461 are outside the `try:` scope. An `ImportError` (frozen build missing hiddenimport) propagates uncaught. Matches known pattern M9.
- **Cross**: Not flagged (provider error).
- **Judgment**: ACCEPT. Diff confirms placement. The `except Exception:` handler two lines below cannot catch an `ImportError` raised before `try:` is entered. Risk is real in PyInstaller builds.
- **Action Required**: Move both imports inside the `try:` block, OR move to module-level and add `core.requirement_llm` to `af.spec` `hiddenimports`.

---

#### 5. [ACCEPT] [Medium] Magic number `sources[:6]` — misleading prompt label
- **Critic**: `sources[:6]` slice at line 419 feeds only 6 sources to the LLM while the prompt label reads `Sources({len(sources)} total)`, creating a count mismatch visible to the model.
- **Cross**: Not flagged (provider error).
- **Judgment**: ACCEPT. Diff confirms both `sources[:6]` and `Sources({len(sources)} total)` in the same prompt block. A 12-source pack would tell the model "12 total" but present only 6. Matches pattern M3/M4.
- **Action Required**: Define `_EVIDENCE_PROMPT_SOURCE_LIMIT = 6` as a class constant; use it for both the slice and the label: `Sources({len(sources[:_EVIDENCE_PROMPT_SOURCE_LIMIT])} total)`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `agent_role_hints` dropped in merge loop | High | ACCEPT | Critic |
| 2 | Silent `except Exception` — no logging | High | ACCEPT | Critic |
| 3 | `content_full` = `excerpt` for local/llm refs | High | ACCEPT | Critic |
| 4 | Imports outside `try` — `ImportError` uncaught | Medium | ACCEPT | Critic |
| 5 | Magic number `sources[:6]` / misleading label | Medium | ACCEPT | Critic |

---

### Recommendations

- **Fix 1 before anything else**: `agent_role_hints` is actively computed and silently discarded — a guaranteed data loss on every call.
- **Fix 2 alongside Fix 1**: Logging the suppressed exception is a one-liner and removes a blind spot across the entire `_synthesize_structured_evidence` code path.
- **Fix 3**: The `content_full = excerpt` alias undermines the whole Phase 1b schema intent. Use a proper fallback cascade.
- **Fix 4**: Move the two imports inside `try:` — five-second change, prevents a class of frozen-build crashes (M9 recurrence).
- **Fix 5**: Name the constant, fix the label — this is a cosmetic-plus-correctness change that prevents the LLM from receiving contradictory context about how many sources it has.
- Cross Review was unavailable (provider error). **Re-run af-cross-review after fixes** to satisfy the 3-tier gate before merging.