"""가중 랜덤 추천기 단위 테스트."""

from __future__ import annotations

import importlib
import random
import sys
from collections import Counter
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _추천_함수():
    """추천 생성기 인터페이스를 로드한다."""

    try:
        module = importlib.import_module("src.lotto.recommender")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("`src.lotto.recommender` 모듈 구현이 필요합니다.") from exc

    try:
        return module.generate_recommendations
    except AttributeError as exc:
        raise AttributeError(
            "`src.lotto.recommender.generate_recommendations(weights, count=5, rng=None)` 함수가 필요합니다."
        ) from exc


def _추천_생성(
    weights: dict[int, float],
    *,
    count: int = 5,
    seed: int = 1234,
):
    추천_함수 = _추천_함수()
    return 추천_함수(weights=weights, count=count, rng=random.Random(seed))


def _번호_빈도_집계(추천결과: list[tuple[int, ...]]) -> Counter[int]:
    빈도: Counter[int] = Counter()
    for 조합 in 추천결과:
        빈도.update(조합)
    return 빈도


@pytest.fixture
def 기본_가중치() -> dict[int, float]:
    return {번호: float(번호) / 45.0 for 번호 in range(1, 46)}


@pytest.fixture
def 고가중치_가중치() -> dict[int, float]:
    가중치 = {번호: 1.0 for 번호 in range(1, 46)}
    for 번호 in range(1, 7):
        가중치[번호] = 25.0
    return 가중치


@pytest.fixture
def 영가중치_포함_가중치() -> dict[int, float]:
    가중치 = {번호: 1.0 for 번호 in range(1, 46)}
    for 번호 in (1, 2, 3, 4, 5):
        가중치[번호] = 0.0
    return 가중치


@pytest.fixture
def 균등_가중치() -> dict[int, float]:
    return {번호: 1.0 for 번호 in range(1, 13)}


class Test추천조합_기본검증:
    """추천 조합 기본 제약 테스트."""

    def test_기본_추천은_오조합을_반환한다(self, 기본_가중치: dict[int, float]):
        추천결과 = _추천_생성(기본_가중치, count=5)

        assert len(추천결과) == 5

    def test_각_조합은_DrawResult와_동일하게_여섯개_오름차순_번호를_가진다(self, 기본_가중치: dict[int, float]):
        추천결과 = _추천_생성(기본_가중치, count=5)

        assert all(len(조합) == 6 for 조합 in 추천결과)
        assert all(tuple(sorted(조합)) == 조합 for 조합 in 추천결과)

    def test_모든_번호는_일에서_사십오_범위다(self, 기본_가중치: dict[int, float]):
        추천결과 = _추천_생성(기본_가중치, count=5)

        assert all(1 <= 번호 <= 45 for 조합 in 추천결과 for 번호 in 조합)

    def test_조합_사이에_중복_조합이_없다(self, 기본_가중치: dict[int, float]):
        추천결과 = _추천_생성(기본_가중치, count=5)

        assert len({tuple(조합) for 조합 in 추천결과}) == len(추천결과)


class Test가중치_반영:
    """가중치 반영 통계 테스트."""

    def test_높은_가중치_번호가_백회_반복에서_더_자주_선택된다(self, 고가중치_가중치: dict[int, float]):
        누적빈도: Counter[int] = Counter()

        for seed in range(100):
            추천결과 = _추천_생성(고가중치_가중치, count=5, seed=seed)
            누적빈도.update(_번호_빈도_집계(추천결과))

        고가중치_평균 = sum(누적빈도[번호] for 번호 in range(1, 7)) / 6
        저가중치_평균 = sum(누적빈도[번호] for 번호 in range(7, 46)) / 39

        assert 고가중치_평균 > 저가중치_평균

    def test_가중치가_영인_번호는_선택되지_않는다(self, 영가중치_포함_가중치: dict[int, float]):
        누적빈도: Counter[int] = Counter()

        for seed in range(50):
            추천결과 = _추천_생성(영가중치_포함_가중치, count=5, seed=seed)
            누적빈도.update(_번호_빈도_집계(추천결과))

        assert all(누적빈도[번호] == 0 for 번호 in (1, 2, 3, 4, 5))

    def test_균등_가중치일_때는_선택_분포가_크게_치우치지_않는다(self, 균등_가중치: dict[int, float]):
        누적빈도: Counter[int] = Counter()

        for seed in range(200):
            추천결과 = _추천_생성(균등_가중치, count=5, seed=seed)
            누적빈도.update(_번호_빈도_집계(추천결과))

        기대평균 = sum(누적빈도.values()) / len(균등_가중치)
        허용편차 = 기대평균 * 0.35

        assert all(
            abs(누적빈도[번호] - 기대평균) <= 허용편차
            for 번호 in 균등_가중치
        )


class Test엣지케이스:
    """입력 유효성 테스트."""

    def test_가중치_딕셔너리가_비어있으면_에러를_발생시킨다(self):
        with pytest.raises(ValueError, match="가중치"):
            _추천_생성({}, count=5)

    def test_가중치가_있는_번호가_여섯개_미만이면_에러를_발생시킨다(self):
        부족한_가중치 = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0}

        with pytest.raises(ValueError, match="6개"):
            _추천_생성(부족한_가중치, count=5)
