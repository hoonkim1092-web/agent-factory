"""
tests/test_skill_evolution_trigger_routing.py
==============================================
Sprint 1 — F6: on_skill_evolved trigger 분기 처리 검증.

커버:
  - metadata_enriched → 메타 보강 분기 (코드 진화 동작 없음)
  - fsa_failure / cross_verification / cross_verification_orchestrator → 코드 진화 분기
  - 알 수 없는 trigger → warning 로그
  - _notify_consolidation 호출 여부
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, call, patch

import pytest

from core.evolution_types import EvolutionDecision
from core.hooks.skill_self_evolution import (
    _CODE_EVOLUTION_TRIGGERS,
    _METADATA_TRIGGERS,
    SkillSelfEvolutionHook,
)


class TestWhitelistConstants:
    def test_metadata_triggers_contains_metadata_enriched(self):
        assert "metadata_enriched" in _METADATA_TRIGGERS

    def test_code_triggers_contains_all_three(self):
        assert "fsa_failure" in _CODE_EVOLUTION_TRIGGERS
        assert "cross_verification" in _CODE_EVOLUTION_TRIGGERS
        assert "cross_verification_orchestrator" in _CODE_EVOLUTION_TRIGGERS

    def test_no_overlap(self):
        assert _METADATA_TRIGGERS.isdisjoint(_CODE_EVOLUTION_TRIGGERS)


class TestOnSkillEvolvedBranching:
    def _make_hook(self):
        hook = SkillSelfEvolutionHook(run_id="run_x")
        return hook

    def test_metadata_trigger_does_not_call_notify_consolidation(self):
        hook = self._make_hook()
        mock_store = MagicMock()
        with patch("core.events.run_event.get_default_store", return_value=mock_store), \
             patch.object(hook, "_notify_consolidation") as mock_notify:
            hook.on_skill_evolved("s1", "v1", "v2", "metadata_enriched")
        mock_notify.assert_not_called()

    @pytest.mark.parametrize("trigger", list(_CODE_EVOLUTION_TRIGGERS))
    def test_code_trigger_calls_notify_consolidation(self, trigger):
        hook = self._make_hook()
        mock_store = MagicMock()
        with patch("core.events.run_event.get_default_store", return_value=mock_store), \
             patch.object(hook, "_notify_consolidation") as mock_notify:
            hook.on_skill_evolved("s1", "v1", "v2", trigger)
        mock_notify.assert_called_once_with("s1")

    def test_unknown_trigger_logs_warning(self, caplog):
        hook = self._make_hook()
        mock_store = MagicMock()
        with patch("core.events.run_event.get_default_store", return_value=mock_store), \
             caplog.at_level(logging.WARNING, logger="core.hooks.skill_self_evolution"):
            hook.on_skill_evolved("s1", "v1", "v2", "totally_unknown")
        assert any("알 수 없는 trigger" in r.message for r in caplog.records)

    def test_on_skill_evolved_always_calls_record(self):
        """trigger 종류와 무관하게 _record_evolution_to_memory는 항상 호출."""
        hook = self._make_hook()
        with patch.object(hook, "_record_evolution_to_memory") as mock_rec, \
             patch.object(hook, "_notify_consolidation"):
            hook.on_skill_evolved("s1", "v1", "v2", "fsa_failure", EvolutionDecision.PUBLISHED)
        mock_rec.assert_called_once_with("s1", "v1", "v2", "fsa_failure", EvolutionDecision.PUBLISHED)

    def test_decision_parameter_forwarded(self):
        hook = self._make_hook()
        captured: list = []
        mock_store = MagicMock()
        mock_store.append.side_effect = lambda e: captured.append(e)
        with patch("core.events.run_event.get_default_store", return_value=mock_store):
            hook.on_skill_evolved("s1", "v1", "v2", "fsa_failure", EvolutionDecision.REJECTED)
        from core.events.run_event import RunEventType
        assert captured[0].event_type == RunEventType.EVOLUTION_ROLLED_BACK
