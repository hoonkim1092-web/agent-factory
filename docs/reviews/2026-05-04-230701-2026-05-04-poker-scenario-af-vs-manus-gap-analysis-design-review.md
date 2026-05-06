# Design Review: 2026-05-04-poker-scenario-af-vs-manus-gap-analysis

> Source: docs/2026-05-04-poker-scenario-af-vs-manus-gap-analysis.md
> Date: 2026-05-04 23:07
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

I verified the critic's key claims (researcher.py:919, project_pipeline.py:798-810, §7.2 "schema만 추가" wording). Cross-review is unavailable due to provider error, so each critic finding stands on its own evidence.

## Final Design Review

### Verdict: **BLOCK**

Cross-review failed with a provider error (gpt-5.5 stdin issue) — only critic-side findings are available. Two Critical findings are evidence-strong and grep-verified against current code; they must be resolved in the upcoming `2026-05-04-af-research-quality-gate-design.md` before P0 implementation.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] §7.3 P0 A1 lost the post-LLM injection step from §4 ①
- **Critic**: §7.3 A1 "schema에 original_request 필드 추가" + §7.2 "brief에 original_request 필드만 추가하면 자동 흐름. 4 generator 함수 수정 불필요" collapses §4 ①'s "researcher가 task_input 그대로 보존" — relying on LLM to copy verbatim text into JSON loses Korean prompt fidelity.
- **Cross**: not available (provider error).
- **Judgment**: ACCEPT. Verified against `core/researcher.py:919` — `research_project_brief()` returns LLM JSON; without an explicit post-LLM `brief["original_request"] = task_input` assignment, the field becomes paraphrased, not verbatim. Strong evidence.
- **Action Required**: In new design §5 P0 A1, rewrite as: "LLM 반환 직후 `brief['original_request'] = task_input` 무조건 할당. Schema entry는 문서화용. 단위 테스트: byte-equal 검증."

#### 2. [ACCEPT] [Critical] §7.3 P2 C1 "Spec Before Tasks" naming contradicts L798/L810 insertion point
- **Critic**: `core/project_pipeline.py:799` is `build_project_board(...)` (task board construction) — inserting the spec gate between L798 and L810 is "Spec After Task Board, Before Work Items," not "Spec Before Tasks."
- **Cross**: not available.
- **Judgment**: ACCEPT. Verified — L799 builds `task_board`, L810 calls `generate_work_items()`. The proposed insertion is post-task-board. Implementer reading the current name will likely move the gate up and break `build_project_board()`'s signature.
- **Action Required**: Pick one in new design §5 P2: (a) move gate before L799 + extend `build_project_board(project_brief, role_plan, spec)`, OR (b) rename to "Spec Before Work Items" and document task_board ignores spec.

#### 3. [ACCEPT] [High] §7.3 P0 A2 stopword guard breaks Korean prompts
- **Critic**: Stopword-stripped Korean tokens ({"8인","네트워크","플레이","포커게임","만들어줘"}) won't match English-headed local refs in an English codebase; "1-or-more match" filter zeros out legitimate refs while letting self-referential `docs/architecture.md` through if it happens to contain a Korean fragment.
- **Cross**: not available.
- **Judgment**: ACCEPT. The motivating prompt is Korean — A2 must handle the language gap or it regresses the very case it's meant to fix.
- **Action Required**: Add to new design §5 P0 A2: bilingual extraction OR score-threshold fallback for non-Latin inputs OR explicit `lang=="en"` gate. Add Korean test fixture.

#### 4. [ACCEPT] [High] §7.3 P0 A3 hardcodes poker domains in core/, violating D2/D4
- **Critic**: D2 says manifests are external YAML, D4 says one manifest at a time. A3 puts wsop.com / pokertda.com / pokerstars.com / upswingpoker.com directly in `core/researcher.py:311`. Adding chess later requires editing core code — exactly what D2 prevents.
- **Cross**: not available.
- **Judgment**: ACCEPT. Self-contradiction with the design's own decisions D2/D4.
- **Action Required**: New design §7 (poker.yaml schema): add `authority_domains: [...]` field. P0 A3 implements only the trust_score machinery; URL list ships in poker.yaml from P1 B2.

#### 5. [ACCEPT] [High] §7.3 P1 B4 evidence.json schema change has no backward-compat plan
- **Critic**: `core/research_verifier.py` and `core/researcher.py:_build_evidence_summary` consume the current schema. "강화" doesn't say additive vs replacement.
- **Cross**: not available.
- **Judgment**: ACCEPT. Schema migrations without an additive path cause silent breakage in existing consumers.
- **Action Required**: New design §6 must capture: (a) current schema (read from a real evidence.json), (b) new schema, (c) added vs replaced keys, (d) consumer migration list. Make B4 additive (legacy keys retained ≥1 phase).

#### 6. [ACCEPT] [High] §7.3 P1 B1 RecoverySearchLoop has no per-round bound
- **Critic**: §9 placeholder names "무한 루프" risk but B1 only caps total rounds=3. No early-break on `len(matched) - len(matched_prev) == 0`, no per-round Tavily call cap, no keyless-mode skip. Worst case: 3 × 4 web calls × N gaps = quota burn.
- **Cross**: not available.
- **Judgment**: ACCEPT. Convergence test is missing; the "max_rounds=3" alone does not bound cost.
- **Action Required**: New design §9 must specify three bounds: (1) early-break on no-progress, (2) per-round Tavily cap, (3) `TAVILY_API_KEY` 부재 시 loop no-op.

#### 7. [ACCEPT] [Medium] §7.3 P2 C2 5-way spec generator violates D4 (Simplicity First)
- **Critic**: D4 says "1 manifest first." C2 adds 5 new doc types (rules-spec / state-machine / server-architecture / event-protocol / client-view), all poker-shaped. ~5 LLM × ~2K tokens per run with no cost projection.
- **Cross**: not available.
- **Judgment**: ACCEPT. Symmetric with D4: starting with 5 generators for one domain is the same anti-pattern.
- **Action Required**: Reduce P2 C2 to 1–2 generic spec types (e.g., `domain-rules-spec.md`, `system-architecture.md`). Defer 5-way split until ≥2 domains exist.

#### 8. [ACCEPT] [Medium] §7.3 P2 C4 traceability has no spec_section ID scheme
- **Critic**: `spec_section` needs a stable referrable ID (slug? numbered? markdown header?). Without pinning, every spec edit rots the trace links.
- **Cross**: not available.
- **Judgment**: ACCEPT. Standard requirement for any traceability matrix.
- **Action Required**: New design §6: define `<spec-name>#<header-slug>` (or equivalent) + a `verify_traceability.py` lint that errors on missing anchors.

#### 9. [ACCEPT] [Medium] §7.3 P3 D2 acceptance criteria not operationalized
- **Critic**: "추적 가능 검증" is subjective. Without a CLI script, P3 cannot be closed (CLAUDE.md "검증될 때까지 반복" rule).
- **Cross**: not available.
- **Judgment**: ACCEPT. Vague success criteria are the most common reason phases reopen.
- **Action Required**: D2 ships `python scripts/verify_traceability.py docs/research/<slug>-traceability.md` returning exit 0 iff every claim_id/source_id/spec_section/task_id resolves.

#### 10. [ACCEPT] [Medium] Frozen build (af.exe) compatibility for `config/coverage_manifests/poker.yaml`
- **Critic**: PyInstaller bundles only what `af.spec` lists. Runtime data files (`config/coverage_manifests/*.yaml`) need `datas` entry or `dist/af/af.exe` will FileNotFoundError.
- **Cross**: not available.
- **Judgment**: ACCEPT. Recurring foot-gun (code-review.md M9 already flags af.spec hiddenimports gaps).
- **Action Required**: New design §6 sub-bullet: "af.spec datas → `config/coverage_manifests/*.yaml`" + frozen-build smoke test in P3.

#### 11. [ACCEPT] [Medium] Multi-PC concurrent file write paths under `docs/research/<slug>-*` not specified
- **Critic**: AF supports multi-PC sync. New artifacts (`docs/research/`, `docs/specs/`, `docs/decisions/`) lack file_lock spec; D3 says git-tracked but JSON 3-way merge is hostile.
- **Cross**: not available.
- **Judgment**: ACCEPT. Real concern given existing Supabase sync model.
- **Action Required**: New design §6 specifies: (a) `core/file_lock.py` for new artifacts, (b) JSON files have `generated_at` and regenerate on conflict instead of merging, (c) document expected `git status` after a run.

#### 12. [ACCEPT] [Medium] §7.1 폐기 reasoning vs §3 ⑥ deep_synthesis question unresolved
- **Critic**: §3 ⑥ said fast_synthesis (1 LLM call) lacks depth for simulation/architecture; §7.1 says evidence-only fix suffices. But P0–P2 add evidence collection only, not multi-step LLM chaining inside synthesis. If brief still synthesizes in 1 call, depth claims may not surface even with richer evidence.
- **Cross**: not available.
- **Judgment**: ACCEPT. The reconciliation is not in the document; it's load-bearing for whether the proposed P0–P2 actually closes the gap.
- **Action Required**: New design §1 adds rationale paragraph with falsifiable prediction: "after P0–P2, single fast_synthesis call will surface state-machine/protocol claims because evidence prompt now contains them." If empirically false in P3 D1, deep_synthesis revival is needed (track as P3 D4 fallback).

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | A1 lost post-LLM injection | Critical | ACCEPT | Critic |
| 2 | P2 C1 "Spec Before Tasks" naming contradiction | Critical | ACCEPT | Critic |
| 3 | A2 stopword guard breaks Korean | High | ACCEPT | Critic |
| 4 | A3 hardcodes domains, violates D2/D4 | High | ACCEPT | Critic |
| 5 | B4 evidence.json schema, no compat plan | High | ACCEPT | Critic |
| 6 | B1 RecoverySearchLoop unbounded per round | High | ACCEPT | Critic |
| 7 | C2 5 generators violates D4 | Medium | ACCEPT | Critic |
| 8 | C4 spec_section ID scheme missing | Medium | ACCEPT | Critic |
| 9 | D2 acceptance criteria not operational | Medium | ACCEPT | Critic |
| 10 | af.spec datas for poker.yaml | Medium | ACCEPT | Critic |
| 11 | Multi-PC file_lock + merge policy | Medium | ACCEPT | Critic |
| 12 | §7.1↔§3⑥ depth-vs-evidence reconciliation | Medium | ACCEPT | Critic |

### Recommendations

Before P0 implementation, the new design doc `docs/2026-05-04-af-research-quality-gate-design.md` must:

1. **Rewrite P0 A1** as post-LLM verbatim assignment, not schema-only (#1).
2. **Resolve P2 C1 naming** — either rename phase or move gate before L799 (#2).
3. **Add a Korean-language test fixture and bilingual matcher** for A2 (#3).
4. **Move poker domain URLs out of core/** into `poker.yaml authority_domains` (#4).
5. **Pin evidence.json schema** in §6 with current/new/migration table; B4 must be additive (#5).
6. **Specify B1 convergence + cost bounds** explicitly in §9 (#6).
7. **Reduce P2 C2 to 1–2 generic spec types**; defer 5-way split (#7).
8. **Define spec_section ID scheme + lint script** (#8, #9).
9. **Add af.spec datas entry + frozen-build smoke test** in P3 (#10).
10. **Document file_lock + JSON regeneration policy** for new artifacts (#11).
11. **Add falsifiable depth-prediction paragraph** in §1 for fast_synthesis sufficiency (#12).
12. **Re-run cross-review** after the document is written — current cross result was a provider error, not a substantive PASS.

Note: Cross-review (gpt-5.5) errored out on stdin; this verdict relies entirely on the critic. The "BLOCK" call comes from #1 and #2 alone, both Critical and grep-verified.