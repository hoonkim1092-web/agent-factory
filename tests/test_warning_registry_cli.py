"""tests/test_warning_registry_cli.py — CLI 서브커맨드 4 케이스."""
from __future__ import annotations

import json
import sys
import os

import pytest


# ---------------------------------------------------------------------------
# 1. --workspace 누락 시 argparse error (SystemExit 2)
# ---------------------------------------------------------------------------

def test_warning_summary_missing_workspace(capsys):
    from run_factory_cli import _run_warning_summary_subcommand
    with pytest.raises(SystemExit) as exc:
        _run_warning_summary_subcommand(["--slug", "test"])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# 2. warning-repair — _summary.json 재생성
# ---------------------------------------------------------------------------

def test_warning_repair_rebuilds_summary(tmp_path, capsys):
    from core.warning_registry import WarningRegistry
    from run_factory_cli import _run_warning_repair_subcommand

    wr = WarningRegistry(workspace=str(tmp_path))
    wr.record(project_slug="proj", rule_id="e2e_command_missing", count=7)

    # summary 없는 상태에서 repair 실행
    _run_warning_repair_subcommand(["--workspace", str(tmp_path), "--slug", "proj"])

    summary_path = tmp_path / "runtime" / "warnings" / "proj" / "_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text())
    assert summary["by_rule"]["e2e_command_missing"]["count"] == 7
    captured = capsys.readouterr()
    assert "rebuilt" in captured.out


# ---------------------------------------------------------------------------
# 3. frozen subcommand wiring — _STAGE1_DISPATCH에 등록 확인
# ---------------------------------------------------------------------------

def test_warning_subcommands_in_dispatch():
    from run_factory_cli import _STAGE1_DISPATCH
    assert "warning-summary" in _STAGE1_DISPATCH
    assert "warning-repair" in _STAGE1_DISPATCH


# ---------------------------------------------------------------------------
# 4. dedup idempotent — warning-summary 2회 호출해도 동일 결과
# ---------------------------------------------------------------------------

def test_warning_summary_dedup_idempotent(tmp_path, capsys):
    from core.warning_registry import WarningRegistry
    from run_factory_cli import _run_warning_summary_subcommand

    wr = WarningRegistry(workspace=str(tmp_path))
    wr.record(project_slug="proj", rule_id="owner_role_mismatch", count=1)
    wr.record(project_slug="proj", rule_id="owner_role_mismatch", count=1)  # dedup

    _run_warning_summary_subcommand(["--workspace", str(tmp_path), "--slug", "proj"])
    out1 = capsys.readouterr().out

    _run_warning_summary_subcommand(["--workspace", str(tmp_path), "--slug", "proj"])
    out2 = capsys.readouterr().out

    d1 = json.loads(out1)
    d2 = json.loads(out2)
    # last_updated 제외하고 동일해야 함
    d1.pop("last_updated", None)
    d2.pop("last_updated", None)
    assert d1 == d2
    # dedup으로 1건만 기록
    assert d1["by_rule"]["owner_role_mismatch"]["count"] == 1
