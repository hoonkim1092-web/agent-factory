# Design Review: 2026-05-04-af-research-quality-gate-design

> Source: docs/2026-05-04-af-research-quality-gate-design.md
> Date: 2026-05-04 23:01
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

> **⚠️ Cross-review unavailable**: The Codex cross-reviewer failed with a provider error (`gpt-5.5` model unavailable / stdin read error). Aggregation is based on **critic review alone**. Findings with strong file:line evidence are still ACCEPTed; recommend re-running af-cross-review after codex provider recovery (≥2026-05-05 15:37 KST per §0).

### Verdict: **BLOCK**

2 Critical findings (A5 dataclass mutation, B4 field rename/inversion) directly conflict with HEAD code. Implementation as-currently-specified will silently break poker pipeline at the verifier and escalation paths.

### Aggregated Findings (12 total + 6 advisory)

#### 1. [ACCEPT] [Critical] B4 `authority` rename + semantics inversion conflicts with `authority_level` consumers
- **Critic**: B4 introduces `"authority": "primary"` (web=primary), but `core/researcher.py:347` already emits `authority_level` (local=primary), and `core/research_verifier.py:168,252,278,317` reads it; rename + invert silently zeros `primary_source_ratio` and triggers `official_source_missing` on every poker run.
- **Cross**: not available
- **Judgment**: ACCEPT — evidence is grep-verifiable (4 read sites in verifier). This is the single most damaging finding.
- **Action Required**: Keep existing `authority_level` field. Add a new orthogonal `authority_tier` ("rulebook"/"strategy"/"blog") for poker semantics, OR remap so trust_score≥0.4 web refs get `authority_level="primary"` in `_build_source_pack`. Update §5.2 B4 + §6.2 + §8 accordingly.

#### 2. [ACCEPT] [Critical] A5 ResearchPlan flags lost on gap-driven escalation via `for_mode()`
- **Critic**: `core/researcher.py:690` calls `ResearchPlan.for_mode(escalated_mode)`; `research_router.py:91 for_mode()` is a controlled-mutation factory. Adding 3 fields to dataclass without updating `for_mode()` discards `requires_research/domain/research_depth` on escalation; manifest pipeline downstream loses `domain` and silently bypasses gating.
- **Cross**: not available
- **Judgment**: ACCEPT — direct conflict with the recovery loop B1 itself depends on. Without fix, P0+P1 silently degrade to current behavior on escalation paths.
- **Action Required**: Update `for_mode()` signature to accept (or copy from prior plan) `domain` and `research_depth`. Add regression test `plan(poker) → escalate via gap_to_mode → assert domain == "poker"`. Document in §5.1 A5.

#### 3. [ACCEPT] [High] A6 duplicates existing `prepare_brief` save + proposes wrong path
- **Critic**: `core/project_pipeline.py:722-723` already writes `<workspace>/planning/project_brief.json`; `PreparedBrief.project_brief_path:51,733` propagates it. A6's `docs/research/<slug>-project-brief.json` either double-saves or breaks downstream consumers.
- **Cross**: not available
- **Judgment**: ACCEPT — A6 is mostly already done; only `original_request` field (covered by A1) is missing. Proposing it as new code mis-scopes P0.
- **Action Required**: Drop A6 OR explicitly extend the existing save. State authoritative path in §11.3 cold-start step 2.

#### 4. [ACCEPT] [High] B1 silently undoes P5 G4 parallelization (commit `31057abf`, 5 commits ago)
- **Critic**: B1's serial `while rounds < max_rounds:` replaces the `ThreadPoolExecutor(max_workers=2)` local+secondary concurrent collect at researcher.py:706-723. Poker (`requires_web=True`+`deep`) loses 2-3× wall-time benefit from a 5-day-old optimization.
- **Cross**: not available
- **Judgment**: ACCEPT — verifiable via `git log --oneline | head -5`. Undoing recent committed work without rationale is a regression.
- **Action Required**: Specify in §5.2 B1 that the executor stays. RecoverySearchLoop wraps the parallel fetch — escalation rounds run only if `_is_sufficient(...)` fails after the parallel pass, and each retry can still parallelize.

#### 5. [ACCEPT] [High] `_is_sufficient` is unreachable on `requires_web=True` path (poker)
- **Critic**: `_is_sufficient` is only called in `else` branch at researcher.py:730; deep_source_research path skips it. A4's `domain_checklist` is dead code for poker until B1 unifies the 3-branch dispatch.
- **Cross**: not available
- **Judgment**: ACCEPT — code-grounded. Without explicit B1 restructuring, A4 ships as a no-op for the very domain the design targets.
- **Action Required**: §5.2 B1 must specify converting the 3-branch dispatch into a single canonical flow with `_is_sufficient(...)` always-on. Add unit test asserting `_is_sufficient` called once per round on deep_source_research path.

#### 6. [ACCEPT] [High] §6.1 brief schema is incomplete vs current pipeline writes
- **Critic**: `project_pipeline.py:719-721` adds `requested_role/route/generated_at`; LLM prompt at `researcher.py:962-979` declares `data_model/user_flows/non_goals/architecture_style/recommended_architecture/recommended_tech_stack/required_capabilities/skill_gap_hypotheses/verification_focus/maintenance_strategy/source_backed_claims`. §6.1 lists none.
- **Cross**: not available
- **Judgment**: ACCEPT — implementers using §6.1 as source-of-truth will break work_item_generator/plan_verifier/research_verifier consumers.
- **Action Required**: Replace §6.1 with delta spec: "existing schema + `original_request` + `research_plan` (extended fields)". Pin to current code with a code-pointer footnote.

#### 7. [ACCEPT] [Medium] CoverageGate (B5) overlaps with `research_verifier.verify_with_retry` — undefined precedence
- **Critic**: `research_verifier.py` already implements 4-metric scoring + gap emission, plumbed into `prepare_brief` at project_pipeline.py:672-675. B5 introduces a parallel gate without specifying interaction.
- **Cross**: not available
- **Judgment**: ACCEPT — two gates without precedence rules → double-cost LLM rounds or contradictory verdicts.
- **Action Required**: §5.2 B5 must declare hierarchy. Preferred: extend `ResearchVerifier` with manifest-based gaps (single gate). Alternative: state B5 runs AFTER verifier with `block=True` overriding verifier "pass".

#### 8. [ACCEPT] [Medium] A3 `trust_score` boost never reaches `source_pack` / verifier
- **Critic**: Boost only affects `_collect_web_references` ordering. `_build_source_pack:357-371` hard-codes `authority_level: "secondary"` for web refs; `trust_score` is dropped before verifier sees it.
- **Cross**: not available
- **Judgment**: ACCEPT — orthogonal to finding #1 but interacts with it; the fix can be unified.
- **Action Required**: Add 1-bullet in §5.1 A3: in `_build_source_pack`, promote `authority_level="primary"` when `trust_score ≥ 0.4`, OR carry `trust_score` through to the source dict and update `_compute_metrics`.

#### 9. [ACCEPT] [Medium] Frozen build / `af.spec` compatibility unaddressed
- **Critic**: New YAML at `config/coverage_manifests/poker.yaml` won't ship in `dist/af-{version}.zip` unless `af.spec` `datas` updated. `Path(__file__).parent.parent` resolution under PyInstaller points into `_MEIPASS`.
- **Cross**: not available
- **Judgment**: ACCEPT — repeated AF release pattern (CLAUDE.md "새 core/*.py 파일은 af.spec hiddenimports에 반드시 추가" — same applies to data files).
- **Action Required**: Add §5.2 B2 sub-bullet: `af.spec datas` += `('config/coverage_manifests', 'config/coverage_manifests')`. `_load_domain_manifest` resolves via `sys._MEIPASS` first, project root fallback.

#### 10. [ACCEPT] [Medium] R8 slug-collision claim is factually wrong
- **Critic**: `work_item_generator.py:114 _slug_from_goal` is 60-char goal hash with no timestamp; `:737 os.makedirs(..., exist_ok=True)` silently overwrites. Two poker runs in 5 minutes → second clobbers first. Same risk for A6 path.
- **Cross**: not available
- **Judgment**: ACCEPT — directly verifiable. The §9 R8 mitigation premise is false.
- **Action Required**: Include `run_id` (already in PreparedBrief) in path, e.g. `docs/research/<run_id>-<slug>-project-brief.json`. Or `mkdir(exist_ok=False)` with retry suffix. Document in §9 R8.

#### 11. [ACCEPT] [Medium] §11 cold-start ordering contradicts §10 "6개 병렬" claim
- **Critic**: §11.3 strict serial vs §10 "6개 병렬"; actual DAG: A6 depends on A1, B1 depends on A4+A5, B3 depends on A5.
- **Cross**: not available
- **Judgment**: ACCEPT — internal consistency issue; will fork implementers.
- **Action Required**: Drop "6개 병렬" sentence in §10. Replace §11.3 numbered list with the actual dependency DAG (3 fan-out groups: {A1}, {A2,A3,A4,A5}, {A6}).

#### 12. [ACCEPT] [Low] Manifest `version: "1.0"` field has no consumer
- **Critic**: `_load_domain_manifest` returns only `required_fields`; version is read and discarded.
- **Cross**: not available
- **Judgment**: ACCEPT — minor but trivial to fix.
- **Action Required**: Either drop the field in §7 OR add an §5.2 acceptance test that propagates version into `coverage.json`.

#### Advisory (Missing from Design — not blocking but recommended)
- **A1.** No `RunBudget` integration for P2 (spec×5 + ADR + traceability ≈ 7 LLM calls/run).
- **A2.** No backward-compat story for existing `research_evidence.json` consumers when B4 reshapes claims/sources.
- **A3.** R4 mitigation covers "key missing" but not "low-quality results" (Tavily set, all non-whitelist URLs).
- **A4.** `_extract_domain_tokens` stopword list + Korean tokenization rules unspecified ("포커게임" → ?). BM25 filtering will be non-deterministic.
- **A5.** No file lock / atomic rename for concurrent run isolation on `docs/research/`.
- **A6.** Cold-start step 11 says "Blueprint §3·§12 동기화" but doesn't list which §3 subsystems (researcher, research_router, project_pipeline, new spec_generator?).

### Summary Table

| #  | Title | Severity | Verdict | Source |
|----|-------|----------|---------|--------|
| 1  | B4 authority field conflict | **Critical** | ACCEPT | Critic |
| 2  | A5 for_mode() drops new flags | **Critical** | ACCEPT | Critic |
| 3  | A6 duplicates existing save | High | ACCEPT | Critic |
| 4  | B1 undoes P5 G4 parallelization | High | ACCEPT | Critic |
| 5  | _is_sufficient unreachable on poker | High | ACCEPT | Critic |
| 6  | §6.1 schema missing fields | High | ACCEPT | Critic |
| 7  | CoverageGate vs verifier precedence | Medium | ACCEPT | Critic |
| 8  | trust_score doesn't propagate | Medium | ACCEPT | Critic |
| 9  | af.spec / PyInstaller datas | Medium | ACCEPT | Critic |
| 10 | R8 slug-collision claim wrong | Medium | ACCEPT | Critic |
| 11 | §10 vs §11 contradiction | Medium | ACCEPT | Critic |
| 12 | Manifest version field unused | Low | ACCEPT | Critic |
| A1–A6 | Advisory: budget, BC, tokens, locking, blueprint mapping | Advisory | NOTE | Critic |

### Recommendations (action order before implementation)

1. **Reconcile #1 + #8**: pick a single authority model (extend `authority_level` semantics OR add orthogonal `authority_tier`), then thread `trust_score → authority promotion` through `_build_source_pack` so verifier metrics actually move. This unblocks both Criticals on the verifier side.
2. **Fix #2 + #5 + #4 together** as one "P0 escalation path correctness" change: update `for_mode()` to preserve `domain/research_depth`; unify the 3-branch dispatch in `collect_project_evidence` so `_is_sufficient` always runs; preserve `ThreadPoolExecutor` parallelism across rounds.
3. **Resolve #3 + #6**: rewrite §6.1 as a delta against the actual schema (with `researcher.py:962-979` code pointer); drop or rescope A6 to a single-line `original_request` insertion via A1.
4. **Decide #7**: state in §5.2 B5 whether CoverageGate replaces, wraps, or runs after `ResearchVerifier`. Implementers cannot derive this.
5. **Add #9 to §5.2 B2** as a 1-line af.spec note before the YAML lands; otherwise frozen builds will fail at runtime.
6. **Fix #10 + #11**: replace R8 mitigation with actual `run_id`-prefixed path; replace §11.3 list with explicit dependency DAG.
7. **Trivial #12**: drop the unused version field or wire it through.
8. **Re-run af-cross-review** once codex provider recovers (per §0, ≥2026-05-05 15:37 KST). Aggregation may upgrade some HOLD candidates if cross flags areas critic missed.

**Do not begin P0 implementation** until #1, #2, #3, #4, #5, #6 are resolved in the design document. Items #7–#12 can be folded into the same revision pass.