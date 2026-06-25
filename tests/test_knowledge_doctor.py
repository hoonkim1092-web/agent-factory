"""tests/test_knowledge_doctor.py — STAGE 3 staleness/skew 점검기 단위 테스트.

설계 §5 STAGE3 [검증] 기준:
  #1 SKEW: created_commit 로컬 미보유 → SKEW Finding (file:line 체크 없음)
  #2 STALE: created_commit 있음 + file:line 내용 변동 → STALE Finding
  #3 OK: created_commit 있음 + file:line 내용 동일 → Finding 없음
  #4 created_commit=unknown 노트 → 건너뜀 (STAGE1 이전)
  #5 file deleted → STALE
  #6 크로스OS: import·main() 실행 (Windows 회귀)
  #7 JSON 출력 모드
  #8 두 dispatch 진입점 등록 확인 (agent_launcher + run_factory_cli)
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.af_knowledge_doctor import (
    Finding,
    _commit_exists,
    _current_line,
    _extract_file_line_refs,
    _line_at_commit,
    _parse_created_commit,
    check_note,
    main,
    run_doctor,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_note(tmp_path: Path, filename: str, created_commit: str, body: str) -> Path:
    p = tmp_path / filename
    p.write_text(
        textwrap.dedent(f"""\
        ---
        id: session/test-machine-000000-aa0000-test.md
        type: session
        scope: project
        title: test note
        author: testuser
        source_machine: TEST
        created_commit: "{created_commit}"
        created_at: 2026-06-25T00:00:00+00:00
        visibility: private
        links: []
        ---

        {body}
        """),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# _parse_created_commit
# ---------------------------------------------------------------------------

def test_parse_created_commit_normal():
    text = '---\ncreated_commit: "abc1234"\n---\nbody'
    assert _parse_created_commit(text) == "abc1234"


def test_parse_created_commit_unknown_returns_empty():
    text = '---\ncreated_commit: "unknown"\n---\nbody'
    assert _parse_created_commit(text) == ""


def test_parse_created_commit_missing_returns_empty():
    text = '---\ntitle: "no commit"\n---\nbody'
    assert _parse_created_commit(text) == ""


# ---------------------------------------------------------------------------
# _extract_file_line_refs
# ---------------------------------------------------------------------------

def test_extract_file_line_refs_forward_slash():
    refs = _extract_file_line_refs("see core/knowledge/note.py:178 for detail")
    assert ("core/knowledge/note.py", 178) in refs


def test_extract_file_line_refs_backslash():
    refs = _extract_file_line_refs(r"see core\knowledge\note.py:178 for detail")
    assert any(line_num == 178 for _, line_num in refs)


def test_extract_file_line_refs_no_refs():
    assert _extract_file_line_refs("no refs here") == []


# ---------------------------------------------------------------------------
# _commit_exists (mock git)
# ---------------------------------------------------------------------------

def test_commit_exists_true(tmp_path):
    with patch("scripts.af_knowledge_doctor._git", return_value=(0, "commit\n")):
        assert _commit_exists("abc1234", str(tmp_path)) is True


def test_commit_exists_false(tmp_path):
    with patch("scripts.af_knowledge_doctor._git", return_value=(128, "")):
        assert _commit_exists("deadbeef", str(tmp_path)) is False


# ---------------------------------------------------------------------------
# _line_at_commit / _current_line
# ---------------------------------------------------------------------------

def test_line_at_commit_returns_correct_line(tmp_path):
    file_content = "line1\nline2\nline3\n"
    with patch("scripts.af_knowledge_doctor._git", return_value=(0, file_content)):
        assert _line_at_commit("some/file.py", 2, "abc", str(tmp_path)) == "line2"


def test_line_at_commit_out_of_range(tmp_path):
    with patch("scripts.af_knowledge_doctor._git", return_value=(0, "line1\n")):
        assert _line_at_commit("some/file.py", 99, "abc", str(tmp_path)) is None


def test_line_at_commit_git_fail(tmp_path):
    with patch("scripts.af_knowledge_doctor._git", return_value=(128, "")):
        assert _line_at_commit("some/file.py", 1, "abc", str(tmp_path)) is None


def test_current_line_reads_file(tmp_path):
    f = tmp_path / "myfile.py"
    f.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    assert _current_line("myfile.py", 2, str(tmp_path)) == "beta"


def test_current_line_missing_file(tmp_path):
    assert _current_line("nonexistent.py", 1, str(tmp_path)) is None


# ---------------------------------------------------------------------------
# check_note — SKEW (#1)
# ---------------------------------------------------------------------------

def test_check_note_skew(tmp_path):
    """created_commit 로컬 미보유 → SKEW, file:line 체크 없음."""
    note = _make_note(tmp_path, "skew_note.md", "deadbeef1", "core/foo.py:10 참조")
    with patch("scripts.af_knowledge_doctor._commit_exists", return_value=False):
        findings = check_note(note, str(tmp_path))
    assert len(findings) == 1
    assert findings[0].status == "SKEW"
    assert findings[0].ref == "deadbeef1"


# ---------------------------------------------------------------------------
# check_note — STALE (#2)
# ---------------------------------------------------------------------------

def test_check_note_stale_changed_line(tmp_path):
    """created_commit 있음 + file:line 내용 변경 → STALE."""
    note = _make_note(tmp_path, "stale_note.md", "aabb123", "core/foo.py:5 참조")

    def fake_git(args, cwd, **kwargs):
        if args[0] == "cat-file":
            return (0, "commit\n")
        if "show" in args[0]:
            return (0, "old_line\n")
        return (0, "")

    target = tmp_path / "core" / "foo.py"
    target.parent.mkdir(parents=True)
    target.write_text("line1\nline2\nline3\nnew_line5\nline5\n", encoding="utf-8")

    with (
        patch("scripts.af_knowledge_doctor._commit_exists", return_value=True),
        patch("scripts.af_knowledge_doctor._line_at_commit", return_value="old_line"),
        patch("scripts.af_knowledge_doctor._current_line", return_value="new_line"),
    ):
        findings = check_note(note, str(tmp_path))

    assert any(f.status == "STALE" for f in findings)


# ---------------------------------------------------------------------------
# check_note — OK (#3)
# ---------------------------------------------------------------------------

def test_check_note_ok_same_line(tmp_path):
    """created_commit 있음 + file:line 내용 동일 → Finding 없음."""
    note = _make_note(tmp_path, "ok_note.md", "aabb123", "core/foo.py:2 참조")

    with (
        patch("scripts.af_knowledge_doctor._commit_exists", return_value=True),
        patch("scripts.af_knowledge_doctor._line_at_commit", return_value="same content"),
        patch("scripts.af_knowledge_doctor._current_line", return_value="same content"),
    ):
        findings = check_note(note, str(tmp_path))

    assert findings == []


# ---------------------------------------------------------------------------
# check_note — unknown commit → 건너뜀 (#4)
# ---------------------------------------------------------------------------

def test_check_note_unknown_commit_skipped(tmp_path):
    note = tmp_path / "no_commit.md"
    note.write_text(
        '---\ncreated_commit: "unknown"\ntitle: "x"\n---\nbody\n',
        encoding="utf-8",
    )
    findings = check_note(note, str(tmp_path))
    assert findings == []


# ---------------------------------------------------------------------------
# check_note — file deleted → STALE (#5)
# ---------------------------------------------------------------------------

def test_check_note_stale_file_deleted(tmp_path):
    note = _make_note(tmp_path, "stale_del.md", "aabb123", "core/deleted.py:3 참조")

    with (
        patch("scripts.af_knowledge_doctor._commit_exists", return_value=True),
        patch("scripts.af_knowledge_doctor._line_at_commit", return_value="old content"),
        patch("scripts.af_knowledge_doctor._current_line", return_value=None),
    ):
        findings = check_note(note, str(tmp_path))

    assert any(f.status == "STALE" for f in findings)


# ---------------------------------------------------------------------------
# main() CLI — JSON 출력 (#7)
# ---------------------------------------------------------------------------

def test_main_json_output(tmp_path, capsys):
    note = _make_note(tmp_path, "note.md", "abc1234", "see core/foo.py:1")

    with (
        patch("scripts.af_knowledge_doctor._commit_exists", return_value=False),
    ):
        rc = main(["--vault", str(tmp_path), "--repo", str(tmp_path), "--json"])

    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert rc == 0


def test_main_no_vault(tmp_path, capsys):
    rc = main(["--vault", str(tmp_path / "nonexistent"), "--repo", str(tmp_path)])
    assert rc == 1


def test_main_ok_no_findings(tmp_path, capsys):
    """vault 에 created_commit 없는 노트만 있으면 OK."""
    note = tmp_path / "plain.md"
    note.write_text("---\ntitle: x\n---\nbody\n", encoding="utf-8")
    rc = main(["--vault", str(tmp_path), "--repo", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


# ---------------------------------------------------------------------------
# dispatch 진입점 등록 확인 (#8)
# ---------------------------------------------------------------------------

def test_agent_launcher_knowledge_doctor_registered():
    """agent_launcher 에 knowledge doctor 서브커맨드가 등록돼 있는지 확인."""
    repo_root = Path(__file__).resolve().parents[1]
    src = (repo_root / "agent_launcher.py").read_text(encoding="utf-8")
    assert "doctor" in src and "knowledge_doctor_main" in src


def test_run_factory_cli_knowledge_doctor_registered():
    """run_factory_cli 의 _run_knowledge_subcommand 에 doctor 분기가 있는지 확인."""
    repo_root = Path(__file__).resolve().parents[1]
    src = (repo_root / "run_factory_cli.py").read_text(encoding="utf-8")
    assert "_knowledge_doctor_main" in src or "af_knowledge_doctor" in src
