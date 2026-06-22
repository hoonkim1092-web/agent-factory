"""STAGE 0 Knowledge Wiki Builder 테스트.

핵심 검증:
- INV-K7: build_llm_wiki 재실행 후 knowledge/ 파일 무손실
- 분류 라우팅: metadata.type → 하위 폴더
- MOC 생성
- memory 없을 때 graceful degradation
"""

import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_knowledge_wiki import (
    _DEFAULT_WIKI_DIR,
    _get_memory_type,
    build,
)
from scripts.build_llm_wiki import _DEFAULT_OUT as _CODE_OUT, build as _code_build


# ---------------------------------------------------------------------------
# _get_memory_type
# ---------------------------------------------------------------------------
class TestGetMemoryType:
    def test_project_type(self):
        text = "---\nname: foo\nmetadata:\n  node_type: memory\n  type: project\n---\nbody"
        assert _get_memory_type(text) == "project"

    def test_feedback_type(self):
        text = "---\nname: bar\nmetadata:\n  type: feedback\n---\nbody"
        assert _get_memory_type(text) == "feedback"

    def test_user_type(self):
        text = "---\nmetadata:\n  type: user\n---\n"
        assert _get_memory_type(text) == "user"

    def test_reference_type(self):
        text = "---\nmetadata:\n  type: reference\n---\n"
        assert _get_memory_type(text) == "reference"

    def test_no_frontmatter(self):
        assert _get_memory_type("plain text") == ""

    def test_unknown_type(self):
        text = "---\nmetadata:\n  type: unknown_custom\n---\n"
        assert _get_memory_type(text) == "unknown_custom"

    def test_crlf_frontmatter(self):
        crlf = "---\r\nmetadata:\r\n  type: project\r\n---\r\nbody"
        assert _get_memory_type(crlf) == "project"

    def test_toplevel_crlf_frontmatter(self):
        crlf = "---\r\nname: foo\r\ntype: feedback\r\n---\r\nbody"
        assert _get_memory_type(crlf) == "feedback"


# ---------------------------------------------------------------------------
# 분류 라우팅
# ---------------------------------------------------------------------------
class TestClassification:
    def _make_memory(self, tmp_path: Path, name: str, note_type: str) -> Path:
        f = tmp_path / name
        f.write_text(
            f"---\nname: {name[:-3]}\nmetadata:\n  type: {note_type}\n---\nbody",
            encoding="utf-8",
        )
        return f

    def test_project_goes_to_sessions(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        self._make_memory(mem_dir, "my_project.md", "project")
        written = build(workspace=str(tmp_path), memory_dir=str(mem_dir))
        keys = [Path(p).parts for p in written]
        assert any("sessions" in parts for parts in keys)

    def test_feedback_goes_to_patterns(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        self._make_memory(mem_dir, "fb.md", "feedback")
        written = build(workspace=str(tmp_path), memory_dir=str(mem_dir))
        assert any("patterns" in Path(p).parts for p in written)

    def test_user_goes_to_concepts(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        self._make_memory(mem_dir, "usr.md", "user")
        written = build(workspace=str(tmp_path), memory_dir=str(mem_dir))
        assert any("concepts" in Path(p).parts for p in written)

    def test_reference_goes_to_concepts(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        self._make_memory(mem_dir, "ref.md", "reference")
        written = build(workspace=str(tmp_path), memory_dir=str(mem_dir))
        assert any("concepts" in Path(p).parts for p in written)

    def test_unknown_type_fallback_to_concepts(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        self._make_memory(mem_dir, "misc.md", "exotic_unknown")
        written = build(workspace=str(tmp_path), memory_dir=str(mem_dir))
        assert any("concepts" in Path(p).parts for p in written)

    def test_memory_index_skipped(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "MEMORY.md").write_text("# index\n", encoding="utf-8")
        written = build(workspace=str(tmp_path), memory_dir=str(mem_dir))
        # MEMORY.md 자체는 knowledge에 복사되지 않는다
        assert not any("MEMORY.md" in Path(p).name for p in written if "knowledge" in p)


# ---------------------------------------------------------------------------
# MOC 생성
# ---------------------------------------------------------------------------
class TestMOCGeneration:
    def test_moc_created(self, tmp_path):
        written = build(workspace=str(tmp_path), memory_dir=str(tmp_path / "nonexistent"))
        moc_paths = [p for p in written if Path(p).name == "MOC.md"]
        assert len(moc_paths) == 1

    def test_moc_contains_code_links(self, tmp_path):
        written = build(workspace=str(tmp_path), memory_dir=str(tmp_path / "nonexistent"))
        moc = next(v for k, v in written.items() if Path(k).name == "MOC.md")
        assert "[[code/" in moc

    def test_moc_contains_knowledge_links_when_memory_exists(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "a_note.md").write_text(
            "---\nmetadata:\n  type: feedback\n---\nbody", encoding="utf-8"
        )
        written = build(workspace=str(tmp_path), memory_dir=str(mem_dir))
        moc = next(v for k, v in written.items() if Path(k).name == "MOC.md")
        assert "[[knowledge/" in moc


# ---------------------------------------------------------------------------
# Memory 없을 때 graceful degradation
# ---------------------------------------------------------------------------
class TestNoMemoryDir:
    def test_no_memory_dir_still_creates_moc(self, tmp_path):
        written = build(workspace=str(tmp_path), memory_dir=str(tmp_path / "nonexistent"))
        assert any(Path(p).name == "MOC.md" for p in written)

    def test_no_memory_dir_no_knowledge_files(self, tmp_path):
        written = build(workspace=str(tmp_path), memory_dir=str(tmp_path / "nonexistent"))
        knowledge_files = [p for p in written if "knowledge" in p and Path(p).name != "MOC.md"]
        assert knowledge_files == []


# ---------------------------------------------------------------------------
# INV-K7: build_llm_wiki 재실행 후 knowledge/ 파일 무손실
# ---------------------------------------------------------------------------
class TestINVK7:
    """build_llm_wiki의 stale unlink는 out_dir(docs/wiki/code) 안에서만 동작한다.
    docs/wiki/knowledge/ 는 sibling 폴더라 절대 건드리지 않는다."""

    def test_knowledge_files_survive_code_wiki_rebuild(self, tmp_path):
        # 1) knowledge 파일 먼저 생성
        k_file = tmp_path / "docs" / "wiki" / "knowledge" / "sessions" / "sentinel.md"
        k_file.parent.mkdir(parents=True, exist_ok=True)
        sentinel_content = "# sentinel — must survive code wiki rebuild\n"
        k_file.write_text(sentinel_content, encoding="utf-8")

        # 2) code wiki 빌드 (workspace에 소스가 없으면 최소 pages만 생성)
        _code_build(workspace=str(tmp_path), out_dir=_CODE_OUT)

        # 3) knowledge 파일 무손실 확인
        assert k_file.exists(), "INV-K7 위반: build_llm_wiki가 knowledge/ 파일을 삭제했다"
        assert k_file.read_text(encoding="utf-8") == sentinel_content, (
            "INV-K7 위반: build_llm_wiki가 knowledge/ 파일을 수정했다"
        )

    def test_code_out_dir_does_not_overlap_knowledge(self, tmp_path):
        """_DEFAULT_OUT(code/)와 knowledge/ 경로가 물리적으로 분리됨을 확인."""
        code_out = Path(tmp_path) / _CODE_OUT
        knowledge_out = Path(tmp_path) / _DEFAULT_WIKI_DIR / "knowledge"
        # 한쪽이 다른 쪽의 부모/자식이 아니어야 함
        assert not code_out.is_relative_to(knowledge_out), (
            "code out_dir이 knowledge/ 안에 있으면 stale unlink가 knowledge를 삭제할 수 있다"
        )
        assert not knowledge_out.is_relative_to(code_out), (
            "knowledge/가 code out_dir 안에 있으면 stale unlink가 knowledge를 삭제할 수 있다"
        )


# ---------------------------------------------------------------------------
# 파일 내용 무결성
# ---------------------------------------------------------------------------
class TestContentIntegrity:
    def test_memory_content_copied_verbatim(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        original = textwrap.dedent("""\
            ---
            name: precise_ref
            metadata:
              type: project
            ---
            See `agent_runner.py:1226` commit `bf8ea506` INV-O1.
        """)
        (mem_dir / "precise_ref.md").write_text(original, encoding="utf-8")
        written = build(workspace=str(tmp_path), memory_dir=str(mem_dir))
        dest = next(v for k, v in written.items() if "precise_ref.md" in k)
        assert dest == original  # verbatim 복사 — 정밀참조 보존 (INV-K5)
