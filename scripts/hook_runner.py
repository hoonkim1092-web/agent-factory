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
  python3 scripts/hook_runner.py post_edit_py_compile   # builtin — stdin JSON 파싱

builtin 이름(post_edit_*)은 내부 함수로 직접 처리된다.
스크립트 이름만 주면 scripts/ 디렉토리에서 찾는다.
항상 exit 0 — hook 차단 방지.

stdin 재사용 계약: _BUILTINS 함수는 다른 builtin을 subprocess로 간접 호출하지 않는다.
Claude Code는 각 hook command에 독립 stdin을 공급하므로 subprocess 자식은 빈 stdin을 받는다.
"""
from __future__ import annotations

import json
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
    return sys.executable


def _resolve_script(name: str, root: str) -> str:
    """스크립트 이름을 전체 경로로 변환한다."""
    if os.path.isabs(name):
        return name
    if not name.endswith(".py"):
        name += ".py"
    candidate = os.path.join(root, "scripts", name)
    if os.path.isfile(candidate):
        return candidate
    candidate = os.path.join(root, name)
    if os.path.isfile(candidate):
        return candidate
    return os.path.join(root, "scripts", name)


# ── Builtin helpers ───────────────────────────────────────────────────────────

def _read_hook_stdin_once() -> dict:
    """Claude Code가 각 hook command에 독립 stdin을 공급하므로
    이 함수는 프로세스당 한 번만 호출된다. 반환값 dict를 재사용한다."""
    if sys.stdin.isatty():
        return {}
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def _extract_file_path(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    return str(ti.get("file_path") or "")


def _log_hook_event(builtin: str, file: str, exit_code: int, error: str = "") -> None:
    """훅 실행 시점·파일·결과를 append-only 로그에 기록. 실패는 silently swallow."""
    try:
        from datetime import datetime
        line = f"{datetime.now().isoformat()}|{builtin}|{file}|{exit_code}|{error}\n"
        root = _project_root()
        log_path = os.path.join(root, ".af_review_queue", "hook_events.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


# ── Builtin functions ─────────────────────────────────────────────────────────

def _post_edit_py_compile(payload: dict) -> int:
    fp = _extract_file_path(payload)
    if not fp or not fp.endswith(".py"):
        return 0
    try:
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", fp],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            print(f"[af-hook] syntax error in {fp}\n{r.stderr}", file=sys.stderr)
        _log_hook_event("post_edit_py_compile", fp, r.returncode)
    except Exception as exc:
        _log_hook_event("post_edit_py_compile", fp, 1, error=str(exc))
    return 0


def _post_edit_enqueue(payload: dict) -> int:
    """Enqueue file for agent review.

    Contract: do NOT call other builtins via subprocess — stdin is already consumed.
    """
    fp = _extract_file_path(payload)
    if not fp or not fp.endswith(".py"):
        return 0
    root = _project_root()
    script = os.path.join(root, "scripts", "enqueue_agent_review.py")
    try:
        subprocess.run([sys.executable, script, fp], timeout=3, cwd=root, capture_output=True)
        _log_hook_event("post_edit_enqueue", fp, 0)
    except Exception as exc:
        _log_hook_event("post_edit_enqueue", fp, 1, error=str(exc))
    return 0


def _post_edit_code_review(payload: dict) -> int:
    fp = _extract_file_path(payload)
    if not fp or not fp.endswith(".py"):
        return 0
    root = _project_root()
    script = os.path.join(root, "scripts", "code_review_updater.py")
    if not os.path.isfile(script):
        return 0
    try:
        subprocess.run(
            [sys.executable, script, "--context", f"edit: {fp}"],
            timeout=120, cwd=root, capture_output=True,
        )
        _log_hook_event("post_edit_code_review", fp, 0)
    except Exception as exc:
        _log_hook_event("post_edit_code_review", fp, 1, error=str(exc))
    return 0


def _post_edit_blueprint(payload: dict) -> int:
    fp = _extract_file_path(payload)
    if not fp or not fp.endswith(".py"):
        return 0
    root = _project_root()
    script = os.path.join(root, "scripts", "blueprint_updater.py")
    if not os.path.isfile(script):
        return 0
    try:
        subprocess.run(
            [sys.executable, script, "--context", f"edit: {fp}"],
            timeout=120, cwd=root, capture_output=True,
        )
        _log_hook_event("post_edit_blueprint", fp, 0)
    except Exception as exc:
        _log_hook_event("post_edit_blueprint", fp, 1, error=str(exc))
    return 0


def _post_edit_design_review(payload: dict) -> int:
    """Trigger design review for any edited file (no .py filter)."""
    fp = _extract_file_path(payload)
    root = _project_root()
    script = os.path.join(root, "scripts", "design_review_trigger.py")
    if not os.path.isfile(script):
        return 0
    try:
        subprocess.run([sys.executable, script, fp], timeout=5, cwd=root, capture_output=True)
        _log_hook_event("post_edit_design_review", fp, 0)
    except Exception as exc:
        _log_hook_event("post_edit_design_review", fp, 1, error=str(exc))
    return 0


def _post_edit_test(payload: dict) -> int:
    """Run related pytest tests immediately after .py edit (fast feedback path).

    Finds tests/test_<module>.py matching the edited file and runs them.
    Falls back to tests/ --ignore=test_web_project_scope.py if no match found.
    """
    fp = _extract_file_path(payload)
    if not fp or not fp.endswith(".py"):
        return 0
    root = _project_root()

    # edited file → candidate test file name
    basename = os.path.basename(fp)
    module_name = basename[:-3]  # strip .py
    test_candidate = os.path.join(root, "tests", f"test_{module_name}.py")

    if os.path.isfile(test_candidate):
        test_target = test_candidate
    else:
        # fallback: full suite (excluding known collection-error test)
        test_target = os.path.join(root, "tests")

    try:
        r = subprocess.run(
            [
                sys.executable, "-m", "pytest", test_target,
                "-q", "--tb=line", "--no-header",
                f"--ignore={os.path.join(root, 'tests', 'test_web_project_scope.py')}",
            ],
            capture_output=True, text=True, timeout=60, cwd=root,
        )
        if r.returncode != 0:
            print(f"[af-test] FAIL in {fp}\n{r.stdout[-2000:]}", file=sys.stderr)
        _log_hook_event("post_edit_test", fp, r.returncode)
    except Exception as exc:
        _log_hook_event("post_edit_test", fp, 1, error=str(exc))
    return 0


_BUILTINS: dict[str, object] = {
    "post_edit_py_compile": _post_edit_py_compile,
    "post_edit_enqueue": _post_edit_enqueue,
    "post_edit_code_review": _post_edit_code_review,
    "post_edit_blueprint": _post_edit_blueprint,
    "post_edit_design_review": _post_edit_design_review,
    "post_edit_test": _post_edit_test,
}


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    cmd = sys.argv[1]

    # Builtin dispatch — checked before script-resolve path (backward compat preserved)
    if cmd in _BUILTINS:
        payload = _read_hook_stdin_once()
        return _BUILTINS[cmd](payload)  # type: ignore[operator]

    script_name = cmd
    extra_args = sys.argv[2:]

    root = _project_root()
    workspace = _detect_workspace()
    python = _find_venv_python(root)
    script = _resolve_script(script_name, root)

    if not os.path.isfile(script):
        return 0

    cmd_list = [python, script] + extra_args
    stdin_arg = sys.stdin if not sys.stdin.isatty() else subprocess.DEVNULL
    try:
        proc = subprocess.Popen(
            cmd_list,
            cwd=workspace,
            stdin=stdin_arg,
        )
        proc.wait(timeout=120)
        return proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        print(f"[hook_runner] timeout: {script_name}", file=sys.stderr)
        return 0
    except Exception as exc:
        print(f"[hook_runner] error: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
