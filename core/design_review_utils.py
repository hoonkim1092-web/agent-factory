"""
core/design_review_utils.py
=============================
설계 문서 교차 검증 — shared 로직.

사용처:
  1. core/hooks/design_review_hook.py (af.exe 런타임)
  2. scripts/design_review_trigger.py (Claude Code hook / CLI)
  3. scripts/design_review_watcher.py (백그라운드 데몬)

이 모듈은 frozen 빌드(af.exe)에서도 동작해야 하므로 core/에 위치한다.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from fnmatch import fnmatch
from pathlib import Path

# ── 트리거 대상 패턴 ─────────────────────────────────────────────────────────

INCLUDE_PATTERNS = [
    "docs/features/**/*.md",
    "docs/features/*.md",
    "docs/plans/**/*.md",
    "docs/plans/*.md",
    "docs/**/*design*.md",
    "docs/**/*feature*.md",
    "docs/*design*.md",
    "docs/*feature*.md",
    # YYYY-MM-DD-*.md 형식 날짜 포함 설계문서 — CLAUDE.md 문서 규칙 대응
    # flat/recursive 쌍을 모두 등록 (다른 키워드 패턴과 동일한 대칭)
    "docs/**/20??-??-??-*.md",
    "docs/20??-??-??-*.md",
]

EXCLUDE_PATTERNS = [
    "docs/archive/**",
    "docs/archive/*",
    "docs/code_review/**",
    "docs/code_review/*",
    "docs/reviews/**",
    "docs/reviews/*",
    # work-item 4-문서 세트는 별도 경로(af-doc-qa 3-agent)로 처리됨
    "docs/work-items/**",
    "docs/work-items/*",
    # 짧은 참조성 패턴 노트 — 2026-04-21-design-doc-review-gate.md §1.1 design 분류 제외 확정
    "docs/patterns/**",
    "docs/patterns/*",
]

# ── 코드 교차검증 패턴 ──────────────────────────────────────────────────────

CODE_INCLUDE_PATTERNS = [
    "core/**/*.py",
    "scripts/**/*.py",
    "skills/**/*.py",
]

CODE_EXCLUDE_PATTERNS = [
    "tests/**",
    "build/**",
    "dist/**",
    "**/__pycache__/**",
    "**/*.pyc",
]

MIN_DIFF_LINES = 5  # 최소 변경량 (미만이면 스킵)

SKIP_DIFF_PATTERNS = [
    r"^[\+\-]\s*(import |from .+ import )",
    r"^[\+\-]\s*(\"\"\"|\'\'\').*",
    r"^[\+\-]\s*#",
]

# ── 큐 디렉토리 (design/code 분리) ──────────────────────────────────────────

QUEUE_DIR = ".af_review_queue"
PENDING_DESIGN_DIR = os.path.join(QUEUE_DIR, "pending", "design")
PENDING_CODE_DIR = os.path.join(QUEUE_DIR, "pending", "code")
# 하위호환: 기존 pending/ 경로도 유지
PENDING_DIR = os.path.join(QUEUE_DIR, "pending")
NOTIFICATIONS_DIR = os.path.join(QUEUE_DIR, "notifications")
PID_FILE = os.path.join(QUEUE_DIR, ".watcher.pid")
SPAWN_LOCK_FILE = os.path.join(QUEUE_DIR, ".watcher.spawn.lock")
SPAWN_LOCK_TTL = 10  # seconds — spawn은 즉시 완료되므로 10s 초과면 stale
CODE_REVIEW_COUNT_FILE = os.path.join(QUEUE_DIR, ".code_review_count")


# ── 경로 매칭 ────────────────────────────────────────────────────────────────

def normalize_path(filepath: str, workspace: str) -> str:
    """절대경로를 workspace 기준 상대경로로 변환. 슬래시 통일."""
    try:
        rel = os.path.relpath(filepath, workspace)
    except ValueError:
        rel = filepath
    return rel.replace("\\", "/")


def _matches_glob(path: str, pattern: str) -> bool:
    """간단한 glob 매칭. ** = 임의 디렉토리, * = 임의 파일명."""
    if "**" in pattern:
        prefix, _, suffix = pattern.partition("**")
        prefix = prefix.rstrip("/")
        suffix = suffix.lstrip("/")
        if prefix and not path.startswith(prefix + "/") and path != prefix:
            return False
        remainder = path[len(prefix):].lstrip("/") if prefix else path
        if suffix:
            parts = remainder.split("/")
            for i in range(len(parts)):
                candidate = "/".join(parts[i:])
                if fnmatch(candidate, suffix):
                    return True
            return False
        return True
    return fnmatch(path, pattern)


def is_design_doc(filepath: str, workspace: str) -> bool:
    """파일이 설계 문서 트리거 대상인지 판정."""
    rel = normalize_path(filepath, workspace)

    for pattern in EXCLUDE_PATTERNS:
        if _matches_glob(rel, pattern):
            return False

    for pattern in INCLUDE_PATTERNS:
        if _matches_glob(rel, pattern):
            return True

    return False


def is_code_file(filepath: str, workspace: str) -> bool:
    """파일이 코드 교차검증 트리거 대상인지 판정."""
    rel = normalize_path(filepath, workspace)

    for pattern in CODE_EXCLUDE_PATTERNS:
        if _matches_glob(rel, pattern):
            return False

    for pattern in CODE_INCLUDE_PATTERNS:
        if _matches_glob(rel, pattern):
            return True

    return False


def check_code_review_budget(workspace: str) -> bool:
    """일일 코드 리뷰 횟수 제한 확인. True면 실행 가능."""
    count_path = os.path.join(workspace, CODE_REVIEW_COUNT_FILE)
    today = time.strftime("%Y-%m-%d")
    count = 0

    if os.path.exists(count_path):
        try:
            with open(count_path) as f:
                data = json.load(f)
            if data.get("date") == today:
                count = data.get("count", 0)
        except Exception:
            pass

    return count < 5  # 일일 최대 5회


def increment_code_review_count(workspace: str) -> None:
    """코드 리뷰 횟수 증가."""
    count_path = os.path.join(workspace, CODE_REVIEW_COUNT_FILE)
    today = time.strftime("%Y-%m-%d")
    count = 0

    if os.path.exists(count_path):
        try:
            with open(count_path) as f:
                data = json.load(f)
            if data.get("date") == today:
                count = data.get("count", 0)
        except Exception:
            pass

    os.makedirs(os.path.dirname(count_path), exist_ok=True)
    with open(count_path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "count": count + 1}, f)


# ── 큐 관리 ──────────────────────────────────────────────────────────────────

def pathhash(rel_path: str) -> str:
    """상대경로의 deterministic hash (앞 12자리)."""
    return hashlib.md5(rel_path.encode("utf-8")).hexdigest()[:12]


def _get_pending_dir(workspace: str, review_type: str = "design") -> str:
    """review_type별 pending 디렉토리 경로."""
    if review_type == "code":
        return os.path.join(workspace, PENDING_CODE_DIR)
    return os.path.join(workspace, PENDING_DESIGN_DIR)


def enqueue(
    filepath: str,
    workspace: str,
    source: str = "unknown",
    review_type: str = "design",
) -> str | None:
    """pending 큐에 리뷰 요청 추가. 이미 있으면 timestamp만 갱신."""
    rel = normalize_path(filepath, workspace)
    ph = pathhash(rel)
    pending_dir = _get_pending_dir(workspace, review_type)
    os.makedirs(pending_dir, exist_ok=True)

    queue_file = os.path.join(pending_dir, f"{ph}.json")
    entry = {
        "file_path": rel,
        "timestamp": time.time(),
        "trigger_source": source,
        "workspace": workspace,
        "review_type": review_type,
    }
    with open(queue_file, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2)

    return queue_file


# ── watcher 관리 ──────────────────────────────────────────────────────────────

HEARTBEAT_STALE_THRESHOLD = 660  # REVIEW_TIMEOUT(600) + POLL_INTERVAL(10) * 6

_STILL_ACTIVE = 259  # Windows STILL_ACTIVE exit code sentinel


def _process_alive(pid: int) -> bool:
    """Cross-platform 프로세스 생존 확인.

    Windows: os.kill(pid, 0)이 WinError 87을 raise하는 케이스가 있어
    ctypes.OpenProcess + GetExitCodeProcess로 교체.
    Unix: POSIX kill(pid, 0) 사용.
    """
    if platform.system() == "Windows":
        import ctypes  # stdlib — 항상 사용 가능

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return exit_code.value == _STILL_ACTIVE
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except OSError:
            return True  # 프로세스 존재하나 권한 없음


def _is_watcher_alive(workspace: str) -> bool:
    """PID 파일 기반 watcher 생존 확인 (heartbeat 방식)."""
    pid_path = os.path.join(workspace, PID_FILE)
    if not os.path.exists(pid_path):
        return False
    try:
        with open(pid_path) as f:
            raw = f.read().strip()
        # 하위호환: 순수 숫자면 구형 포맷 → 무조건 stale 판정
        if raw.isdigit():
            raise OSError("legacy pid format, treat as stale")

        data = json.loads(raw)
        pid = int(data["pid"])
        heartbeat = float(data.get("heartbeat", data.get("start_time", 0)))

        if not _process_alive(pid):
            raise OSError("process not alive")

        # heartbeat 기반 stale 감지:
        # process_review()가 최대 REVIEW_TIMEOUT(600s) 동기 블로킹하므로
        # HEARTBEAT_STALE_THRESHOLD(660s) 이상 미갱신이면 다른 프로세스
        if (time.time() - heartbeat) > HEARTBEAT_STALE_THRESHOLD:
            raise OSError("stale heartbeat")

        return True
    except (ValueError, OSError, ProcessLookupError, json.JSONDecodeError, KeyError):
        try:
            os.remove(pid_path)
        except OSError:
            pass
        return False


def _update_heartbeat(workspace: str) -> None:
    """매 poll마다 호출하여 watcher 생존을 증명. atomic write 사용."""
    pid_path = os.path.join(workspace, PID_FILE)
    if not os.path.exists(pid_path):
        return
    try:
        with open(pid_path) as f:
            data = json.load(f)
        data["heartbeat"] = time.time()
        pid_dir = os.path.dirname(pid_path)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=pid_dir)
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, pid_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception:
        pass


def _start_watcher(workspace: str) -> None:
    """watcher를 detached 백그라운드 프로세스로 시작."""
    watcher_script = os.path.join(workspace, "scripts", "design_review_watcher.py")
    if not os.path.exists(watcher_script):
        return

    kwargs: dict = {}
    if platform.system() == "Windows":
        # DETACHED_PROCESS: 부모 콘솔에서 완전 분리 (codex 등 부모 종료 시 같이 죽지 않음)
        # CREATE_NEW_PROCESS_GROUP: CTRL+C 시그널 격리
        _DETACHED_PROCESS = 0x00000008
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | _DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True

    env = os.environ.copy()
    env["PYTHONPATH"] = workspace + os.pathsep + env.get("PYTHONPATH", "")

    try:
        subprocess.Popen(
            [sys.executable, watcher_script, workspace],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=workspace,
            env=env,
            **kwargs,
        )
    except Exception:
        pass


def _try_acquire_spawn_lock(workspace: str) -> bool:
    """O_CREAT|O_EXCL 기반 spawn 락 원자적 취득. 성공 시 True."""
    lock_path = os.path.join(workspace, SPAWN_LOCK_FILE)
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    try:
        if os.path.exists(lock_path) and time.time() - os.path.getmtime(lock_path) > SPAWN_LOCK_TTL:
            os.remove(lock_path)
    except OSError:
        pass
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except (FileExistsError, OSError):
        return False


def _release_spawn_lock(workspace: str) -> None:
    try:
        os.remove(os.path.join(workspace, SPAWN_LOCK_FILE))
    except OSError:
        pass


def ensure_watcher(workspace: str) -> None:
    """watcher가 없으면 시작. O_CREAT|O_EXCL spawn 락으로 TOCTOU 제거."""
    if _is_watcher_alive(workspace):
        return
    if not _try_acquire_spawn_lock(workspace):
        return  # 다른 프로세스가 동시 스폰 중
    try:
        if not _is_watcher_alive(workspace):  # 락 취득 후 재확인
            _start_watcher(workspace)
    finally:
        _release_spawn_lock(workspace)


# ── 상태 조회 ─────────────────────────────────────────────────────────────────

def _count_pending(directory: str) -> list[dict]:
    """pending 디렉토리의 큐 항목을 읽어 반환."""
    items = []
    if not os.path.isdir(directory):
        return items
    for f in os.listdir(directory):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, f)) as fh:
                items.append(json.load(fh))
        except Exception:
            items.append({"file_path": f"{f} (unreadable)"})
    return items


def show_status(workspace: str) -> None:
    """큐 상태 출력."""
    design_items = _count_pending(os.path.join(workspace, PENDING_DESIGN_DIR))
    code_items = _count_pending(os.path.join(workspace, PENDING_CODE_DIR))
    # 하위호환: 기존 pending/ 루트에 있는 항목도 수집
    legacy_items = _count_pending(os.path.join(workspace, PENDING_DIR))
    legacy_items = [
        i for i in legacy_items
        if not i.get("review_type")  # 신규 포맷은 review_type 필드가 있음
    ]

    notif_dir = os.path.join(workspace, NOTIFICATIONS_DIR)
    notifs = []
    if os.path.isdir(notif_dir):
        notifs = [f for f in os.listdir(notif_dir) if f.endswith(".txt")]

    alive = _is_watcher_alive(workspace)

    print(f"[review] Watcher: {'running' if alive else 'stopped'}")
    print(f"[review] Design pending: {len(design_items) + len(legacy_items)}")
    for item in design_items + legacy_items:
        print(f"  - {item.get('file_path', '?')}")
    print(f"[review] Code pending: {len(code_items)}")
    for item in code_items:
        print(f"  - {item.get('file_path', '?')}")
    print(f"[review] Notifications: {len(notifs)}")

    # 코드 리뷰 예산
    budget_ok = check_code_review_budget(workspace)
    if not budget_ok:
        print("[review] Code review daily limit reached (5/5)")


# ── 동기 실행 ─────────────────────────────────────────────────────────────────

def run_sync(filepath: str, workspace: str, source: str) -> None:
    """watcher 없이 동기적으로 리뷰 실행."""
    watcher_script = os.path.join(workspace, "scripts", "design_review_watcher.py")
    if not os.path.exists(watcher_script):
        print("[design-review] watcher script not found", file=sys.stderr)
        return

    rel = normalize_path(filepath, workspace)
    try:
        subprocess.run(
            [sys.executable, watcher_script, workspace, "--sync", rel],
            cwd=workspace,
            timeout=900,
        )
    except subprocess.TimeoutExpired:
        print("[design-review] sync review timed out (900s)", file=sys.stderr)
    except Exception as e:
        print(f"[design-review] sync review failed: {e}", file=sys.stderr)
