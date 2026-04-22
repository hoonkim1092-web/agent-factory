#!/usr/bin/env python3
"""start_sync — pull project context from db, git, or both.

Cross-platform replacement for start_sync.cmd.

Usage:
    python start_sync.py [backend] [target] [agent]
    python start_sync.py db agent-factory
    python start_sync.py git all
    python start_sync.py all agent-factory my-agent

backend: db | git | all (default: all)
If first arg is not a backend keyword it is treated as target with backend=all.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKENDS = {"db", "git", "all"}


def _run(script: Path, target: str, agent: str) -> int:
    cmd = [sys.executable, str(script), target]
    if agent:
        cmd.append(agent)
    return subprocess.run(cmd).returncode


def main() -> None:
    argv = sys.argv[1:]

    if argv and argv[0].lower() in BACKENDS:
        backend = argv[0].lower()
        target = argv[1] if len(argv) > 1 else "all"
        agent = argv[2] if len(argv) > 2 else ""
    else:
        backend = "all"
        target = argv[0] if argv else "all"
        agent = argv[1] if len(argv) > 1 else ""

    print(f"[SYNC START] backend={backend}  target={target}  agent={agent or '(all)'}")

    if backend in ("db", "all"):
        rc = _run(REPO_ROOT / "start_db.py", target, agent)
        if rc != 0:
            sys.exit(rc)

    if backend in ("git", "all"):
        rc = _run(REPO_ROOT / "start_git.py", target, agent)
        if rc != 0:
            sys.exit(rc)


if __name__ == "__main__":
    main()
