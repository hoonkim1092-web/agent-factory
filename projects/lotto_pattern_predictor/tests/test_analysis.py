"""AnalysisEngine 단위 테스트."""

from __future__ import annotations

import pytest
from datetime import date

from src.lotto.analysis import (
    AnalysisEngine,
    AnalysisResult,
    NumberFrequency,
    PairCooccurrence,
    DEFAULT_WINDOWS,
)
from src.lotto.exceptions import AnalysisError
from src.lotto.models import DrawResult


# ── 테스트 픽스처 ──────────────────────────────────────


def _draw(draw_no: int, numbers: tuple[int, ...], bonus: int = 7) -> DrawResult:
    """테스트용 DrawResult를 간편 생성한다."""
    return DrawResult(
        draw_no=draw_no,
        draw_date=date(2024, 1, draw_no if draw_no <= 28 else 28),
        numbers=numbers,
        bonus=bonus,
        total_sell_amount=100_000_000,
        first_prize_amount=2_000_000_000,
        first_prize_winners=10,
    )


@pytest.fixture
def sample_draws() -> list[DrawResult]:
    """3회차 테스트 데이터."""
    return [
        _draw(1, (1, 2, 3, 4, 5, 6), bonus=7),
        _draw(2, (1, 2, 3, 10, 11, 12), bonus=7),
        _draw(3, (1, 7, 14, 21, 28, 35), bonus=42),
    ]


@pytest.fixture
def engine(sample_draws: list[DrawResult]) -> AnalysisEngine:
    """기본 윈도우 설정의 엔진 인스턴스."""
    return AnalysisEngine(sample_draws, windows={"최근_3회": 3, "최근_2회": 2})


# ── 초기화 테스트 ──────────────────────────────────────


class TestInit:
    def test_빈_데이터_예외(self) -> None:
        with pytest.raises(AnalysisError, match="분석할 데이터가 없습니다"):
            AnalysisEngine([])

    def test_정상_초기화(self, sample_draws: list[DrawResult]) -> None:
        engine = AnalysisEngine(sample_draws)
        assert engine._draws[0].draw_no == 1
        assert engine._draws[-1].draw_no == 3

    def test_비순서_입력도_정렬(self) -> None:
        draws = [_draw(3, (1, 2, 3, 4, 5, 6)), _draw(1, (7, 8, 9, 10, 11, 12))]
        engine = AnalysisEngine(draws)
        assert engine._draws[0].draw_no == 1

    def test_커스텀_윈도우(self, sample_draws: list[DrawResult]) -> None:
        engine = AnalysisEngine(sample_draws, windows={"w1": 1})
        assert engine._windows == {"w1": 1}


# ── 빈도 계산 테스트 ─────────────────────────────────────


class TestComputeFrequencies:
    def test_출현_횟수(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        # 번호 1은 3회 모두 출현
        assert freq[1].count == 3
        # 번호 2는 1, 2회차에 출현
        assert freq[2].count == 2
        # 번호 45는 미출현
        assert freq[45].count == 0

    def test_마지막_출현_회차(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        assert freq[1].last_appeared_draw == 3
        assert freq[6].last_appeared_draw == 1
        assert freq[45].last_appeared_draw == 0

    def test_평균_간격(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        # 번호 1: 회차 1, 2, 3 → 간격 [1, 1] → 평균 1.0
        assert freq[1].avg_gap == 1.0
        # 번호 2: 회차 1, 2 → 간격 [1] → 평균 1.0
        assert freq[2].avg_gap == 1.0
        # 번호 6: 회차 1만 → 간격 없음 → 0.0
        assert freq[6].avg_gap == 0.0

    def test_전체_범위_포함(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        assert set(freq.keys()) == set(range(1, 46))

    def test_반환_타입(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        assert isinstance(freq[1], NumberFrequency)


# ── 보너스 빈도 테스트 ───────────────────────────────────


class TestComputeBonusFrequencies:
    def test_보너스_횟수(self, engine: AnalysisEngine) -> None:
        bf = engine.compute_bonus_frequencies()
        assert bf[7] == 2  # 1, 2회차
        assert bf[42] == 1  # 3회차
        assert bf[1] == 0

    def test_전체_범위(self, engine: AnalysisEngine) -> None:
        bf = engine.compute_bonus_frequencies()
        assert set(bf.keys()) == set(range(1, 46))


# ── 동시출현 테스트 ──────────────────────────────────────


class TestComputePairCooccurrences:
    def test_동시출현_횟수(self, engine: AnalysisEngine) -> None:
        pairs = engine.compute_pair_cooccurrences()
        # (1, 2)는 1, 2회차에 동시 출현
        assert pairs[(1, 2)].count == 2
        # (1, 3)도 1, 2회차에 동시 출현
        assert pairs[(1, 3)].count == 2
        # (4, 5)는 1회차에만
        assert pairs[(4, 5)].count == 1

    def test_미출현_쌍(self, engine: AnalysisEngine) -> None:
        pairs = engine.compute_pair_cooccurrences()
        # (6, 10)은 같은 회차에 없었음
        assert (6, 10) not in pairs

    def test_쌍_순서(self, engine: AnalysisEngine) -> None:
        pairs = engine.compute_pair_cooccurrences()
        for (a, b), pc in pairs.items():
            assert a < b
            assert pc.num_a == a
            assert pc.num_b == b


# ── 구간 통계 테스트 ─────────────────────────────────────


class TestComputeWindowFrequencies:
    def test_윈도우_크기(self, engine: AnalysisEngine) -> None:
        wf = engine.compute_window_frequencies()
        assert "최근_3회" in wf
        assert "최근_2회" in wf

    def test_최근_2회_빈도(self, engine: AnalysisEngine) -> None:
        wf = engine.compute_window_frequencies()
        recent2 = wf["최근_2회"]
        # 최근 2회 = 2회차 + 3회차
        # 2회차: 1, 2, 3, 10, 11, 12
        # 3회차: 1, 7, 14, 21, 28, 35
        assert recent2[1] == 2  # 2, 3회차 모두
        assert recent2[2] == 1  # 2회차만
        assert recent2[7] == 1  # 3회차만
        assert recent2[6] == 0  # 1회차에만 출현 (범위 밖)

    def test_전체_번호_포함(self, engine: AnalysisEngine) -> None:
        wf = engine.compute_window_frequencies()
        for window_data in wf.values():
            assert set(window_data.keys()) == set(range(1, 46))


# ── 가중치 테스트 ────────────────────────────────────────


class TestComputeWeights:
    def test_범위_0_1(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        wf = engine.compute_window_frequencies()
        weights = engine.compute_weights(freq, wf)
        for w in weights.values():
            assert 0.0 <= w <= 1.0

    def test_최소_최대_존재(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        wf = engine.compute_window_frequencies()
        weights = engine.compute_weights(freq, wf)
        values = list(weights.values())
        assert min(values) == 0.0
        assert max(values) == 1.0

    def test_전체_범위(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        wf = engine.compute_window_frequencies()
        weights = engine.compute_weights(freq, wf)
        assert set(weights.keys()) == set(range(1, 46))

    def test_빈번_번호가_높은_가중치(self, engine: AnalysisEngine) -> None:
        freq = engine.compute_frequencies()
        wf = engine.compute_window_frequencies()
        weights = engine.compute_weights(freq, wf)
        # 번호 1은 매회 출현 → 높은 가중치
        assert weights[1] > weights[45]


# ── 통합 analyze() 테스트 ────────────────────────────────


class TestAnalyze:
    def test_반환_타입(self, engine: AnalysisEngine) -> None:
        result = engine.analyze()
        assert isinstance(result, AnalysisResult)

    def test_총_회차수(self, engine: AnalysisEngine) -> None:
        result = engine.analyze()
        assert result.total_draws == 3

    def test_모든_필드_채워짐(self, engine: AnalysisEngine) -> None:
        result = engine.analyze()
        assert len(result.frequencies) == 45
        assert len(result.bonus_frequencies) == 45
        assert len(result.pair_cooccurrences) > 0
        assert len(result.window_frequencies) == 2
        assert len(result.weights) == 45


# ── 단일 회차 엣지 케이스 ────────────────────────────────


class TestSingleDraw:
    def test_단일_회차_분석(self) -> None:
        draws = [_draw(1, (1, 2, 3, 4, 5, 6))]
        engine = AnalysisEngine(draws, windows={"최근_1회": 1})
        result = engine.analyze()
        assert result.total_draws == 1
        assert result.frequencies[1].count == 1
        assert result.frequencies[1].avg_gap == 0.0

    def test_단일_회차_가중치(self) -> None:
        draws = [_draw(1, (1, 2, 3, 4, 5, 6))]
        engine = AnalysisEngine(draws, windows={"최근_1회": 1})
        result = engine.analyze()
        # 출현 번호 가중치 > 미출현 번호 가중치
        assert result.weights[1] > result.weights[45]
