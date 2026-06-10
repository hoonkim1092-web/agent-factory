#!/usr/bin/env python3
"""Provider-neutral review queue enqueue for staged Python changes.

Claude hooks enqueue files at edit time, but git commits may come from Codex,
plain shells, IDEs, or other providers. This script makes the repository-level
pre-commit path self-sufficient by enqueueing staged review-target files before
review_gate.py checks the queue.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _detect_workspace() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return os.getcwd()


def _staged_files(workspace: str) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=workspace,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in r.stdout.splitlines() if line.strip()]


def _staged_blob_hash(workspace: str, rel: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "ls-files", "-s", "--", rel],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=workspace,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    first = next((line for line in r.stdout.splitlines() if line.strip()), "")
    parts = first.split()
    return parts[1] if len(parts) >= 2 else None


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _pending_path(workspace: str) -> Path:
    return Path(workspace) / ".af_review_queue" / "pending_agent_review.json"


def _load_pending(workspace: str) -> dict:
    path = _pending_path(workspace)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_pending(workspace: str, data: dict) -> None:
    path = _pending_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pending_", suffix=".tmp", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _mark_seen_staged_hash(workspace: str, rel: str, blob_hash: str) -> None:
    data = _load_pending(workspace)
    hashes = data.setdefault("staged_index_hashes", {})
    if isinstance(hashes, dict):
        hashes[rel] = blob_hash
        _save_pending(workspace, data)


def _already_enqueued_for_staged_hash(workspace: str, rel: str, blob_hash: str | None) -> bool:
    data = _load_pending(workspace)
    if rel not in (data.get("files") or []):
        return False
    hashes = data.get("staged_index_hashes")
    if isinstance(hashes, dict) and blob_hash and hashes.get(rel) == blob_hash:
        return True
    if not isinstance(hashes, dict) and blob_hash:
        _mark_seen_staged_hash(workspace, rel, blob_hash)
    return not isinstance(hashes, dict)


def enqueue_staged(workspace: str | None = None) -> list[str]:
    workspace = workspace or _detect_workspace()
    root = Path(workspace)

    scripts_dir = _script_dir()
    sys.path.insert(0, str(scripts_dir))
    import enqueue_agent_review  # type: ignore

    enqueued: list[str] = []
    for rel in _staged_files(workspace):
        if not enqueue_agent_review._is_review_target(rel):  # type: ignore[attr-defined]
            continue
        blob_hash = _staged_blob_hash(workspace, rel)
        if _already_enqueued_for_staged_hash(workspace, rel, blob_hash):
            continue
        target = root / rel
        enqueue_agent_review.main_for_path(str(target), workspace=workspace)  # type: ignore[attr-defined]
        if blob_hash:
            _mark_seen_staged_hash(workspace, rel, blob_hash)
        enqueued.append(rel)
    return enqueued


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enqueue staged Python files for review-gate.")
    parser.add_argument("--workspace", "-w", default=None)
    args = parser.parse_args(argv)
    enqueued = enqueue_staged(args.workspace)
    if enqueued:
        print("[enqueue-staged-review] " + ", ".join(enqueued))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
