"""tests/test_warning_stats.py — core/warning_stats.py 7 케이스."""
from __future__ import annotations

import json
import os

import pytest

from core.warning_stats import collect_workspace_stats, iter_warning_records, _validate_slug


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_jsonl(slug_dir: str, rule_id: str, records: list[dict]) -> None:
    os.makedirs(slug_dir, exist_ok=True)
    path = os.path.join(slug_dir, f"{rule_id}.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _warnings_dir(tmp_path, slug: str) -> str:
    return str(tmp_path / "runtime" / "warnings" / slug)


def _make_record(count: int = 1, phase: str = "build", ts: str = "", **extra) -> dict:
    r = {"rule_id": "owner_role_mismatch", "count": count, "affected_phase": phase}
    if ts:
        r["ts"] = ts
    r.update(extra)
    return r


# ---------------------------------------------------------------------------
# 1. empty_workspace
# ---------------------------------------------------------------------------

def test_empty_workspace(tmp_path):
    result = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch")
    assert result["scanned_slug_count"] == 0
    assert result["distribution"] is None
    assert result["projects"] == []
    assert result["applied_filters"] == {"slug": None, "phase": None}
    assert any("no slug directories" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# 2. single_slug_single_record
# ---------------------------------------------------------------------------

def test_single_slug_single_record(tmp_path):
    slug_dir = _warnings_dir(tmp_path, "proj-a")
    _write_jsonl(slug_dir, "owner_role_mismatch", [_make_record(count=3)])

    result = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch")
    assert result["scanned_slug_count"] == 1
    assert result["project_count_total"] == 1
    assert len(result["projects"]) == 1

    proj = result["projects"][0]
    assert proj["count"] == 3
    assert proj["record_lines"] == 1
    assert proj["repeat_count_max"] == 3

    dist = result["distribution"]
    assert dist is not None
    bpc = dist["by_project_count"]
    assert bpc["n"] == 1
    assert bpc["min"] == bpc["max"] == bpc["p95"] == 3
    assert bpc["median"] == 3.0  # float 강제

    bpr = dist["by_per_record_count"]
    assert bpr["n"] == 1
    assert bpr["min"] == bpr["max"] == 3


# ---------------------------------------------------------------------------
# 3. multi_slug_distribution
# ---------------------------------------------------------------------------

def test_multi_slug_distribution(tmp_path):
    counts = [1, 2, 3, 5, 8]
    for i, cnt in enumerate(counts):
        slug_dir = _warnings_dir(tmp_path, f"proj-{i}")
        _write_jsonl(slug_dir, "owner_role_mismatch", [_make_record(count=cnt)])

    result = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch")
    assert result["project_count_total"] == 5

    bpc = result["distribution"]["by_project_count"]
    assert bpc["n"] == 5
    assert bpc["min"] == 1
    assert bpc["max"] == 8
    assert bpc["median"] == 3.0  # float
    # p95: ceil(0.95 * 5) - 1 = ceil(4.75) - 1 = 5 - 1 = 4 → sorted[4] = 8
    assert bpc["p95"] == 8

    # by_per_record_count: record 수 = 5 (한 slug당 1 record)
    bpr = result["distribution"]["by_per_record_count"]
    assert bpr["n"] == 5


# ---------------------------------------------------------------------------
# 4. rule_filter
# ---------------------------------------------------------------------------

def test_rule_filter(tmp_path):
    slug_dir = _warnings_dir(tmp_path, "proj-x")
    _write_jsonl(slug_dir, "owner_role_mismatch", [_make_record(count=5)])
    _write_jsonl(slug_dir, "e2e_command_missing", [_make_record(count=99)])

    result = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch")
    assert result["totals"]["count"] == 5
    assert result["projects"][0]["count"] == 5


# ---------------------------------------------------------------------------
# 5. phase_filter_record_level
# ---------------------------------------------------------------------------

def test_phase_filter_record_level(tmp_path):
    slug_dir = _warnings_dir(tmp_path, "proj-p")
    records = [
        _make_record(count=2, phase="build"),
        _make_record(count=3, phase="build"),
        _make_record(count=4, phase="verify"),
        _make_record(count=1, phase="verify"),
        _make_record(count=6, phase="build"),
    ]
    _write_jsonl(slug_dir, "owner_role_mismatch", records)

    result = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch", phase="build")

    assert result["applied_filters"]["phase"] == "build"
    assert result["totals"]["count"] == 2 + 3 + 6  # build only
    assert result["by_phase_total"] == {"build": 11}
    assert result["by_phase_total_unfiltered"]["build"] == 11
    assert result["by_phase_total_unfiltered"]["verify"] == 5
    assert result["distribution"]["by_per_record_count"]["n"] == 3  # build record 3개

    # 빈 결과 case: phase=scope → 매칭 0건
    result_empty = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch", phase="scope")
    assert result_empty["by_phase_total"] == {}
    assert result_empty["by_phase_total_unfiltered"]["build"] == 11
    assert result_empty["distribution"] is None


# ---------------------------------------------------------------------------
# 6. malformed_jsonl_skip_warnings_sot
# ---------------------------------------------------------------------------

def test_malformed_jsonl_skip_warnings_sot(tmp_path):
    slug_dir = _warnings_dir(tmp_path, "proj-m")
    os.makedirs(slug_dir, exist_ok=True)
    jsonl_path = os.path.join(slug_dir, "owner_role_mismatch.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(_make_record(count=1)) + "\n")
        fh.write("{broken json\n")
        fh.write(json.dumps(_make_record(count=2)) + "\n")

    # 메타파일 (자동 필터 검증용)
    (tmp_path / "runtime" / "warnings" / "_index.json").write_text("{}", encoding="utf-8")
    (tmp_path / "runtime" / "warnings" / "_summary.json").write_text("{}", encoding="utf-8")

    result = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch")

    assert result["totals"]["count"] == 3  # 1 + 2, 깨진 라인 skip
    assert result["totals"]["record_lines"] == 2

    malformed_warnings = [w for w in result["warnings"] if "malformed line" in w]
    assert len(malformed_warnings) == 1
    assert "proj-m/owner_role_mismatch.jsonl:2" in malformed_warnings[0]

    # _index.json, _summary.json은 스캔 대상 아님 (not startswith("_") 필터)
    assert result["scanned_slug_count"] == 1  # proj-m만


# ---------------------------------------------------------------------------
# 7. slug_filter_core_with_traversal_guard
# ---------------------------------------------------------------------------

def test_slug_filter_core_with_traversal_guard(tmp_path):
    slug_dir = _warnings_dir(tmp_path, "proj-s")
    _write_jsonl(slug_dir, "owner_role_mismatch", [_make_record(count=7)])

    # slug 필터 — 존재하는 slug
    result = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch", slug="proj-s")
    assert result["scanned_slug_count"] == 1
    assert result["applied_filters"]["slug"] == "proj-s"
    assert result["totals"]["count"] == 7

    # slug 필터 — 없는 slug
    result_missing = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch", slug="no-such")
    assert result_missing["scanned_slug_count"] == 0
    assert any("no-such" in w for w in result_missing["warnings"])

    # slug=None → fan-out
    result_all = collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch", slug=None)
    assert result_all["scanned_slug_count"] == 1

    # path traversal 거부
    for bad_slug in ["../../etc", "a/b", "", ".."]:
        with pytest.raises(ValueError):
            collect_workspace_stats(str(tmp_path), rule_id="owner_role_mismatch", slug=bad_slug)

    # _validate_slug 직접 검증
    with pytest.raises(ValueError):
        _validate_slug("a/b")
    with pytest.raises(ValueError):
        _validate_slug("")
    with pytest.raises(ValueError):
        _validate_slug("../../etc")
    _validate_slug("valid-slug-123")  # 정상 통과
