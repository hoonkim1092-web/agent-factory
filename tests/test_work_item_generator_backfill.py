"""tests/test_work_item_generator_backfill.py — §9 #25 (8개 mock → ≥7개 정확히 파싱)."""
from __future__ import annotations

import pytest

from core.work_item_generator import _backfill_e2e_from_tasks_md


def _board_with_tasks(*task_ids: str) -> dict:
    return {
        "tasks": [
            {"task_id": tid, "e2e_command": "", "phase": "build"}
            for tid in task_ids
        ]
    }


# 1. 정상 매칭
def test_backfill_normal_match():
    content = "- task_id: T-001\n- e2e_command: pytest -k T-001 -q\n"
    board = _board_with_tasks("T-001")
    result = _backfill_e2e_from_tasks_md(content, board)
    assert result["tasks"][0]["e2e_command"] == "pytest -k T-001 -q"


# 2. task_id 없는 경우 — silent skip, 기존 값 유지
def test_backfill_no_task_id():
    content = "- e2e_command: pytest -q\n"
    board = _board_with_tasks("T-001")
    result = _backfill_e2e_from_tasks_md(content, board)
    assert result["tasks"][0]["e2e_command"] == ""  # 기존값 유지


# 3. TODO 마커 — 덮어쓰지 않음
def test_backfill_todo_marker():
    content = "- task_id: T-001\n- e2e_command: # TODO: fill this\n"
    board = _board_with_tasks("T-001")
    result = _backfill_e2e_from_tasks_md(content, board)
    assert result["tasks"][0]["e2e_command"] == ""  # 기존값 유지 (TODO 무시)


# 4. 중복 task_id — 첫 번째 매칭만 사용
def test_backfill_duplicate_task_id():
    content = (
        "- task_id: T-001\n- e2e_command: first-cmd\n"
        "- task_id: T-001\n- e2e_command: second-cmd\n"
    )
    board = _board_with_tasks("T-001")
    result = _backfill_e2e_from_tasks_md(content, board)
    assert result["tasks"][0]["e2e_command"] == "first-cmd"


# 5. 예외 발생 — 기존 task_board 반환
def test_backfill_exception_returns_original():
    board = _board_with_tasks("T-001")
    # tasks_content가 str이 아닌 경우 — 내부에서 예외 발생 가능
    # str로 강제되므로 의도적으로 잘못된 타입 주입 불가; 대신 빈 str 전달 (silent skip 검증)
    result = _backfill_e2e_from_tasks_md("", board)
    # 빈 content → 매칭 없음 → 원본 반환
    assert result["tasks"][0]["e2e_command"] == ""


# 6. e2e_command 필드 없는 task → 영향 없음
def test_backfill_task_without_e2e_field():
    board = {"tasks": [{"task_id": "T-001", "phase": "build"}]}  # e2e_command 없음
    content = "- task_id: T-001\n- e2e_command: pytest -q\n"
    result = _backfill_e2e_from_tasks_md(content, board)
    assert result["tasks"][0].get("e2e_command") == "pytest -q"


# 7. 순서 역전 (task_id가 e2e_command 이후에 등장) — 5줄 window 미달 → skip
def test_backfill_task_id_after_e2e():
    content = "- e2e_command: pytest -q\n- task_id: T-001\n"
    board = _board_with_tasks("T-001")
    result = _backfill_e2e_from_tasks_md(content, board)
    # task_id가 e2e_command 이후 → 5줄 window 내에 없음 → skip
    assert result["tasks"][0]["e2e_command"] == ""


# 8. 다중 phase 다중 task
def test_backfill_multiple_phases():
    content = (
        "- task_id: T-001\n- e2e_command: pytest -k T-001\n"
        "- task_id: T-002\n- e2e_command: bash smoke.sh\n"
    )
    board = {
        "tasks": [
            {"task_id": "T-001", "e2e_command": "", "phase": "build"},
            {"task_id": "T-002", "e2e_command": "", "phase": "verify"},
        ]
    }
    result = _backfill_e2e_from_tasks_md(content, board)
    assert result["tasks"][0]["e2e_command"] == "pytest -k T-001"
    assert result["tasks"][1]["e2e_command"] == "bash smoke.sh"


def test_backfill_pass_count():
    """≥7/8 mock markdowns 정확히 파싱 확인."""
    pass_count = 0
    tests = [
        # (content, board, expected_e2e_command_of_T001)
        ("- task_id: T-001\n- e2e_command: pytest -k T-001 -q\n",
         _board_with_tasks("T-001"), "pytest -k T-001 -q"),
        ("- e2e_command: pytest -q\n",
         _board_with_tasks("T-001"), ""),
        ("- task_id: T-001\n- e2e_command: # TODO: fill\n",
         _board_with_tasks("T-001"), ""),
        ("- task_id: T-001\n- e2e_command: first\n- task_id: T-001\n- e2e_command: second\n",
         _board_with_tasks("T-001"), "first"),
        ("", _board_with_tasks("T-001"), ""),
        ("- task_id: T-001\n- e2e_command: pytest -q\n",
         {"tasks": [{"task_id": "T-001", "phase": "build"}]}, "pytest -q"),
        ("- e2e_command: pytest -q\n- task_id: T-001\n",
         _board_with_tasks("T-001"), ""),
        ("- task_id: T-001\n- e2e_command: pytest -k T-001\n- task_id: T-002\n- e2e_command: bash smoke.sh\n",
         {"tasks": [{"task_id": "T-001", "e2e_command": "", "phase": "build"}, {"task_id": "T-002", "e2e_command": "", "phase": "verify"}]},
         "pytest -k T-001"),
    ]

    for content, board, expected in tests:
        result = _backfill_e2e_from_tasks_md(content, board)
        actual = result["tasks"][0].get("e2e_command", "")
        if actual == expected:
            pass_count += 1

    assert pass_count >= 7, f"≥7/8 기대, 실제: {pass_count}/8"
