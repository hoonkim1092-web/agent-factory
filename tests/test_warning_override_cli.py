"""tests/test_warning_override_cli.py — §9.9 케이스 (2)."""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest


def _run_cli(args: list[str]) -> int:
    """_run_warning_override_subcommand를 직접 호출."""
    from run_factory_cli import _run_warning_override_subcommand
    _run_warning_override_subcommand(args)
    return 0


def test_warning_override_add_and_summary(tmp_path):
    """#24: add override → _overrides.json 생성, summary any_override=true, decision block=False."""
    slug = "test-slug"
    ws = str(tmp_path)
    # jsonl seed 먼저 작성
    slug_dir = tmp_path / "runtime" / "warnings" / slug
    slug_dir.mkdir(parents=True)
    record = {
        "rule_id": "e2e_command_missing",
        "severity": "warn",
        "project_slug": slug,
        "ts": "2026-05-10T00:00:00+09:00",
        "record_id": f"{slug}:e2e_command_missing:abc12345",
        "affected_phase": "build",
        "count": 5,
        "repeat_count": 1,
        "baseline_delta": 0.0,
        "false_positive_override": False,
        "rationale": "test",
        "affected_ids": [],
        "source_path": "test",
        "extra": {},
        "schema_version": 1,
    }
    import json
    (slug_dir / "e2e_command_missing.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )

    _run_cli([
        "--workspace", ws,
        "--slug", slug,
        "--rule", "e2e_command_missing",
        "--reason", "prototype phase — will fix later",
    ])

    overrides_path = slug_dir / "_overrides.json"
    assert overrides_path.exists()
    with open(overrides_path, encoding="utf-8") as fh:
        ov = json.load(fh)
    assert any(e["rule_id"] == "e2e_command_missing" for e in ov["overrides"])

    summary_path = slug_dir / "_summary.json"
    assert summary_path.exists()
    with open(summary_path, encoding="utf-8") as fh:
        s = json.load(fh)
    assert s["by_rule"]["e2e_command_missing"]["any_override"] is True

    decision_path = slug_dir / "_decision.json"
    assert decision_path.exists()
    with open(decision_path, encoding="utf-8") as fh:
        d = json.load(fh)
    assert d["block"] is False


def test_warning_override_remove_restores_block(tmp_path):
    """#25: override 제거 → any_override=false, decision block=True 복귀."""
    slug = "test-slug"
    ws = str(tmp_path)
    slug_dir = tmp_path / "runtime" / "warnings" / slug
    slug_dir.mkdir(parents=True)

    import json
    record = {
        "rule_id": "e2e_command_missing",
        "severity": "warn",
        "project_slug": slug,
        "ts": "2026-05-10T00:00:00+09:00",
        "record_id": f"{slug}:e2e_command_missing:abc12345",
        "affected_phase": "build",
        "count": 5,
        "repeat_count": 1,
        "baseline_delta": 0.0,
        "false_positive_override": False,
        "rationale": "test",
        "affected_ids": [],
        "source_path": "test",
        "extra": {},
        "schema_version": 1,
    }
    (slug_dir / "e2e_command_missing.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )

    # add first
    _run_cli([
        "--workspace", ws, "--slug", slug,
        "--rule", "e2e_command_missing",
        "--reason", "test override",
    ])

    # remove
    _run_cli([
        "--workspace", ws, "--slug", slug,
        "--rule", "e2e_command_missing",
        "--remove",
    ])

    summary_path = slug_dir / "_summary.json"
    with open(summary_path, encoding="utf-8") as fh:
        s = json.load(fh)
    assert s["by_rule"]["e2e_command_missing"]["any_override"] is False

    decision_path = slug_dir / "_decision.json"
    with open(decision_path, encoding="utf-8") as fh:
        d = json.load(fh)
    assert d["block"] is True


def test_dispatch_dict_has_warning_override():
    """dispatch dict wiring 확인."""
    from run_factory_cli import _STAGE1_DISPATCH, _run_warning_override_subcommand
    assert "warning-override" in _STAGE1_DISPATCH
    assert _STAGE1_DISPATCH["warning-override"] is _run_warning_override_subcommand
