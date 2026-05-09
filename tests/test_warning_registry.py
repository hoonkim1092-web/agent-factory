"""tests/test_warning_registry.py — WarningRegistry 핵심 8 케이스."""
from __future__ import annotations

import json
import os
import threading

import pytest

from core.warning_registry import WarningRegistry, _normalize_phase


# ---------------------------------------------------------------------------
# 1. record — SoT append
# ---------------------------------------------------------------------------

def test_record_creates_jsonl(tmp_path):
    wr = WarningRegistry(workspace=str(tmp_path))
    wr.record(project_slug="proj", rule_id="e2e_command_missing", count=3)
    jsonl = tmp_path / "runtime" / "warnings" / "proj" / "e2e_command_missing.jsonl"
    assert jsonl.exists()
    records = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
    assert len(records) == 1
    r = records[0]
    assert r["rule_id"] == "e2e_command_missing"
    assert r["count"] == 3
    assert r["severity"] == "warn"
    assert r["project_slug"] == "proj"
    assert "record_id" in r
    assert "ts" in r


# ---------------------------------------------------------------------------
# 2. summarize — by_phase 분포 출력
# ---------------------------------------------------------------------------

def test_summarize_by_phase(tmp_path):
    wr = WarningRegistry(workspace=str(tmp_path))
    wr.record(project_slug="proj", rule_id="e2e_command_missing", affected_phase="build", count=16)
    wr.record(project_slug="proj", rule_id="e2e_command_missing", affected_phase="scope", count=5)
    summary = wr.summarize(project_slug="proj")
    assert summary["project_slug"] == "proj"
    by_phase = summary["by_rule"]["e2e_command_missing"]["by_phase"]
    assert by_phase.get("build") == 16
    assert by_phase.get("scope") == 5
    assert summary["by_severity"]["warn"] == 21


# ---------------------------------------------------------------------------
# 3. lock — 동시 append 직렬화 (IOError 격리 포함)
# ---------------------------------------------------------------------------

def test_concurrent_record(tmp_path):
    wr = WarningRegistry(workspace=str(tmp_path))
    errors = []

    def _record(idx: int):
        try:
            # count를 달리해 각 record의 stable_payload가 다르게 (dedup 방지)
            wr.record(project_slug="proj", rule_id="test_rule", affected_phase="build", count=idx + 1)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_record, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    jsonl = tmp_path / "runtime" / "warnings" / "proj" / "test_rule.jsonl"
    records = [l for l in jsonl.read_text().splitlines() if l.strip()]
    assert len(records) == 10


# ---------------------------------------------------------------------------
# 4. IOError 격리 — workspace 없을 때 record()가 ValueError (explicit workspace 필수)
# ---------------------------------------------------------------------------

def test_registry_requires_workspace():
    with pytest.raises(ValueError, match="explicit workspace"):
        WarningRegistry(workspace="")


# ---------------------------------------------------------------------------
# 5. record_id idempotency — 동일 payload 2회 → SoT 1라인
# ---------------------------------------------------------------------------

def test_record_id_idempotency(tmp_path):
    wr = WarningRegistry(workspace=str(tmp_path))
    wr.record(project_slug="proj", rule_id="e2e_command_missing", count=5, affected_phase="build")
    wr.record(project_slug="proj", rule_id="e2e_command_missing", count=5, affected_phase="build")
    jsonl = tmp_path / "runtime" / "warnings" / "proj" / "e2e_command_missing.jsonl"
    lines = [l for l in jsonl.read_text().splitlines() if l.strip()]
    assert len(lines) == 1  # dedup


# ---------------------------------------------------------------------------
# 6. phase 정규화 — alias 및 unknown fallback
# ---------------------------------------------------------------------------

def test_normalize_phase_alias():
    canon, orig = _normalize_phase("design")
    assert canon == "scope"
    assert orig == "design"

def test_normalize_phase_unknown():
    canon, orig = _normalize_phase("unknown_xyz")
    assert canon == "build"
    assert orig == "unknown_xyz"

def test_normalize_phase_canonical():
    canon, orig = _normalize_phase("integrate")
    assert canon == "integrate"
    assert orig is None

def test_normalize_phase_empty():
    canon, orig = _normalize_phase("")
    assert canon == ""
    assert orig is None


# ---------------------------------------------------------------------------
# 7. repeat_count persist — 다른 payload 호출 시 repeat_count 증가
# ---------------------------------------------------------------------------

def test_repeat_count_persists(tmp_path):
    wr = WarningRegistry(workspace=str(tmp_path))
    wr.record(project_slug="proj", rule_id="e2e_command_missing", count=3, affected_phase="build")
    wr.record(project_slug="proj", rule_id="e2e_command_missing", count=5, affected_phase="scope")
    jsonl = tmp_path / "runtime" / "warnings" / "proj" / "e2e_command_missing.jsonl"
    lines = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    assert lines[0]["repeat_count"] == 1
    assert lines[1]["repeat_count"] == 2


# ---------------------------------------------------------------------------
# 8. atomic write — _summary.json 최종 정합
# ---------------------------------------------------------------------------

def test_summarize_atomic_write(tmp_path):
    wr = WarningRegistry(workspace=str(tmp_path))
    wr.record(project_slug="proj", rule_id="owner_role_mismatch", count=2)
    summary = wr.summarize(project_slug="proj")
    summary_path = tmp_path / "runtime" / "warnings" / "proj" / "_summary.json"
    assert summary_path.exists()
    on_disk = json.loads(summary_path.read_text())
    assert on_disk["by_rule"]["owner_role_mismatch"]["count"] == 2
    # tmp 파일이 남지 않아야 함
    tmp_files = list((tmp_path / "runtime" / "warnings" / "proj").glob("*.tmp"))
    assert tmp_files == []
