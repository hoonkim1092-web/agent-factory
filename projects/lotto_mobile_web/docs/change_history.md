# 변경 이력

설계, 아키텍처, 워크플로, 구현 전략이 바뀔 때마다 항목을 하나씩 추가한다.

## 항목 템플릿
### YYYY-MM-DD HH:MM:SS
- 요약:
- 이유:
- 영향 파일:
- 후속 작업:

## 이력
### 2026-04-18T20:15:00
- 요약: 오프라인 캐시 폴백 모듈(`frontend_dev_module_5`) build 단계를 완료했다. `web/js/app.js` 에 마지막 성공 응답의 `localStorage` 저장, `OfflineError` 발생 시 TTL 24시간·버전·최소 shape 검증을 거친 캐시 복구, 캐시 부재 시 `result=null` 정리까지 구현했다. `web/js/components/OfflineBanner.js` 는 `renderOfflineBanner(el, status)` 공개 시그니처를 유지하면서 stale 메시지와 저장 시각/기준 회차 메타를 실제 DOM으로 렌더하고, `source=cache|offline` 을 모두 stale 로 처리한다. `tests/frontend/test_offline_cache_contract.py` 를 추가해 성공 저장, 오프라인 복구, 배너 표시 계약을 Node 기반 회귀 테스트로 고정했다.
- 이유: 셸 수준 placeholder 로 남아 있던 오프라인 경로를 실제 저장소 기반 폴백으로 치환하고, 백엔드 `source` 드리프트를 흡수하는 프론트 계약을 코드와 테스트에 동시에 반영하기 위해.
- 영향 파일: `web/js/app.js`, `web/js/components/OfflineBanner.js`, `web/styles/layout.css`, `tests/frontend/test_offline_cache_contract.py`, `tests/frontend/test_smoke_render.py`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_5_verify_3` 또는 QA 단계에서 실제 브라우저에서 `localStorage` 차단 환경, 만료 캐시, 신규 세션 오프라인 진입을 수동 점검하고 handoff 메모에 반영한다.

### 2026-04-18T19:45:00
- 요약: 오프라인 캐시 폴백 모듈(`frontend_dev_module_5`)의 범위, 캐시 레코드 계약, 공개 인터페이스, 구현 순서를 고정했다. `renderOfflineBanner(el, status)` 공개 API 시그니처는 유지하고, 실제 캐시 읽기/쓰기는 `app.js` 가 담당하도록 경계를 분리했다. `localStorage` 키는 `lotto:last-success-recommendation`, 레코드 shape 는 `version`, `cached_at`, `params`, `result`, TTL 은 24시간으로 고정했다. 백엔드 `source` 계약 드리프트가 해소되기 전까지 프론트는 `source=cache|offline` 둘 다 stale 데이터로 처리한다.
- 이유: build 단계에서 오프라인 캐시 책임이 `OfflineBanner.js`, `app.js`, `api.js` 사이에 흩어지지 않게 모듈 경계를 먼저 고정하고, 백엔드 handoff 에서 보고된 `source/status` 드리프트를 프론트가 방어적으로 흡수할 수 있도록 계약을 명시하기 위해.
- 영향 파일: `docs/plans/2026-04-18-offline-cache-fallback.md`, `docs/modules/frontend_dev_module_5_scope.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_5_build_2` 에서 scope 문서 §구현 순서 1–7 을 그대로 실행한다. 메일박스 도구가 제공되는 실행 환경에서는 build 전 `review_request` 를 전송해 교차검증을 요청해야 한다.

### 2026-04-18T18:50:00
- 요약: 파라미터 슬라이더 컨트롤(`frontend_dev_module_4`)의 범위, 공개 인터페이스, 구현 순서를 고정했다. `renderParamPanel(el, store)` 공개 API 시그니처는 그대로 유지하고 내부 구현만 두 개의 `<input type="range">`(`n` 1..10/step 1, `draws` 100..500/step 50) + `<output>` 표시값 + `aria-valuetext` 단위 안내로 치환한다. 슬라이더 min/max/step 은 `backend_dev_module_1` 의 검증 범위와 1:1 정렬한다. 1회 마운트 + 속성 갱신 정책으로 드래그 중 DOM 재생성을 금지하고, `setState` 의 `params` 부분 패치 + `shallowEqual` 가드 + `syncFromState` 의 값 비교로 양방향 루프를 차단한다. `params.offline` 키는 본 모듈이 건드리지 않는다(→ `module_5`). 전용 스타일은 신규 `web/styles/sliders.css` 로 격리하고 `web/index.html` 에 링크 1줄을 `base → layout → cards → sliders` 순으로 추가한다.
- 이유: build 단계에서 DOM/접근성/스토어 결합 정책을 재해석하지 않도록 계약을 먼저 고정하고, `qa_engineer_module_7` smoke 계약·`frontend_dev_module_5` 오프라인 모듈과의 결합 지점(`params.offline` 비침범)을 명시하기 위해.
- 영향 파일: `docs/modules/frontend_dev_module_4_scope.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_4_build_2` 에서 scope 문서 §구현 순서 1–7 을 그대로 실행하고, `docs/architecture.md` 의 "프론트엔드 셸 공개 API 요약 > `renderParamPanel`" 항목은 build 단계에서 실제 슬라이더 설명으로 갱신한다.

### 2026-04-18T19:20:00
- 요약: 파라미터 슬라이더 컨트롤(`frontend_dev_module_4`) build 단계를 문서와 테스트 기준으로 확정했다. `renderParamPanel(el, store)` 는 `n`/`draws` 슬라이더를 `<input type="range">` 로 마운트하고, `input`/`change` 이벤트에서 `store.setState({ params: { [name]: value } })` 를 호출한다. 구독 콜백은 `value`, `aria-valuetext`, `<output>`, `disabled` 만 갱신해 드래그 중 DOM 재생성을 피하고, `loading` 상태에서 슬라이더를 비활성화한다.
- 이유: 구현된 슬라이더 동작을 build 기준 아키텍처 설명과 회귀 테스트에 반영해, verify 단계가 placeholder 기준 문서가 아니라 실제 동작 기준으로 검증할 수 있게 하기 위해.
- 영향 파일: `docs/plans/2026-04-18-parameter-slider-control.md`, `tests/frontend/test_param_panel_contract.py`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_4_verify_3` 에서 프론트 테스트 5건 통과를 재확인하고, 수동 뷰포트 점검(iPhone SE/Pixel) 결과를 handoff 문서에 남긴다.

### 2026-04-18T18:35:00
- 요약: `backend_dev_module_1`(로또 추천 REST API) verify 단계를 완료하고 handoff 메모를 `docs/modules/backend_dev_module_1_handoff.md`로 남겼다. 3단계 검증(`py_compile` OK → `pytest tests/api -v` 10/10 통과 → `server.app` import + 라우트 점검 OK)과 보조 런타임 스모크(헬스 200, OpenAPI 200, 스텁 DI 기반 `/api/draws/latest` 503, 422 envelope 형상)를 캡처했다. 의존성(`requirements.txt` ↔ scope §6.1)도 1:1 일치함을 재확인했다. 잔여 리스크는 cross-validator C1/C2(`source`/`status` 3자 드리프트)를 1순위로 C3~C5(테스트 갭 5종), C6(코드 리뷰 WARN I1~I6), C7(scope 디렉터리 표), CORS/딥 핀/Python 3.11 재검증을 handoff 문서에 정리했다.
- 이유: backend API 경계가 Frontend/QA와 바로 결합 가능한지 점검 근거를 고정하고, 누수 없이 프론트엔드·QA에 체크리스트를 인계하기 위해.
- 영향 파일: `docs/modules/backend_dev_module_1_handoff.md`, `docs/change_history.md`
- 후속 작업: Frontend Dev(`module_3/4/5`)는 handoff §5·§6.1, QA Engineer는 §6.2(C3~C5 회귀 테스트 5종 추가)를 수행한다. Backend Dev 후속 커밋은 §6.3에 따라 C1/C2 단일 결정(도메인 확장 A 또는 축소 B)으로 scope/코드/테스트/architecture를 동시 정렬한다.

### 2026-04-18T18:20:00
- 요약: 조합 카드 시각화 컴포넌트(`frontend_dev_module_3`) build 단계를 완료했다. scope §구현 순서 1–3 에 따라 `web/styles/cards.css` 를 신설하고 `web/index.html` 에 `base → layout → cards` 링크 1줄을 추가했으며, `web/js/components/CardList.js` 를 자리표시자에서 실제 카드 UI로 치환했다(요약: 번호 공 6개 + 점수 텍스트 / 상세: 점수 게이지 `role="meter"` + 홀짝 배지 + 5칸 구간 히스토그램). 번호 공은 1..45 를 한국 로또 표준 5단계 색상 버킷(`b1..b5`)으로 매핑하고 방어적으로 오름차순 정렬한다. 접기/펼치기는 `<button aria-expanded>` 한 개로 통합하고 Enter/Space 를 preventDefault 후 토글한다. `pytest tests/frontend -q` 4건 통과를 확인했다.
- 이유: module_2 가 노출한 `renderCardList` 자리표시자를 실제 시각화로 교체해 사용자 시나리오(“카드 탭 → 상세 영역 표시”)를 충족하고, `qa_engineer_module_7` smoke 계약과 `frontend_dev_module_5` 오프라인 폴백 결합 지점을 유지하면서 스타일만 별도 파일로 격리하기 위해.
- 영향 파일: `web/js/components/CardList.js`, `web/styles/cards.css`, `web/index.html`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_3_verify_3` 에서 iPhone SE(375)/Pixel(412) 뷰포트 수동 렌더(가로 스크롤 없음, 탭·키보드 펼침 동작, `prefers-reduced-motion` 대응)를 점검하고 잔여 리스크 R1(재렌더 시 펼침 상태 초기화), R2(번호 공 대비 AA), R3(필드 누락 방어) 현황을 handoff 메모에 기록한다. `module_5` 는 `source === 'offline' | 'cache'` 상태에서 본 카드 렌더를 그대로 재사용한다.

### 2026-04-18T18:05:00
- 요약: 모바일 반응형 추천 웹 UI 셸(`frontend_dev_module_2`) verify 단계를 완료했다. scope 문서의 파일 레이아웃과 컴포넌트 공개 API 계약이 코드와 일치함을 확인했고, `pytest tests/frontend -q`가 4건 모두 통과함을 확인했다. 잔여 리스크 5건(iPhone SE/Pixel 수동 렌더 미수행, 백엔드 확장 메타 미소비, 비-idle 경로 empty-hint 미재삽입, 구형 Safari `AbortController` fallback, 캐시 성공 UX 부재)을 `docs/work-items/.../frontend-module-2-verify-handoff.md`에 기록하고 `module_3/4/5`·QA로 후속 작업을 위임했다.
- 이유: 셸 계약이 하위 모듈과 QA 스위트가 바로 결합 가능한 상태임을 공식화하고, 브라우저 수동 렌더 점검 등 남은 확인 항목을 누수 없이 인계하기 위해.
- 영향 파일: `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/frontend-module-2-verify-handoff.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_3` build에서 `renderCardList` 치환과 `web/styles/cards.css` 분리를 진행하고, `frontend_dev_module_4`/`frontend_dev_module_5`는 본 handoff의 우선순위 2·3에 따라 슬라이더/오프라인 폴백을 얹는다. QA는 `qa_engineer_module_7` 후속에서 상태 전이 smoke 보강을 이어간다.

### 2026-04-18T17:55:00
- 요약: `backend_dev_module_1`(로또 추천 REST API) 전체 정합성 교차검증을 수행해 결과를 `docs/code_review/backend_dev_module_1_cross_validation.md`로 남겼다. 판정은 `WARN`이며, 핵심 계약(엔드포인트·스키마·에러 envelope·DI 주입 규약)은 scope ↔ 구현 ↔ 테스트가 정렬되어 인수인계 가능하지만 `GET /api/recommend`의 `source`/`status` 라벨에서 scope({api,cache}, {success,degraded-success}) ↔ 구현({api,cache,offline}, offline 분기 status='success' 유지) ↔ 테스트(`source=='offline'` 단언) **3자 계약 드리프트**가 굳어진 상태다. 더불어 에러 envelope 형상·헬스·503 폴백·X-Request-ID 회귀 그물망 부재(C3~C5)와 코드 리뷰 WARN 5건 미반영(C6)을 이슈로 기록했다.
- 이유: backend_dev_module_1 build/code review 산출물에 대한 모듈 단위 정합성을 검증해 frontend `module_5` 오프라인 배지 작업으로 같은 드리프트가 전파되는 것을 막고, verify 단계에서 단일 결정으로 정렬하도록 의사결정 포인트(C1/C2)를 명시하기 위해.
- 영향 파일: `docs/code_review/backend_dev_module_1_cross_validation.md`, `docs/change_history.md`
- 후속 작업: 다음 작업자(verify 또는 frontend 통합)는 C1/C2를 같은 커밋에서 해결해 scope, 구현, 테스트, architecture, frontend scope를 동시에 정렬하고, 권고된 테스트(`/api/health`, `/api/draws/latest` 503, X-Request-ID echo, 422 envelope 형상, `status` 필드 단언) 5종을 `tests/api/`에 추가한다. 코드 리뷰 WARN 5건(I1~I3, I5, I6)도 verify 단계 또는 후속 커밋에서 일괄 보강을 권고한다.

### 2026-04-18T17:40:00
- 요약: 조합 카드 시각화 컴포넌트(`frontend_dev_module_3`)의 범위, 공개 인터페이스, 구현 순서를 고정했다. `renderCardList(el, combos)` 공개 API 시그니처는 그대로 유지하고 내부 구현만 번호 공·점수 게이지·홀짝 배지·구간 히스토그램·접기/펼치기 토글로 치환한다. 스타일은 신규 `web/styles/cards.css` 로 격리하고 `web/index.html` 에 링크 1줄을 추가한다.
- 이유: build 단계에서 DOM 구조, 접근성, CSS 격리 방식, 영향 파일 목록을 재해석하지 않도록 계약을 먼저 고정하고, `qa_engineer_module_7` smoke 테스트 및 `frontend_dev_module_5` 오프라인 폴백과의 결합 지점을 명시하기 위해.
- 영향 파일: `docs/modules/frontend_dev_module_3_scope.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_3_build_2` 에서 scope 문서 §구현 순서 1–7 을 그대로 실행하고, `docs/architecture.md` 의 “프론트엔드 셸 공개 API 요약 > `renderCardList`” 항목은 build 단계에서 실제 시각화 설명으로 갱신한다.

### 2026-04-18T17:20:00
- 요약: `backend_dev_module_1`(로또 추천 REST API) build 산출물에 대한 코드 리뷰 결과를 `docs/code_review/backend_dev_module_1_code_review.md`로 남겼다. 판정은 `WARN`이며, 핵심 계약(엔드포인트·스키마·에러 envelope·테스트 DI 규약)은 scope 문서와 정합하지만 온라인 경로 null 가드, DrawCacheService 예외 삼킴, `_unexpected_exception_handler` 로깅 부재, `RecommendationService`가 DI 싱글톤 대신 자체 `DrawCacheService`를 생성하는 비일관성, `X-Request-ID` 로그 인젝션 방어 부재 등 5건의 WARN과 5건의 INFO를 기록했다.
- 이유: backend_dev_module_1 build 결과에 대한 코드 품질·보안·설계 리뷰를 수행해 후속 verify/핸드오프 전에 리스크를 명시하기 위해.
- 영향 파일: `docs/code_review/backend_dev_module_1_code_review.md`, `docs/change_history.md`
- 후속 작업: Backend Dev는 WARN 5건(I1~I5, I6 포함 재검토)을 후속 커밋에서 보강할지 판단하고, verify 단계에서 오프라인 폴백/빈 캐시 503 경로와 요청 ID 로그 무결성 시나리오를 수동 확인한다.

### 2026-04-18T17:10:00
- 요약: 로또 추천 REST API 서버(`backend_dev_module_1`) build 단계를 완료했다. `server/` 하위에 `bootstrap.py`, `schemas.py`, `errors.py`, `services/draw_cache.py`, `services/recommendation.py`, `dependencies.py`, `app.py`를 scope 문서 §8의 순서대로 생성하고 모듈 레벨 `app = create_app()`를 노출했다. 워크스페이스 루트 `conftest.py`가 QA fixture용 `QA_API_APP_TARGET`과 `QA_API_PREDICTOR_DEPENDENCY` 환경 변수를 주입한다.
- 이유: Frontend/QA가 대기 중인 API 계약(§3~§4)을 실제 동작 서버와 테스트 더블 주입 지점으로 구현해, 후속 모듈과 QA 테스트 스위트가 바로 결합 가능하도록 하기 위해.
- 영향 파일: `server/__init__.py`, `server/bootstrap.py`, `server/schemas.py`, `server/errors.py`, `server/services/__init__.py`, `server/services/draw_cache.py`, `server/services/recommendation.py`, `server/dependencies.py`, `server/app.py`, `conftest.py`, `requirements.txt`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `backend_dev_module_1_verify_1`에서 수동 스모크(캐시 비어 있을 때 503 응답, 정적 자산 마운트 확인)와 오프라인 폴백 경로 회귀를 점검하고, 프론트엔드는 실제 응답 스키마와 DTO를 동기화한다.

### 2026-04-18T16:55:00
- 요약: 모바일 반응형 추천 웹 UI 셸(`frontend_dev_module_2`) build 단계 구현을 완료했다. `web/` 하위에 `index.html`, `styles/{base,layout}.css`, `js/{app,state,api}.js`, `js/components/{CardList,ParamPanel,OfflineBanner}.js`를 scope 문서의 구현 순서 1–8을 따라 생성했다.
- 이유: 하위 모듈(`module_3/4/5`)이 공개 API와 DOM 슬롯을 바로 소비할 수 있도록 셸 계약을 실제 코드로 고정하고, QA smoke 테스트가 정적 산출물과 컴포넌트 export를 직접 검증할 수 있게 하기 위해.
- 영향 파일: `web/index.html`, `web/styles/base.css`, `web/styles/layout.css`, `web/js/state.js`, `web/js/api.js`, `web/js/app.js`, `web/js/components/CardList.js`, `web/js/components/ParamPanel.js`, `web/js/components/OfflineBanner.js`, `docs/architecture.md`, `docs/change_history.md`.
- 후속 작업: `frontend_dev_module_2_build_2` 검증(handoff) 태스크에서 실제 브라우저 뷰포트(iPhone SE/Pixel) 수동 렌더 확인을 수행하고, `module_3/4/5`는 본 구현이 노출한 컴포넌트 공개 API를 치환 구현한다.

### 2026-04-18T16:50:00
- 요약: 프론트엔드 렌더링 smoke 테스트(`qa_engineer_module_7`)의 검증 범위, 테스트 인터페이스, 구현 순서를 고정했다.
- 이유: build 단계에서 테스트 대상 파일, 공개 API, fixture 구조를 다시 해석하지 않도록 QA 계약을 먼저 확정하고, 프론트엔드 셸 변경에 대한 최소 회귀 검출선을 명확히 하기 위해.
- 영향 파일: `docs/modules/qa_engineer_module_7_scope.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `qa_engineer_module_7_build_2`에서 `tests/frontend/` 구조를 만들고, 본 문서의 구현 순서(1–8)에 따라 파일 존재성, HTML 셸 계약, JS export 계약, 대표 상태 smoke 테스트를 구현한다.

### 2026-04-18T16:35:00
- 요약: 로또 추천 REST API 서버(`backend_dev_module_1`)의 범위, 엔드포인트 계약, 에러 스키마, 구현 순서를 고정했다.
- 이유: 프론트엔드·QA가 스키마를 계약으로 삼아 병렬 작업을 시작할 수 있도록 build 단계 이전에 API 경계를 고정하고, `lotto_predictor_v2`의 import 재사용 방식을 문서화해 신규 알고리즘 개발을 배제하기 위해.
- 영향 파일: `docs/architecture.md`, `docs/plans/2026-04-18-backend-api-scope.md`, `docs/change_history.md`
- 후속 작업: `backend_dev_module_1_build_1`에서 scope 문서 §8의 실행 순서대로 `server/` 디렉터리 골격, Pydantic 스키마, 서비스 레이어를 구현한다. 프론트엔드는 §3~§4 응답 스키마를 계약으로 사용하고, QA는 `create_app()` 팩토리를 기반으로 httpx TestClient fixture를 구성한다.

### 2026-04-18T01:35:00
- 요약: 모바일 반응형 추천 웹 UI(`frontend_dev_module_2`)의 범위, 인터페이스, 구현 순서를 정의했다.
- 이유: 프론트엔드 셸과 하위 모듈(카드·슬라이더·오프라인) 사이의 공개 API를 먼저 고정해, build 단계에서 DOM 슬롯·JS 모듈 경계가 흔들리지 않도록 하기 위해.
- 영향 파일: `docs/architecture.md`, `docs/modules/frontend_dev_module_2_scope.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_2_build_2`에서 scope 문서의 구현 순서(1–10)에 따라 `web/` 골격을 구현하고, `module_3/4/5` scope 문서는 본 문서의 컴포넌트 공개 API 표를 역참조한다.

### 2026-04-18T01:26:22
- 요약: API 단위 테스트 스위트의 범위, 테스트 인터페이스, 구현 순서를 정의했다.
- 이유: QA build 단계에서 테스트 대상과 fixture 경계를 다시 해석하지 않도록 선행 계약을 고정하기 위해.
- 영향 파일: `docs/architecture.md`, `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/qa-api-unit-test-scope.md`, `docs/change_history.md`
- 후속 작업: QA build 단계에서 `tests/api/` 구조와 fixture를 실제 코드로 구현하고, 백엔드 구현이 노출한 주입 지점에 맞춰 stub 방식을 확정한다.

### 2026-04-18T01:19:38
- 요약: 문서 계약 초기화.
- 이유: 아키텍처와 워크플로 변경 이력을 안정적으로 보존하기 위해.
- 영향 파일: `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: 이 파일을 append-only로 유지하고, 생성하거나 수정하는 모든 문서를 운영체제 언어 코드 `ko-KR`에 맞는 한국어로 작성한다.
