"""tests/test_build_review_bundle.py — scripts/build_review_bundle.py unit tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


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
    assert "review_bundle" in content


def test_run_returns_0_on_error(tmp_path, monkeypatch):
    m = _script()

    q = tmp_path / ".af_review_queue"
    q.mkdir()
    (q / "pending_agent_review.json").write_text(
        json.dumps({"files": ["core/foo.py"]}), encoding="utf-8"
    )
    # No actual file exists → _resolve_paths returns [] → early exit 0
    assert m.run(str(tmp_path)) == 0
