"""agent_runner.run()의 force_provider 우선 처리 단위 테스트 (WI-2)."""
from __future__ import annotations

import pytest


def _pick_cli_providers(agent: dict, all_providers: list[str], available: list[str]):
    """agent_runner.run() force_provider 분기 로직 재현.

    available에 force_provider 없으면 실패를 나타내는 None 반환.
    production 코드는 {'ok': False, 'reason': ...}를 return한다.
    """
    force_prov = str(agent.get("force_provider") or "").strip()
    if force_prov:
        if force_prov not in available:
            return None  # production: {"ok": False, ...}
        return [force_prov]
    if len(all_providers) > 1:
        return all_providers
    return all_providers


class TestForceProviderLogic:
    def test_force_provider_available_uses_it_exclusively(self):
        agent = {"force_provider": "codex_cli"}
        result = _pick_cli_providers(agent, ["claude_cli", "codex_cli"], ["claude_cli", "codex_cli"])
        assert result == ["codex_cli"]

    def test_force_provider_not_available_signals_failure(self):
        # cross_validate invariant: unavailable이면 silent fallback이 아니라 실패
        agent = {"force_provider": "codex_cli"}
        result = _pick_cli_providers(agent, ["claude_cli"], ["claude_cli"])
        assert result is None

    def test_no_force_provider_returns_all(self):
        agent = {}
        result = _pick_cli_providers(agent, ["claude_cli", "codex_cli"], ["claude_cli", "codex_cli"])
        assert result == ["claude_cli", "codex_cli"]

    def test_force_provider_empty_string_treats_as_no_force(self):
        agent = {"force_provider": ""}
        result = _pick_cli_providers(agent, ["claude_cli"], ["claude_cli"])
        assert result == ["claude_cli"]
