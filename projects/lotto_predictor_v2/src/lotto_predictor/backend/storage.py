"""SQLite 기반 회차/체크포인트/빈도 영속 계층.

단일 프로세스(PyInstaller 단일 실행 파일) 사용을 전제로 WAL 모드와 트랜잭션
래핑을 사용한다. 본 클래스는 비즈니스 규칙을 포함하지 않으며, 입력된
도메인 타입을 그대로 저장하거나 복원하는 순수 I/O 계층이다.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .models import FetchCheckpoint, LottoDraw, NumberFrequencyRow

_SCHEMA_FILE = Path(__file__).with_name("schema.sql")


class LottoStorage:
    """SQLite 연결 수명과 도메인 타입 직렬화를 담당하는 영속 저장소."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # 수명 주기 및 컨텍스트 매니저
    # ------------------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        """연결이 없으면 열고, 이미 열려 있으면 기존 연결을 반환한다."""
        if self._conn is None:
            # 부모 디렉터리가 없으면 영속 파일을 만들 수 없으므로 먼저 보장한다.
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path), isolation_level=None)
            conn.row_factory = sqlite3.Row
            # WAL 모드는 단일 프로세스 읽기/쓰기 혼합에 유리하다.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._conn = conn
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def __enter__(self) -> "LottoStorage":
        self.connect()
        self.ensure_schema()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # 스키마 초기화
    # ------------------------------------------------------------------
    def ensure_schema(self) -> None:
        """DDL 스크립트를 멱등하게 적용한다."""
        conn = self.connect()
        ddl = _SCHEMA_FILE.read_text(encoding="utf-8")
        # executescript 는 내부에서 트랜잭션을 제어하므로 외부 래핑을 사용하지 않는다.
        conn.executescript(ddl)

    # ------------------------------------------------------------------
    # 회차 I/O
    # ------------------------------------------------------------------
    def upsert_draws(self, draws: Iterable[LottoDraw]) -> int:
        """회차 레코드를 일괄 upsert 하고 반영된 행 수를 반환한다.

        동일 ``drw_no`` 가 이미 존재하면 최신 값으로 덮어쓴다. 외부 API 스키마가
        바뀌어 재수집이 필요한 경우에도 안전하게 재실행할 수 있다.
        """
        conn = self.connect()
        rows = [_draw_to_row(d) for d in draws]
        if not rows:
            return 0
        with _transaction(conn):
            conn.executemany(
                """
                INSERT INTO lotto_draw (
                    drw_no, drw_date,
                    n1, n2, n3, n4, n5, n6,
                    bonus_no, tot_sell_amnt, first_win_amnt
                ) VALUES (
                    :drw_no, :drw_date,
                    :n1, :n2, :n3, :n4, :n5, :n6,
                    :bonus_no, :tot_sell_amnt, :first_win_amnt
                )
                ON CONFLICT(drw_no) DO UPDATE SET
                    drw_date=excluded.drw_date,
                    n1=excluded.n1, n2=excluded.n2, n3=excluded.n3,
                    n4=excluded.n4, n5=excluded.n5, n6=excluded.n6,
                    bonus_no=excluded.bonus_no,
                    tot_sell_amnt=excluded.tot_sell_amnt,
                    first_win_amnt=excluded.first_win_amnt
                """,
                rows,
            )
        return len(rows)

    def get_draws(
        self,
        *,
        limit: int | None = None,
        since_no: int | None = None,
    ) -> list[LottoDraw]:
        """회차를 내림차순으로 조회한다.

        - ``since_no`` 는 배타적 하한선(해당 값보다 큰 회차만).
        - ``limit`` 가 주어지면 최신 기준 상위 N개만 반환한다.
        """
        conn = self.connect()
        sql = "SELECT * FROM lotto_draw"
        params: list[object] = []
        if since_no is not None:
            sql += " WHERE drw_no > ?"
            params.append(since_no)
        sql += " ORDER BY drw_no DESC"
        if limit is not None:
            if limit < 0:
                raise ValueError(f"limit 은 음수일 수 없다: {limit}")
            sql += " LIMIT ?"
            params.append(limit)
        cur = conn.execute(sql, params)
        return [_row_to_draw(r) for r in cur.fetchall()]

    def get_draw(self, draw_no: int) -> LottoDraw | None:
        conn = self.connect()
        cur = conn.execute("SELECT * FROM lotto_draw WHERE drw_no = ?", (draw_no,))
        row = cur.fetchone()
        return _row_to_draw(row) if row is not None else None

    # ------------------------------------------------------------------
    # 체크포인트 I/O
    # ------------------------------------------------------------------
    def get_checkpoint(self) -> FetchCheckpoint | None:
        conn = self.connect()
        cur = conn.execute(
            "SELECT last_fetched_drw_no, fetched_at, source_url FROM fetch_checkpoint WHERE id = 1"
        )
        row = cur.fetchone()
        if row is None:
            return None
        return FetchCheckpoint(
            last_fetched_drw_no=int(row["last_fetched_drw_no"]),
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            source_url=row["source_url"],
        )

    def set_checkpoint(self, cp: FetchCheckpoint) -> None:
        conn = self.connect()
        with _transaction(conn):
            conn.execute(
                """
                INSERT INTO fetch_checkpoint (id, last_fetched_drw_no, fetched_at, source_url)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    last_fetched_drw_no=excluded.last_fetched_drw_no,
                    fetched_at=excluded.fetched_at,
                    source_url=excluded.source_url
                """,
                (cp.last_fetched_drw_no, cp.fetched_at.isoformat(), cp.source_url),
            )

    # ------------------------------------------------------------------
    # 빈도 캐시 I/O
    # ------------------------------------------------------------------
    def write_number_frequency(self, rows: Iterable[NumberFrequencyRow]) -> None:
        """집계 결과를 전체 치환한다.

        통계 엔진은 주기적으로 전체 빈도를 재계산하므로, 부분 업데이트 대신
        테이블 단위 트랜잭션으로 원자적으로 치환한다.
        """
        conn = self.connect()
        rows_list = list(rows)
        with _transaction(conn):
            conn.execute("DELETE FROM number_frequency")
            if rows_list:
                conn.executemany(
                    """
                    INSERT INTO number_frequency (
                        number, count, last_seen_drw_no, recent_50_count
                    ) VALUES (:number, :count, :last_seen_drw_no, :recent_50_count)
                    """,
                    [
                        {
                            "number": r.number,
                            "count": r.count,
                            "last_seen_drw_no": r.last_seen_drw_no,
                            "recent_50_count": r.recent_50_count,
                        }
                        for r in rows_list
                    ],
                )

    def read_number_frequency(self) -> list[NumberFrequencyRow]:
        conn = self.connect()
        cur = conn.execute(
            "SELECT number, count, last_seen_drw_no, recent_50_count FROM number_frequency ORDER BY number ASC"
        )
        return [
            NumberFrequencyRow(
                number=int(r["number"]),
                count=int(r["count"]),
                last_seen_drw_no=int(r["last_seen_drw_no"]),
                recent_50_count=int(r["recent_50_count"]),
            )
            for r in cur.fetchall()
        ]


# ----------------------------------------------------------------------
# 내부 유틸리티
# ----------------------------------------------------------------------
class _transaction:
    """BEGIN IMMEDIATE ~ COMMIT/ROLLBACK 을 감싸는 단순 컨텍스트 매니저."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def __enter__(self) -> sqlite3.Connection:
        # autocommit(isolation_level=None) 상태에서 명시적 트랜잭션을 연다.
        self._conn.execute("BEGIN IMMEDIATE")
        return self._conn

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self._conn.execute("COMMIT")
        else:
            self._conn.execute("ROLLBACK")


def _draw_to_row(draw: LottoDraw) -> dict[str, object]:
    n1, n2, n3, n4, n5, n6 = draw.numbers
    return {
        "drw_no": draw.drw_no,
        "drw_date": draw.drw_date.isoformat(),
        "n1": n1,
        "n2": n2,
        "n3": n3,
        "n4": n4,
        "n5": n5,
        "n6": n6,
        "bonus_no": draw.bonus_no,
        "tot_sell_amnt": draw.tot_sell_amnt,
        "first_win_amnt": draw.first_win_amnt,
    }


def _row_to_draw(row: sqlite3.Row) -> LottoDraw:
    numbers = (
        int(row["n1"]),
        int(row["n2"]),
        int(row["n3"]),
        int(row["n4"]),
        int(row["n5"]),
        int(row["n6"]),
    )
    return LottoDraw(
        drw_no=int(row["drw_no"]),
        drw_date=date.fromisoformat(row["drw_date"]),
        numbers=numbers,
        bonus_no=int(row["bonus_no"]),
        tot_sell_amnt=_optional_int(row["tot_sell_amnt"]),
        first_win_amnt=_optional_int(row["first_win_amnt"]),
    )


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


__all__ = ["LottoStorage"]
