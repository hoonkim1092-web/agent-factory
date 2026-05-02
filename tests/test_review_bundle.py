"""tests/test_review_bundle.py — core/review_bundle.py unit tests.

Phase 2-prep D: build/save/load API, grep fallback, AST availability flag.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def _bundle():
    import importlib
    import core.review_bundle as m
    importlib.reload(m)
    return m


# ── _grep_risks ───────────────────────────────────────────────────────────────

def test_grep_risks_detects_subprocess(tmp_path):
    m = _bundle()
    f = tmp_path / "x.py"
    f.write_text("import subprocess\nsubprocess.run(['ls'])\n")
    hits = m._grep_risks(str(f))
    assert any(h["risk_id"] == "subprocess_usage" for h in hits)


def test_grep_risks_detects_shell_true(tmp_path):
    m = _bundle()
    f = tmp_path / "x.py"
    f.write_text("subprocess.run('ls', shell=True)\n")
    hits = m._grep_risks(str(f))
    assert any(h["risk_id"] == "shell_true" for h in hits)


def test_grep_risks_clean_file(tmp_path):
    m = _bundle()
    f = tmp_path / "clean.py"
    f.write_text("x = 1\ny = x + 2\n")
    hits = m._grep_risks(str(f))
    assert hits == []


def test_grep_risks_missing_file():
    m = _bundle()
    hits = m._grep_risks("/nonexistent/path/missing.py")
    assert hits == []


# ── build ─────────────────────────────────────────────────────────────────────

def test_build_returns_dict(tmp_path):
    m = _bundle()
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    result = m.build([str(f)])
    assert "engine" in result
    assert "files" in result
    assert result["files"][0]["path"] == str(f)


def test_build_engine_field(tmp_path, monkeypatch):
    m = _bundle()
    monkeypatch.setattr(m, "_ast_available", lambda: False)
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    result = m.build([str(f)])
    assert result["engine"] == "grep"


def test_build_empty_list(tmp_path):
    m = _bundle()
    result = m.build([])
    assert result["files"] == []


# ── save / load ───────────────────────────────────────────────────────────────

def test_save_creates_file(tmp_path):
    m = _bundle()
    bundle = {"engine": "grep", "files": [{"path": "core/x.py", "risks": []}]}
    out = m.save(bundle, str(tmp_path))
    assert out.exists()
    assert "review_bundle" in out.read_text(encoding="utf-8")


def test_save_includes_risk(tmp_path):
    m = _bundle()
    bundle = {
        "engine": "grep",
        "files": [{"path": "core/x.py", "risks": [{"risk_id": "subprocess_usage", "line": 5, "text": "subprocess.run"}]}],
    }
    out = m.save(bundle, str(tmp_path))
    assert "subprocess_usage" in out.read_text(encoding="utf-8")


def test_save_new_format_contains_desc(tmp_path):
    m = _bundle()
    bundle = {
        "engine": "grep",
        "files": [{"path": "core/x.py", "risks": [{"risk_id": "shell_true", "line": 3, "text": "shell=True"}]}],
    }
    text = m.save(bundle, str(tmp_path)).read_text(encoding="utf-8")
    # new format: "- L3 `shell_true` — shell=True — ..."
    assert "- L3 `shell_true` —" in text
    assert "코드:" in text


def test_save_dynamic_import_desc(tmp_path):
    m = _bundle()
    bundle = {
        "engine": "grep",
        "files": [{"path": "x.py", "risks": [{"risk_id": "dynamic_import", "line": 1, "text": "__import__"}]}],
    }
    text = m.save(bundle, str(tmp_path)).read_text(encoding="utf-8")
    assert "dynamic_import" in text
    assert "동적 import" in text


def test_grep_risks_dynamic_import():
    m = _bundle()
    import tempfile, pathlib
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("mod = __import__('os')\n")
        fname = f.name
    hits = m._grep_risks(fname)
    pathlib.Path(fname).unlink()
    assert any(h["risk_id"] == "dynamic_import" for h in hits)


def test_grep_risks_with_windows_style_path(tmp_path):
    # _grep_risks는 subprocess 호출 없이 pathlib.read_text를 사용하므로
    # 경로에 공백이 있어도 (Windows: "C:\Program Files\tool.cmd") 문제없이 동작.
    # POSIX: "/Applications/My Tool/run" 도 동일.
    m = _bundle()
    py_file = tmp_path / "my module.py"
    py_file.write_text("result = eval(user_input)\n", encoding="utf-8")
    hits = m._grep_risks(str(py_file))
    assert any(h["risk_id"] == "eval_usage" for h in hits)


def test_load_returns_none_when_missing(tmp_path):
    m = _bundle()
    assert m.load(str(tmp_path)) is None


def test_load_returns_raw_after_save(tmp_path):
    m = _bundle()
    bundle = {"engine": "grep", "files": []}
    m.save(bundle, str(tmp_path))
    loaded = m.load(str(tmp_path))
    assert loaded is not None
    assert "raw" in loaded
