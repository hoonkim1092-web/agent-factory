# Backend Dev Module 1 — 로또 추천 REST API 서버 Handoff 메모

- 작업: `backend_dev_module_1_verify_3`
- 단계: `verify`
- 작성자: Backend Dev
- 작성 시각: 2026-04-18
- 상태: **검증 완료, 다음 작업자 인계 가능**. 계약 드리프트 1건(C1/C2)은 후속 단일 커밋에서 결정 필요.
- 선행 산출물
  - 설계: `docs/plans/2026-04-18-backend-api-scope.md`
  - 구현: `server/app.py`, `server/bootstrap.py`, `server/dependencies.py`, `server/errors.py`, `server/schemas.py`, `server/services/recommendation.py`, `server/services/draw_cache.py`
  - 테스트: `tests/api/test_recommend_endpoint.py`, `tests/api/conftest.py`, 워크스페이스 `conftest.py`
  - 리뷰: `docs/code_review/backend_dev_module_1_code_review.md`, `docs/code_review/backend_dev_module_1_cross_validation.md`
  - 아키텍처 요약: `docs/architecture.md` §"백엔드 API 공개 인터페이스 요약"

## 1. 검증 결과 요약

### 1.1 3단계 검증 로그 (2026-04-18)

| 단계 | 명령 | 결과 |
|------|------|------|
| py_compile | `python3 -m py_compile server/__init__.py server/app.py server/bootstrap.py server/dependencies.py server/errors.py server/schemas.py server/services/__init__.py server/services/draw_cache.py server/services/recommendation.py` | **OK** (`PY_COMPILE_OK`) |
| pytest | `python3 -m pytest tests/api -v` | **10 passed, 7 warnings in 0.37s** (deprecation 경고는 Starlette 쪽 `HTTP_422_UNPROCESSABLE_ENTITY` 상수 리네임으로, 계약 영향 없음) |
| import smoke | `python3 -c "from server.app import create_app, app"` | **OK** — 등록 라우트: `/api/openapi.json`, `/api/docs`, `/docs/oauth2-redirect`, `/api/health`, `/api/recommend`, `/api/draws/latest`, `/static` |

### 1.2 보조 런타임 스모크(수동)
- `GET /api/health` → 200, `{"status":"ok","version":"0.1.0","time":"<ISO8601>"}`
- `GET /api/openapi.json` → 200 (FastAPI OpenAPI 3 스키마 노출)
- `X-Request-ID` 응답 헤더가 자동 발급·회신됨(`RequestIdMiddleware`).
- 스텁 DI(`get_draw_cache_service`→`get_latest()=None`)로 `GET /api/draws/latest` → **503 `data_unavailable`**, envelope `{"error":{"code":"data_unavailable","message":"캐시된 회차가 없습니다."}}` 확인.
- 스텁 DI(`get_recommendation_service`)로 `GET /api/recommend?n=2&draws=100` → 200 정상 응답, `n=99` → **422 `invalid_parameter`**, envelope `{"error":{"code":"invalid_parameter", "message":"...","details":{"errors":[...]}}}` 확인.
- 의존성 고정 확인: `requirements.txt`는 scope §6.1과 1:1 일치 — `fastapi>=0.110`, `uvicorn[standard]>=0.29`, `pydantic>=2.5`, `httpx>=0.27`.

## 2. 완성된 엔드포인트 목록과 계약

| 메서드 | 경로 | 쿼리/바디 | 성공 응답 | 실패 시나리오 |
|--------|------|-----------|-----------|----------------|
| `GET` | `/api/health` | 없음 | 200 `{status:"ok", version:"0.1.0", time:<ISO8601 UTC>}` | — |
| `GET` | `/api/recommend` | `n:int[1..10]=5`, `draws:int[100..500]=500`, `offline:bool=false` | 200 `{generated_at, source, status, draws_used, latest_draw_no, latest_draw_date, combos:[{numbers[6], score, odd_even_ratio, section_distribution}]}` | 422 `invalid_parameter`(범위/타입 위반), 503 `data_unavailable`(캐시/온라인 모두 실패), 500 `internal_error` |
| `GET` | `/api/draws/latest` | 없음 | 200 `{round, numbers[6], bonus, fetched_at}` | 503 `data_unavailable`(캐시 공란) |

공통 에러 envelope: `{"error":{"code":"<string>", "message":"<string>", "details":{}?}}`.

정적 자산: 환경변수 `LOTTO_STATIC_DIR` 우선, 없으면 `web/` 디렉터리가 `/static`으로 자동 마운트. 프론트엔드는 같은 포트로 정적 자산을 제공할 수 있다.

CORS: 환경변수 `LOTTO_CORS_ORIGINS` (콤마 구분, 기본 `*`), 허용 메서드는 `GET`만, 모든 헤더 허용.

## 3. 실행·배포 방법

### 3.1 의존성 설치
```bash
pip install -r projects/lotto_mobile_web/requirements.txt
```

### 3.2 수동 기동(개발)
```bash
cd projects/lotto_mobile_web
python -m uvicorn server.app:create_app --factory --reload --port 8000
# 또는 모듈 레벨 싱글톤 사용:
python -m uvicorn server.app:app --reload --port 8000
```

> `server.app.app`은 `create_app()`으로 사전 초기화된 인스턴스를 노출한다. uvicorn `--factory`를 선호하지 않는 테스트 러너/도커 헬스체크도 그대로 사용 가능하다.

### 3.3 환경 변수
| 변수 | 기본 | 설명 |
|------|------|------|
| `LOTTO_PREDICTOR_SRC` | `projects/lotto_predictor_v2/src` 자동 탐색 | `lotto_predictor_v2` 소스 경로 오버라이드 |
| `LOTTO_STATIC_DIR` | `../web` (워크스페이스 `web/`) | 정적 자산 루트 |
| `LOTTO_CORS_ORIGINS` | `*` | 허용 origin. `,`로 여러 개 |
| `QA_API_APP_TARGET` | `server.app:app` | QA pytest가 import할 ASGI app 경로 |
| `QA_API_PREDICTOR_DEPENDENCY` | `server.dependencies:get_recommendation_service` | DI override 타깃 |

### 3.4 초기 캐시 부트스트랩 (운영 체크)
- `/api/draws/latest`와 `offline=true` 경로는 `lotto_predictor_v2` 캐시(`lotto.cache.store.LottoCacheStore`)에 의존한다.
- 신규 배포 환경에서는 캐시가 비어 있을 수 있으므로, 서비스 기동 전 **CLI로 1회 수집**하거나 온라인 경로가 캐시를 채우도록 warm-up을 돌려야 한다.
- 캐시 공란 상태에서는 `/api/draws/latest`가 503, `/api/recommend?offline=true`도 503 `data_unavailable`을 반환한다 (scope §3.4, §R3).

### 3.5 운영 체크리스트
1. `GET /api/health` 200인지 외부 헬스체커에 연결.
2. `X-Request-ID` 헤더가 리버스 프록시를 통과해 로그로 상관관계 추적되는지 확인.
3. CORS origin을 실제 프론트 배포 도메인으로 좁힐 것(현재 기본 `*`).
4. 캐시 디스크(`lotto_predictor_v2`의 sqlite/json 경로)가 컨테이너 재기동에도 보존되는지 확인.

## 4. 알려진 제한과 미해결 이슈

### 4.1 계약 드리프트 (cross-validator C1/C2, **단일 커밋으로 정렬 필요**)
- `GET /api/recommend` 응답 `source`/`status` 도메인이 scope ↔ 구현 ↔ 테스트 3자 사이에서 어긋나 있다.
  - scope §3.3/§7: `source∈{api,cache}`, `offline=true` → `source=cache, status=degraded-success`.
  - 구현(`server/services/recommendation.py`): `source="offline" if offline else "api"`, offline 경로 `status="success"` 유지.
  - 테스트(`tests/api/test_recommend_endpoint.py::test_recommend_uses_offline_source_when_requested`): `assert payload["source"] == "offline"`.
- 영향: Frontend(`frontend_dev_module_5` 오프라인 배지) 분기 로직이 3자 중 어느 쪽을 따르든 나머지 두 곳이 회귀한다.
- 해소 방안(둘 중 택일)
  - **(A) 도메인 확장** — scope를 `source∈{api,cache,offline}`, `status∈{success,degraded-success}`로 확장하고 architecture/frontend scope 동기 갱신.
  - **(B) 도메인 축소** — 구현을 `offline=true → source="cache", status="degraded-success"`로 맞추고 테스트 단언·architecture 갱신.
- 담당: 다음 build 단계(backend 후속 커밋) 또는 `frontend_dev_module_5` scope에서 단일 결정 후 **같은 커밋**으로 scope+코드+테스트+architecture 동시 갱신.

### 4.2 테스트 커버리지 갭 (cross-validator C3~C5)
현재 `tests/api/`가 덮지 않는 시나리오(우선순위 H/M):
- `GET /api/health` contract 회귀(`status==ok`, `version`, `time` ISO8601) — **H**
- `GET /api/draws/latest` 200 정상 + 503 분기 — **M**
- `/api/recommend` 503 `data_unavailable` envelope 형상 — **H**
- 422 응답 envelope 구조(`{error:{code:"invalid_parameter", message, details:{errors:[...]}}}`) — **H**
- `X-Request-ID` 응답 헤더 echo + 클라이언트 발급 ID 보존 — **M**
- 응답 dict의 `status`, `latest_draw_no`, `latest_draw_date`, `combos[*].score`(float), `section_distribution` 타입(dict vs list) 단언 — **H**

### 4.3 코드 리뷰 WARN 미반영 (cross-validator C6, code-review I1~I6)
| ID | 위치 | 요지 | 권고 |
|----|------|------|------|
| I1 | `services/recommendation.py:_load_online` | 온라인 경로에서 `latest`/`loaded[-1]` null 가드 부재 | 예외 감싸서 캐시 폴백으로 내려보내기 |
| I2 | `services/draw_cache.py:load_recent` | 광역 `except Exception` 삼킴(로그 없음) | `logger.warning`으로 사유 보존 |
| I3 | `errors.py:_unexpected_exception_handler` | 내부 500에서 `logger.exception` 누락 | 스택 트레이스 서버 로그에 기록 |
| I4 | `dependencies.py` | `RecommendationService`가 `DrawCacheService`를 내부 생성 → `/api/draws/latest`와 인스턴스 분리 | DI에서 하나의 `DrawCacheService` 싱글톤을 주입받도록 변경 |
| I5 | `app.py:RequestIdMiddleware` | 클라이언트가 보낸 `X-Request-ID` 문자열이 로그에 그대로 주입 | 정규식/길이 제한으로 sanitize |
| I6 | `app.py:/api/recommend` | `response_model` 미선언 (`JSONResponse` 직접 반환) | `response_model=RecommendationResponse`로 OpenAPI 스키마 노출 |

> 모두 인수인계 차단 사항은 아니나, 운영 관측성·로그 무결성·OpenAPI 계약 노출 관점에서 후속 보강 권고.

### 4.4 기타
- **scope §5 디렉터리 표 갱신 미반영(C7)**: scope가 `tests/server/`를 명시하지만 실제 QA는 `tests/api/`. architecture는 후자로 정렬됨. 한 줄 갱신 권고.
- **Pydantic v2 + Python 3.14**: 로컬 실행은 Python 3.14.3 / pytest 9.0.3에서 통과. scope §6.1은 Python 3.11을 권장. 배포 환경에서 3.11로 재확인 필요.
- **의존성 핀**: `requirements.txt`는 `>=` 하한만 고정. 프로덕션에서는 lockfile 또는 `==` 핀을 권고.
- **Starlette deprecation**: `HTTP_422_UNPROCESSABLE_ENTITY` → `HTTP_422_UNPROCESSABLE_CONTENT` 리네임 경고 7건. 향후 Starlette 메이저 업그레이드 시 갱신 필요.
- **CORS 기본 `*`**: 배포 전에 반드시 도메인 화이트리스트로 좁힐 것.

## 5. 프론트엔드 연동 시 유의사항

1. **응답 `source`/`status` 필드**: 현재 `source` 값은 `api | cache | offline` 3종이 실제로 나온다. scope(§3.3)는 `api | cache`만 규정. 4.1 결정이 내려오기 전까지 프론트는 방어적으로 세 값 모두를 허용하거나, 결정 대기 상태임을 컴포넌트 스타일 가이드에 명시할 것.
2. **`combos[*].section_distribution` 형식**: scope(§3.3)는 dict(`{"1-10":1,...}`)로 기술되어 있다. 실제 `_combo_to_dict()`가 반환하는 형태는 `lotto.recommender.recommend_combinations` 구현에 의존한다. 프론트 연동 전 실제 엔드포인트 응답을 1회 캡처해 dict인지 list인지 확정하고, 카드 히스토그램 렌더러(`frontend_dev_module_3`의 `renderCardList`)가 두 형태 모두 견디도록 방어적 가드를 넣거나 회귀 테스트(C5)로 고정할 것.
3. **에러 envelope**: 프론트 에러 배너/토스트는 `payload.error.code`(`invalid_parameter`/`data_unavailable`/`internal_error`/`not_found`/`http_error`)로 분기한다. `details` 필드는 선택적. 422는 `details.errors[].loc`으로 필드 단위 오류를 추출 가능.
4. **X-Request-ID**: 클라이언트가 `X-Request-ID` 헤더를 보내면 그대로 echo, 없으면 서버가 uuid4로 발급. 고객 지원 티켓을 위해 프론트 fetch 래퍼에서 RID를 로깅/UI에 노출 권고.
5. **오프라인 폴백 UX**: `source=offline` 또는 `source=cache`일 때 카드 상단에 stale 배지, `latest_draw_no/date`를 함께 노출. `status=degraded-success`가 나오는 경로(온라인→캐시 폴백)는 `source=cache`와 중복이므로 배지 하나만 노출.
6. **정적 자산**: `/static/...`으로 프론트 번들을 배포하거나, 프록시를 통해 같은 origin을 유지할 것. CORS는 개발 편의용 `*`이므로 본격 배포 시 좁힌다.
7. **파라미터 경계**: `n∈[1..10]`, `draws∈[100..500]`. 슬라이더(`frontend_dev_module_4`)는 이 범위를 UI 단에서 먼저 제한해 422를 줄일 것.
8. **응답 지연**: `draws=500` 기본값에서 P95 < 3초 목표. 모바일에서는 스켈레톤/로딩 UX 필요(장기 호출 시 취소 UX는 module_4/5가 결정).

## 6. 후속 작업자 체크리스트

### 6.1 Frontend Dev (`frontend_dev_module_3/4/5`)
- [ ] `GET /api/recommend` 응답을 실기기/Chrome DevTools로 1회 캡처해 `section_distribution` 실제 타입(dict vs list)을 확정하고 렌더러에 반영.
- [ ] `source`/`status` 값 매핑 테이블을 컴포넌트 레벨로 고정하되, 4.1 결정이 내려오면 단일 값으로 축소.
- [ ] 에러 envelope(`error.code`) 기반 사용자 메시지 매핑 테이블 정의.
- [ ] 오프라인 배지(`module_5`)는 `source∈{cache,offline}` 둘 다를 수용하거나 4.1 결정 후 한 값으로 좁힐 것.
- [ ] 파라미터 슬라이더 UI에서 `n∈[1..10]`, `draws∈[100..500]` 경계를 시각적으로 강제.
- [ ] 프론트 fetch 래퍼가 `X-Request-ID`를 로깅하고(가능하면) UI 장애 안내에 노출.

### 6.2 QA Engineer (`qa_engineer_module_*`)
- [ ] `tests/api/`에 C3~C5 회귀 테스트 5종 추가:
  - `test_health_returns_contract_shape`
  - `test_latest_draw_returns_503_when_cache_empty` (DI override로 `get_draw_cache_service` 스텁 → `get_latest()=None`)
  - `test_recommend_returns_503_when_data_unavailable` (`get_recommendation_service` 스텁이 `DataUnavailableError` 발생)
  - `test_request_id_header_is_echoed` (요청 헤더 `X-Request-ID` 지정/미지정 두 케이스)
  - `test_invalid_query_envelope_shape` (422 envelope가 `{error:{code:"invalid_parameter",message,details:{errors}}}` 인지 단언)
- [ ] 응답 dict 단언을 `status`, `latest_draw_no`, `latest_draw_date`, `combos[*].score` 타입, `section_distribution` 타입까지 확장.
- [ ] `source`/`status` 계약 드리프트 해소(4.1) 후 단언 값을 단일 값으로 좁힐 것.
- [ ] `frontend_dev_module_5` 오프라인 폴백과 결합되는 브라우저 smoke(`qa_engineer_module_7`)에 `source=cache|offline` 배지 표시 케이스 추가.

### 6.3 Backend Dev (후속 커밋 / 다음 build)
- [ ] 4.1 C1/C2 결정에 따라 `server/services/recommendation.py`의 `source`/`status` 분기와 `docs/plans/2026-04-18-backend-api-scope.md` §3.3/§7, `docs/architecture.md`, 프론트 scope를 **같은 커밋으로** 정렬.
- [ ] 코드 리뷰 WARN I1~I6 보강 여부 결정. I4(DI 싱글톤 공유)는 `/api/draws/latest`와 `/api/recommend`가 같은 캐시 상태를 보게 만들어 회귀를 줄여준다.
- [ ] scope §5 디렉터리 표 `tests/server/` → `tests/api/` 한 줄 갱신(C7).
- [ ] 배포 파이프라인이 확정되면 `requirements.txt`를 lockfile 또는 `==` 핀으로 고정.

## 7. 변경 이력 동기화
- 본 verify 단계 항목을 `docs/change_history.md`에 append해 타임라인을 유지한다.
- architecture 수준 변경이 없으므로 `docs/architecture.md`는 이번 verify에서는 건드리지 않는다(4.1 결정 커밋에서 같이 업데이트).
