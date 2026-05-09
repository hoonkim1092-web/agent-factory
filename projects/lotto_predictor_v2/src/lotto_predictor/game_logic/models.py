from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


NumberSet = tuple[int, int, int, int, int, int]


class CandidateStage(str, Enum):
    INITIALIZED = "초기화"
    GENERATED = "생성"
    VALIDATED = "규칙 검증"
    SCORED = "점수화"
    RANKED = "정렬"
    SELECTED = "최종 선택"
    REJECTED = "탈락"


@dataclass(frozen=True)
class LottoDraw:
    draw_no: int
    numbers: NumberSet
    bonus_number: int | None = None


@dataclass(frozen=True)
class StatisticsSummary:
    number_frequency: dict[int, int]
    recent_frequency: dict[int, int] = field(default_factory=dict)
    number_last_seen: dict[int, int] = field(default_factory=dict)
    sum_range: tuple[int, int] = (100, 175)


@dataclass(frozen=True)
class RecommendationConfig:
    target_count: int = 5
    candidate_pool_size: int = 12
    min_odd_count: int = 2
    max_odd_count: int = 4
    min_sum: int = 100
    max_sum: int = 175
    max_consecutive_pairs: int = 1
    excluded_numbers: tuple[int, ...] = ()
    fixed_numbers: tuple[int, ...] = ()


@dataclass(frozen=True)
class RecommendationRequest:
    draw_history: list[LottoDraw]
    statistics_summary: StatisticsSummary
    config: RecommendationConfig


@dataclass(frozen=True)
class RejectedCandidate:
    numbers: NumberSet
    stage: CandidateStage
    reason: str


@dataclass(frozen=True)
class RejectionReasonSummary:
    reason: str
    count: int


@dataclass(frozen=True)
class EvaluationSummary:
    requested_count: int
    generated_candidates: int
    validated_candidates: int
    scored_candidates: int
    selected_candidates: int
    candidate_pool: tuple[int, ...]


@dataclass(frozen=True)
class RecommendationResult:
    numbers: NumberSet
    score: float
    odd_even_ratio: str
    sum_total: int
    matched_fixed_numbers: tuple[int, ...]
    stage: CandidateStage = CandidateStage.SELECTED


@dataclass(frozen=True)
class RecommendationBatch:
    recommendations: list[RecommendationResult]
    rejected_candidates: list[RejectionReasonSummary]
    evaluation_summary: EvaluationSummary
