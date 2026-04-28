"""최신 회차 탐색(`detect_latest_draw_no`) 관련 단위 테스트."""

from __future__ import annotations

import unittest

from lotto_predictor.backend import TransientFetchError
from lotto_predictor.collector import CollectorConfig, LottoCollector

from ._fakes import FakeClient, FakeStorage


class DetectLatestDrawNoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = CollectorConfig(min_interval_s=0, max_probe=10)
        self.storage = FakeStorage()

    def test_probe_start_가_성공이고_이후_미발표이면_해당_회차_반환(self) -> None:
        client = FakeClient(success_range={1100}, not_found={1101})
        collector = LottoCollector(client=client, storage=self.storage, config=self.config)

        self.assertEqual(collector.detect_latest_draw_no(1100), 1100)

    def test_여러_회차를_전진하며_마지막_발표_회차를_찾는다(self) -> None:
        client = FakeClient(success_range={1100, 1101, 1102}, not_found={1103})
        collector = LottoCollector(client=client, storage=self.storage, config=self.config)

        self.assertEqual(collector.detect_latest_draw_no(1100), 1102)

    def test_probe_start_가_이미_미발표이면_직전_회차_반환(self) -> None:
        client = FakeClient(not_found={1100})
        collector = LottoCollector(client=client, storage=self.storage, config=self.config)

        self.assertEqual(collector.detect_latest_draw_no(1100), 1099)

    def test_probe_start_가_1이고_미발표이면_0_반환(self) -> None:
        # 회차 1 조차 미발표인 가상 상황(초기 상태)을 안전하게 처리한다.
        client = FakeClient(not_found={1})
        collector = LottoCollector(client=client, storage=self.storage, config=self.config)

        self.assertEqual(collector.detect_latest_draw_no(1), 0)

    def test_probe_start_가_0_이하이면_ValueError(self) -> None:
        collector = LottoCollector(
            client=FakeClient(), storage=self.storage, config=self.config
        )
        with self.assertRaises(ValueError):
            collector.detect_latest_draw_no(0)

    def test_일시_실패는_전파되어_탐색이_중단된다(self) -> None:
        client = FakeClient(success_range={1100}, transient={1101})
        collector = LottoCollector(client=client, storage=self.storage, config=self.config)

        with self.assertRaises(TransientFetchError):
            collector.detect_latest_draw_no(1100)

    def test_max_probe_한계_내_모두_성공이면_마지막_성공_회차_반환(self) -> None:
        # max_probe=3 이므로 1100, 1101, 1102 까지만 확인하고 1102 반환.
        config = CollectorConfig(min_interval_s=0, max_probe=3)
        client = FakeClient(success_range={1100, 1101, 1102, 1103, 1104})
        collector = LottoCollector(client=client, storage=self.storage, config=config)

        self.assertEqual(collector.detect_latest_draw_no(1100), 1102)


if __name__ == "__main__":
    unittest.main()
