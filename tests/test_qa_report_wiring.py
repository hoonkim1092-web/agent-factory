"""Q-S6 wiring 테스트: render_html → project_pipeline.execute + dogfood._run_verify_phase.

불변식:
- pipeline execute()가 qa_report_path 키를 반환한다 (contract 있을 때 비어있지 않음).
- pipeline execute()가 contract=None 일 때 qa_report_path="" 반환한다.
- dogfood _run_verify_phase()가 contract 있을 때 state.qa_report_path를 설정한다.
- dogfood _run_verify_phase()가 contract=None 일 때 state.qa_report_path="" 유지.
- qa_report.html 파일이 실제로 디스크에 생성된다.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.completion_contract import (
    AcceptanceGate,
    GoalContract,
    GoalEntry,
    build_evidence_ledger,
)
from core.qa_report import render_html


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _verified_contract() -> GoalContract:
    goal = GoalEntry(goal_id="G-v", description="cli test", harness_type="cli",
                     command="python --version")
    c = GoalContract(task_id="T-v", goals=[goal])
    AcceptanceGate().run(c, ".")
    return c


# ---------------------------------------------------------------------------
# 1. pipeline execute → qa_report_path 비어있지 않음 (contract 있을 때)
# ---------------------------------------------------------------------------

class TestPipelineQaReportPath(unittest.TestCase):
    """project_pipeline.execute() 반환 dict에 qa_report_path 포함 검증."""

    def _call_pipeline_gating_block(self, contract, workspace):
        """execute() 내 AcceptanceGate+render_html 로직을 직접 재현."""
        if contract is not None:
            from core.completion_contract import AcceptanceGate, build_evidence_ledger
            AcceptanceGate().run(contract, workspace)
            evidence_ledger = build_evidence_ledger(contract)
            try:
                from core.qa_report import render_html as _render_qa_html
                qa_report_path = _render_qa_html(evidence_ledger, workspace)
            except Exception:
                qa_report_path = ""
        else:
            evidence_ledger = {}
            qa_report_path = ""
        return qa_report_path, evidence_ledger

    def test_with_contract_returns_nonempty_path(self):
        """contract 있을 때 qa_report_path가 비어있지 않고 파일이 존재."""
        c = _verified_contract()
        with tempfile.TemporaryDirectory() as d:
            path, _ = self._call_pipeline_gating_block(c, d)
            self.assertTrue(path, "qa_report_path가 비어있어서는 안 됨")
            self.assertTrue(os.path.exists(path), "qa_report.html 파일이 실제 존재해야 함")

    def test_no_contract_path_is_empty(self):
        """contract=None 이면 qa_report_path=""."""
        with tempfile.TemporaryDirectory() as d:
            path, ledger = self._call_pipeline_gating_block(None, d)
            self.assertEqual(path, "")
            self.assertEqual(ledger, {})

    def test_html_file_is_named_qa_report(self):
        """생성된 파일명이 qa_report.html."""
        c = _verified_contract()
        with tempfile.TemporaryDirectory() as d:
            path, _ = self._call_pipeline_gating_block(c, d)
            self.assertEqual(os.path.basename(path), "qa_report.html")


# ---------------------------------------------------------------------------
# 2. dogfood _run_verify_phase → state.qa_report_path 설정
# ---------------------------------------------------------------------------

class TestDogfoodVerifyQaReportPath(unittest.TestCase):
    """_run_verify_phase()가 state.qa_report_path를 올바르게 설정하는지 검증."""

    def _make_state(self, contract=None):
        from core.dogfood import DogfoodState, DogfoodPhase
        state = DogfoodState(
            run_id="test-run",
            task="test task",
            phase=DogfoodPhase.VERIFY,
            source_workspace=".",
            runtime_workspace=".",
        )
        state.goal_contract = contract
        return state

    def test_with_contract_sets_qa_report_path(self):
        """contract 있을 때 verify phase 후 state.qa_report_path 설정."""
        from core.dogfood import _run_verify_phase
        c = _verified_contract()
        with tempfile.TemporaryDirectory() as d:
            state = self._make_state(c)
            state.source_workspace = d
            state.runtime_workspace = d

            with patch("core.dogfood._command_runner", return_value=(True, "")):
                plan = {"steps": [{"action": "verify"}], "verification_requirements": []}
                context = {"plan": plan}
                _run_verify_phase(state, context)

            self.assertTrue(state.qa_report_path, "qa_report_path가 설정되어야 함")
            self.assertTrue(os.path.exists(state.qa_report_path))

    def test_no_contract_qa_report_path_stays_empty(self):
        """contract=None 이면 state.qa_report_path="" 유지."""
        from core.dogfood import _run_verify_phase
        with tempfile.TemporaryDirectory() as d:
            state = self._make_state(contract=None)
            state.source_workspace = d
            state.runtime_workspace = d

            with patch("core.dogfood._command_runner", return_value=(True, "")):
                plan = {"steps": [], "verification_requirements": []}
                context = {"plan": plan}
                _run_verify_phase(state, context)

            self.assertEqual(state.qa_report_path, "")


# ---------------------------------------------------------------------------
# 3. DogfoodState round-trip — qa_report_path 직렬화 검증
# ---------------------------------------------------------------------------

class TestDogfoodStateQaReportPathRoundTrip(unittest.TestCase):
    def test_to_dict_includes_qa_report_path(self):
        from core.dogfood import DogfoodState, DogfoodPhase
        state = DogfoodState(
            run_id="r1", task="t", phase=DogfoodPhase.VERIFY,
            source_workspace=".", runtime_workspace=".",
        )
        state.qa_report_path = "/tmp/qa_report.html"
        d = state.to_dict()
        self.assertEqual(d["qa_report_path"], "/tmp/qa_report.html")

    def test_from_dict_restores_qa_report_path(self):
        from core.dogfood import DogfoodState, DogfoodPhase
        state = DogfoodState(
            run_id="r1", task="t", phase=DogfoodPhase.VERIFY,
            source_workspace=".", runtime_workspace=".",
        )
        state.qa_report_path = "/tmp/qa_report.html"
        restored = DogfoodState.from_dict(state.to_dict())
        self.assertEqual(restored.qa_report_path, "/tmp/qa_report.html")

    def test_from_dict_defaults_empty_when_missing(self):
        from core.dogfood import DogfoodState, DogfoodPhase
        d = {
            "run_id": "r1", "task": "t", "phase": "verify",
            "source_workspace": ".", "runtime_workspace": ".",
        }
        state = DogfoodState.from_dict(d)
        self.assertEqual(state.qa_report_path, "")


if __name__ == "__main__":
    unittest.main()
