from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Sequence, runtime_checkable

from lotto.analytics.patterns import (
    MAX_DRAWS,
    PatternStats,
    analyze_patterns as _analyze_patterns,
    calculate_consecutive_gaps,
    calculate_number_frequency,
    calculate_odd_even_ratio,
    calculate_section_distribution,
    calculate_trend_weights,
)
from lotto_predictor.game_logic import StatisticsSummary


@dataclass(frozen=True)
class AnalysisRunSummary:
    """통계 분석 실행의 핵심 메타데이터 요약."""

    source_draw_count: int
    latest_draw_no: int
    oldest_draw_no: int
    dominant_ratio: str
    top_frequency_numbers: tuple[int, ...]
    generated_at: str


@runtime_checkable
class DrawCacheLike(Protocol):
    """통계 엔진이 요구하는 최소 캐시 읽기 계약."""

    def get_recent_draws(self, n: int) -> list[object]: ...


def analyze_patterns(draws: Sequence[object]) -> PatternStats:
    """기존 순수 패턴 계산기를 재노출한다."""

    return _analyze_patterns(draws)


def build_pattern_stats_from_cache(
    cache: DrawCacheLike,
    draw_limit: int = MAX_DRAWS,
) -> PatternStats:
    """캐시 읽기 계약 위에서 패턴 통계를 계산한다."""

    if draw_limit <= 0:
        raise ValueError(f"draw_limit 은 1 이상이어야 합니다: {draw_limit}")
    if draw_limit > MAX_DRAWS:
        raise ValueError(f"draw_limit 은 {MAX_DRAWS} 이하여야 합니다: {draw_limit}")
    if not isinstance(cache, DrawCacheLike):
        raise TypeError("cache 는 get_recent_draws(n) 메서드를 지원해야 합니다.")

    draws = cache.get_recent_draws(draw_limit)
    return analyze_patterns(draws)


def build_statistics_summary(
    draws: Sequence[object],
    *,
    recent_window: int = 50,
) -> StatisticsSummary:
    """추천 엔진이 소비하는 `StatisticsSummary` 를 조립한다."""

    if recent_window <= 0:
        raise ValueError(f"recent_window 는 1 이상이어야 합니다: {recent_window}")

    pattern_stats = analyze_patterns(draws)
    recent_draws = list(draws[:recent_window])
    recent_frequency = calculate_number_frequency(recent_draws)
    number_last_seen = _calculate_number_last_seen(draws)
    sum_range = _calculate_sum_range(draws)

    return StatisticsSummary(
        number_frequency=pattern_stats.number_frequency,
        recent_frequency=recent_frequency,
        number_last_seen=number_last_seen,
        sum_range=sum_range,
    )


def summarize_analysis_run(
    stats: PatternStats,
    source_draw_count: int,
    latest_draw_no: int,
    *,
    oldest_draw_no: int | None = None,
    generated_at: datetime | None = None,
    top_n: int = 6,
) -> AnalysisRunSummary:
    """패턴 통계를 실행 메타데이터와 함께 요약한다."""

    if source_draw_count <= 0:
        raise ValueError(f"source_draw_count 는 1 이상이어야 합니다: {source_draw_count}")
    if latest_draw_no <= 0:
        raise ValueError(f"latest_draw_no 는 1 이상이어야 합니다: {latest_draw_no}")
    if oldest_draw_no is None:
        oldest_draw_no = max(1, latest_draw_no - source_draw_count + 1)
    if oldest_draw_no <= 0 or oldest_draw_no > latest_draw_no:
        raise ValueError(
            "oldest_draw_no 는 1 이상이면서 latest_draw_no 이하이어야 합니다."
        )
    if top_n <= 0:
        raise ValueError(f"top_n 은 1 이상이어야 합니다: {top_n}")

    top_frequency_numbers = tuple(
        number
        for number, _ in sorted(
            stats.number_frequency.items(),
            key=lambda item: (-item[1], item[0]),
        )[:top_n]
    )
    timestamp = generated_at or datetime.now(timezone.utc)
    return AnalysisRunSummary(
        source_draw_count=source_draw_count,
        latest_draw_no=latest_draw_no,
        oldest_draw_no=oldest_draw_no,
        dominant_ratio=str(stats.odd_even_ratio["dominant_ratio"]),
        top_frequency_numbers=top_frequency_numbers,
        generated_at=timestamp.isoformat(),
    )


def _calculate_number_last_seen(draws: Sequence[object]) -> dict[int, int]:
    normalized = _normalize_numbers(draws)
    sentinel = len(normalized) + 1
    last_seen = {number: sentinel for number in range(1, 46)}
    for index, draw in enumerate(normalized, start=1):
        for number in draw:
            if last_seen[number] == sentinel:
                last_seen[number] = index
    return last_seen


def _calculate_sum_range(draws: Sequence[object]) -> tuple[int, int]:
    totals = sorted(sum(draw) for draw in _normalize_numbers(draws))
    if len(totals) == 1:
        return (totals[0], totals[0])

    lower_index = max(0, int(len(totals) * 0.1) - 1)
    upper_index = min(len(totals) - 1, int(len(totals) * 0.9))
    return (totals[lower_index], totals[upper_index])


def _normalize_numbers(draws: Sequence[object]) -> list[tuple[int, ...]]:
    analyze_patterns(draws)
    normalized: list[tuple[int, ...]] = []
    for draw in draws:
        numbers = getattr(draw, "numbers", draw)
        normalized.append(tuple(sorted(numbers)))
    return normalized
