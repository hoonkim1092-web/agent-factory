# 아키텍처

이 문서는 현재 아키텍처와 워크플로를 설명하는 살아 있는 기준 문서다.
설계, 워크플로, 인터페이스, 데이터 흐름, 구현 전략이 바뀌면 같은 작업 안에서 갱신한다.

## 메타데이터
- 마지막 업데이트: 2026-04-18T20:15:00
- 상태: active
- 문서 언어: 한국어 (OS: `ko-KR`)

## 현재 설계
- 요약:
  - 서비스는 FastAPI 기반 `GET /api/recommend` 백엔드와 Vanilla JS 기반 모바일 반응형 SPA 셸로 구성한다.
  - 프론트엔드 셸(`frontend_dev_module_2`)은 상태/스타일/API 레이어만 담당하고, 카드/슬라이더/오프라인 처리는 하위 모듈(`module_3/4/5`)이 공개 API를 통해 치환한다.
  - QA 범위에서 API 단위 테스트 스위트는 FastAPI 앱 내부 호출 방식으로 계약 회귀를 검출하며, 프론트엔드 smoke 테스트(`qa_engineer_module_7`)는 `web/index.html` 셸 계약, 핵심 자산 존재성, JS 모듈 export 계약을 검증한다.
- 핵심 구성 요소:
  - 백엔드 API(`backend_dev_module_1`): `server/` 하위에 FastAPI 앱을 배치한다(`app.py`, `schemas.py`, `dependencies.py`, `errors.py`, `bootstrap.py`, `services/recommendation.py`, `services/draw_cache.py`). 엔드포인트는 `GET /api/health`, `GET /api/recommend`, `GET /api/draws/latest` 세 가지이며, 질의 파라미터 `n`, `draws`, `offline`를 받아 추천 조합 JSON을 반환한다.
  - 재사용 모듈: `projects/lotto_predictor_v2/src/lotto`의 `analytics.patterns.analyze_patterns`, `recommender.recommend_combinations`, `cache.store.LottoCacheStore`. `server/bootstrap.py`가 `sys.path`를 주입해 신규 구현 없이 import로 재사용한다.
  - 프론트엔드 셸(`frontend_dev_module_2`): `web/index.html` + `web/styles/{base,layout}.css` + `web/js/{app,state,api}.js` 구조의 모바일-퍼스트 SPA. ES2020 순정 JavaScript 모듈만 사용하고, 부트스트랩 시 `mountApp()`이 `createStore(initialState)`로 단일 스토어를 만들어 DOM에 바인딩한다. 헤더/메인/푸터 3단 수직 구조에 `data-status` 속성으로 상태 전이를 공개한다. `web/js/components/{CardList,ParamPanel,OfflineBanner}.js`는 본 모듈에서 자리표시자로만 구현되고, 각 하위 모듈(`module_3/4/5`)이 공개 API를 치환한다.
  - 카드 시각화(`frontend_dev_module_3`): `web/js/components/CardList.js` + 전용 스타일 `web/styles/cards.css` (번호 공 팔레트, 게이지, 히스토그램). build 단계에서 `renderCardList` 자리표시자를 실제 카드 UI(요약/상세 접기·펼치기)로 치환했다.
  - 파라미터 슬라이더(`frontend_dev_module_4`): `web/js/components/ParamPanel.js` + 전용 스타일 `web/styles/sliders.css`. `n`(1..10, step 1) / `draws`(100..500, step 50) 두 슬라이더를 1회 마운트하고, 이후에는 `value`·`aria-valuetext`·`<output>`·`disabled` 속성만 동기화한다. `state.status === "loading"` 동안 슬라이더를 비활성화하며, `params.offline` 키는 본 모듈이 건드리지 않는다.
  - 오프라인 폴백(`frontend_dev_module_5`): `web/js/components/OfflineBanner.js` + `localStorage` 캐시. `app.js` 가 마지막 성공 추천 응답을 `lotto:last-success-recommendation` 키로 저장하고, `OfflineError` 발생 시 TTL 24시간 이내의 캐시를 읽어 `status='offline'` + stale 배너로 복구한다. 캐시가 없거나 손상되었거나 TTL을 초과하면 `result` 를 비우고 오프라인 안내만 남긴다. 백엔드 `source` 값은 `cache` 와 `offline` 둘 다 stale 로 취급한다.
  - QA API 단위 테스트 스위트: `tests/api/` 아래에서 `TestClient`와 stubbed predictor를 사용해 엔드포인트 계약을 검증한다.
  - QA 프론트엔드 smoke 테스트(`qa_engineer_module_7`): `tests/frontend/` 아래에서 정적 HTML 파싱과 파일/export 존재성 검증으로 프론트엔드 셸 계약을 점검한다.
- 데이터 흐름:
  - 프론트엔드 경로: `ParamPanel` 입력 → `state.store` → `api.fetchRecommendation` → `GET /api/recommend` → 응답을 `state`와 `localStorage` 캐시에 저장 → `CardList` 렌더링. 네트워크 실패 시 `OfflineError` → `app.js` 가 캐시 유효성(TTL 24시간, `version=1`, `params/result` 최소 shape 검증)을 확인 → 유효하면 `status='offline'` + cached `result` hydrate + `OfflineBanner` stale 표시, 무효하면 `result=null` 로 정리하고 오프라인 오류 안내만 유지.
  - 백엔드 경로: FastAPI DTO(`RecommendationQuery`)가 `n ∈ [1,10]`, `draws ∈ [100,500]`, `offline ∈ {true,false}`를 검증 → `services/recommendation.py`가 `LottoCacheStore`로 회차를 로드 → `analyze_patterns` → `recommend_combinations` → `RecommendationResponse` 반환. 온라인 실패 또는 `offline=true`면 캐시 폴백 경로로 전환해 `source=cache`, `status=degraded-success`로 표시한다.
  - 테스트 경로: API 테스트 코드는 `app_client` fixture로 FastAPI 앱(`create_app()`)을 호출하고, `predictor_stub` 또는 monkeypatch 지점으로 예측 의존성을 대체한 뒤 응답 JSON(`generated_at`, `source`, `draws_used`, `combos`, `combos[*]`)을 검증한다.
  - 프론트 smoke 테스트 경로: `tests/frontend/test_smoke_render.py`가 `web/index.html`, `web/styles/{base,layout}.css`, `web/js/{app,state,api}.js`, `web/js/components/*.js`를 읽어 셸 구조와 공개 API 이름을 확인하고, 대표 성공 stub fixture 를 기준으로 최소 렌더 상태 계약을 검증한다.
- 제약 사항:
  - 프론트엔드는 프레임워크 미도입(Vanilla JS, ES2020)으로 번들러 없이 정적 파일 서빙. 모바일 퍼스트(360–430 CSS px 기준), 터치 타깃 최소 44×44 px.
  - 백엔드는 상태 비저장 JSON API, Pydantic v2, Python 3.11. 기존 `lotto_predictor_v2` 분석 모듈을 **신규 구현 없이 import**로 재사용한다.
  - 오프라인 캐시에는 stale 데이터 표시 의무(`source=offline` 또는 `source=cache`).
  - 프론트 캐시는 `localStorage` 단일 레코드 1건만 유지하며, TTL은 24시간으로 고정한다.
  - 백엔드 공통 에러 스키마: `{error:{code,message,details}}`. 코드 `invalid_parameter`(422), `data_unavailable`(503), `internal_error`(500).
  - QA API 단위 테스트는 외부 네트워크나 실제 추첨 데이터 수집에 의존하지 않는다.
  - API 검증 범위는 계약, 입력 검증, 오류 응답까지로 제한하며 브라우저 렌더링은 별도 smoke 테스트가 담당한다.
  - 프론트 smoke 테스트는 브라우저 자동화나 픽셀 비교를 수행하지 않고, 정적 셸 계약과 최소 렌더 가능성 확인에 집중한다.
  - 파라미터 경계는 `n=1..10`, `draws=100..500`을 기준으로 고정한다.
- 열린 질문:
  - 백엔드 구현에서 내부 예측 엔진 주입 지점은 `server/dependencies.py`의 `get_recommendation_service()`를 FastAPI `app.dependency_overrides`로 치환하는 방식으로 고정한다(build 단계에서 최종 확정).
  - `draws=500` 분석 응답이 수초 지연될 경우 모바일 UX 처리 기준(로딩 스켈레톤, 취소 UI 등)을 후속 모듈에서 결정한다.
  - 캐시가 전혀 없는 신규 배포 환경에서 초기 캐시 부트스트랩 방법(현재: CLI 수동 1회 실행) — 자동 부트스트랩 도입 여부는 build 단계에서 재검토.

## 모듈 범위 문서
- `docs/plans/2026-04-18-backend-api-scope.md` — 로또 추천 REST API 서버 범위·인터페이스·구현 순서
- `docs/modules/frontend_dev_module_2_scope.md` — 모바일 반응형 추천 웹 UI 범위·인터페이스·구현 순서
- `docs/modules/frontend_dev_module_3_scope.md` — 조합 카드 시각화 컴포넌트 범위·인터페이스·구현 순서
- `docs/modules/frontend_dev_module_4_scope.md` — 파라미터 슬라이더 컨트롤 범위·인터페이스·구현 순서
- `docs/modules/frontend_dev_module_5_scope.md` — 오프라인 캐시 폴백 모듈 범위·인터페이스·구현 순서
- `docs/modules/qa_engineer_module_7_scope.md` — 프론트엔드 렌더링 smoke 테스트 범위·인터페이스·구현 순서

## 백엔드 API 공개 인터페이스 요약 (backend_dev_module_1 / build)
- 엔트리 포인트: `server.app:create_app()` 팩토리와 모듈 레벨 `server.app:app` 인스턴스(테스트/uvicorn 모두 지원).
- 의존성 주입 지점(테스트 치환용)
  - `server.dependencies:get_recommendation_service` — 기본 `RecommendationService` 싱글톤. FastAPI `app.dependency_overrides`로 스텁 교체.
  - `server.dependencies:get_draw_cache_service` — `/api/draws/latest`용 캐시 조회 서비스.
- 서비스 계약
  - `RecommendationService.predict(n, draws, offline) -> dict` — dict는 `generated_at`, `source`, `status`, `draws_used`, `latest_draw_no`, `latest_draw_date`, `combos`를 포함한다.
  - `DrawCacheService.get_latest() -> dict | None` — 비어 있으면 `None`을 돌려주며 엔드포인트가 503을 반환한다.
- 에러 모델: `server.errors.ApiError` 계열 예외를 `install_error_handlers()`가 공통 envelope로 직렬화한다. `DataUnavailableError`는 503/`data_unavailable`로 매핑된다.
- 미들웨어: `RequestIdMiddleware`가 모든 응답에 `X-Request-ID`를 부착한다. CORS 허용 출처는 환경 변수 `LOTTO_CORS_ORIGINS`(기본 `*`)로 조정한다.
- 정적 자산 마운트: 환경 변수 `LOTTO_STATIC_DIR` 우선, 없으면 `web/` 디렉터리를 `/static`으로 자동 마운트한다.
- 테스트 주입 규약: 워크스페이스 루트 `conftest.py`가 `QA_API_APP_TARGET=server.app:app`, `QA_API_PREDICTOR_DEPENDENCY=server.dependencies:get_recommendation_service`를 미리 세팅해 `tests/api/conftest.py`의 `app_client` fixture가 그대로 동작한다.

## 프론트엔드 셸 공개 API 요약 (frontend_dev_module_2 / build)
- `web/js/state.js`
  - `createStore(initial?)` → `{ getState, setState, subscribe }`. `setState`는 부분 패치(함수 또는 객체)를 허용하고, `params` 키만 한 단계 더 얕게 병합해 하위 모듈이 슬라이더 값만 바꿔도 안전하게 쓸 수 있다. 상태 변경이 없으면 구독자를 깨우지 않는다.
  - `initialState` — `{ params: { n: 5, draws: 500, offline: false }, result: null, status: 'idle', lastError: null }`.
- `web/js/api.js`
  - `fetchRecommendation(params, options?)` — `GET /api/recommend?n&draws&offline`. 기본 타임아웃 8s, 외부 `AbortSignal`과 결합.
  - `OfflineError` — 네트워크 실패, 타임아웃, 5xx 응답에 대한 단일 승격 타입. `module_5`가 `instanceof`로 폴백 진입을 결정한다.
  - `ApiError` — 4xx 응답을 `{ code, message, status, details }`로 감싼 타입. 사용자 메시지 노출에 사용.
- `web/js/components/*.js`
  - `renderCardList(el, combos)` — `module_3` build에서 실제 카드 시각화로 치환. 조합 1개를 `<button class="combo-card" aria-expanded>` 로 조립하고 요약(번호 공 6개 + 점수 텍스트)과 상세(`role="meter"` 점수 게이지 + 홀짝 배지 + 5칸 구간 히스토그램)를 접기/펼치기 토글로 분리한다. 번호 공은 1..45 범위를 5단계 색상 버킷(`b1..b5`)으로 매핑하고 오름차순 정렬해 렌더하며, 비정상 입력(배열 아님/빈 배열/점수 범위 밖/구간 길이 불일치)은 안전 분기로 방어한다. 전용 스타일은 `web/styles/cards.css` 로 분리하며 `web/index.html` 은 `base → layout → cards` 순으로 링크한다.
  - `renderParamPanel(el, store)` — `<input type="range">` 두 개(`n` 1..10/step 1, `draws` 100..500/step 50)와 `<output>` 표시값을 렌더한다. 사용자 입력은 `input`/`change` 이벤트에서 `store.setState({ params: { [name]: value } })` 로 부분 반영하고, 구독 콜백은 동일 값일 때 DOM을 건드리지 않아 드래그 중 포커스 손실을 막는다. 전용 스타일은 `web/styles/sliders.css`, 셸 링크 순서는 `base → layout → cards → sliders` 이다. `params.offline` 키는 건드리지 않는다.
  - `renderOfflineBanner(el, status)` — `status === 'offline'` 또는 hydrated `result.source ∈ {'cache','offline'}` 인 경우 stale 배너를 렌더한다. 캐시 저장/복구는 `app.js` 가 담당하고, 배너는 `data-*` 로 주입된 `cached_at`, `latest_draw_no`, `latest_draw_date`, `source`, `hasResult`, `message` 메타를 읽어 사용자 안내 문구와 stale 메타를 표시한다. 공개 시그니처는 그대로 유지한다.
- `web/js/app.js`
  - `mountApp({ root?, fetcher? })` — 루트 `#app`에 마운트하고 추천 버튼 클릭 → 상태 전이 `idle → loading → (success | error | offline)`를 수행한다. 성공 응답은 즉시 캐시에 저장하고, `OfflineError` 는 캐시 복구를 먼저 시도한다. DOM 갱신은 `root.dataset.status` + `#session-status` + 자리표시자 컴포넌트 3종을 통해 이뤄지며, 오프라인 배너용 `data-*` 메타도 같은 경로에서 동기화한다. 모듈 스크립트 자동 부트스트랩은 `window` 환경에서만 실행되며, 테스트/외부 소비 시에는 수동 `mountApp()` 호출로 대체할 수 있다.

## 문서 규칙
- 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다.
- 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다.
- 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다.
- 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
