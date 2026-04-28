from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lotto_predictor.game_logic import RecommendationConfig, RecommendationEngine, RecommendationRequest


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cache"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _build_500_draws() -> list[dict[str, object]]:
    draws: list[dict[str, object]] = []
    for draw_no in range(1, 501):
        base = ((draw_no - 1) % 40) + 1
        numbers = tuple(sorted((((base + offset - 1) % 45) + 1) for offset in range(6)))
        draws.append(
            {
                "drwNo": draw_no,
                "drwNoDate": f"2024-01-{((draw_no - 1) % 28) + 1:02d}",
                "numbers": list(numbers),
                "bnusNo": ((base + 6 - 1) % 45) + 1,
            }
        )
    return draws


def _import_cache_contract() -> object:
    module = pytest.importorskip(
        "lotto_predictor.cache",
        reason="캐시 계층 구현 전에는 통계 파이프라인 통합 회귀를 실행할 수 없다.",
    )
    if not hasattr(module, "JsonDrawCacheStore"):
        pytest.skip("`JsonDrawCacheStore` 계약이 아직 없어 통계 파이프라인 골격만 유지한다.")
    return module


def _import_patterns_contract() -> object:
    module = pytest.importorskip(
        "lotto_predictor.analytics.patterns",
        reason="통계 분석 엔진 모듈이 아직 구현되지 않아 파이프라인 골격만 유지한다.",
    )
    if not hasattr(module, "build_statistics_summary"):
        pytest.skip("`build_statistics_summary` 계약이 아직 없어 파이프라인 골격만 유지한다.")
    return module


def test_500회차_데이터를_로드해_통계_엔진과_추천기까지_연결하는_골격() -> None:
    cache_module = _import_cache_contract()
    patterns_module = _import_patterns_contract()
    cache_payload = _load_fixture("analytics_pipeline_store.json")
    cache_payload["draws"] = _build_500_draws()

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_file = Path(temp_dir) / "analytics-cache.json"
        cache_file.write_text(
            json.dumps(cache_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        store = cache_module.JsonDrawCacheStore.from_json(cache_file)
        draws = store.get_recent_draws(500)
        statistics_summary = patterns_module.build_statistics_summary(draws)

        batch = RecommendationEngine().generate(
            RecommendationRequest(
                draw_history=draws,
                statistics_summary=statistics_summary,
                config=RecommendationConfig(target_count=3, candidate_pool_size=12),
            )
        )

        assert len(draws) == 500
        assert batch.evaluation_summary.requested_count == 3
        assert len(batch.recommendations) == 3
