#!/usr/bin/env python3
"""setup_dev — configure Agent Factory dev environment.

Cross-platform replacement for setup-dev.cmd / setup-dev.py.

Usage:
    python setup_dev.py
    setup-dev          # after pip install -e .
"""

import os
import subprocess
import sys
from pathlib import Path


def _add_scripts_to_path_windows(scripts_dir: str) -> None:
    """Add scripts_dir to user PATH on Windows (persistent)."""
    ps_script = (
        f'$p = [System.Environment]::GetEnvironmentVariable("PATH","User"); '
        f'if ($p -notlike "*{scripts_dir}*") {{ '
        f'[System.Environment]::SetEnvironmentVariable("PATH", $p + ";{scripts_dir}", "User"); '
        f'Write-Host "[OK] PATH 추가됨: {scripts_dir}" '
        f'}} else {{ Write-Host "[OK] PATH 이미 포함됨: {scripts_dir}" }}'
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script])
    print("[INFO] 새 터미널을 열면 PATH가 적용됩니다.")


def main() -> None:
    print("[setup-dev] Agent Factory 개발 환경 설정")

    rc = subprocess.run(["git", "config", "core.hooksPath", ".githooks"]).returncode
    if rc != 0:
        print("[FAIL] git config core.hooksPath 설정 실패")
        sys.exit(rc)

    print("[OK] core.hooksPath = .githooks")
    result = subprocess.run(["git", "config", "--get", "core.hooksPath"],
                            capture_output=True, text=True)
    print(f"[OK] 확인: {result.stdout.strip()}")

    print("\n[setup-dev] pip install -e . 실행 중...")
    rc2 = subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".",
                          "--quiet"]).returncode
    if rc2 != 0:
        print("[WARN] pip install -e . 실패. 수동으로 실행하세요.")
    else:
        print("[OK] pip install -e . 완료")

        scripts_dir = Path(sys.executable).parent / "Scripts"
        if sys.platform == "win32" and scripts_dir.exists():
            current_path = os.environ.get("PATH", "")
            if str(scripts_dir) not in current_path:
                print(f"\n[setup-dev] Scripts 폴더를 PATH에 추가합니다: {scripts_dir}")
                _add_scripts_to_path_windows(str(scripts_dir))
            else:
                print(f"[OK] Scripts 폴더 이미 PATH에 있음: {scripts_dir}")
        elif sys.platform != "win32":
            scripts_dir_unix = Path(sys.executable).parent
            print(f"[INFO] Linux/Mac: {scripts_dir_unix} 가 PATH에 없으면 추가하세요.")

    print("\n[setup-dev] 완료. start_db, end_db 등 명령어를 사용할 수 있습니다.")


if __name__ == "__main__":
    main()
