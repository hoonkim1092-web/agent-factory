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


# ── Phase 2 v7 §7.2: `_extract_verdict_from_content` collision 회귀 (C1~C7) ─

from scripts.review_gate import _extract_verdict_from_content  # noqa: E402


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


def test_workspace_path_consistency_via_log_event():
    """workspace path 일관성 단위: AF_SKIP_REVIEW_GATE=1 시 hook_events.log가
    workspace 하위 .af_review_queue/ 경로에 기록되는가."""
    # test_j_skip_gate_env 와 같은 보장이지만 path 자체에 초점.
    pass  # test_j_skip_gate_env가 동일 보장을 이미 다룸 — duplicate 방지
