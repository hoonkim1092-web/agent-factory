"""S1 invariants for the completion contract data layer.

Design: docs/2026-06-17-af-completion-contract-goal-verification-design.md
        §4 (구조체), §8 S1 (직렬화 명세), §9 INV-A.

S1 범위는 구조체 + 직렬화뿐 — 하니스 실행(ExecutionHarness)은 S2.
여기서는 dataclass 계약 / is_done() / has_failures() / round-trip만 검증한다.
"""
from __future__ import annotations

from core.completion_contract import (
    GoalContract,
    GoalEntry,
    GoalEvidence,
    HarnessResult,
)
from core.dogfood import DogfoodPhase, DogfoodState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(verdict: str, gid: str = "G-1", harness: str = "cli") -> GoalEntry:
    return GoalEntry(
        goal_id=gid,
        description=f"goal {gid}",
        harness_type=harness,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# is_done() — INV-A
# ---------------------------------------------------------------------------

def test_empty_contract_is_not_done():
    """골이 하나도 없으면 done 아님 (빈 계약 통과 금지)."""
    assert GoalContract(task_id="T-1").is_done() is False


def test_all_verified_is_done():
    c = GoalContract(task_id="T-1", goals=[_entry("VERIFIED"), _entry("VERIFIED", "G-2")])
    assert c.is_done() is True


def test_verified_plus_cannot_verify_is_done():
    """CANNOT_VERIFY는 실패 아님 → done 허용 (INV-G)."""
    c = GoalContract(task_id="T-1", goals=[_entry("VERIFIED"), _entry("CANNOT_VERIFY", "G-2")])
    assert c.is_done() is True


def test_unverified_blocks_done():
    c = GoalContract(task_id="T-1", goals=[_entry("VERIFIED"), _entry("UNVERIFIED", "G-2")])
    assert c.is_done() is False


def test_failed_blocks_done():
    c = GoalContract(task_id="T-1", goals=[_entry("VERIFIED"), _entry("FAILED", "G-2")])
    assert c.is_done() is False


# ---------------------------------------------------------------------------
# has_failures()
# ---------------------------------------------------------------------------

def test_has_failures_true_only_for_failed():
    assert GoalContract(task_id="T", goals=[_entry("FAILED")]).has_failures() is True
    assert GoalContract(task_id="T", goals=[_entry("UNVERIFIED")]).has_failures() is False
    assert GoalContract(task_id="T", goals=[_entry("CANNOT_VERIFY")]).has_failures() is False
    assert GoalContract(task_id="T", goals=[_entry("VERIFIED")]).has_failures() is False


def test_has_failures_empty_contract():
    assert GoalContract(task_id="T").has_failures() is False


# ---------------------------------------------------------------------------
# Defaults / dataclass contract
# ---------------------------------------------------------------------------

def test_goal_entry_defaults():
    g = GoalEntry(goal_id="G-1", description="d", harness_type="none")
    assert g.evidence is None
    assert g.verdict == "UNVERIFIED"
    assert g.cannot_verify_reason == ""


def test_harness_result_is_plain_struct():
    r = HarnessResult(ok=True, evidence_type="exit_code", evidence_value="0", command_run="x --help")
    assert r.ok is True
    assert r.evidence_value == "0"


# ---------------------------------------------------------------------------
# Serialization round-trip — §8 S1 (from_dict(to_dict(x)) == x)
# ---------------------------------------------------------------------------

def test_evidence_round_trip():
    ev = GoalEvidence(evidence_type="exit_code", evidence_value="0", command_run="x --help")
    assert GoalEvidence.from_dict(ev.to_dict()) == ev


def test_entry_round_trip_with_evidence():
    g = GoalEntry(
        goal_id="G-1",
        description="cli runs",
        harness_type="cli",
        evidence=GoalEvidence("exit_code", "0", "x --help"),
        verdict="VERIFIED",
    )
    assert GoalEntry.from_dict(g.to_dict()) == g


def test_entry_round_trip_without_evidence():
    g = GoalEntry(goal_id="G-2", description="wasapi", harness_type="gui",
                  verdict="CANNOT_VERIFY", cannot_verify_reason="needs hardware")
    restored = GoalEntry.from_dict(g.to_dict())
    assert restored == g
    assert restored.evidence is None


def test_contract_round_trip_nested():
    c = GoalContract(
        task_id="T-123",
        goals=[
            GoalEntry("G-1", "cli", "cli", GoalEvidence("exit_code", "0", "x"), "VERIFIED"),
            GoalEntry("G-2", "wasapi", "gui", None, "CANNOT_VERIFY", "needs hardware"),
            GoalEntry("G-3", "unknown", "none", None, "UNVERIFIED"),
        ],
    )
    assert GoalContract.from_dict(c.to_dict()) == c


def test_empty_contract_round_trip():
    c = GoalContract(task_id="T-0")
    assert GoalContract.from_dict(c.to_dict()) == c


# ---------------------------------------------------------------------------
# DogfoodState persist channel — §8 S1
# ---------------------------------------------------------------------------

def _mk_state(contract: GoalContract | None) -> DogfoodState:
    return DogfoodState(
        run_id="r1",
        task="t",
        phase=DogfoodPhase.IMPLEMENT,
        source_workspace="/src",
        runtime_workspace="/rt",
        goal_contract=contract,
    )


def test_dogfood_state_round_trip_with_contract():
    contract = GoalContract(
        task_id="T-1",
        goals=[GoalEntry("G-1", "cli", "cli", GoalEvidence("exit_code", "0", "x"), "VERIFIED")],
    )
    st = _mk_state(contract)
    restored = DogfoodState.from_dict(st.to_dict())
    assert restored.goal_contract == contract


def test_dogfood_state_round_trip_none_contract():
    st = _mk_state(None)
    assert st.to_dict()["goal_contract"] is None
    assert DogfoodState.from_dict(st.to_dict()).goal_contract is None


def test_dogfood_state_legacy_dict_without_contract_key():
    """기존 직렬화(필드 부재)도 깨지지 않고 None으로 복원."""
    st = _mk_state(None)
    data = st.to_dict()
    del data["goal_contract"]
    assert DogfoodState.from_dict(data).goal_contract is None
