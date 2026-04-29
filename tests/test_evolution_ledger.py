"""
tests/test_evolution_ledger.py
================================
EvolutionLedger 단위 테스트 — Sprint 2.

JSONL 라운드트립, list_for_skill/run 인덱싱, stats 집계, Optional no-op 검증.
"""
from __future__ import annotations

import datetime
import json

import pytest

from core.evolution_ledger import EvolutionLedger, LedgerEntry
from core.evolution_types import EvolutionDecision


def _entry(
    skill_id: str = "s1",
    decision: EvolutionDecision = EvolutionDecision.PUBLISHED,
    trigger: str = "fsa_failure",
    run_id: str = "run1",
    cost_tokens: int = 100,
) -> LedgerEntry:
    return LedgerEntry(
        skill_id=skill_id,
        old_version="1.0",
        new_version="1.1",
        trigger=trigger,
        decision=decision,
        cost_tokens=cost_tokens,
        candidate_dir="",
        rejection_reason=None,
        run_id=run_id,
        ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


class TestLedgerAppendLoad:
    def test_append_and_load_roundtrip(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        e = _entry()
        ledger.append(e)

        entries = ledger._load_all()
        assert len(entries) == 1
        assert entries[0].skill_id == "s1"
        assert entries[0].decision == EvolutionDecision.PUBLISHED

    def test_multiple_appends(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        for i in range(5):
            ledger.append(_entry(skill_id=f"s{i}"))

        entries = ledger._load_all()
        assert len(entries) == 5

    def test_empty_file_returns_empty(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        assert ledger._load_all() == []

    def test_decision_serialization(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        ledger.append(_entry(decision=EvolutionDecision.REJECTED))
        entries = ledger._load_all()
        assert entries[0].decision == EvolutionDecision.REJECTED

    def test_invalid_line_skipped(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        path.write_text('{"invalid": true}\n{"also": "broken"}\n')
        ledger = EvolutionLedger(str(path))
        entries = ledger._load_all()  # 파싱 실패 라인 skip, 예외 미발생
        assert entries == []


class TestLedgerFilters:
    def test_list_for_skill(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        ledger.append(_entry(skill_id="alpha"))
        ledger.append(_entry(skill_id="beta"))
        ledger.append(_entry(skill_id="alpha"))

        result = ledger.list_for_skill("alpha")
        assert len(result) == 2
        assert all(e.skill_id == "alpha" for e in result)

    def test_list_for_run(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        ledger.append(_entry(run_id="r1"))
        ledger.append(_entry(run_id="r2"))
        ledger.append(_entry(run_id="r1"))

        result = ledger.list_for_run("r1")
        assert len(result) == 2
        assert all(e.run_id == "r1" for e in result)


class TestLedgerStats:
    def test_stats_empty(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        stats = ledger.stats()
        assert stats["total"] == 0
        assert stats["publish_rate"] == 0.0

    def test_stats_all_published(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        for _ in range(4):
            ledger.append(_entry(decision=EvolutionDecision.PUBLISHED, cost_tokens=50))

        stats = ledger.stats()
        assert stats["total"] == 4
        assert stats["publish_count"] == 4
        assert stats["publish_rate"] == 1.0
        assert stats["total_cost_tokens"] == 200
        assert stats["rejection_breakdown"] == {}

    def test_stats_mixed(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        ledger.append(_entry(decision=EvolutionDecision.PUBLISHED, cost_tokens=100))
        ledger.append(_entry(decision=EvolutionDecision.REJECTED, cost_tokens=50))
        ledger.append(_entry(decision=EvolutionDecision.ERROR, cost_tokens=0))

        stats = ledger.stats()
        assert stats["total"] == 3
        assert stats["publish_count"] == 1
        assert abs(stats["publish_rate"] - 1 / 3) < 1e-9
        assert stats["total_cost_tokens"] == 150
        assert stats["rejection_breakdown"]["rejected"] == 1
        assert stats["rejection_breakdown"]["error"] == 1

    def test_stats_by_trigger(self, tmp_path):
        ledger = EvolutionLedger(str(tmp_path / "ledger.jsonl"))
        ledger.append(_entry(trigger="fsa_failure"))
        ledger.append(_entry(trigger="fsa_failure"))
        ledger.append(_entry(trigger="cross_verification"))

        stats = ledger.stats()
        assert stats["by_trigger"]["fsa_failure"] == 2
        assert stats["by_trigger"]["cross_verification"] == 1
