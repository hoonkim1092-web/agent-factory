from __future__ import annotations

from copy import deepcopy

import pytest

from lotto.analytics.patterns import PatternStats


def _base_number_frequency() -> dict[int, int]:
    # 기본값은 낮게 두고, 특정 번호만 뚜렷하게 가중해 추천 우선순위를 고정한다.
    number_frequency = {number: 1 for number in range(1, 46)}
    preferred_numbers = {
        3: 20,
        7: 19,
        12: 18,
        16: 17,
        23: 16,
        28: 15,
        31: 14,
        34: 13,
        41: 12,
        44: 11,
    }
    number_frequency.update(preferred_numbers)
    return number_frequency


def _base_trend_weights() -> dict[int, float]:
    # 고정 시드가 필요 없는 순수 함수이지만, 회귀 테스트의 기대값을 안정적으로 만들기 위해
    # 최근 트렌드 가중치를 명시적으로 주입한다.
    trend_weights = {number: 1.0 for number in range(1, 46)}
    preferred_numbers = {
        3: 18.0,
        7: 17.0,
        12: 16.5,
        16: 16.0,
        23: 15.5,
        28: 15.0,
        31: 14.5,
        34: 14.0,
        41: 13.5,
        44: 13.0,
    }
    trend_weights.update(preferred_numbers)
    return trend_weights


def _base_consecutive_gaps() -> dict[int, dict[str, object]]:
    # 간격 통계는 점수 계산에 직접 쓰이므로 모든 번호에 최소 구조를 채운다.
    return {
        number: {
            "gaps": [3, 5],
            "average_gap": 4.0,
            "last_gap": 5,
            "appearance_count": 2,
        }
        for number in range(1, 46)
    }


def build_pattern_stats() -> PatternStats:
    return PatternStats(
        number_frequency=_base_number_frequency(),
        consecutive_gaps=_base_consecutive_gaps(),
        odd_even_ratio={
            "ratio_counts": {"3:3": 8, "4:2": 4},
            "dominant_ratio": "3:3",
            "dominant_count": 8,
            "average_odd_count": 3.1,
            "average_even_count": 2.9,
        },
        section_distribution={
            "1-10": 60,
            "11-20": 55,
            "21-30": 58,
            "31-40": 57,
            "41-45": 40,
        },
        trend_weights=_base_trend_weights(),
    )


@pytest.fixture()
def recommender_stats() -> PatternStats:
    """기본 추천 회귀 테스트에 사용하는 통계 입력."""

    return build_pattern_stats()


@pytest.fixture()
def trend_shifted_stats() -> PatternStats:
    """최근 트렌드 가중치 변경 회귀 테스트에 사용하는 변형 입력."""

    stats = build_pattern_stats()
    shifted_weights = deepcopy(stats.trend_weights)

    # 저번호 구간 대신 고번호 구간이 우선되도록 최근성만 크게 이동시킨다.
    for number in (3, 7, 12, 16, 23):
        shifted_weights[number] = 2.0
    for number in (34, 38, 41, 42, 44, 45):
        shifted_weights[number] = 30.0

    return PatternStats(
        number_frequency=deepcopy(stats.number_frequency),
        consecutive_gaps=deepcopy(stats.consecutive_gaps),
        odd_even_ratio=deepcopy(stats.odd_even_ratio),
        section_distribution=deepcopy(stats.section_distribution),
        trend_weights=shifted_weights,
    )


@pytest.fixture()
def invalid_missing_frequency_stats() -> PatternStats:
    """필수 통계 입력 일부가 누락된 비정상 케이스."""

    stats = build_pattern_stats()
    broken_frequency = deepcopy(stats.number_frequency)
    broken_frequency.pop(45)
    return PatternStats(
        number_frequency=broken_frequency,
        consecutive_gaps=deepcopy(stats.consecutive_gaps),
        odd_even_ratio=deepcopy(stats.odd_even_ratio),
        section_distribution=deepcopy(stats.section_distribution),
        trend_weights=deepcopy(stats.trend_weights),
    )


@pytest.fixture()
def invalid_section_distribution_stats() -> PatternStats:
    """구간 분포 값이 비정상적으로 깨진 케이스."""

    stats = build_pattern_stats()
    broken_distribution = deepcopy(stats.section_distribution)
    broken_distribution.pop("41-45")
    return PatternStats(
        number_frequency=deepcopy(stats.number_frequency),
        consecutive_gaps=deepcopy(stats.consecutive_gaps),
        odd_even_ratio=deepcopy(stats.odd_even_ratio),
        section_distribution=broken_distribution,
        trend_weights=deepcopy(stats.trend_weights),
    )
