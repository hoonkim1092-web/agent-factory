"""tests/test_codebase_symbols.py — codebase_symbols 빌더 계약 테스트.

scripts/codebase_symbols.py 는 주어진 디렉터리의 Python 파일을 read-only AST
(표준 ``ast`` 모듈)로 분석해 각 모듈의 top-level 클래스·함수 이름을 추출하고
symbols.md 마크다운 문자열로 렌더링한다. 원본 코드는 절대 수정하지 않는다.

이 테스트는 다음 공개 계약을 고정한다 (TDD — 구현보다 먼저 작성):

- ``extract_symbols(source: str) -> dict``
      단일 소스 문자열을 파싱해 ``{"classes": [...], "functions": [...]}`` 반환.
      top-level 심볼만 — 클래스 메서드/중첩 함수는 제외. async 함수 포함.
- ``collect_symbols(directory) -> dict[str, dict]``
      디렉터리를 재귀 walk 하여 posix 상대경로 → 심볼 dict 매핑 반환.
- ``build(directory) -> str``
      collect + render. symbols.md 마크다운 문자열 반환.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.codebase_symbols import (  # noqa: E402
    extract_symbols,
    collect_symbols,
    build,
)


# ---------------------------------------------------------------------------
# extract_symbols — 단일 소스 파싱
# ---------------------------------------------------------------------------
def test_extract_symbols_top_level_classes_and_functions():
    source = (
        "class Alpha:\n"
        "    pass\n"
        "\n"
        "class Beta:\n"
        "    pass\n"
        "\n"
        "def do_thing():\n"
        "    return 1\n"
    )
    result = extract_symbols(source)
    assert set(result["classes"]) == {"Alpha", "Beta"}
    assert set(result["functions"]) == {"do_thing"}


def test_extract_symbols_includes_async_functions():
    source = "async def fetch():\n    return None\n"
    result = extract_symbols(source)
    assert "fetch" in result["functions"]


def test_extract_symbols_excludes_methods_and_nested():
    """클래스 메서드와 중첩 함수는 top-level 함수 목록에 포함되지 않는다."""
    source = (
        "class Service:\n"
        "    def method(self):\n"
        "        def inner():\n"
        "            return 1\n"
        "        return inner\n"
        "\n"
        "def outer():\n"
        "    def nested():\n"
        "        return 2\n"
        "    return nested\n"
    )
    result = extract_symbols(source)
    assert set(result["classes"]) == {"Service"}
    assert set(result["functions"]) == {"outer"}
    assert "method" not in result["functions"]
    assert "inner" not in result["functions"]
    assert "nested" not in result["functions"]


def test_extract_symbols_empty_source():
    result = extract_symbols("")
    assert result["classes"] == []
    assert result["functions"] == []


# ---------------------------------------------------------------------------
# collect_symbols — 디렉터리 walk
# ---------------------------------------------------------------------------
def test_collect_symbols_finds_python_files(tmp_path):
    (tmp_path / "mod_a.py").write_text(
        "class Widget:\n    pass\n\ndef helper():\n    pass\n", encoding="utf-8"
    )
    result = collect_symbols(tmp_path)
    assert "mod_a.py" in result
    assert set(result["mod_a.py"]["classes"]) == {"Widget"}
    assert set(result["mod_a.py"]["functions"]) == {"helper"}


def test_collect_symbols_recurses_with_posix_keys(tmp_path):
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "nested.py").write_text("def deep():\n    pass\n", encoding="utf-8")
    result = collect_symbols(tmp_path)
    # 키는 OS 무관 posix 상대경로 — 백슬래시 금지 (Windows 결정성)
    keys = list(result.keys())
    assert "pkg/nested.py" in keys
    assert all("\\" not in k for k in keys)


def test_collect_symbols_ignores_non_python(tmp_path):
    (tmp_path / "readme.md").write_text("# not python\n", encoding="utf-8")
    (tmp_path / "data.txt").write_text("class NotReal:\n", encoding="utf-8")
    (tmp_path / "real.py").write_text("class Real:\n    pass\n", encoding="utf-8")
    result = collect_symbols(tmp_path)
    assert "real.py" in result
    assert "readme.md" not in result
    assert "data.txt" not in result


def test_collect_symbols_skips_runtime_and_cache_directories(tmp_path):
    runtime = tmp_path / ".af_runtime" / "generated"
    cache = tmp_path / "__pycache__"
    runtime.mkdir(parents=True)
    cache.mkdir()
    (runtime / "ignored.py").write_text("class RuntimeLeak:\n    pass\n", encoding="utf-8")
    (cache / "ignored.py").write_text("def cache_leak():\n    pass\n", encoding="utf-8")
    (tmp_path / "real.py").write_text("class Real:\n    pass\n", encoding="utf-8")

    result = collect_symbols(tmp_path)

    assert "real.py" in result
    assert ".af_runtime/generated/ignored.py" not in result
    assert "__pycache__/ignored.py" not in result


def test_collect_symbols_empty_directory(tmp_path):
    result = collect_symbols(tmp_path)
    assert result == {}


def test_collect_symbols_does_not_modify_source(tmp_path):
    """read-only 보장 — 원본 파일 내용이 변경되지 않는다."""
    src = tmp_path / "untouched.py"
    original = "class Keep:\n    pass\n\ndef stay():\n    pass\n"
    src.write_text(original, encoding="utf-8")
    collect_symbols(tmp_path)
    assert src.read_text(encoding="utf-8") == original


def test_collect_symbols_tolerates_syntax_error(tmp_path):
    """파싱 불가 파일이 있어도 크래시하지 않고 정상 파일은 수집한다."""
    (tmp_path / "broken.py").write_text("def (:\n    this is not python\n", encoding="utf-8")
    (tmp_path / "good.py").write_text("class Good:\n    pass\n", encoding="utf-8")
    result = collect_symbols(tmp_path)  # raise 하면 실패
    assert "good.py" in result
    assert set(result["good.py"]["classes"]) == {"Good"}


def test_collect_symbols_respects_python_encoding_cookie(tmp_path):
    encoded = "# -*- coding: cp949 -*-\nclass KoreanName:\n    label = '한글'\n"
    (tmp_path / "encoded.py").write_bytes(encoded.encode("cp949"))

    result = collect_symbols(tmp_path)

    assert "encoded.py" in result
    assert result["encoded.py"]["classes"] == ["KoreanName"]


def test_collect_symbols_tolerates_decode_error(tmp_path):
    (tmp_path / "bad_encoding.py").write_bytes(b"\xff\xfe\x00\x00")

    result = collect_symbols(tmp_path)

    assert result["bad_encoding.py"] == {"classes": [], "functions": []}


# ---------------------------------------------------------------------------
# build — 마크다운 렌더링
# ---------------------------------------------------------------------------
def test_build_returns_markdown_string(tmp_path):
    (tmp_path / "sample.py").write_text(
        "class Engine:\n    pass\n\ndef run():\n    pass\n", encoding="utf-8"
    )
    md = build(tmp_path)
    assert isinstance(md, str)
    # 모듈 경로, 클래스명, 함수명이 모두 출력에 나타난다
    assert "sample.py" in md
    assert "Engine" in md
    assert "run" in md


def test_build_is_deterministic(tmp_path):
    (tmp_path / "a.py").write_text("class A:\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def b():\n    pass\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("class C:\n    pass\n", encoding="utf-8")
    first = build(tmp_path)
    second = build(tmp_path)
    assert first == second


def test_build_empty_directory_returns_string(tmp_path):
    md = build(tmp_path)
    assert isinstance(md, str)


def test_build_accepts_str_path(tmp_path):
    (tmp_path / "x.py").write_text("def x():\n    pass\n", encoding="utf-8")
    md = build(str(tmp_path))
    assert "x.py" in md
    assert "x" in md
