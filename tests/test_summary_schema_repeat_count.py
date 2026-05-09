"""tests/test_summary_schema_repeat_count.py — §9.3 케이스 (1)."""
from __future__ import annotations

import json
import os
import tempfile

from core.warning_registry import WarningRegistry


def test_build_summary_schema_with_repeat_count_max_and_any_override(tmp_path):
    """#10: _build_summary 산출 dict = {count, first_ts, last_ts, severity, by_phase, repeat_count_max, any_override}."""
    slug = "test-slug"
    ws = str(tmp_path)

    # seed jsonl
    slug_dir = tmp_path / "runtime" / "warnings" / slug
    slug_dir.mkdir(parents=True)
    records = [
        {
            "rule_id": "e2e_command_missing",
            "severity": "warn",
            "project_slug": slug,
            "ts": "2026-05-09T00:00:00+09:00",
            "record_id": f"{slug}:e2e_command_missing:aaa11111",
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
        },
        {
            "rule_id": "e2e_command_missing",
            "severity": "warn",
            "project_slug": slug,
            "ts": "2026-05-10T00:00:00+09:00",
            "record_id": f"{slug}:e2e_command_missing:bbb22222",
            "affected_phase": "verify",
            "count": 3,
            "repeat_count": 2,
            "baseline_delta": 0.0,
            "false_positive_override": False,
            "rationale": "test",
            "affected_ids": [],
            "source_path": "test",
            "extra": {},
            "schema_version": 1,
        },
    ]
    with open(slug_dir / "e2e_command_missing.jsonl", "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    summary = WarningRegistry(ws).summarize(project_slug=slug)
    entry = summary["by_rule"]["e2e_command_missing"]

    required_keys = {"count", "first_ts", "last_ts", "severity", "by_phase", "repeat_count_max", "any_override"}
    missing = required_keys - set(entry.keys())
    assert not missing, f"누락된 키: {missing}"

    assert entry["count"] == 8
    assert entry["repeat_count_max"] == 2
    assert entry["any_override"] is False
    assert "build" in entry["by_phase"]
    assert "verify" in entry["by_phase"]
