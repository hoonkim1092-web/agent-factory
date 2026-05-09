#!/usr/bin/env python3
"""start_git — pull project context from Git.

Cross-platform replacement for start_git.cmd.

Usage:
    python start_git.py [target] [agent]
    python start_git.py agent-factory
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
GIT_SYNC = REPO_ROOT / "scripts" / "project_context_git_sync.py"

TARGET_ALL = "logi-mind-v22,agent-factory,@repo"


def _resolve_target(raw: str) -> tuple[str, bool]:
    if raw.lower() == "all":
        return TARGET_ALL, True
    if "," in raw:
        return raw, True
    return raw, False


def main() -> None:
    argv = sys.argv[1:]
    target = argv[0] if argv else "all"
    agent = argv[1] if len(argv) > 1 else ""

    target_val, is_multi = _resolve_target(target)

    print(f"[SYNC START] pulling from Git  target={target}  agent={agent or '(all)'}")

    cmd = [sys.executable, str(GIT_SYNC), "--mode", "pull"]
    cmd += ["--projects" if is_multi else "--project", target_val]
    if agent:
        cmd += ["--agent", agent]

    rc = subprocess.run(cmd).returncode
    if rc != 0:
        sys.exit(rc)

    print("[SYNC START] done.")


if __name__ == "__main__":
    main()
