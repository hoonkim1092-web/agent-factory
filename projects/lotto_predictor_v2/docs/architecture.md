# 아키텍처

이 문서는 현재 아키텍처와 워크플로를 설명하는 살아 있는 기준 문서다.
설계, 워크플로, 인터페이스, 데이터 흐름, 구현 전략이 바뀌면 같은 작업 안에서 갱신한다.

## 메타데이터
- 마지막 업데이트: 2026-04-17T04:17:00
- 상태: active
- 문서 언어: 한국어 (OS: `ko-KR`)

## 현재 설계
- 요약:
  - QA Engineer는 각 역할 산출물을 통합 관점에서 검증하며, 핵심 플로우와 회귀 시나리오를 분리된 단계로 관리한다.
- 핵심 구성 요소:
  - 검증 대상 입력: Backend Dev, Frontend Dev, Game Logic Dev가 생성한 모듈 진입점, 문서, 빌드 산출물
  - QA 시나리오 집합: smoke, regression, failure-path, artifact-check
  - QA 산출물: 검증 실행 기록, 실패 목록, `verification-report.md`, handoff 메모
  - QA 템플릿 경로: `artifacts/qa_engineer/core-flow-checklist.md`, `artifacts/qa_engineer/regression-scenarios.md`, `artifacts/qa_engineer/verification-report-template.md`, `artifacts/qa_engineer/execution-log-template.md`, `artifacts/qa_engineer/handoff-template.md`
- 데이터 흐름:
  - 각 역할이 build 단계 산출물을 확정한다.
  - QA Engineer가 고정된 입력 인터페이스로 산출물을 수집한다.
  - smoke 시나리오로 전체 연결성을 먼저 확인한다.
  - regression/failure-path 시나리오로 재현성과 예외 처리를 검증한다.
  - verify 단계에서 결과를 `verification-report.md`와 handoff 메모로 정리한다.
- 제약 사항:
  - QA Engineer build 단계는 `qa_engineer_module_10_scope_1`에서 정의한 인터페이스와 순서를 변경하지 않는다.
  - 검증 순서는 수집기/캐시 -> 분석 엔진 -> 추천기 -> 리포트 -> 빌드 산출물 -> 사용자 가이드 -> 교차 통합 검증 순으로 고정한다.
  - 모든 문서형 산출물은 한국어로 기록한다.
  - build 단계는 실행 결과 자체를 확정하지 않고, verify 단계에서 재사용할 체크리스트/회귀 목록/기록 템플릿을 먼저 고정한다.
- 열린 질문:
  - mailbox 프로토콜 도구가 없는 런타임에서 교차검증 요청을 어떤 대체 채널로 남길지 확정이 필요하다.

## QA 검증 산출물 구조
- `artifacts/qa_engineer/core-flow-checklist.md`
  - 핵심 플로우 smoke 및 artifact-check 합격 기준
- `artifacts/qa_engineer/regression-scenarios.md`
  - 회귀 및 실패 시나리오 정의
- `artifacts/qa_engineer/verification-report-template.md`
  - verify 단계 최종 결과 문서 템플릿
- `artifacts/qa_engineer/execution-log-template.md`
  - 실행 로그 기록 템플릿
- `artifacts/qa_engineer/handoff-template.md`
  - handoff 메시지 구조 템플릿

## Game Logic Dev 구현 계약
### 설계 요약
- `Game Logic Dev`는 추천 조합 생성의 핵심 규칙과 상태 전이를 담당하는 순수 도메인 계층이다.
- 이 역할은 네트워크 호출, 로컬 저장, 출력 렌더링을 수행하지 않고, 정규화된 입력을 받아 결정적 결과를 반환한다.

### 구현 범위
- 담당 범위:
  - 추천 요청 입력 검증
  - 후보 번호 조합 생성
  - 규칙 필터 적용과 상태 전이 관리
  - 후보 점수화, 정렬, 상위 조합 선택
  - 추천 결과와 실패 사유 계약 반환
- 제외 범위:
  - 동행복권 API 호출
  - 회차 데이터 저장 및 캐시 갱신
  - CLI 출력 렌더링
  - PyInstaller 패키징

### 입력 인터페이스
```text
RecommendationRequest
- draw_history: LottoDraw[]
- statistics_summary: StatisticsSummary
- config: RecommendationConfig
```

### 출력 인터페이스
```text
RecommendationEngine.generate(request: RecommendationRequest) -> RecommendationBatch

RecommendationBatch
- recommendations: RecommendationResult[]
- rejected_candidates: RejectionReasonSummary[]
- evaluation_summary: EvaluationSummary
```

### 오류 인터페이스
- `InvalidRequestError`: 필수 필드 누락, 숫자 범위 오류, 회차 이력 비어 있음
- `RuleConflictError`: 규칙 조합이 상호 충돌하여 유효 후보를 만들 수 없음
- `InsufficientCandidateError`: 필터 통과 후보가 목표 개수보다 부족함

### 내부 상태 전이
- 상태 흐름: `초기화 -> 생성 -> 규칙 검증 -> 점수화 -> 정렬 -> 최종 선택`
- 각 후보는 한 단계씩만 전이하며, 탈락 시 `rejected_candidates`에 사유를 기록한다.
- 동일 입력에 대해 동일 결과를 반환하도록 난수 의존 동작을 허용하지 않는다.

### 의존성
- 선행 의존성:
  - 회차 이력 정규화 결과
  - 통계 분석 요약 결과
  - 추천 설정 기본값 계약
- 후행 소비자:
  - 추천 결과 출력 계층
  - QA 검증 시나리오

### 산출물
- 범위 문서와 인터페이스 계약
- 상태 전이 기준과 구현 순서
- build 단계에서 구현할 엔진/도메인 타입 명세
- verify 단계에서 사용할 실패 사유 분류 기준

### 구현 순서
1. `RecommendationRequest`, `RecommendationConfig`, `RecommendationResult` 타입 정의
2. 입력 검증과 오류 계약 구현
3. 후보 생성 규칙과 상태 전이 구조 구현
4. 필터 규칙 적용 순서 구현
5. 점수화, 정렬, 최종 선택 구현
6. 결과 요약과 handoff용 메타데이터 정리

## 통계 분석 엔진 패턴 규칙 계약
### 설계 요약
- 통계 분석 엔진의 패턴 규칙 모듈은 최근 최대 500회차 당첨번호를 입력받아 추천기와 리포트가 공통으로 소비할 수 있는 순수 함수 결과를 반환한다.
- 네트워크, 저장소, 출력 렌더링과 분리된 계산 계층으로 유지한다.
- Frontend Dev `module_3` 는 캐시(`LottoDrawCache`)의 읽기 계약만 사용하며, 수집기/저장소의 세부 구현을 직접 호출하지 않는다.

### 구현 범위
- 담당 범위:
  - 번호 빈도 계산
  - 번호별 연속 등장 간격 계산
  - 회차별 홀짝 비율 집계
  - 구간 분포(1-10, 11-20, 21-30, 31-40, 41-45) 집계
  - 최근 회차 우선 트렌드 가중치 계산
  - 공통 입력 검증과 예외 반환
- 제외 범위:
  - 회차 수집 및 저장
  - 추천 후보 생성
  - 화면 렌더링과 사용자 메시지 포매팅

### 공개 인터페이스
```text
calculate_number_frequency(draws) -> dict[int, int]
calculate_consecutive_gaps(draws) -> dict[int, dict[str, object]]
calculate_odd_even_ratio(draws) -> dict[str, object]
calculate_section_distribution(draws) -> dict[str, int]
calculate_trend_weights(draws) -> dict[int, float]
analyze_patterns(draws) -> PatternStats
build_pattern_stats_from_cache(cache, draw_limit=500) -> PatternStats
summarize_analysis_run(stats, source_draw_count, latest_draw_no) -> AnalysisRunSummary
```

### 입력 계약
- `draws`는 최근 회차부터 과거 회차 순으로 정렬된 길이 1 이상 500 이하의 시퀀스여야 한다.
- 각 항목은 길이 6의 정수 시퀀스이거나 `numbers` 속성을 가진 객체여야 한다.
- 모든 번호는 `1..45` 범위의 중복 없는 정수여야 한다.
- `build_pattern_stats_from_cache()` 는 `LottoDrawCache.get_recent_draws(500)` 를 기본 입력으로 사용하며, cache 계층 공개 API 외 직접 의존을 허용하지 않는다.

### 출력 계약
- 빈도: `1..45` 전체 번호를 항상 포함한다.
- 연속 등장 간격: 번호별 `gaps`, `average_gap`, `last_gap`, `appearance_count`를 반환한다.
- 홀짝 비율: `ratio_counts`, `dominant_ratio`, `dominant_count`, 평균 홀수/짝수 개수를 반환한다.
- 구간 분포: `1-10`, `11-20`, `21-30`, `31-40`, `41-45` 키를 고정 반환한다.
- 트렌드 가중치: 최신 회차일수록 더 큰 선형 가중치를 반영한 번호별 점수를 반환한다.
- `AnalysisRunSummary` 는 `source_draw_count`, `latest_draw_no`, `oldest_draw_no`, `dominant_ratio`, `top_frequency_numbers`, `generated_at` 을 포함한다.

### 오류 계약
- `TypeError`: 입력이 시퀀스가 아니거나 번호가 정수가 아닐 때
- `ValueError`: 회차 목록이 비었거나 500건을 초과할 때, 번호 개수/범위/중복이 잘못됐을 때

### 의존성
- 선행 의존성:
  - `frontend_dev_module_2` 의 `LottoDrawCache.get_recent_draws(n)` 공개 계약
  - Backend Dev `LottoDraw.draw_no`, `LottoDraw.numbers`
- 후행 소비자:
  - 추천기 `PatternStats` 직접 소비 계층
  - 리포트/시각화 계층
  - QA 단위 테스트

### 구현 순서
1. `PatternStats`, `AnalysisRunSummary` 출력 계약 확정
2. 입력 검증 및 회차 정규화 헬퍼 구현
3. 5개 통계 계산 함수 구현
4. `analyze_patterns()` 조립
5. `build_pattern_stats_from_cache()` 캐시 어댑터 구현
6. `summarize_analysis_run()` 및 통합 테스트 골격 정리

## 패턴 기반 추천기 계약
### 설계 요약
- `src/lotto/recommender.py`는 `PatternStats`를 직접 입력받아 결정적 조합 추천을 수행하는 순수 추천 계층이다.
- 추천 결과는 빈도 상위 70% 번호 풀, 홀짝 비율, 구간 균형, 최근 트렌드 가중치를 기준으로 필터링 및 정렬된다.

### 공개 인터페이스
```text
recommend_combinations(stats: PatternStats, n_combinations: int = 5) -> list[Combination]
```

### 입력 계약
- `stats`는 `number_frequency`, `consecutive_gaps`, `odd_even_ratio`, `section_distribution`, `trend_weights`를 모두 포함한 `PatternStats`여야 한다.
- `n_combinations`는 1 이상의 정수다.

### 출력 계약
- `Combination.numbers`: 오름차순 6개 번호 튜플
- `Combination.score`: 가중치 기반 최종 점수
- `Combination.odd_even_ratio`: `홀수:짝수`
- `Combination.section_distribution`: 조합 내부 구간별 개수

### 제약 규칙
- 후보 번호는 빈도 상위 70% 번호 풀에서만 선택한다.
- 홀짝 비율은 `3:3`, `4:2`, `2:4`만 허용한다.
- 구간 분포는 최소 4개 구간을 사용하고, 어떤 구간도 2개를 넘지 않는다.
- 최근 트렌드 가중치는 최종 스코어에 반영한다.

### 스코어링 규칙
- 기본 점수: 번호 빈도 합 + 트렌드 가중치 합 + 연속 등장 간격 보정치
- 패널티/보너스: 구간 불균형 패널티, `3:3` 비율 보너스

### 제약 사항
- 추천기는 무작위 추출을 사용하지 않고 전체 후보 열거 후 정렬한다.
- 후보 풀이 45개 전체로 늘어나면 계산량이 커지므로 상위 70% 제한을 유지한다.

## Backend Dev 구현 계약 (module_8)
### 설계 요약
- Backend Dev는 **서버·데이터·외부 연동**을 담당하는 저수준 어댑터 계층이다.
- Frontend Dev(수집기·캐시·통계·추천·리포트) 등 상위 모듈이 본 계층을 import 하여 사용한다.
- 비즈니스 규칙이나 출력 렌더링은 포함하지 않는다.

### 구현 범위
- 담당 범위:
  - 동행복권 HTTP 클라이언트(재시도, 타임아웃, rate limit 대응)
  - SQLite 영속 계층(스키마 DDL, 트랜잭션, 회차/체크포인트/빈도 I/O)
  - 도메인 데이터 타입(`LottoDraw`, `FetchCheckpoint`, `NumberFrequencyRow`, 예외 타입)
  - 외부 JSON → 도메인 타입 직렬화
- 제외 범위:
  - 증분 수집 오케스트레이션(Frontend Dev 수집기)
  - 캐시 조회/업서트 비즈니스 규칙(Frontend Dev 캐시)
  - 통계·추천·리포트·빌드·가이드(Frontend Dev)
  - 번호 규칙 검증(Game Logic Dev)
  - 테스트 시나리오(QA Engineer)

### 공개 인터페이스
```text
DhLotteryClient.fetch_draw(draw_no: int) -> FetchResult
LottoStorage.ensure_schema() -> None
LottoStorage.upsert_draws(draws: Iterable[LottoDraw]) -> int
LottoStorage.get_draws(*, limit=None, since_no=None) -> list[LottoDraw]
LottoStorage.get_draw(draw_no: int) -> LottoDraw | None
LottoStorage.get_checkpoint() -> FetchCheckpoint | None
LottoStorage.set_checkpoint(cp: FetchCheckpoint) -> None
LottoStorage.write_number_frequency(rows) -> None
LottoStorage.read_number_frequency() -> list[NumberFrequencyRow]
parse_draw(payload: dict) -> LottoDraw
```

### 오류 인터페이스
- `DrawNotFoundError`: API `returnValue != "success"` 또는 존재하지 않는 회차
- `TransientFetchError`: 재시도 후에도 네트워크·서버 일시 오류 지속
- `ValueError`: 스키마 불일치로 도메인 타입 매핑 실패

### 의존성
- 선행 의존성: 외부 `requests` 라이브러리, Python stdlib `sqlite3`
- 후행 소비자: Frontend Dev 수집기/캐시/통계 모듈, Game Logic Dev(도메인 타입만)

### 산출물
- `src/lotto_predictor/backend/__init__.py`
- `src/lotto_predictor/backend/http_client.py`
- `src/lotto_predictor/backend/storage.py`, `schema.sql`
- `src/lotto_predictor/backend/models.py`
- `src/lotto_predictor/backend/serialization.py`
- `docs/work-items/한국-로또-.../backend-dev-scope.md`

### 구현 순서 (고정)
1. `models.py` — 도메인 타입 확정
2. `schema.sql` + `storage.py` 최소 골격(`ensure_schema`, 컨텍스트 매니저)
3. `serialization.py` — `parse_draw`
4. `http_client.py` — `DhLotteryClient.fetch_draw` (재시도 포함)
5. `storage.py` 나머지 I/O 메서드
6. `__init__.py` 공개 심볼 정리

### 구현 상태 (2026-04-17T02:05:00, backend_dev_module_8_build_2)
- `models.py`, `schema.sql`, `storage.py`, `serialization.py`, `http_client.py`, `__init__.py` 초안을 확정해 scope 단계 계약을 그대로 구현했다.
- `LottoStorage`는 WAL 모드 + `BEGIN IMMEDIATE` 트랜잭션 경계, `executescript` 자체 트랜잭션 존중, `upsert/set_checkpoint/write_number_frequency` 치환 전략을 적용했다.
- `DhLotteryClient`는 `min_interval` 기반 rate limit, 408/429/5xx 재시도, 지수 백오프, User-Agent 헤더 설정을 포함한다.
- `parse_draw`는 본 번호를 오름차순으로 정렬한 뒤 `LottoDraw` 불변식을 거쳐 반환한다.
- 스모크 검증: py_compile, LottoStorage CRUD·checkpoint·frequency round-trip, `DhLotteryClient` 정상/`DrawNotFoundError`/`TransientFetchError`/`ValueError` 경로.
- 후속 소비자(Frontend Dev 수집기/캐시) build 가능 상태.

## Frontend Dev 동행복권 회차 수집기 계약 (module_1)
### 설계 요약
- Frontend Dev의 `frontend_dev_module_1`은 Backend Dev `DhLotteryClient`/`LottoStorage` 위에 얹는 **증분 수집 오케스트레이션 계층**이다.
- HTTP 세션과 SQLite 연결은 Backend Dev 계층에 위임하고, 본 모듈은 루프/체크포인트/부분 성공 집계에만 집중한다.
- 상세 설계는 `docs/plans/2026-04-17-dhlottery-회차-수집기-범위.md` 참조.

### 구현 범위
- 담당 범위:
  - `LottoStorage.get_checkpoint()`로 시작점을 읽어 누락 회차 증분 수집
  - 최신 회차 탐색(`DrawNotFoundError`를 만날 때까지 전진)
  - 명시적 범위 수집(`sync_range`) — 백필용
  - 호출 간 최소 간격(`min_interval_s`) 보장과 연속 실패 중단 규칙 적용
  - 성공 회차의 `upsert_draws` + `set_checkpoint` 위임 저장
- 제외 범위:
  - 단일 회차 HTTP 호출 자체(Backend Dev)
  - 응답 스키마 파싱(Backend Dev `parse_draw`)
  - SQLite DDL/연결 관리(Backend Dev)
  - 통계·추천·리포트·빌드·가이드(Frontend Dev 타 모듈)
  - 번호 규칙 검증(Game Logic Dev)

### 공개 인터페이스
```text
CollectorConfig(min_interval_s=0.2, max_probe=20, target_draw_no=None, abort_on_consecutive_failures=3)

LottoCollector(client: DhLotteryClient, storage: LottoStorage, config: CollectorConfig, logger=None)
  .detect_latest_draw_no(probe_start: int) -> int
  .sync_incremental() -> SyncResult
  .sync_range(start: int, end: int) -> SyncResult

SyncResult
- fetched: list[LottoDraw]
- failures: list[FetchFailure]
- last_fetched_drw_no: int | None
- stopped_reason: Literal["caught_up", "not_yet_drawn", "aborted", "target_reached"]

FetchFailure
- draw_no: int
- reason: Literal["not_yet_drawn", "transient", "rate_limited", "unknown"]
- detail: str
```

### 오류 인터페이스
- Backend Dev의 `DrawNotFoundError` → `FetchFailure(reason="not_yet_drawn")` 또는 `stopped_reason="not_yet_drawn"`.
- Backend Dev의 `TransientFetchError` → `FetchFailure(reason="transient")`.
- 연속 실패 임계 초과 시 `SyncResult.stopped_reason="aborted"`로 즉시 중단.
- 저장소 예외는 수집기에서 잡지 않고 호출자에게 전파.

### 의존성
- 선행 의존성:
  - Backend Dev `DhLotteryClient.fetch_draw`
  - Backend Dev `LottoStorage` (`get_checkpoint`, `upsert_draws`, `set_checkpoint`)
  - Backend Dev 도메인 타입 `LottoDraw`, `FetchCheckpoint`, `DrawNotFoundError`, `TransientFetchError`
- 후행 소비자:
  - 회차 데이터 로컬 캐시 저장소(`frontend_dev_module_2`) — 수집기 결과 소비
  - 통계 분석/추천/리포트 모듈 — 캐시를 통한 간접 소비
  - QA Engineer 검증 시나리오

### 산출물
- `src/lotto_predictor/collector/__init__.py`
- `src/lotto_predictor/collector/models.py` — `CollectorConfig`, `FetchFailure`, `SyncResult`
- `src/lotto_predictor/collector/core.py` — `LottoCollector`
- `tests/collector/test_collector_sync.py`, `test_collector_detect.py`, `test_collector_failures.py`
- `docs/plans/2026-04-17-dhlottery-회차-수집기-범위.md`

### 구현 순서 (고정)
1. `models.py` — 데이터 계약 확정
2. `core.py`의 `LottoCollector.__init__`과 rate limit 헬퍼
3. `detect_latest_draw_no` 구현과 단위 테스트
4. `sync_range` 구현(부분 성공, 연속 실패 중단)
5. `sync_incremental` 구현(체크포인트 연동, 최신 회차 탐색, 저장소 위임)
6. `__init__.py` 공개 심볼 정리
7. Backend Dev build 완료 후 실제 클라이언트와의 통합 점검(QA 단계)

### 구현 상태 (2026-04-17T02:10:00, frontend_dev_module_1_build_2)
- `src/lotto_predictor/collector/models.py` — `CollectorConfig`, `FetchFailure`, `SyncResult` 계약 확정(필드 검증 포함).
- `src/lotto_predictor/collector/core.py` — `LottoCollector` 구현. 내부에 `_fetch_one`(예외→`FetchFailure` 사유 정규화), `_sleep_between_calls`(단조시계 기반 rate limit), `_persist_draw`, `_update_checkpoint` 헬퍼 포함. 회차 파싱은 `backend.parse_draw` 에 위임.
- `detect_latest_draw_no`: probe_start 에서 전진 탐색, 첫 probe 미발표 시 `probe_start - 1` 반환, 일시 실패는 `TransientFetchError` 로 전파, `max_probe` 한도 존중.
- `sync_range`: 성공 시 즉시 `upsert_draws`, 미발표/알 수 없음은 `FetchFailure` 기록 후 진행, 일시/rate_limited 연속 실패가 `abort_on_consecutive_failures` 이상이면 `stopped_reason="aborted"`, 마지막 성공 회차만 체크포인트 갱신.
- `sync_incremental`: 체크포인트 다음 회차부터 시작, 타겟 미지정 시 `detect_latest_draw_no` 로 상한 확정, 타겟 전 미발표는 `stopped_reason="not_yet_drawn"`, 명시 타겟 달성 시 `target_reached`, 탐색 단계 일시 실패는 체크포인트를 건드리지 않고 `aborted` 반환.
- `src/lotto_predictor/collector/__init__.py` — 공개 심볼(`LottoCollector`, `DrawFetcher`, `CollectorConfig`, `SyncResult`, `FetchFailure`, `FailureReason`, `StoppedReason`) 재노출.
- 단위 테스트: `tests/collector/test_collector_sync.py`(증분/범위 수집 8케이스), `test_collector_detect.py`(최신 회차 탐색 7케이스), `test_collector_failures.py`(연속 실패 중단/미지원 예외 4케이스) — 총 19개, `pytest` 로 전 건 통과.
- 후행 소비자(`frontend_dev_module_2` 회차 캐시) build 가능 상태.

## Frontend Dev 회차 데이터 로컬 캐시 저장소 계약 (module_2)
### 설계 요약
- Frontend Dev의 `frontend_dev_module_2`는 Backend Dev `LottoStorage`(저수준 CRUD)와 Frontend Dev `LottoCollector`(증분 수집) 위에 얹는 **캐시 정책 계층**이다.
- 도메인 수준 신선도 판정, 부족 시 수집기 위임 호출, 도메인 읽기 API, 연속성 검증의 네 가지 책임만 담당한다.
- SQL 발행, HTTP 호출, 증분 루프 구현은 하위 계층에 위임하고, 캐시 계층은 정책과 조합 결과만 제공한다.
- 상세 설계는 `docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md` 참조.

### 구현 범위
- 담당 범위:
  - 캐시 상태 요약(`CacheStatus`): 보유 회차 수, 최신/최초 회차, 마지막 수집 시각, `is_stale`, `stale_reasons`.
  - 신선도 판정 정책: `required_draws`, `freshness_hours`, `refresh_policy`, `offline`.
  - `ensure_ready` 플로우: 상태 조회 → 필요 시 `LottoCollector.sync_incremental` 호출 → 결과 요약.
  - 도메인 읽기 API: `get_recent_draws(n)`, `get_all_draws()`, `get_draw(draw_no)`.
  - 연속성 검증(`validate_continuity`): 누락 회차 목록과 `is_continuous` 플래그.
- 제외 범위:
  - SQLite 연결·DDL·트랜잭션(Backend Dev).
  - HTTP 호출과 재시도(Backend Dev).
  - 증분 수집 루프·rate limit(Frontend Dev 수집기 module_1).
  - 통계·추천·리포트·빌드·가이드(상위 Frontend Dev 모듈).
  - 번호 규칙 검증(Game Logic Dev).

### 공개 인터페이스
```text
CacheConfig(
    required_draws=500,
    freshness_hours=24.0,
    refresh_policy="auto",  # "auto" | "never"
    offline=False,
)

CacheStatus
- total_draws: int
- latest_drw_no: int | None
- earliest_drw_no: int | None
- last_fetched_at: datetime | None
- is_stale: bool
- stale_reasons: list["missing_checkpoint" | "insufficient_draws" | "expired_checkpoint" | "unknown"]

CacheReadyResult
- status: CacheStatus
- sync_result: SyncResult | None
- action: "skipped" | "synced" | "offline"

CacheGapReport
- expected_range: tuple[int, int] | None
- missing_draws: list[int]
- is_continuous: bool

LottoDrawCache(
    storage: LottoStorage,
    collector: LottoCollector | None = None,
    config: CacheConfig = CacheConfig(),
    clock: Callable[[], datetime] = datetime.now,
    logger: Logger | None = None,
)
  .status() -> CacheStatus
  .ensure_ready() -> CacheReadyResult
  .get_recent_draws(n: int) -> list[LottoDraw]
  .get_all_draws() -> list[LottoDraw]
  .get_draw(draw_no: int) -> LottoDraw | None
  .validate_continuity() -> CacheGapReport
```

### 오류 인터페이스
- `get_recent_draws(n<=0)` → `ValueError`.
- `LottoStorage`가 발생시키는 예외는 캐시에서 잡지 않고 호출자에게 전파.
- 수집 실패는 예외가 아닌 `CacheReadyResult.sync_result.stopped_reason`/`failures`로 보존.

### 의존성
- 선행 의존:
  - Backend Dev: `LottoStorage`, `LottoDraw`, `FetchCheckpoint`.
  - Frontend Dev 수집기(module_1): `LottoCollector`, `SyncResult`.
  - Python stdlib: `dataclasses`, `typing`, `datetime`, `logging`.
- 후행 소비자:
  - 통계 분석 엔진(`frontend_dev_module_3`), 추천기(`frontend_dev_module_4`), 리포트(`frontend_dev_module_5`).
  - QA Engineer 회귀 시나리오.

### 산출물
- `src/lotto_predictor/cache/__init__.py`
- `src/lotto_predictor/cache/models.py`
- `src/lotto_predictor/cache/core.py`
- `tests/cache/test_cache_status.py`, `test_cache_ensure_ready.py`, `test_cache_reads.py`, `test_cache_continuity.py`
- `docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md`

### 구현 순서 (고정)
1. `models.py` — `CacheConfig`, `CacheStatus`, `CacheReadyResult`, `CacheGapReport` 확정.
2. `core.py` — `LottoDrawCache.__init__`과 내부 헬퍼(`_load_checkpoint`, `_compute_status`).
3. `status()` 구현과 단위 테스트.
4. `ensure_ready()` 구현(수집기 유무·`offline`·`refresh_policy` 분기)과 단위 테스트.
5. 읽기 API(`get_recent_draws`, `get_all_draws`, `get_draw`) 구현과 단위 테스트.
6. `validate_continuity()` 구현과 누락 회차 테스트.
7. `__init__.py` 공개 심볼 정리.

### 구현 상태 (2026-04-17T03:10:00, frontend_dev_module_2_build_2)
- `src/lotto_predictor/cache/models.py` — `CacheConfig`(필드 검증, `refresh_policy` 리터럴 제한), `CacheStatus`(`is_stale`/`stale_reasons` 정합성 검증), `CacheReadyResult`(`action` vs `sync_result` 정합성 검증), `CacheGapReport`(`expected_range` 범위 검증, `missing_draws` 오름차순/중복 불변식) 계약 확정.
- `src/lotto_predictor/cache/core.py` — `LottoDrawCache` 구현. 내부 헬퍼 `_compute_status`(체크포인트·회차 개수 기반 `stale_reasons` 조립), `_is_checkpoint_expired`(`freshness_hours` 이하는 만료 판정 생략). SQL 을 직접 발행하지 않고 `LottoStorage.get_draws`·`get_draw`·`get_checkpoint` 만 호출.
- `status()`: 빈 저장소는 `missing_checkpoint`+`insufficient_draws`, 부족 회차는 `insufficient_draws`, 경과 체크포인트는 `expired_checkpoint`. `freshness_hours=0` 이면 만료 판정을 건너뛰도록 정책 고정.
- `ensure_ready()`: `offline=True` 또는 `collector` 미주입이면 `action="offline"`, `refresh_policy="never"` 이면 `action="skipped"`, 신선하면 수집 생략(`"skipped"`), 그 외에는 `LottoCollector.sync_incremental()` 호출 후 상태 재조회(`"synced"`). 수집 중단/실패도 예외로 올리지 않고 `sync_result` 에 보존.
- 읽기 API: `get_recent_draws(n)`는 내림차순 상위 n개(`n<=0` 은 `ValueError`), `get_all_draws()` 는 저장소 반환을 뒤집어 오름차순, `get_draw(draw_no)` 는 존재 시 도메인 객체 반환·없으면 `None`.
- `validate_continuity()`: 빈 저장소는 `expected_range=None`+`is_continuous=True`, 그 외에는 `[earliest..latest]` 구간에서 누락 회차를 오름차순으로 보고.
- `src/lotto_predictor/cache/__init__.py` — 공개 심볼(`LottoDrawCache`, `CacheConfig`, `CacheStatus`, `CacheReadyResult`, `CacheGapReport`, `StaleReason`, `RefreshPolicy`, `CacheAction`) 재노출.
- 단위 테스트: `tests/cache/test_cache_status.py`(9케이스), `test_cache_ensure_ready.py`(6케이스), `test_cache_reads.py`(7케이스), `test_cache_continuity.py`(5케이스) — 총 27건 `pytest` 전 건 통과. 공용 fake 는 `tests/cache/_fakes.py` 에 분리.
- 후행 소비자(통계 분석 엔진 `frontend_dev_module_3`) build 가능 상태.

## 문서 규칙
- 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다.
- 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다.
- 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다.
- 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
