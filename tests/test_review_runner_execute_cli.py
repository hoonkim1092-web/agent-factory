"""
tests/test_review_runner_execute_cli.py
=========================================
WI-4: _run_provider → execute_cli_chat 위임 검증.

행위 기반 계약:
  - CliChatRequest가 올바른 provider_id·task_input·workspace·timeout_sec·allow_file_edit로 빌드됨
  - ok=True 시 result["text"] 반환
  - ok=False 시 "(provider error: <reason>)" 반환
  - text 빈 문자열 시 "(empty response)" 반환
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.review_runner import _run_provider, _PROVIDER_ID_MAP, REVIEW_TIMEOUT


def _make_ok_result(text: str) -> dict:
    return {"ok": True, "text": text, "reason": "claude_cli", "provider_id": "claude_cli"}


def _make_fail_result(reason: str) -> dict:
    return {"ok": False, "text": "", "reason": reason, "provider_id": "claude_cli"}


class TestRunProviderExecuteCliChat:
    """_run_provider가 execute_cli_chat을 올바르게 위임하는지 검증."""

    def test_success_returns_text(self):
        """ok=True이면 result["text"]를 그대로 반환."""
        with patch("core.providers.cli.execute_cli_chat", return_value=_make_ok_result("review output")) as mock_exec:
            result = _run_provider("claude", "my prompt", "/workspace")
        assert result == "review output"
        mock_exec.assert_called_once()

    def test_failure_returns_error_string(self):
        """ok=False이면 (provider error: <reason>) 문자열 반환."""
        with patch("core.providers.cli.execute_cli_chat", return_value=_make_fail_result("cli_timeout")):
            result = _run_provider("claude", "prompt", "/ws")
        assert result == "(provider error: cli_timeout)"

    def test_empty_text_returns_placeholder(self):
        """ok=True인데 text가 빈 문자열이면 (empty response) 반환."""
        with patch("core.providers.cli.execute_cli_chat", return_value={"ok": True, "text": "", "reason": "ok"}):
            result = _run_provider("claude", "p", ".")
        assert result == "(empty response)"

    def test_provider_id_mapping_claude(self):
        """'claude' → CliChatRequest.provider_id='claude_cli'."""
        captured = {}

        def fake_exec(req, **_):
            captured["req"] = req
            return _make_ok_result("ok")

        with patch("core.providers.cli.execute_cli_chat", side_effect=fake_exec):
            _run_provider("claude", "p", "/ws")

        assert captured["req"].provider_id == "claude_cli"

    def test_provider_id_mapping_codex(self):
        """'codex' → CliChatRequest.provider_id='codex_cli'."""
        captured = {}

        def fake_exec(req, **_):
            captured["req"] = req
            return _make_ok_result("ok")

        with patch("core.providers.cli.execute_cli_chat", side_effect=fake_exec):
            _run_provider("codex", "p", "/ws")

        assert captured["req"].provider_id == "codex_cli"

    def test_provider_id_mapping_gemini(self):
        """'gemini' → CliChatRequest.provider_id='gemini_cli'."""
        captured = {}

        def fake_exec(req, **_):
            captured["req"] = req
            return _make_ok_result("ok")

        with patch("core.providers.cli.execute_cli_chat", side_effect=fake_exec):
            _run_provider("gemini", "p", "/ws")

        assert captured["req"].provider_id == "gemini_cli"

    def test_request_fields(self):
        """task_input, workspace, timeout_sec, allow_file_edit 필드 계약 검증."""
        captured = {}

        def fake_exec(req, **_):
            captured["req"] = req
            return _make_ok_result("text")

        with patch("core.providers.cli.execute_cli_chat", side_effect=fake_exec):
            _run_provider("claude", "the prompt", "/my/workspace")

        req = captured["req"]
        assert req.task_input == "the prompt"
        assert req.workspace == "/my/workspace"
        assert req.timeout_sec == REVIEW_TIMEOUT
        assert req.allow_file_edit is False

    def test_unknown_reason_fallback(self):
        """reason 필드 없는 실패 결과 → '(provider error: unknown_error)'."""
        with patch("core.providers.cli.execute_cli_chat", return_value={"ok": False, "text": ""}):
            result = _run_provider("claude", "p", ".")
        assert result == "(provider error: unknown_error)"


    def test_ok_true_with_rate_limit_text_calls_mark(self, monkeypatch):
        """ok=True 응답에 rate limit 텍스트가 있어도 mark_rate_limited 호출 (codex ok=True 위장 경로)."""
        calls: list[tuple] = []
        monkeypatch.setattr("core.provider_detect.mark_rate_limited", lambda p, u: calls.append((p, u)))

        with patch(
            "core.providers.cli.execute_cli_chat",
            return_value={"ok": True, "text": "usage limit exceeded. Please try again later.", "reason": "ok"},
        ):
            result = _run_provider("codex", "prompt", ".")

        assert len(calls) == 1
        pid, _ = calls[0]
        assert pid == "codex_cli"
        assert "usage limit" in result  # 텍스트는 그대로 반환


class TestProviderIdMap:
    """_PROVIDER_ID_MAP 상수 계약."""

    def test_all_short_names_covered(self):
        assert _PROVIDER_ID_MAP["claude"] == "claude_cli"
        assert _PROVIDER_ID_MAP["codex"] == "codex_cli"
        assert _PROVIDER_ID_MAP["gemini"] == "gemini_cli"
