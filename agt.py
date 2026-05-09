#!/usr/bin/env python3
"""agt — run antigravity_link.py with UTF-8 output.

Cross-platform replacement for agt.cmd.

Usage:
    python agt.py [args...]
"""

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def main() -> None:
    script = Path(__file__).resolve().parent / "antigravity_link.py"
    if not script.exists():
        print(f"[agt] antigravity_link.py not found: {script}")
        sys.exit(1)

    result = subprocess.run([sys.executable, str(script)] + sys.argv[1:])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
