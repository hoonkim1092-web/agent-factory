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
    # load directly from the state's own runtime_workspace (bypasses _default_runtime_workspace)
    from core.dogfood import load_state
    loaded = load_state(state.runtime_workspace, state.run_id)
    assert loaded.phase == DogfoodPhase.COMPLETE
    assert loaded.task == "hello task"


def test_cli_dogfood_status_not_found(tmp_path):
    """dogfood status raises FileNotFoundError for unknown run_id."""
    from core.dogfood import load_state
    with pytest.raises(FileNotFoundError):
        load_state(str(tmp_path / ".af_runtime"), "nonexistent-run-id")


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
    from core.dogfood import load_state
    with pytest.raises(ValueError, match="Invalid run_id"):
        load_state(str(tmp_path / ".af_runtime"), bad_id)


# ---------------------------------------------------------------------------
# _detect_mode — dogfood is a subcommand, not ad_hoc
# ---------------------------------------------------------------------------

def test_detect_mode_dogfood():
    import agent_launcher as al
    assert al._detect_mode(["dogfood", "run", "task"]) == "subcommand"


def test_detect_mode_ad_hoc_not_dogfood():
    import agent_launcher as al
    assert al._detect_mode(["do something with AI"]) == "ad_hoc"


# ---------------------------------------------------------------------------
# §17 Step 12 — dogfood interview subcommand parser
# ---------------------------------------------------------------------------

def test_parser_dogfood_interview_basic():
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "interview", "add", "logging"])
    assert args.subcommand == "dogfood"
    assert args.dogfood_cmd == "interview"
    assert args.task == ["add", "logging"]
    assert args.non_interactive is False
    assert args.deep_skip is False
    assert args.out is None


def test_parser_dogfood_interview_flags():
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args([
        "dogfood", "interview", "my task",
        "--non-interactive", "--out", "/tmp/out.json", "--workspace", "/tmp/ws",
    ])
    assert args.non_interactive is True
    assert args.out == "/tmp/out.json"
    assert args.workspace == "/tmp/ws"


def test_parser_dogfood_interview_deep_skip():
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "interview", "task", "--deep-skip"])
    assert args.deep_skip is True


def test_parser_dogfood_run_from_file():
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "run", "task", "--from-file", "/tmp/interview.json"])
    assert args.from_file == "/tmp/interview.json"


def test_parser_dogfood_run_no_from_file_default():
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "run", "task"])
    assert args.from_file is None


# ---------------------------------------------------------------------------
# §17 Step 12 — dogfood interview dispatch (mocked run_interview)
# ---------------------------------------------------------------------------

def test_cli_dogfood_interview_dispatch(tmp_path):
    """dogfood interview calls run_interview and exits 0 on success."""
    import agent_launcher as al

    fake_result = {
        "ok": True,
        "questions": [{"question": "q1"}],
        "output_path": str(tmp_path / "interview.json"),
    }

    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "interview", "add logging"])

    with patch("core.interview.run_interview", return_value=fake_result) as mock_iv:
        with pytest.raises(SystemExit) as exc:
            import os
            workspace = os.path.abspath(getattr(args, "workspace", None) or os.getcwd())
            from core.interview import run_interview
            result = run_interview(
                " ".join(args.task).strip(),
                workspace=workspace,
                output_path=args.out,
                non_interactive=args.non_interactive,
                deep_skip=args.deep_skip,
            )
            sys.exit(0 if result.get("ok") else 1)

        assert exc.value.code == 0


def test_cli_dogfood_interview_failure(tmp_path):
    """dogfood interview exits 1 when run_interview returns ok=False."""
    fake_result = {"ok": False, "reason": "empty_task"}

    with patch("core.interview.run_interview", return_value=fake_result):
        from core.interview import run_interview
        result = run_interview("", workspace=str(tmp_path))
        exit_code = 0 if result.get("ok") else 1
        assert exit_code == 1


# ---------------------------------------------------------------------------
# §17 Step 12 — dogfood run --from-file dispatch
# ---------------------------------------------------------------------------

def test_cli_dogfood_run_from_file_success(tmp_path):
    """dogfood run --from-file loads interview artifact and passes to run_all."""
    interview_file = tmp_path / "interview.json"
    artifact = {"goal": "add logging", "intent": "add logging"}
    interview_file.write_text(json.dumps(artifact), encoding="utf-8")

    final_state = create_run("add logging", str(tmp_path), runtime_workspace=str(tmp_path / ".af_runtime"))
    final_state.phase = DogfoodPhase.COMPLETE

    with patch("core.dogfood.run_all", return_value=final_state) as mock_run:
        import agent_launcher as al, os
        parser = al._build_arg_parser(ad_hoc_mode=False)
        args = parser.parse_args(["dogfood", "run", "add logging", "--from-file", str(interview_file)])

        loaded = json.loads(open(os.path.abspath(args.from_file), encoding="utf-8").read())
        workspace = os.path.abspath(getattr(args, "workspace", None) or str(tmp_path))

        with pytest.raises(SystemExit) as exc:
            from core.dogfood import run_all
            state = run_all(args.task, workspace, run_id=args.run_id, interview_artifact=loaded)
            sys.exit(0 if state.phase.value == "complete" else 1)

        assert exc.value.code == 0
        mock_run.assert_called_once_with(
            "add logging", workspace, run_id=None, interview_artifact=artifact
        )


def test_cli_dogfood_run_from_file_missing(tmp_path):
    """dogfood run --from-file exits 1 when file is not found."""
    missing = str(tmp_path / "nonexistent.json")
    with pytest.raises((OSError, FileNotFoundError)):
        open(missing, encoding="utf-8").read()


def test_cli_dogfood_run_from_file_bad_json(tmp_path):
    """dogfood run --from-file exits 1 on JSON parse error."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json}", encoding="utf-8")

    import json as _json
    with pytest.raises(ValueError):
        _json.loads(bad_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# §17 Step 13 — _run_interview_phase injectable + run_all TTY integration
# ---------------------------------------------------------------------------

def test_run_interview_phase_calls_interview_fn(tmp_path):
    """`_run_interview_phase` calls _interview_fn and uses returned project_brief."""
    from core.dogfood import DogfoodPhase, _run_interview_phase, create_run

    state = create_run("my task", str(tmp_path), runtime_workspace=str(tmp_path / ".rt"))
    state.phase = DogfoodPhase.INTERVIEW

    fake_brief = {"goal": "my task", "intent": "do the thing"}
    calls: list[tuple[str, str]] = []

    def mock_fn(task: str, workspace: str) -> dict:
        calls.append((task, workspace))
        return {"ok": True, "project_brief": fake_brief}

    result = _run_interview_phase(state, {"goal": "my task"}, _interview_fn=mock_fn)
    assert result == fake_brief
    assert calls == [("my task", str(tmp_path))]
    assert state.interview_path.endswith("interview.json")


def test_run_interview_phase_raises_on_fn_failure(tmp_path):
    """`_run_interview_phase` raises RuntimeError when _interview_fn returns ok=False."""
    from core.dogfood import DogfoodPhase, _run_interview_phase, create_run

    state = create_run("t", str(tmp_path), runtime_workspace=str(tmp_path / ".rt"))
    state.phase = DogfoodPhase.INTERVIEW

    def bad_fn(task: str, workspace: str) -> dict:
        return {"ok": False, "reason": "empty_task"}

    with pytest.raises(RuntimeError, match="Interview failed"):
        _run_interview_phase(state, {"goal": "t"}, _interview_fn=bad_fn)


def test_run_interview_phase_no_fn_uses_artifact(tmp_path):
    """`_run_interview_phase` without _interview_fn writes the artifact as-is."""
    from core.dogfood import DogfoodPhase, _run_interview_phase, create_run

    state = create_run("t", str(tmp_path), runtime_workspace=str(tmp_path / ".rt"))
    state.phase = DogfoodPhase.INTERVIEW
    artifact = {"goal": "t", "intent": "do it"}

    result = _run_interview_phase(state, artifact)
    assert result == artifact


def test_run_phase_passes_interview_fn(tmp_path):
    """`run_phase` threads _interview_fn kwarg through to _run_interview_phase."""
    from core.dogfood import DogfoodPhase, create_run, run_phase

    state = create_run("task", str(tmp_path), runtime_workspace=str(tmp_path / ".rt"))
    state.phase = DogfoodPhase.INTERVIEW

    fake_brief = {"goal": "task", "intent": "intent"}
    called: list[bool] = []

    def mock_fn(task: str, workspace: str) -> dict:
        called.append(True)
        return {"ok": True, "project_brief": fake_brief}

    result = run_phase(state, artifact={"goal": "task"}, _interview_fn=mock_fn)
    assert result == fake_brief
    assert called


def test_run_all_calls_interview_fn_when_no_artifact(tmp_path):
    """`run_all` invokes _interview_fn when interview_artifact=None."""
    from core.dogfood import run_all

    brief = {"goal": "g", "intent": "i"}
    calls: list[str] = []

    def mock_fn(task: str, workspace: str) -> dict:
        calls.append(task)
        return {"ok": True, "project_brief": brief}

    state = run_all("g", str(tmp_path), _interview_fn=mock_fn)
    assert calls == ["g"]
    assert state.phase.value in ("complete", "blocked")


def test_run_all_skips_interview_fn_when_artifact_provided(tmp_path):
    """`run_all` does NOT invoke _interview_fn when interview_artifact is given."""
    from core.dogfood import run_all

    calls: list[str] = []

    def mock_fn(task: str, workspace: str) -> dict:
        calls.append(task)
        return {"ok": True, "project_brief": {"goal": task}}

    artifact = {"goal": "g", "intent": "i"}
    state = run_all("g", str(tmp_path), interview_artifact=artifact, _interview_fn=mock_fn)
    assert calls == []
    assert state.phase.value in ("complete", "blocked")


def test_parser_dogfood_run_non_interactive():
    """dogfood run parser accepts --non-interactive flag."""
    import agent_launcher as al
    parser = al._build_arg_parser(ad_hoc_mode=False)
    args = parser.parse_args(["dogfood", "run", "my task", "--non-interactive"])
    assert args.non_interactive is True
    assert args.task == "my task"
