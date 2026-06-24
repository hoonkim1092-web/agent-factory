"""af ponytail full|ultra|lite|off|status - Ponytail 플러그인 defaultMode 설정."""
from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

_VALID_MODES = ["full", "ultra", "lite", "off"]

_MODE_DESC: dict[str, str] = {
    "full": "요청 분석 + 기다리는 동안 동작 수행 (기본값, 의무사항)",
    "ultra": "필요한 전체 분석 + 결과 우선 (더 큰 채팅 메세지)",
    "lite": "요청 분석 + 짧은 동작, 사용자가 원함",
    "off": "Ponytail 비활성화",
}

_PROVIDER_INSTALL_NOTE = (
    "  [!] config가 효력을 발휘하려면 해당 프로바이더에 Ponytail이 설치되어 있어야 합니다.\n"
    "      Claude Code, Codex, Gemini, Cursor 등 사용하는 프로바이더마다 설치를 확인하세요."
)


def _get_config_path() -> Path:
    """플러그인 Ponytail config.json 경로."""
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "ponytail" / "config.json"
    elif system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "ponytail" / "config.json"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        return Path(xdg) / "ponytail" / "config.json"


def _load_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _cmd_set(mode: str) -> int:
    config_path = _get_config_path()
    data = _load_config(config_path)
    data["defaultMode"] = mode
    _save_config(config_path, data)
    desc = _MODE_DESC.get(mode, "")
    print(f"[af ponytail] defaultMode={mode} 설정됨. ({desc})")
    print(f"  config: {config_path}")
    print(_PROVIDER_INSTALL_NOTE)
    return 0


def _cmd_status() -> int:
    config_path = _get_config_path()
    print("[af ponytail status]")
    print(f"  config    : {config_path}")
    if not config_path.exists():
        print(" (없음 - Ponytail 미설치 또는 미구성)")
        print(_PROVIDER_INSTALL_NOTE)
        return 0
    data = _load_config(config_path)
    mode = data.get("defaultMode", "")
    desc = _MODE_DESC.get(mode, "(알수없음)")
    print(f"  defaultMode: {mode}")
    print(f"  ({desc})")
    print(_PROVIDER_INSTALL_NOTE)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        modes = "|".join(_VALID_MODES)
        print(f"사용: af ponytail <{modes}|status>", file=sys.stderr)
        return 1
    action = args[0].lower()
    if action == "status":
        return _cmd_status()
    if action not in _VALID_MODES:
        modes = "|".join(_VALID_MODES)
        print(f"알 수 없는 action: {action}. {modes}|status 중 하나.", file=sys.stderr)
        return 1
    return _cmd_set(action)


if __name__ == "__main__":
    sys.exit(main())
