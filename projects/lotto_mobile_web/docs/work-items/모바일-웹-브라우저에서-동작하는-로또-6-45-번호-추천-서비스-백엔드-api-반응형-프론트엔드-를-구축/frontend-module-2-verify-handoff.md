# 모바일 반응형 추천 웹 UI 검증 및 handoff

## 메타데이터
- task_id: `frontend_dev_module_2_verify_3`
- module_id: `frontend_dev_module_2`
- owner_role: `frontend_dev`
- phase: `verify`
- 작성 시각: `2026-04-18T18:05:00+09:00`
- 문서 언어: 한국어 (OS: `ko-KR`)

## 검증 결과 요약
- 판정: **조건부 통과(WARN 포함)**
- 근거:
  - scope 문서 §파일·디렉터리 레이아웃의 9개 산출물이 모두 존재한다.
  - scope 문서 §컴포넌트 공개 API 표의 6개 export가 모두 노출되고, `mountApp`도 추가 export되어 `module_3/4/5` 및 QA가 바로 소비 가능하다.
  - 연관 smoke 테스트(`tests/frontend/test_smoke_render.py`) 4건 모두 통과 — 정적 자산, HTML 셸 계약, JS export 계약이 그대로 일치함을 확인했다.
  - 단, 실제 브라우저(iPhone SE 360px / Pixel 412px) 수동 렌더 확인은 본 검증 세션에서 실행하지 못했다(웹 서버 기동·뷰포트 브라우저 없음).

## 실행한 확인 작업
- 산출물 존재 확인:
  - `web/index.html`, `web/styles/base.css`, `web/styles/layout.css`
  - `web/js/app.js`, `web/js/state.js`, `web/js/api.js`
  - `web/js/components/CardList.js`, `ParamPanel.js`, `OfflineBanner.js`
- 계약 정합 확인:
  - `index.html` — `<meta viewport>`, `theme-color`, 3단(header/main/footer) 골격, `data-status`·`data-slot`·`data-testid` 선언이 scope와 일치.
  - `state.js` — `createStore`, `initialState`(`n=5`, `draws=500`, `offline=false`) 노출. 부분 패치 + `params` 얕은 병합 + 무변경 스킵 동작이 주석으로 설계 의도와 일치.
  - `api.js` — `fetchRecommendation(params, options)` + `OfflineError` + 추가로 `ApiError` 노출. 네트워크 실패/타임아웃/5xx를 `OfflineError`로, 4xx를 `ApiError`로 승격.
  - `app.js` — `mountApp({ root?, fetcher? })` 노출. `idle → loading → (success|error|offline)` 상태 전이를 scope §상태 전이 다이어그램 그대로 구현.
  - 자리표시자 3종 — scope §3의 시그니처(`(HTMLElement, ...)` 반환형 `void`) 유지.
- 자동화 테스트: `pytest tests/frontend -q` → `4 passed in 0.02s`.

## 잔여 리스크
- (R1) 모바일 실기기 수동 렌더 확인 미수행 — scope §구현 순서 9가 명시한 `python -m http.server` 기반 iPhone SE/Pixel 뷰포트 점검을 수동으로 돌리지 못했다. 레이아웃 깨짐/가로 스크롤 가능성은 기능 구현이 아닌 검증 절차 측면에서 여전히 열려 있다.
- (R2) 백엔드 응답의 확장 메타 필드를 프런트 상태에서 관찰·활용하지 않는다. `server`가 내려주는 `status`, `latest_draw_no`, `latest_draw_date`는 `state.result`에 그대로 저장되지만, `app.js` 렌더 경로에서 사용되지 않아 `source=cache` 시나리오를 UI로 구분하기 어렵다. `module_5`에서 `source`/`status` 판별 후 `OfflineBanner`/힌트 문구를 분기해야 한다.
- (R3) `empty-hint` 초기화 책임 분산. `applyStateToDom`은 `status === 'idle'`일 때만 `cardListRoot`를 비우고 힌트를 재삽입한다. `loading → error` 경로 직후 `result`가 비어 있을 때 힌트가 재삽입되지 않아 빈 패널이 그대로 노출될 수 있다. `module_3` build에서 실제 카드 컴포넌트가 자체 빈 상태를 갖추면 자연 해소되지만, 그 전까지는 WARN.
- (R4) `api.js`의 `composeSignal`은 구형 Safari에서 `AbortController`가 없을 때 외부 `signal`만 통과시킨다. 타임아웃 fallback이 사라지는 이 경로는 iOS Safari 15+ 기준에서는 문제가 없지만, 14 이하로 타깃이 내려가면 재검토 필요.
- (R5) `renderOfflineBanner`는 `status === 'offline'` 단일 조건만 본다. `source === 'cache'`로 성공이 내려왔을 때 사용자에게 “캐시에서 제공”임을 고지할 UX 요소가 비어 있다 — `module_5` 범위에서 해결 예정이지만 인계 시점에 명시해 둔다.

## 후속 작업(다음 작업자 handoff)
- 우선순위 1 (module_3 카드 시각화 담당):
  - `renderCardList(el, combos)` 시그니처를 유지하면서 점수·홀짝 비율·구간 분포 UI를 치환한다.
  - 빈 결과 처리(`combos.length === 0`)를 카드 컴포넌트 내부에서 책임지면 상단 R3 리스크가 자연 해소된다.
  - 신규 CSS는 `web/styles/cards.css`로 분리하고 `index.html`에 `<link>` 1줄만 추가해 셸 CSS 격리를 깨지 않는다.
- 우선순위 2 (module_4 슬라이더 담당):
  - `renderParamPanel(el, store)` 시그니처 유지. 슬라이더 입력 → `store.setState({ params: { n|draws: value } })` 경로만 사용. `initialState.params` 구조는 변경하지 않는다.
  - 터치 타깃 44×44 최소치와 `prefers-reduced-motion`은 `base.css` 토큰을 재사용한다.
- 우선순위 3 (module_5 오프라인 폴백 담당):
  - `api.js`가 던지는 `OfflineError`를 `mountApp`보다 한 층 위에서 가로채도록 재설계하거나, `app.js`의 catch 분기를 커스터마이즈할 수 있는 훅을 열어 달라.
  - `localStorage` 캐시 키/TTL 설계는 본 scope 문서 §범위 밖 항목이며, module_5 scope 단계에서 결정.
  - `source === 'cache'` 성공 응답에 대한 배너 문구는 `renderOfflineBanner` 서명 확장 또는 별도 슬롯 추가로 해결.
- 우선순위 4 (QA module_7 후속):
  - `qa-frontend-smoke-verify-handoff.md`에 이미 기록된 상태 전이/모바일 레이아웃 smoke 보강과 fixture 계약 정렬을 본 셸 구현 위에서 진행한다. `mountApp({ root, fetcher })` 시그니처가 테스트 가능성을 위해 `fetcher` 주입을 열어두었음을 활용한다.
- 우선순위 5 (잔여 수동 검증):
  - `python -m http.server`로 `web/`를 띄우고 실제 iPhone SE/Pixel 뷰포트(360–430 CSS px)에서 가로 스크롤 발생 여부, 터치 타깃, 다크 모드 훅(`prefers-color-scheme: dark`)을 확인한다. 결과는 `docs/change_history.md`에 보조 항목으로 기록한다.

## 참고 파일
- `docs/modules/frontend_dev_module_2_scope.md`
- `docs/architecture.md` §프론트엔드 셸 공개 API 요약 (frontend_dev_module_2 / build)
- `web/index.html`, `web/styles/{base,layout}.css`, `web/js/{app,state,api}.js`, `web/js/components/*.js`
- `tests/frontend/test_smoke_render.py`, `tests/frontend/conftest.py`, `tests/frontend/fixtures/recommendation_success.json`
- `runs/run_1776443747_frontend_dev_code_reviewer_33f548/` (code review)
- `runs/run_1776443888_frontend_dev_cross_validator_ffe817/` (cross validate)
