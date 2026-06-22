"""STAGE 0 — Knowledge Vault Builder.

memory/*.md → docs/wiki/knowledge/{sessions,patterns,concepts}/
docs/wiki/MOC.md (Map of Content) 생성.

진화 기능 0줄 — 파일을 분류·복사해 Obsidian이 code wiki와 한 그래프로 볼 수 있게 한다.

Usage:
    python scripts/build_knowledge_wiki.py [--workspace .] [--memory-dir <path>] [--wiki-dir docs/wiki]
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
_DEFAULT_WIKI_DIR = "docs/wiki"
_KNOWLEDGE_SUBDIR = "knowledge"
_CODE_SUBDIR = "code"
_MOC_NAME = "MOC.md"

# memory frontmatter metadata.type → knowledge 하위 폴더
_TYPE_TO_SUBDIR: dict[str, str] = {
    "project": "sessions",
    "feedback": "patterns",
    "user": "concepts",
    "reference": "concepts",
}
_DEFAULT_SUBDIR = "concepts"

# 노이즈 세그먼트 (sync_claude_memory 패턴 재사용)
_NOISE_SEGMENTS = ("worktrees", "tmp", "temp", "test", "tests")


# ---------------------------------------------------------------------------
# memory 폴더 탐색
# ---------------------------------------------------------------------------
def _find_memory_dir(workspace: Path) -> Path | None:
    """~/.claude/projects/ 아래에서 workspace에 해당하는 memory/ 폴더를 찾는다."""
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.exists():
        return None

    try:
        project_dirs = list(claude_projects.iterdir())
    except (PermissionError, OSError):
        return None

    repo_key = workspace.name.lower().replace("-", "").replace("_", "")
    candidates: list[Path] = []

    for project_dir in project_dirs:
        if not project_dir.is_dir():
            continue
        try:
            encoded_key = project_dir.name.lower().replace("-", "").replace("_", "")
            if repo_key not in encoded_key:
                continue
            mem = project_dir / "memory"
            if mem.is_dir():
                candidates.append(mem)
        except (PermissionError, OSError):
            continue

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def _score(mem: Path) -> tuple[int, int]:
        name_lower = mem.parent.name.lower()
        noise = sum(1 for s in _NOISE_SEGMENTS if s in name_lower)
        return (noise, len(mem.parent.name))

    return min(candidates, key=_score)


# ---------------------------------------------------------------------------
# frontmatter 파싱
# ---------------------------------------------------------------------------
def _get_memory_type(text: str) -> str:
    """memory .md frontmatter의 type 값을 추출한다.

    두 가지 형식 지원:
      1. 중첩: metadata:\\n  type: project  (신규 format)
      2. 최상위: type: project              (구형 format)
    중첩 형식이 있으면 우선한다.
    """
    text = text.replace("\r\n", "\n")  # CRLF 정규화 (Windows 파일 호환)
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return ""
    fm = m.group(1)
    # 중첩 type (들여쓰기 있음)
    nested = re.search(r"^\s+type:\s*(\S+)", fm, re.MULTILINE)
    if nested:
        return nested.group(1)
    # 최상위 type (들여쓰기 없음)
    top = re.search(r"^type:\s*(\S+)", fm, re.MULTILINE)
    return top.group(1) if top else ""


# ---------------------------------------------------------------------------
# MOC 생성
# ---------------------------------------------------------------------------
def _build_moc(wiki_path: Path, knowledge_rel: str, code_rel: str) -> str:
    """docs/wiki/MOC.md 내용을 구성한다."""
    k_path = wiki_path / knowledge_rel
    section_lines: list[str] = []
    for subdir in ("sessions", "patterns", "concepts"):
        sub = k_path / subdir
        if not sub.is_dir():
            continue
        files = sorted(sub.glob("*.md"))
        if not files:
            continue
        section_lines.append(f"\n### {subdir.capitalize()}\n")
        for f in files:
            section_lines.append(f"- [[{knowledge_rel}/{subdir}/{f.stem}]]\n")

    knowledge_body = (
        "".join(section_lines)
        if section_lines
        else "_(비어 있음 — af project wiki 실행 후 채워짐)_\n"
    )

    return (
        f"# Map of Content (MOC)\n\n"
        f"> Obsidian vault root: `docs/wiki/`  \n"
        f"> `af project wiki` 로 재생성\n\n"
        f"## Code Wiki\n"
        f"- [[{code_rel}/index|Index]]\n"
        f"- [[{code_rel}/architecture|Architecture]]\n"
        f"- [[{code_rel}/symbols|Symbols]]\n\n"
        f"## Knowledge Vault\n"
        f"{knowledge_body}\n"
        f"---\n"
        f"*`[[{code_rel}/]]` ↔ `[[{knowledge_rel}/]]` 교차링크로 하나의 Obsidian 그래프*\n"
    )


# ---------------------------------------------------------------------------
# 메인 빌드 함수
# ---------------------------------------------------------------------------
def build(
    workspace: str = ".",
    memory_dir: str | None = None,
    wiki_dir: str = _DEFAULT_WIKI_DIR,
) -> dict[str, str]:
    """
    memory/*.md → docs/wiki/knowledge/ 분류 복사 + MOC.md 생성.

    반환: {절대 파일 경로 → 파일 내용}
    INV-K7: out_dir(knowledge/)는 build_llm_wiki의 code/ out_dir과 물리 분리 — 절대 겹치지 않는다.
    """
    ws = Path(workspace).resolve()
    wiki_path = ws / wiki_dir

    # memory 폴더 결정
    if memory_dir:
        mem_path = Path(memory_dir).resolve()
    else:
        mem_path = _find_memory_dir(ws)

    written: dict[str, str] = {}

    if not mem_path or not mem_path.is_dir():
        print(
            "[build_knowledge_wiki] memory dir not found — knowledge/ skipped.",
            file=sys.stderr,
        )
    else:
        k_out = wiki_path / _KNOWLEDGE_SUBDIR
        # auto-managed 하위 폴더 stale 파일 정리 (이전 분류 결과 제거, 중복 제거)
        for auto_subdir in set(_TYPE_TO_SUBDIR.values()):
            sub = k_out / auto_subdir
            if sub.is_dir():
                for stale in sub.glob("*.md"):
                    stale.unlink()
        for md_file in sorted(mem_path.glob("*.md")):
            if md_file.name == "MEMORY.md":
                continue
            text = md_file.read_text(encoding="utf-8")
            note_type = _get_memory_type(text)
            subdir = _TYPE_TO_SUBDIR.get(note_type, _DEFAULT_SUBDIR)
            target = k_out / subdir / md_file.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            written[str(target)] = text

    # MOC 생성 (memory 없어도 code/ 링크는 넣는다)
    moc_content = _build_moc(wiki_path, _KNOWLEDGE_SUBDIR, _CODE_SUBDIR)
    moc_path = wiki_path / _MOC_NAME
    moc_path.parent.mkdir(parents=True, exist_ok=True)
    moc_path.write_text(moc_content, encoding="utf-8")
    written[str(moc_path)] = moc_content

    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Vault Builder (STAGE 0)")
    parser.add_argument("--workspace", default=".", help="repo root")
    parser.add_argument("--memory-dir", default=None, help="memory/ 폴더 경로 (미지정 시 자동 탐색)")
    parser.add_argument("--wiki-dir", default=_DEFAULT_WIKI_DIR, help="vault root (workspace 상대)")
    args = parser.parse_args()

    written = build(workspace=args.workspace, memory_dir=args.memory_dir, wiki_dir=args.wiki_dir)
    for path in sorted(written):
        print(f"  wrote: {path}")
    print(f"done - {len(written)} files")


if __name__ == "__main__":
    main()
