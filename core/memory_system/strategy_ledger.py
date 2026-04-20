"""
core/memory_system/strategy_ledger.py
======================================
성공 DAG / 역할 배정 / 실패 패턴 영구 원장.

Phase 4: 과거 프로젝트의 성공·실패 전략을 기록하고
`_pick_owner_role`과 `work_item_generator`에 힌트를 제공한다.

저장소: memory/episodes/strategy_ledger.json (atomic write)
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
import threading
from typing import Any

_MAX_ENTRIES = 1000  # R15: 메모리 폭발 방지 상한


@dataclasses.dataclass
class RoleAssignmentRecord:
    deliverable_pattern: str  # 매칭 키워드 (소문자)
    owner_role: str           # 성공한 역할 ID
    project_id: str
    pass_count: int = 1
    fail_count: int = 0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RoleAssignmentRecord":
        return cls(
            deliverable_pattern=str(d.get("deliverable_pattern", "")),
            owner_role=str(d.get("owner_role", "")),
            project_id=str(d.get("project_id", "")),
            pass_count=max(0, int(d.get("pass_count", 1))),
            fail_count=max(0, int(d.get("fail_count", 0))),
        )

    @property
    def score(self) -> float:
        total = self.pass_count + self.fail_count
        if total == 0:
            return 0.0
        return self.pass_count / total


@dataclasses.dataclass
class FailurePatternRecord:
    pattern_key: str  # error_type + deliverable_keyword
    warning_hint: str
    occurrence_count: int = 1

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FailurePatternRecord":
        return cls(
            pattern_key=str(d.get("pattern_key", "")),
            warning_hint=str(d.get("warning_hint", "")),
            occurrence_count=max(1, int(d.get("occurrence_count", 1))),
        )


class StrategyLedger:
    """성공·실패 전략 원장 — 파일 기반 영속, atomic write."""

    def __init__(self, ledger_path: str) -> None:
        self._path = ledger_path
        self._lock = threading.Lock()
        self._role_assignments: dict[str, RoleAssignmentRecord] = {}
        self._failure_patterns: dict[str, FailurePatternRecord] = {}
        # window_days는 미래 rolling-window 구현 예약 필드.
        # can_auto_save()는 현재 누적 합산 기준으로 판단 (날짜 필터 미구현).
        self._auto_save_stats: dict[str, Any] = {
            "total": 0,
            "pass": 0,
        }
        self._load()

    # ── Persistence ──────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in (data.get("role_assignments") or []):
                rec = RoleAssignmentRecord.from_dict(item)
                if rec.deliverable_pattern:
                    _key = f"{rec.deliverable_pattern}::{rec.owner_role}"
                    if _key in self._role_assignments:
                        # 중복 key: 카운터 합산 (load→save 사이클에서 데이터 손실 방지)
                        existing = self._role_assignments[_key]
                        existing.pass_count += rec.pass_count
                        existing.fail_count += rec.fail_count
                    else:
                        self._role_assignments[_key] = rec
            for item in (data.get("failure_patterns") or []):
                rec2 = FailurePatternRecord.from_dict(item)
                if rec2.pattern_key:
                    self._failure_patterns[rec2.pattern_key] = rec2
            if "auto_save_stats" in data:
                self._auto_save_stats.update(data["auto_save_stats"])
        except Exception:
            pass

    def _save(self) -> None:
        dir_path = os.path.dirname(os.path.abspath(self._path))
        os.makedirs(dir_path, exist_ok=True)
        payload = {
            "role_assignments": [r.to_dict() for r in self._role_assignments.values()],
            "failure_patterns": [r.to_dict() for r in self._failure_patterns.values()],
            "auto_save_stats": self._auto_save_stats,
        }
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

    # ── Auto-save gate (Phase 4 §GR) ────────────────────────────────────

    def record_episode_outcome(self, outcome: str) -> None:
        """verify e2e 결과 기록. outcome: 'pass' | 'fail'."""
        with self._lock:
            self._auto_save_stats["total"] = self._auto_save_stats.get("total", 0) + 1
            if outcome == "pass":
                self._auto_save_stats["pass"] = self._auto_save_stats.get("pass", 0) + 1
            self._save()

    def can_auto_save(self) -> bool:
        """
        누적 합산 기준 PASS ≥ 80% gate.
        조건: N≥20 and M/N≥0.8.
        N<20 또는 미충족 → False (보류).
        (rolling window는 미구현 — 현재 누적 카운터 기반)
        """
        with self._lock:
            total = self._auto_save_stats.get("total", 0)
            passes = self._auto_save_stats.get("pass", 0)
        if total == 0:
            return False
        rate = passes / total
        return total >= 20 and rate >= 0.8

    # ── Role assignment ledger ───────────────────────────────────────────

    def record_role_success(
        self, deliverable_pattern: str, owner_role: str, project_id: str
    ) -> None:
        with self._lock:
            key = f"{deliverable_pattern.lower()}::{owner_role}"
            if key in self._role_assignments:
                self._role_assignments[key].pass_count += 1
            else:
                self._role_assignments[key] = RoleAssignmentRecord(
                    deliverable_pattern=deliverable_pattern.lower(),
                    owner_role=owner_role,
                    project_id=project_id,
                )
            self._evict_if_needed()
            self._save()

    def record_role_failure(
        self, deliverable_pattern: str, owner_role: str, project_id: str
    ) -> None:
        with self._lock:
            key = f"{deliverable_pattern.lower()}::{owner_role}"
            if key in self._role_assignments:
                self._role_assignments[key].fail_count += 1
            else:
                self._role_assignments[key] = RoleAssignmentRecord(
                    deliverable_pattern=deliverable_pattern.lower(),
                    owner_role=owner_role,
                    project_id=project_id,
                    pass_count=0,
                    fail_count=1,
                )
            self._evict_if_needed()
            self._save()

    def lookup_best_role(self, deliverable: str) -> str | None:
        """과거 성공률이 가장 높은 역할을 반환. 충분한 샘플이 없으면 None."""
        with self._lock:
            lowered = deliverable.lower()
            candidates: list[RoleAssignmentRecord] = []
            for _key, rec in self._role_assignments.items():
                dp = rec.deliverable_pattern  # 실제 패턴으로 매칭 (key는 "dp::role" 형식)
                if dp in lowered or any(tok in lowered for tok in dp.split()):
                    if rec.pass_count + rec.fail_count >= 3:
                        candidates.append(rec)
        if not candidates:
            return None
        best = max(candidates, key=lambda r: (r.score, r.pass_count))
        return best.owner_role if best.score > 0.5 else None

    # ── Failure pattern ledger ───────────────────────────────────────────

    def record_failure_pattern(
        self, error_type: str, deliverable_keyword: str, warning_hint: str
    ) -> None:
        with self._lock:
            key = f"{error_type}::{deliverable_keyword.lower()}"
            if key in self._failure_patterns:
                self._failure_patterns[key].occurrence_count += 1
            else:
                self._failure_patterns[key] = FailurePatternRecord(
                    pattern_key=key,
                    warning_hint=warning_hint,
                )
            self._evict_failure_patterns_if_needed()
            self._save()

    def get_warnings_for(self, task_description: str) -> list[str]:
        """task 설명과 매칭되는 경고 힌트 목록을 반환."""
        with self._lock:
            lowered = task_description.lower()
            warnings: list[str] = []
            for rec in self._failure_patterns.values():
                parts = rec.pattern_key.split("::")
                keyword = parts[1] if len(parts) > 1 else ""
                if keyword and keyword in lowered:
                    warnings.append(rec.warning_hint)
        return warnings

    # ── Internal ─────────────────────────────────────────────────────────

    def _evict_if_needed(self) -> None:
        if len(self._role_assignments) > _MAX_ENTRIES:
            sorted_keys = sorted(
                self._role_assignments,
                key=lambda k: self._role_assignments[k].pass_count
                + self._role_assignments[k].fail_count,
            )
            for k in sorted_keys[: len(self._role_assignments) - _MAX_ENTRIES]:
                del self._role_assignments[k]

    def _evict_failure_patterns_if_needed(self) -> None:
        if len(self._failure_patterns) > _MAX_ENTRIES:
            sorted_keys = sorted(
                self._failure_patterns,
                key=lambda k: self._failure_patterns[k].occurrence_count,
            )
            for k in sorted_keys[: len(self._failure_patterns) - _MAX_ENTRIES]:
                del self._failure_patterns[k]


_LEDGER_CACHE: dict[str, StrategyLedger] = {}
_CACHE_LOCK = threading.Lock()


def get_strategy_ledger(workspace: str | None = None) -> StrategyLedger:
    """워크스페이스 기준 memory/strategy_ledger.json 경로로 인스턴스를 반환.

    _CACHE_LOCK으로 멀티스레드 중복 생성을 방지한다.
    """
    base = os.path.abspath(workspace or ".")
    with _CACHE_LOCK:
        if base not in _LEDGER_CACHE:
            path = os.path.join(base, "memory", "episodes", "strategy_ledger.json")
            _LEDGER_CACHE[base] = StrategyLedger(ledger_path=path)
        return _LEDGER_CACHE[base]


def reset_strategy_ledger(workspace: str | None = None) -> None:
    with _CACHE_LOCK:
        if workspace is None:
            _LEDGER_CACHE.clear()
        else:
            _LEDGER_CACHE.pop(os.path.abspath(workspace), None)
