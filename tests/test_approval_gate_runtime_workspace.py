"""tests/test_approval_gate_runtime_workspace.py — ApprovalGate runtime_workspace 3 케이스."""
from __future__ import annotations

import re
import os

import pytest

from core.approval_gate import ApprovalGate


# ---------------------------------------------------------------------------
# 1. single mode — runtime_workspace 미지정 시 workspace와 동일
# ---------------------------------------------------------------------------

def test_single_mode_runtime_workspace_defaults_to_workspace(tmp_path):
    gate = ApprovalGate(workspace=str(tmp_path), slug="test-slug")
    assert gate.runtime_workspace == str(tmp_path)


# ---------------------------------------------------------------------------
# 2. 분리 mode — runtime_workspace 명시 시 별도 경로
# ---------------------------------------------------------------------------

def test_split_mode_runtime_workspace(tmp_path):
    doc_root = tmp_path / "doc_root"
    runtime_ws = tmp_path / "runtime_ws"
    doc_root.mkdir()
    runtime_ws.mkdir()

    gate = ApprovalGate(
        workspace=str(doc_root),
        slug="test-slug",
        runtime_workspace=str(runtime_ws),
    )
    assert gate.workspace == str(doc_root)
    assert gate.runtime_workspace == str(runtime_ws)
    assert gate.workspace != gate.runtime_workspace


# ---------------------------------------------------------------------------
# 3. _render 정규식 회귀 — gate_decision_report 라인 주입 확인
# ---------------------------------------------------------------------------

def test_render_injects_gate_decision_report(tmp_path):
    gate = ApprovalGate(workspace=str(tmp_path), slug="test-slug")
    gate.initialize("work-item-001")

    content = open(gate.gate_path, encoding="utf-8").read()
    assert "gate_decision_report:" in content
    # 절대경로 포함 확인
    expected_path = os.path.join(str(tmp_path), "runtime", "warnings", "test-slug", "_decision.md")
    assert expected_path in content

    # 기존 5섹션 정규식이 깨지지 않는지 — _parse() 성공 여부
    parsed = gate._parse()
    assert "work_item" in parsed
    assert "status" in parsed


# ---------------------------------------------------------------------------
# 보너스: 기존 keyword arg 호출 호환성 (test_t3_7_run_event_integration.py:96 패턴)
# ---------------------------------------------------------------------------

def test_keyword_arg_backward_compat(tmp_path):
    gate = ApprovalGate(workspace=str(tmp_path), slug="test-slug")
    assert gate.workspace == str(tmp_path)
