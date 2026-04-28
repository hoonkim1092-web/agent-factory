"""통계 분석 엔진 단위 테스트."""

from __future__ import annotations

import importlib
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.lotto.models import DrawResult


def _load_analysis_module():
    """구현 파일 경로 차이를 흡수해 분석 모듈을 로드한다."""

    for module_name in ("src.lotto.analyzer", "src.lotto.analysis"):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
    raise ModuleNotFoundError("src.lotto.analyzer 또는 src.lotto.analysis 모듈이 필요합니다.")


analysis_module = _load_analysis_module()
AnalysisEngine = analysis_module.AnalysisEngine
AnalysisResult = analysis_module.AnalysisResult
NumberFrequency = analysis_module.NumberFrequency
PairCooccurrence = analysis_module.PairCooccurrence


def _추첨결과(
    draw_no: int,
    numbers: tuple[int, int, int, int, int, int],
    bonus: int = 7,
) -> DrawResult:
    return DrawResult(
        draw_no=draw_no,
        draw_date=date(2024, 1, 1) + timedelta(days=draw_no),
        numbers=numbers,
        bonus=bonus,
        total_sell_amount=1_000_000,
        first_prize_amount=500_000,
        first_prize_winners=1,
    )


def _회전_번호(draw_no: int) -> tuple[int, int, int, int, int, int]:
    시작값 = ((draw_no - 1) % 45) + 1
    numbers = {((시작값 + 오프셋 - 1) % 45) + 1 for 오프셋 in range(6)}
    return tuple(sorted(numbers))  # type: ignore[return-value]


@pytest.fixture
def 분석용_추첨목록() -> list[DrawResult]:
    return [
        _추첨결과(101, (1, 2, 3, 4, 5, 45), bonus=6),
        _추첨결과(102, (1, 2, 3, 10, 11, 12), bonus=13),
        _추첨결과(103, (1, 7, 8, 9, 10, 45), bonus=11),
    ]


@pytest.fixture
def 단일_추첨() -> list[DrawResult]:
    return [_추첨결과(201, (4, 8, 15, 16, 23, 42), bonus=7)]


@pytest.fixture
def 육십회_윈도우_추첨목록() -> list[DrawResult]:
    draws: list[DrawResult] = []
    for draw_no in range(1, 11):
        draws.append(_추첨결과(draw_no, (1, 2, 3, 4, 5, 6), bonus=7))
    for draw_no in range(11, 61):
        draws.append(_추첨결과(draw_no, (40, 41, 42, 43, 44, 45), bonus=39))
    return draws


@pytest.fixture
def 전체번호_포함_추첨목록() -> list[DrawResult]:
    return [_추첨결과(draw_no, _회전_번호(draw_no), bonus=((draw_no + 6 - 1) % 45) + 1) for draw_no in range(1, 61)]


class TestComputeFrequencies:
    """번호별 출현 빈도 테스트."""

    def test_알려진_입력에_대한_번호별_출현_횟수를_정확히_계산한다(self, 분석용_추첨목록: list[DrawResult]):
        engine = AnalysisEngine(분석용_추첨목록)

        frequencies = engine.compute_frequencies()

        assert frequencies[1].count == 3
        assert frequencies[2].count == 2
        assert frequencies[10].count == 2
        assert frequencies[45].count == 2
        assert frequencies[6].count == 0

    def test_빈_리스트에서도_빈도_계산_결과를_안전하게_반환한다(self):
        engine = AnalysisEngine.__new__(AnalysisEngine)
        engine._draws = []
        engine._windows = {"recent_50": 50, "recent_100": 100}

        frequencies = engine.compute_frequencies()

        assert frequencies == {} or all(정보.count == 0 for 정보 in frequencies.values())

    def test_번호_1과_45_경계값_빈도를_정확히_처리한다(self, 분석용_추첨목록: list[DrawResult]):
        engine = AnalysisEngine(분석용_추첨목록)

        frequencies = engine.compute_frequencies()

        assert frequencies[1].number == 1
        assert frequencies[1].count == 3
        assert frequencies[45].number == 45
        assert frequencies[45].count == 2


class TestComputePairCooccurrences:
    """번호 쌍 동시 출현 테스트."""

    def test_알려진_입력에_대한_번호쌍_동시출현_횟수를_정확히_계산한다(self, 분석용_추첨목록: list[DrawResult]):
        engine = AnalysisEngine(분석용_추첨목록)

        pair_counts = engine.compute_pair_cooccurrences()

        assert pair_counts[(1, 2)].count == 2
        assert pair_counts[(1, 3)].count == 2
        assert pair_counts[(1, 45)].count == 2
        assert pair_counts[(10, 11)].count == 1

    def test_단일_추첨에서도_열다섯개_번호쌍을_생성한다(self, 단일_추첨: list[DrawResult]):
        engine = AnalysisEngine(단일_추첨)

        pair_counts = engine.compute_pair_cooccurrences()

        assert len(pair_counts) == 15

    def test_키가_항상_오름차순으로_정렬된다(self, 단일_추첨: list[DrawResult]):
        engine = AnalysisEngine(단일_추첨)

        pair_counts = engine.compute_pair_cooccurrences()

        assert all(num_a < num_b for num_a, num_b in pair_counts.keys())
        assert all(key == (value.num_a, value.num_b) for key, value in pair_counts.items())


class TestComputeWindowFrequencies:
    """구간별 빈도 테스트."""

    def test_window_50일_때_최근_오십건만_사용한다(self, 육십회_윈도우_추첨목록: list[DrawResult]):
        engine = AnalysisEngine(육십회_윈도우_추첨목록, windows={"recent_50": 50})

        window_frequencies = engine.compute_window_frequencies()

        assert window_frequencies["recent_50"][1] == 0
        assert window_frequencies["recent_50"][45] == 50

    def test_전체_데이터가_window보다_적을_때는_전체를_사용한다(self, 분석용_추첨목록: list[DrawResult]):
        engine = AnalysisEngine(분석용_추첨목록, windows={"recent_50": 50})

        window_frequencies = engine.compute_window_frequencies()

        assert window_frequencies["recent_50"][1] == 3
        assert window_frequencies["recent_50"][45] == 2


class TestComputeWeights:
    """가중치 계산 테스트."""

    def test_가중치_공식_40_40_20을_검증한다(self, 육십회_윈도우_추첨목록: list[DrawResult]):
        """가중치 산출: 전체 빈도 40% + 최근 구간 40% + 간격 역수 20% → 0~1 정규화."""
        engine = AnalysisEngine(육십회_윈도우_추첨목록, windows={"recent_50": 50})
        frequencies = engine.compute_frequencies()
        window_frequencies = engine.compute_window_frequencies()

        weights = engine.compute_weights(frequencies, window_frequencies)

        # 번호 45는 최근 50회에 매회 출현 + 전체 60회 중 50회 → 높은 가중치
        assert weights[45] == pytest.approx(1.0)
        # 모든 가중치는 0~1 범위
        assert all(0.0 <= w <= 1.0 for w in weights.values())

    def test_반환된_가중치가_모두_비음수다(self, 전체번호_포함_추첨목록: list[DrawResult]):
        engine = AnalysisEngine(전체번호_포함_추첨목록, windows={"recent_50": 50})
        frequencies = engine.compute_frequencies()
        window_frequencies = engine.compute_window_frequencies()

        weights = engine.compute_weights(frequencies, window_frequencies)

        assert all(weight >= 0 for weight in weights.values())

    def test_모든_번호에_대한_가중치가_존재한다(self, 전체번호_포함_추첨목록: list[DrawResult]):
        engine = AnalysisEngine(전체번호_포함_추첨목록, windows={"recent_50": 50})
        frequencies = engine.compute_frequencies()
        window_frequencies = engine.compute_window_frequencies()

        weights = engine.compute_weights(frequencies, window_frequencies)

        assert set(weights) == set(range(1, 46))


class TestAnalysisResult:
    """분석 결과 컨테이너 테스트."""

    def test_모든_필드가_올바르게_저장된다(self):
        frequencies = {
            1: NumberFrequency(number=1, count=3, last_appeared_draw=103, avg_gap=1.0),
        }
        bonus_frequencies = {7: 2}
        pair_cooccurrences = {
            (1, 45): PairCooccurrence(num_a=1, num_b=45, count=2),
        }
        window_frequencies = {
            "recent_50": {1: 3},
            "all": {1: 3},
        }
        weights = {1: 1.0}

        result = AnalysisResult(
            total_draws=3,
            frequencies=frequencies,
            bonus_frequencies=bonus_frequencies,
            pair_cooccurrences=pair_cooccurrences,
            window_frequencies=window_frequencies,
            weights=weights,
        )

        assert result.total_draws == 3
        assert result.frequencies == frequencies
        assert result.bonus_frequencies == bonus_frequencies
        assert result.pair_cooccurrences == pair_cooccurrences
        assert result.window_frequencies == window_frequencies
        assert result.weights == weights
