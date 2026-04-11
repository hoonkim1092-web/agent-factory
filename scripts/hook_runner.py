#!/usr/bin/env python3
"""
scripts/hook_runner.py
========================
OS 독립적 hook 실행기.

Claude Code hook에서 호출하면, 현재 OS에 맞는 python/workspace 경로를 자동 감지하여
대상 스크립트를 실행한다. Windows/macOS 양쪽에서 에러 없이 동작.

사용법:
  python3 scripts/hook_runner.py <script> [args...]
  python3 scripts/hook_runner.py cli_hook_bridge --provider claude --run-id my_run

스크립트 이름만 주면 scripts/ 디렉토리에서 찾는다.
항상 exit 0 — hook 차단 방지.
"""
from __future__ import annotations

import os
import subprocess
import sys


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _detect_workspace() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return _project_root()


def _find_venv_python(root: str) -> str:
    """프로젝트 venv의 python을 찾는다."""
    if os.name == "nt":
        candidates = [
            os.path.join(root, ".venv", "Scripts", "python.exe"),
            os.path.join(root, ".venv", "Scripts", "python3.exe"),
        ]
    else:
        candidates = [
            os.path.join(root, ".venv", "bin", "python3"),
            os.path.join(root, ".venv", "bin", "python"),
        ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # venv 없으면 시스템 python
    return sys.executable


def _resolve_script(name: str, root: str) -> str:
    """스크립트 이름을 전체 경로로 변환한다."""
    # 이미 전체 경로면 그대로
    if os.path.isabs(name):
        return name
    # .py 확장자 없으면 추가
    if not name.endswith(".py"):
        name += ".py"
    # scripts/ 디렉토리에서 찾기
    candidate = os.path.join(root, "scripts", name)
    if os.path.isfile(candidate):
        return candidate
    # 프로젝트 루트에서 찾기
    candidate = os.path.join(root, name)
    if os.path.isfile(candidate):
        return candidate
    return os.path.join(root, "scripts", name)


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    script_name = sys.argv[1]
    extra_args = sys.argv[2:]

    root = _project_root()
    workspace = _detect_workspace()
    python = _find_venv_python(root)
    script = _resolve_script(script_name, root)

    if not os.path.isfile(script):
        # 스크립트가 없으면 조용히 종료 (다른 OS용 스크립트일 수 있음)
        return 0

    cmd = [python, script] + extra_args
    try:
        result = subprocess.run(
            cmd,
            cwd=workspace,
            timeout=30,
            capture_output=False,  # stdout/stderr를 그대로 전달
            stdin=sys.stdin if not sys.stdin.isatty() else subprocess.DEVNULL,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"[hook_runner] timeout: {script_name}", file=sys.stderr)
        return 0
    except Exception as exc:
        print(f"[hook_runner] error: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
