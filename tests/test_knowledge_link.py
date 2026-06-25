"""tests/test_knowledge_link.py — af_knowledge_link 단위 테스트."""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

from scripts.af_knowledge_link import (
    _extract_py_refs,
    _parse_links_list,
    _format_links_list,
    _existing_wikilinks,
    _load_symbol_files,
    _update_note,
    compute_links,
)


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_note(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# production-accurate: _load_symbol_files는 full path + basename 역인덱스를 모두 포함
SYMBOL_FILES = {
    "af.py",
    "core/fsa_loop.py", "fsa_loop.py",       # basename 역인덱스
    "scripts/af_doctor.py", "af_doctor.py",
    "agent_launcher.py",
}


# ---------------------------------------------------------------------------
# _extract_py_refs
# ---------------------------------------------------------------------------

def test_extract_bare_filename():
    refs = _extract_py_refs("수정: af.py:42에서 버그 발견", SYMBOL_FILES)
    assert "af.py" in refs


def test_extract_path_with_slash():
    refs = _extract_py_refs("core/fsa_loop.py:87 참조", SYMBOL_FILES)
    # full path가 basename보다 우선 매칭되어야 함 (false cross-link 방지)
    assert "core/fsa_loop.py" in refs
    assert "fsa_loop.py" not in refs  # basename이 아닌 full path로 참조됨


def test_extract_unknown_file():
    refs = _extract_py_refs("unknown_module.py:10 수정", SYMBOL_FILES)
    assert not refs  # symbols에 없으면 제외


def test_extract_multiple():
    text = "af.py:1 그리고 agent_launcher.py:50 수정"
    refs = _extract_py_refs(text, SYMBOL_FILES)
    assert "af.py" in refs
    assert "agent_launcher.py" in refs


# ---------------------------------------------------------------------------
# _parse_links_list / _format_links_list
# ---------------------------------------------------------------------------

def test_parse_empty():
    assert _parse_links_list("") == []


def test_parse_one():
    assert _parse_links_list('"[[code/symbols]]"') == ["[[code/symbols]]"]


def test_parse_two():
    result = _parse_links_list('"[[code/symbols]]", "[[knowledge/session/x]]"')
    assert "[[code/symbols]]" in result
    assert "[[knowledge/session/x]]" in result


def test_format_round_trip():
    links = ["[[code/symbols]]", "[[knowledge/session/abc]]"]
    formatted = _format_links_list(links)
    assert _parse_links_list(formatted[1:-1]) == links  # 괄호 제거 후 파싱


# ---------------------------------------------------------------------------
# _existing_wikilinks
# ---------------------------------------------------------------------------

def test_existing_wikilinks():
    text = "참고 [[code/symbols]] 및 [[knowledge/session/x]]\n"
    wl = _existing_wikilinks(text)
    assert "[[code/symbols]]" in wl
    assert "[[knowledge/session/x]]" in wl


# ---------------------------------------------------------------------------
# _load_symbol_files
# ---------------------------------------------------------------------------

def test_load_symbol_files(tmp_path: Path):
    symbols = tmp_path / "symbols.md"
    symbols.write_text("## `af.py`\n\n## `core/fsa_loop.py`\n", encoding="utf-8")
    result = _load_symbol_files(symbols)
    assert "af.py" in result
    assert "core/fsa_loop.py" in result
    assert "fsa_loop.py" in result  # basename 역인덱스


def test_load_symbol_files_missing(tmp_path: Path):
    result = _load_symbol_files(tmp_path / "no_such.md")
    assert result == set()


# ---------------------------------------------------------------------------
# _update_note
# ---------------------------------------------------------------------------

NOTE_TEMPLATE = textwrap.dedent("""\
    ---
    id: "session/test-note"
    links: []
    ---

    본문 내용.
""")


def test_update_note_adds_link(tmp_path: Path):
    note = _make_note(tmp_path, "test.md", NOTE_TEMPLATE)
    changed = _update_note(note, ["[[code/symbols]]"])
    assert changed
    text = note.read_text(encoding="utf-8")
    assert "[[code/symbols]]" in text


def test_update_note_no_duplicate(tmp_path: Path):
    # frontmatter와 본문 양쪽에 이미 [[code/symbols]]가 있으면 변경 없음
    already_there = (
        NOTE_TEMPLATE
        .replace("links: []", 'links: ["[[code/symbols]]"]')
        .replace("본문 내용.", "본문 내용.\n\n## 관련\n- [[code/symbols]]")
    )
    note = _make_note(tmp_path, "test.md", already_there)
    changed = _update_note(note, ["[[code/symbols]]"])
    assert not changed


def test_update_note_adds_section(tmp_path: Path):
    note = _make_note(tmp_path, "test.md", NOTE_TEMPLATE)
    _update_note(note, ["[[code/symbols]]"])
    text = note.read_text(encoding="utf-8")
    assert "## 관련" in text


def test_update_note_appends_to_existing_section(tmp_path: Path):
    body = NOTE_TEMPLATE + "\n## 관련\n- [[code/symbols]]\n"
    note = _make_note(tmp_path, "test.md", body)
    changed = _update_note(note, ["[[knowledge/session/other]]"])
    assert changed
    text = note.read_text(encoding="utf-8")
    # 기존 링크 보존
    assert "[[code/symbols]]" in text
    # 새 링크 추가
    assert "[[knowledge/session/other]]" in text
    # ## 관련 중복 없음
    assert text.count("## 관련") == 1


# ---------------------------------------------------------------------------
# compute_links (통합)
# ---------------------------------------------------------------------------

def test_compute_links_symbols_link(tmp_path: Path):
    symbols = tmp_path / "symbols.md"
    symbols.write_text("## `af.py`\n", encoding="utf-8")
    symbol_files = _load_symbol_files(symbols)

    vault = tmp_path / "knowledge"
    vault.mkdir()
    note = _make_note(vault, "note1.md", textwrap.dedent("""\
        ---
        id: "session/note1"
        links: []
        ---

        af.py:10 에서 발견.
    """))
    changes = compute_links(vault, symbol_files)
    assert len(changes) == 1
    assert "[[code/symbols]]" in changes[0].new_links


def test_compute_links_session_cross(tmp_path: Path):
    symbols = tmp_path / "symbols.md"
    symbols.write_text("## `af.py`\n", encoding="utf-8")
    symbol_files = _load_symbol_files(symbols)

    vault = tmp_path / "knowledge"
    session_dir = vault / "session"
    session_dir.mkdir(parents=True)

    _make_note(session_dir, "noteA.md", textwrap.dedent("""\
        ---
        id: "session/noteA"
        links: []
        ---

        af.py:10 참조.
    """))
    _make_note(session_dir, "noteB.md", textwrap.dedent("""\
        ---
        id: "session/noteB"
        links: []
        ---

        af.py:20 참조.
    """))

    changes = compute_links(vault, symbol_files)
    assert len(changes) == 2
    # 두 노트가 서로 연결
    all_links = [lk for ch in changes for lk in ch.new_links]
    cross_links = [lk for lk in all_links if "session" in lk and "note" in lk.lower()]
    assert len(cross_links) >= 2  # A→B, B→A


def test_agent_launcher_knowledge_link_registered():
    repo_root = Path(__file__).resolve().parents[1]
    src = (repo_root / "agent_launcher.py").read_text(encoding="utf-8")
    assert "link" in src and "knowledge_link_main" in src


def test_run_factory_cli_knowledge_link_registered():
    repo_root = Path(__file__).resolve().parents[1]
    src = (repo_root / "run_factory_cli.py").read_text(encoding="utf-8")
    assert "knowledge_link_main" in src or "af_knowledge_link" in src


def test_af_spec_hiddenimport():
    repo_root = Path(__file__).resolve().parents[1]
    src = (repo_root / "af.spec").read_text(encoding="utf-8")
    assert "scripts.af_knowledge_link" in src
