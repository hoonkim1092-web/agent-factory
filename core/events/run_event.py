"""
RunEvent — AF 실행 이벤트의 단일 진실원천 스키마.

현재 3곳에 분산된 trace 기록(agent_runner chat_trace, dynamic_orchestrator
state_snapshot, hooks/memory_consolidation episode)을 이 schema로 수렴시킨다.
T3-7에서 audit/cost/approval을 이 스키마로 통합한다.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

_SIZE_WARN_THRESHOLD = 1_048_576  # 1 MiB
_size_warned_paths: set[str] = set()  # 프로세스 수명 동안 경로별 1회만 경고


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
    SKILL_EVOLVED = "skill_evolved"                          # deprecated — 1 sprint 호환 유지
    METADATA_ENRICHED = "metadata_enriched"                  # bulk_enrich → on_bulk_enriched
    EVOLUTION_REQUESTED = "evolution_requested"              # Controller.submit() 진입
    EVOLUTION_PUBLISHED = "evolution_published"              # candidate → live publish 성공
    EVOLUTION_ROLLED_BACK = "evolution_rolled_back"          # REJECTED/DEFERRED/ERROR → candidate 폐기


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
            # 파일 크기 경고 (1회만)
            if path not in _size_warned_paths:
                try:
                    if os.path.getsize(path) >= _SIZE_WARN_THRESHOLD:
                        _size_warned_paths.add(path)
                        logger.warning(
                            "[RunEventStore] events.jsonl 크기 초과 (≥1MiB): %s — 오래된 run 정리 권장",
                            path,
                        )
                except OSError:
                    pass
        except Exception as exc:
            logger.error("[RunEventStore] append 실패 (run_id=%s): %s", event.run_id, exc)

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
_default_store_lock = threading.Lock()  # get_default_store() 멀티스레드 초기화 안전


def get_default_store(base_dir: str = "runs") -> RunEventStore:
    """프로세스 싱글톤 RunEventStore 반환. 첫 번째 호출 이후 base_dir는 무시됨.
    Warning: 테스트에서는 반드시 patch 또는 AF_CHECKPOINT_DIR 설정 필요 — 미적용 시 상태 누출."""
    global _default_store
    if _default_store is None:
        with _default_store_lock:
            if _default_store is None:  # double-checked locking
                resolved = os.environ.get("AF_CHECKPOINT_DIR") or base_dir
                _default_store = FileRunEventStore(base_dir=resolved)
    return _default_store
