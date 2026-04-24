"""tests/test_strategy_ledger.py — StrategyLedger unit tests (B2-4 + B2-6)."""
import os
import json
import tempfile
import logging

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


# ═══════════════════════════════════════════════════════════════════════════════
# B2-6: _record_ledger_outcomes 통합 테스트
# ═══════════════════════════════════════════════════════════════════════════════

def _make_board_fixture(workspace, modules_spec: list[dict]) -> dict:
    """board 파일을 workspace에 작성하고 board dict를 반환."""
    from core.project_task_board import build_project_board, write_project_board

    _unique_owners: list[dict] = []
    _seen_owners: set = set()
    for s in modules_spec:
        if s.get("owner_role") and s["owner_role"] not in _seen_owners:
            _seen_owners.add(s["owner_role"])
            _unique_owners.append({"id": s["owner_role"], "name": s["owner_role"]})

    role_plan = {
        "execution_strategy": "sequential",
        "roles": _unique_owners,
        "modules": [
            {
                "id": s["id"],
                "name": s.get("name", s["id"]),
                "owner_role": s.get("owner_role", ""),
                "deliverables": s.get("deliverables", []),
                "tasks": [
                    {
                        "id": f"{s['id']}_t{i}",
                        "title": f"{s['id']} task {i}",
                        "instruction": f"do {s['id']} task {i}",
                        "owner_role": s.get("owner_role", ""),
                        "phase": "build",
                        "status": status,
                    }
                    for i, status in enumerate(s["task_statuses"], 1)
                ],
            }
            for s in modules_spec
        ],
    }
    board = build_project_board({"goal": "test"}, role_plan)

    # build_project_board resets notes to [] — patch task_notes after build
    notes_by_mod: dict[str, list[str | None]] = {
        s["id"]: s["task_notes"]
        for s in modules_spec if s.get("task_notes")
    }
    if notes_by_mod:
        for task in board.get("tasks") or []:
            tid = str(task.get("task_id") or "")
            # task_id format: "{mod_id}_t{n}"
            for mod_id, notes in notes_by_mod.items():
                prefix = f"{mod_id}_t"
                if tid.startswith(prefix):
                    try:
                        idx = int(tid[len(prefix):]) - 1
                        note = notes[idx] if idx < len(notes) else None
                        if note is not None:
                            task["notes"] = [note]
                    except (ValueError, IndexError):
                        pass

    write_project_board(str(workspace), board)
    return board


def _make_role_plan(modules_spec: list[dict]) -> dict:
    return {
        "modules": [
            {
                "id": s["id"],
                "name": s.get("name", s["id"]),
                "owner_role": s.get("owner_role", ""),
                "deliverables": s.get("deliverables", []),
            }
            for s in modules_spec
        ],
    }


def _new_pipeline():
    from core.project_pipeline import ProjectPipeline
    return ProjectPipeline(mr=None, agent_mgr=None, research_agent=None, procurer=None)


# ── I1: crashed / unknown → skip ─────────────────────────────────────────────

def test_ledger_skips_on_crashed(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    _make_board_fixture(tmp_path, [
        {"id": "ma", "owner_role": "backend", "deliverables": ["api"], "task_statuses": ["completed"]},
    ])
    role_plan = _make_role_plan([{"id": "ma", "owner_role": "backend", "deliverables": ["api"]}])
    pipeline._record_ledger_outcomes(status="crashed", role_plan=role_plan, workspace=str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}


def test_ledger_skips_on_unknown(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    _make_board_fixture(tmp_path, [
        {"id": "ma", "owner_role": "backend", "deliverables": ["api"], "task_statuses": ["completed"]},
    ])
    role_plan = _make_role_plan([{"id": "ma", "owner_role": "backend", "deliverables": ["api"]}])
    pipeline._record_ledger_outcomes(status="unknown", role_plan=role_plan, workspace=str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}


# ── I8: board 파일 없음 → skip ────────────────────────────────────────────────

def test_ledger_skips_on_empty_board(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    role_plan = _make_role_plan([{"id": "m1", "owner_role": "backend", "deliverables": ["x"]}])
    pipeline._record_ledger_outcomes(status="partial", role_plan=role_plan, workspace=str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}


# ── I5 + I4: completed/at_risk/pending 모듈 ──────────────────────────────────

def test_ledger_per_module_completed(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    board = _make_board_fixture(tmp_path, [
        {"id": "ma", "owner_role": "backend", "deliverables": ["api server"],
         "task_statuses": ["completed", "completed"]},
        {"id": "mb", "owner_role": "frontend", "deliverables": ["ui"],
         "task_statuses": ["failed", "pending"]},
    ])
    assert next(m for m in board["modules"] if m["id"] == "ma")["status"] == "completed"
    assert next(m for m in board["modules"] if m["id"] == "mb")["status"] == "at_risk"
    # disk roundtrip 검증
    from core.project_task_board import load_project_board
    reloaded = load_project_board(str(tmp_path))
    assert reloaded
    assert next(m for m in reloaded["modules"] if m["id"] == "ma")["status"] == "completed"

    role_plan = _make_role_plan([
        {"id": "ma", "owner_role": "backend", "deliverables": ["api server"]},
        {"id": "mb", "owner_role": "frontend", "deliverables": ["ui"]},
    ])
    pipeline._record_ledger_outcomes(status="partial", role_plan=role_plan, workspace=str(tmp_path))
    reset_strategy_ledger(str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments["api server::backend"].pass_count == 1
    assert ledger._role_assignments["ui::frontend"].fail_count == 1


def test_ledger_skips_pending_module(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    _make_board_fixture(tmp_path, [
        {"id": "m1", "owner_role": "backend", "deliverables": ["x"], "task_statuses": ["pending", "pending"]},
    ])
    role_plan = _make_role_plan([{"id": "m1", "owner_role": "backend", "deliverables": ["x"]}])
    pipeline._record_ledger_outcomes(status="stopped_max_cycles", role_plan=role_plan, workspace=str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}


def test_ledger_mixed_module_status(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    _make_board_fixture(tmp_path, [
        {"id": "mc", "owner_role": "backend", "deliverables": ["core"], "task_statuses": ["completed"]},
        {"id": "mf", "owner_role": "frontend", "deliverables": ["ui"],   "task_statuses": ["failed"]},
        {"id": "mp", "owner_role": "qa",       "deliverables": ["test"], "task_statuses": ["pending"]},
    ])
    role_plan = _make_role_plan([
        {"id": "mc", "owner_role": "backend", "deliverables": ["core"]},
        {"id": "mf", "owner_role": "frontend", "deliverables": ["ui"]},
        {"id": "mp", "owner_role": "qa",       "deliverables": ["test"]},
    ])
    pipeline._record_ledger_outcomes(status="partial", role_plan=role_plan, workspace=str(tmp_path))
    reset_strategy_ledger(str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments.get("core::backend") is not None
    assert ledger._role_assignments["core::backend"].pass_count == 1
    assert ledger._role_assignments.get("ui::frontend") is not None
    assert ledger._role_assignments["ui::frontend"].fail_count == 1
    assert "test::qa" not in ledger._role_assignments


# ── L3: dedup — 동일 pattern 첫 모듈 기준 ───────────────────────────────────

def test_ledger_seen_dedup_first_outcome_wins(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    _make_board_fixture(tmp_path, [
        {"id": "m_a", "owner_role": "backend", "deliverables": ["api v1"], "task_statuses": ["completed"]},
        {"id": "m_b", "owner_role": "backend", "deliverables": ["api v1"], "task_statuses": ["failed"]},
    ])
    role_plan = _make_role_plan([
        {"id": "m_a", "owner_role": "backend", "deliverables": ["api v1"]},
        {"id": "m_b", "owner_role": "backend", "deliverables": ["api v1"]},
    ])
    pipeline._record_ledger_outcomes(status="partial", role_plan=role_plan, workspace=str(tmp_path))
    reset_strategy_ledger(str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    key = "api v1::backend"
    assert ledger._role_assignments[key].pass_count == 1
    assert ledger._role_assignments[key].fail_count == 0


# ── I2: board에 없는 모듈 skip ────────────────────────────────────────────────

def test_ledger_module_missing_in_board(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    _make_board_fixture(tmp_path, [
        {"id": "in_board", "owner_role": "backend", "deliverables": ["api"], "task_statuses": ["completed"]},
    ])
    role_plan = _make_role_plan([
        {"id": "in_board", "owner_role": "backend", "deliverables": ["api"]},
        {"id": "ghost",    "owner_role": "qa",       "deliverables": ["phantom test"]},
    ])
    pipeline._record_ledger_outcomes(status="partial", role_plan=role_plan, workspace=str(tmp_path))
    reset_strategy_ledger(str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert "api::backend" in ledger._role_assignments
    assert not any(k.endswith("::qa") for k in ledger._role_assignments)


# ── I3: owner_role 빈 문자열 skip ────────────────────────────────────────────

def test_ledger_empty_owner_role_skip(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    _make_board_fixture(tmp_path, [
        {"id": "m1", "owner_role": "backend", "deliverables": ["api"], "task_statuses": ["completed"]},
    ])
    role_plan = {"modules": [{"id": "m1", "owner_role": "", "name": "M1", "deliverables": ["api"]}]}
    pipeline._record_ledger_outcomes(status="completed", role_plan=role_plan, workspace=str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}


# ── I7: 4단어 절삭 패턴 ──────────────────────────────────────────────────────

def test_ledger_4word_truncation(tmp_path):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    _make_board_fixture(tmp_path, [
        {"id": "m1", "owner_role": "backend",
         "deliverables": ["rest api endpoint with jwt authentication and refresh"],
         "task_statuses": ["completed"]},
    ])
    role_plan = _make_role_plan([{
        "id": "m1", "owner_role": "backend",
        "deliverables": ["rest api endpoint with jwt authentication and refresh"],
    }])
    pipeline._record_ledger_outcomes(status="completed", role_plan=role_plan, workspace=str(tmp_path))
    reset_strategy_ledger(str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert "rest api endpoint with::backend" in ledger._role_assignments


# ── L6: INFRA failure task → skip ─────────────────────────────────────────────

def test_ledger_skips_infra_failure(tmp_path):
    """task note가 infra_failure: 접두사 → INFRA 필터로 제외 → skip."""
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    # 모든 task가 INFRA failure → non_infra 비어있어서 skip
    spec = [
        {"id": "mi", "owner_role": "backend", "deliverables": ["svc"],
         "task_statuses": ["failed"],
         "task_notes": ["infra_failure: quota_exceeded"]},
    ]
    _make_board_fixture(tmp_path, spec)
    role_plan = _make_role_plan([{"id": "mi", "owner_role": "backend", "deliverables": ["svc"]}])
    pipeline._record_ledger_outcomes(status="partial", role_plan=role_plan, workspace=str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}


# ── L5: owner drift → skip + warning ─────────────────────────────────────────

def test_ledger_skips_on_owner_drift(tmp_path, caplog):
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = _new_pipeline()
    # board fixture에서 task owner를 module owner와 다르게 설정해야 함
    # build_project_board는 tasks[].owner_role을 그대로 보존하므로,
    # fixture 작성 후 board JSON을 직접 수정한다
    _make_board_fixture(tmp_path, [
        {"id": "md", "owner_role": "backend", "deliverables": ["api"], "task_statuses": ["completed"]},
    ])
    from core.project_task_board import load_project_board, write_project_board
    board = load_project_board(str(tmp_path))
    # task의 owner_role을 다른 role로 변조하여 drift 유발
    for t in board.get("tasks") or []:
        if str(t.get("task_id") or "").startswith("md_"):
            t["owner_role"] = "frontend"
    write_project_board(str(tmp_path), board)

    role_plan = _make_role_plan([{"id": "md", "owner_role": "backend", "deliverables": ["api"]}])
    with caplog.at_level(logging.WARNING, logger="core.project_pipeline"):
        pipeline._record_ledger_outcomes(status="completed", role_plan=role_plan, workspace=str(tmp_path))
    assert "owner drift" in caplog.text
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}
