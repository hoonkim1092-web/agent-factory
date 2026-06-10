"""tests/test_build_llm_wiki.py — LLM Wiki Phase 0 빌더 invariant 테스트."""

import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

# 레포 루트 기준 import
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from scripts.build_llm_wiki import (
    _parse_blueprint,
    _split_blueprint_sections,
    _parse_code_review,
    _split_code_review_sections,
    _parse_open_items,
    build,
    _BLUEPRINT,
    _CODE_REVIEW,
    _NEXT_STEPS,
    _OPEN_MARKERS,
)

# ---------------------------------------------------------------------------
# 픽스처 — 최소 원본 텍스트
# ---------------------------------------------------------------------------
_SAMPLE_BLUEPRINT = """\
# Agent Factory — Master Blueprint
<!-- last_updated: 2026-06-07 | version: test -->

## §0 빠른 참조 테이블

### 루트 파일

| 파일 | 역할 | 주요 클래스/함수 |
|------|------|----------------|
| `agent_launcher.py` | AF 부트스트랩 | `AgentFactory` |

### core/ 파일

| 파일 | 역할 | 주요 클래스/함수 |
|------|------|----------------|
| `core/dogfood.py` | dogfood 파이프라인 | `run_all()` |

## §1 아키텍처 개요

## §3 핵심 서브시스템

### §3.1 ProjectPipeline (`core/project_pipeline.py`)

내용.

### §3.2 DynamicOrchestrator (`core/dynamic_orchestrator.py`)

내용.
"""

_SAMPLE_CODE_REVIEW = """\
# Agent Factory 전체 코드 리뷰

## 1. 프로젝트 통계

내용.

## 2. 서브시스템별 리뷰

### 2.1 실행 엔진 (Runtime Engine)

- 에이전트 Runner가 핵심.
- 비동기 실행 지원.

### 2.2 Control Plane

- Sidecar 패턴.
"""

_SAMPLE_NEXT_STEPS = """\
# NEXT_STEPS

> 다음 세션 진입점: 🚧 LLM Wiki Phase 1 보류 중
>
> 다음 작업 선정 대기

## 완료 항목

- ✅ dogfood 종료

## 미완료

- ❌ F10 git 맥락 주입 미완료
- 보류: cli_hook_bridge
"""


# ---------------------------------------------------------------------------
# 파서 단위 테스트
# ---------------------------------------------------------------------------
class TestParsers:
    def test_blueprint_extracts_root_rows(self):
        bp = _parse_blueprint(_SAMPLE_BLUEPRINT)
        assert any(r["path"] == "agent_launcher.py" for r in bp["root_rows"])

    def test_blueprint_extracts_core_rows(self):
        bp = _parse_blueprint(_SAMPLE_BLUEPRINT)
        assert any(r["path"] == "core/dogfood.py" for r in bp["core_rows"])

    def test_blueprint_extracts_subsystems(self):
        bp = _parse_blueprint(_SAMPLE_BLUEPRINT)
        ids = [s["id"] for s in bp["subsystems"]]
        assert "§3.1" in ids
        assert "§3.2" in ids

    def test_blueprint_subsystem_has_file(self):
        bp = _parse_blueprint(_SAMPLE_BLUEPRINT)
        s31 = next(s for s in bp["subsystems"] if s["id"] == "§3.1")
        assert s31["file"] == "core/project_pipeline.py"

    def test_blueprint_sections_split_for_obsidian_pages(self):
        sections = _split_blueprint_sections(_SAMPLE_BLUEPRINT + "\n## 목차\n\n- item\n\n## 유지보수 가이드\n\n내용.\n")
        headings = [s["heading"] for s in sections]
        slugs = [s["slug"] for s in sections]
        assert "목차" in headings
        assert "개요" in headings
        assert "§0 빠른 참조 테이블" in headings
        assert "§1 아키텍처 개요" in headings
        assert "§3 핵심 서브시스템" in headings
        assert "유지보수 가이드" in headings
        assert "overview" in slugs
        assert "toc" in slugs
        assert "0-빠른-참조-테이블" in slugs
        assert "1-아키텍처-개요" in slugs
        assert "3-핵심-서브시스템" in slugs
        assert "maintenance-guide" in slugs

    def test_code_review_extracts_sections(self):
        sections = _parse_code_review(_SAMPLE_CODE_REVIEW)
        ids = [s["id"] for s in sections]
        assert "2.1" in ids
        assert "2.2" in ids

    def test_code_review_first_bullet(self):
        sections = _parse_code_review(_SAMPLE_CODE_REVIEW)
        s21 = next(s for s in sections if s["id"] == "2.1")
        assert "Runner" in s21["first_bullet"]

    def test_code_review_has_line_number(self):
        sections = _parse_code_review(_SAMPLE_CODE_REVIEW)
        for s in sections:
            assert s["line"] > 0

    def test_code_review_sections_split_for_obsidian_pages(self):
        sections = _split_code_review_sections(_SAMPLE_CODE_REVIEW)
        slugs = [s["slug"] for s in sections]
        assert "2-1-실행-엔진-runtime-engine" in slugs
        assert "2-2-control-plane" in slugs
        assert any("Runtime Engine" in s["content"] for s in sections)

    def test_code_review_duplicate_section_ids_get_unique_slugs(self):
        sections = _split_code_review_sections(
            "### 2.1 First\n\nA\n\n### 2.1 Second\n\nB\n"
        )
        assert [s["slug"] for s in sections] == ["2-1-first", "2-1-second"]

    def test_open_items_extracts_markers(self):
        items = _parse_open_items(_SAMPLE_NEXT_STEPS)
        texts = [i["text"] for i in items]
        # ❌, 보류, 🚧 포함 라인이 잡혀야 함
        assert any("❌" in t or "보류" in t or "🚧" in t for t in texts)

    def test_open_items_excludes_completed(self):
        items = _parse_open_items(_SAMPLE_NEXT_STEPS)
        for item in items:
            assert "✅" not in item["text"], f"완료 항목이 섞임: {item['text']}"


# ---------------------------------------------------------------------------
# 빌더 통합 테스트
# ---------------------------------------------------------------------------
class TestBuild:
    def _build_with_samples(self, tmp_path: Path, out_sub: str = "wiki") -> dict:
        """임시 워크스페이스에 샘플 원본을 넣고 build() 실행."""
        (tmp_path / "Master_Blueprint.md").write_text(_SAMPLE_BLUEPRINT, encoding="utf-8")
        (tmp_path / "docs" / "code_review").mkdir(parents=True, exist_ok=True)
        (tmp_path / "docs" / "code_review" / "code-review.md").write_text(
            _SAMPLE_CODE_REVIEW, encoding="utf-8"
        )
        (tmp_path / "NEXT_STEPS.md").write_text(_SAMPLE_NEXT_STEPS, encoding="utf-8")
        return build(workspace=str(tmp_path), out_dir=out_sub)

    def _generated_files(self, root: Path) -> list[Path]:
        return sorted(p for p in root.rglob("*.md") if p.is_file())

    # --- 기본 6개 + Blueprint 섹션 페이지 생성 ---
    def test_expected_pages_generated(self, tmp_path):
        pages = self._build_with_samples(tmp_path)
        assert len(pages) == 14

    def test_all_expected_files_exist(self, tmp_path):
        self._build_with_samples(tmp_path)
        out = tmp_path / "wiki"
        for name in ("index.md", "architecture.md", "review_patterns.md",
                     "open_items.md", "source_refs.md", "symbols.md"):
            assert (out / name).exists(), f"{name} 미생성"
        for name in (
            "index.md",
            "overview.md",
            "0-빠른-참조-테이블.md",
            "1-아키텍처-개요.md",
            "3-핵심-서브시스템.md",
        ):
            assert (out / "blueprint" / name).exists(), f"blueprint/{name} 미생성"

    def test_blueprint_overview_contains_preamble(self, tmp_path):
        self._build_with_samples(tmp_path)
        overview = (tmp_path / "wiki" / "blueprint" / "overview.md").read_text(encoding="utf-8")
        index = (tmp_path / "wiki" / "blueprint" / "index.md").read_text(encoding="utf-8")

        assert "# Agent Factory — Master Blueprint" in overview
        assert "version: test" in overview
        assert "[[blueprint/overview|개요]]" in index

    def test_code_review_expected_files_exist(self, tmp_path):
        self._build_with_samples(tmp_path)
        out = tmp_path / "wiki" / "code_review"
        for name in ("index.md", "2-1-실행-엔진-runtime-engine.md", "2-2-control-plane.md"):
            assert (out / name).exists(), f"code_review/{name} missing"

    def test_blueprint_section_pages_contain_source_content(self, tmp_path):
        self._build_with_samples(tmp_path)
        section = (tmp_path / "wiki" / "blueprint" / "0-빠른-참조-테이블.md").read_text(encoding="utf-8")
        index = (tmp_path / "wiki" / "blueprint" / "index.md").read_text(encoding="utf-8")
        source_refs = (tmp_path / "wiki" / "source_refs.md").read_text(encoding="utf-8")

        assert "Master_Blueprint.md:" in section
        assert "````markdown" in section
        assert "## §0 빠른 참조 테이블" in section
        assert "`agent_launcher.py`" in section
        assert "[[blueprint/0-빠른-참조-테이블|§0 빠른 참조 테이블]]" in index
        assert "[[blueprint/0-빠른-참조-테이블]]" in source_refs

    def test_stale_blueprint_generated_pages_are_removed(self, tmp_path):
        stale_dir = tmp_path / "wiki" / "blueprint"
        stale_dir.mkdir(parents=True)
        stale = stale_dir / "old-section.md"
        stale.write_text("stale", encoding="utf-8")

        self._build_with_samples(tmp_path)

        assert not stale.exists()

    def test_code_review_section_pages_contain_source_content(self, tmp_path):
        self._build_with_samples(tmp_path)
        section = (tmp_path / "wiki" / "code_review" / "2-1-실행-엔진-runtime-engine.md").read_text(encoding="utf-8")
        index = (tmp_path / "wiki" / "code_review" / "index.md").read_text(encoding="utf-8")
        source_refs = (tmp_path / "wiki" / "source_refs.md").read_text(encoding="utf-8")
        root_index = (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")

        assert "docs/code_review/code-review.md:" in section
        assert "````markdown" in section
        assert "### 2.1" in section
        assert "Runner" in section
        assert "[[code_review/2-1-실행-엔진-runtime-engine|" in index
        assert "[[code_review/2-1-실행-엔진-runtime-engine]]" in source_refs
        assert "[[code_review/index]]" in root_index

    def test_stale_code_review_generated_pages_are_removed(self, tmp_path):
        stale_dir = tmp_path / "wiki" / "code_review"
        stale_dir.mkdir(parents=True)
        stale = stale_dir / "old-section.md"
        stale.write_text("stale", encoding="utf-8")

        self._build_with_samples(tmp_path)

        assert not stale.exists()

    def test_symbols_page_contains_ast_content(self, tmp_path):
        """symbols.md는 AST 추출 심볼을 포함한다 — 실제 .py fixture로 검증."""
        # .py 파일을 workspace에 추가해 _cs_build()가 실제 심볼을 추출하도록 한다
        (tmp_path / "sample_mod.py").write_text(
            "class WikiEngine:\n    pass\n\ndef wiki_run():\n    return 1\n",
            encoding="utf-8",
        )
        self._build_with_samples(tmp_path)
        symbols = (tmp_path / "wiki" / "symbols.md").read_text(encoding="utf-8")
        assert "Codebase Symbols" in symbols
        assert "[[index]]" in symbols
        # _cs_build()가 실제로 연결돼 심볼을 추출했는지 확인
        assert "sample_mod.py" in symbols
        assert "WikiEngine" in symbols
        assert "wiki_run" in symbols
        assert "scripts/codebase_symbols.py" in symbols
        assert "**/*.py" in symbols

    def test_source_refs_includes_symbols_sources(self, tmp_path):
        self._build_with_samples(tmp_path)
        source_refs = (tmp_path / "wiki" / "source_refs.md").read_text(encoding="utf-8")
        assert "Codebase Symbols" in source_refs
        assert "scripts/codebase_symbols.py" in source_refs
        assert "**/*.py" in source_refs

    def test_frontmatter_quotes_glob_sources(self, tmp_path):
        self._build_with_samples(tmp_path)
        symbols = (tmp_path / "wiki" / "symbols.md").read_text(encoding="utf-8")
        assert '- "**/*.py"' in symbols
        assert "- **/*.py" not in symbols

    # --- source reference ---
    def test_each_page_has_source_ref(self, tmp_path):
        self._build_with_samples(tmp_path)
        out = tmp_path / "wiki"
        for fname in self._generated_files(out):
            content = fname.read_text(encoding="utf-8")
            assert "Source" in content, f"{fname.name}에 Source ref 없음"

    # --- wikilink ---
    def test_each_page_has_wikilink(self, tmp_path):
        self._build_with_samples(tmp_path)
        out = tmp_path / "wiki"
        wikilink_re = re.compile(r"\[\[[^\]]+\]\]")
        for fname in self._generated_files(out):
            content = fname.read_text(encoding="utf-8")
            assert wikilink_re.search(content), f"{fname.name}에 [[wikilink]] 없음"

    # --- frontmatter ---
    def test_frontmatter_present(self, tmp_path):
        self._build_with_samples(tmp_path)
        out = tmp_path / "wiki"
        for fname in self._generated_files(out):
            content = fname.read_text(encoding="utf-8")
            assert content.startswith("---"), f"{fname.name} frontmatter 없음"
            assert "generated_at:" in content
            assert "sources:" in content

    # --- 원본 무수정 ---
    def test_originals_not_modified(self, tmp_path):
        blueprint = tmp_path / "Master_Blueprint.md"
        cr = tmp_path / "docs" / "code_review" / "code-review.md"
        ns = tmp_path / "NEXT_STEPS.md"

        self._build_with_samples(tmp_path)

        assert blueprint.read_text(encoding="utf-8") == _SAMPLE_BLUEPRINT
        assert cr.read_text(encoding="utf-8") == _SAMPLE_CODE_REVIEW
        assert ns.read_text(encoding="utf-8") == _SAMPLE_NEXT_STEPS

    # --- body 결정성 (generated_at 제외) ---
    def test_body_deterministic(self, tmp_path):
        """같은 입력으로 두 번 실행하면 body(frontmatter 제외)가 동일."""
        def _body(text: str) -> str:
            # frontmatter(--- ... ---\n\n) 제거
            if text.startswith("---"):
                end = text.index("---", 3) + 3
                return text[end:].lstrip("\n")
            return text

        self._build_with_samples(tmp_path, out_sub="wiki1")
        run1 = {
            p.relative_to(tmp_path / "wiki1").as_posix(): _body(p.read_text(encoding="utf-8"))
            for p in self._generated_files(tmp_path / "wiki1")
        }
        self._build_with_samples(tmp_path, out_sub="wiki2")
        run2 = {
            p.relative_to(tmp_path / "wiki2").as_posix(): _body(p.read_text(encoding="utf-8"))
            for p in self._generated_files(tmp_path / "wiki2")
        }
        for fname, body in run1.items():
            assert body == run2[fname], f"{fname} body가 두 실행 간 다름"

    # --- generated_at ISO 포맷 ---
    def test_generated_at_is_iso_format(self, tmp_path):
        self._build_with_samples(tmp_path)
        iso_re = re.compile(r"generated_at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        out = tmp_path / "wiki"
        for fname in self._generated_files(out):
            content = fname.read_text(encoding="utf-8")
            assert iso_re.search(content), f"{fname.name}의 generated_at 포맷 이상"
