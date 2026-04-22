#!/usr/bin/env python3
"""cdx — Codex CLI wrapper with UTF-8 env and session bridge.

Cross-platform replacement for cdx.cmd.

Usage:
    python cdx.py [codex-args...]

Env:
    CDX_DEBUG=1   verbose logging
    CDX_LOG_FILE  path to append start/exit log lines
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("LANG", "C.UTF-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")

debug = os.environ.get("CDX_DEBUG", "") == "1"
log_file = os.environ.get("CDX_LOG_FILE", "")

codex = shutil.which("codex")
if not codex:
    print("[CDX] 'codex' command not found in PATH.")
    print("[CDX] Install Codex CLI first, then run: cdx")
    sys.exit(1)

if debug:
    print(f"[CDX] codex path: {codex}")
    print(f"[CDX] args: {sys.argv[1:]}")


def _log(msg: str) -> None:
    if log_file:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")


_log(f"start {' '.join(sys.argv[1:])}")

result = subprocess.run([codex] + sys.argv[1:])
exit_code = result.returncode

_log(f"exit {exit_code}")

bridge = Path(__file__).resolve().parent / "scripts" / "codex_session_bridge.py"
if bridge.exists():
    repo_root = str(Path(__file__).resolve().parent)
    bridge_cmd = [sys.executable, str(bridge), "--repo-root", repo_root]
    if debug:
        subprocess.run(bridge_cmd)
    else:
        subprocess.run(bridge_cmd, capture_output=True)
    if debug:
        print(f"[CDX] bridge exit: done")

sys.exit(exit_code)
