# Backend Dev Handoff (module_8)

## 목적
이 문서는 `Backend Dev`(module_8) 구현 결과를 검증한 뒤, 후속 `frontend_dev`(수집기·캐시·통계 엔진) 및 `qa_engineer` 가 본 레이어의 공개 API 와 잔여 리스크를 즉시 이어받을 수 있도록 고정한다.

## 메타데이터
- task_id: backend_dev_module_8_verify_3
- 작성 일자: 2026-04-17
- 문서 언어: 한국어 (OS: `ko-KR`)
- 상태: verify 완료
- 선행 작업:
  - `backend_dev_module_8_scope_1` (완료)
  - `backend_dev_module_8_build_2` (완료)
  - `backend_dev_module_8_code_review` (완료, 판정 WARN)

## 검증 대상
- `src/lotto_predictor/backend/__init__.py`
- `src/lotto_predictor/backend/models.py`
- `src/lotto_predictor/backend/schema.sql`
- `src/lotto_predictor/backend/storage.py`
- `src/lotto_predictor/backend/serialization.py`
- `src/lotto_predictor/backend/http_client.py`

## 실행한 검증
### 1. 구문·임포트 점검
- 명령: `python -m py_compile src/lotto_predictor/backend/*.py`
- 결과: 오류 없음.
- 명령: `PYTHONPATH=src python -c "from lotto_predictor.backend import ..."` (공개 심볼 10개 전수 임포트).
- 결과: `import OK`.

### 2. `parse_draw` 스모크
- 정상 응답: `returnValue=success` + `drwNo=1120` + 무작위 순서 본번호 → `(1,2,3,4,5,6)` 로 오름차순 정렬되어 반환. ✓
- `returnValue=fail` → `DrawNotFoundError` 발생. ✓
- 필수 키 누락(`drwNoDate`) → `ValueError("필수 키 누락: drwNoDate")`. ✓

### 3. `LottoDraw` 도메인 불변식
- 중복 본번호 `(1,1,2,3,4,5)` → `ValueError("본 번호에 중복이 있다")`. ✓
- 비오름차순·보너스 중복·범위 초과 등 나머지 불변식은 scope 계약대로 `__post_init__` 에서 방어된다.

### 4. `LottoStorage` 왕복
- 임시 디렉터리(`tempfile.TemporaryDirectory`)에 `LottoStorage` 컨텍스트 매니저로 WAL DB 생성.
- 시나리오:
  - `upsert_draws([draw])` → `get_draws()` = 1건 반환.
  - `set_checkpoint(FetchCheckpoint(1120, ...))` → `get_checkpoint().last_fetched_drw_no == 1120`.
  - `write_number_frequency(...)` / `read_number_frequency()` = 2건 왕복.
  - 동일 `drw_no` 재 upsert 시 행 수 1 유지(멱등). ✓
  - `get_draws(since_no=1200)` = `[]`(배타적 하한선 동작). ✓

### 5. `DhLotteryClient` 정책 점검(네트워크 차단, `unittest.mock.MagicMock` 세션 주입)
- 200 + `returnValue=success` → `FetchResult(draw_no=10, payload=...)` 반환. ✓
- HTTP 500 반복(`max_retries=1`) → 최종 `TransientFetchError`. ✓
- HTTP 404 → 즉시 `DrawNotFoundError`. ✓
- `min_interval` / 지수 백오프(`backoff_base * 2**attempt`) 경로가 정상 경유됨.

## 스코프 계약 준수도
| 계약 항목 | 결과 |
| --- | --- |
| 4개 파일(http_client, storage+schema, models, serialization) 구현 | ✓ |
| 공개 시그니처 일치 (`DhLotteryClient.fetch_draw`, `LottoStorage` 7종, `parse_draw`) | ✓ |
| SQLite 스키마 DDL 일치 (`lotto_draw`, `fetch_checkpoint`, `number_frequency`, `idx_lotto_draw_date`) | ✓ |
| 외부 의존성(`requests` + stdlib `sqlite3`/`datetime`/`pathlib`/`json`/`logging`) | ✓ |
| 구현 순서 6단계 고정 | ✓ |
| 비소유 범위 침범 없음(수집 오케스트레이션·캐시 규칙·추천 규칙·빌드 미포함) | ✓ |

## 공개 인터페이스 요약 (소비자 참조용)
```python
from lotto_predictor.backend import (
    DhLotteryClient,
    LottoStorage,
    parse_draw,
    LottoDraw,
    FetchCheckpoint,
    FetchResult,
    NumberFrequencyRow,
    BackendError,
    DrawNotFoundError,
    TransientFetchError,
)
```
- `DhLotteryClient(timeout=5.0, max_retries=3, user_agent=..., min_interval=0.2, backoff_base=0.5, session=None)`
  - `fetch_draw(draw_no: int) -> FetchResult`
  - `close()` / `__enter__` / `__exit__`
- `LottoStorage(db_path: Path | str)`
  - `ensure_schema()`
  - `upsert_draws(iterable[LottoDraw]) -> int`
  - `get_draws(*, limit=None, since_no=None) -> list[LottoDraw]`
  - `get_draw(draw_no: int) -> LottoDraw | None`
  - `get_checkpoint() -> FetchCheckpoint | None`
  - `set_checkpoint(cp: FetchCheckpoint) -> None`
  - `write_number_frequency(iterable[NumberFrequencyRow]) -> None`
  - `read_number_frequency() -> list[NumberFrequencyRow]`
- `parse_draw(payload: dict) -> LottoDraw`  (`DrawNotFoundError` / `ValueError`)

## 코드 리뷰 요약 참조
- 파일: `artifacts/backend_dev_code_reviewer/2026-04-17-module-8-review.md`
- 판정: **WARN** (BLOCK 0건, 보안·설계·성능·scope 모두 PASS)
- 주요 권고(운영 관측성·견고성 관련) 9건. 동작에는 영향이 없으므로 본 verify 단계에서는 수용 보류한다. 후속 소비 모듈에서 재현될 가능성이 있는 항목만 아래 "잔여 리스크"에 선별 기록한다.

## 잔여 리스크 (후속 작업자 참고)
1. **마지막 시도 후 불필요한 백오프 대기 (B1)** — `DhLotteryClient.fetch_draw` 최종 실패 경로가 `_sleep_backoff` 를 한 번 더 호출해 약 `backoff_base * 2**max_retries` 초만큼 지연된다. 사용자 체감 실패 지연에 영향. 수집기(`frontend_dev_module_1`)에서 총 타임아웃 예산을 잡을 때 이 여분을 고려한다.
2. **200 OK + 비-JSON 응답의 즉시 영구 실패 처리 (B2)** — `response.json()` 실패 시 즉시 `ValueError` 가 나 재시도되지 않는다. 동행복권이 점검 HTML을 200으로 반환하는 희귀 사례에 약하다. 수집기 레벨에서 자체 재시도를 붙이거나, 후속 patch 로 `TransientFetchError` 로 분류하도록 조정할 수 있다.
3. **`FetchResult.fetched_at` naive datetime (B3)** — `datetime.now()` 로 생성되어 시간대 정보가 없다. `LottoStorage.set_checkpoint` 왕복은 동작하나 리포트에서 시각을 표시할 때 "로컬 시간"임을 명시하고, UTC 변환이 필요하면 상위에서 수행한다.
4. **비-200/비-재시도 HTTP 상태의 `DrawNotFoundError` 단일화 (B4)** — 401/403/451 도 "회차 없음" 으로 분류된다. 동행복권 공식 API는 인증이 없어 현재는 무해하나, 관측성은 낮다. 수집기 로그에 상태 코드를 함께 남길 것을 권장.
5. **`_optional_int` silent fail (B8)** — `totSellamnt` 가 문자열(`"1,234,...")로 바뀌면 NULL 로 떨어진다. 리포트/통계에서 해당 필드를 활용하기 전에 원본 타입을 확인한다.
6. **스키마 마이그레이션 미지원 (B7)** — 컬럼 추가 변경 시 기존 사용자 DB가 자동 마이그레이션되지 않는다. 초기 배포에서는 수용 가능. 향후 컬럼이 추가되면 `schema_version` 메타 테이블 도입이 필요하다.
7. **단일 스레드 전제 (B6)** — `sqlite3.connect(check_same_thread=True)` 기본값 유지. GUI/백그라운드 수집 스레드를 도입하면 즉시 깨진다. 현재 수집기/캐시/통계가 동일 스레드에서 동작한다는 계약을 유지한다.
8. **빈도 캐시 전체 치환 (`write_number_frequency`)** — 트랜잭션으로 테이블을 비우고 재삽입한다. 동시 소비자가 있는 상황을 가정하지 않는다.
9. **`LottoStorage.get_draws(limit=0)`** — `LIMIT 0` → 빈 리스트. 의도적 0 요청과 혼동될 수 있어 호출자는 `limit=0` 대신 `limit=None`/생략을 사용한다.

## 후속 작업자 (Frontend Dev · Game Logic Dev · QA) 즉시 체크리스트

### 수집기(`frontend_dev_module_1`)
- `from lotto_predictor.backend import DhLotteryClient, parse_draw, DrawNotFoundError, TransientFetchError, FetchResult` 를 사용한다.
- 증분 수집 루프는 `DrawNotFoundError` 발생 직전 회차를 "최신 확정 회차" 로 간주한다.
- 세션/재시도 정책은 `DhLotteryClient` 내부에서 책임지므로 이중 래핑하지 않는다.
- 본 레이어의 `FetchResult.payload` 를 그대로 `parse_draw` 에 전달해 `LottoDraw` 로 변환한다.

### 캐시 저장소(`frontend_dev_module_2`)
- `LottoStorage(db_path).__enter__()` 로 컨텍스트 매니저 진입 시 `ensure_schema()` 가 자동 호출된다.
- 상위에서 별도 `BEGIN/COMMIT` 을 쓰지 말 것. 내부 `_transaction` 이 이미 `BEGIN IMMEDIATE` 래핑한다.
- 최근 N회차 필터는 `get_draws(limit=N, since_no=...)` 조합으로 표현 가능. 비즈니스 규칙(최신 500회차 정의)은 캐시 모듈이 소유한다.

### 통계 엔진(`frontend_dev_module_3`)
- `read_number_frequency()` / `write_number_frequency(rows)` 로 빈도 캐시를 주고받는다.
- 집계 재계산은 트랜잭션으로 테이블이 원자적으로 치환된다는 점을 전제한다.

### Game Logic Dev (`game_logic_dev`)
- `StatisticsSummary` 입력의 `number_frequency` 는 본 레이어의 `NumberFrequencyRow.count` 를 직접 채울 수 있다.
- `number_last_seen` 의 의미 정의는 통계 엔진 단계에서 확정될 예정이므로, 현재는 본 레이어에서 해당 의미를 부여하지 않는다.

### QA Engineer (`qa_engineer_module_10`)
- `artifacts/qa_engineer/core-flow-checklist.md` 의 smoke 시나리오에 본 handoff 의 5개 실행 단계를 그대로 활용할 수 있다.
- 네트워크 차단 환경에서도 `DhLotteryClient` 는 `session=` 주입으로 완전 재현 가능하다.

## 메일박스 / 교차검증 기록
- 런타임에 `read_mailbox` / `send_mailbox_message` 가 도구로 노출되지 않아 메일박스 핸드오프는 수행 못 했다. 파일 handoff(본 문서)로 대체한다.
- 설계 수준 변경이 없어 `docs/plans/YYYY-MM-DD-*.md` 신규 설계문서는 작성하지 않았다(`[Design Review Contract]` 면제 조건 — 구현은 scope 단계에서 고정된 계약 내에서 끝남).

## 결론
- Backend Dev module_8 구현은 scope 계약을 충족하며 검증을 통과했다.
- 코드 리뷰 판정 WARN 9건은 BLOCK 없음. 위 잔여 리스크로 후속 작업자에게 인계한다.
- 후속 `frontend_dev_module_1/2/3` 는 본 문서의 공개 API만 참조해 build 를 시작할 수 있다.
