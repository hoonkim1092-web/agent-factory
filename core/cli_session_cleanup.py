"""CLI session 파일의 30일 TTL 정리.

generate_work_items() 진입 시 1회 호출 (idempotent). 실패해도 main flow 영향 없음.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from core.continuity.runtime_paths import workspace_runtime_dir

_LOGGER = logging.getLogger(__name__)


def cleanup_stale_sessions(workspace: str, days: int = 30) -> int:
    """workspace의 .af_runtime/cli_sessions/ 하위에서 30일 초과 파일 삭제.

    삭제 대상:
      - {provider}_{slug}.json
      - {provider}_{slug}_events.jsonl
      - {provider}_{slug}_gemini_defaults.json
      - {provider}_{slug}_destructive_guard.toml
      - {provider}_{slug}_shell_guard/ (디렉토리)

    Returns:
        삭제된 파일/디렉토리 수 (0 if no-op).
    """
    cutoff = time.time() - days * 86400
    try:
        runtime_root = workspace_runtime_dir(workspace) / "cli_sessions"
    except Exception as exc:
        _LOGGER.warning("cleanup_stale_sessions: workspace_runtime_dir 실패: %s", exc)
        return 0

    if not runtime_root.exists():
        return 0

    deleted = 0
    for entry in runtime_root.iterdir():
        try:
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                entry.unlink()
                deleted += 1
            elif entry.is_dir() and entry.stat().st_mtime < cutoff:
                import shutil
                shutil.rmtree(entry, ignore_errors=True)
                deleted += 1
        except OSError as exc:
            _LOGGER.debug("cleanup skip %s: %s", entry, exc)
    return deleted
