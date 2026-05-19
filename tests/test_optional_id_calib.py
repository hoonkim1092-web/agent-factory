"""CALIB 회귀 테스트 — optional-id 정규화 work-item (2026-05-19).

safe_id("") = "skill" 버그로 발생하는 결함 클러스터 재현.
수정 전: 전 케이스 FAIL.  수정 후: 전 케이스 PASS.
"""
from __future__ import annotations

import os
import types

os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# C1  project_mailbox — send_agent_message / read_inbox / ack
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def ws(tmp_path):
    return str(tmp_path)


def _send(ws, **kwargs):
    from core.project_mailbox import send_agent_message
    defaults = dict(
        workspace=ws,
        from_role="architect",
        to_role="backend_dev",
        message_type="handoff",
        body="please implement",
        strict_files=False,
    )
    defaults.update(kwargs)
    return send_agent_message(**defaults)


# C1a — 빈 to_role 은 ValueError 를 발생시켜야 한다
def test_c1a_empty_to_role_raises(ws):
    with pytest.raises(ValueError, match="to_role_required"):
        _send(ws, to_role="")


# C1b — 빈 from_role 은 "unknown_sender" 로 대체돼야 한다
def test_c1b_empty_from_role_becomes_unknown_sender(ws):
    msg = _send(ws, from_role="")
    assert msg["from_role"] == "unknown_sender"


# C1c — 빈 task_id 는 thread_id 에 'general' 을 사용해야 한다
def test_c1c_empty_task_id_uses_general_thread(ws):
    msg = _send(ws, task_id="")
    assert "general" in msg["thread_id"]
    assert "skill" not in msg["thread_id"]


# C1d — read_inbox(task_id="") 는 task_id 필터 없이 전체를 반환해야 한다
def test_c1d_empty_task_id_read_returns_all(ws):
    from core.project_mailbox import read_inbox
    _send(ws, task_id="spec_123")
    _send(ws, task_id="impl_456")
    result = read_inbox(ws, "backend_dev", task_id="")
    assert len(result) == 2


# C1e — ack_mailbox_message(role="") 는 to_role 필터 없이 ack 해야 한다
def test_c1e_empty_role_ack_succeeds(ws):
    from core.project_mailbox import ack_mailbox_message
    msg = _send(ws)
    acked = ack_mailbox_message(ws, msg["message_id"], role="")
    assert acked is True


# ═══════════════════════════════════════════════════════════════════════════
# C2  install_candidate_utils — normalize_install_candidate_item
# ═══════════════════════════════════════════════════════════════════════════

def test_c2_empty_raw_key_string_path_returns_none():
    from core.install_candidate_utils import normalize_install_candidate_item
    # raw_key="" → skill_id 가 "" → None 반환 (현재: "skill" 처리)
    result = normalize_install_candidate_item("", "/some/path/to/skill.py")
    assert result is None


def test_c2_empty_id_dict_returns_none():
    from core.install_candidate_utils import normalize_install_candidate_item
    result = normalize_install_candidate_item("", {"id": "", "path": "/some/path"})
    assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# C3  project_task_board — _dependency_satisfied
# ═══════════════════════════════════════════════════════════════════════════

def test_c3_empty_dep_is_satisfied():
    from core.project_task_board import _dependency_satisfied
    board = {"tasks": [], "modules": []}
    # 빈 의존성 → 만족 (no requirement)
    assert _dependency_satisfied("", board, set()) is True


def test_c3_whitespace_dep_is_satisfied():
    from core.project_task_board import _dependency_satisfied
    board = {"tasks": [], "modules": []}
    assert _dependency_satisfied("   ", board, set()) is True


# ═══════════════════════════════════════════════════════════════════════════
# C4  dynamic_orchestrator — _completed_subtask_keys
# ═══════════════════════════════════════════════════════════════════════════

def test_c4_empty_task_id_not_in_completed_keys():
    import core.dynamic_orchestrator as dyn

    # state_board 에 task_id="" 인 completed_subtask
    mo = types.SimpleNamespace(
        state_board={"completed_subtasks": [{"task_id": "", "subtask": "something done"}]},
        _workspace="",
        _run_id="",
        _runtime_workspace="",
    )
    keys = dyn.DynamicOrchestrator._completed_subtask_keys(mo)
    # "skill" 이 keys 에 들어있으면 안 된다 (safe_id("") = "skill" 버그)
    assert "skill" not in keys
    # "something_done" 은 subtask 텍스트 경로로 추가됨 — 회귀 없음
    assert "something_done" in keys


# ═══════════════════════════════════════════════════════════════════════════
# C5  work_item_parser — parse_implementation_tasks
# ═══════════════════════════════════════════════════════════════════════════

def test_c5_whitespace_only_title_task_id_is_empty():
    from core.work_item_parser import parse_implementation_tasks
    # 제목이 탭/공백만 → task_id 는 "" 여야 함 (현재: "skill")
    md = "- [ ] \t"
    tasks = parse_implementation_tasks(md)
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == ""
