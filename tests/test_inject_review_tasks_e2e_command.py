"""tests/test_inject_review_tasks_e2e_command.py — §9.7 케이스 (1)."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import pytest


def _seed_board(workspace: str, slug: str = "test-module") -> dict:
    board = {
        "project_id": "test-proj",
        "tasks": [
            {
                "task_id": "T-001",
                "title": "build auth",
                "phase": "build",
                "module_id": slug,
                "owner_role": "backend_dev",
                "status": "done",
                "depends_on": [],
                "acceptance": [],
                "artifacts": [],
                "notes": [],
                "updated_at": "2026-05-10T00:00:00+09:00",
            },
            {
                "task_id": "T-002",
                "title": "verify auth",
                "phase": "verify",
                "module_id": slug,
                "owner_role": "backend_dev",
                "status": "pending",
                "depends_on": ["T-001"],
                "acceptance": [],
                "artifacts": [],
                "notes": [],
                "updated_at": "2026-05-10T00:00:00+09:00",
            },
        ],
        "modules": [{"id": slug, "task_ids": ["T-001", "T-002"]}],
    }
    from core.project_task_board import write_project_board
    write_project_board(workspace, board)
    return board


def test_inject_review_tasks_e2e_command():
    """#23: inject_review_tasks → code_review/cross_validate task에 e2e_command.startswith('# TODO:')."""
    with tempfile.TemporaryDirectory() as tmp:
        slug = "auth-module"
        _seed_board(tmp, slug)

        completed_task = {
            "task_id": "T-001",
            "phase": "build",
            "module_id": slug,
            "owner_role": "backend_dev",
            "provider_id": "claude",
        }

        # CLI provider detection: 2개 이상으로 mock (cross_validate도 주입)
        # inject_review_tasks 내부에서 지역 import하므로 실제 모듈 경로를 patch
        with patch("core.providers.registry.detect_available_cli_providers", return_value=["claude", "gemini"]):
            with patch("core.providers.registry.pick_review_provider", return_value="gemini"):
                from core.project_task_board import inject_review_tasks
                review_tasks = inject_review_tasks(tmp, completed_task)

        assert len(review_tasks) >= 1, "리뷰 태스크가 주입되어야 함"
        phases = {t["phase"] for t in review_tasks}
        assert "code_review" in phases, "code_review 태스크 없음"

        for rt in review_tasks:
            phase = rt.get("phase", "")
            if phase in ("code_review", "cross_validate"):
                e2e = rt.get("e2e_command", "")
                assert e2e.startswith("# TODO"), (
                    f"{phase} task의 e2e_command가 # TODO로 시작해야 함: {e2e!r}"
                )


def test_inject_review_tasks_provider_id_routing():
    """provider_id가 completed_task에 포함되면 pick_review_provider에 전달되어야 한다."""
    with tempfile.TemporaryDirectory() as tmp:
        slug = "auth-module"
        _seed_board(tmp, slug)

        completed_task = {
            "task_id": "T-001",
            "phase": "build",
            "module_id": slug,
            "owner_role": "backend_dev",
            "provider_id": "claude_cli",
        }

        captured: list[str] = []

        def _fake_pick(author: str) -> str:
            captured.append(author)
            return "codex"

        with patch("core.providers.registry.detect_available_cli_providers", return_value=["claude_cli", "codex"]):
            with patch("core.providers.registry.pick_review_provider", side_effect=_fake_pick):
                from core.project_task_board import inject_review_tasks
                inject_review_tasks(tmp, completed_task)

        assert captured == ["claude_cli"], (
            f"pick_review_provider는 author_provider='claude_cli'로 호출되어야 함, got: {captured}"
        )


def test_inject_review_tasks_provider_id_missing_defaults_to_first():
    """provider_id 없으면 available[0]을 author_provider로 사용한다."""
    with tempfile.TemporaryDirectory() as tmp:
        slug = "auth-module2"
        _seed_board(tmp, slug)

        completed_task = {
            "task_id": "T-001",
            "phase": "build",
            "module_id": slug,
            "owner_role": "backend_dev",
            # provider_id 없음
        }

        captured: list[str] = []

        def _fake_pick(author: str) -> str:
            captured.append(author)
            return "codex"

        with patch("core.providers.registry.detect_available_cli_providers", return_value=["claude_cli", "codex"]):
            with patch("core.providers.registry.pick_review_provider", side_effect=_fake_pick):
                from core.project_task_board import inject_review_tasks
                inject_review_tasks(tmp, completed_task)

        assert captured == ["claude_cli"], (
            f"provider_id 없으면 available[0]='claude_cli'로 폴백해야 함, got: {captured}"
        )
