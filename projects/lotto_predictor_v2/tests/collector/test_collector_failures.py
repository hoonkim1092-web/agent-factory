"""일시 실패와 연속 실패 중단 규칙 테스트."""

from __future__ import annotations

import unittest
from datetime import datetime

from lotto_predictor.backend import FetchCheckpoint
from lotto_predictor.collector import CollectorConfig, LottoCollector

from ._fakes import FakeClient, FakeStorage


class ConsecutiveFailureAbortTest(unittest.TestCase):
    def test_sync_range_에서_연속_일시_실패_임계_초과_시_중단(self) -> None:
        # 100,101,102 가 모두 일시 실패 -> 2 회 임계에서 중단되어야 한다.
        config = CollectorConfig(min_interval_s=0, abort_on_consecutive_failures=2)
        client = FakeClient(transient={100, 101, 102})
        storage = FakeStorage()
        collector = LottoCollector(client=client, storage=storage, config=config)

        result = collector.sync_range(100, 105)

        self.assertEqual(result.stopped_reason, "aborted")
        self.assertEqual(len(result.failures), 2)
        self.assertEqual([f.draw_no for f in result.failures], [100, 101])
        self.assertTrue(all(f.reason == "transient" for f in result.failures))
        self.assertIsNone(result.last_fetched_drw_no)
        self.assertEqual(client.calls, [100, 101])

    def test_성공_사이의_일시_실패는_연속_카운터를_초기화한다(self) -> None:
        config = CollectorConfig(min_interval_s=0, abort_on_consecutive_failures=2)
        client = FakeClient(success_range={100, 102}, transient={101, 103, 104})
        storage = FakeStorage()
        collector = LottoCollector(client=client, storage=storage, config=config)

        result = collector.sync_range(100, 105)

        # 100 성공 → 101 실패(1) → 102 성공(카운터 초기화) → 103 실패(1) → 104 실패(2) -> abort.
        self.assertEqual([d.drw_no for d in result.fetched], [100, 102])
        self.assertEqual([f.draw_no for f in result.failures], [101, 103, 104])
        self.assertEqual(result.stopped_reason, "aborted")
        self.assertEqual(result.last_fetched_drw_no, 102)

    def test_sync_incremental_탐색_단계_일시_실패는_체크포인트를_유지한다(self) -> None:
        cp = FetchCheckpoint(
            last_fetched_drw_no=5,
            fetched_at=datetime.now(),
            source_url="https://example.test/checkpoint",
        )
        config = CollectorConfig(min_interval_s=0, abort_on_consecutive_failures=2)
        # detect_latest_draw_no 가 probe_start=6 에서 일시 실패를 만나면 전파되어
        # sync_incremental 은 aborted 로 빠져나간다. 이 때 체크포인트는 변동 없음.
        client = FakeClient(transient={6})
        storage = FakeStorage(checkpoint=cp)
        collector = LottoCollector(client=client, storage=storage, config=config)

        result = collector.sync_incremental()

        self.assertEqual(result.fetched, [])
        self.assertEqual(result.stopped_reason, "aborted")
        self.assertEqual(result.last_fetched_drw_no, 5, "체크포인트 회차가 유지되어야 한다")
        self.assertEqual(len(storage.checkpoints), 0, "체크포인트가 변경되면 안 된다")
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0].reason, "transient")


class UnknownFailureTest(unittest.TestCase):
    def test_예상치_못한_예외는_unknown_사유로_기록된다(self) -> None:
        def boom(_draw_no: int):
            raise RuntimeError("예상치 못한 오류")

        client = FakeClient(custom=boom)
        storage = FakeStorage()
        config = CollectorConfig(min_interval_s=0, abort_on_consecutive_failures=5)
        collector = LottoCollector(client=client, storage=storage, config=config)

        result = collector.sync_range(1, 2)

        self.assertEqual(result.fetched, [])
        self.assertEqual(len(result.failures), 2)
        self.assertTrue(all(f.reason == "unknown" for f in result.failures))
        self.assertEqual(result.stopped_reason, "caught_up")


if __name__ == "__main__":
    unittest.main()
