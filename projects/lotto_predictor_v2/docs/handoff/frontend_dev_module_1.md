# Frontend Dev 동행복권 회차 수집기 모듈 Handoff (module_1)

## 목적
이 문서는 `Frontend Dev` `frontend_dev_module_1`(동행복권 회차 수집기) 구현과 코드 리뷰 결과를 검증한 뒤, 후속 `frontend_dev_module_2`(회차 데이터 로컬 캐시 저장소)와 `frontend_dev_module_3`(통계 분석 엔진) 담당자가 공개 API, 잔여 리스크, 후속 작업을 즉시 이어받도록 고정한다.

## 메타데이터
- task_id: `frontend_dev_module_1_verify_3`
- 작성 일자: 2026-04-17
- 문서 언어: 한국어 (OS: `ko-KR`)
- 상태: verify 완료 (다음 build 전 WARN-Hi 3건 처리 권고)
- 선행 작업
  - `frontend_dev_module_1_scope_1` (완료) — `docs/plans/2026-04-17-dhlottery-회차-수집기-범위.md`
  - `frontend_dev_module_1_build_2` (완료) — 구현 및 단위 테스트 19건
  - `frontend_dev_module_1_code_review` (완료, 판정 **WARN**, BLOCK 없음) — `artifacts/frontend_dev_code_reviewer/2026-04-17-module-1-review.md`

## 검증 대상
- `src/lotto_predictor/collector/__init__.py`
- `src/lotto_predictor/collector/models.py`
- `src/lotto_predictor/collector/core.py`
- `tests/collector/__init__.py`
- `tests/collector/_fakes.py`
- `tests/collector/test_collector_sync.py`
- `tests/collector/test_collector_detect.py`
- `tests/collector/test_collector_failures.py`
- 상위 문서: `docs/architecture.md` §Frontend Dev 동행복권 회차 수집기 계약, `docs/change_history.md`(2026-04-17T01:55:00, 02:10:00)

## 실행한 검증
### 1. 구문·임포트 점검
- `python -m py_compile src/lotto_predictor/collector/__init__.py src/lotto_predictor/collector/core.py src/lotto_predictor/collector/models.py` — 오류 없음.
- `PYTHONPATH=src python -c "from lotto_predictor.collector import CollectorConfig, DrawFetcher, FailureReason, FetchFailure, LottoCollector, StoppedReason, SyncResult"` — 공개 심볼 7종 전수 임포트 성공.
- verify 재실행 시점(2026-04-17): 위 두 명령 모두 현재 워크스페이스에서 다시 통과.

### 2. 공개 계약 스모크
- `CollectorConfig()` 기본값: `min_interval_s=0.2`, `max_probe=20`, `target_draw_no=None`, `abort_on_consecutive_failures=3` — scope 계약과 일치.
- `SyncResult()` 기본값: `fetched=[]`, `failures=[]`, `last_fetched_drw_no=None`, `stopped_reason="caught_up"` — 모듈 기본 계약 정상.
- `FetchFailure` 불변식: `draw_no <= 0`, `detail=""` 모두 `ValueError`로 즉시 거절.

### 3. 단위 테스트
- 명령: `python -m pytest tests/collector -v`
- 결과: **19 passed / 0 failed** (0.16s, Python 3.14.3).
- verify 재실행 명령: `python -m pytest tests/collector -q`
- verify 재실행 결과: **19 passed** (0.17s).
- 커버된 경로:
  - `sync_incremental`: 체크포인트 유무, target 지정, 미발표 조기 종료, 최신 상태(no-op) — 5건.
  - `sync_range`: 정상 범위, start>end `ValueError`, 미발표 섞임 부분 성공 — 3건.
  - `detect_latest_draw_no`: probe_start 성공/미발표/0 경계/ValueError/`TransientFetchError` 전파/`max_probe` 한계 — 7건.
  - 실패 집계: 연속 transient 중단, 성공 사이 transient 리셋, detect 단계 transient 시 체크포인트 보전, 알 수 없는 예외 `unknown` 분류 — 4건.

## 이번 verify 단계 결론
- 현재 워크스페이스 기준으로 수집기 모듈은 컴파일, 공개 심볼 import, `tests/collector` 회귀가 모두 통과한다.
- 선행 코드 리뷰의 WARN-Hi 3건(C1~C3)은 여전히 미해결이며, 이번 단계에서는 동작 변경 없이 위험 기록과 인계에 집중했다.
- 따라서 판정은 **검증 통과 + 후속 보강 필요**다. 다음 작업자는 본 문서의 잔여 리스크를 전제로 이어서 작업해야 한다.

### 4. 스코프 계약 준수도 (리뷰어 판단과 일치)
| 계약 항목 | 결과 |
| --- | --- |
| 파일 구조(`__init__.py`, `models.py`, `core.py`) | ✓ |
| 공개 심볼 7종(`LottoCollector`, `DrawFetcher`, `CollectorConfig`, `FailureReason`, `FetchFailure`, `StoppedReason`, `SyncResult`) | ✓ |
| 공개 메서드 3종(`detect_latest_draw_no`, `sync_incremental`, `sync_range`) | ✓ |
| Backend Dev 도메인 재사용(`LottoDraw`, `FetchCheckpoint`, `DrawNotFoundError`, `TransientFetchError`, `parse_draw`) | ✓ |
| 구현 순서(models → rate-limit 헬퍼 → detect → sync_range → sync_incremental → `__init__`) | ✓ |
| HTTP/SQLite 직접 접근 없음(전부 Backend Dev 위임) | ✓ |
| 한국어 주석/로그/오류 메시지 | ✓ |

## 공개 API 요약 (후속 소비자가 import 해야 하는 계약)
- `from lotto_predictor.collector import LottoCollector, CollectorConfig, SyncResult, FetchFailure, DrawFetcher, FailureReason, StoppedReason`
- `LottoCollector(client: DrawFetcher, storage: LottoStorage, config: CollectorConfig | None = None, logger: logging.Logger | None = None)`
  - `detect_latest_draw_no(probe_start: int) -> int`
  - `sync_incremental() -> SyncResult`
  - `sync_range(start: int, end: int) -> SyncResult`
- 부수효과는 `LottoStorage.upsert_draws`, `LottoStorage.set_checkpoint` 에만 한정된다(저장소 예외는 수집기에서 잡지 않고 호출자에게 전파).
- `SyncResult.stopped_reason` 은 `{"caught_up", "not_yet_drawn", "aborted", "target_reached"}` 중 하나.

## 잔여 리스크 (코드 리뷰 WARN — BLOCK 없음)
아래 항목은 동작·보안·scope 준수에는 영향이 없으나 운영·데이터 정합성 관점의 위험이다. **module_1 의 후속 build 분기** 또는 **module_2(캐시)의 `ensure_ready` 설계**에서 처리 정책을 결정한다.

### WARN-Hi — 다음 build 에서 반드시 처리 권고
- **C1. `sync_incremental` 갭 전진.** `core.py:226-257` — 일시 실패 회차를 건너뛰면서 `last_success` 가 전진하고, 이어서 체크포인트도 갱신되어 다음 호출이 **회차 갭을 영구 누락**한다. 재실행으로 복구되지 않고 `sync_range` 수동 백필이 필요하다.
  - 권고(택1): (a) `last_success`를 "최초 실패 이전의 최대 성공 회차"로 재정의, (b) 별도 누락 테이블 도입, (c) 최소한 docstring/리포트에서 "사용자가 직접 `sync_range` 백필 필요" 경고.
  - module_2 캐시 측은 `validate_continuity()` 에서 갭을 탐지하고 `ensure_ready` 가 자동 `sync_range` 백필을 실행할지 결정해야 한다.
- **C2. 파서 `ValueError` → `unknown` 침묵.** `core.py:298-301` + `core.py:248-256` — `parse_draw` 가 던지는 `ValueError` 는 `reason="unknown"` 으로 분류되어 연속 실패 카운터를 리셋한다. 동행복권 응답 스키마가 드리프트되면 500회차 전부 `unknown` 으로 수집되고 `stopped_reason="caught_up"` 으로 정상 종료되는 **대량 침묵 실패**가 발생할 수 있다.
  - 권고: `FailureReason` 에 `"schema_error"` 신설 또는 `transient` 와 동일하게 카운터 집계, 혹은 연속 `unknown` 임계치 추가.
- **C3. 응답 `drwNo` 불일치 저장.** `core.py:304-310` — 요청 회차와 응답 회차가 다를 때 경고만 남기고 서버 값을 그대로 upsert·반환한다. `sync_range` 경로에서는 `last_success` 가 역행할 수 있다.
  - 권고: 불일치 시 저장 생략 + `reason="unknown"`/`schema_error` 로 분류.

### WARN-Lo — 문서/가독성
- **C4.** `sync_incremental` 이 `target_draw_no` 지정 상태에서 이미 최신이면 `stopped_reason="caught_up"` 을 반환(docstring 의 `target_reached` 정의와 어긋남). `core.py:206-215`.
- **C5.** `probe_start = start if checkpoint is None else checkpoint.last_fetched_drw_no + 1` 분기는 양쪽 값이 동일하므로 `probe_start = start` 로 단순화 가능. `core.py:181-185`.
- **C6.** `_FetchOutcome` 의 성공 경로에서도 `reason="unknown"` 이 설정되어 의미 모호. `core.py:310, 338-350`.
- **C7.** `sync_range` 와 `sync_incremental` 의 transient/rate_limited 판정 스타일이 다름(`or` vs `in`). 통일 권고. `core.py:152, 248`.
- **C8.** `stopped_reason` 지역 변수에 `StoppedReason` 리터럴 주석 누락으로 `sync_incremental` 에는 `# type: ignore[arg-type]` 만 걸려 있음. `core.py:134, 223, 272`.

### 연계 권고 (cross-module)
- **datetime 통일**: Backend Dev 코드 리뷰에서 지적된 `datetime.now()` UTC-aware 통일 권고가 수집기 `_update_checkpoint`(`core.py:320`) 에도 동일하게 적용 대상이다. Backend Dev 체크포인트 표현이 UTC-aware 로 바뀌면 수집기도 같은 커밋에서 `datetime.now(timezone.utc)` 로 변경한다.
- **run_id 로깅**: 상위 소비자(캐시·리포트)가 여러 번 호출할 수 있으므로 `self._logger` 에 run_id/호출 컨텍스트를 넘길 필요가 있는지 module_5(리포트) 설계에서 재점검.

## 누락 테스트 (module_1 향후 build 또는 QA 단계에서 추가 권고)
- C1 시나리오: `sync_incremental` → 갭 발생 → 재호출 시 `start` 가 갭을 뛰어넘는 것을 증명하는 회귀 테스트.
- C2 시나리오: `parse_draw` 가 `ValueError` 를 던지도록 payload 를 훼손한 fake 시나리오.
- C3 시나리오: 응답 payload 의 `drwNo` 가 요청과 다른 경우.
- `sync_range` 의 `rate_limited` 경로(현재 `transient` 만 커버).

## 후속 작업 (다음 작업자 체크리스트)
1. `frontend_dev_module_2_scope_1` 후속 build 담당자
   - 본 handoff 의 공개 API(`LottoCollector.sync_incremental`, `sync_range`, `SyncResult`, `FetchFailure`)를 그대로 import 해 `LottoDrawCache.ensure_ready` 의 수집 단계에 위임한다.
   - C1 위험을 `validate_continuity()` / `ensure_ready()` 의 자동 백필 정책으로 흡수할지 결정한다. (scope 문서 `docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md` 의 `refresh_policy` 분기 참조)
   - 수집기 `min_interval_s` 기본값(0.2s) 을 캐시 레이어에서 재조정하지 않는다 — Backend Dev 계층의 재시도와 이중 관리 금지.
2. `frontend_dev_module_3_scope_1` 담당자(통계 분석 엔진)
   - 수집기는 직접 의존하지 않고, 캐시(`LottoDrawCache.get_all_draws()`) 를 통한 간접 의존만 유지한다. 수집기 공개 심볼을 직접 import 하지 않는다.
3. QA Engineer
   - 실제 `DhLotteryClient` 와의 통합 회귀 시나리오(최근 500회차 end-to-end sync)를 `qa_engineer_*` 단계에서 실행한다.
   - C1/C2/C3 의 재현 시나리오를 회귀 스위트에 포함한다.
4. 추가 build 가 열리는 경우 우선순위
   - C1(WARN-Hi) → C2(WARN-Hi) → C3(WARN-Hi) → C4–C8(WARN-Lo) 순.
   - UTC-aware datetime 은 Backend Dev 교정과 같은 커밋에서 동시 반영.

## 미완료 / 미해결
- 이 verify 단계에서는 **실제 HTTP 통신** 을 시도하지 않았다(Backend Dev scope 계약에 따라 단위 테스트는 fake 주입으로 계약 준수만 확인). 실 환경 500회차 수집은 QA 단계에서 재확인 필요.
- mailbox 도구는 현재 런타임에 노출되지 않아 본 verify 결과에 대한 `review_request` 를 송신하지 못했다. 도구가 제공되는 런타임에서 교차검증 요청을 이어 수행한다.

## 참조
- 범위 문서: `docs/plans/2026-04-17-dhlottery-회차-수집기-범위.md`
- 아키텍처: `docs/architecture.md` §Frontend Dev 동행복권 회차 수집기 계약(module_1)
- 변경 이력: `docs/change_history.md` 2026-04-17T01:55:00 (scope), 2026-04-17T02:10:00 (build)
- 코드 리뷰: `artifacts/frontend_dev_code_reviewer/2026-04-17-module-1-review.md`
- Backend Dev handoff (상위 의존): `docs/handoff/backend_dev.md`

## Signature
[frontend_dev] module_1 검증 완료 · WARN-Hi 3건과 후속 작업 인계.
