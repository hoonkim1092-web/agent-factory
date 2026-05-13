# Design Review: 2026-05-13-superpowers-11-skills-quality-verification

> Source: docs/codex_논의/2026-05-13-superpowers-11-skills-quality-verification.md
> Date: 2026-05-13 14:29
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

다수의 High-severity 코드 인용 오류(존재하지 않는 파일·잘못된 cap·stale wire-up 주장)가 §3·§4의 핵심 명제("정적 분석 + 코드 실측 file:line 명시")를 직접 훼손하며, 흡수 5개 중 3개 항목(brainstorming/verification-before-completion/finishing-a-development-branch)의 구현 contract가 미명세. 5/11 v2 작성 전 좌표 정정 필수.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [High] `core/project_planning_director.py` 파일은 실재하지 않음
- **Critic** (#3): §2 line 54, §3.5 line 166에 인용된 파일 없음. `ProjectPlanningDirector` 클래스는 `core/bootstrap_roles.py:120`에 정의됨
- **Cross** (#1): 동일 — `ProjectPlanningDirector.generate_research_brief()`도 실재하지 않음. 실제 메서드는 `plan()` (`core/bootstrap_roles.py:398`), pipeline 호출은 `core/project_pipeline.py:880`
- **Judgment**: 양측 강력한 file:line 증거. 핵심 비교 매트릭스의 신뢰성 훼손.
- **Action Required**: §2 표 line 54와 §3.5 line 166-167을 `core/bootstrap_roles.py` (class `ProjectPlanningDirector`)로 교체. 메서드명 `generate_research_brief()` → `plan()`로 정정. 실제 흐름은 `prepare_brief() → ProjectPlanningDirector.plan() → enrich_role_plan() / build_project_board() → generate_work_items()`로 기술.

#### 2. [ACCEPT] [High] §3.4 `_select_task_skills` 코드 인용 오류 (8-cap vs 12-cap, 점수 체계 없음)
- **Critic** (#1): `core/agent_specializer.py:202`는 `return result[:8]` — 8-cap. line 193-198는 substring 키워드 매치이며 0.35×0.40×0.25 가중 점수 체계는 코드에 없음
- **Cross**: 별도로 flag하지 않음
- **Judgment**: Critic의 file:line 인용이 구체적이고 강력. 본 문서가 자기 선언한 "코드 실측" 원칙 위반.
- **Action Required**: §3.4 표 line 157을 "최대 8개, 키워드 부분일치"로 정정. "0.35×0.40×0.25" 삭제.

#### 3. [ACCEPT] [High] §3.4·§8 M8 (메모리 wire-up 미완) 주장은 stale
- **Critic** (#2): `core/agent_specializer.py:125-128`은 "M8 해소" 명시, `_fetch_episode_context`(:250)가 `UnifiedMemoryFacade.search_semantic(..., MemoryType.EPISODIC, limit=3)` 호출
- **Cross** (#6): 동일 결론 — `_build_task_prompt()`에서 episode section 빌드, `_fetch_episode_context()`로 facade 호출. Cross는 자기 finding을 REJECT(=design은 OK)했지만, 실측 자체는 Critic과 일치
- **Judgment**: 두 리뷰어 모두 "wire-up이 실재한다"는 코드 사실을 확인. 본 문서가 §3.4·§8에서 "wire-up 미완"이라 주장한 부분이 stale. Critic의 High 채택.
- **Action Required**: §3.4 line 158 행을 "에피소드 메모리 회상 — `_fetch_episode_context` 경유 wire-up 완료, semantic search top-3"로 정정. §8 line 278 "M8 미완" 항목 삭제. 단, "Jaccard 0.4 임계"는 `EpisodeMatcher` 별도 모듈이며 specializer 경로에 적용 여부 별도 grep 검증.

#### 4. [ACCEPT] [High] `domain-review.md §1.5` 흡수의 파일 contract 미명세
- **Critic** (Missing from Design): 흡수 실패 시 롤백 경로 부재 언급
- **Cross** (#2): `docs/work-items/_template/`에 `domain-review.md` 파일이 *존재하지 않음*. `core/work_item_generator.py:1391-1394`은 verification-report/change-request/bug-fix-spec 3개만 복사
- **Judgment**: Cross의 file 부재 증거가 직접적 강력함. brainstorming 흡수의 implementation entrypoint가 비어있음.
- **Action Required**: (a) `docs/work-items/_template/domain-review.md` 파일을 생성하거나 본 문서에 명시. (b) machine-readable section contract 정의: `verdict: PASS|WARN|BLOCK`, 질문/답변 필드, parser/gate caller 좌표. (c) `core/clarification.py` 재사용 검토 (별도 question-gen 경로 신설 회피).

#### 5. [ACCEPT] [High] verification-before-completion 흡수 wiring 미명세
- **Critic**: Missing from Design — "회귀 테스트 plan 없음, acceptance criteria 미정의"
- **Cross** (#4): "verdict 강화"는 구현 불가 — 현 propagation 경로는 `scripts/verify_handoff_checker.py:45,105` + `.githooks/pre-commit:92-108` + `scripts/nightly_tick.py` + `ApprovalGate.apply_verification_verdict()`로 분산
- **Judgment**: 양측이 다른 각도에서 같은 underspecification을 짚음.
- **Action Required**: `verification-report.md` schema + caller 좌표 + 실패 코드 정의. 회귀 테스트 케이스 명시 (missing report, empty `e2e_command`, `verdict: BLOCK`, pre-commit staged path, nightly sweep, `ProjectPipeline.execute()`).

#### 6. [ACCEPT] [Medium] Review-gate 강제력은 skill/doc-only 변경에 과대평가
- **Critic**: 별도 flag 없음 (Missing from Design "Frozen build 호환성" 항목에서 일부 시사)
- **Cross** (#5): `scripts/review_gate.py`는 `.py` 변경만 필터링 — `SKILL.md`, `_template/**`, `docs/codex_논의/**`는 `no-py-files`로 PASS. `.githooks/pre-commit`도 `core/*.py`, `skills/*/skill.py` 등 한정
- **Judgment**: Cross의 코드 인용 명확. 본 문서가 §3.6에서 "강제 시스템"으로 일반화한 부분과 충돌.
- **Action Required**: §3.6에 "단, `.py` 미포함 변경(SKILL.md, 템플릿, docs)은 게이트 대상 외 — 별도 수동 design review 필요"를 명시하거나, doc/skill 게이트 경로(`skills/**/SKILL.md`, `docs/work-items/_template/**`)를 추가.

#### 7. [ACCEPT] [Medium] §3 "비선형 상승" / "품질 multiplier" 정량 표현은 측정값 부재
- **Critic** (#4): §3.1 "결함 검출 곡선 비선형 상승" / §3.7 — §8 자인 "런타임 실측 미수행". BLOCK 5건의 Tier별 분포 미인용
- **Cross** (#7): HOLD — 6개 보류를 정당화한다면 measurable criteria 필요 (defect catch-rate by tier, FP rate, latency)
- **Judgment**: Critic Medium + Cross HOLD = Medium ACCEPT. 정성 framing은 유지 가능하나 정량 어휘는 약화 필요.
- **Action Required**: "비선형 상승" → "결함 검출 범위가 직교 누적" 류로 약화. 또는 부록에 BLOCK 5건의 Tier 출처 표(`project_auto_approve_block_followup.md` 참조) 첨부.

#### 8. [ACCEPT] [Medium] §4 LOC 추정은 §5 #4 비판을 자기 표에 적용 안 함
- **Critic** (#5): §4 표 80/120/50/0/0 LOC가 §5 line 243 "Phase C LOC 자가모순" 비판과 동일 결함
- **Cross**: 별도 flag 없음
- **Judgment**: Critic의 자기 일관성 지적이 타당. LOC 표 신뢰도 표시 필요.
- **Action Required**: §4 LOC 셀에 "(±50% 추정)" 표기 또는 실측 후 갱신 마커.

#### 9. [ACCEPT] [Medium] §4 "흡수 5개" 실질 코드 변화는 3개
- **Critic** (#6): #4 TDD "0 (통합)", #5 worktrees "0" — 실질 변경 표면 3건. "5개 흡수"로 호명 시 비용·일정 과대평가
- **Cross**: 별도 flag 없음
- **Judgment**: Critic 단독이지만 §4 표 자체에 명시된 사실로부터 도출되어 evidence 강함.
- **Action Required**: §6 line 261, §7 line 270을 "코드 변경 3개 + 문서/SKILL 통합 2개"로 재표기.

#### 10. [HOLD] [Medium] 신규 gate/doc write에 non-atomic `write_text()` 경로 사용 우려
- **Critic**: 별도 flag 없음
- **Cross** (#3): `core/file_io.py:117` `write_text()`는 직접 open/write. `core/approval_gate.py:141,218,240,416` + `core/work_item_generator.py:1118,1142,1147,1173` 모두 이 경로 사용. code-review context의 cross-cutting risk
- **Judgment**: 본 설계 문서가 *직접* 다루는 범위는 아니지만, 흡수 #3 (verification verdict 강화)·#1 (domain-review.md write)이 추가 write를 유발하므로 관련성 있음. 본 문서에서 결정해야 하는지, 별도 P5 follow-up인지 저자 판단 필요.
- **Question for Author**: 본 흡수 작업에서 `atomic_write_text()` 도입을 in-scope로 할 것인가, 아니면 별도 follow-up으로 분리할 것인가? in-scope라면 §4 LOC + §6 일정 갱신 필요.

#### 11. [REJECT] [Low] §2 file:line 누락 (`escalation_evaluator.py`) / 좌표 표기 불일치 (`:307`,`:311` vs `:307-337`)
- **Source**: Critic (#7, #8)
- **Original Finding**: 일관성 개선 제안
- **Rejection Reason**: 일관성 개선으로서 valid하나, BLOCK 수준의 1차 우선순위는 아님. Action #1~#9 처리 시 함께 cleanup하면 충분 — 별도 항목으로 트래킹하지 않음. (저자가 정정해도 좋고, 우선순위 낮음)

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | project_planning_director.py 부재 | High | ACCEPT | Both |
| 2 | _select_task_skills 8-cap·점수체계 없음 | High | ACCEPT | Critic |
| 3 | M8 wire-up 미완 주장 stale | High | ACCEPT | Both (Cross는 reject로 표기했으나 사실 일치) |
| 4 | domain-review.md 파일·contract 부재 | High | ACCEPT | Cross |
| 5 | verification-before-completion wiring 미명세 | High | ACCEPT | Cross + Critic missing-section |
| 6 | review-gate 강제력 skill/doc 변경에 과대 | Medium | ACCEPT | Cross |
| 7 | "비선형 상승" 측정값 부재 | Medium | ACCEPT | Both |
| 8 | §4 LOC 자가모순 | Medium | ACCEPT | Critic |
| 9 | "흡수 5개" 실질 3개 | Medium | ACCEPT | Critic |
| 10 | non-atomic write_text 위험 | Medium | HOLD | Cross |
| 11 | file:line 누락·좌표 불일치 | Low | REJECT | Critic |

### Recommendations

구현 진입 전 다음을 v2(또는 본 문서 in-place 갱신)에 반영:

1. **좌표 정정 일괄 (Finding #1, #2, #3)** — `core/bootstrap_roles.py` 교체, `_select_task_skills` 8-cap·substring 매치 정정, M8 wire-up 완료 사실 반영. grep으로 메서드명·라인 재검증.
2. **흡수 contract 명세 (Finding #4, #5)** — `domain-review.md` 템플릿 파일 생성 + section schema, verification-report.md schema + caller 좌표 + 회귀 테스트 케이스 정의.
3. **§3.6 강제력 표현 약화 (Finding #6)** — `.py` 미포함 변경은 게이트 대상 외라는 한계를 명시.
4. **정량 어휘 약화 (Finding #7)** — "비선형 상승" → "직교 누적". BLOCK 5건 Tier 출처 부록 첨부 시 정량 표현 복원 가능.
5. **LOC·범위 재표기 (Finding #8, #9)** — ±50% 마커, "코드 3개 + 문서 2개" 분리.
6. **저자 판단 필요 (Finding #10)** — `atomic_write_text()` in-scope 여부 결정.
7. **5/11 BLOCK 11건 동기화 (Critic missing-section)** — v2와 본 문서의 관계 명시 (같은 문서 갱신 vs 별도 추적).