"""tests/test_knowledge_retrieve.py — STAGE R 검색 엔진 단위 테스트.

검증 기준 (설계 §9):
  #1 키워드 모드: 알려진 노트를 top-3에 인출
  #2 파일 모드: exact-match + 합성 KnowledgeNote fixture
  #3 3종 frontmatter 수용 (KnowledgeNote/레거시/무)
  #4 결정론: 동일 쿼리 2회 = 바이트 동일 출력
  #5 read-only: open('w')/write/unlink/mkdir 0건 grep (INV-R4)
  #6 두 진입점 dispatch 등록 확인 (agent_launcher + run_factory_cli)
  #7 크로스OS / 한글 경로 노트 검색
"""
from __future__ import annotations

import io
import json
import re
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# fixture 헬퍼
# ---------------------------------------------------------------------------

_KNOWLEDGE_NOTE_MD = textwrap.dedent("""\
---
id: session/TEST-machine-000000-aaa000-test-note.md
type: session
scope: project
title: Router Research Decoupling 결정
author: testuser
source_machine: TEST-machine
created_commit: aabbccd
created_at: 2026-06-25T00:00:00+00:00
visibility: private
links: []
---

라우터의 scope/research decoupling 4-phase 계획을 결정함.

## 정밀 참조 (verbatim, INV-K5)

- core/right_sized_router.py:234
- aabbccd
- INV-R3
""")

_LEGACY_MEMORY_MD = textwrap.dedent("""\
---
name: router-scope-decoupling
description: Router scope와 research 결합 해소 계획 문서
metadata:
  node_type: feedback
  type: project
---

Router 내부 scope 처리와 research 결합 해소에 대한 설명.
""")

_NO_FRONTMATTER_MD = textwrap.dedent("""\
# 무-frontmatter 개념 노트

이 노트는 frontmatter 없이 마크다운 본문만 있는 예시다.
retrieval 테스트를 위한 샘플 내용.
""")


@pytest.fixture()
def vault_dir(tmp_path: Path) -> Path:
    """테스트용 임시 vault (3종 frontmatter 모두 포함)."""
    vr = tmp_path / "knowledge"
    (vr / "session").mkdir(parents=True)
    (vr / "patterns").mkdir(parents=True)
    (vr / "concepts").mkdir(parents=True)

    (vr / "session" / "test-note.md").write_text(_KNOWLEDGE_NOTE_MD, encoding="utf-8")
    (vr / "patterns" / "legacy-note.md").write_text(_LEGACY_MEMORY_MD, encoding="utf-8")
    (vr / "concepts" / "no-frontmatter.md").write_text(_NO_FRONTMATTER_MD, encoding="utf-8")
    return vr


# ---------------------------------------------------------------------------
# 임포트 (파일 생성 후)
# ---------------------------------------------------------------------------
from core.knowledge.retrieve import (
    NoteDoc,
    _parse_frontmatter,
    format_results,
    load_notes,
    score_notes,
    main as retrieve_main,
)


# ---------------------------------------------------------------------------
# §9 #3 — 3종 frontmatter 수용 (INV-R3)
# ---------------------------------------------------------------------------
class TestLoadNotes:
    def test_loads_all_three_formats(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        assert len(notes) == 3

    def test_knowledge_note_title(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        titles = {n.title for n in notes}
        assert "Router Research Decoupling 결정" in titles

    def test_legacy_memory_title_from_name(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        titles = {n.title for n in notes}
        assert "router-scope-decoupling" in titles

    def test_no_frontmatter_title_from_h1(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        titles = {n.title for n in notes}
        assert "무-frontmatter 개념 노트" in titles

    def test_parse_failure_still_indexed(self, vault_dir: Path) -> None:
        """깨진 frontmatter라도 본문 전문으로 인덱싱 (INV-R3)."""
        broken = vault_dir / "concepts" / "broken.md"
        broken.write_text("---\nbad:yaml:\n---\n본문 내용", encoding="utf-8")
        notes = load_notes(vault_dir)
        bodies = [n.body for n in notes]
        assert any("본문 내용" in b for b in bodies)

    def test_knowledge_note_type(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        session_note = next(n for n in notes if "session" in str(n.path))
        assert session_note.note_type == "session"

    def test_precise_ref_section_extracted(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        session_note = next(n for n in notes if "test-note.md" in str(n.path))
        assert "core/right_sized_router.py:234" in session_note.precise_ref_section

    def test_refs_extracted_from_body(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        session_note = next(n for n in notes if "test-note.md" in str(n.path))
        assert any("right_sized_router.py:234" in r for r in session_note.refs)


# ---------------------------------------------------------------------------
# §9 #1 — 키워드 모드 top-3 인출
# ---------------------------------------------------------------------------
class TestScoreNotesQuery:
    def test_keyword_top3(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("router research decoupling", [], notes)
        top3_titles = [r[0].title for r in ranked[:3]]
        assert "Router Research Decoupling 결정" in top3_titles

    def test_zero_score_excluded(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("XYZZY_NONEXISTENT_TERM_12345", [], notes)
        assert len(ranked) == 0

    def test_title_weighted_higher(self, vault_dir: Path) -> None:
        """title 매칭(가중 3)이 본문 매칭(가중 1)보다 점수 높음."""
        notes = load_notes(vault_dir)
        ranked = score_notes("Router Research Decoupling", [], notes)
        assert ranked[0][0].title == "Router Research Decoupling 결정"
        assert ranked[0][1] >= 9  # "router" + "research" + "decoupling" 각 3점 이상

    def test_empty_query_returns_all(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("", [], notes)
        assert len(ranked) == len(notes)


# ---------------------------------------------------------------------------
# §9 #2 — 파일 모드 exact-match (합성 fixture)
# ---------------------------------------------------------------------------
class TestScoreNotesFiles:
    def test_file_exact_match(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("", ["core/right_sized_router.py"], notes)
        matched = [r for r in ranked if r[1] > 0]
        assert len(matched) >= 1
        assert any("test-note.md" in str(r[0].path) for r in matched)

    def test_file_no_irrelevant_match(self, vault_dir: Path) -> None:
        """정밀참조 없는 노트는 파일 매칭 점수 0."""
        notes = load_notes(vault_dir)
        ranked = score_notes("", ["core/some_unrelated_file.py"], notes)
        matched = [r for r in ranked if r[1] > 0]
        assert len(matched) == 0

    def test_basename_match(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        # right_sized_router.py basename만으로도 매칭
        ranked = score_notes("", ["some/other/path/right_sized_router.py"], notes)
        matched = [r for r in ranked if r[1] > 0]
        assert len(matched) >= 1

    def test_query_and_files_combined(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("router", ["core/right_sized_router.py"], notes)
        # 쿼리+파일 동시 매칭 = 더 높은 점수
        top = ranked[0]
        assert top[0].title == "Router Research Decoupling 결정"
        assert top[1] >= 8  # 쿼리+파일 합산


# ---------------------------------------------------------------------------
# §9 #4 — 결정론: 동일 쿼리 2회 = 바이트 동일
# ---------------------------------------------------------------------------
class TestDeterminism:
    def test_identical_output_twice(self, vault_dir: Path) -> None:
        notes1 = load_notes(vault_dir)
        notes2 = load_notes(vault_dir)
        r1 = score_notes("router", [], notes1)
        r2 = score_notes("router", [], notes2)
        out1 = format_results(r1)
        out2 = format_results(r2)
        assert out1 == out2

    def test_determinism_json(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        r1 = score_notes("research", [], notes)
        r2 = score_notes("research", [], notes)
        j1 = format_results(r1, as_json=True)
        j2 = format_results(r2, as_json=True)
        assert j1 == j2


# ---------------------------------------------------------------------------
# §9 #5 — read-only (INV-R4): retrieve.py에 write 경로 없음
# ---------------------------------------------------------------------------
class TestReadOnly:
    def test_no_write_calls_in_source(self) -> None:
        src = Path(__file__).parent.parent / "core" / "knowledge" / "retrieve.py"
        text = src.read_text(encoding="utf-8")
        # open(..., 'w') / .write() / .unlink() / .mkdir() 금지
        assert not re.search(r"open\([^)]*['\"]w['\"]", text), "open('w') 발견"
        assert not re.search(r"\.unlink\(", text), ".unlink() 발견"
        assert not re.search(r"\.mkdir\(", text), ".mkdir() 발견"
        # .write_text / .write_bytes 금지 (read_text는 허용)
        assert not re.search(r"\.write_text\(", text), ".write_text() 발견"
        assert not re.search(r"\.write_bytes\(", text), ".write_bytes() 발견"


# ---------------------------------------------------------------------------
# §9 #6 — 두 진입점 dispatch 등록 확인
# ---------------------------------------------------------------------------
class TestTwoEntrypoints:
    def test_agent_launcher_known_subcommands(self) -> None:
        src = Path(__file__).parent.parent / "agent_launcher.py"
        text = src.read_text(encoding="utf-8")
        assert '"knowledge"' in text or "'knowledge'" in text

    def test_run_factory_cli_dispatch(self) -> None:
        src = Path(__file__).parent.parent / "run_factory_cli.py"
        text = src.read_text(encoding="utf-8")
        assert '"knowledge"' in text or "'knowledge'" in text

    def test_agent_launcher_knowledge_handler(self) -> None:
        src = Path(__file__).parent.parent / "agent_launcher.py"
        text = src.read_text(encoding="utf-8")
        assert "knowledge_search_main" in text or "knowledge" in text

    def test_run_factory_cli_knowledge_handler(self) -> None:
        src = Path(__file__).parent.parent / "run_factory_cli.py"
        text = src.read_text(encoding="utf-8")
        assert "_run_knowledge_subcommand" in text


# ---------------------------------------------------------------------------
# §9 #7 — 한글 경로 노트 검색
# ---------------------------------------------------------------------------
class TestCrossOS:
    def test_korean_filename_note(self, vault_dir: Path) -> None:
        """한글 파일명 노트도 정상 인덱싱·검색."""
        korean_file = vault_dir / "concepts" / "한글파일명테스트.md"
        korean_file.write_text(
            "# 한글 제목\n\n한글 내용 포함 노트. router 관련 내용.",
            encoding="utf-8",
        )
        notes = load_notes(vault_dir)
        titled = [n for n in notes if "한글 제목" in n.title]
        assert len(titled) == 1

    def test_korean_query(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("무-frontmatter", [], notes)
        assert len(ranked) >= 1
        assert any("no-frontmatter" in str(r[0].path) for r in ranked)

    def test_import_succeeds_on_current_os(self) -> None:
        """현재 OS에서 모듈 import 성공."""
        import importlib
        mod = importlib.import_module("core.knowledge.retrieve")
        assert hasattr(mod, "load_notes")
        assert hasattr(mod, "score_notes")
        assert hasattr(mod, "format_results")
        assert hasattr(mod, "main")


# ---------------------------------------------------------------------------
# format_results 기본 동작
# ---------------------------------------------------------------------------
class TestFormatResults:
    def test_empty_returns_no_result_message(self) -> None:
        assert "없음" in format_results([])

    def test_limit_applied(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("", [], notes)
        out = format_results(ranked, limit=1)
        # 2번째 노트는 출력되지 않아야 함
        assert "2." not in out

    def test_json_output_parseable(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("router", [], notes)
        out = format_results(ranked, as_json=True)
        data = json.loads(out)
        assert isinstance(data, list)
        if data:
            assert "path" in data[0]
            assert "score" in data[0]

    def test_text_output_has_score(self, vault_dir: Path) -> None:
        notes = load_notes(vault_dir)
        ranked = score_notes("router", [], notes)
        out = format_results(ranked)
        assert "score=" in out


# ---------------------------------------------------------------------------
# main() CLI 함수
# ---------------------------------------------------------------------------
class TestMain:
    def test_main_no_args_returns_0(self, vault_dir: Path) -> None:
        rc = retrieve_main(["--vault", str(vault_dir)])
        assert rc == 0

    def test_main_query(self, vault_dir: Path, capsys: pytest.CaptureFixture) -> None:
        rc = retrieve_main(["--query", "router", "--vault", str(vault_dir)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Router" in captured.out or "router" in captured.out

    def test_main_json(self, vault_dir: Path, capsys: pytest.CaptureFixture) -> None:
        rc = retrieve_main(["--query", "router", "--vault", str(vault_dir), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)

    def test_main_missing_vault_returns_1(self, tmp_path: Path) -> None:
        rc = retrieve_main(["--query", "x", "--vault", str(tmp_path / "nonexistent")])
        assert rc == 1

    def test_main_limit(self, vault_dir: Path, capsys: pytest.CaptureFixture) -> None:
        rc = retrieve_main(["--query", "router", "--vault", str(vault_dir), "--limit", "1"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "2." not in out
