"""tests for scripts/af_provider.py — af provider status/install/auth."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _run(argv: list[str]) -> int:
    from scripts.af_provider import main
    return main(argv)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

class TestProviderStatus:
    def test_status_fast_all_installed(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=["claude_cli", "gemini_cli", "codex_cli"]):
            rc = _run(["status", "--fast"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Claude Code" in out
        assert "Gemini CLI" in out
        assert "Codex CLI" in out

    def test_status_fast_none_installed(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=[]):
            rc = _run(["status", "--fast"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "[✗]" in out  # missing marker

    def test_status_shows_install_hint_for_missing(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=["claude_cli"]):
            rc = _run(["status", "--fast"])
        out = capsys.readouterr().out
        assert "npm install" in out  # install hint for missing providers

    def test_status_no_subcmd_shows_help(self, capsys):
        rc = _run([])
        assert rc == 0


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

class TestProviderInstall:
    def test_install_skip_already_installed(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=["claude_cli", "gemini_cli", "codex_cli"]), \
             patch("core.providers.registry.invalidate_installed_cli_cache"):
            rc = _run(["install"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "이미 설치됨" in out

    def test_install_missing_provider(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=[]), \
             patch("scripts.af_provider._npm_install", return_value=0), \
             patch("core.providers.registry.invalidate_installed_cli_cache"):
            rc = _run(["install", "claude"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "설치 완료" in out or "설치 중" in out

    def test_install_npm_fail(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=[]), \
             patch("scripts.af_provider._npm_install", return_value=1), \
             patch("core.providers.registry.invalidate_installed_cli_cache"):
            rc = _run(["install", "gemini"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "실패" in out

    def test_install_unknown_provider(self, capsys):
        rc = _run(["install", "unknown_xyz"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "알 수 없는" in err

    def test_install_force_reinstall(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=["codex_cli"]), \
             patch("scripts.af_provider._npm_install", return_value=0), \
             patch("core.providers.registry.invalidate_installed_cli_cache"):
            rc = _run(["install", "codex", "--force"])
        assert rc == 0


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

class TestProviderAuth:
    def test_auth_missing_provider_skipped(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=[]):
            rc = _run(["auth", "claude"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "미설치" in out

    def test_auth_unknown_provider(self):
        rc = _run(["auth", "badname"])
        assert rc == 1

    def test_auth_runs_subprocess(self, capsys):
        with patch("core.providers.registry.detect_installed_cli_providers",
                   return_value=["claude_cli"]), \
             patch("scripts.af_provider.shutil.which", return_value="/usr/bin/claude"), \
             patch("scripts.af_provider.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            rc = _run(["auth", "claude"])
        assert rc == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "claude" in call_args[0]
        assert "auth" in call_args


# ---------------------------------------------------------------------------
# alias resolution
# ---------------------------------------------------------------------------

class TestAliasResolution:
    @pytest.mark.parametrize("alias,expected", [
        ("claude", "claude_cli"),
        ("claude_cli", "claude_cli"),
        ("gemini", "gemini_cli"),
        ("gemini_cli", "gemini_cli"),
        ("codex", "codex_cli"),
        ("codex_cli", "codex_cli"),
        ("CLAUDE", "claude_cli"),
        ("Gemini", "gemini_cli"),
    ])
    def test_resolve_alias(self, alias: str, expected: str):
        from scripts.af_provider import _resolve_provider
        assert _resolve_provider(alias) == expected

    def test_resolve_unknown_returns_none(self):
        from scripts.af_provider import _resolve_provider
        assert _resolve_provider("gpt4") is None
