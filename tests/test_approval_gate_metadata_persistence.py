"""
Regression tests for approval-gate metadata persistence.

F2: _render() must preserve work_kind and blast_radius across state changes.
"""
from __future__ import annotations

import os
import re

import pytest

from core.approval_gate import ApprovalGate


def _seed_gate(gate_path: str, work_kind: str, blast_radius: str) -> None:
    existing = ""
    if os.path.exists(gate_path):
        with open(gate_path, encoding="utf-8") as fh:
            existing = fh.read()

    patched = re.sub(
        r"(- last_updated:.*\n)",
        rf"\1- work_kind: {work_kind}\n- blast_radius: {blast_radius}\n",
        existing,
        count=1,
    )
    with open(gate_path, "w", encoding="utf-8") as fh:
        fh.write(patched)


@pytest.fixture
def gate(tmp_path):
    workspace = tmp_path
    slug = "meta-test-item"
    g = ApprovalGate(str(workspace), slug)
    g.initialize(work_item_id="WI-META")
    return g


def test_approve_preserves_metadata(gate):
    _seed_gate(gate.gate_path, work_kind="refactor", blast_radius="system_wide")

    result = gate.approve(approver="user")
    assert result is True

    parsed = gate._parse()
    assert parsed.get("work_kind") == "refactor"
    assert parsed.get("blast_radius") == "system_wide"


def test_invalidate_preserves_metadata(gate):
    _seed_gate(gate.gate_path, work_kind="bugfix", blast_radius="module")
    gate.approve(approver="user")

    gate.invalidate(reason="document changed")

    parsed = gate._parse()
    assert parsed.get("work_kind") == "bugfix"
    assert parsed.get("blast_radius") == "module"


def test_apply_verification_verdict_preserves_metadata(gate):
    _seed_gate(gate.gate_path, work_kind="feature_update", blast_radius="cross_module")
    gate.approve(approver="user")

    gate.apply_verification_verdict("BLOCK")

    parsed = gate._parse()
    assert parsed.get("work_kind") == "feature_update"
    assert parsed.get("blast_radius") == "cross_module"


def test_no_metadata_fields_backward_compat(gate):
    result = gate.approve(approver="user")
    assert result is True

    parsed = gate._parse()
    assert not parsed.get("work_kind")
    assert not parsed.get("blast_radius")

    with open(gate.gate_path, encoding="utf-8") as fh:
        content = fh.read()
    assert "- work_kind:" not in content
    assert "- blast_radius:" not in content
