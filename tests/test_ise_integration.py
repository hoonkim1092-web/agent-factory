"""Phase A Step 1f — ISE 배선 복구 단위 테스트 4건.

Gap analysis NEW-M2 해소: ISE 직접 테스트 0건 상태를 4건으로 전환.

검증 대상:
1. execution_mode="ise" 분기가 ISELoop.run_mission 경로로 진입
2. StrategyLedger._hash()가 32자 SHA256 앞부분 (16자 truncation 해소)
3. StallDetector가 반복된 동일 에러에서 human_escalation 신호 발생
4. DynamicOrchestrator._should_decompose() 조건부 동작
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.ise_stall_detector import StallDetector
from core.ise_strategy_ledger import StrategyEntry, StrategyLedger


# ── Test 1: ISE 모드 배선 ─────────────────────────────────────────────────

def test_agent_launcher_routes_ise_mode_to_ise_loop():
    """execution_mode='ise' 전달 시 ISELoop.run_mission 호출 경로가 선택되는지 확인."""
    from agent_launcher import AgentFactory

    launcher = AgentFactory.__new__(AgentFactory)
    launcher.ultra = MagicMock()
    launcher.ise = MagicMock()
    launcher.ise.run_mission = MagicMock(return_value={"ok": True, "reason": "ise_ok"})
    launcher.runner = MagicMock()
    launcher.request_router = MagicMock()
    launcher.request_router.route.return_value = {"pipeline": "agent"}

    dummy_agent = {"name": "test", "skills": []}
    launcher._get_agent = MagicMock(return_value=dummy_agent)
    launcher._analyze_requirements = MagicMock(return_value={"missing_skills": []})
    launcher._ensure_single_run_todo = MagicMock()
    launcher._missing_local_skill_files = MagicMock(return_value=[])
    launcher._read_approval_policy = MagicMock(return_value={})
    launcher._ask_skill_change_approval = None
    launcher.procurer = MagicMock()

    with patch("agent_launcher.append_dashboard_run"):
        result = launcher.run(
            task_input="test task",
            role_spec="General",
            enable_build=False,
            execution_mode="ise",
        )

    launcher.ise.run_mission.assert_called_once()
    launcher.ultra.run_mission.assert_not_called()
    assert result["ok"] is True


# ── Test 2: StrategyLedger SHA256 truncation 32자 ────────────────────────

def test_strategy_ledger_hash_returns_32_chars():
    """NEW-C2 보정: SHA256 truncation이 16자 → 32자로 확장됐는지 확인."""
    hash_value = StrategyLedger._hash("some strategy description")
    assert len(hash_value) == 32
    assert all(c in "0123456789abcdef" for c in hash_value)


def test_strategy_ledger_hash_distinct_for_different_inputs():
    """해시가 입력별로 구분 가능한지 확인 (32자로 충돌 위험 완화)."""
    h1 = StrategyLedger._hash("strategy A")
    h2 = StrategyLedger._hash("strategy B")
    assert h1 != h2


# ── Test 3: StallDetector human_escalation ───────────────────────────────

def test_stall_detector_escalates_on_repeated_same_error():
    """동일 error_signature가 3회 이상 반복되면 human_escalation 또는 creativity_injection 신호."""
    ledger = StrategyLedger(run_id="test_run", original_task="task")

    for i in range(5):
        ledger.entries.append(
            StrategyEntry(
                meta_cycle=i,
                timestamp="2026-04-22T00:00:00Z",
                escalation_level=1,
                task_input_hash="abc" * 10,
                strategy_description="same retry",
                strategy_hash="same_hash",
                error_category="logic",
                error_signature="AssertionError: same",
                result_ok=False,
                result_reason="failed",
            )
        )

    detector = StallDetector()
    verdict = detector.check(ledger)
    assert verdict in ("creativity_injection", "human_escalation"), (
        f"Expected escalation signal on 5 identical failures, got '{verdict}'"
    )


# ── Test 4: DynamicOrchestrator._should_decompose ────────────────────────

def test_should_decompose_triggers_on_three_logic_failures():
    """3연속 logic 카테고리 실패 + retry_count≥3 시 _should_decompose True."""
    from core.dynamic_orchestrator import DynamicOrchestrator

    orch = DynamicOrchestrator.__new__(DynamicOrchestrator)
    orch._task_retry_count = {"task_xyz": 3}
    orch.state_board = {
        "failed_subtasks": [
            {"task_id": "task_xyz", "failure_category": "logic"},
            {"task_id": "task_xyz", "failure_category": "logic"},
            {"task_id": "task_xyz", "failure_category": "architecture"},
        ]
    }

    assert orch._should_decompose("task_xyz") is True


def test_should_decompose_rejects_transient_failures():
    """transient는 재시도로 해결 가능하므로 decompose 부적합."""
    from core.dynamic_orchestrator import DynamicOrchestrator

    orch = DynamicOrchestrator.__new__(DynamicOrchestrator)
    orch._task_retry_count = {"task_t": 3}
    orch.state_board = {
        "failed_subtasks": [
            {"task_id": "task_t", "failure_category": "transient"},
            {"task_id": "task_t", "failure_category": "transient"},
            {"task_id": "task_t", "failure_category": "transient"},
        ]
    }

    assert orch._should_decompose("task_t") is False


def test_should_decompose_below_retry_threshold():
    """retry_count<3이면 false."""
    from core.dynamic_orchestrator import DynamicOrchestrator

    orch = DynamicOrchestrator.__new__(DynamicOrchestrator)
    orch._task_retry_count = {"task_y": 2}
    orch.state_board = {"failed_subtasks": []}

    assert orch._should_decompose("task_y") is False
