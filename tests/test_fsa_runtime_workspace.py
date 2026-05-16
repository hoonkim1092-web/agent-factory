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
