from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.destructive_guard import inject_destructive_guard_contract
from core.implementation_language_policy import inject_implementation_language_contract
from core.providers.session_adapter import finalize_cli_session, prepare_cli_session


def _default_cli_timeout_sec() -> int:
    """환경변수 AGENT_CLI_TIMEOUT_SEC로 CLI 실행 타임아웃을 조절할 수 있다."""
    raw = str(os.getenv("AGENT_CLI_TIMEOUT_SEC", "") or "").strip()
    if raw:
        try:
            return max(60, int(raw))
        except ValueError:
            pass
    return 900  # 15분 (복잡한 작업 대응)


@dataclass(frozen=True)
class CliChatRequest:
    provider_id: str
    model: str
    system_prompt: str
    task_input: str
    workspace: str
    run_id: str = ""
    timeout_sec: int = 0  # 0이면 _default_cli_timeout_sec() 사용
    auto_approve: bool = False
    allow_file_edit: bool = True  # False이면 headless_edit_flags 제외(control-plane JSON 전용 호출)

    @property
    def effective_timeout_sec(self) -> int:
        return self.timeout_sec if self.timeout_sec > 0 else _default_cli_timeout_sec()


@dataclass(frozen=True)
class CliProviderSpec:
    provider_id: str
    default_command: tuple[str, ...]
    command_env: str
    install_command_env: str = ""
    install_package: str = ""
    prompt_flag: str | None = None
    model_flag: str | None = None
    system_prompt_flag: str | None = None
    output_format_flags: tuple[str, ...] = ()
    fixed_flags: tuple[str, ...] = ()
    combine_system_prompt: bool = False
    workspace_access_flag: str | None = None
    headless_edit_flags: tuple[str, ...] = ()
    auth_status_command: tuple[str, ...] = ()
    auth_login_command: tuple[str, ...] = ()


_CLI_SPECS = {
    "claude_cli": CliProviderSpec(
        provider_id="claude_cli",
        default_command=("claude",),
        command_env="AGENT_CLAUDE_CLI_COMMAND",
        install_command_env="AGENT_CLAUDE_CLI_INSTALL_COMMAND",
        install_package="@anthropic-ai/claude-code",
        prompt_flag="-p",
        model_flag="--model",
        system_prompt_flag="--append-system-prompt",
        output_format_flags=("--output-format", "json"),
        workspace_access_flag="--add-dir",
        headless_edit_flags=("--permission-mode", "bypassPermissions"),
        auth_status_command=("auth", "status"),
        auth_login_command=("auth", "login"),
    ),
    "gemini_cli": CliProviderSpec(
        provider_id="gemini_cli",
        default_command=("gemini",),
        command_env="AGENT_GEMINI_CLI_COMMAND",
        install_command_env="AGENT_GEMINI_CLI_INSTALL_COMMAND",
        install_package="@google/gemini-cli",
        prompt_flag="-p",
        model_flag="-m",
        output_format_flags=("--output-format", "json"),
        combine_system_prompt=True,
        workspace_access_flag="--include-directories",
        headless_edit_flags=("--sandbox", "--approval-mode", "yolo"),
    ),
    "codex_cli": CliProviderSpec(
        provider_id="codex_cli",
        default_command=("codex", "--ask-for-approval", "never", "--sandbox", "workspace-write", "exec", "--skip-git-repo-check"),
        command_env="AGENT_CODEX_CLI_COMMAND",
        install_command_env="AGENT_CODEX_CLI_INSTALL_COMMAND",
        install_package="@openai/codex",
        model_flag="-m",
        fixed_flags=("-c", 'model_reasoning_effort="low"'),
        combine_system_prompt=True,
        workspace_access_flag="--add-dir",
        headless_edit_flags=(),
        auth_status_command=("login", "status"),
        auth_login_command=("login",),
    ),
}

_PERMISSION_DENIED_MARKERS = (
    "access is denied",
    "access denied",
    "permission denied",
    "operation not permitted",
    "unauthorizedaccess",
    "os error 5",
)

_AUTH_REQUIRED_MARKERS = (
    "not logged in",
    "not authenticated",
    "authentication required",
    "authentication_error",
    "invalid authentication credentials",
    "login required",
    "please login",
    "please log in",
    "run `codex login`",
    "run codex login",
    "sign in required",
    "failed to authenticate",
)

_HOOK_FAILURE_MARKERS = (
    "can't open file",
    "hook_runner.py] failed",
    "cli_hook_bridge.py] failed",
    "hook_bridge.py] failed",
)


def get_cli_provider_spec(provider_id: str) -> CliProviderSpec:
    key = str(provider_id or "").strip().lower()
    try:
        return _CLI_SPECS[key]
    except KeyError as exc:
        raise ValueError(f"unsupported_cli_provider:{provider_id}") from exc


def _split_command_template(text: str) -> list[str]:
    return shlex.split(text, posix=(os.name != "nt"))


def _resolve_base_command(spec: CliProviderSpec) -> list[str]:
    override = str(os.getenv(spec.command_env, "") or "").strip()
    if override:
        override_parts = _split_command_template(override)
        if len(override_parts) == 1 and len(spec.default_command) > 1:
            return override_parts + list(spec.default_command[1:])
        return override_parts
    resolved = _resolve_installed_command(spec.default_command)
    if resolved:
        return resolved
    return list(spec.default_command)


def _windows_roaming_npm_dir() -> str:
    appdata = str(os.getenv("APPDATA", "") or "").strip()
    if appdata:
        return os.path.join(appdata, "npm")
    home = str(os.path.expanduser("~") or "").strip()
    if home:
        return os.path.join(home, "AppData", "Roaming", "npm")
    return ""


def _resolve_installed_command(default_command: tuple[str, ...]) -> list[str] | None:
    if not default_command:
        return None

    executable = str(default_command[0]).strip()
    if not executable:
        return None

    found = shutil.which(executable)
    if found:
        return [found] + list(default_command[1:])

    if os.name == "nt":
        npm_dir = _windows_roaming_npm_dir()
        if npm_dir:
            for suffix in (".cmd", ".exe", ".bat"):
                candidate = os.path.join(npm_dir, executable + suffix)
                if os.path.exists(candidate):
                    return [candidate] + list(default_command[1:])

    return None


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    text = str(raw).strip().lower()
    if not text:
        return default
    return text not in {"0", "false", "no", "off"}


def _default_install_command(spec: CliProviderSpec) -> list[str]:
    if not spec.install_package:
        return []
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    return [npm_cmd, "install", "-g", spec.install_package]


def _resolve_install_command(spec: CliProviderSpec) -> list[str]:
    override = str(os.getenv(spec.install_command_env, "") or "").strip()
    if override:
        return _split_command_template(override)
    return _default_install_command(spec)


def _should_auto_install(request: CliChatRequest, spec: CliProviderSpec) -> bool:
    if not spec.install_package and not spec.install_command_env:
        return False
    return _env_truthy("AGENT_AUTO_INSTALL_CLI", default=bool(request.auto_approve))


_PROGRESS_INTERVAL_SEC = 30  # 진행 표시 간격


def _progress_printer(
    provider_id: str,
    timeout_sec: int,
    stop_event: threading.Event,
    start_time: float = 0.0,
) -> None:
    """CLI 실행 중 경과 시간을 주기적으로 출력하는 스레드 함수."""
    start = start_time or time.monotonic()
    while not stop_event.wait(_PROGRESS_INTERVAL_SEC):
        elapsed = int(time.monotonic() - start)
        remaining = timeout_sec - elapsed
        if remaining <= 0:
            break
        mins, secs = divmod(elapsed, 60)
        rem_mins, rem_secs = divmod(remaining, 60)
        print(
            f"  [{provider_id}] running... "
            f"{mins}m {secs}s elapsed (remaining: {rem_mins}m {rem_secs}s)",
            flush=True,
        )


def _run_command(
    runner: Callable[..., subprocess.CompletedProcess],
    cmd: list[str],
    *,
    cwd: str,
    env: dict[str, str],
    timeout_sec: int,
    input_text: str | None = None,
    provider_id: str = "",
) -> subprocess.CompletedProcess:
    # 테스트 mock이 아닌 실제 실행일 때만 진행 표시
    show_progress = (runner is subprocess.run) and timeout_sec > _PROGRESS_INTERVAL_SEC
    stop_event: threading.Event | None = None
    cmd_start = time.monotonic()

    if show_progress:
        stop_event = threading.Event()
        t = threading.Thread(
            target=_progress_printer,
            args=(provider_id or "cli", timeout_sec, stop_event, cmd_start),
            daemon=True,
        )
        t.start()

    try:
        return runner(
            cmd,
            cwd=cwd,
            env=env,
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=max(1, int(timeout_sec)),
        )
    finally:
        if stop_event is not None:
            stop_event.set()


def _attempt_cli_auto_install(
    request: CliChatRequest,
    spec: CliProviderSpec,
    env: dict[str, str],
    run_command: Callable[..., subprocess.CompletedProcess] | None = None,
) -> dict:
    install_cmd = _resolve_install_command(spec)
    if not install_cmd:
        return {"ok": False, "attempted": False, "reason": "auto_install_not_configured"}

    runner = run_command or subprocess.run
    timeout_sec = max(120, int(os.getenv("AGENT_CLI_INSTALL_TIMEOUT_SEC", "900") or "900"))

    try:
        completed = _run_command(
            runner,
            install_cmd,
            cwd=str(request.workspace),
            env=env,
            timeout_sec=timeout_sec,
        )
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "attempted": True,
            "reason": f"install_command_not_found:{install_cmd[0]}",
            "stdout": "",
            "stderr": str(exc),
            "returncode": None,
            "command": install_cmd,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "attempted": True,
            "reason": "cli_auto_install_timeout",
            "stdout": str(getattr(exc, "stdout", "") or ""),
            "stderr": str(getattr(exc, "stderr", "") or ""),
            "returncode": None,
            "command": install_cmd,
        }

    return {
        "ok": completed.returncode == 0,
        "attempted": True,
        "reason": "cli_auto_install_ok" if completed.returncode == 0 else "cli_auto_install_failed",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
        "command": install_cmd,
    }


def _build_cli_env(request: CliChatRequest, prepared: dict) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    env.setdefault("TERM", "dumb")
    env.update(prepared.get("env", {}))
    if request.provider_id == "claude_cli":
        env.pop("ANTHROPIC_API_KEY", None)
    if request.provider_id == "gemini_cli":
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI"):
            env.pop(name, None)
        env["GOOGLE_GENAI_USE_GCA"] = "true"
    if request.provider_id == "codex_cli":
        env.pop("OPENAI_API_KEY", None)
    return env


def _command_exists(command: str) -> bool:
    target = str(command or "").strip()
    if not target:
        return False
    if os.path.isabs(target) or any(sep in target for sep in (os.sep, "/")):
        return os.path.exists(target)
    return shutil.which(target) is not None


def _excerpt(text: str, limit: int = 400) -> str:
    return str(text or "")[:limit]


def _classify_cli_issue(stdout: str, stderr: str) -> str:
    haystack = f"{stdout}\n{stderr}".lower()
    if any(marker in haystack for marker in _PERMISSION_DENIED_MARKERS):
        return "permission_denied"
    if any(marker in haystack for marker in _AUTH_REQUIRED_MARKERS):
        return "auth_required"
    if any(marker in haystack for marker in _HOOK_FAILURE_MARKERS):
        return "hook_failure"
    return ""


def _should_auto_login(spec: CliProviderSpec) -> bool:
    if not spec.auth_login_command:
        return False
    return _env_truthy("AGENT_AUTO_LOGIN_CLI", default=True)


def _auth_timeout_sec() -> int:
    raw = str(os.getenv("AGENT_CLI_AUTH_TIMEOUT_SEC", "300") or "300").strip()
    try:
        return max(30, int(raw))
    except ValueError:
        return 300


def _auth_status_timeout_sec() -> int:
    raw = str(os.getenv("AGENT_CLI_AUTH_STATUS_TIMEOUT_SEC", "30") or "30").strip()
    try:
        return max(5, int(raw))
    except ValueError:
        return 30


def _build_auth_command(executable: str, suffix: tuple[str, ...]) -> list[str]:
    return [str(executable).strip(), *list(suffix)]


def _run_cli_auth_preflight(
    request: CliChatRequest,
    spec: CliProviderSpec,
    cmd: list[str],
    env: dict[str, str],
    runner: Callable[..., subprocess.CompletedProcess],
) -> dict:
    preflight = {
        "provider_id": spec.provider_id,
        "status": "skipped",
        "auth_checked": False,
        "login_attempted": False,
    }
    if not spec.auth_status_command:
        return preflight

    executable = str(cmd[0]).strip() if cmd else ""
    if not _command_exists(executable):
        preflight["status"] = "command_unavailable"
        return preflight

    status_cmd = _build_auth_command(executable, spec.auth_status_command)
    preflight["auth_checked"] = True
    preflight["status_command"] = status_cmd
    try:
        status_completed = _run_command(
            runner,
            status_cmd,
            cwd=str(request.workspace),
            env=env,
            timeout_sec=_auth_status_timeout_sec(),
        )
    except FileNotFoundError as exc:
        preflight["status"] = "command_unavailable"
        preflight["status_stderr_excerpt"] = _excerpt(str(exc))
        return preflight
    except subprocess.TimeoutExpired as exc:
        preflight["status"] = "status_timeout"
        preflight["status_stdout_excerpt"] = _excerpt(str(getattr(exc, "stdout", "") or ""))
        preflight["status_stderr_excerpt"] = _excerpt(str(getattr(exc, "stderr", "") or ""))
        preflight["fatal_reason"] = "cli_auth_preflight_timeout"
        return preflight

    preflight["status_returncode"] = status_completed.returncode
    preflight["status_stdout_excerpt"] = _excerpt(status_completed.stdout)
    preflight["status_stderr_excerpt"] = _excerpt(status_completed.stderr)
    status_issue = _classify_cli_issue(status_completed.stdout, status_completed.stderr)

    if status_completed.returncode == 0 and status_issue != "permission_denied":
        preflight["status"] = "authenticated"
        return preflight

    if status_issue == "permission_denied":
        preflight["status"] = "permission_denied"
        preflight["fatal_reason"] = "cli_permission_denied"
        return preflight

    if status_issue != "auth_required":
        preflight["status"] = "status_inconclusive"
        return preflight

    preflight["status"] = "auth_required"
    if not _should_auto_login(spec):
        preflight["fatal_reason"] = "cli_auth_required"
        return preflight

    login_cmd = _build_auth_command(executable, spec.auth_login_command)
    preflight["login_attempted"] = True
    preflight["login_command"] = login_cmd
    try:
        login_completed = _run_command(
            runner,
            login_cmd,
            cwd=str(request.workspace),
            env=env,
            timeout_sec=_auth_timeout_sec(),
        )
    except FileNotFoundError as exc:
        preflight["status"] = "command_unavailable"
        preflight["login_stderr_excerpt"] = _excerpt(str(exc))
        preflight["fatal_reason"] = "cli_auth_required"
        return preflight
    except subprocess.TimeoutExpired as exc:
        preflight["status"] = "login_timeout"
        preflight["login_stdout_excerpt"] = _excerpt(str(getattr(exc, "stdout", "") or ""))
        preflight["login_stderr_excerpt"] = _excerpt(str(getattr(exc, "stderr", "") or ""))
        preflight["fatal_reason"] = "cli_auth_login_timeout"
        return preflight

    preflight["login_returncode"] = login_completed.returncode
    preflight["login_stdout_excerpt"] = _excerpt(login_completed.stdout)
    preflight["login_stderr_excerpt"] = _excerpt(login_completed.stderr)
    login_issue = _classify_cli_issue(login_completed.stdout, login_completed.stderr)

    if login_issue == "permission_denied":
        preflight["status"] = "permission_denied"
        preflight["fatal_reason"] = "cli_permission_denied"
        return preflight

    if login_completed.returncode != 0:
        preflight["status"] = "auth_required"
        preflight["fatal_reason"] = "cli_auth_required"
        return preflight

    preflight["status"] = "authenticated"
    return preflight


def _build_preflight_failure_result(
    request: CliChatRequest,
    cmd: list[str],
    preflight: dict,
) -> dict:
    active_command = preflight.get("login_command") or preflight.get("status_command") or cmd
    stdout_excerpt = (
        str(preflight.get("login_stdout_excerpt", "") or "").strip()
        or str(preflight.get("status_stdout_excerpt", "") or "").strip()
    )
    stderr_excerpt = (
        str(preflight.get("login_stderr_excerpt", "") or "").strip()
        or str(preflight.get("status_stderr_excerpt", "") or "").strip()
    )
    return {
        "ok": False,
        "provider_id": request.provider_id,
        "reason": str(preflight.get("fatal_reason") or "cli_auth_required"),
        "stdout": stdout_excerpt,
        "stderr": stderr_excerpt,
        "text": "",
        "returncode": preflight.get("login_returncode", preflight.get("status_returncode")),
        "command": active_command,
        "preflight": preflight,
    }

def _compose_prompt(request: CliChatRequest, spec: CliProviderSpec, system_prompt: str = "") -> str:
    task_text = str(request.task_input or "").strip()
    workspace_text = str(request.workspace or "").strip()
    effective_system_prompt = str(system_prompt or "").strip()
    git_context = _collect_git_context(workspace_text)
    if spec.provider_id == "gemini_cli":
        lines = [
            f"Task: {task_text}",
            "Return the final answer directly. Do not inspect files or use tools unless the task explicitly requires it.",
        ]
        if workspace_text:
            lines.extend(["", f"Workspace: {workspace_text}"])
        if git_context:
            lines.extend(["", git_context])
        if effective_system_prompt:
            lines.extend(["", "System instructions:", effective_system_prompt])
        return "\n".join(lines).strip()
    if spec.combine_system_prompt and effective_system_prompt:
        lines = [
            "[Task]",
            task_text,
            "",
            "Respond to the task directly. Do not summarize the system prompt, workspace, or configuration unless the task explicitly asks for that.",
        ]
        if workspace_text:
            lines.extend(["", "[Workspace]", workspace_text])
        if git_context:
            lines.extend(["", git_context])
        lines.extend(["", "[System Prompt]", effective_system_prompt])
        return "\n".join(lines).strip()
    parts = [f"[Workspace]\n{workspace_text}"]
    if git_context:
        parts.append(git_context)
    parts.append(f"[Task]\n{task_text}")
    return "\n\n".join(parts).strip()


def _detect_repo_root(workspace: str) -> str:
    try:
        current = Path(str(workspace or "")).resolve()
    except (NotImplementedError, OSError):
        return ""
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return ""


def _collect_git_context(workspace: str) -> str:
    """Extract git state (HEAD, recent commits, working tree status) for prompt injection."""
    repo_root = _detect_repo_root(workspace)
    if not repo_root:
        return ""
    lines = []
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3, check=False)
        b = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           cwd=repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3, check=False)
        head = h.stdout.strip() if h.returncode == 0 else ""
        branch = b.stdout.strip() if b.returncode == 0 else ""
        if head and branch:
            lines.append(f"HEAD: {head} on {branch}")
        elif head:
            lines.append(f"HEAD: {head}")
        elif branch:
            lines.append(f"on {branch}")
    except Exception:
        pass
    try:
        r = subprocess.run(["git", "log", "-5", "--oneline"],
                           cwd=repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3, check=False)
        if r.returncode == 0 and r.stdout.strip():
            lines.append("Recent commits:")
            for line in r.stdout.strip().splitlines():
                lines.append(f"  {line}")
    except Exception:
        pass
    try:
        r = subprocess.run(["git", "status", "-sb"],
                           cwd=repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3, check=False)
        if r.returncode == 0 and r.stdout.strip():
            lines.append("Working tree:")
            for line in r.stdout.strip().splitlines():
                lines.append(f"  {line}")
    except Exception:
        pass
    return ("[Git State]\n" + "\n".join(lines)) if lines else ""


def _should_include_model(request: CliChatRequest, spec: CliProviderSpec) -> bool:
    model = str(request.model or "").strip()
    if not model or not spec.model_flag:
        return False
    lowered = model.lower()
    if spec.provider_id == "gemini_cli" and lowered in {"gemini", "models/gemini"}:
        return False
    if spec.provider_id == "claude_cli" and lowered in {"claude", "models/claude"}:
        return False
    return True


def _build_workspace_access_flags(request: CliChatRequest, spec: CliProviderSpec) -> list[str]:
    if not spec.workspace_access_flag:
        return []
    repo_root = _detect_repo_root(request.workspace)
    workspace = str(request.workspace or "").strip()
    if repo_root and workspace and os.path.normcase(repo_root) != os.path.normcase(workspace):
        return [spec.workspace_access_flag, repo_root]
    return []


def compose_cli_prompt(request: CliChatRequest) -> str:
    spec = get_cli_provider_spec(request.provider_id)
    effective_system_prompt = inject_implementation_language_contract(request.system_prompt)
    effective_system_prompt = inject_destructive_guard_contract(effective_system_prompt)
    return _compose_prompt(request, spec, effective_system_prompt)


def build_cli_command(request: CliChatRequest) -> list[str]:
    spec = get_cli_provider_spec(request.provider_id)
    cmd = _resolve_base_command(spec)
    effective_system_prompt = inject_implementation_language_contract(request.system_prompt)
    effective_system_prompt = inject_destructive_guard_contract(effective_system_prompt)

    if _should_include_model(request, spec):
        cmd.extend([spec.model_flag, str(request.model)])
    if spec.headless_edit_flags:
        # allow_file_edit=False는 claude_cli의 bypassPermissions만 차단.
        # gemini_cli의 headless 실행 플래그(--sandbox --approval-mode yolo)는 유지해야 hang을 막는다.
        if request.allow_file_edit or spec.provider_id != "claude_cli":
            cmd.extend(spec.headless_edit_flags)
    cmd.extend(_build_workspace_access_flags(request, spec))
    if spec.fixed_flags:
        cmd.extend(spec.fixed_flags)
    if spec.output_format_flags:
        cmd.extend(spec.output_format_flags)
    if effective_system_prompt and spec.system_prompt_flag and not spec.combine_system_prompt:
        cmd.extend([spec.system_prompt_flag, effective_system_prompt])

    prompt_text = _compose_prompt(request, spec, effective_system_prompt)
    if spec.provider_id == "claude_cli":
        # Windows 명령줄 인자 파싱 문제 방지: 프롬프트를 stdin으로 전달
        # claude --print 는 인자 없이 -p 만 있으면 stdin에서 읽음
        cmd.append("-p")
    elif spec.prompt_flag:
        cmd.extend([spec.prompt_flag, prompt_text])
    elif spec.provider_id == "codex_cli":
        cmd.append("-")
    else:
        cmd.append(prompt_text)
    return cmd


def _extract_text(stdout: str) -> str:
    raw = str(stdout or "").strip()
    if not raw:
        return ""

    candidates = [raw]
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if lines:
        candidates.append(lines[-1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except Exception:
            continue
        if isinstance(payload, dict):
            for key in ("result", "text", "content", "message", "output"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if isinstance(payload, list):
            parts = [item for item in payload if isinstance(item, str) and item.strip()]
            if parts:
                return "\n".join(parts)

    return raw


def _extract_codex_agent_message(stderr: str) -> str:
    """codex exec stderr에서 agent_message 이벤트의 최종 응답을 추출한다."""
    raw = str(stderr or "").strip()
    if not raw:
        return ""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("type") == "event_msg":
            inner = obj.get("payload", {})
            if isinstance(inner, dict) and inner.get("type") == "agent_message":
                msg = str(inner.get("message", "") or "").strip()
                if msg:
                    return msg
    return ""


def execute_cli_chat(
    request: CliChatRequest,
    run_command: Callable[..., subprocess.CompletedProcess] | None = None,
    install_command_runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> dict:
    spec = get_cli_provider_spec(request.provider_id)
    cmd = build_cli_command(request)
    # claude_cli도 stdin으로 프롬프트 전달 (Windows 명령줄 길이/파싱 문제 회피)
    input_text = compose_cli_prompt(request) if request.provider_id in ("codex_cli", "claude_cli") else None
    prepared = prepare_cli_session(request, cmd)
    env = _build_cli_env(request, prepared)
    runner = run_command or subprocess.run
    auto_install = {"ok": False, "attempted": False, "reason": "auto_install_not_attempted"}
    preflight = _run_cli_auth_preflight(request, spec, cmd, env, runner)
    if preflight.get("status") == "command_unavailable" and _should_auto_install(request, spec):
        auto_install = _attempt_cli_auto_install(
            request,
            spec,
            env,
            run_command=install_command_runner,
        )
        if auto_install.get("ok"):
            cmd = build_cli_command(request)
            preflight = _run_cli_auth_preflight(request, spec, cmd, env, runner)
    if preflight.get("fatal_reason"):
        result = _build_preflight_failure_result(request, cmd, preflight)
        if auto_install.get("attempted"):
            result["auto_install"] = auto_install
        finalize_cli_session(request, prepared, result)
        return result
    effective_timeout = int(request.effective_timeout_sec)
    display_name = _CLI_SPECS.get(request.provider_id, spec).provider_id
    print(
        f"  [{display_name}] CLI start (timeout: {effective_timeout}s)",
        flush=True,
    )
    started = time.monotonic()
    try:
        completed = _run_command(
            runner,
            cmd,
            cwd=str(request.workspace),
            env=env,
            timeout_sec=effective_timeout,
            input_text=input_text,
            provider_id=request.provider_id,
        )
    except FileNotFoundError as exc:
        auto_install = {"ok": False, "attempted": False, "reason": "auto_install_disabled"}
        if _should_auto_install(request, spec):
            auto_install = _attempt_cli_auto_install(
                request,
                spec,
                env,
                run_command=install_command_runner,
            )
            if auto_install.get("ok"):
                retry_cmd = build_cli_command(request)
                preflight = _run_cli_auth_preflight(request, spec, retry_cmd, env, runner)
                if preflight.get("fatal_reason"):
                    result = _build_preflight_failure_result(request, retry_cmd, preflight)
                    result["auto_install"] = auto_install
                    finalize_cli_session(request, prepared, result)
                    return result
                try:
                    completed = _run_command(
                        runner,
                        retry_cmd,
                        cwd=str(request.workspace),
                        env=env,
                        timeout_sec=int(request.effective_timeout_sec),
                        input_text=input_text,
                        provider_id=request.provider_id,
                    )
                    text = _extract_text(completed.stdout)
                    ok = completed.returncode == 0 and bool(text.strip())
                    result = {
                        "ok": ok,
                        "provider_id": request.provider_id,
                        "reason": request.provider_id if ok else f"{request.provider_id}_failed",
                        "stdout": completed.stdout,
                        "stderr": completed.stderr,
                        "text": text,
                        "returncode": completed.returncode,
                        "command": retry_cmd,
                        "auto_install": auto_install,
                        "preflight": preflight,
                    }
                    finalize_cli_session(request, prepared, result)
                    return result
                except FileNotFoundError as retry_exc:
                    exc = retry_exc
                    cmd = retry_cmd
                except subprocess.TimeoutExpired as retry_exc:
                    result = {
                        "ok": False,
                        "provider_id": request.provider_id,
                        "reason": "cli_timeout",
                        "stdout": str(getattr(retry_exc, "stdout", "") or ""),
                        "stderr": str(getattr(retry_exc, "stderr", "") or ""),
                        "text": "",
                        "returncode": None,
                        "command": retry_cmd,
                        "auto_install": auto_install,
                        "preflight": preflight,
                    }
                    finalize_cli_session(request, prepared, result)
                    return result

        result = {
            "ok": False,
            "provider_id": request.provider_id,
            "reason": f"cli_command_not_found:{cmd[0]}",
            "stdout": "",
            "stderr": str(exc),
            "text": "",
            "returncode": None,
            "command": cmd,
            "auto_install": auto_install,
            "preflight": preflight,
        }
        finalize_cli_session(request, prepared, result)
        return result
    except subprocess.TimeoutExpired as exc:
        elapsed = int(time.monotonic() - started)
        mins, secs = divmod(elapsed, 60)
        print(
            f"  [{display_name}] timeout ({mins}m {secs}s elapsed, limit: {effective_timeout}s)",
            flush=True,
        )
        result = {
            "ok": False,
            "provider_id": request.provider_id,
            "reason": "cli_timeout",
            "stdout": str(getattr(exc, "stdout", "") or ""),
            "stderr": str(getattr(exc, "stderr", "") or ""),
            "text": "",
            "returncode": None,
            "command": cmd,
            "preflight": preflight,
        }
        finalize_cli_session(request, prepared, result)
        return result

    elapsed = int(time.monotonic() - started)
    text = _extract_text(completed.stdout)
    # codex exec는 stderr에 agent_message로 응답을 출력하고 returncode=1을 반환할 수 있음
    if request.provider_id == "codex_cli" and not text.strip():
        text = _extract_codex_agent_message(completed.stderr)
    issue = _classify_cli_issue(completed.stdout, completed.stderr)
    ok = completed.returncode == 0 and bool(text.strip())
    if not ok and request.provider_id == "codex_cli" and bool(text.strip()):
        if issue not in ("auth_required", "permission_denied", "hook_failure"):
            ok = True
    mins, secs = divmod(elapsed, 60)
    if ok:
        failure_reason = request.provider_id
        print(f"  [{display_name}] done ({mins}m {secs}s)", flush=True)
    else:
        failure_reason = f"{request.provider_id}_{issue}" if issue else f"{request.provider_id}_failed"
        print(f"  [{display_name}] failed: {failure_reason} ({mins}m {secs}s)", flush=True)
    result = {
        "ok": ok,
        "provider_id": request.provider_id,
        "reason": failure_reason,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "text": text,
        "returncode": completed.returncode,
        "command": cmd,
        "auto_install": auto_install,
        "preflight": preflight,
    }
    finalize_cli_session(request, prepared, result)
    return result



