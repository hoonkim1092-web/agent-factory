"""tests/test_review_gate_phase0.py — Phase 0 (Proof-Carrying Review 도입 전 단계) 테스트.

추가 동작:
  (T1)  blast_tier=1 — af-test-runner만 기록해도 PASS
  (T2)  round_count 증가 — 필수 tier 모두 완료 시 +1
  (T3)  last_round_summary.has_block — BLOCK/FAIL 포함 시 True, 아니면 False
  (T4)  claim_id — record_review_done 후 reviews[agent]에 포함
  (T5)  blast_radius — 결정적 분류

설계: docs/2026-04-30-proof-carrying-review.md (예정), Phase 0 정책 (CLAUDE.md).
"""
from __future__ import annotations

import json
import os
import time

import pytest

from scripts.review_gate import is_gate_blocked, record_review_done, _load_state
from scripts.blast_radius import classify_path, classify_with_content, required_agents


@pytest.fixture
def ws(tmp_path):
    return str(tmp_path)


def _write_state(ws: str, state: dict) -> None:
    queue = os.path.join(ws, ".af_review_queue")
    os.makedirs(queue, exist_ok=True)
    with open(os.path.join(queue, "pending_agent_review.json"), "w") as f:
        json.dump(state, f)


# ── Tier 1 경량 게이트 ────────────────────────────────────────────────────────

def test_t1_tier1_only_test_runner_required(ws):
    """blast_tier=1 → af-test-runner만 기록해도 PASS."""
    files = ["scripts/example.py"]
    completed = time.time() - 5
    state = {
        "files": files,
        "created_at": completed - 10,
        "updated_at": completed - 1,
        "blast_tier": 1,
    }
    _write_state(ws, state)

    record_review_done(ws, "af-test-runner", 1, "pass", files)

    blocked, reason = is_gate_blocked(ws)
    assert not blocked
    assert reason == "all-tiers-passed"


def test_t1b_tier1_no_test_runner_blocks(ws):
    """blast_tier=1이라도 af-test-runner가 없으면 BLOCK."""
    files = ["scripts/example.py"]
    state = {
        "files": files,
        "updated_at": time.time(),
        "blast_tier": 1,
        "reviews": {},
    }
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked
    assert reason == "missing-tier-1"


# ── round_count 증가 ─────────────────────────────────────────────────────────

def test_t2_round_count_increments_on_full_completion(ws):
    """필수 tier 모두 완료 시 round_count += 1, last_round_summary 갱신."""
    files = ["core/foo.py"]
    state = {
        "files": files,
        "created_at": time.time() - 10,
        "updated_at": time.time() - 5,
        "blast_tier": 2,
        "round_count": 0,
    }
    _write_state(ws, state)

    record_review_done(ws, "af-test-runner", 1, "pass", files)
    s = _load_state(ws)
    assert s.get("round_count", 0) == 0  # 아직 미완료

    record_review_done(ws, "af-critic", 2, "warn", files)
    s = _load_state(ws)
    assert s.get("round_count", 0) == 0

    record_review_done(ws, "af-cross-review", 3, "pass", files)
    s = _load_state(ws)
    assert s["round_count"] == 1
    assert s["last_round_summary"]["round"] == 1
    assert s["last_round_summary"]["has_block"] is False
    assert s["last_round_summary"]["verdicts"]["af-critic"] == "warn"


def test_t3_has_block_true_on_block_verdict(ws):
    """tier 중 하나라도 BLOCK이면 last_round_summary.has_block == True."""
    files = ["core/foo.py"]
    state = {
        "files": files,
        "created_at": time.time() - 10,
        "updated_at": time.time() - 5,
        "blast_tier": 2,
    }
    _write_state(ws, state)

    record_review_done(ws, "af-test-runner", 1, "pass", files)
    record_review_done(ws, "af-critic", 2, "block", files)
    record_review_done(ws, "af-cross-review", 3, "pass", files)

    s = _load_state(ws)
    assert s["last_round_summary"]["has_block"] is True


def test_t3b_has_block_true_on_fail_verdict(ws):
    """fail verdict도 has_block에 포함된다."""
    files = ["core/foo.py"]
    state = {"files": files, "updated_at": time.time() - 5, "blast_tier": 2}
    _write_state(ws, state)

    record_review_done(ws, "af-test-runner", 1, "fail", files)
    record_review_done(ws, "af-critic", 2, "pass", files)
    record_review_done(ws, "af-cross-review", 3, "pass", files)

    s = _load_state(ws)
    assert s["last_round_summary"]["has_block"] is True


# ── claim_id ──────────────────────────────────────────────────────────────────

def test_t4_claim_id_present(ws):
    """record_review_done 후 reviews[agent]에 claim_id가 포함된다."""
    files = ["core/foo.py"]
    state = {"files": files, "updated_at": time.time() - 5, "blast_tier": 2}
    _write_state(ws, state)

    record_review_done(ws, "af-critic", 2, "warn", files)
    s = _load_state(ws)
    cid = s["reviews"]["af-critic"].get("claim_id")
    assert cid is not None
    assert cid.startswith("AF-RG-")
    assert "T2" in cid


# ── Blast Radius 결정적 분류 ──────────────────────────────────────────────────

def test_t5_classify_tier3_known_paths():
    """알려진 hook launcher / DB sync 등은 Tier 3."""
    assert classify_path("scripts/run.py") == 3
    assert classify_path("scripts/hook_runner.py") == 3
    assert classify_path("scripts/review_gate.py") == 3
    # DB sync 파일은 루트에 위치 (CLAUDE.md: `python end_db.py agent-factory`)
    assert classify_path("end_db.py") == 3
    assert classify_path("start_db.py") == 3
    assert classify_path("af.spec") == 3
    assert classify_path("policy.yaml") == 3
    assert classify_path("version.py") == 3
    assert classify_path(".githooks/pre-commit") == 3
    assert classify_path(".github/workflows/ci.yml") == 3


def test_t5f_path_normalization():
    """./prefix, 중복 슬래시, 백슬래시는 모두 동일하게 정규화."""
    assert classify_path("./scripts/run.py") == 3
    assert classify_path("scripts//run.py") == 3
    assert classify_path("scripts\\run.py") == 3


def test_t5g_tier3_paths_exist_on_disk():
    """모든 _TIER3_PATHS 핀이 실제 레포에 존재해야 한다."""
    import os
    from scripts.blast_radius import _TIER3_PATHS
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    missing = [p for p in _TIER3_PATHS if not os.path.exists(os.path.join(repo_root, p))]
    assert missing == [], f"_TIER3_PATHS 핀이 디스크에 없음: {missing}"


def test_t5h_regex_call_patterns_only(tmp_path):
    """Comment 라인의 password/token은 false-positive로 매칭하지 않아야 한다."""
    f = tmp_path / "comment.py"
    f.write_text("# password = \"x\"\n# this is just a comment about token\nx = 1\n")
    assert classify_with_content("comment.py", str(tmp_path)) == 2

    # 실제 secret assignment는 매칭되어야 함
    f2 = tmp_path / "secret.py"
    f2.write_text("api_key = \"sk-12345\"\n")
    assert classify_with_content("secret.py", str(tmp_path)) == 3


def test_t5i_regex_literal_exec_eval(tmp_path):
    """exec("...") / eval("...") literal 호출도 매칭되어야 한다."""
    f = tmp_path / "exec_call.py"
    f.write_text('exec("print(1)")\n')
    assert classify_with_content("exec_call.py", str(tmp_path)) == 3

    f2 = tmp_path / "eval_call.py"
    f2.write_text('result = eval("1 + 1")\n')
    assert classify_with_content("eval_call.py", str(tmp_path)) == 3


def test_t5j_invalid_tier_raises():
    """tier=0 등 무효 값은 ValueError 발생."""
    import pytest as _pt
    with _pt.raises(ValueError):
        required_agents(0)
    with _pt.raises(ValueError):
        required_agents(99)


# ── 라운드 모델 정확성 (review #2의 Critical findings 검증) ─────────────────

def test_t6_round_count_no_double_increment_on_same_round_re_record(ws):
    """같은 라운드에서 동일 에이전트가 재기록되어도 round_count 증가 안 함.

    Critical #1: 1초 가드만 있던 모델에서는 round_count 폭주 위험 → round_started_at
    토큰 기반 모델로 검증.
    """
    files = ["core/foo.py"]
    state = {
        "files": files,
        "updated_at": time.time() - 10,
        "blast_tier": 2,
    }
    _write_state(ws, state)

    # 1라운드 시작 → 모든 tier 기록
    record_review_done(ws, "af-test-runner", 1, "pass", files)
    record_review_done(ws, "af-critic", 2, "warn", files)
    record_review_done(ws, "af-cross-review", 3, "pass", files)
    s = _load_state(ws)
    assert s["round_count"] == 1

    # 같은 라운드에서 af-critic 재기록 (예: 동시 실행)
    # → round_started_at이 이미 None이므로 새 라운드 시작 처리됨이 정상이지만,
    # 같은 호출에서 round_count++가 두 번 발생하지 않는지가 핵심
    time.sleep(0.05)
    record_review_done(ws, "af-critic", 2, "pass", files)
    s = _load_state(ws)
    # 새 라운드 토큰이 부여되어 round 2로 진입할 수 있음 — 하지만 아직 모든 tier 미완료
    # → round_count는 1 또는 2 (재진입 시), 단일 record로 ++가 두 번 발생하면 3 이상
    assert s["round_count"] in (1, 2), f"round_count 폭주: {s['round_count']}"


def test_t7_clear_resets_round_metadata(ws):
    """clear_committed_files: files가 모두 비면 round_count/last_round_summary 리셋.

    Critical #3: 리셋 누락 시 다음 작업 사이클이 영구 silent-fail.
    """
    from scripts.review_gate import clear_committed_files

    files = ["core/foo.py"]
    state = {"files": files, "updated_at": time.time() - 5, "blast_tier": 2}
    _write_state(ws, state)
    record_review_done(ws, "af-test-runner", 1, "pass", files)
    record_review_done(ws, "af-critic", 2, "pass", files)
    record_review_done(ws, "af-cross-review", 3, "pass", files)

    s = _load_state(ws)
    assert s["round_count"] == 1
    assert s.get("last_round_summary") is not None

    # commit 후 리셋
    clear_committed_files(ws, files)
    s = _load_state(ws)
    assert s["files"] == []
    assert s.get("round_count") is None
    assert s.get("last_round_summary") is None
    assert s.get("round_started_at") is None
    assert s.get("blast_tier") is None


def test_t8_block_verdict_checked_even_when_rounds_capped(ws):
    """round_count >= MAX_ROUNDS(5)이고 stale이어도 BLOCK verdict는 차단되어야 한다.

    Critical #2: rounds-capped 분기가 BLOCK 검사를 우회하면 안 됨.
    """
    files = ["core/foo.py"]
    completed = time.time() - 100
    state = {
        "files": files,
        "created_at": completed - 200,
        "updated_at": time.time(),  # stale (재편집 발생)
        "blast_tier": 2,
        "round_count": 5,  # cap 도달 (MAX_ROUNDS=5)
        "reviews": {
            "af-test-runner": {"tier": 1, "verdict": "pass", "files_snapshot": files, "completed_at": completed},
            "af-critic": {"tier": 2, "verdict": "block", "files_snapshot": files, "completed_at": completed + 1},
            "af-cross-review": {"tier": 3, "verdict": "pass", "files_snapshot": files, "completed_at": completed + 2},
        },
    }
    _write_state(ws, state)
    blocked, reason = is_gate_blocked(ws)
    assert blocked, f"BLOCK이 우회됨 — rounds-capped 분기가 fall-through 안 됨"
    assert reason.startswith("verdict-block:")


def test_t9_claim_id_includes_round_and_uses_utc(ws):
    """claim_id: AF-RG-YYYYMMDDHHMMSS-R{round}-{tier} (UTC 14자리 + round 번호)."""
    files = ["core/foo.py"]
    state = {"files": files, "updated_at": time.time() - 5, "blast_tier": 2}
    _write_state(ws, state)

    record_review_done(ws, "af-critic", 2, "warn", files)
    s = _load_state(ws)
    cid = s["reviews"]["af-critic"]["claim_id"]
    # 형식: AF-RG-{14자리}-R{n}-T2
    import re as _re
    assert _re.match(r"^AF-RG-\d{14}-R\d+-T2$", cid), f"claim_id 형식 오류: {cid}"
    # round 번호는 1 (현재 라운드)
    assert "-R1-" in cid


def test_t5b_classify_tier1_docs():
    """docs/*.md, README, .gitignore 등은 Tier 1."""
    assert classify_path("docs/2026-04-30-test.md") == 1
    assert classify_path("README.md") == 1
    assert classify_path(".gitignore") == 1
    assert classify_path("Master_Blueprint.md") == 1


def test_t5c_classify_tier2_default():
    """일반 파일은 Tier 2 기본값."""
    assert classify_path("core/cli.py") == 2
    assert classify_path("core/foo/bar.py") == 2


def test_t5d_required_agents_per_tier():
    assert required_agents(1) == ["af-test-runner"]
    assert required_agents(2) == ["af-test-runner", "af-critic", "af-cross-review"]
    assert required_agents(3) == ["af-test-runner", "af-critic", "af-cross-review"]


def test_t5e_classify_with_content_promotes_to_tier3(tmp_path):
    """내용에 subprocess/shell 등 Tier 3 지표가 있으면 Tier 3 승격."""
    f = tmp_path / "danger.py"
    f.write_text("import subprocess\nsubprocess.run(['ls'])\n")
    tier = classify_with_content("danger.py", str(tmp_path))
    assert tier == 3

    f2 = tmp_path / "safe.py"
    f2.write_text("def add(a, b):\n    return a + b\n")
    tier2 = classify_with_content("safe.py", str(tmp_path))
    assert tier2 == 2
