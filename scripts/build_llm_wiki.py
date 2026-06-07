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
    from scripts.codebase_symbols import build as _cs_build
except ModuleNotFoundError:
    from codebase_symbols import build as _cs_build

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


def _slugify_blueprint_heading(heading: str) -> str:
    if heading == "목차":
        return "toc"
    if heading == "유지보수 가이드":
        return "maintenance-guide"
    if heading.startswith("§"):
        section_id = heading.split(maxsplit=1)[0]
        return "section-" + section_id.removeprefix("§").replace(".", "-")
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", "-", heading).strip("-").lower()
    return normalized or "section"


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


def _slugify_code_review_section(section_id: str) -> str:
    return "section-" + section_id.replace(".", "-")


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
        slug = _slugify_code_review_section(section_id)
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
def _build_index(workspace: str, sources: list[str]) -> str:
    fm = _make_frontmatter(workspace, sources)
    return (
        fm
        + "# LLM Wiki — Index\n\n"
        + "> AF 프로젝트 지식 뷰 (generated view — 원본 수정 금지).\n"
        + "> 원본: Master_Blueprint.md / docs/code_review/code-review.md / NEXT_STEPS.md\n\n"
        + "## 페이지 목록\n\n"
        + "- [[architecture]] — 모듈 구조 + 서브시스템 네비게이션\n"
        + "- [[review_patterns]] — 서브시스템별 코드 리뷰 패턴\n"
        + "- [[open_items]] — 미완료/보류 항목 (best-effort)\n"
        + "- [[source_refs]] — 섹션 ↔ 원본 파일 경로 매핑\n"
        + "- [[blueprint/index]] — Master Blueprint 섹션별 전문\n"
        + "- [[code_review/index]] — Code Review 섹션별 전문\n"
        + "- [[symbols]] — 코드베이스 top-level 심볼 (AST 추출)\n\n"
        + "## 사용법\n\n"
        + "Obsidian에서 이 디렉터리를 vault로 열면 `[[...]]` 링크로 탐색 가능.\n"
        + "재생성: `python scripts/build_llm_wiki.py`\n\n"
        + "Source: scripts/build_llm_wiki.py\n"
    )


def _build_architecture(workspace: str, sources: list[str], bp: dict) -> str:
    fm = _make_frontmatter(workspace, sources)
    lines = [
        "# Architecture — 모듈 네비게이션\n",
        "> Source: Master_Blueprint.md §0 + §3\n",
        "> 관련: [[index]] | [[source_refs]]\n\n",
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


def _build_symbols(workspace: str, sources: list[str]) -> str:
    fm = _make_frontmatter(workspace, sources + ["scripts/codebase_symbols.py", "**/*.py"])
    header = (
        "> Source: scripts/codebase_symbols.py (AST 추출, read-only)\n"
        "> 관련: [[index]] | [[architecture]] | [[source_refs]]\n\n"
    )
    body = _cs_build(workspace)
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
                       bp: dict, cr_sections: list[dict],
                       blueprint_sections: list[dict] | None = None,
                       code_review_sections: list[dict] | None = None) -> str:
    fm = _make_frontmatter(workspace, sources)
    commit = _short_commit(workspace)
    lines = [
        "# Source References — 섹션 ↔ 원본 경로 매핑\n\n",
        f"> source_commit: `{commit}`\n",
        "> 관련: [[index]] | [[architecture]] | [[review_patterns]]\n\n",
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

    lines += [
        "\n## NEXT_STEPS.md\n\n",
        "| 항목 | 원본 경로 |\n",
        "|------|----------|\n",
        "| 미완료/보류 항목 | `NEXT_STEPS.md` (마커 기반 추출) |\n",
        "| 세션 재개 가이드 | `NEXT_STEPS.md:1` |\n",
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

    def _read(rel: str) -> str:
        return (Path(workspace) / rel).read_text(encoding="utf-8")

    bp_text = _read(_BLUEPRINT)
    cr_text = _read(_CODE_REVIEW)
    ns_text = _read(_NEXT_STEPS)

    bp = _parse_blueprint(bp_text)
    blueprint_sections = _split_blueprint_sections(bp_text)
    cr_sections = _parse_code_review(cr_text)
    code_review_sections = _split_code_review_sections(cr_text)
    open_items = _parse_open_items(ns_text)

    sources = [_BLUEPRINT, _CODE_REVIEW, _NEXT_STEPS]

    pages = {
        "index.md": _build_index(workspace, sources),
        "architecture.md": _build_architecture(workspace, sources, bp),
        "review_patterns.md": _build_review_patterns(workspace, sources, cr_sections),
        "open_items.md": _build_open_items(workspace, sources, open_items),
        "source_refs.md": _build_source_refs(workspace, sources, bp, cr_sections, blueprint_sections, code_review_sections),
        "symbols.md": _build_symbols(workspace, sources),
        "blueprint/index.md": _build_blueprint_index(workspace, blueprint_sections),
        "code_review/index.md": _build_code_review_index(workspace, code_review_sections),
    }
    for section in blueprint_sections:
        pages[f"blueprint/{section['slug']}.md"] = _build_blueprint_section(workspace, section)
    for section in code_review_sections:
        pages[f"code_review/{section['slug']}.md"] = _build_code_review_section(workspace, section)

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
