"""LLM Wiki Phase 0 — 결정적(무-LLM) knowledge view 생성기.

원본 문서(Master_Blueprint.md / docs/code_review/code-review.md / NEXT_STEPS.md)를
read-only로 파싱해 docs/generated/llm_wiki/ 에 5개 Markdown 파일을 생성한다.

원본 문서는 수정하지 않는다. 생성물은 원본에서 파생된 view이며 원본을 대체하지 않는다.

Usage:
    python scripts/build_llm_wiki.py [--workspace .] [--out docs/generated/llm_wiki]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.codebase_symbols import collect_symbols as _cs_collect, render as _cs_render
except ModuleNotFoundError:
    from codebase_symbols import collect_symbols as _cs_collect, render as _cs_render

# ---------------------------------------------------------------------------
# 경로 상수 (POSIX 슬래시 리터럴 — OS 무관 frontmatter 안정성)
# ---------------------------------------------------------------------------
_DEFAULT_OUT = "docs/generated/llm_wiki"
_BLUEPRINT = "Master_Blueprint.md"
_CODE_REVIEW = "docs/code_review/code-review.md"
_NEXT_STEPS = "NEXT_STEPS.md"

# NEXT_STEPS 미완료 마커
_OPEN_MARKERS = ("🚧", "보류", "❌", "⚠️", "대기", "다음", "TODO", "WIP")


# ---------------------------------------------------------------------------
# git 헬퍼 (blueprint_updater 패턴 재사용)
# ---------------------------------------------------------------------------
def _git(args: list[str], cwd: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _short_commit(workspace: str) -> str:
    out = _git(["rev-parse", "--short", "HEAD"], cwd=workspace)
    return out.strip() or "unknown"


# ---------------------------------------------------------------------------
# frontmatter 생성
# ---------------------------------------------------------------------------
def _make_frontmatter(workspace: str, sources: list[str]) -> str:
    commit = _short_commit(workspace)
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    src_lines = "\n".join(f"  - {json.dumps(s, ensure_ascii=False)}" for s in sources)
    return f"---\ngenerated_at: {now}\nsource_commit: {commit}\nsources:\n{src_lines}\n---\n\n"


# ---------------------------------------------------------------------------
# 파서 — Master_Blueprint.md
# ---------------------------------------------------------------------------
def _parse_blueprint(text: str) -> dict:
    """§0 테이블 행과 §3.x 서브시스템 헤더를 추출한다."""
    result: dict = {"root_rows": [], "core_rows": [], "subsystems": []}

    # §0 테이블 행 파싱: | `file` | 역할 | 클래스 |
    # §0 블록만 슬라이스해 다른 섹션 헤더 오염 방지
    sec0_match = re.search(r"^## §0 ", text, re.MULTILINE)
    sec1_match = re.search(r"^## §1 ", text, re.MULTILINE)
    if not sec0_match:
        print("[build_llm_wiki] WARNING: §0 섹션을 찾지 못했습니다 — architecture.md 테이블이 비어있을 수 있습니다.", file=sys.stderr)
        sec0_text = ""
    else:
        sec0_text = text[sec0_match.start(): sec1_match.start() if sec1_match else len(text)]

    table_re = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
    section = ""
    for line in sec0_text.splitlines():
        if "### 루트 파일" in line:
            section = "root"
        elif "### core/ 파일" in line:
            section = "core"
        elif re.match(r"^## §", line):
            section = ""
        if section and (m := table_re.match(line)):
            path, role, funcs = m.group(1), m.group(2).strip(), m.group(3).strip()
            if path in ("파일", "---"):
                continue
            row = {"path": path, "role": role, "funcs": funcs}
            (result["root_rows"] if section == "root" else result["core_rows"]).append(row)

    # §3.x 서브시스템 헤더: ### §3.N Name (`file`)
    sub_re = re.compile(r"^### (§3\.\S+)\s+(.*?)(?:\s*\(`([^`]+)`\))?$")
    for line in text.splitlines():
        if m := sub_re.match(line):
            result["subsystems"].append({
                "id": m.group(1),
                "name": m.group(2).strip(),
                "file": m.group(3) or "",
            })

    return result


def _slug_text(text: str, fallback: str = "section") -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", "-", text).strip("-").lower()
    return normalized or fallback


def _slugify_blueprint_heading(heading: str) -> str:
    if heading == "목차":
        return "toc"
    if heading == "유지보수 가이드":
        return "maintenance-guide"
    if heading.startswith("§"):
        section_id = heading.split(maxsplit=1)[0]
        title = heading.split(maxsplit=1)[1] if len(heading.split(maxsplit=1)) > 1 else ""
        number = section_id.removeprefix("§").replace(".", "-")
        title_slug = _slug_text(title, fallback="section")
        return f"{number}-{title_slug}"
    return _slug_text(heading)


def _split_blueprint_sections(text: str) -> list[dict]:
    """Master_Blueprint.md의 ## 섹션을 Obsidian 페이지 단위로 분할한다."""
    lines = text.splitlines()
    matches = [
        (i, line)
        for i, line in enumerate(lines)
        if re.match(r"^##\s+", line)
    ]
    sections: list[dict] = []
    if matches and matches[0][0] > 0:
        preamble = "\n".join(lines[: matches[0][0]]).rstrip()
        if preamble:
            sections.append(
                {
                    "heading": "개요",
                    "slug": "overview",
                    "line": 1,
                    "content": preamble + "\n",
                }
            )
    seen: dict[str, int] = {}
    for pos, (start, heading_line) in enumerate(matches):
        end = matches[pos + 1][0] if pos + 1 < len(matches) else len(lines)
        heading = heading_line.removeprefix("##").strip()
        slug = _slugify_blueprint_heading(heading)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        content = "\n".join(lines[start:end]).rstrip() + "\n"
        sections.append(
            {
                "heading": heading,
                "slug": slug,
                "line": start + 1,
                "content": content,
            }
        )
    return sections


# ---------------------------------------------------------------------------
# 파서 — code-review.md
# ---------------------------------------------------------------------------
def _parse_code_review(text: str) -> list[dict]:
    """### 2.x 서브시스템 섹션 헤더와 첫 리스크 불릿을 추출한다."""
    section_re = re.compile(r"^### (\d+\.\d+)\s+(.+)$")
    bullet_re = re.compile(r"^\s*[-*]\s+(.+)")
    sections: list[dict] = []
    current: dict | None = None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if m := section_re.match(line):
            if current is not None:
                sections.append(current)
            current = {"id": m.group(1), "name": m.group(2).strip(), "first_bullet": "", "line": i + 1}
        elif current and not current["first_bullet"]:
            if m := bullet_re.match(line):
                current["first_bullet"] = m.group(1).strip()
    if current is not None:
        sections.append(current)
    return sections


def _slugify_code_review_section(section_id: str, heading: str = "") -> str:
    title = heading.split(maxsplit=1)[1] if len(heading.split(maxsplit=1)) > 1 else heading
    title_slug = _slug_text(title, fallback="section")
    return f"{section_id.replace('.', '-')}-{title_slug}"


def _split_code_review_sections(text: str) -> list[dict]:
    """Split docs/code_review/code-review.md into section pages for Obsidian."""
    lines = text.splitlines()
    matches = [
        (i, line)
        for i, line in enumerate(lines)
        if re.match(r"^###\s+\d+\.\d+\s+", line)
    ]
    sections: list[dict] = []
    seen: dict[str, int] = {}
    for pos, (start, heading_line) in enumerate(matches):
        end = matches[pos + 1][0] if pos + 1 < len(matches) else len(lines)
        heading = heading_line.removeprefix("###").strip()
        section_id = heading.split(maxsplit=1)[0]
        slug = _slugify_code_review_section(section_id, heading)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        sections.append(
            {
                "id": section_id,
                "heading": heading,
                "slug": slug,
                "line": start + 1,
                "content": "\n".join(lines[start:end]).rstrip() + "\n",
            }
        )
    return sections


# ---------------------------------------------------------------------------
# 파서 — NEXT_STEPS.md
# ---------------------------------------------------------------------------
def _parse_open_items(text: str) -> list[dict]:
    """미완료 마커가 포함된 라인을 추출한다 (best-effort)."""
    items: list[dict] = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if any(marker in stripped for marker in _OPEN_MARKERS):
            # 완료 표시(✅)가 함께 있으면 제외
            if "✅" not in stripped:
                items.append({"line": i, "text": stripped[:200]})
    return items


# ---------------------------------------------------------------------------
# 생성기 — 5개 페이지
# ---------------------------------------------------------------------------
# index 페이지 링크 정의 — (생성 파일 키, 표시 문구). 실제 생성된 페이지만 링크된다.
_INDEX_LINKS: list[tuple[str, str]] = [
    ("architecture.md", "[[architecture]] — 모듈 구조 + 서브시스템 네비게이션"),
    ("review_patterns.md", "[[review_patterns]] — 서브시스템별 코드 리뷰 패턴"),
    ("open_items.md", "[[open_items]] — 미완료/보류 항목 (best-effort)"),
    ("source_refs.md", "[[source_refs]] — 섹션 ↔ 원본 파일 경로 매핑"),
    ("blueprint/index.md", "[[blueprint/index]] — Master Blueprint 섹션별 전문"),
    ("code_review/index.md", "[[code_review/index]] — Code Review 섹션별 전문"),
    ("symbols.md", "[[symbols]] — 코드베이스 top-level 심볼 (AST 추출)"),
]


def _build_index(workspace: str, sources: list[str], generated: set[str]) -> str:
    fm = _make_frontmatter(workspace, sources)
    link_lines = "".join(
        f"- {desc}\n" for rel, desc in _INDEX_LINKS if rel in generated
    )
    return (
        fm
        + "# LLM Wiki — Index\n\n"
        + "> 프로젝트 지식 뷰 (generated view — 원본 수정 금지).\n\n"
        + "## 페이지 목록\n\n"
        + link_lines
        + "\n## 사용법\n\n"
        + "Obsidian에서 이 디렉터리를 vault로 열면 `[[...]]` 링크로 탐색 가능.\n"
        + "재생성: `python scripts/build_llm_wiki.py` 또는 `af project wiki <path>`\n\n"
        + "Source: scripts/build_llm_wiki.py\n"
    )


def _build_codebase_tree(symbols: dict) -> str:
    """AST 심볼 맵을 디렉터리별 모듈 navigation 섹션으로 렌더링한다 (결정적).

    외부 프로젝트(Blueprint 부재)에서도 코드 구조 navigation을 제공하는
    범용 view. ``codebase_symbols.collect_symbols`` 결과를 입력으로 받는다.
    """
    by_dir: dict[str, list[str]] = {}
    for rel in sorted(symbols):
        parent = Path(rel).parent.as_posix()
        directory = "(root)" if parent == "." else parent
        by_dir.setdefault(directory, []).append(rel)

    if not by_dir:
        return "_(Python 모듈을 찾지 못했습니다)_\n"

    lines: list[str] = []
    for directory in sorted(by_dir):
        mods = by_dir[directory]
        n_class = sum(len(symbols[m].get("classes", [])) for m in mods)
        n_func = sum(len(symbols[m].get("functions", [])) for m in mods)
        lines.append(f"### `{directory}`\n\n")
        lines.append(f"{len(mods)} modules · {n_class} classes · {n_func} functions\n\n")
        for m in mods:
            c = len(symbols[m].get("classes", []))
            f = len(symbols[m].get("functions", []))
            lines.append(f"- `{m}` — {c} class / {f} func\n")
        lines.append("\n")
    return "".join(lines)


def _build_architecture(workspace: str, sources: list[str], bp: dict | None, symbols: dict) -> str:
    fm = _make_frontmatter(workspace, sources)
    has_bp = bool(bp and (bp["root_rows"] or bp["core_rows"] or bp["subsystems"]))

    lines = ["# Architecture — 모듈 네비게이션\n"]
    if has_bp:
        lines += [
            "> Source: Master_Blueprint.md §0 + §3\n",
            "> 관련: [[index]] | [[symbols]] | [[source_refs]]\n\n",
            "## 루트 파일\n\n",
            "| 파일 | 역할 | Source |\n",
            "|------|------|--------|\n",
        ]
        for r in bp["root_rows"]:
            lines.append(f"| `{r['path']}` | {r['role']} | Master_Blueprint.md §0 |\n")

        lines += [
            "\n## core/ 주요 모듈\n\n",
            "| 파일 | 역할 | Source |\n",
            "|------|------|--------|\n",
        ]
        for r in bp["core_rows"]:
            lines.append(f"| `{r['path']}` | {r['role']} | Master_Blueprint.md §0 |\n")

        if bp["subsystems"]:
            lines += ["\n## §3 서브시스템\n\n",
                      "| ID | 이름 | 파일 | Source |\n",
                      "|----|------|------|--------|\n"]
            for s in bp["subsystems"]:
                lines.append(f"| {s['id']} | {s['name']} | `{s['file']}` | Master_Blueprint.md {s['id']} |\n")
    else:
        lines += [
            "> Source: scripts/codebase_symbols.py (AST 추출, read-only)\n",
            "> 관련: [[index]] | [[symbols]] | [[source_refs]]\n\n",
        ]

    lines += [
        "\n## 코드베이스 구조 (AST)\n\n",
        "> Source: scripts/codebase_symbols.py (read-only AST) — 디렉터리별 모듈/심볼\n\n",
    ]
    lines.append(_build_codebase_tree(symbols))

    return fm + "".join(lines)


def _build_review_patterns(workspace: str, sources: list[str], sections: list[dict]) -> str:
    fm = _make_frontmatter(workspace, sources)
    lines = [
        "# Review Patterns — 서브시스템별 리뷰 패턴\n\n",
        "> Source: docs/code_review/code-review.md §2.x\n",
        "> 관련: [[index]] | [[open_items]] | [[source_refs]]\n\n",
    ]
    for s in sections:
        src_ref = f"docs/code_review/code-review.md:{s['line']}"
        lines.append(f"## {s['id']} {s['name']}\n\n")
        if s["first_bullet"]:
            lines.append(f"- {s['first_bullet']}\n")
        lines.append(f"\nSource: `{src_ref}`\n\n")
    return fm + "".join(lines)


def _build_open_items(workspace: str, sources: list[str], items: list[dict]) -> str:
    fm = _make_frontmatter(workspace, sources)
    lines = [
        "# Open Items — 미완료/보류 항목\n\n",
        "> **주의**: 마커(`🚧`/`보류`/`❌`/`⚠️`) 기반 자동 추출 — 불완전할 수 있음.\n",
        "> 정확한 상태는 NEXT_STEPS.md 원본을 참조.\n",
        "> Source: NEXT_STEPS.md\n",
        "> 관련: [[index]] | [[review_patterns]] | [[source_refs]]\n\n",
    ]
    if not items:
        lines.append("(추출된 미완료 항목 없음)\n")
    else:
        for item in items:
            lines.append(f"- (L{item['line']}) {item['text']}\n")
    lines.append(f"\nSource: `NEXT_STEPS.md` ({len(items)}건 추출)\n")
    return fm + "".join(lines)


def _build_symbols(workspace: str, sources: list[str], symbols: dict) -> str:
    fm = _make_frontmatter(workspace, sources + ["scripts/codebase_symbols.py", "**/*.py"])
    header = (
        "> Source: scripts/codebase_symbols.py (AST 추출, read-only)\n"
        "> 관련: [[index]] | [[architecture]] | [[source_refs]]\n\n"
    )
    body = _cs_render(symbols)
    return fm + header + body


def _build_blueprint_index(workspace: str, sections: list[dict]) -> str:
    fm = _make_frontmatter(workspace, [_BLUEPRINT])
    lines = [
        "# Master Blueprint — Section Index\n\n",
        "> Source: Master_Blueprint.md 전체 섹션 분할\n",
        "> 관련: [[index]] | [[architecture]] | [[source_refs]]\n\n",
        "## Sections\n\n",
    ]
    for section in sections:
        lines.append(
            f"- [[blueprint/{section['slug']}|{section['heading']}]]"
            f" — `Master_Blueprint.md:{section['line']}`\n"
        )
    return fm + "".join(lines)


def _build_blueprint_section(workspace: str, section: dict) -> str:
    fm = _make_frontmatter(workspace, [_BLUEPRINT])
    return (
        fm
        + f"# {section['heading']}\n\n"
        + f"> Source: `Master_Blueprint.md:{section['line']}`\n"
        + "> 관련: [[blueprint/index]] | [[index]] | [[source_refs]]\n\n"
        + "````markdown\n"
        + section["content"]
        + "````\n"
    )


def _build_code_review_index(workspace: str, sections: list[dict]) -> str:
    fm = _make_frontmatter(workspace, [_CODE_REVIEW])
    lines = [
        "# Code Review 섹션 Index\n\n",
        "> Source: docs/code_review/code-review.md 섹션 mirror\n",
        "> 관련: [[index]] | [[review_patterns]] | [[source_refs]]\n\n",
        "## 섹션\n\n",
    ]
    for section in sections:
        lines.append(
            f"- [[code_review/{section['slug']}|{section['heading']}]]"
            f" - `docs/code_review/code-review.md:{section['line']}`\n"
        )
    return fm + "".join(lines)


def _build_code_review_section(workspace: str, section: dict) -> str:
    fm = _make_frontmatter(workspace, [_CODE_REVIEW])
    return (
        fm
        + f"# {section['heading']}\n\n"
        + f"> Source: `docs/code_review/code-review.md:{section['line']}`\n"
        + "> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]\n\n"
        + "````markdown\n"
        + section["content"]
        + "````\n"
    )


def _build_source_refs(workspace: str, sources: list[str],
                       bp: dict | None, cr_sections: list[dict],
                       blueprint_sections: list[dict] | None = None,
                       code_review_sections: list[dict] | None = None) -> str:
    fm = _make_frontmatter(workspace, sources)
    commit = _short_commit(workspace)
    lines = [
        "# Source References — 섹션 ↔ 원본 경로 매핑\n\n",
        f"> source_commit: `{commit}`\n",
        "> 관련: [[index]] | [[architecture]] | [[symbols]]\n\n",
    ]

    if bp:
        lines += [
            "## Master_Blueprint.md\n\n",
            "| 항목 | 원본 경로 |\n",
            "|------|----------|\n",
            "| §0 루트 파일 테이블 | `Master_Blueprint.md:§0 루트 파일` |\n",
            "| §0 core/ 파일 테이블 | `Master_Blueprint.md:§0 core/ 파일` |\n",
            "| 섹션별 전문 mirror | `blueprint/*.md` |\n",
        ]
        if blueprint_sections:
            for section in blueprint_sections:
                lines.append(
                    f"| {section['heading']} | `Master_Blueprint.md:{section['line']}`"
                    f" / [[blueprint/{section['slug']}]] |\n"
                )
        for s in bp["subsystems"]:
            lines.append(f"| {s['id']} {s['name']} | `Master_Blueprint.md:{s['id']}` |\n")

    if cr_sections:
        lines += [
            "\n## docs/code_review/code-review.md\n\n",
            "| 섹션 | 원본 경로 |\n",
            "|------|----------|\n",
            "| 섹션 mirror | `code_review/*.md` |\n",
        ]
        for s in cr_sections:
            mirror = ""
            if code_review_sections:
                match = next((section for section in code_review_sections if section["id"] == s["id"]), None)
                if match:
                    mirror = f" / [[code_review/{match['slug']}]]"
            lines.append(f"| §{s['id']} {s['name']} | `docs/code_review/code-review.md:{s['line']}`{mirror} |\n")

    if _NEXT_STEPS in sources:
        lines += [
            "\n## NEXT_STEPS.md\n\n",
            "| 항목 | 원본 경로 |\n",
            "|------|----------|\n",
            "| 미완료/보류 항목 | `NEXT_STEPS.md` (마커 기반 추출) |\n",
            "| 세션 재개 가이드 | `NEXT_STEPS.md:1` |\n",
        ]

    lines += [
        "\n## Codebase Symbols\n\n",
        "| 항목 | 원본 경로 |\n",
        "|------|----------|\n",
        "| AST 심볼 추출기 | `scripts/codebase_symbols.py` |\n",
        "| Python top-level classes/functions | `**/*.py` (runtime/cache/vendor 디렉터리 제외) |\n",
    ]
    return fm + "".join(lines)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def build(workspace: str = ".", out_dir: str = _DEFAULT_OUT) -> dict[str, str]:
    """5개 wiki 페이지를 생성해 반환한다 (파일 경로 → 내용). 파일은 out_dir에 저장."""
    workspace = str(Path(workspace).resolve())
    out_path = Path(workspace) / out_dir
    out_path.mkdir(parents=True, exist_ok=True)

    def _read_optional(rel: str) -> str | None:
        p = Path(workspace) / rel
        if not p.is_file():
            return None
        return p.read_text(encoding="utf-8")

    # AF 전용 문서는 존재할 때만 처리한다 (외부 프로젝트는 부재 — skip).
    bp_text = _read_optional(_BLUEPRINT)
    cr_text = _read_optional(_CODE_REVIEW)
    ns_text = _read_optional(_NEXT_STEPS)

    bp = _parse_blueprint(bp_text) if bp_text is not None else None
    blueprint_sections = _split_blueprint_sections(bp_text) if bp_text is not None else []
    cr_sections = _parse_code_review(cr_text) if cr_text is not None else []
    code_review_sections = _split_code_review_sections(cr_text) if cr_text is not None else []
    open_items = _parse_open_items(ns_text) if ns_text is not None else []

    # AST 심볼은 한 번만 수집해 symbols/architecture 페이지가 공유한다.
    symbols = _cs_collect(workspace)

    sources = [
        rel for rel, text in (
            (_BLUEPRINT, bp_text), (_CODE_REVIEW, cr_text), (_NEXT_STEPS, ns_text)
        ) if text is not None
    ]

    # 범용 페이지 (모든 프로젝트에서 생성) — index는 생성 확정 후 마지막에 추가.
    pages = {
        "architecture.md": _build_architecture(workspace, sources, bp, symbols),
        "source_refs.md": _build_source_refs(workspace, sources, bp, cr_sections, blueprint_sections, code_review_sections),
        "symbols.md": _build_symbols(workspace, sources, symbols),
    }
    # Blueprint 의존 페이지
    if bp is not None:
        pages["blueprint/index.md"] = _build_blueprint_index(workspace, blueprint_sections)
        for section in blueprint_sections:
            pages[f"blueprint/{section['slug']}.md"] = _build_blueprint_section(workspace, section)
    # code-review 의존 페이지
    if cr_text is not None:
        pages["review_patterns.md"] = _build_review_patterns(workspace, sources, cr_sections)
        pages["code_review/index.md"] = _build_code_review_index(workspace, code_review_sections)
        for section in code_review_sections:
            pages[f"code_review/{section['slug']}.md"] = _build_code_review_section(workspace, section)
    # NEXT_STEPS 의존 페이지
    if ns_text is not None:
        pages["open_items.md"] = _build_open_items(workspace, sources, open_items)

    # index는 실제 생성된 페이지만 적응적으로 링크한다.
    pages["index.md"] = _build_index(workspace, sources, set(pages.keys()))

    blueprint_out = out_path / "blueprint"
    if blueprint_out.exists():
        expected_blueprint = {
            (out_path / rel).resolve()
            for rel in pages
            if rel.startswith("blueprint/")
        }
        for stale in blueprint_out.glob("*.md"):
            if stale.resolve() not in expected_blueprint:
                stale.unlink()

    code_review_out = out_path / "code_review"
    if code_review_out.exists():
        expected_code_review = {
            (out_path / rel).resolve()
            for rel in pages
            if rel.startswith("code_review/")
        }
        for stale in code_review_out.glob("*.md"):
            if stale.resolve() not in expected_code_review:
                stale.unlink()

    for fname, content in pages.items():
        target = out_path / fname
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, target)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    return {str(out_path / k): v for k, v in pages.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Wiki Phase 0 builder")
    parser.add_argument("--workspace", default=".", help="repo root (default: .)")
    parser.add_argument("--out", default=_DEFAULT_OUT, help="output dir relative to workspace")
    args = parser.parse_args()
    pages = build(workspace=args.workspace, out_dir=args.out)
    for path in pages:
        print(f"  wrote: {path}")
    print(f"done - {len(pages)} pages")


if __name__ == "__main__":
    main()
