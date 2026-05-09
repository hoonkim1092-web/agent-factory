# Code Review — backend_dev_module_1 (로또 추천 REST API)

- 작업: `backend_dev_module_1_code_review`
- 단계: `code_review`
- 리뷰어: backend_dev_code_reviewer
- 리뷰 일시: 2026-04-18
- 대상 산출물: `server/app.py`, `server/bootstrap.py`, `server/dependencies.py`, `server/errors.py`, `server/schemas.py`, `server/services/recommendation.py`, `server/services/draw_cache.py`

## 판정 요약

- **verdict**: `WARN` — 핵심 계약(엔드포인트, 스키마, 에러 envelope, 미들웨어, 테스트 주입 규약)은 scope 문서와 정합한다. 다만 온라인 경로의 null 가드, 조용한 예외 삼킴, DI 일관성 등 몇 가지 유지보수·관측성 이슈가 남아 있어 후속 커밋에서 보강을 권고한다. 현재 상태로도 인수인계 가능.

## 검토 항목별 결과

### 1) 보안 (OWASP Top 10, 인증, 인젝션)

- **CORS 기본값 `*`** (`server/app.py:61-64`): scope §7에 명시된 기본 정책을 그대로 따름. 프론트 통합과 로컬 개발 편의를 위해 `*`를 허용하나, 운영 배포 시 반드시 `LOTTO_CORS_ORIGINS`로 제한되어야 함. (INFO)
- **요청 ID 주입 (`X-Request-ID`) 신뢰성** (`server/app.py:46-57`): 외부 헤더 값을 그대로 받아 `request.state`에 저장하고 로그에 출력한다. 제어문자/개행이 포함된 값이 들어오면 로그 포맷을 오염시킬 수 있다(로그 인젝션). 최소한 `\r\n` 제거 또는 UUID 포맷 검증 권고. (WARN)
- **입력 검증**: `RecommendationQuery`에서 `extra="forbid"` + 수치 범위 제한, `RecommendationCombo`에서 1..45 가드, `min_length=max_length=6` — 타입/범위 방어 견고. (PASS)
- **정적 파일 마운트** (`server/app.py:127-129`): `LOTTO_STATIC_DIR`을 `expanduser().resolve()` 후 `is_dir()` 체크. 임의 경로를 마운트할 가능성이 있으나 운영자가 명시적으로 설정하는 환경 변수이므로 신뢰 경계 내. (PASS)
- **인증/세션/SSRF 경로**: scope 상 제외. 외부 네트워크 호출은 `lotto_predictor_v2`의 공식 수집기만 호출하므로 SSRF 리스크 낮음. (PASS)

### 2) 버그 및 엣지 케이스

- **온라인 경로 null 가드 부족** (`server/services/recommendation.py:102-107`):
  ```python
  latest = predictor_collector.detect_latest_draw_no(probe_start=1200)
  ...
  start = max(1, latest - draws + 1)
  ```
  `detect_latest_draw_no`가 `None`을 반환하거나 예외를 던지면 `latest - draws + 1`에서 `TypeError`가 발생한다. 현재는 호출 측 `try/except Exception`이 오프라인 폴백으로 전환해주므로 응답 레벨에서 크래시하진 않지만, 로그에 `TypeError`가 남아 원인 파악이 흐려진다. 명시적으로 `if latest is None: raise RuntimeError(...)` 또는 초기 가드 추가 권고. (WARN)
- **`probe_start=1200` 매직 넘버** (`server/services/recommendation.py:102`): 현재 회차가 1200을 넘으면 탐색 성공 여부가 `detect_latest_draw_no` 구현 의존적으로 달라진다. 상수화하고 주석으로 의도(탐색 시작점) 설명 필요. (INFO)
- **`DrawCacheService.load_draws((1, 9999))` 매직 상한** (`server/services/draw_cache.py:41`): scope 문서에도 기록됨. 2026~2028년 내로 9999 도달은 없지만 상수로 분리 권고. (INFO)
- **`load_recent(draw_count=0)` 미정의 동작**: `draws[-0:]`는 Python에서 전체 리스트를 반환한다. API 입력 검증이 `draws>=100`을 강제하므로 현재 경로로는 도달 불가. 내부 호출 시 실수 여지 있음. `draw_count`에 `max(1, draw_count)` 가드 권고. (INFO)
- **`RecommendationService.predict`의 `status/source` 초기값** (`server/services/recommendation.py:52-67`): `offline=True`일 때 `status`가 `success`로 남는다. scope §3.3에서는 오프라인 경로도 `status=degraded-success`로 라벨링하도록 했으므로 일관성 측면에서 `offline=True` 분기에서도 `status="degraded-success"`를 설정하는 것이 계약과 더 정합적. (WARN)
- **`_jsonify`가 set/Decimal 등을 다루지 않음** (`server/app.py:142-153`): 현재 응답 생성 경로가 dataclass → dict → 기본 타입으로만 흐르므로 문제 없음. 향후 확장 시 주의. (INFO)

### 3) 설계 품질

- **DI 싱글톤 비일관성** (`server/dependencies.py` + `server/services/recommendation.py:43-44`): `/api/draws/latest`는 `get_draw_cache_service` 싱글톤을 쓰고, `RecommendationService`는 생성자에서 별도 `DrawCacheService()`를 새로 만든다. 두 엔드포인트가 서로 다른 캐시 서비스 인스턴스를 쓰게 된다. `RecommendationService`가 `get_draw_cache_service()`를 주입받도록 리팩터 권고(또는 FastAPI `Depends`로 체이닝). (WARN)
- **엔드포인트 `response_model` 일부 누락** (`server/app.py:105-111`): `/api/recommend`는 `JSONResponse`를 직접 반환하며 `response_model=RecommendationResponse`를 선언하지 않는다. OpenAPI 스키마가 응답 모양을 설명하지 못한다. `response_model=RecommendationResponse, response_model_exclude_none=True`를 지정하거나, Pydantic 직렬화를 사용하는 형태로 맞추는 편이 계약 노출에 유리. (WARN)
- **예측 모듈 부트스트랩 시점**: `server/services/recommendation.py:16`에서 모듈 import 시점에 `ensure_predictor_importable()`을 호출 — 테스트/import 순서에 영향을 주지만 단일 진입점으로 묶여 있어 수용 가능. (PASS)
- **에러 모델**: `ApiError`/`DataUnavailableError`를 도메인 예외로 정의하고, `install_error_handlers`에서 RequestValidationError/StarletteHTTPException/Exception 4단 매핑 — 깔끔한 분리. (PASS)

### 4) 에러 처리 / 관측성

- **조용한 예외 삼킴** (`server/services/draw_cache.py:40-43`):
  ```python
  try:
      draws = self._store.load_draws((1, 9999))
  except Exception:
      draws = []
  ```
  로그가 전혀 남지 않아 캐시 접근 실패 원인이 사라진다. 최소 `logger.warning("캐시 조회 실패: %s", exc)` 추가 권고. (WARN)
- **`_unexpected_exception_handler`가 예외 로깅을 하지 않음** (`server/errors.py:86-93`): 500 응답만 반환하고 스택트레이스/예외 메시지를 로그에 남기지 않는다. 디버깅 난이도를 크게 높이는 반패턴. `logger.exception(...)` 호출 추가 권고. (WARN)
- **온라인 실패 폴백 로그** (`server/services/recommendation.py:63-67`): `logger.warning`로 원인이 남으므로 관측성 적절. (PASS)

### 5) 성능

- **`load_draws((1, 9999))` 풀스캔**: 캐시가 JSON 기반이고 규모가 수백~수천 건이므로 현 시점 영향은 미미. `load_recent(draw_count=N)`가 실제로 필요한 건 최신 N건이므로 하위 저장소에 범위 축소를 위임할 수 있으면 개선 가능. scope 문서에 "공개 API 부재"로 기록됨. (INFO)
- **외부 네트워크 경로**: `_load_online`에서 동기 호출을 하지만 FastAPI가 threadpool로 래핑하므로 엔드포인트 블로킹은 회피. (PASS)
- **`lru_cache(maxsize=1)` 싱글톤**: 프로세스 생명주기 동안 재사용되므로 적절. 다만 DI 비일관성(위 설계 항목) 함께 고려. (PASS)

## 이슈 목록(JSON 호환)

```json
{
  "verdict": "WARN",
  "issues": [
    {
      "id": "I1",
      "severity": "warn",
      "category": "bug",
      "file": "server/services/recommendation.py",
      "line": 102,
      "summary": "detect_latest_draw_no()가 None/예외일 때 `max(1, latest - draws + 1)`에서 TypeError가 발생할 수 있음. 명시적 null 가드 필요."
    },
    {
      "id": "I2",
      "severity": "warn",
      "category": "observability",
      "file": "server/services/draw_cache.py",
      "line": 40,
      "summary": "캐시 로드 실패 시 bare except로 빈 리스트를 반환하면서 로깅이 없음. 최소한 logger.warning 필요."
    },
    {
      "id": "I3",
      "severity": "warn",
      "category": "observability",
      "file": "server/errors.py",
      "line": 86,
      "summary": "_unexpected_exception_handler가 예외를 로깅하지 않아 500 원인 추적이 어려움. logger.exception 추가 필요."
    },
    {
      "id": "I4",
      "severity": "warn",
      "category": "design",
      "file": "server/services/recommendation.py",
      "line": 43,
      "summary": "RecommendationService가 DI 싱글톤 대신 DrawCacheService를 자체 생성해 /api/draws/latest와 캐시 인스턴스가 분리됨. DI 주입으로 일관성 확보 권고."
    },
    {
      "id": "I5",
      "severity": "warn",
      "category": "security",
      "file": "server/app.py",
      "line": 47,
      "summary": "X-Request-ID 헤더를 검증 없이 수용해 로그 인젝션 가능. UUID 형식 검증 또는 제어문자 제거 권고."
    },
    {
      "id": "I6",
      "severity": "warn",
      "category": "design",
      "file": "server/app.py",
      "line": 105,
      "summary": "/api/recommend 엔드포인트에 response_model이 없어 OpenAPI가 응답 스키마를 드러내지 못함. response_model=RecommendationResponse 선언 권고."
    },
    {
      "id": "I7",
      "severity": "info",
      "category": "contract",
      "file": "server/services/recommendation.py",
      "line": 52,
      "summary": "offline=True 경로에서 status가 'success'로 남음. scope §3.3의 `degraded-success` 계약과 더 정합하도록 라벨 정리 권고."
    },
    {
      "id": "I8",
      "severity": "info",
      "category": "maintainability",
      "file": "server/services/recommendation.py",
      "line": 102,
      "summary": "probe_start=1200 매직 넘버. 상수화 및 의미 주석 권고."
    },
    {
      "id": "I9",
      "severity": "info",
      "category": "maintainability",
      "file": "server/services/draw_cache.py",
      "line": 41,
      "summary": "load_draws((1, 9999))의 9999 상한 매직 넘버. 상수화 권고."
    },
    {
      "id": "I10",
      "severity": "info",
      "category": "security",
      "file": "server/app.py",
      "line": 61,
      "summary": "CORS 기본값 `*`. 운영 배포 시 LOTTO_CORS_ORIGINS 환경 변수로 제한 필요(배포 체크리스트에 기재)."
    }
  ],
  "summary": "핵심 계약(엔드포인트 3종, Pydantic 스키마, 에러 envelope, 미들웨어, 테스트 DI 주입 규약)은 scope 문서와 일치해 PASS. 다만 온라인 경로 null 가드, DrawCacheService 예외 삼킴, 내부 500 로깅 부재, DI 싱글톤 비일관성, X-Request-ID 로그 인젝션 등 5건의 WARN과 5건의 INFO가 남음. 배포 전 WARN 5건은 보강 권고, 현재 상태로 인수인계는 가능."
}
```

## 후속 권고 (수용 여부는 Backend Dev 판단)

1. `server/services/recommendation.py`: `_load_online`에서 `latest is None` 명시 가드 + 온라인 소스 실패 분기 로깅 강화.
2. `server/services/draw_cache.py`: 예외 삼킴을 `logger.warning` 또는 `logger.exception`으로 전환.
3. `server/errors.py`: `_unexpected_exception_handler`에 `logger.exception("처리되지 않은 예외: request_id=%s", ...)` 추가.
4. `server/dependencies.py` + `server/services/recommendation.py`: `RecommendationService`가 `get_draw_cache_service()` 싱글톤을 공유하도록 DI 체이닝.
5. `server/app.py`: `request_id` sanitize (예: 공백 제거 + 정규식 `^[A-Za-z0-9._-]{1,128}$` 검증, 실패 시 신규 UUID 발급).
6. `server/app.py`: `/api/recommend`에 `response_model=RecommendationResponse` 선언(또는 Pydantic 직접 반환).

## 참고 자료

- scope 문서: `docs/plans/2026-04-18-backend-api-scope.md`
- 아키텍처 문서: `docs/architecture.md`
- 대상 커밋 범위: build 산출물(`server/**`), 테스트 기반 conftest(`conftest.py`, `tests/api/conftest.py`)

[backend_dev_code_reviewer] 작업 결과를 파일로 남깁니다.
