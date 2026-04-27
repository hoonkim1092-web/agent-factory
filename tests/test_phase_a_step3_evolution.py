"""
Phase A Step 3 — EVOLUTION 마무리: 직접 단위 테스트.

대상:
  - GateResult.quality_delta 필드
  - SkillEvolutionBus 7단계 캐시 무효화
  - SkillQualityGate.validate() 통과/실패 분기
  - SkillSelfEvolutionHook 카운터 / 감사 트리거
  - E2E: 결함 스킬 → QualityGate 실패 → rollback 시뮬레이션
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.skill_quality_gate import GateResult, SkillQualityGate
from core.skill_evolution_bus import SkillEvolutionBus
from core.hooks.skill_self_evolution import SkillSelfEvolutionHook
from core.agent_specializer import AgentSpecializer


# ── GateResult ───────────────────────────────────────────────────────────

class TestGateResult:
    def test_quality_delta_defaults_to_none(self):
        r = GateResult(
            passed=True,
            skill_path="/tmp/skill",
            recommended_stage="stable",
            pass_rate=1.0,
            eval_report_path="",
        )
        assert r.quality_delta is None

    def test_quality_delta_can_be_set(self):
        r = GateResult(
            passed=True,
            skill_path="/tmp/skill",
            recommended_stage="stable",
            pass_rate=1.0,
            eval_report_path="",
            quality_delta=0.15,
        )
        assert r.quality_delta == pytest.approx(0.15)

    def test_quality_delta_negative_allowed(self):
        r = GateResult(
            passed=False,
            skill_path="/tmp/skill",
            recommended_stage="draft",
            pass_rate=0.4,
            eval_report_path="",
            quality_delta=-0.3,
        )
        assert r.quality_delta == pytest.approx(-0.3)

    def test_asdict_includes_quality_delta(self):
        r = GateResult(
            passed=True,
            skill_path="/tmp/skill",
            recommended_stage="stable",
            pass_rate=1.0,
            eval_report_path="",
            quality_delta=0.05,
        )
        d = asdict(r)
        assert "quality_delta" in d
        assert d["quality_delta"] == pytest.approx(0.05)


# ── SkillEvolutionBus ────────────────────────────────────────────────────

class TestSkillEvolutionBus:
    def test_singleton(self):
        a = SkillEvolutionBus.get_instance()
        b = SkillEvolutionBus.get_instance()
        assert a is b

    def test_on_skill_evolved_no_binding_raises_nothing(self):
        bus = SkillEvolutionBus()
        # 바인딩 없이 호출해도 예외 없이 7단계 완주
        bus.on_skill_evolved(
            skill_id="test-skill",
            old_version="1.0.0",
            new_version="1.1.0",
            trigger="manual",
        )

    def test_on_bulk_enriched_empty_is_noop(self):
        bus = SkillEvolutionBus()
        bus.on_bulk_enriched([])  # 빈 리스트 → 아무 작업도 없음

    def test_on_bulk_enriched_calls_steps(self):
        bus = SkillEvolutionBus()
        with (
            patch.object(bus, "_step1_reload_registry") as s1,
            patch.object(bus, "_step2_invalidate_dep_graph") as s2,
            patch.object(bus, "_step3_recompute_embeddings") as s3,
            patch.object(bus, "_step4_clear_relevance_caches") as s4,
            patch.object(bus, "_step5_evict_module_cache") as s5,
            patch.object(bus, "_step6_evict_loader_cache") as s6,
            patch.object(bus, "_step7_broadcast") as s7,
        ):
            bus.on_bulk_enriched(["skill-a", "skill-b"])
            s1.assert_called_once()
            s2.assert_called_once()
            s3.assert_called_once()
            s4.assert_called_once()
            assert s5.call_count == 2
            s6.assert_called_once()
            # H3: broadcast는 skill_ids 개수만큼 호출됨
            assert s7.call_count == 2
            s7.assert_any_call(skill_id="skill-a", old_version="", new_version="", trigger="metadata_enriched")
            s7.assert_any_call(skill_id="skill-b", old_version="", new_version="", trigger="metadata_enriched")

    def test_on_skill_evolved_calls_all_7_steps(self):
        bus = SkillEvolutionBus()
        with (
            patch.object(bus, "_step1_reload_registry") as s1,
            patch.object(bus, "_step2_invalidate_dep_graph") as s2,
            patch.object(bus, "_step3_recompute_embeddings") as s3,
            patch.object(bus, "_step4_clear_relevance_caches") as s4,
            patch.object(bus, "_step5_evict_module_cache") as s5,
            patch.object(bus, "_step6_evict_loader_cache") as s6,
            patch.object(bus, "_step7_broadcast") as s7,
        ):
            bus.on_skill_evolved("my-skill")
            s1.assert_called_once()
            s2.assert_called_once()
            s3.assert_called_once()
            s4.assert_called_once()
            s5.assert_called_once_with("my-skill")
            s6.assert_called_once()
            s7.assert_called_once()

    def test_bind_runner(self):
        bus = SkillEvolutionBus()
        mock_runner = MagicMock()
        bus.bind_runner(mock_runner)
        assert bus._runner_ref is mock_runner

    def test_bind_event_bus(self):
        bus = SkillEvolutionBus()
        mock_eb = MagicMock()
        bus.bind_event_bus(mock_eb)
        assert bus._event_bus_ref is mock_eb


# ── SkillQualityGate ─────────────────────────────────────────────────────

class TestSkillQualityGate:
    def test_validate_eval_error_returns_failed(self, tmp_path: Path):
        gate = SkillQualityGate.__new__(SkillQualityGate)
        mock_harness = MagicMock()
        mock_harness.evaluate.side_effect = RuntimeError("harness blew up")
        gate.harness = mock_harness
        gate.registry = MagicMock()

        result = gate.validate(str(tmp_path))

        assert result.passed is False
        assert result.pass_rate == 0.0
        assert any("eval error" in r for r in result.failure_reasons)

    def test_validate_pass_rate_below_threshold_fails(self, tmp_path: Path):
        gate = SkillQualityGate.__new__(SkillQualityGate)
        mock_report = MagicMock()
        mock_report.contract_eval.total_cases = 5
        mock_report.contract_eval.pass_rate = 0.4  # below 0.8
        mock_report.contract_eval.details = []
        mock_report.recommended_stage = "draft"
        mock_report.report_path = ""
        gate.harness = MagicMock(evaluate=MagicMock(return_value=mock_report))
        gate.registry = MagicMock()

        result = gate.validate(str(tmp_path), auto_register=False)

        assert result.passed is False
        assert "contract pass_rate" in result.failure_reasons[0]

    def test_validate_passes_and_registers(self, tmp_path: Path):
        # Create minimal skill structure
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        (skill_dir / "meta.yaml").write_text("name: my_skill\n")

        gate = SkillQualityGate.__new__(SkillQualityGate)
        mock_report = MagicMock()
        mock_report.contract_eval.total_cases = 3
        mock_report.contract_eval.pass_rate = 0.9
        mock_report.recommended_stage = "stable"
        mock_report.report_path = ""
        gate.harness = MagicMock(evaluate=MagicMock(return_value=mock_report))
        gate.registry = MagicMock()

        with patch("core.skill_quality_gate.SkillQualityGate._register_with_eval") as mock_reg:
            result = gate.validate(str(skill_dir), auto_register=True)
            assert result.passed is True
            mock_reg.assert_called_once()

    def test_quality_delta_not_set_by_validate(self, tmp_path: Path):
        gate = SkillQualityGate.__new__(SkillQualityGate)
        gate.harness = MagicMock()
        gate.harness.evaluate.side_effect = RuntimeError("fail")
        gate.registry = MagicMock()

        result = gate.validate(str(tmp_path))
        assert result.quality_delta is None  # validate()는 quality_delta를 설정하지 않음


# ── SkillSelfEvolutionHook ───────────────────────────────────────────────

class TestSkillSelfEvolutionHook:
    def test_post_execute_increments_count(self):
        hook = SkillSelfEvolutionHook(check_interval=10)
        for _ in range(5):
            hook.post_execute({}, {})
        assert hook._execution_count == 5

    def test_audit_triggered_at_interval(self):
        hook = SkillSelfEvolutionHook(check_interval=3)
        with patch.object(hook, "_trigger_audit_async") as mock_audit:
            hook.post_execute({}, {})
            hook.post_execute({}, {})
            hook.post_execute({}, {})  # 3rd call → trigger
            mock_audit.assert_called_once()
            hook.post_execute({}, {})
            mock_audit.assert_called_once()  # 4th call → no trigger

    def test_get_stats(self):
        hook = SkillSelfEvolutionHook(check_interval=10)
        for _ in range(3):
            hook.post_execute({}, {})
        stats = hook.get_stats()
        assert stats["execution_count"] == 3
        assert stats["check_interval"] == 10
        assert stats["next_audit_in"] == 7
        assert stats["audit_in_progress"] is False

    def test_on_skill_evolved_logs(self, caplog, tmp_path):
        import logging
        from core.events.run_event import FileRunEventStore
        store = FileRunEventStore(base_dir=str(tmp_path))
        hook = SkillSelfEvolutionHook()
        with (
            caplog.at_level(logging.INFO, logger="core.hooks.skill_self_evolution"),
            patch("core.events.run_event.get_default_store", return_value=store),
        ):
            hook.on_skill_evolved(
                skill_id="test-skill",
                old_version="1.0",
                new_version="1.1",
                trigger="test",
            )
        assert "test-skill" in caplog.text

    def test_record_evolution_emits_run_event(self, tmp_path):
        """_record_evolution_to_memory → RunEventStore에 SKILL_EVOLVED 방출 검증."""
        from core.events.run_event import FileRunEventStore, RunEventType
        store = FileRunEventStore(base_dir=str(tmp_path))
        hook = SkillSelfEvolutionHook()
        with patch("core.events.run_event.get_default_store", return_value=store):
            hook.on_skill_evolved(
                skill_id="evolve-skill",
                old_version="2.0",
                new_version="2.1",
                trigger="fsa_failure",
            )
        events = store.list_events("_skill_evolution")
        assert len(events) == 1
        evt = events[0]
        assert evt.event_type == RunEventType.SKILL_EVOLVED
        assert evt.payload["skill_id"] == "evolve-skill"
        assert evt.payload["trigger"] == "fsa_failure"

    def test_duplicate_audit_guard(self):
        hook = SkillSelfEvolutionHook(check_interval=1)
        hook._audit_in_progress = True  # 감사 진행 중 상태 강제 세팅
        with patch.object(hook, "_run_quality_audit") as mock_run:
            hook._trigger_audit_async()
            # 이미 in_progress → 스레드 생성 없이 즉시 반환
            import time
            time.sleep(0.05)
            mock_run.assert_not_called()


# ── E2E: Defect Skill → QualityGate Fail → Rollback sim ─────────────────

class TestDefectSkillE2E:
    def test_defect_skill_fails_quality_gate(self, tmp_path: Path):
        """고의적으로 낮은 pass_rate인 스킬 → QualityGate 실패 → rollback 필요 감지."""
        skill_dir = tmp_path / "defect_skill"
        skill_dir.mkdir()

        # mock harness: 40% pass rate (below 80% threshold)
        mock_report = MagicMock()
        mock_report.contract_eval.total_cases = 5
        mock_report.contract_eval.pass_rate = 0.4
        mock_report.contract_eval.details = [
            MagicMock(passed=False, name="case1", error="assertion failed"),
            MagicMock(passed=False, name="case2", error="timeout"),
            MagicMock(passed=True, name="case3", error=""),
        ]
        mock_report.recommended_stage = "draft"
        mock_report.report_path = ""

        gate = SkillQualityGate.__new__(SkillQualityGate)
        gate.harness = MagicMock(evaluate=MagicMock(return_value=mock_report))
        gate.registry = MagicMock()

        result = gate.validate(str(skill_dir), auto_register=False)

        assert result.passed is False
        assert result.pass_rate == pytest.approx(0.4)
        assert len(result.failure_reasons) >= 1
        # rollback이 필요한 상태임을 확인 (실제 rollback은 caller 책임)
        assert result.recommended_stage == "draft"

    def test_evolved_skill_passes_quality_gate(self, tmp_path: Path):
        """진화 후 품질이 개선된 스킬 → QualityGate 통과."""
        skill_dir = tmp_path / "evolved_skill"
        skill_dir.mkdir()
        (skill_dir / "meta.yaml").write_text("name: evolved_skill\n")

        mock_report = MagicMock()
        mock_report.contract_eval.total_cases = 5
        mock_report.contract_eval.pass_rate = 0.95
        mock_report.recommended_stage = "stable"
        mock_report.report_path = str(tmp_path / "report.json")

        gate = SkillQualityGate.__new__(SkillQualityGate)
        gate.harness = MagicMock(evaluate=MagicMock(return_value=mock_report))
        gate.registry = MagicMock()

        with patch("core.skill_quality_gate.SkillQualityGate._register_with_eval"):
            result = gate.validate(str(skill_dir), auto_register=True)

        assert result.passed is True
        assert result.pass_rate == pytest.approx(0.95)
        # quality_delta는 외부 caller가 설정 (baseline과 비교)
        assert result.quality_delta is None

    def test_quality_delta_set_by_caller(self):
        """caller가 이전 pass_rate와 비교해 quality_delta를 계산 후 설정."""
        baseline_pass_rate = 0.70
        current_pass_rate = 0.90

        result = GateResult(
            passed=True,
            skill_path="/tmp/skill",
            recommended_stage="stable",
            pass_rate=current_pass_rate,
            eval_report_path="",
            quality_delta=round(current_pass_rate - baseline_pass_rate, 4),
        )

        assert result.quality_delta == pytest.approx(0.20)
        assert result.passed is True


# ── AgentSpecializer._fetch_episode_context ──────────────────────────────

class TestFetchEpisodeContext:
    def test_empty_query_returns_empty(self):
        result = AgentSpecializer._fetch_episode_context({}, "/workspace")
        assert result == ""

    def test_uninitialised_facade_returns_empty(self):
        # facade가 초기화되지 않은 경우 빈 문자열 반환
        with patch("core.memory_system.facade.UnifiedMemoryFacade.get_instance") as mock_gi:
            mock_facade = MagicMock()
            mock_facade._initialised = False
            mock_gi.return_value = mock_facade
            result = AgentSpecializer._fetch_episode_context(
                {"instruction": "deploy web app"}, "/workspace"
            )
        assert result == ""

    def test_no_records_returns_empty(self):
        mock_facade = MagicMock()
        mock_facade._initialised = True
        mock_facade.search_semantic = AsyncMock(return_value=[])
        with patch("core.memory_system.facade.UnifiedMemoryFacade.get_instance", return_value=mock_facade):
            result = AgentSpecializer._fetch_episode_context(
                {"instruction": "deploy web app"}, "/workspace"
            )
        assert result == ""

    def test_records_returned_formatted(self):
        from core.memory_system.models import MemoryRecord, MemoryType
        mock_rec = MemoryRecord(
            content="deploy web app to staging",
            memory_type=MemoryType.EPISODIC,
            metadata={"outcome": "success", "error_info": ""},
        )
        mock_facade = MagicMock()
        mock_facade._initialised = True
        mock_facade.search_semantic = AsyncMock(return_value=[mock_rec])
        with patch("core.memory_system.facade.UnifiedMemoryFacade.get_instance", return_value=mock_facade):
            result = AgentSpecializer._fetch_episode_context(
                {"instruction": "deploy web app to production"}, "/workspace"
            )
        assert "success" in result
        assert "deploy web app" in result

    def test_works_from_async_context(self):
        """이미 실행 중인 이벤트 루프에서 호출해도 RuntimeError 없이 동작한다."""
        mock_facade = MagicMock()
        mock_facade._initialised = True
        mock_facade.search_semantic = AsyncMock(return_value=[])

        async def _run():
            with patch("core.memory_system.facade.UnifiedMemoryFacade.get_instance", return_value=mock_facade):
                result = AgentSpecializer._fetch_episode_context(
                    {"instruction": "test task"}, "/workspace"
                )
            return result

        result = asyncio.run(_run())
        assert result == ""  # 레코드 없음 → 빈 문자열, RuntimeError 없음
        # ThreadPoolExecutor 경로가 실제로 search를 호출했는지 확인
        assert mock_facade.search_semantic.call_count == 1

    def test_exception_returns_empty(self):
        with patch("core.memory_system.facade.UnifiedMemoryFacade.get_instance") as mock_gi:
            mock_gi.side_effect = RuntimeError("import failed")
            result = AgentSpecializer._fetch_episode_context(
                {"instruction": "some task"}, "/workspace"
            )
        assert result == ""
