"""af knowledge doctor — vault staleness/skew 점검기 (크로스OS, advisory only).

설계: docs/2026-06-23-knowledge-library-evolution-design.md §5 STAGE3
STALE: created_commit 히스토리에 있음 + file:line 내용이 변동됨
SKEW:  created_commit 이 로컬 히스토리에 없음 (이 PC 미pull)
advisory: 리포트만 — 자동 삭제/수정 절대 금지 (§5 STAGE3 [제약])
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_VAULT_RELPATH = Path("docs") / "wiki" / "knowledge"
_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# file:line 패턴 (distill._REF_PATTERNS[1] 동일 — SSOT는 distill.py이나 여기서 직접 정의해
# 순환 import 없이 크로스OS subprocess 컨텍스트에서 동작하게 한다)
_FILE_LINE_RE = re.compile(r"(?:[\w.\-]+[/\\])*[\w.\-]+\.[A-Za-z]{1,6}:(\d+)")


# ---------------------------------------------------------------------------
# 데이터 타입
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    note_path: str
    status: str          # "SKEW" | "STALE"
    ref: str             # commit 해시 or "path:line"
    detail: str = ""


# ---------------------------------------------------------------------------
# git 헬퍼 (note._git 패턴 — stdin=DEVNULL Windows WinError 6 방어)
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: str, timeout: int = 15) -> tuple[int, str]:
    """git 호출 → (returncode, stdout)."""
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True,
            cwd=cwd, timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return r.returncode, r.stdout
    except Exception as e:
        return 1, str(e)


def _commit_exists(commit: str, cwd: str) -> bool:
    """로컬 git 히스토리에 커밋이 있는지 확인."""
    rc, _ = _git(["cat-file", "-t", commit], cwd=cwd)
    return rc == 0


def _line_at_commit(path: str, line_num: int, commit: str, cwd: str) -> str | None:
    """commit 시점의 path 파일 line_num 번째 줄 내용. 없으면 None."""
    norm = path.replace("\\", "/")
    rc, out = _git(["show", f"{commit}:{norm}"], cwd=cwd)
    if rc != 0:
        return None
    lines = out.splitlines()
    idx = line_num - 1
    return lines[idx] if 0 <= idx < len(lines) else None


def _current_line(path: str, line_num: int, cwd: str) -> str | None:
    """현재 워킹트리에서 path 파일 line_num 번째 줄 내용. 없으면 None."""
    p = Path(cwd) / path.replace("\\", "/")
    if not p.exists():
        return None
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        idx = line_num - 1
        return lines[idx] if 0 <= idx < len(lines) else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# frontmatter / ref 파싱
# ---------------------------------------------------------------------------

def _parse_created_commit(text: str) -> str:
    """frontmatter 에서 created_commit 값 추출. 없거나 unknown 이면 ""."""
    normalized = text.replace("\r\n", "\n")
    m = _FRONTMATTER.match(normalized)
    if not m:
        return ""
    for line in m.group(1).split("\n"):
        if not line.startswith("created_commit:"):
            continue
        _, _, raw = line.partition(":")
        val = raw.strip().strip('"').strip("'")
        return "" if val in ("unknown", "") else val
    return ""


def _extract_file_line_refs(text: str) -> list[tuple[str, int]]:
    """text 에서 (파일경로, 줄번호) 쌍을 추출."""
    results: list[tuple[str, int]] = []
    for m in _FILE_LINE_RE.finditer(text):
        ref = m.group(0)
        colon_idx = ref.rfind(":")
        path = ref[:colon_idx]
        try:
            line_num = int(ref[colon_idx + 1:])
        except ValueError:
            continue
        if line_num > 0:
            results.append((path, line_num))
    return results


# ---------------------------------------------------------------------------
# 핵심 점검 로직
# ---------------------------------------------------------------------------

def check_note(note_path: Path, repo_root: str) -> list[Finding]:
    """노트 하나를 점검해 STALE/SKEW Finding 목록 반환."""
    try:
        text = note_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    created_commit = _parse_created_commit(text)
    if not created_commit:
        return []  # created_commit 없으면 STAGE 1 이전 노트 — 건너뜀

    try:
        note_rel = str(note_path.relative_to(Path(repo_root).resolve()))
    except ValueError:
        note_rel = str(note_path)

    # SKEW: created_commit 이 로컬 히스토리에 없음 → 오보 차단
    if not _commit_exists(created_commit, repo_root):
        return [Finding(
            note_path=note_rel,
            status="SKEW",
            ref=created_commit,
            detail="created_commit 이 로컬 git 히스토리에 없음 (git pull 필요)",
        )]

    # STALE: file:line 참조 중 내용이 변한 것
    findings: list[Finding] = []
    for path, line_num in _extract_file_line_refs(text):
        old = _line_at_commit(path, line_num, created_commit, repo_root)
        if old is None:
            # created_commit 시점에 없던 파일 → 이 노트가 가리키는 ref 아님, 건너뜀
            continue
        cur = _current_line(path, line_num, repo_root)
        if cur is None:
            findings.append(Finding(
                note_path=note_rel,
                status="STALE",
                ref=f"{path}:{line_num}",
                detail="파일 삭제 또는 줄 번호 범위 초과",
            ))
        elif cur.strip() != old.strip():
            findings.append(Finding(
                note_path=note_rel,
                status="STALE",
                ref=f"{path}:{line_num}",
                detail=f"변경됨: {old.strip()!r} → {cur.strip()!r}",
            ))

    return findings


def run_doctor(vault: Path, repo_root: str) -> list[Finding]:
    """vault 전체 노트를 점검해 Finding 목록 반환."""
    all_findings: list[Finding] = []
    for note_path in sorted(vault.rglob("*.md")):
        all_findings.extend(check_note(note_path, repo_root))
    return all_findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="af knowledge doctor",
        description="vault staleness/skew 점검 (advisory — 자동 수정 없음)",
    )
    p.add_argument("--vault", default="", help="vault 루트 경로 (기본: docs/wiki/knowledge)")
    p.add_argument("--repo", default="", help="git repo 루트 (기본: 현재 디렉터리)")
    p.add_argument("--json", dest="as_json", action="store_true", help="JSON 출력")
    args = p.parse_args(argv)

    repo_root = str(Path(args.repo or ".").resolve())
    vault = Path(args.vault) if args.vault else Path(repo_root) / _DEFAULT_VAULT_RELPATH

    if not vault.exists():
        print(f"[doctor] vault 없음: {vault}", file=sys.stderr)
        return 1

    notes_count = sum(1 for _ in vault.rglob("*.md"))
    findings = run_doctor(vault, repo_root)

    if args.as_json:
        print(json.dumps(
            [{"note": f.note_path, "status": f.status, "ref": f.ref, "detail": f.detail}
             for f in findings],
            ensure_ascii=False, indent=2,
        ))
        return 0

    stale = [f for f in findings if f.status == "STALE"]
    skew = [f for f in findings if f.status == "SKEW"]

    print(f"af knowledge doctor — {notes_count}개 노트 점검")

    if not findings:
        print("OK — staleness/skew 없음")
        return 0

    if skew:
        print(f"\n── SKEW ({len(skew)}건) — created_commit 로컬 미보유 (git pull 필요) ──")
        for f in skew:
            print(f"  {f.note_path}")
            print(f"    commit: {f.ref}")

    if stale:
        print(f"\n── STALE ({len(stale)}건) — file:line 내용 변동 ──")
        for f in stale:
            print(f"  {f.note_path}: {f.ref}")
            print(f"    {f.detail}")

    print(f"\n총 {len(findings)}건 (STALE {len(stale)} · SKEW {len(skew)}) — advisory 전용, 수동 확인 권장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
