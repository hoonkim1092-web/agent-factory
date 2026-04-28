"""`LottoDrawCache.ensure_ready()` 의 분기 규칙 단위 테스트."""

from __future__ import annotations

from datetime import datetime, timedelta

from lotto_predictor.backend import FetchCheckpoint
from lotto_predictor.cache import CacheConfig, LottoDrawCache
from lotto_predictor.collector import SyncResult

from ._fakes import FakeCollector, FakeStorage, fixed_clock, make_draw


def _fresh_storage(now: datetime, count: int = 10) -> FakeStorage:
    return FakeStorage(
        draws=[make_draw(i) for i in range(1, count + 1)],
        checkpoint=FetchCheckpoint(
            last_fetched_drw_no=count,
            fetched_at=now - timedelta(hours=1),
            source_url="https://example.test/lotto",
        ),
    )


def test_ensure_ready_skipped_when_fresh() -> None:
    # 이미 신선하면 수집기를 호출하지 않고 skipped 로 반환해야 한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = _fresh_storage(now)
    collector = FakeCollector()
    cache = LottoDrawCache(
        storage=storage,
        collector=collector,
        config=CacheConfig(required_draws=10, freshness_hours=24.0),
        clock=fixed_clock(now),
    )

    result = cache.ensure_ready()

    assert result.action == "skipped"
    assert result.sync_result is None
    assert result.status.is_stale is False
    assert collector.calls == 0


def test_ensure_ready_offline_mode_skips_collector() -> None:
    # offline=True 는 stale 여부와 무관하게 수집 호출을 생략해야 한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage()
    collector = FakeCollector()
    cache = LottoDrawCache(
        storage=storage,
        collector=collector,
        config=CacheConfig(required_draws=10, offline=True),
        clock=fixed_clock(now),
    )

    result = cache.ensure_ready()

    assert result.action == "offline"
    assert result.sync_result is None
    assert result.status.is_stale is True
    assert collector.calls == 0


def test_ensure_ready_no_collector_yields_offline_action() -> None:
    # 수집기 미주입도 offline 경로와 동일하게 처리된다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage()
    cache = LottoDrawCache(
        storage=storage,
        collector=None,
        config=CacheConfig(required_draws=10),
        clock=fixed_clock(now),
    )

    result = cache.ensure_ready()

    assert result.action == "offline"
    assert result.sync_result is None


def test_ensure_ready_refresh_policy_never_skips_even_when_stale() -> None:
    # refresh_policy='never' 는 stale 이어도 수집을 건너뛰어야 한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage()
    collector = FakeCollector()
    cache = LottoDrawCache(
        storage=storage,
        collector=collector,
        config=CacheConfig(required_draws=10, refresh_policy="never"),
        clock=fixed_clock(now),
    )

    result = cache.ensure_ready()

    assert result.action == "skipped"
    assert result.status.is_stale is True
    assert collector.calls == 0


def test_ensure_ready_synced_refreshes_status_after_collection() -> None:
    # stale 상태에서 auto 정책이면 수집기를 호출하고, 수집 후 상태를 재조회해 반환한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage()

    def seed_after_sync() -> None:
        # 수집기 호출 직후 저장소가 갱신된 상황을 시뮬레이션한다.
        storage.seed_draws([make_draw(i) for i in range(1, 11)])
        storage.set_checkpoint(
            FetchCheckpoint(
                last_fetched_drw_no=10,
                fetched_at=now - timedelta(minutes=1),
                source_url="https://example.test/lotto",
            )
        )

    collector = FakeCollector(
        result=SyncResult(
            fetched=[make_draw(i) for i in range(1, 11)],
            last_fetched_drw_no=10,
            stopped_reason="caught_up",
        ),
        on_sync=seed_after_sync,
    )
    cache = LottoDrawCache(
        storage=storage,
        collector=collector,
        config=CacheConfig(required_draws=10, freshness_hours=24.0),
        clock=fixed_clock(now),
    )

    result = cache.ensure_ready()

    assert result.action == "synced"
    assert collector.calls == 1
    assert result.sync_result is not None
    assert result.sync_result.stopped_reason == "caught_up"
    # 재조회된 상태는 더 이상 stale 이 아니어야 한다.
    assert result.status.is_stale is False
    assert result.status.total_draws == 10


def test_ensure_ready_preserves_sync_result_even_on_aborted() -> None:
    # 수집이 중단되어도 예외를 던지지 않고 sync_result 에 결과를 보존해야 한다.
    now = datetime(2026, 4, 17, 12, 0, 0)
    storage = FakeStorage()
    aborted = SyncResult(
        fetched=[],
        failures=[],
        last_fetched_drw_no=None,
        stopped_reason="aborted",
    )
    collector = FakeCollector(result=aborted)
    cache = LottoDrawCache(
        storage=storage,
        collector=collector,
        config=CacheConfig(required_draws=10),
        clock=fixed_clock(now),
    )

    result = cache.ensure_ready()

    assert result.action == "synced"
    assert result.sync_result is aborted
    assert result.status.is_stale is True
