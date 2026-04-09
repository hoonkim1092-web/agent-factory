#!/usr/bin/env python3
"""
scripts/blueprint_updater.py
================================
Master_Blueprint.md §12 자동 업데이트 — called from:
  1. Claude Code PostToolUse hook  (after .py edits)
  2. git post-commit hook
  3. Manual: python scripts/blueprint_updater.py [workspace] [--context "..."]

Updates Master_Blueprint.md §12 변경 이력 + §0 새 파일 감지.
Always exits 0 so hooks are never blocked.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import time
from datetime import datetime

BLUEPRINT_REL = "Master_Blueprint.md"
DIFF_MAX_CHARS = 6000
DEBOUNCE_FILE = os.path.join(".af_review_queue", ".blueprint_debounce")
QUIET_PERIOD_SEC = 15

# Blueprint 업데이트 대상 파일 패턴
TRIGGER_PREFIXES = ("core/", "scripts/", "skills/")
TRIGGER_FILES = ("af.spec", "version.py", "run_factory_cli.py", "model_utils.py")


# ── git helpers ──────────────────────────────────────────────────────────────

def _git(args: list[str], cwd: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _detect_workspace() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return os.getcwd()


def _changed_files(workspace: str) -> list[str]:
    """Unstaged + staged changed files."""
    seen: list[str] = []
    for extra in [["HEAD"], ["--staged"]]:
        for line in _git(["diff", "--name-only"] + extra, workspace).splitlines():
            f = line.strip()
            if f and f not in seen:
                seen.append(f)
    return seen


def _new_files(workspace: str) -> list[str]:
    """신규 추가된 파일 (git diff --diff-filter=A)."""
    out = _git(["diff", "--diff-filter=A", "--name-only", "HEAD"], workspace)
    return [f.strip() for f in out.splitlines() if f.strip()]


def _diff_content(workspace: str) -> str:
    out = _git(["diff", "HEAD"], workspace, timeout=15)
    if len(out) > DIFF_MAX_CHARS:
        return out[:DIFF_MAX_CHARS] + "\n... (truncated)"
    return out


def _short_commit(workspace: str) -> str:
    return _git(["rev-parse", "--short", "HEAD"], workspace).strip()


def _read_version(workspace: str) -> str:
    ver_path = os.path.join(workspace, "version.py")
    try:
        with open(ver_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r'__version__\s*=\s*["\'](.+?)["\']', line)
                if m:
                    return f"v{m.group(1)}"
    except Exception:
        pass
    return "v?.?.?"


# ── debounce ────────────────────────────────────────────────────────────────

def _should_run_debounce(workspace: str) -> bool:
    debounce_path = os.path.join(workspace, DEBOUNCE_FILE)
    if os.path.exists(debounce_path):
        try:
            mtime = os.path.getmtime(debounce_path)
            if time.time() - mtime < QUIET_PERIOD_SEC:
                return False
        except Exception:
            pass
    try:
        os.makedirs(os.path.dirname(debounce_path), exist_ok=True)
        with open(debounce_path, "w") as f:
            f.write("")
    except Exception:
        pass
    return True


# ── trigger check ───────────────────────────────────────────────────────────

def _has_trigger_files(changed: list[str]) -> bool:
    """변경 파일 중 Blueprint 업데이트 대상이 있는지."""
    for f in changed:
        if any(f.startswith(p) for p in TRIGGER_PREFIXES):
            return True
        if f in TRIGGER_FILES:
            return True
    return False


# ── LLM changelog generation ───────────────────────────────────────────────

def _llm_changelog(changed: list[str], diff_text: str, context: str) -> str:
    """LLM에게 git diff를 주고 §12 형식 변경 이력 1행을 생성."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from core.control_plane_llm import ControlPlaneLLM
        llm = ControlPlaneLLM()
        if not llm.is_available():
            return ""
    except Exception:
        return ""

    files_str = ", ".join(changed[:20])
    prompt = (
        "Analyze the git diff and generate a single Korean changelog entry.\n\n"
        f"[Changed Files ({len(changed)})]\n{files_str}\n\n"
        f"[Diff]\n{diff_text[:5000]}\n\n"
        f"[Context]\n{context or 'development session'}\n\n"
        "## Output Format (single line, Korean)\n"
        "type(scope): 한줄 요약 — 세부 변경 3-5개\n\n"
        "## Rules\n"
        "- type: feat, fix, refactor, chore, docs 중 하나\n"
        "- scope: 주요 변경 모듈명\n"
        "- 한줄 요약 뒤 em dash(—)로 세부 변경 나열\n"
        "- 새 파일이면 '신규' 표시, 메서드 변경이면 메서드명 포함\n"
        "- 한 줄만 출력, 마크다운 불필요\n"
    )
    try:
        result = llm.generate(prompt) or ""
        # 첫 줄만 사용
        return result.strip().splitlines()[0] if result.strip() else ""
    except Exception:
        return ""


def _fallback_changelog(changed: list[str], context: str) -> str:
    """LLM 없이 최소 이력 행 생성."""
    if not changed:
        return f"chore: {context or 'code update'}"
    first = changed[0]
    # 일관된 scope: 첫 디렉토리명 사용 (core, scripts, skills 등)
    scope = first.split("/")[0] if "/" in first else os.path.splitext(first)[0]
    files_str = ", ".join(os.path.basename(f) for f in changed[:5])
    if len(changed) > 5:
        files_str += f" (+{len(changed) - 5})"
    return f"chore({scope}): {context or 'code update'} — {files_str}"


# ── §0 new file detection (AST based, no LLM) ──────────────────────────────

def _extract_ast_symbols(filepath: str) -> tuple[list[str], list[str]]:
    """top-level 클래스와 public 함수 추출."""
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        classes = [n.name for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef)]
        funcs = [n.name for n in ast.iter_child_nodes(tree)
                 if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
        return classes[:3], funcs[:3]
    except Exception:
        return [], []


def _update_section_0(blueprint_path: str, new_core_files: list[str], workspace: str) -> bool:
    """§0 core/ 테이블에 새 파일 행 추가. 추가했으면 True."""
    if not new_core_files:
        return False

    try:
        with open(blueprint_path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return False

    added = False
    for rel_path in new_core_files:
        if not rel_path.startswith("core/") or not rel_path.endswith(".py"):
            continue
        # 이미 §0에 있으면 스킵
        check_name = rel_path.replace("\\", "/")
        if check_name in content or f"`{check_name}`" in content:
            continue

        full_path = os.path.join(workspace, rel_path)
        if not os.path.exists(full_path):
            continue

        classes, funcs = _extract_ast_symbols(full_path)
        symbols = ", ".join(f"`{c}`" for c in classes) or ", ".join(f"`{f}()`" for f in funcs) or "—"
        # 파일명에서 역할 추론
        stem = os.path.splitext(os.path.basename(rel_path))[0]
        role = stem.replace("_", " ")

        new_row = f"| `{check_name}` | {role} | {symbols} |"

        # "### 서브디렉토리" 직전에 삽입
        marker = "### 서브디렉토리"
        idx = content.find(marker)
        if idx == -1:
            print(f"[blueprint_updater] WARNING: '### 서브디렉토리' marker not found, "
                  f"skipping §0 update for {rel_path}", file=sys.stderr)
            continue
        content = content[:idx] + new_row + "\n" + content[idx:]
        added = True

    if added:
        _atomic_write(blueprint_path, content)
    return added


# ── §12 update ──────────────────────────────────────────────────────────────

def _already_logged(blueprint_path: str, commit_hash: str) -> bool:
    """동일 커밋이 이미 §12에 기록되었는지."""
    if not commit_hash:
        return False
    try:
        with open(blueprint_path, encoding="utf-8") as f:
            return commit_hash in f.read()
    except Exception:
        return False


def _prepend_to_section_12(blueprint_path: str, entry: str, version: str) -> bool:
    """§12 테이블 헤더 행 바로 다음에 새 행 삽입."""
    try:
        with open(blueprint_path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return False

    date_str = datetime.now().strftime("%Y-%m-%d")
    new_row = f"| {date_str} | {version} | {entry} |"

    # §12 섹션을 먼저 찾고, 그 안의 테이블 구분선을 찾음
    section_marker = "## §12 변경 이력"
    section_idx = content.find(section_marker)
    if section_idx == -1:
        return False

    table_marker = "|------|------|----------|"
    idx = content.find(table_marker, section_idx)
    if idx == -1:
        return False

    insert_pos = idx + len(table_marker)
    content = content[:insert_pos] + "\n" + new_row + content[insert_pos:]
    _atomic_write(blueprint_path, content)
    return True


def _update_header_metadata(blueprint_path: str, version: str) -> None:
    """<!-- last_updated: ... | version: ... --> 갱신."""
    try:
        with open(blueprint_path, encoding="utf-8") as f:
            content = f.read()
        date_str = datetime.now().strftime("%Y-%m-%d")
        updated = re.sub(
            r"<!-- last_updated: .+? \| version: .+? -->",
            f"<!-- last_updated: {date_str} | version: {version} -->",
            content,
            count=1,
        )
        if updated != content:
            _atomic_write(blueprint_path, updated)
    except Exception:
        pass


# ── file write helpers ──────────────────────────────────────────────────────

def _atomic_write(path: str, content: str) -> None:
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ── main ────────────────────────────────────────────────────────────────────

def update_blueprint(workspace: str, context: str, no_llm: bool) -> bool:
    """Master_Blueprint.md 자동 업데이트. 성공 시 True."""
    changed = _changed_files(workspace)
    if not changed or not _has_trigger_files(changed):
        return False

    blueprint_path = os.path.join(os.path.abspath(workspace), BLUEPRINT_REL)
    if not os.path.exists(blueprint_path):
        return False

    commit = _short_commit(workspace)
    if _already_logged(blueprint_path, commit):
        return False

    version = _read_version(workspace)

    # §12 변경 이력 추가
    if not no_llm:
        diff_text = _diff_content(workspace)
        entry = _llm_changelog(changed, diff_text, context)
    else:
        entry = ""

    if not entry:
        entry = _fallback_changelog(changed, context)

    updated = _prepend_to_section_12(blueprint_path, entry, version)

    # §0 새 파일 감지 (AST 기반, LLM 불필요)
    new_files = _new_files(workspace)
    new_core = [f for f in new_files if f.startswith("core/") and f.endswith(".py")]
    if new_core:
        _update_section_0(blueprint_path, new_core, workspace)

    # 헤더 메타데이터 갱신
    if updated:
        _update_header_metadata(blueprint_path, version)
        print(f"[blueprint_updater] {blueprint_path} updated — {entry[:80]}")

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-update Master_Blueprint.md §12 changelog and §0 file table"
    )
    parser.add_argument(
        "workspace", nargs="?", default=None,
        help="Workspace/git-root directory (default: auto-detect)"
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Skip LLM — fallback to file-list based entry"
    )
    parser.add_argument(
        "--context", default="",
        help="Short description of current work"
    )
    args = parser.parse_args()

    workspace = args.workspace or _detect_workspace()
    if not os.path.isdir(workspace):
        print(f"[blueprint_updater] workspace not found: {workspace}", file=sys.stderr)
        sys.exit(0)

    # debounce (PostToolUse에서 빈번 호출 방지)
    if not args.no_llm and not _should_run_debounce(workspace):
        sys.exit(0)

    try:
        update_blueprint(workspace, args.context, args.no_llm)
    except Exception as exc:
        print(f"[blueprint_updater] error: {exc}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
