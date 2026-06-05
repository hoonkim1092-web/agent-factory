"""AgentSpecializer.specialize() 단위 테스트 (WI-2: force_provider 주입)."""
from __future__ import annotations

from unittest.mock import patch

from core.agent_specializer import AgentSpecializer


def _base_agent(name: str = "backend_dev") -> dict:
    return {"name": name, "role": name, "system_ko": "역할 설명", "skills": []}


def _task(phase: str = "build", review_provider: str = "") -> dict:
    task = {
        "task_id": f"module_1_{phase}",
        "title": f"{phase} task",
        "instruction": f"{phase} 작업 수행",
        "owner_role": "backend_dev",
        "module_id": "module_1",
        "phase": phase,
        "depends_on": [],
        "acceptance": [],
        "artifacts": [],
    }
    if review_provider:
        task["review_provider"] = review_provider
    return task


class TestSpecializeForceProvider:
    def test_cross_validate_task_with_review_provider_sets_force_provider(self):
        specializer = AgentSpecializer()
        with patch("core.agent_specializer.mailbox_prompt_digest", return_value=""):
            with patch("core.agent_specializer.load_project_board", return_value={}):
                agent = specializer.specialize(
                    _base_agent(),
                    _task(phase="cross_validate", review_provider="codex_cli"),
                    workspace="/fake",
                )
        assert agent.get("force_provider") == "codex_cli"

    def test_task_without_review_provider_does_not_set_force_provider(self):
        specializer = AgentSpecializer()
        with patch("core.agent_specializer.mailbox_prompt_digest", return_value=""):
            with patch("core.agent_specializer.load_project_board", return_value={}):
                agent = specializer.specialize(
                    _base_agent(),
                    _task(phase="build"),
                    workspace="/fake",
                )
        assert "force_provider" not in agent

    def test_specialize_does_not_mutate_base_agent(self):
        base = _base_agent()
        specializer = AgentSpecializer()
        with patch("core.agent_specializer.mailbox_prompt_digest", return_value=""):
            with patch("core.agent_specializer.load_project_board", return_value={}):
                specializer.specialize(
                    base,
                    _task(phase="cross_validate", review_provider="codex_cli"),
                    workspace="/fake",
                )
        assert "force_provider" not in base
