from __future__ import annotations

from core.fsa_loop import FSALoop
from core.ise_loop import ISELoop


class _DummyRunner:
    def run(self, agent, task_input, run_id=None, auto_approve=False, workspace=None, runtime_workspace=None):
        return {
            "ok": True,
            "workspace": workspace,
            "runtime_workspace": runtime_workspace,
        }


class _InfraFailRunner:
    """Always returns an INFRA failure (auth_expired) to exercise the early-exit path."""

    def __init__(self):
        self.call_count = 0

    def run(self, agent, task_input, run_id=None, auto_approve=False, workspace=None, runtime_workspace=None):
        self.call_count += 1
        return {"ok": False, "reason": "auth_expired"}


def test_fsa_saves_ledger_under_runtime_workspace(tmp_path):
    workspace = tmp_path / "repo"
    runtime_ws = tmp_path / "runtime"
    workspace.mkdir()
    runtime_ws.mkdir()

    fsa = FSALoop(_DummyRunner())
    result = fsa.run_mission(
        agent={"name": "Dev"},
        task_input="finish task",
        run_id="run_fsa",
        workspace=str(workspace),
        runtime_workspace=str(runtime_ws),
        initial_failure_result={"ok": True, "reason": "already_fixed"},
    )

    assert result["ok"] is True
    assert (runtime_ws / ".af" / "ise_ledger_run_fsa.json").exists()
    assert not (workspace / ".af").exists()


def test_fsa_infra_failure_exits_immediately(tmp_path):
    """INFRA failure (auth_expired) must cause FSA to exit after the first cycle,
    not retry up to max_cycles times."""
    workspace = tmp_path / "repo"
    runtime_ws = tmp_path / "runtime"
    workspace.mkdir()
    runtime_ws.mkdir()

    runner = _InfraFailRunner()
    fsa = FSALoop(runner)
    result = fsa.run_mission(
        agent={"name": "Dev"},
        task_input="some task",
        run_id="run_infra",
        workspace=str(workspace),
        runtime_workspace=str(runtime_ws),
    )

    assert result["ok"] is False
    assert "auth_expired" in result["reason"]
    # Must exit after first cycle — not max_cycles (5) retries.
    assert runner.call_count == 1, (
        f"INFRA failure must stop FSA immediately; got {runner.call_count} calls"
    )


def test_ise_loop_forwards_runtime_workspace(tmp_path):
    workspace = tmp_path / "repo"
    runtime_ws = tmp_path / "runtime"
    workspace.mkdir()
    runtime_ws.mkdir()

    runner = _DummyRunner()
    ise = ISELoop(fsa_loop=FSALoop(runner), runner=runner)
    result = ise.run_mission(
        agent={"name": "Dev"},
        task_input="finish task",
        run_id="run_ise",
        workspace=str(workspace),
        runtime_workspace=str(runtime_ws),
        initial_failure_result={"ok": True, "reason": "already_fixed"},
    )

    assert result["ok"] is True
    assert (runtime_ws / ".af" / "ise_ledger_run_ise.json").exists()
    assert not (workspace / ".af").exists()
