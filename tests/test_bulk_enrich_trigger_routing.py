"""
tests/test_bulk_enrich_trigger_routing.py
==========================================
Sprint 1 — F7 회귀 방지: on_bulk_enriched 호출 시 step7 broadcast가
"metadata_enriched" trigger를 사용함을 보장 (§8.2).

코드 변경 0줄, 회귀 방지 테스트만.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from core.hooks.skill_self_evolution import _METADATA_TRIGGERS


class TestBulkEnrichTriggerConsistency:
    def test_metadata_triggers_contains_metadata_enriched(self):
        """_METADATA_TRIGGERS whitelist와 bus.py:138 trigger 값이 일치."""
        assert "metadata_enriched" in _METADATA_TRIGGERS

    def test_on_bulk_enriched_broadcasts_with_metadata_enriched(self):
        """on_bulk_enriched 내부 step7 broadcast가 "metadata_enriched" trigger를 사용."""
        from core.skill_evolution_bus import SkillEvolutionBus

        bus = SkillEvolutionBus.__new__(SkillEvolutionBus)
        # 단계 1~6을 no-op으로 mock
        for step in [
            "_step1_reload_registry", "_step2_invalidate_dep_graph",
            "_step3_recompute_embeddings", "_step4_clear_relevance_caches",
            "_step5_evict_module_cache", "_step6_evict_loader_cache",
        ]:
            setattr(bus, step, MagicMock())

        # 실제 시그니처: _step7_broadcast(self, skill_id, old_version, new_version, trigger)
        mock_broadcast = MagicMock()
        bus._step7_broadcast = mock_broadcast  # type: ignore[attr-defined]

        # on_bulk_enriched 실행
        bus.on_bulk_enriched(["skill_a", "skill_b"])

        # step7 broadcast가 2번 호출됐는지 확인
        assert mock_broadcast.call_count == 2

        # 모든 호출에서 trigger="metadata_enriched" 전달 검증
        for c in mock_broadcast.call_args_list:
            kwargs = c.kwargs if c.kwargs else {}
            args = c.args if c.args else ()
            # keyword 또는 positional(4번째=trigger)로 전달
            trigger_val = kwargs.get("trigger") or (args[3] if len(args) > 3 else None)
            assert trigger_val == "metadata_enriched", (
                f"on_bulk_enriched broadcast trigger이 변경됨: {trigger_val!r} "
                f"(expected 'metadata_enriched'). "
                f"_METADATA_TRIGGERS whitelist 업데이트 필요."
            )

    def test_metadata_triggers_is_frozenset(self):
        assert isinstance(_METADATA_TRIGGERS, frozenset)
