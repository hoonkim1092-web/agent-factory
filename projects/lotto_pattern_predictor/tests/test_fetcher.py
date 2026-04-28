"""fetcher.py 단위 테스트.

실제 네트워크 호출 없이 응답을 모킹하여 검증한다.
"""

from datetime import date
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from src.lotto.exceptions import DrawNotFoundError, FetchError
from src.lotto.fetcher import LottoFetcher, _parse_draw_response


@pytest.fixture
def sample_response() -> dict:
    return {
        "returnValue": "success",
        "drwNo": 1100,
        "drwNoDate": "2024-01-20",
        "drwtNo1": 40,
        "drwtNo2": 3,
        "drwtNo3": 23,
        "drwtNo4": 10,
        "drwtNo5": 37,
        "drwtNo6": 33,
        "bnusNo": 16,
        "totSellamnt": 3681782000,
        "firstWinamnt": 2312839938,
        "firstPrzwnerCo": 8,
        "firstAccumamnt": 18502719504,
    }


@pytest.fixture
def not_found_response() -> dict:
    return {
        "returnValue": "fail",
        "drwNo": 9999,
    }


@pytest.fixture
def response_factory():
    def _build(json_data: dict, *, raise_error: Exception | None = None) -> MagicMock:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = json_data
        if raise_error is not None:
            response.raise_for_status.side_effect = raise_error
        return response

    return _build


@pytest.fixture
def session_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def fetcher(session_mock: MagicMock) -> LottoFetcher:
    return LottoFetcher(
        timeout=5,
        delay=0.25,
        max_retries=3,
        session=session_mock,
    )


class TestParseDrawResponse:
    """API JSON 응답 파싱 정합성 검증."""

    def test_정상_응답을_DrawResult로_변환한다(self, sample_response: dict):
        result = _parse_draw_response(sample_response)

        assert result.draw_no == 1100
        assert result.draw_date == date(2024, 1, 20)
        assert result.numbers == (3, 10, 23, 33, 37, 40)
        assert result.bonus == 16
        assert result.total_sell_amount == 3_681_782_000
        assert result.first_prize_amount == 2_312_839_938
        assert result.first_prize_winners == 8

    def test_fail_응답이면_DrawNotFoundError를_발생시킨다(self, not_found_response: dict):
        with pytest.raises(DrawNotFoundError, match="9999"):
            _parse_draw_response(not_found_response)

    def test_필수_필드가_누락되면_FetchError를_발생시킨다(self):
        broken_response = {
            "returnValue": "success",
            "drwNo": 1,
            "drwNoDate": "2024-01-20",
        }

        with pytest.raises(FetchError, match="파싱 실패"):
            _parse_draw_response(broken_response)


class TestLottoFetcher:
    """수집기 동작 검증."""

    def test_단일_회차를_조회한다(
        self,
        fetcher: LottoFetcher,
        session_mock: MagicMock,
        sample_response: dict,
        response_factory,
    ):
        session_mock.get.return_value = response_factory(sample_response)

        result = fetcher.fetch_draw(1100)

        assert result.draw_no == 1100
        session_mock.get.assert_called_once_with(
            "https://www.dhlottery.co.kr/common.do",
            params={"method": "getLottoNumber", "drwNo": 1100},
            timeout=5,
        )

    def test_네트워크_타임아웃_후_재시도에_성공한다(
        self,
        fetcher: LottoFetcher,
        session_mock: MagicMock,
        sample_response: dict,
        response_factory,
    ):
        session_mock.get.side_effect = [
            requests.Timeout("타임아웃"),
            response_factory(sample_response),
        ]

        with patch("src.lotto.fetcher.time.sleep") as sleep_mock:
            result = fetcher.fetch_draw(1100)

        assert result.draw_no == 1100
        assert session_mock.get.call_count == 2
        sleep_mock.assert_called_once_with(0.25)

    def test_네트워크_오류가_반복되면_최대_횟수까지_재시도한다(
        self,
        fetcher: LottoFetcher,
        session_mock: MagicMock,
    ):
        session_mock.get.side_effect = requests.ConnectionError("연결 실패")

        with patch("src.lotto.fetcher.time.sleep") as sleep_mock:
            with pytest.raises(FetchError, match="시도 3/3"):
                fetcher.fetch_draw(1100)

        assert session_mock.get.call_count == 3
        assert sleep_mock.call_args_list == [call(0.25), call(0.5)]

    @pytest.mark.parametrize("invalid_draw_no", [0, -1, -100])
    def test_비정상_회차번호면_즉시_ValueError를_발생시킨다(
        self,
        fetcher: LottoFetcher,
        session_mock: MagicMock,
        invalid_draw_no: int,
    ):
        with pytest.raises(ValueError, match="1 이상"):
            fetcher.fetch_draw(invalid_draw_no)

        session_mock.get.assert_not_called()

    def test_범위_수집에서_누락_회차를_건너뛴다(
        self,
        fetcher: LottoFetcher,
        sample_response: dict,
    ):
        with patch.object(fetcher, "fetch_draw") as fetch_draw_mock:
            fetch_draw_mock.side_effect = [
                _make_draw_result(sample_response, draw_no=1098),
                DrawNotFoundError(1099),
                _make_draw_result(sample_response, draw_no=1100),
            ]

            results = fetcher.fetch_range(1098, 1100)

        assert [result.draw_no for result in results] == [1098, 1100]

    def test_fetch_recent는_최근_500회차_범위를_계산한다(
        self,
        fetcher: LottoFetcher,
        sample_response: dict,
    ):
        latest = _make_draw_result(sample_response, draw_no=1200)
        expected_results = [
            _make_draw_result(sample_response, draw_no=701),
            _make_draw_result(sample_response, draw_no=1200),
        ]

        with patch.object(fetcher, "fetch_latest", return_value=latest) as latest_mock:
            with patch.object(fetcher, "fetch_range", return_value=expected_results) as range_mock:
                results = fetcher.fetch_recent()

        latest_mock.assert_called_once_with()
        range_mock.assert_called_once_with(701, 1200, on_progress=None)
        assert results == expected_results

    def test_fetch_recent는_500회차보다_적으면_1회차부터_수집한다(
        self,
        fetcher: LottoFetcher,
        sample_response: dict,
    ):
        latest = _make_draw_result(sample_response, draw_no=320)

        with patch.object(fetcher, "fetch_latest", return_value=latest):
            with patch.object(fetcher, "fetch_range", return_value=[]) as range_mock:
                fetcher.fetch_recent()

        range_mock.assert_called_once_with(1, 320, on_progress=None)

    def test_범위_수집_진행_콜백은_전체_개수_기준으로_호출된다(
        self,
        fetcher: LottoFetcher,
        sample_response: dict,
    ):
        progress_calls: list[tuple[int, int]] = []

        with patch.object(fetcher, "fetch_draw") as fetch_draw_mock:
            fetch_draw_mock.side_effect = [
                _make_draw_result(sample_response, draw_no=1),
                _make_draw_result(sample_response, draw_no=2),
                _make_draw_result(sample_response, draw_no=3),
            ]

            with patch("src.lotto.fetcher.time.sleep"):
                fetcher.fetch_range(1, 3, on_progress=lambda current, total: progress_calls.append((current, total)))

        assert progress_calls == [(1, 3), (2, 3), (3, 3)]

    def test_시작_회차가_종료_회차보다_크면_실패한다(self, fetcher: LottoFetcher):
        with pytest.raises(ValueError, match="시작 회차"):
            fetcher.fetch_range(10, 9)

    def test_컨텍스트_매니저_종료_시_세션을_닫는다(self, session_mock: MagicMock):
        with LottoFetcher(session=session_mock, delay=0) as managed_fetcher:
            assert isinstance(managed_fetcher, LottoFetcher)

        session_mock.close.assert_called_once_with()


def _make_draw_result(base_response: dict, *, draw_no: int):
    response = dict(base_response)
    response["drwNo"] = draw_no
    return _parse_draw_response(response)
