"""tests/test_approval_gate_block_decision.py — §9.5 케이스 (5) + §9.11 (1)."""
from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from core.approval_gate import ApprovalGate
from core.utils import now_iso


def _make_gate(tmp_dir: str, slug: str = "test-slug") -> ApprovalGate:
    return ApprovalGate(tmp_dir, slug, runtime_workspace=tmp_dir)


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def test_read_block_decision_no_summary():
    """#14: _summary.json 부재 → (False, None) P1 호환."""
    with tempfile.TemporaryDirectory() as tmp:
        gate = _make_gate(tmp)
        blocked, d = gate.read_block_decision()
        assert blocked is False
        assert d is None


def test_read_block_decision_no_phase_marker():
    """#15: _summary.json 존재 + escalation_phase 마커 없음 → (False, None)."""
    with tempfile.TemporaryDirectory() as tmp:
        slug_dir = os.path.join(tmp, "runtime", "warnings", "test-slug")
        os.makedirs(slug_dir)
        _write_json(os.path.join(slug_dir, "_summary.json"), {
            "project_slug": "test-slug",
            "last_updated": now_iso(),
        })
        gate = _make_gate(tmp)
        blocked, d = gate.read_block_decision()
        assert blocked is False
        assert d is None


def test_read_block_decision_missing_decision_file():
    """#16: _summary.json.escalation_phase="P2" + _decision.json 부재 → fail-closed."""
    with tempfile.TemporaryDirectory() as tmp:
        slug_dir = os.path.join(tmp, "runtime", "warnings", "test-slug")
        os.makedirs(slug_dir)
        _write_json(os.path.join(slug_dir, "_summary.json"), {
            "project_slug": "test-slug",
            "last_updated": now_iso(),
            "escalation_phase": "P2",
        })
        gate = _make_gate(tmp)
        blocked, d = gate.read_block_decision()
        assert blocked is True
        assert d is not None
        assert d["reason"] == "decision_missing"


def test_read_block_decision_phase_mismatch():
    """#17: _decision.json.escalation_phase 미래 → decision_phase_mismatch."""
    with tempfile.TemporaryDirectory() as tmp:
        slug_dir = os.path.join(tmp, "runtime", "warnings", "test-slug")
        os.makedirs(slug_dir)
        summary_ts = "2026-05-10T00:00:00+09:00"
        _write_json(os.path.join(slug_dir, "_summary.json"), {
            "project_slug": "test-slug",
            "last_updated": summary_ts,
            "escalation_phase": "P2",
        })
        _write_json(os.path.join(slug_dir, "_decision.json"), {
            "decision_schema_version": 1,
            "escalation_phase": "P3",   # 미래 phase
            "generated_from_summary_last_updated": summary_ts,
            "block": False,
            "blocking_rules": [],
            "reason": "no_active_blocks_in_run",
        })
        gate = _make_gate(tmp)
        blocked, d = gate.read_block_decision()
        assert blocked is True
        assert d["reason"] == "decision_phase_mismatch"


def test_read_block_decision_stale():
    """#18: _decision.json.generated_from_summary_last_updated 오래됨 → decision_stale."""
    with tempfile.TemporaryDirectory() as tmp:
        slug_dir = os.path.join(tmp, "runtime", "warnings", "test-slug")
        os.makedirs(slug_dir)
        old_ts = "2026-05-09T00:00:00+09:00"
        new_ts = "2026-05-10T00:00:00+09:00"
        _write_json(os.path.join(slug_dir, "_summary.json"), {
            "project_slug": "test-slug",
            "last_updated": new_ts,
            "escalation_phase": "P2",
        })
        _write_json(os.path.join(slug_dir, "_decision.json"), {
            "decision_schema_version": 1,
            "escalation_phase": "P2",
            "generated_from_summary_last_updated": old_ts,  # 이전 summary 기준
            "block": False,
            "blocking_rules": [],
            "reason": "no_active_blocks_in_run",
        })
        gate = _make_gate(tmp)
        blocked, d = gate.read_block_decision()
        assert blocked is True
        assert d["reason"] == "decision_stale"


def test_read_block_decision_phase_forward_compat():
    """#27: decision.escalation_phase=P2, summary.escalation_phase=P3 → 순방향 호환 (fail-closed 아님)."""
    with tempfile.TemporaryDirectory() as tmp:
        slug_dir = os.path.join(tmp, "runtime", "warnings", "test-slug")
        os.makedirs(slug_dir)
        ts = "2026-05-10T00:00:00+09:00"
        _write_json(os.path.join(slug_dir, "_summary.json"), {
            "project_slug": "test-slug",
            "last_updated": ts,
            "escalation_phase": "P3",  # summary는 P3
        })
        _write_json(os.path.join(slug_dir, "_decision.json"), {
            "decision_schema_version": 1,
            "escalation_phase": "P2",   # decision은 P2 (더 낮음 — 순방향 호환)
            "generated_from_summary_last_updated": ts,
            "block": False,
            "blocking_rules": [],
            "reason": "no_active_blocks_in_run",
        })
        gate = _make_gate(tmp)
        blocked, d = gate.read_block_decision()
        # 순방향 호환: fail-closed 아님
        assert blocked is False
        assert d is not None
        assert d["reason"] == "no_active_blocks_in_run"
