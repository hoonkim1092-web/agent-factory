"""
tests/test_run_event_evolution_split.py
========================================
Sprint 1 — F5: RunEventType 4종 분화 + DEFERRED 라우팅 + deprecated SKILL_EVOLVED 호환성.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.events.run_event import RunEventType
from core.evolution_types import EvolutionDecision
from core.hooks.skill_self_evolution import SkillSelfEvolutionHook


class TestRunEventTypeSplit:
    def test_four_new_types_exist(self):
        assert RunEventType.METADATA_ENRICHED
        assert RunEventType.EVOLUTION_REQUESTED
        assert RunEventType.EVOLUTION_PUBLISHED
        assert RunEventType.EVOLUTION_ROLLED_BACK

    def test_deprecated_skill_evolved_still_present(self):
        """1 sprint 호환 유지 — SKILL_EVOLVED enum 값 존재해야 함."""
        assert RunEventType.SKILL_EVOLVED == "skill_evolved"

    def test_from_dict_unknown_enum_falls_back_gracefully(self):
        """Stage 0 §10 검증: 알 수 없는 enum 값에도 from_dict가 raw string으로 폴백."""
        from core.events.run_event import RunEvent
        event = RunEvent.from_dict({
            "run_id": "r1",
            "event_type": "totally_unknown_event",
            "payload": {},
        })
        assert event.event_type == "totally_unknown_event"


class TestEvolutionDecisionRouting:
    def _run_record(self, hook: SkillSelfEvolutionHook, trigger: str, decision=None):
        captured: list = []
        mock_store = MagicMock()
        mock_store.append.side_effect = lambda e: captured.append(e)
        with patch("core.events.run_event.get_default_store", return_value=mock_store):
            hook._record_evolution_to_memory("skill_t", "v1", "v2", trigger, decision)
        return captured

    def test_metadata_enriched_trigger(self):
        hook = SkillSelfEvolutionHook()
        events = self._run_record(hook, "metadata_enriched")
        assert events[0].event_type == RunEventType.METADATA_ENRICHED

    def test_published_decision(self):
        hook = SkillSelfEvolutionHook()
        events = self._run_record(hook, "fsa_failure", EvolutionDecision.PUBLISHED)
        assert events[0].event_type == RunEventType.EVOLUTION_PUBLISHED

    def test_rejected_decision(self):
        hook = SkillSelfEvolutionHook()
        events = self._run_record(hook, "fsa_failure", EvolutionDecision.REJECTED)
        assert events[0].event_type == RunEventType.EVOLUTION_ROLLED_BACK

    def test_error_decision(self):
        hook = SkillSelfEvolutionHook()
        events = self._run_record(hook, "fsa_failure", EvolutionDecision.ERROR)
        assert events[0].event_type == RunEventType.EVOLUTION_ROLLED_BACK

    def test_deferred_decision_maps_to_rolled_back_with_reason(self):
        """DEFERRED는 ROLLED_BACK으로 매핑, payload.reason="deferred"로 구분."""
        hook = SkillSelfEvolutionHook()
        events = self._run_record(hook, "fsa_failure", EvolutionDecision.DEFERRED)
        assert events[0].event_type == RunEventType.EVOLUTION_ROLLED_BACK
        assert events[0].payload.get("reason") == "deferred"

    def test_no_decision_code_trigger_maps_to_requested(self):
        hook = SkillSelfEvolutionHook()
        events = self._run_record(hook, "cross_verification", None)
        assert events[0].event_type == RunEventType.EVOLUTION_REQUESTED

    def test_decision_value_stored_in_payload(self):
        hook = SkillSelfEvolutionHook()
        events = self._run_record(hook, "fsa_failure", EvolutionDecision.PUBLISHED)
        assert events[0].payload.get("decision") == "published"
