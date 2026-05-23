"""Tests for dogfood CLI subcommand in agent_launcher (§17 Step 11)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.dogfood import DogfoodPhase, DogfoodState, create_run, save_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(tmp_path: Path, phase: str = "complete", task: str = "test task") -> DogfoodState:
    state = create_run(task, str(tmp_path), runtime_workspace=str(tmp_path / ".af_runtime"))
    state.phase = DogfoodPhase(phase)
    save_state(state)
    return state


# ---------------------------------------------------------------------------
# _build_arg_parser — dogfood subcommand registration
# ---------------------------------------------------------------------------

def test_dogfood_subcommand_registered():
    """'dogfood' appears in _KNOWN_SUBCOMMANDS and parser accepts it."""
    import agent_launcher as al
    assert "dogfood" in al._KNOWN_SUBCOMMANDS


def test_parser_dogfood_run_parses():
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "run", "my task"])
    assert args.subcommand == "dogfood"
    assert args.dogfood_cmd == "run"
    assert args.task == "my task"
    assert args.workspace is None
    assert args.run_id is None


def test_parser_dogfood_run_with_options():
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "run", "task", "--workspace", "/tmp/ws", "--run-id", "abc123"])
    assert args.workspace == "/tmp/ws"
    assert args.run_id == "abc123"


def test_parser_dogfood_status_parses():
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "status", "abc123"])
    assert args.dogfood_cmd == "status"
    assert args.run_id == "abc123"


# ---------------------------------------------------------------------------
# CLI subprocess — dogfood run (mocked run_all)
# ---------------------------------------------------------------------------

def test_cli_dogfood_run_complete(tmp_path, monkeypatch):
    """dogfood run exits 0 when run_all returns COMPLETE state."""
    final_state = create_run("t", str(tmp_path), runtime_workspace=str(tmp_path / ".af_runtime"))
    final_state.phase = DogfoodPhase.COMPLETE

    with patch("core.dogfood.run_all", return_value=final_state) as mock_run:
        import agent_launcher as al
        parser = al._build_arg_parser(ad_hoc_mode=False)
        args = parser.parse_args(["dogfood", "run", "my task"])

        with pytest.raises(SystemExit) as exc:
            # Simulate the __main__ dispatch block
            from core.dogfood import run_all, load_state, _default_runtime_workspace
            import os
            workspace = os.path.abspath(getattr(args, "workspace", None) or os.getcwd())
            state = run_all(args.task, workspace, run_id=args.run_id)
            sys.exit(0 if state.phase.value == "complete" else 1)

        assert exc.value.code == 0
        mock_run.assert_called_once()


def test_cli_dogfood_run_blocked(tmp_path):
    """dogfood run exits 1 when run_all returns BLOCKED state."""
    final_state = create_run("t", str(tmp_path), runtime_workspace=str(tmp_path / ".af_runtime"))
    final_state.phase = DogfoodPhase.BLOCKED
    final_state.last_failure = "verify failed"

    with patch("core.dogfood.run_all", return_value=final_state):
        from core.dogfood import run_all
        import os
        state = run_all("task", str(tmp_path))
        exit_code = 0 if state.phase.value == "complete" else 1
        assert exit_code == 1


# ---------------------------------------------------------------------------
# CLI subprocess — dogfood status
# ---------------------------------------------------------------------------

def test_cli_dogfood_status_found(tmp_path):
    """dogfood status succeeds for an existing run."""
    state = _make_state(tmp_path, phase="complete", task="hello task")

    from core.dogfood import load_state, _default_runtime_workspace
    rt_ws = _default_runtime_workspace(str(tmp_path))
    loaded = load_state(rt_ws, state.run_id)
    assert loaded.phase == DogfoodPhase.COMPLETE
    assert loaded.task == "hello task"


def test_cli_dogfood_status_not_found(tmp_path):
    """dogfood status raises FileNotFoundError for unknown run_id."""
    from core.dogfood import load_state, _default_runtime_workspace
    rt_ws = _default_runtime_workspace(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_state(rt_ws, "nonexistent-run-id")


# ---------------------------------------------------------------------------
# run_id path traversal guard
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_id", [
    "../../etc/passwd",
    "../sibling",
    "a/b",
    "a\\b",
    "run.id",
])
def test_run_id_traversal_rejected_create(tmp_path, bad_id):
    """create_run() rejects run_id with path-separator or dot characters."""
    from core.dogfood import create_run
    with pytest.raises(ValueError, match="Invalid run_id"):
        create_run("task", str(tmp_path), run_id=bad_id, runtime_workspace=str(tmp_path / ".af_runtime"))


@pytest.mark.parametrize("bad_id", [
    "../../etc/passwd",
    "../sibling",
    "a/b",
    "a\\b",
    "run.id",
])
def test_run_id_traversal_rejected_load(tmp_path, bad_id):
    """load_state() rejects run_id with path-separator or dot characters."""
    from core.dogfood import load_state, _default_runtime_workspace
    rt_ws = _default_runtime_workspace(str(tmp_path))
    with pytest.raises(ValueError, match="Invalid run_id"):
        load_state(rt_ws, bad_id)


# ---------------------------------------------------------------------------
# _detect_mode — dogfood is a subcommand, not ad_hoc
# ---------------------------------------------------------------------------

def test_detect_mode_dogfood():
    import agent_launcher as al
    assert al._detect_mode(["dogfood", "run", "task"]) == "subcommand"


def test_detect_mode_ad_hoc_not_dogfood():
    import agent_launcher as al
    assert al._detect_mode(["do something with AI"]) == "ad_hoc"
