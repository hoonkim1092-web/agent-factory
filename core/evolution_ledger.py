"""
core/evolution_ledger.py
========================
Stage 1 진화 이력 영속 저장소.

RunEventStore(run-scoped)와 분리된 cross-run 영구 ledger.
설계: §4 (병렬 트랙 — Controller와 독립 진행 가능).

append-only JSONL 파일. stats() 집계 메서드 포함.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from core.evolution_types import EvolutionDecision

logger = logging.getLogger(__name__)

_DEFAULT_LEDGER_PATH = os.path.join("data", "evolution", "ledger.jsonl")


@dataclass
class LedgerEntry:
    skill_id: str
    old_version: str
    new_version: str
    trigger: str
    decision: EvolutionDecision
    cost_tokens: int
    candidate_dir: str
    rejection_reason: Optional[str]
    run_id: str
    ts: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["decision"] = self.decision.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LedgerEntry":
        d = dict(d)
        try:
            d["decision"] = EvolutionDecision(d["decision"])
        except (KeyError, ValueError):
            d["decision"] = EvolutionDecision.ERROR
        return cls(**d)


class EvolutionLedger:
    """
    진화 결정 영구 이력.

    append-only JSONL 파일에 기록한다. 스레드 안전.
    """

    def __init__(self, ledger_path: str = _DEFAULT_LEDGER_PATH) -> None:
        self._path = ledger_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)

    def append(self, entry: LedgerEntry) -> None:
        """LedgerEntry를 append-only JSONL에 기록 (best-effort, no fsync)."""
        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception as e:
                logger.error("[EvolutionLedger] append 실패: %s", e)

    def _load_all(self) -> List[LedgerEntry]:
        """전체 ledger 로드. 파일 없으면 빈 리스트."""
        entries: List[LedgerEntry] = []
        with self._lock:
            # exists 검사를 lock 안에서 수행: 같은 프로세스 내 다른 스레드의 동시 쓰기·삭제 race 방어.
            if not os.path.exists(self._path):
                return entries
            try:
                with open(self._path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entries.append(LedgerEntry.from_dict(json.loads(line)))
                        except Exception as e:
                            logger.warning("[EvolutionLedger] 파싱 실패 라인 skip: %s", e)
            except Exception as e:
                logger.error("[EvolutionLedger] load 실패: %s", e)
        return entries

    def list_for_skill(self, skill_id: str) -> List[LedgerEntry]:
        return [e for e in self._load_all() if e.skill_id == skill_id]

    def list_for_run(self, run_id: str) -> List[LedgerEntry]:
        return [e for e in self._load_all() if e.run_id == run_id]

    def stats(self) -> Dict:
        """
        publish_rate, rejection_breakdown, total_cost 집계.

        Returns:
            {
                "total": int,
                "publish_count": int,
                "publish_rate": float,   # 0.0 ~ 1.0
                "rejection_breakdown": {decision_value: count},
                "total_cost_tokens": int,
                "by_trigger": {trigger: count},
            }
        """
        entries = self._load_all()
        total = len(entries)
        if total == 0:
            return {
                "total": 0,
                "publish_count": 0,
                "publish_rate": 0.0,
                "rejection_breakdown": {},
                "total_cost_tokens": 0,
                "by_trigger": {},
            }

        publish_count = sum(1 for e in entries if e.decision == EvolutionDecision.PUBLISHED)
        rejection_breakdown: Dict[str, int] = {}
        total_cost = 0
        by_trigger: Dict[str, int] = {}

        for e in entries:
            if e.decision != EvolutionDecision.PUBLISHED:
                key = e.decision.value
                rejection_breakdown[key] = rejection_breakdown.get(key, 0) + 1
            total_cost += e.cost_tokens
            by_trigger[e.trigger] = by_trigger.get(e.trigger, 0) + 1

        return {
            "total": total,
            "publish_count": publish_count,
            "publish_rate": publish_count / total,
            "rejection_breakdown": rejection_breakdown,
            "total_cost_tokens": total_cost,
            "by_trigger": by_trigger,
        }
