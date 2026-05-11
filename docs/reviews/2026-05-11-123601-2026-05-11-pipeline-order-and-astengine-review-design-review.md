# Design Review: 2026-05-11-pipeline-order-and-astengine-review

> Source: docs/2026-05-11-pipeline-order-and-astengine-review.md
> Date: 2026-05-11 12:36
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

cross-review가 provider 에러(`codex` 호출 stdin 실패)로 실질 응답을 반환하지 못했음을 먼저 명시. 따라서 본 판정은 **Critic 단독 근거 + 원문 직접 검증**에 의존하며, 향후 cross-review 재실행이 가능하면 결과를 추가 반영해야 함.

Critic의 9건 발견 중 High 3건은 원문 검증 결과 모두 사실로 확인됨. 다만 모두 "문서 완성도/구조" 차원이며 코드 수정을 차단할 Critical 결함은 없음 → **WARN** (구현 단계로 직행하지 않고 문서 보강 후 진행 권장).

### Aggregated Findings (9 total)

#### 1. [ACCEPT] [High] 본 문서는 "결정문"이 아닌 "조사 보고서/질문지"
- **Critic**: §5 Q1~Q4가 전부 "확인 필요"·"동의 여부"로 코덱스에 위임. §4.4 권장 조치도 한 줄 스케치.
- **Cross**: provider error — 미확인.
- **Judgment**: 원문 line 356~382 직접 검증 — 정확. 본 문서 머리말도 line 7에서 "분석 결과의 초안이며, 코덱스 cross-review 미실시"라고 자인. 설계문서로서의 결정·수용기준 부재.
- **Action Required**: 본 문서를 `docs/investigations/2026-05-11-...md`로 *조사 보고서* 명시 이동 또는 머리말에 "본 문서는 진단 결과물이며 설계 결정은 Q3 회신 후 별도 work-item으로 분리"를 명시. Q3 답변 후 `docs/work-items/ast-engine-revival/{spec,design,tasks,plan}.md` 4종을 작성하여 결정·수용기준·테스트 계획을 분리.

#### 2. [ACCEPT] [High] §2.2 약점 4건이 §4와 비교해 정적 추적 깊이 불균형
- **Critic**: §4는 grep + 라인번호로 검증 가능하지만, §2.2 약점 1~4는 "확인 필요" 질문만 있고 코드 추적 비어있음. §4와 동일한 grep/라인 인용 수준 요구.
- **Cross**: provider error — 미확인.
- **Judgment**: 원문 line 109~148 직접 검증 — 약점 1은 "코드 추적 결과 ~로 위임됨"만 한 줄, 약점 2~4 모두 grep 명령 없음. 반면 §4.1·§4.2는 검증 grep까지 첨부됨. 사실로 확인.
- **Action Required**: §2.2 각 약점 블록에 §4 스타일의 grep 명령과 파일:라인 인용을 추가. 특히 약점 1 `_execute_agent_task` 실제 분기 코드 한 단락 인용으로 "양쪽 동시 발화 경로 유무"를 본 문서 단계에서 답하기.

#### 3. [ACCEPT] [High] §4.4 (b) 권장안의 비용·시퀀스 분석 부재
- **Critic**: (b) 채택 시 git diff 추출 + AST 파싱 + pub/sub broadcast가 매 step마다 추가됨. §2.1이 "0-토큰 경로 우선"을 칭송하면서 (b)는 0-토큰 경로에 IO+CPU를 더하는 변경. parse 시간·5에이전트 폭주·snapshot 동시쓰기 race 모두 미언급.
- **Cross**: provider error — 미확인.
- **Judgment**: 원문 line 346~352 표 직접 검증 — (b)의 비용·시퀀스·rollback 모두 부재. Critic의 worst-case 모델(O(5×5) callback per step) 추산은 합리적.
- **Action Required**: §4.4 표 옆에 "비용 분석" 부속 섹션 추가. (b) 채택 시 ① ast-grep-py 1회 parse 측정, ② subscribe callback SLA(현재 10s/콜백 timeout만, total cap 없음), ③ `.system_generated/cache/ast_hub_snapshot.json` Supabase sync 여부, ④ feature flag(`AF_AST_HUB_ENABLED`) rollback 경로를 명시. 비용 분석 없이는 (a) "Blueprint 축소"가 default여야 함을 본 문서가 결정.

#### 4. [ACCEPT] [Medium] §1 다이어그램의 `approval_gate.*` 네임스페이스 오기
- **Critic**: §1 line 49에 `approval_gate.read_block_decision()`로 표기되었으나 실제로는 `WarningRegistry`. 짧은 주석으로 정정 시도했으나 §2.2까지 가야 두 게이트가 별개 모듈임을 알 수 있음.
- **Cross**: provider error — 미확인.
- **Judgment**: 원문 line 49 `approval_gate.read_block_decision()  # WarningRegistry escalation` 직접 확인. 실제 호출 모듈이 다르므로 다이어그램 오기가 맞음.
- **Action Required**: §1 line 49를 `warning_registry.read_block_decision()`으로 정정. §2.2 약점 4에 "두 게이트는 서로 다른 도메인(quality blocker vs human gate) — short-circuit은 의미적으로 부적절할 수 있음"을 추가.

#### 5. [ACCEPT] [Medium] §4.2 "publish no-op" 표현 정확성 + (b) 폭주 시나리오 부재
- **Critic**: 정확히는 callback 빈 리스트 시 *조기 반환*이지 no-op 아님. (b) 활성화 시 publish 폭주 worst-case 모델 부재.
- **Cross**: provider error — 미확인.
- **Judgment**: 표현 정확성은 minor. 폭주 시나리오 부재는 Finding #3과 합쳐서 핵심 보강 사항.
- **Action Required**: §4.2 결함 3 표현을 "callbacks 빈 → 조기 반환(즉 현 시점에는 effective no-op)"로 정확화. (b) 폭주 시나리오는 Finding #3 보강에 포함.

#### 6. [ACCEPT] [Medium] Frozen build / af.spec 영향 미언급
- **Critic**: `dist/af/af.exe` 배포 환경에서 (b) 채택 시 `hiddenimports` 추가·번들 크기 영향 미평가. `review_bundle.py:8`의 grep fallback 경로도 frozen에서 어떻게 동작할지 미정.
- **Cross**: provider error — 미확인.
- **Judgment**: 본 프로젝트는 frozen exe 배포 표준(CLAUDE.md §빌드). 코드 통합 결정에 frozen 영향 분석은 필수.
- **Action Required**: §4.4 표에 "frozen 빌드 영향" 행 추가. (b) 채택 시 `af.spec` hiddenimports 패치·ast-grep-py 번들 크기 측정 명시.

#### 7. [ACCEPT] [Medium] 수용 기준 및 테스트 계획 부재
- **Critic**: Q1~Q4 답변 후 "해결됐다"의 객관 기준 없음. (b) 채택 시 어떤 단위 테스트가 통과해야 하는지 미정.
- **Cross**: provider error — 미확인.
- **Judgment**: Karpathy 4원칙 §4 "Goal-Driven Execution" — 본 프로젝트 CLAUDE.md 최상단 정책과 직접 충돌. 검증 가능 목표 없이는 구현 단계 진입 불가.
- **Action Required**: 후속 work-item 문서 작성 시 "수용 기준" 섹션 필수. 예: `tests/test_ast_memory_hub_integration.py`의 X assertion 통과, hub_snapshot.json round-trip 테스트.

#### 8. [ACCEPT] [Low] §3 28-category 분할이 "실행 순서"가 아닌 혼합 구조
- **Critic**: Cat L~R은 동시 작동 layer, Cat Q는 분기, Cat V~W는 백그라운드 — "순서대로 재정렬"이라는 표제와 불일치.
- **Cross**: provider error — 미확인.
- **Judgment**: 원문 line 152 표제 "파이프라인 순서대로 카테고리 재정렬"과 line 197~243 (Cat L~R 동시 layer), line 252~256 (Cat V~W 백그라운드)이 실제로 불일치. 사실 확인.
- **Action Required**: §3 표제를 "파이프라인 구성 요소 28개 (실행 단계 + 항상 동작 레이어 + 분기 + 백그라운드)"로 정정하거나, 시간축/레이어 다이어그램을 분리.

#### 9. [ACCEPT] [Low] 본 문서의 메타 위치 모호 — `[af-design-review-pending]` 자동 발화의 입력으로 부적합
- **Critic**: 자동 발화된 af-cross-review가 무엇을 cross-review할지(분석 결과? 질문 4개?) 모호.
- **Cross**: provider error — 미확인. (역설적으로 이 finding을 cross-review가 실제로 처리하지 못한 사실이 finding을 뒷받침.)
- **Judgment**: 본 응답 자체가 cross-review 실패로 critic 단독 판정이 된 상황이 finding을 강화. 검토 트랙이 흐려지는 위험 실재.
- **Action Required**: Finding #1과 합쳐서 처리 — `docs/investigations/`로 분류 명시 또는 머리말에 "조사 보고서, 설계 결정은 후속 work-item에서" 명시.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | 결정문이 아닌 위임 | High | ACCEPT | Critic (cross 미응답) |
| 2 | §2.2 추적 깊이 불균형 | High | ACCEPT | Critic |
| 3 | §4.4 (b) 비용 분석 부재 | High | ACCEPT | Critic |
| 4 | §1 approval_gate 오기 | Medium | ACCEPT | Critic |
| 5 | publish no-op 표현 + 폭주 시나리오 | Medium | ACCEPT | Critic |
| 6 | Frozen build 영향 미언급 | Medium | ACCEPT | Critic |
| 7 | 수용 기준/테스트 계획 부재 | Medium | ACCEPT | Critic |
| 8 | 28-category 분할 표제 부정합 | Low | ACCEPT | Critic |
| 9 | 문서 메타 위치 모호 | Low | ACCEPT | Critic |

### Recommendations

1. **본 문서 분류 재정의** — 머리말에 "조사 보고서이며 설계 결정문 아님" 명시 또는 `docs/investigations/`로 이동. (Finding #1·#9)
2. **§1 다이어그램 line 49 오기 즉시 정정** — `warning_registry.read_block_decision()`. (Finding #4)
3. **§2.2 약점 1~4에 §4 스타일 grep + 파일:라인 인용 추가** — 코덱스가 같은 추적을 반복하지 않도록. (Finding #2)
4. **§4.4 표에 "비용 분석" + "frozen 빌드 영향" + "rollback 경로" 행 추가** — (b) 채택을 권장하려면 필수. (Finding #3·#5·#6)
5. **§3 표제 정정** — "파이프라인 구성 요소 28개 (실행 단계 + 레이어 + 분기 + 백그라운드)". (Finding #8)
6. **후속 단계 분리 명시** — 본 문서 → 코덱스 deliberation(Q1~Q4 답변) → `docs/work-items/ast-engine-revival/` 4종 작성(spec/design/tasks/plan) — 후속 문서에서 수용 기준·테스트 계획·feature flag(`AF_AST_HUB_ENABLED`)를 결정. (Finding #1·#7)
7. **Cross-review 재실행 권장** — `codex` provider 에러로 cross 결과가 누락됨. provider 상태 점검 후 재발화 또는 본 판정에 대한 사용자 confirm 후 진행.