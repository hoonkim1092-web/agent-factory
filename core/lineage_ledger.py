"""
core/lineage_ledger.py
======================
lineage 기반 Level 누적 원장.

각 lineage_id에 대한 에스컬레이션 레벨·시도 횟수·이력을 .af/lineage_ledger.json에 영구 기록한다.
쓰기는 tempfile+os.replace atomic write로 보장한다.

Lineage 상한: attempts >= 20 또는 level > 5 → watchdog degrade 경로 위임.
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile

_MAX_ATTEMPTS = 20


@dataclasses.dataclass
class LineageEntry:
    lineage_id: str
    level: int = 1
    attempts: int = 0
    history: list = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lineage_id": self.lineage_id,
            "level": self.level,
            "attempts": self.attempts,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineageEntry":
        return cls(
            lineage_id=str(data.get("lineage_id", "")),
            level=max(1, int(data.get("level", 1))),
            attempts=max(0, int(data.get("attempts", 0))),
            history=list(data.get("history") or []),
        )


class LineageLedger:
    """lineage 원장 — 파일 기반 영속, atomic write."""

    def __init__(self, ledger_path: str):
        self._path = ledger_path
        self._entries: dict[str, LineageEntry] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in (data.get("entries") or []):
                entry = LineageEntry.from_dict(item)
                if entry.lineage_id:
                    self._entries[entry.lineage_id] = entry
        except Exception:
            pass

    def _save(self) -> None:
        dir_path = os.path.dirname(os.path.abspath(self._path))
        os.makedirs(dir_path, exist_ok=True)
        payload = {"entries": [e.to_dict() for e in self._entries.values()]}
        fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def get_or_create(self, lineage_id: str) -> LineageEntry:
        if lineage_id not in self._entries:
            self._entries[lineage_id] = LineageEntry(lineage_id=lineage_id)
        return self._entries[lineage_id]

    def is_maxed(self, lineage_id: str) -> bool:
        entry = self._entries.get(lineage_id)
        if entry is None:
            return False
        return entry.attempts >= _MAX_ATTEMPTS or entry.level > 5

    def on_task_failure(self, lineage_id: str, new_level: int, reason: str = "") -> LineageEntry:
        """실패 기록 + 레벨 갱신 후 atomic write."""
        from core.utils import now_iso
        entry = self.get_or_create(lineage_id)
        entry.attempts += 1
        entry.level = new_level
        entry.history.append({
            "ts": now_iso(),
            "level": new_level,
            "attempts": entry.attempts,
            "outcome": "failure",
            "reason": reason[:200],
        })
        self._save()
        return entry

    def on_task_success(self, lineage_id: str, level: int) -> None:
        """성공 기록 후 atomic write."""
        from core.utils import now_iso
        entry = self.get_or_create(lineage_id)
        entry.history.append({
            "ts": now_iso(),
            "level": level,
            "attempts": entry.attempts,
            "outcome": "success",
        })
        self._save()


_LEDGER_CACHE: dict[str, LineageLedger] = {}


def get_lineage_ledger(workspace: str | None = None) -> LineageLedger:
    """워크스페이스 기준 .af/lineage_ledger.json 경로로 인스턴스를 반환.

    workspace별로 캐싱하여 다중 프로젝트 실행 시 원장 교차 오염을 방지한다.
    """
    base = os.path.abspath(workspace or ".")
    if base not in _LEDGER_CACHE:
        path = os.path.join(base, ".af", "lineage_ledger.json")
        _LEDGER_CACHE[base] = LineageLedger(ledger_path=path)
    return _LEDGER_CACHE[base]


def reset_lineage_ledger(workspace: str | None = None) -> None:
    """지정 워크스페이스(또는 전체) 캐시를 초기화한다."""
    if workspace is None:
        _LEDGER_CACHE.clear()
    else:
        _LEDGER_CACHE.pop(os.path.abspath(workspace), None)
