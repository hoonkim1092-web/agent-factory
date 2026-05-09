# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 15:14
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

BLOCK = Critical findings #1 and #2 must be fixed before merge. Additionally, High findings #3–#6 represent functional correctness bugs that will silently corrupt output.

---

### Aggregated Findings (9 total)

#### 1. [ACCEPT] [Critical] `__file__` used for config path — broken in frozen build
- **Critic**: "`Path(__file__).parent.parent / config / coverage_manifests` resolves to the executable path in PyInstaller builds. Both `_load_domain_manifest` and `_emit_coverage_report` silently return `None`/skip loading — features permanently disabled in `dist/af/af.exe` with no error."
- **Cross**: Not flagged.
- **Judgment**: Strong accept. `__file__` behavior in frozen builds is well-established. The codebase already has `config_paths.PROJECT_ROOT` guarded for this exact scenario. Two call sites (lines 604, 681) commit the same error.
- **Action Required**: Replace both `Path(__file__).parent.parent / "config" / ...` with `config_paths.PROJECT_ROOT / "config" / "coverage_manifests" / f"{domain}.yaml"`.

---

#### 2. [ACCEPT] [Critical] Non-atomic file writes in emit methods
- **Critic**: "`write_text()` truncates before writing — a crash or KeyboardInterrupt mid-write leaves corrupt/empty files at lines 661–663, 712–713, 723. Known M10 pattern in `code-review.md`; this change adds 3 new instances."
- **Cross**: "Same pattern at line 661 for all three artifacts. `ProjectPipeline._write_json()` already uses `temp + os.replace()` at `project_pipeline.py:128–137`."
- **Judgment**: Both reviewers agree. The fix pattern already exists in the codebase. No excuse to not use it.
- **Action Required**: Write to a `.tmp` sibling, then `os.replace(tmp, final_path)` for all three artifact writes. Reuse or extract the `_write_json` helper from `project_pipeline.py`.

---

#### 3. [ACCEPT] [High] `_identify_unmet_gaps`: first condition never lowercased — systematic false misses
- **Critic**: "`item.replace('_', ' ')` preserves original case, but `joined` is `.lower()`. For any mixed-case checklist item, the first condition is always `True` (no match). The second condition `item.lower()` retains underscores and also never matches space-separated text in `joined`. Items with underscores or uppercase are always classified as unmet."
- **Cross**: Not flagged.
- **Judgment**: Strong accept — the code evidence is unambiguous. `"HTTP_Status_Code".replace("_", " ")` → `"HTTP Status Code"` will never appear in a `.lower()` string. This inflates `_unmet` every round, causing unnecessary recovery fetches.
- **Action Required**: Change condition to `item.replace("_", " ").lower() not in joined` as the sole check (line 626).

---

#### 4. [ACCEPT] [High] `web_refs` overwritten when gap resolution succeeds
- **Critic**: "When `_unmet` empties after targeted per-gap fetches, `if not _unmet` fires and **assigns** (not extends) `web_refs` with a broad untargeted fetch, discarding all targeted evidence collected during recovery."
- **Cross**: Not flagged.
- **Judgment**: Accept — the diff at lines 931–937 clearly shows `web_refs =` (assignment) inside `if not _unmet`, which is the success branch. The recovery loop's targeted work is silently thrown away on success. This is a semantic inversion bug.
- **Action Required**: Change `web_refs = self._collect_web_references(task_input)` to `web_refs.extend(...)` (line 937), or skip the broad fetch entirely when targeted refs already covered the gaps.

---

#### 5. [ACCEPT] [High] Coverage `block` result produced but no caller enforces it
- **Critic**: Not flagged.
- **Cross**: "`_emit_coverage_report()` returns `{'block': True}` but `ProjectPipeline` at `project_pipeline.py:669–700` stores `research_evidence` and passes it to `research_project_brief()` without checking `coverage_report.block`. The gate is computed and written to disk but never acted upon."
- **Judgment**: Strong accept. Cross provided specific line numbers in `project_pipeline.py` confirming the caller path. The entire B5 coverage gate feature is dead on arrival — the report is a file artifact only.
- **Action Required**: In `ProjectPipeline`, after the verify step, add: `if research_evidence.get("coverage_report", {}).get("block"): <stop or degrade>` before entering brief generation.

---

#### 6. [ACCEPT] [High] Evidence artifact corrupts structured claim shape and source IDs
- **Critic**: Not flagged.
- **Cross**: "`_synthesize_structured_evidence()` returns `source_backed_claims` as dicts `{'claim': ..., 'source_ids': [...]}`, but `_emit_evidence_files()` treats each item as a scalar (`str(claim_text)`) and invents sequential `S001, S002…` IDs from `web_refs` position — losing the actual claim-to-source mapping. `research_verifier.py:221–224` reads `source_ids` from these artifacts downstream."
- **Judgment**: Strong accept. The diff at line 649 shows `for i, claim_text in enumerate(claims_raw, 1)` treating dict items as scalars. The downstream verifier depends on the claim-source mapping being correct. This silently corrupts verifier output.
- **Action Required**: In `_emit_evidence_files`, normalize dict claims: `claim_text.get("claim")` and `claim_text.get("source_ids")` instead of `str(claim_text)`, preserving the original source ID mapping.

---

#### 7. [ACCEPT] [Medium] `os.getcwd()` ignores requested `workspace` — wrong output dir under concurrent use
- **Critic**: "`os.getcwd()` is the process working directory at call time. Under `ThreadPoolExecutor` or subprocess workers with different cwd, output lands in the wrong directory. `config_paths.PROJECT_ROOT` exists for this." (lines 636, 695)
- **Cross**: "`collect_project_evidence()` resolves `target_workspace` at line 889 and `ProjectPipeline` passes `workspace=target_workspace` at `project_pipeline.py:642`, but emit helpers never receive it — artifacts always go to the runner's cwd." (line 636)
- **Judgment**: Both reviewers agree, citing different dimensions of the same bug (cwd fragility + workspace parameter ignored). Merged.
- **Action Required**: Pass `target_workspace` (or a resolved `out_dir`) into `_emit_evidence_files` and `_emit_coverage_report`. Write under `Path(target_workspace) / "docs" / "research"`.

---

#### 8. [ACCEPT] [Medium] `_load_domain_manifest` called 3–4× per invocation for same domain
- **Critic**: "Same YAML file read at lines 922, 1008, 1046, plus a 4th read inside `_emit_coverage_report` at line 681. Total: 4 disk reads for one file per `collect_project_evidence()` call."
- **Cross**: Not flagged.
- **Judgment**: Accept. Confirmed by diff: `_load_domain_manifest` is called at each of the three listed lines, and `_emit_coverage_report` re-opens the same YAML independently. Not a correctness bug but a clear structural inefficiency with a simple fix.
- **Action Required**: Load once at line 922. Pass `_domain_checklist` and extracted `match_keywords` to all callers. Remove the redundant re-load inside `_emit_coverage_report`.

---

#### 9. [ACCEPT] [Low] Magic threshold constants duplicated without names
- **Critic**: "`0.7` appears 3 times across `_emit_coverage_report` and `_is_sufficient`. Hardcoded `3` missing-field threshold in `_emit_coverage_report` has no equivalent in `_is_sufficient`. Calibration risk." (lines 656, 706, 765)
- **Cross**: Not flagged.
- **Judgment**: Accept, low severity. Not a blocker but a maintenance hazard given the threshold is load-bearing for the block decision.
- **Action Required**: `_COVERAGE_THRESHOLD = 0.7` and `_BLOCK_MISSING_COUNT = 3` as module-level constants.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `__file__` broken in frozen build | Critical | ACCEPT | Critic |
| 2 | Non-atomic file writes (3 sites) | Critical | ACCEPT | Both |
| 3 | `_identify_unmet_gaps` case mismatch | High | ACCEPT | Critic |
| 4 | `web_refs` overwritten on success | High | ACCEPT | Critic |
| 5 | Coverage `block` never enforced by caller | High | ACCEPT | Cross |
| 6 | Evidence artifact corrupts claim/source shape | High | ACCEPT | Cross |
| 7 | `os.getcwd()` ignores `workspace` param | Medium | ACCEPT | Both |
| 8 | `_load_domain_manifest` called 4× per invocation | Medium | ACCEPT | Critic |
| 9 | Magic threshold constants duplicated | Low | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 first** (1 line each, 2 sites): swap `Path(__file__).parent.parent` → `config_paths.PROJECT_ROOT` before any other work, since it makes the entire coverage feature silently dead in builds.
- **Fix #2 alongside #1**: extract an `_atomic_write(path, content)` helper using `tempfile + os.replace`; apply to all 3 artifact sites in one pass.
- **Fix #6 and #7 together**: `_emit_evidence_files` and `_emit_coverage_report` both need `out_dir` passed in — do it in one refactor and fix the `workspace` ignored bug at the same time.
- **Fix #3** (1 line): `item.replace("_", " ").lower() not in joined` — trivial but high impact on recovery loop correctness.
- **Fix #4** (1 word): `web_refs =` → `web_refs.extend(...)`.
- **Fix #5**: add the `coverage_report.block` check in `ProjectPipeline` before brief generation — the feature was designed but the gate was never wired.
- **Fix #8**: load manifest once, pass result downstream — reduces disk I/O and eliminates the 4th silent-failure opportunity.
- **Fix #9** (deferred): module-level constants, low urgency, can batch with next refactor pass.