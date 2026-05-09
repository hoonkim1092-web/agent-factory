"""통계 분석 엔진 공개 인터페이스."""

from .patterns import (
    AnalysisRunSummary,
    PatternStats,
    analyze_patterns,
    build_pattern_stats_from_cache,
    build_statistics_summary,
    calculate_consecutive_gaps,
    calculate_number_frequency,
    calculate_odd_even_ratio,
    calculate_section_distribution,
    calculate_trend_weights,
    summarize_analysis_run,
)

__all__ = [
    "AnalysisRunSummary",
    "PatternStats",
    "analyze_patterns",
    "build_pattern_stats_from_cache",
    "build_statistics_summary",
    "calculate_consecutive_gaps",
    "calculate_number_frequency",
    "calculate_odd_even_ratio",
    "calculate_section_distribution",
    "calculate_trend_weights",
    "summarize_analysis_run",
]
