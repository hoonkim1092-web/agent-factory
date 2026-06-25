"""af knowledge link — knowledge 노트 ↔ code wiki 자동 wikilink 연결.

전략:
  1. symbols.md에서 파일명 집합 추출
  2. 각 노트에서 .py 파일 참조 추출
  3. symbols에 있는 파일 참조 → [[code/symbols]] 링크
  4. 같은 파일을 공유하는 session 노트끼리 → [[knowledge/session/X]] 링크
  5. --dry-run: 리포트만, --apply: 실제 write

보수 원칙: 오탐 < 누락. 기존 links[] 보존(append only).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_DEFAULT_VAULT_RELPATH = "docs/wiki/knowledge"
_SYMBOLS_RELPATH = "docs/wiki/code/symbols.md"

# 파일명.py 또는 path/to/file.py(:숫자) 패턴
_PY_REF_RE = re.compile(
    r"(?:[\w.\-/\\]+/)?(\w[\w.\-]*)\.py(?::\d+)?",
    re.IGNORECASE,
)
# frontmatter 블록 (첫 ---...---) 추출
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# links: [...] 줄 — greedy로 한 줄 전체를 잡아야 [[wikilink]] 중첩 대괄호 처리 가능
_LINKS_RE = re.compile(r"^(links:\s*)(\[.*\])\s*$", re.MULTILINE)
# 기존 wikilink [[...]]
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass
class LinkChange:
    note_path: Path
    new_links: list[str] = field(default_factory=list)
    reason: str = ""


# ---------------------------------------------------------------------------
# symbols.md 파싱
# ---------------------------------------------------------------------------

def _load_symbol_files(symbols_path: Path) -> set[str]:
    """symbols.md에서 파일명 집합 반환 (경로 포함, e.g. 'core/fsa_loop.py')."""
    if not symbols_path.exists():
        return set()
    text = symbols_path.read_text(encoding="utf-8")
    # ## `core/fsa_loop.py` → core/fsa_loop.py
    pat2 = re.compile(r"^## [`'](.+?)[`']", re.MULTILINE)
    found = set(pat2.findall(text))
    # 파일명만(basename) 역인덱스도 추가
    result: set[str] = set()
    for f in found:
        result.add(f)
        result.add(Path(f).name)  # basename도 매칭에 사용
    return result


# ---------------------------------------------------------------------------
# 노트 파싱
# ---------------------------------------------------------------------------

def _extract_py_refs(text: str, symbol_files: set[str]) -> set[str]:
    """노트 본문에서 symbols에 있는 .py 파일 참조 추출.

    full path 우선, 모호한 경우만 basename fallback.
    (basename을 먼저 체크하면 _load_symbol_files가 역인덱스를 포함하므로
    항상 basename으로 매칭되어 false cross-link가 발생한다.)
    """
    refs: set[str] = set()
    for m in _PY_REF_RE.finditer(text):
        # 전체 매칭 문자열에서 :숫자 제거
        full = m.group(0).split(":")[0]
        basename = m.group(1) + ".py"
        if full in symbol_files:
            refs.add(full)
        elif basename in symbol_files:
            refs.add(basename)
    return refs


def _existing_wikilinks(text: str) -> set[str]:
    """본문의 [[wikilink]] 집합 반환 — [[...]] 형식 포함."""
    return {"[[" + m + "]]" for m in _WIKILINK_RE.findall(text)}


def _parse_links_list(links_str: str) -> list[str]:
    """'["[[a]]", "[[b]]"]' 또는 '[[a]], [[b]]' → ['[[a]]', '[[b]]']"""
    s = links_str.strip()
    # bare wikilink (배열 아님): "[[code/symbols]]" → ["[[code/symbols]]"]
    if s.startswith("[[") and s.endswith("]]"):
        return [s]
    # 외부 [...] 배열 괄호 제거
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    if not s.strip():
        return []
    items = []
    for item in s.split(","):
        item = item.strip().strip('"').strip("'")
        if item:
            items.append(item)
    return items


def _format_links_list(links: list[str]) -> str:
    if not links:
        return "[]"
    quoted = ", ".join(f'"{lk}"' for lk in links)
    return f"[{quoted}]"


# ---------------------------------------------------------------------------
# 노트 업데이트
# ---------------------------------------------------------------------------

def _update_note(note_path: Path, new_links: list[str]) -> bool:
    """frontmatter links:에 new_links를 append하고 본문 끝에 ## 관련 섹션 추가.

    Returns True if file was modified.
    """
    text = note_path.read_text(encoding="utf-8")
    original = text

    # 먼저 기존 frontmatter links 파악 (중복 체크에 사용)
    existing_fm_links: list[str] = []
    fm_match = _FM_RE.match(text)
    if fm_match:
        fm_block = fm_match.group(0)
        links_m = _LINKS_RE.search(fm_block)
        if links_m:
            existing_fm_links = _parse_links_list(links_m.group(2))

    # 1) frontmatter links: 업데이트
    if fm_match:
        fm_block = fm_match.group(0)
        links_m = _LINKS_RE.search(fm_block)
        if links_m:
            merged = existing_fm_links[:]
            for lk in new_links:
                if lk not in merged:
                    merged.append(lk)
            new_fm = fm_block[: links_m.start()] + \
                links_m.group(1) + _format_links_list(merged) + \
                fm_block[links_m.end():]
            text = new_fm + text[len(fm_block):]

    # 2) 본문에 ## 관련 섹션 추가 (본문에 없는 링크만 — Obsidian 그래프는 본문 기준)
    # frontmatter를 제외한 본문만 스캔 (frontmatter 안의 [[link]] 오탐 방지)
    body_start = len(_FM_RE.match(text).group(0)) if _FM_RE.match(text) else 0
    body_wikilinks = _existing_wikilinks(text[body_start:])
    to_add = [lk for lk in new_links if lk not in body_wikilinks]
    if to_add:
        # 기존 ## 관련 섹션이 있으면 거기에 append
        rel_section = re.search(r"^## 관련\s*\n", text, re.MULTILINE)
        if rel_section:
            insert_at = rel_section.end()
            additions = "".join(f"- {lk}\n" for lk in to_add)
            text = text[:insert_at] + additions + text[insert_at:]
        else:
            additions = "\n## 관련\n" + "".join(f"- {lk}\n" for lk in to_add)
            text = text.rstrip("\n") + "\n" + additions + "\n"

    if text == original:
        return False
    note_path.write_text(text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# 연결 계산
# ---------------------------------------------------------------------------

def compute_links(
    vault: Path,
    symbol_files: set[str],
    symbols_link: str = "[[code/symbols]]",
) -> list[LinkChange]:
    """모든 노트에 대한 LinkChange 목록을 계산한다."""
    # 파일명 → 참조하는 노트들 역인덱스
    file_to_notes: dict[str, list[Path]] = defaultdict(list)
    note_refs: dict[Path, set[str]] = {}
    note_texts: dict[Path, str] = {}

    notes = list(vault.rglob("*.md"))
    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace")
        note_texts[note] = text
        refs = _extract_py_refs(text, symbol_files)
        note_refs[note] = refs
        for ref in refs:
            file_to_notes[ref].append(note)

    changes: list[LinkChange] = []

    for note in notes:
        refs = note_refs[note]
        if not refs:
            continue

        text = note_texts[note]
        # frontmatter 제외 본문만 스캔 (frontmatter 안 [[link]] 오탐 방지)
        fm_match = _FM_RE.match(text)
        body_start = len(fm_match.group(0)) if fm_match else 0
        existing_wl = _existing_wikilinks(text[body_start:])

        # frontmatter links 파싱
        existing_links: list[str] = []
        if fm_match:
            links_m = _LINKS_RE.search(fm_match.group(0))
            if links_m:
                existing_links = _parse_links_list(links_m.group(2))

        existing_set = set(existing_links) | existing_wl
        new_links: list[str] = []

        # symbols 연결
        if symbols_link not in existing_set:
            new_links.append(symbols_link)

        # 같은 파일을 참조하는 다른 session 노트 연결
        for ref in refs:
            for other in file_to_notes[ref]:
                if other == note:
                    continue
                # session 노트끼리만 (session/ 폴더)
                if "session" not in note.parts or "session" not in other.parts:
                    continue
                # vault root 기준 wikilink 경로
                try:
                    vault_root = vault.parent  # docs/wiki/
                    rel = other.relative_to(vault_root)
                    wl = "[[" + rel.with_suffix("").as_posix() + "]]"
                except ValueError:
                    continue
                if wl not in existing_set:
                    new_links.append(wl)

        # 중복 제거 (순서 유지)
        seen: set[str] = set()
        deduped: list[str] = []
        for lk in new_links:
            if lk not in seen:
                seen.add(lk)
                deduped.append(lk)

        if deduped:
            reasons = []
            if symbols_link in deduped:
                reasons.append(f"{len(refs)}개 파일 참조")
            peer_count = len(deduped) - (1 if symbols_link in deduped else 0)
            if peer_count:
                reasons.append(f"session 공유 {peer_count}건")
            changes.append(LinkChange(note, deduped, " + ".join(reasons)))

    return changes


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def run_linker(
    vault: Path,
    repo_root: str,
    dry_run: bool = True,
) -> list[LinkChange]:
    symbols_path = Path(repo_root) / _SYMBOLS_RELPATH
    symbol_files = _load_symbol_files(symbols_path)

    if not symbol_files:
        return []

    changes = compute_links(vault, symbol_files)

    if not dry_run:
        for ch in changes:
            _update_note(ch.note_path, ch.new_links)

    return changes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="af knowledge link")
    parser.add_argument("--vault", default="", help="vault 경로 (기본: docs/wiki/knowledge)")
    parser.add_argument("--repo", default="", help="repo root (기본: cwd)")
    parser.add_argument("--apply", action="store_true", help="실제 write (기본 dry-run)")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv)

    repo_root = args.repo or str(Path(".").resolve())
    vault_path = Path(args.vault) if args.vault else Path(repo_root) / _DEFAULT_VAULT_RELPATH

    if not vault_path.exists():
        print(f"[link] vault 없음: {vault_path}", file=sys.stderr)
        return 1

    dry_run = not args.apply
    changes = run_linker(vault_path, repo_root, dry_run=dry_run)

    if args.as_json:
        import json
        print(json.dumps(
            [{"note": str(c.note_path), "links": c.new_links, "reason": c.reason}
             for c in changes],
            ensure_ascii=False, indent=2,
        ))
        return 0

    if not changes:
        print("[link] 추가할 링크 없음 — 모두 최신")
        return 0

    action = "적용" if not dry_run else "예정 (--apply 로 실제 write)"
    print(f"[link] {len(changes)}개 노트 변경 {action}\n")
    for ch in changes:
        short = ch.note_path.name
        print(f"  {short}")
        for lk in ch.new_links:
            print(f"    + {lk}")
        if ch.reason:
            print(f"    ({ch.reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
