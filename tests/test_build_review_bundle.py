"""tests/test_build_review_bundle.py — scripts/build_review_bundle.py + core/review_bundle build_full unit tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from core import review_bundle as rb


def _script():
    import importlib, sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import scripts.build_review_bundle as m
    importlib.reload(m)
    return m


# ── _load_pending ─────────────────────────────────────────────────────────────

def test_load_pending_empty_when_no_queue(tmp_path):
    m = _script()
    assert m._load_pending(str(tmp_path)) == []


def test_load_pending_returns_files(tmp_path):
    m = _script()
    q = tmp_path / ".af_review_queue"
    q.mkdir()
    (q / "pending_agent_review.json").write_text(
        json.dumps({"files": ["core/foo.py", "scripts/bar.py"]}),
        encoding="utf-8",
    )
    assert m._load_pending(str(tmp_path)) == ["core/foo.py", "scripts/bar.py"]


def test_load_pending_skips_empty_entries(tmp_path):
    m = _script()
    q = tmp_path / ".af_review_queue"
    q.mkdir()
    (q / "pending_agent_review.json").write_text(
        json.dumps({"files": ["core/foo.py", "", None]}),
        encoding="utf-8",
    )
    result = m._load_pending(str(tmp_path))
    assert "" not in result
    assert None not in result


# ── _resolve_paths ────────────────────────────────────────────────────────────

def test_resolve_paths_only_py(tmp_path):
    m = _script()
    f = tmp_path / "core" / "foo.py"
    f.parent.mkdir()
    f.write_text("x = 1\n")
    result = m._resolve_paths(str(tmp_path), ["core/foo.py", "README.md"])
    assert any("foo.py" in p for p in result)
    assert not any("README" in p for p in result)


def test_resolve_paths_skips_missing(tmp_path):
    m = _script()
    result = m._resolve_paths(str(tmp_path), ["core/nonexistent.py"])
    assert result == []


# ── run ───────────────────────────────────────────────────────────────────────

def test_run_returns_0_when_no_queue(tmp_path):
    m = _script()
    assert m.run(str(tmp_path)) == 0


def test_run_creates_bundle_file(tmp_path, monkeypatch):
    m = _script()

    # Setup: queue with a real .py file
    f = tmp_path / "core" / "foo.py"
    f.parent.mkdir()
    f.write_text("import subprocess\nsubprocess.run(['ls'])\n")

    q = tmp_path / ".af_review_queue"
    q.mkdir()
    (q / "pending_agent_review.json").write_text(
        json.dumps({"files": ["core/foo.py"]}), encoding="utf-8"
    )

    monkeypatch.syspath_prepend(str(tmp_path))

    result = m.run(str(tmp_path))
    assert result == 0

    bundle_file = q / "review_bundle.md"
    assert bundle_file.exists(), "review_bundle.md should be created"
    content = bundle_file.read_text(encoding="utf-8")
    # Full 8-section bundle: check header + key sections
    assert "Review Bundle" in content
    assert "## 1. Pending Files" in content
    assert "## 2. Git Diff" in content
    assert "## 6. Risk Flags" in content
    assert "subprocess_usage" in content  # risk detected in foo.py


# ── build_full ────────────────────────────────────────────────────────────────

def test_build_full_returns_required_keys(tmp_path):
    f = tmp_path / "core" / "foo.py"
    f.parent.mkdir()
    f.write_text("import subprocess\nsubprocess.run(['ls'])\n", encoding="utf-8")
    result = rb.build_full(str(tmp_path), [str(f)])
    assert "bundle_md" in result
    assert "source_hash" in result
    assert "generated_at" in result
    assert "stats" in result


def test_build_full_bundle_md_has_all_sections(tmp_path):
    f = tmp_path / "core" / "foo.py"
    f.parent.mkdir()
    f.write_text("x = 1\n", encoding="utf-8")
    result = rb.build_full(str(tmp_path), [str(f)])
    md = result["bundle_md"]
    for section in ["## 1. Pending Files", "## 2. Git Diff", "## 3. Test Gap",
                     "## 4. Related Tests", "## 5. Direct Callers",
                     "## 6. Risk Flags", "## 7. Prior Findings", "## 8. Bundle Stats"]:
        assert section in md, f"Missing: {section}"


def test_build_full_source_hash_is_hex(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("pass\n", encoding="utf-8")
    result = rb.build_full(str(tmp_path), [str(f)])
    h = result["source_hash"]
    assert len(h) == 16
    int(h, 16)  # must be valid hex


def test_build_full_detects_risk_flags(tmp_path):
    f = tmp_path / "core" / "bad.py"
    f.parent.mkdir()
    f.write_text("import subprocess\nsubprocess.run(['rm', '-rf'], shell=True)\n", encoding="utf-8")
    result = rb.build_full(str(tmp_path), [str(f)])
    md = result["bundle_md"]
    assert "subprocess_usage" in md or "shell_true" in md


def test_build_full_respects_100kb_cap(tmp_path):
    # Create a large file to stress the cap
    f = tmp_path / "big.py"
    f.write_text("x = " + "1" * 200_000 + "\n", encoding="utf-8")
    result = rb.build_full(str(tmp_path), [str(f)])
    assert result["stats"]["size_bytes"] <= 100 * 1024 + 4096  # allow small overshoot from §8


def test_save_full_writes_file(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("pass\n", encoding="utf-8")
    bundle = rb.build_full(str(tmp_path), [str(f)])
    out = rb.save_full(bundle, str(tmp_path))
    assert out.exists()
    assert out.read_text(encoding="utf-8") == bundle["bundle_md"]


def test_run_returns_0_on_error(tmp_path, monkeypatch):
    m = _script()

    q = tmp_path / ".af_review_queue"
    q.mkdir()
    (q / "pending_agent_review.json").write_text(
        json.dumps({"files": ["core/foo.py"]}), encoding="utf-8"
    )
    # No actual file exists → _resolve_paths returns [] → early exit 0
    assert m.run(str(tmp_path)) == 0
