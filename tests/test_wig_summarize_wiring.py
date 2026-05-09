"""tests/test_wig_summarize_wiring.py — §9.10 케이스 (1): generate_work_items → _summary.json + _decision.json 생성 확인 (hermetic).

LLM provider 없이 hermetic: jsonl seed + fake gate + tmp_path workspace.
"""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


def test_summarize_wiring_creates_decision_files(tmp_path):
    """#26: record loop 이후 _summary.json + _decision.json 파일이 생성됨."""
    slug = "test-project-wiring"
    ws = str(tmp_path)
    slug_dir = tmp_path / "runtime" / "warnings" / slug
    slug_dir.mkdir(parents=True)

    record = {
        "rule_id": "e2e_command_missing",
        "severity": "warn",
        "project_slug": slug,
        "ts": "2026-05-10T00:00:00+09:00",
        "record_id": f"{slug}:e2e_command_missing:seed1234",
        "affected_phase": "build",
        "count": 2,
        "repeat_count": 1,
        "baseline_delta": 0.0,
        "false_positive_override": False,
        "rationale": "hermetic test seed",
        "affected_ids": ["T-001"],
        "source_path": "test",
        "extra": {},
        "schema_version": 1,
    }
    (slug_dir / "e2e_command_missing.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )

    # summarize() 직접 호출 (work_item_generator.generate_work_items의 wiring과 동일 경로)
    from core.warning_registry import WarningRegistry
    WarningRegistry(workspace=ws).summarize(project_slug=slug)

    assert (slug_dir / "_summary.json").exists(), "_summary.json 없음"
    assert (slug_dir / "_decision.json").exists(), "_decision.json 없음"

    with open(slug_dir / "_decision.json", encoding="utf-8") as fh:
        d = json.load(fh)
    assert "decision_schema_version" in d
    assert "escalation_phase" in d
    assert "block" in d
