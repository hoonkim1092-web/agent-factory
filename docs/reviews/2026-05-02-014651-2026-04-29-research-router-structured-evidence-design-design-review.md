# Design Review: 2026-04-29-research-router-structured-evidence-design

> Source: docs/2026-04-29-research-router-structured-evidence-design.md
> Date: 2026-05-02 01:46
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

3 Critical findings (Phase 1a detector vacuous, `final_mode` arg-name contradiction, structured-evidence Phase 1a/1b timing contradiction) plus multiple High findings make implementation rework unavoidable. Hold Phase 1a coding until v1.5 patches.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] §4.4.5 detector's `source_pack` obligation is vacuous in Phase 1a — over-triggers deep escalation
- **Critic** (#2): `not evidence.get("source_pack")` is always truthy in Phase 1a because `source_pack` is a Phase 1b artifact (§6.6 line 754: chars stay 0). Detector reduces to `deep_signal AND is_pre_deep`, contradicting the line 384 "evidence vs obligation mismatch" narrative.
- **Cross** (#3): Same issue — any fast/fresh request with `external_stack_score >= 3` will escalate to deep even when web refs are sufficient. References [researcher.py:579](core/researcher.py:579) returning `web_references`, not `source_pack`.
- **Judgment**: Both reviewers independently identified the same vacuous obligation; evidence is conclusive at design.md:372 vs design.md:754.
- **Action Required**: Either (a) replace `not evidence.get("source_pack")` with a Phase 1a–available obligation (e.g., `not evidence.get("web_references") and required_external_stack`, or capability-coverage check on `web_references`), or (b) explicitly mark Phase 1a detector as signal-only and rewrite line 384 narrative; activate `source_pack` check at Phase 1b. Update §4.4.5 + §10.1 final-mode trace accordingly.

#### 2. [ACCEPT] [Critical] §4.4.5 `final_mode` argument name contradicts its semantic role — v1.3 ACCEPT action never applied
- **Critic** (#1): Prior round ACCEPT was "rename `final_mode` → `current_mode` across §0/§4.4.5/§10.1." v1.4 changelog #2 logged OR-merge but omitted the rename; v1.4.1 only touched §12.5. Result: detector's pre-escalation mode is still labeled `final_mode` while immediately checking `is_pre_deep`.
- **Cross**: Not flagged.
- **Judgment**: ACCEPT — direct evidence at design.md:360 and design.md:370. Implementer reading "final_mode" then seeing "is_pre_deep" check will be confused on first encounter; this is a pure naming defect with zero behavior risk but high comprehension cost.
- **Action Required**: Rename `final_mode` → `current_mode` in §4.4.5 code (line 360, 370), §11 Phase 1a item 1 signature (line 1070), §10.1 detector trace (line 945), and §3.2 escalation flow. Add explicit changelog entry in v1.5.

#### 3. [ACCEPT] [Critical] §3.2 vs §3.2-text: Phase 1a structured-evidence timing contradicts itself
- **Critic**: Not flagged.
- **Cross** (#1): §3.2 flow diagram (line 137-138) marks `synthesize_structured_evidence()` as "Phase 1b부터", but immediately below at line 144, the prose says "Phase 1a 단계에서 `synthesize_structured_evidence()`는 fresh/deep/archive 모드에서만 호출된다". §11 Phase 1b item 2 (line 1124-1127) confirms Phase 1b ownership. This affects LLM call count, evidence schema, and verifier inputs.
- **Judgment**: ACCEPT — direct contradiction within the same section. Cross's evidence is unambiguous (design.md:137 vs design.md:144 vs design.md:1124).
- **Action Required**: Remove line 144 prose entirely OR rename Phase 1a output to `evidence_summary` (legacy field) and reserve `structured_evidence` exclusively for Phase 1b. Update §3.2 flow to be unambiguous.

#### 4. [ACCEPT] [High] `data_pipeline` emitted as secondary without mode contract
- **Critic**: Not flagged.
- **Cross** (#2): §4.1 mode table (line 160) lists six modes excluding `data_pipeline`; §4.2.1 (line 241) emits it as a secondary; §10.2 (line 999, 1013) treats it as a secondary mode. No tool gating, no `requires_web` contract, no verifier expectations defined.
- **Judgment**: ACCEPT — strong evidence; this is a dead-vocabulary risk previously called out for `statistical_analysis`/`scheduled_maintenance` (v1.3 R2-3) and re-introduced.
- **Action Required**: Either (a) add `data_pipeline` row to §4.1 mode table with `requires_web`/`requires_notebooklm`/capability hints, or (b) rename "secondary_modes" to "analysis_tags" so implementers don't treat them as runnable modes. Update §10.2 wording accordingly.

#### 5. [ACCEPT] [High] §6.6 `mode_escalation_gap` singular vs §4.4.5 dual-gap emit
- **Critic** (#3): Diagnostics field (line 741) is single-string while §4.4.5 line 374-375 emits two gaps simultaneously. Example value `architecture_coverage_low` is now Phase 1b verifier territory (§9.3 line 888), not a Phase 1a detector enum — stale example.
- **Cross**: Not flagged.
- **Judgment**: ACCEPT — direct schema/code mismatch. KPI counting at §12.4 line 1196 ("deep gap emission 빈도") inherits the ambiguity.
- **Action Required**: Change `mode_escalation_gap: str` → `mode_escalation_gaps: list[str]` in §6.6 and update example to a Phase 1a-emittable enum (e.g., `["multi_client_missing", "high_risk_capability_missing"]`). Define KPI counting rule (per-gap vs per-escalation) in §12.4.

#### 6. [ACCEPT] [High] §10.2 lottery scenario still uses fuzzy `">="` notation — v1.4 token-level principle only half-applied
- **Critic** (#4): v1.4 changelog #1 mandated "token-level trace, no intuition-based score annotations." §10.1 was updated; §10.2 (line 1001-1003) was not. Fixture authors will not be able to label expected scores precisely.
- **Cross**: Not flagged.
- **Judgment**: ACCEPT — direct violation of v1.4 stated principle, evidence at design.md:1001-1003 vs design.md:1270.
- **Action Required**: Update §10.2 to §10.1-style token enumeration with exact integer scores (e.g., `data_pipeline_score: 7 (수집/누적/통계/분석/추천/패턴/회차)`). Add `_select_mode` precedence trace in body.

#### 7. [ACCEPT] [High] Research log path semantics underspecified (workspace abs-path + concurrent-append safety)
- **Critic**: Not flagged.
- **Cross** (#4): `projects/<workspace>/data/research_log.jsonl` is invalid because [project_pipeline.py:608](core/project_pipeline.py:608) normalizes workspace to absolute path; current planning artifacts go to `{workspace}/planning` ([project_pipeline.py:167](core/project_pipeline.py:167)). No locking semantics specified despite [file_lock.py:37](core/file_lock.py:37) being available.
- **Judgment**: ACCEPT — Cross provides concrete file/line evidence. This is a Phase 1a item 8 (line 1109-1111) defect that will surface immediately during implementation.
- **Action Required**: Fix path to `{workspace}/.af_runtime/research/research_log.jsonl` (or `{workspace}/data/research_log.jsonl` — pick one) and require appends through `core.file_lock.locked_file()`. Update §11 Phase 1a item 8 + §12.3.

#### 8. [ACCEPT] [Medium] Phase 1b structured fields lack legacy-projection contract — risk of stranded data
- **Critic**: Not flagged.
- **Cross** (#5): Phase 2 is deferred but Phase 1b adds `required_capabilities`/`verification_focus`/`skill_gap_hypotheses`. Current downstream consumers ([researcher.py:589](core/researcher.py:589), [work_item_generator.py:43](core/work_item_generator.py:43), [project_task_board.py:593](core/project_task_board.py:593)) read only legacy fields. Improved research will be stored but not actionable.
- **Judgment**: ACCEPT — code references confirm. Without a projection rule, Phase 1b is an invisible improvement.
- **Action Required**: Add Phase 1b projection rule to §11: structured fields must enrich legacy `required_skills`, `role_hints`, `risks`, `deliverables`, `research_notes`. Add one integration test proving a capability (e.g., `multi_client_simulation_test`) reaches `role_plan` or work-item docs before Phase 2.

#### 9. [ACCEPT] [Medium] §11 fixture label `expected_secondary_modes` not stage-split despite §10.1 dual-stage labels
- **Critic** (#7): §10.1 distinguishes 1차 plan secondary `["fresh_lookup"]` vs final secondary `["fresh_lookup", "skill_evolution"]`. §11 line 1105 only has single `expected_secondary_modes`; §12.5 line 1205 "≥60% partial match" doesn't say which stage.
- **Cross**: Not flagged.
- **Judgment**: ACCEPT — direct schema gap. Same defect class as v1.4 #4 fixed for primary mode but missed for secondary.
- **Action Required**: Split into `expected_initial_secondary_modes` / `expected_final_secondary_modes` in §11 and §12.5, OR explicitly state in §12.5 that fixture compares only final-stage secondary.

#### 10. [ACCEPT] [Medium] §11 Phase 1a item 7 fixture format ambiguous (py vs json)
- **Critic** (#8): Line 1103 says `tests/test_research_router_modes.py` "(또는 `tests/fixtures/research_router_cases.json`)". Implementer free choice complicates §12.5 calibration automation.
- **Cross**: Not flagged.
- **Judgment**: ACCEPT — minor but real ambiguity.
- **Action Required**: Pick one. JSON fixture is preferred for calibration automation; document the choice in §11.

#### 11. [HOLD] [Medium] §4.2.1 router primary vs §4.4.4 detector threshold asymmetry — design intent undocumented
- **Critic** (#5): `external_stack_score >= 3` exists in detector but not router primary (line 232-233 vs line 336-338). Intent likely "router conservative; detector escalates after evidence" but never stated.
- **Cross**: Not flagged.
- **Judgment**: HOLD — this is intentional design (8인 포커 case requires the asymmetry per §10.1 trace), and current behavior is correct. The defect is documentation-only. Author should confirm intent before patching.
- **Question for Author**: Is the asymmetry intentional (router conservative, detector uses external_stack as a post-evidence escalation lever to reduce false positives)? If yes, document the rationale in §4.4 or §4.4.4. If no, align the thresholds.

#### 12. [REJECT] [Low] §11 Phase 1a item 4 deprecation fallback as unnecessary middle state
- **Source**: Critic (#6)
- **Original Finding**: Suggests removing the `try/except TypeError` fallback in the same Phase 1a PR rather than via a deferred follow-up.
- **Rejection Reason**: This is a stylistic preference about PR sequencing; the design already specifies "Phase 1a 머지 직후 fallback 제거" (line 1089). Whether removal happens in the same PR or the next is an implementation-time call, not a design defect. No correctness or coverage gap introduced either way.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Phase 1a detector `source_pack` obligation vacuous | Critical | ACCEPT | Both |
| 2 | `final_mode` arg-name semantic contradiction | Critical | ACCEPT | Critic |
| 3 | Phase 1a vs 1b structured-evidence timing contradiction | Critical | ACCEPT | Cross |
| 4 | `data_pipeline` secondary lacks mode contract | High | ACCEPT | Cross |
| 5 | `mode_escalation_gap` singular vs dual-emit | High | ACCEPT | Critic |
| 6 | §10.2 fuzzy `">="` violates v1.4 token-trace rule | High | ACCEPT | Critic |
| 7 | research_log path + concurrent-append unsafe | High | ACCEPT | Cross |
| 8 | Phase 1b legacy-projection contract missing | Medium | ACCEPT | Cross |
| 9 | `expected_secondary_modes` not stage-split | Medium | ACCEPT | Critic |
| 10 | Fixture format (py vs json) ambiguous | Medium | ACCEPT | Critic |
| 11 | Router/detector threshold asymmetry undocumented | Medium | HOLD | Critic |
| 12 | Same-PR fallback removal preference | Low | REJECT | Critic |

### Recommendations

Before Phase 1a implementation begins, produce v1.5 with:

1. **Fix #1 first** (Phase 1a detector vacuousness) — this is the highest-impact defect; every Phase 1a deep escalation will be wrong otherwise. Decide between options (a) Phase-1a–compatible obligation or (b) signal-only Phase 1a.
2. **Fix #3** (Phase 1a/1b boundary contradiction in §3.2) — pick one: either Phase 1a has structured_evidence or it doesn't. Update both §3.2 paragraphs and §11.
3. **Apply #2 rename** across §0/§4.4.5/§10.1/§11 in the same patch — this is leftover v1.3 work.
4. **Patch #4 + #6** together (mode-table integrity): add `data_pipeline` row OR rename to `analysis_tags`; align §10.2 with §10.1 token-trace format.
5. **Patch #5 + #9**: schema fixes (`mode_escalation_gaps: list[str]`, dual-stage secondary labels) — small but unblocks fixture authors.
6. **Patch #7**: fix research_log path and add `file_lock` requirement before §11 item 8 is implemented.
7. **Patch #8**: add Phase 1b legacy-projection rule + one integration test acceptance criterion.
8. **Pick fixture format (#10)** — recommend JSON for calibration automation.
9. **Confirm or document #11** in §4.4 prose.
10. **Add 4 missing-design items** raised by Critic: Phase 1a→1b entry gate, detector+verifier dual-gap collision rule, single CRUD label example in §12.5, frozen-build smoke test for `core.research_router` import.

Once v1.5 lands, re-run af-cross-review on the patched document before Phase 1a coding starts.