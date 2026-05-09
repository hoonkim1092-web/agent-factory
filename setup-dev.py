#!/usr/bin/env python3
"""setup-dev — configure Agent Factory dev environment.

Cross-platform replacement for setup-dev.cmd.

Usage:
    python setup-dev.py
"""

import subprocess
import sys

print("[setup-dev] Agent Factory 개발 환경 설정")

rc = subprocess.run(["git", "config", "core.hooksPath", ".githooks"]).returncode
if rc != 0:
    print("[FAIL] git config core.hooksPath 설정 실패")
    sys.exit(rc)

print("[OK] core.hooksPath = .githooks")
result = subprocess.run(["git", "config", "--get", "core.hooksPath"],
                        capture_output=True, text=True)
print(f"[OK] 확인: {result.stdout.strip()}")
print("\n[setup-dev] 완료. .githooks/ 의 pre-commit 등이 활성화됩니다.")
