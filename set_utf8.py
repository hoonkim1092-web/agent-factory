#!/usr/bin/env python3
"""set_utf8 — configure UTF-8 for the current process and print shell instructions.

Cross-platform replacement for set_utf8.cmd.

On Windows, also switches the console codepage to 65001.
Note: env vars set here only affect child processes, not the parent shell.
To persist in the shell, run the printed export commands manually.
"""

import os
import subprocess
import sys

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"


def main() -> None:
    if sys.platform == "win32":
        subprocess.run(["chcp", "65001"], capture_output=True, shell=True)
        print("[UTF8] Windows: console codepage set to 65001 (this process)")
        print("[UTF8] To set in cmd.exe permanently: chcp 65001")
        print("[UTF8] To set in PowerShell:  $OutputEncoding = [System.Text.Encoding]::UTF8")
    else:
        print("[UTF8] Linux/Mac: UTF-8 is typically the default locale")
        print("[UTF8] If needed, add to your shell profile:")
        print("       export PYTHONUTF8=1")
        print("       export PYTHONIOENCODING=utf-8")

    print("[UTF8] PYTHONUTF8=1, PYTHONIOENCODING=utf-8 set for this process")


if __name__ == "__main__":
    main()
