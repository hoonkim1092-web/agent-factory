"""
tests/test_skill_evolution_safety.py
=====================================
core/skill_evolution_safety.py 단위 테스트.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.skill_evolution_safety import rollback_evolved_skill, verify_evolved_skill_sandbox


class TestVerifyEvolvedSkillSandbox:
    def test_missing_skill_py_returns_false(self, tmp_path):
        result = verify_evolved_skill_sandbox(str(tmp_path / "skill.py"), "missing")
        assert result is False

    def test_quick_guard_failure_returns_false(self, tmp_path):
        skill_py = tmp_path / "skill.py"
        skill_py.write_text("import os; os.system('rm -rf /')", encoding="utf-8")
        with patch("core.skill_evolution_safety.quick_guard", return_value=(False, ["os.system"])):
            result = verify_evolved_skill_sandbox(str(skill_py), "bad-skill")
        assert result is False

    def test_run_isolated_failure_returns_false(self, tmp_path):
        skill_py = tmp_path / "skill.py"
        skill_py.write_text("print('hello')", encoding="utf-8")
        with (
            patch("core.skill_evolution_safety.quick_guard", return_value=(True, [])),
            patch("core.skill_evolution_safety.run_isolated", return_value=(False, {"reason": "timeout"}, "")),
        ):
            result = verify_evolved_skill_sandbox(str(skill_py), "timeout-skill")
        assert result is False

    def test_both_pass_returns_true(self, tmp_path):
        skill_py = tmp_path / "skill.py"
        skill_py.write_text("print('hello')", encoding="utf-8")
        with (
            patch("core.skill_evolution_safety.quick_guard", return_value=(True, [])),
            patch("core.skill_evolution_safety.run_isolated", return_value=(True, {}, "")),
        ):
            result = verify_evolved_skill_sandbox(str(skill_py), "good-skill")
        assert result is True


class TestRollbackEvolvedSkill:
    def test_no_bak_files_returns_false(self, tmp_path):
        result = rollback_evolved_skill(str(tmp_path), "no-bak-skill")
        assert result is False

    def test_restores_existing_bak_files(self, tmp_path):
        skill_py = tmp_path / "skill.py"
        bak = tmp_path / "skill.py.bak"
        bak.write_text("original code", encoding="utf-8")
        skill_py.write_text("broken code", encoding="utf-8")

        result = rollback_evolved_skill(str(tmp_path), "test-skill")

        assert result is True
        assert skill_py.read_text(encoding="utf-8") == "original code"
        assert not bak.exists()

    def test_continues_on_individual_file_failure(self, tmp_path, caplog):
        import logging
        bak1 = tmp_path / "skill.py.bak"
        bak2 = tmp_path / "SKILL.md.bak"
        bak1.write_text("py bak", encoding="utf-8")
        bak2.write_text("md bak", encoding="utf-8")

        original_move = __import__("shutil").move

        def flaky_move(src, dst):
            if "skill.py" in str(src):
                raise OSError("permission denied")
            return original_move(src, dst)

        with (
            patch("core.skill_evolution_safety.shutil.move", side_effect=flaky_move),
            caplog.at_level(logging.WARNING, logger="core.skill_evolution_safety"),
        ):
            result = rollback_evolved_skill(str(tmp_path), "flaky-skill")

        assert result is True  # SKILL.md.bak 복원 성공
        assert "permission denied" in caplog.text
