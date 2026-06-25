"""STAGE R — af knowledge search 검색 엔진 (read-only, 결정론 sparse).

설계: docs/2026-06-25-stage-r-retrieval-design.md
INV-R1: 외부 LLM/임베딩/네트워크 호출 0 — 순수 Python·결정론.
INV-R2: 정밀참조 추출은 distill.extract_precise_refs SSOT 재사용.
INV-R3: 3종 frontmatter(KnowledgeNote/레거시/무) + 파싱실패도 본문 전문으로 인덱싱.
INV-R4: write/create/delete 경로 0.
INV-R5: 출력 bounded(--limit 기본 8) + 발췌만. 결정론 tie-break(created_at desc→path).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.knowledge.distill import extract_precise_refs

_DEFAULT_VAULT_RELPATH = Path("docs") / "wiki" / "knowledge"
_DEFAULT_LIMIT = 8
_EXCERPT_CONTEXT = 2

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_PRECISE_REF_HEADING = re.compile(r"^##\s+정밀\s*참조", re.MULTILINE | re.IGNORECASE)
_H1 = re.compile(r"^#\s+(.+)", re.MULTILINE)


@dataclass
class NoteDoc:
    """검색 전용 경량 노트 문서 (내부 타입 — KnowledgeNote와 별개, 설계 §4)."""
    path: Path
    note_type: str            # KnowledgeNote type / 레거시 metadata.type / ""
    title: str
    description: str
    body: str                 # 전문 (INV-R3: 파싱 실패 시에도 검색 대상)
    refs: list[str]           # extract_precise_refs(body) 재사용 (INV-R2)
    precise_ref_section: str  # ## 정밀 참조 섹션 텍스트
    created_at: str           # ISO timestamp 또는 ""


def _git_call(args: list[str], cwd: str, timeout: int = 10) -> str:
    """git 호출 헬퍼 (stdin=DEVNULL — Windows WinError 6 방어, note._git 패턴)."""
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """관용적 frontmatter 파싱 (INV-R3 — 실패해도 (빈 dict, 전문) 반환)."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    m = _FRONTMATTER.match(normalized)
    if not m:
        return {}, normalized
    fm_text, body = m.group(1), m.group(2)
    meta: dict[str, Any] = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().replace(".", "_")
        val = val.strip()
        if key:
            meta[key] = val
    return meta, body


def _extract_title(meta: dict[str, Any], body: str, path: Path) -> str:
    """title → name → 첫 # 헤딩 → 파일 stem 폴백 (설계 §3.3)."""
    for key in ("title", "name"):
        if meta.get(key, "").strip():
            return meta[key].strip()
    m = _H1.search(body)
    if m:
        return m.group(1).strip()
    return path.stem


def _extract_precise_ref_section(body: str) -> str:
    """## 정밀 참조 섹션 텍스트 추출 (KnowledgeNote 포맷 전용)."""
    m = _PRECISE_REF_HEADING.search(body)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s", body[start:], re.MULTILINE)
    end = start + nxt.start() if nxt else len(body)
    return body[start:end].strip()


def load_notes(vault_root: Path) -> list[NoteDoc]:
    """vault_root 하위 .md 전수 스캔 → NoteDoc 목록.

    파싱 실패한 파일도 본문 전문으로 포함 (INV-R3 누락 0 보장).
    """
    docs: list[NoteDoc] = []
    for p in sorted(vault_root.rglob("*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        meta, body = _parse_frontmatter(text)
        docs.append(NoteDoc(
            path=p,
            note_type=meta.get("type", meta.get("metadata_type", "")),
            title=_extract_title(meta, body, p),
            description=meta.get("description", ""),
            body=body,
            refs=extract_precise_refs(body),
            precise_ref_section=_extract_precise_ref_section(body),
            created_at=meta.get("created_at", ""),
        ))
    return docs


def _term_score(term: str, doc: NoteDoc) -> int:
    """단일 쿼리 용어 점수 (가중치: title=3, description=2, 정밀참조섹션=2, 본문=1)."""
    t = term.lower()
    return (
        doc.title.lower().count(t) * 3
        + doc.description.lower().count(t) * 2
        + doc.precise_ref_section.lower().count(t) * 2
        + doc.body.lower().count(t) * 1
    )


def _file_score(changed_files: list[str], doc: NoteDoc) -> tuple[int, list[str]]:
    """refs ∩ changed_files 매칭 점수 (전체경로=5, basename=3, 설계 §4.1)."""
    score = 0
    reasons: list[str] = []
    cf_norm = {cf.replace("\\", "/") for cf in changed_files}
    cf_basenames = {Path(cf).name for cf in changed_files}
    for ref in doc.refs:
        # file:line 형태만 처리 (INV명·커밋 해시 제외)
        if ":" not in ref or ref.startswith("INV-"):
            continue
        ref_path, _, _ = ref.rpartition(":")
        norm_ref = ref_path.replace("\\", "/")
        if norm_ref in cf_norm:
            score += 5
            reasons.append(f"file={ref}")
        elif Path(ref_path).name in cf_basenames:
            score += 3
            reasons.append(f"basename={Path(ref_path).name}")
    return score, reasons


def score_notes(
    query: str,
    files: list[str],
    notes: list[NoteDoc],
    note_type_filter: str = "",
) -> list[tuple[NoteDoc, float, list[str]]]:
    """결정론 sparse 점수화. tie-break: created_at 내림차순 → path 사전순 (INV-R5).

    stable sort 3단계로 구현:
      1) path 사전순 (기준)
      2) created_at 내림차순 stable
      3) score 내림차순 stable
    """
    terms = [t for t in query.split() if t] if query else []
    results: list[tuple[NoteDoc, float, list[str]]] = []
    for doc in notes:
        if note_type_filter and doc.note_type != note_type_filter:
            continue
        score = 0.0
        reasons: list[str] = []
        for term in terms:
            ts = _term_score(term, doc)
            if ts:
                score += ts
                reasons.append(f"query:{term}={ts}")
        if files:
            fs, freasons = _file_score(files, doc)
            score += fs
            reasons.extend(freasons)
        if score > 0 or (not terms and not files):
            results.append((doc, score, reasons))

    results.sort(key=lambda x: str(x[0].path))
    results.sort(key=lambda x: x[0].created_at or "", reverse=True)
    results.sort(key=lambda x: -x[1])
    return results


def _excerpt(doc: NoteDoc, reasons: list[str]) -> str:
    """발췌: 정밀참조 섹션 우선, 없으면 첫 매칭 줄 주변 (INV-R5 통째 본문 금지)."""
    if doc.precise_ref_section:
        return "\n".join(doc.precise_ref_section.splitlines()[:3])
    # 쿼리 용어 첫 매칭 줄 주변
    query_terms: set[str] = set()
    for r in reasons:
        if r.startswith("query:"):
            term = r.split(":", 1)[1].split("=")[0].lower()
            query_terms.add(term)
    if query_terms:
        body_lines = doc.body.splitlines()
        for i, line in enumerate(body_lines):
            if any(t in line.lower() for t in query_terms):
                start = max(0, i - _EXCERPT_CONTEXT)
                end = min(len(body_lines), i + _EXCERPT_CONTEXT + 1)
                return "\n".join(body_lines[start:end])
    if doc.description:
        return doc.description[:200]
    return "\n".join(doc.body.splitlines()[:3])


def format_results(
    ranked: list[tuple[NoteDoc, float, list[str]]],
    as_json: bool = False,
    limit: int = _DEFAULT_LIMIT,
) -> str:
    """검색 결과 포맷 (사람용 표 또는 --json 에이전트 소비용)."""
    top = ranked[:limit]
    if as_json:
        return json.dumps(
            [
                {
                    "path": str(doc.path),
                    "title": doc.title,
                    "type": doc.note_type,
                    "score": score,
                    "reasons": reasons,
                    "excerpt": _excerpt(doc, reasons),
                }
                for doc, score, reasons in top
            ],
            ensure_ascii=False,
            indent=2,
        )
    if not top:
        return "(검색 결과 없음)"
    lines: list[str] = []
    for i, (doc, score, reasons) in enumerate(top, 1):
        type_tag = f"[{doc.note_type}] " if doc.note_type else ""
        lines.append(f"{i}. {type_tag}{doc.title}  (score={score:.0f})")
        lines.append(f"   {doc.path}")
        if reasons:
            shown = ", ".join(reasons[:3]) + (" ..." if len(reasons) > 3 else "")
            lines.append(f"   매칭: {shown}")
        ex = _excerpt(doc, reasons)
        if ex:
            for el in ex.splitlines()[:_EXCERPT_CONTEXT + 1]:
                lines.append(f"   | {el}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _find_repo_root(start: Path) -> Path:
    """start 기준으로 .git 있는 조상 탐색 (최대 10단계)."""
    p = start.resolve()
    for _ in range(10):
        if (p / ".git").exists():
            return p
        parent = p.parent
        if parent == p:
            break
        p = parent
    return start.resolve()


def main(argv: list[str] | None = None) -> int:
    """af knowledge search CLI 진입점 (INV-R4: write 경로 없음)."""
    parser = argparse.ArgumentParser(
        prog="af knowledge search",
        description="knowledge vault 검색 (결정론 sparse, read-only)",
    )
    parser.add_argument("--query", "-q", default="", help="키워드 쿼리")
    parser.add_argument("--files", "-f", default="", help="변경 파일 목록 (콤마 구분)")
    parser.add_argument("--diff", action="store_true", help="현재 git diff 변경 파일 자동 수집")
    parser.add_argument("--type", dest="note_type", default="", help="노트 타입 필터 (decision/concept/pattern/session)")
    parser.add_argument("--limit", "-n", type=int, default=_DEFAULT_LIMIT, help=f"최대 결과 수 (기본 {_DEFAULT_LIMIT})")
    parser.add_argument("--json", dest="as_json", action="store_true", help="JSON 출력 (에이전트 소비용)")
    parser.add_argument("--vault", default="", help="vault 루트 경로 (기본: <repo_root>/docs/wiki/knowledge)")
    args = parser.parse_args(argv)

    if args.vault:
        vault_root = Path(args.vault)
    else:
        # core/knowledge/retrieve.py → core/knowledge → core → repo_root
        repo_root = _find_repo_root(Path(__file__).parent.parent.parent)
        vault_root = repo_root / _DEFAULT_VAULT_RELPATH

    if not vault_root.exists():
        print(f"[knowledge search] vault 없음: {vault_root}", file=sys.stderr)
        return 1

    git_cwd = str(_find_repo_root(vault_root))

    files: list[str] = []
    if args.files:
        files = [f.strip() for f in args.files.split(",") if f.strip()]
    if args.diff:
        out = _git_call(["diff", "--name-only", "HEAD"], cwd=git_cwd)
        if not out:
            out = _git_call(["diff", "--name-only"], cwd=git_cwd)
        files += [f.strip() for f in out.splitlines() if f.strip()]

    if not args.query and not files:
        parser.print_help()
        return 0

    notes = load_notes(vault_root)
    ranked = score_notes(args.query, files, notes, note_type_filter=args.note_type)
    print(format_results(ranked, as_json=args.as_json, limit=args.limit))
    return 0
