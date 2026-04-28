"""models.py 단위 테스트."""

import pytest
from datetime import date

from src.lotto.models import DrawResult


class TestDrawResult:
    """DrawResult 데이터 모델 검증."""

    def test_정상_생성(self):
        result = DrawResult(
            draw_no=1100,
            draw_date=date(2024, 1, 20),
            numbers=(3, 10, 23, 33, 37, 40),
            bonus=16,
            total_sell_amount=3_681_782_000,
            first_prize_amount=2_312_839_938,
            first_prize_winners=8,
        )
        assert result.draw_no == 1100
        assert result.numbers == (3, 10, 23, 33, 37, 40)
        assert result.bonus == 16

    def test_번호_6개_아니면_실패(self):
        with pytest.raises(ValueError, match="6개"):
            DrawResult(
                draw_no=1,
                draw_date=date(2024, 1, 1),
                numbers=(1, 2, 3, 4, 5),
                bonus=7,
                total_sell_amount=0,
                first_prize_amount=0,
                first_prize_winners=0,
            )

    def test_번호_범위_초과(self):
        with pytest.raises(ValueError, match="1~45"):
            DrawResult(
                draw_no=1,
                draw_date=date(2024, 1, 1),
                numbers=(0, 2, 3, 4, 5, 6),
                bonus=7,
                total_sell_amount=0,
                first_prize_amount=0,
                first_prize_winners=0,
            )

    def test_번호_정렬_안됨(self):
        with pytest.raises(ValueError, match="오름차순"):
            DrawResult(
                draw_no=1,
                draw_date=date(2024, 1, 1),
                numbers=(5, 3, 10, 20, 30, 40),
                bonus=7,
                total_sell_amount=0,
                first_prize_amount=0,
                first_prize_winners=0,
            )

    def test_보너스_범위_초과(self):
        with pytest.raises(ValueError, match="보너스"):
            DrawResult(
                draw_no=1,
                draw_date=date(2024, 1, 1),
                numbers=(1, 2, 3, 4, 5, 6),
                bonus=46,
                total_sell_amount=0,
                first_prize_amount=0,
                first_prize_winners=0,
            )

    def test_회차_번호_음수(self):
        with pytest.raises(ValueError, match="1 이상"):
            DrawResult(
                draw_no=0,
                draw_date=date(2024, 1, 1),
                numbers=(1, 2, 3, 4, 5, 6),
                bonus=7,
                total_sell_amount=0,
                first_prize_amount=0,
                first_prize_winners=0,
            )

    def test_불변(self):
        result = DrawResult(
            draw_no=1,
            draw_date=date(2024, 1, 1),
            numbers=(1, 2, 3, 4, 5, 6),
            bonus=7,
            total_sell_amount=0,
            first_prize_amount=0,
            first_prize_winners=0,
        )
        with pytest.raises(AttributeError):
            result.draw_no = 2  # type: ignore[misc]
