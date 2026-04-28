"""Backend 레이어 도메인 타입과 예외 정의.

이 모듈은 서버·데이터·외부 연동 계층에서 공통으로 사용하는 결정적이고
불변인 값 객체를 제공한다. 비즈니스 규칙(번호 유효성 범위 등)은 Game Logic Dev가
담당하므로, 여기서는 외부 API 및 SQLite 영속 계층에서 필요한 최소한의
구조 검증만 수행한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

# 로또 번호의 허용 범위(동행복권 6/45 규격). 모델 단계에서는 단순 범위만
# 확인하고, 조합 규칙 검증은 상위 레이어에서 수행한다.
_MIN_NUMBER = 1
_MAX_NUMBER = 45


class BackendError(Exception):
    """Backend 계층 공통 기반 예외."""


class DrawNotFoundError(BackendError):
    """동행복권 API가 ``returnValue != "success"`` 를 반환하거나 존재하지 않는 회차."""


class TransientFetchError(BackendError):
    """재시도 후에도 복구되지 않은 네트워크/서버 일시 오류."""


@dataclass(frozen=True)
class LottoDraw:
    """단일 회차 당첨 결과를 나타내는 불변 값 객체.

    - ``numbers`` 는 오름차순 6개의 본 번호를 담는다.
    - ``bonus_no`` 는 보너스 번호다.
    - ``tot_sell_amnt`` 와 ``first_win_amnt`` 는 외부 API에서 누락될 수 있어 Optional 로 둔다.
    """

    drw_no: int
    drw_date: date
    numbers: tuple[int, int, int, int, int, int]
    bonus_no: int
    tot_sell_amnt: int | None = None
    first_win_amnt: int | None = None

    def __post_init__(self) -> None:
        if self.drw_no <= 0:
            raise ValueError(f"회차 번호는 양의 정수여야 한다: {self.drw_no}")
        if len(self.numbers) != 6:
            raise ValueError(f"당첨 번호는 정확히 6개여야 한다: {self.numbers}")
        for n in (*self.numbers, self.bonus_no):
            if not (_MIN_NUMBER <= n <= _MAX_NUMBER):
                raise ValueError(
                    f"번호는 {_MIN_NUMBER}..{_MAX_NUMBER} 범위를 벗어날 수 없다: {n}"
                )
        if len(set(self.numbers)) != 6:
            raise ValueError(f"본 번호에 중복이 있다: {self.numbers}")
        if self.bonus_no in self.numbers:
            raise ValueError(
                f"보너스 번호는 본 번호와 달라야 한다: bonus={self.bonus_no}, numbers={self.numbers}"
            )
        if tuple(sorted(self.numbers)) != self.numbers:
            # 정렬되지 않은 입력은 상위 계층에서 정렬 후 전달한다는 계약을 고정한다.
            raise ValueError(f"본 번호는 오름차순이어야 한다: {self.numbers}")


@dataclass(frozen=True)
class FetchCheckpoint:
    """증분 수집 진행 상태를 표현하는 체크포인트.

    ``last_fetched_drw_no`` 까지의 회차는 SQLite 에 저장되어 있음이 보장된다.
    상위 수집기는 이 값을 기준으로 다음 회차부터 수집한다.
    """

    last_fetched_drw_no: int
    fetched_at: datetime
    source_url: str

    def __post_init__(self) -> None:
        if self.last_fetched_drw_no <= 0:
            raise ValueError(
                f"체크포인트 회차는 양의 정수여야 한다: {self.last_fetched_drw_no}"
            )
        if not self.source_url:
            raise ValueError("source_url 은 비어 있을 수 없다")


@dataclass(frozen=True)
class NumberFrequencyRow:
    """번호별 빈도 집계 결과 한 행.

    통계 엔진이 산출한 집계 결과를 SQLite ``number_frequency`` 테이블에
    캐시해 두기 위한 단순 레코드다.
    """

    number: int
    count: int
    last_seen_drw_no: int
    recent_50_count: int

    def __post_init__(self) -> None:
        if not (_MIN_NUMBER <= self.number <= _MAX_NUMBER):
            raise ValueError(
                f"번호는 {_MIN_NUMBER}..{_MAX_NUMBER} 범위여야 한다: {self.number}"
            )
        if self.count < 0 or self.recent_50_count < 0:
            raise ValueError(
                f"빈도 값은 0 이상이어야 한다: count={self.count}, "
                f"recent_50_count={self.recent_50_count}"
            )
        if self.last_seen_drw_no < 0:
            raise ValueError(
                f"마지막 등장 회차는 0 이상이어야 한다: {self.last_seen_drw_no}"
            )


@dataclass(frozen=True)
class FetchResult:
    """HTTP 클라이언트가 반환하는 회차 단건 조회 결과.

    ``payload`` 는 외부 응답 JSON 원본을 그대로 보존해 상위에서 재직렬화가
    가능하도록 한다. 도메인 타입 변환은 ``serialization.parse_draw`` 에 위임한다.
    """

    draw_no: int
    payload: dict
    fetched_at: datetime


__all__ = [
    "BackendError",
    "DrawNotFoundError",
    "TransientFetchError",
    "LottoDraw",
    "FetchCheckpoint",
    "NumberFrequencyRow",
    "FetchResult",
]
