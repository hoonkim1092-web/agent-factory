"""tests/test_review_runner_auth_expired.py

AUTH_EXPIRED provider에 대한 1회 재인증 안내 + 스킵 옵션 + 토큰낭비 차단 검증.

원천 결함(fix 전):
  - DocumentReviewSession.run_review()가 AUTH_EXPIRED 1개라도 있으면 무조건 BLOCK.
  - BLOCK 메시지에 `<cli> login`만 있고 graceful skip 탈출구(AF_SKIP_PROVIDER) 안내 부재.
  - 사용자가 스킵을 원해도 정확한 명령을 모르므로 매 라운드 동일 BLOCK 반복 → 토큰/시간 낭비.

fix 후:
  - build_auth_expired_notice()가 provider별 정확한 재인증 명령 + AF_SKIP_PROVIDER 스킵 명령을 안내.
  - AF_SKIP_PROVIDER 설정 시 provider_detect가 마스킹 → blocked에서 빠짐 → 더 이상 BLOCK 안 함(스킵 통과).
"""
from __future__ import annotations

from unittest.mock import patch

import core.provider_detect as pd
from core.provider_detect import ProviderState, detect_provider_states
from core.review_runner import (
    REAUTH_COMMANDS,
    SKIP_PROVIDER_ENV,
    build_auth_expired_notice,
    detect_blocked_providers,
)


# ──────────────────────────────────────────
# build_auth_expired_notice — 안내 메시지 구성
# ──────────────────────────────────────────

def test_notice_includes_per_provider_reauth_command():
    """각 만료 provider에 대해 정확한 재인증 명령이 포함된다."""
    notice = build_auth_expired_notice(["codex", "gemini"])
    assert REAUTH_COMMANDS["codex"] in notice
    assert REAUTH_COMMANDS["gemini"] in notice


def test_notice_includes_skip_escape_hatch():
    """스킵 탈출구(AF_SKIP_PROVIDER) 명령이 정확한 provider id와 함께 안내된다."""
    notice = build_auth_expired_notice(["codex"])
    assert SKIP_PROVIDER_ENV in notice
    # 사용자가 그대로 복사할 수 있는 정확한 스킵 명령 — canonical id 사용
    assert f"{SKIP_PROVIDER_ENV}=codex_cli" in notice


def test_notice_multiple_providers_comma_joined_skip():
    """여러 provider 만료 시 스킵 명령이 콤마로 결합된 canonical id를 안내한다."""
    notice = build_auth_expired_notice(["codex", "gemini"])
    assert f"{SKIP_PROVIDER_ENV}=codex_cli,gemini_cli" in notice


def test_notice_empty_returns_empty():
    """만료 provider 0개면 빈 문자열."""
    assert build_auth_expired_notice([]) == ""


def test_reauth_commands_cover_all_known_providers():
    """SSOT: 알려진 모든 provider에 재인증 명령이 정의돼 있다."""
    for p in ("claude", "codex", "gemini"):
        assert p in REAUTH_COMMANDS
        assert REAUTH_COMMANDS[p].strip()


# ──────────────────────────────────────────
# graceful skip — AF_SKIP_PROVIDER 설정 시 토큰낭비 차단
# ──────────────────────────────────────────

def _mock_installed(monkeypatch, providers):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: list(providers))


def _fake_auth_expired_run(cmd, **kwargs):
    """모든 ping을 auth 실패(exit 1)로 처리."""
    from unittest.mock import MagicMock
    m = MagicMock()
    m.returncode = 1
    m.stderr = "Error: not authenticated. login required."
    return m


def test_blocked_provider_detected_before_skip(monkeypatch, tmp_path):
    """fix 전 동작 재현: 스킵 미설정이면 AUTH_EXPIRED provider가 blocked로 잡힌다."""
    monkeypatch.setenv("AF_HOME", str(tmp_path / ".af"))
    monkeypatch.delenv("AF_SKIP_PROVIDER", raising=False)
    _mock_installed(monkeypatch, ["codex_cli"])

    with patch("subprocess.run", side_effect=_fake_auth_expired_run):
        blocked = detect_blocked_providers()

    assert "codex" in blocked


def test_skip_provider_removes_from_blocked_no_reping(monkeypatch, tmp_path):
    """fix 검증: AF_SKIP_PROVIDER 설정 시 blocked에서 빠지고 ping subprocess가 호출되지 않는다.

    이것이 '재시도 토큰/시간 낭비 차단'의 핵심 — 만료 provider는 probe 자체를 건너뛴다.
    """
    monkeypatch.setenv("AF_HOME", str(tmp_path / ".af2"))
    monkeypatch.setenv("AF_SKIP_PROVIDER", "codex_cli")
    _mock_installed(monkeypatch, ["codex_cli"])

    with patch("subprocess.run", side_effect=_fake_auth_expired_run) as mock_run:
        blocked = detect_blocked_providers()

    assert "codex" not in blocked
    # skip provider는 probe(subprocess ping)를 아예 호출하지 않아야 함 → 30s timeout 낭비 차단
    mock_run.assert_not_called()


def test_skipped_provider_masked_as_not_installed(monkeypatch, tmp_path):
    """AF_SKIP_PROVIDER provider는 NOT_INSTALLED로 마스킹된다 (provider_detect SSOT)."""
    monkeypatch.setenv("AF_HOME", str(tmp_path / ".af3"))
    monkeypatch.setenv("AF_SKIP_PROVIDER", "codex_cli")
    _mock_installed(monkeypatch, ["codex_cli"])

    with patch("subprocess.run", side_effect=_fake_auth_expired_run):
        states = detect_provider_states(providers=["codex_cli"], use_cache=False)

    assert states["codex_cli"].state == ProviderState.NOT_INSTALLED
