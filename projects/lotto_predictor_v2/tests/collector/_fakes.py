"""수집기 테스트에서 공통으로 사용하는 fake 의존성.

실제 HTTP 호출과 SQLite 연결을 피하기 위해 메모리 기반 대체 구현을 둔다.
테스트는 본 fake 가 Backend Dev 계약(`DhLotteryClient.fetch_draw`,
`LottoStorage.get_checkpoint` 등)을 동일한 시그니처로 노출하는 것에만 의존한다.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Callable, Iterable

from lotto_predictor.backend import (
    DrawNotFoundError,
    FetchCheckpoint,
    FetchResult,
    LottoDraw,
    TransientFetchError,
)


def make_payload(drw_no: int) -> dict:
    """정상 회차 payload 샘플을 생성한다. 테스트용 고정 번호 집합을 사용한다."""
    return {
        "returnValue": "success",
        "drwNo": drw_no,
        "drwNoDate": "2024-06-01",
        "drwtNo1": 1,
        "drwtNo2": 2,
        "drwtNo3": 3,
        "drwtNo4": 4,
        "drwtNo5": 5,
        "drwtNo6": 6,
        "bnusNo": 7,
        "totSellamnt": 1000,
        "firstWinamnt": 5000,
    }


def make_draw(drw_no: int) -> LottoDraw:
    """위 payload 와 동일한 내용의 도메인 타입 인스턴스."""
    return LottoDraw(
        drw_no=drw_no,
        drw_date=date(2024, 6, 1),
        numbers=(1, 2, 3, 4, 5, 6),
        bonus_no=7,
        tot_sell_amnt=1000,
        first_win_amnt=5000,
    )


class FakeClient:
    """시나리오 기반 회차 조회 fake.

    - ``success_range`` 에 포함된 회차는 정상 응답을 반환한다.
    - ``not_found`` 에 포함된 회차는 ``DrawNotFoundError`` 를 던진다.
    - ``transient`` 에 포함된 회차는 ``TransientFetchError`` 를 던진다.
    - ``custom`` 에 콜러블이 지정되면 우선 적용되어 임의 시나리오를 구성할 수 있다.
    """

    def __init__(
        self,
        *,
        success_range: Iterable[int] = (),
        not_found: Iterable[int] = (),
        transient: Iterable[int] = (),
        custom: Callable[[int], FetchResult] | None = None,
    ) -> None:
        self._success = set(success_range)
        self._not_found = set(not_found)
        self._transient = set(transient)
        self._custom = custom
        self.calls: list[int] = []

    def fetch_draw(self, draw_no: int) -> FetchResult:
        self.calls.append(draw_no)
        if self._custom is not None:
            return self._custom(draw_no)
        if draw_no in self._transient:
            raise TransientFetchError(f"일시 오류 시뮬레이션: drw_no={draw_no}")
        if draw_no in self._not_found:
            raise DrawNotFoundError(f"미발표 시뮬레이션: drw_no={draw_no}")
        if draw_no in self._success:
            return FetchResult(
                draw_no=draw_no,
                payload=make_payload(draw_no),
                fetched_at=datetime.now(),
            )
        raise DrawNotFoundError(f"테스트에서 정의되지 않은 회차: drw_no={draw_no}")


class FakeStorage:
    """메모리 기반 ``LottoStorage`` 대체. 수집기가 호출하는 최소 API 만 지원."""

    def __init__(self, checkpoint: FetchCheckpoint | None = None) -> None:
        self._checkpoint = checkpoint
        self.upserts: list[LottoDraw] = []
        self.checkpoints: list[FetchCheckpoint] = []

    def get_checkpoint(self) -> FetchCheckpoint | None:
        return self._checkpoint

    def set_checkpoint(self, cp: FetchCheckpoint) -> None:
        self._checkpoint = replace(cp)
        self.checkpoints.append(self._checkpoint)

    def upsert_draws(self, draws: Iterable[LottoDraw]) -> int:
        draws_list = list(draws)
        self.upserts.extend(draws_list)
        return len(draws_list)


__all__ = ["FakeClient", "FakeStorage", "make_draw", "make_payload"]
