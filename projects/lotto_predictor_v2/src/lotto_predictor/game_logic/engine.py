from __future__ import annotations

from collections import Counter
from itertools import combinations

from .errors import InsufficientCandidateError, InvalidRequestError, RuleConflictError
from .models import (
    CandidateStage,
    EvaluationSummary,
    LottoDraw,
    RecommendationBatch,
    RecommendationConfig,
    RecommendationRequest,
    RecommendationResult,
    RejectedCandidate,
    RejectionReasonSummary,
    StatisticsSummary,
)


class RecommendationEngine:
    """추천 후보의 상태 전이를 순차적으로 수행한다."""

    def generate(self, request: RecommendationRequest) -> RecommendationBatch:
        self._validate_request(request)

        candidate_pool = self._build_candidate_pool(
            request.statistics_summary,
            request.config,
        )
        generated = self._generate_candidates(candidate_pool, request.config)
        validated, rejected = self._validate_candidates(
            generated,
            request.draw_history,
            request.statistics_summary,
            request.config,
        )
        scored = self._score_candidates(validated, request.statistics_summary, request.config)

        ranked = sorted(scored, key=lambda item: (-item.score, item.numbers))
        recommendations = [
            RecommendationResult(
                numbers=item.numbers,
                score=item.score,
                odd_even_ratio=f"{self._odd_count(item.numbers)}:{6 - self._odd_count(item.numbers)}",
                sum_total=sum(item.numbers),
                matched_fixed_numbers=tuple(number for number in item.numbers if number in request.config.fixed_numbers),
                stage=CandidateStage.SELECTED,
            )
            for item in ranked[: request.config.target_count]
        ]
        if len(recommendations) < request.config.target_count:
            raise InsufficientCandidateError("필터를 통과한 후보가 목표 개수보다 부족합니다.")

        summary = EvaluationSummary(
            requested_count=request.config.target_count,
            generated_candidates=len(generated),
            validated_candidates=len(validated),
            scored_candidates=len(scored),
            selected_candidates=len(recommendations),
            candidate_pool=tuple(candidate_pool),
        )
        rejection_summary = [
            RejectionReasonSummary(reason=reason, count=count)
            for reason, count in sorted(Counter(item.reason for item in rejected).items())
        ]
        return RecommendationBatch(
            recommendations=recommendations,
            rejected_candidates=rejection_summary,
            evaluation_summary=summary,
        )

    def _validate_request(self, request: RecommendationRequest) -> None:
        if not request.draw_history:
            raise InvalidRequestError("회차 이력은 비어 있을 수 없습니다.")
        if request.config.target_count <= 0:
            raise InvalidRequestError("target_count는 1 이상이어야 합니다.")
        if request.config.candidate_pool_size < 6:
            raise InvalidRequestError("candidate_pool_size는 6 이상이어야 합니다.")
        if request.config.min_odd_count > request.config.max_odd_count:
            raise RuleConflictError("홀수 개수 규칙이 서로 충돌합니다.")
        if request.config.min_sum > request.config.max_sum:
            raise RuleConflictError("합계 범위 규칙이 서로 충돌합니다.")
        if len(set(request.config.fixed_numbers)) != len(request.config.fixed_numbers):
            raise InvalidRequestError("fixed_numbers에는 중복이 허용되지 않습니다.")
        if len(set(request.config.excluded_numbers)) != len(request.config.excluded_numbers):
            raise InvalidRequestError("excluded_numbers에는 중복이 허용되지 않습니다.")
        conflict_numbers = set(request.config.fixed_numbers) & set(request.config.excluded_numbers)
        if conflict_numbers:
            raise RuleConflictError("고정 번호와 제외 번호가 충돌합니다.")
        if len(request.config.fixed_numbers) > 6:
            raise RuleConflictError("고정 번호는 최대 6개까지만 허용됩니다.")

        for number in request.config.fixed_numbers + request.config.excluded_numbers:
            self._validate_number(number)
        for draw in request.draw_history:
            self._validate_draw(draw)

    def _validate_number(self, number: int) -> None:
        if not 1 <= number <= 45:
            raise InvalidRequestError("로또 번호는 1부터 45 사이여야 합니다.")

    def _validate_draw(self, draw: LottoDraw) -> None:
        if draw.draw_no <= 0:
            raise InvalidRequestError("draw_no는 1 이상이어야 합니다.")
        if len(draw.numbers) != 6 or len(set(draw.numbers)) != 6:
            raise InvalidRequestError("각 회차 번호는 중복 없는 6개여야 합니다.")
        for number in draw.numbers:
            self._validate_number(number)

    def _build_candidate_pool(
        self,
        statistics_summary: StatisticsSummary,
        config: RecommendationConfig,
    ) -> list[int]:
        ranked_numbers = sorted(
            range(1, 46),
            key=lambda number: (
                -statistics_summary.number_frequency.get(number, 0),
                -statistics_summary.recent_frequency.get(number, 0),
                statistics_summary.number_last_seen.get(number, 10**9),
                number,
            ),
        )
        pool: list[int] = list(dict.fromkeys(config.fixed_numbers))
        for number in ranked_numbers:
            if number in config.excluded_numbers or number in pool:
                continue
            pool.append(number)
            if len(pool) >= config.candidate_pool_size:
                break
        if len(pool) < 6:
            raise RuleConflictError("후보 풀을 구성할 수 없습니다.")
        return sorted(pool)

    def _generate_candidates(self, candidate_pool: list[int], config: RecommendationConfig) -> list[tuple[int, ...]]:
        generated = [
            candidate
            for candidate in combinations(candidate_pool, 6)
            if set(config.fixed_numbers).issubset(candidate)
        ]
        if not generated:
            raise RuleConflictError("고정 번호 조건을 만족하는 후보를 생성할 수 없습니다.")
        return generated

    def _validate_candidates(
        self,
        candidates: list[tuple[int, ...]],
        draw_history: list[LottoDraw],
        statistics_summary: StatisticsSummary,
        config: RecommendationConfig,
    ) -> tuple[list[tuple[int, ...]], list[RejectedCandidate]]:
        existing_draws = {tuple(sorted(draw.numbers)) for draw in draw_history}
        validated: list[tuple[int, ...]] = []
        rejected: list[RejectedCandidate] = []

        for candidate in candidates:
            reason = self._find_rejection_reason(candidate, existing_draws, statistics_summary, config)
            if reason is None:
                validated.append(candidate)
            else:
                rejected.append(
                    RejectedCandidate(
                        numbers=candidate,
                        stage=CandidateStage.REJECTED,
                        reason=reason,
                    )
                )
        return validated, rejected

    def _find_rejection_reason(
        self,
        candidate: tuple[int, ...],
        existing_draws: set[tuple[int, ...]],
        statistics_summary: StatisticsSummary,
        config: RecommendationConfig,
    ) -> str | None:
        if candidate in existing_draws:
            return "기존 회차 중복"
        if any(number in config.excluded_numbers for number in candidate):
            return "제외 번호 포함"
        odd_count = self._odd_count(candidate)
        if odd_count < config.min_odd_count or odd_count > config.max_odd_count:
            return "홀짝 비율 위반"
        sum_total = sum(candidate)
        min_sum = max(config.min_sum, statistics_summary.sum_range[0])
        max_sum = min(config.max_sum, statistics_summary.sum_range[1])
        if sum_total < min_sum or sum_total > max_sum:
            return "합계 범위 위반"
        consecutive_pairs = sum(1 for left, right in zip(candidate, candidate[1:]) if right - left == 1)
        if consecutive_pairs > config.max_consecutive_pairs:
            return "연속 번호 위반"
        return None

    def _score_candidates(
        self,
        candidates: list[tuple[int, ...]],
        statistics_summary: StatisticsSummary,
        config: RecommendationConfig,
    ) -> list[_ScoredCandidate]:
        scored: list[_ScoredCandidate] = []
        for candidate in candidates:
            score = 0.0
            for number in candidate:
                score += statistics_summary.number_frequency.get(number, 0) * 1.0
                score += statistics_summary.recent_frequency.get(number, 0) * 1.5
                last_seen = statistics_summary.number_last_seen.get(number, 0)
                if last_seen > 0:
                    score += min(last_seen / 100.0, 3.0)
            score += len(set(candidate) & set(config.fixed_numbers)) * 5.0
            spread = candidate[-1] - candidate[0]
            score += min(spread / 10.0, 4.0)
            scored.append(_ScoredCandidate(numbers=candidate, score=round(score, 4), stage=CandidateStage.RANKED))
        return scored

    def _odd_count(self, numbers: tuple[int, ...]) -> int:
        return sum(1 for number in numbers if number % 2 == 1)


class _ScoredCandidate:
    def __init__(self, numbers: tuple[int, ...], score: float, stage: CandidateStage) -> None:
        self.numbers = numbers
        self.score = score
        self.stage = stage
