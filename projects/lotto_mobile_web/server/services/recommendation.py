"""추천 파이프라인 오케스트레이션.

온라인 경로는 `lotto_predictor_v2` 수집기를 호출하고, 실패하거나 `offline=true`
이면 캐시 전용 폴백으로 전환한다.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any

from ..bootstrap import ensure_predictor_importable
from ..errors import DataUnavailableError

ensure_predictor_importable()

from lotto.analytics.patterns import analyze_patterns  # noqa: E402
from lotto.recommender import recommend_combinations  # noqa: E402

from .draw_cache import DrawCacheService  # noqa: E402

logger = logging.getLogger(__name__)


def _combo_to_dict(combo: Any) -> dict[str, Any]:
    """`Combination` 데이터클래스를 JSON 직렬화 가능한 dict로 변환한다."""
    if is_dataclass(combo):
        payload = asdict(combo)
    elif hasattr(combo, "__dict__"):
        payload = dict(combo.__dict__)
    else:
        payload = dict(combo) if isinstance(combo, dict) else {}
    numbers = payload.get("numbers")
    if isinstance(numbers, tuple):
        payload["numbers"] = list(numbers)
    return payload


class RecommendationService:
    """추천 파이프라인을 단일 `predict(n, draws, offline)` 경계로 노출한다."""

    def __init__(self, cache_service: DrawCacheService | None = None) -> None:
        self._cache_service = cache_service or DrawCacheService()

    def predict(self, n: int, draws: int, offline: bool = False) -> dict[str, Any]:
        """추천 조합 N개를 생성해 API 응답 dict를 반환한다.

        - offline=True 또는 온라인 실패 시 캐시 기반 폴백을 수행한다.
        - 반환 dict는 `RecommendationResponse` 스키마와 호환된다.
        """
        source = "offline" if offline else "api"
        status = "success"
        cache_result = None

        if offline:
            cache_result = self._cache_service.load_recent(draw_count=draws)
        else:
            try:
                cache_result = self._load_online(draws=draws)
                source = "api"
                status = "success"
            except Exception as exc:
                logger.warning("온라인 경로 실패, 캐시로 폴백합니다: %s", exc)
                cache_result = self._cache_service.load_recent(draw_count=draws)
                source = "cache"
                status = "degraded-success"

        if cache_result is None or not cache_result.has_data:
            cache_result = self._load_seed()
            if cache_result is None or not cache_result.has_data:
                raise DataUnavailableError("회차 데이터가 없어 추천을 생성할 수 없습니다.")
            source = "seed"
            status = "degraded-success"
            logger.info("Tier3 seed 데이터로 폴백: source=seed")

        ordered_draws = list(cache_result.draws)
        stats = analyze_patterns(list(reversed(ordered_draws)))
        combinations = recommend_combinations(stats, n_combinations=n)

        return {
            "generated_at": datetime.now(timezone.utc),
            "source": source,
            "status": status,
            "draws_used": len(ordered_draws),
            "latest_draw_no": cache_result.latest_draw_no,
            "latest_draw_date": cache_result.latest_draw_date,
            "combos": [_combo_to_dict(combo) for combo in combinations],
        }

    def _load_seed(self):
        """seed_draws.json에서 회차를 로드한다 (Tier 3)."""
        import pathlib
        from .draw_cache import CacheLoadResult

        seed_file = pathlib.Path(__file__).parent.parent.parent.parent / "projects" / "lotto_predictor_v2" / "seed_draws.json"
        # lotto_mobile_web 배포 시에는 상대 경로로도 탐색
        if not seed_file.exists():
            seed_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "lotto_predictor_v2" / "seed_draws.json"
        if not seed_file.exists():
            return CacheLoadResult(draws=[], latest_draw_no=None, latest_draw_date=None)

        try:
            import json
            from lotto_predictor.backend.http_client import ThreeTierLotteryClient
            client = ThreeTierLotteryClient()
            seed_draws = client.load_seed_draws()
            if not seed_draws:
                return CacheLoadResult(draws=[], latest_draw_no=None, latest_draw_date=None)

            from .draw_cache import CacheLoadResult as CLR
            last = seed_draws[-1]
            return CLR(
                draws=seed_draws,
                latest_draw_no=last.drw_no,
                latest_draw_date=str(last.drw_date),
            )
        except Exception as exc:
            logger.warning("seed 로드 실패: %s", exc)
            from .draw_cache import CacheLoadResult
            return CacheLoadResult(draws=[], latest_draw_no=None, latest_draw_date=None)

    def _load_online(self, *, draws: int):
        """온라인 수집기로 최신 회차를 확보하고 캐시로 로드한다."""
        from lotto.cache.store import LottoCacheStore
        from lotto.collector import CollectorAdapter
        from pathlib import Path as _Path

        from lotto_predictor.backend import DhLotteryClient, LottoStorage
        from lotto_predictor.collector import CollectorConfig, LottoCollector

        _db_path = _Path.home() / ".lotto_cache" / "draws.db"
        client = DhLotteryClient()
        storage: LottoStorage = LottoStorage(db_path=_db_path)
        predictor_collector = LottoCollector(
            client=client, storage=storage, config=CollectorConfig()
        )
        latest = predictor_collector.detect_latest_draw_no(probe_start=1200)

        adapter = CollectorAdapter(predictor_collector)
        store = LottoCacheStore(collector=adapter)
        start = max(1, latest - draws + 1)
        loaded = store.load_draws((start, latest))

        from .draw_cache import CacheLoadResult

        if not loaded:
            return CacheLoadResult(draws=[], latest_draw_no=None, latest_draw_date=None)
        last = loaded[-1]
        return CacheLoadResult(
            draws=loaded,
            latest_draw_no=getattr(last, "drw_no", None),
            latest_draw_date=getattr(last, "drw_no_date", None),
        )
