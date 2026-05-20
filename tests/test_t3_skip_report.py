from __future__ import annotations

import json

from scripts.t3_skip_report import build_report, load_records


def test_load_records_skips_invalid_json(tmp_path):
    q = tmp_path / ".af_review_queue"
    q.mkdir()
    (q / "t3_skip_telemetry.jsonl").write_text(
        json.dumps({
            "skip_reason": "cosmetic-only-python-ast",
            "classifier_version": "t3-deterministic-v1",
            "files": ["core/a.py"],
        }) + "\nnot-json\n",
        encoding="utf-8",
    )

    records = load_records(str(tmp_path))

    assert len(records) == 1
    assert records[0]["files"] == ["core/a.py"]


def test_build_report_groups_reason_version_and_files():
    report = build_report([
        {
            "skip_reason": "cosmetic-only-python-ast",
            "classifier_version": "t3-deterministic-v1",
            "files": ["core/a.py", "core/b.py"],
        },
        {
            "skip_reason": "cosmetic-only-python-ast",
            "classifier_version": "t3-deterministic-v1",
            "files": ["core/a.py"],
        },
    ])

    assert "total_skips: 2" in report
    assert "- cosmetic-only-python-ast: 2" in report
    assert "- t3-deterministic-v1: 2" in report
    assert "- core/a.py: 2" in report
