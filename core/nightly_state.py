"""야간 자율 파이프라인 상태 관리.

`.af/state_snapshot.json` 을 단일 진실원천(single source of truth)으로 사용.
모든 상태는 이 파일 하나에 atomic write된다.
파생 파일(board_state, watchdog_state, budget_state 등)은 이 파일에서 렌더링된다.
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.watchdog import WatchdogState


_AF_DIR = ".af"
_SNAPSHOT_FILE = "state_snapshot.json"
_LOCK_FILE = "nightly.lock"
_ALERT_FLAG = "alert.flag"
_SUMMARY_FILE = "nightly_summary.md"
_LINEAGE_FILE = "lineage_ledger.json"


def af_dir(workspace: str | Path | None = None) -> Path:
    base = Path(workspace) if workspace else Path.cwd()
    return base / _AF_DIR


def snapshot_path(workspace: str | Path | None = None) -> Path:
    return af_dir(workspace) / _SNAPSHOT_FILE


def lock_path(workspace: str | Path | None = None) -> Path:
    return af_dir(workspace) / _LOCK_FILE


def alert_flag_path(workspace: str | Path | None = None) -> Path:
    return af_dir(workspace) / _ALERT_FLAG


def summary_path(workspace: str | Path | None = None) -> Path:
    return af_dir(workspace) / _SUMMARY_FILE


@dataclasses.dataclass
class BudgetState:
    max_tokens: int = 0        # 0 = unlimited
    consumed_tokens: int = 0
    tick_count: int = 0
    start_tick_id: Optional[str] = None

    def tokens_remaining(self) -> int:
        if self.max_tokens <= 0:
            return 999_999_999
        return max(0, self.max_tokens - self.consumed_tokens)

    def is_exhausted(self) -> bool:
        return self.max_tokens > 0 and self.consumed_tokens >= self.max_tokens

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BudgetState":
        return cls(
            max_tokens=int(data.get("max_tokens", 0)),
            consumed_tokens=int(data.get("consumed_tokens", 0)),
            tick_count=int(data.get("tick_count", 0)),
            start_tick_id=data.get("start_tick_id"),
        )


@dataclasses.dataclass
class NightlyState:
    """야간 자율 파이프라인의 전체 상태."""

    nightly_autonomy_enabled: bool = False
    active_project: Optional[str] = None          # project_id
    active_workspace: Optional[str] = None        # absolute path
    watchdog: WatchdogState = dataclasses.field(default_factory=WatchdogState)
    budget: BudgetState = dataclasses.field(default_factory=BudgetState)
    active_assignments: dict[str, Any] = dataclasses.field(default_factory=dict)
    task_retry_count: dict[str, int] = dataclasses.field(default_factory=dict)
    consecutive_tick_failures: int = 0
    last_tick_id: Optional[str] = None
    last_tick_at: Optional[str] = None
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "nightly_autonomy_enabled": self.nightly_autonomy_enabled,
            "active_project": self.active_project,
            "active_workspace": self.active_workspace,
            "watchdog": self.watchdog.to_dict(),
            "budget": self.budget.to_dict(),
            "active_assignments": self.active_assignments,
            "task_retry_count": self.task_retry_count,
            "consecutive_tick_failures": self.consecutive_tick_failures,
            "last_tick_id": self.last_tick_id,
            "last_tick_at": self.last_tick_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NightlyState":
        raw_retry = data.get("task_retry_count") or {}
        safe_retry: dict[str, int] = {
            str(k): max(0, int(v)) for k, v in raw_retry.items()
            if isinstance(v, (int, float))
        }

        raw_assignments = data.get("active_assignments") or {}
        safe_assignments: dict[str, Any] = (
            raw_assignments if isinstance(raw_assignments, dict) else {}
        )

        return cls(
            schema_version=int(data.get("schema_version", 1)),
            nightly_autonomy_enabled=bool(data.get("nightly_autonomy_enabled", False)),
            active_project=data.get("active_project"),
            active_workspace=data.get("active_workspace"),
            watchdog=WatchdogState.from_dict(data.get("watchdog") or {}),
            budget=BudgetState.from_dict(data.get("budget") or {}),
            active_assignments=safe_assignments,
            task_retry_count=safe_retry,
            consecutive_tick_failures=max(0, int(data.get("consecutive_tick_failures", 0))),
            last_tick_id=data.get("last_tick_id"),
            last_tick_at=data.get("last_tick_at"),
        )


def load_state(workspace: str | Path | None = None) -> NightlyState:
    """state_snapshot.json에서 상태를 로드한다. 파일 없으면 기본 상태 반환."""
    path = snapshot_path(workspace)
    if not path.exists():
        return NightlyState()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return NightlyState.from_dict(data)
    except Exception:
        return NightlyState()


def save_state(state: NightlyState, workspace: str | Path | None = None) -> None:
    """state를 state_snapshot.json에 atomic write한다."""
    path = snapshot_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = state.to_dict()
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    _render_derived_files(state, path.parent)


def _render_derived_files(state: NightlyState, af_dir_path: Path) -> None:
    """state_snapshot에서 파생 파일들을 렌더링한다 (사람/외부 도구 관찰용)."""
    _write_json_file(af_dir_path / "watchdog_state.json", state.watchdog.to_dict())
    _write_json_file(af_dir_path / "budget_state.json", state.budget.to_dict())
    _write_json_file(
        af_dir_path / "lineage_ledger.json",
        state.watchdog.lineage_counters,
    )


def _write_json_file(path: Path, data: Any) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def mark_alert(workspace: str | Path | None = None, message: str = "") -> None:
    """연속 실패 알림 플래그를 생성한다."""
    flag = alert_flag_path(workspace)
    flag.parent.mkdir(parents=True, exist_ok=True)
    with open(flag, "w", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()}\n{message}\n")


def clear_alert(workspace: str | Path | None = None) -> None:
    flag = alert_flag_path(workspace)
    flag.unlink(missing_ok=True)


def make_tick_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
