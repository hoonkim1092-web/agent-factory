#!/usr/bin/env python3
"""Git-based project context sync. Cross-platform replacement for project_context_git_sync.ps1."""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.project_context_sync import load_dotenv_simple, parse_project_inputs, resolve_project_root


def _safe_id(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"[^a-z0-9_-]+", "_", t)
    return re.sub(r"_+", "_", t).strip("_")


def _is_git_repo(path: Path) -> bool:
    r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True,
    )
    return r.returncode == 0 and r.stdout.strip() == "true"


def _git_pull(project_path: Path, branch: str = "", no_rebase: bool = False) -> dict:
    cmd = ["git", "-C", str(project_path)]
    if no_rebase:
        cmd += ["pull"] + (["origin", branch] if branch else [])
    else:
        cmd += ["pull", "--rebase", "--autostash"] + (["origin", branch] if branch else [])
    rc = subprocess.run(cmd).returncode
    detail = "pulled" if rc == 0 else "git_pull_failed"
    return {"project_path": str(project_path), "ok": rc == 0, "mode": "pull", "detail": detail}


def _git_push(project_path: Path, agent_id: str = "", branch: str = "", message: str = "") -> dict:
    if agent_id:
        agent_paths = [
            f"data/memory/{agent_id}",
            f"agents/{agent_id}.yaml",
            "runs", "artifacts", "dashboard.json",
            "policies.yaml", "settings.yaml", "skill-lock.yaml",
            "workflow.yaml", "context_schema.yaml",
        ]
        subprocess.run(["git", "-C", str(project_path), "add", "--"] + agent_paths)
    else:
        subprocess.run(["git", "-C", str(project_path), "add", "-A", "--",
                        ".", ":(exclude)syncCompyne/**"])

    rc = subprocess.run(["git", "-C", str(project_path), "diff", "--cached", "--quiet"]).returncode
    if rc == 0:
        return {"project_path": str(project_path), "ok": True, "mode": "push", "detail": "no_changes"}

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    proj_name = project_path.name
    if not message:
        message = (
            f"sync({proj_name}/{agent_id}): context snapshot {ts}"
            if agent_id else
            f"sync({proj_name}): context snapshot {ts}"
        )

    rc = subprocess.run(["git", "-C", str(project_path), "commit", "-m", message]).returncode
    if rc != 0:
        return {"project_path": str(project_path), "ok": False, "mode": "push", "detail": "git_commit_failed"}

    push_cmd = ["git", "-C", str(project_path), "push"]
    if branch:
        push_cmd += ["origin", branch]
    rc = subprocess.run(push_cmd).returncode
    detail = "pushed" if rc == 0 else "git_push_failed"
    return {"project_path": str(project_path), "ok": rc == 0, "mode": "push", "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser(description="Git project context sync.")
    parser.add_argument("--mode", "-m", choices=["push", "pull"], required=True)
    parser.add_argument("--project", "-p", default="")
    parser.add_argument("--projects", default="")
    parser.add_argument("--agent", "-a", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--message", default="")
    parser.add_argument("--no-rebase", action="store_true")
    args = parser.parse_args()

    load_dotenv_simple(REPO_ROOT)
    project_inputs = parse_project_inputs(args.project, args.projects)
    if not project_inputs:
        print("Error: provide --project or --projects", file=sys.stderr)
        sys.exit(1)

    agent_id = _safe_id(args.agent) if args.agent else ""
    results = []

    for pi in project_inputs:
        _, project_path = resolve_project_root(REPO_ROOT, pi)
        if not _is_git_repo(project_path):
            results.append({"project_path": str(project_path), "ok": False,
                            "mode": args.mode, "detail": "not_git_repo"})
            continue
        if args.mode == "pull":
            results.append(_git_pull(project_path, args.branch, args.no_rebase))
        else:
            results.append(_git_push(project_path, agent_id, args.branch, args.message))

    fail_count = sum(1 for r in results if not r["ok"])
    print(json.dumps({"ok": fail_count == 0, "items": results}, indent=2))
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
