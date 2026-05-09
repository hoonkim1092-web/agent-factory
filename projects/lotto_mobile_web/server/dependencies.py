"""FastAPI 의존성 주입 팩토리.

테스트는 `app.dependency_overrides[get_recommendation_service]` 경로로
예측 서비스를 스텁으로 교체한다.
"""
from __future__ import annotations

from functools import lru_cache

from .services.draw_cache import DrawCacheService
from .services.recommendation import RecommendationService


@lru_cache(maxsize=1)
def get_recommendation_service() -> RecommendationService:
    """프로세스 내부에서 재사용하는 기본 추천 서비스 싱글톤."""
    return RecommendationService()


@lru_cache(maxsize=1)
def get_draw_cache_service() -> DrawCacheService:
    """기본 캐시 조회 서비스 싱글톤."""
    return DrawCacheService()
