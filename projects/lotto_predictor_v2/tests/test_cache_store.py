from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cache"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _import_cache_contract() -> object:
    module = pytest.importorskip(
        "lotto_predictor.cache",
        reason="회차 로컬 캐시 모듈이 아직 구현되지 않아 회귀 골격만 고정한다.",
    )
    if not hasattr(module, "JsonDrawCacheStore"):
        pytest.skip("`JsonDrawCacheStore` 계약이 아직 구현되지 않아 회귀 골격만 유지한다.")
    return module


@pytest.fixture
def cache_hit_fixture() -> dict[str, object]:
    """캐시 hit/miss 검증용 JSON fixture 를 읽어온다."""
    return _load_fixture("cache_hit_store.json")


@pytest.fixture
def cache_expired_fixture() -> dict[str, object]:
    """만료·무효화 검증용 JSON fixture 를 읽어온다."""
    return _load_fixture("cache_expired_store.json")


def test_json_파일_기반_저장소의_cache_hit_miss_동작_골격(
    cache_hit_fixture: dict[str, object],
) -> None:
    cache_module = _import_cache_contract()
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_file = Path(temp_dir) / "draw-cache.json"
        cache_file.write_text(
            json.dumps(cache_hit_fixture, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 구현 계약:
        # - from_json(path) 또는 동등한 팩토리로 JSON 저장소를 연다.
        # - get(draw_no)는 존재 시 hit, 부재 시 miss 메타데이터를 제공한다.
        store = cache_module.JsonDrawCacheStore.from_json(cache_file)

        hit_result = store.get(500)
        miss_result = store.get(9999)

        assert hit_result.hit is True
        assert hit_result.draw["drwNo"] == 500
        assert miss_result.hit is False
        assert miss_result.draw is None


def test_cache_만료와_무효화_처리_골격(
    cache_expired_fixture: dict[str, object],
) -> None:
    cache_module = _import_cache_contract()
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_file = Path(temp_dir) / "expired-cache.json"
        cache_file.write_text(
            json.dumps(cache_expired_fixture, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        store = cache_module.JsonDrawCacheStore.from_json(cache_file)
        status_before = store.status()

        assert status_before.is_stale is True
        assert "expired_checkpoint" in status_before.stale_reasons

        invalidated = store.invalidate(draw_no=499)
        status_after = store.status()

        assert invalidated is True
        assert store.get(499).hit is False
        assert status_after.is_stale is True


@pytest.mark.xfail(
    reason="파일 락 계약은 설계에만 존재하고 실제 JSON 캐시 구현이 아직 없다.",
    strict=False,
)
def test_동시성_파일_락_시나리오_골격() -> None:
    cache_module = _import_cache_contract()
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_file = Path(temp_dir) / "shared-cache.json"
        cache_file.write_text("{}", encoding="utf-8")

        writer_a = cache_module.JsonDrawCacheStore.from_json(cache_file)
        writer_b = cache_module.JsonDrawCacheStore.from_json(cache_file)

        lock_a = writer_a.acquire_lock(timeout=0.1)
        try:
            with pytest.raises(cache_module.CacheLockTimeoutError, match="파일 락"):
                writer_b.acquire_lock(timeout=0.1)
        finally:
            writer_a.release_lock(lock_a)
