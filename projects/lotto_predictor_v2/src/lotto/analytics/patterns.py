from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from statistics import fmean

MAX_DRAWS = 500
NUMBER_RANGE = range(1, 46)
SECTION_RANGES: tuple[tuple[str, range], ...] = (
    ("1-10", range(1, 11)),
    ("11-20", range(11, 21)),
    ("21-30", range(21, 31)),
    ("31-40", range(31, 41)),
    ("41-45", range(41, 46)),
)


@dataclass(frozen=True)
class PatternStats:
    """추천기와 리포트가 공통으로 소비하는 패턴 통계 묶음."""

    number_frequency: dict[int, int]
    consecutive_gaps: dict[int, dict[str, object]]
    odd_even_ratio: dict[str, object]
    section_distribution: dict[str, int]
    trend_weights: dict[int, float]


def calculate_number_frequency(draws: Sequence[object]) -> dict[int, int]:
    """최근 회차 목록에서 번호별 출현 빈도를 계산한다.

    입력은 최근 회차부터 과거 회차 순으로 정렬된 최대 500건의 회차 목록이어야 한다.
    각 회차는 길이 6의 정수 시퀀스이거나 `numbers` 속성을 가진 객체여야 한다.
    반환값은 1부터 45까지 모든 번호를 키로 가지며, 등장하지 않은 번호는 0으로 채운다.
    """

    normalized_draws = _normalize_draws(draws)
    frequency = {number: 0 for number in NUMBER_RANGE}
    for draw in normalized_draws:
        for number in draw:
            frequency[number] += 1
    return frequency


def calculate_consecutive_gaps(draws: Sequence[object]) -> dict[int, dict[str, object]]:
    """번호별 연속 등장 간격 통계를 계산한다.

    간격은 동일 번호가 등장한 두 회차의 입력 인덱스 차이로 정의한다.
    입력 순서는 최신 회차에서 과거 회차 순이어야 하며, 반환값에는 각 번호의
    `gaps`, `average_gap`, `last_gap`, `appearance_count`가 포함된다.
    """

    normalized_draws = _normalize_draws(draws)
    positions: dict[int, list[int]] = {number: [] for number in NUMBER_RANGE}

    for index, draw in enumerate(normalized_draws):
        for number in draw:
            positions[number].append(index)

    gap_summary: dict[int, dict[str, object]] = {}
    for number in NUMBER_RANGE:
        number_positions = positions[number]
        gaps = [
            current - previous
            for previous, current in zip(number_positions, number_positions[1:])
        ]
        gap_summary[number] = {
            "gaps": gaps,
            "average_gap": round(fmean(gaps), 4) if gaps else None,
            "last_gap": gaps[-1] if gaps else None,
            "appearance_count": len(number_positions),
        }
    return gap_summary


def calculate_odd_even_ratio(draws: Sequence[object]) -> dict[str, object]:
    """회차별 홀짝 비율 분포를 계산한다.

    각 회차에서 홀수 개수를 세어 `홀수:짝수` 문자열로 집계하고,
    가장 많이 나온 대표 비율과 전체 평균 홀수/짝수 개수도 함께 반환한다.
    """

    normalized_draws = _normalize_draws(draws)
    ratio_counts: Counter[str] = Counter()
    odd_counts: list[int] = []

    for draw in normalized_draws:
        odd_count = sum(1 for number in draw if number % 2 == 1)
        even_count = 6 - odd_count
        ratio_counts[f"{odd_count}:{even_count}"] += 1
        odd_counts.append(odd_count)

    dominant_ratio, dominant_count = sorted(
        ratio_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[0]
    average_odd_count = round(fmean(odd_counts), 4)
    average_even_count = round(6 - average_odd_count, 4)
    return {
        "ratio_counts": dict(sorted(ratio_counts.items())),
        "dominant_ratio": dominant_ratio,
        "dominant_count": dominant_count,
        "average_odd_count": average_odd_count,
        "average_even_count": average_even_count,
    }


def calculate_section_distribution(draws: Sequence[object]) -> dict[str, int]:
    """번호를 구간별로 나눈 누적 분포를 계산한다.

    구간은 `1-10`, `11-20`, `21-30`, `31-40`, `41-45`로 고정한다.
    각 회차의 6개 번호를 모두 누적 집계해 구간별 출현 횟수를 반환한다.
    """

    normalized_draws = _normalize_draws(draws)
    distribution = {label: 0 for label, _ in SECTION_RANGES}

    for draw in normalized_draws:
        for number in draw:
            distribution[_section_label(number)] += 1
    return distribution


def calculate_trend_weights(draws: Sequence[object]) -> dict[int, float]:
    """최근 회차에 더 큰 가중치를 주는 번호별 트렌드 점수를 계산한다.

    입력은 최신 회차가 앞에 오는 순서여야 한다. 첫 회차에는 전체 회차 수와 같은
    가중치를 주고, 이후 회차는 1씩 감소하는 선형 가중치를 적용한다.
    """

    normalized_draws = _normalize_draws(draws)
    total_draws = len(normalized_draws)
    weights = {number: 0.0 for number in NUMBER_RANGE}

    for index, draw in enumerate(normalized_draws):
        weight = float(total_draws - index)
        for number in draw:
            weights[number] += weight
    return {number: round(score, 4) for number, score in weights.items()}


def analyze_patterns(draws: Sequence[object]) -> PatternStats:
    """최근 회차 목록에서 5가지 패턴 분석 결과를 한 번에 반환한다."""

    normalized_draws = _normalize_draws(draws)
    return PatternStats(
        number_frequency=calculate_number_frequency(normalized_draws),
        consecutive_gaps=calculate_consecutive_gaps(normalized_draws),
        odd_even_ratio=calculate_odd_even_ratio(normalized_draws),
        section_distribution=calculate_section_distribution(normalized_draws),
        trend_weights=calculate_trend_weights(normalized_draws),
    )


def _normalize_draws(draws: Sequence[object]) -> list[tuple[int, ...]]:
    if not isinstance(draws, Sequence) or isinstance(draws, (str, bytes)):
        raise TypeError("draws는 길이를 가진 회차 시퀀스여야 합니다.")
    if not draws:
        raise ValueError("draws는 최소 1건 이상이어야 합니다.")
    if len(draws) > MAX_DRAWS:
        raise ValueError("draws는 최대 500건까지만 허용됩니다.")

    normalized: list[tuple[int, ...]] = []
    for index, draw in enumerate(draws, start=1):
        numbers = _extract_numbers(draw)
        if len(numbers) != 6:
            raise ValueError(f"{index}번째 회차는 번호 6개를 가져야 합니다.")
        if len(set(numbers)) != 6:
            raise ValueError(f"{index}번째 회차에는 중복 번호가 있으면 안 됩니다.")
        for number in numbers:
            if not isinstance(number, int):
                raise TypeError(f"{index}번째 회차 번호는 정수여야 합니다.")
            if number not in NUMBER_RANGE:
                raise ValueError(f"{index}번째 회차 번호는 1부터 45 사이여야 합니다.")
        normalized.append(tuple(sorted(numbers)))
    return normalized


def _extract_numbers(draw: object) -> tuple[int, ...]:
    if hasattr(draw, "numbers"):
        candidate = getattr(draw, "numbers")
    else:
        candidate = draw
    if not isinstance(candidate, Iterable) or isinstance(candidate, (str, bytes)):
        raise TypeError("각 회차는 반복 가능한 번호 목록이어야 합니다.")
    return tuple(candidate)


def _section_label(number: int) -> str:
    for label, section_range in SECTION_RANGES:
        if number in section_range:
            return label
    raise ValueError(f"구간을 찾을 수 없는 번호입니다: {number}")
