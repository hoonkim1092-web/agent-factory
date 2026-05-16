# Implementation Tasks

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | implement-a-browser-poker-game |
| source_design | Implementation Design (2026-05-16) |
| status | pending |
| last_updated | 2026-05-16 |

---

## Preconditions

- Node.js 16+ 설치 완료 (ESM 테스트 실행 환경)
- `npx serve` 사용 가능 (로컬 HTTP 서버, `file://` CORS 우회)
- `docs/architecture.md` § Modules 섹션 존재 확인 — game rules·game ui 모듈 설명 추가 기준 문서
- 브라우저: Chrome 87+ 또는 Firefox 78+ (ESM `<script type="module">` 지원)
- 외부 빌드 파이프라인 없음: 번들러·트랜스파일러 사용 금지

---

## Task Evidence

| 증거 ID | 출처 | 핵심 발견 | 관련 태스크 |
|---------|------|-----------|------------|
| E-01 | `docs/architecture.md` § Modules (신뢰도 0.9) | "game state is split by module" — 규칙 모듈과 UI 모듈의 완전 분리 결정 근거 | T-001, T-002, T-004, T-005 |
| E-02 | Poker rules 웹 참조 (신뢰도 0.8) | "verify state transitions and winner evaluation" — 핸드 평가·상태 전이 테스트 체크포인트 설계 근거 | T-006, T-008, T-009 |
| E-03 | 노트북 요약 | "Prefer isolated game-rule modules and explicit verification checkpoints" — `src/rules/`를 DOM 의존 없이 격리, `tests/rules.test.js` Node.js 단독 실행 근거 | T-004, T-006, T-009 |
| E-04 | Implementation Design § Risks R-01 | 에이스 로우 스트레이트·킥커 동점 처리 버그 위험 — 경계 케이스 테스트 TC-03~TC-05, TC-08 필수 | T-006, T-008 |
| E-05 | Implementation Design § Risks R-03 | 상태 전이 누락(올인·연속 폴드) — 허용 전이 테이블 + 명시적 `throw` 설계 근거 | T-004 |

## Source Alignment

| 원천 데이터 항목 | 문서 반영 위치 | 정합성 기준 |
|------------------|----------------|-------------|
| goal: Implement a browser poker game | T-004, T-005, Definition Of Done | 브라우저에서 실행되는 포커 게임 UI와 규칙 엔진을 모두 산출한다 |
| constraints: network_allowed | Preconditions, T-005 | 네트워크 허용 환경이나 vanilla JS 구현은 외부 CDN·API 없이 로컬 실행만 의도한다; 향후 멀티플레이어 확장 시 활용 가능 |
| required_skills: frontend_game_ui | T-002, T-005, T-008 | game ui 스킬 — UI 컴포넌트 렌더링·이벤트 처리·CSS 레이아웃을 scope→build→verify 3단계로 완주한다 |
| required_skills: gameplay_core | T-001, T-004, T-007 | game rules 스킬 — 핸드 평가·상태 전이·승자 판정 로직을 scope→build→verify 3단계로 완주한다 |
| required_skills: integration_test_guard | T-003, T-006, T-009 | test checklist 스킬 — 자동화 TC-01~TC-08 + 수동 시나리오 8항목으로 규칙 엔진을 통합 검증한다 |
| role_hints: frontend_dev | T-001, T-002, T-004, T-005, T-007, T-008 | 프론트엔드 개발자가 game rules·game ui 모듈의 scope+build+verify 6태스크를 담당한다 |
| role_hints: qa_engineer | T-003, T-006, T-009 | QA 엔지니어가 test checklist 모듈의 scope+build+verify 3태스크를 담당한다 |
| tech_stack: vanilla_js | Preconditions, T-001~T-006 | 번들러·트랜스파일러 없이 ESM 기반 vanilla JavaScript로 구현한다 |
| deliverables: game ui, game rules, test checklist | T-004, T-005, T-006 | 세 산출물이 각각 독립 artifact로 생성되고 검증된다 |
| risk: rule evaluation bug | T-004, T-006, T-007, T-009 | 핸드 평가, 킥커, 동점, 7장 최강 조합을 자동 테스트로 검증한다 |
| notebook_summary: isolated game-rule modules + verification checkpoints | E-03, T-004, T-008 | `src/rules/` DOM import 0건 격리 원칙과 TC-01~TC-08 명시적 검증 체크포인트로 구현한다 |
| blast_radius: isolated | Rollback Sign-Off | 모듈 단위 롤백이 가능하며 다른 시스템에 영향을 주지 않는다 |
| local_references: `docs/architecture.md` § Modules | E-01, T-001, T-002, Definition Of Done | game state 분리 원칙을 규칙/UI 모듈 경계로 반영한다 |
| web_references: Poker rules | E-02, T-006, T-009 | 상태 전이와 승자 판정 검증을 테스트 체크리스트에 포함한다 |

---

## Cross-Verification Remediation

| 보강 항목 | 수정 기준 | 반영 위치 |
|-----------|-----------|-----------|
| 낮은 rubric score 보정 | 원천 데이터의 goal·deliverables·required_skills가 각 태스크와 검증 단계에 직접 연결되어야 한다 | Source Alignment, T-001~T-009 |
| rule evaluation bug 리스크 보정 | 핸드 평가 오류 가능성을 A-2-3-4-5 스트레이트, 킥커, 동점, 7장 최강 조합 테스트로 검증한다 | T-004, T-006, T-007, T-009 |
| 모듈 분리 근거 보정 | `docs/architecture.md` § Modules의 "game state is split by module" 원칙을 규칙/UI/test checklist 경계로 유지한다 | T-001, T-002, T-003, Definition Of Done |
| 웹 규칙 참조 보정 | Poker rules 웹 참조의 상태 전이·승자 판정 검증 요구를 자동화/수동 체크리스트에 모두 포함한다 | T-006, T-009 |
| 산출물 완결성 보정 | game ui, game rules, test checklist가 각각 artifact와 e2e_command를 가진다 | T-004, T-005, T-006 |

---

## Task List

### T-001 — game rules 범위와 인터페이스를 정의한다

- **task_id**: T-001
- **lineage_id**: frontend_dev_module_2_scope_1
- **owner_role**: Frontend Dev
- **phase**: scope
- **depends_on**: []
- **estimated_complexity**: 낮음
- **acceptance**:
  - `src/rules/` 디렉터리 구조와 파일 목록(`deck.js`, `evaluator.js`, `stateMachine.js`, `index.js`)이 문서로 확정된다
  - 공개 API 시그니처 (`createDeck`, `shuffle`, `evaluateHand`, `compareHands`, `createGameState`, `transition`, `determineWinner`) 가 타입 주석 수준으로 고정된다
  - 카드·핸드·게임 상태·액션·승자 결과 타입 정의(`Card`, `HandResult`, `GameState`, `Action`, `WinnerResult`)가 확정된다
  - 핸드 순위 열거(rank 0~9)와 허용 액션 타입 목록이 정리된다
  - 의존성 목록: DOM 의존성 0개
- **artifacts**: `docs/rules-interface.md` (또는 `src/rules/README.md`)
- **e2e_command**: `grep -n "export" src/rules/index.js`
- **implementation_hint**: Design § M-1 공개 API 표를 그대로 복사해 인터페이스 문서를 작성한다. 타입 정의는 JSDoc `@typedef`로 기록하면 T-004 build 단계에서 직접 복사해 사용할 수 있다.

---

### T-002 — game ui 범위와 인터페이스를 정의한다

- **task_id**: T-002
- **lineage_id**: frontend_dev_module_1_scope_1
- **owner_role**: Frontend Dev
- **phase**: scope
- **depends_on**: []
- **estimated_complexity**: 낮음
- **acceptance**:
  - `src/ui/` 디렉터리 구조와 파일 목록(`index.js`, `renderer.js`, `dealerAI.js`, `style.css`)이 확정된다
  - `GameController`, `CardRenderer`, `BettingPanel`, `MessageDisplay`, `MessageBus` 컴포넌트 경계와 책임이 한 문장씩 정리된다
  - `GameController`가 M-1 API만 호출하고 규칙 로직을 직접 구현하지 않는다는 계약이 명시된다
  - `index.html` ESM 로드 구조(`<script type="module" src="src/ui/index.js">`)가 확정된다
  - UI가 소비하는 타입(`HandResult`, `WinnerResult`, `GameState`)이 T-001 계약과 연결된다
- **artifacts**: `docs/ui-interface.md` (또는 `src/ui/README.md`)
- **e2e_command**: `grep -n "class\|function\|export" src/ui/renderer.js`
- **implementation_hint**: Design § M-2 핵심 컴포넌트 표를 기반으로 작성한다. `GameController`의 책임 경계(이벤트 수신 → action 생성 → `transition()` 호출 → 렌더링 트리거)가 흐림 없이 서술되어야 T-005 build에서 결합 위험(R-02)을 사전 차단할 수 있다.

---

### T-003 — test checklist 범위와 인터페이스를 정의한다

- **task_id**: T-003
- **lineage_id**: qa_engineer_module_3_scope_1
- **owner_role**: QA Engineer
- **phase**: scope
- **depends_on**: []
- **estimated_complexity**: 낮음
- **acceptance**:
  - 자동화 테스트 파일(`tests/rules.test.js`)과 수동 체크리스트 파일(`tests/checklist.md`)의 역할과 실행 방법이 구분된다
  - TC-01~TC-08 8개 자동화 테스트 케이스 ID와 검증 항목이 초안으로 열거된다 (T-006 acceptance 기준)
  - TC-01 덱 52장/중복 없음, TC-02 핸드 순위 10종, TC-03 A-2-3-4-5 스트레이트, TC-04 킥커 비교, TC-05 완전 동점, TC-06 승자 판정, TC-07 허용되지 않은 액션, TC-08 7장 최강 조합을 포함한다
  - 수동 체크리스트 항목 8개 (브라우저 시나리오)가 초안으로 열거된다
  - 수동 체크리스트는 초기화, 프리플랍 진입, fold, call, raise, 쇼다운 승자 표시, 새 게임 초기화, 브라우저 콘솔 오류 0건을 포함한다
  - `tests/rules.test.js`가 DOM 없이 `node tests/rules.test.js`로 실행 가능해야 한다는 제약이 확정된다
  - QA가 M-1 공개 API만 호출하며 내부 구현에 접근하지 않는다는 계약이 명시된다
- **artifacts**: `tests/checklist.md` (초안), `tests/rules.test.js` (파일 뼈대)
- **e2e_command**: `node tests/rules.test.js 2>&1 | head -5`
- **implementation_hint**: Design § Test Strategy의 케이스 표와 수동 체크리스트 8항목을 그대로 옮겨 초안을 만든다. T-004(game rules build) 완료 전이므로 `import` 경로만 확보하고 assert 본문은 `// TODO`로 남긴다.

---

### T-004 — game rules 핵심 로직을 구현한다

- **task_id**: T-004
- **lineage_id**: frontend_dev_module_2_build_2
- **owner_role**: Frontend Dev
- **phase**: build
- **depends_on**: [T-001]
- **estimated_complexity**: 높음
- **acceptance**:
  - `src/rules/deck.js`: `createDeck()` → 52장 `Card[]` 반환, `shuffle(deck)` → Fisher-Yates 적용
  - `src/rules/evaluator.js`: `evaluateHand(cards)` → rank 0~9 + name + tiebreakers 반환 (10종 핸드 전부 구현)
  - `evaluateHand`가 7장(핸드 2장 + 커뮤니티 5장)을 받아 최강 5장 조합을 선택한다 (TC-08 검증 대상)
  - 에이스 로우 스트레이트(A-2-3-4-5)에서 A를 1로 처리한다 (R-01 완화, TC-03 검증)
  - `compareHands(a, b)` → `-1|0|1` 반환, 동점 킥커 비교 포함 (TC-04, TC-05 검증)
  - `src/rules/stateMachine.js`: 허용 전이 테이블이 존재하고, 미정의 액션 수신 시 `throw new Error('허용되지 않은 액션')` 발생 (R-03 완화, TC-07 검증)
  - `transition(state, action)` → 새 `GameState` 반환 (불변, 원본 변경 없음)
  - `src/rules/index.js`: 위 함수 전체를 named export로 재노출
  - DOM import 없음: `grep -rn "document\|window\|DOM" src/rules/` 결과 0건
- **artifacts**: `src/rules/deck.js`, `src/rules/evaluator.js`, `src/rules/stateMachine.js`, `src/rules/index.js`
- **e2e_command**: `node tests/rules.test.js`
- **implementation_hint**: `evaluateHand` 구현 시 7장 조합(C(7,5)=21가지)을 전부 생성해 최고 rank를 선택하는 brute-force 접근이 가장 안전하다. 에이스 처리는 rank 배열에서 14를 1로 복사한 별도 배열을 만들어 스트레이트 검사에 함께 적용한다. 상태 전이 허용 테이블은 객체 리터럴(`const ALLOWED = { preflop: ['DEAL', 'BET', ...] }`)로 선언하면 TC-07 테스트가 구조적으로 검증 가능해진다.

---

### T-005 — game ui 화면을 구현한다

- **task_id**: T-005
- **lineage_id**: frontend_dev_module_1_build_2
- **owner_role**: Frontend Dev
- **phase**: build
- **depends_on**: [T-002, T-004]
- **estimated_complexity**: 높음
- **acceptance**:
  - `index.html`: `<script type="module" src="src/ui/index.js">` 로 ESM 로드, 게임 레이아웃 마크업 포함
  - `src/ui/renderer.js`: `CardRenderer.render(cards, { faceUp })` 가 카드를 유니코드 또는 텍스트(A♠ 형식) DOM 요소로 변환한다
  - `src/ui/renderer.js`: `BettingPanel.enable(actions)` 가 fold/call/raise 버튼을 활성화하고, 칩 수량을 표시한다
  - `src/ui/renderer.js`: `MessageDisplay.show(winnerResult)` 가 핸드명 + 승자 + 획득 칩 메시지를 렌더링한다
  - `src/ui/index.js` (`GameController`): 사용자 클릭 이벤트를 `Action` 객체로 변환 후 `transition()` 호출, 반환된 `GameState`로 렌더링 트리거
  - `GameController`가 `evaluateHand`·`compareHands` 등 규칙 함수를 직접 호출하지 않는다 (`grep -n "evaluateHand\|compareHands" src/ui/` 결과 0건)
  - `src/ui/dealerAI.js`: `DealerAI.decide(state)` 가 단순 확률 기반 call/fold 결정을 반환한다
  - `src/ui/style.css`: 게임 화면의 기본 레이아웃(카드 슬롯, 베팅 영역, 팟 표시)이 스타일링된다
  - `npx serve .` 실행 후 브라우저에서 Phase 0(초기화) → Phase 1(프리플랍) 화면 전환이 동작한다
- **artifacts**: `index.html`, `src/ui/index.js`, `src/ui/renderer.js`, `src/ui/dealerAI.js`, `src/ui/style.css`
- **e2e_command**: `npx serve . & sleep 2 && open http://localhost:3000`
- **implementation_hint**: `GameController`는 `MessageBus` 패턴(DOM `CustomEvent` 또는 단순 콜백 객체)으로 렌더러와 통신한다. 렌더러가 규칙 모듈을 직접 import하는 구조는 R-02 위험이므로, `GameController`가 유일한 규칙 모듈 호출자가 되어야 한다. `DealerAI.decide`는 `state.pot`과 난수를 조합한 단순 조건문으로 구현하면 충분하다(과설계 불필요).

---

### T-006 — test checklist를 완성한다

- **task_id**: T-006
- **lineage_id**: qa_engineer_module_3_build_2
- **owner_role**: QA Engineer
- **phase**: build
- **depends_on**: [T-003, T-004]
- **estimated_complexity**: 중간
- **acceptance**:
  - `tests/rules.test.js`: TC-01~TC-08 8개 케이스가 전부 구현되고 `node tests/rules.test.js` 실행 시 모두 통과한다
  - TC-01 (덱 무결성): `createDeck()`가 52장을 반환하고 suit/rank 조합 중복이 없음을 검증한다
  - TC-02 (핸드 순위 10종): 하이카드부터 로열 플러시까지 rank 0~9가 각각 최소 1회 검증된다
  - TC-03 (에이스 로우 스트레이트): `evaluateHand`에 [A,2,3,4,5] 핸드를 전달하면 rank 4를 반환한다
  - TC-04 (킥커 비교): 같은 페어에서 더 높은 킥커가 승리함을 검증한다
  - TC-05 (동점): `compareHands(a, b)` → 0 반환을 검증한다
  - TC-06 (승자 판정): `determineWinner(state)`가 플레이어·딜러·무승부 결과를 반환한다
  - TC-07 (허용되지 않은 액션): `transition(state, { type: 'INVALID' })` 가 `Error`를 throw한다
  - TC-08 (7장 최강 조합): 7장 중 최강 5장 조합이 올바르게 선택된다
  - `tests/checklist.md`: 수동 시나리오 8개 항목이 체크박스(`- [ ]`) 형식으로 완성된다
  - 모든 테스트가 `import` 경로 오류 없이 실행된다
- **artifacts**: `tests/rules.test.js` (최종본), `tests/checklist.md` (최종본)
- **e2e_command**: `node tests/rules.test.js`
- **implementation_hint**: Node.js 내장 `assert` 모듈로 구현하면 외부 의존성이 없어 E-03 격리 원칙을 준수한다. 각 테스트는 `console.log('TC-01 PASS')` / `console.error('TC-01 FAIL:', e.message)` 패턴으로 출력하면 T-009 검증 단계에서 grep으로 결과를 자동 확인할 수 있다. `assert.strictEqual(result.rank, 4, 'A-2-3-4-5 스트레이트 rank 오판정')` 형식으로 실패 메시지를 한국어로 작성한다.

---

### T-007 — game rules 결과를 검증하고 handoff를 남긴다

- **task_id**: T-007
- **lineage_id**: frontend_dev_module_2_verify_3
- **owner_role**: Frontend Dev
- **phase**: verify
- **depends_on**: [T-004, T-006]
- **estimated_complexity**: 낮음
- **acceptance**:
  - `node tests/rules.test.js` 실행 결과 TC-01~TC-08 전부 PASS
  - `grep -rn "document\|window" src/rules/` 결과 0건 (DOM 의존성 없음 확인)
  - 규칙 모듈 공개 API가 T-001에서 정의한 인터페이스와 일치한다
  - 핸드 순위 rank 0~9 전체 케이스가 최소 1개 이상의 테스트로 커버된다
  - `docs/rules-handoff.md` 에 잔여 리스크(R-01 경계 케이스, 추가 테스트 필요 항목), 미구현 항목, T-005·T-006이 이어받아야 할 사항이 기록된다
- **artifacts**: `docs/rules-handoff.md`
- **e2e_command**: `node tests/rules.test.js 2>&1 | grep -E "PASS|FAIL"`
- **implementation_hint**: handoff 메모는 "완료된 것 / 남은 리스크 / 다음 담당자가 주의할 점" 3단 구조로 작성한다. R-01(킥커·동점 경계), R-03(허용 전이 테이블 완성 여부)를 명시한다.

---

### T-008 — game ui 결과를 검증하고 handoff를 남긴다

- **task_id**: T-008
- **lineage_id**: frontend_dev_module_1_verify_3
- **owner_role**: Frontend Dev
- **phase**: verify
- **depends_on**: [T-005, T-007]
- **estimated_complexity**: 중간
- **acceptance**:
  - `npx serve .` 로컬 서버에서 Phase 0 → Phase 1(프리플랍) → Phase 2(플랍) → Phase 3(쇼다운) → Phase 4(게임 오버) 전체 흐름이 오류 없이 실행된다
  - fold 버튼 클릭 시 Phase 4로 직행하고 팟이 즉시 수여된다
  - `grep -n "evaluateHand\|compareHands\|determineWinner" src/ui/` 결과 0건 (UI가 규칙 내부를 직접 호출하지 않음 — R-02 완화 확인)
  - 칩이 0이 되면 게임 오버 화면이 렌더링되고 '새 게임' 버튼으로 Phase 0 재초기화된다
  - 브라우저 콘솔에 JS 오류 없음
  - `docs/ui-handoff.md` 에 잔여 리스크(R-02 혼입 위험, 딜러 AI 개선 여지), 미구현 항목, QA가 이어받을 수동 체크리스트 실행 방법이 기록된다
- **artifacts**: `docs/ui-handoff.md`
- **e2e_command**: `npx serve . & sleep 2 && open http://localhost:3000`
- **implementation_hint**: 수동으로 fold·call·raise를 각 1회 이상 실행하고 칩 변화량이 올바른지 확인한다. 브라우저 DevTools Network 탭에서 ESM 모듈 로드 오류(CORS, 404)가 없는지 점검한다.

---

### T-009 — test checklist 결과를 검증하고 handoff를 남긴다

- **task_id**: T-009
- **lineage_id**: qa_engineer_module_3_verify_3
- **owner_role**: QA Engineer
- **phase**: verify
- **depends_on**: [T-006, T-007, T-008]
- **estimated_complexity**: 중간
- **acceptance**:
  - `node tests/rules.test.js` 최종 실행 결과 TC-01~TC-08 전부 PASS, FAIL 0건
  - `tests/checklist.md` 수동 시나리오 8항목을 브라우저에서 직접 실행하고 전부 체크(`- [x]`) 완료
  - 수동 시나리오 8항목은 초기화, 프리플랍 진입, fold, call, raise, 쇼다운 승자 표시, 새 게임 초기화, 브라우저 콘솔 오류 0건을 모두 포함한다
  - 특히 "에이스 로우 스트레이트 올바른 판정" 수동 항목을 쇼다운 화면에서 직접 확인한다 (R-01)
  - '새 게임' 버튼 클릭 후 상태가 완전히 초기화됨을 확인한다 (Phase 0 재진입)
  - 잔여 리스크와 후속 작업이 `docs/qa-handoff.md` 에 기록된다 (미해결 엣지 케이스, 자동화 확장 제안 포함)
- **artifacts**: `tests/checklist.md` (체크 완료본), `docs/qa-handoff.md`
- **e2e_command**: `node tests/rules.test.js 2>&1 | grep -c "PASS"`
- **implementation_hint**: 수동 체크 시 에이스 로우 스트레이트 재현은 덱을 [A,2,3,4,5,x,y] 조합으로 고정하거나 브라우저 콘솔에서 `transition()` 직접 호출로 재현한다. handoff 메모에는 "다음 개선 후보: 딜러 AI 강화, 올인 시나리오, 멀티 라운드 통계 표시"를 명시한다.

---

## Blockers

| ID | 설명 | 영향 태스크 | 해소 방법 |
|----|------|------------|-----------|
| B-01 | `file://` 프로토콜에서 ESM import 차단 (R-04) | T-005, T-008 | `npx serve .` 로컬 서버 사용. README에 실행 방법 명시 필수 |
| B-02 | `tests/rules.test.js` Node.js ESM 실행 환경 미확인 | T-006, T-007, T-009 | `node --version` 으로 Node.js 16+ 확인 후 진행. `package.json` `"type": "module"` 추가 필요할 수 있음 |
| B-03 | T-001 인터페이스 계약 미완료 시 T-004·T-005 병렬 진행 불가 | T-004, T-005 | T-001 완료 후 T-004 착수. T-002는 T-001과 병렬 진행 가능 |

---

## Rollback Sign-Off

| 항목 | 기준 |
|------|------|
| 롤백 단위 | 모듈 단위(game rules / game ui / test checklist) — 각 모듈은 독립 배포 가능 |
| 롤백 트리거 | `node tests/rules.test.js` 에서 FAIL이 1건 이상 발생하고 1라운드 내 수정 불가 시 |
| 롤백 방법 | `git revert` 로 해당 모듈 커밋만 되돌린다. 전체 초기화 금지 |
| 안전 체크 | 롤백 후 `node tests/rules.test.js` 재실행하여 0 FAIL 확인 |
| 보존 대상 | `docs/` 하위 handoff 메모와 `tests/checklist.md`는 롤백 대상에서 제외한다 (의사결정 기록) |

---

## Definition Of Done

- [ ] T-001~T-009 전체 태스크 status = completed
- [ ] `node tests/rules.test.js` → FAIL 0건, PASS 8건
- [ ] TC-01~TC-08이 덱 무결성, 핸드 순위 10종, A-2-3-4-5 스트레이트, 킥커 비교, 동점, 승자 판정, 허용되지 않은 액션, 7장 최강 조합을 모두 검증
- [ ] `tests/checklist.md` 수동 시나리오 8항목 전부 `- [x]` 체크 완료
- [ ] `grep -rn "document\|window" src/rules/` → 결과 0건 (규칙 모듈 DOM 격리)
- [ ] `grep -n "evaluateHand\|compareHands\|determineWinner" src/ui/` → 결과 0건 (UI 모듈 규칙 직접 접근 금지)
- [ ] `npx serve .` 로컬 서버에서 Phase 0→1→2→3→4 전체 흐름 오류 없이 실행
- [ ] 브라우저 콘솔 JS 오류 0건
- [ ] `docs/rules-handoff.md`, `docs/ui-handoff.md`, `docs/qa-handoff.md` 세 handoff 문서 존재
- [ ] `docs/architecture.md` § Modules에 game rules·game ui 모듈 설명 추가 완료
