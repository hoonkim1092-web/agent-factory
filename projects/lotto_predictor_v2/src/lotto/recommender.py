from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import ceil

from .analytics.patterns import NUMBER_RANGE, SECTION_RANGES, PatternStats

TOP_POOL_RATIO = 0.7
ALLOWED_ODD_COUNTS = {2, 3, 4}
MAX_PER_SECTION = 2
MIN_ACTIVE_SECTIONS = 4
DEFAULT_COMBINATION_COUNT = 5


@dataclass(frozen=True)
class Combination:
    """추천된 번호 조합과 계산된 메타데이터."""

    numbers: tuple[int, int, int, int, int, int]
    score: float
    odd_even_ratio: str
    section_distribution: dict[str, int]


def recommend_combinations(
    stats: PatternStats,
    n_combinations: int = DEFAULT_COMBINATION_COUNT,
) -> list[Combination]:
    """패턴 통계를 바탕으로 상위 후보 번호 조합을 추천한다."""

    if n_combinations <= 0:
        raise ValueError("n_combinations는 1 이상이어야 합니다.")

    candidate_pool = _build_candidate_pool(stats)
    section_pool = _build_section_pool(candidate_pool, stats)
    scored_candidates: list[Combination] = []
    seen_numbers: set[tuple[int, int, int, int, int, int]] = set()

    for candidate in _generate_section_balanced_candidates(section_pool):
        if not _satisfies_constraints(candidate):
            continue
        section_counts = _count_sections(candidate)
        combination = Combination(
            numbers=candidate,
            score=round(_score_candidate(candidate, section_counts, stats), 4),
            odd_even_ratio=_format_odd_even_ratio(candidate),
            section_distribution=section_counts,
        )
        if combination.numbers in seen_numbers:
            continue
        seen_numbers.add(combination.numbers)
        scored_candidates.append(combination)

    ranked = sorted(
        scored_candidates,
        key=lambda item: (-item.score, item.numbers),
    )
    return ranked[:n_combinations]


def _build_candidate_pool(stats: PatternStats) -> list[int]:
    pool_size = max(6, ceil(len(NUMBER_RANGE) * TOP_POOL_RATIO))
    ranked_numbers = sorted(
        NUMBER_RANGE,
        key=lambda number: (
            -stats.number_frequency.get(number, 0),
            -stats.trend_weights.get(number, 0.0),
            _gap_priority(stats, number),
            number,
        ),
    )
    return ranked_numbers[:pool_size]


def _satisfies_constraints(candidate: tuple[int, ...]) -> bool:
    odd_count = sum(1 for number in candidate if number % 2 == 1)
    if odd_count not in ALLOWED_ODD_COUNTS:
        return False

    section_counts = _count_sections(candidate)
    active_sections = sum(1 for count in section_counts.values() if count > 0)
    if active_sections < MIN_ACTIVE_SECTIONS:
        return False
    if any(count > MAX_PER_SECTION for count in section_counts.values()):
        return False
    return True


def _build_section_pool(
    candidate_pool: list[int],
    stats: PatternStats,
) -> dict[str, list[int]]:
    section_pool = {label: [] for label, _ in SECTION_RANGES}
    for number in candidate_pool:
        label = _section_label(number)
        section_pool[label].append(number)

    for label in section_pool:
        section_pool[label] = sorted(
            section_pool[label],
            key=lambda number: (
                -stats.number_frequency.get(number, 0),
                -stats.trend_weights.get(number, 0.0),
                _gap_priority(stats, number),
                number,
            ),
        )[:5]
    return section_pool


def _generate_section_balanced_candidates(
    section_pool: dict[str, list[int]],
) -> list[tuple[int, int, int, int, int, int]]:
    labels = [label for label, _ in SECTION_RANGES]
    generated: set[tuple[int, int, int, int, int, int]] = set()

    for doubled_label in labels:
        if len(section_pool[doubled_label]) < 2:
            continue
        singles = [label for label in labels if label != doubled_label]
        if not all(section_pool[label] for label in singles):
            continue
        for double_numbers in combinations(section_pool[doubled_label], 2):
            for pick_a in section_pool[singles[0]]:
                for pick_b in section_pool[singles[1]]:
                    for pick_c in section_pool[singles[2]]:
                        for pick_d in section_pool[singles[3]]:
                            generated.add(tuple(sorted(double_numbers + (pick_a, pick_b, pick_c, pick_d))))

    for omitted_label in labels:
        active_labels = [label for label in labels if label != omitted_label]
        doubled_pairs = list(combinations(active_labels, 2))
        for left_label, right_label in doubled_pairs:
            single_labels = [label for label in active_labels if label not in {left_label, right_label}]
            if len(section_pool[left_label]) < 2 or len(section_pool[right_label]) < 2:
                continue
            if not all(section_pool[label] for label in single_labels):
                continue
            for left_numbers in combinations(section_pool[left_label], 2):
                for right_numbers in combinations(section_pool[right_label], 2):
                    for pick_a in section_pool[single_labels[0]]:
                        for pick_b in section_pool[single_labels[1]]:
                            generated.add(
                                tuple(
                                    sorted(
                                        left_numbers
                                        + right_numbers
                                        + (pick_a, pick_b)
                                    )
                                )
                            )

    return sorted(generated)


def _score_candidate(
    candidate: tuple[int, ...],
    section_counts: dict[str, int],
    stats: PatternStats,
) -> float:
    frequency_total = sum(stats.number_frequency.get(number, 0) for number in candidate)
    trend_total = sum(stats.trend_weights.get(number, 0.0) for number in candidate)

    gap_score = 0.0
    for number in candidate:
        gap_data = stats.consecutive_gaps.get(number, {})
        average_gap = gap_data.get("average_gap")
        last_gap = gap_data.get("last_gap")
        if isinstance(average_gap, (int, float)):
            gap_score += min(float(average_gap), 20.0) * 0.3
        if isinstance(last_gap, (int, float)):
            gap_score += min(float(last_gap), 20.0) * 0.2

    section_penalty = 0.0
    expected = 6 / len(SECTION_RANGES)
    total_section_weight = sum(stats.section_distribution.values()) or 1
    for label, _ in SECTION_RANGES:
        section_ratio = stats.section_distribution.get(label, 0) / total_section_weight
        target = 1.0 if section_ratio < 0.12 else expected
        section_penalty += abs(section_counts[label] - target)

    odd_even_bonus = 2.0 if _format_odd_even_ratio(candidate) == "3:3" else 1.0
    return (
        frequency_total * 1.0
        + trend_total * 0.35
        + gap_score
        + odd_even_bonus
        - section_penalty * 1.5
    )


def _gap_priority(stats: PatternStats, number: int) -> float:
    gap_data = stats.consecutive_gaps.get(number, {})
    average_gap = gap_data.get("average_gap")
    last_gap = gap_data.get("last_gap")
    if isinstance(last_gap, (int, float)):
        return -float(last_gap)
    if isinstance(average_gap, (int, float)):
        return -float(average_gap)
    return 0.0


def _count_sections(candidate: tuple[int, ...]) -> dict[str, int]:
    counts = {label: 0 for label, _ in SECTION_RANGES}
    for number in candidate:
        for label, section_range in SECTION_RANGES:
            if number in section_range:
                counts[label] += 1
                break
    return counts


def _section_label(number: int) -> str:
    for label, section_range in SECTION_RANGES:
        if number in section_range:
            return label
    raise ValueError(f"구간을 찾을 수 없는 번호입니다: {number}")


def _format_odd_even_ratio(candidate: tuple[int, ...]) -> str:
    odd_count = sum(1 for number in candidate if number % 2 == 1)
    even_count = len(candidate) - odd_count
    return f"{odd_count}:{even_count}"
