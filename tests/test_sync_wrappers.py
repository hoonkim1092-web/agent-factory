"""Tests for start_db.py and start_sync.py cross-platform wrappers.

Replaces the deleted .cmd wrapper tests (ba401c93: .cmd → .py migration).
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import start_db
import start_sync


class TestStartDbResolveTarget:
    def test_all_expands_to_multi_target(self):
        val, is_multi = start_db._resolve_target("all")
        assert is_multi is True
        assert "," in val
        assert "agent-factory" in val

    def test_all_is_case_insensitive(self):
        val, is_multi = start_db._resolve_target("ALL")
        assert is_multi is True

    def test_single_project_not_multi(self):
        val, is_multi = start_db._resolve_target("agent-factory")
        assert val == "agent-factory"
        assert is_multi is False

    def test_at_repo_alias_not_multi(self):
        val, is_multi = start_db._resolve_target("@repo")
        assert val == "@repo"
        assert is_multi is False

    def test_comma_separated_is_multi(self):
        val, is_multi = start_db._resolve_target("proj-a,proj-b")
        assert is_multi is True
        assert val == "proj-a,proj-b"


class TestStartDbCommandArgs:
    """Verify main() builds the right subprocess command."""

    def _capture_run(self, argv: list[str]) -> list[str]:
        captured = []

        def fake_run(cmd: list[str]) -> int:
            captured.extend(cmd)
            return 0

        with (
            patch.object(start_db, "_run", side_effect=fake_run),
            patch.object(start_db, "_global_user_key", return_value=""),
            patch("subprocess.run"),
            patch.object(sys, "argv", ["start_db.py"] + argv),
        ):
            start_db.main()

        return captured

    def test_single_target_uses_project_flag(self):
        cmd = self._capture_run(["agent-factory"])
        assert "--project" in cmd
        assert "--projects" not in cmd
        assert "agent-factory" in cmd

    def test_all_target_uses_projects_flag(self):
        cmd = self._capture_run(["all"])
        assert "--projects" in cmd
        assert "--project" not in cmd

    def test_no_args_defaults_to_all(self):
        cmd = self._capture_run([])
        assert "--projects" in cmd

    def test_agent_arg_forwarded(self):
        cmd = self._capture_run(["agent-factory", "my-agent"])
        assert "--agent" in cmd
        assert "my-agent" in cmd


class TestStartSyncBackendDispatch:
    def _dispatch(self, argv: list[str]) -> list[tuple[str, str, str]]:
        calls: list[tuple[str, str, str]] = []

        def fake_run(script: Path, target: str, agent: str) -> int:
            calls.append((Path(script).name, target, agent))
            return 0

        with (
            patch.object(start_sync, "_run", side_effect=fake_run),
            patch.object(sys, "argv", ["start_sync.py"] + argv),
        ):
            start_sync.main()

        return calls

    def test_db_backend_calls_start_db_only(self):
        calls = self._dispatch(["db", "agent-factory"])
        scripts = [s for s, _, _ in calls]
        assert "start_db.py" in scripts
        assert "start_git.py" not in scripts

    def test_git_backend_calls_start_git_only(self):
        calls = self._dispatch(["git", "agent-factory"])
        scripts = [s for s, _, _ in calls]
        assert "start_git.py" in scripts
        assert "start_db.py" not in scripts

    def test_all_backend_calls_both(self):
        calls = self._dispatch(["all", "agent-factory"])
        scripts = [s for s, _, _ in calls]
        assert "start_db.py" in scripts
        assert "start_git.py" in scripts

    def test_non_backend_first_arg_treated_as_target(self):
        calls = self._dispatch(["agent-factory"])
        targets = [t for _, t, _ in calls]
        assert all(t == "agent-factory" for t in targets)
        assert len(calls) == 2  # both db and git

    def test_no_args_defaults_to_all_backend(self):
        calls = self._dispatch([])
        scripts = [s for s, _, _ in calls]
        assert "start_db.py" in scripts
        assert "start_git.py" in scripts
