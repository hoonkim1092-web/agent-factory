"""Cross-platform nightly tick scheduler installer.

Supports macOS (launchd), Linux (crontab), Windows (Task Scheduler).
Called by `af nightly-start` / `af nightly-stop`.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

LAUNCHD_LABEL = "com.af.nightly.tick"
CRON_MARKER = "# AF-NightlyTick"
TASK_NAME = "AF-NightlyTick"


def install(repo_root: Path, workspace: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        _install_macos(repo_root, workspace)
    elif system == "Linux":
        _install_linux(repo_root, workspace)
    elif system == "Windows":
        _install_windows(repo_root, workspace)
    else:
        print(f"[scheduler] {system}: 스케줄러 자동 설치 미지원. 수동으로 15분 주기 설정 필요.", file=sys.stderr)


def uninstall(repo_root: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        _uninstall_macos()
    elif system == "Linux":
        _uninstall_linux()
    elif system == "Windows":
        _uninstall_windows()


# ── macOS ────────────────────────────────────────────────────────────────────

def _install_macos(repo_root: Path, workspace: Path) -> None:
    python = _find_python(repo_root)
    tick_script = repo_root / "scripts" / "nightly_tick.py"
    log_dir = _ensure_log_dir(repo_root)
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)
    plist_path = plist_dir / f"{LAUNCHD_LABEL}.plist"

    plist_path.write_text(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LAUNCHD_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python}</string>
    <string>{tick_script}</string>
    <string>--workspace</string>
    <string>{workspace}</string>
  </array>
  <key>StartInterval</key>
  <integer>900</integer>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Minute</key><integer>0</integer></dict>
    <dict><key>Minute</key><integer>15</integer></dict>
    <dict><key>Minute</key><integer>30</integer></dict>
    <dict><key>Minute</key><integer>45</integer></dict>
  </array>
  <key>KeepAlive</key>
  <dict><key>SuccessfulExit</key><false/></dict>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{log_dir}/nightly_tick.out</string>
  <key>StandardErrorPath</key>
  <string>{log_dir}/nightly_tick.err</string>
</dict>
</plist>""")

    print(f"[scheduler] plist 작성: {plist_path}")
    uid = os.getuid()
    for cmd in (
        ["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)],
        ["launchctl", "load", "-w", str(plist_path)],
    ):
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[scheduler] launchd 등록 완료: {LAUNCHD_LABEL}")
            return
        except subprocess.CalledProcessError:
            continue
    print(f"[scheduler] WARNING: launchd 자동 로드 실패. 수동: launchctl load -w {plist_path}", file=sys.stderr)


def _uninstall_macos() -> None:
    plist = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
    if not plist.exists():
        return
    uid = os.getuid()
    for cmd in (
        ["launchctl", "bootout", f"gui/{uid}", str(plist)],
        ["launchctl", "unload", "-w", str(plist)],
    ):
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            break
        except subprocess.CalledProcessError:
            continue
    plist.unlink(missing_ok=True)
    print("[scheduler] launchd 항목 제거됨.")


# ── Linux ────────────────────────────────────────────────────────────────────

def _install_linux(repo_root: Path, workspace: Path) -> None:
    python = _find_python(repo_root)
    tick_script = repo_root / "scripts" / "nightly_tick.py"
    log_dir = _ensure_log_dir(repo_root)

    cron_line = (
        f"*/15 * * * * {python} {tick_script} --workspace {workspace}"
        f" >> {log_dir}/nightly_tick.out 2>> {log_dir}/nightly_tick.err"
        f"  {CRON_MARKER}"
    )
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""
    lines = [l for l in existing.splitlines() if CRON_MARKER not in l]
    lines.append(cron_line)
    proc = subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    if proc.returncode == 0:
        print("[scheduler] crontab 등록 완료 (*/15분).")
    else:
        print("[scheduler] WARNING: crontab 설치 실패.", file=sys.stderr)


def _uninstall_linux() -> None:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return
    lines = [l for l in result.stdout.splitlines() if CRON_MARKER not in l]
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    print("[scheduler] crontab 항목 제거됨.")


# ── Windows ──────────────────────────────────────────────────────────────────

def _install_windows(repo_root: Path, workspace: Path) -> None:
    python = _find_python_windows(repo_root)
    tick_script = repo_root / "scripts" / "nightly_tick.py"
    _ensure_log_dir(repo_root)
    cmd_str = f'"{python}" "{tick_script}" --workspace "{workspace}"'
    result = subprocess.run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/TR", cmd_str,
         "/SC", "MINUTE", "/MO", "15", "/F"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"[scheduler] Task Scheduler 등록 완료: {TASK_NAME}")
    else:
        print(f"[scheduler] WARNING: schtasks 실패: {result.stderr.strip()}", file=sys.stderr)


def _uninstall_windows() -> None:
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"[scheduler] Task '{TASK_NAME}' 제거됨.")
    else:
        print(f"[scheduler] Task 제거 실패 (이미 없을 수 있음): {result.stderr.strip()}", file=sys.stderr)


# ── helpers ──────────────────────────────────────────────────────────────────

def _find_python(repo_root: Path) -> str:
    venv_py = repo_root / ".venv" / "bin" / "python3"
    return str(venv_py) if venv_py.exists() else sys.executable


def _find_python_windows(repo_root: Path) -> str:
    venv_py = repo_root / ".venv" / "Scripts" / "python.exe"
    return str(venv_py) if venv_py.exists() else sys.executable


def _ensure_log_dir(repo_root: Path) -> Path:
    log_dir = repo_root / ".system_generated" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="AF nightly tick 스케줄러 설치/제거")
    p.add_argument("action", choices=["install", "uninstall"])
    p.add_argument("--workspace", default=None)
    a = p.parse_args()
    root = Path(__file__).resolve().parent.parent
    ws = Path(a.workspace) if a.workspace else root
    if a.action == "install":
        install(root, ws)
    else:
        uninstall(root)
