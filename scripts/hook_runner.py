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
import re
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
        r = subprocess.run(
            [sys.executable, script, "--no-llm", "--context", f"edit: {fp}"],
            timeout=120, cwd=root, capture_output=True,
        )
        _log_hook_event("post_edit_code_review", fp, r.returncode)
    except subprocess.TimeoutExpired:
        _log_hook_event("post_edit_code_review", fp, 1, error="timeout")
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
        r = subprocess.run(
            [sys.executable, script, "--no-llm", "--context", f"edit: {fp}"],
            timeout=120, cwd=root, capture_output=True,
        )
        _log_hook_event("post_edit_blueprint", fp, r.returncode)
    except subprocess.TimeoutExpired:
        _log_hook_event("post_edit_blueprint", fp, 1, error="timeout")
    except Exception as exc:
        _log_hook_event("post_edit_blueprint", fp, 1, error=str(exc))
    return 0


def _post_edit_design_review(payload: dict) -> int:
    """Trigger design review for any edited file (no .py filter).

    design_review_trigger.py는 enqueue() + ensure_watcher()만 실행하며
    ControlPlaneLLM을 직접 호출하지 않는다 — child Claude CLI 세션 미생성 보장.
    """
    fp = _extract_file_path(payload)
    root = _project_root()
    script = os.path.join(root, "scripts", "design_review_trigger.py")
    if not os.path.isfile(script):
        return 0
    try:
        r = subprocess.run([sys.executable, script, fp], timeout=5, cwd=root, capture_output=True)
        _log_hook_event("post_edit_design_review", fp, r.returncode)
    except subprocess.TimeoutExpired:
        _log_hook_event("post_edit_design_review", fp, 1, error="timeout")
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


# ── Review-gate builtins ──────────────────────────────────────────────────────

# git commit 정규식: 합성 명령 대응, --help 제외 (§6.2)
_GIT_COMMIT_RE = re.compile(r"(?:^|[\s;&|])git\s+commit\b(?!\s+--help)")

# 에이전트 → tier 매핑 (§6.2)
_AGENT_TIER_MAP: dict[str, int] = {
    "af-test-runner": 1,
    "af-critic": 2,
    "af-cross-review": 3,
}


_SKIP_GATE_RE = re.compile(r"(?:^|[\s;&|])AF_SKIP_REVIEW_GATE=1\b")


def _pre_bash_review_gate(payload: dict) -> int:
    """PreToolUse(Bash): git commit 시도 시 review-gate 판정. BLOCK → exit 2."""
    ti = payload.get("tool_input") or {}
    command = ti.get("command", "")
    if not _GIT_COMMIT_RE.search(command):
        return 0  # git commit 아님 → skip

    # 인라인 환경변수 우회 감지 (AF_SKIP_REVIEW_GATE=1 git commit ...)
    if _SKIP_GATE_RE.search(command) or os.environ.get("AF_SKIP_REVIEW_GATE") == "1":
        _log_hook_event("pre_bash_review_gate", command[:80], 0, error="gate-skipped-cmd")
        return 0

    root = _project_root()
    workspace = _detect_workspace()
    try:
        sys.path.insert(0, root)
        from scripts.review_gate import is_gate_blocked  # type: ignore[import]
        blocked, reason = is_gate_blocked(workspace)
        if blocked:
            print(
                f"\n⛔ [review-gate] 교차검증 미완료: {reason}\n"
                "   af-test-runner → af-critic → af-cross-review 순서로 Agent 실행 후 재시도.\n"
                "   우회: AF_SKIP_REVIEW_GATE=1",
                file=sys.stderr,
            )
            _log_hook_event("pre_bash_review_gate", command[:80], 2, error=reason)
            return 2  # exit 2 → Claude Code Bash 툴 차단
        _log_hook_event("pre_bash_review_gate", command[:80], 0)
    except Exception as exc:
        # fail-open: 훅 버그로 commit 막히면 안 됨 (§10 Q3)
        print(f"[review-gate] 훅 오류 (PASS): {exc}", file=sys.stderr)
        _log_hook_event("pre_bash_review_gate", command[:80], 0, error=str(exc))
    return 0


def _post_agent_record(payload: dict) -> int:
    """PostToolUse(Task/Agent): af-* 에이전트 완료 시 tier 기록."""
    ti = payload.get("tool_input") or {}
    subagent_type = ti.get("subagent_type", "")
    if subagent_type not in _AGENT_TIER_MAP:
        return 0  # 관심 없는 에이전트

    tier = _AGENT_TIER_MAP[subagent_type]

    # tool_response에서 verdict 파싱 — 구조화 패턴만 인식 (본문 키워드 오탐 방지)
    tr = payload.get("tool_response") or {}
    content = ""
    if isinstance(tr, dict):
        content = str(tr.get("content") or tr.get("result") or "")
    elif isinstance(tr, str):
        content = tr

    root = _project_root()
    workspace = _detect_workspace()
    sys.path.insert(0, root)  # 단일 삽입 (L1 중복 제거)

    try:
        from scripts.review_gate import _VERDICT_RE, _VERDICT_HEADER_RE  # type: ignore[import]
        m = _VERDICT_RE.search(content)
        if m:
            verdict = m.group(1).lower()
        else:
            hm = _VERDICT_HEADER_RE.search(content)
            verdict = hm.group(1).lower() if hm else "pass"
    except Exception:
        verdict = "pass"

    if subagent_type == "af-test-runner":
        verdict = _apply_test_gap_verdict(workspace, verdict)

    try:
        from scripts.review_gate import record_review_done  # type: ignore[import]
        # M1: files_snapshot=None → record_review_done이 락 내부에서 직접 읽음 (TOCTOU 해소)
        record_review_done(workspace, subagent_type, tier, verdict)
        _log_hook_event("post_agent_record", subagent_type, 0)
    except Exception as exc:
        _log_hook_event("post_agent_record", subagent_type, 1, error=str(exc))
    return 0


def _apply_test_gap_verdict(workspace: str, verdict: str) -> str:
    """Force af-test-runner verdict to fail when the test-gap analyzer fails."""
    try:
        from scripts import test_gap_analyzer as tga  # type: ignore[import]

        changed = tga.changed_files_from_pending(workspace) or tga.changed_files_from_git(workspace)
        diff_text = tga.git_diff(workspace, changed)
        report = tga.analyze_diff(
            workspace=workspace,
            changed_files=changed,
            diff_text=diff_text,
        )
        if report.verdict == "FAIL":
            _write_test_gap_report(workspace, report)
            try:
                from scripts.review_gate import downgrade_blast_tier  # type: ignore[import]
                downgrade_blast_tier(workspace, 1)
            except Exception:
                pass
            gap_ids = ",".join(g.risk_id for g in report.gaps[:5])
            _log_hook_event("test_gap_analyzer", "af-test-runner", 1, error=f"forced-fail:{gap_ids}")
            return "fail"
        _clear_test_gap_report(workspace)
        _log_hook_event("test_gap_analyzer", "af-test-runner", 0)
    except Exception as exc:
        _log_hook_event("test_gap_analyzer", "af-test-runner", 0, error=f"skipped:{exc}")
    return verdict


def _test_gap_report_path(workspace: str) -> str:
    return os.path.join(workspace, ".af_review_queue", "test_gap_report.json")


def _write_test_gap_report(workspace: str, report: object) -> None:
    try:
        path = _test_gap_report_path(workspace)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp"
        payload = report.to_dict() if hasattr(report, "to_dict") else {"verdict": "FAIL"}
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception as exc:
        _log_hook_event("test_gap_analyzer", "af-test-runner", 0, error=f"report-write-skipped:{exc}")


def _clear_test_gap_report(workspace: str) -> None:
    try:
        os.unlink(_test_gap_report_path(workspace))
    except FileNotFoundError:
        pass
    except Exception as exc:
        _log_hook_event("test_gap_analyzer", "af-test-runner", 0, error=f"report-clear-skipped:{exc}")


def _post_commit_clear(payload: dict) -> int:
    """PostToolUse(Bash): commit 성공 후 커밋된 파일 정리."""
    ti = payload.get("tool_input") or {}
    command = ti.get("command", "")
    if not _GIT_COMMIT_RE.search(command):
        return 0  # git commit 아님 → skip

    # exit_code 확인 — 확실히 0임을 확인한 경우에만 정리 (fail-safe: 불확실 → skip)
    tr = payload.get("tool_response") or {}
    exit_code = None
    if isinstance(tr, dict):
        exit_code = tr.get("exit_code") if "exit_code" in tr else tr.get("returncode")
    if exit_code is None:
        return 0  # exit_code 미확인 → 커밋 성공 여부 불명 → 정리 생략
    try:
        if int(exit_code) != 0:
            return 0  # 커밋 실패
    except (ValueError, TypeError):
        return 0  # 파싱 불가 → 생략

    root = _project_root()
    workspace = _detect_workspace()
    try:
        r = subprocess.run(
            ["git", "diff", "HEAD~1", "--name-only"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        if r.returncode != 0:
            # M2: 첫 커밋(HEAD~1 없음) 또는 git 오류 → 정리 생략 (safe no-op)
            return 0
        committed_files = [f.strip() for f in r.stdout.splitlines() if f.strip()]
        sys.path.insert(0, root)
        from scripts.review_gate import clear_committed_files  # type: ignore[import]
        clear_committed_files(workspace, committed_files)
        _log_hook_event("post_commit_clear", command[:80], 0)
    except Exception as exc:
        _log_hook_event("post_commit_clear", command[:80], 1, error=str(exc))
    return 0


_BUILTINS: dict[str, object] = {
    "post_edit_py_compile": _post_edit_py_compile,
    "post_edit_enqueue": _post_edit_enqueue,
    "post_edit_code_review": _post_edit_code_review,
    "post_edit_blueprint": _post_edit_blueprint,
    "post_edit_design_review": _post_edit_design_review,
    "post_edit_test": _post_edit_test,
    # Review-gate builtins
    "pre_bash_review_gate": _pre_bash_review_gate,
    "post_agent_record": _post_agent_record,
    "post_commit_clear": _post_commit_clear,
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
