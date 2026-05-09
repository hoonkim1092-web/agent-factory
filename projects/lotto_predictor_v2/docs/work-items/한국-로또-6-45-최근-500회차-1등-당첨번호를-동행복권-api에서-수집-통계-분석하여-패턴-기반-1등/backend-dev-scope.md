# Backend Dev 구현 범위 정의 (module_8)

## 메타데이터
- task_id: backend_dev_module_8_scope_1
- module_id: backend_dev_module_8
- owner_role: Backend Dev
- phase: scope
- 작성일: 2026-04-17
- 상태: fixed
- 문서 언어: 한국어 (OS: `ko-KR`)

## 목적
프로젝트 전체에서 **서버·데이터·외부 연동 레이어**를 담당한다. Frontend Dev가 소유한 상위 모듈(수집기, 캐시, 통계 엔진, 추천기, 터미널 리포트, 빌드 스펙, 가이드)이 직접 사용할 **재사용 가능한 저수준 어댑터**를 제공한다. 상위 모듈의 비즈니스 로직은 여기서 다루지 않는다.

## 소유 범위 (In-Scope)
1. **동행복권 HTTP 클라이언트** (`src/lotto_predictor/backend/http_client.py`)
   - 엔드포인트: `https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={n}`
   - 회차 단건 조회, 타임아웃, 재시도 정책, rate limit 대응, User-Agent 설정
   - 네트워크 장애 분류: 일시 오류(재시도) / 영구 오류(중단) / 스키마 오류(경고)
2. **SQLite 영속 계층** (`src/lotto_predictor/backend/storage.py`, `src/lotto_predictor/backend/schema.sql`)
   - 연결 관리, 스키마 초기화/마이그레이션, 트랜잭션 경계
   - 테이블: `lotto_draw`, `number_frequency`, `fetch_checkpoint`
3. **도메인 데이터 타입** (`src/lotto_predictor/backend/models.py`)
   - `LottoDraw`, `FetchCheckpoint`, `DrawNotFoundError`, `FetchResult` 등 dataclass/Enum
4. **JSON 직렬화 유틸** (`src/lotto_predictor/backend/serialization.py`)
   - 외부 API 응답 → 도메인 타입 매핑, 검증, 실패 시 예외 전파

## 비소유 범위 (Out-Of-Scope)
- 수집 파이프라인 오케스트레이션(증분 수집 루프, 진행 표시) → Frontend Dev 수집기 모듈
- 캐시 조회/업서트 비즈니스 규칙(최근 N회차 필터 등) → Frontend Dev 캐시 모듈
- 통계/추천/리포트/빌드/가이드 → Frontend Dev 각 모듈
- 게임 규칙(번호 유효성, 중복 검사 등) → Game Logic Dev
- 테스트 시나리오·회귀 검증 → QA Engineer

## 공개 인터페이스 계약

### 1. `http_client.py`
```python
class DhLotteryClient:
    def __init__(self, timeout: float = 5.0, max_retries: int = 3, user_agent: str = ...): ...
    def fetch_draw(self, draw_no: int) -> FetchResult: ...
    def close(self) -> None: ...

@dataclass(frozen=True)
class FetchResult:
    draw_no: int
    payload: dict  # 원본 JSON
    fetched_at: datetime

class DrawNotFoundError(Exception): ...  # returnValue != "success"
class TransientFetchError(Exception): ...  # 재시도 후에도 네트워크 실패
```

### 2. `storage.py`
```python
class LottoStorage:
    def __init__(self, db_path: Path): ...
    def __enter__(self) -> "LottoStorage": ...
    def __exit__(self, *exc) -> None: ...

    # 스키마
    def ensure_schema(self) -> None: ...

    # 회차
    def upsert_draws(self, draws: Iterable[LottoDraw]) -> int: ...
    def get_draws(self, *, limit: int | None = None, since_no: int | None = None) -> list[LottoDraw]: ...
    def get_draw(self, draw_no: int) -> LottoDraw | None: ...

    # 체크포인트
    def get_checkpoint(self) -> FetchCheckpoint | None: ...
    def set_checkpoint(self, cp: FetchCheckpoint) -> None: ...

    # 빈도 캐시(집계 결과 저장용)
    def write_number_frequency(self, rows: Iterable[NumberFrequencyRow]) -> None: ...
    def read_number_frequency(self) -> list[NumberFrequencyRow]: ...
```

### 3. `models.py`
```python
@dataclass(frozen=True)
class LottoDraw:
    drw_no: int
    drw_date: date
    numbers: tuple[int, int, int, int, int, int]
    bonus_no: int
    tot_sell_amnt: int | None
    first_win_amnt: int | None

@dataclass(frozen=True)
class FetchCheckpoint:
    last_fetched_drw_no: int
    fetched_at: datetime
    source_url: str

@dataclass(frozen=True)
class NumberFrequencyRow:
    number: int
    count: int
    last_seen_drw_no: int
    recent_50_count: int
```

### 4. `serialization.py`
```python
def parse_draw(payload: dict) -> LottoDraw: ...  # 실패 시 DrawNotFoundError 또는 ValueError
```

## 데이터 스키마 (SQLite)
```sql
CREATE TABLE IF NOT EXISTS lotto_draw (
    drw_no INTEGER PRIMARY KEY,
    drw_date TEXT NOT NULL,
    n1 INTEGER NOT NULL, n2 INTEGER NOT NULL, n3 INTEGER NOT NULL,
    n4 INTEGER NOT NULL, n5 INTEGER NOT NULL, n6 INTEGER NOT NULL,
    bonus_no INTEGER NOT NULL,
    tot_sell_amnt INTEGER,
    first_win_amnt INTEGER
);
CREATE TABLE IF NOT EXISTS fetch_checkpoint (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_fetched_drw_no INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    source_url TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS number_frequency (
    number INTEGER PRIMARY KEY,
    count INTEGER NOT NULL,
    last_seen_drw_no INTEGER NOT NULL,
    recent_50_count INTEGER NOT NULL
);
```

## 의존성
- 외부 라이브러리: `requests` (HTTP), Python stdlib `sqlite3`, `dataclasses`, `datetime`, `pathlib`, `json`, `logging`
- 프로젝트 내부 의존성: 없음 (최하위 레이어)
- 역방향 소비자: Frontend Dev 수집기/캐시 모듈이 본 레이어를 import 한다

## 산출물 (Deliverables)
- `src/lotto_predictor/backend/__init__.py`
- `src/lotto_predictor/backend/http_client.py`
- `src/lotto_predictor/backend/storage.py`
- `src/lotto_predictor/backend/schema.sql`
- `src/lotto_predictor/backend/models.py`
- `src/lotto_predictor/backend/serialization.py`
- `docs/work-items/한국-로또-.../backend-dev-scope.md` (본 문서)

## 구현 순서 (Fixed)
1. `models.py` — 도메인 타입을 먼저 확정하여 이후 모듈의 시그니처를 고정한다.
2. `schema.sql` + `storage.py` — 스키마 DDL과 `LottoStorage` 최소 골격(`ensure_schema`, 컨텍스트 매니저).
3. `serialization.py` — 외부 JSON → `LottoDraw` 매핑.
4. `http_client.py` — `DhLotteryClient.fetch_draw` (재시도·타임아웃 포함).
5. `storage.py` 나머지 메서드(`upsert_draws`, `get_draws`, 체크포인트, 빈도 테이블 I/O).
6. 모듈 `__init__.py` 공개 심볼 정리.

## 완료 기준 (Scope 단계)
- [x] Backend Dev 구현 범위가 In/Out-Of-Scope로 명확히 분리되었다.
- [x] 4개 파일(http_client, storage+schema, models, serialization)의 공개 시그니처가 확정되었다.
- [x] SQLite 스키마 DDL이 본 문서에 고정되었다.
- [x] 외부 의존성(`requests` + stdlib)과 Frontend Dev 측 소비자가 명시되었다.
- [x] 구현 순서 6단계가 번호로 고정되었다.

## 리스크와 완화
- 동행복권 API 스키마 변경: `serialization.parse_draw`에서 필수 키 검증 후 `DrawNotFoundError` 또는 `ValueError` 발생 → 상위 수집기가 처리.
- Rate limit / IP 차단: `DhLotteryClient`에 요청 간 최소 간격(기본 0.2s)과 지수 백오프 적용.
- SQLite 동시성: 단일 프로세스(PyInstaller 단일 실행 파일) 전제. WAL 모드 + 트랜잭션 래핑.

## 다음 단계 핸드오프
- build 단계(`backend_dev_module_8_build_1`)에서 위 6단계 순서대로 구현한다.
- Frontend Dev 수집기/캐시 모듈은 본 문서의 공개 인터페이스를 기반으로 구현 착수 가능.
