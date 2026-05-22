#!/usr/bin/env python3
"""sync_claude_memory — Claude Code project memory ↔ Supabase 동기화.

Usage:
    python scripts/sync_claude_memory.py --mode push   # local → Supabase
    python scripts/sync_claude_memory.py --mode pull   # Supabase → local
    python scripts/sync_claude_memory.py --mode pull --dry-run
    python scripts/sync_claude_memory.py --mode push --memory-dir /path/to/memory

Security note: memory/*.md 파일 내용이 Supabase에 평문으로 저장됨.
SUPABASE_KEY 보안 관리 필수. symlink 파일은 업로드 제외.

Supabase DDL (artifacts/claude_memory_schema.sql 참조):
    CREATE TABLE claude_memory (
        project_id  TEXT        PRIMARY KEY,
        machine     TEXT        NOT NULL    DEFAULT 'unknown',
        updated_at  TIMESTAMPTZ NOT NULL    DEFAULT now(),
        files       JSONB       NOT NULL    DEFAULT '{}'::jsonb
    );
"""

import argparse
import json
import os
import socket
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLE_DEFAULT = "claude_memory"


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

def _load_dotenv(root: Path) -> None:
    env_path = root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mtime_iso(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Memory dir detection
# ---------------------------------------------------------------------------

def _path_to_claude_key(path: Path) -> str:
    """절대 경로 → Claude Code ~/.claude/projects/ 하위 디렉터리 이름으로 인코딩.

    인코딩 규칙: 각 문자에서 ':' → '-', '\\' → '-', '/' → '-'
    예) D:\\hoonProJect\\agent-factory → D--hoonProJect-agent-factory
    """
    s = str(path.resolve())
    return s.replace(":", "-").replace("\\", "-").replace("/", "-")


_NOISE_SEGMENTS = ("worktrees", "tmp", "temp", "test", "tests")


def _find_memory_dir(repo_name: str, repo_root: Path | None = None) -> Path | None:
    """~/.claude/projects/ 아래에서 memory/ 폴더를 찾는다.

    repo_name substring 매칭 후:
    - "worktrees", "tmp", "test" 등 노이즈 세그먼트가 없는 후보를 우선
    - 후보가 여럿이면 경로 길이(짧을수록 원본 clone에 가까움)로 선택
    """
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.exists():
        return None

    try:
        project_dirs = list(claude_projects.iterdir())
    except (PermissionError, OSError):
        return None

    repo_key = repo_name.lower().replace("-", "").replace("_", "")
    candidates: list[Path] = []

    for project_dir in project_dirs:
        if not project_dir.is_dir():
            continue
        try:
            encoded_key = project_dir.name.lower().replace("-", "").replace("_", "")
            if repo_key not in encoded_key:
                continue
            mem = project_dir / "memory"
            if mem.exists() and mem.is_dir():
                candidates.append(mem)
        except (PermissionError, OSError):
            continue

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def _score(mem: Path) -> tuple[int, int]:
        name_lower = mem.parent.name.lower()
        noise = sum(1 for s in _NOISE_SEGMENTS if s in name_lower)
        return (noise, len(mem.parent.name))  # 노이즈 적고, 이름 짧은 것 우선

    return min(candidates, key=_score)


# ---------------------------------------------------------------------------
# Supabase HTTP
# ---------------------------------------------------------------------------

def _http_json(method: str, url: str, headers: dict, body=None) -> dict | list:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body_text}") from e


def _supabase_env() -> tuple[str, str, str, str]:
    sb_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    sb_key = os.getenv("SUPABASE_KEY", "").strip()
    table = os.getenv("CLAUDE_MEMORY_TABLE", TABLE_DEFAULT)
    machine = os.getenv("SYNC_MACHINE_ID", socket.gethostname())
    return sb_url, sb_key, table, machine


def _fetch_remote_row(sb_url: str, sb_key: str, table: str, project_id: str) -> dict | None:
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }
    q = urllib.parse.quote(project_id, safe="")
    url = f"{sb_url}/rest/v1/{table}?project_id=eq.{q}&select=project_id,machine,updated_at,files&limit=1"
    rows = _http_json("GET", url, headers)
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Atomic file write
# ---------------------------------------------------------------------------

def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

def _print_json(payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe = text.encode(enc, errors="replace").decode(enc, errors="replace")
        print(safe)

# ---------------------------------------------------------------------------
# Push (local → Supabase)
# ---------------------------------------------------------------------------

def _push(memory_dir: Path, project_id: str, dry_run: bool) -> dict:
    sb_url, sb_key, table, machine = _supabase_env()
    if not sb_url or not sb_key:
        return {"ok": False, "error": "missing_supabase_env (SUPABASE_URL / SUPABASE_KEY)"}

    # 로컬 파일 수집 (symlink 제외)
    local_files: dict[str, dict] = {}
    for md_file in sorted(memory_dir.glob("*.md")):
        if md_file.is_symlink():
            continue
        local_files[md_file.name] = {
            "content": md_file.read_text(encoding="utf-8"),
            "mtime": _mtime_iso(md_file),
        }

    if not local_files:
        return {"ok": True, "pushed": 0, "note": "memory dir is empty"}

    if dry_run:
        print(f"[DRY-RUN] would push {len(local_files)} files: {list(local_files)}")
        return {"ok": True, "dry_run": True, "files": list(local_files)}

    # 기존 row를 먼저 가져와서 다른 PC의 파일 보존 (merge)
    try:
        existing = _fetch_remote_row(sb_url, sb_key, table, project_id)
    except Exception as fetch_err:
        print(f"[WARN] remote fetch 실패 — 다른 PC 파일 병합 불가, 로컬만 push ({fetch_err})")
        existing = None
    remote_files: dict = (existing.get("files") or {}) if existing else {}

    # remote의 파일을 base로, 로컬을 덮어씀 (로컬이 우선)
    merged = {**remote_files, **local_files}

    row = {
        "project_id": project_id,
        "machine": machine,
        "updated_at": _now_iso(),
        "files": merged,
    }
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    url = f"{sb_url}/rest/v1/{table}?on_conflict=project_id"
    result = _http_json("POST", url, headers, [row])
    return {"ok": True, "pushed": len(local_files), "merged_total": len(merged), "result": result}


# ---------------------------------------------------------------------------
# Pull (Supabase → local)
# ---------------------------------------------------------------------------

def _pull(memory_dir: Path, project_id: str, dry_run: bool, overwrite: bool) -> dict:
    sb_url, sb_key, table, _machine = _supabase_env()
    if not sb_url or not sb_key:
        return {"ok": False, "error": "missing_supabase_env (SUPABASE_URL / SUPABASE_KEY)"}

    remote = _fetch_remote_row(sb_url, sb_key, table, project_id)
    if not remote:
        return {"ok": True, "pulled": 0, "note": "no remote record found"}

    remote_files: dict = remote.get("files") or {}
    if not remote_files:
        return {"ok": True, "pulled": 0, "note": "remote record has no files"}

    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_dir_resolved = memory_dir.resolve()
    written, skipped = 0, 0

    for filename, meta in remote_files.items():
        # path traversal 방지 — 파일명만 추출
        safe_name = Path(filename).name
        if not safe_name or safe_name.startswith("."):
            continue
        local_path = memory_dir / safe_name
        # 경로 이탈 최종 확인
        if not local_path.resolve().is_relative_to(memory_dir_resolved):
            print(f"[WARN] path traversal 차단: {filename}")
            continue

        remote_mtime = meta.get("mtime", "")
        content = meta.get("content", "")

        if not overwrite and local_path.exists():
            try:
                local_mtime = _mtime_iso(local_path)
            except OSError:
                local_mtime = ""
            if local_mtime >= remote_mtime:
                skipped += 1
                continue

        if dry_run:
            action = "write" if not local_path.exists() else "overwrite"
            print(f"[DRY-RUN] would {action}: {safe_name}  (remote={remote_mtime})")
            written += 1
            continue

        _write_atomic(local_path, content)
        written += 1

    return {
        "ok": True,
        "pulled": written,
        "skipped": skipped,
        "remote_machine": remote.get("machine"),
        "remote_updated_at": remote.get("updated_at"),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Claude Code memory ↔ Supabase 동기화")
    parser.add_argument("--mode", choices=["push", "pull"], required=True)
    parser.add_argument("--project-id", default="agent-factory",
                        help="Supabase row key (default: agent-factory)")
    parser.add_argument("--memory-dir", default="",
                        help="memory 폴더 경로 (기본: 자동 탐색)")
    parser.add_argument("--overwrite", action="store_true",
                        help="pull 시 로컬이 더 최신이어도 덮어씀")
    parser.add_argument("--dry-run", action="store_true",
                        help="실제 I/O 없이 동작만 출력")
    args = parser.parse_args()

    _load_dotenv(REPO_ROOT)

    if args.memory_dir:
        memory_dir = Path(args.memory_dir).expanduser()
    else:
        memory_dir = _find_memory_dir(args.project_id, REPO_ROOT)
        if not memory_dir:
            _print_json({
                "ok": False,
                "error": f"memory dir not found for '{args.project_id}' under ~/.claude/projects/",
            })
            sys.exit(1)

    print(f"[claude-memory] mode={args.mode}  dir={memory_dir}  project={args.project_id}")

    try:
        if args.mode == "push":
            result = _push(memory_dir, args.project_id, args.dry_run)
        else:
            result = _pull(memory_dir, args.project_id, args.dry_run, args.overwrite)
    except Exception as e:
        _print_json({"ok": False, "error": str(e)})
        sys.exit(1)

    _print_json(result)
    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
