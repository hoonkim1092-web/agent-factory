"""터미널 포맷 출력 리포트 모듈.

추천 조합과 패턴 통계를 사람이 읽기 좋은 한국어 텍스트로 포맷한다.
PyInstaller 단일 실행 파일에서도 외부 의존성 없이 동작하도록 표준 라이브러리만 사용한다.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from io import StringIO
from typing import Any

from .analytics.patterns import SECTION_RANGES, PatternStats
from .recommender import Combination


LINE = "=" * 60
SUB_LINE = "-" * 60


def format_report(
    combinations: Sequence[Combination],
    stats: PatternStats,
    *,
    draw_count: int,
    latest_draw_no: int | None = None,
    latest_draw_date: str | None = None,
    generated_at: datetime | None = None,
    data_source: str = "api",
    status: str = "success",
) -> str:
    """추천 조합과 통계를 터미널 리포트 문자열로 반환한다.

    data_source: "api" | "cache" — 데이터 출처 표기 ("api" → "동행복권 API 호출 완료",
    "cache" → "캐시 fallback 사용")
    status: "success" | "degraded-success" — 최종 실행 상태 라인
    """

    if not combinations:
        raise ValueError("combinations는 1개 이상이어야 합니다.")
    if draw_count <= 0:
        raise ValueError("draw_count는 1 이상이어야 합니다.")

    buf = StringIO()
    _write_header(buf, draw_count, latest_draw_no, latest_draw_date, generated_at)
    _write_contract_source(buf, draw_count, data_source)
    _write_combinations(buf, combinations)
    _write_pattern_summary(buf, stats)
    _write_contract_status(buf, status)
    _write_footer(buf)
    return buf.getvalue()


def _write_contract_source(buf: StringIO, draw_count: int, data_source: str) -> None:
    """e2e 테스트 계약 라인: 데이터 출처 표기."""
    if data_source == "cache":
        buf.write(f"캐시 fallback 사용: 최근 저장 회차 {draw_count}\n")
        buf.write("통계 분석 완료: cache_source=local\n")
    else:
        buf.write(f"동행복권 API 호출 완료: {draw_count}회차\n")
        buf.write("통계 분석 완료: 빈도/홀짝/구간/트렌드\n")
    buf.write("\n")


def _write_contract_status(buf: StringIO, status: str) -> None:
    """e2e 테스트 계약 라인: 최종 실행 상태."""
    buf.write(f"실행 상태: {status}\n")


def _write_header(
    buf: StringIO,
    draw_count: int,
    latest_draw_no: int | None,
    latest_draw_date: str | None,
    generated_at: datetime | None,
) -> None:
    ts = (generated_at or datetime.now()).strftime("%Y-%m-%d %H:%M")
    buf.write(LINE + "\n")
    buf.write("  로또 6/45 패턴 기반 추천 번호 리포트\n")
    buf.write(LINE + "\n")
    buf.write(f"  분석 회차 수   : 최근 {draw_count}회\n")
    if latest_draw_no is not None:
        tail = f" ({latest_draw_date})" if latest_draw_date else ""
        buf.write(f"  최신 회차      : {latest_draw_no}회차{tail}\n")
    buf.write(f"  생성 일시      : {ts}\n")
    buf.write(SUB_LINE + "\n\n")


def _write_combinations(buf: StringIO, combinations: Sequence[Combination]) -> None:
    buf.write(f"[추천 조합 {len(combinations)}개]\n\n")
    for rank, combo in enumerate(combinations, start=1):
        # 계약 형식: "추천 조합 N: a, b, c, d, e, f"
        contract_line = ", ".join(str(n) for n in combo.numbers)
        buf.write(f"  추천 조합 {rank}: {contract_line}\n")
        sections = _format_section_distribution(combo.section_distribution)
        buf.write(f"      점수: {combo.score:.4f}   홀짝: {combo.odd_even_ratio}   구간: {sections}\n\n")


def _write_pattern_summary(buf: StringIO, stats: PatternStats) -> None:
    buf.write(SUB_LINE + "\n")
    buf.write("[패턴 요약]\n\n")

    top_numbers = sorted(
        stats.number_frequency.items(),
        key=lambda item: (-item[1], item[0]),
    )[:10]
    freq_line = ", ".join(f"{num}({count})" for num, count in top_numbers)
    buf.write(f"  출현 상위 10  : {freq_line}\n")

    trend_top = sorted(
        stats.trend_weights.items(),
        key=lambda item: (-item[1], item[0]),
    )[:10]
    trend_line = ", ".join(f"{num}({weight:.2f})" for num, weight in trend_top)
    buf.write(f"  최근 트렌드   : {trend_line}\n")

    section_line = ", ".join(
        f"{label}:{stats.section_distribution.get(label, 0)}"
        for label, _ in SECTION_RANGES
    )
    buf.write(f"  구간 분포     : {section_line}\n")

    oe = stats.odd_even_ratio
    dominant = oe.get("dominant_ratio") if isinstance(oe, dict) else None
    if dominant:
        buf.write(f"  홀짝 대표비율 : {dominant}\n")
    buf.write("\n")


def _write_footer(buf: StringIO) -> None:
    buf.write(SUB_LINE + "\n")
    buf.write("  ※ 본 리포트는 통계적 패턴 분석 결과이며 당첨을 보장하지 않습니다.\n")
    buf.write(LINE + "\n")


def _format_section_distribution(distribution: dict[str, int]) -> str:
    parts = []
    for label, _ in SECTION_RANGES:
        value = distribution.get(label, 0)
        if value:
            parts.append(f"{label}×{value}")
    return " ".join(parts) if parts else "-"


def write_report(report_text: str, stream: Any | None = None) -> None:
    """리포트 텍스트를 stream(기본 stdout)에 출력한다."""
    import sys

    out = stream if stream is not None else sys.stdout
    out.write(report_text)
    if not report_text.endswith("\n"):
        out.write("\n")
