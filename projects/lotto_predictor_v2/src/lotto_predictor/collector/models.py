"""동행복권 회차 수집기 모듈의 데이터 계약.

수집기 오케스트레이션 계층이 호출자에게 반환하거나 설정으로 받는 값 객체를
정의한다. Backend Dev 계층의 도메인 타입(``LottoDraw`` 등)은 재사용하며,
여기서는 수집 루프 고유의 입력/출력/실패 표현만 정의한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from lotto_predictor.backend import LottoDraw

# 실패 사유 분류. Backend Dev 예외(`DrawNotFoundError`, `TransientFetchError`)와
# 수집기 고유 사유(`rate_limited`, `unknown`)를 함께 표현한다.
FailureReason = Literal["not_yet_drawn", "transient", "rate_limited", "unknown"]

# 수집 루프 종료 사유. 체크포인트 갱신 전략과 호출자 로깅 분기에 사용된다.
StoppedReason = Literal["caught_up", "not_yet_drawn", "aborted", "target_reached"]


@dataclass(frozen=True)
class CollectorConfig:
    """수집기 동작을 제어하는 설정 값 묶음.

    - ``min_interval_s``: 외부 HTTP 호출 간 최소 간격(초). Backend Dev 클라이언트가
      자체적으로 rate limit 을 갖더라도, 오케스트레이션 계층이 한 번 더
      과도 요청을 막는다.
    - ``max_probe``: ``detect_latest_draw_no`` 가 전진하며 탐색할 최대 회차 수.
    - ``target_draw_no``: 명시 목표 회차. 지정 시 ``sync_incremental`` 이
      해당 회차까지만 수집하고 ``stopped_reason="target_reached"`` 로 종료한다.
    - ``abort_on_consecutive_failures``: 연속 일시 실패 허용 횟수. 초과 시
      수집 루프를 즉시 중단한다.
    """

    min_interval_s: float = 0.2
    max_probe: int = 20
    target_draw_no: int | None = None
    abort_on_consecutive_failures: int = 3

    def __post_init__(self) -> None:
        if self.min_interval_s < 0:
            raise ValueError(
                f"min_interval_s 는 0 이상이어야 한다: {self.min_interval_s}"
            )
        if self.max_probe <= 0:
            raise ValueError(f"max_probe 는 양의 정수여야 한다: {self.max_probe}")
        if self.target_draw_no is not None and self.target_draw_no <= 0:
            raise ValueError(
                f"target_draw_no 는 양의 정수여야 한다: {self.target_draw_no}"
            )
        if self.abort_on_consecutive_failures <= 0:
            raise ValueError(
                "abort_on_consecutive_failures 는 양의 정수여야 한다: "
                f"{self.abort_on_consecutive_failures}"
            )


@dataclass(frozen=True)
class FetchFailure:
    """단일 회차 수집 실패 기록.

    호출자가 재시도 결정을 내릴 때 사용할 최소 정보만 담는다. 상세 원인은
    ``detail`` 에 문자열로 직렬화한다(예외 원본은 유지하지 않는다).
    """

    draw_no: int
    reason: FailureReason
    detail: str

    def __post_init__(self) -> None:
        if self.draw_no <= 0:
            raise ValueError(f"draw_no 는 양의 정수여야 한다: {self.draw_no}")
        if not self.detail:
            raise ValueError("detail 은 비어 있을 수 없다")


@dataclass(frozen=True)
class SyncResult:
    """수집 루프 한 번의 결과 집계.

    - ``fetched`` 는 성공 회차만 오름차순으로 담는다.
    - ``failures`` 는 발생 순서대로 보존하여 호출자가 추적할 수 있게 한다.
    - ``last_fetched_drw_no`` 는 체크포인트에 기록된 마지막 성공 회차를 반영한다.
    - ``stopped_reason`` 은 루프 종료 원인을 분기 가능한 문자열로 고정한다.
    """

    fetched: list[LottoDraw] = field(default_factory=list)
    failures: list[FetchFailure] = field(default_factory=list)
    last_fetched_drw_no: int | None = None
    stopped_reason: StoppedReason = "caught_up"


__all__ = [
    "CollectorConfig",
    "FailureReason",
    "FetchFailure",
    "StoppedReason",
    "SyncResult",
]
