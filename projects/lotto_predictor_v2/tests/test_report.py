"""터미널 리포트 포맷 단위 테스트 — 계약 라인 + 가독성 검증."""
from __future__ import annotations

import re
from datetime import datetime

import pytest

from lotto.analytics.patterns import PatternStats
from lotto.recommender import Combination
from lotto.report import format_report, write_report


def _make_stats() -> PatternStats:
    freq = {n: 10 for n in range(1, 46)}
    freq[3] = 50
    freq[11] = 45
    gaps = {n: {"gaps": [], "average_gap": None, "last_gap": None, "appearance_count": 0} for n in range(1, 46)}
    return PatternStats(
        number_frequency=freq,
        consecutive_gaps=gaps,
        odd_even_ratio={"distribution": {}, "dominant_ratio": "3:3"},
        section_distribution={"1-10": 50, "11-20": 40, "21-30": 45, "31-40": 30, "41-45": 20},
        trend_weights={n: float(freq[n]) for n in range(1, 46)},
    )


def _make_combinations(count: int = 3) -> list[Combination]:
    samples = [
        (3, 11, 19, 27, 35, 42),
        (1, 9, 14, 28, 33, 45),
        (5, 12, 18, 24, 37, 44),
        (2, 8, 21, 29, 34, 41),
        (7, 13, 20, 26, 32, 39),
    ]
    return [
        Combination(
            numbers=samples[i],
            score=0.9 - i * 0.05,
            odd_even_ratio="3:3",
            section_distribution={"1-10": 1, "11-20": 2, "21-30": 1, "31-40": 1, "41-45": 1},
        )
        for i in range(count)
    ]


def test_report_contains_contract_lines_for_api_source():
    text = format_report(
        _make_combinations(5),
        _make_stats(),
        draw_count=500,
        latest_draw_no=1168,
        latest_draw_date="2026-04-05",
        data_source="api",
        status="success",
    )
    assert "동행복권 API 호출 완료: 500회차" in text
    assert "통계 분석 완료: 빈도/홀짝/구간/트렌드" in text
    assert "실행 상태: success" in text


def test_report_contains_cache_fallback_lines_for_cache_source():
    text = format_report(
        _make_combinations(5),
        _make_stats(),
        draw_count=500,
        data_source="cache",
        status="degraded-success",
    )
    assert "캐시 fallback 사용: 최근 저장 회차 500" in text
    assert "통계 분석 완료: cache_source=local" in text
    assert "실행 상태: degraded-success" in text


def test_report_combination_lines_match_contract_regex():
    """test_pyinstaller_e2e의 정규식으로 조합 라인 추출 가능해야 함."""
    text = format_report(
        _make_combinations(5),
        _make_stats(),
        draw_count=500,
    )
    matches = re.findall(r"추천 조합\s+\d+\s*:\s*([0-9,\s]+)", text)
    assert len(matches) == 5
    for chunk in matches:
        numbers = [int(n.strip()) for n in chunk.split(",")]
        assert len(numbers) == 6
        assert all(1 <= n <= 45 for n in numbers)


def test_report_header_includes_generation_time():
    now = datetime(2026, 4, 17, 23, 30)
    text = format_report(
        _make_combinations(3),
        _make_stats(),
        draw_count=100,
        generated_at=now,
    )
    assert "2026-04-17 23:30" in text


def test_report_validates_inputs():
    stats = _make_stats()
    with pytest.raises(ValueError):
        format_report([], stats, draw_count=100)
    with pytest.raises(ValueError):
        format_report(_make_combinations(1), stats, draw_count=0)


def test_write_report_appends_newline_if_missing():
    import io
    buf = io.StringIO()
    write_report("hello", stream=buf)
    assert buf.getvalue() == "hello\n"

    buf2 = io.StringIO()
    write_report("hello\n", stream=buf2)
    assert buf2.getvalue() == "hello\n"
