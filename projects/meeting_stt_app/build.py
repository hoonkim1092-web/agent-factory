"""배포 빌드 헬퍼(M9).

``meeting_stt.spec``으로 PyInstaller onedir 빌드를 실행한다. 빌드 전 헤드리스
셀프테스트를 돌려 배선 단선을 사전 차단한다.

사용: ``python build.py``
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SPEC = _ROOT / "meeting_stt.spec"


def run_selftest() -> int:
    print("=== 빌드 전 헤드리스 셀프테스트 ===")
    return subprocess.call([sys.executable, "-m", "tests.selftest_pipeline"], cwd=str(_ROOT))


def run_pyinstaller() -> int:
    print("=== PyInstaller onedir 빌드 ===")
    return subprocess.call(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(_SPEC)],
        cwd=str(_ROOT),
    )


def main() -> int:
    rc = run_selftest()
    if rc != 0:
        print("셀프테스트 실패 — 빌드를 중단합니다.")
        return rc
    return run_pyinstaller()


if __name__ == "__main__":
    raise SystemExit(main())
