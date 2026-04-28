"""
tests/test_skill_evolution_controller.py
=========================================
SelfEvolutionController 단위 테스트 — Sprint 2.

evolve_skill / verify_evolved_skill_sandbox / SkillQualityGate / SkillEvolutionBus를
mock해서 submit() 4종 결과(PUBLISHED/REJECTED/DEFERRED/ERROR)와
RunBudget 연동, Ledger no-op를 검증.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from core.evolution_types import EvolutionDecision
from core.skill_evolution_controller import SelfEvolutionController


# ── 헬퍼 ──────────────────────────────────────────────────────────────────

@dataclass
class _FakeGateResult:
    passed: bool
    failure_reasons: list


def _make_controller(
    live_dir: str,
    *,
    budget=None,
    ledger=None,
    run_id: str = "test-run",
) -> SelfEvolutionController:
    return SelfEvolutionController(
        ledger=ledger,
        run_id=run_id,
        budget=budget,
    )


def _setup_live_dir(tmp_path) -> str:
    """skill.py + meta.yaml이 있는 임시 live skill 디렉토리."""
    live = tmp_path / "skills" / "my_skill"
    live.mkdir(parents=True)
    (live / "skill.py").write_text("def apply(): pass\n")
    (live / "meta.yaml").write_text("version: '1.0.0'\nname: my_skill\n")
    return str(live)


def _setup_candidate_dir(tmp_path, name: str = "cand") -> str:
    """sandbox 검증을 통과할 수 있도록 skill.py가 있는 candidate 디렉토리."""
    cand = tmp_path / name
    cand.mkdir(parents=True, exist_ok=True)
    (cand / "skill.py").write_text("def apply(): return True\n")
    (cand / "meta.yaml").write_text("version: '1.1.0'\nname: my_skill\n")
    return str(cand)


# ── submit() — PUBLISHED 경로 ─────────────────────────────────────────────

class TestSubmitPublished:
    def test_published_on_all_gates_pass(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        cand_dir = _setup_candidate_dir(tmp_path)  # skill.py 포함
        ctrl = _make_controller(live_dir)

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=cand_dir),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget"),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._run_quality_gate",
                  return_value=_FakeGateResult(passed=True, failure_reasons=[])),
            patch("core.skill_evolution_controller.SelfEvolutionController._publish"),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_candidate_version",
                  return_value="1.1.0"),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_live_version",
                  return_value="1.0.0"),
        ):
            result = ctrl.submit(
                skill_dir=live_dir,
                skill_id="my_skill",
                trigger="fsa_failure",
            )

        assert result.decision == EvolutionDecision.PUBLISHED
        assert result.new_version == "1.1.0"
        assert result.rejection_reason is None
        assert result.candidate_dir is None  # publish 후 소멸


# ── submit() — REJECTED 경로들 ───────────────────────────────────────────

class TestSubmitRejected:
    def test_rejected_when_budget_exhausted(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        budget = MagicMock()
        budget.is_exhausted.return_value = True
        ctrl = _make_controller(live_dir, budget=budget)

        result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="t")

        assert result.decision == EvolutionDecision.REJECTED
        assert result.rejection_reason == "budget_exhausted_pre_call"

    def test_rejected_when_budget_insufficient(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        budget = MagicMock()
        budget.is_exhausted.return_value = False
        budget.remaining.return_value = 10  # < _ESTIMATED_EVOLUTION_COST
        ctrl = _make_controller(live_dir, budget=budget)

        result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="t")

        assert result.decision == EvolutionDecision.REJECTED
        assert result.rejection_reason == "budget_insufficient_remaining"

    def test_rejected_when_evolve_skill_fails(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        ctrl = _make_controller(live_dir)

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=str(tmp_path / "cand")),
            patch("core.skill_creator.evolve_skill", return_value=False),
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.REJECTED
        assert result.rejection_reason == "evolve_skill_failed"

    def test_rejected_when_sandbox_fails(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        cand = tmp_path / "cand"
        cand.mkdir()
        (cand / "skill.py").write_text("bad_code()")
        ctrl = _make_controller(live_dir)

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=str(cand)),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget"),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=False),
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.REJECTED
        assert result.rejection_reason == "sandbox_verification_failed"

    def test_rejected_when_gate_fails(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        cand_dir = _setup_candidate_dir(tmp_path, "cand_gate")
        ctrl = _make_controller(live_dir)

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=cand_dir),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget"),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._run_quality_gate",
                  return_value=_FakeGateResult(passed=False, failure_reasons=["score too low"])),
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.REJECTED
        assert "quality_gate_failed" in (result.rejection_reason or "")


# ── submit() — DEFERRED 경로 ─────────────────────────────────────────────

class TestSubmitDeferred:
    def test_deferred_when_gate_raises(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        cand_dir = _setup_candidate_dir(tmp_path, "cand_defer")
        ctrl = _make_controller(live_dir)

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=cand_dir),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget"),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._run_quality_gate",
                  return_value=None),  # gate 예외 → None
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.DEFERRED
        assert result.rejection_reason == "quality_gate_incomplete"


# ── submit() — ERROR 경로 ─────────────────────────────────────────────────

class TestSubmitError:
    def test_error_on_unexpected_exception(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        ctrl = _make_controller(live_dir)

        with patch(
            "core.skill_evolution_controller.SelfEvolutionController._create_candidate",
            side_effect=RuntimeError("unexpected"),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.ERROR
        assert "unexpected" in (result.rejection_reason or "")

    def test_error_cost_tokens_reflects_actual_budget_consumed(self, tmp_path):
        """_record_budget 이후 예외 시 cost_tokens에 실제 소비값이 반영된다."""
        live_dir = _setup_live_dir(tmp_path)
        budget = MagicMock()
        budget.is_exhausted.return_value = False
        budget.remaining.return_value = 999_999
        budget.consumed = 0
        ctrl = _make_controller(live_dir, budget=budget)

        def fake_record_budget(candidate_dir):
            budget.consumed = 500  # _record_budget 후 consumed 증가 시뮬레이션

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=_setup_candidate_dir(tmp_path, "cand_err_cost")),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget",
                  side_effect=fake_record_budget),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  side_effect=RuntimeError("sandbox crash after budget")),
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.ERROR
        assert result.cost_tokens == 500  # pre_consumed=0, consumed=500 → delta=500


# ── partial publish rollback ──────────────────────────────────────────────

class TestPublishRollback:
    def test_live_restored_on_partial_publish_failure(self, tmp_path):
        """shutil.move가 2번째 파일에서 실패하면 live dir이 원본으로 복원된다."""
        live = tmp_path / "skills" / "sk"
        live.mkdir(parents=True)
        (live / "skill.py").write_text("original_code()\n")
        (live / "SKILL.md").write_text("# original\n")
        (live / "meta.yaml").write_text("version: '1.0.0'\n")

        cand = tmp_path / "cand"
        cand.mkdir()
        (cand / "skill.py").write_text("evolved_code()\n")
        (cand / "SKILL.md").write_text("# evolved\n")
        (cand / "meta.yaml").write_text("version: '1.1.0'\n")

        ctrl = SelfEvolutionController()
        call_count = 0

        original_move = __import__("shutil").move

        def failing_move(src, dst):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # 2번째 파일 이동 시 실패
                raise OSError("simulated disk error")
            return original_move(src, dst)

        with (
            patch("core.skill_evolution_controller.shutil.move", side_effect=failing_move),
            patch("core.skill_evolution_bus.SkillEvolutionBus"),
        ):
            try:
                ctrl._publish(
                    str(cand), str(live),
                    skill_id="sk", old_version="1.0.0", new_version="1.1.0", trigger="t",
                )
            except Exception:
                pass  # ERROR 경로

        # live dir이 original 상태여야 한다 (이동됐다가 스냅샷으로 복원)
        assert "original_code" in (live / "skill.py").read_text()
        assert "# original" in (live / "SKILL.md").read_text()
        assert "1.0.0" in (live / "meta.yaml").read_text()
        # 스냅샷 파일은 정리되어야 한다
        snaps = list(live.glob("*.__publish_snap__"))
        assert snaps == [], f"스냅샷 파일 잔류: {snaps}"

    def test_error_decision_on_publish_failure(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        ctrl = _make_controller(live_dir)

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=_setup_candidate_dir(tmp_path, "cand_pub_err")),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget"),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._run_quality_gate",
                  return_value=_FakeGateResult(passed=True, failure_reasons=[])),
            patch("core.skill_evolution_controller.SelfEvolutionController._publish",
                  side_effect=OSError("disk full")),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_candidate_version",
                  return_value="1.1.0"),
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.ERROR
        assert "disk full" in (result.rejection_reason or "")


# ── RunBudget 연동 ────────────────────────────────────────────────────────

class TestRunBudget:
    def test_record_called_after_evolve(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        budget = MagicMock()
        budget.is_exhausted.return_value = False
        budget.remaining.return_value = 999_999
        budget.consumed = 0
        ctrl = _make_controller(live_dir, budget=budget)

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=_setup_candidate_dir(tmp_path, "cand_budget")),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._run_quality_gate",
                  return_value=_FakeGateResult(passed=True, failure_reasons=[])),
            patch("core.skill_evolution_controller.SelfEvolutionController._publish"),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_candidate_version",
                  return_value="1.1.0"),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_live_version",
                  return_value="1.0.0"),
        ):
            ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")
        # _record_budget(step 6)은 _verify_sandbox(step 7) 이전에 호출된다.
        # cand_budget/skill.py가 존재하므로 budget.record가 실제로 호출된다.
        budget.record.assert_called_once()

    def test_record_budget_reads_skill_py(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        cand = tmp_path / "cand2"
        cand.mkdir()
        (cand / "skill.py").write_text("a" * 400)

        budget = MagicMock()
        ctrl = SelfEvolutionController(budget=budget)
        ctrl._record_budget(str(cand))

        budget.record.assert_called_once()
        call_arg = budget.record.call_args[0][0]
        assert "a" * 400 == call_arg


# ── Ledger no-op ──────────────────────────────────────────────────────────

class TestLedgerNoOp:
    def test_no_ledger_does_not_raise(self, tmp_path):
        live_dir = _setup_live_dir(tmp_path)
        ctrl = SelfEvolutionController(ledger=None)

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=str(tmp_path / "cand")),
            patch("core.skill_creator.evolve_skill", return_value=False),
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="t")

        assert result.decision == EvolutionDecision.REJECTED  # evolve_skill=False → REJECTED

    def test_ledger_append_called_on_published_with_correct_versions(self, tmp_path):
        from core.evolution_ledger import LedgerEntry

        live_dir = _setup_live_dir(tmp_path)
        ledger = MagicMock()
        ctrl = SelfEvolutionController(ledger=ledger, run_id="r1")

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=_setup_candidate_dir(tmp_path, "cand_ledger")),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget"),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._run_quality_gate",
                  return_value=_FakeGateResult(passed=True, failure_reasons=[])),
            patch("core.skill_evolution_controller.SelfEvolutionController._publish"),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_candidate_version",
                  return_value="1.1.0"),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_live_version",
                  return_value="1.0.0"),
        ):
            ctrl.submit(skill_dir=live_dir, skill_id="s", trigger="fsa_failure")

        ledger.append.assert_called_once()
        call_arg = ledger.append.call_args[0][0]
        assert isinstance(call_arg, LedgerEntry)
        assert call_arg.old_version == "1.0.0"
        assert call_arg.new_version == "1.1.0"
        assert call_arg.skill_id == "s"
        assert call_arg.run_id == "r1"


# ── RunEvent 기록 ──────────────────────────────────────────────────────────

class TestRunEventEmission:
    """REJECTED/DEFERRED/ERROR 결정 시 EVOLUTION_ROLLED_BACK RunEvent 기록 검증 (BLOCK fix)."""

    def test_rolled_back_event_emitted_on_rejected(self, tmp_path):
        from core.events.run_event import RunEventType
        from unittest.mock import MagicMock, patch

        live_dir = _setup_live_dir(tmp_path)
        mock_store = MagicMock()
        ctrl = SelfEvolutionController(run_id="r-reject")

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=str(tmp_path / "cand_re")),
            patch("core.skill_creator.evolve_skill", return_value=False),
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
            patch("core.events.run_event.get_default_store", return_value=mock_store),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="my_skill", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.REJECTED
        mock_store.append.assert_called_once()
        event = mock_store.append.call_args[0][0]
        assert event.event_type == RunEventType.EVOLUTION_ROLLED_BACK
        assert event.payload["skill_id"] == "my_skill"
        assert event.payload["decision"] == "rejected"
        assert event.run_id == "r-reject"

    def test_no_rolled_back_event_on_published(self, tmp_path):
        from unittest.mock import MagicMock, patch

        live_dir = _setup_live_dir(tmp_path)
        mock_store = MagicMock()
        ctrl = SelfEvolutionController(run_id="r-pub")

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=_setup_candidate_dir(tmp_path, "cand_pub")),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget"),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._run_quality_gate",
                  return_value=_FakeGateResult(passed=True, failure_reasons=[])),
            patch("core.skill_evolution_controller.SelfEvolutionController._publish"),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_candidate_version",
                  return_value="1.1.0"),
            patch("core.skill_evolution_controller.SelfEvolutionController._read_live_version",
                  return_value="1.0.0"),
            patch("core.events.run_event.get_default_store", return_value=mock_store),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="my_skill", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.PUBLISHED
        mock_store.append.assert_not_called()  # PUBLISHED는 Bus 경유, Controller에서 직접 미기록

    def test_rolled_back_event_emitted_on_deferred(self, tmp_path):
        from core.events.run_event import RunEventType
        from unittest.mock import MagicMock, patch

        live_dir = _setup_live_dir(tmp_path)
        mock_store = MagicMock()
        ctrl = SelfEvolutionController(run_id="r-deferred")

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  return_value=_setup_candidate_dir(tmp_path, "cand_def")),
            patch("core.skill_creator.evolve_skill", return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._record_budget"),
            patch("core.skill_evolution_controller.SelfEvolutionController._verify_sandbox",
                  return_value=True),
            patch("core.skill_evolution_controller.SelfEvolutionController._run_quality_gate",
                  return_value=None),  # gate 예외 → DEFERRED
            patch("core.skill_evolution_controller.SelfEvolutionController._discard_candidate"),
            patch("core.events.run_event.get_default_store", return_value=mock_store),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="my_skill", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.DEFERRED
        mock_store.append.assert_called_once()
        event = mock_store.append.call_args[0][0]
        assert event.event_type == RunEventType.EVOLUTION_ROLLED_BACK
        assert event.payload["decision"] == "deferred"

    def test_rolled_back_event_emitted_on_error(self, tmp_path):
        from core.events.run_event import RunEventType
        from unittest.mock import MagicMock, patch

        live_dir = _setup_live_dir(tmp_path)
        mock_store = MagicMock()
        ctrl = SelfEvolutionController(run_id="r-error")

        with (
            patch("core.skill_evolution_controller.SelfEvolutionController._create_candidate",
                  side_effect=RuntimeError("disk full")),  # 예외 → ERROR
            patch("core.events.run_event.get_default_store", return_value=mock_store),
        ):
            result = ctrl.submit(skill_dir=live_dir, skill_id="my_skill", trigger="fsa_failure")

        assert result.decision == EvolutionDecision.ERROR
        mock_store.append.assert_called_once()
        event = mock_store.append.call_args[0][0]
        assert event.event_type == RunEventType.EVOLUTION_ROLLED_BACK
        assert event.payload["decision"] == "error"
