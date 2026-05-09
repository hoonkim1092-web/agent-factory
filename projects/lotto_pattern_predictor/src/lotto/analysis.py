"""번호별 출현빈도·동시출현·구간 통계 분석 엔진."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from .exceptions import AnalysisError
from .models import DrawResult


# ── 분석 데이터 모델 ────────────────────────────────────


@dataclass(frozen=True)
class NumberFrequency:
    """번호별 출현 빈도 통계."""

    number: int  # 1~45
    count: int  # 출현 횟수
    last_appeared_draw: int  # 마지막 출현 회차
    avg_gap: float  # 평균 출현 간격


@dataclass(frozen=True)
class PairCooccurrence:
    """번호 쌍 동시 출현 통계."""

    num_a: int  # 작은 번호
    num_b: int  # 큰 번호 (num_a < num_b)
    count: int  # 동시 출현 횟수


@dataclass(frozen=True)
class AnalysisResult:
    """전체 분석 결과 집합."""

    total_draws: int
    frequencies: dict[int, NumberFrequency]
    bonus_frequencies: dict[int, int]
    pair_cooccurrences: dict[tuple[int, int], PairCooccurrence]
    window_frequencies: dict[str, dict[int, int]]
    weights: dict[int, float]  # 0.0~1.0 정규화


# ── 기본 윈도우 크기 ─────────────────────────────────────

DEFAULT_WINDOWS: dict[str, int] = {
    "최근_50회": 50,
    "최근_100회": 100,
    "최근_200회": 200,
}


# ── 분석 엔진 ────────────────────────────────────────────


class AnalysisEngine:
    """로또 당첨번호 통계 분석 엔진.

    Args:
        draws: 분석 대상 DrawResult 목록 (회차 오름차순 권장).
        windows: 구간 통계 윈도우 크기 매핑. None이면 기본값 사용.
    """

    def __init__(
        self,
        draws: list[DrawResult],
        windows: dict[str, int] | None = None,
    ) -> None:
        if not draws:
            raise AnalysisError("분석할 데이터가 없습니다")
        # 회차 오름차순 정렬
        self._draws = sorted(draws, key=lambda d: d.draw_no)
        self._windows = windows if windows is not None else DEFAULT_WINDOWS

    # ── 공개 API ──────────────────────────────────────

    def analyze(self) -> AnalysisResult:
        """모든 통계를 계산하고 AnalysisResult를 반환한다."""
        frequencies = self.compute_frequencies()
        bonus_frequencies = self.compute_bonus_frequencies()
        pair_cooccurrences = self.compute_pair_cooccurrences()
        window_frequencies = self.compute_window_frequencies()
        weights = self.compute_weights(frequencies, window_frequencies)
        return AnalysisResult(
            total_draws=len(self._draws),
            frequencies=frequencies,
            bonus_frequencies=bonus_frequencies,
            pair_cooccurrences=pair_cooccurrences,
            window_frequencies=window_frequencies,
            weights=weights,
        )

    def compute_frequencies(self) -> dict[int, NumberFrequency]:
        """번호별(1~45) 출현 빈도를 계산한다."""
        counts: dict[int, int] = defaultdict(int)
        last_appeared: dict[int, int] = {}
        appearances: dict[int, list[int]] = defaultdict(list)

        for draw in self._draws:
            for num in draw.numbers:
                counts[num] += 1
                last_appeared[num] = draw.draw_no
                appearances[num].append(draw.draw_no)

        result: dict[int, NumberFrequency] = {}
        for num in range(1, 46):
            count = counts.get(num, 0)
            last_draw = last_appeared.get(num, 0)
            avg_gap = self._calc_avg_gap(appearances.get(num, []))
            result[num] = NumberFrequency(
                number=num,
                count=count,
                last_appeared_draw=last_draw,
                avg_gap=avg_gap,
            )
        return result

    def compute_bonus_frequencies(self) -> dict[int, int]:
        """보너스 번호별(1~45) 출현 횟수를 계산한다."""
        counts: dict[int, int] = defaultdict(int)
        for draw in self._draws:
            counts[draw.bonus] += 1
        return {num: counts.get(num, 0) for num in range(1, 46)}

    def compute_pair_cooccurrences(self) -> dict[tuple[int, int], PairCooccurrence]:
        """모든 번호 쌍의 동시 출현 횟수를 계산한다."""
        pair_counts: dict[tuple[int, int], int] = defaultdict(int)
        for draw in self._draws:
            for a, b in combinations(sorted(draw.numbers), 2):
                pair_counts[(a, b)] += 1

        return {
            pair: PairCooccurrence(num_a=pair[0], num_b=pair[1], count=count)
            for pair, count in pair_counts.items()
        }

    def compute_window_frequencies(self) -> dict[str, dict[int, int]]:
        """구간별 번호 출현 빈도를 계산한다.

        각 윈도우는 최근 N회차 데이터만 사용한다.
        """
        result: dict[str, dict[int, int]] = {}
        for name, size in self._windows.items():
            window_draws = self._draws[-size:]
            counts: dict[int, int] = defaultdict(int)
            for draw in window_draws:
                for num in draw.numbers:
                    counts[num] += 1
            result[name] = {n: counts.get(n, 0) for n in range(1, 46)}
        return result

    def compute_weights(
        self,
        frequencies: dict[int, NumberFrequency],
        window_frequencies: dict[str, dict[int, int]],
    ) -> dict[int, float]:
        """번호별 가중치를 계산한다 (0.0~1.0 정규화).

        가중치 산출 전략:
        - 전체 빈도 점수 (40%)
        - 최근 구간 빈도 점수 (40%) — 가장 작은 윈도우 사용
        - 출현 간격 역수 점수 (20%) — 오래 안 나온 번호에 보정
        """
        total_draws = len(self._draws)
        if total_draws == 0:
            return {n: 0.0 for n in range(1, 46)}

        # 전체 빈도 비율
        freq_scores: dict[int, float] = {}
        for num in range(1, 46):
            freq_scores[num] = frequencies[num].count / total_draws

        # 최근 구간 빈도 비율 (가장 작은 윈도우)
        smallest_window_name = min(self._windows, key=self._windows.get)  # type: ignore[arg-type]
        smallest_size = min(self._windows.values())
        actual_size = min(smallest_size, total_draws)
        recent_scores: dict[int, float] = {}
        recent_freq = window_frequencies.get(smallest_window_name, {})
        for num in range(1, 46):
            recent_scores[num] = recent_freq.get(num, 0) / actual_size if actual_size > 0 else 0.0

        # 출현 간격 역수 점수 (마지막 회차와의 간격)
        latest_draw_no = self._draws[-1].draw_no
        gap_scores: dict[int, float] = {}
        max_gap = 0
        for num in range(1, 46):
            last = frequencies[num].last_appeared_draw
            gap = latest_draw_no - last if last > 0 else latest_draw_no
            gap_scores[num] = float(gap)
            if gap > max_gap:
                max_gap = gap

        # 간격이 클수록 높은 점수 (미출현 보정)
        if max_gap > 0:
            gap_scores = {n: g / max_gap for n, g in gap_scores.items()}

        # 합산 (40% + 40% + 20%)
        raw: dict[int, float] = {}
        for num in range(1, 46):
            raw[num] = (
                0.4 * freq_scores[num]
                + 0.4 * recent_scores[num]
                + 0.2 * gap_scores[num]
            )

        # 0~1 정규화
        raw_min = min(raw.values())
        raw_max = max(raw.values())
        spread = raw_max - raw_min
        if spread == 0:
            return {n: 1.0 for n in range(1, 46)}
        return {n: (v - raw_min) / spread for n, v in raw.items()}

    # ── 내부 헬퍼 ─────────────────────────────────────

    @staticmethod
    def _calc_avg_gap(draw_nos: list[int]) -> float:
        """출현 회차 목록으로부터 평균 출현 간격을 계산한다."""
        if len(draw_nos) < 2:
            return 0.0
        sorted_nos = sorted(draw_nos)
        gaps = [sorted_nos[i + 1] - sorted_nos[i] for i in range(len(sorted_nos) - 1)]
        return sum(gaps) / len(gaps)
