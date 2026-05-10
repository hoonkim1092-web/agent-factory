# Implementation Tasks

## Metadata

- work_item: implement-a-browser-poker-game
- source_design: implementation-design.md
- status: draft
- last_updated: 2026-05-08T15:07:08

## Preconditions

- 범위와 계약 정의
- 기능 슬라이스 구현
- 통합과 핸드오프
- 검증과 마감

## Task Evidence

- Local reference: docs/architecture.md -> game state is split by module.
- Web reference: Poker rules -> verify state transitions and winner evaluation.
- NotebookLM: Prefer isolated game-rule modules and explicit verification checkpoints.

## Task List

- [ ] Frontend Dev: game ui 범위와 인터페이스를 정의한다.
  - task_id: frontend_dev_module_1_scope_1
  - owner_role: frontend_dev
  - phase: scope
  - acceptance: `game/index.html`, `game/js/ui.js` 파일 목록과 각 함수 시그니처가 문서화된다.; 카드 렌더링·베팅 컨트롤·게임 보드 레이아웃 세 영역의 인터페이스가 명시된다.; `game/docs/ui-interface-spec.md`에 의존성(poker-rules.js 이벤트 버스)과 산출물 파일 목록이 기재된다.
  - e2e_command: test -f game/docs/ui-interface-spec.md && grep -q "ui.js" game/docs/ui-interface-spec.md && echo PASS || echo FAIL

- [ ] Frontend Dev: game rules 범위와 인터페이스를 정의한다.
  - task_id: frontend_dev_module_2_scope_1
  - owner_role: frontend_dev
  - phase: scope
  - acceptance: `game/js/poker-rules.js`가 노출할 public API(`evaluateHand`, `compareHands`, `determineWinner`)가 JSDoc 형태로 정의된다.; pre-flop → flop → turn → river → showdown 상태 전이 다이어그램이 `game/docs/rules-spec.md`에 포함된다.; 의존 없는 순수 함수 모듈임이 명시된다.
  - e2e_command: test -f game/docs/rules-spec.md && grep -q "evaluateHand" game/docs/rules-spec.md && echo PASS || echo FAIL

- [ ] QA Engineer: test checklist 범위와 인터페이스를 정의한다.
  - task_id: qa_engineer_module_3_scope_1
  - owner_role: qa_engineer
  - phase: scope
  - acceptance: `game/tests/test-checklist.md`에 룰 평가(핸드 랭킹·키커 비교·동점 처리), 상태 전이, UI 렌더링 3개 카테고리가 체크리스트 항목으로 열거된다.; 각 항목에 입력·기대 출력·판정 기준이 명시된다.; 항목 수 ≥ 15.
  - e2e_command: test -f game/tests/test-checklist.md && awk '/^- \[/{n++} END{print (n>=15)?"PASS":"FAIL (항목 "n"개)"}' game/tests/test-checklist.md

- [ ] Frontend Dev: game ui 기능을 구현한다.
  - task_id: frontend_dev_module_1_build_2
  - owner_role: frontend_dev
  - phase: build
  - depends_on: frontend_dev_module_1_scope_1
  - acceptance: `game/index.html`이 브라우저에서 열리고 카드 52장 덱이 시각적으로 렌더링된다.; 베팅 컨트롤(check/call/raise/fold) 버튼이 DOM에 존재하고 클릭 이벤트가 `poker-rules.js` 이벤트로 연결된다.; `game/css/style.css`가 로드되어 카드 레이아웃이 정렬된다.
  - e2e_command: test -f game/index.html && grep -q "poker-rules.js" game/index.html && grep -q "id=\"bet-controls\"" game/index.html && echo PASS || echo FAIL

- [ ] Frontend Dev: game rules 기능을 구현한다.
  - task_id: frontend_dev_module_2_build_2
  - owner_role: frontend_dev
  - phase: build
  - depends_on: frontend_dev_module_2_scope_1
  - acceptance: `game/js/poker-rules.js`에서 `evaluateHand(['Ah','Kh','Qh','Jh','Th'])` 호출 시 `{rank: "royal_flush", score: 9}` 형태 객체를 반환한다.; `compareHands` 호출로 동점·키커 비교가 정확히 처리된다.; 파일이 `require`/`import` 없이 브라우저 `<script>` 태그로 로드 가능한 vanilla JS 모듈이다.
  - e2e_command: node -e "const r = require('./game/js/poker-rules.js'); const h = r.evaluateHand(['Ah','Kh','Qh','Jh','Th']); console.log(h.rank === 'royal_flush' ? 'PASS' : 'FAIL: ' + JSON.stringify(h))"

- [ ] QA Engineer: test checklist 기능을 구현한다.
  - task_id: qa_engineer_module_3_build_2
  - owner_role: qa_engineer
  - phase: build
  - depends_on: qa_engineer_module_3_scope_1
  - acceptance: `game/tests/test-checklist.md`의 모든 체크리스트 항목에 실제 실행 결과(`PASS`/`FAIL`/`SKIP`)가 기재된다.; 룰 평가 카테고리 항목 전부 PASS.; UI 렌더링 카테고리 ≥ 80% PASS.; FAIL 항목은 원인과 후속 작업이 기재된다.
  - e2e_command: grep -c "\- \[x\]" game/tests/test-checklist.md | awk '{print ($1>=12)?"PASS":"FAIL (완료 항목 "$1"개)"}'

- [ ] Frontend Dev: game ui 결과를 검증하고 handoff를 남긴다.
  - task_id: frontend_dev_module_1_verify_3
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: frontend_dev_module_1_build_2
  - acceptance: `game/docs/verification-report-ui.md`에 e2e_command 실행 결과(exit_code, stdout)가 기재된다.; 카드 렌더링·베팅 컨트롤·레이아웃 3항목이 각각 PASS/WARN/BLOCK 판정을 받는다.; 잔여 리스크(반응형 레이아웃 미지원 등)와 후속 작업이 명시된다.
  - e2e_command: test -f game/docs/verification-report-ui.md && grep -q "verdict:" game/docs/verification-report-ui.md && echo PASS || echo FAIL

- [ ] Frontend Dev: game rules 결과를 검증하고 handoff를 남긴다.
  - task_id: frontend_dev_module_2_verify_3
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: frontend_dev_module_2_build_2
  - acceptance: `game/docs/verification-report-rules.md`에 핸드 랭킹 9종(high-card ~ royal-flush), 키커 비교, 동점 처리 각 케이스의 실행 결과가 기재된다.; node 실행 exit_code=0 및 모든 케이스 PASS.; 룰 평가 버그 리스크 완화 여부가 판정된다.
  - e2e_command: test -f game/docs/verification-report-rules.md && grep -q "verdict: PASS" game/docs/verification-report-rules.md && echo PASS || echo WARN

- [ ] QA Engineer: test checklist 결과를 검증하고 handoff를 남긴다.
  - task_id: qa_engineer_module_3_verify_3
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: qa_engineer_module_3_build_2
  - acceptance: `game/docs/verification-report-qa.md`에 체크리스트 전체 항목 집계(PASS/FAIL/SKIP 건수)가 기재된다.; 총 PASS율 ≥ 80%.; FAIL 항목별 원인 분석과 수정 방향이 기재된다.; verdict 필드가 PASS/WARN/BLOCK 중 하나로 확정된다.
  - e2e_command: test -f game/docs/verification-report-qa.md && grep -q "verdict:" game/docs/verification-report-qa.md && echo PASS || echo FAIL

## Blockers

- none

## Rollback Sign-Off

- Commit after each module-level implementation milestone

## Definition Of Done

- All task checkboxes are complete
- verification-report.md 작성 완료 (`templates/verify-handoff.md.tpl` 참고)
  - `e2e_command:` 필드에 실행 명령어 기재
  - `- verdict:` 필드에 PASS/WARN/BLOCK 기재
