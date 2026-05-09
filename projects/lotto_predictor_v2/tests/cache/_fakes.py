"""캐시 테스트 공용 fake 의존성.

실제 SQLite 연결과 HTTP 호출을 피하기 위해 메모리 기반 대체 구현을 둔다.
`FakeStorage` 는 Backend Dev `LottoStorage` 가 `LottoDrawCache` 에 노출하는
최소 API 만 충족하며, `FakeCollector` 는 `sync_incremental()` 만 지원한다.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Callable, Iterable

from lotto_predictor.backend import FetchCheckpoint, LottoDraw
from lotto_predictor.collector import SyncResult


def make_draw(drw_no: int) -> LottoDraw:
    """테스트용 고정 번호 집합을 가진 `LottoDraw` 를 만든다."""
    return LottoDraw(
        drw_no=drw_no,
        drw_date=date(2024, 6, 1),
        numbers=(1, 2, 3, 4, 5, 6),
        bonus_no=7,
        tot_sell_amnt=1000,
        first_win_amnt=5000,
    )


class FakeStorage:
    """메모리 기반 `LottoStorage` 대체.

    캐시 계층이 호출하는 `get_checkpoint`, `get_draws(limit=None)`, `get_draw` 만
    지원한다. 테스트에서 직접 회차 집합을 주입한다.
    """

    def __init__(
        self,
        *,
        draws: Iterable[LottoDraw] = (),
        checkpoint: FetchCheckpoint | None = None,
    ) -> None:
        # 저장소 계약에 맞춰 내림차순으로 보관한다.
        self._draws: list[LottoDraw] = sorted(draws, key=lambda d: d.drw_no, reverse=True)
        self._checkpoint = checkpoint

    def get_checkpoint(self) -> FetchCheckpoint | None:
        return self._checkpoint

    def get_draws(
        self,
        *,
        limit: int | None = None,
        since_no: int | None = None,
    ) -> list[LottoDraw]:
        rows = list(self._draws)
        if since_no is not None:
            rows = [d for d in rows if d.drw_no > since_no]
        if limit is not None:
            if limit < 0:
                raise ValueError(f"limit 은 음수일 수 없다: {limit}")
            rows = rows[:limit]
        return rows

    def get_draw(self, draw_no: int) -> LottoDraw | None:
        for d in self._draws:
            if d.drw_no == draw_no:
                return d
        return None

    # 테스트 편의: 회차/체크포인트 조작
    def seed_draws(self, draws: Iterable[LottoDraw]) -> None:
        self._draws = sorted(draws, key=lambda d: d.drw_no, reverse=True)

    def set_checkpoint(self, checkpoint: FetchCheckpoint | None) -> None:
        self._checkpoint = replace(checkpoint) if checkpoint is not None else None


class FakeCollector:
    """`sync_incremental` 호출을 시뮬레이션하는 수집기 fake.

    - ``on_sync`` 가 주어지면 호출 시 이를 실행해 저장소를 갱신할 수 있다.
    - 반환할 `SyncResult` 는 ``result`` 로 고정한다.
    """

    def __init__(
        self,
        *,
        result: SyncResult | None = None,
        on_sync: Callable[[], None] | None = None,
    ) -> None:
        self._result = result if result is not None else SyncResult()
        self._on_sync = on_sync
        self.calls = 0

    def sync_incremental(self) -> SyncResult:
        self.calls += 1
        if self._on_sync is not None:
            self._on_sync()
        return self._result


def fixed_clock(now: datetime) -> Callable[[], datetime]:
    """호출마다 동일한 시각을 반환하는 clock 함수."""

    def _clock() -> datetime:
        return now

    return _clock


__all__ = ["FakeCollector", "FakeStorage", "fixed_clock", "make_draw"]
