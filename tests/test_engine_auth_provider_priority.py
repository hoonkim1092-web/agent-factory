"""Tests for R4 fix: provider priority sorting by credential availability."""
import pytest


# ──────────────────────────────────────────────
# _has_required_credentials
# ──────────────────────────────────────────────

def test_claude_cli_always_available(monkeypatch):
    """claude_cli is not in _PROVIDER_KEY_ENVS → always True."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from core.engine_auth import _has_required_credentials
    assert _has_required_credentials("claude_cli") is True


def test_gemini_no_keys_not_available(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from core.engine_auth import _has_required_credentials
    assert _has_required_credentials("gemini_cli") is False


def test_gemini_with_google_api_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from core.engine_auth import _has_required_credentials
    assert _has_required_credentials("gemini_cli") is True


def test_gemini_with_gemini_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from core.engine_auth import _has_required_credentials
    assert _has_required_credentials("gemini_cli") is True


def test_codex_no_key_not_available(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from core.engine_auth import _has_required_credentials
    assert _has_required_credentials("codex_cli") is False


def test_codex_with_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from core.engine_auth import _has_required_credentials
    assert _has_required_credentials("codex_cli") is True


# ──────────────────────────────────────────────
# auto_configure_cli_provider — sorting
# ──────────────────────────────────────────────

def _setup_auto_configure(monkeypatch, installed, env_overrides=None):
    """Patch registry stubs and env vars; return captured configure call."""
    monkeypatch.delenv("AGENT_CHAT_PROVIDER", raising=False)
    for k, v in (env_overrides or {}).items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)

    import core.providers.registry as _reg
    monkeypatch.setattr(_reg, "_runtime_providers", [])

    captured = {}

    monkeypatch.setattr("core.engine_auth._registry_detect_installed", lambda: list(installed))
    monkeypatch.setattr("core.engine_auth._registry_configure_providers",
                        lambda providers: captured.update({"providers": list(providers)}))
    monkeypatch.setattr("core.engine_auth._registry_get_active_provider_setting", lambda: "")

    return captured


def test_no_google_key_claude_preferred(monkeypatch):
    """gemini+claude installed, no GOOGLE_API_KEY → claude_cli is primary."""
    captured = _setup_auto_configure(
        monkeypatch,
        installed=["gemini_cli", "claude_cli"],
        env_overrides={"GOOGLE_API_KEY": None, "GEMINI_API_KEY": None},
    )
    from core.engine_auth import auto_configure_cli_provider
    result = auto_configure_cli_provider()
    assert result == "claude_cli", f"Expected claude_cli, got {result}"
    assert captured["providers"][0] == "claude_cli"
    assert captured["providers"][1] == "gemini_cli"


def test_with_google_key_gemini_preferred(monkeypatch):
    """gemini+claude installed, GOOGLE_API_KEY set → gemini_cli is primary."""
    captured = _setup_auto_configure(
        monkeypatch,
        installed=["gemini_cli", "claude_cli"],
        env_overrides={"GOOGLE_API_KEY": "my-key"},
    )
    from core.engine_auth import auto_configure_cli_provider
    result = auto_configure_cli_provider()
    assert result == "gemini_cli", f"Expected gemini_cli, got {result}"
    assert captured["providers"][0] == "gemini_cli"


def test_only_gemini_no_key_still_returns_gemini(monkeypatch):
    """If only gemini is installed (no key), it's still selected — no crash."""
    captured = _setup_auto_configure(
        monkeypatch,
        installed=["gemini_cli"],
        env_overrides={"GOOGLE_API_KEY": None, "GEMINI_API_KEY": None},
    )
    from core.engine_auth import auto_configure_cli_provider
    result = auto_configure_cli_provider()
    assert result == "gemini_cli"


def test_all_three_no_keys_claude_first(monkeypatch):
    """gemini+claude+codex installed, no API keys → claude_cli first (has_creds=True)."""
    captured = _setup_auto_configure(
        monkeypatch,
        installed=["gemini_cli", "claude_cli", "codex_cli"],
        env_overrides={"GOOGLE_API_KEY": None, "GEMINI_API_KEY": None, "OPENAI_API_KEY": None},
    )
    from core.engine_auth import auto_configure_cli_provider
    result = auto_configure_cli_provider()
    assert result == "claude_cli"
    assert captured["providers"][0] == "claude_cli"
    # gemini and codex both lack keys → sorted by _PRIORITY: gemini before codex
    assert captured["providers"][1] == "gemini_cli"
    assert captured["providers"][2] == "codex_cli"
