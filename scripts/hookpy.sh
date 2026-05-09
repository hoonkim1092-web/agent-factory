#!/bin/sh
# Cross-platform Python resolver: tries python3 first, falls back to python
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
exec "$PYTHON" "$@"
