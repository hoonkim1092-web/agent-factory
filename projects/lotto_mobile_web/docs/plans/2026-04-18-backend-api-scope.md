# 백엔드 API 범위·인터페이스 고정(Scope Contract)

- 작업: backend_dev_module_1_scope_1
- 모듈: 로또 추천 REST API 서버
- 담당 역할: Backend Dev
- 작성 시각: 2026-04-18
- 상태: draft (교차검증 대기)

## 1. 목표와 배경
- `lotto_predictor_v2`의 CLI 전용 추천 파이프라인을 모바일 웹에서 호출 가능한 HTTP 경계로 감싼다.
- 기존 패턴 분석 로직(`lotto.analytics.patterns.analyze_patterns`, `lotto.recommender.recommend_combinations`, `lotto.cache.store.LottoCacheStore`)을 **재구현하지 않고 import 방식으로 재사용**한다.
- 모바일 UX를 위해 응답은 JSON 전용, 상태 비저장(stateless), 질의 파라미터 범위 검증을 엄격히 수행한다.

## 2. 범위 경계
### 2.1 포함 (In-Scope)
- FastAPI 기반 REST 서버 엔트리포인트 (`server/app.py`).
- 엔드포인트 3종
  - `GET /api/health` — 가동 확인용 헬스 체크.
  - `GET /api/recommend` — 추천 조합 N개 반환 (핵심).
  - `GET /api/draws/latest` — 캐시 기준 최신 회차 요약(선택적, UI 헤더용).
- Pydantic v2 스키마(`server/schemas.py`) 및 예외 핸들러(`server/errors.py`).
- `lotto_predictor_v2.src` 모듈 재사용을 위한 경로 부트스트랩 모듈(`server/bootstrap.py`).
- 오프라인 폴백: `lotto.cli._load_offline`과 동일한 캐시 전용 경로 재사용(공개 API 없으면 `LottoCacheStore`를 직접 호출하는 얇은 래퍼 신설).
- 정적 자산 서빙 마운트 훅(`/static`) — 프론트엔드 작업자가 같은 서버에서 HTML/CSS/JS를 배포할 수 있게 한다(실제 파일은 Frontend Dev가 추가).
- 단위 테스트에 필요한 `create_app()` 팩토리 함수.

### 2.2 제외 (Out-of-Scope)
- 사용자 인증, 세션, 권한.
- 실 복권 구매 연동.
- 새로운 패턴 분석 알고리즘.
- WebSocket, SSE 등 실시간 스트리밍.
- 영구 저장소(DB) 도입 — 데이터는 기존 JSON 캐시와 인메모리 응답만 다룬다.
- 인프라(배포, CI, Docker) — 실행 명령만 문서화한다.

## 3. 인터페이스 정의 (API Contract)

### 3.1 공통 규칙
- 프로토콜: HTTPS 호환 HTTP/1.1, JSON UTF-8.
- 응답 시간 목표: 기본 파라미터(n=5, draws=500) 기준 P95 < 3초 (로컬 환경).
- 에러 응답 공통 스키마
  ```json
  {
    "error": {
      "code": "<string>",
      "message": "<string>",
      "details": { }
    }
  }
  ```
- 에러 코드 목록
  - `invalid_parameter` — 질의 파라미터 범위 위반 (HTTP 422).
  - `data_unavailable` — 온라인/오프라인 모두 회차 데이터가 없는 경우 (HTTP 503).
  - `internal_error` — 예기치 못한 내부 오류 (HTTP 500).

### 3.2 `GET /api/health`
- 응답: `200 OK`
- 바디
  ```json
  { "status": "ok", "version": "<semver>", "time": "<ISO8601>" }
  ```

### 3.3 `GET /api/recommend`
- 질의 파라미터
  | 이름 | 타입 | 기본값 | 범위/규칙 |
  |------|------|--------|-----------|
  | `n` | int | 5 | 1 ≤ n ≤ 10 |
  | `draws` | int | 500 | 100 ≤ draws ≤ 500 |
  | `offline` | bool | false | `true`면 네트워크 호출 금지, 캐시만 사용 |
- 성공 응답 `200 OK`
  ```json
  {
    "generated_at": "2026-04-18T10:00:00Z",
    "source": "api" ,
    "status": "success",
    "draws_used": 500,
    "latest_draw_no": 1170,
    "latest_draw_date": "2026-04-12",
    "combos": [
      {
        "numbers": [3, 12, 22, 27, 34, 41],
        "score": 123.4567,
        "odd_even_ratio": "3:3",
        "section_distribution": { "1-10": 1, "11-20": 1, "21-30": 2, "31-40": 1, "41-45": 1 }
      }
    ]
  }
  ```
- `source` 값 계약
  - `api` — 최신 회차를 네트워크에서 성공적으로 확보.
  - `cache` — 네트워크 실패 또는 `offline=true`로 캐시 기반 응답.
- `status` 값 계약
  - `success` — 온라인 경로 정상.
  - `degraded-success` — 오프라인 폴백 경로 정상.

### 3.4 `GET /api/draws/latest`
- 질의 파라미터: 없음.
- 성공 응답 `200 OK`
  ```json
  { "round": 1170, "numbers": [1,7,15,22,33,44], "bonus": 8, "fetched_at": "2026-04-18T10:00:00Z" }
  ```
- 캐시가 비어있으면 `503 data_unavailable`.

## 4. 데이터 모델 (Pydantic v2)
- `RecommendationQuery` — 쿼리 파라미터 DTO (FastAPI `Depends` 주입용).
  - `n: int`, `draws: int`, `offline: bool`
  - validator: `n` 범위, `draws` 범위.
- `RecommendationCombo`
  - `numbers: tuple[int, int, int, int, int, int]`
  - `score: float`
  - `odd_even_ratio: str` (예: `"3:3"`)
  - `section_distribution: dict[str, int]`
- `RecommendationResponse`
  - `generated_at: datetime`, `source: Literal["api","cache"]`, `status: Literal["success","degraded-success"]`
  - `draws_used: int`, `latest_draw_no: int | None`, `latest_draw_date: str | None`
  - `combos: list[RecommendationCombo]`
- `DrawCacheEntry`
  - `round: int`, `numbers: list[int]`, `bonus: int`, `fetched_at: datetime`
- `ErrorBody` / `ErrorEnvelope` — 공통 에러 구조.

## 5. 디렉터리 구조(산출물)
```
lotto_mobile_web/
├── server/
│   ├── __init__.py
│   ├── app.py            # FastAPI app factory (create_app)
│   ├── bootstrap.py      # lotto_predictor_v2 경로 주입
│   ├── dependencies.py   # 쿼리 DTO, 서비스 주입
│   ├── errors.py         # 예외 → 에러 응답 매핑
│   ├── schemas.py        # Pydantic 모델
│   └── services/
│       ├── __init__.py
│       ├── recommendation.py   # 추천 파이프라인 오케스트레이션
│       └── draw_cache.py       # LottoCacheStore 얇은 래퍼
├── tests/
│   └── server/              # QA Engineer 작업 영역 (범위 외)
├── requirements.txt         # fastapi, uvicorn, pydantic>=2, httpx
└── README.md                # 실행 방법 (후속 작업)
```

## 6. 의존성

### 6.1 외부 패키지
- `fastapi >= 0.110`
- `uvicorn[standard] >= 0.29`
- `pydantic >= 2.5`
- `httpx >= 0.27` (테스트 및 추후 확장)
- Python 3.11 (`lotto_predictor_v2` 대응)

### 6.2 내부 모듈 재사용 계약
- import 대상
  - `lotto.analytics.patterns.analyze_patterns`
  - `lotto.analytics.patterns.MAX_DRAWS`
  - `lotto.recommender.recommend_combinations`
  - `lotto.recommender.DEFAULT_COMBINATION_COUNT`
  - `lotto.cache.store.LottoCacheStore`
  - `lotto.collector.DrawResult` (타입 참조용)
- **절대 경로**: `projects/lotto_predictor_v2/src`를 `sys.path`에 부트스트랩. `server/bootstrap.py`가 담당하고, 환경 변수 `LOTTO_PREDICTOR_SRC`로 override 가능.
- 리스크: `lotto_predictor_v2` 내부 API가 바뀌면 import가 깨진다 → 서버 부팅 시 스모크 임포트로 즉시 감지한다.

### 6.3 역할 간 의존성
- **Frontend Dev**: API 응답 스키마(§3, §4)를 계약으로 사용. 정적 자산 마운트 경로(`/static`)는 동일 서버에서 제공 가능.
- **QA Engineer**: `create_app()` 팩토리로 `httpx.ASGITransport` + `TestClient`를 구성. 테스트 파일은 `tests/server/` 아래.

## 7. 동작 계약(비기능)
- **파라미터 검증**: 범위 위반 시 `422 invalid_parameter` 즉시 반환, 다운스트림 호출 없음.
- **오프라인 폴백**: `offline=true`이거나 온라인 경로 예외 발생 시 캐시 경로로 자동 전환하며 `source=cache`, `status=degraded-success`.
- **관측성**: 모든 요청에 `X-Request-ID`를 발급해 로그에 부착한다(uuid4 기반). 로그 메시지는 한국어.
- **캐시 안전성**: 캐시 데이터가 없으면 `503 data_unavailable`로 명확히 실패.
- **CORS**: 개발 편의를 위해 기본 `*` 허용 + 환경 변수 `LOTTO_CORS_ORIGINS`로 제한 가능.
- **타임아웃**: 외부 호출 기본 5초 (lotto_predictor_v2 내부 설정 사용).

## 8. 구현 순서(Fixed)
동일 작업자가 PR 1개로 진행하지 않고, [scope → build → verify] 세 작업으로 분해한다. 본 문서는 scope 단계이며 아래 순서는 **build 단계의 실행 순서**이다.

1. `server/bootstrap.py` — `sys.path` 부트스트랩 + import 스모크 테스트 헬퍼.
2. `server/schemas.py` — Pydantic 모델 5종.
3. `server/errors.py` — 공통 에러 스키마, 예외 → HTTP 매핑.
4. `server/services/draw_cache.py` — 캐시 로드/최신 회차 조회 래퍼.
5. `server/services/recommendation.py` — 온라인·오프라인 경로 오케스트레이션.
6. `server/dependencies.py` — `RecommendationQuery` DTO, 서비스 DI.
7. `server/app.py` — `create_app()` + 라우터 등록 + CORS + 요청 ID 미들웨어.
8. `requirements.txt` 갱신.
9. `python -m uvicorn server.app:create_app --factory` 수동 기동 스모크.
10. `docs/architecture.md` 최종 반영, `docs/change_history.md` append.

## 9. 완료 기준(이 scope 작업)
- [x] 로또 추천 REST API 서버 범위(포함/제외)가 §2에 명시된다.
- [x] 의존성(§6)과 산출물 디렉터리(§5)가 명시된다.
- [x] 엔드포인트·스키마·에러 코드가 §3, §4에 고정된다.
- [x] build 단계의 구현 순서(§8)가 고정된다.
- [x] `docs/architecture.md`와 `docs/change_history.md`가 같은 작업에서 갱신된다.

## 10. 리스크와 대안
- **R1. lotto_predictor_v2 import 실패** — 대안: 부트스트랩 모듈에서 시작 시 임포트 스모크 실행, 실패 시 명확한 예외 메시지 + 프로세스 종료.
- **R2. 온라인 수집 타임아웃으로 모바일 UX 악화** — 대안: 온라인 경로 실패 시 즉시 캐시 폴백, 클라이언트는 `source` 필드로 뱃지 표시.
- **R3. 캐시가 비어있는 신규 배포 환경** — 대안: `/api/draws/latest`가 503으로 실패할 수 있음. README에 초기 1회 CLI 실행으로 캐시를 채우라고 명시(후속 build 단계에서 작성).
- **R4. 검증 회차 분포 변화로 응답 지연** — 대안: `draws=500` 기본 유지하되 클라이언트가 100~500 사이로 조절 가능.

## 11. 다음 단계 (Handoff Preview)
- backend_dev_module_1_build_1: §8 구현 순서대로 빌드.
- backend_dev_module_1_verify_1: 수동 스모크 + 핵심 흐름 로그 샘플 + 후속 QA 인수인계.
- 프론트엔드/QA 합류 지점: 본 문서 §3~§4가 공용 계약. 계약 변경 시 본 문서를 먼저 업데이트한다.
