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
    TestManifest,
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


# ---------------------------------------------------------------------------
# Q-S1: GoalEntry 확장 (scenario / expected_output / provenance) — §5.1
# ---------------------------------------------------------------------------

def test_goal_entry_q_s1_defaults():
    """Q-S1 신규 필드는 기본값으로 하위호환."""
    g = GoalEntry(goal_id="G-1", description="d", harness_type="cli")
    assert g.scenario == []
    assert g.expected_output == ""
    assert g.provenance == "default"


def test_goal_entry_q_s1_round_trip():
    """scenario / expected_output / provenance 직렬화 round-trip."""
    g = GoalEntry(
        goal_id="G-1",
        description="STT 텍스트 출력",
        harness_type="cli",
        scenario=["python stt.py --audio test.wav", "grep '안녕하세요' output.txt"],
        expected_output="안녕하세요",
        provenance="user",
        verdict="UNVERIFIED",
    )
    restored = GoalEntry.from_dict(g.to_dict())
    assert restored == g
    assert restored.scenario == g.scenario
    assert restored.expected_output == "안녕하세요"
    assert restored.provenance == "user"


def test_goal_entry_provenance_research():
    """provenance=research round-trip."""
    g = GoalEntry(goal_id="G-2", description="연구 합성", harness_type="none",
                  provenance="research", expected_output="synthesized")
    assert GoalEntry.from_dict(g.to_dict()).provenance == "research"


def test_goal_entry_legacy_dict_missing_q_s1_fields():
    """구 직렬화(Q-S1 필드 부재)도 기본값으로 복원 — 하위호환."""
    old_data = {
        "goal_id": "G-1",
        "description": "old",
        "harness_type": "cli",
        "verdict": "UNVERIFIED",
        "cannot_verify_reason": "",
        "command": "",
    }
    g = GoalEntry.from_dict(old_data)
    assert g.scenario == []
    assert g.expected_output == ""
    assert g.provenance == "default"


def test_goal_entry_scenario_preserved_in_contract_round_trip():
    """GoalContract 내 GoalEntry의 scenario 필드도 round-trip."""
    entry = GoalEntry(
        goal_id="G-1", description="cli test", harness_type="cli",
        scenario=["step1", "step2"], expected_output="ok", provenance="user",
    )
    c = GoalContract(task_id="T-1", goals=[entry])
    restored = GoalContract.from_dict(c.to_dict())
    assert restored.goals[0].scenario == ["step1", "step2"]
    assert restored.goals[0].provenance == "user"


# ---------------------------------------------------------------------------
# Q-S1: TestManifest — §5.2
# ---------------------------------------------------------------------------

def test_test_manifest_defaults():
    m = TestManifest()
    assert m.required_tools == []
    assert m.required_env == []
    assert m.seam_requirements == []
    assert m.provenance == "default"


def test_test_manifest_round_trip():
    m = TestManifest(
        required_tools=["ffmpeg", "python"],
        required_env=["OPENAI_API_KEY"],
        seam_requirements=["--audio-file flag", "stdout transcription output"],
        provenance="research",
    )
    assert TestManifest.from_dict(m.to_dict()) == m


def test_test_manifest_legacy_dict_missing_fields():
    """구 직렬화에서 필드 부재 시 기본값 복원."""
    m = TestManifest.from_dict({})
    assert m.required_tools == []
    assert m.seam_requirements == []
    assert m.provenance == "default"


# ---------------------------------------------------------------------------
# Q-S1: GoalContract.manifest — §5.2
# ---------------------------------------------------------------------------

def test_goal_contract_manifest_none_by_default():
    c = GoalContract(task_id="T-1")
    assert c.manifest is None


def test_goal_contract_manifest_round_trip():
    m = TestManifest(
        required_tools=["ffmpeg"],
        seam_requirements=["--audio-file"],
        provenance="user",
    )
    c = GoalContract(task_id="T-1", goals=[], manifest=m)
    restored = GoalContract.from_dict(c.to_dict())
    assert restored.manifest == m
    assert restored.manifest.required_tools == ["ffmpeg"]


def test_goal_contract_manifest_none_round_trip():
    """manifest=None 직렬화 → None 복원."""
    c = GoalContract(task_id="T-2", goals=[])
    assert GoalContract.from_dict(c.to_dict()).manifest is None


def test_goal_contract_legacy_dict_missing_manifest():
    """구 직렬화(manifest 키 부재)도 None으로 복원 — 하위호환."""
    old_data = {"task_id": "T-old", "goals": []}
    c = GoalContract.from_dict(old_data)
    assert c.manifest is None


def test_goal_contract_full_round_trip_with_manifest_and_q_s1():
    """GoalContract(manifest 포함) + GoalEntry(Q-S1 필드 포함) 전체 round-trip."""
    entry = GoalEntry(
        goal_id="G-1",
        description="STT 출력 검증",
        harness_type="cli",
        scenario=["python stt.py --audio rec.wav", "cat out.txt | grep 안녕"],
        expected_output="안녕하세요",
        provenance="research",
        verdict="UNVERIFIED",
    )
    manifest = TestManifest(
        required_tools=["ffmpeg"],
        required_env=["AUDIO_DEVICE"],
        seam_requirements=["--audio-file injection flag"],
        provenance="research",
    )
    c = GoalContract(task_id="T-full", goals=[entry], manifest=manifest)
    restored = GoalContract.from_dict(c.to_dict())
    assert restored == c
    assert restored.manifest.seam_requirements == ["--audio-file injection flag"]
    assert restored.goals[0].provenance == "research"
