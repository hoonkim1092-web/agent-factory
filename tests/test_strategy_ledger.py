"""tests/test_strategy_ledger.py — StrategyLedger unit tests (B2-4)."""
import os
import json
import tempfile

import pytest

from core.memory_system.strategy_ledger import StrategyLedger, _MAX_ENTRIES


@pytest.fixture()
def ledger(tmp_path):
    return StrategyLedger(ledger_path=str(tmp_path / "ledger.json"))


# ── record_role_batch ─────────────────────────────────────────────────────────

def test_batch_increments_pass(ledger):
    ledger.record_role_batch([("api", "backend_dev", "proj1", True)])
    assert ledger._role_assignments["api::backend_dev"].pass_count == 1
    assert ledger._role_assignments["api::backend_dev"].fail_count == 0


def test_batch_increments_fail(ledger):
    ledger.record_role_batch([("api", "backend_dev", "proj1", False)])
    assert ledger._role_assignments["api::backend_dev"].pass_count == 0
    assert ledger._role_assignments["api::backend_dev"].fail_count == 1


def test_batch_same_key_accumulates(ledger):
    ledger.record_role_batch([
        ("api", "backend_dev", "proj1", True),
        ("api", "backend_dev", "proj1", True),
    ])
    assert ledger._role_assignments["api::backend_dev"].pass_count == 2


def test_batch_empty_is_noop(ledger, tmp_path):
    path = str(tmp_path / "ledger.json")
    before_mtime = os.path.exists(path)
    ledger.record_role_batch([])
    # 파일이 생성되지 않아야 함 (빈 배치 → _save() 호출 안 됨)
    assert not os.path.exists(path)


def test_batch_multiple_patterns(ledger):
    ledger.record_role_batch([
        ("ui 구현", "frontend_dev", "proj1", True),
        ("api 서버", "backend_dev", "proj1", True),
    ])
    assert "ui 구현::frontend_dev" in ledger._role_assignments
    assert "api 서버::backend_dev" in ledger._role_assignments


# ── atomic write + reload roundtrip ──────────────────────────────────────────

def test_batch_persists_and_reloads(tmp_path):
    path = str(tmp_path / "ledger.json")
    l1 = StrategyLedger(ledger_path=path)
    l1.record_role_batch([("game", "frontend_dev", "proj1", True)] * 3)

    l2 = StrategyLedger(ledger_path=path)
    assert l2._role_assignments["game::frontend_dev"].pass_count == 3


# ── eviction ─────────────────────────────────────────────────────────────────

def test_eviction_on_overflow(tmp_path):
    path = str(tmp_path / "ledger.json")
    ledger = StrategyLedger(ledger_path=path)
    entries = [(f"pattern_{i}", "role", "proj", True) for i in range(_MAX_ENTRIES + 5)]
    ledger.record_role_batch(entries)
    assert len(ledger._role_assignments) <= _MAX_ENTRIES


# ── lookup_best_role (word-boundary pattern) ──────────────────────────────────

def test_lookup_returns_role_after_enough_samples(tmp_path):
    path = str(tmp_path / "ledger.json")
    ledger = StrategyLedger(ledger_path=path)
    # 4단어 절삭 패턴 "api endpoint for user" — 3회 이상 통과해야 lookup 반환
    ledger.record_role_batch([("api endpoint for user", "backend_dev", "proj", True)] * 3)
    result = ledger.lookup_best_role("api endpoint for user management")
    assert result == "backend_dev"


def test_lookup_returns_none_below_sample_threshold(tmp_path):
    path = str(tmp_path / "ledger.json")
    ledger = StrategyLedger(ledger_path=path)
    ledger.record_role_batch([("api", "backend_dev", "proj", True)] * 2)
    assert ledger.lookup_best_role("api server") is None


def test_lookup_returns_none_on_low_score(tmp_path):
    path = str(tmp_path / "ledger.json")
    ledger = StrategyLedger(ledger_path=path)
    # 실패 다수 → score <= 0.5
    ledger.record_role_batch([("game", "backend_dev", "proj", False)] * 4)
    assert ledger.lookup_best_role("game logic") is None


# ── end-to-end: record_role_batch → _pick_owner_role integration ─────────────

def test_pick_owner_role_uses_ledger_after_batch(tmp_path):
    """record_role_batch로 저장된 패턴을 _pick_owner_role이 올바르게 사용하는지 검증 (B2-4)."""
    import unittest.mock as mock
    from core.project_task_board import _pick_owner_role

    path = str(tmp_path / "ledger.json")
    ledger = StrategyLedger(ledger_path=path)
    # 4단어 패턴으로 3회 이상 성공 기록
    ledger.record_role_batch([("game logic engine", "logic_dev", "proj", True)] * 3)

    roles = [
        {"id": "logic_dev", "name": "Logic Dev"},
        {"id": "frontend_dev", "name": "Frontend Dev"},
    ]

    with mock.patch(
        "core.memory_system.strategy_ledger.get_strategy_ledger",
        return_value=ledger,
    ):
        result = _pick_owner_role("game logic engine implementation", roles, workspace=str(tmp_path))

    assert result == "logic_dev"


def test_batch_duplicate_entries_accumulate(tmp_path):
    """record_role_batch 내 동일 (pattern, owner_role) 쌍은 순서대로 누산된다 (docstring 계약)."""
    path = str(tmp_path / "ledger.json")
    ledger = StrategyLedger(ledger_path=path)
    entries = [
        ("api 서버", "backend_dev", "proj", True),
        ("api 서버", "backend_dev", "proj", True),
    ]
    ledger.record_role_batch(entries)
    assert ledger._role_assignments["api 서버::backend_dev"].pass_count == 2
