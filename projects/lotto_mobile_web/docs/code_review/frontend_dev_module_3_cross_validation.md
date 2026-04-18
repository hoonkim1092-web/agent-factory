# frontend_dev_module_3 Cross Validation

## 메타데이터
- task_id: `frontend_dev_module_3_cross_validate`
- reviewer_role: frontend_dev_cross_validator
- reviewed_at: 2026-04-18
- phase: cross_validate
- 문서 언어: 한국어 (OS: `ko-KR`)
- 대상 산출물:
  - `web/js/components/CardList.js`
  - `web/styles/cards.css`
  - `web/index.html`
  - `docs/architecture.md`, `docs/change_history.md`
- 참고 입력:
  - `docs/modules/frontend_dev_module_3_scope.md`
  - `docs/modules/frontend_dev_module_3_scope_review.md`
  - `docs/code_review/frontend_dev_module_3_code_review.md`
  - `docs/modules/frontend_dev_module_2_scope.md`
  - `docs/modules/qa_engineer_module_7_scope.md`
  - `tests/frontend/test_smoke_render.py`

## 판정
- `PASS` (with low-severity 정보)

## 1. 모듈 간 인터페이스 일관성 (입출력 타입, 계약)
- `ACCEPT`: 공개 API `renderCardList(el: HTMLElement, combos: RecommendationCombo[]) => void` 시그니처가 module_2 자리표시자 계약과 동일하다.
  - 근거: `web/js/components/CardList.js:20`, `web/js/app.js:7`, `web/js/app.js:129`, `docs/modules/frontend_dev_module_2_scope.md:86-95`
- `ACCEPT`: 호출자(`app.js`)는 본 모듈 변경에도 수정 불필요. `cardListRoot`(HTMLElement)·`combos`(배열) 두 인자만 흘려보낸다.
  - 근거: `web/js/app.js:120-130`, scope §5 결합 표
- `ACCEPT`: 소비하는 데이터 형(`RecommendationCombo` = numbers[6], score(0..1), odd_even_ratio("a:b"), section_distribution[5])이 backend `RecommendationService.predict()` 응답 contract와 일치한다.
  - 근거: `docs/architecture.md:55-57`, scope §1 인터페이스 정의, `docs/modules/frontend_dev_module_2_scope.md:66-84`
- `ACCEPT`: 비정상 입력은 no-op 또는 부분 안전 분기(`empty-hint` 유지, ball 비숫자 필터, 섹션 패딩/절삭, 점수 클램프)로 모두 방어된다.
  - 근거: `web/js/components/CardList.js:21-32, 109-126, 161-198, 219-240`

## 2. 설계 문서와 구현의 괴리
- `ACCEPT`: scope §1–7 In-Scope 7개 항목(카드 리스트 치환, 번호 공 5단계 색상, 점수 텍스트+게이지, 홀짝 배지, 5칸 히스토그램, 카드 토글, 빈 상태/이상 데이터) 모두 구현에 반영.
  - 근거: `web/js/components/CardList.js:34-240`, `web/styles/cards.css:35-218`
- `ACCEPT`: scope §2 DOM 구조(`<button class="combo-card" aria-expanded aria-controls aria-labelledby>` + `__summary`/`__detail`)가 그대로 조립된다.
  - 근거: `web/js/components/CardList.js:53-89`, scope §2 트리
- `ACCEPT`: scope §3 스타일 자산(신규 `cards.css`, `base → layout → cards` 링크 순서)이 일치하며 `base.css`/`layout.css`는 미수정.
  - 근거: `web/index.html:15-17`, `web/styles/cards.css:1-22`
- `ACCEPT`: scope §4 상호작용 정책(지역 DOM 상태, `aria-expanded`/`hidden`만 사용, store 미접근, 재렌더 시 펼침 초기화 수용)이 코드와 일치.
  - 근거: `web/js/components/CardList.js:80-101`, `web/styles/cards.css:71-153`, scope §4
- `ACCEPT`: scope §리스크 R2 대응(AA 대비 ≥ 4.5:1)이 팔레트 명세에 반영 — 노랑 배경+짙은 갈색 텍스트, 그 외 배경+흰색 텍스트.
  - 근거: `web/styles/cards.css:8-22`
- `ACCEPT`: scope §리스크 R4(신규 CSS 링크 추가가 smoke 회귀 만들지 않음) 검증 — 4건 모두 통과(`pytest tests/frontend -q` 0.02s, 4 passed).
- `ACCEPT`: scope_review BLOCK 2건이 모두 해소됐다.
  - architecture.md §프론트엔드 셸 공개 API 요약·§핵심 구성 요소가 build 결과(실제 카드 시각화)로 갱신됨.
    - 근거: `docs/architecture.md:19-20`, `docs/architecture.md:72-73`
  - change_history.md 2026-04-18T18:20:00 항목에 build 요약·이유·영향 파일·후속 작업이 기록됨.
    - 근거: `docs/change_history.md:19-23`

## 3. 테스트 커버리지 갭 (QA가 놓친 시나리오)
- `ACCEPT`(범위 정합): module_3 의 자동화 회귀선은 `qa_engineer_module_7` smoke 4건이며, 이 스위트의 명시 범위는 “파일/Export/셸 계약”이다. 카드 내부 DOM·인터랙션은 의도적으로 범위 밖.
  - 근거: `tests/frontend/test_smoke_render.py:6-71`, `docs/modules/qa_engineer_module_7_scope.md`
- `INFO`(자동화 갭, BLOCK 아님): 다음 시나리오는 자동화돼 있지 않다. handoff 단계에서 수동 확인 또는 후속 회귀 추가 항목으로 기록 권고.
  - (T1) 펼침/접힘 토글: click·Enter·Space 세 경로의 `aria-expanded` 토글
  - (T2) 번호 공 색상 버킷: 1·11·21·31·41·45 경계값에서 `combo-card__ball--bX` 매핑
  - (T3) score 게이지 클램프: -0.1, 1.5, NaN 입력 시 `aria-valuenow`·width 동작
  - (T4) section_distribution 길이/타입 이상: 4·6 길이, 음수, 비숫자 시 5칸 렌더 보장
  - (T5) 빈 배열·`combos` 비배열·`el` 비-HTMLElement 시 안전 반환
  - 정책 판단: `qa_engineer_module_7` scope 가 smoke 한정이므로 본 모듈 단독 책임 아님. verify(`frontend_dev_module_3_verify_3`) 또는 후속 QA 모듈 백로그로 위임.
- `INFO`: scope §리스크 R1(재렌더 시 펼침 초기화)·R2(대비)·R3(필드 누락 부분 실패)는 verify 단계 수동 확인 항목으로 명시돼 있어, 자동화 부재 자체가 계약 위반은 아니다.
  - 근거: scope §리스크, change_history.md 2026-04-18T18:20:00 후속 작업

## 4. 의존성 그래프 정합성
- `ACCEPT`: 상류(소비)
  - module_2: `web/index.html`(`#card-list-root` 슬롯), `web/js/app.js`(import + 호출), `web/js/components/CardList.js`(자리표시자 시그니처), `state.result.combos` 계약 — 모두 변경 없이 그대로 소비.
  - backend module_1: `RecommendationCombo` 스키마(필드/타입) — 그대로 소비, 추가 가정 없음.
- `ACCEPT`: 하류(제공)
  - module_5(오프라인 폴백): `source === 'offline' | 'cache'` 상태에서도 동일한 `renderCardList` 가 재사용 가능. CardList.js 가 store/네트워크 상태에 의존하지 않으므로 캐시 주입 시 결합 위험 없음.
  - 근거: `web/js/components/CardList.js` 전체에서 `state`, `fetch`, `localStorage`, `OfflineError` 미참조
- `ACCEPT`: 횡단
  - QA module_7 smoke 의 필수 셀렉터/슬롯/링크/Export 가 모두 유지됨(테스트 4건 통과로 확인).
- `ACCEPT`: 비침범 파일 보호 — `state.js`, `api.js`, `app.js`, `base.css`, `layout.css`, `ParamPanel.js`, `OfflineBanner.js` 미수정.

## 5. 문서 업데이트 누락
- `ACCEPT`: `docs/architecture.md`
  - §핵심 구성 요소에 module_3 항목 추가(라인 20).
  - §프론트엔드 셸 공개 API 요약의 `renderCardList` 항목이 실제 시각화 설명으로 갱신(라인 72-73).
  - 마지막 업데이트(라인 7) 타임스탬프 갱신.
- `ACCEPT`: `docs/change_history.md` 2026-04-18T18:20:00 항목에 요약·이유·영향 파일·후속 작업 4필드가 빠짐없이 기록됨.
- `ACCEPT`: `docs/modules/frontend_dev_module_3_scope.md` (산출물 §) 의 build 단계 문서 갱신 의무가 모두 충족됨.
- `INFO`(누락 아님): handoff 메모(`docs/modules/frontend_dev_module_3_handoff.md` 또는 work-items 디렉터리 내 동급 파일)는 아직 없으나, open_todos 의 “조합 카드 시각화 컴포넌트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.” 가 verify 단계 책임이므로 본 cross_validate 의 BLOCK 사유 아님.

## 회귀 점검 결과
- `pytest tests/frontend -q` → 4 passed (0.02s). smoke 계약 회귀 없음.

## 이슈 요약
1. (INFO) 자동화 회귀 갭 5종(T1–T5) — `qa_engineer_module_7` 범위 밖. verify 또는 후속 QA 모듈 백로그로 위임 권고.
2. (LOW, code_review 인계) `<button>` 자손에 `<ul>`/`<ol>` 포함 — HTML5 content model 경고. scope 합의 사항이며 lint 도입 시 재논의.
3. (LOW, code_review 인계) Enter/Space keydown 중복 처리 — 모던 브라우저에서는 `preventDefault` 로 안전. 지원 범위 내 문제 없음.
4. (INFO, code_review 인계) `renderBalls` 길이 6 미강제 — R3 부분 실패 허용 정책과 일치. 후속 모듈에서 콘솔 warn 검토 가능.
5. (INFO) handoff 메모 미작성 — verify 단계 책임. cross_validate 단계의 BLOCK 사유 아님.

## 결론
- 모듈 간 인터페이스(상류 module_2/backend, 하류 module_5, 횡단 QA module_7)가 모두 정렬돼 있다.
- scope_review BLOCK 2건(architecture/change_history 미정렬)은 build 단계에서 모두 해소됐고, 본 단계에서 잔여 위반은 발견되지 않았다.
- 자동화 회귀 갭(T1–T5)은 QA module_7 의 명시 범위 밖이며, verify 단계 수동 점검 또는 후속 QA 백로그로 위임 가능하다.
- code_review WARN 2건/INFO 1건은 모두 scope·교차검증 합의 안의 사항으로, 새 BLOCK 사유 없음.
- 따라서 verify 단계(`frontend_dev_module_3_verify_3`)로의 진행을 권고한다.

## JSON 판정
```json
{
  "verdict": "PASS",
  "issues": [
    {
      "severity": "info",
      "category": "test-coverage",
      "title": "카드 인터랙션·경계값 자동화 회귀 5종 갭",
      "location": "tests/frontend/",
      "impact": "smoke 한정 정책과 일치. 회귀 위험은 수동 verify 로 흡수.",
      "recommendation": "verify(`frontend_dev_module_3_verify_3`) 수동 체크리스트에 T1~T5 추가 또는 후속 QA 모듈 백로그로 위임."
    },
    {
      "severity": "low",
      "category": "design",
      "title": "button 자손에 ul/ol 포함 — HTML5 content model 경고",
      "location": "web/js/components/CardList.js:57-89",
      "impact": "lint/axe 도입 시 경고. 실 동작/접근성 영향 없음.",
      "recommendation": "frontend_dev_module_4/5 통합 시 button → div[role=button] 또는 펼침 제어 외부화 검토."
    },
    {
      "severity": "low",
      "category": "bug",
      "title": "Enter/Space keydown 중복 처리",
      "location": "web/js/components/CardList.js:80-86",
      "impact": "모던 브라우저는 preventDefault 로 안전.",
      "recommendation": "지원 범위 모던 모바일 유지. 의도 주석 보존."
    },
    {
      "severity": "info",
      "category": "edge-case",
      "title": "renderBalls 가 length !== 6 미강제",
      "location": "web/js/components/CardList.js:109-126",
      "impact": "R3 부분 실패 허용 정책과 일치.",
      "recommendation": "후속 모듈에서 dev-only console.warn 추가 검토."
    },
    {
      "severity": "info",
      "category": "documentation",
      "title": "handoff 메모 미작성",
      "location": "docs/modules/",
      "impact": "verify 단계 책임. cross_validate BLOCK 아님.",
      "recommendation": "frontend_dev_module_3_verify_3 에서 handoff 메모를 남긴다."
    }
  ],
  "summary": "frontend_dev_module_3 (CardList 시각화) 의 모듈 간 인터페이스, 설계↔구현, 의존성 그래프, 문서 업데이트가 모두 정렬됐다. scope_review BLOCK 2건은 build 에서 해소됐고 smoke 회귀 4건도 통과한다. 잔여 사항은 자동화 갭 5종(QA 범위 밖)·코드리뷰 인계 LOW 2건·handoff 메모(다음 단계)뿐이라 PASS 판정으로 verify 단계 진행을 권고한다."
}
```
