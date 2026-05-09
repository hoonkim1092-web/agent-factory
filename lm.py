#!/usr/bin/env python3
"""lm — navigate to / run commands inside the logi-mind-v22 repo.

Cross-platform replacement for lm.cmd.

Usage:
    python lm.py              # print resolved path
    python lm.py <command>    # run command inside logi-mind-v22 root
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_shortcuts import resolve_repo_path


def main() -> None:
    target = resolve_repo_path("logi-mind-v22", Path.cwd())
    if not target:
        print("[lm] Could not find 'logi-mind-v22'. "
              "Set HOON_PROJECTS_HOME or move under a matching parent.")
        sys.exit(1)

    if len(sys.argv) == 1:
        print(target)
        return

    result = subprocess.run(sys.argv[1:], cwd=str(target))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
