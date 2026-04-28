# Frontend Dev 회차 데이터 로컬 캐시 저장소 Handoff (module_2)

## 목적
이 문서는 `Frontend Dev` `frontend_dev_module_2`(회차 데이터 로컬 캐시 저장소) 구현과 코드 리뷰 결과를 검증한 뒤, 후속 `frontend_dev_module_3`(통계 분석 엔진), 추천기, 리포트, QA 담당자가 공개 API와 잔여 리스크를 즉시 이어받을 수 있도록 고정한다.

## 메타데이터
- task_id: `frontend_dev_module_2_verify_3`
- 작성 일자: 2026-04-17
- 문서 언어: 한국어 (OS: `ko-KR`)
- 상태: verify 완료 (판정 PASS-with-WARN, BLOCK 없음)
- 선행 작업
  - `frontend_dev_module_2_scope_1` (완료) — `docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md`
  - `frontend_dev_module_2_build_2` (완료) — `LottoDrawCache` 및 단위 테스트 27건 구현
  - `frontend_dev_module_2_code_review` (완료, 판정 `WARN`) — `artifacts/frontend_dev_code_reviewer/2026-04-17-module-2-review.md`

## 검증 대상
- `src/lotto_predictor/cache/__init__.py`
- `src/lotto_predictor/cache/models.py`
- `src/lotto_predictor/cache/core.py`
- `tests/cache/__init__.py`
- `tests/cache/_fakes.py`
- `tests/cache/test_cache_status.py`
- `tests/cache/test_cache_ensure_ready.py`
- `tests/cache/test_cache_reads.py`
- `tests/cache/test_cache_continuity.py`
- 참고 회귀 골격: `tests/test_cache_store.py`

## 실행한 검증
### 1. 정책 계층 단위 테스트
- 명령: `PYTHONPATH=src pytest tests/cache -q`
- 결과: **27 passed** (0.23s)
- 커버된 경로:
  - `status()` 상태 판정 9건
  - `ensure_ready()` 분기 6건
  - 읽기 API(`get_recent_draws`, `get_all_draws`, `get_draw`) 7건
  - `validate_continuity()` 5건

### 2. 기존 회귀 골격 상태 확인
- 명령: `PYTHONPATH=src pytest tests/test_cache_store.py -q`
- 결과: **3 skipped** (0.14s)
- 해석:
  - 이 파일은 현재 module_2 스코프와 다른 과거 JSON 파일 저장소 계약(`JsonDrawCacheStore`)을 전제로 작성된 골격이다.
  - 현재 구현물은 `LottoDrawCache` 정책 계층이므로 skip 결과는 실패가 아니라 "현 범위 미대상" 상태다.

### 3. 코드/스코프 계약 대조
- `src/lotto_predictor/cache/__init__.py` 에서 공개 심볼(`LottoDrawCache`, `CacheConfig`, `CacheStatus`, `CacheReadyResult`, `CacheGapReport`) 재노출 확인.
- `docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md` 의 공개 인터페이스, 구현 순서, 책임 경계와 현재 구현이 일치함을 확인.
- `artifacts/frontend_dev_code_reviewer/2026-04-17-module-2-review.md` 기준 BLOCK 없음, WARN만 남아 있음.

## 이번 verify 단계 결론
- 현재 워크스페이스 기준으로 회차 데이터 로컬 캐시 저장소는 **정책 계층 구현과 단위 테스트가 모두 정상**이다.
- `tests/cache` 전수 통과로 상태 판정, 수집 위임 분기, 읽기 API, 연속 회차 검증 계약이 재확인됐다.
- 별도 `tests/test_cache_store.py` 는 현 구현 범위가 아닌 과거 JSON 저장소 골격이므로 skip 상태를 유지한다.
- 따라서 판정은 **검증 통과 + WARN 리스크 인계**다. 다음 작업자는 본 문서의 리스크와 제외 범위를 전제로 이어서 작업해야 한다.

## 공개 API 요약
- `from lotto_predictor.cache import LottoDrawCache, CacheConfig, CacheStatus, CacheReadyResult, CacheGapReport`
- `LottoDrawCache(storage, collector=None, config=None, clock=datetime.now, logger=None)`
  - `status() -> CacheStatus`
  - `ensure_ready() -> CacheReadyResult`
  - `get_recent_draws(n: int) -> list[LottoDraw]`
  - `get_all_draws() -> list[LottoDraw]`
  - `get_draw(draw_no: int) -> LottoDraw | None`
  - `validate_continuity() -> CacheGapReport`
- 호출 경계:
  - SQL 직접 발행 없음. `LottoStorage` 공개 메서드만 사용.
  - HTTP 직접 호출 없음. 필요 시 `LottoCollector.sync_incremental()` 에 위임.
  - `get_recent_draws(n)` 은 내림차순, `get_all_draws()` 는 오름차순 반환 계약을 가진다.

## 잔여 리스크 (코드 리뷰 WARN)
### WARN-Med
- **B1. `ensure_ready()` 의 전체 회차 I/O 2회** — stale 경로에서 `status()` 를 수집 전/후 두 번 호출해 전체 회차를 두 번 읽는다. 현재 500회차 규모에서는 기능 결함은 아니지만, 상위 모듈이 매 실행 전 `ensure_ready()` 를 호출하면 불필요한 I/O 가 누적된다.

### WARN-Low
- **B2. naive/aware datetime 혼용 가능성** — `_is_checkpoint_expired()` 가 `clock()` 반환값과 `FetchCheckpoint.fetched_at` 을 직접 뺀다. Backend 계층의 datetime 정책이 UTC-aware 로 바뀌면 `TypeError` 가능성이 있다.
- **B3. clock 예외 시 만료 판정 우회** — `clock()` 예외가 나면 `_is_checkpoint_expired()` 가 `False` 를 반환해 실제 stale 캐시를 fresh 로 간주할 수 있다.
- **B4. 부분 실패 정보는 `status` 에 반영되지 않음** — `ensure_ready()` 이후 부분 실패를 보려면 `CacheReadyResult.sync_result.failures` 를 함께 읽어야 한다.
- **B5. `CacheGapReport` 정합성 검증 비대칭** — `missing_draws=()` 인데 `is_continuous=False` 인 잘못된 조합을 생성자 수준에서 막지 않는다.
- **D1. 단일 스레드 사용 가정 미명시** — 동시 호출 직렬화는 외부 책임인데 클래스 docstring 에 그 전제가 아직 없다.

## 범위 외 항목 / 오해 방지
- `tests/test_cache_store.py` 의 `JsonDrawCacheStore` 계약은 현재 module_2 산출물이 아니다.
- 본 모듈은 **JSON 파일 캐시 구현이 아니라 SQLite 기반 Backend 저장소 위의 정책 계층**이다.
- 통계 계산, 추천 조합 생성, 리포트 출력, HTTP 재시도 정책, DB 스키마 변경은 본 모듈 책임이 아니다.

## 후속 작업 (다음 작업자 체크리스트)
1. `frontend_dev_module_3` 담당자
   - `get_all_draws()` 의 오름차순 반환을 통계 입력 기본 계약으로 사용한다.
   - 최근 회차 기준 보조 정보가 필요하면 `get_recent_draws(n)` 을 별도로 사용하고, 정렬 방향을 혼동하지 않는다.
   - `ensure_ready()` 호출 후에는 `status` 뿐 아니라 `sync_result.failures` 도 함께 확인할지 결정한다.
2. 추천기/리포트 담당자
   - 사용자 표시용 최신 회차/신선도 배지는 `status()` 결과를 사용한다.
   - offline 실행을 지원해야 하면 `CacheConfig(offline=True)` 경로를 그대로 재사용한다.
3. 후속 유지보수 task
   - B1: `ensure_ready()` 의 상태 재계산 경로를 단일 I/O 중심으로 정리한다.
   - B2/B3: datetime 정책을 Backend와 함께 정규화하고, clock 실패 시 보수적 만료 처리 여부를 결정한다.
   - B5/D1: 모델 불변식 대칭 보강과 단일 스레드 가정 명시를 별도 소규모 패치로 처리한다.
4. QA Engineer
   - 정책 계층 회귀는 `tests/cache` 기준으로 PASS 상태다.
   - 통합 회귀에서는 실제 `LottoStorage` + `LottoCollector` 조합으로 `ensure_ready()` 경로를 재확인한다.
   - 과거 JSON 저장소 골격 테스트는 현재 스코프와 분리해 해석해야 한다.

## 미완료 / 미해결
- 실제 `LottoStorage` 와 `LottoCollector` 를 함께 연결한 통합 테스트는 이번 verify 범위에서 새로 추가하지 않았다.
- mailbox 도구(`read_mailbox`, `send_mailbox_message`, `ack_mailbox_message`)가 현재 런타임에 노출되지 않아 구조화된 메일박스 handoff 는 수행하지 못했고, 파일 handoff 로 대체한다.

## 참조
- 범위 문서: `docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md`
- 코드 리뷰: `artifacts/frontend_dev_code_reviewer/2026-04-17-module-2-review.md`
- 선행 handoff: `docs/handoff/frontend_dev_module_1.md`
- 상위 의존 handoff: `docs/handoff/backend_dev.md`

## Signature
[frontend_dev] module_2 검증 완료 · WARN 리스크와 후속 작업 인계.
