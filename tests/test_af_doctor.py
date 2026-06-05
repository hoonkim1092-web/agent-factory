"""tests/test_af_doctor.py — scripts/af_doctor.py 단위 테스트."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.af_doctor import (
    DoctorResult,
    _exit_code,
    check_dogfood_root,
    check_git,
    check_git_dirty,
    check_hooks,
    check_providers,
    check_pytest,
    check_python,
    format_json,
    format_text,
    run_checks,
)


# ---------------------------------------------------------------------------
# check_python
# ---------------------------------------------------------------------------

def test_check_python_always_ok():
    r = check_python()
    assert r.status == "ok"
    assert r.name == "python"
    assert sys.version.split()[0] in r.detail


# ---------------------------------------------------------------------------
# check_git
# ---------------------------------------------------------------------------

def test_check_git_ok(monkeypatch):
    mock = MagicMock()
    mock.returncode = 0
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock)
    r = check_git()
    assert r.status == "ok"


def test_check_git_fail_not_repo(monkeypatch):
    mock = MagicMock()
    mock.returncode = 128
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock)
    r = check_git()
    assert r.status == "fail"


def test_check_git_fail_no_git(monkeypatch):
    def raise_fnf(*a, **kw):
        raise FileNotFoundError
    monkeypatch.setattr(subprocess, "run", raise_fnf)
    r = check_git()
    assert r.status == "fail"
    assert "미설치" in r.detail


# ---------------------------------------------------------------------------
# check_git_dirty
# ---------------------------------------------------------------------------

def test_check_git_dirty_clean(monkeypatch):
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = ""
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock)
    r = check_git_dirty()
    assert r.status == "ok"
    assert "clean" in r.detail


def test_check_git_dirty_has_changes(monkeypatch):
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = " M core/foo.py\n?? bar.py\n"
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock)
    r = check_git_dirty()
    assert r.status == "warn"
    assert "2" in r.detail


def test_check_git_dirty_subprocess_fail(monkeypatch):
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = ""
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock)
    r = check_git_dirty()
    assert r.status == "warn"


# ---------------------------------------------------------------------------
# check_providers — fast mode
# ---------------------------------------------------------------------------

def test_check_providers_fast_installed():
    with patch("core.providers.registry.detect_installed_cli_providers", return_value=["claude_cli"]):
        results = check_providers(fast=True)
    assert len(results) == 1
    assert results[0].status == "ok"
    assert "claude_cli" in results[0].detail


def test_check_providers_fast_none_installed(monkeypatch):
    with patch("core.providers.registry.detect_installed_cli_providers", return_value=[]):
        results = check_providers(fast=True)
    assert results[0].status == "warn"


# ---------------------------------------------------------------------------
# check_providers — normal mode
# ---------------------------------------------------------------------------

def test_check_providers_normal_available():
    from core.provider_detect import ProviderProbeResult, ProviderState
    probe_avail = ProviderProbeResult(
        provider_id="claude_cli",
        state=ProviderState.AVAILABLE,
        checked_at="2026-01-01T00:00:00",
    )
    probe_expired = ProviderProbeResult(
        provider_id="gemini_cli",
        state=ProviderState.AUTH_EXPIRED,
        checked_at="2026-01-01T00:00:00",
    )
    probe_missing = ProviderProbeResult(
        provider_id="codex_cli",
        state=ProviderState.NOT_INSTALLED,
        checked_at="2026-01-01T00:00:00",
    )
    fake_states = {
        "claude_cli": probe_avail,
        "gemini_cli": probe_expired,
        "codex_cli": probe_missing,
    }
    with patch("core.provider_detect.detect_provider_states", return_value=fake_states):
        results = check_providers()

    statuses = {r.name: r.status for r in results}
    assert statuses["provider_claude_cli"] == "ok"
    assert statuses["provider_gemini_cli"] == "warn"
    assert statuses["provider_codex_cli"] == "warn"
    assert "재인증" in next(r.fix_hint for r in results if r.name == "provider_gemini_cli")


# ---------------------------------------------------------------------------
# check_hooks
# ---------------------------------------------------------------------------

def test_check_hooks_git_config(monkeypatch, tmp_path):
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "pre-commit").write_text("#!/bin/sh\n")

    def fake_run(cmd, **kw):
        m = MagicMock()
        if "config" in cmd:
            m.returncode = 0
            m.stdout = str(hooks_dir)
        else:
            m.returncode = 0
            m.stdout = ""
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)
    r = check_hooks()
    assert r.status == "ok"


def test_check_hooks_missing(monkeypatch, tmp_path, monkeypatch_cwd=None):
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = ""
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock)
    # .githooks가 없는 tmp_path 기준 — 실제 cwd에 있을 수 있으므로 Path 패치
    monkeypatch.setattr("scripts.af_doctor.Path", lambda *a: MagicMock(is_dir=lambda: False, iterdir=lambda: []))
    r = check_hooks()
    assert r.status == "warn"


# ---------------------------------------------------------------------------
# check_pytest
# ---------------------------------------------------------------------------

def test_check_pytest_installed(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/pytest")
    r = check_pytest()
    assert r.status == "ok"
    assert "/usr/bin/pytest" in r.detail


def test_check_pytest_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    r = check_pytest()
    assert r.status == "warn"
    assert "pip install pytest" in r.fix_hint


# ---------------------------------------------------------------------------
# check_dogfood_root
# ---------------------------------------------------------------------------

def test_check_dogfood_root_exists(monkeypatch, tmp_path):
    dogfood_root = tmp_path / ".af-dogfood"
    dogfood_root.mkdir()
    (dogfood_root / "run-1").mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.delenv("AF_DOGFOOD_ROOT", raising=False)
    r = check_dogfood_root()
    assert r.status == "ok"
    assert "1 runs" in r.detail


def test_check_dogfood_root_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.delenv("AF_DOGFOOD_ROOT", raising=False)
    r = check_dogfood_root()
    assert r.status == "warn"
    assert "자동 생성" in r.fix_hint


def test_check_dogfood_root_env_override(monkeypatch, tmp_path):
    custom = tmp_path / "custom-dogfood"
    custom.mkdir()
    monkeypatch.setenv("AF_DOGFOOD_ROOT", str(custom))
    r = check_dogfood_root()
    assert r.status == "ok"
    assert str(custom) in r.detail


# ---------------------------------------------------------------------------
# format_text / format_json
# ---------------------------------------------------------------------------

def _sample_checks() -> list[DoctorResult]:
    return [
        DoctorResult("python", "ok", "Python 3.12.0"),
        DoctorResult("git_repo", "fail", "git 미설치", "git 설치 필요"),
        DoctorResult("git_dirty", "warn", "2개 변경", "git commit"),
    ]


def test_format_text_contains_icons():
    text = format_text(_sample_checks())
    assert "✓" in text
    assert "✗" in text
    assert "!" in text
    assert "1 fail" in text
    assert "1 warn" in text
    assert "1 ok" in text


def test_format_text_shows_fix_hint():
    text = format_text(_sample_checks())
    assert "git 설치 필요" in text


def test_format_json_structure():
    data = json.loads(format_json(_sample_checks()))
    assert data["fail_count"] == 1
    assert data["warn_count"] == 1
    assert data["ok_count"] == 1
    assert len(data["checks"]) == 3
    fields = set(data["checks"][0].keys())
    assert fields == {"name", "status", "detail", "fix_hint"}


# ---------------------------------------------------------------------------
# _exit_code
# ---------------------------------------------------------------------------

def test_exit_code_all_ok():
    checks = [DoctorResult("x", "ok", "")]
    assert _exit_code(checks, strict=False) == 0


def test_exit_code_fail():
    checks = [DoctorResult("x", "fail", "")]
    assert _exit_code(checks, strict=False) == 1


def test_exit_code_warn_no_strict():
    checks = [DoctorResult("x", "warn", "")]
    assert _exit_code(checks, strict=False) == 0


def test_exit_code_warn_strict():
    checks = [DoctorResult("x", "warn", "")]
    assert _exit_code(checks, strict=True) == 1


def test_exit_code_fail_takes_priority_over_warn():
    checks = [DoctorResult("a", "warn", ""), DoctorResult("b", "fail", "")]
    assert _exit_code(checks, strict=False) == 1


# ---------------------------------------------------------------------------
# run_checks integration (smoke)
# ---------------------------------------------------------------------------

def test_run_checks_fast_returns_list():
    """fast 모드에서 최소 항목 수 확인 (provider ping 없음)."""
    with patch("core.providers.registry.detect_installed_cli_providers", return_value=["claude_cli"]):
        results = run_checks(fast=True)
    # python, git, git_dirty, providers_installed, hooks, pytest, dogfood_root = 최소 7개
    assert len(results) >= 7
    names = [r.name for r in results]
    assert "python" in names
    assert "git_repo" in names
    assert "dogfood_root" in names
