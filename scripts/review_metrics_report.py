#!/usr/bin/env python3
"""
scripts/review_metrics_report.py
==================================
Phase 3.5: review_metrics.jsonl 분석 CLI.

사용법:
  python3 scripts/review_metrics_report.py
  python3 scripts/review_metrics_report.py /path/to/workspace
  python3 scripts/review_metrics_report.py --raw         # raw JSONL 덤프
"""
from __future__ import annotations

import json
import os
import sys


def _detect_workspace() -> str:
    try:
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return os.getcwd()


def main() -> None:
    args = sys.argv[1:]
    raw_mode = "--raw" in args
    args = [a for a in args if a != "--raw"]

    workspace = args[0] if args else _detect_workspace()

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scripts.review_metrics_logger import _load_records, compute_report  # type: ignore

    if raw_mode:
        records = _load_records(workspace)
        for r in records:
            print(json.dumps(r, ensure_ascii=False))
        return

    print(compute_report(workspace))


if __name__ == "__main__":
    main()
