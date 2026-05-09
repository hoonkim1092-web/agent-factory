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

Two Critical findings require fixes before merge. Five additional High/Medium findings are documented.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [Critical] Non-atomic file writes — 3 output locations
- **Critic**: Direct `.write_text()` at lines 661, 712, 723 — truncates to 0 bytes on crash/kill, same pattern as the already-fixed `dashboard.py:H5a` and `checkpoint.py:C2`
- **Cross**: Not flagged independently, but the same functions are cited in finding #3 (CWD issue)
- **Judgment**: Strong evidence — the fix pattern is established in this codebase (`temp + Path.replace()`), and three new sites bypass it. Accepted on one-reviewer basis given direct code evidence.
- **Action Required**: For each of the three `.write_text()` calls, write to a `.tmp` sidecar then `Path.replace()` atomically, matching the `dashboard.py:H5a` fix.

---

#### 2. [ACCEPT] [Critical] `__file__` used for config path resolution — frozen build silent no-op
- **Critic**: `Path(__file__).parent.parent / "config" / "coverage_manifests"` at lines 604 and 680 — in a PyInstaller `af.exe`, `__file__` resolves inside the archive; `path.exists()` returns `False` silently, manifest feature no-ops entirely on every frozen run
- **Cross**: Not flagged
- **Judgment**: Accepted on one-reviewer basis. The AF checklist explicitly flags this pattern; `config_paths.PROJECT_ROOT` already exists to solve exactly this. Two new sites bypass it.
- **Action Required**: Replace both `Path(__file__).parent.parent / "config" / ...` with `config_paths.PROJECT_ROOT / "config" / "coverage_manifests" / f"{domain}.yaml"`.

---

#### 3. [ACCEPT] [High] Evidence sidecars written to process CWD, not caller workspace
- **Critic**: Not flagged
- **Cross**: `_emit_evidence_files()` and `_emit_coverage_report()` use `Path(os.getcwd()) / "docs" / "research"`; production caller at `project_pipeline.py:696-728` passes explicit `target_workspace` and writes its own sidecars there — evidence files land in the AF repo dir, not the project workspace
- **Judgment**: Accepted. Cross reviewer cites concrete caller code (`project_pipeline.py:696-699`, `:726-728`) proving the mismatch. This is a silent correctness failure for every multi-workspace run.
- **Action Required**: Add `workspace: str | Path` parameter to `_emit_evidence_files()` and `_emit_coverage_report()`; replace `os.getcwd()` with the passed workspace. Update callers accordingly.

---

#### 4. [ACCEPT] [High] Broken claim→source mapping in evidence JSON
- **Critic**: `min(i, len(sources))` at line 654 pins all overflow claims to the last source ID — claims C004+ all show `S003` when there are 3 sources
- **Cross**: `_emit_evidence_files()` also converts dict claims (`{"claim": ..., "source_ids": [...]}`) to bare strings via `str(claim_text)`, losing the structured mapping that `_synthesize_structured_evidence()` produced and `research_verifier.py:222-240` expects
- **Judgment**: Both reviewers flag the same function for related but distinct bugs. Merged. The diff confirms both: `str(claim_text)` on line 649 and the `min(i, len(sources))` formula on line 654.
- **Action Required**: (a) Normalize claims — if item is a dict, extract `claim["claim"]` and `claim["source_ids"]`; if string, treat as legacy. (b) Fix source assignment — use modulo cycling or explicit `""` for unmapped claims. Do not pin overflow to the last source.

---

#### 5. [ACCEPT] [High] Recovery loop: unbounded API calls + sufficiency check ignores web_refs
- **Critic**: `_unmet` is not bounded; with N manifest fields × 2 calls × 3 rounds = up to 90 Tavily calls; no deduplication across rounds
- **Cross**: Sufficiency is re-evaluated at line 927 with `_is_sufficient(local_refs, ...)` — `web_refs` from recovery are never included, so the loop can exhaust all rounds even when web evidence already covers all gaps; `research_verifier.py:127-131` penalizes `sufficiency_gate_passed=False`
- **Judgment**: Both reviewers flag the same loop (lines 927-940) for complementary failure modes. Combined: the loop wastes API calls AND cannot terminate early via success. Both are confirmed by the diff.
- **Action Required**: (a) Cap total `web_refs` growth (e.g. `MAX_WEB_REFS = 12`) or deduplicate queries across rounds. (b) After each recovery round, re-evaluate `_identify_unmet_gaps(local_refs, web_refs, checklist)` and exit when `_unmet` is empty.

---

#### 6. [ACCEPT] [High] `_load_domain_manifest` called 4× for the same domain per call
- **Critic**: Lines 922, 1008, 1046, and 680 each read the same YAML from disk; `_final_domain_checklist` at line 1008 is identical to `_domain_checklist` still in scope from line 922; `_emit_coverage_report` also re-reads `match_keywords` internally
- **Cross**: Not flagged
- **Judgment**: Accepted on one-reviewer basis. The diff confirms four call sites with no caching. Beyond I/O cost this creates a test-time inconsistency hazard.
- **Action Required**: Load once at the top of the `else` branch, store result, pass through. Refactor `_emit_coverage_report` to accept `match_keywords: dict` as a parameter.

---

#### 7. [ACCEPT] [Medium] Magic thresholds without named constants
- **Critic**: `0.7` coverage threshold appears independently in `_is_sufficient` (line 765) and `_emit_coverage_report` (line 700); `len(missing) >= 3` and round counts (2/3) are similarly opaque
- **Cross**: Not flagged
- **Judgment**: Accepted. The diff confirms two separate `0.7` literals with no shared constant — silent drift is guaranteed as coverage policy evolves.
- **Action Required**: Define module-level constants: `_COVERAGE_PASS_RATE = 0.70`, `_MAX_MISSING_FIELDS = 3`, `_MAX_RECOVERY_ROUNDS_DEEP = 3`, `_MAX_RECOVERY_ROUNDS_DEFAULT = 2`. Reference in both methods.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Non-atomic file writes (3 locations) | Critical | ACCEPT | Critic |
| 2 | `__file__` config path — frozen build no-op | Critical | ACCEPT | Critic |
| 3 | Evidence sidecars written to CWD not workspace | High | ACCEPT | Cross |
| 4 | Broken claim→source mapping in evidence JSON | High | ACCEPT | Both |
| 5 | Recovery loop: unbounded API calls + sufficiency ignores web_refs | High | ACCEPT | Both |
| 6 | `_load_domain_manifest` called 4× per invocation | High | ACCEPT | Critic |
| 7 | Magic thresholds without named constants | Medium | ACCEPT | Critic |

---

### Recommendations

- **Before anything else**: Add `workspace` parameter to `_emit_evidence_files` and `_emit_coverage_report` — this is the root cause of findings 1 and 3 both affecting the same output functions; fixing CWD first may simplify the atomic-write refactor.
- Wrap all three file writes in the temp+replace pattern from `dashboard.py:H5a` as a single atomic helper (avoids repeating the pattern three times).
- Replace both `Path(__file__)` manifest path constructions with `config_paths.PROJECT_ROOT` in a single pass.
- Fix claim serialization (finding 4) and loop sufficiency (finding 5) together — they are in the same call path and share the `web_refs` list.
- Load manifest once and extract `match_keywords` in the same load (finding 6) — eliminates the redundant reads and the four-call problem.
- Name the threshold constants (finding 7) last, low risk.