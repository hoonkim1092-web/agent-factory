from __future__ import annotations

import unittest

from lotto.analytics.patterns import (
    calculate_number_frequency,
    calculate_odd_even_ratio,
    calculate_section_distribution,
)


class PatternAnalyticsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.draws = [
            (1, 2, 3, 12, 22, 41),
            (4, 5, 6, 13, 23, 42),
            (7, 8, 9, 14, 24, 43),
        ]

    def test_번호_빈도는_전체_구간을_포함해_집계한다(self) -> None:
        frequency = calculate_number_frequency(self.draws)

        self.assertEqual(45, len(frequency))
        self.assertEqual(1, frequency[1])
        self.assertEqual(1, frequency[42])
        self.assertEqual(0, frequency[45])

    def test_구간_분포는_고정_구간별로_누적된다(self) -> None:
        distribution = calculate_section_distribution(self.draws)

        self.assertEqual(
            {
                "1-10": 9,
                "11-20": 3,
                "21-30": 3,
                "31-40": 0,
                "41-45": 3,
            },
            distribution,
        )

    def test_홀짝_비율은_회차별_분포와_대표값을_반환한다(self) -> None:
        summary = calculate_odd_even_ratio(self.draws)

        self.assertEqual({"3:3": 3}, summary["ratio_counts"])
        self.assertEqual("3:3", summary["dominant_ratio"])
        self.assertEqual(3, summary["dominant_count"])
        self.assertEqual(3.0, summary["average_odd_count"])
        self.assertEqual(3.0, summary["average_even_count"])


if __name__ == "__main__":
    unittest.main()
