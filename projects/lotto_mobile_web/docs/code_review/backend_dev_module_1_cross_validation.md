# Cross Validation — backend_dev_module_1 (로또 추천 REST API)

- 작업: `backend_dev_module_1_cross_validate`
- 단계: `cross_validate`
- 검증자: backend_dev_cross_validator
- 검증 일시: 2026-04-18
- 대상 산출물:
  - 설계: `docs/plans/2026-04-18-backend-api-scope.md`
  - 구현: `server/app.py`, `server/bootstrap.py`, `server/dependencies.py`, `server/errors.py`, `server/schemas.py`, `server/services/recommendation.py`, `server/services/draw_cache.py`
  - 테스트: `tests/api/conftest.py`, `tests/api/test_recommend_endpoint.py`, 워크스페이스 `conftest.py`
  - 코드 리뷰: `docs/code_review/backend_dev_module_1_code_review.md`
  - 문서: `docs/architecture.md`, `docs/change_history.md`

## 판정 요약

- **verdict**: `WARN`
- 핵심 계약(엔드포인트 3종, Pydantic v2 모델, 공통 에러 envelope, 미들웨어, FastAPI `dependency_overrides` 주입 규약)은 scope ↔ 구현 ↔ 테스트가 정렬되어 있다.
- 다만 `source`/`status` 응답 라벨에서 **scope ↔ 코드 ↔ 테스트 3자 간 계약 드리프트**가 발견되었다. 이는 Frontend Dev가 응답 뱃지(`source=cache`/`source=offline`)에 분기 로직을 붙이기 전에 한쪽으로 통일해야 한다.
- 코드 리뷰가 남긴 WARN 5건(I1~I5)과 INFO 5건은 인수인계 차단 사항은 아니나 후속 보강 권고 항목으로 추적이 필요하다.
- 테스트 커버리지에 503 폴백, 요청 ID 헤더, `/api/health`, `/api/draws/latest` 시나리오가 누락되어 있다(이번 모듈의 책임 범위에서 보강 권고).

## 1) 모듈 간 인터페이스 일관성 (입출력 타입, 계약)

| 항목 | scope §3~§4 | 구현 | 테스트 | 결과 |
|------|-------------|------|--------|------|
| `GET /api/health` 응답 키 (`status`, `version`, `time`) | 정의됨 | `HealthResponse` 일치 | 미검증 | PASS (테스트 갭) |
| `GET /api/recommend` 쿼리 범위 (`n∈[1,10]`, `draws∈[100,500]`, `offline:bool`) | 정의됨 | `RecommendationQuery` 일치, `extra="forbid"` | 422 회귀 7건 검증 | PASS |
| `GET /api/recommend` 응답 필수 키 (`generated_at`, `source`, `status`, `draws_used`, `latest_draw_no`, `latest_draw_date`, `combos`) | 정의됨 | `predict()` 반환 dict 일치 | `generated_at/source/draws_used/combos` 형상 검증, `status/latest_*`는 미검증 | PASS (부분 검증) |
| `combos[*].numbers` 6개·1~45 | 정의됨 | `RecommendationCombo` 일치 | 6개·`int` 검증, 1~45 범위는 stub 데이터로만 보장 | PASS |
| `GET /api/draws/latest` 응답 (`round`, `numbers`, `bonus`, `fetched_at`) | 정의됨 | `DrawCacheEntry` 일치 | 미검증 | PASS (테스트 갭) |
| 에러 envelope `{error:{code,message,details}}` | 정의됨 | `_envelope()` 일치 | 422 status_code만 검증 (envelope 형상 미검증) | PASS (부분 검증) |
| `source` 도메인 값 | `{"api","cache"}` | `{"api","cache","offline"}` (offline 분기에서 `"offline"` 반환) | `assert payload["source"] == "offline"` | **FAIL — 3자 드리프트** |
| `status` 도메인 값 | `{"success","degraded-success"}` (offline=true → `degraded-success`) | offline=true 경로에서 `status="success"` 유지 | 미검증 | **FAIL — 계약 위반** |

### 핵심 발견: `source`/`status` 라벨 드리프트
- scope §3.3: "오프라인 폴백 → `source=cache`, `status=degraded-success`".
- scope §7: "`offline=true`이거나 온라인 경로 예외 발생 시 캐시 경로로 자동 전환하며 `source=cache`, `status=degraded-success`."
- 구현 `server/services/recommendation.py:52-67`:
  ```python
  source = "offline" if offline else "api"   # ← scope에 없는 값
  status = "success"
  if offline:
      cache_result = self._cache_service.load_recent(...)
      # source="offline", status="success" 그대로 — degraded 라벨 유실
  else:
      try: ...; source="api"; status="success"
      except: source="cache"; status="degraded-success"   # 이 분기만 계약 일치
  ```
- 테스트 `tests/api/test_recommend_endpoint.py:64-72`: `assert payload["source"] == "offline"` — 구현을 그대로 굳혀 scope를 위반.
- 영향: Frontend (`frontend_dev_module_5` 오프라인 배지)가 `source`로 분기하는 순간 `cache`/`offline` 두 값을 모두 처리해야 하거나, 한쪽이 다른 쪽을 따라가야 한다. 본 모듈에서 한쪽으로 정렬해 두는 것이 안전하다.

## 2) 설계 문서와 구현의 괴리

| 항목 | scope 명시 | 구현 상태 | 결과 |
|------|------------|-----------|------|
| `server/bootstrap.py`가 `LOTTO_PREDICTOR_SRC` env로 override 가능 | §6.2 | 구현 확인됨 | PASS |
| `create_app()` 팩토리 함수 노출 | §2.1 | `app.py:create_app` + 모듈 레벨 `app=create_app()` | PASS (uvicorn factory + 테스트 import 둘 다 지원) |
| 정적 자산 마운트 `/static` (Frontend가 추가) | §2.1 | `_resolve_static_dir()`로 `web/` 자동 마운트 | PASS |
| 에러 코드 3종 (`invalid_parameter`/`data_unavailable`/`internal_error`) | §3.1 | 모두 구현 | PASS |
| `X-Request-ID` 발급 + 로그 부착 | §7 | `RequestIdMiddleware` 구현 | PASS (단, 입력 sanitize 누락 — code review I5) |
| `lotto_predictor_v2` 부팅 시 import 스모크 | §6.2/§10 R1 | `ensure_predictor_importable()` 호출 | PASS |
| 응답 `source`/`status` 도메인 | §3.3, §7 | offline 경로 라벨 불일치 | **FAIL** (위 §1 참고) |
| `/api/recommend`에 `response_model` 선언 | scope에 명시되진 않으나 §3.3 스키마 노출 의도 | 미선언 (`JSONResponse` 직접 반환) | WARN (code review I6) |
| `RecommendationService` ↔ `DrawCacheService` 단일 인스턴스 공유 | scope 미언급 | `RecommendationService.__init__`이 `DrawCacheService()`를 자체 생성 → `/api/draws/latest`와 인스턴스 분리 | WARN (code review I4) |
| 디렉터리 구조 `server/`, `tests/server/` | §5 | 구현은 `server/` ✓, 테스트는 `tests/api/`로 위치 변경 | INFO (QA 모듈 6의 별도 결정으로 일관성 유지됨, scope 디렉터리 한 줄 갱신 필요) |

## 3) 테스트 커버리지 갭 (QA가 놓친 시나리오)

`tests/api/test_recommend_endpoint.py`(현재 4 테스트 + 7 파라미터)는 contract shape, 422 회귀, n=2 매칭, offline `source` 단일 값을 검증한다. 다만 다음 갭이 남아 있다.

| 갭 | 우선순위 | 사유 |
|----|----------|------|
| `GET /api/health` 응답 검증 (200 + `status==ok` + `version` + `time` ISO8601) | M | 헬스 체크가 인프라 모니터링/배포 readiness에 활용됨 |
| `GET /api/draws/latest` 정상 + 503 분기 검증 | M | scope §3.4가 503을 명시했고 구현도 503을 발생시키지만 회귀 그물망 없음 |
| `/api/recommend`에서 캐시 비어 있고 online 실패 → 503 `data_unavailable` envelope 형상 검증 | H | scope §3.1 에러 envelope 계약을 검증하는 유일한 폴백 경로 |
| `X-Request-ID` 응답 헤더 echo + 클라이언트 발급 ID 보존 | M | scope §7 관측성 계약 |
| 에러 envelope 형상 (422 응답이 `{"error":{"code":"invalid_parameter",...}}`인지) | H | 현재 422 status_code만 검증 — envelope 형상이 회귀해도 못 잡음 |
| `status` 필드 값 검증 (현재 미검증) | H | `source`/`status` 드리프트가 굳어진 직접 원인. 둘 중 하나라도 검증되면 조기 차단 가능했음 |
| `combos[*].score` 타입(float)과 `section_distribution`이 dict인지 list인지 (scope=dict, stub=list) | H | scope §3.3은 dict, 테스트 stub은 list — 실제 `_combo_to_dict()`가 어느 쪽을 반환하는지 회귀 검증 부재 |

## 4) 의존성 그래프 정합성

- `server/app.py` → `server/dependencies.py` → `server/services/{recommendation,draw_cache}.py` → `server/bootstrap.py` → `lotto_predictor_v2`. 순환 없음. PASS.
- `server/services/recommendation.py:16`이 모듈 import 시점에 `ensure_predictor_importable()`을 호출 — `tests/api/conftest.py`가 의존성 override를 하기 전에 이미 import가 끝나므로 테스트 부팅에 부작용 없음. PASS.
- `requirements.txt` ↔ scope §6.1 일치 확인 (`fastapi>=0.110`, `uvicorn[standard]>=0.29`, `pydantic>=2.5`, `httpx>=0.27`). 실제 파일 미점검 — 후속 verify에서 1회 확인 필요. INFO.
- 워크스페이스 `conftest.py`가 `QA_API_APP_TARGET`/`QA_API_PREDICTOR_DEPENDENCY`를 미리 세팅 → QA 작업자(`tests/api/conftest.py`)와 결합 지점이 정확히 맞음. PASS.

## 5) 문서 업데이트 누락

| 문서 | 갱신 대상 | 결과 |
|------|-----------|------|
| `docs/architecture.md` | "백엔드 API 공개 인터페이스 요약" 섹션 추가됨 (`server.app:create_app`, DI 지점, 서비스 계약, 미들웨어, 정적 마운트, 테스트 주입 규약) | PASS |
| `docs/change_history.md` | 2026-04-18T17:10:00 build 항목 + 17:20:00 code review 항목 등재 | PASS |
| `docs/code_review/backend_dev_module_1_code_review.md` | 단일 살아 있는 문서로 작성 (10개 이슈, JSON 호환 envelope 포함) | PASS |
| `docs/plans/2026-04-18-backend-api-scope.md` | scope 단계 산출물, build 결과로 §5 디렉터리 표(`tests/server/`)와 §3.3 `source`/`status` 도메인 갱신 필요 | WARN — 미반영 |
| 신규 cross validate 항목 (이 작업) | `docs/change_history.md`에 본 작업 항목 append 필요 | 본 작업에서 추가 |

## 이슈 목록 (JSON 호환)

```json
{
  "verdict": "WARN",
  "issues": [
    {
      "id": "C1",
      "severity": "block-candidate",
      "category": "contract-divergence",
      "files": [
        "docs/plans/2026-04-18-backend-api-scope.md",
        "server/services/recommendation.py",
        "tests/api/test_recommend_endpoint.py"
      ],
      "summary": "GET /api/recommend의 `source` 필드 도메인이 scope({api,cache}) ↔ 구현({api,cache,offline}) ↔ 테스트(offline 단언)에서 3자 드리프트. Frontend가 source 기반 뱃지를 붙이기 전에 한쪽으로 통일 필요.",
      "remediation_options": [
        "(A) scope를 source∈{api,cache,offline}로 확장하고 cache=온라인 폴백/offline=요청자 명시 분기로 의미를 분리한 뒤 architecture.md와 frontend scope에도 동기화.",
        "(B) 구현을 scope에 맞춰 offline=true → source='cache'로 통일하고 테스트 단언과 architecture.md를 함께 갱신."
      ]
    },
    {
      "id": "C2",
      "severity": "warn",
      "category": "contract-divergence",
      "files": [
        "server/services/recommendation.py",
        "docs/plans/2026-04-18-backend-api-scope.md"
      ],
      "summary": "scope §3.3+§7은 offline 경로 status='degraded-success'를 명시하지만 구현은 status='success'를 유지. C1 결정과 동일 커밋에서 일치시켜야 함."
    },
    {
      "id": "C3",
      "severity": "warn",
      "category": "test-gap",
      "files": ["tests/api/test_recommend_endpoint.py"],
      "summary": "에러 envelope 형상(422 응답 본문이 {error:{code,message,details}}인지) 검증 부재. status_code만 보면 envelope 회귀를 놓칠 수 있음."
    },
    {
      "id": "C4",
      "severity": "warn",
      "category": "test-gap",
      "files": ["tests/api/test_recommend_endpoint.py"],
      "summary": "GET /api/health, GET /api/draws/latest, /api/recommend의 503 폴백, X-Request-ID 응답 헤더에 대한 테스트 부재. scope §3.2/§3.4/§7 회귀 그물망이 없음."
    },
    {
      "id": "C5",
      "severity": "warn",
      "category": "test-gap",
      "files": ["tests/api/test_recommend_endpoint.py"],
      "summary": "`status`, `latest_draw_no`, `latest_draw_date`, `combos[*].score` 타입, `section_distribution` 타입(dict vs list)이 미검증. 스키마 회귀가 흘러나갈 수 있고, C1/C2 드리프트가 굳어진 직접 원인."
    },
    {
      "id": "C6",
      "severity": "warn",
      "category": "code-review-followup",
      "files": [
        "server/services/recommendation.py",
        "server/services/draw_cache.py",
        "server/errors.py",
        "server/dependencies.py",
        "server/app.py"
      ],
      "summary": "코드 리뷰 WARN 5건(I1 null 가드, I2 캐시 예외 삼킴 로깅, I3 500 핸들러 logger.exception, I4 DI 싱글톤 공유, I5 X-Request-ID sanitize, I6 response_model 누락)이 미반영 상태. 인수인계 가능하나 verify 또는 후속 커밋에서 보강 권고."
    },
    {
      "id": "C7",
      "severity": "info",
      "category": "scope-doc-stale",
      "files": ["docs/plans/2026-04-18-backend-api-scope.md"],
      "summary": "scope §5 디렉터리 표가 tests/server/를 명시하지만 실제 QA는 tests/api/에 구현. architecture.md는 후자로 정렬됨. scope 문서 1줄 갱신 권고."
    },
    {
      "id": "C8",
      "severity": "info",
      "category": "dependency-verification",
      "files": ["requirements.txt"],
      "summary": "requirements.txt ↔ scope §6.1 버전 핀 1회 매칭 검증이 verify 단계 체크리스트에 누락. verify 작업에서 import smoke와 함께 확인."
    }
  ],
  "summary": "core 계약(엔드포인트 3종, Pydantic 모델, 에러 envelope, DI override 지점, 정적 마운트, 미들웨어)은 scope ↔ 구현 ↔ 테스트가 정렬되어 인수인계 가능. 그러나 GET /api/recommend의 `source`/`status` 라벨에서 scope ↔ 구현 ↔ 테스트 3자 드리프트가 굳어졌고, 에러 envelope/헬스/503/X-Request-ID 회귀 그물망이 비어 있음. 코드 리뷰 WARN 5건은 미반영. 다음 작업(verify 또는 build 후속 커밋)에서 C1/C2를 단일 결정으로 통일하고 C3~C5 테스트를 보강할 것."
}
```

## 검증자 권고 (수용 여부는 Backend Dev/QA 판단)

1. **C1/C2를 같은 커밋으로 해결한다.** 두 가지 안 중 하나를 선택해 scope, 구현, 테스트, architecture, frontend scope를 동시에 정렬한다.
   - (A) 도메인 확장: `source∈{api,cache,offline}` + `status∈{success,degraded-success}`로 scope를 갱신하고 frontend는 `cache`/`offline`을 별개 뱃지로 분기한다.
   - (B) 도메인 축소: 구현이 `offline=true → source='cache', status='degraded-success'`를 따르도록 변경하고 테스트 단언을 같이 바꾼다. (현 scope §7과 가장 정합.)
2. **테스트 보강(C3~C5)** — `tests/api/`에 다음 케이스 추가 권고:
   - `test_health_returns_contract_shape`
   - `test_latest_draw_returns_503_when_cache_empty` (DI override로 `get_draw_cache_service` 스텁)
   - `test_recommend_returns_503_when_data_unavailable`
   - `test_request_id_header_is_echoed`
   - `test_invalid_query_envelope_shape`
   - 응답 dict에 `status`, `latest_draw_no`, `section_distribution` 타입까지 단언.
3. **코드 리뷰 후속(C6)** — verify 단계에서 I1/I2/I3/I5/I6를 일괄 보강하면 운영 관측성·로그 무결성이 크게 개선된다.
4. **scope 문서 정리(C7)** — `tests/server/` → `tests/api/`로 1줄 갱신.
5. **verify 체크리스트(C8)** — `requirements.txt` 버전 핀 1회 비교 + `python -m uvicorn server.app:create_app --factory` 수동 스모크.

## 결론

backend_dev_module_1은 **인수인계 가능(WARN)** 상태다. 다음 작업자(verify 또는 frontend 통합)는 위 이슈 목록 중 **C1/C2 결정을 가장 먼저 해소**해야 하며, 결정 결과를 scope·구현·테스트·architecture에 동시에 반영해 동일한 드리프트가 frontend `module_5` 오프라인 배지 작업으로 전파되는 것을 막아야 한다.

[backend_dev_cross_validator] 작업 결과를 파일로 남깁니다.
