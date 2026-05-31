"""tests/test_review_gate.py — review_gate.py 유닛 테스트 10종.

§9.3 DoD 요구사항:
  (a) 빈 큐 → PASS
  (b) tier 1 누락 → BLOCK("missing-tier-1")
  (c) tier 2 누락 → BLOCK("missing-tier-2")
  (d) tier 3 누락 → BLOCK("missing-tier-3")
  (e) 재편집 → BLOCK("stale-review")
  (f) 신규 파일 추가 → BLOCK("new-files-added")
  (g) 전부 완료 → PASS
  (h) verdict=block + AF_GATE_ALLOW_VERDICT_BLOCK unset → BLOCK
  (i) verdict=block + AF_GATE_ALLOW_VERDICT_BLOCK=1 → PASS
  (j) AF_SKIP_REVIEW_GATE=1 → PASS + 로그
"""
from __future__ import annotations

import json
import os
import time

import pytest

from scripts.review_gate import (
    _AGENT_TIER,
    _is_always_tier3,
    _load_state,
    _required_tiers_for,
    _save_state,
    _telemetry_skip_enacted,
    clear_committed_files,
    is_gate_blocked,
    record_review_done,
)


# ── 픽스처 ───────────────────────────────────────────────────────────────────

@pytest.fixture
def ws(tmp_path):
    """임시 워크스페이스 — .af_review_queue/ 하위에 pending 파일 없이 시작."""
    return str(tmp_path)


def _write_state(ws: str, state: dict) -> None:
    queue = os.path.join(ws, ".af_review_queue")
    os.makedirs(queue, exist_ok=True)
    with open(os.path.join(queue, "pending_agent_review.json"), "w") as f:
        json.dump(state, f)


def _base_state(py_files: list[str], updated_at: float | None = None) -> dict:
    now = updated_at if updated_at is not None else time.time()
    return {
        "files": py_files,
        "created_at": now - 10,
        "updated_at": now,
    }


def _full_reviews(
    files: list[str],
    completed_at: float,
    tier3_verdict: str = "pass",
) -> dict:
    return {
        "af-test-runner": {
            "tier": 1,
            "verdict": "pass",
            "files_snapshot": list(files),
            "completed_at": completed_at,
        },
        "af-critic": {
            "tier": 2,
            "verdict": "pass",
            "files_snapshot": list(files),
            "completed_at": completed_at + 1,
        },
        "af-cross-review": {
            "tier": 3,
            "verdict": tier3_verdict,
            "files_snapshot": list(files),
            "completed_at": completed_at + 2,
        },
    }


# ── 테스트 ────────────────────────────────────────────────────────────────────

def test_a_empty_queue_pass(ws):
    """(a) 큐 파일 없음 → PASS(no-queue)."""
    blocked, reason = is_gate_blocked(ws)
    assert not blocked
    assert reason == "no-queue"


def test_b_missing_tier1_block(ws):
    """(b) tier 1 누락 → BLOCK(missing-tier-1)."""
    state = _base_state(["core/foo.py"])
    state["reviews"] = {}
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason == "missing-tier-1"


def test_c_missing_tier2_block(ws):
    """(c) tier 2 누락 → BLOCK(missing-tier-2)."""
    files = ["core/foo.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["reviews"] = {
        "af-test-runner": {
            "tier": 1, "verdict": "pass",
            "files_snapshot": files, "completed_at": completed,
        }
    }
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason == "missing-tier-2"


def test_d_missing_tier3_block(ws):
    """(d) tier 3 누락 → BLOCK(missing-tier-3)."""
    files = ["core/foo.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["reviews"] = {
        "af-test-runner": {
            "tier": 1, "verdict": "pass",
            "files_snapshot": files, "completed_at": completed,
        },
        "af-critic": {
            "tier": 2, "verdict": "pass",
            "files_snapshot": files, "completed_at": completed + 1,
        },
    }
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason == "missing-tier-3"


def test_e_stale_review_block(ws):
    """(e) 재편집(updated_at > 어느 리뷰 completed_at) → BLOCK(stale-review)."""
    files = ["core/foo.py"]
    completed = time.time() - 10
    # updated_at이 reviews 완료 이후 → stale
    state = _base_state(files, updated_at=time.time())
    state["reviews"] = _full_reviews(files, completed)
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason == "stale-review"


def test_f_new_files_added_block(ws):
    """(f) 신규 파일 추가(tier-3 snapshot에 없음) → BLOCK(new-files-added)."""
    files_at_review = ["core/old.py"]
    completed = time.time() - 5
    # 현재 files에 new.py가 추가됨
    state = _base_state(["core/old.py", "core/new.py"], updated_at=completed - 1)
    state["reviews"] = _full_reviews(files_at_review, completed)
    # tier-3 snapshot은 old.py만 — new.py 없음
    state["reviews"]["af-cross-review"]["files_snapshot"] = list(files_at_review)
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason == "new-files-added"


def test_g_all_tiers_pass(ws):
    """(g) 3 tier 모두 완료 + stale 없음 + 신규 파일 없음 → PASS."""
    files = ["core/bar.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["reviews"] = _full_reviews(files, completed)
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert not blocked
    assert reason == "all-tiers-passed"


def test_g2_t3_skip_requires_only_tier1_and_tier2(ws):
    """Deterministic cosmetic classifier may skip only Tier 3."""
    files = ["core/cosmetic.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["blast_tier"] = 2
    state["t3_required"] = False
    state["t3_decision"] = {
        "decision": "skip_t3",
        "reason": "cosmetic-only-python-ast",
        "classifier_version": "t3-deterministic-v1",
        "files": files,
        "diff_summary": {"added": 1, "deleted": 1},
    }
    state["reviews"] = {
        "af-test-runner": {
            "tier": 1,
            "verdict": "pass",
            "files_snapshot": files,
            "completed_at": completed,
        },
        "af-critic": {
            "tier": 2,
            "verdict": "pass",
            "t3_required": "no",
            "files_snapshot": files,
            "completed_at": completed + 1,
        },
    }
    _write_state(ws, state)

    blocked, reason = is_gate_blocked(ws)

    assert not blocked
    assert reason == "all-tiers-passed"


def test_g2b_t3_skip_requires_critic_no_advisory(ws):
    """If af-critic says yes/unknown, deterministic candidate still requires Tier 3."""
    files = ["core/cosmetic.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["blast_tier"] = 2
    state["t3_required"] = False
    state["t3_decision"] = {
        "decision": "skip_t3",
        "reason": "cosmetic-only-python-ast",
        "classifier_version": "t3-deterministic-v1",
        "files": files,
        "diff_summary": {"added": 1, "deleted": 1},
    }
    state["reviews"] = {
        "af-test-runner": {
            "tier": 1,
            "verdict": "pass",
            "files_snapshot": files,
            "completed_at": completed,
        },
        "af-critic": {
            "tier": 2,
            "verdict": "pass",
            "t3_required": "unknown",
            "files_snapshot": files,
            "completed_at": completed + 1,
        },
    }
    _write_state(ws, state)

    blocked, reason = is_gate_blocked(ws)

    assert blocked
    assert reason == "missing-tier-3"


def test_g2c_critic_t3_escalation_rearms_pending_prompt(ws):
    """When T2 escalates a deterministic skip candidate, pending hook must re-fire."""
    files = ["core/cosmetic.py"]
    now = time.time() - 100
    _write_state(ws, {
        "files": files,
        "created_at": now - 10,
        "updated_at": now,
        "fired_at": now + 1,
        "blast_tier": 2,
        "t3_required": False,
        "t3_decision": {
            "decision": "skip_t3",
            "reason": "cosmetic-only-python-ast",
            "classifier_version": "t3-deterministic-v1",
            "files": files,
            "diff_summary": {"added": 1, "deleted": 1},
        },
        "reviews": {},
    })

    record_review_done(ws, "af-test-runner", 1, "pass", files)
    record_review_done(ws, "af-critic", 2, "pass", files, t3_required="unknown")

    state = _load_state(ws)
    assert "fired_at" not in state
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason == "missing-tier-3"


def test_g3_t3_skip_ignored_for_blast_tier3(ws):
    """Hard-guard/Tier 3 queues cannot skip Tier 3 even with stale t3_required=false."""
    files = ["scripts/t3_classifier.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["blast_tier"] = 3
    state["t3_required"] = False
    state["t3_decision"] = {
        "decision": "skip_t3",
        "reason": "cosmetic-only-python-ast",
        "classifier_version": "t3-deterministic-v1",
        "files": files,
        "diff_summary": {"added": 1, "deleted": 1},
    }
    state["reviews"] = {
        "af-test-runner": {
            "tier": 1,
            "verdict": "pass",
            "files_snapshot": files,
            "completed_at": completed,
        },
        "af-critic": {
            "tier": 2,
            "verdict": "pass",
            "files_snapshot": files,
            "completed_at": completed + 1,
        },
    }
    _write_state(ws, state)

    blocked, reason = is_gate_blocked(ws)

    assert blocked
    assert reason == "missing-tier-3"


def test_g4_t3_skip_requires_matching_decision_files(ws):
    """Stale/mismatched classifier state is fail-closed at gate time."""
    files = ["core/current.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["blast_tier"] = 2
    state["t3_required"] = False
    state["t3_decision"] = {
        "decision": "skip_t3",
        "reason": "cosmetic-only-python-ast",
        "classifier_version": "t3-deterministic-v1",
        "files": ["core/old.py"],
        "diff_summary": {"added": 1, "deleted": 1},
    }
    state["reviews"] = {
        "af-test-runner": {
            "tier": 1,
            "verdict": "pass",
            "files_snapshot": files,
            "completed_at": completed,
        },
        "af-critic": {
            "tier": 2,
            "verdict": "pass",
            "files_snapshot": files,
            "completed_at": completed + 1,
        },
    }
    _write_state(ws, state)

    blocked, reason = is_gate_blocked(ws)

    assert blocked
    assert reason == "missing-tier-3"


def test_h_verdict_block_without_env(ws, monkeypatch):
    """(h) verdict=block + AF_GATE_ALLOW_VERDICT_BLOCK 미설정 → BLOCK(verdict-block:...)."""
    monkeypatch.delenv("AF_GATE_ALLOW_VERDICT_BLOCK", raising=False)
    files = ["core/baz.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["reviews"] = _full_reviews(files, completed, tier3_verdict="block")
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason.startswith("verdict-block:")


def test_h2_verdict_fail_without_env(ws, monkeypatch):
    """(h2) verdict=fail도 BLOCK과 동등하게 게이트를 막음."""
    monkeypatch.delenv("AF_GATE_ALLOW_VERDICT_BLOCK", raising=False)
    files = ["core/baz.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["reviews"] = _full_reviews(files, completed, tier3_verdict="fail")
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason.startswith("verdict-block:")


def test_i_verdict_block_with_env(ws, monkeypatch):
    """(i) verdict=block + AF_GATE_ALLOW_VERDICT_BLOCK=1 → PASS."""
    monkeypatch.setenv("AF_GATE_ALLOW_VERDICT_BLOCK", "1")
    files = ["core/baz.py"]
    completed = time.time() - 5
    state = _base_state(files, updated_at=completed - 1)
    state["reviews"] = _full_reviews(files, completed, tier3_verdict="block")
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert not blocked
    assert reason == "all-tiers-passed"


def test_j_skip_gate_env(ws, monkeypatch):
    """(j) AF_SKIP_REVIEW_GATE=1 → PASS + hook_events.log 기록."""
    monkeypatch.setenv("AF_SKIP_REVIEW_GATE", "1")
    # 심각한 BLOCK 상태라도 env bypass
    state = _base_state(["core/x.py"])
    state["reviews"] = {}
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert not blocked
    assert reason == "gate-skipped-env"
    log_path = os.path.join(ws, ".af_review_queue", "hook_events.log")
    assert os.path.exists(log_path)
    assert "gate-skipped-env" in open(log_path).read()


# ── 보조 기능 테스트 ──────────────────────────────────────────────────────────

def test_record_and_clear(ws):
    """record_review_done + clear_committed_files 연동."""
    _write_state(ws, {"files": ["core/a.py", "core/b.py"], "created_at": time.time(), "updated_at": time.time() - 1})

    record_review_done(ws, "af-test-runner", 1, "pass", ["core/a.py", "core/b.py"])
    state = _load_state(ws)
    assert "af-test-runner" in state["reviews"]
    assert state["reviews"]["af-test-runner"]["verdict"] == "pass"

    clear_committed_files(ws, ["core/a.py"])
    state = _load_state(ws)
    assert "core/a.py" not in state["files"]
    assert "core/b.py" in state["files"]

    clear_committed_files(ws, ["core/b.py"])
    state = _load_state(ws)
    assert state["files"] == []
    assert state.get("reviews") == {}


def test_no_py_files_pass(ws):
    """files에 .py가 없으면 PASS."""
    _write_state(ws, {"files": ["README.md", "docs/x.md"], "updated_at": time.time()})
    blocked, reason = is_gate_blocked(ws)
    assert not blocked
    assert reason == "no-py-files"


def test_staged_py_not_queued_no_queue(ws):
    """큐 없음 + staged core/*.py → BLOCK(staged-py-not-queued). git add 경로 누락 버그 대응."""
    blocked, reason = is_gate_blocked(ws, staged_py=["core/interview.py"])
    assert blocked
    assert reason == "staged-py-not-queued"


def test_staged_py_not_queued_empty_py_in_queue(ws):
    """큐에 .py 없음 + staged core/*.py → BLOCK(staged-py-not-queued)."""
    _write_state(ws, {"files": ["README.md"], "updated_at": time.time()})
    blocked, reason = is_gate_blocked(ws, staged_py=["core/foo.py"])
    assert blocked
    assert reason == "staged-py-not-queued"


def test_staged_non_review_py_no_queue_passes(ws):
    """큐 없음 + staged_py=None (비대상 파일은 _staged_review_py_files가 필터 → 빈 리스트) → PASS(no-queue)."""
    # tests/*.py는 리뷰 비대상 → _staged_review_py_files()가 걸러내 [] → None 전달
    blocked, reason = is_gate_blocked(ws, staged_py=None)
    assert not blocked
    assert reason == "no-queue"


def test_staged_py_not_in_snap_blocks_even_if_queue_fully_reviewed(ws):
    """큐에 .py 있고 3-tier 리뷰 PASS 완료 + 새 staged core/*.py가 snap에 없음 → BLOCK(staged-py-not-queued).

    git add로 추가한 신규 파일이 큐에 없는 상태에서 all-tiers-passed로 우회되는 버그 차단.
    """
    now = time.time()
    reviewed_file = "core/old.py"
    _write_state(ws, {
        "files": [reviewed_file],
        "created_at": now - 100,
        "updated_at": now - 50,
        "reviews": _full_reviews([reviewed_file], now - 40),
        "blast_tier": 3,
    })
    # core/new.py는 staged됐지만 큐에 없고 snap에도 없음
    blocked, reason = is_gate_blocked(ws, staged_py=["core/new.py"])
    assert blocked
    assert reason == "staged-py-not-queued"


def test_staged_skills_skill_py_blocks(ws):
    """큐 없음 + skills/foo/skill.py staged → BLOCK(staged-py-not-queued). skills/ 패턴 동형 확인."""
    blocked, reason = is_gate_blocked(ws, staged_py=["skills/foo/skill.py"])
    assert blocked
    assert reason == "staged-py-not-queued"


def test_staged_skills_nested_not_review_target(ws):
    """skills/foo/bar/skill.py는 1-depth가 아니므로 리뷰 비대상 → PASS(no-queue)."""
    # _STAGED_SKILLS_RE = r"^skills/[^/]+/skill\.py$" → 2-depth 이상 미매칭
    blocked, reason = is_gate_blocked(ws, staged_py=None)  # 비대상은 staged_py에 포함 안 됨
    assert not blocked
    assert reason == "no-queue"


# ── Round 2 (2026-05-15): stale 누적 시나리오 ────────────────────────────────

def test_clear_stale_reset_when_round_passed_and_idle(ws):
    """이전 라운드 PASS 종료 + idle 상태에서 committed_set 미포함 stale .py 잔존
    → 큐 통째 reset. 새 .py 작업이 stale 큐에 막히지 않음.
    """
    now = time.time()
    _write_state(ws, {
        "files": ["core/stale_a.py", "core/stale_b.py"],
        "created_at": now - 100,
        "updated_at": now - 50,
        "reviews": _full_reviews(["core/stale_a.py", "core/stale_b.py"], now - 40),
        "round_count": 3,
        "last_round_summary": {
            "round": 3,
            "verdicts": {"af-test-runner": "pass", "af-critic": "pass", "af-cross-review": "pass"},
            "has_block": False,
            "completed_at": now - 30,
            "round_started_at": now - 60,
        },
        "round_started_at": None,
        "blast_tier": 3,
    })

    clear_committed_files(ws, ["docs/unrelated.md"])

    state = _load_state(ws)
    assert state["files"] == []
    assert state.get("reviews") == {}
    assert "round_count" not in state
    assert "last_round_summary" not in state
    assert "blast_tier" not in state


def test_clear_no_stale_reset_when_round_in_flight(ws):
    """round_started_at != None (= 새 라운드 진행 중) 이면 stale reset 차단.
    in-flight 작업이 commit 직후 잘못 reset되어 enqueue 되돌리는 일 방지.
    """
    now = time.time()
    _write_state(ws, {
        "files": ["core/in_flight.py"],
        "created_at": now - 100,
        "updated_at": now - 5,
        "reviews": _full_reviews(["core/old_pass.py"], now - 40),
        "round_count": 3,
        "last_round_summary": {
            "round": 3,
            "verdicts": {"af-test-runner": "pass", "af-critic": "pass", "af-cross-review": "pass"},
            "has_block": False,
            "completed_at": now - 30,
            "round_started_at": now - 60,
        },
        "round_started_at": now - 3,
        "blast_tier": 3,
    })

    clear_committed_files(ws, ["core/old_pass.py"])

    state = _load_state(ws)
    assert state["files"] == ["core/in_flight.py"]
    assert state.get("round_count") == 3
    assert state.get("round_started_at") is not None


def test_clear_stale_reset_at_round_count_one(ws):
    """round_count=1 (첫 라운드 직후 idle)도 stale reset 트리거 — boundary."""
    now = time.time()
    _write_state(ws, {
        "files": ["core/stale_first_round.py"],
        "created_at": now - 100,
        "updated_at": now - 50,
        "reviews": _full_reviews(["core/stale_first_round.py"], now - 40),
        "round_count": 1,
        "last_round_summary": {
            "round": 1,
            "verdicts": {"af-test-runner": "pass", "af-critic": "pass", "af-cross-review": "pass"},
            "has_block": False,
            "completed_at": now - 30,
            "round_started_at": now - 60,
        },
        "round_started_at": None,
        "blast_tier": 3,
    })

    clear_committed_files(ws, ["docs/x.md"])

    state = _load_state(ws)
    assert state["files"] == []
    assert "round_count" not in state


def test_clear_no_stale_reset_when_round_count_corrupt(ws):
    """round_count=null/None 등 corrupt 값에서 TypeError 없이 안전 통과 — null-safe."""
    now = time.time()
    _write_state(ws, {
        "files": ["core/corrupt.py"],
        "created_at": now - 100,
        "updated_at": now - 50,
        "reviews": _full_reviews(["core/corrupt.py"], now - 40),
        "round_count": None,
        "last_round_summary": {
            "round": 1,
            "verdicts": {"af-test-runner": "pass", "af-critic": "pass", "af-cross-review": "pass"},
            "has_block": False,
            "completed_at": now - 30,
            "round_started_at": now - 60,
        },
        "round_started_at": None,
        "blast_tier": 3,
    })

    clear_committed_files(ws, ["docs/y.md"])

    state = _load_state(ws)
    assert state["files"] == ["core/corrupt.py"]


def test_clear_no_stale_reset_when_last_round_had_block(ws):
    """has_block=True (BLOCK 라운드)면 stale reset 차단. 사용자가 fix 작업 중일 수
    있으므로 자동 reset이 작업 흐름을 끊지 않도록.
    """
    now = time.time()
    _write_state(ws, {
        "files": ["core/block_residue.py"],
        "created_at": now - 100,
        "updated_at": now - 50,
        "reviews": _full_reviews(["core/block_residue.py"], now - 40, tier3_verdict="block"),
        "round_count": 2,
        "last_round_summary": {
            "round": 2,
            "verdicts": {"af-test-runner": "pass", "af-critic": "pass", "af-cross-review": "block"},
            "has_block": True,
            "completed_at": now - 30,
            "round_started_at": now - 60,
        },
        "round_started_at": None,
        "blast_tier": 3,
    })

    clear_committed_files(ws, ["docs/other.md"])

    state = _load_state(ws)
    assert state["files"] == ["core/block_residue.py"]
    assert state.get("round_count") == 2


# ── Phase 2 v7 §7.2: `_extract_verdict_from_content` collision 회귀 (C1~C7) ─

from scripts.review_gate import (  # noqa: E402
    _extract_t3_required_from_content,
    _extract_verdict_from_content,
)


def test_c1_fence_inner_single_verdict_line():
    """C1: fence 내부 단일 `## Tier 3 판정: WARN` → verdict=warn."""
    content = (
        "# header\n"
        "본문\n"
        "<!-- final-verdict-start -->\n"
        "## Tier 3 판정: WARN\n"
        "사유: advisory only\n"
        "<!-- final-verdict-end -->\n"
    )
    assert _extract_verdict_from_content(content) == "warn"


def test_c2_body_quote_outside_fence_uses_fence_only():
    """C2: 본문 인용 + fence 내부 verdict 라인 → fence 내부만 인식 (G7 차단)."""
    content = (
        "이전 라운드 판정: BLOCK 이라고 알려져 있다 (인용)\n"
        "<!-- final-verdict-start -->\n"
        "## Tier 3 판정: PASS\n"
        "사유: 발견 없음\n"
        "<!-- final-verdict-end -->\n"
    )
    assert _extract_verdict_from_content(content) == "pass"


def test_c3_no_fence_two_patterns_last_position_wins():
    """C3 (v4 정정): fence 부재 + 위쪽 _VERDICT_RE BLOCK + 아래쪽 _VERDICT_HEADER_RE PASS
    → last-position 헤더 PASS 선택 (Critic #1 핵심 케이스)."""
    content = (
        "verdict: BLOCK 라는 이전 인용\n"
        "본문 본문 본문\n"
        "## PASS\n"
    )
    assert _extract_verdict_from_content(content) == "pass"


def test_c3b_no_fence_symmetric_swap_position_wins():
    """C3b (v4 신규): fence 부재 + 위쪽 헤더 BLOCK + 아래쪽 verdict-line PASS
    → last-position(verdict-line PASS) 선택 — 패턴 종류 무관, 위치만 비교 (대칭성)."""
    content = (
        "## BLOCK\n"
        "본문 본문 본문\n"
        "판정: PASS\n"
    )
    assert _extract_verdict_from_content(content) == "pass"


def test_c4_no_fence_critic_format_compat():
    """C4: fence 부재 + 단일 `Verdict: BLOCK` (af-critic 형식) → block (호환성)."""
    content = "Verdict: BLOCK\n"
    assert _extract_verdict_from_content(content) == "block"


def test_c5_no_fence_no_verdict_line_returns_none():
    """C5: fence 부재 + verdict 라인 0건 → None (caller가 silent fallback 결정)."""
    content = "본문에 verdict 라벨이 전혀 없음\n"
    assert _extract_verdict_from_content(content) is None


def test_c6_multiple_fences_first_pair_only():
    """C6 (v4 신규): 본문에 fence 2쌍 — 첫 쌍 PASS + 둘째 쌍 BLOCK
    → 첫 쌍만 인식 → verdict=pass (Missing #4 해소)."""
    content = (
        "<!-- final-verdict-start -->\n"
        "## Tier 3 판정: PASS\n"
        "사유: 첫 쌍\n"
        "<!-- final-verdict-end -->\n"
        "본문\n"
        "<!-- final-verdict-start -->\n"
        "## Tier 3 판정: BLOCK\n"
        "사유: 둘째 쌍은 무시되어야 함\n"
        "<!-- final-verdict-end -->\n"
    )
    assert _extract_verdict_from_content(content) == "pass"


def test_c7_no_fence_trailing_body_quote_known_limitation():
    """C7 (v7 신규): fence 부재 + 정상 verdict 라인 `## PASS` + trailing 본문 인용
    → last-position이 trailing 캡처 → block (LLM drift 한계 — fence 사용으로 차단 권장).

    v6 cross-review #5가 식별한 last-position 휴리스틱의 알려진 한계.
    spec-level에 명시 — 운영 시 fence 의무화로 차단."""
    content = (
        "## PASS\n"
        "사유: 정상\n"
        "한계 케이스: verdict: BLOCK 키워드를 본문에 인용함\n"
    )
    # 알려진 한계 — last-position이 trailing BLOCK 인용을 캡처
    assert _extract_verdict_from_content(content) == "block"


def test_t3_advisory_parser_uses_last_value():
    content = "t3_required: yes\nbody\n### T3 Advisory\n\nt3_required: no\n### Findings\n"
    assert _extract_t3_required_from_content(content) == "no"


def test_t3_advisory_parser_missing_is_unknown():
    assert _extract_t3_required_from_content("### Verdict: PASS\n") == "unknown"


def test_t3_advisory_parser_fence_only():
    content = (
        "outside t3_required: yes\n"
        "<!-- final-verdict-start -->\n"
        "### Verdict: PASS\n"
        "t3_required: unknown\n"
        "<!-- final-verdict-end -->\n"
    )
    assert _extract_t3_required_from_content(content) == "unknown"


def test_t3_advisory_parser_conflicting_values_fail_closed():
    content = "### T3 Advisory\n\nt3_required: yes\n### Findings\nexample: t3_required: no\n"
    assert _extract_t3_required_from_content(content) == "yes"


def test_t3_advisory_parser_multiple_values_without_section_unknown():
    content = "t3_required: yes\nbody example t3_required: no\n"
    assert _extract_t3_required_from_content(content) == "unknown"


def test_workspace_path_consistency_via_log_event():
    """workspace path 일관성 단위: AF_SKIP_REVIEW_GATE=1 시 hook_events.log가
    workspace 하위 .af_review_queue/ 경로에 기록되는가."""
    # test_j_skip_gate_env 와 같은 보장이지만 path 자체에 초점.
    pass  # test_j_skip_gate_env가 동일 보장을 이미 다룸 — duplicate 방지


# ── Followup #3+#4 (2026-05-20): --t3-required CLI + version single-source ───

def test_cli_record_with_t3_required_advisory(ws):
    """#3: --record af-critic --t3-required no → state['reviews']['af-critic']['t3_required']='no'."""
    from scripts.review_gate import _cli
    _write_state(ws, {"files": ["a.py"], "updated_at": time.time(), "created_at": time.time() - 1})
    rc = _cli([
        "--workspace", ws,
        "--record", "af-critic",
        "--verdict", "pass",
        "--t3-required", "no",
        "--files", "a.py",
    ])
    assert rc == 0
    state = _load_state(ws)
    assert state["reviews"]["af-critic"]["t3_required"] == "no"


def test_cli_record_without_t3_required_defaults_to_unknown(ws):
    """#3: --t3-required 미전달 시 af-critic 어드바이저리는 'unknown'으로 정규화 (fail-closed)."""
    from scripts.review_gate import _cli
    _write_state(ws, {"files": ["a.py"], "updated_at": time.time(), "created_at": time.time() - 1})
    rc = _cli([
        "--workspace", ws,
        "--record", "af-critic",
        "--verdict", "pass",
        "--files", "a.py",
    ])
    assert rc == 0
    state = _load_state(ws)
    assert state["reviews"]["af-critic"]["t3_required"] == "unknown"


def test_cli_record_t3_required_invalid_choice_rejected(ws):
    """#3: argparse choices가 잘못된 advisory 값을 거부 (SystemExit). fail-closed 보호."""
    from scripts.review_gate import _cli
    _write_state(ws, {"files": ["a.py"], "updated_at": time.time(), "created_at": time.time() - 1})
    with pytest.raises(SystemExit):
        _cli([
            "--workspace", ws,
            "--record", "af-critic",
            "--verdict", "pass",
            "--t3-required", "maybe",
            "--files", "a.py",
        ])


def test_t3_skip_classifier_version_single_source():
    """#4: review_gate._T3_SKIP_CLASSIFIER_VERSION은 t3_classifier.CLASSIFIER_VERSION에서
    import — 한쪽만 bump 시 silent BLOCK 회귀 차단."""
    from scripts.review_gate import _T3_SKIP_CLASSIFIER_VERSION
    from scripts.t3_classifier import CLASSIFIER_VERSION
    assert _T3_SKIP_CLASSIFIER_VERSION == CLASSIFIER_VERSION


# ── Followup-of-followup #4 (2026-05-20): non-critic invariant guard ──────────

def test_cli_record_non_critic_does_not_persist_t3_required(ws):
    """non-critic agent의 --t3-required 인자는 reviews[agent]에 기록되지 않는다.

    가드(review_gate.py: `if agent == "af-critic":`)가 풀리면 deterministic skip
    candidate에서 af-test-runner advisory='yes'가 fired_at을 pop하여 재발화 루프 유발.
    """
    from scripts.review_gate import _cli
    files = ["core/cosmetic.py"]
    now = time.time() - 100
    _write_state(ws, {
        "files": files,
        "created_at": now - 10,
        "updated_at": now,
        "fired_at": now + 1,
        "blast_tier": 2,
        "t3_required": False,
        "t3_decision": {
            "decision": "skip_t3",
            "reason": "cosmetic-only-python-ast",
            "classifier_version": "t3-deterministic-v1",
            "files": files,
            "diff_summary": {"added": 1, "deleted": 1},
        },
        "reviews": {},
    })

    rc = _cli([
        "--workspace", ws,
        "--record", "af-test-runner",
        "--verdict", "pass",
        "--t3-required", "yes",
        "--files", "core/cosmetic.py",
    ])
    assert rc == 0

    state = _load_state(ws)
    assert "t3_required" not in state["reviews"]["af-test-runner"]
    assert state.get("fired_at") == now + 1


# ── Phase 4: ALWAYS-Tier-3 안전망 + telemetry skip 분기 ─────────────────────────

def test_is_always_tier3_risk_files():
    """위험군 파일은 ALWAYS-Tier-3로 분류."""
    assert _is_always_tier3(["scripts/review_gate.py"])
    assert _is_always_tier3(["scripts/hook_runner.py"])
    assert _is_always_tier3(["scripts/enqueue_agent_review.py"])
    assert _is_always_tier3(["scripts/review_metrics_logger.py"])
    assert _is_always_tier3(["scripts/t3_classifier.py"])
    assert _is_always_tier3(["core/providers/codex.py"])
    assert _is_always_tier3(["core/provider_detect.py"])
    assert _is_always_tier3([".claude/agents/af-critic.md"])
    assert _is_always_tier3([".claude/skills/foo/SKILL.md"])
    # Windows 백슬래시 경로도 정규화
    assert _is_always_tier3([r"scripts\review_gate.py"])


def test_is_always_tier3_non_risk_files():
    """일반 core 파일은 위험군 아님."""
    assert not _is_always_tier3(["core/utils.py"])
    assert not _is_always_tier3(["core/foo.py"])
    assert not _is_always_tier3(["scripts/blueprint_updater.py"])
    assert not _is_always_tier3([])


def _telemetry_state(blast_tier, *, skip, files=None):
    return {
        "files": files if files is not None else ["core/utils.py"],
        "blast_tier": blast_tier,
        "t3_telemetry_skip": {"skip": skip, "reason": "t3-redundant", "metrics": {}},
    }


def test_telemetry_skip_enacted_true():
    """blast 2 + skip True + 비위험 파일 → 발효."""
    assert _telemetry_skip_enacted(_telemetry_state(2, skip=True))


def test_telemetry_skip_enacted_false_when_decision_false():
    assert not _telemetry_skip_enacted(_telemetry_state(2, skip=False))


def test_telemetry_skip_enacted_false_blast3():
    """blast 3는 telemetry skip 불가."""
    assert not _telemetry_skip_enacted(_telemetry_state(3, skip=True))


def test_telemetry_skip_enacted_false_risk_file():
    """위험군 파일은 skip 결정과 무관하게 발효 안 됨."""
    assert not _telemetry_skip_enacted(
        _telemetry_state(2, skip=True, files=["scripts/review_gate.py"])
    )


def test_telemetry_skip_enacted_false_no_decision():
    assert not _telemetry_skip_enacted({"files": ["core/utils.py"], "blast_tier": 2})


def test_required_tiers_telemetry_skip():
    """blast 2 + telemetry skip 발효 → [1, 2]."""
    assert _required_tiers_for(_telemetry_state(2, skip=True)) == [1, 2]


def test_required_tiers_always_tier3_overrides_telemetry():
    """위험군 파일은 telemetry skip을 무시하고 [1, 2, 3]."""
    state = _telemetry_state(2, skip=True, files=["scripts/review_gate.py"])
    assert _required_tiers_for(state) == [1, 2, 3]


def test_required_tiers_blast3_no_telemetry_skip():
    """blast 3는 telemetry skip 무관 [1, 2, 3]."""
    assert _required_tiers_for(_telemetry_state(3, skip=True)) == [1, 2, 3]


def test_required_tiers_no_skip_default():
    """telemetry 결정 없음 → 정상 3-tier."""
    assert _required_tiers_for({"files": ["core/utils.py"], "blast_tier": 2}) == [1, 2, 3]


def test_required_tiers_blast1():
    assert _required_tiers_for({"files": ["core/utils.py"], "blast_tier": 1}) == [1]
