"""
tests/test_skill_self_evolution_hook_runid.py
=============================================
Sprint 1 — F4: SkillSelfEvolutionHook __init__(run_id=) 정상화 검증.

커버:
  - run_id= 파라미터가 인스턴스 속성 _run_id로 저장
  - _record_evolution_to_memory에서 sentinel "_skill_evolution" fallback 동작
  - run_id= 주입 시 실제 run_id가 RunEvent에 기록됨
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.hooks.skill_self_evolution import SkillSelfEvolutionHook


class TestRunIdInit:
    def test_default_run_id_is_none(self):
        hook = SkillSelfEvolutionHook()
        assert hook._run_id is None

    def test_explicit_run_id_stored(self):
        hook = SkillSelfEvolutionHook(run_id="run_abc")
        assert hook._run_id == "run_abc"

    def test_sentinel_fallback_when_run_id_none(self):
        hook = SkillSelfEvolutionHook(run_id=None)
        captured: list[object] = []

        mock_store = MagicMock()
        mock_store.append.side_effect = lambda e: captured.append(e)

        with patch("core.events.run_event.get_default_store", return_value=mock_store):
            hook._record_evolution_to_memory("skill_x", "v1", "v2", "fsa_failure")

        assert len(captured) == 1
        assert captured[0].run_id == "_skill_evolution"

    def test_explicit_run_id_used_in_event(self):
        hook = SkillSelfEvolutionHook(run_id="run_test_123")
        captured: list[object] = []

        mock_store = MagicMock()
        mock_store.append.side_effect = lambda e: captured.append(e)

        with patch("core.events.run_event.get_default_store", return_value=mock_store):
            hook._record_evolution_to_memory("skill_y", "v1", "v2", "fsa_failure")

        assert len(captured) == 1
        assert captured[0].run_id == "run_test_123"

    def test_old_current_run_id_attr_not_used(self):
        """Stage 0의 _current_run_id 외부 주입 패턴은 더 이상 사용하지 않는다."""
        hook = SkillSelfEvolutionHook(run_id=None)
        hook._current_run_id = "injected_old_style"  # type: ignore[attr-defined]
        captured: list[object] = []

        mock_store = MagicMock()
        mock_store.append.side_effect = lambda e: captured.append(e)

        with patch("core.events.run_event.get_default_store", return_value=mock_store):
            hook._record_evolution_to_memory("skill_z", "v1", "v2", "fsa_failure")

        # _current_run_id가 아닌 _run_id(=None)에서 sentinel 사용
        assert captured[0].run_id == "_skill_evolution"
