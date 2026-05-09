"""`LottoCacheStore`를 감싸는 얇은 래퍼.

CLI의 `_load_offline` 경로와 동일한 의미를 갖지만 공개 API가 없으므로
넓은 round_range로 전체 캐시를 조회해 최신 N건을 반환한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..bootstrap import ensure_predictor_importable

ensure_predictor_importable()

from lotto.cache.store import LottoCacheStore  # noqa: E402


@dataclass(frozen=True)
class CacheLoadResult:
    """캐시 조회 결과."""

    draws: list[Any]
    latest_draw_no: int | None
    latest_draw_date: str | None

    @property
    def has_data(self) -> bool:
        return bool(self.draws)


class DrawCacheService:
    """캐시 조회 전용 서비스."""

    def __init__(self, store: LottoCacheStore | None = None) -> None:
        self._store = store or LottoCacheStore()

    def load_recent(self, draw_count: int) -> CacheLoadResult:
        """캐시에서 최신 `draw_count` 건을 오름차순으로 반환한다."""
        try:
            draws = self._store.load_draws((1, 9999))
        except Exception:
            draws = []
        if not draws:
            return CacheLoadResult(draws=[], latest_draw_no=None, latest_draw_date=None)
        draws = draws[-draw_count:]
        latest = draws[-1]
        return CacheLoadResult(
            draws=draws,
            latest_draw_no=getattr(latest, "drw_no", None),
            latest_draw_date=getattr(latest, "drw_no_date", None),
        )

    def get_latest(self) -> dict[str, Any] | None:
        """가장 최신 회차 요약을 반환한다. 비어 있으면 None."""
        result = self.load_recent(draw_count=1)
        if not result.has_data:
            return None
        latest = result.draws[-1]
        numbers = list(getattr(latest, "numbers", ()) or ())
        bonus = getattr(latest, "bonus_no", None)
        return {
            "round": result.latest_draw_no,
            "numbers": numbers,
            "bonus": bonus,
            "fetched_at": datetime.now(timezone.utc),
        }
