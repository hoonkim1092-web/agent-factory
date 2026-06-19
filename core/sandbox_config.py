"""sandbox_config — AF sandbox 활성 여부 SSOT.

우선순위: env AF_SANDBOX > ~/.af/sandbox.json > 플랫폼 기본(Windows=False, 그 외=True).
"""
import json
import os
import platform
from pathlib import Path

_ENV_OVERRIDE = "AF_SANDBOX"
_CONFIG_PATH = Path.home() / ".af" / "sandbox.json"


def sandbox_enabled() -> bool:
    """sandbox 활성 여부 SSOT."""
    env = os.getenv(_ENV_OVERRIDE, "").strip().lower()
    if env in ("0", "off", "false", "no"):
        return False
    if env in ("1", "on", "true", "yes"):
        return True
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "enabled" in data:
            return bool(data["enabled"])
    except Exception:
        pass
    return platform.system() != "Windows"


def set_sandbox_enabled(enabled: bool) -> None:
    """~/.af/sandbox.json에 write-through."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(
        json.dumps({"enabled": bool(enabled)}, ensure_ascii=False),
        encoding="utf-8",
    )
