#!/usr/bin/env python3
"""end_db — push project context to DB.

Cross-platform replacement for end_db.cmd.

Usage:
    python end_db.py [target] [agent]
    python end_db.py agent-factory
    python end_db.py all my-agent

target defaults to "all" → logi-mind-v22, agent-factory, @repo
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SYNC_SCRIPT = REPO_ROOT / "scripts" / "project_context_sync.py"
RESUME_SCRIPT = REPO_ROOT / "scripts" / "write_resume_brief.py"

TARGET_ALL = "logi-mind-v22,agent-factory,@repo"


def _resolve_target(raw: str) -> tuple[str, bool]:
    """Return (resolved_value, is_multi)."""
    if raw.lower() == "all":
        return TARGET_ALL, True
    if "," in raw:
        return raw, True
    return raw, False


def _global_user_key() -> str:
    key = os.environ.get("AGENT_GLOBAL_USER_KEY", "").strip()
    if key:
        return key
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("AGENT_GLOBAL_USER_KEY") and "=" in stripped:
                _, v = stripped.split("=", 1)
                return v.strip().strip('"').strip("'")
    return ""


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd).returncode


def main() -> None:
    argv = sys.argv[1:]
    target = argv[0] if argv else "all"
    agent = argv[1] if len(argv) > 1 else ""

    target_val, is_multi = _resolve_target(target)

    print(f"[SYNC END] pushing to DB  target={target}  agent={agent or '(all)'}")

    # write resume brief before pushing
    resume_cmd = [sys.executable, str(RESUME_SCRIPT), "--trigger", "sync_push"]
    resume_cmd += ["--projects" if is_multi else "--project", target_val]
    rc = _run(resume_cmd)
    if rc != 0:
        sys.exit(rc)

    # project sync push
    cmd = [sys.executable, str(SYNC_SCRIPT), "--mode", "push"]
    cmd += ["--projects" if is_multi else "--project", target_val]
    if agent:
        cmd += ["--agent", agent]

    rc = _run(cmd)
    if rc != 0:
        sys.exit(rc)

    global_key = _global_user_key()
    if global_key:
        print(f"[SYNC GLOBAL] pushing global profile  user_key={global_key}")
        rc = _run([sys.executable, str(SYNC_SCRIPT),
                   "--mode", "push", "--scope", "global", "--user-key", global_key])
        if rc != 0:
            sys.exit(rc)

    print("[SYNC END] done.")


if __name__ == "__main__":
    main()
