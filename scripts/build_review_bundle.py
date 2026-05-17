#!/usr/bin/env python3
"""scripts/build_review_bundle.py — review_bundle.md 생성기.

Phase 2: enqueue 후 pending_agent_review.json의 파일 목록을 읽어
core/review_bundle.py로 AST/grep 분석 후 .af_review_queue/review_bundle.md 저장.

hook_runner.py post_edit_enqueue builtin에서 호출되거나 단독 실행 가능.
항상 exit 0 — hook 차단 방지.

Usage:
    python3 scripts/build_review_bundle.py [workspace]
    python3 scripts/build_review_bundle.py  # git root 자동 감지
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _detect_workspace() -> str:
    import subprocess
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return os.getcwd()


def _load_pending(workspace: str) -> list[str]:
    p = Path(workspace) / ".af_review_queue" / "pending_agent_review.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return [f for f in data.get("files", []) if f]
    except Exception:
        return []


def _resolve_paths(workspace: str, files: list[str]) -> list[str]:
    """상대 경로를 절대 경로로 변환, 존재하는 .py 파일만 반환."""
    result = []
    for f in files:
        if not f.endswith(".py"):
            continue
        p = Path(f) if Path(f).is_absolute() else Path(workspace) / f
        if p.exists():
            result.append(str(p))
    return result


def run(workspace: str | None = None) -> int:
    workspace = workspace or _detect_workspace()

    files = _load_pending(workspace)
    if not files:
        return 0

    abs_files = _resolve_paths(workspace, files)
    if not abs_files:
        return 0

    try:
        sys.path.insert(0, workspace)
        from core import review_bundle
        bundle = review_bundle.build_full(workspace, abs_files)
        out = review_bundle.save_full(bundle, workspace)
        stats = bundle.get("stats", {})
        print(
            f"[build_review_bundle] "
            f"files={len(abs_files)} "
            f"size={stats.get('size_bytes', 0) // 1024}KB "
            f"callers={stats.get('caller_files_included', 0)}/{stats.get('caller_files_included', 0) + stats.get('caller_files_truncated', 0)} "
            f"-> {out}",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"[build_review_bundle] error: {e}", file=sys.stderr)

    return 0


def main() -> None:
    workspace = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run(workspace))


if __name__ == "__main__":
    main()
