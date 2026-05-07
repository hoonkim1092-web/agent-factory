# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 17:22
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. One High data-integrity defect (fallback claim IDs) plus five Medium issues. All are merge-blocking only if evidence files are considered a correctness guarantee — otherwise documentable risks.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] Fallback claim path emits `S001` IDs — sources list has no matching entry
- **Critic**: "plain-string claim fallback at line 675 generates `S{i:03d}`; sources now use `web_001`/`local_001` format"
- **Cross**: "both string claims and dict claims without `source_ids` key produce `S001`; absent from emitted `sources[]`"
- **Judgment**: Both reviewers independently confirm the same defect. `_synthesize_structured_evidence()` instructs the LLM to cite `web_001`-style IDs (lines 498–505), and `_emit_evidence_files()` writes those same IDs into `sources[]` (line 657). Any evidence file that hits the fallback branch will have a `claim.source_id` that references a nonexistent source — silent structural corruption.
- **Action Required**: At line 672 (llm_source_ids fallback) and line 675 (plain-string fallback), replace `f"S{min(i, len(sources)):03d}"` with `sources[min(i, len(sources)) - 1]["source_id"] if sources else ""`.

---

#### 2. [ACCEPT] [Medium] Non-atomic writes for evidence and coverage artifacts
- **Critic**: "lines 684, 736, 747 use `Path.write_text()` — truncated files on crash, same as code-review §3.3 M10"
- **Cross**: "`ProjectPipeline._write_json()` already uses `tempfile` + `os.replace()`; new artifacts bypass this"
- **Judgment**: Both reviewers flag the same three write sites. The existing atomic-write helper is available in the codebase (`core/project_pipeline.py:128–136`); this PR simply doesn't use it for the three new outputs. Low probability of triggering in practice, but the fix cost is minimal.
- **Action Required**: Use `tempfile.NamedTemporaryFile` + `os.replace()` (or reuse `ProjectPipeline._write_json()`) for `*-evidence.json`, `*-coverage.json`, and `*-coverage.md`.

---

#### 3. [ACCEPT] [Medium] Coverage report silently returns `{}` for `requires_web=True` research
- **Critic**: Not flagged directly (flagged `__file__` path resolution for the same manifest — see Finding 4)
- **Cross**: "`_domain_checklist` is only loaded in the non-`requires_web` branch (line 947); `_emit_coverage_report()` called at line 1073 with `None`, returns `{}`"
- **Judgment**: Single-reviewer finding, but code evidence is unambiguous — the manifest load is inside the branch that `requires_web` research never enters. Coverage reporting is silently a no-op for all web-backed domain queries, which defeats the feature's purpose.
- **Action Required**: Move `self._domain_checklist = self._load_domain_manifest(research_plan.domain)` to before the `requires_web` branch split so all modes share coverage behavior.

---

#### 4. [ACCEPT] [Medium] `__file__` in coverage manifest path — frozen build fails silently
- **Critic**: "lines 604, 704: `Path(__file__).parent.parent / 'config' / 'coverage_manifests'` resolves to `.exe` parent in PyInstaller, manifest not found, coverage always empty"
- **Cross**: Not flagged (flagged the `requires_web` branch gap instead — related failure mode)
- **Judgment**: Single-reviewer finding, but this is a documented AF-specific pattern (PyInstaller `__file__` breakage). The fix is mechanical and the risk in frozen builds is a silent empty result — same symptom as Finding 3 but from a different cause. Strong evidence.
- **Action Required**: Replace `Path(__file__).parent.parent` with `Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))` at lines 604 and 704. Confirm `coverage_manifests/*.yaml` is listed in `af.spec` datas.

---

#### 5. [ACCEPT] [Medium] `trust_score` overwritten with `relevance_score` in evidence JSON
- **Critic**: Not flagged
- **Cross**: "`_collect_web_references()` computes authority-domain `trust_score`; `_build_source_pack()` drops it; `_pack_web` path writes `relevance_score` into the `trust_score` field"
- **Judgment**: Single-reviewer finding. Code path is traceable: `_build_source_pack()` at lines 405–419 does not forward `trust_score`, so `_emit_evidence_files()` line 648 silently substitutes `relevance_score`. Both fields exist, they measure different things, and consumers of the evidence JSON will read incorrect authority scores.
- **Action Required**: Preserve `trust_score` when building `source_pack` entries for web refs; use `s.get("trust_score", 0.0)` (not `relevance_score`) in `_emit_evidence_files()`. Keep `relevance_score` as a separate field.

---

#### 6. [ACCEPT] [Medium] `_local_pipelines` dict grows without bound in long-lived instances
- **Critic**: "lines 43, 299: each distinct `root` path adds an `IngestionPipeline` (in-memory document index) with no eviction"
- **Cross**: Not flagged
- **Judgment**: Single-reviewer finding. The concern is valid for daemon-mode usage where many workspaces are processed over time — `IngestionPipeline` holds a full document index in memory. The fix is advisory for the current PR but warrants a cap before any daemon/server deployment.
- **Action Required**: Apply `maxsize=3` LRU eviction (e.g. `functools.lru_cache` on a factory or a manual `OrderedDict` cap) to `_local_pipelines`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Fallback claim IDs (`S001`) not in sources | High | ACCEPT | Both |
| 2 | Non-atomic evidence/coverage writes | Medium | ACCEPT | Both |
| 3 | Coverage report empty for `requires_web` domain | Medium | ACCEPT | Cross |
| 4 | `__file__` frozen-build incompatibility | Medium | ACCEPT | Critic |
| 5 | `trust_score` overwritten with `relevance_score` | Medium | ACCEPT | Cross |
| 6 | `_local_pipelines` unbounded growth | Medium | ACCEPT | Critic |

---

### Recommendations

- **Fix before merge (data integrity)**: Finding 1 — fallback claim ID is a silent structural defect in every evidence file that hits the string-claim path.
- **Fix before merge (correctness)**: Finding 3 — coverage report is a no-op for all web research; the feature is essentially disabled for its primary use case.
- **Fix before merge (correctness)**: Finding 5 — trust scores in evidence JSON are wrong for all web sources.
- **Fix before frozen build**: Finding 4 — `__file__` path will fail silently in `dist/af.exe`; verify `af.spec` datas at the same time.
- **Fix at low cost now**: Finding 2 — atomic-write helper already exists; three sites to update.
- **Defer to next session (low-urgency)**: Finding 6 — LRU cap for `_local_pipelines`; only matters for long-running daemon instances.