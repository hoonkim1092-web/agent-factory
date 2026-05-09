from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest
import requests

from lotto_predictor.backend import (
    DhLotteryClient,
    FetchResult,
    LottoStorage,
    TransientFetchError,
)
from lotto_predictor.collector import CollectorConfig, LottoCollector
from tests.fixtures.mock_responses import (
    HTML_ERROR_PAGE,
    SCHEMA_CHANGED_DRAW_1120,
    SUCCESS_DRAW_1120,
    clone_payload,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: object | None = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class SequencedSession:
    """요청마다 미리 준비한 응답 또는 예외를 순서대로 돌려주는 세션."""

    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.headers: dict[str, str] = {}
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, *, params: dict[str, object], timeout: float) -> object:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        return None


class FakeFetcher:
    """회차별 payload 또는 예외를 돌려주는 수집기용 fake."""

    def __init__(self, mapping: dict[int, object]) -> None:
        self._mapping = mapping
        self.calls: list[int] = []

    def fetch_draw(self, draw_no: int) -> FetchResult:
        self.calls.append(draw_no)
        outcome = self._mapping[draw_no]
        if isinstance(outcome, Exception):
            raise outcome
        return FetchResult(draw_no=draw_no, payload=outcome, fetched_at=datetime.now())


@pytest.fixture
def temp_storage() -> LottoStorage:
    temp_dir = tempfile.TemporaryDirectory()
    storage = LottoStorage(Path(temp_dir.name) / "collector.sqlite3")
    storage.connect()
    storage.ensure_schema()
    try:
        yield storage
    finally:
        storage.close()
        temp_dir.cleanup()


def test_정상_회차_응답을_파싱해_저장한다(temp_storage: LottoStorage) -> None:
    fetcher = FakeFetcher({1120: clone_payload(SUCCESS_DRAW_1120)})
    collector = LottoCollector(
        client=fetcher,
        storage=temp_storage,
        config=CollectorConfig(min_interval_s=0),
    )

    result = collector.sync_range(1120, 1120)
    saved = temp_storage.get_draw(1120)

    assert result.stopped_reason == "caught_up"
    assert result.failures == []
    assert result.last_fetched_drw_no == 1120
    assert saved is not None
    assert saved.drw_no == 1120
    assert saved.drw_date == date(2024, 6, 1)
    assert saved.numbers == (2, 19, 26, 31, 38, 41)
    assert saved.bonus_no == 34


def test_네트워크_오류와_타임아웃은_재시도_후_성공한다(monkeypatch: pytest.MonkeyPatch) -> None:
    session = SequencedSession(
        [
            requests.ConnectionError("연결이 끊겼다"),
            requests.Timeout("응답 시간이 초과됐다"),
            FakeResponse(status_code=200, payload=clone_payload(SUCCESS_DRAW_1120)),
        ]
    )
    client = DhLotteryClient(
        timeout=0.1,
        max_retries=2,
        min_interval=0,
        backoff_base=0.01,
        session=session,
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr("lotto_predictor.backend.http_client.time.sleep", sleep_calls.append)

    result = client.fetch_draw(1120)

    assert result.draw_no == 1120
    assert result.payload["returnValue"] == "success"
    assert len(session.calls) == 3
    assert sleep_calls == [0.01, 0.02]


@pytest.mark.parametrize(
    ("name", "payload", "expected_message"),
    [
        (
            "html_error_page",
            ValueError(f"JSON 디코딩 실패: {HTML_ERROR_PAGE[:18]}"),
            "동행복권 응답이 JSON 이 아니다",
        ),
        (
            "schema_changed_json",
            clone_payload(SCHEMA_CHANGED_DRAW_1120),
            "필수 키 누락",
        ),
    ],
)
def test_비정상_응답은_명시적으로_실패한다(
    name: str,
    payload: object,
    expected_message: str,
    monkeypatch: pytest.MonkeyPatch,
    temp_storage: LottoStorage,
) -> None:
    if name == "html_error_page":
        session = SequencedSession([FakeResponse(status_code=200, payload=payload)])
        client = DhLotteryClient(
            timeout=0.1,
            max_retries=0,
            min_interval=0,
            backoff_base=0.01,
            session=session,
        )
        monkeypatch.setattr("lotto_predictor.backend.http_client.time.sleep", lambda _: None)

        with pytest.raises(ValueError, match=expected_message):
            client.fetch_draw(1120)
        return

    fetcher = FakeFetcher({1120: payload})
    collector = LottoCollector(
        client=fetcher,
        storage=temp_storage,
        config=CollectorConfig(min_interval_s=0),
    )

    result = collector.sync_range(1120, 1120)

    assert result.fetched == []
    assert len(result.failures) == 1
    assert result.failures[0].reason == "unknown"
    assert expected_message in result.failures[0].detail


@pytest.mark.xfail(
    reason="현재 수집기는 HTTP 429 를 rate_limited 로 분류하지 않아 목표 계약을 아직 충족하지 못한다."
)
def test_500회차_일괄_수집시_rate_limit_대응_골격(temp_storage: LottoStorage) -> None:
    mapping: dict[int, object] = {
        draw_no: clone_payload(SUCCESS_DRAW_1120) | {"drwNo": draw_no}
        for draw_no in range(1, 501)
    }
    mapping[120] = TransientFetchError("HTTP 429 응답: drw_no=120")
    mapping[121] = TransientFetchError("HTTP 429 응답: drw_no=121")
    mapping[122] = TransientFetchError("HTTP 429 응답: drw_no=122")

    collector = LottoCollector(
        client=FakeFetcher(mapping),
        storage=temp_storage,
        config=CollectorConfig(min_interval_s=0, abort_on_consecutive_failures=5),
    )

    result = collector.sync_range(1, 500)

    assert result.stopped_reason == "caught_up"
    assert any(failure.reason == "rate_limited" for failure in result.failures)
    assert result.last_fetched_drw_no == 500
    assert len(result.fetched) >= 497
