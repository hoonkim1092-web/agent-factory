"""
RunEvent — AF 실행 이벤트의 단일 진실원천 스키마.

현재 3곳에 분산된 trace 기록(agent_runner chat_trace, dynamic_orchestrator
state_snapshot, hooks/memory_consolidation episode)을 이 schema로 수렴시킨다.
T3-7에서 audit/cost/approval을 이 스키마로 통합한다.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunEventType(str, Enum):
    RUN_STARTED = "run_started"
    RUN_RESUMED = "run_resumed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    CHECKPOINT_SAVED = "checkpoint_saved"
    CHECKPOINT_LOADED = "checkpoint_loaded"
    COST_INCURRED = "cost_incurred"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"


@dataclass
class RunEvent:
    run_id: str
    event_type: RunEventType
    payload: dict
    ts: str = field(default_factory=_utcnow)
    project_id: str = ""
    agent_id: str = ""
    step_id: str = ""
    tenant_id: str = ""
    cost_event_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "event_type": self.event_type.value if isinstance(self.event_type, RunEventType) else self.event_type,
            "payload": self.payload,
            "ts": self.ts,
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "step_id": self.step_id,
            "tenant_id": self.tenant_id,
            "cost_event_id": self.cost_event_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RunEvent":
        et = data.get("event_type", "")
        try:
            et = RunEventType(et)
        except ValueError:
            pass
        return cls(
            run_id=data["run_id"],
            event_type=et,
            payload=data.get("payload", {}),
            ts=data.get("ts", _utcnow()),
            project_id=data.get("project_id", ""),
            agent_id=data.get("agent_id", ""),
            step_id=data.get("step_id", ""),
            tenant_id=data.get("tenant_id", ""),
            cost_event_id=data.get("cost_event_id"),
        )


class RunEventStore(ABC):
    @abstractmethod
    def append(self, event: RunEvent) -> None: ...

    @abstractmethod
    def list_events(self, run_id: str) -> list[RunEvent]: ...


class FileRunEventStore(RunEventStore):
    """파일 기반 RunEvent store. runs/{run_id}/events.jsonl (append-only)."""

    def __init__(self, base_dir: str = "runs"):
        self._base_dir = base_dir

    def _path(self, run_id: str) -> str:
        return os.path.join(self._base_dir, run_id, "events.jsonl")

    def append(self, event: RunEvent) -> None:
        path = self._path(event.run_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass  # fire-and-forget — event logging must not crash the caller

    def list_events(self, run_id: str) -> list[RunEvent]:
        path = self._path(run_id)
        if not os.path.exists(path):
            return []
        events = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(RunEvent.from_dict(json.loads(line)))
                        except Exception:
                            pass
        except Exception:
            pass
        return events


_default_store: Optional[RunEventStore] = None


def get_default_store(base_dir: str = "runs") -> RunEventStore:
    global _default_store
    if _default_store is None:
        resolved = os.environ.get("AF_CHECKPOINT_DIR") or base_dir
        _default_store = FileRunEventStore(base_dir=resolved)
    return _default_store
