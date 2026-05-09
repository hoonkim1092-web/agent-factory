# Design Review: 2026-05-04-poker-scenario-af-vs-manus-gap-analysis

> Source: docs/2026-05-04-poker-scenario-af-vs-manus-gap-analysis.md
> Date: 2026-05-04 22:14
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

The document references §7 four times as the load-bearing forward path, but §7 does not exist in the 176-line file. The §0 entry guide for the next cold-start session has no destination. Additionally, deprecation in §0 was not propagated into §3 ⑥, §4 ④, and §6 checklist — leaving contradictory recommendations that will mis-route the next session.

> Note: Cross-review provider returned an error (codex stdin read failure, no findings produced). All findings below are sourced from Critic. Per aggregation rule #2, single-source findings with strong evidence (verified grep/line citations against HEAD) are accepted.

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [Critical] §7 referenced 4× but missing from document
- **Critic**: §7 cited at lines 8, 17, 18, 20 but `wc -l = 176` and grep for §7 headers returns 0 matches.
- **Cross**: not flagged (provider error).
- **Judgment**: Accepted — verifiable via grep on the file. The §0 entry guide depends entirely on §7.3/§7.4/§7.5 which don't exist; "session handoff, self-contained" promise (line 4) is broken.
- **Action Required**: Either (a) write §7 (후속 합의 + D1~D9 의사결정 + P0 단계 트리) before merging, or (b) move the redirection target into the planned `docs/2026-05-04-af-research-quality-gate-design.md` and rewrite §0 to point there directly.

#### 2. [ACCEPT] [High] §0 deprecation not propagated to §3 ⑥ / §4 ④ — readers see contradictory recommendations
- **Critic**: §3 ⑥ (104-109) unchanged; §4 ④ (135) still bears "⭐ 본질 해결책" emphasis. Partial revision leaves baseline contradictions — exactly what `feedback_cross_review_stale_baseline_repeat` warns against.
- **Cross**: not flagged (provider error).
- **Judgment**: Accepted — line 135 verbatim in source still says "⭐ **본질 해결책**". Reader who jumps to §4 will not see the supersede.
- **Action Required**: Strike-through `~~⭐ 본질 해결책~~` at §4 ④ heading and add `> ⚠️ 폐기 — §0 참조` inline. For §3 ⑥, quote the specific deprecated sentence (current "표현 일부" is too vague).

#### 3. [ACCEPT] [High] §6 checklist still instructs creating deprecated §4 ④ design doc
- **Critic**: Line 175 `- [ ] 중기 ④ 설계문서 작성: docs/2026-05-XX-intent-routed-output-formats.md` contradicts §0 line 22.
- **Cross**: not flagged (provider error).
- **Judgment**: Accepted — verified at line 175. Action-oriented next-session reader uses checklist; will create the deprecated doc.
- **Action Required**: Replace with `- [x] ~~중기 ④ 설계문서~~ — §0/§7 폐기` and add `- [ ] 신규 통합 설계문서 작성: docs/2026-05-04-af-research-quality-gate-design.md`.

#### 4. [ACCEPT] [High] §4 ① prescription overstates blast radius — single researcher fix is sufficient
- **Critic**: `core/work_item_generator.py:535` already does `json.dumps(project_brief, ensure_ascii=False)`. If researcher saves `original_request` into `project_brief`, all 4 generators receive it without modification. "4 generators 동시 수정" framing inflates scope.
- **Cross**: not flagged (provider error).
- **Judgment**: Accepted — claim is grep-verifiable in `work_item_generator.py`. Reduces real change to 1 schema field in researcher.
- **Action Required**: Reframe ① to: "researcher.py:919 출력 schema에 `original_request` 필드 추가 (1곳). 4 generator는 이미 `project_brief` 직렬화로 prompt에 흐름 — explicit `## Original User Request` 섹션이 필요한 경우에만 추가".

#### 5. [ACCEPT] [Medium] Line-number citation convention inconsistent — weakens "HEAD 정합" claim
- **Critic**: `:528` cited as `_generate_feature_plan` but def is at `:522`; `:528` is body line. Same for `:568, :605, :642`.
- **Cross**: not flagged (provider error).
- **Judgment**: Accepted — convention drift makes "cross-review verified" claim hard to audit (memory `feedback_cross_review_stale_baseline_repeat` applies).
- **Action Required**: Standardize on `def`-line citations OR annotate body-line citations: e.g., `core/work_item_generator.py:528 (goal extraction inside _generate_feature_plan, def at :522)`.

#### 6. [ACCEPT] [Medium] "cross-review 검증 완료" self-claim unverifiable
- **Critic**: Line 16 lacks run-id, verdict file path, or trace link. Memory `feedback_cross_review_stale_baseline_repeat` warns about cross-review false positives on docs with spec churn (this doc had §0 정정 — high churn signal).
- **Cross**: not flagged (provider error — ironically reinforces the point).
- **Judgment**: Accepted — claim cannot be relied upon without provenance, especially given today's actual cross-review provider error.
- **Action Required**: Add `(cross-review run: <path-to-verdict.md>)` or downgrade to `(self-grep verified, not cross-review)`.

#### 7. [ACCEPT] [Medium] §4 ② Goals/Non-Goals schema change lacks backward-compat path
- **Critic**: `researcher.py:964` outputs `"goal": "single sentence"` (string). Proposal silently switches to structured object. Existing work-items have flat string; generators read `project_brief.get("goal")` as string at `:528, :568, :605`.
- **Cross**: not flagged (provider error).
- **Judgment**: Accepted — schema migration not addressed. Existing briefs would break under naive read.
- **Action Required**: Add to ②: "기존 work-item brief는 flat goal string — generator는 `goals_explicit or [goal]` 패턴으로 dual-read; researcher 출력만 신 schema 우선".

#### 8. [ACCEPT] [Medium] §4 ⑤ hard-coded domain whitelist doesn't generalize
- **Critic**: Whitelist `*.wsop.com`, `*.pokertda.com`, `*.w3.org`, `*.ietf.org` is poker/standards-specific; AF task domain is unbounded → unmaintainable.
- **Cross**: not flagged (provider error).
- **Judgment**: Accepted on architectural grounds — unbounded task distribution makes hardcoded list a future liability.
- **Action Required**: Replace with intent-driven query boost ("official rules" / "specification" / "RFC" auto-injection) without domain whitelist, or move whitelist into per-task metadata.

### Missing from Design (gap notes — not blocking but should be added)
- §7 contents (D1~D9 의사결정, P0/P1/P2 단계 트리)
- frozen build (`af.spec` hiddenimports) impact if new modules added
- Quantified acceptance criteria for "Manus 수준 근접" (룰 출처 ≥ 4건, JSON 메시지 ≥ 1건, 좌석 명시 등)
- Regression analysis on `plan_verifier.py:200` from `goal` schema change
- Non-Korean task input handling for `_collect_local_references()` domain matching

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §7 referenced 4× but missing | Critical | ACCEPT | Critic |
| 2 | §0 deprecation not propagated | High | ACCEPT | Critic |
| 3 | §6 checklist instructs deprecated action | High | ACCEPT | Critic |
| 4 | §4 ① overstates blast radius | High | ACCEPT | Critic |
| 5 | Line-number citation inconsistent | Medium | ACCEPT | Critic |
| 6 | "cross-review verified" unverifiable | Medium | ACCEPT | Critic |
| 7 | §4 ② schema change lacks backcompat | Medium | ACCEPT | Critic |
| 8 | §4 ⑤ hardcoded whitelist | Medium | ACCEPT | Critic |

### Recommendations (in order)

Before re-submitting for review:

1. **(Blocker)** Resolve §7 — either write the section or redirect §0 to the new integrated design doc.
2. **(Blocker)** Propagate the §0 deprecation into §3 ⑥, §4 ④, and §6 checklist (Findings #2, #3) so the body matches the header.
3. Reframe §4 ① to acknowledge `project_brief` is already serialized into prompts (Finding #4).
4. Add backward-compat dual-read pattern to §4 ② (Finding #7).
5. Replace domain whitelist in §4 ⑤ with intent-driven query boost (Finding #8).
6. Standardize line-number citation convention with one of the two formats in Finding #5.
7. Either cite the cross-review verdict path or drop the "cross-review 검증 완료" claim (Finding #6).

> **Process note**: Cross-review provider errored out (codex stdin failure). Per CLAUDE.md "Tier 3 fan-out" rule, if all external providers fail this becomes a SKIP (auto-PASS for Tier 3). However, the Critic's Critical finding (§7 missing) is independently verifiable via grep and stands on its own — verdict remains BLOCK.