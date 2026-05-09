"""tests/test_hook_runner_builtins.py — Stage 1 builtin dispatch unit tests."""
import importlib
import io
import json
import os
import sys
import time
from pathlib import Path


def _runner():
    import scripts.hook_runner as m
    importlib.reload(m)
    return m


def _payload(file_path: str) -> dict:
    return {"tool_input": {"file_path": file_path}}


# ── _extract_file_path ────────────────────────────────────────────────────────

def test_extract_file_path_normal():
    m = _runner()
    assert m._extract_file_path({"tool_input": {"file_path": "core/foo.py"}}) == "core/foo.py"


def test_extract_file_path_missing_tool_input():
    m = _runner()
    assert m._extract_file_path({}) == ""


def test_extract_file_path_empty_string():
    m = _runner()
    assert m._extract_file_path({"tool_input": {"file_path": ""}}) == ""


def test_extract_file_path_none_value():
    m = _runner()
    assert m._extract_file_path({"tool_input": {"file_path": None}}) == ""


# ── _read_hook_stdin_once ────────────────────────────────────────────────────

def test_read_hook_stdin_valid_json(monkeypatch):
    m = _runner()
    payload = {"tool_input": {"file_path": "core/x.py"}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    result = m._read_hook_stdin_once()
    assert result == payload


def test_read_hook_stdin_invalid_json(monkeypatch):
    m = _runner()
    monkeypatch.setattr("sys.stdin", io.StringIO("not-json"))
    result = m._read_hook_stdin_once()
    assert result == {}


def test_read_hook_stdin_empty(monkeypatch):
    m = _runner()
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    result = m._read_hook_stdin_once()
    assert result == {}


# ── post_edit_py_compile ──────────────────────────────────────────────────────

def test_py_compile_non_py_file():
    m = _runner()
    assert m._post_edit_py_compile({"tool_input": {"file_path": "docs/x.md"}}) == 0


def test_py_compile_empty_path():
    m = _runner()
    assert m._post_edit_py_compile({}) == 0


def test_py_compile_valid_file(tmp_path):
    m = _runner()
    f = tmp_path / "ok.py"
    f.write_text("x = 1\n")
    assert m._post_edit_py_compile({"tool_input": {"file_path": str(f)}}) == 0


def test_py_compile_syntax_error(tmp_path, capsys, monkeypatch):
    m = _runner()
    f = tmp_path / "bad.py"
    f.write_text("def (:\n")

    import subprocess as sp

    def fake_run(args, **kwargs):
        assert args[:3] == [sys.executable, "-m", "py_compile"]
        class R:
            returncode = 1
            stderr = "SyntaxError: invalid syntax"
        return R()

    monkeypatch.setattr(sp, "run", fake_run)
    m._post_edit_py_compile({"tool_input": {"file_path": str(f)}})
    captured = capsys.readouterr()
    assert "[af-hook] syntax error" in captured.err


# ── post_edit_enqueue ─────────────────────────────────────────────────────────

def test_enqueue_non_py_file(tmp_path):
    m = _runner()
    assert m._post_edit_enqueue({"tool_input": {"file_path": "README.md"}}) == 0


def test_enqueue_calls_script_for_py(monkeypatch, tmp_path):
    """enqueue builtin calls enqueue_agent_review.py with the file path."""
    m = _runner()
    called_args = []

    import subprocess as sp

    def fake_run(args, **kwargs):
        called_args.extend(args)
        class R:
            returncode = 0
        return R()

    monkeypatch.setattr(sp, "run", fake_run)
    m._post_edit_enqueue({"tool_input": {"file_path": "core/foo.py"}})
    assert any("enqueue_agent_review" in a for a in called_args)
    assert "core/foo.py" in called_args


# ── BUILTINS dispatch table ───────────────────────────────────────────────────

def test_builtins_keys_present():
    m = _runner()
    expected = {
        "post_edit_py_compile",
        "post_edit_enqueue",
        "post_edit_code_review",
        "post_edit_blueprint",
        "post_edit_design_review",
        "post_edit_test",
        "pre_bash_review_gate",
        "post_agent_record",
        "post_commit_clear",
    }
    assert expected == set(m._BUILTINS.keys())


def test_main_dispatches_builtin(monkeypatch, tmp_path):
    """main() routes post_edit_* to builtin, not _resolve_script."""
    m = _runner()
    dispatched = []

    def fake_builtin(payload):
        dispatched.append(payload)
        return 0

    monkeypatch.setitem(m._BUILTINS, "post_edit_py_compile", fake_builtin)
    monkeypatch.setattr(sys, "argv", ["hook_runner.py", "post_edit_py_compile"])
    payload = {"tool_input": {"file_path": "core/x.py"}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    result = m.main()
    assert result == 0
    assert dispatched == [payload]


def test_main_falls_through_for_unknown_cmd(monkeypatch, tmp_path):
    """main() with unknown command falls through to script-resolve path (returns 0 if script missing)."""
    m = _runner()
    monkeypatch.setattr(sys, "argv", ["hook_runner.py", "nonexistent_script_xyz"])
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    result = m.main()
    assert result == 0


# ── _log_hook_event ───────────────────────────────────────────────────────────

def test_log_hook_event_creates_log(tmp_path, monkeypatch):
    m = _runner()
    monkeypatch.setattr(m, "_project_root", lambda: str(tmp_path))
    m._log_hook_event("post_edit_enqueue", "core/x.py", 0)
    log = tmp_path / ".af_review_queue" / "hook_events.log"
    assert log.exists()
    content = log.read_text()
    assert "post_edit_enqueue" in content
    assert "core/x.py" in content
    assert "|0|" in content


def test_log_hook_event_silently_swallows_errors(monkeypatch):
    """_log_hook_event must not raise even if dir creation fails."""
    m = _runner()
    monkeypatch.setattr(m, "_project_root", lambda: "/nonexistent/path/xyz")
    m._log_hook_event("post_edit_enqueue", "core/x.py", 1, error="boom")


def test_post_agent_record_forces_fail_when_test_gap_analyzer_fails(monkeypatch, tmp_path):
    m = _runner()
    recorded = []

    monkeypatch.setattr(m, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))

    import scripts.review_gate as rg
    import scripts.test_gap_analyzer as tga

    monkeypatch.setattr(rg, "record_review_done", lambda workspace, agent, tier, verdict: recorded.append((workspace, agent, tier, verdict)))
    monkeypatch.setattr(tga, "changed_files_from_pending", lambda workspace: ["core/providers/cli.py"])
    monkeypatch.setattr(tga, "changed_files_from_git", lambda workspace: [])
    monkeypatch.setattr(tga, "git_diff", lambda workspace, changed: "diff --git a/core/providers/cli.py b/core/providers/cli.py\n+shlex.split(raw)\n")

    def fake_analyze_diff(*, workspace, changed_files, diff_text):
        return tga.TestGapReport(
            verdict="FAIL",
            gaps=[
                tga.TestGap(
                    risk_id="cross_platform_quoted_path_subprocess",
                    severity="FAIL",
                    changed_file="core/providers/cli.py",
                    reason="missing representative test",
                    expected_test_evidence="add cross-platform quoted path cases",
                )
            ],
        )

    monkeypatch.setattr(tga, "analyze_diff", fake_analyze_diff)

    payload = {
        "tool_input": {"subagent_type": "af-test-runner"},
        "tool_response": {"content": "Verdict: PASS\nall tests passed"},
    }

    assert m._post_agent_record(payload) == 0
    assert recorded == [(str(tmp_path), "af-test-runner", 1, "fail")]
    report_path = Path(tmp_path) / ".af_review_queue" / "test_gap_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["verdict"] == "FAIL"
    assert report["gaps"][0]["risk_id"] == "cross_platform_quoted_path_subprocess"


def test_post_agent_record_keeps_verdict_when_test_gap_analyzer_passes(monkeypatch, tmp_path):
    m = _runner()
    recorded = []

    monkeypatch.setattr(m, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))

    import scripts.review_gate as rg
    import scripts.test_gap_analyzer as tga

    monkeypatch.setattr(rg, "record_review_done", lambda workspace, agent, tier, verdict: recorded.append((workspace, agent, tier, verdict)))
    monkeypatch.setattr(tga, "changed_files_from_pending", lambda workspace: ["core/a.py"])
    monkeypatch.setattr(tga, "changed_files_from_git", lambda workspace: [])
    monkeypatch.setattr(tga, "git_diff", lambda workspace, changed: "")
    monkeypatch.setattr(tga, "analyze_diff", lambda *, workspace, changed_files, diff_text: tga.TestGapReport(verdict="PASS"))

    payload = {
        "tool_input": {"subagent_type": "af-test-runner"},
        "tool_response": {"content": "Verdict: PASS\nall tests passed"},
    }

    assert m._post_agent_record(payload) == 0
    assert recorded == [(str(tmp_path), "af-test-runner", 1, "pass")]


def test_post_agent_record_clears_stale_test_gap_report_when_analyzer_passes(monkeypatch, tmp_path):
    m = _runner()
    recorded = []

    stale_dir = Path(tmp_path) / ".af_review_queue"
    stale_dir.mkdir()
    stale_report = stale_dir / "test_gap_report.json"
    stale_report.write_text('{"verdict":"FAIL"}', encoding="utf-8")

    monkeypatch.setattr(m, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))

    import scripts.review_gate as rg
    import scripts.test_gap_analyzer as tga

    monkeypatch.setattr(rg, "record_review_done", lambda workspace, agent, tier, verdict: recorded.append((workspace, agent, tier, verdict)))
    monkeypatch.setattr(tga, "changed_files_from_pending", lambda workspace: ["core/a.py"])
    monkeypatch.setattr(tga, "changed_files_from_git", lambda workspace: [])
    monkeypatch.setattr(tga, "git_diff", lambda workspace, changed: "")
    monkeypatch.setattr(tga, "analyze_diff", lambda *, workspace, changed_files, diff_text: tga.TestGapReport(verdict="PASS"))

    payload = {
        "tool_input": {"subagent_type": "af-test-runner"},
        "tool_response": {"content": "Verdict: PASS\nall tests passed"},
    }

    assert m._post_agent_record(payload) == 0
    assert recorded == [(str(tmp_path), "af-test-runner", 1, "pass")]
    assert not stale_report.exists()


def test_apply_test_gap_verdict_does_not_modify_blast_tier_on_fail(monkeypatch, tmp_path):
    """test-gap analyzer FAIL → verdict=fail 강제, blast_tier는 변경하지 않는다 (Phase 1).

    blast_tier는 blast_radius.py + enqueue max-merge만 결정한다.
    """
    m = _runner()

    queue_dir = tmp_path / ".af_review_queue"
    queue_dir.mkdir()
    pending = queue_dir / "pending_agent_review.json"
    pending.write_text(
        json.dumps({"files": ["core/foo.py"], "blast_tier": 3, "reviews": {}}),
        encoding="utf-8",
    )

    import scripts.test_gap_analyzer as tga

    monkeypatch.setattr(tga, "changed_files_from_pending", lambda workspace: ["core/foo.py"])
    monkeypatch.setattr(tga, "changed_files_from_git", lambda workspace: [])
    monkeypatch.setattr(tga, "git_diff", lambda workspace, changed: "diff ...\n+shlex.split(x)\n")

    def fake_analyze(*, workspace, changed_files, diff_text):
        return tga.TestGapReport(
            verdict="FAIL",
            gaps=[tga.TestGap(
                risk_id="cross_platform_quoted_path_subprocess",
                severity="FAIL",
                changed_file="core/foo.py",
                reason="test",
                expected_test_evidence="add",
            )],
        )

    monkeypatch.setattr(tga, "analyze_diff", fake_analyze)
    monkeypatch.setattr(m, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))

    result = m._apply_test_gap_verdict(str(tmp_path), "pass")
    assert result == "fail"

    state = json.loads(pending.read_text(encoding="utf-8"))
    assert state["blast_tier"] == 3  # Phase 1: blast_tier must be unchanged
