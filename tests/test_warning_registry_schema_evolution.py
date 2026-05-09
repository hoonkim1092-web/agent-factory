"""tests/test_warning_registry_schema_evolution.py — schema round-trip 1 케이스."""
from __future__ import annotations

import json
import os


def test_schema_round_trip(tmp_path):
    """v1 record에 v2 신규 필드 추가 후 round-trip — 기존 record 파싱 성공."""
    from core.warning_registry import WarningRegistry

    wr = WarningRegistry(workspace=str(tmp_path))
    wr.record(
        project_slug="proj",
        rule_id="e2e_command_missing",
        count=1,
        affected_phase="build",
    )

    # 수동으로 jsonl에 v0.2 스타일 레코드 (신규 필드 포함) 추가
    jsonl = tmp_path / "runtime" / "warnings" / "proj" / "e2e_command_missing.jsonl"
    with open(jsonl, "a", encoding="utf-8") as fh:
        new_record = {
            "rule_id": "e2e_command_missing",
            "severity": "warn",
            "project_slug": "proj",
            "ts": "2026-05-09T00:00:00+09:00",
            "record_id": "proj:e2e_command_missing:abcd1234",
            "schema_version": 2,
            "affected_phase": "integrate",
            "count": 3,
            "repeat_count": 2,
            "baseline_delta": 0.0,
            "false_positive_override": False,
            "rationale": "",
            "affected_ids": [],
            "source_path": "",
            "extra": {},
            "new_v2_field": "some_value",  # 신규 필드 — extra로 흡수되어야 함
        }
        fh.write(json.dumps(new_record) + "\n")

    # summarize가 두 레코드를 정상 파싱하는지 확인
    summary = wr.summarize(project_slug="proj")
    assert summary["by_rule"]["e2e_command_missing"]["count"] == 4  # 1 + 3
    assert summary["by_rule"]["e2e_command_missing"]["by_phase"].get("build") == 1
    assert summary["by_rule"]["e2e_command_missing"]["by_phase"].get("integrate") == 3
