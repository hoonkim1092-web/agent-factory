#!/usr/bin/env python3
"""Summarize deterministic Tier-3 skip telemetry."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path


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


def _telemetry_path(workspace: str) -> Path:
    return Path(workspace) / ".af_review_queue" / "t3_skip_telemetry.jsonl"


def load_records(workspace: str) -> list[dict]:
    path = _telemetry_path(workspace)
    if not path.exists():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def build_report(records: list[dict]) -> str:
    if not records:
        return "T3 skip telemetry: no records"

    reasons = Counter(str(r.get("skip_reason") or "unknown") for r in records)
    versions = Counter(str(r.get("classifier_version") or "unknown") for r in records)
    files: Counter[str] = Counter()
    for record in records:
        for file in record.get("files") or []:
            files[str(file)] += 1

    lines = [
        "T3 skip telemetry",
        f"total_skips: {len(records)}",
        "",
        "by_reason:",
    ]
    lines.extend(f"- {reason}: {count}" for reason, count in reasons.most_common())
    lines.append("")
    lines.append("by_classifier_version:")
    lines.extend(f"- {version}: {count}" for version, count in versions.most_common())
    lines.append("")
    lines.append("top_files:")
    lines.extend(f"- {file}: {count}" for file, count in files.most_common(10))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    raw_mode = "--raw" in args
    args = [arg for arg in args if arg != "--raw"]
    workspace = args[0] if args else _detect_workspace()

    records = load_records(workspace)
    if raw_mode:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    else:
        print(build_report(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
