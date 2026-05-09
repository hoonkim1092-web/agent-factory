"""로또 추천 API의 Pydantic v2 모델 모음."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

N_MIN = 1
N_MAX = 10
DRAWS_MIN = 100
DRAWS_MAX = 500


class RecommendationQuery(BaseModel):
    """`GET /api/recommend`의 쿼리 파라미터 DTO."""

    model_config = ConfigDict(extra="forbid")

    n: int = Field(default=5, ge=N_MIN, le=N_MAX, description="추천 조합 수 (1~10)")
    draws: int = Field(
        default=DRAWS_MAX,
        ge=DRAWS_MIN,
        le=DRAWS_MAX,
        description="분석에 사용할 회차 수 (100~500)",
    )
    offline: bool = Field(
        default=False,
        description="true면 캐시만 사용하고 네트워크 호출을 금지한다.",
    )


class RecommendationCombo(BaseModel):
    """추천된 번호 조합 한 건."""

    model_config = ConfigDict(extra="allow")

    numbers: list[int] = Field(..., min_length=6, max_length=6)
    score: float
    odd_even_ratio: str
    section_distribution: Any

    @field_validator("numbers")
    @classmethod
    def _validate_numbers(cls, value: list[int]) -> list[int]:
        for number in value:
            if not 1 <= number <= 45:
                raise ValueError("번호는 1~45 범위여야 합니다.")
        return value


class RecommendationResponse(BaseModel):
    """`GET /api/recommend`의 응답 본문."""

    model_config = ConfigDict(extra="allow")

    generated_at: datetime
    source: str
    status: str = "success"
    draws_used: int
    latest_draw_no: int | None = None
    latest_draw_date: str | None = None
    combos: list[RecommendationCombo]


class DrawCacheEntry(BaseModel):
    """`GET /api/draws/latest`의 응답 본문."""

    round: int
    numbers: list[int] = Field(..., min_length=6, max_length=6)
    bonus: int | None = None
    fetched_at: datetime


class HealthResponse(BaseModel):
    """`GET /api/health`의 응답 본문."""

    status: str = "ok"
    version: str
    time: datetime


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
