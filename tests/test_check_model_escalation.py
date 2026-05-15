"""Tests for scripts/check_model_escalation.py (P4.5b hook)."""
from __future__ import annotations

import sys


def test_main_returns_early_when_frozen(monkeypatch):
    """Frozen build environment: main() must exit immediately without import attempts."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    import importlib
    import scripts.check_model_escalation as m
    importlib.reload(m)
    # Must not raise; frozen guard returns before any sys.path manipulation
    m.main()
    monkeypatch.delattr(sys, "frozen", raising=False)


def test_main_runs_without_error_when_no_pending_state(tmp_path, monkeypatch):
    """Normal (non-frozen) run with no pending state: exits silently."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    import scripts.check_model_escalation as m
    import sys as _sys
    import subprocess

    monkeypatch.setattr(
        m, "_detect_workspace", lambda: str(tmp_path), raising=False
    )

    import importlib
    importlib.reload(m)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    m.main()  # no pending state → silent return


def test_main_prints_escalation_when_pending(tmp_path, monkeypatch, capsys):
    """When pending escalation exists, main() prints a recommendation."""
    import importlib
    import scripts.check_model_escalation as m
    importlib.reload(m)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))

    from scripts.agent_model_selector import store_pending_escalation
    store_pending_escalation(str(tmp_path), "af-test-runner", "sonnet", ["test_failure"])

    m.main()
    captured = capsys.readouterr()
    assert "model-escalation" in captured.out
    assert "sonnet" in captured.out
    assert "test_failure" in captured.out


def test_main_clears_pending_after_print(tmp_path, monkeypatch):
    """After surfacing, pending state must be cleared (one-shot)."""
    import importlib
    import scripts.check_model_escalation as m
    importlib.reload(m)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))

    from scripts.agent_model_selector import store_pending_escalation, get_pending_escalation
    store_pending_escalation(str(tmp_path), "af-critic", "opus", ["core_policy_change"])

    m.main()
    assert get_pending_escalation(str(tmp_path)) is None


def test_main_frozen_build_does_not_clear_pending(tmp_path, monkeypatch):
    """Frozen build early-exit must NOT consume the pending escalation state.

    dist/af/af.exe (PyInstaller frozen build) should not interfere with hook state.
    """
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    from scripts.agent_model_selector import store_pending_escalation, get_pending_escalation
    store_pending_escalation(str(tmp_path), "af-test-runner", "sonnet", ["test_failure"])

    import importlib
    import scripts.check_model_escalation as m
    importlib.reload(m)
    m.main()

    # State must still be there (frozen path exited before clear)
    assert get_pending_escalation(str(tmp_path)) is not None
    monkeypatch.delattr(sys, "frozen", raising=False)
