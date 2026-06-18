"""
tests/test_watcher_portability.py
===================================
_is_watcher_alive / _process_alive / _start_watcher 이식성 테스트.
실제 프로세스를 사용하지 않고 mock으로 플랫폼 분기 검증.
"""
from __future__ import annotations

import json
import os
import platform
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from core.design_review_utils import (
    PID_FILE,
    HEARTBEAT_STALE_THRESHOLD,
    _STILL_ACTIVE,
    _is_watcher_alive,
    _process_alive,
    _start_watcher,
)


# ── _process_alive ────────────────────────────────────────────────────────────


class TestProcessAliveUnix:
    """Unix 경로: os.kill(pid, 0) 위임."""

    def test_alive_returns_true(self):
        with patch("platform.system", return_value="Linux"), patch(
            "os.kill"
        ) as mock_kill:
            mock_kill.return_value = None  # no exception = alive
            assert _process_alive(1234) is True

    def test_process_lookup_error_returns_false(self):
        with patch("platform.system", return_value="Linux"), patch(
            "os.kill", side_effect=ProcessLookupError
        ):
            assert _process_alive(9999) is False

    def test_oserror_permission_returns_true(self):
        # ProcessLookupError가 아닌 OSError(EPERM) → 존재하지만 권한 없음
        with patch("platform.system", return_value="Linux"), patch(
            "os.kill", side_effect=OSError("permission denied")
        ):
            assert _process_alive(1) is True


class TestProcessAliveWindows:
    """Windows 경로: ctypes OpenProcess + GetExitCodeProcess."""

    def _make_ctypes_mock(self, handle_val: int, exit_code_val: int):
        """ctypes.windll.kernel32 mock 빌더."""
        kernel32 = MagicMock()
        kernel32.OpenProcess.return_value = handle_val

        def fake_get_exit(handle, ptr):
            ptr.value = exit_code_val

        kernel32.GetExitCodeProcess.side_effect = fake_get_exit
        return kernel32

    def test_alive_process_returns_true(self):
        kernel32 = self._make_ctypes_mock(handle_val=1, exit_code_val=_STILL_ACTIVE)
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = kernel32
        mock_ctypes.c_ulong = MagicMock(return_value=MagicMock(value=_STILL_ACTIVE))

        import ctypes as real_ctypes

        with patch("platform.system", return_value="Windows"), patch.dict(
            "sys.modules", {"ctypes": mock_ctypes}
        ):
            # c_ulong() 반환값의 value가 STILL_ACTIVE인지 확인
            mock_ctypes.c_ulong.return_value.value = _STILL_ACTIVE
            kernel32.GetExitCodeProcess.side_effect = lambda h, p: None
            # OpenProcess 0이 아님 → 존재 → GetExitCode STILL_ACTIVE → True
            kernel32.OpenProcess.return_value = 999
            # GetExitCodeProcess side_effect: ptr.value = STILL_ACTIVE
            captured = []

            def set_exit(handle, ptr):
                ptr.value = _STILL_ACTIVE
                captured.append(ptr)

            mock_ctypes.c_ulong.return_value = MagicMock()
            mock_ctypes.c_ulong.return_value.value = _STILL_ACTIVE
            kernel32.GetExitCodeProcess.side_effect = set_exit
            result = _process_alive(1234)
        assert result is True

    def test_no_handle_returns_false(self):
        kernel32 = self._make_ctypes_mock(handle_val=0, exit_code_val=0)
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = kernel32
        mock_ctypes.c_ulong = MagicMock(return_value=MagicMock(value=0))

        with patch("platform.system", return_value="Windows"), patch.dict(
            "sys.modules", {"ctypes": mock_ctypes}
        ):
            result = _process_alive(9999)
        assert result is False

    def test_exited_process_returns_false(self):
        """exit_code != STILL_ACTIVE → 프로세스 종료됨 → False."""
        kernel32 = self._make_ctypes_mock(handle_val=1, exit_code_val=0)
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = kernel32
        mock_ctypes.c_ulong.return_value = MagicMock(value=0)

        def set_exit(handle, ptr):
            ptr.value = 0  # 종료 코드

        kernel32.GetExitCodeProcess.side_effect = set_exit

        with patch("platform.system", return_value="Windows"), patch.dict(
            "sys.modules", {"ctypes": mock_ctypes}
        ):
            result = _process_alive(1234)
        assert result is False


# ── _is_watcher_alive ─────────────────────────────────────────────────────────


class TestIsWatcherAlive:
    def _write_pid(self, directory: str, pid: int, heartbeat: float | None = None):
        pid_path = os.path.join(directory, PID_FILE)
        os.makedirs(os.path.dirname(pid_path), exist_ok=True)
        data = {"pid": pid, "heartbeat": heartbeat or time.time(), "start_time": time.time()}
        with open(pid_path, "w") as f:
            json.dump(data, f)

    def test_no_pid_file_returns_false(self, tmp_path):
        assert _is_watcher_alive(str(tmp_path)) is False

    def test_alive_process_fresh_heartbeat(self, tmp_path):
        self._write_pid(str(tmp_path), pid=os.getpid())
        with patch("core.design_review_utils._process_alive", return_value=True):
            assert _is_watcher_alive(str(tmp_path)) is True

    def test_dead_process_cleans_pid_file(self, tmp_path):
        self._write_pid(str(tmp_path), pid=99999999)
        with patch("core.design_review_utils._process_alive", return_value=False):
            result = _is_watcher_alive(str(tmp_path))
        assert result is False
        pid_path = os.path.join(str(tmp_path), PID_FILE)
        assert not os.path.exists(pid_path)

    def test_stale_heartbeat_returns_false(self, tmp_path):
        stale_time = time.time() - HEARTBEAT_STALE_THRESHOLD - 10
        self._write_pid(str(tmp_path), pid=os.getpid(), heartbeat=stale_time)
        with patch("core.design_review_utils._process_alive", return_value=True):
            result = _is_watcher_alive(str(tmp_path))
        assert result is False

    def test_legacy_numeric_pid_format_returns_false(self, tmp_path):
        pid_path = os.path.join(str(tmp_path), PID_FILE)
        os.makedirs(os.path.dirname(pid_path), exist_ok=True)
        with open(pid_path, "w") as f:
            f.write("12345")
        assert _is_watcher_alive(str(tmp_path)) is False


# ── _start_watcher Windows creationflags ──────────────────────────────────────


class TestStartWatcherWindows:
    def test_windows_uses_detached_process_flag(self, tmp_path):
        """Windows spawn 시 DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP 확인."""
        import subprocess as sp

        script = tmp_path / "scripts" / "design_review_watcher.py"
        script.parent.mkdir(parents=True)
        script.write_text("pass")

        captured_kwargs: dict = {}

        def fake_popen(args, **kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock()

        _DETACHED_PROCESS = 0x00000008
        expected_flags = sp.CREATE_NEW_PROCESS_GROUP | _DETACHED_PROCESS

        with patch("platform.system", return_value="Windows"), patch(
            "subprocess.Popen", side_effect=fake_popen
        ):
            _start_watcher(str(tmp_path))

        assert "creationflags" in captured_kwargs
        assert captured_kwargs["creationflags"] == expected_flags
        assert "close_fds" not in captured_kwargs  # 제거됨

    def test_unix_uses_start_new_session(self, tmp_path):
        """Unix spawn 시 start_new_session=True 확인."""
        script = tmp_path / "scripts" / "design_review_watcher.py"
        script.parent.mkdir(parents=True)
        script.write_text("pass")

        captured_kwargs: dict = {}

        def fake_popen(args, **kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock()

        with patch("platform.system", return_value="Linux"), patch(
            "subprocess.Popen", side_effect=fake_popen
        ):
            _start_watcher(str(tmp_path))

        assert captured_kwargs.get("start_new_session") is True
        assert "creationflags" not in captured_kwargs
