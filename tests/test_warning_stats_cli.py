"""tests/test_warning_stats_cli.py — run_factory_cli warning-stats/export CLI 9 케이스."""
from __future__ import annotations

import csv
import json
import os
import sys

import pytest


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


def _make_record(count: int = 1, phase: str = "build", **extra) -> dict:
    r = {"rule_id": "owner_role_mismatch", "count": count, "affected_phase": phase}
    r.update(extra)
    return r


def _run_cli(argv: list[str], capsys) -> tuple[int, str, str]:
    """run_factory_cli main()을 직접 호출해 (exit_code, stdout, stderr) 반환."""
    import importlib
    import io
    cli = importlib.import_module("run_factory_cli")
    old_argv = sys.argv
    sys.argv = ["af"] + argv
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = captured_out
    sys.stderr = captured_err
    exit_code = 0
    try:
        cli.main()
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        sys.argv = old_argv
    return exit_code, captured_out.getvalue(), captured_err.getvalue()


# ---------------------------------------------------------------------------
# 8. cli_workspace_required
# ---------------------------------------------------------------------------

def test_cli_workspace_required(tmp_path, capsys):
    code, out, err = _run_cli(["warning-stats"], capsys)
    assert code == 2
    assert "required" in err.lower()


# ---------------------------------------------------------------------------
# 9. cli_top_truncation_meta
# ---------------------------------------------------------------------------

def test_cli_top_truncation_meta(tmp_path, capsys):
    counts = [10, 5, 3, 2, 1]
    for i, cnt in enumerate(counts):
        slug_dir = _warnings_dir(tmp_path, f"proj-{i}")
        _write_jsonl(slug_dir, "owner_role_mismatch", [_make_record(count=cnt)])

    code, out, err = _run_cli(
        ["warning-stats", "--workspace", str(tmp_path), "--top", "2"],
        capsys,
    )
    assert code == 0
    result = json.loads(out)
    assert len(result["projects"]) == 2
    assert result["project_count_returned"] == 2
    assert result["project_count_total"] == 5
    # totals/distribution는 full population
    assert result["totals"]["count"] == sum(counts)
    assert result["distribution"]["by_project_count"]["n"] == 5

    # --top 0 → 전체
    code2, out2, _ = _run_cli(
        ["warning-stats", "--workspace", str(tmp_path), "--top", "0"],
        capsys,
    )
    assert code2 == 0
    result2 = json.loads(out2)
    assert result2["project_count_total"] == result2["project_count_returned"] == 5


# ---------------------------------------------------------------------------
# 10. cli_export_csv_affected_ids_json
# ---------------------------------------------------------------------------

def test_cli_export_csv_affected_ids_json(tmp_path, capsys):
    slug_dir = _warnings_dir(tmp_path, "proj-ids")
    affected = ["task_a", "task;b", "task,c"]
    record = _make_record(count=1, affected_ids=affected)
    _write_jsonl(slug_dir, "owner_role_mismatch", [record])

    code, out, err = _run_cli(
        ["warning-export", "--workspace", str(tmp_path), "--format", "csv"],
        capsys,
    )
    assert code == 0

    import io
    reader = csv.DictReader(io.StringIO(out))
    rows = list(reader)
    assert len(rows) == 1
    cell = rows[0]["affected_ids"]
    # json.dumps 결과여야 함
    parsed = json.loads(cell)
    assert parsed == affected


# ---------------------------------------------------------------------------
# 11. cli_export_json_records_format
# ---------------------------------------------------------------------------

def test_cli_export_json_records_format(tmp_path, capsys):
    slug_dir = _warnings_dir(tmp_path, "proj-jr")
    _write_jsonl(slug_dir, "owner_role_mismatch", [
        _make_record(count=2),
        _make_record(count=3),
    ])

    code, out, err = _run_cli(
        ["warning-export", "--workspace", str(tmp_path), "--format", "json", "--mode", "records"],
        capsys,
    )
    assert code == 0
    payload = json.loads(out)
    for key in ("schema_version", "rule_id", "workspace", "applied_filters",
                "exported_at", "scanned_slug_count", "record_count", "records", "warnings"):
        assert key in payload, f"missing key: {key}"
    assert payload["record_count"] == len(payload["records"])
    assert payload["record_count"] == 2
    # records 각 항목 구조
    for item in payload["records"]:
        assert "project_slug" in item
        assert "record" in item


# ---------------------------------------------------------------------------
# 12. cli_export_summary_csv_rejected
# ---------------------------------------------------------------------------

def test_cli_export_summary_csv_rejected(tmp_path, capsys):
    code, out, err = _run_cli(
        ["warning-export", "--workspace", str(tmp_path), "--format", "csv", "--mode", "summary"],
        capsys,
    )
    assert code == 2
    assert "summary mode is incompatible with csv format" in err


# ---------------------------------------------------------------------------
# 13. cli_slug_filter_and_sanitization
# ---------------------------------------------------------------------------

def test_cli_slug_filter_and_sanitization(tmp_path, capsys):
    slug_dir = _warnings_dir(tmp_path, "proj-slug")
    _write_jsonl(slug_dir, "owner_role_mismatch", [_make_record(count=5)])

    # 존재하는 slug
    code, out, _ = _run_cli(
        ["warning-stats", "--workspace", str(tmp_path), "--slug", "proj-slug"],
        capsys,
    )
    assert code == 0
    result = json.loads(out)
    assert result["applied_filters"]["slug"] == "proj-slug"
    assert result["scanned_slug_count"] == 1

    # 없는 slug
    code2, out2, _ = _run_cli(
        ["warning-stats", "--workspace", str(tmp_path), "--slug", "no-such-slug"],
        capsys,
    )
    assert code2 == 0
    result2 = json.loads(out2)
    assert result2["scanned_slug_count"] == 0
    assert any("no-such-slug" in w for w in result2["warnings"])

    # path traversal → argparse error
    for bad in ["../../etc", "a/b", ""]:
        code_bad, _, err_bad = _run_cli(
            ["warning-stats", "--workspace", str(tmp_path), "--slug", bad],
            capsys,
        )
        assert code_bad == 2, f"expected exit 2 for slug={bad!r}, got {code_bad}"


# ---------------------------------------------------------------------------
# 14. cli_export_phase_filter
# ---------------------------------------------------------------------------

def test_cli_export_phase_filter(tmp_path, capsys):
    slug_dir = _warnings_dir(tmp_path, "proj-phase")
    _write_jsonl(slug_dir, "owner_role_mismatch", [
        _make_record(count=2, phase="build"),
        _make_record(count=3, phase="verify"),
    ])

    code, out, _ = _run_cli(
        ["warning-export", "--workspace", str(tmp_path),
         "--format", "json", "--mode", "summary", "--phase", "build"],
        capsys,
    )
    assert code == 0
    result = json.loads(out)
    assert result["applied_filters"]["phase"] == "build"
    assert result["totals"]["count"] == 2  # build only

    # --phase 미지정 시 모든 phase
    code2, out2, _ = _run_cli(
        ["warning-export", "--workspace", str(tmp_path),
         "--format", "json", "--mode", "summary"],
        capsys,
    )
    assert code2 == 0
    result2 = json.loads(out2)
    assert result2["totals"]["count"] == 5  # build + verify


# ---------------------------------------------------------------------------
# 15. cli_export_out_atomic
# ---------------------------------------------------------------------------

def test_cli_export_out_atomic(tmp_path, capsys):
    slug_dir = _warnings_dir(tmp_path, "proj-atomic")
    _write_jsonl(slug_dir, "owner_role_mismatch", [_make_record(count=1)])
    out_file = str(tmp_path / "out.csv")

    code, out, err = _run_cli(
        ["warning-export", "--workspace", str(tmp_path),
         "--format", "csv", "--out", out_file],
        capsys,
    )
    assert code == 0
    assert os.path.isfile(out_file)
    # temp 파일 잔존 없음
    parent = os.path.dirname(out_file)
    tmp_files = [f for f in os.listdir(parent) if f.endswith(f".tmp.{os.getpid()}")]
    assert tmp_files == []

    # 권한 없는 디렉토리 → nonzero exit
    locked_dir = tmp_path / "locked"
    locked_dir.mkdir()
    locked_dir.chmod(0o000)
    locked_out = str(locked_dir / "out.csv")
    try:
        code_fail, _, err_fail = _run_cli(
            ["warning-export", "--workspace", str(tmp_path),
             "--format", "csv", "--out", locked_out],
            capsys,
        )
        assert code_fail != 0
        assert "write failed" in err_fail
    finally:
        locked_dir.chmod(0o755)


# ---------------------------------------------------------------------------
# 16. cli_warning_stats_unknown_rule_keeps_data
# ---------------------------------------------------------------------------

def test_cli_warning_stats_unknown_rule_keeps_data(tmp_path, capsys):
    slug_dir = _warnings_dir(tmp_path, "proj-x")
    _write_jsonl(slug_dir, "owner_role_mismatch", [_make_record(count=3)] * 3)

    # _index.json 생성 (owner_role_mismatch만 등록 → unknown_rule은 없음)
    index = {
        "schema_version": 1,
        "rules": [{"rule_id": "owner_role_mismatch", "activate_at": "P4", "source": "x"}]
    }
    index_path = tmp_path / "runtime" / "warnings" / "_index.json"
    index_path.write_text(json.dumps(index), encoding="utf-8")

    # --rule unknown → warnings에 진단 1줄 + 데이터(0건) 정상 반환
    code, out, _ = _run_cli(
        ["warning-stats", "--workspace", str(tmp_path), "--rule", "unknown_rule"],
        capsys,
    )
    assert code == 0
    result = json.loads(out)
    assert any("not in runtime/warnings/_index.json" in w for w in result["warnings"])

    # unknown_rule.jsonl이 실제로 있으면 그 데이터 출력
    _write_jsonl(slug_dir, "unknown_rule", [_make_record(count=7)])
    code2, out2, _ = _run_cli(
        ["warning-stats", "--workspace", str(tmp_path), "--rule", "unknown_rule"],
        capsys,
    )
    assert code2 == 0
    result2 = json.loads(out2)
    assert result2["totals"]["count"] == 7
