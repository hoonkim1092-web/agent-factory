"""tests/test_pipeline_block_enforcement.py — §9.6 케이스 (2)."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


def _make_prepared_mock(tmp_dir: str, slug: str = "test-slug") -> MagicMock:
    """fake PreparedProject 객체."""
    mock = MagicMock()
    mock.workspace = tmp_dir
    mock.work_item_slug = slug
    mock.task_board = {"tasks": []}
    mock.role_plan = {}
    mock.project_brief = {"goal": "test"}
    mock.run_id = "run-test-001"
    mock._effective_doc_root.return_value = tmp_dir
    mock._work_item_done_already.return_value = False
    return mock


def test_execute_blocked_by_escalation():
    """#19: read_block_decision → (True, {blocking_rules: ['e2e_command_missing']}) → execute() returns escalation_block."""
    from core.project_pipeline import ProjectPipeline

    with tempfile.TemporaryDirectory() as tmp:
        prepared = _make_prepared_mock(tmp)

        # gate mock: is_execution_open=True, read_block_decision=(True, {...})
        gate_mock = MagicMock()
        gate_mock.is_execution_open.return_value = True
        gate_mock.read_block_decision.return_value = (
            True,
            {"block": True, "blocking_rules": ["e2e_command_missing"], "reason": "blocked_by:e2e_command_missing"},
        )
        prepared.gate.return_value = gate_mock

        pipeline = ProjectPipeline.__new__(ProjectPipeline)

        with patch.object(pipeline, "_get_execution_mode", return_value="default", create=True):
            with patch("core.project_pipeline.sync_board_from_work_items", return_value={"tasks": []}):
                with patch("core.project_pipeline.write_project_board"):
                    result = pipeline.execute(prepared=prepared)

        assert result["ok"] is False
        assert result["reason"] == "escalation_block"
        assert "e2e_command_missing" in result["blocking_rules"]


def test_execute_passes_when_not_blocked():
    """#20 smoke: _summary.json 부재(P1 호환) → read_block_decision = (False, None) → escalation_block 없음."""
    with tempfile.TemporaryDirectory() as tmp:
        from core.approval_gate import ApprovalGate
        gate = ApprovalGate(tmp, "test-slug", runtime_workspace=tmp)

        # _summary.json 없음 → read_block_decision = (False, None)
        blocked, d = gate.read_block_decision()
        assert blocked is False
        assert d is None
