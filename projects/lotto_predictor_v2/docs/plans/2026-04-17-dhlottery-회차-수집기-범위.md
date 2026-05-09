# 동행복권 회차 수집기 모듈 범위 설계

## 메타데이터
- 작성일: 2026-04-17
- 관련 task_id: `frontend_dev_module_1_scope_1`
- 담당 역할: frontend_dev
- 모듈 식별자: `frontend_dev_module_1` (동행복권 회차 수집기 모듈)
- 상태: review_pending

## 설계 의도
- 동행복권 회차 조회를 **오케스트레이션 계층**으로 래핑해 500회차 이상의 회차 데이터를 안정적으로 가져온다.
- Backend Dev 구현(`backend_dev_module_8`)이 제공하는 저수준 어댑터(`DhLotteryClient.fetch_draw`, `LottoStorage`, 도메인 타입)를 **재사용**한다. 수집기는 HTTP 세션을 직접 구성하지 않는다.
- 회차 데이터 로컬 캐시 저장소(`frontend_dev_module_2`)가 소비할 증분 수집 결과 계약을 먼저 고정한다.
- 통계 분석 엔진(`frontend_dev_module_3`)과 추천기(`frontend_dev_module_4`)는 캐시를 통해 간접 의존하므로, 수집기는 조회/오케스트레이션/결과 집계 책임만 진다.
- 구현 순서를 미리 고정해 이후 build 단계에서 파일 경계와 테스트 범위가 흔들리지 않게 한다.

## 영향 범위
- `docs/architecture.md`: 수집기 모듈의 경계와 인터페이스, 데이터 흐름 보강.
- `docs/change_history.md`: 본 설계 변경 이력 추가.
- `src/lotto_predictor/collector/` 하위 신규 파일 계획(실제 생성은 build 단계에서 수행).

## 역할 경계 (Backend Dev와의 분리)
- Backend Dev(`backend_dev_module_8`)의 책임
  - `DhLotteryClient.fetch_draw(draw_no) -> FetchResult` — 단일 회차 조회, HTTP 재시도/타임아웃.
  - `LottoStorage` — SQLite 영속 계층.
  - 도메인 타입 `LottoDraw`, `FetchCheckpoint`, `DrawNotFoundError`, `TransientFetchError`.
  - 응답 파싱 `parse_draw(payload) -> LottoDraw`.
- Frontend Dev 수집기(`frontend_dev_module_1`)의 책임
  - Backend Dev의 `DhLotteryClient`를 입력받아 범위/증분 수집 루프를 수행.
  - 최신 회차 탐색(`DrawNotFoundError`를 만날 때까지 전진).
  - 호출 간 최소 간격 보장(`min_interval_s`)과 과도 요청 보호.
  - `LottoStorage.get_checkpoint()`로 시작점을 읽고, 결과를 `upsert_draws` + `set_checkpoint`로 위임.
  - 부분 성공과 실패를 집계한 `SyncResult` 반환.

## 모듈 범위
### 포함
- 증분 동기화: `LottoStorage.get_checkpoint()`의 `last_fetched_drwNo`를 입력으로 받아 누락 구간만 조회하고, 결과를 저장소에 위임 저장.
- 범위 조회: `start_draw_no`~`end_draw_no`를 순차 호출하며 `DhLotteryClient.fetch_draw`를 호출.
- 최신 회차 탐색: 기준 회차에서 시작해 `DrawNotFoundError`를 만날 때까지 전진.
- Rate limit 보호: 호출 간 최소 간격(`min_interval_s`)을 강제.
- 실패 집계: 일시적/영구적 실패를 분리해 `SyncResult.failures`로 노출.
- 캐시 체크포인트 갱신: 최종 성공 회차를 `FetchCheckpoint`에 기록.

### 제외
- 단일 회차 HTTP 호출 자체(= Backend Dev 책임).
- SQLite 연결 관리와 DDL(= Backend Dev 책임).
- 응답 스키마 파싱(= Backend Dev의 `parse_draw`).
- 통계 계산, 추천, 리포트 출력(다른 모듈 책임).
- GUI, 웹 서버, 결제/구매 연동, 당첨 보장성 예측.

## 공개 인터페이스 (계약 초안)
### 데이터 객체
- `FetchFailure`
  - `draw_no: int`
  - `reason: Literal["not_yet_drawn", "transient", "rate_limited", "unknown"]`
  - `detail: str`
- `SyncResult`
  - `fetched: list[LottoDraw]` — Backend Dev의 도메인 타입 재사용.
  - `failures: list[FetchFailure]`
  - `last_fetched_drw_no: int | None`
  - `stopped_reason: Literal["caught_up", "not_yet_drawn", "aborted", "target_reached"]`

### 설정
- `CollectorConfig(min_interval_s: float = 0.2, max_probe: int = 20, target_draw_no: int | None = None, abort_on_consecutive_failures: int = 3)`

### 함수/클래스
- `LottoCollector(client: DhLotteryClient, storage: LottoStorage, config: CollectorConfig, logger: Logger | None = None)`
  - `detect_latest_draw_no(probe_start: int) -> int` — `probe_start`에서 전진하며 마지막 발표 회차 반환.
  - `sync_incremental() -> SyncResult` — 저장소 체크포인트에서 시작해 최신 회차까지 증분 수집.
  - `sync_range(start: int, end: int) -> SyncResult` — 명시적 범위 수집(백필용).

### 외부 입력
- Backend Dev에서 이미 고정한 엔드포인트와 파라미터(`DhLotteryClient.fetch_draw`가 캡슐화).
- `LottoStorage.get_checkpoint()`가 반환하는 `FetchCheckpoint.last_fetched_drw_no`(없으면 1부터).

### 외부 출력
- `SyncResult` 반환값.
- 부수효과: `LottoStorage.upsert_draws(fetched)`, `LottoStorage.set_checkpoint(...)` 호출.

## 의존성
### 외부 라이브러리
- 없음(Backend Dev가 래핑한 것 이외 추가 없음).
- Python 표준 라이브러리: `dataclasses`, `typing`, `time`, `logging`.

### 내부 모듈 의존
- 선행 의존: Backend Dev 구현의 `DhLotteryClient`, `LottoStorage`, `LottoDraw`, `FetchCheckpoint`, `DrawNotFoundError`, `TransientFetchError`.
- 상위 소비자: 회차 데이터 로컬 캐시 저장소(`frontend_dev_module_2`)에서 `LottoCollector.sync_incremental()`을 호출하는 방식으로 래핑 가능.
- 간접 소비자: 통계 분석 엔진(`frontend_dev_module_3`), 추천기(`frontend_dev_module_4`), 리포트(`frontend_dev_module_5`).

### 역할 간 의존
- Backend Dev의 scope(`backend_dev_module_8_scope_1`) 계약이 변경되면 본 문서도 갱신.
- Game Logic Dev는 수집기 단계에 직접 개입하지 않음.
- QA Engineer는 수집기 플로우 전체(증분 성공, 미발표 회차 처리, 네트워크 실패 집계, 체크포인트 갱신)에 대한 회귀 시나리오를 설계.

## 산출물 (build 단계에서 생성할 파일)
- `src/lotto_predictor/collector/__init__.py` — 공개 심볼 재노출.
- `src/lotto_predictor/collector/models.py` — `FetchFailure`, `SyncResult`, `CollectorConfig`.
- `src/lotto_predictor/collector/core.py` — `LottoCollector` 구현(`detect_latest_draw_no`, `sync_incremental`, `sync_range`).
- `tests/collector/test_collector_sync.py` — fake `DhLotteryClient`/`LottoStorage`로 증분 수집 시나리오.
- `tests/collector/test_collector_detect.py` — `DrawNotFoundError` 처리와 최신 회차 탐색 테스트.
- `tests/collector/test_collector_failures.py` — `TransientFetchError`, 연속 실패 중단 규칙 테스트.

## 구현 순서 (고정)
1. `models.py`: `FetchFailure`, `SyncResult`, `CollectorConfig` 계약을 확정한다.
2. `core.py`의 `LottoCollector.__init__`과 rate limit 헬퍼(`_sleep_between_calls`) 구현.
3. `detect_latest_draw_no` 구현과 단위 테스트.
4. `sync_range` 구현(부분 성공 처리, 연속 실패 중단).
5. `sync_incremental` 구현(체크포인트 연동, 최신 회차 탐색, 저장소 위임 저장).
6. `__init__.py` 공개 심볼 정리.
7. Backend Dev build 완료 후 실제 `DhLotteryClient`와의 통합 점검(QA 단계에서 회귀 시나리오 실행).

## 에러 및 장애 시나리오
- `DrawNotFoundError` 수신
  - `sync_incremental`: `stopped_reason="not_yet_drawn"`으로 정상 종료, 체크포인트는 마지막 성공 회차로 유지.
  - `sync_range`: 해당 회차만 `FetchFailure(reason="not_yet_drawn")`로 기록하고 남은 범위는 계속 진행(설정에 따라 중단 선택 가능).
- `TransientFetchError` 수신: `FetchFailure(reason="transient")`로 기록. `abort_on_consecutive_failures` 이상 연속되면 즉시 중단하고 `stopped_reason="aborted"`.
- Rate limit 신호(429에 가까운 패턴): Backend Dev가 `TransientFetchError`로 표준화한 값이면 그대로 기록. 별도 신호가 있으면 `reason="rate_limited"`.
- 알 수 없는 예외: 래핑해서 `FetchFailure(reason="unknown")`로 기록하고 다음 회차로 진행.
- 저장소 실패: `LottoStorage`가 던지는 예외는 수집기에서 잡지 않고 그대로 전파(호출자가 롤백/재시도 결정).

## 비기능 제약
- 기본 요청 간격 `min_interval_s = 0.2s`, 연속 실패 허용 3회.
- 로그는 주입 가능한 `logging.Logger`를 통해 기록. 기본 logger는 `lotto_predictor.collector`.
- 수집기 모듈은 부수효과를 Backend Dev 계층으로 명시 위임하고 내부 상태는 최소화한다.
- 모든 새 주석/메시지/로그는 한국어로 작성한다.

## 대안 검토
- 대안 1: 수집기가 자체 HTTP 클라이언트를 가진다.
  - 기각: Backend Dev 계층과 책임이 겹쳐 재시도 정책/타임아웃을 이중 관리하게 된다.
- 대안 2: 수집기가 SQLite도 직접 접근한다.
  - 기각: 영속 계층 책임 분리가 무너지고, 스키마 변경 시 양쪽 수정이 필요.
- 대안 3: 비동기(`asyncio` + `httpx`) 수집기.
  - 기각: 500회차 수준 순차 수집에 과한 복잡도. PyInstaller 번들 비용 증가.
- 대안 4: 서드파티 공개 API 사용.
  - 기각: 공식 소스 대비 지속성/신뢰도 불명확.

## 완료 기준 (scope 단계 기준)
- Backend Dev와의 역할 경계가 명시됨.
- 수집기 모듈의 포함/제외 범위가 기록됨.
- 공개 인터페이스(`LottoCollector.detect_latest_draw_no`, `sync_incremental`, `sync_range`)와 데이터 객체(`FetchFailure`, `SyncResult`, `CollectorConfig`)가 고정됨.
- 상위 소비자(캐시 저장소)와 하위 의존(Backend Dev)의 계약 연결 지점이 확정됨.
- 구현 순서가 파일 단위로 고정됨.
- `docs/architecture.md`에 Frontend Dev 수집기 섹션이 추가됨.

## 검토 요청 메모
- 현재 실행 환경에는 `read_mailbox`, `send_mailbox_message`, `ack_mailbox_message` 도구가 노출되어 있지 않아 본 스코프 문서 작성까지만 선행한다.
- 교차검증 요청은 도구가 제공되는 런타임에서 `review_request` 메시지로 이어서 수행해야 한다.
- Backend Dev scope(`backend_dev_module_8_scope_1`)의 `DhLotteryClient` 실패 표현(`DrawNotFoundError`, `TransientFetchError`)이 유지되는지 상호 확인 필요.
- 캐시 모듈(`frontend_dev_module_2`) scope에서 본 문서가 정의한 `SyncResult` 계약을 수용할 수 있는지 연쇄 확인 필요.
