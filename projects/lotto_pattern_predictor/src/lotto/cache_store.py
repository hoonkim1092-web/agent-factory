"""SQLite 기반 당첨번호 캐시 저장소."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from .exceptions import CacheError
from .models import DrawResult

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS draws (
    draw_no              INTEGER PRIMARY KEY,
    draw_date            TEXT    NOT NULL,
    num1                 INTEGER NOT NULL,
    num2                 INTEGER NOT NULL,
    num3                 INTEGER NOT NULL,
    num4                 INTEGER NOT NULL,
    num5                 INTEGER NOT NULL,
    num6                 INTEGER NOT NULL,
    bonus                INTEGER NOT NULL,
    total_sell_amount    INTEGER NOT NULL DEFAULT 0,
    first_prize_amount   INTEGER NOT NULL DEFAULT 0,
    first_prize_winners  INTEGER NOT NULL DEFAULT 0,
    fetched_at           TEXT    NOT NULL
);
"""

_INSERT_SQL = """\
INSERT OR IGNORE INTO draws
    (draw_no, draw_date, num1, num2, num3, num4, num5, num6,
     bonus, total_sell_amount, first_prize_amount, first_prize_winners, fetched_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _result_to_row(result: DrawResult) -> tuple:
    """DrawResult를 INSERT 파라미터 튜플로 변환한다."""
    nums = result.numbers
    return (
        result.draw_no,
        result.draw_date.isoformat(),
        nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
        result.bonus,
        result.total_sell_amount,
        result.first_prize_amount,
        result.first_prize_winners,
        datetime.now().isoformat(),
    )


def _row_to_result(row: sqlite3.Row) -> DrawResult:
    """sqlite3.Row를 DrawResult로 변환한다."""
    return DrawResult(
        draw_no=row["draw_no"],
        draw_date=date.fromisoformat(row["draw_date"]),
        numbers=(
            row["num1"], row["num2"], row["num3"],
            row["num4"], row["num5"], row["num6"],
        ),
        bonus=row["bonus"],
        total_sell_amount=row["total_sell_amount"],
        first_prize_amount=row["first_prize_amount"],
        first_prize_winners=row["first_prize_winners"],
    )


class CacheStore:
    """SQLite 기반 당첨번호 캐시 저장소."""

    DEFAULT_DB_PATH = Path("data/lotto_cache.db")

    def __init__(self, db_path: Path | str | None = None) -> None:
        """저장소를 초기화하고 테이블을 생성한다.

        Args:
            db_path: SQLite 데이터베이스 파일 경로.
                     None이면 DEFAULT_DB_PATH 사용.
                     ":memory:"이면 인메모리 DB 사용.
        """
        if db_path is None:
            db_path = self.DEFAULT_DB_PATH
        self._db_path = Path(db_path) if db_path != ":memory:" else db_path

        try:
            # 파일 기반 DB인 경우 부모 디렉터리 생성
            if isinstance(self._db_path, Path):
                self._db_path.parent.mkdir(parents=True, exist_ok=True)

            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            # WAL 모드 활성화
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(_CREATE_TABLE_SQL)
            self._conn.commit()
        except sqlite3.Error as e:
            raise CacheError(f"데이터베이스 초기화 실패: {e}") from e

    # ── 저장 ──────────────────────────────────────────

    def save(self, result: DrawResult) -> None:
        """단일 회차 결과를 저장한다. 이미 존재하는 회차는 무시한다."""
        try:
            self._conn.execute(_INSERT_SQL, _result_to_row(result))
            self._conn.commit()
        except sqlite3.Error as e:
            raise CacheError(f"회차 {result.draw_no} 저장 실패: {e}") from e

    def save_many(self, results: list[DrawResult]) -> int:
        """여러 회차 결과를 트랜잭션으로 일괄 저장한다.

        Returns:
            새로 저장된 건수 (중복 제외)
        """
        try:
            before = self.count()
            self._conn.executemany(_INSERT_SQL, [_result_to_row(r) for r in results])
            self._conn.commit()
            return self.count() - before
        except sqlite3.Error as e:
            raise CacheError(f"일괄 저장 실패: {e}") from e

    # ── 조회 ──────────────────────────────────────────

    def get(self, draw_no: int) -> DrawResult | None:
        """회차 번호로 결과를 조회한다."""
        try:
            row = self._conn.execute(
                "SELECT * FROM draws WHERE draw_no = ?", (draw_no,)
            ).fetchone()
            return _row_to_result(row) if row else None
        except sqlite3.Error as e:
            raise CacheError(f"회차 {draw_no} 조회 실패: {e}") from e

    def get_range(self, start: int, end: int) -> list[DrawResult]:
        """회차 범위로 결과를 조회한다 (start, end 포함)."""
        try:
            rows = self._conn.execute(
                "SELECT * FROM draws WHERE draw_no BETWEEN ? AND ? ORDER BY draw_no",
                (start, end),
            ).fetchall()
            return [_row_to_result(r) for r in rows]
        except sqlite3.Error as e:
            raise CacheError(f"범위 조회 실패 ({start}~{end}): {e}") from e

    def get_all(self) -> list[DrawResult]:
        """저장된 모든 결과를 조회한다 (회차 오름차순)."""
        try:
            rows = self._conn.execute(
                "SELECT * FROM draws ORDER BY draw_no"
            ).fetchall()
            return [_row_to_result(r) for r in rows]
        except sqlite3.Error as e:
            raise CacheError(f"전체 조회 실패: {e}") from e

    def get_cached_draw_numbers(self) -> set[int]:
        """캐시된 회차 번호 집합을 반환한다."""
        try:
            rows = self._conn.execute("SELECT draw_no FROM draws").fetchall()
            return {r["draw_no"] for r in rows}
        except sqlite3.Error as e:
            raise CacheError(f"회차 목록 조회 실패: {e}") from e

    def count(self) -> int:
        """저장된 총 레코드 수를 반환한다."""
        try:
            row = self._conn.execute("SELECT COUNT(*) AS cnt FROM draws").fetchone()
            return row["cnt"]
        except sqlite3.Error as e:
            raise CacheError(f"건수 조회 실패: {e}") from e

    # ── 연결 관리 ─────────────────────────────────────

    def close(self) -> None:
        """데이터베이스 연결을 닫는다."""
        self._conn.close()

    def __enter__(self) -> CacheStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
