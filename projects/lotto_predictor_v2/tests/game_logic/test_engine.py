import unittest

from lotto_predictor.game_logic import (
    InsufficientCandidateError,
    InvalidRequestError,
    LottoDraw,
    RecommendationConfig,
    RecommendationEngine,
    RecommendationRequest,
    RuleConflictError,
    StatisticsSummary,
)


class RecommendationEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RecommendationEngine()
        self.draw_history = [
            LottoDraw(draw_no=101, numbers=(1, 2, 3, 4, 5, 6)),
            LottoDraw(draw_no=102, numbers=(7, 8, 9, 10, 11, 12)),
            LottoDraw(draw_no=103, numbers=(13, 14, 15, 16, 17, 18)),
        ]
        self.statistics = StatisticsSummary(
            number_frequency={number: 50 - number for number in range(1, 46)},
            recent_frequency={number: 10 - (number % 10) for number in range(1, 46)},
            number_last_seen={number: number for number in range(1, 46)},
            sum_range=(90, 190),
        )

    def test_빈_회차_이력은_거부한다(self) -> None:
        request = RecommendationRequest(
            draw_history=[],
            statistics_summary=self.statistics,
            config=RecommendationConfig(),
        )

        with self.assertRaises(InvalidRequestError):
            self.engine.generate(request)

    def test_추천_배치를_생성한다(self) -> None:
        request = RecommendationRequest(
            draw_history=self.draw_history,
            statistics_summary=self.statistics,
            config=RecommendationConfig(
                target_count=3,
                candidate_pool_size=14,
                fixed_numbers=(19,),
                excluded_numbers=(1, 2, 3, 4, 5, 6),
                min_sum=90,
                max_sum=190,
                max_consecutive_pairs=2,
            ),
        )

        batch = self.engine.generate(request)

        self.assertEqual(len(batch.recommendations), 3)
        self.assertEqual(batch.evaluation_summary.requested_count, 3)
        self.assertGreater(batch.evaluation_summary.generated_candidates, 0)
        self.assertGreater(batch.evaluation_summary.validated_candidates, 0)
        self.assertIn(19, batch.recommendations[0].numbers)
        self.assertTrue(all(result.stage.value == "최종 선택" for result in batch.recommendations))

    def test_충돌하는_규칙은_에러를_발생시킨다(self) -> None:
        request = RecommendationRequest(
            draw_history=self.draw_history,
            statistics_summary=self.statistics,
            config=RecommendationConfig(fixed_numbers=(3,), excluded_numbers=(3,)),
        )

        with self.assertRaises(RuleConflictError):
            self.engine.generate(request)

    def test_후보가_부족하면_예외를_발생시킨다(self) -> None:
        request = RecommendationRequest(
            draw_history=self.draw_history,
            statistics_summary=self.statistics,
            config=RecommendationConfig(
                target_count=5,
                candidate_pool_size=6,
                fixed_numbers=(19, 20, 21, 22, 23, 24),
                min_odd_count=0,
                max_odd_count=0,
            ),
        )

        with self.assertRaises(InsufficientCandidateError):
            self.engine.generate(request)


if __name__ == "__main__":
    unittest.main()
