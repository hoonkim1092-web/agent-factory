"""
core/skill_pack_bootstrapper.py
================================
외부 CLI 플러그인 팩 감지 전용 부트스트래퍼.

설치는 하지 않고 탐지만 수행한다 (Q8 결정: (a) 탐지만).
설치가 필요한 경우 호출자가 사용자에게 안내하도록 설계되어 있다.

지원 플러그인:
  - claude-code  : Anthropic Claude Code CLI (claude)
  - codex        : OpenAI Codex CLI (codex)
  - gemini       : Google Gemini CLI (gemini)
"""
from __future__ import annotations

import shutil

# 플러그인 ID → 탐지할 CLI 명령어 후보 목록
_PLUGIN_CLI_MAP: dict[str, list[str]] = {
    "claude-code": ["claude"],
    "codex": ["codex"],
    "gemini": ["gemini"],
}


class SkillPackBootstrapper:
    """외부 플러그인 설치 여부를 탐지한다."""

    def check_installed(self) -> dict[str, bool]:
        """각 플러그인의 CLI 바이너리 존재 여부를 반환한다.

        Returns
        -------
        dict[str, bool]
            플러그인 ID → 설치 여부. PATH에 CLI가 있으면 True.
        """
        return {
            plugin_id: any(shutil.which(cmd) is not None for cmd in cmds)
            for plugin_id, cmds in _PLUGIN_CLI_MAP.items()
        }

    def missing(self) -> list[str]:
        """미설치 플러그인 ID 목록을 반환한다."""
        return [pid for pid, ok in self.check_installed().items() if not ok]

    def installed(self) -> list[str]:
        """설치된 플러그인 ID 목록을 반환한다."""
        return [pid for pid, ok in self.check_installed().items() if ok]
