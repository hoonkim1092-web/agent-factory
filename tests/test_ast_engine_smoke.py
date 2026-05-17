"""tests/test_ast_engine_smoke.py — ASTEngine smoke tests.

Phase 2-prep C: ast-grep-py 설치 확인 + search/replace/search_dir 동작 검증.
frozen build 환경에서도 동일하게 통과해야 한다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from core import ast_engine


def test_search_finds_print():
    results = ast_engine.search("print($A)", "print(1 + 2)\nprint('hello')", "python")
    assert len(results) == 2
    assert results[0]["line"] == 0
    assert "print" in results[0]["text"]


def test_search_returns_empty_on_no_match():
    results = ast_engine.search("logging.info($A)", "print(1)", "python")
    assert results == []


def test_replace_substitutes_pattern():
    code = "print(x)\nprint(y)"
    result = ast_engine.replace("print($A)", "logger.info($A)", code, "python")
    assert "logger.info(x)" in result
    assert "logger.info(y)" in result
    assert "print(" not in result


def test_search_file(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("import subprocess\nsubprocess.run(['ls'])\n", encoding="utf-8")
    results = ast_engine.search_file("subprocess.$F($$$ARGS)", str(f))
    assert len(results) >= 1
    assert results[0]["file"] == str(f.resolve())


def test_search_file_nonexistent():
    results = ast_engine.search_file("print($A)", "/nonexistent/path.py")
    assert results == []


def test_search_dir(tmp_path):
    (tmp_path / "a.py").write_text("eval('1+1')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("x = 1\n", encoding="utf-8")
    results = ast_engine.search_dir("eval($A)", str(tmp_path), extensions=[".py"])
    assert any("a.py" in r["file"] for r in results)
    assert not any("b.py" in r["file"] for r in results)


def test_detect_lang_python():
    assert ast_engine.detect_lang("core/foo.py") == "python"


def test_detect_lang_unknown_falls_back():
    assert ast_engine.detect_lang("file.xyz") == "python"
