"""증분 수집(`sync_incremental`, `sync_range`) 핵심 플로우 테스트."""

from __future__ import annotations

import unittest
from datetime import datetime

from lotto_predictor.backend import FetchCheckpoint
from lotto_predictor.collector import CollectorConfig, LottoCollector

from ._fakes import FakeClient, FakeStorage


class SyncIncrementalTest(unittest.TestCase):
    def setUp(self) -> None:
        # 모든 테스트에서 sleep 이 실제로 발생하지 않도록 간격을 0 으로 둔다.
        self.config = CollectorConfig(min_interval_s=0, max_probe=5)

    def test_체크포인트_없을_때_1회차부터_타겟까지_수집한다(self) -> None:
        client = FakeClient(success_range=range(1, 6), not_found={6})
        storage = FakeStorage()
        collector = LottoCollector(client=client, storage=storage, config=self.config)

        result = collector.sync_incremental()

        self.assertEqual([d.drw_no for d in result.fetched], [1, 2, 3, 4, 5])
        self.assertEqual(result.last_fetched_drw_no, 5)
        self.assertEqual(result.stopped_reason, "caught_up")
        self.assertEqual([d.drw_no for d in storage.upserts], [1, 2, 3, 4, 5])
        self.assertEqual(len(storage.checkpoints), 1)
        self.assertEqual(storage.checkpoints[-1].last_fetched_drw_no, 5)

    def test_체크포인트가_있으면_다음_회차부터_수집한다(self) -> None:
        cp = FetchCheckpoint(
            last_fetched_drw_no=3,
            fetched_at=datetime.now(),
            source_url="https://example.test/checkpoint",
        )
        client = FakeClient(success_range=range(1, 7), not_found={7})
        storage = FakeStorage(checkpoint=cp)
        collector = LottoCollector(client=client, storage=storage, config=self.config)

        result = collector.sync_incremental()

        self.assertEqual([d.drw_no for d in result.fetched], [4, 5, 6])
        self.assertEqual(client.calls[0], 4, "체크포인트 직후 회차부터 호출되어야 한다")
        self.assertEqual(result.stopped_reason, "caught_up")

    def test_최신_상태이면_빈_결과를_반환하고_체크포인트는_유지된다(self) -> None:
        cp = FetchCheckpoint(
            last_fetched_drw_no=10,
            fetched_at=datetime.now(),
            source_url="https://example.test/checkpoint",
        )
        # probe_start=11 이 미발표이므로 detect_latest 는 10 을 반환한다.
        client = FakeClient(success_range={10}, not_found={11})
        storage = FakeStorage(checkpoint=cp)
        collector = LottoCollector(client=client, storage=storage, config=self.config)

        result = collector.sync_incremental()

        self.assertEqual(result.fetched, [])
        self.assertEqual(result.last_fetched_drw_no, 10)
        self.assertEqual(result.stopped_reason, "caught_up")
        self.assertEqual(len(storage.checkpoints), 0, "업데이트할 이유가 없어야 한다")

    def test_target_draw_no_지정_시_해당_회차까지만_수집한다(self) -> None:
        cp = FetchCheckpoint(
            last_fetched_drw_no=1,
            fetched_at=datetime.now(),
            source_url="https://example.test/checkpoint",
        )
        client = FakeClient(success_range=range(1, 10))
        storage = FakeStorage(checkpoint=cp)
        config = CollectorConfig(min_interval_s=0, target_draw_no=4)
        collector = LottoCollector(client=client, storage=storage, config=config)

        result = collector.sync_incremental()

        self.assertEqual([d.drw_no for d in result.fetched], [2, 3, 4])
        self.assertEqual(result.last_fetched_drw_no, 4)
        self.assertEqual(result.stopped_reason, "target_reached")

    def test_타겟_전에_미발표_회차를_만나면_not_yet_drawn_으로_종료한다(self) -> None:
        client = FakeClient(success_range=range(1, 4), not_found={4})
        storage = FakeStorage()
        config = CollectorConfig(min_interval_s=0, target_draw_no=10)
        collector = LottoCollector(client=client, storage=storage, config=config)

        result = collector.sync_incremental()

        self.assertEqual([d.drw_no for d in result.fetched], [1, 2, 3])
        self.assertEqual(result.stopped_reason, "not_yet_drawn")
        self.assertEqual(result.last_fetched_drw_no, 3)


class SyncRangeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = CollectorConfig(min_interval_s=0)

    def test_명시_범위를_순차_수집한다(self) -> None:
        client = FakeClient(success_range=range(100, 106))
        storage = FakeStorage()
        collector = LottoCollector(client=client, storage=storage, config=self.config)

        result = collector.sync_range(100, 105)

        self.assertEqual([d.drw_no for d in result.fetched], [100, 101, 102, 103, 104, 105])
        self.assertEqual(result.failures, [])
        self.assertEqual(result.last_fetched_drw_no, 105)
        self.assertEqual(result.stopped_reason, "caught_up")
        self.assertEqual(client.calls, [100, 101, 102, 103, 104, 105])

    def test_start_가_end_보다_크면_ValueError(self) -> None:
        collector = LottoCollector(
            client=FakeClient(), storage=FakeStorage(), config=self.config
        )
        with self.assertRaises(ValueError):
            collector.sync_range(10, 5)

    def test_범위에_미발표_회차가_섞이면_실패로_기록되고_계속_진행한다(self) -> None:
        client = FakeClient(success_range={1, 3}, not_found={2})
        storage = FakeStorage()
        collector = LottoCollector(client=client, storage=storage, config=self.config)

        result = collector.sync_range(1, 3)

        self.assertEqual([d.drw_no for d in result.fetched], [1, 3])
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0].draw_no, 2)
        self.assertEqual(result.failures[0].reason, "not_yet_drawn")
        self.assertEqual(result.last_fetched_drw_no, 3)


if __name__ == "__main__":
    unittest.main()
