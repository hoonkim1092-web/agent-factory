#!/bin/sh
# Cross-platform Python resolver for Claude/Codex hooks.
# macOS/Linux normally provide python3. On Windows, Claude may run hooks through
# Git Bash without python/python3 in bash PATH, while cmd.exe can still resolve
# the normal Windows Python install.

PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -n "$PYTHON" ]; then
  exec "$PYTHON" "$@"
fi

if command -v py.exe >/dev/null 2>&1; then
  exec py.exe -3 "$@"
fi

if command -v cmd.exe >/dev/null 2>&1; then
  if cmd.exe /c python --version >/dev/null 2>&1; then
    exec cmd.exe /c python "$@"
  fi
  if cmd.exe /c py -3 --version >/dev/null 2>&1; then
    exec cmd.exe /c py -3 "$@"
  fi
fi

echo "[hookpy] Python interpreter not found; skipping hook." >&2
exit 0
