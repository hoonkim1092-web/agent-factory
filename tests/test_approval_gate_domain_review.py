"""
Regression tests for Domain Gate Phase A identifiers.

F1: approval_gate.py must not use invalid blast_radius tokens.
Valid tokens are: {"isolated", "module", "cross_module", "system_wide"}.
Invalid historical tokens include standalone "local" and "system".
"""
from __future__ import annotations

import os
import re


_GATE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "core", "approval_gate.py"
)


def _read_source() -> str:
    with open(_GATE_FILE, encoding="utf-8") as fh:
        return fh.read()


def test_no_invalid_blast_radius_local_token():
    source = _read_source()
    matches = [
        (i + 1, line)
        for i, line in enumerate(source.splitlines())
        if re.search(r'["\']local["\']', line)
    ]
    assert matches == [], (
        'core/approval_gate.py contains invalid blast_radius token "local":\n'
        + "\n".join(f"  line {ln}: {txt}" for ln, txt in matches)
    )


def test_no_invalid_blast_radius_system_token():
    source = _read_source()
    matches = [
        (i + 1, line)
        for i, line in enumerate(source.splitlines())
        if re.search(r'["\']system["\']', line)
    ]
    assert matches == [], (
        'core/approval_gate.py contains invalid blast_radius token "system":\n'
        + "\n".join(f"  line {ln}: {txt}" for ln, txt in matches)
    )
