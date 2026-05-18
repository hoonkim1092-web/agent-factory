#!/usr/bin/env python3
"""
scripts/blast_radius.py
=========================
Blast Radius 결정적 분류기 (Phase 0 — Proof-Carrying Review 도입 전 단계).

Tier 1: docs, formatting, low-impact  → tests/static check만, AI BLOCK 불가
Tier 2: 일반 app/core 코드             → 정상 3-tier 리뷰
Tier 3: subprocess/shell/auth/hook/deploy 지표 포함 → 3-tier + 사람 승인 옵션

분류는 결정적이어야 하므로 LLM이 아닌 path/AST/regex 매칭으로 판정한다.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Literal

Tier = Literal[1, 2, 3]

# ── Tier 3 호출 패턴 — comment/docstring false-positive 방지 위해 호출 형태로 한정 ──
_TIER3_REGEX = re.compile(
    r"("
    # subprocess: 실제 호출 형태만
    r"\bsubprocess\.(run|Popen|call|check_call|check_output)(?=\s*\()|"
    r"\bos\.system(?=\s*\()|"
    r"\bshell\s*=\s*True|"
    # exec/eval: literal 호출까지 포함하도록 trailing \b 제거
    r"\b(exec|eval)\s*\(|"
    # 위험 git 명령 (shell 안)
    r"git\s+(reset|push|rebase|checkout|merge)\s+|"
    # 파일 삭제 호출
    r"\bos\.unlink(?=\s*\()|"
    r"\bshutil\.rmtree(?=\s*\()|"
    # network 호출
    r"\brequests\.(get|post|put|delete|patch)(?=\s*\()|"
    r"\bhttpx\.(get|post|put|delete|patch|Client)(?=\s*\()|"
    r"\burllib\.request\.(urlopen|Request)(?=\s*\()|"
    # 비밀/자격증명 — string assignment 인접 조건
    r"(jwt|oauth|credential|api[_-]?key|secret|token|password)\s*=\s*['\"]"
    r")",
    re.IGNORECASE,
)

# ── Tier 3 path 핀 — 작아도 blast radius 큰 파일들 ────────────────────────────
# 모든 항목은 workspace 상대경로, 정규화된 형태(./prefix 없음, 슬래시 단일).
_TIER3_PATHS = frozenset({
    # hook / launcher
    "scripts/run.py",
    "scripts/hook_runner.py",
    "scripts/cli_hook_bridge.py",
    "scripts/review_gate.py",
    # DB 동기화 — 루트에 위치 (CLAUDE.md: `python end_db.py agent-factory`)
    "start_db.py",
    "end_db.py",
    "scripts/sync_claude_memory.py",
    # 빌드 / 배포 / 핵심 설정
    "build_exe.py",
    "install-af.ps1",
    "af.spec",
    "policy.yaml",
    "version.py",
    # git hooks
    ".githooks/pre-commit",
    ".githooks/post-commit",
})

# ── Tier 3 prefix — 디렉토리 단위 위험 영역 ──────────────────────────────────
_TIER3_PREFIXES = (
    ".github/workflows/",
    ".githooks/",
)

# ── Tier 1 path 패턴 — blast radius가 명확히 작은 파일/패턴 ──────────────────
_TIER1_PATTERNS = (
    re.compile(r"^docs/.*\.md$"),
    re.compile(r"^projects/.*/docs/.*\.md$"),
    re.compile(r"^README"),
    re.compile(r"^CHANGELOG"),
    re.compile(r"^Master_Blueprint\.md$"),
    re.compile(r"^NEXT_STEPS\.md$"),
    re.compile(r".*\.template\.json$"),
    re.compile(r"^\.gitignore$"),
    # Auto-generated memory artifacts — PR마다 대량 stage되지만 위험도 0
    re.compile(r"^projects/.*/data/memory/.*\.(json|jsonl)$"),
    re.compile(r"^.*\.lock$"),
)

# ── 내용 검사 대상 확장자 — .py 외에도 위험 가능성 있는 텍스트 파일 ─────────
_CONTENT_SCAN_EXTS = (
    ".py", ".sh", ".bash", ".ps1", ".yml", ".yaml", ".toml",
)
_CONTENT_SCAN_NAMES = ("Dockerfile",)


def _normalize(rel_path: str) -> str:
    """경로를 결정적 형태로 정규화: '\\' → '/', ./ 제거, 중복 슬래시 제거.

    절대경로가 들어오면 변경하지 않고 그대로 반환 (호출자가 workspace 기준
    상대경로를 넘기는 것이 계약).
    """
    norm = rel_path.replace("\\", "/")
    norm = re.sub(r"/+", "/", norm)
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def _validate_tier(t: int) -> Tier:
    if t not in (1, 2, 3):
        raise ValueError(f"invalid tier: {t!r} (expected 1, 2, or 3)")
    return t  # type: ignore[return-value]


def classify_path(rel_path: str) -> Tier:
    """파일 경로만 보고 Tier를 결정한다 (1-pass, 결정적).

    내용 검사가 필요한 경우는 classify_with_content()를 사용.
    """
    norm = _normalize(rel_path)

    # Tier 3 path 핀
    if norm in _TIER3_PATHS:
        return 3

    # Tier 3 prefix
    for pfx in _TIER3_PREFIXES:
        if norm.startswith(pfx):
            return 3

    # Tier 1 path 핀
    for pat in _TIER1_PATTERNS:
        if pat.match(norm):
            return 1

    # 기본값: 일반 코드는 Tier 2
    return 2


def _has_tier3_content(abs_path: str) -> bool:
    """파일을 라인 단위로 읽어 Tier 3 regex와 매칭한다.

    line-stripped `#` 시작 라인은 건너뛰어 comment false-positive 회피.
    파일 iteration은 Python 내부에서 버퍼링되므로 대형 파일에서도 효율적.
    """
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                # comment-only 라인은 검사 제외 (false-positive 방지)
                if line.lstrip().startswith("#"):
                    continue
                if _TIER3_REGEX.search(line):
                    return True
    except OSError:
        return False
    return False


def classify_with_content(rel_path: str, workspace: str) -> Tier:
    """파일 경로 + 내용 휴리스틱으로 Tier를 결정한다.

    Tier 1로 path 분류된 파일은 내용 검사 없이 1 반환.
    Tier 3 path 핀은 무조건 3.
    그 외 텍스트 파일(.py/.sh/.yml/Dockerfile 등)은 Tier 3 regex 매칭 시 3.
    """
    base = classify_path(rel_path)
    if base == 1:
        return 1
    if base == 3:
        return 3

    # base == 2 → 내용 검사 대상이면 regex 검사
    norm = _normalize(rel_path)
    basename = os.path.basename(norm)
    is_scan_target = (
        any(norm.endswith(ext) for ext in _CONTENT_SCAN_EXTS)
        or basename in _CONTENT_SCAN_NAMES
    )
    if not is_scan_target:
        return base

    abs_path = os.path.join(workspace, norm)
    if _has_tier3_content(abs_path):
        return 3

    return base


def required_agents(tier: int) -> list[str]:
    """Tier에 따라 실행해야 할 에이전트 목록.

    Tier 1: af-test-runner만 (정적 검사 + 테스트)
    Tier 2: 3-tier 모두
    Tier 3: 3-tier 모두 (사람 에스컬레이션은 별도 경로)

    Raises:
        ValueError: tier가 1, 2, 3이 아닐 때.
    """
    t = _validate_tier(tier)
    if t == 1:
        return ["af-test-runner"]
    return ["af-test-runner", "af-critic", "af-cross-review"]


# CLI ─────────────────────────────────────────────────────────────────────────

def _cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Blast Radius Tier 분류 CLI")
    parser.add_argument("path", help="분류할 파일 경로 (workspace 상대)")
    parser.add_argument("--workspace", "-w", default=None)
    parser.add_argument("--with-content", action="store_true",
                        help="내용 검사 포함 (Tier 3 regex)")
    args = parser.parse_args(argv)

    ws = args.workspace or os.getcwd()
    if args.with_content:
        tier = classify_with_content(args.path, ws)
    else:
        tier = classify_path(args.path)

    agents = required_agents(tier)
    print(f"path={_normalize(args.path)}")
    print(f"tier={tier}")
    print(f"agents={','.join(agents)}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
