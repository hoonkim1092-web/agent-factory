"""STAGE 1 검증 — KnowledgeNote 스키마 + 식별/접근 seam.

설계 §5 STAGE1 / §9 검증기준:
  - round-trip(to_md→from_md)
  - created_commit 이 현재 HEAD 와 일치(주입 테스트)
  - restricted/ enforcement 코드 0건(grep 검증, INV-K6)
  - id 네임스페이스 Windows 안전 (§12.9 크로스OS)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.knowledge.note import (
    KnowledgeNote,
    make_id,
    new_note,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# round-trip
# ---------------------------------------------------------------------------
def _sample_note() -> KnowledgeNote:
    return KnowledgeNote(
        id="decision/HOST-20260623T141530-482193Z-abc123-some-slug.md",
        type="decision",
        title="제목: 콜론 \"따옴표\" 포함",
        body="본문 첫 줄\n\n둘째 단락 — `file:line` verbatim 보존\n",
        author="HOON",
        source_machine="HOST",
        created_commit="0848fc74",
        created_at="2026-06-23T14:15:30+09:00",
        scope="project",
        visibility="private",
        links=["[[other-note]]", "[[code/symbols]]"],
    )


def test_roundtrip_preserves_all_fields():
    note = _sample_note()
    restored = KnowledgeNote.from_md(note.to_md())
    assert restored == note


def test_roundtrip_with_empty_body_and_links():
    note = KnowledgeNote(
        id="session/H-20260623T000000-000000Z-aa-x.md",
        type="session",
        title="빈 본문",
    )
    restored = KnowledgeNote.from_md(note.to_md())
    assert restored == note
    assert restored.links == []
    assert restored.body == ""


def test_roundtrip_body_with_triple_dash():
    """본문에 '---' 가 있어도 frontmatter 만 분리한다."""
    note = _sample_note()
    note.body = "위\n\n---\n\n아래 (수평선)\n"
    restored = KnowledgeNote.from_md(note.to_md())
    assert restored.body == note.body


def test_from_md_crlf_normalized():
    note = _sample_note()
    crlf = note.to_md().replace("\n", "\r\n")
    restored = KnowledgeNote.from_md(crlf)
    assert restored.title == note.title
    assert restored.links == note.links


def test_from_md_rejects_missing_frontmatter():
    with pytest.raises(ValueError):
        KnowledgeNote.from_md("frontmatter 없는 본문")


def test_frontmatter_is_yaml_compatible_inline():
    """스칼라/배열이 JSON(=YAML 부분집합) 인라인 형식이라 Obsidian 호환."""
    md = _sample_note().to_md()
    assert md.startswith("---\n")
    assert 'type: "decision"' in md
    assert 'links: ["[[other-note]]", "[[code/symbols]]"]' in md


# ---------------------------------------------------------------------------
# new_note 자동 스탬프 — created_commit = HEAD
# ---------------------------------------------------------------------------
def test_new_note_created_commit_matches_head():
    # production 헬퍼 재사용(try/except·stdin=DEVNULL 내포) — raw subprocess 의 hook 환경
    # WinError 6 회피, 멀티OS 안전. git 조회 불가 환경이면 skip.
    from core.knowledge.note import _short_commit

    head = _short_commit(str(REPO_ROOT))
    if head == "unknown":
        pytest.skip("git 커밋 조회 불가 환경")
    note = new_note("테스트 노트", "본문", "decision", workspace=str(REPO_ROOT))
    assert note.created_commit == head
    assert note.created_commit != "unknown"


def test_new_note_stamps_machine_and_author():
    note = new_note("x", note_type="pattern", workspace=str(REPO_ROOT))
    assert note.source_machine and note.source_machine != "unknown"
    assert note.author  # git author 또는 OS 사용자
    assert note.created_at  # ISO 스탬프
    # 기본 seam 값
    assert note.scope == "project"
    assert note.visibility == "private"


def test_new_note_id_namespace_shape():
    note = new_note("My Title Here", note_type="concept", workspace=str(REPO_ROOT), rand="deadbe")
    assert note.id.startswith("concept/")
    assert note.id.endswith("-my-title-here.md")
    assert "-deadbe-" in note.id


def test_new_note_rejects_invalid_type():
    with pytest.raises(ValueError):
        new_note("x", note_type="bogus", workspace=str(REPO_ROOT))  # type: ignore[arg-type]


def test_new_note_roundtrips():
    note = new_note("자동 스탬프 노트", "내용", "decision", workspace=str(REPO_ROOT))
    assert KnowledgeNote.from_md(note.to_md()) == note


# ---------------------------------------------------------------------------
# id 네임스페이스 — Windows 안전 (§12.9)
# ---------------------------------------------------------------------------
def test_id_has_no_windows_unsafe_chars():
    now = datetime(2026, 6, 23, 14, 15, 30, 482193, tzinfo=timezone.utc)
    note_id = make_id("decision", "DESKTOP-FOO", "어떤 제목: 콜론/슬래시\\백슬래시", now, rand="abc123")
    # 파일명 부분('decision/' 뒤)에 Windows 금지 문자 없어야 함
    filename = note_id.split("/", 1)[1]
    for ch in '<>:"\\|?*':
        assert ch not in filename, f"unsafe char {ch!r} in {filename}"


def test_make_id_uses_microsecond_resolution():
    now = datetime(2026, 6, 23, 14, 15, 30, 482193, tzinfo=timezone.utc)
    note_id = make_id("session", "H", "t", now, rand="aa")
    assert "20260623T141530-482193Z" in note_id


def test_make_id_collision_avoidance_with_rand():
    """동일 (type, machine, micro, title) 라도 rand 가 다르면 다른 id (INV-K11)."""
    now = datetime(2026, 6, 23, 14, 15, 30, 482193, tzinfo=timezone.utc)
    a = make_id("pattern", "H", "same", now, rand="111111")
    b = make_id("pattern", "H", "same", now, rand="222222")
    assert a != b


def test_korean_title_slug_preserved():
    note = new_note("한글 제목 테스트", note_type="session", workspace=str(REPO_ROOT), rand="aa")
    assert note.id.endswith("한글-제목-테스트.md")


def test_write_to_lands_at_id_path(tmp_path):
    note = new_note("쓰기 테스트", "본문", "decision", workspace=str(REPO_ROOT), rand="ff")
    target = note.write_to(tmp_path)
    assert target == tmp_path / note.id
    assert target.exists()
    assert KnowledgeNote.from_md(target.read_text(encoding="utf-8")) == note


# ---------------------------------------------------------------------------
# INV-K6 — restricted/ enforcement 코드 0건
# ---------------------------------------------------------------------------
def test_no_access_enforcement_code():
    """visibility/scope/restricted 는 데이터 seam 일 뿐 — 접근제어 enforcement 금지."""
    src = (REPO_ROOT / "core" / "knowledge" / "note.py").read_text(encoding="utf-8")
    # 권한 거부 / 가시성 게이팅 패턴이 없어야 함
    assert "PermissionError" not in src
    assert "restricted" not in src.lower() or "enforcement 코드" in src  # 주석 언급만 허용
    # visibility 를 조건으로 raise/return 차단하는 코드 부재
    assert not re.search(r"if\s+.*visibility.*:\s*\n\s*raise", src)
    assert not re.search(r"if\s+.*visibility\s*==\s*[\"']private", src)
