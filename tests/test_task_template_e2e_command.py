"""tests/test_task_template_e2e_command.py — §9.7 케이스 (2)."""
from __future__ import annotations

import pytest

from core.project_task_board import _task_template


def test_task_template_build_has_todo_marker():
    """#21: build phase task → e2e_command.startswith('# TODO:')."""
    tasks = _task_template("alice", "auth-module", "인증 모듈 구현")
    build_tasks = [t for t in tasks if t.get("phase") == "build"]
    assert build_tasks, "build phase task 없음"
    for bt in build_tasks:
        assert "e2e_command" in bt, "e2e_command 필드 없음"
        assert bt["e2e_command"].startswith("# TODO"), (
            f"# TODO로 시작해야 함: {bt['e2e_command']!r}"
        )


def test_task_template_scope_has_no_e2e_command():
    """#22: scope phase task → e2e_command 필드 없거나 빈 값 (exempt)."""
    tasks = _task_template("alice", "auth-module", "인증 모듈 구현")
    scope_tasks = [t for t in tasks if t.get("phase") == "scope"]
    assert scope_tasks, "scope phase task 없음"
    for st in scope_tasks:
        e2e = st.get("e2e_command", "")
        assert not e2e or not e2e.strip(), (
            f"scope task에 e2e_command가 있으면 안됨: {e2e!r}"
        )


def test_task_template_verify_has_todo_marker():
    """verify phase도 # TODO: 마커 확인."""
    tasks = _task_template("bob", "payment", "결제 모듈")
    verify_tasks = [t for t in tasks if t.get("phase") == "verify"]
    assert verify_tasks
    for vt in verify_tasks:
        assert "e2e_command" in vt
        assert vt["e2e_command"].startswith("# TODO")
