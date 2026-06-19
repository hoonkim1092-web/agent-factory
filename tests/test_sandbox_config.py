"""INV-S1~S7: sandbox_config + cli._apply_sandbox_mode + af_sandbox 통합 테스트."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_request(provider_id: str, allow_file_edit: bool = True):
    """CliChatRequest 최소 픽스처."""
    from core.providers.cli import CliChatRequest
    return CliChatRequest(
        provider_id=provider_id,
        model="",
        system_prompt="",
        task_input="test",
        workspace=".",
        allow_file_edit=allow_file_edit,
    )


def _cmd(provider_id: str, sandbox: bool, **kw) -> list[str]:
    """sandbox on/off 환경에서 build_cli_command 호출."""
    from core.providers.cli import build_cli_command
    env_val = "1" if sandbox else "0"
    with patch.dict(os.environ, {"AF_SANDBOX": env_val}):
        return build_cli_command(_make_request(provider_id, **kw))


# ===========================================================================
# INV-S1: 플랫폼 기본 — env·config 부재 시 Windows=off, 그 외=on
# ===========================================================================

class TestSandboxDefault:
    def test_default_windows_off(self, tmp_path, monkeypatch):
        """INV-S1: Windows 플랫폼 기본 → False."""
        monkeypatch.delenv("AF_SANDBOX", raising=False)
        with patch("core.sandbox_config._CONFIG_PATH", tmp_path / "no_file.json"), \
             patch("core.sandbox_config.platform") as mock_plat:
            mock_plat.system.return_value = "Windows"
            from core.sandbox_config import sandbox_enabled
            assert sandbox_enabled() is False

    def test_default_posix_on(self, tmp_path, monkeypatch):
        """INV-S1: 비-Windows 플랫폼 기본 → True."""
        monkeypatch.delenv("AF_SANDBOX", raising=False)
        with patch("core.sandbox_config._CONFIG_PATH", tmp_path / "no_file.json"), \
             patch("core.sandbox_config.platform") as mock_plat:
            mock_plat.system.return_value = "Linux"
            from core.sandbox_config import sandbox_enabled
            assert sandbox_enabled() is True


# ===========================================================================
# INV-S2: 우선순위 env > config > 플랫폼 기본
# ===========================================================================

class TestSandboxPrecedence:
    def test_env_overrides_config(self, tmp_path, monkeypatch):
        """INV-S2: env AF_SANDBOX=0이면 config True여도 False."""
        config = tmp_path / "sandbox.json"
        config.write_text(json.dumps({"enabled": True}), encoding="utf-8")
        monkeypatch.setenv("AF_SANDBOX", "0")
        with patch("core.sandbox_config._CONFIG_PATH", config), \
             patch("core.sandbox_config.platform") as mock_plat:
            mock_plat.system.return_value = "Linux"
            from core.sandbox_config import sandbox_enabled
            assert sandbox_enabled() is False

    def test_config_overrides_platform(self, tmp_path, monkeypatch):
        """INV-S2: config False면 Linux 기본 True여도 False."""
        config = tmp_path / "sandbox.json"
        config.write_text(json.dumps({"enabled": False}), encoding="utf-8")
        monkeypatch.delenv("AF_SANDBOX", raising=False)
        with patch("core.sandbox_config._CONFIG_PATH", config), \
             patch("core.sandbox_config.platform") as mock_plat:
            mock_plat.system.return_value = "Linux"
            from core.sandbox_config import sandbox_enabled
            assert sandbox_enabled() is False

    def test_env_on_values(self, tmp_path, monkeypatch):
        """INV-S2: env 'true'/'yes'/'1'/'on' 모두 True."""
        config = tmp_path / "no.json"
        for val in ("true", "yes", "1", "on"):
            monkeypatch.setenv("AF_SANDBOX", val)
            with patch("core.sandbox_config._CONFIG_PATH", config), \
                 patch("core.sandbox_config.platform") as mock_plat:
                mock_plat.system.return_value = "Windows"
                from core.sandbox_config import sandbox_enabled
                assert sandbox_enabled() is True, f"expected True for env={val!r}"

    def test_env_off_values(self, tmp_path, monkeypatch):
        """INV-S2: env 'false'/'no'/'0'/'off' 모두 False."""
        config = tmp_path / "no.json"
        for val in ("false", "no", "0", "off"):
            monkeypatch.setenv("AF_SANDBOX", val)
            with patch("core.sandbox_config._CONFIG_PATH", config), \
                 patch("core.sandbox_config.platform") as mock_plat:
                mock_plat.system.return_value = "Linux"
                from core.sandbox_config import sandbox_enabled
                assert sandbox_enabled() is False, f"expected False for env={val!r}"


# ===========================================================================
# INV-S3: sandbox off → codex danger-full-access, gemini --sandbox 제거
# ===========================================================================

class TestSandboxOffArgv:
    def test_codex_sandbox_off_argv(self):
        """INV-S3: codex sandbox off → --sandbox danger-full-access."""
        argv = _cmd("codex_cli", sandbox=False)
        assert "--sandbox" in argv
        idx = argv.index("--sandbox")
        assert argv[idx + 1] == "danger-full-access", f"got: {argv}"

    def test_gemini_sandbox_off_argv(self):
        """INV-S3: gemini sandbox off → --sandbox 부재."""
        argv = _cmd("gemini_cli", sandbox=False)
        assert "--sandbox" not in argv, f"--sandbox still present: {argv}"


# ===========================================================================
# INV-S4: sandbox on → argv 그대로(회귀 0)
# ===========================================================================

class TestSandboxOnArgvUnchanged:
    def test_sandbox_on_argv_unchanged_codex(self):
        """INV-S4: codex sandbox on → workspace-write 유지."""
        argv = _cmd("codex_cli", sandbox=True)
        assert "--sandbox" in argv
        idx = argv.index("--sandbox")
        assert argv[idx + 1] == "workspace-write", f"got: {argv}"

    def test_sandbox_on_argv_unchanged_gemini(self):
        """INV-S4: gemini sandbox on → --sandbox 유지."""
        argv = _cmd("gemini_cli", sandbox=True)
        assert "--sandbox" in argv, f"--sandbox missing: {argv}"


# ===========================================================================
# INV-S5: 배포 동등성 — _apply_sandbox_mode가 build_cli_command 최종 return 직전 배선
# ===========================================================================

class TestDeployParity:
    def test_build_cli_command_applies_sandbox_mode(self):
        """INV-S5: build_cli_command 경유 시 sandbox off가 codex argv에 반영됨."""
        argv = _cmd("codex_cli", sandbox=False)
        idx = argv.index("--sandbox")
        assert argv[idx + 1] == "danger-full-access"

    def test_gemini_sandbox_stripped_via_build_cli_command(self):
        """INV-S5: build_cli_command 경유 시 sandbox off가 gemini argv에 반영됨."""
        argv = _cmd("gemini_cli", sandbox=False)
        assert "--sandbox" not in argv


# ===========================================================================
# INV-S6: af sandbox off → ~/.af/sandbox.json + claude settings 기록
# ===========================================================================

class TestAfSandboxOffWritesBoth:
    def test_af_sandbox_off_writes_both(self, tmp_path, monkeypatch):
        """INV-S6: off 명령 시 SSOT + claude settings 둘 다 기록."""
        config = tmp_path / "sandbox.json"
        claude_settings = tmp_path / "settings.json"
        claude_settings.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

        with patch("core.sandbox_config._CONFIG_PATH", config), \
             patch("scripts.af_sandbox._CLAUDE_SETTINGS_PATHS", [claude_settings]):
            from scripts.af_sandbox import main
            ret = main(["off"])

        assert ret == 0
        assert config.exists()
        ssot = json.loads(config.read_text(encoding="utf-8"))
        assert ssot["enabled"] is False

        settings_data = json.loads(claude_settings.read_text(encoding="utf-8"))
        assert settings_data["sandbox"]["enabled"] is False
        assert settings_data["sandbox"]["allowUnsandboxedCommands"] is True

    def test_claude_settings_merge_preserves(self, tmp_path, monkeypatch):
        """INV-S6: claude settings merge 시 기존 키 보존."""
        config = tmp_path / "sandbox.json"
        claude_settings = tmp_path / "settings.json"
        claude_settings.write_text(
            json.dumps({"theme": "dark", "sandbox": {"customKey": "preserved"}}),
            encoding="utf-8",
        )

        with patch("core.sandbox_config._CONFIG_PATH", config), \
             patch("scripts.af_sandbox._CLAUDE_SETTINGS_PATHS", [claude_settings]):
            from scripts.af_sandbox import main
            main(["off"])

        settings_data = json.loads(claude_settings.read_text(encoding="utf-8"))
        assert settings_data["sandbox"]["customKey"] == "preserved"
        assert settings_data["sandbox"]["enabled"] is False
        assert settings_data["theme"] == "dark"


# ===========================================================================
# INV-S7: gemini hang 방지 — sandbox off여도 --approval-mode yolo 보존
# ===========================================================================

class TestGeminiYoloPreserved:
    def test_gemini_yolo_preserved_when_sandbox_off(self):
        """INV-S7: sandbox off여도 gemini argv에 --approval-mode yolo 유지."""
        argv = _cmd("gemini_cli", sandbox=False)
        assert "--approval-mode" in argv, f"--approval-mode missing: {argv}"
        idx = argv.index("--approval-mode")
        assert argv[idx + 1] == "yolo", f"got: {argv[idx + 1]}"
        assert "--sandbox" not in argv


# ===========================================================================
# set_sandbox_enabled round-trip
# ===========================================================================

class TestSetSandboxEnabled:
    def test_roundtrip_off_on(self, tmp_path, monkeypatch):
        """set_sandbox_enabled → sandbox_enabled round-trip."""
        config = tmp_path / "sandbox.json"
        monkeypatch.delenv("AF_SANDBOX", raising=False)
        with patch("core.sandbox_config._CONFIG_PATH", config), \
             patch("core.sandbox_config.platform") as mock_plat:
            mock_plat.system.return_value = "Linux"
            from core.sandbox_config import set_sandbox_enabled, sandbox_enabled
            set_sandbox_enabled(False)
            assert sandbox_enabled() is False
            set_sandbox_enabled(True)
            assert sandbox_enabled() is True
