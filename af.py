#!/usr/bin/env python3
"""af — navigate to / run commands inside the agent-factory repo.

Cross-platform replacement for af.cmd.

Usage:
    python af.py              # print resolved path
    python af.py <command>    # run command inside agent-factory root
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_shortcuts import resolve_repo_path


def main() -> None:
    target = resolve_repo_path("agent-factory", Path.cwd())
    if not target:
        print("[af] Could not find 'agent-factory'. "
              "Set HOON_PROJECTS_HOME or move under a matching parent.")
        sys.exit(1)

    if len(sys.argv) == 1:
        print(target)
        return

    result = subprocess.run(sys.argv[1:], cwd=str(target))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
