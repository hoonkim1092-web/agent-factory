import importlib
import json
import os
import sys
import types

import pytest


def test_config_paths_allows_cli_only_bootstrap_without_api_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_CHAT_PROVIDER", "claude_cli")
    monkeypatch.setenv("AGENT_PROJECT_ROOT", str(tmp_path / "proj"))
    monkeypatch.setenv("AGENT_PROJECT_ID", "proj_cli_boot")

    import core.config_paths

    cfg = importlib.reload(core.config_paths)
    assert cfg.PROJECT_ID == "proj_cli_boot"
    assert cfg.PROJECT_ROOT.endswith("proj")


def test_cli_provider_registry_defaults_and_filtering():
    from core.providers.registry import (
        default_chat_model_for_provider,
        engine_api_keys_disabled,
        get_engine_api_key,
        get_requested_cli_providers,
        strip_engine_api_keys,
        supports_cli_bootstrap,
    )

    assert get_requested_cli_providers("claude_cli, gemini, codex_cli") == ["claude_cli", "codex_cli"]
    assert default_chat_model_for_provider("claude_cli") == "claude"
    assert default_chat_model_for_provider("gemini_cli") == "gemini"
    assert default_chat_model_for_provider("codex_cli") == ""
    assert supports_cli_bootstrap("gemini_cli") is True
    assert supports_cli_bootstrap("gemini") is False
    assert engine_api_keys_disabled("gemini_cli") is True
    assert get_engine_api_key("google", raw_provider="gemini_cli") == ""
    assert strip_engine_api_keys({"GOOGLE_API_KEY": "x", "PATH": "ok"}, raw_provider="gemini_cli") == {"PATH": "ok"}


def test_config_paths_ignores_engine_api_keys_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_DISABLE_ENGINE_API_KEYS", "1")
    monkeypatch.delenv("AGENT_CHAT_PROVIDER", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("AGENT_PROJECT_ROOT", str(tmp_path / "proj"))
    monkeypatch.setenv("AGENT_PROJECT_ID", "proj_disabled_keys")

    import core.config_paths

    cfg = importlib.reload(core.config_paths)
    assert cfg.GOOGLE_API_KEY == ""
    assert cfg.OPENAI_API_KEY == ""


@pytest.mark.parametrize(
    ("provider_id", "expected_prefix", "expected_items", "prompt_in_command"),
    [
        ("claude_cli", ["claude"], ["-p", "--append-system-prompt", "--output-format", "json", "--permission-mode", "bypassPermissions"], False),
        ("gemini_cli", ["gemini"], ["-p", "--output-format", "json", "--sandbox", "--approval-mode", "yolo"], True),
        (
            "codex_cli",
            ["codex", "--ask-for-approval", "never", "--sandbox", "workspace-write", "exec", "--skip-git-repo-check"],
            ["-c", "model_reasoning_effort=\"low\"", "-"],
            False,
        ),
    ],
)
def test_build_cli_command_uses_provider_specific_defaults(provider_id, expected_prefix, expected_items, prompt_in_command, monkeypatch):
    from core.providers.cli import CliChatRequest, build_cli_command

    monkeypatch.setenv("AF_SANDBOX", "1")  # sandbox on — 기존 동작 유지

    cmd = build_cli_command(
        CliChatRequest(
            provider_id=provider_id,
            model="test-model",
            system_prompt="system prompt",
            task_input="execute task",
            workspace="D:/workspace",
        )
    )

    first = os.path.basename(cmd[0]).lower()
    assert first in {
        expected_prefix[0],
        expected_prefix[0] + ".cmd",
        expected_prefix[0] + ".exe",
        expected_prefix[0] + ".bat",
    }
    if len(expected_prefix) > 1:
        assert cmd[1: len(expected_prefix)] == expected_prefix[1:]
    for item in expected_items:
        assert item in cmd
    if prompt_in_command:
        assert any("execute task" in part for part in cmd)
    else:
        assert not any("execute task" in part for part in cmd)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path handling only tested on Windows")
def test_codex_cli_path_override_keeps_exec_subcommand(monkeypatch):
    from core.providers.cli import CliChatRequest, build_cli_command

    monkeypatch.setenv("AF_SANDBOX", "1")  # sandbox on — 기존 동작 유지
    monkeypatch.setenv("AGENT_CODEX_CLI_COMMAND", r"C:\Tools\codex.cmd")

    cmd = build_cli_command(
        CliChatRequest(
            provider_id="codex_cli",
            model="gpt-5",
            system_prompt="system prompt",
            task_input="execute task",
            workspace="D:/workspace",
        )
    )

    assert cmd[:7] == [
        r"C:\Tools\codex.cmd",
        "--ask-for-approval",
        "never",
        "--sandbox",
        "workspace-write",
        "exec",
        "--skip-git-repo-check",
    ]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows npm shim only applicable on Windows")
def test_build_cli_command_falls_back_to_windows_roaming_npm_shim(monkeypatch):
    from core.providers.cli import CliChatRequest, build_cli_command

    monkeypatch.delenv("AGENT_GEMINI_CLI_COMMAND", raising=False)
    monkeypatch.setattr("core.providers.cli.shutil.which", lambda _name: None)
    monkeypatch.setattr("core.providers.cli.os.name", "nt")
    monkeypatch.setattr("core.providers.cli.os.getenv", lambda key, default=None: r"C:\Users\HOME\AppData\Roaming" if key == "APPDATA" else default)
    monkeypatch.setattr(
        "core.providers.cli.os.path.exists",
        lambda path: path == r"C:\Users\HOME\AppData\Roaming\npm\gemini.cmd",
    )

    cmd = build_cli_command(
        CliChatRequest(
            provider_id="gemini_cli",
            model="gemini",
            system_prompt="system prompt",
            task_input="execute task",
            workspace="D:/workspace",
        )
    )

    assert cmd[0] == r"C:\Users\HOME\AppData\Roaming\npm\gemini.cmd"


def test_gemini_cli_default_alias_omits_model_flag():
    from core.providers.cli import CliChatRequest, build_cli_command

    cmd = build_cli_command(
        CliChatRequest(
            provider_id="gemini_cli",
            model="gemini",
            system_prompt="system prompt",
            task_input="execute task",
            workspace="D:/workspace",
        )
    )

    assert "-m" not in cmd


def test_gemini_cli_prompt_prioritizes_task_before_system_context():
    from core.providers.cli import CliChatRequest, build_cli_command

    cmd = build_cli_command(
        CliChatRequest(
            provider_id="gemini_cli",
            model="gemini",
            system_prompt="system prompt",
            task_input="reply exactly",
            workspace="D:/workspace",
        )
    )

    prompt = cmd[cmd.index("-p") + 1]
    assert prompt.startswith("Task: reply exactly")
    assert "Do not inspect files or use tools" in prompt
    assert "System instructions:" in prompt
    assert "[Destructive Action Guard]" in prompt
    assert "git reset --hard" in prompt


def test_gemini_cli_normalized_default_alias_omits_model_flag():
    from core.providers.cli import CliChatRequest, build_cli_command

    cmd = build_cli_command(
        CliChatRequest(
            provider_id="gemini_cli",
            model="models/gemini",
            system_prompt="system prompt",
            task_input="execute task",
            workspace="D:/workspace",
        )
    )

    assert "-m" not in cmd


def test_codex_cli_combined_prompt_prioritizes_task_and_includes_destructive_guard():
    from core.providers.cli import CliChatRequest, compose_cli_prompt

    prompt = compose_cli_prompt(
        CliChatRequest(
            provider_id="codex_cli",
            model="gpt-5",
            system_prompt="system prompt",
            task_input="execute task",
            workspace="D:/workspace",
        )
    )

    assert prompt.startswith("[Task]\nexecute task")
    assert "Do not summarize the system prompt, workspace, or configuration" in prompt
    assert "[System Prompt]" in prompt
    assert "[Destructive Action Guard]" in prompt
    assert "git clean" in prompt


def test_build_cli_command_uses_stdin_prompt_for_codex_cli():
    from core.providers.cli import CliChatRequest, build_cli_command

    cmd = build_cli_command(
        CliChatRequest(
            provider_id="codex_cli",
            model="gpt-5",
            system_prompt="system prompt",
            task_input="execute task",
            workspace="D:/workspace",
        )
    )

    assert cmd[-1] == "-"


def test_claude_cli_append_system_prompt_includes_destructive_guard():
    from core.providers.cli import CliChatRequest, build_cli_command

    cmd = build_cli_command(
        CliChatRequest(
            provider_id="claude_cli",
            model="claude",
            system_prompt="system prompt",
            task_input="execute task",
            workspace="D:/workspace",
        )
    )

    prompt = cmd[cmd.index("--append-system-prompt") + 1]
    assert "[Destructive Action Guard]" in prompt
    assert "Remove-Item" in prompt


@pytest.mark.parametrize(
    ("provider_id", "expected_flag"),
    [
        ("claude_cli", "--add-dir"),
        ("gemini_cli", "--include-directories"),
        ("codex_cli", "--add-dir"),
    ],
)
def test_cli_provider_includes_repo_root_when_workspace_is_nested(monkeypatch, provider_id, expected_flag):
    from core.providers.cli import CliChatRequest, build_cli_command

    monkeypatch.setattr("core.providers.cli._detect_repo_root", lambda _workspace: r"D:\repo")

    cmd = build_cli_command(
        CliChatRequest(
            provider_id=provider_id,
            model="gemini" if provider_id == "gemini_cli" else "test-model",
            system_prompt="system prompt",
            task_input="execute task",
            workspace=r"D:\repo\projects\demo",
        )
    )

    assert expected_flag in cmd
    idx = cmd.index(expected_flag)
    assert cmd[idx + 1] == r"D:\repo"


def test_agent_runner_uses_cli_provider_before_sdk_fallback(monkeypatch, tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / ".todo.md").write_text("- execute task\n", encoding="utf-8")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_CHAT_PROVIDER", "codex_cli")
    monkeypatch.setenv("AGENT_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("AGENT_PROJECT_ID", "proj_cli_runner")

    import core.config_paths
    import core.utils
    import core.agent_runner as ar

    importlib.reload(core.config_paths)
    importlib.reload(core.utils)
    ar = importlib.reload(ar)

    calls = []

    def fake_execute_cli_chat(request, run_command=None):
        calls.append(request)
        return {
            "ok": True,
            "provider_id": request.provider_id,
            "text": "cli output",
            "stdout": "cli output",
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(ar, "execute_cli_chat", fake_execute_cli_chat)

    runner = ar.AgentRunner(ar.ModelRouter())
    monkeypatch.setattr(runner, "load_skills", lambda agent, **kw: [])
    monkeypatch.setattr(
        runner,
        "build_tool_registry",
        lambda modules, ctx, policy: types.SimpleNamespace(get_active_tools=lambda: []),
    )

    result = runner.run(
        {"name": "cli-agent", "role": "architect", "skills": []},
        "execute task",
        workspace=str(project_root),
    )

    assert result["ok"] is True
    assert result["reason"] == "codex_cli"
    assert calls
    assert calls[0].provider_id == "codex_cli"


def test_agent_runner_cli_only_short_task_does_not_require_todo(monkeypatch, tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_CHAT_PROVIDER", "codex_cli")
    monkeypatch.setenv("AGENT_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("AGENT_PROJECT_ID", "proj_cli_short_task")

    import core.config_paths
    import core.utils
    import core.agent_runner as ar

    importlib.reload(core.config_paths)
    importlib.reload(core.utils)
    ar = importlib.reload(ar)

    calls = []

    def fake_execute_cli_chat(request, run_command=None):
        calls.append(request)
        return {
            "ok": True,
            "provider_id": request.provider_id,
            "text": "AGENT_FACTORY_OK",
            "stdout": "AGENT_FACTORY_OK",
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(ar, "execute_cli_chat", fake_execute_cli_chat)

    runner = ar.AgentRunner(ar.ModelRouter())
    monkeypatch.setattr(runner, "load_skills", lambda agent, **kw: [])
    monkeypatch.setattr(
        runner,
        "build_tool_registry",
        lambda modules, ctx, policy: types.SimpleNamespace(get_active_tools=lambda: []),
    )

    result = runner.run(
        {"name": "cli-agent", "role": "project manager", "skills": []},
        "Return AGENT_FACTORY_OK",
        workspace=str(project_root),
    )

    assert result["ok"] is True
    assert result["reason"] == "codex_cli"
    assert calls
    assert calls[0].provider_id == "codex_cli"


def test_agent_runner_cli_only_still_blocks_complex_task_without_todo(monkeypatch, tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_CHAT_PROVIDER", "codex_cli")
    monkeypatch.setenv("AGENT_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("AGENT_PROJECT_ID", "proj_cli_complex_task")

    import core.config_paths
    import core.utils
    import core.agent_runner as ar

    importlib.reload(core.config_paths)
    importlib.reload(core.utils)
    ar = importlib.reload(ar)

    calls = []

    def fake_execute_cli_chat(request, run_command=None):
        calls.append(request)
        return {
            "ok": True,
            "provider_id": request.provider_id,
            "text": "unexpected",
            "stdout": "unexpected",
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(ar, "execute_cli_chat", fake_execute_cli_chat)

    runner = ar.AgentRunner(ar.ModelRouter())
    monkeypatch.setattr(runner, "load_skills", lambda agent, **kw: [])
    monkeypatch.setattr(
        runner,
        "build_tool_registry",
        lambda modules, ctx, policy: types.SimpleNamespace(get_active_tools=lambda: []),
    )

    result = runner.run(
        {"name": "cli-agent", "role": "generalist", "skills": []},
        "implement a small feature",
        workspace=str(project_root),
    )

    assert result["ok"] is False
    assert result["reason"] == "hook_event_bus_blocked_pre"
    assert calls == []


def test_execute_cli_chat_persists_failed_launch_state(tmp_path):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)

    def missing_runner(*args, **kwargs):
        raise FileNotFoundError("missing cli")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id="codex_cli",
            model="codex",
            system_prompt="system prompt",
            task_input="ship feature",
            workspace=str(workspace),
            run_id="run_missing",
        ),
        run_command=missing_runner,
    )

    state_path = workspace / ".af_runtime" / "cli_sessions" / "codex_cli_run_missing.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert result["ok"] is False
    assert result["reason"].startswith("cli_command_not_found:")
    assert state["ok"] is False
    assert state["reason"].startswith("cli_command_not_found:")


def test_execute_cli_chat_auto_installs_missing_provider_and_retries(monkeypatch, tmp_path):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_AUTO_INSTALL_CLI", "1")

    run_calls = []

    def cli_runner(*args, **kwargs):
        run_calls.append(list(args[0]))
        if len(run_calls) == 1:
            raise FileNotFoundError("missing cli")
        return types.SimpleNamespace(returncode=0, stdout='{"text":"installed ok"}', stderr="")

    install_calls = []

    def install_runner(*args, **kwargs):
        install_calls.append(list(args[0]))
        return types.SimpleNamespace(returncode=0, stdout="installed", stderr="")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id="claude_cli",
            model="claude",
            system_prompt="system prompt",
            task_input="ship feature",
            workspace=str(workspace),
            run_id="run_auto_install",
        ),
        run_command=cli_runner,
        install_command_runner=install_runner,
    )

    assert result["ok"] is True
    assert result["reason"] == "claude_cli"
    assert result["text"] == "installed ok"
    assert len(run_calls) == 3
    assert run_calls[0][1:] == ["auth", "status"]
    assert run_calls[1][1:] == ["auth", "status"]
    assert install_calls == [["npm.cmd" if os.name == "nt" else "npm", "install", "-g", "@anthropic-ai/claude-code"]]
    assert result["auto_install"]["ok"] is True


def test_execute_cli_chat_keeps_not_found_when_auto_install_disabled(monkeypatch, tmp_path):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_AUTO_INSTALL_CLI", "0")

    def missing_runner(*args, **kwargs):
        raise FileNotFoundError("missing cli")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id="gemini_cli",
            model="gemini",
            system_prompt="system prompt",
            task_input="ship feature",
            workspace=str(workspace),
            run_id="run_no_auto_install",
        ),
        run_command=missing_runner,
    )

    assert result["ok"] is False
    assert result["reason"].startswith("cli_command_not_found:")
    assert result["auto_install"]["attempted"] is False


@pytest.mark.parametrize(
    ("provider_id", "seed_env", "blocked_env", "expected_env"),
    [
        ("claude_cli", {"ANTHROPIC_API_KEY": "anthropic-secret"}, ["ANTHROPIC_API_KEY"], {}),
        ("codex_cli", {"OPENAI_API_KEY": "openai-secret"}, ["OPENAI_API_KEY"], {}),
        (
            "gemini_cli",
            {
                "GEMINI_API_KEY": "gemini-secret",
                "GOOGLE_API_KEY": "google-secret",
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
            },
            ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI"],
            {"GOOGLE_GENAI_USE_GCA": "true"},
        ),
    ],
)
def test_execute_cli_chat_strips_provider_api_key_env(monkeypatch, tmp_path, provider_id, seed_env, blocked_env, expected_env):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)
    for key, value in seed_env.items():
        monkeypatch.setenv(key, value)

    seen = {}

    def cli_runner(*args, **kwargs):
        seen["env"] = dict(kwargs["env"])
        return types.SimpleNamespace(returncode=0, stdout='{"text":"oauth ok"}', stderr="")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id=provider_id,
            model="gemini" if provider_id == "gemini_cli" else "test-model",
            system_prompt="system prompt",
            task_input="ship feature",
            workspace=str(workspace),
            run_id="run_env_strip",
        ),
        run_command=cli_runner,
    )

    assert result["ok"] is True
    for key in blocked_env:
        assert key not in seen["env"]
    for key, value in expected_env.items():
        assert seen["env"][key] == value


def test_execute_cli_chat_sends_codex_prompt_via_stdin(tmp_path):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)
    seen = {}

    def cli_runner(*args, **kwargs):
        seen["cmd"] = list(args[0])
        seen["input"] = kwargs.get("input")
        return types.SimpleNamespace(returncode=0, stdout="AGENT_FACTORY_OK", stderr="")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id="codex_cli",
            model="gpt-5",
            system_prompt="system prompt",
            task_input="Return AGENT_FACTORY_OK",
            workspace=str(workspace),
            run_id="run_codex_stdin",
        ),
        run_command=cli_runner,
    )

    assert result["ok"] is True
    assert seen["cmd"][-1] == "-"
    assert seen["input"].startswith("[Task]\nReturn AGENT_FACTORY_OK")


def test_execute_cli_chat_sends_claude_prompt_via_stdin(tmp_path):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)
    seen = {}

    def cli_runner(*args, **kwargs):
        seen["cmd"] = list(args[0])
        seen["input"] = kwargs.get("input")
        return types.SimpleNamespace(returncode=0, stdout='{"result":"AGENT_FACTORY_OK"}', stderr="")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id="claude_cli",
            model="claude",
            system_prompt="system prompt",
            task_input="Return AGENT_FACTORY_OK",
            workspace=str(workspace),
            run_id="run_claude_stdin",
        ),
        run_command=cli_runner,
    )

    assert result["ok"] is True
    assert "-p" in seen["cmd"]
    assert not any("Return AGENT_FACTORY_OK" in part for part in seen["cmd"])
    assert seen["input"] is not None
    assert "Return AGENT_FACTORY_OK" in seen["input"]


def test_execute_cli_chat_runs_codex_auth_preflight_and_auto_login(monkeypatch, tmp_path):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_AUTO_LOGIN_CLI", "1")

    calls = []

    def cli_runner(*args, **kwargs):
        cmd = list(args[0])
        calls.append(cmd)
        if cmd[1:] == ["login", "status"]:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="Not logged in. Run `codex login`.")
        if cmd[1:] == ["login"]:
            return types.SimpleNamespace(returncode=0, stdout="Login complete", stderr="")
        return types.SimpleNamespace(returncode=0, stdout='{"text":"oauth ok"}', stderr="")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id="codex_cli",
            model="gpt-5",
            system_prompt="system prompt",
            task_input="ship feature",
            workspace=str(workspace),
            run_id="run_codex_auth_repair",
        ),
        run_command=cli_runner,
    )

    state_path = workspace / ".af_runtime" / "cli_sessions" / "codex_cli_run_codex_auth_repair.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["reason"] == "codex_cli"
    assert result["text"] == "oauth ok"
    assert result["preflight"]["status"] == "authenticated"
    assert result["preflight"]["login_attempted"] is True
    assert calls[0][1:] == ["login", "status"]
    assert calls[1][1:] == ["login"]
    assert calls[2][-1] == "-"
    assert state["preflight"]["login_attempted"] is True
    assert state["preflight"]["status"] == "authenticated"


def test_execute_cli_chat_codex_preflight_stops_on_permission_denied(monkeypatch, tmp_path):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_AUTO_LOGIN_CLI", "1")

    calls = []

    def cli_runner(*args, **kwargs):
        cmd = list(args[0])
        calls.append(cmd)
        if cmd[1:] == ["login", "status"]:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="Access is denied. (os error 5)")
        raise AssertionError("main codex exec should not run after preflight permission failure")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id="codex_cli",
            model="gpt-5",
            system_prompt="system prompt",
            task_input="ship feature",
            workspace=str(workspace),
            run_id="run_codex_permission_denied",
        ),
        run_command=cli_runner,
    )

    state_path = workspace / ".af_runtime" / "cli_sessions" / "codex_cli_run_codex_permission_denied.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert result["ok"] is False
    assert result["reason"] == "cli_permission_denied"
    assert result["preflight"]["status"] == "permission_denied"
    assert result["preflight"]["login_attempted"] is False
    assert len(calls) == 1
    assert calls[0][1:] == ["login", "status"]
    assert state["preflight"]["status"] == "permission_denied"


def test_execute_cli_chat_runs_claude_auth_preflight_and_auto_login(monkeypatch, tmp_path):
    from core.providers.cli import CliChatRequest, execute_cli_chat

    workspace = tmp_path / "proj"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_AUTO_LOGIN_CLI", "1")

    calls = []

    def cli_runner(*args, **kwargs):
        cmd = list(args[0])
        calls.append(cmd)
        if cmd[1:] == ["auth", "status"]:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="Not logged in")
        if cmd[1:] == ["auth", "login"]:
            return types.SimpleNamespace(returncode=0, stdout="Login complete", stderr="")
        return types.SimpleNamespace(returncode=0, stdout='{"text":"claude ok"}', stderr="")

    result = execute_cli_chat(
        CliChatRequest(
            provider_id="claude_cli",
            model="claude",
            system_prompt="system prompt",
            task_input="ship feature",
            workspace=str(workspace),
            run_id="run_claude_auth_repair",
        ),
        run_command=cli_runner,
    )

    assert result["ok"] is True
    assert result["reason"] == "claude_cli"
    assert result["text"] == "claude ok"
    assert result["preflight"]["status"] == "authenticated"
    assert result["preflight"]["login_attempted"] is True
    assert calls[0][1:] == ["auth", "status"]
    assert calls[1][1:] == ["auth", "login"]
    assert "-p" in calls[2]




def test_agent_runner_writes_skill_runtime_feedback(monkeypatch, tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / ".todo.md").write_text("- execute task\n", encoding="utf-8")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_CHAT_PROVIDER", "codex_cli")
    monkeypatch.setenv("AGENT_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("AGENT_PROJECT_ID", "proj_cli_runtime_feedback")

    import core.config_paths
    import core.utils
    import core.agent_runner as ar

    importlib.reload(core.config_paths)
    importlib.reload(core.utils)
    ar = importlib.reload(ar)

    def fake_execute_cli_chat(request, run_command=None):
        del run_command
        return {
            "ok": True,
            "provider_id": request.provider_id,
            "text": "cli output",
            "stdout": "cli output",
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(ar, "execute_cli_chat", fake_execute_cli_chat)

    runner = ar.AgentRunner(ar.ModelRouter())
    monkeypatch.setattr(runner, "load_skills", lambda agent, **kw: [types.SimpleNamespace(__skill_id__="runtime_skill")])
    monkeypatch.setattr(
        runner,
        "build_tool_registry",
        lambda modules, ctx, policy: types.SimpleNamespace(get_active_tools=lambda: []),
    )

    result = runner.run(
        {"name": "cli-agent", "role": "architect", "skills": ["runtime_skill"]},
        "execute task",
        workspace=str(project_root),
    )

    events_path = project_root / "data" / "skill-usage.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    runtime_events = [event for event in events if event["event_type"] == "skill_runtime"]

    assert result["ok"] is True
    assert runtime_events
    assert runtime_events[0]["skill_id"] == "runtime_skill"
    assert runtime_events[0]["status"] == "succeeded"
    assert runtime_events[0]["payload"]["reason"] == "codex_cli"


def test_compose_prompt_includes_git_state_claude_cli(monkeypatch):
    from core.providers.cli import _compose_prompt, CliChatRequest, CliProviderSpec
    monkeypatch.setattr(
        "core.providers.cli._collect_git_context",
        lambda ws: "[Git State]\nHEAD: abc1234 on main\nRecent commits:\n  abc1234 feat: add git awareness"
    )
    request = CliChatRequest(
        provider_id="claude_cli",
        model="claude",
        system_prompt="",
        task_input="execute task",
        workspace="/workspace"
    )
    spec = CliProviderSpec(
        provider_id="claude_cli",
        default_command=("claude",),
        command_env="TEST",
        combine_system_prompt=False
    )
    prompt = _compose_prompt(request, spec, "")
    assert "[Git State]" in prompt
    assert "HEAD: abc1234 on main" in prompt


def test_compose_prompt_omits_git_state_when_empty(monkeypatch):
    from core.providers.cli import _compose_prompt, CliChatRequest, CliProviderSpec
    monkeypatch.setattr("core.providers.cli._collect_git_context", lambda ws: "")
    request = CliChatRequest(
        provider_id="claude_cli",
        model="claude",
        system_prompt="",
        task_input="execute task",
        workspace="/workspace"
    )
    spec = CliProviderSpec(
        provider_id="claude_cli",
        default_command=("claude",),
        command_env="TEST",
        combine_system_prompt=False
    )
    prompt = _compose_prompt(request, spec, "")
    assert "[Git State]" not in prompt
    assert "[Workspace]" in prompt
    assert "[Task]" in prompt


def test_gemini_cli_prompt_git_state_after_workspace(monkeypatch):
    from core.providers.cli import _compose_prompt, CliChatRequest, CliProviderSpec
    monkeypatch.setattr(
        "core.providers.cli._collect_git_context",
        lambda ws: "[Git State]\nHEAD: def5678 on feat/x"
    )
    request = CliChatRequest(
        provider_id="gemini_cli",
        model="gemini",
        system_prompt="sys",
        task_input="task",
        workspace="/workspace"
    )
    spec = CliProviderSpec(
        provider_id="gemini_cli",
        default_command=("gemini",),
        command_env="TEST",
        combine_system_prompt=True
    )
    prompt = _compose_prompt(request, spec, "sys prompt")
    assert "Workspace: /workspace" in prompt
    assert "[Git State]" in prompt
    assert prompt.index("[Git State]") > prompt.index("Workspace:")
    assert prompt.index("[Git State]") < prompt.index("System instructions:")


def test_codex_cli_prompt_git_state_between_workspace_and_system(monkeypatch):
    from core.providers.cli import _compose_prompt, CliChatRequest, CliProviderSpec
    monkeypatch.setattr(
        "core.providers.cli._collect_git_context",
        lambda ws: "[Git State]\nHEAD: 111aaaa on main"
    )
    request = CliChatRequest(
        provider_id="codex_cli",
        model="gpt4",
        system_prompt="sys",
        task_input="task",
        workspace="/workspace"
    )
    spec = CliProviderSpec(
        provider_id="codex_cli",
        default_command=("codex",),
        command_env="TEST",
        combine_system_prompt=True
    )
    prompt = _compose_prompt(request, spec, "sys prompt")
    assert "[Git State]" in prompt
    assert "[Workspace]" in prompt
    assert "[System Prompt]" in prompt
    assert prompt.index("[Git State]") > prompt.index("[Workspace]")
    assert prompt.index("[Git State]") < prompt.index("[System Prompt]")


def test_collect_git_context_returns_empty_for_non_git_dir(tmp_path, monkeypatch):
    from core.providers.cli import _collect_git_context
    monkeypatch.setattr("core.providers.cli._detect_repo_root", lambda ws: "")
    non_git_dir = tmp_path / "no_git"
    non_git_dir.mkdir()
    result = _collect_git_context(str(non_git_dir))
    assert result == ""


class TestAllowFileEdit:
    """allow_file_edit 필드: claude_cli는 bypassPermissions 제어, gemini_cli headless 플래그는 유지."""

    def _build(self, provider_id: str, allow_file_edit: bool):
        from core.providers.cli import CliChatRequest, build_cli_command
        return build_cli_command(
            CliChatRequest(
                provider_id=provider_id,
                model="test-model",
                system_prompt="sys",
                task_input="task",
                workspace="D:/workspace",
                allow_file_edit=allow_file_edit,
            )
        )

    def test_claude_allow_file_edit_true_includes_bypass_permissions(self):
        cmd = self._build("claude_cli", allow_file_edit=True)
        assert "--permission-mode" in cmd
        assert "bypassPermissions" in cmd

    def test_claude_allow_file_edit_false_excludes_bypass_permissions(self):
        # control-plane JSON 결정 호출 — 파일편집 도구 차단
        cmd = self._build("claude_cli", allow_file_edit=False)
        assert "--permission-mode" not in cmd
        assert "bypassPermissions" not in cmd

    def test_gemini_allow_file_edit_false_still_includes_headless_flags(self, monkeypatch):
        # gemini_cli의 headless 실행 플래그는 allow_file_edit=False여도 유지 (hang 방지)
        monkeypatch.setenv("AF_SANDBOX", "1")  # sandbox on — 기존 동작 유지
        cmd = self._build("gemini_cli", allow_file_edit=False)
        assert "--sandbox" in cmd
        assert "--approval-mode" in cmd
        assert "yolo" in cmd

    def test_gemini_allow_file_edit_true_includes_headless_flags(self, monkeypatch):
        monkeypatch.setenv("AF_SANDBOX", "1")  # sandbox on — 기존 동작 유지
        cmd = self._build("gemini_cli", allow_file_edit=True)
        assert "--sandbox" in cmd
        assert "--approval-mode" in cmd
        assert "yolo" in cmd


# S1: shell_error 분류 및 ok 승격 차단 테스트
class TestShellErrorClassification:
    """S1 슬라이스 — _SHELL_FAILURE_MARKERS 및 제외 튜플 신규 분기 검증."""

    def test_shell_error_classified_correctly(self, tmp_path):
        """stderr에 shell_error 시그니처 + returncode=1 + text非공백 → ok is False, reason에 shell_error 포함."""
        from core.providers.cli import CliChatRequest, execute_cli_chat

        workspace = tmp_path / "proj"
        workspace.mkdir(parents=True, exist_ok=True)

        def cli_runner(*args, **kwargs):
            return types.SimpleNamespace(
                returncode=1,
                stdout="some agent output",
                stderr="error: batch file arguments are invalid, check your invocation",
            )

        result = execute_cli_chat(
            CliChatRequest(
                provider_id="codex_cli",
                model="gpt-5",
                system_prompt="system prompt",
                task_input="execute task",
                workspace=str(workspace),
                run_id="run_shell_error",
            ),
            run_command=cli_runner,
        )

        from core.providers.cli import _classify_cli_issue
        issue = _classify_cli_issue(
            "some agent output",
            "error: batch file arguments are invalid, check your invocation",
        )
        assert issue == "shell_error"
        assert result["ok"] is False
        assert "shell_error" in result["reason"]

    def test_shell_error_no_false_promotion_regression(self, tmp_path):
        """동일 조건에서 shell_error 시그니처 제거 → ok is True (기존 codex 승격 유지)."""
        from core.providers.cli import CliChatRequest, execute_cli_chat

        workspace = tmp_path / "proj"
        workspace.mkdir(parents=True, exist_ok=True)

        def cli_runner(*args, **kwargs):
            return types.SimpleNamespace(
                returncode=1,
                stdout="some agent output",
                stderr="normal stderr without shell failure marker",
            )

        result = execute_cli_chat(
            CliChatRequest(
                provider_id="codex_cli",
                model="gpt-5",
                system_prompt="system prompt",
                task_input="execute task",
                workspace=str(workspace),
                run_id="run_no_shell_error",
            ),
            run_command=cli_runner,
        )

        assert result["ok"] is True

    def test_existing_markers_unaffected(self):
        """auth/permission/hook 기존 마커는 결과 불변."""
        from core.providers.cli import _classify_cli_issue

        assert _classify_cli_issue("", "not logged in") == "auth_required"
        assert _classify_cli_issue("", "access is denied") == "permission_denied"
        assert _classify_cli_issue("", "hook_runner.py] failed: exit 1") == "hook_failure"
        # shell_error 시그니처만 shell_error 반환
        assert _classify_cli_issue("", "batch file arguments are invalid") == "shell_error"
        # 아무 마커 없으면 빈 문자열
        assert _classify_cli_issue("", "") == ""


# 멀티OS/멀티프로바이더 — 가짜성공 승격 차단 불변식(SSOT) 검증
class TestFalseSuccessPromotionMultiOS:
    """승격 차단을 _classify_cli_issue 반환(SSOT)에 묶은 뒤의 OS/프로바이더 커버리지.

    핵심 불변식: codex_cli가 returncode!=0 + 텍스트를 내도, _classify_cli_issue가
    비공백 issue를 반환하면(어느 OS/프로바이더 시그니처든) ok로 승격되지 않는다.
    """

    @staticmethod
    def _split_runner(exec_rc, exec_stdout, exec_stderr):
        """preflight(auth status)는 깨끗이 통과시키고 본 exec만 페이로드를 반환하는 mock.

        머신에 codex 설치 여부와 무관하게 promotion 분기를 결정적으로 타게 한다
        (status 명령은 rc=0·무마커 → preflight 비치명적 통과 → 본 exec 도달)."""
        def runner(cmd, **kwargs):
            joined = " ".join(str(c) for c in cmd)
            if "status" in joined:  # codex auth_status_command=("login", "status")
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")
            return types.SimpleNamespace(
                returncode=exec_rc, stdout=exec_stdout, stderr=exec_stderr
            )
        return runner

    def _run_codex(self, tmp_path, exec_rc, exec_stdout, exec_stderr):
        from core.providers.cli import CliChatRequest, execute_cli_chat

        workspace = tmp_path / "proj"
        workspace.mkdir(parents=True, exist_ok=True)
        return execute_cli_chat(
            CliChatRequest(
                provider_id="codex_cli",
                model="gpt-5",
                system_prompt="system prompt",
                task_input="execute task",
                workspace=str(workspace),
                run_id="run_multios",
            ),
            run_command=self._split_runner(exec_rc, exec_stdout, exec_stderr),
        )

    def test_posix_sandbox_denial_classified_permission_denied(self):
        """macOS seatbelt / Linux landlock 샌드박스 거부 시그니처 → permission_denied."""
        from core.providers.cli import _classify_cli_issue

        # POSIX 샌드박스 거부는 .cmd 셔임 에러와 달리 권한 마커로 흡수된다.
        assert _classify_cli_issue("", "operation not permitted (os error 1)") == "permission_denied"

    @pytest.mark.parametrize(
        "exec_stderr",
        [
            "operation not permitted",  # POSIX 샌드박스 거부 (macOS/Linux)
            "batch file arguments are invalid",  # Windows .cmd 셔임 깨짐
            "hook_runner.py] failed: exit 1",  # hook 실패 (OS 무관)
            "not logged in",  # auth 실패 (OS 무관)
        ],
    )
    def test_any_classified_issue_blocks_false_success(self, tmp_path, exec_stderr):
        """SSOT 불변식: 비공백 issue를 내는 어떤 OS/프로바이더 시그니처든 ok 승격 차단."""
        result = self._run_codex(tmp_path, 1, "some agent output", exec_stderr)
        assert result["ok"] is False

    def test_empty_issue_still_promotes_codex(self, tmp_path):
        """대조군: 인프라 시그니처 없는 codex rc=1+text는 기존대로 승격(회귀 방지)."""
        result = self._run_codex(tmp_path, 1, "some agent output", "ordinary stderr noise")
        assert result["ok"] is True

    def test_non_codex_provider_not_promoted_on_failure(self, tmp_path):
        """멀티프로바이더: rc!=0 승격은 codex 전용. gemini_cli rc=1+text는 ok=False."""
        from core.providers.cli import CliChatRequest, execute_cli_chat

        workspace = tmp_path / "proj"
        workspace.mkdir(parents=True, exist_ok=True)

        def runner(cmd, **kwargs):
            return types.SimpleNamespace(
                returncode=1, stdout="some agent output", stderr="ordinary stderr noise"
            )

        result = execute_cli_chat(
            CliChatRequest(
                provider_id="gemini_cli",
                model="gemini-2.5-pro",
                system_prompt="system prompt",
                task_input="execute task",
                workspace=str(workspace),
                run_id="run_gemini",
            ),
            run_command=runner,
        )
        assert result["ok"] is False
