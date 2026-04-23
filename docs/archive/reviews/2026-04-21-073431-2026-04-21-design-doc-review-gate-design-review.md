# Design Review: 2026-04-21-design-doc-review-gate

> Source: docs/2026-04-21-design-doc-review-gate.md
> Date: 2026-04-21 07:34
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

At least 3 Critical findings with strong evidence (specific file:line references, internal contradictions between v1→v2 sections). Do not implement until resolved.

> **Note on aggregation:** The cross-review run failed with a provider error (stdin read error before reviewer output). This aggregation is based on the critic review alone. Each critic finding was evaluated against the original document for evidence strength; findings with concrete line/file references are accepted, weaker claims are held.

### Aggregated Findings (13 total)

#### 1. [ACCEPT] [Critical] §1.1 `docs/reviews/*.md` creates circular review-gate loop
- **Critic**: `docs/reviews/` is the output directory of `scripts/pre_commit_review.py:33` (`REVIEWS_DIR = os.path.join("docs", "reviews")`); 21 review files already exist there. Gating them as design docs creates a loop: auto-review written → staged → gate demands review-of-review → BLOCK forever.
- **Cross**: not flagged (provider error)
- **Judgment**: Strong evidence — concrete path, existing artifacts, plausible failure mode. Line 39 in original doc confirms `docs/reviews/*.md` inclusion.
- **Action Required**: Remove `docs/reviews/*.md` from §1.1 inclusion list; add it to the exclusion list alongside `work-items/`, `patterns/`, `code-review.md`.

#### 2. [ACCEPT] [Critical] §3.3 D3 contradicts §3.2 and v2 changelog on af-doc-qa tracking
- **Critic**: §3.2 line 256 says "af-doc-qa는 추가하지 않음 (v2 결정: work-item 전용)", but D3 Sonnet handoff (line 377) still says `_post_agent_record`에 af-doc-qa 포함 tracking.
- **Cross**: not flagged
- **Judgment**: Strong evidence — direct internal contradiction between two sections of the same doc. Sonnet will produce inconsistent code.
- **Action Required**: Delete the "af-doc-qa 포함 tracking" phrase from §3.3/§6 D3. D3 should only confirm `.md` flows through `_classify`.

#### 3. [ACCEPT] [Critical] §5.1 I3 requires 4 agents, contradicting §2.2 + D0 test case
- **Critic**: I3 says mixed `.py`+`.md` commit needs `{af-test-runner, af-doc-qa, af-critic, af-cross-review}`, but per §2.2 af-doc-qa isn't in `_REQUIRED_AGENTS_BY_TYPE["design"]` and isn't tracked in `_AGENT_TIER_MAP`. §6 D0 test `test_mixed_code_and_design_commit` correctly says 3 agents (code 3 ∪ design 2). If I3 becomes spec, every mixed commit emits `missing-agent-af-doc-qa`.
- **Cross**: not flagged
- **Judgment**: Strong evidence — internal spec contradiction with concrete implementation consequence.
- **Action Required**: Rewrite I3 as `{af-test-runner, af-critic, af-cross-review}` (3 agents, set union with shared af-critic/af-cross-review).

#### 4. [ACCEPT] [High] §2.1 JSON schema example shows af-doc-qa in `reviews`
- **Critic**: Lines 78-83 include `"af-doc-qa": {...}` with comment "design 전용 tier 1" — v1 residue.
- **Cross**: not flagged
- **Judgment**: Direct document evidence. Schema example is authoritative for readers.
- **Action Required**: Delete the af-doc-qa entry from the JSON example in §2.1.

#### 5. [ACCEPT] [High] §5.2 E2 describes an impossible/nonsensical scenario
- **Critic**: Per §3.2 af-doc-qa is excluded from `_AGENT_TIER_MAP`, so running it leaves `reviews` empty. E2 framing ("af-doc-qa만 돌리고 commit") doesn't test a real failure mode.
- **Cross**: not flagged
- **Judgment**: Logically consistent with §3.2 exclusion — E2 test is dead code.
- **Action Required**: Rewrite E2 as "af-critic만 실행 → `missing-agent-af-cross-review` BLOCK" to test the real partial-run case.

#### 6. [ACCEPT] [High] `_infer_type` import crosses private module boundary
- **Critic**: `scripts/enqueue_agent_review.py` imports `_infer_type` (leading underscore, private) from `scripts/review_gate.py` at line 224. Hard cross-script coupling on private API.
- **Cross**: not flagged
- **Judgment**: Document evidence clear. Private-API import is a real maintainability hazard.
- **Action Required**: Either (a) promote `_infer_type` to a public helper in a shared module (e.g., `scripts/_review_types.py`), or (b) duplicate the small function in both scripts and document the convention.

#### 7. [ACCEPT] [High] `docs/standards/*.md` doesn't match `YYYY-MM-DD-제목.md` naming rule
- **Critic**: `docs/standards/api-standards.md`, `testing-standards.md` exist without date prefix but §1.1 line 46 says "확장자는 `.md`만 (설계문서 규칙: `YYYY-MM-DD-제목.md`)".
- **Cross**: not flagged
- **Judgment**: Rule ambiguity — editing `api-standards.md` would trigger gate despite non-standard naming.
- **Action Required**: Explicitly state "standards/ is design-gated regardless of date naming", or exclude standards/ from initial rollout.

#### 8. [ACCEPT] [High] `docs/plans/` scope applies to 20+ historical docs
- **Critic**: `docs/plans/` contains planning docs from 2026-03. Typo fix on old plan triggers 2-agent review with no safety benefit.
- **Cross**: not flagged
- **Judgment**: Scope creep is real; operational friction without commensurate value.
- **Action Required**: Either (a) restrict to "new files" only, (b) add historical exemption, or (c) limit initial rollout to `docs/` root + `docs/features/` and expand later.

#### 9. [HOLD] [High] §3.3 `record_review_done` "tier optional화 확정" may be a no-op
- **Critic**: Every existing caller passes concrete tier. `hook_runner.py:338` and `review_gate.py:287` both pass tier from `_AGENT_TIER_MAP`. Af-critic/af-cross-review already have tier 2/3. No one will call with tier=0.
- **Cross**: not flagged
- **Judgment**: Claim has evidence, but the change is forward-compat and low-cost. HOLD because v1→v2 changelog framed it as Critical; author should justify the use case or drop it.
- **Question for Author**: What concrete caller (now or planned) passes tier=0? If none, drop the change from v2; if design agent without tier is foreseen, document the case.

#### 10. [ACCEPT] [Medium] Section numbering inverted — §5.3 before §5.2
- **Critic**: Line 336 (§5.3 알려진 한계) appears before line 340 (§5.2 엣지 케이스).
- **Cross**: not flagged
- **Judgment**: Trivial to verify. Document structure defect.
- **Action Required**: Swap to §5.1 → §5.2 엣지 케이스 → §5.3 알려진 한계.

#### 11. [ACCEPT] [Medium] §8.5 "v2 재검증 권장" is self-referential and becomes stale
- **Critic**: §8.5 lines 426-428 request the review that is currently happening.
- **Cross**: not flagged
- **Judgment**: Correct — once this review completes, §8.5 is dead text.
- **Action Required**: Post-review, either remove §8.5 or convert to historical note.

#### 12. [ACCEPT] [Medium] Coverage check redundant with existing `new-files-added` for `.py`
- **Critic**: New `coverage-gap` check (§2.3 lines 145-152) and existing `new-files-added` check both fire on `af-cross-review.files_snapshot`. For `.py`, coverage-gap fires first, making `new-files-added` dead.
- **Cross**: not flagged
- **Judgment**: Overlap documented with line references. Real redundancy.
- **Action Required**: Either consolidate into one check, or explicitly document `new-files-added` as backup for files not in `_REQUIRED_AGENTS_BY_TYPE`.

#### 13. [ACCEPT] [Medium] `file_types` never persisted — legacy entries always re-inferred
- **Critic**: §4 says missing `file_types` is inferred via `_infer_type(path)`, but nothing writes it back. If `_infer_type` rules change, legacy vs new entries diverge despite being logically identical.
- **Cross**: not flagged
- **Judgment**: Valid design gap. Either persist-on-load (lazy migration) or document "always inferred, never cached".
- **Action Required**: Add explicit decision in §4; include a D0 test case `test_legacy_queue_without_file_types` with concrete JSON fixture.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `docs/reviews/*.md` circular loop | Critical | ACCEPT | Critic |
| 2 | §3.3 D3 vs §3.2 af-doc-qa contradiction | Critical | ACCEPT | Critic |
| 3 | §5.1 I3 demands 4 agents | Critical | ACCEPT | Critic |
| 4 | §2.1 JSON schema shows af-doc-qa | High | ACCEPT | Critic |
| 5 | §5.2 E2 nonsensical scenario | High | ACCEPT | Critic |
| 6 | Private `_infer_type` import | High | ACCEPT | Critic |
| 7 | `docs/standards/` naming mismatch | High | ACCEPT | Critic |
| 8 | `docs/plans/` historical scope creep | High | ACCEPT | Critic |
| 9 | `record_review_done` tier optional no-op | High | HOLD | Critic |
| 10 | §5.2/§5.3 numbering inverted | Medium | ACCEPT | Critic |
| 11 | §8.5 self-referential | Medium | ACCEPT | Critic |
| 12 | Coverage check redundancy | Medium | ACCEPT | Critic |
| 13 | `file_types` not persisted | Medium | ACCEPT | Critic |

### Recommendations

Before implementation (must resolve all Critical before handing to Sonnet):

1. **§1.1 — Remove `docs/reviews/*.md` from inclusion list** (Finding 1). Add to exclusion list with rationale.
2. **§3.3/§6 D3 — Delete af-doc-qa tracking mention** (Finding 2). D3 scope reduced to confirming `.md` passes `_classify`.
3. **§5.1 I3 — Rewrite to 3 agents** (Finding 3): `{af-test-runner, af-critic, af-cross-review}` for mixed commits.
4. **§2.1 — Delete af-doc-qa from JSON example** (Finding 4).
5. **§5.2 E2 — Rewrite to test af-critic-only partial run** (Finding 5).
6. **§3.1 — Decide public API for `_infer_type`** (Finding 6). Shared module preferred.
7. **§1.1 — Disambiguate `docs/standards/` and `docs/plans/` scope** (Findings 7, 8). Consider initial rollout to `docs/` + `docs/features/` only.
8. **§5 — Fix section numbering** (Finding 10).
9. **§2.3 + §3.3 — Reconcile coverage-gap vs new-files-added** (Finding 12).
10. **§4 — Decide persistence policy for `file_types`** and add D0 fixture (Finding 13).
11. **§8.5 — Plan to remove or convert post-review** (Finding 11).
12. **§3.3 `record_review_done` tier change** (Finding 9): Author confirms use case, else drop.

Re-run cross-review (provider error on this pass) before marking design ready — only critic signal currently available.