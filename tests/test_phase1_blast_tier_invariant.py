"""tests/test_phase1_blast_tier_invariant.py — Phase 1: blast_tier 불변 invariant 검증.

blast_tier는 blast_radius.py + enqueue_agent_review.py:109 max-merge만 결정한다.
_apply_test_gap_verdict()는 blast_tier를 수정해서는 안 된다 (downgrade_blast_tier 호출 제거).

Layer 1 (unit)        : _apply_test_gap_verdict FAIL 후에도 blast_tier 불변
Layer 2 (integration) : test-gap FAIL 기록 후 gate가 BLOCK하는지 확인
Layer 3 (integration) : fail→pass 사이클 전체에서 blast_tier 불변
Layer 4 (regression)  : 기존 42개 테스트는 별도 파일에서 유지 (여기선 key invariant만)
Layer 5 (dry-run)     : fixture 기반 check_pending_review 동작 검증
Layer 6 (state matrix): is_gate_blocked() 4가지 상태 조합
"""
from __future__ import annotations

import importlib
import json
import os
import time

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _runner():
    import scripts.hook_runner as m
    importlib.reload(m)
    return m


def _write_queue(tmp_path, state: dict) -> None:
    q = tmp_path / ".af_review_queue"
    q.mkdir(exist_ok=True)
    (q / "pending_agent_review.json").write_text(
        json.dumps(state), encoding="utf-8"
    )


def _read_queue(tmp_path) -> dict:
    return json.loads(
        (tmp_path / ".af_review_queue" / "pending_agent_review.json").read_text()
    )


# ═════════════════════════════════════════════════════════════════════════════
# Layer 1 — Unit: _apply_test_gap_verdict는 blast_tier를 변경하지 않는다
# ═════════════════════════════════════════════════════════════════════════════

def test_layer1_blast_tier_unchanged_on_test_gap_fail(monkeypatch, tmp_path):
    """test-gap FAIL 시 _apply_test_gap_verdict()가 blast_tier를 수정하지 않는다.

    blast_tier는 blast_radius.py + enqueue의 max-merge만 결정 — 이 함수의 책임 아님.
    """
    m = _runner()

    _write_queue(tmp_path, {"files": ["core/foo.py"], "blast_tier": 3, "reviews": {}})

    import scripts.test_gap_analyzer as tga
    monkeypatch.setattr(tga, "changed_files_from_pending", lambda ws: ["core/foo.py"])
    monkeypatch.setattr(tga, "changed_files_from_git", lambda ws: [])
    monkeypatch.setattr(tga, "git_diff", lambda ws, changed: "diff +subprocess.run(x)")

    def _fake_analyze(*, workspace, changed_files, diff_text):
        return tga.TestGapReport(
            verdict="FAIL",
            gaps=[tga.TestGap(
                risk_id="test_gap_subprocess",
                severity="FAIL",
                changed_file="core/foo.py",
                reason="subprocess usage",
                expected_test_evidence="add test",
            )],
        )

    monkeypatch.setattr(tga, "analyze_diff", _fake_analyze)
    monkeypatch.setattr(m, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))

    result = m._apply_test_gap_verdict(str(tmp_path), "pass")
    assert result == "fail"  # verdict is forced fail

    state = _read_queue(tmp_path)
    assert state["blast_tier"] == 3, (
        f"blast_tier must stay 3 (was: {state['blast_tier']}). "
        "downgrade_blast_tier() must not be called from _apply_test_gap_verdict()."
    )


# ═════════════════════════════════════════════════════════════════════════════
# Layer 2 — Integration: test-gap FAIL → gate BLOCK (blast_tier 불변이어도 차단)
# ═════════════════════════════════════════════════════════════════════════════

def test_layer2_gate_blocks_after_test_gap_fail(tmp_path):
    """test-gap FAIL verdict가 reviews에 기록되면 blast_tier=3이어도 gate가 BLOCK한다.

    blast_tier=3 → required_tiers=[1,2,3]. af-test-runner(T1) verdict=fail → verdict-block.
    """
    from scripts.review_gate import is_gate_blocked, record_review_done

    completed = time.time() - 5
    _write_queue(tmp_path, {
        "files": ["core/foo.py"],
        "blast_tier": 3,
        "reviews": {},
        "created_at": completed - 10,
        "updated_at": completed - 1,
    })

    record_review_done(str(tmp_path), "af-test-runner", 1, "fail", ["core/foo.py"])

    blocked, reason = is_gate_blocked(str(tmp_path))
    assert blocked, f"gate must BLOCK when T1 verdict=fail, got reason={reason}"
    assert "verdict" in reason or "missing" in reason, f"unexpected reason: {reason}"


# ═════════════════════════════════════════════════════════════════════════════
# Layer 3 — Integration: fail→pass 사이클 전체에서 blast_tier 불변
# ═════════════════════════════════════════════════════════════════════════════

def test_layer3_blast_tier_preserved_through_full_cycle(monkeypatch, tmp_path):
    """blast_tier=3 상태에서 test-gap FAIL 후 PASS 복구까지 blast_tier가 3으로 유지된다."""
    m = _runner()

    _write_queue(tmp_path, {"files": ["core/foo.py"], "blast_tier": 3, "reviews": {}})

    import scripts.test_gap_analyzer as tga
    monkeypatch.setattr(tga, "changed_files_from_pending", lambda ws: ["core/foo.py"])
    monkeypatch.setattr(tga, "changed_files_from_git", lambda ws: [])
    monkeypatch.setattr(tga, "git_diff", lambda ws, changed: "diff +subprocess.run(x)")
    monkeypatch.setattr(m, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))

    # Step 1: FAIL
    call_count = {"n": 0}

    def _fail_then_pass(*, workspace, changed_files, diff_text):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return tga.TestGapReport(
                verdict="FAIL",
                gaps=[tga.TestGap(
                    risk_id="r1", severity="FAIL",
                    changed_file="core/foo.py",
                    reason="subprocess", expected_test_evidence="add",
                )],
            )
        return tga.TestGapReport(verdict="PASS", gaps=[])

    monkeypatch.setattr(tga, "analyze_diff", _fail_then_pass)

    result_fail = m._apply_test_gap_verdict(str(tmp_path), "pass")
    assert result_fail == "fail"
    assert _read_queue(tmp_path)["blast_tier"] == 3, "blast_tier must stay 3 after FAIL"

    # Step 2: PASS (recovery)
    result_pass = m._apply_test_gap_verdict(str(tmp_path), "pass")
    assert result_pass == "pass"
    assert _read_queue(tmp_path)["blast_tier"] == 3, "blast_tier must stay 3 after PASS"


# ═════════════════════════════════════════════════════════════════════════════
# Layer 5 — Dry-run: fixture 기반 check_pending_review 동작
# ═════════════════════════════════════════════════════════════════════════════

def test_layer5_gate_blocked_fixture_blast_tier3_no_reviews(tmp_path):
    """blast_tier=3, reviews={} 상태의 fixture → gate BLOCK (missing-tier-1)."""
    from scripts.review_gate import is_gate_blocked

    _write_queue(tmp_path, {
        "files": ["core/foo.py"],
        "blast_tier": 3,
        "reviews": {},
        "created_at": time.time() - 60,
        "updated_at": time.time() - 1,
    })

    blocked, reason = is_gate_blocked(str(tmp_path))
    assert blocked
    assert reason == "missing-tier-1"


def test_layer5_gate_pass_fixture_blast_tier3_all_reviews(tmp_path):
    """blast_tier=3, T1+T2+T3 모두 pass → gate PASS."""
    from scripts.review_gate import is_gate_blocked, record_review_done

    completed = time.time() - 10
    _write_queue(tmp_path, {
        "files": ["core/foo.py"],
        "blast_tier": 3,
        "reviews": {},
        "created_at": completed - 60,
        "updated_at": completed - 5,
    })

    for agent, tier in [("af-test-runner", 1), ("af-critic", 2), ("af-cross-review", 3)]:
        record_review_done(str(tmp_path), agent, tier, "pass", ["core/foo.py"])

    blocked, reason = is_gate_blocked(str(tmp_path))
    assert not blocked, f"expected PASS, got BLOCK reason={reason}"


# ═════════════════════════════════════════════════════════════════════════════
# Layer 6 — State matrix: is_gate_blocked() 4가지 시나리오 parametrize
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("scenario,expect_blocked,expect_reason_contains", [
    (
        "blast_tier3_all_pass",
        False,
        "all-tiers-passed",
    ),
    (
        "blast_tier3_t1_fail",
        True,
        "verdict",
    ),
    (
        "blast_tier1_t1_pass",
        False,
        "all-tiers-passed",
    ),
    (
        "blast_tier3_no_reviews",
        True,
        "missing",
    ),
])
def test_layer6_state_matrix(tmp_path, scenario, expect_blocked, expect_reason_contains):
    """is_gate_blocked() 4가지 상태 조합 — Phase 1 invariant 검증."""
    from scripts.review_gate import is_gate_blocked, record_review_done

    completed = time.time() - 10

    if scenario == "blast_tier3_all_pass":
        _write_queue(tmp_path, {
            "files": ["core/foo.py"], "blast_tier": 3, "reviews": {},
            "created_at": completed - 60, "updated_at": completed - 5,
        })
        for agent, tier in [("af-test-runner", 1), ("af-critic", 2), ("af-cross-review", 3)]:
            record_review_done(str(tmp_path), agent, tier, "pass", ["core/foo.py"])

    elif scenario == "blast_tier3_t1_fail":
        # blast_tier=3, T1+T2+T3 모두 완료하되 T1 verdict=fail → verdict-block
        _write_queue(tmp_path, {
            "files": ["core/foo.py"], "blast_tier": 3, "reviews": {},
            "created_at": completed - 60, "updated_at": completed - 5,
        })
        record_review_done(str(tmp_path), "af-test-runner", 1, "fail", ["core/foo.py"])
        record_review_done(str(tmp_path), "af-critic", 2, "pass", ["core/foo.py"])
        record_review_done(str(tmp_path), "af-cross-review", 3, "pass", ["core/foo.py"])

    elif scenario == "blast_tier1_t1_pass":
        _write_queue(tmp_path, {
            "files": ["core/foo.py"], "blast_tier": 1, "reviews": {},
            "created_at": completed - 60, "updated_at": completed - 5,
        })
        record_review_done(str(tmp_path), "af-test-runner", 1, "pass", ["core/foo.py"])

    elif scenario == "blast_tier3_no_reviews":
        _write_queue(tmp_path, {
            "files": ["core/foo.py"], "blast_tier": 3, "reviews": {},
            "created_at": completed - 60, "updated_at": completed - 1,
        })

    blocked, reason = is_gate_blocked(str(tmp_path))
    assert blocked == expect_blocked, f"[{scenario}] blocked={blocked}, reason={reason}"
    assert expect_reason_contains in reason, (
        f"[{scenario}] expected '{expect_reason_contains}' in reason, got '{reason}'"
    )
