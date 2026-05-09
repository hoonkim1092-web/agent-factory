"""fetcher.py 통합 테스트 — 실제 동행복권 API 호출.

네트워크 연결이 필요하므로 기본적으로 건너뛴다.
실행: pytest tests/test_fetcher_integration.py -m integration --run-integration
"""

import pytest

from src.lotto.fetcher import LottoFetcher


pytestmark = pytest.mark.integration


@pytest.fixture
def fetcher():
    with LottoFetcher(delay=1.0) as f:
        yield f


@pytest.mark.skipif(
    True,  # CI/로컬 네트워크 환경에서 수동 전환
    reason="실제 API 호출 필요 — 수동 실행 전용",
)
class TestFetcherIntegration:
    """동행복권 API 실제 호출 검증."""

    def test_회차_1100_수집(self, fetcher: LottoFetcher):
        result = fetcher.fetch_draw(1100)
        assert result.draw_no == 1100
        assert len(result.numbers) == 6
        assert all(1 <= n <= 45 for n in result.numbers)

    def test_최근_3회차_수집(self, fetcher: LottoFetcher):
        results = fetcher.fetch_range(1098, 1100)
        assert len(results) == 3
        assert results[0].draw_no < results[-1].draw_no
