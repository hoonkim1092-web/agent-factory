"""야간 자율 파이프라인 워치독 상태 관리.

tick 기반 아키텍처에서 cycle 카운터 대신 파일 기반 stall 감지를 수행한다.
상태는 state_snapshot.json에 포함되어 atomic write로 보존된다.
"""
from __future__ import annotations

import dataclasses
from typing import Any, Optional


@dataclasses.dataclass
class LineageCounter:
    level: int = 0
    attempts: int = 0


@dataclasses.dataclass
class WatchdogState:
    """tick 간 유지되는 watchdog 상태. cycle 카운터 없음."""

    last_progress_tick_id: Optional[str] = None
    consecutive_no_progress_ticks: int = 0
    # OK | STALL_1 | STALL_2 | STALL_3 | CHECKPOINT_ONLY
    watchdog_level: str = "OK"
    lineage_counters: dict[str, dict] = dataclasses.field(default_factory=dict)
    checkpoint_only_since: Optional[str] = None

    STALL_1_THRESHOLD = 1
    STALL_2_THRESHOLD = 4
    STALL_3_THRESHOLD = 8
    CHECKPOINT_ONLY_THRESHOLD = 16

    def tick_no_progress(self) -> None:
        """진전 없는 tick을 기록하고 stall 레벨을 에스컬레이션한다."""
        self.consecutive_no_progress_ticks += 1
        n = self.consecutive_no_progress_ticks
        if n >= self.CHECKPOINT_ONLY_THRESHOLD:
            self.watchdog_level = "CHECKPOINT_ONLY"
        elif n >= self.STALL_3_THRESHOLD:
            self.watchdog_level = "STALL_3"
        elif n >= self.STALL_2_THRESHOLD:
            self.watchdog_level = "STALL_2"
        elif n >= self.STALL_1_THRESHOLD:
            self.watchdog_level = "STALL_1"

    def tick_progress(self, tick_id: str) -> None:
        """진전 있는 tick을 기록하고 stall 카운터를 리셋한다."""
        self.last_progress_tick_id = tick_id
        self.consecutive_no_progress_ticks = 0
        self.watchdog_level = "OK"
        self.checkpoint_only_since = None

    def increment_lineage(self, lineage_id: str) -> int:
        """lineage 재시도 횟수를 증분하고 현재 횟수를 반환한다."""
        entry = self.lineage_counters.setdefault(lineage_id, {"level": 0, "attempts": 0})
        entry["attempts"] += 1
        return entry["attempts"]

    def update_lineage_level(self, lineage_id: str, level: int, outcome: str) -> None:
        """lineage 레벨과 결과를 갱신한다 (WatchdogState 내 빠른 조회용)."""
        entry = self.lineage_counters.setdefault(lineage_id, {"level": 0, "attempts": 0})
        entry["level"] = level
        entry["last_outcome"] = outcome

    def is_lineage_maxed(self, lineage_id: str, max_attempts: int = 20) -> bool:
        """lineage 상한 도달 여부 반환. lineage_ledger와 이중 체크용."""
        entry = self.lineage_counters.get(lineage_id)
        if entry is None:
            return False
        return entry.get("attempts", 0) >= max_attempts or entry.get("level", 0) > 5

    def degrade_lineage(self, lineage_id: str) -> None:
        """lineage 상한 도달 시 degrade 플래그 설정. attempts를 max+1로 고정."""
        entry = self.lineage_counters.setdefault(lineage_id, {"level": 0, "attempts": 0})
        entry["degraded"] = True
        if entry.get("attempts", 0) < 20:
            entry["attempts"] = 20

    def is_checkpoint_only(self) -> bool:
        return self.watchdog_level == "CHECKPOINT_ONLY"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    _VALID_LEVELS: frozenset[str] = frozenset(
        {"OK", "STALL_1", "STALL_2", "STALL_3", "CHECKPOINT_ONLY"}
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WatchdogState":
        raw_level = data.get("watchdog_level", "OK")
        safe_level = raw_level if raw_level in cls._VALID_LEVELS else "OK"

        raw_counters = data.get("lineage_counters") or {}
        safe_counters: dict[str, dict] = {}
        for lid, entry in raw_counters.items():
            if isinstance(entry, dict):
                try:
                    level = max(0, int(entry.get("level", 0)))
                    attempts = max(0, int(entry.get("attempts", 0)))
                except (TypeError, ValueError):
                    level, attempts = 0, 0
                # extra fields(last_outcome, degraded 등)도 보존한다
                rebuilt: dict = dict(entry)
                rebuilt["level"] = level
                rebuilt["attempts"] = attempts
                safe_counters[str(lid)] = rebuilt

        return cls(
            last_progress_tick_id=data.get("last_progress_tick_id"),
            consecutive_no_progress_ticks=max(0, int(data.get("consecutive_no_progress_ticks", 0))),
            watchdog_level=safe_level,
            lineage_counters=safe_counters,
            checkpoint_only_since=data.get("checkpoint_only_since"),
        )
