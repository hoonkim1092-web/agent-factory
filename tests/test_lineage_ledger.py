"""LineageLedger — level cap 및 atomic write 테스트 (P0-D).

Codex 검증이 지적한 `entry.level > 5` dead-code 버그가 `>= _MAX_LEVEL`
수정으로 해결됐는지 검증한다. 기본 read/write 경로도 smoke 테스트.
"""
from __future__ import annotations

import os
import tempfile
import pytest

from core.lineage_ledger import (
    LineageEntry,
    LineageLedger,
    _MAX_LEVEL,
    _MAX_ATTEMPTS,
    _MAX_LIFETIME_ATTEMPTS,
    get_lineage_ledger,
    reset_lineage_ledger,
)


@pytest.fixture
def tmp_ledger_path():
    with tempfile.TemporaryDirectory() as d:
        yield os.path.join(d, "lineage_ledger.json")


def test_is_maxed_returns_false_on_new_lineage(tmp_ledger_path):
    ledger = LineageLedger(tmp_ledger_path)
    assert ledger.is_maxed("new-lineage-id") is False


def test_is_maxed_triggers_on_max_level(tmp_ledger_path):
    """Codex 지적: 이전에는 level > 5 → 영원히 False. 이제 level == 5에서 True."""
    ledger = LineageLedger(tmp_ledger_path)
    ledger.on_task_failure("lin1", new_level=_MAX_LEVEL, reason="decomposed and failed")
    assert ledger.is_maxed("lin1") is True


def test_is_maxed_false_below_max_level(tmp_ledger_path):
    ledger = LineageLedger(tmp_ledger_path)
    ledger.on_task_failure("lin2", new_level=_MAX_LEVEL - 1, reason="not yet")
    assert ledger.is_maxed("lin2") is False


def test_is_maxed_triggers_on_max_attempts(tmp_ledger_path):
    ledger = LineageLedger(tmp_ledger_path)
    for _ in range(_MAX_ATTEMPTS):
        ledger.on_task_failure("lin3", new_level=1, reason="retry")
    assert ledger.is_maxed("lin3") is True


def test_entry_persists_across_reload(tmp_ledger_path):
    """실패 기록만 한 lineage는 다음 로드 시 level/attempts가 보존되어야 한다."""
    ledger1 = LineageLedger(tmp_ledger_path)
    ledger1.on_task_failure("lin4", new_level=3, reason="persist me")

    ledger2 = LineageLedger(tmp_ledger_path)
    entry = ledger2._entries.get("lin4")
    assert entry is not None
    assert entry.level == 3
    assert entry.attempts == 1
    assert len(entry.history) == 1
    assert entry.history[0]["outcome"] == "failure"


def test_history_persists_after_success_reset(tmp_ledger_path):
    """P3: success는 level/attempts를 리셋하지만 history는 보존되고 디스크에 영속된다."""
    ledger1 = LineageLedger(tmp_ledger_path)
    ledger1.on_task_failure("lin4b", new_level=3, reason="prior")
    ledger1.on_task_success("lin4b", level=3)

    ledger2 = LineageLedger(tmp_ledger_path)
    entry = ledger2._entries.get("lin4b")
    assert entry is not None
    assert entry.level == 1  # P3 리셋
    assert entry.attempts == 0
    assert len(entry.history) == 2
    assert {h["outcome"] for h in entry.history} == {"failure", "success"}


def test_on_task_success_resets_maxed_state(tmp_ledger_path):
    """P3: on_task_success가 level/attempts를 리셋해야 한다.

    af-critic 지적: 분해 성공 후에도 entry.level=5가 남으면 다음 lineage 재진입에서
    is_maxed 즉시 트리거되어 FSA 재시도가 차단된다.
    """
    ledger = LineageLedger(tmp_ledger_path)
    ledger.on_task_failure("lin-success", new_level=_MAX_LEVEL, reason="prep")
    assert ledger.is_maxed("lin-success") is True

    ledger.on_task_success("lin-success", level=_MAX_LEVEL)
    assert ledger.is_maxed("lin-success") is False
    entry = ledger._entries["lin-success"]
    assert entry.level == 1
    assert entry.attempts == 0
    # history는 보존
    assert any(h.get("outcome") == "success" for h in entry.history)
    # lifetime_attempts는 보존되어야 라이프타임 캡 회귀 방지
    assert entry.lifetime_attempts == 1


def test_lifetime_attempts_cap_blocks_oscillation(tmp_ledger_path):
    """Codex 회귀 #4: fail-success-fail 패턴이 attempts 리셋을 악용해 무한 retry할 수 없어야 한다."""
    ledger = LineageLedger(tmp_ledger_path)
    for _ in range(_MAX_LIFETIME_ATTEMPTS):
        ledger.on_task_failure("lin-osc", new_level=2, reason="streak")
        ledger.on_task_success("lin-osc", level=2)
    # streak attempts는 매번 리셋되어 _MAX_ATTEMPTS 미달이지만,
    # lifetime_attempts >= _MAX_LIFETIME_ATTEMPTS → maxed True
    entry = ledger._entries["lin-osc"]
    assert entry.attempts == 0
    assert entry.lifetime_attempts >= _MAX_LIFETIME_ATTEMPTS
    assert ledger.is_maxed("lin-osc") is True


def test_legacy_data_without_lifetime_attempts_loads(tmp_ledger_path):
    """레거시 JSON(attempts만 있음)은 lifetime_attempts를 attempts에서 복사해 로드되어야 한다."""
    import json
    legacy = {
        "entries": [
            {
                "lineage_id": "legacy",
                "level": 2,
                "attempts": 5,
                "history": [],
            }
        ]
    }
    with open(tmp_ledger_path, "w") as f:
        json.dump(legacy, f)
    ledger = LineageLedger(tmp_ledger_path)
    entry = ledger._entries["legacy"]
    assert entry.attempts == 5
    assert entry.lifetime_attempts == 5


def test_get_lineage_ledger_caches_per_workspace(tmp_path):
    reset_lineage_ledger()
    ws_a = str(tmp_path / "a")
    ws_b = str(tmp_path / "b")
    os.makedirs(ws_a)
    os.makedirs(ws_b)

    la1 = get_lineage_ledger(ws_a)
    la2 = get_lineage_ledger(ws_a)
    lb = get_lineage_ledger(ws_b)

    assert la1 is la2
    assert la1 is not lb

    reset_lineage_ledger()
