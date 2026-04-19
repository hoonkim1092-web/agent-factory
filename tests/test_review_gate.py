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
    _load_state,
    _save_state,
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
