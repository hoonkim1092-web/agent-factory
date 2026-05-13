# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-13 18:18
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

> Cross Review returned a **provider error** (Codex session output truncated mid-header — no findings produced). Aggregation is based solely on the Critic Review; all three findings are evaluated on code-evidence strength alone.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] `_clean()` bypasses sanitization contract for new metadata fields

- **Critic**: "`_clean()` is `str(value or "").strip()` — does not strip `\n`/`\r`/`#`. These characters in a `- key: value` metadata line can inject fake keys that `_parse()` reads back as real. `_sanitize_reason()` was introduced specifically to prevent this pattern."
- **Cross**: Provider error — not flagged
- **Judgment**: Evidence is strong and self-contained in the diff. The codebase documents the injection class at `approval_gate.py:29-32`. The current risk is low (line-by-line parsing prevents embedded-newline round-trips today), but `_render()` now formally accepts `work_kind`/`blast_radius` as `str` with no sanitization contract — the unsafe pattern is structurally re-introduced for any future call site. Accepting as High per security-issue minimum-severity rule.
- **Action Required**: Replace both `_clean(current.get("work_kind"))` and `_clean(current.get("blast_radius"))` calls (lines 217-218, 241-242, 419-420) with `_sanitize_reason(current.get("work_kind") or "")` / `_sanitize_reason(current.get("blast_radius") or "")`.

---

#### 2. [ACCEPT] [Medium] `initialize()` not updated — new fields are permanently empty for new gates

- **Critic**: "`initialize()` creates gate files from scratch but was not updated. `current.get("work_kind")` on a freshly-initialized gate returns `None → ""`, so the `if work_kind:` guards in `_render()` never fire. Feature is inert unless gate files are externally pre-edited."
- **Cross**: Provider error — not flagged
- **Judgment**: The diff confirms only three write sites were updated (`approve`, `invalidate`, `apply_verification_verdict`). `initialize()` at line 129-141 is absent from the diff. Since all gate files start via `initialize()`, the new fields will never populate through normal code paths. This is a clear functional gap, not a speculative one.
- **Action Required**: Either add `work_kind: str = ""` / `blast_radius: str = ""` parameters to `initialize()` and pass them through to `_render()`, **or** add a comment explicitly documenting that these fields are populated by a downstream phase (e.g., a future `work_item_generator` step) so the inert behavior is intentional and visible.

---

#### 3. [ACCEPT] [Medium] `get_status()` omits new fields, breaking read API consistency

- **Critic**: "`get_status()` explicitly selects keys but omits `work_kind` and `blast_radius`. Callers needing these for routing (e.g., `execution_policy.py` already uses `work_kind + blast_radius`) cannot access them without calling private `_parse()` directly."
- **Cross**: Provider error — not flagged
- **Judgment**: The diff shows `get_status()` (lines 424-437) was not modified. The return dict pattern selects specific keys, so omission is not a default-passthrough — the fields are actively excluded. If any caller needs policy routing on these values, they will silently receive stale or absent data without an error.
- **Action Required**: Add `"work_kind": _clean(data.get("work_kind"))` and `"blast_radius": _clean(data.get("blast_radius"))` to the `get_status()` return dict. (Note: update to `_sanitize_reason()` here too, per Finding 1.)

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_clean()` bypasses sanitization contract | High | ACCEPT | Critic |
| 2 | `initialize()` not updated — fields never SET | Medium | ACCEPT | Critic |
| 3 | `get_status()` omits new fields | Medium | ACCEPT | Critic |

---

### Recommendations

1. **Fix Finding 1 first** — swap `_clean()` → `_sanitize_reason()` at all 6 call sites (3 callers × 2 fields) before the next merge. This is a one-line change per site and removes a structural re-introduction of a documented vulnerability class.
2. **Resolve Finding 2 explicitly** — either wire `work_kind`/`blast_radius` into `initialize()`, or add a comment marking the fields as intentionally deferred. Leaving it silent means the feature ships silently inert.
3. **Apply Finding 3** — extend `get_status()` return dict with both new fields. This is additive and backward-compatible.
4. **Re-run cross-review** — the Cross Review provider errored. Findings 1-3 are accepted on single-reviewer evidence; a successful cross-review pass would increase confidence before merge.