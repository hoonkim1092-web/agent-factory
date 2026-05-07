# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-05-06 21:48
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Six accepted findings. Cross #1 (wrong filename) alone guarantees that `_claims` and `_sources` are always `[]` in production — which means Critic #1 and #2 fire on every run, not just on LLM failure. The four high-severity issues form an interlocking failure cluster: evidence is never loaded → fallback ADR is silently written as authoritative → empty traceability table is written as complete → both files are invisible to any downstream gating.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] Wrong filename — evidence is never loaded

- **Critic**: not flagged
- **Cross**: "`_load_evidence()` looks for `<slug_from_brief>-evidence.json`, but researcher writes `<safe_id(task_input)[:40]>-evidence.json`. Korean inputs diverge more sharply."
- **Judgment**: Code evidence is unambiguous. `researcher.py:1069` uses `safe_id(task_input)[:40]`; `project_pipeline.py:867` derives slug from `slug_from_brief(project_brief)`. Even for ASCII input `"build a poker game"`, the two slugs differ in separator (`_` vs `-`). This is not a corner case — it fires on every invocation. All downstream findings (#2, #3) are guaranteed consequences.
- **Action Required**: Do not re-derive the slug. Either thread the evidence path/content out of `collect_project_evidence()` and pass it directly, or store `claims`/`sources` in `research_evidence` before `_load_evidence` is called.

---

#### 2. [ACCEPT] [High] Fallback ADR persisted as authoritative "Accepted" decision

- **Critic**: "`_call_llm_raw` returns `_fallback_adr()` on any exception. `_fallback_adr()` has `Status: Accepted`. The `if _adr_md:` guard is a truthiness test — it cannot distinguish synthetic from real output."
- **Cross**: not flagged (but this fires unconditionally given finding #1)
- **Judgment**: Strong evidence in diff. `_fallback_adr()` at `spec_generator.py:188-190` hard-codes `Status: Accepted` and a plausible Decision body. With finding #1 confirmed, `_claims=[]` always, so the prompt quality degrades and LLM timeout risk rises — but even on success the guard is broken. No sentinel exists.
- **Action Required**: Either (a) return `""` from `_call_llm_raw` on failure so `if _adr_md:` gates correctly, or (b) prefix fallback with `<!-- FALLBACK -->` and check for it at `project_pipeline.py:880`. Option (a) is simpler.

---

#### 3. [ACCEPT] [High] `TraceabilityGenerator.generate()` always returns truthy — empty table written as complete doc

- **Critic**: "Method always returns at minimum heading + table headers. `if _trace_md:` is always `True`. Zero-coverage doc is indistinguishable from a populated one."
- **Cross**: not flagged (but this fires unconditionally given finding #1)
- **Judgment**: Confirmed in diff. `spec_generator.py:241-246` always builds and returns the header rows before iterating `rows`. When `rows` is empty the returned string is non-empty. The `if _trace_md:` check at `pipeline.py:883` provides no gate.
- **Action Required**: Add `if not rows: return ""` at the top of the loop body in `TraceabilityGenerator.generate()` before building `table_lines`.

---

#### 4. [ACCEPT] [High] `_load_evidence` silently swallows all I/O and parse errors

- **Critic**: "`PermissionError`, `UnicodeDecodeError`, malformed JSON — all return `([], [])` silently, identical to a legitimately absent file. No log, no exception propagated."
- **Cross**: not flagged directly (covered implicitly by finding #1 rendering the method moot)
- **Judgment**: Bare `except Exception: return [], []` at `project_pipeline.py:239` is confirmed in diff. Combined with findings #1–#3, a corrupt evidence file triggers a silent write of a zero-evidence ADR with `Status: Accepted`. This repeats the known H3 pattern (`ise_redesigner.py`).
- **Action Required**: Narrow to `except json.JSONDecodeError` with `logging.warning(...)`. Re-raise or log `OSError`/`PermissionError` separately — do not swallow unexpected I/O errors.

---

#### 5. [ACCEPT] [Medium] Non-atomic writes in `_save_adr` and `_save_traceability`

- **Critic**: "Direct `write_text` truncates before writing. A crash mid-write leaves a partial file. Downstream review/gating parses markdown — partial content parsed as valid. Same as M10 pattern."
- **Cross**: "The project already uses atomic JSON writes via `temp file + os.replace()` in `_write_json()`. These two new write sites are separate instances of the same class."
- **Judgment**: Both reviewers flag the same lines (`project_pipeline.py:247, 254`). Confirmed in diff. Pattern is identical to previously fixed C2/H5a sites. Severity is Medium rather than High because the window is narrow, but the risk is real given that downstream gating consumes these files.
- **Action Required**: Extract an atomic text-write helper (mirror `_write_json`) and use it in both `_save_adr` and `_save_traceability`.

---

#### 6. [ACCEPT] [Medium] Generated docs not added to `planning_files` — invisible to downstream gating

- **Critic**: not flagged
- **Cross**: "`agent_launcher.py` prints only `prepared.planning_files`; `execute()` records only those in dashboard output. `ApprovalGate` snapshots only `_DOC_FILES`. New artifacts are neither surfaced nor guarded."
- **Judgment**: Cross provides specific call-site evidence. The diff shows `_save_adr`/`_save_traceability` write files but return `None`. Nothing appends the paths to `PreparedProject`. The feature is inert from any user-visible or gating perspective.
- **Action Required**: Have `_save_adr`/`_save_traceability` return `Path`; append returned paths to `planning_files` inside `prepare()`; decide explicitly whether they enter the `ApprovalGate` `_DOC_FILES` set.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Wrong evidence filename — never loaded | High | ACCEPT | Cross |
| 2 | Fallback ADR persisted as "Accepted" | High | ACCEPT | Critic |
| 3 | Empty traceability always written | High | ACCEPT | Critic |
| 4 | `_load_evidence` swallows all exceptions | High | ACCEPT | Critic |
| 5 | Non-atomic writes in `_save_*` | Medium | ACCEPT | Both |
| 6 | Generated docs invisible to downstream | Medium | ACCEPT | Cross |

---

### Recommendations

Fix in this order — #1 unblocks diagnosis of all others:

1. **Fix the filename** (`_load_evidence`): align slug derivation with `researcher.py:1069`, or pass evidence content directly from `collect_project_evidence()`.
2. **Fix the fallback sentinel** (`_call_llm_raw`): return `""` on exception so `if _adr_md:` is meaningful.
3. **Fix the empty-table guard** (`TraceabilityGenerator.generate`): `if not rows: return ""` before building `table_lines`.
4. **Narrow the exception clause** (`_load_evidence`): `except json.JSONDecodeError` + `logging.warning`; re-raise I/O errors.
5. **Make writes atomic** (`_save_adr`, `_save_traceability`): use `tempfile + os.replace` consistent with `_write_json`.
6. **Surface paths downstream** (`_save_adr`, `_save_traceability`): return `Path`, append to `planning_files`, decide gate membership.