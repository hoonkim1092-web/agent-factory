# 변경 이력

설계, 아키텍처, 워크플로, 구현 전략이 바뀔 때마다 항목을 하나씩 추가한다.

## 항목 템플릿
### YYYY-MM-DD HH:MM:SS
- 요약:
- 이유:
- 영향 파일:
- 후속 작업:

## 이력
### 2026-04-17T04:17:00
- 요약: `Frontend Dev` 통계 분석 엔진(module_3)의 범위, 캐시 입력 경계, 출력 계약(`PatternStats`, `AnalysisRunSummary`), 의존성, 구현 순서를 고정했다.
- 이유: `frontend_dev_module_3_scope_1` 작업의 완료 기준(범위 명확화, 의존성·산출물 명시)을 충족하고 module_2 캐시 계약과 module_4 추천기 계약 사이의 연결 인터페이스를 build 전에 명확히 하기 위해.
- 영향 파일: `docs/plans/2026-04-17-통계-분석-엔진-범위.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: mailbox 도구가 제공되는 런타임에서 `review_request` 교차검증을 수행한 뒤, `frontend_dev_module_3_build_2`에서 `출력 계약 → 입력 검증/정규화 → 5개 통계 함수 → analyze_patterns → cache 어댑터 → 실행 요약` 순으로 구현한다.

### 2026-04-17T01:23:37
- 요약: 문서 계약 초기화.
- 이유: 아키텍처와 워크플로 변경 이력을 안정적으로 보존하기 위해.
- 영향 파일: `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: 이 파일을 append-only로 유지하고, 생성하거나 수정하는 모든 문서를 운영체제 언어 코드 `ko-KR`에 맞는 한국어로 작성한다.

### 2026-04-17T01:35:00
- 요약: QA Engineer 검증 범위, 입력/출력 인터페이스, 구현 순서를 고정했다.
- 이유: QA build 단계에서 검증 대상 의존성, 산출물, 실행 순서를 선행 확정해 재작업 위험을 줄이기 위해.
- 영향 파일: `docs/plans/2026-04-17-qa-engineer-검증-범위.md`, `docs/architecture.md`, `docs/task_execution_plan.md`, `docs/change_history.md`
- 후속 작업: mailbox 도구가 제공되는 런타임에서 `review_request` 교차검증을 수행한 뒤 QA build 단계로 진행한다.

### 2026-04-17T01:32:29
- 요약: QA build 단계에서 사용할 체크리스트, 회귀 시나리오, 결과 템플릿 경로를 고정했다.
- 이유: verify 단계가 산출물 부족으로 지연되지 않도록 핵심 검증 흐름과 기록 형식을 먼저 구현하기 위해.
- 영향 파일: `artifacts/qa_engineer/core-flow-checklist.md`, `artifacts/qa_engineer/regression-scenarios.md`, `artifacts/qa_engineer/verification-report-template.md`, `artifacts/qa_engineer/execution-log-template.md`, `artifacts/qa_engineer/handoff-template.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: verify 단계에서 실제 실행 결과를 템플릿에 채우고 실패/보류 항목을 handoff 메모로 연결한다.

### 2026-04-17T01:42:00
- 요약: `Game Logic Dev`의 구현 범위, 인터페이스, 의존성, 산출물, 구현 순서를 문서로 고정했다.
- 이유: `game_logic_dev_module_9_scope_1` 작업의 완료 기준인 범위 명확화와 계약 고정을 충족하기 위해.
- 영향 파일: `docs/plans/2026-04-17-game-logic-dev-scope.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: 메일박스 도구가 제공되면 설계 검토 요청을 송신하고, `build` 단계에서 타입 정의와 상태 전이 구현을 이 계약에 맞춰 진행한다.

### 2026-04-17T01:47:00
- 요약: `Backend Dev`(module_8)의 구현 범위·공개 인터페이스·데이터 스키마·구현 순서를 고정했다.
- 이유: `backend_dev_module_8_scope_1` 작업의 완료 기준(범위 명확화, 의존성·산출물 명시, 구현 순서 고정)을 충족하고 Frontend Dev 상위 모듈이 참조할 계약을 확정하기 위해.
- 영향 파일: `docs/work-items/한국-로또-.../backend-dev-scope.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: mailbox 도구가 제공되는 런타임에서 `review_request` 교차검증을 수행한 뒤 `backend_dev_module_8_build_1`에서 고정된 순서대로 `models.py → schema/storage 골격 → serialization → http_client → storage 나머지 → __init__` 순으로 구현한다.

### 2026-04-17T01:55:00
- 요약: `Frontend Dev` 동행복권 회차 수집기(module_1)의 범위, 공개 인터페이스(`LottoCollector`, `SyncResult`, `FetchFailure`, `CollectorConfig`), 의존성, 산출물, 구현 순서를 고정했다.
- 이유: `frontend_dev_module_1_scope_1` 작업의 완료 기준(범위 명확화, 의존성·산출물 명시)을 충족하고 Backend Dev 저수준 어댑터와의 역할 경계를 사전에 확정해 build 단계에서 중복 구현을 방지하기 위해.
- 영향 파일: `docs/plans/2026-04-17-dhlottery-회차-수집기-범위.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: mailbox 도구가 제공되는 런타임에서 `review_request` 교차검증을 수행한 뒤 Backend Dev `DhLotteryClient.fetch_draw`와 `LottoStorage` 구현이 완료되는 시점에 맞춰 `frontend_dev_module_1_build_2`에서 `models.py → core.py(init+rate limit) → detect_latest → sync_range → sync_incremental → __init__` 순으로 구현한다.

### 2026-04-17T02:05:00
- 요약: `Backend Dev`(module_8) build 단계에서 scope 계약대로 서버·데이터·외부 연동 레이어 6개 파일을 구현했다.
- 이유: `backend_dev_module_8_build_2` 작업의 완료 기준(핵심 기능 구현, 관련 파일 갱신)을 충족하고 Frontend Dev 수집기/캐시/통계 모듈이 의존할 공개 심볼(`DhLotteryClient`, `LottoStorage`, `parse_draw`, 도메인 타입·예외)을 준비하기 위해.
- 영향 파일: `src/lotto_predictor/__init__.py`, `src/lotto_predictor/backend/__init__.py`, `src/lotto_predictor/backend/models.py`, `src/lotto_predictor/backend/schema.sql`, `src/lotto_predictor/backend/storage.py`, `src/lotto_predictor/backend/serialization.py`, `src/lotto_predictor/backend/http_client.py`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `backend_dev_module_8_verify_*` 단계에서 QA 시나리오와 통합 검증을 실행하고, Frontend Dev 수집기 모듈 build 단계가 본 공개 API를 import 하여 구현한다.

### 2026-04-17T02:10:00
- 요약: `Frontend Dev` 동행복권 회차 수집기(module_1) build 단계에서 `LottoCollector`, `CollectorConfig`, `SyncResult`, `FetchFailure` 를 scope 계약 그대로 구현하고 단위 테스트 19 건을 작성했다.
- 이유: `frontend_dev_module_1_build_2` 완료 기준(핵심 기능 구현, 관련 파일 갱신)을 충족하고 후행 소비자인 회차 데이터 로컬 캐시 저장소(`frontend_dev_module_2`) 가 본 수집기의 `sync_incremental`/`sync_range` 결과 계약에 의존할 수 있도록 하기 위해.
- 영향 파일: `src/lotto_predictor/collector/__init__.py`, `src/lotto_predictor/collector/models.py`, `src/lotto_predictor/collector/core.py`, `tests/collector/__init__.py`, `tests/collector/_fakes.py`, `tests/collector/test_collector_sync.py`, `tests/collector/test_collector_detect.py`, `tests/collector/test_collector_failures.py`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_1_verify_*` 단계에서 Backend Dev 실제 `DhLotteryClient` 와의 통합 점검을 수행하고, `frontend_dev_module_2` scope 단계에서 본 수집기의 `SyncResult` 계약을 캐시 소비자 관점에서 재확인한다.

### 2026-04-17T02:20:00
- 요약: 통계 분석 엔진 패턴 규칙 모듈의 입력/출력 계약을 고정하고 빈도·연속 간격·홀짝·구간·트렌드 계산 함수를 추가했다.
- 이유: 최근 500회차 기반 통계 계산을 추천기와 리포트가 공통으로 재사용할 수 있도록 순수 함수 계층을 확정하기 위해.
- 영향 파일: `docs/plans/2026-04-17-통계-분석-엔진-패턴-규칙.md`, `src/lotto/__init__.py`, `src/lotto/analytics/__init__.py`, `src/lotto/analytics/patterns.py`, `tests/test_patterns.py`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: mailbox 도구가 제공되는 런타임에서 설계 검토 요청을 송신하고, 후속 통합 작업에서 본 결과를 `StatisticsSummary`로 정규화한다.

### 2026-04-17T02:30:00
- 요약: `Frontend Dev` 회차 데이터 로컬 캐시 저장소(module_2) 의 구현 범위, 공개 인터페이스(`LottoDrawCache.status`·`ensure_ready`·`get_recent_draws`·`get_all_draws`·`get_draw`·`validate_continuity`), 데이터 객체(`CacheConfig`, `CacheStatus`, `CacheReadyResult`, `CacheGapReport`), 의존성, 산출물, 구현 순서를 고정했다.
- 이유: `frontend_dev_module_2_scope_1` 작업의 완료 기준(범위 명확화, 의존성·산출물 명시)을 충족하고 Backend Dev `LottoStorage`·Frontend Dev 수집기(module_1) 와의 역할 경계를 사전에 확정해 build 단계에서 상위 소비자(통계·추천·리포트) 가 참조할 신선도 판정·읽기 API 계약을 먼저 고정하기 위해.
- 영향 파일: `docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: mailbox 도구가 제공되는 런타임에서 `review_request` 교차검증을 수행한 뒤, `frontend_dev_module_2_build_2` 에서 `models.py → core.__init__/_compute_status → status() → ensure_ready() → 읽기 API → validate_continuity() → __init__` 순으로 구현한다.

### 2026-04-17T03:35:00
- 요약: `PatternStats` 입력과 `recommend_combinations` 공개 계약을 추가하고, 패턴 기반 번호 조합 추천기 규칙을 구현했다.
- 이유: 통계 분석 엔진의 5가지 패턴 결과를 직접 소비하는 추천 계층을 확정하고, 빈도 상위 70%/홀짝/구간 균형/트렌드 가중치 제약을 테스트 가능한 형태로 고정하기 위해.
- 영향 파일: `docs/plans/2026-04-17-패턴-기반-추천기-규칙.md`, `src/lotto/analytics/patterns.py`, `src/lotto/recommender.py`, `src/lotto/__init__.py`, `tests/test_recommender.py`, `docs/handoff/recommender.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: mailbox 도구가 제공되는 런타임에서 설계 검토 요청을 송신하고, 통합 단계에서 실제 `analyze_patterns` 출력과 추천기 연결을 검증한다.

### 2026-04-17T03:10:00
- 요약: `Frontend Dev` 회차 데이터 로컬 캐시 저장소(module_2) build 단계에서 `LottoDrawCache` 와 값 객체(`CacheConfig`, `CacheStatus`, `CacheReadyResult`, `CacheGapReport`) 를 scope 계약 그대로 구현하고 단위 테스트 27건을 작성했다.
- 이유: `frontend_dev_module_2_build_2` 완료 기준(핵심 기능 구현, 관련 파일 갱신)을 충족하고 후행 소비자인 통계 분석 엔진(`frontend_dev_module_3`)·추천기·리포트가 `get_recent_draws`/`get_all_draws`/`status`/`ensure_ready` 계약으로 회차 데이터를 안정적으로 소비할 수 있게 하기 위해.
- 영향 파일: `src/lotto_predictor/cache/__init__.py`, `src/lotto_predictor/cache/models.py`, `src/lotto_predictor/cache/core.py`, `tests/cache/__init__.py`, `tests/cache/_fakes.py`, `tests/cache/test_cache_status.py`, `tests/cache/test_cache_ensure_ready.py`, `tests/cache/test_cache_reads.py`, `tests/cache/test_cache_continuity.py`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: `frontend_dev_module_2_verify_*` 단계에서 실제 `LottoStorage`·`LottoCollector` 와 연결한 통합 점검을 수행하고, `frontend_dev_module_3` scope 단계에서 본 캐시의 `get_all_draws`(오름차순) 및 `get_recent_draws(n)`(내림차순) 계약을 통계 입력 관점에서 재확인한다.

### 2026-04-17T04:00:00
- 요약: `Frontend Dev` 동행복권 회차 수집기(module_1) verify 단계에서 구문·임포트·단위 테스트(19/19 pass)·scope 준수도를 재확인하고, 코드 리뷰 결과(판정 WARN, BLOCK 없음)의 WARN-Hi 3건(C1 sync_incremental 갭 전진 / C2 파서 ValueError 침묵 / C3 응답 drwNo 불일치 저장)을 포함한 후속 작업 체크리스트를 handoff 문서로 고정했다.
- 이유: `frontend_dev_module_1_verify_3` 완료 기준(검증 결과 정리, 잔여 리스크·후속 작업 기록)을 충족하고 후행 소비자인 `frontend_dev_module_2`(캐시)·`frontend_dev_module_3`(통계)·QA Engineer 가 공개 API(`LottoCollector.sync_incremental`/`sync_range`/`detect_latest_draw_no`, `SyncResult`, `FetchFailure`, `CollectorConfig`)와 WARN-Hi 리스크 대응 정책을 즉시 이어받을 수 있게 하기 위해.
- 영향 파일: `docs/handoff/frontend_dev_module_1.md`, `docs/change_history.md`
- 후속 작업: 다음 build 분기 또는 module_2 `ensure_ready`/`validate_continuity` 설계에서 C1/C2/C3 정책 처리(갭 백필, 스키마 드리프트 분류, 불일치 저장 차단) 및 Backend Dev datetime UTC-aware 통일(`core.py:320 _update_checkpoint`) 을 함께 반영한다.
