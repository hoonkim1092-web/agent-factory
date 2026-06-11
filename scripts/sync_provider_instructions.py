#!/usr/bin/env python3
"""Sync INSTRUCTIONS.md common block into CLAUDE.md, GEMINI.md, and AGENTS.md.

Usage:
    python scripts/sync_provider_instructions.py [--workspace <repo_root>]

Called automatically by .githooks/pre-commit when INSTRUCTIONS.md or agents/*.yaml
are staged.  Failure exits non-zero and blocks the commit (no || true).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_AF_ROOT = Path(__file__).resolve().parent.parent
if str(_AF_ROOT) not in sys.path:
    sys.path.insert(0, str(_AF_ROOT))

# ---------------------------------------------------------------------------
# Marker constants — single SSOT, no magic strings elsewhere.
# ---------------------------------------------------------------------------

MARKER_START = "<!-- AF-COMMON-START (generated from INSTRUCTIONS.md — DO NOT EDIT between markers) -->"
MARKER_END = "<!-- AF-COMMON-END -->"

_SSOT_FILE = "INSTRUCTIONS.md"
_PROVIDER_FILES = ["CLAUDE.md", "GEMINI.md"]
_AGENTS_FILE = "AGENTS.md"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _repo_root(workspace: str | None) -> Path:
    if workspace:
        return Path(workspace).resolve()
    return _AF_ROOT


def _read_instructions(repo_root: Path) -> str:
    path = repo_root / _SSOT_FILE
    if not path.exists():
        raise FileNotFoundError(f"{_SSOT_FILE} not found: {path}")
    return path.read_text(encoding="utf-8")


def _inject_common_block(file_path: Path, common_block: str) -> bool:
    """Replace content between AF-COMMON markers with *common_block*.

    Returns True if the file was changed, False if already in sync.
    Raises ValueError when either marker is absent.
    """
    text = file_path.read_text(encoding="utf-8")

    start_idx = text.find(MARKER_START)
    end_idx = text.find(MARKER_END)

    if start_idx == -1 or end_idx == -1:
        raise ValueError(
            f"AF-COMMON markers missing in {file_path}. "
            f"Insert '{MARKER_START}' and '{MARKER_END}' before running sync."
        )

    if end_idx <= start_idx:
        raise ValueError(
            f"AF-COMMON-END appears before AF-COMMON-START in {file_path}"
        )

    new_text = (
        text[: start_idx + len(MARKER_START)]
        + "\n"
        + common_block.rstrip("\n")
        + "\n"
        + text[end_idx:]
    )

    if new_text == text:
        return False

    file_path.write_text(new_text, encoding="utf-8")
    return True


def _generate_agents_md(repo_root: Path, common_block: str) -> bool:
    """Generate AGENTS.md = common block markers + roster table.

    Returns True if the file was changed.
    Imports collect_records and render_roster from generate_agents_md (SSOT — no
    re-declaration here per INV-6).
    """
    from scripts.generate_agents_md import collect_records, render_roster  # type: ignore[import]

    agents_dir = repo_root / "agents"
    if not agents_dir.exists():
        raise FileNotFoundError(f"agents/ directory not found: {agents_dir}")

    records = collect_records(repo_root, agents_dir)
    roster = render_roster(records, agents_dir_label="agents")

    content = (
        MARKER_START + "\n"
        + common_block.rstrip("\n") + "\n"
        + MARKER_END + "\n\n"
        + roster
    )

    output_path = repo_root / _AGENTS_FILE
    if output_path.exists() and output_path.read_text(encoding="utf-8") == content:
        return False

    output_path.write_text(content, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def sync(workspace: str | None = None) -> int:
    """Sync INSTRUCTIONS.md into all provider files.  Returns 0 on success."""
    root = _repo_root(workspace)

    try:
        common_block = _read_instructions(root)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []

    for fname in _PROVIDER_FILES:
        fpath = root / fname
        if not fpath.exists():
            errors.append(f"[ERROR] {fname} not found: {fpath}")
            continue
        try:
            changed = _inject_common_block(fpath, common_block)
            status = "updated" if changed else "already in sync"
            print(f"[OK] {fname} {status}")
        except (ValueError, OSError) as exc:
            errors.append(f"[ERROR] {fname}: {exc}")

    try:
        changed = _generate_agents_md(root, common_block)
        status = "generated" if changed else "already in sync"
        print(f"[OK] {_AGENTS_FILE} {status}")
    except Exception as exc:  # broad — roster render failures must not be silent
        errors.append(f"[ERROR] {_AGENTS_FILE}: {exc}")

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync INSTRUCTIONS.md common block into provider instruction files."
    )
    parser.add_argument("--workspace", default=None, help="Repo root path (default: auto-detect)")
    args = parser.parse_args()
    return sync(workspace=args.workspace)


if __name__ == "__main__":
    raise SystemExit(main())
