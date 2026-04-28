# SQLite 기반 당첨번호 캐시 저장소 — 범위 및 인터페이스 정의

## 메타데이터
- 작업 ID: `backend_dev_module_2_scope_1`
- 작성자: backend_dev
- 작성일: 2026-04-16
- 상태: 확정

---

## 1. 모듈 목적

동행복권 API에서 수집한 `DrawResult` 데이터를 SQLite 데이터베이스에 캐싱하여,
동일 회차를 재요청하지 않고 로컬에서 즉시 조회할 수 있게 한다.
인터넷 미연결 시에도 캐시된 데이터로 분석·추천이 가능하도록 보장한다.

---

## 2. 범위

### 포함
| 항목 | 설명 |
|------|------|
| 테이블 생성 | `draws` 테이블 자동 생성 (IF NOT EXISTS) |
| 단건 저장 | `DrawResult` → SQLite INSERT |
| 벌크 저장 | `list[DrawResult]` → 트랜잭션 내 일괄 INSERT |
| 단건 조회 | 회차 번호로 `DrawResult` 조회 |
| 범위 조회 | 회차 범위(start~end)로 `list[DrawResult]` 조회 |
| 전체 조회 | 저장된 모든 `DrawResult` 조회 |
| 캐시된 회차 목록 | 저장된 회차 번호 집합 반환 (`set[int]`) |
| 건수 조회 | 저장된 총 레코드 수 반환 |
| 중복 무시 | 이미 존재하는 회차는 INSERT OR IGNORE로 건너뜀 |
| 연결 관리 | 컨텍스트 매니저 지원 (`with` 구문) |

### 제외
| 항목 | 사유 |
|------|------|
| API 수집 | `fetcher` 모듈 책임 |
| 통계 계산 | `analysis` 모듈 책임 |
| 캐시 만료/삭제 | 로또 데이터는 불변이므로 캐시 무효화 불필요 |
| 마이그레이션 | 스키마 v1 단일 버전, 향후 필요 시 별도 모듈 |

---

## 3. 데이터베이스 스키마

### draws 테이블
```sql
CREATE TABLE IF NOT EXISTS draws (
    draw_no        INTEGER PRIMARY KEY,
    draw_date      TEXT    NOT NULL,   -- ISO 8601 (YYYY-MM-DD)
    num1           INTEGER NOT NULL,
    num2           INTEGER NOT NULL,
    num3           INTEGER NOT NULL,
    num4           INTEGER NOT NULL,
    num5           INTEGER NOT NULL,
    num6           INTEGER NOT NULL,
    bonus          INTEGER NOT NULL,
    total_sell_amount    INTEGER NOT NULL DEFAULT 0,
    first_prize_amount   INTEGER NOT NULL DEFAULT 0,
    first_prize_winners  INTEGER NOT NULL DEFAULT 0,
    fetched_at     TEXT    NOT NULL    -- ISO 8601 datetime (저장 시각)
);
```

### 설계 결정
- `draw_no`를 PRIMARY KEY로 사용하여 중복 INSERT를 자연스럽게 방지한다.
- 당첨 번호 6개를 `num1`~`num6` 개별 컬럼으로 저장하여 SQL 쿼리에서 직접 활용 가능하게 한다.
- `fetched_at` 컬럼으로 데이터 수집 시점을 기록한다.
- WAL 모드를 활성화하여 읽기/쓰기 동시성을 개선한다.

---

## 4. 인터페이스 정의

### 4.1 캐시 저장소 클래스

```python
# src/lotto/cache_store.py

from pathlib import Path

class CacheStore:
    """SQLite 기반 당첨번호 캐시 저장소."""

    DEFAULT_DB_PATH = Path("data/lotto_cache.db")

    def __init__(self, db_path: Path | str | None = None) -> None:
        """저장소를 초기화하고 테이블을 생성한다.

        Args:
            db_path: SQLite 데이터베이스 파일 경로.
                     None이면 DEFAULT_DB_PATH 사용.
        """
        ...

    def save(self, result: DrawResult) -> None:
        """단일 회차 결과를 저장한다.

        이미 존재하는 회차는 무시한다 (INSERT OR IGNORE).

        Args:
            result: 저장할 DrawResult 객체

        Raises:
            CacheError: SQLite 오류 발생 시
        """
        ...

    def save_many(self, results: list[DrawResult]) -> int:
        """여러 회차 결과를 트랜잭션으로 일괄 저장한다.

        Args:
            results: 저장할 DrawResult 리스트

        Returns:
            새로 저장된 건수 (중복 제외)

        Raises:
            CacheError: SQLite 오류 발생 시
        """
        ...

    def get(self, draw_no: int) -> DrawResult | None:
        """회차 번호로 결과를 조회한다.

        Args:
            draw_no: 회차 번호

        Returns:
            DrawResult 또는 None (미존재 시)
        """
        ...

    def get_range(self, start: int, end: int) -> list[DrawResult]:
        """회차 범위로 결과를 조회한다.

        Args:
            start: 시작 회차 (포함)
            end: 종료 회차 (포함)

        Returns:
            DrawResult 리스트 (회차 오름차순)
        """
        ...

    def get_all(self) -> list[DrawResult]:
        """저장된 모든 결과를 조회한다.

        Returns:
            DrawResult 리스트 (회차 오름차순)
        """
        ...

    def get_cached_draw_numbers(self) -> set[int]:
        """캐시된 회차 번호 집합을 반환한다.

        Returns:
            저장된 회차 번호의 set
        """
        ...

    def count(self) -> int:
        """저장된 총 레코드 수를 반환한다."""
        ...

    def close(self) -> None:
        """데이터베이스 연결을 닫는다."""
        ...

    def __enter__(self) -> CacheStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
```

### 4.2 예외 클래스 (추가)

```python
# src/lotto/exceptions.py (기존 파일에 추가)

class CacheError(LottoError):
    """캐시 저장소 읽기/쓰기 오류."""
```

---

## 5. 의존성

### 외부 패키지
- 없음 (sqlite3는 표준 라이브러리)

### 표준 라이브러리
- `sqlite3`, `pathlib`, `datetime`

### 내부 의존성
| 모듈 | 사용 항목 |
|------|-----------|
| `models.py` | `DrawResult` (읽기 전용 소비) |
| `exceptions.py` | `LottoError` (상속), `CacheError` (신규 정의) |

---

## 6. 산출물

| 파일 경로 | 설명 |
|-----------|------|
| `src/lotto/cache_store.py` | `CacheStore` 캐시 저장소 구현 |
| `src/lotto/exceptions.py` | `CacheError` 예외 추가 |
| `tests/test_cache_store.py` | 단위 테스트 (인메모리 DB 기반) |

---

## 7. 구현 순서

| 순서 | 슬라이스 | 설명 |
|------|----------|------|
| 1 | `exceptions.py` — `CacheError` | 예외 클래스 1개 추가 |
| 2 | `cache_store.py` — `__init__` + 스키마 | DB 연결, WAL 모드, 테이블 생성 |
| 3 | `cache_store.py` — `save()` + `save_many()` | 단건/벌크 저장 (INSERT OR IGNORE) |
| 4 | `cache_store.py` — 조회 메서드 | `get`, `get_range`, `get_all`, `get_cached_draw_numbers`, `count` |
| 5 | `cache_store.py` — 연결 관리 | `close`, `__enter__`, `__exit__` |
| 6 | `tests/test_cache_store.py` | `:memory:` DB 기반 단위 테스트 |

---

## 8. 상위/하위 모듈 연동 계약

### 이 모듈이 소비하는 데이터
| 제공 모듈 | 데이터 | 사용 방식 |
|-----------|--------|-----------|
| `fetcher.py` | `list[DrawResult]` | `save_many()`로 캐시에 저장 |

### 이 모듈을 소비하는 모듈
| 소비 모듈 | 사용 방식 |
|-----------|-----------|
| `analysis.py` | `get_all()` 또는 `get_range()`로 분석 대상 데이터 로드 |
| `cli.py` | `get_cached_draw_numbers()`로 증분 수집 시 skip 집합 계산 |

### 증분 수집 연동 패턴
```python
# cli.py 또는 상위 오케스트레이션에서 사용할 패턴
with CacheStore() as cache:
    cached = cache.get_cached_draw_numbers()
    with LottoFetcher() as fetcher:
        latest = fetcher.fetch_latest()
        start = max(1, latest.draw_no - 499)
        # 캐시된 회차를 건너뛰고 미수집 회차만 요청
        to_fetch = [n for n in range(start, latest.draw_no + 1) if n not in cached]
        for draw_no in to_fetch:
            result = fetcher.fetch_draw(draw_no)
            cache.save(result)
```

---

## 9. 리스크 및 완화 전략

| 리스크 | 영향 | 완화 |
|--------|------|------|
| DB 파일 경로 권한 오류 | 저장 불가 | 부모 디렉터리 자동 생성 (`mkdir -p`) + 명확한 `CacheError` |
| 동시 접근 충돌 | 데이터 손상 | WAL 모드 + 단일 프로세스 CLI 특성상 낮은 위험 |
| 스키마 변경 필요 시 | 기존 데이터 유실 | v1 스키마가 충분하므로 현재 대응 불필요. 향후 필요 시 마이그레이션 모듈 별도 추가 |
| 대량 INSERT 성능 | 느린 저장 | 트랜잭션 일괄 처리 (`save_many`), 500건 기준 충분한 성능 |
