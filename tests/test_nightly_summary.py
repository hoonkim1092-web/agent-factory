"""tests/test_nightly_summary.py — nightly_summary C2 테스트 (4건)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scripts.nightly_summary import render_summary, _render_modules_section
from core.nightly_state import NightlyState


# helper — test_strategy_ledger._make_board_fixture와 동일 구현
def _make_board_fixture(workspace, modules_spec: list[dict]) -> dict:
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
    write_project_board(str(workspace), board)
    return board


# ── C2 tests ─────────────────────────────────────────────────────────────────

def test_render_summary_no_workspace():
    """workspace=None, state.active_workspace=None → '(프로젝트 비활성)'."""
    state = NightlyState()
    out = render_summary(state, workspace=None)
    assert "(프로젝트 비활성)" in out


def test_render_summary_no_board(tmp_path):
    """workspace 있지만 project_board_state.json 없음 → '(모듈 정보 없음)'."""
    state = NightlyState()
    out = render_summary(state, workspace=str(tmp_path))
    assert "(모듈 정보 없음)" in out


def test_render_summary_modules_mix(tmp_path):
    """✅/⚠️ 모듈 혼재 + 집계 정확도 검증."""
    _make_board_fixture(tmp_path, [
        {"id": "ma", "owner_role": "backend", "task_statuses": ["completed"] * 3},
        {"id": "mb", "owner_role": "frontend", "task_statuses": ["failed", "pending"]},
    ])
    state = NightlyState()
    out = render_summary(state, workspace=str(tmp_path))
    assert "## 모듈별 상태" in out
    assert "✅" in out
    assert "⚠️" in out
    assert "**완료**: 1" in out
    assert "**위험**: 1" in out


def test_render_summary_workspace_priority(tmp_path):
    """호출자 workspace가 state.active_workspace보다 우선."""
    _make_board_fixture(tmp_path, [
        {"id": "mx", "owner_role": "backend", "task_statuses": ["completed"]},
    ])
    state = NightlyState()
    state.active_workspace = "/nonexistent_path_xyz"
    out = render_summary(state, workspace=str(tmp_path))
    assert "## 모듈별 상태" in out
    assert "(모듈 정보 없음)" not in out
    assert "(프로젝트 비활성)" not in out
