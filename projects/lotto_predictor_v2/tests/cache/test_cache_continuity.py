"""`LottoDrawCache.validate_continuity()` 단위 테스트."""

from __future__ import annotations

from datetime import datetime

from lotto_predictor.cache import CacheConfig, LottoDrawCache

from ._fakes import FakeStorage, fixed_clock, make_draw


def _cache_with(*draws_no: int) -> LottoDrawCache:
    storage = FakeStorage(draws=[make_draw(i) for i in draws_no])
    return LottoDrawCache(
        storage=storage,
        config=CacheConfig(required_draws=1),
        clock=fixed_clock(datetime(2026, 4, 17, 12, 0, 0)),
    )


def test_validate_continuity_empty_storage_returns_no_range() -> None:
    # 빈 저장소는 누락 판정을 하지 않고 빈 리포트로 반환한다.
    cache = _cache_with()

    report = cache.validate_continuity()

    assert report.expected_range is None
    assert report.missing_draws == ()
    assert report.is_continuous is True


def test_validate_continuity_continuous_range_has_no_gaps() -> None:
    # 연속 구간이면 missing_draws 가 비어 있고 is_continuous=True.
    cache = _cache_with(1, 2, 3, 4, 5)

    report = cache.validate_continuity()

    assert report.expected_range == (1, 5)
    assert report.missing_draws == ()
    assert report.is_continuous is True


def test_validate_continuity_reports_missing_in_middle() -> None:
    # 중간 회차 누락을 오름차순으로 정확히 잡아내야 한다.
    cache = _cache_with(1, 2, 5, 6, 9, 10)

    report = cache.validate_continuity()

    assert report.expected_range == (1, 10)
    assert report.missing_draws == (3, 4, 7, 8)
    assert report.is_continuous is False


def test_validate_continuity_single_draw_is_continuous() -> None:
    # 단일 회차는 스스로 연속 범위다.
    cache = _cache_with(42)

    report = cache.validate_continuity()

    assert report.expected_range == (42, 42)
    assert report.missing_draws == ()
    assert report.is_continuous is True


def test_validate_continuity_ignores_starting_offset() -> None:
    # 기대 범위는 저장된 회차의 실제 최소·최대 기준이므로 1번 회차 누락은
    # "누락" 이 아니다(백필 정책은 호출자가 결정).
    cache = _cache_with(100, 101, 103)

    report = cache.validate_continuity()

    assert report.expected_range == (100, 103)
    assert report.missing_draws == (102,)
    assert report.is_continuous is False
