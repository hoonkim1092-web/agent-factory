# 변경 이력

설계, 아키텍처, 워크플로, 구현 전략이 바뀔 때마다 항목을 하나씩 추가한다.

## 항목 템플릿
### YYYY-MM-DD HH:MM:SS
- 요약:
- 이유:
- 영향 파일:
- 후속 작업:

## 이력
### 2026-04-16T20:40:47
- 요약: 문서 계약 초기화.
- 이유: 아키텍처와 워크플로 변경 이력을 안정적으로 보존하기 위해.
- 영향 파일: `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: 이 파일을 append-only로 유지하고, 생성하거나 수정하는 모든 문서를 운영체제 언어 코드 `ko-KR`에 맞는 한국어로 작성한다.

### 2026-04-16T21:02:00
- 요약: QA Engineer 검증 모듈의 범위, 입력 인터페이스, 산출물, 구현 순서를 고정했다.
- 이유: QA 단계가 어떤 의존 산출물을 입력으로 받아 무엇을 검증하고 어떤 결과를 남겨야 하는지 명확히 하기 위해.
- 영향 파일: `docs/plans/2026-04-16-qa-engineer-검증-범위-정의.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: build 단계에서 검증 시나리오와 실행 자산을 이 계약에 맞춰 구현한다.

### 2026-04-16T20:48:00
- 요약: 동행복권 API 데이터 수집 모듈의 범위, 인터페이스, 산출물, 구현 순서를 확정했다.
- 이유: `LottoFetcher` 클래스와 `DrawResult` 데이터 모델의 계약을 고정하여, 하위 모듈(cache_store, analysis_engine)이 안정적으로 소비할 수 있게 하기 위해.
- 영향 파일: `docs/scope-동행복권-api-데이터-수집-모듈.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: build 단계에서 `src/lotto/models.py`, `src/lotto/exceptions.py`, `src/lotto/fetcher.py` 순으로 구현한다.

### 2026-04-16T21:10:00
- 요약: 동행복권 API 데이터 수집 모듈 구현 완료 — models.py, exceptions.py, fetcher.py 및 단위 테스트 20건 전수 통과.
- 이유: scope 단계에서 확정한 `DrawResult` 모델과 `LottoFetcher` 인터페이스 계약을 실제 코드로 구현하기 위해.
- 영향 파일: `src/lotto/__init__.py`, `src/lotto/models.py`, `src/lotto/exceptions.py`, `src/lotto/fetcher.py`, `tests/test_models.py`, `tests/test_fetcher.py`, `tests/test_fetcher_integration.py`, `docs/architecture.md`
- 후속 작업: verify 단계에서 실제 API 호출 통합 검증, 이후 SQLite 캐시 저장소(cache_store.py) 구현으로 진행.

### 2026-04-16T21:20:00
- 요약: 동행복권 API 데이터 수집 모듈 검증 완료 — 단위 테스트 22건 통과, 스코프 정합성 확인, handoff 메모 작성.
- 이유: build 단계 산출물이 scope 문서와 일치하는지 검증하고, 후속 모듈(cache_store) 작업자가 이어받을 수 있도록 잔여 리스크와 연동 포인트를 정리하기 위해.
- 영향 파일: `artifacts/backend_dev/module_1_verify_report.md`, `docs/change_history.md`
- 후속 작업: SQLite 기반 당첨번호 캐시 저장소(cache_store.py) 범위 정의 및 구현 시작. `fetch_range()`에 `skip` 파라미터 추가 필요.

### 2026-04-16T21:30:00
- 요약: SQLite 기반 당첨번호 캐시 저장소의 범위, DB 스키마, 인터페이스, 산출물, 구현 순서를 확정했다.
- 이유: `CacheStore` 클래스의 계약을 고정하여 상위 모듈(cli.py)과 하위 모듈(analysis.py)이 안정적으로 연동할 수 있게 하기 위해.
- 영향 파일: `docs/scope-sqlite-캐시-저장소.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: build 단계에서 `exceptions.py`에 `CacheError` 추가 후, `cache_store.py` 순서대로 구현한다.

### 2026-04-16T22:00:00
- 요약: 번호별 출현빈도·동시출현·구간 통계 분석 엔진의 범위, 데이터 모델, 인터페이스, 산출물, 구현 순서를 확정했다.
- 이유: `AnalysisEngine` 클래스와 `NumberFrequency`/`PairCooccurrence`/`AnalysisResult` 데이터 모델의 계약을 고정하여, 하위 모듈(recommender.py, formatter.py)이 안정적으로 소비할 수 있게 하기 위해.
- 영향 파일: `docs/scope-통계-분석-엔진.md`, `docs/architecture.md`, `docs/change_history.md`
- 후속 작업: build 단계에서 `exceptions.py`에 `AnalysisError` 추가 후, `analysis.py` 순서대로 구현한다.

### 2026-04-16T21:06:00
- 요약: SQLite 기반 당첨번호 캐시 저장소 구현 완료 — CacheError 예외, CacheStore 전체 메서드, 단위 테스트 16건 전수 통과.
- 이유: scope 단계에서 확정한 `CacheStore` 인터페이스 계약을 실제 코드로 구현하기 위해.
- 영향 파일: `src/lotto/exceptions.py`, `src/lotto/cache_store.py`, `tests/test_cache_store.py`, `docs/architecture.md`
- 후속 작업: verify 단계에서 스코프 정합성 검증 및 handoff 메모 작성. 이후 분석 엔진(analysis.py) 구현으로 진행.

### 2026-04-16T23:30:00
- 요약: 번호별 출현빈도·동시출현·구간 통계 분석 엔진 구현 완료 — AnalysisError 예외, AnalysisEngine 전체 메서드, 데이터 모델 3종, 단위 테스트 26건 + 기존 테스트 수정 4건, 전체 80건 통과.
- 이유: scope 단계에서 확정한 `AnalysisEngine` 인터페이스 계약을 실제 코드로 구현. 가중치 산출: 전체 빈도 40% + 최근 구간 빈도 40% + 출현 간격 역수 20%.
- 영향 파일: `src/lotto/exceptions.py`, `src/lotto/analysis.py`, `tests/test_analysis.py`, `tests/test_analyzer.py`, `docs/architecture.md`
- 후속 작업: verify 단계에서 스코프 정합성 검증 및 handoff 메모 작성. 이후 가중 랜덤 5조합 추천 생성기(recommender.py) 구현으로 진행.
