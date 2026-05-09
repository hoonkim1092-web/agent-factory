# Code Review — backend_dev_module_8

- 작성 시각: 2026-04-17
- 리뷰어 역할: `backend_dev_code_reviewer`
- 대상 작업: `backend_dev_module_8_build_2`
- 리뷰 범위: `src/lotto_predictor/backend/**`
- 결론 판정: **WARN** (BLOCK 없음, 개선 권고 다수)

## 리뷰 대상 파일
| 경로 | 역할 | 비고 |
| --- | --- | --- |
| `src/lotto_predictor/backend/__init__.py` | 공개 심볼 묶음 | `__all__` 정의 OK |
| `src/lotto_predictor/backend/models.py` | 도메인 dataclass·예외 | frozen + `__post_init__` 검증 |
| `src/lotto_predictor/backend/schema.sql` | SQLite DDL | `IF NOT EXISTS` 멱등성 |
| `src/lotto_predictor/backend/storage.py` | SQLite 영속 계층 | WAL + `BEGIN IMMEDIATE` 트랜잭션 |
| `src/lotto_predictor/backend/serialization.py` | JSON → 도메인 변환 | 순수 함수 |
| `src/lotto_predictor/backend/http_client.py` | 동행복권 HTTP 클라이언트 | 재시도/백오프/rate limit |

## 보안 (OWASP)
- HTTPS 엔드포인트 사용(`https://www.dhlottery.co.kr/...`), `requests` 기본 SSL 검증 활성. ✓
- SQL 전부 매개변수화(`?` 또는 named param). 인젝션 표면 없음. ✓
- 외부 응답은 `parse_draw`에서 타입·범위 검증 후 도메인 타입 진입. ✓
- 인증·세션·역직렬화 위험 없음. `eval/pickle/yaml.load` 미사용. ✓
- `db_path`는 호출자 신뢰 입력. 데스크톱 단일 프로세스 전제이므로 수용 가능.
- **보안 이슈: 없음.**

## 버그 / 엣지 케이스

### B1. 마지막 시도 후 불필요한 백오프 슬립 — http_client.py:88-104, 165-168
```python
for attempt in range(self._max_retries + 1):  # 0..max_retries
    ...
    self._sleep_backoff(attempt)
    continue
...
raise TransientFetchError(...)
```
- `attempt = max_retries` 가 마지막 시도다. 이 시도까지 실패하면 `_sleep_backoff(max_retries)`가 한 번 더 호출되어(기본값 0.5×2³ = 4초) 즉시 실패하지 못하고 대기한다.
- **권고**: `if attempt < self._max_retries: self._sleep_backoff(attempt)` 가드로 최종 시도 후의 슬립을 생략한다.

### B2. JSON 디코드 실패가 영구 오류로 분류됨 — http_client.py:125-130
```python
try:
    payload: Any = response.json()
except ValueError as exc:
    raise ValueError(...)  # 즉시 종료, 재시도 없음
```
- 동행복권이 일시적으로 HTML 점검 페이지(200 OK)를 반환하면 JSON 파싱이 깨진다. 현재 구현은 즉시 `ValueError`로 중단하므로 일시 장애에 약하다.
- **권고**: 200 응답이지만 JSON 디코드 실패 시 `TransientFetchError`로 분류해 백오프 재시도 대상에 포함시킨다.

### B3. `datetime.now()` 시간대 미지정 — http_client.py:146, 호출자 영향
- `FetchResult.fetched_at`이 naive datetime. `LottoStorage.set_checkpoint`에서 `isoformat`/`fromisoformat` round-trip은 동작하지만 OS 로캘에 따라 UTC 오프셋 정보가 사라진다.
- **권고**: `datetime.now(timezone.utc)`로 통일하고 `models.FetchCheckpoint.fetched_at` 도 aware datetime을 기대한다고 docstring에 명시. 또는 ISO 8601 Z 표기로 직렬화.

### B4. 200 이외의 비재시도 상태 코드가 모두 `DrawNotFoundError`로 매핑 — http_client.py:119-123
```python
if response.status_code != 200:
    raise DrawNotFoundError(...)
```
- 401/403/451 같은 권한·차단 상태도 "회차 없음"으로 분류된다. 의미가 어긋난다.
- 영향도는 낮음(동행복권 공식 API는 인증 없음). 현재 코드는 동작에 문제 없으나 분류 정확도가 떨어진다.
- **권고**: 4xx 중 408/429만 재시도 대상이고 그 외 4xx는 별도 `BackendError` 하위 타입(예: `PermanentFetchError`) 또는 메시지를 분리해 관측성을 높인다.

### B5. `executescript` + `isolation_level=None` 상호작용 — storage.py:65-66
- `sqlite3` 문서상 `executescript`는 자체적으로 `commit`을 호출한다. 본 코드는 이를 인지해 외부 트랜잭션을 두지 않았으므로 동작은 정상이다. 다만 향후 누군가가 `with _transaction(conn): conn.executescript(...)` 형태로 감싸면 "no transaction is active" 류 오류가 난다.
- **권고**: `ensure_schema` 도큐스트링에 "executescript는 자체 트랜잭션을 사용하므로 `_transaction`으로 감싸지 말 것" 한 줄 추가.

### B6. `LottoStorage`의 스레드 안전성 — storage.py:35
```python
sqlite3.connect(str(self._db_path), isolation_level=None)
```
- `check_same_thread` 기본값은 True. PyInstaller 단일 스레드 전제이므로 현재는 OK이지만, GUI 진화 시 백그라운드 수집 스레드를 도입하면 즉시 깨진다.
- **권고**: scope 문서에 "동일 인스턴스를 두 스레드에서 공유하지 말 것" 명시 또는 `threading.local` 기반 연결 풀 도입을 후속 과제로 등록.

### B7. 스키마 마이그레이션 미지원 — schema.sql, storage.py
- 모든 DDL이 `CREATE TABLE IF NOT EXISTS`. 컬럼 추가/타입 변경 시 기존 사용자 DB를 자동으로 마이그레이션하지 못한다.
- v1 단계에서는 수용 가능하나, 향후 `tot_sell_amnt` 등 컬럼이 늘어나면 침묵하는 스키마 드리프트가 발생한다.
- **권고**: `schema_version` 메타 테이블과 단순 마이그레이션 스텝을 후속 작업으로 등록.

### B8. `_optional_int` 가 silent fail — serialization.py:80-87
```python
def _optional_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
```
- 외부 응답이 `"1,234,567,890"` 같은 콤마 포함 문자열이면 None으로 떨어져 매출/당첨금이 영구히 NULL이 된다. 현재 동행복권 API는 정수 그대로지만 변경 가능성이 있다.
- **권고**: 변환 실패 시 `_LOGGER.warning`으로 로깅하거나, 문자열 정제(콤마 제거) 후 재시도.

### B9. `LottoStorage.get_draws(limit=0)` 의 반환 — storage.py:117-129
- `limit < 0` 만 검증하고 `limit=0`은 SQL `LIMIT 0`이 되어 빈 리스트 반환. 호출자가 의도적으로 "0개" 가져오려 했는지 확인 어렵다.
- 영향 미미. 의미가 모호하므로 `limit=0`도 ValueError로 거절하거나 docstring에 동작 명시.

## 설계 품질
- **단일 책임**: http_client(네트워크), storage(SQLite), serialization(매핑), models(값 객체)로 깔끔하게 분리. ✓
- **의존 방향**: backend → 외부(`requests`, `sqlite3`) 단방향. 상위 모듈 미참조. ✓
- **공개 API 일관성**: `__init__.py`의 `__all__`이 scope 계약과 일치. ✓
- **프리즘 도메인 객체**: `frozen=True` dataclass + `__post_init__` 검증으로 불변식 강제. ✓
- **컨텍스트 매니저**: `DhLotteryClient`, `LottoStorage` 모두 `__enter__/__exit__` 제공. ✓
- 개선점: `_NUMBER_KEYS` 같은 상수가 모듈 사적인데 `parse_draw` 외 다른 함수에서 재사용 시 외부 노출 필요할 수 있음(현재 OK).

## 에러 처리
- 예외 계층(`BackendError` → `DrawNotFoundError`/`TransientFetchError`)이 명확. ✓
- `parse_draw`는 타입 오류와 누락 키를 `ValueError`로, 비정상 응답을 `DrawNotFoundError`로 분기. ✓
- `_transaction.__exit__`의 ROLLBACK 자체가 실패하면 원래 예외가 가려진다. SQLite 단일 프로세스에서는 거의 발생 안 하지만, `try/except` 로 가린 후 `__cause__` 보존이 더 안전.
- 개선 포인트는 위 B1, B2, B4 참조.

## 성능
- `executemany` 일괄 upsert. ✓
- `idx_lotto_draw_date` 인덱스 정의. ✓
- `read_number_frequency`, `get_draws`는 단순 정렬 SELECT. 회차 500건 규모에서 부담 없음.
- O(n²) 루프, N+1 쿼리 없음.
- HTTP 호출은 회차당 1회 + 재시도 시 최대 3회 백오프. 500회차 풀 수집 = ~500×0.2s ≈ 100초. 사용자 인내 범위 내.
- WAL 모드로 읽기/쓰기 병행 시 잠금 경합 완화. ✓

## scope 계약 준수도
| 계약 항목 | 결과 |
| --- | --- |
| 4개 파일(http_client/storage+schema/models/serialization) 구현 | ✓ |
| 공개 시그니처 일치 | ✓ (DhLotteryClient.fetch_draw, LottoStorage 7종, parse_draw) |
| SQLite 스키마 DDL 일치 | ✓ |
| 외부 의존성: `requests` + stdlib | ✓ |
| 구현 순서 6단계 | ✓ (`__init__`이 마지막에 공개 심볼 정리) |
| 비소유 범위 침범 없음 | ✓ (수집 오케스트레이션·캐시 규칙·번호 규칙 미포함) |

## 권고 우선순위
1. **WARN-Hi (다음 build에서 처리 권장)**: B1(불필요한 백오프), B2(JSON 디코드 실패 분류), B3(naive datetime).
2. **WARN-Med (백로그)**: B4(상태코드 분류 정밀화), B8(silent fail 로깅).
3. **WARN-Lo (문서 보강)**: B5, B6, B7, B9.

## 결론
- **PASS 항목**: 보안, 설계, 성능, scope 준수.
- **WARN 항목**: 위 B1~B9. 모두 동작에는 영향이 없으며, 운영·관측성·확장성 개선 권고다.
- **BLOCK 항목**: 없음.
- 다음 단계(`backend_dev_module_8_verify_*`)에서 QA 시나리오와 통합 검증을 진행할 수 있다. Frontend Dev 수집기/캐시 모듈은 본 공개 API에 의존해 build 가능 상태다.

## JSON 결과
```json
{
  "verdict": "WARN",
  "issues": [
    {"id": "B1", "severity": "warn-hi", "file": "src/lotto_predictor/backend/http_client.py", "line_range": "88-104,165-168", "summary": "마지막 시도 후 불필요한 _sleep_backoff 호출"},
    {"id": "B2", "severity": "warn-hi", "file": "src/lotto_predictor/backend/http_client.py", "line_range": "125-130", "summary": "200 OK + JSON 디코드 실패가 영구 오류로 분류되어 재시도 미발생"},
    {"id": "B3", "severity": "warn-hi", "file": "src/lotto_predictor/backend/http_client.py", "line_range": "146", "summary": "datetime.now() naive 사용 — UTC aware로 통일 권고"},
    {"id": "B4", "severity": "warn-med", "file": "src/lotto_predictor/backend/http_client.py", "line_range": "119-123", "summary": "비-200/비-재시도 코드 전부가 DrawNotFoundError로 분류됨"},
    {"id": "B5", "severity": "warn-lo", "file": "src/lotto_predictor/backend/storage.py", "line_range": "61-66", "summary": "executescript는 자체 트랜잭션 사용 — docstring 가드 필요"},
    {"id": "B6", "severity": "warn-lo", "file": "src/lotto_predictor/backend/storage.py", "line_range": "35", "summary": "check_same_thread 기본값 True — 다중 스레드 진화 시 위험"},
    {"id": "B7", "severity": "warn-lo", "file": "src/lotto_predictor/backend/schema.sql", "line_range": "all", "summary": "스키마 마이그레이션 미지원 — schema_version 메타 테이블 후속 권고"},
    {"id": "B8", "severity": "warn-med", "file": "src/lotto_predictor/backend/serialization.py", "line_range": "80-87", "summary": "_optional_int 변환 실패 silent → 로깅 또는 정제 후 재시도 권고"},
    {"id": "B9", "severity": "warn-lo", "file": "src/lotto_predictor/backend/storage.py", "line_range": "117-129", "summary": "limit=0 동작 모호 — docstring 명시 또는 ValueError 처리"}
  ],
  "summary": "보안·설계·성능·scope 준수 모두 통과. 재시도 정책의 백오프/JSON 처리, naive datetime, 상태코드 분류 등 운영 관측성·견고성 측면 개선 권고 9건. BLOCK 없음, verify 단계로 진행 가능."
}
```
