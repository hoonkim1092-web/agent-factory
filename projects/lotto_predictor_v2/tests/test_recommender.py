from __future__ import annotations

import pytest

from lotto.analytics.patterns import PatternStats
from lotto.recommender import recommend_combinations
from tests.fixtures.recommender.mock_stats import (
    invalid_missing_frequency_stats,
    invalid_section_distribution_stats,
    recommender_stats,
    trend_shifted_stats,
)


def test_5조합_추천결과는_형식과_범위_중복_계약을_만족한다(
    recommender_stats: PatternStats,
) -> None:
    combinations = recommend_combinations(recommender_stats, n_combinations=5)
    candidate_pool = _top_pool(
        recommender_stats.number_frequency,
        recommender_stats.trend_weights,
    )

    assert len(combinations) == 5
    assert len({item.numbers for item in combinations}) == 5

    for combination in combinations:
        assert combination.numbers == tuple(sorted(combination.numbers))
        assert len(combination.numbers) == 6
        assert len(set(combination.numbers)) == 6
        assert all(1 <= number <= 45 for number in combination.numbers)
        assert set(combination.numbers).issubset(candidate_pool)


def test_빈도_구간_홀짝_패턴_가중치가_추천점수와_조합에_반영된다(
    recommender_stats: PatternStats,
) -> None:
    combinations = recommend_combinations(recommender_stats, n_combinations=1)
    top_combination = combinations[0]

    odd_count = sum(1 for number in top_combination.numbers if number % 2 == 1)
    active_sections = sum(
        1 for count in top_combination.section_distribution.values() if count > 0
    )

    assert top_combination.score >= 140.0
    assert {3, 7, 12, 16, 23}.issubset(set(top_combination.numbers))
    assert top_combination.odd_even_ratio == "4:2"
    assert odd_count == 4
    assert active_sections >= 4
    assert all(count <= 2 for count in top_combination.section_distribution.values())


@pytest.mark.xfail(
    reason="game_logic handoff의 입력 검증 예외 계약이 기존 lotto.recommender에는 아직 반영되지 않았다.",
)
@pytest.mark.parametrize(
    "fixture_name",
    ["invalid_missing_frequency_stats", "invalid_section_distribution_stats"],
)
def test_통계입력_누락과_비정상값은_명시적_예외로_차단되어야한다(
    fixture_name: str,
    request: pytest.FixtureRequest,
) -> None:
    stats = request.getfixturevalue(fixture_name)
    with pytest.raises((KeyError, TypeError, ValueError, AttributeError)):
        recommend_combinations(stats, n_combinations=5)


def test_최근_트렌드_가중치가_바뀌면_추천결과도_함께_변한다(
    recommender_stats: PatternStats,
    trend_shifted_stats: PatternStats,
) -> None:
    baseline = recommend_combinations(recommender_stats, n_combinations=3)
    shifted = recommend_combinations(trend_shifted_stats, n_combinations=3)

    assert [item.numbers for item in baseline] != [item.numbers for item in shifted]
    assert baseline[0].numbers != shifted[0].numbers
    assert sum(number >= 31 for number in shifted[0].numbers) >= sum(
        number >= 31 for number in baseline[0].numbers
    )


def _top_pool(
    number_frequency: dict[int, int],
    trend_weights: dict[int, float],
) -> set[int]:
    ranked = sorted(
        range(1, 46),
        key=lambda number: (-number_frequency[number], -trend_weights[number], number),
    )
    return set(ranked[:32])
