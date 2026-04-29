#!/usr/bin/env python3
"""Cross-platform hook launcher for Agent Factory.

Invoke with whichever Python is available:
  Mac/Linux : python3 scripts/run.py <hook_or_script> [args...]
  Windows   : python  scripts/run.py <hook_or_script> [args...]

Uses sys.executable so all child processes inherit the same interpreter —
no python3/python naming ambiguity downstream.

Dispatch rules:
  arg ends with .py  → run scripts/<arg> directly (boundary-checked, timeout=120)
  otherwise          → delegate to hook_runner.py (builtin dispatch)

Always exits 0 — hooks must not block Claude Code operations.
"""
from __future__ import annotations

import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS_DIR = os.path.realpath(os.path.join(_ROOT, "scripts"))
_TIMEOUT = 120


def _safe_script(target: str) -> str | None:
    """Return resolved absolute path if target is inside scripts/, else None."""
    resolved = os.path.realpath(os.path.join(_SCRIPTS_DIR, target))
    if not resolved.startswith(_SCRIPTS_DIR + os.sep):
        return None
    return resolved


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    target = sys.argv[1]
    extra = sys.argv[2:]
    cwd = os.getcwd()

    if target.endswith(".py"):
        script = _safe_script(target)
        if script is None:
            print(f"[run.py] unsafe target rejected: {target}", file=sys.stderr)
            return 0
        if not os.path.isfile(script):
            print(f"[run.py] script not found: {script}", file=sys.stderr)
            return 0
        try:
            result = subprocess.run(
                [sys.executable, script] + extra,
                cwd=cwd,
                timeout=_TIMEOUT,
            )
            return max(result.returncode, 0)
        except subprocess.TimeoutExpired:
            print(f"[run.py] timeout ({_TIMEOUT}s): {target}", file=sys.stderr)
        except OSError as exc:
            print(f"[run.py] OSError: {exc}", file=sys.stderr)
    else:
        runner = os.path.join(_SCRIPTS_DIR, "hook_runner.py")
        if not os.path.isfile(runner):
            print(f"[run.py] hook_runner.py not found: {runner}", file=sys.stderr)
            return 0
        try:
            result = subprocess.run(
                [sys.executable, runner, target] + extra,
                cwd=cwd,
            )
            return max(result.returncode, 0)
        except OSError as exc:
            print(f"[run.py] OSError: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
