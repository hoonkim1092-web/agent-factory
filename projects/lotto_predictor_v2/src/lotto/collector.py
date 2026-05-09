"""동행복권 회차 수집기 연동 모델과 변환 유틸리티."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, runtime_checkable

from lotto_predictor.backend import LottoDraw
from lotto_predictor.collector import LottoCollector as PredictorLottoCollector
from lotto_predictor.collector import SyncResult


@dataclass(frozen=True)
class DrawResult:
    """단일 회차 당첨 결과를 표현하는 경량 값 객체.

    통계/추천 파이프라인은 `numbers` 속성만 있으면 동작하므로, `src/lotto`
    계층에서는 필요한 필드만 고정해 JSON 캐시와 collector 사이의 공통 계약으로
    사용한다.
    """

    drw_no: int
    drw_no_date: str
    numbers: tuple[int, int, int, int, int, int]
    bnus_no: int

    def to_dict(self) -> dict[str, Any]:
        """JSON 캐시 저장 형식으로 직렬화한다."""
        return {
            "drwNo": self.drw_no,
            "drwNoDate": self.drw_no_date,
            "numbers": list(self.numbers),
            "bnusNo": self.bnus_no,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DrawResult":
        """JSON dict 를 `DrawResult` 로 변환한다."""
        if not isinstance(payload, dict):
            raise TypeError(f"payload 는 dict 여야 한다: {type(payload).__name__}")
        try:
            drw_no = int(payload["drwNo"])
            drw_no_date = str(payload["drwNoDate"])
            numbers_raw = payload["numbers"]
            bnus_no = int(payload["bnusNo"])
        except KeyError as exc:
            raise ValueError(f"필수 키가 누락되었다: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(f"회차 데이터 변환에 실패했다: {exc}") from exc

        if not isinstance(numbers_raw, (list, tuple)):
            raise TypeError("numbers 는 리스트 또는 튜플이어야 한다.")
        numbers = tuple(sorted(int(number) for number in numbers_raw))
        if len(numbers) != 6:
            raise ValueError(f"numbers 는 6개여야 한다: {numbers!r}")
        return cls(
            drw_no=drw_no,
            drw_no_date=drw_no_date,
            numbers=(
                numbers[0],
                numbers[1],
                numbers[2],
                numbers[3],
                numbers[4],
                numbers[5],
            ),
            bnus_no=bnus_no,
        )

    @classmethod
    def from_lotto_draw(cls, draw: LottoDraw) -> "DrawResult":
        """`lotto_predictor.backend.LottoDraw` 를 변환한다."""
        return cls(
            drw_no=draw.drw_no,
            drw_no_date=_date_to_iso(draw.drw_date),
            numbers=draw.numbers,
            bnus_no=draw.bonus_no,
        )


@runtime_checkable
class DrawRangeCollector(Protocol):
    """캐시 저장소가 기대하는 최소 수집기 인터페이스."""

    def collect_range(self, start_round: int, end_round: int) -> list[DrawResult]: ...


class CollectorAdapter:
    """`lotto_predictor.collector.LottoCollector` 를 `DrawRangeCollector` 로 감싼다."""

    def __init__(self, collector: PredictorLottoCollector) -> None:
        self._collector = collector

    def collect_range(self, start_round: int, end_round: int) -> list[DrawResult]:
        """지정 범위를 수집해 `DrawResult` 목록으로 반환한다."""
        if start_round <= 0 or end_round <= 0:
            raise ValueError(
                f"start_round/end_round 는 양의 정수여야 한다: {start_round}, {end_round}"
            )
        if start_round > end_round:
            raise ValueError(
                f"start_round 가 end_round 보다 클 수 없다: {start_round}, {end_round}"
            )
        result: SyncResult = self._collector.sync_range(start_round, end_round)
        return [DrawResult.from_lotto_draw(draw) for draw in result.fetched]


def _date_to_iso(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


__all__ = ["CollectorAdapter", "DrawRangeCollector", "DrawResult"]
