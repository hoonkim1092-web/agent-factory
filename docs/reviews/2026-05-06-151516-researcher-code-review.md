# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 15:15
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Eight High/Medium issues exist across both reviews — all accepted. Can merge with documented risks, but three of the High issues directly affect artifact correctness and should be prioritized.

---

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [High] Emitted artifacts written to process CWD, not project workspace
- **Critic**: not flagged
- **Cross**: `_emit_evidence_files()` and `_emit_coverage_report()` use `Path(os.getcwd()) / "docs" / "research"` while `ProjectPipeline.prepare_brief()` writes other artifacts under `target_workspace`. Files can land in the AF repo root instead of the generated project workspace.
- **Judgment**: Strong evidence — `core/project_pipeline.py:641-645` passes `workspace=target_workspace`; `core/project_pipeline.py:726-728` writes adjacent artifacts there. The new methods break this contract. No counter-evidence.
- **Action Required**: Add `workspace: Path` parameter to `_emit_evidence_files()` and `_emit_coverage_report()`; use it as the base path instead of `os.getcwd()`. Pass `target_workspace` from the call sites.

---

#### 2. [ACCEPT] [High] `coverage_report.block` computed but never enforced
- **Critic**: not flagged
- **Cross**: `_emit_coverage_report()` returns `block=True` for insufficient coverage; `collect_project_evidence()` stores it in `initial_evidence["coverage_report"]` but `ProjectPipeline` never checks it — pipeline continues to brief/document generation unconditionally.
- **Judgment**: Accepted. Design doc intent is that `block=True` prevents downstream stages. `core/project_pipeline.py:669-687` only checks `ResearchVerifier` status. The emitted field is a no-op as currently wired.
- **Action Required**: After `ResearchVerifier.verify()` in `ProjectPipeline`, read `research_evidence["coverage_report"].get("block")` and raise or return early if `True`. Alternatively, have `ResearchVerifier.verify()` surface this as a blocking result.

---

#### 3. [ACCEPT] [High] `sufficient` flag stale after max-rounds exhaustion
- **Critic**: When the recovery loop exits via `_recovery_rounds >= _max_rounds` (not `break`), `sufficient` holds the pre-collection value from the final round's check. Web refs gathered in the last pass are never re-evaluated. `initial_evidence["sufficiency_gate_passed"]` can report `False` incorrectly.
- **Cross**: not flagged (rejected a separate "unbounded loop" concern, not this flag-staleness issue)
- **Judgment**: Accepted. The diff confirms the pattern at lines 926–940: `sufficient` is set at loop top, `web_refs` are extended at loop bottom, and `_recovery_rounds += 1` exits the loop before any re-check. Logic bug, strong evidence.
- **Action Required**: After the `while` loop, add: `sufficient = self._is_sufficient(local_refs, task_input, domain_checklist=_domain_checklist)` to reflect the final accumulated refs.

---

#### 4. [ACCEPT] [High] Claim→source mapping fabricated / structured citations lost
- **Critic**: `source_id` assigned by list position (`S{min(i, len(sources)):03d}`) has no relationship to LLM-extracted `source_backed_claims`. Overflow claims all point to the last source.
- **Cross**: `_synthesize_structured_evidence()` requests structured dicts with `source_ids`; `_emit_evidence_files()` casts each claim to `str(claim_text)` and discards the original citation. `core/research_verifier.py:222-227` expects dict claims and validates their `source_ids`.
- **Judgment**: Both reviewers independently identified the same structural defect from different angles (Critic: fabricated index; Cross: dict-to-string lossy cast). High confidence. The output JSON presents authoritative-looking citations that are false.
- **Action Required**: For dict claims, preserve the original `claim`, `source_ids`, `authority`, `confidence`, `applies_to` fields. Map `web_001`-style IDs to emitted `S001` IDs explicitly. For plain-string claims, set `source_id: ""` and `authority: "unverified"` rather than inventing positional references.

---

#### 5. [ACCEPT] [High] Unbounded `web_refs` list growth across recovery rounds
- **Critic**: `web_refs.extend(...)` inside the gap loop has no total-size cap. With `_max_rounds=3`, `len(_unmet)=N`, `limit=2` per gap: up to `3 × N × 2` entries. A 10-item domain checklist (e.g., poker.yaml) yields 60 refs.
- **Cross**: Rejected a separate concern about infinite loops (correctly — `_max_rounds` caps iterations). This is a distinct issue about accumulated list size, not addressed by that rejection.
- **Judgment**: Accepted. No contradiction — the Cross reviewer's rejection targeted loop termination, not list growth. The code has no per-call cap on `web_refs`. Matches the H2 unbounded-cache pattern in code-review.md.
- **Action Required**: Add a constant (e.g., `_MAX_WEB_REFS = 12`) and guard inside the gap loop: `if len(web_refs) >= _MAX_WEB_REFS: break`.

---

#### 6. [ACCEPT] [Medium] Non-atomic file writes — M10 pattern repeated
- **Critic**: Three new `.write_text()` calls at lines 661, 712, 723 repeat the M10 pattern from code-review.md. Prior instances in `conversation_manager.py`, `ise_strategy_ledger.py`, `pdca_state.py`.
- **Cross**: Same finding — notes that adjacent pipeline code already uses a write helper pattern in `core/project_pipeline.py:720`.
- **Judgment**: Both reviewers agree. Medium severity consistent with existing M10 classification. No new escalation warranted, but the fix is straightforward and precedent exists.
- **Action Required**: Use `tempfile.NamedTemporaryFile(dir=out_dir, delete=False)` + `os.replace(tmp, target)` for all three writes, or route through the existing project-level JSON write helper.

---

#### 7. [ACCEPT] [Medium] YAML manifest file read up to 4× per call
- **Critic**: `_load_domain_manifest` is called at line 922, 1008, and once more inside the `_emit_coverage_report` call at 1046 — which also reads the same file internally at line 684 for `match_keywords`. Four I/O hits per `collect_project_evidence` call.
- **Cross**: not flagged
- **Judgment**: Accepted. Evidence in diff is clear — `_emit_coverage_report` receives `domain_checklist` as a parameter but still re-reads the YAML for `match_keywords`. Medium severity: no correctness issue, but unnecessary repeated I/O and the `match_keywords` load should be consolidated with `_load_domain_manifest`.
- **Action Required**: Extend `_load_domain_manifest` to return both `required_fields` and `match_keywords` (e.g., as a dict or namedtuple). Cache once at the `else`-branch entry and pass downstream; remove the internal YAML read from `_emit_coverage_report`.

---

#### 8. [ACCEPT] [Medium] `__file__`-based manifest path silently disabled in frozen builds
- **Critic**: In a PyInstaller `--onefile` build, `Path(__file__).parent.parent` resolves to `sys._MEIPASS/`, not the project root. If `config/coverage_manifests/` is absent from `af.spec` datas, `_load_domain_manifest` returns `None` silently — domain-aware gating and coverage reports are disabled in the binary with no warning.
- **Cross**: not flagged
- **Judgment**: Accepted. AF-specific frozen-build concern consistent with the existing checklist in code-review.md. No counter-evidence. Medium because this affects the packaged binary only, not the development path.
- **Action Required**: Add `("config/coverage_manifests", "config/coverage_manifests")` to `af.spec` datas. Add a startup-time warning (or `logging.warning`) in `_load_domain_manifest` if the manifest directory is absent.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Artifacts written to CWD, not project workspace | High | ACCEPT | Cross only |
| 2 | `coverage_report.block` not enforced by caller | High | ACCEPT | Cross only |
| 3 | `sufficient` flag stale after max-rounds exhaustion | High | ACCEPT | Critic only |
| 4 | Claim→source mapping fabricated / citations lost | High | ACCEPT | Both |
| 5 | Unbounded `web_refs` list growth | High | ACCEPT | Critic only |
| 6 | Non-atomic file writes (M10 repeated) | Medium | ACCEPT | Both |
| 7 | YAML manifest read 4× per call | Medium | ACCEPT | Critic only |
| 8 | `__file__` path disabled in frozen builds | Medium | ACCEPT | Critic only |

---

### Recommendations

- **Fix #1 and #2 together**: both require tracing the `workspace` parameter through the new emit methods and wiring `coverage_report.block` into `ProjectPipeline`'s gate check — natural to do in one pass.
- **Fix #3**: one-line post-loop re-evaluation of `sufficient`; low risk, high correctness gain.
- **Fix #4**: normalize claim serialization in `_emit_evidence_files()` to preserve dict structure from `_synthesize_structured_evidence()`; remove positional `source_id` fallback.
- **Fix #5**: add `_MAX_WEB_REFS` cap; two lines of code.
- **Fix #6**: consolidate with the atomic-write fix; use the project-level JSON helper already present in `ProjectPipeline`.
- **Defer #7 and #8**: medium priority, no correctness impact in dev mode. Address in a follow-up with the manifest loading refactor and `af.spec` update.