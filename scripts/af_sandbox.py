"""af sandbox on|off|status — AF + provider sandbox 일괄 토글."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_CLAUDE_SETTINGS_PATHS = [
    Path.home() / ".claude" / "settings.json",
    Path(".claude") / "settings.json",
]

_SANDBOX_OFF_BLOCK = {
    "enabled": False,
    "allowUnsandboxedCommands": True,
    "failIfUnavailable": False,
}

_SANDBOX_ON_BLOCK = {"enabled": True}


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _merge_claude_settings(sandbox_block: dict) -> None:
    """~/.claude/settings.json (+ 프로젝트 .claude/settings.json)에 sandbox 블록 merge."""
    for settings_path in _CLAUDE_SETTINGS_PATHS:
        if not settings_path.exists():
            continue
        data = _load_json(settings_path)
        existing = data.get("sandbox", {})
        if not isinstance(existing, dict):
            existing = {}
        merged = {**existing, **sandbox_block}
        data["sandbox"] = merged
        _save_json(settings_path, data)
        print(f"  claude settings 갱신: {settings_path}")


def _cmd_off() -> int:
    from core.sandbox_config import set_sandbox_enabled
    set_sandbox_enabled(False)
    _merge_claude_settings(_SANDBOX_OFF_BLOCK)
    print("[af sandbox] off — provider subprocess sandbox 비활성화됨.")
    print("  codex: --sandbox danger-full-access (격리 해제)")
    print("  gemini: --sandbox 플래그 제거 (--approval-mode yolo 유지)")
    print("  claude: settings.json sandbox.enabled=false")
    print("")
    print("[!] Claude Code를 재시작해야 세션 sandbox 설정이 적용됩니다.")
    return 0


def _cmd_on() -> int:
    from core.sandbox_config import set_sandbox_enabled
    set_sandbox_enabled(True)
    _merge_claude_settings(_SANDBOX_ON_BLOCK)
    print("[af sandbox] on — provider subprocess sandbox 활성화됨.")
    print("  codex: --sandbox workspace-write (기본)")
    print("  gemini: --sandbox --approval-mode yolo (기본)")
    print("  claude: settings.json sandbox.enabled=true")
    print("")
    print("[!] Claude Code를 재시작해야 세션 sandbox 설정이 적용됩니다.")
    return 0


def _cmd_status() -> int:
    from core.sandbox_config import sandbox_enabled, _CONFIG_PATH, _ENV_OVERRIDE
    import os
    import platform

    enabled = sandbox_enabled()
    env_val = os.getenv(_ENV_OVERRIDE, "")

    print(f"[af sandbox status]")
    print(f"  sandbox enabled : {enabled}")
    if env_val:
        print(f"  source          : env {_ENV_OVERRIDE}={env_val!r}")
    elif _CONFIG_PATH.exists():
        print(f"  source          : {_CONFIG_PATH}")
    else:
        print(f"  source          : 플랫폼 기본 ({platform.system()})")

    # provider별 예상 argv 효과
    print("")
    print("  provider별 예상 동작 (sandbox off 시):")
    print("    codex   : --sandbox danger-full-access")
    print("    gemini  : --sandbox 제거, --approval-mode yolo 유지")
    print("    claude  : settings.json sandbox 블록 참조")

    # claude settings 현황
    for sp in _CLAUDE_SETTINGS_PATHS:
        if sp.exists():
            data = _load_json(sp)
            sb = data.get("sandbox", "(없음)")
            print(f"  {sp} sandbox: {sb}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("사용법: af sandbox <on|off|status>", file=sys.stderr)
        return 1
    action = args[0].lower()
    if action == "off":
        return _cmd_off()
    if action == "on":
        return _cmd_on()
    if action == "status":
        return _cmd_status()
    print(f"알 수 없는 action: {action!r}. on|off|status 중 하나.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
