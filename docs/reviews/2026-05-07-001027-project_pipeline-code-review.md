# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-05-07 00:10
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Two High/Medium clusters require fixes before merge is advisable; no single finding is a hard blocker by definition, but the silent-failure + path-content inconsistency pair creates a data-integrity risk in prod paths.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Silent exception swallowing hides spec-reload failures
- **Critic**: `except Exception: pass` at `:907-911` causes a key to be silently omitted from `_specs_dict`, injecting an incomplete `domain_specs_summary` into the prompt with no signal to the caller.
- **Cross**: Not flagged independently, but finding #2 below is a direct consequence of the same block.
- **Judgment**: The bare `except: pass` pattern is explicitly listed in `code-review.md §3.2` as a High anti-pattern. The diff introduces it in new code. Evidence is unambiguous.
- **Action Required**: Add `logger.warning("spec 파일 로드 실패: %s — %s", _p, e)` in the except clause (minimum). Do not suppress the exception silently.

---

#### 2. [ACCEPT] [Medium] `_spec_paths.append(_p)` is outside the try block — path/content split
- **Critic**: `:906` appends `_p` to `_spec_paths` unconditionally before the try-read; a failed read leaves a path in `planning_files` with no matching entry in `domain_specs_summary`.
- **Cross**: Not flagged as a separate finding, but the path-content split is the runtime manifestation of finding #1.
- **Judgment**: The diff clearly shows `_spec_paths.append(_p)` preceding `try: ... _specs_dict[...] = _p.read_text(...)`. A read failure produces path-registered, content-absent state. This is a logic error, not a style issue.
- **Action Required**: Move `_spec_paths.append(_p)` inside the try block, after the successful `read_text` call.

---

#### 3. [ACCEPT] [Medium] Full spec bodies are embedded in every work-item LLM call
- **Critic**: Not flagged.
- **Cross**: `project_brief["domain_specs_summary"] = _specs_dict` at `:914` embeds full generated documents. `generate_work_items()` passes `project_brief` to all four document generators, each of which calls `json.dumps(project_brief)` at `work_item_generator.py:535,573,610,650`.
- **Judgment**: Cross cites four concrete line numbers; the mechanism is verified. Token cost scales with spec size × 4 calls. This is a runtime cost concern with a clear remediation path.
- **Action Required**: Either pass a bounded spec manifest (`{key: {"path":..., "excerpt": first_n_chars}}`) or add a dedicated `domain_specs_context` param injected only into the stages that consume it.

---

#### 4. [ACCEPT] [Medium] Mutated `project_brief` diverges from persisted checkpoint
- **Critic**: Noted as [Info] (side-effect on caller's object).
- **Cross**: `project_brief_path` is written in `prepare_brief()` before `prepare_documents()`; the in-memory dict gains `domain_specs_summary` at `:914`, but the file on disk does not. `agent_launcher.py:417-419` prints `planning_files` including that stale path; `project_pipeline.py:1098` stores the enriched brief in checkpoint metadata, creating a split.
- **Judgment**: Cross provides concrete file and line evidence. The state split is real: disk checkpoint ≠ in-memory state passed downstream.
- **Action Required**: Either re-serialize the enriched brief to `project_brief_path` after injection, or avoid mutating `project_brief` and pass spec context as a separate argument to `generate_work_items()`.

---

#### 5. [ACCEPT] [Low] `_save_specs` partial write can leave orphan spec files (M10 pattern)
- **Critic**: `:228-230` — if `write_text` fails mid-loop, `saved` is a partial list; already-written files become orphans; `_verify_domain_spec` on next run sees those files and takes the `else` (reload) branch with an incomplete spec set.
- **Cross**: Rejected finding #3, but that rejection addressed only whether the return-type change breaks callers — not the orphan-file concern. The two concerns are distinct; the cross-reviewer did not evaluate the M10 scenario.
- **Judgment**: Critic's orphan-file concern is independent of return-type compatibility. The M10 pattern is already registered in the project's known-issues list. The diff activates the blast radius by consuming `saved` in `planning_files`.
- **Action Required**: Document as known risk or apply tempfile+`os.replace` to the write loop (matches existing M10 remediation plan).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Silent exception swallowing in spec reload | High | ACCEPT | Critic (Cross indirect) |
| 2 | `_spec_paths`/`_specs_dict` path-content split | Medium | ACCEPT | Critic |
| 3 | Full spec bodies in every LLM call | Medium | ACCEPT | Cross |
| 4 | Mutated `project_brief` not persisted | Medium | ACCEPT | Cross (Critic Info) |
| 5 | `_save_specs` orphan files on partial write | Low | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 + #2 together** — move `_spec_paths.append(_p)` inside the try block and add a warning log on failure; these two fixes share the same three-line region and fix the High finding.
- **Fix #4** — choose one of: re-write enriched brief to disk after injection, or pass spec context as a separate argument. The in-memory/disk split is the more subtle long-term defect.
- **Defer #3** — passing full spec bodies is a token-cost issue, not a correctness bug; add a TODO and address in a dedicated refactor.
- **Defer #5** — M10 already has a registered plan; this diff does not worsen the write side, only the blast radius via `planning_files`. Document the risk in the M10 tracker.
- **Do not merge** until #1 and #2 are fixed — the path-registered, content-absent inconsistency can silently produce malformed work items in any run where a spec file is unreadable.