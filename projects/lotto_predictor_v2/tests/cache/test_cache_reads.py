"""`LottoDrawCache` 도메인 읽기 API 단위 테스트."""

from __future__ import annotations

from datetime import datetime

import pytest

from lotto_predictor.cache import CacheConfig, LottoDrawCache

from ._fakes import FakeStorage, fixed_clock, make_draw


def _cache_with(*draws_no: int) -> tuple[LottoDrawCache, FakeStorage]:
    storage = FakeStorage(draws=[make_draw(i) for i in draws_no])
    cache = LottoDrawCache(
        storage=storage,
        config=CacheConfig(required_draws=1),
        clock=fixed_clock(datetime(2026, 4, 17, 12, 0, 0)),
    )
    return cache, storage


def test_get_recent_draws_returns_descending_with_limit() -> None:
    # 저장소 계약(내림차순)을 그대로 노출해야 한다.
    cache, _ = _cache_with(1, 2, 3, 4, 5)

    rows = cache.get_recent_draws(3)

    assert [d.drw_no for d in rows] == [5, 4, 3]


def test_get_recent_draws_zero_or_negative_raises_value_error() -> None:
    # n<=0 은 조기 차단한다.
    cache, _ = _cache_with(1, 2, 3)

    with pytest.raises(ValueError):
        cache.get_recent_draws(0)
    with pytest.raises(ValueError):
        cache.get_recent_draws(-1)


def test_get_recent_draws_more_than_available_returns_all() -> None:
    # 저장된 개수보다 큰 n 은 전체를 반환하고 예외를 던지지 않아야 한다.
    cache, _ = _cache_with(1, 2, 3)

    rows = cache.get_recent_draws(10)

    assert [d.drw_no for d in rows] == [3, 2, 1]


def test_get_all_draws_returns_ascending() -> None:
    # 통계 집계 입력 계약에 맞춰 오름차순으로 반환한다.
    cache, _ = _cache_with(5, 3, 1, 4, 2)

    rows = cache.get_all_draws()

    assert [d.drw_no for d in rows] == [1, 2, 3, 4, 5]


def test_get_all_draws_empty_storage_returns_empty_list() -> None:
    cache, _ = _cache_with()

    assert cache.get_all_draws() == []


def test_get_draw_returns_matching_row_or_none() -> None:
    cache, _ = _cache_with(1, 2, 3)

    assert cache.get_draw(2).drw_no == 2
    assert cache.get_draw(999) is None


def test_get_draw_rejects_non_positive_input() -> None:
    cache, _ = _cache_with(1, 2)

    with pytest.raises(ValueError):
        cache.get_draw(0)
    with pytest.raises(ValueError):
        cache.get_draw(-5)
