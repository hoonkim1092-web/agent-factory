"""scripts/af_evolution.py — af evolution subcommand.

Phase 1: BLOCK 패턴 레저 read-only 조회.
- af evolution list : 패턴별 발생 횟수 출력, 재발(≥2) 강조
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from scripts.review_gate import _BLOCK_PATTERNS_RELPATH


def _detect_workspace() -> str:
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


def _load_patterns(workspace: str) -> list[dict]:
    path = os.path.join(workspace, _BLOCK_PATTERNS_RELPATH)
    if not os.path.exists(path):
        return []
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return records


def list_patterns(workspace: str) -> list[dict]:
    """패턴별 발생 횟수 집계. unknown:* 는 집계 제외 (v1 Scope)."""
    records = _load_patterns(workspace)
    counts: dict[str, int] = {}
    for r in records:
        key = r.get("pattern_key", "")
        if not key or key.startswith("unknown:"):
            continue
        counts[key] = counts.get(key, 0) + 1
    return [
        {"pattern_key": k, "count": v}
        for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="af evolution", description="AF Evolution 관리")
    sub = parser.add_subparsers(dest="cmd", required=True)
    list_p = sub.add_parser("list", help="반복 BLOCK 패턴 목록 출력")
    list_p.add_argument("--workspace", "-w", default=None, help="워크스페이스 경로 (기본: git root)")

    args = parser.parse_args(argv)

    if args.cmd == "list":
        workspace = args.workspace or _detect_workspace()
        patterns = list_patterns(workspace)
        if not patterns:
            print("[af evolution] BLOCK 패턴 기록 없음")
            return 0
        print(f"{'pattern_key':<42} {'count':>5}")
        print("-" * 50)
        for p in patterns:
            key = p["pattern_key"]
            count = p["count"]
            recurring = "  [재발]" if count >= 2 else ""
            print(f"{key:<42} {count:>5}{recurring}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
