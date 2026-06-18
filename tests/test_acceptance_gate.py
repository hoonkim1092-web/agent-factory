"""S2 tests: ExecutionHarness + AcceptanceGate.

Design: docs/2026-06-17-af-completion-contract-goal-verification-design.md §5·§6·§9
"""
from __future__ import annotations

import shlex
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from core.completion_contract import (
    AcceptanceGate,
    ExecutionHarness,
    GoalContract,
    GoalEntry,
    HarnessResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cli_goal(command: str = "") -> GoalEntry:
    return GoalEntry(goal_id="G-1", description="test", harness_type="cli", command=command)


def _lib_goal(command: str = "") -> GoalEntry:
    return GoalEntry(goal_id="G-1", description="test", harness_type="library", command=command)


def _server_goal(command: str = "") -> GoalEntry:
    return GoalEntry(goal_id="G-1", description="test", harness_type="server", command=command)


def _gui_goal() -> GoalEntry:
    return GoalEntry(goal_id="G-1", description="test", harness_type="gui")


def _none_goal() -> GoalEntry:
    return GoalEntry(goal_id="G-1", description="test", harness_type="none")


def _fake_proc(returncode: int = 0) -> MagicMock:
    p = MagicMock()
    p.returncode = returncode
    p.stdout = ""
    p.stderr = ""
    return p


# ---------------------------------------------------------------------------
# ExecutionHarness — cli
# ---------------------------------------------------------------------------

class TestExecutionHarnessCliMocked:
    def test_cli_exit_0_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_proc(0))
        r = ExecutionHarness().run(_cli_goal("python --version"), str(tmp_path))
        assert r.ok is True
        assert r.evidence_type == "exit_code"
        assert r.evidence_value == "0"
        assert r.command_run == "python --version"

    def test_cli_exit_nonzero_failed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_proc(1))
        r = ExecutionHarness().run(_cli_goal("cmd arg"), str(tmp_path))
        assert r.ok is False
        assert r.evidence_value == "1"

    def test_cli_no_command_unverified(self, tmp_path):
        r = ExecutionHarness().run(_cli_goal(""), str(tmp_path))
        assert r.ok is False
        assert r.evidence_type == "unverified"

    def test_cli_timeout(self, tmp_path, monkeypatch):
        def _raise(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="x", timeout=1)
        monkeypatch.setattr(subprocess, "run", _raise)
        r = ExecutionHarness().run(_cli_goal("x"), str(tmp_path))
        assert r.ok is False
        assert r.evidence_value == "timeout"

    def test_cli_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError()))
        r = ExecutionHarness().run(_cli_goal("no_such_cmd"), str(tmp_path))
        assert r.ok is False
        assert r.evidence_value == "command not found"

    def test_cli_shlex_error_is_unverified_not_failed(self, tmp_path):
        # shlex.split 오류 → evidence_type="unverified" (FAILED 아님, §6.2 불변식)
        r = ExecutionHarness().run(_cli_goal("cmd 'unclosed"), str(tmp_path))
        assert r.ok is False
        assert r.evidence_type == "unverified"

    def test_cli_shlex_posix_matches_platform(self, tmp_path, monkeypatch):
        # shlex.split에 posix=True/False가 현재 플랫폼에 맞게 전달되는지 검증
        captured = []
        original_split = shlex.split

        def mock_split(cmd, posix=True):
            captured.append(posix)
            return original_split(cmd, posix=posix)

        monkeypatch.setattr(shlex, "split", mock_split)
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_proc(0))
        ExecutionHarness().run(_cli_goal("python --version"), str(tmp_path))
        assert captured and captured[0] == (sys.platform != "win32")


# ---------------------------------------------------------------------------
# ExecutionHarness — library (real subprocess, 빠름)
# ---------------------------------------------------------------------------

class TestExecutionHarnessLibraryReal:
    def test_library_success(self, tmp_path):
        r = ExecutionHarness().run(_lib_goal("import sys; assert sys.version"), str(tmp_path))
        assert r.ok is True
        assert r.evidence_type == "exit_code"
        assert r.evidence_value == "0"

    def test_library_failure(self, tmp_path):
        r = ExecutionHarness().run(_lib_goal("raise ValueError('fail')"), str(tmp_path))
        assert r.ok is False
        assert r.evidence_value == "1"

    def test_library_no_command_unverified(self, tmp_path):
        r = ExecutionHarness().run(_lib_goal(""), str(tmp_path))
        assert r.ok is False
        assert r.evidence_type == "unverified"

    def test_library_command_run_preserved(self, tmp_path):
        code = "import sys; assert sys.version"
        r = ExecutionHarness().run(_lib_goal(code), str(tmp_path))
        assert r.command_run == code


# ---------------------------------------------------------------------------
# ExecutionHarness — gui / none
# ---------------------------------------------------------------------------

class TestExecutionHarnessOther:
    def test_gui_cannot_verify(self, tmp_path):
        r = ExecutionHarness().run(_gui_goal(), str(tmp_path))
        assert r.ok is False
        assert r.evidence_type == "cannot_verify"

    def test_none_harness_unverified(self, tmp_path):
        r = ExecutionHarness().run(_none_goal(), str(tmp_path))
        assert r.ok is False
        assert r.evidence_type == "unverified"

    def test_unknown_harness_type_unverified(self, tmp_path):
        goal = GoalEntry(goal_id="G-1", description="x", harness_type="unknown")
        r = ExecutionHarness().run(goal, str(tmp_path))
        assert r.ok is False
        assert r.evidence_type == "unverified"


# ---------------------------------------------------------------------------
# ExecutionHarness — server (mocked Popen)
# ---------------------------------------------------------------------------

class TestExecutionHarnessServerMocked:
    def test_server_alive_ok(self, tmp_path, monkeypatch):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # 살아있음
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: mock_proc)
        monkeypatch.setattr("core.completion_contract.time.sleep", lambda _: None)
        r = ExecutionHarness().run(_server_goal("start_server"), str(tmp_path))
        assert r.ok is True
        assert r.evidence_value == "process_alive"
        mock_proc.terminate.assert_called_once()

    def test_server_dead_failed(self, tmp_path, monkeypatch):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # 죽음
        mock_proc.returncode = 1
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: mock_proc)
        monkeypatch.setattr("core.completion_contract.time.sleep", lambda _: None)
        r = ExecutionHarness().run(_server_goal("bad_server"), str(tmp_path))
        assert r.ok is False
        assert r.evidence_value == "1"

    def test_server_no_command_unverified(self, tmp_path):
        r = ExecutionHarness().run(_server_goal(""), str(tmp_path))
        assert r.ok is False
        assert r.evidence_type == "unverified"


# ---------------------------------------------------------------------------
# AcceptanceGate — verdict 채우기
# ---------------------------------------------------------------------------

class TestAcceptanceGate:
    def test_cli_verified(self, tmp_path, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_proc(0))
        goal = _cli_goal(f"{sys.executable} --version")
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert goal.verdict == "VERIFIED"
        assert goal.evidence is not None
        assert goal.evidence.evidence_type == "exit_code"

    def test_cli_failed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_proc(1))
        goal = _cli_goal("false_cmd")
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert goal.verdict == "FAILED"
        assert goal.evidence is not None

    def test_gui_cannot_verify_no_harness_call(self, tmp_path):
        # AcceptanceGate가 gui를 직접 처리 — harness 미호출
        goal = _gui_goal()
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert goal.verdict == "CANNOT_VERIFY"
        assert goal.cannot_verify_reason == "display required"

    def test_gui_preserves_existing_cannot_verify_reason(self, tmp_path):
        goal = GoalEntry(goal_id="G-1", description="x", harness_type="gui",
                         verdict="UNVERIFIED", cannot_verify_reason="needs WASAPI")
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert goal.verdict == "CANNOT_VERIFY"
        assert goal.cannot_verify_reason == "needs WASAPI"

    def test_none_harness_unverified(self, tmp_path):
        # INV-F: harness_type="none" → UNVERIFIED (file-exists 자동통과 금지)
        goal = _none_goal()
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert goal.verdict == "UNVERIFIED"
        assert goal.evidence is not None
        assert goal.evidence.evidence_type == "unverified"

    def test_idempotent_skip_verified(self, tmp_path, monkeypatch):
        call_count = []
        original_run = ExecutionHarness.run

        def counting_run(self, goal, workspace, timeout=30):
            call_count.append(1)
            return original_run(self, goal, workspace, timeout)

        monkeypatch.setattr(ExecutionHarness, "run", counting_run)
        goal = GoalEntry(goal_id="G-1", description="x", harness_type="cli",
                         verdict="VERIFIED", command="x")
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert len(call_count) == 0  # 재실행 안 함

    def test_idempotent_skip_failed(self, tmp_path, monkeypatch):
        call_count = []
        original_run = ExecutionHarness.run

        def counting_run(self, goal, workspace, timeout=30):
            call_count.append(1)
            return original_run(self, goal, workspace, timeout)

        monkeypatch.setattr(ExecutionHarness, "run", counting_run)
        goal = GoalEntry(goal_id="G-1", description="x", harness_type="cli",
                         verdict="FAILED", command="x")
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert len(call_count) == 0

    def test_idempotent_skip_cannot_verify(self, tmp_path):
        goal = GoalEntry(goal_id="G-1", description="x", harness_type="gui",
                         verdict="CANNOT_VERIFY")
        original_reason = goal.cannot_verify_reason
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert goal.verdict == "CANNOT_VERIFY"
        assert goal.cannot_verify_reason == original_reason

    def test_run_returns_contract(self, tmp_path):
        c = GoalContract(task_id="T-1", goals=[])
        result = AcceptanceGate().run(c, str(tmp_path))
        assert result is c

    def test_unverified_evidence_type_gives_unverified_verdict(self, tmp_path, monkeypatch):
        # evidence_type="unverified" → UNVERIFIED, FAILED 아님 (§5.2/§6.2)
        monkeypatch.setattr(
            ExecutionHarness, "run",
            lambda self, goal, ws, timeout=30: HarnessResult(
                ok=False, evidence_type="unverified",
                evidence_value="harness_type unresolved", command_run="",
            ),
        )
        goal = GoalEntry(goal_id="G-1", description="x", harness_type="none")
        c = GoalContract(task_id="T-1", goals=[goal])
        AcceptanceGate().run(c, str(tmp_path))
        assert goal.verdict == "UNVERIFIED"

    def test_cannot_verify_not_failed(self, tmp_path):
        # INV-G: CANNOT_VERIFY → has_failures()==False, is_done() 허용
        c = GoalContract(task_id="T-1", goals=[
            GoalEntry("G-1", "x", "gui"),
        ])
        AcceptanceGate().run(c, str(tmp_path))
        assert c.goals[0].verdict == "CANNOT_VERIFY"
        assert c.has_failures() is False
        assert c.is_done() is True

    def test_multiple_goals_mixed_verdicts(self, tmp_path, monkeypatch):
        call_order = []

        def fake_run(self, goal, ws, timeout=30):
            call_order.append(goal.goal_id)
            if goal.goal_id == "G-1":
                return HarnessResult(ok=True, evidence_type="exit_code", evidence_value="0", command_run="c")
            return HarnessResult(ok=False, evidence_type="exit_code", evidence_value="1", command_run="c")

        monkeypatch.setattr(ExecutionHarness, "run", fake_run)
        c = GoalContract(task_id="T-1", goals=[
            GoalEntry("G-1", "ok", "cli", command="c"),
            GoalEntry("G-2", "fail", "cli", command="c"),
            GoalEntry("G-3", "gui", "gui"),
        ])
        AcceptanceGate().run(c, str(tmp_path))
        assert c.goals[0].verdict == "VERIFIED"
        assert c.goals[1].verdict == "FAILED"
        assert c.goals[2].verdict == "CANNOT_VERIFY"
        assert c.is_done() is False  # FAILED 있음
        assert c.has_failures() is True
