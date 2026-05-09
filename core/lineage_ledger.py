"""
core/lineage_ledger.py
======================
lineage 기반 Level 누적 원장.

각 lineage_id에 대한 에스컬레이션 레벨·시도 횟수·이력을 .af/lineage_ledger.json에 영구 기록한다.
쓰기는 tempfile+os.replace atomic write로 보장한다.

Lineage 상한: lifetime_attempts >= _MAX_LIFETIME_ATTEMPTS 또는 level >= _MAX_LEVEL
→ watchdog degrade 경로 위임.

`attempts`는 연속 실패(failure_streak)로, success 시 0으로 리셋됨.
`lifetime_attempts`는 누적 시도이며 절대 리셋되지 않아 라이프타임 캡으로 작용한다.
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
import threading

# 연속 실패(failure_streak)가 이 값에 도달하면 maxed로 판정. 레거시 키이며
# attempts 필드와 같은 카운터를 의미한다.
_MAX_ATTEMPTS = 20
# 라이프타임 누적 attempts 상한. fail-success-fail 패턴을 막기 위함.
_MAX_LIFETIME_ATTEMPTS = 50
# FSALoop._decide_escalation가 반환하는 최대 레벨(Level 5 = 태스크 분해).
# 레벨 5도 실패하면 더 이상 에스컬레이션할 단계가 없으므로 degrade로 위임한다.
_MAX_LEVEL = 5


@dataclasses.dataclass
class LineageEntry:
    lineage_id: str
    level: int = 1
    attempts: int = 0  # 연속 실패 streak (success 시 0 리셋)
    lifetime_attempts: int = 0  # 누적 실패 (절대 리셋 안 함, 라이프타임 캡)
    history: list = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lineage_id": self.lineage_id,
            "level": self.level,
            "attempts": self.attempts,
            "lifetime_attempts": self.lifetime_attempts,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineageEntry":
        attempts = max(0, int(data.get("attempts", 0)))
        # 레거시 데이터 호환: lifetime_attempts 미존재 시 attempts에서 복사.
        lifetime = max(attempts, int(data.get("lifetime_attempts", attempts)))
        return cls(
            lineage_id=str(data.get("lineage_id", "")),
            level=max(1, int(data.get("level", 1))),
            attempts=attempts,
            lifetime_attempts=lifetime,
            history=list(data.get("history") or []),
        )


class LineageLedger:
    """lineage 원장 — 파일 기반 영속, atomic write."""

    def __init__(self, ledger_path: str):
        self._path = ledger_path
        self._lock = threading.Lock()
        self._entries: dict[str, LineageEntry] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        if not isinstance(data, dict):
            return

        # Legacy 감지: B2-2 회귀 기간 동안 NightlyState._render_derived_files가
        # 같은 파일에 `{lineage_id: {level, attempts}}` map-shape을 덮어써
        # entries 포맷을 파괴. 이 경우 내용을 `.corrupt.<ts>.json`으로 백업하고
        # 빈 원장으로 재시작하여 FSA 안전장치 복원 (is_maxed 오판정 방지).
        if "entries" not in data and data and all(
            isinstance(v, dict) and ("level" in v or "attempts" in v)
            for v in data.values()
        ):
            import time
            backup = f"{self._path}.corrupt.{int(time.time())}.json"
            try:
                os.replace(self._path, backup)
                print(
                    f"[lineage_ledger] legacy map-shape 감지 → 백업 후 재시작: {backup}",
                    flush=True,
                )
            except OSError:
                pass
            return

        with self._lock:
            for item in (data.get("entries") or []):
                try:
                    entry = LineageEntry.from_dict(item)
                except Exception:
                    continue
                if entry.lineage_id:
                    self._entries[entry.lineage_id] = entry

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

    def _get_or_create(self, lineage_id: str) -> LineageEntry:
        if lineage_id not in self._entries:
            self._entries[lineage_id] = LineageEntry(lineage_id=lineage_id)
        return self._entries[lineage_id]

    def is_maxed(self, lineage_id: str) -> bool:
        """maxed 판정 — 연속 실패 streak, 라이프타임 누적, 레벨 상한 셋 다 검사."""
        with self._lock:
            entry = self._entries.get(lineage_id)
            if entry is None:
                return False
            return (
                entry.attempts >= _MAX_ATTEMPTS
                or entry.lifetime_attempts >= _MAX_LIFETIME_ATTEMPTS
                or entry.level >= _MAX_LEVEL
            )

    def on_task_failure(self, lineage_id: str, new_level: int, reason: str = "") -> LineageEntry:
        """실패 기록 + 레벨 갱신 후 atomic write.

        attempts(연속 streak)와 lifetime_attempts(누적) 둘 다 증가.
        """
        from core.utils import now_iso
        with self._lock:
            entry = self._get_or_create(lineage_id)
            entry.attempts += 1
            entry.lifetime_attempts += 1
            entry.level = new_level
            entry.history.append({
                "ts": now_iso(),
                "level": new_level,
                "attempts": entry.attempts,
                "lifetime_attempts": entry.lifetime_attempts,
                "outcome": "failure",
                "reason": reason[:200],
            })
            self._save()
        return entry

    def on_task_success(self, lineage_id: str, level: int) -> None:
        """성공 기록 후 atomic write.

        attempts(연속 실패 streak)와 level만 1/0으로 리셋.
        lifetime_attempts는 보존하여 fail-success-fail 패턴이 라이프타임 캡을
        우회하지 못하도록 한다. history도 보존해 학습 신호 유지.
        """
        from core.utils import now_iso
        with self._lock:
            entry = self._get_or_create(lineage_id)
            entry.history.append({
                "ts": now_iso(),
                "level": level,
                "attempts": entry.attempts,
                "lifetime_attempts": entry.lifetime_attempts,
                "outcome": "success",
            })
            entry.level = 1
            entry.attempts = 0
            self._save()


_LEDGER_CACHE: dict[str, LineageLedger] = {}
_CACHE_LOCK = threading.Lock()


def get_lineage_ledger(workspace: str | None = None) -> LineageLedger:
    """워크스페이스 기준 .af/lineage_ledger.json 경로로 인스턴스를 반환.

    workspace별로 캐싱하여 다중 프로젝트 실행 시 원장 교차 오염을 방지한다.
    _CACHE_LOCK으로 멀티스레드 중복 생성을 방지한다.
    """
    base = os.path.abspath(workspace or ".")
    with _CACHE_LOCK:
        if base not in _LEDGER_CACHE:
            path = os.path.join(base, ".af", "lineage_ledger.json")
            _LEDGER_CACHE[base] = LineageLedger(ledger_path=path)
        return _LEDGER_CACHE[base]


def reset_lineage_ledger(workspace: str | None = None) -> None:
    """지정 워크스페이스(또는 전체) 캐시를 초기화한다."""
    with _CACHE_LOCK:
        if workspace is None:
            _LEDGER_CACHE.clear()
        else:
            _LEDGER_CACHE.pop(os.path.abspath(workspace), None)
