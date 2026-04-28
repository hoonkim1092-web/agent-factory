"""`LottoDrawCache.status()` 의 상태 판정 규칙 단위 테스트."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from lotto_predictor.backend import FetchCheckpoint
from lotto_predictor.cache import CacheConfig, LottoDrawCache

from ._fakes import FakeStorage, fixed_clock, make_draw


def test_status_beoinn_empty_storage_reports_missing_checkpoint_and_insufficient() -> None:
    # 빈 저장소: 체크포인트 없음 + 회차 부족이 동시에 사유로 잡혀야 한다.
    storage = FakeStorage()
    cache = LottoDrawCache(
        storage=storage,
        config=CacheConfig(required_draws=10),
        clock=fixed_clock(datetime(2026, 4, 17, 12, 0, 0)),
    )

    status = cache.status()

    assert status.total_draws == 0
    assert status.latest_drw_no is None
    assert status.earliest_drw_no is None
    assert status.last_fetched_at is None
    assert status.is_stale is True
    assert "missing_checkpoint" in status.stale_reasons
    assert "insufficient_draws" in status.stale_reasons


def test_status_insufficient_draws_flag_when_below_required() -> None:
    # 체크포인트는 최신이지만 회차 개수가 required_draws 미만이면 stale 이어야 한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage(
        draws=[make_draw(i) for i in range(1, 6)],
        checkpoint=FetchCheckpoint(
            last_fetched_drw_no=5,
            fetched_at=now - timedelta(minutes=10),
            source_url="https://example.test/lotto",
        ),
    )
    cache = LottoDrawCache(
        storage=storage,
        config=CacheConfig(required_draws=10, freshness_hours=24.0),
        clock=fixed_clock(now),
    )

    status = cache.status()

    assert status.total_draws == 5
    assert status.latest_drw_no == 5
    assert status.earliest_drw_no == 1
    assert status.is_stale is True
    assert status.stale_reasons == ("insufficient_draws",)


def test_status_expired_checkpoint_flag_when_older_than_freshness() -> None:
    # 체크포인트가 freshness_hours 이상 경과했으면 expired_checkpoint 가 추가되어야 한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage(
        draws=[make_draw(i) for i in range(1, 11)],
        checkpoint=FetchCheckpoint(
            last_fetched_drw_no=10,
            fetched_at=now - timedelta(hours=48),
            source_url="https://example.test/lotto",
        ),
    )
    cache = LottoDrawCache(
        storage=storage,
        config=CacheConfig(required_draws=10, freshness_hours=24.0),
        clock=fixed_clock(now),
    )

    status = cache.status()

    assert status.total_draws == 10
    assert status.is_stale is True
    assert status.stale_reasons == ("expired_checkpoint",)


def test_status_fresh_and_sufficient_returns_not_stale() -> None:
    # 필요한 회차가 있고 체크포인트도 신선하면 stale 이 아니어야 한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage(
        draws=[make_draw(i) for i in range(1, 11)],
        checkpoint=FetchCheckpoint(
            last_fetched_drw_no=10,
            fetched_at=now - timedelta(hours=1),
            source_url="https://example.test/lotto",
        ),
    )
    cache = LottoDrawCache(
        storage=storage,
        config=CacheConfig(required_draws=10, freshness_hours=24.0),
        clock=fixed_clock(now),
    )

    status = cache.status()

    assert status.is_stale is False
    assert status.stale_reasons == ()
    assert status.latest_drw_no == 10
    assert status.earliest_drw_no == 1
    assert status.total_draws == 10
    assert status.last_fetched_at is not None


def test_status_freshness_zero_disables_expiration_check() -> None:
    # freshness_hours=0 은 "만료 판정을 하지 않음" 으로 해석되어야 한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage(
        draws=[make_draw(i) for i in range(1, 11)],
        checkpoint=FetchCheckpoint(
            last_fetched_drw_no=10,
            fetched_at=now - timedelta(days=365),
            source_url="https://example.test/lotto",
        ),
    )
    cache = LottoDrawCache(
        storage=storage,
        config=CacheConfig(required_draws=10, freshness_hours=0.0),
        clock=fixed_clock(now),
    )

    status = cache.status()

    assert status.is_stale is False
    assert status.stale_reasons == ()


@pytest.mark.parametrize(
    ("required", "draw_count", "hours_elapsed", "expected_reasons"),
    [
        (5, 0, 1.0, {"missing_checkpoint", "insufficient_draws"}),
        (5, 3, 1.0, {"insufficient_draws"}),
        (5, 10, 25.0, {"expired_checkpoint"}),
        (5, 3, 25.0, {"insufficient_draws", "expired_checkpoint"}),
    ],
)
def test_status_parametrized_combinations(
    required: int,
    draw_count: int,
    hours_elapsed: float,
    expected_reasons: set[str],
) -> None:
    # 회차 개수와 경과 시간 조합별 사유 집합을 일괄 검증한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    has_checkpoint = "missing_checkpoint" not in expected_reasons
    storage = FakeStorage(
        draws=[make_draw(i) for i in range(1, draw_count + 1)],
        checkpoint=(
            FetchCheckpoint(
                last_fetched_drw_no=draw_count or 1,
                fetched_at=now - timedelta(hours=hours_elapsed),
                source_url="https://example.test/lotto",
            )
            if has_checkpoint
            else None
        ),
    )
    cache = LottoDrawCache(
        storage=storage,
        config=CacheConfig(required_draws=required, freshness_hours=24.0),
        clock=fixed_clock(now),
    )

    status = cache.status()

    assert set(status.stale_reasons) == expected_reasons
    assert status.is_stale is bool(expected_reasons)
