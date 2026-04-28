"""공유 데이터 모델 정의."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DrawResult:
    """로또 1회차 추첨 결과."""

    draw_no: int  # 회차 번호
    draw_date: date  # 추첨일
    numbers: tuple[int, ...]  # 당첨 번호 6개 (오름차순)
    bonus: int  # 보너스 번호
    total_sell_amount: int  # 총 판매금액
    first_prize_amount: int  # 1등 당첨금액
    first_prize_winners: int  # 1등 당첨자 수

    def __post_init__(self) -> None:
        if len(self.numbers) != 6:
            raise ValueError(f"당첨 번호는 6개여야 합니다 (입력: {len(self.numbers)}개)")
        for n in self.numbers:
            if not 1 <= n <= 45:
                raise ValueError(f"번호는 1~45 범위여야 합니다: {n}")
        if self.numbers != tuple(sorted(self.numbers)):
            raise ValueError("당첨 번호는 오름차순이어야 합니다")
        if not 1 <= self.bonus <= 45:
            raise ValueError(f"보너스 번호는 1~45 범위여야 합니다: {self.bonus}")
        if self.draw_no < 1:
            raise ValueError(f"회차 번호는 1 이상이어야 합니다: {self.draw_no}")
