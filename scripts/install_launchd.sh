#!/usr/bin/env bash
# Agent Factory 야간 자율 파이프라인 launchd 설치 스크립트.
# macOS 전용. `af nightly-start` 에서 호출된다.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_LABEL="com.af.nightly.tick"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
TICK_SCRIPT="$REPO_ROOT/scripts/nightly_tick.py"
LOG_DIR="$REPO_ROOT/.system_generated/logs"

# Python 인터프리터: 프로젝트 venv 우선
if [ -f "$REPO_ROOT/.venv/bin/python3" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
else
    echo "[install_launchd] ERROR: python3를 찾을 수 없습니다." >&2
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$LOG_DIR"

# plist 생성
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${TICK_SCRIPT}</string>
    <string>--workspace</string>
    <string>${REPO_ROOT}</string>
  </array>

  <!-- 기본 15분 인터벌 -->
  <key>StartInterval</key>
  <integer>900</integer>

  <!-- 절대 시각 스케줄: 매시 00/15/30/45분 — macOS sleep 복귀 후 즉시 기동 -->
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Minute</key><integer>0</integer></dict>
    <dict><key>Minute</key><integer>15</integer></dict>
    <dict><key>Minute</key><integer>30</integer></dict>
    <dict><key>Minute</key><integer>45</integer></dict>
  </array>

  <!-- 정상 종료(exit 0) 후 재기동 안 함. 비정상 종료 시 재기동. -->
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/nightly_tick.out</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/nightly_tick.err</string>
</dict>
</plist>
EOF

echo "[install_launchd] plist 작성: $PLIST_PATH"

# launchd 로드 (macOS 버전별 명령 fallback)
_loaded=0
if launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null; then
    _loaded=1
elif launchctl load -w "$PLIST_PATH" 2>/dev/null; then
    _loaded=1
fi

if [ "$_loaded" -eq 1 ]; then
    echo "[install_launchd] launchd 등록 완료: $PLIST_LABEL"
else
    echo "[install_launchd] WARNING: launchd 자동 로드 실패. 수동으로 실행하세요:" >&2
    echo "  launchctl load -w $PLIST_PATH" >&2
fi
