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

> Cross Review provider errored out (incomplete output, no findings). All findings sourced from Critic only. Each finding is assessed against diff evidence independently.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Medium] `initialize()` not updated — feature is a no-op on fresh gates

- **Critic**: "`initialize()` creates the gate file without `work_kind`/`blast_radius`, so all three new `_render()` call sites can only round-trip values that already exist — no code path writes these fields initially."
- **Cross**: not flagged (provider error)
- **Judgment**: Diff confirms `initialize()` at L129-142 was not modified. The three added lines are purely round-trip: `_clean(current.get("work_kind"))` → `_clean(None)` → `""` → `if work_kind:` guard fires falsy → nothing written. Feature is structurally inert until `initialize()` accepts and forwards these parameters. Evidence is direct and unambiguous from the diff alone.
- **Action Required**: Add `work_kind: str = ""` and `blast_radius: str = ""` parameters to `initialize()`, forward to `_render()`.

#### 2. [ACCEPT] [Medium] `get_status()` not updated — new fields absent from public API

- **Critic**: "`get_status()` returns dict without `work_kind`/`blast_radius`; downstream callers needing to route on `work_kind` must call private `_parse()` directly."
- **Cross**: not flagged (provider error)
- **Judgment**: Diff shows `_render()` gains the fields but `get_status()` (L424-437) is untouched. If `work_kind` exists for routing/filtering, it must be readable through the public API without bypassing encapsulation. Finding is consistent with the established `get_status()` contract.
- **Action Required**: Add `"work_kind": _clean(data.get("work_kind")), "blast_radius": _clean(data.get("blast_radius"))` to the `get_status()` return dict.

#### 3. [HOLD] [Medium] `_clean()` lacks `\n`/`#` sanitization — H2-class regression risk

- **Critic**: "`_clean()` doesn't strip embedded `\n` or `#`; `_sanitize_reason()` exists precisely for this. Future callers passing unsanitized external input would bypass the H2 defense layer."
- **Cross**: not flagged (provider error)
- **Judgment**: Current code path is safe — values enter only via `_parse()` which reads line-by-line (embedded newlines impossible). Risk is latent, not exploitable today. Critic correctly identifies the *class* of risk and points to `_sanitize_reason()` as the right tool. Holding pending author confirmation: **does any current or planned caller of the updated `initialize()` pass externally-sourced `work_kind`/`blast_radius` strings?** If yes → ACCEPT and swap `_clean` → `_sanitize_reason` at all 3 call sites. If no (internal enum/constant only) → document the constraint, keep as-is.
- **Question for Author**: What is the source of `work_kind`/`blast_radius` values that will be passed to `initialize()`? Internal constants or user/external input?

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `initialize()` not updated — no-op on fresh gates | Medium | ACCEPT | Critic |
| 2 | `get_status()` missing new fields | Medium | ACCEPT | Critic |
| 3 | `_clean()` lacks `\n`/`#` sanitization (H2-class) | Medium | HOLD | Critic |

---

### Recommendations

- Fix Finding 1 first — without it, Finding 2 is also moot (nothing to read back).
- Add `work_kind`/`blast_radius` to `get_status()` return dict (3-line change, no logic risk).
- Clarify Finding 3's input source before deciding sanitization approach. If external input ever reaches these fields, upgrade to `_sanitize_reason()` at all three call sites.
- Note: Cross Review provider failed entirely — consider re-running `af-cross-review` after fixes are applied if the provider becomes available.