"""CacheStore 단위 테스트 — 인메모리 SQLite 기반."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pytest

from src.lotto.cache_store import CacheStore
from src.lotto.exceptions import CacheError
from src.lotto.fetcher import LottoFetcher
from src.lotto.models import DrawResult


def _make_draw(draw_no: int = 1100, **overrides) -> DrawResult:
    """테스트용 DrawResult 팩토리."""
    defaults = dict(
        draw_no=draw_no,
        draw_date=date(2026, 1, 4),
        numbers=(3, 11, 15, 27, 33, 42),
        bonus=7,
        total_sell_amount=100_000_000_000,
        first_prize_amount=2_000_000_000,
        first_prize_winners=12,
    )
    defaults.update(overrides)
    return DrawResult(**defaults)


# ── 초기화 ────────────────────────────────────────────


class TestInit:
    def test_인메모리_생성(self):
        with CacheStore(":memory:") as store:
            assert store.count() == 0

    def test_파일_기반_생성(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_file = Path(tmp_dir) / "sub" / "test.db"
            with CacheStore(db_file) as store:
                assert store.count() == 0
            assert db_file.exists()


# ── 저장 ──────────────────────────────────────────────


class TestSave:
    def test_단건_저장_후_조회(self):
        with CacheStore(":memory:") as store:
            draw = _make_draw(1100)
            store.save(draw)
            assert store.count() == 1
            result = store.get(1100)
            assert result == draw

    def test_중복_저장_무시(self):
        with CacheStore(":memory:") as store:
            draw = _make_draw(1100)
            store.save(draw)
            store.save(draw)  # 중복 — 무시되어야 함
            assert store.count() == 1

    def test_save_many_일괄_저장(self):
        draws = [_make_draw(n) for n in range(1, 6)]
        with CacheStore(":memory:") as store:
            saved = store.save_many(draws)
            assert saved == 5
            assert store.count() == 5

    def test_save_many_중복_혼합(self):
        draws = [_make_draw(n) for n in range(1, 4)]
        with CacheStore(":memory:") as store:
            store.save(_make_draw(2))  # 미리 저장
            saved = store.save_many(draws)
            assert saved == 2  # 1, 3만 신규
            assert store.count() == 3

    def test_save_many_빈_리스트(self):
        with CacheStore(":memory:") as store:
            saved = store.save_many([])
            assert saved == 0

    def test_save_many_500건_일괄_저장(self):
        draws = [
            _make_draw(
                n,
                draw_date=date(2026, 1, (n - 1) % 28 + 1),
                numbers=tuple(sorted(((n + i - 1) % 45) + 1 for i in range(6))),
                bonus=((n + 6 - 1) % 45) + 1,
            )
            for n in range(1, 501)
        ]
        with CacheStore(":memory:") as store:
            saved = store.save_many(draws)
            assert saved == 500
            assert store.count() == 500
            assert store.get(1) == draws[0]
            assert store.get(500) == draws[-1]


# ── 조회 ──────────────────────────────────────────────


class TestQuery:
    @pytest.fixture()
    def store_with_data(self):
        store = CacheStore(":memory:")
        draws = [_make_draw(n) for n in range(1, 11)]
        store.save_many(draws)
        yield store
        store.close()

    def test_get_존재하는_회차(self, store_with_data):
        result = store_with_data.get(5)
        assert result is not None
        assert result.draw_no == 5

    def test_get_미존재_회차(self, store_with_data):
        assert store_with_data.get(999) is None

    def test_get_range(self, store_with_data):
        results = store_with_data.get_range(3, 7)
        assert len(results) == 5
        assert [r.draw_no for r in results] == [3, 4, 5, 6, 7]

    def test_get_range_빈_결과(self, store_with_data):
        results = store_with_data.get_range(100, 200)
        assert results == []

    def test_get_all(self, store_with_data):
        results = store_with_data.get_all()
        assert len(results) == 10
        # 오름차순 정렬 확인
        assert results[0].draw_no == 1
        assert results[-1].draw_no == 10

    def test_get_cached_draw_numbers(self, store_with_data):
        cached = store_with_data.get_cached_draw_numbers()
        assert cached == set(range(1, 11))

    def test_count(self, store_with_data):
        assert store_with_data.count() == 10


# ── 데이터 왕복 검증 ─────────────────────────────────


class TestRoundTrip:
    def test_모든_필드_보존(self):
        """저장 후 조회한 DrawResult가 원본과 동일한지 확인한다."""
        original = DrawResult(
            draw_no=1150,
            draw_date=date(2026, 3, 15),
            numbers=(1, 10, 20, 30, 40, 45),
            bonus=22,
            total_sell_amount=98_765_432_100,
            first_prize_amount=1_500_000_000,
            first_prize_winners=3,
        )
        with CacheStore(":memory:") as store:
            store.save(original)
            loaded = store.get(1150)
            assert loaded == original

    def test_파일_db_재연결_후_데이터_보존(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_file = Path(tmp_dir) / "cache.db"
            original = _make_draw(321, draw_date=date(2026, 4, 16))

            with CacheStore(db_file) as store:
                store.save(original)
                assert store.count() == 1

            with CacheStore(db_file) as reopened:
                loaded = reopened.get(321)
                assert reopened.count() == 1
                assert loaded == original

    def test_경계값_번호_저장_조회(self):
        original = DrawResult(
            draw_no=1,
            draw_date=date(2026, 1, 1),
            numbers=(1, 2, 3, 43, 44, 45),
            bonus=45,
            total_sell_amount=1,
            first_prize_amount=1,
            first_prize_winners=1,
        )
        with CacheStore(":memory:") as store:
            store.save(original)
            loaded = store.get(1)
            assert loaded == original


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    def __init__(self, payloads: dict[int, dict]) -> None:
        self._payloads = payloads
        self.requested_draws: list[int] = []

    def get(self, _url: str, *, params: dict, timeout: int) -> _FakeResponse:
        del timeout
        draw_no = params["drwNo"]
        self.requested_draws.append(draw_no)
        return _FakeResponse(self._payloads[draw_no])

    def close(self) -> None:
        return None


class TestFetcherIntegration:
    def test_fetcher_결과를_캐시에_저장하고_재조회한다(self):
        payloads = {
            101: {
                "returnValue": "success",
                "drwNo": 101,
                "drwNoDate": "2026-04-01",
                "drwtNo1": 12,
                "drwtNo2": 1,
                "drwtNo3": 45,
                "drwtNo4": 33,
                "drwtNo5": 7,
                "drwtNo6": 22,
                "bnusNo": 9,
                "totSellamnt": 1000,
                "firstWinamnt": 200,
                "firstPrzwnerCo": 3,
            },
            102: {
                "returnValue": "success",
                "drwNo": 102,
                "drwNoDate": "2026-04-08",
                "drwtNo1": 2,
                "drwtNo2": 3,
                "drwtNo3": 4,
                "drwtNo4": 5,
                "drwtNo5": 6,
                "drwtNo6": 7,
                "bnusNo": 8,
                "totSellamnt": 2000,
                "firstWinamnt": 300,
                "firstPrzwnerCo": 4,
            },
        }
        session = _FakeSession(payloads)
        fetcher = LottoFetcher(session=session, delay=0, max_retries=1)

        try:
            fetched = fetcher.fetch_range(101, 102)
            with CacheStore(":memory:") as store:
                saved = store.save_many(fetched)
                loaded = store.get_range(101, 102)

            assert saved == 2
            assert session.requested_draws == [101, 102]
            assert [result.draw_no for result in loaded] == [101, 102]
            assert loaded[0].numbers == (1, 7, 12, 22, 33, 45)
            assert loaded[0].bonus == 9
            assert loaded == fetched
        finally:
            fetcher.close()


# ── 컨텍스트 매니저 ───────────────────────────────────


class TestContextManager:
    def test_with_구문(self):
        with CacheStore(":memory:") as store:
            store.save(_make_draw(1))
            assert store.count() == 1
        # close 이후 연결 사용 불가 — 예외 발생
        with pytest.raises(Exception):
            store.count()
