# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 17:23
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Five High/Medium issues exist — two are confirmed data-integrity bugs by both reviewers. No merge blocker by severity definition, but the two cross-reference integrity issues should be treated as pre-merge requirements.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] String claims still produce dangling `S001` source IDs
- **Critic**: "fallback at lines 672/675 generates `S{i:03d}` format; sources array uses `web_001` format — claim→source cross-reference silently breaks"
- **Cross**: "fallback sources created as `web_{i:03d}` at line 657; string claims still assign `sid = f"S{...}"` at line 675 — test at line 152 only checks counts, not referential integrity"
- **Judgment**: Both reviewers independently confirm the same defect from different angles. The `_pack_web` path was fixed but the string-claim fallback path was not. Any evidence file with a string claim has a structurally invalid `source_id` that cannot be resolved in `sources[]`. Unambiguous data-integrity defect.
- **Action Required**: Replace `f"S{min(i, len(sources)):03d}"` at lines 672 and 675 with `sources[min(i, len(sources)) - 1]["source_id"]` when `sources` is non-empty, else `""`.

---

#### 2. [ACCEPT] [High] Non-web citations (`local_001`, `llm_001`) persisted without matching sources
- **Critic**: Not flagged
- **Cross**: "`_emit_evidence_files()` filters `source_pack.sources` to `source_type == 'web'` (line 641), but `_synthesize_structured_evidence()` gives the LLM all source IDs including `local_001`/`llm_001` (lines 468-505). LLM citing `local_001` produces a claim pointing to an absent source in the persisted file."
- **Judgment**: Strong code evidence — `_build_source_pack()` creates `local_001` at line 423 and `llm_001` at line 439; `_emit_evidence_files()` only writes web-typed sources. Any non-web citation the LLM produces creates a dangling reference identical in structure to Finding 1. Second confirmed data-integrity defect.
- **Action Required**: Either (a) persist all `source_pack.sources` with normalized fields, or (b) filter local/llm sources from the synthesis prompt before passing to the LLM so it can only cite web sources that will be persisted.

---

#### 3. [ACCEPT] [High] Duplicate `_router.classify()` call — `plan` variable is dead
- **Critic**: "`plan` at line 1280 used only for print; `retrieval_plan` at line 1407 called again with identical args and is the one actually used for evidence_pack output. The first call's result is discarded."
- **Cross**: Not flagged
- **Judgment**: Critic provides specific line evidence (1280 vs 1407). The dead variable is provable from the diff alone without runtime. If `classify()` has any I/O or computational cost this is wasteful; at minimum it is misleading. Single-reviewer finding but evidence is unambiguous.
- **Action Required**: Remove the `plan = self._router.classify(...)` call at line 1280. Move `retrieval_plan = self._router.classify(...)` from line 1407 to that position and update the print on line 1284 to reference `retrieval_plan`.

---

#### 4. [ACCEPT] [Medium] `trust_score` now stores relevance, not authority
- **Critic**: Not flagged
- **Cross**: "`_collect_web_references()` computes `trust_score` from authority domain whitelist (lines 372-389); `_build_source_pack()` only carries `relevance_score` (line 417); `_emit_evidence_files()` writes that as `trust_score` (line 648) — field semantics are now inconsistent depending on call path."
- **Judgment**: Clear semantic regression confirmed by code evidence. Downstream consumers expecting authority-derived trust will silently get a relevance ranking instead. Medium severity — no crash, but misleads any consumer of the evidence file.
- **Action Required**: Add `trust_score` to web entries in `_build_source_pack()` (carry it from `_collect_web_references()`) and write that field in `_emit_evidence_files()`. Keep `relevance_score` as a separate field.

---

#### 5. [ACCEPT] [Medium] `research()` feedback loop ignores caller-supplied workspace
- **Critic**: "`SkillFeedbackLoop.for_workspace(os.getenv('AGENT_PROJECT_ROOT') or os.getcwd())` at line 1383 — `research()` has no `workspace` parameter, so feedback history always loads from env/cwd regardless of what the pipeline caller intended."
- **Cross**: REJECTED a related issue (file write path) as already fixed via `collect_project_evidence()` — but did not examine the feedback loop initialization inside `research()` itself.
- **Judgment**: The Cross rejection was for the emit-function workspace fix (confirmed correct). The Critic's issue is a separate code path — the `SkillFeedbackLoop` initialization in `research()`, not the emit path. No contradiction; the Cross reviewer simply did not examine line 1383. Critic evidence is specific and credible.
- **Action Required**: Add `workspace: str | None = None` to `research()` signature; derive `target_workspace = os.path.abspath(workspace or os.getenv("AGENT_PROJECT_ROOT") or os.getcwd())` and pass to `SkillFeedbackLoop.for_workspace()`.

---

#### 6. [ACCEPT] [Medium] Silent `except Exception: pass` swallows emit failures
- **Critic**: "line 1082 — disk full, permission errors, JSON serialization failures all silently pass; user has no way to know evidence.json / coverage.json were not written"
- **Cross**: Not flagged
- **Judgment**: No contradicting evidence. Bare `except: pass` on file-write paths is a well-established defect pattern. Single-reviewer but strong general-practice evidence. Previously documented as "silent fallback" in code-review.md §3.2.
- **Action Required**: Replace `except Exception: pass` with `except Exception as e: print(f"[researcher] emit failed: {e}", file=sys.stderr)` at minimum.

---

#### 7. [ACCEPT] [Medium] Non-atomic file writes in new emit functions
- **Critic**: "lines 684, 736-737, 747 — three new files all use direct `write_text()`; interrupted write leaves partial JSON on disk. Previously documented as M10 in code-review.md §3.3."
- **Cross**: Not flagged
- **Judgment**: Pattern is consistent with prior M10 finding in code-review.md. Critic correctly identifies that the new `_emit_evidence_files` and `_emit_coverage_report` functions repeat the pattern rather than using the atomic write already established in `checkpoint.py`.
- **Action Required**: Apply `tempfile.NamedTemporaryFile` + `os.replace()` pattern to all three write sites (lines 684, 736, 747), following the checkpoint.py C2 fix.

---

### Previously Flagged Issues — Resolved

| Issue | Status |
|-------|--------|
| H1 — `os.getcwd()` in `_emit_evidence_files` / `_emit_coverage_report` | **Fixed** — `workspace` param added; `collect_project_evidence()` passes `target_workspace` (lines 1066-1079) |
| Dict claims stringified / `source_ids` lost | **Fixed** — `isinstance(claim_text, dict)` branch now extracts `claim` and reads `source_ids` (line 669-672) |

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | String claims → dangling `S001` IDs | High | ACCEPT | Both |
| 2 | Non-web citations absent from persisted sources | High | ACCEPT | Cross |
| 3 | Duplicate `classify()` / dead `plan` variable | High | ACCEPT | Critic |
| 4 | `trust_score` semantics changed to relevance | Medium | ACCEPT | Cross |
| 5 | `research()` feedback loop ignores workspace | Medium | ACCEPT | Critic |
| 6 | Silent `except Exception: pass` on emit | Medium | ACCEPT | Critic |
| 7 | Non-atomic writes in new emit functions | Medium | ACCEPT | Critic |

---

### Recommendations

- **Pre-merge (data integrity):** Fix findings 1 and 2 together — both break `claims[].source_id` → `sources[].source_id` referential integrity. Add a test asserting every `source_id` in `claims[]` exists in `sources[]`.
- **Pre-merge (correctness):** Fix finding 3 (duplicate `classify()`) — straightforward refactor with no behavioral risk.
- **Pre-merge (correctness):** Fix finding 4 (`trust_score` semantics) — carry `trust_score` through `_build_source_pack()` to avoid silent field meaning change.
- **Can merge with tracked debt:** Findings 5-7 are real but lower-risk; document in code-review.md and fix in a follow-up commit.
- **Add referential integrity test:** `tests/test_research_p1_quality_gate.py:152` exercises the string-claim path but only checks counts. Add an assertion: `all(c["source_id"] in {s["source_id"] for s in evidence["sources"]} for c in evidence["claims"] if c.get("source_id"))`.