"""
cli.py _run_command — cp949 출력 UnicodeDecodeError 방어 테스트

배경: gemini 등 CLI provider가 Windows cp949 인코딩 오류 메시지를 출력할 때
subprocess.run(encoding="utf-8") strict decode 실패(UnicodeDecodeError: 0xb8 ...)
→ _readerthread 사망 → CLI failed → fallback(full) 오진단.

fix: encoding="utf-8" 외에 errors="replace" 추가 (git 호출 선례 동일 패턴).
"""

import os
import subprocess
import sys


# ── Unit test: runner에 errors="replace"가 전달되는지 ──────────────────────────

def test_run_command_passes_errors_replace_to_runner():
    """_run_command는 runner 호출 시 errors='replace'를 전달해야 한다.
    이것이 빠지면 cp949 바이트에서 UnicodeDecodeError가 발생한다.
    """
    from core.providers.cli import _run_command

    captured: dict = {}

    def mock_runner(cmd, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    _run_command(
        mock_runner,
        ["echo", "test"],
        cwd=".",
        env={},
        timeout_sec=10,
    )

    assert captured.get("errors") == "replace", (
        "errors='replace'가 runner에 전달되지 않음 — "
        "cp949 바이트 출력 시 UnicodeDecodeError 발생"
    )


# ── Integration test: 실제 cp949 바이트 출력에 graceful 처리 ─────────────────

def test_run_command_tolerates_cp949_output(tmp_path):
    """_run_command는 CLI provider가 cp949 바이트를 출력해도 UnicodeDecodeError를
    발생시키지 않고 replacement char로 처리해야 한다.
    """
    from core.providers.cli import _run_command

    # cp949 바이트 0xb8 0xa6 은 UTF-8로 디코딩 불가 (standalone continuation bytes).
    # bytes.fromhex()를 사용해 ASCII-only 스크립트로 raw 바이트를 생성한다.
    # (b'\xb8\xa6' 리터럴을 .py 파일에 직접 삽입하면 Python 파서가 SyntaxError를 낸다.)
    script = tmp_path / "emit_cp949.py"
    script.write_bytes(
        b"import sys; sys.stdout.buffer.write(bytes.fromhex('b8a6')); sys.stdout.flush()"
    )

    result = _run_command(
        subprocess.run,
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        timeout_sec=15,
    )

    assert result.returncode == 0
    assert isinstance(result.stdout, str)
    # errors="replace" 적용 시 U+FFFD('�')로 치환
    assert "�" in result.stdout


def test_run_command_normal_utf8_unaffected(tmp_path):
    """errors='replace' 추가 후에도 정상 UTF-8 출력은 그대로 반환된다."""
    from core.providers.cli import _run_command

    script = tmp_path / "hello.py"
    script.write_bytes(b"print('hello world')")

    result = _run_command(
        subprocess.run,
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        timeout_sec=15,
    )

    assert result.returncode == 0
    assert "hello world" in result.stdout


def test_run_command_valid_utf8_bytes_decoded_correctly(tmp_path):
    """stdout.buffer에 직접 기록된 유효한 UTF-8 바이트는 올바르게 디코딩된다.
    (print()는 Windows 콘솔 인코딩을 경유하므로 buffer.write로 직접 검증)
    """
    from core.providers.cli import _run_command

    script = tmp_path / "utf8_bytes.py"
    # '완료' UTF-8 hex: ec9984 eba38c
    # bytes.fromhex()로 ASCII-only 스크립트에서 raw UTF-8 바이트를 생성한다.
    script.write_bytes(
        b"import sys; sys.stdout.buffer.write(bytes.fromhex('ec9984eba38c0a')); sys.stdout.flush()"
    )

    result = _run_command(
        subprocess.run,
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        timeout_sec=15,
    )

    assert result.returncode == 0
    assert "완료" in result.stdout
