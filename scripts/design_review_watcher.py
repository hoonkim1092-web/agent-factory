#!/usr/bin/env python3
"""
scripts/design_review_watcher.py
==================================
설계 문서 교차 검증 백그라운드 데몬.

.af_review_queue/pending/ 를 폴링하여 리뷰 실행 후 docs/reviews/에 결과 저장.

실행:
  - 자동: design_review_trigger.py가 detached spawn
  - 수동: python scripts/design_review_watcher.py <workspace>
  - 동기: python scripts/design_review_watcher.py <workspace> --sync <rel_path>

idle 180초 후 자동 종료. heartbeat 기반 생존 증명.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ── 상수 ──────────────────────────────────────────────────────────────────────

QUEUE_DIR = ".af_review_queue"
PENDING_DIR = os.path.join(QUEUE_DIR, "pending")
PENDING_DESIGN_DIR = os.path.join(QUEUE_DIR, "pending", "design")
PENDING_CODE_DIR = os.path.join(QUEUE_DIR, "pending", "code")
FAILED_DIR = os.path.join(QUEUE_DIR, "failed")
NOTIFICATIONS_DIR = os.path.join(QUEUE_DIR, "notifications")
PID_FILE = os.path.join(QUEUE_DIR, ".watcher.pid")

RESULTS_DIR = os.path.join("docs", "reviews")
PROMPTS_DIR = os.path.join("scripts", "prompts")

POLL_INTERVAL = 10   # seconds
QUIET_PERIOD_DESIGN = 8     # seconds — 설계 문서 연속 편집 대기
QUIET_PERIOD_CODE = 15      # seconds — 코드 연속 편집 대기 (빈번하므로 길게)
IDLE_TIMEOUT = 180   # seconds — 무활동 시 자동 종료 (설계 문서 작성 2-5분 고려)
MAX_PENDING_AGE = 900  # seconds — 이보다 오래된 pending은 stuck으로 간주
REVIEW_TIMEOUT = 600 # seconds — 단일 리뷰 실행 제한 (codex 자율 탐색 고려)

JUDGE_PRIORITY = ["claude", "codex", "gemini"]

# ── 공유 함수 (core/review_runner.py에서 import) ─────────────────────────────
# frozen build에서도 동작하도록 core/ 레이어에 위치.

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.review_runner import (  # noqa: E402
    detect_providers,
    select_review_pair,
    select_judge,
)


from core.review_runner import (  # noqa: E402
    _load_prompt,
    _run_provider,
    _build_review_prompt,
    run_critic,
    run_critic_review,
    run_cross,
    run_cross_review,
    run_aggregation,
)


def _read_document(workspace: str, rel_path: str) -> str:
    """설계 문서 읽기. 50KB 초과 시 앞 20KB + 뒤 10KB + 라인 넘버링."""
    full_path = os.path.join(workspace, rel_path)
    with open(full_path, encoding="utf-8") as f:
        content = f.read()

    if len(content) <= 50_000:
        lines = content.splitlines()
        return "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines))

    lines = content.splitlines()
    # 앞 부분: ~20KB
    front_lines = []
    front_size = 0
    front_end = 0
    for i, line in enumerate(lines):
        front_size += len(line) + 1
        if front_size > 20_000:
            front_end = i
            break
        front_lines.append(f"{i+1}: {line}")
    else:
        front_end = len(lines)

    # 뒷 부분: ~10KB
    back_lines = []
    back_size = 0
    back_start = len(lines)
    for i in range(len(lines) - 1, front_end - 1, -1):
        back_size += len(lines[i]) + 1
        if back_size > 10_000:
            back_start = i + 1
            break
        back_start = i

    back_numbered = [f"{i+1}: {lines[i]}" for i in range(back_start, len(lines))]
    omitted_kb = sum(len(lines[i]) + 1 for i in range(front_end, back_start)) // 1024

    truncation_marker = (
        f"\n--- [TRUNCATED: lines {front_end+1}-{back_start} omitted ({omitted_kb}KB)] ---\n"
    )

    return "\n".join(front_lines) + truncation_marker + "\n".join(back_numbered)


def _read_project_context(workspace: str) -> str:
    """docs/code_review/code-review.md 읽기 (있으면)."""
    path = os.path.join(workspace, "docs", "code_review", "code-review.md")
    if not os.path.exists(path):
        return "(프로젝트 컨텍스트 문서 없음)"
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if len(content) > 15_000:
            return content[:15_000] + "\n... (truncated)"
        return content
    except Exception:
        return "(읽기 실패)"



# ── 리뷰 실행 함수는 core/review_runner.py에서 import됨 (위쪽 참조) ──────────

# ── 결과 저장 ─────────────────────────────────────────────────────────────────

def _write_result(
    workspace: str,
    rel_path: str,
    providers_used: dict[str, str],
    mode: str,
    verdict_content: str,
    trigger_source: str,
    review_type: str = "design",
) -> str:
    """docs/reviews/ 에 결과 파일 저장. 파일 경로 반환."""
    results_dir = os.path.join(workspace, RESULTS_DIR)
    os.makedirs(results_dir, exist_ok=True)

    stem = Path(rel_path).stem
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d-%H%M%S")
    filename = f"{ts}-{stem}-{review_type}-review.md"
    result_path = os.path.join(results_dir, filename)

    type_label = {"design": "Design", "code": "Code", "document": "Document"}.get(
        review_type, review_type.title()
    )
    providers_str = ", ".join(f"{role}={name}" for role, name in providers_used.items())
    header = (
        f"# {type_label} Review: {stem}\n\n"
        f"> Source: {rel_path}\n"
        f"> Date: {now.strftime('%Y-%m-%d %H:%M')}\n"
        f"> Type: {review_type}\n"
        f"> Providers: {providers_str}\n"
        f"> Mode: {mode}\n"
        f"> Trigger: {trigger_source}\n\n"
        f"---\n\n"
    )

    with open(result_path, "w", encoding="utf-8") as f:
        f.write(header + verdict_content)

    return result_path


def _write_notification(workspace: str, rel_path: str, result_path: str) -> None:
    """알림 파일 생성."""
    notif_dir = os.path.join(workspace, NOTIFICATIONS_DIR)
    os.makedirs(notif_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = Path(rel_path).stem
    notif_path = os.path.join(notif_dir, f"{ts}-{stem}.txt")

    rel_result = os.path.relpath(result_path, workspace).replace("\\", "/")
    msg = f"[design-review] Review complete: {rel_path} → {rel_result}"
    with open(notif_path, "w", encoding="utf-8") as f:
        f.write(msg)


# ── 단일 문서 리뷰 처리 ───────────────────────────────────────────────────────

def _prompt_prefix_for_type(review_type: str) -> str:
    """review_type별 프롬프트 파일 접두사."""
    return {"code": "code", "document": "doc"}.get(review_type, "design")


def process_review(
    workspace: str,
    rel_path: str,
    trigger_source: str,
    review_type: str = "design",
) -> None:
    """하나의 파일에 대해 리뷰 실행. review_type에 따라 프롬프트 분기."""
    providers = detect_providers()

    if not providers:
        print(f"[watcher] No providers available, skipping: {rel_path}")
        _write_notification_skip(workspace, rel_path, "프로바이더 없음")
        return

    # review_type에 따라 프롬프트 접두사 결정
    prefix = _prompt_prefix_for_type(review_type)
    critic_prompt = f"{prefix}_critic"
    cross_prompt = f"{prefix}_cross_review"
    agg_prompt = f"{prefix}_aggregation"

    # 코드 리뷰일 때: git diff를 doc_content로 사용
    if review_type == "code":
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD", "--", rel_path],
                capture_output=True, text=True, timeout=10, cwd=workspace,
            )
            doc_content = result.stdout[:8000] if result.stdout else f"(no diff for {rel_path})"
        except Exception:
            doc_content = _read_document(workspace, rel_path)
    else:
        doc_content = _read_document(workspace, rel_path)

    context = _read_project_context(workspace)
    context_path = os.path.join("docs", "code_review", "code-review.md")

    if len(providers) == 1:
        # ── 단일 프로바이더: critic만 ──
        print(f"[watcher] Single provider ({providers[0]}), {review_type} critic: {rel_path}")
        critic_result = run_critic(
            providers[0], doc_content, context, workspace,
            rel_path=rel_path, context_path=context_path,
            prompt_name=critic_prompt,
        )

        result_path = _write_result(
            workspace, rel_path,
            {"critic": providers[0]},
            f"single-provider ({review_type} critic only)",
            critic_result,
            trigger_source,
            review_type=review_type,
        )
    else:
        # ── 복수 프로바이더: critic + cross + 취합 ──
        p_a, p_b = select_review_pair(providers)
        judge = select_judge(providers)
        print(f"[watcher] {review_type} cross review: critic={p_a}, cross={p_b}, judge={judge}: {rel_path}")

        # 병렬 실행
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_critic = pool.submit(
                run_critic, p_a, doc_content, context, workspace,
                rel_path=rel_path, context_path=context_path,
                prompt_name=critic_prompt,
            )
            future_cross = pool.submit(
                run_cross, p_b, doc_content, context, workspace,
                rel_path=rel_path, context_path=context_path,
                prompt_name=cross_prompt,
            )

            critic_result = future_critic.result()
            cross_result = future_cross.result()

        # 취합 판정
        final = run_aggregation(
            judge, critic_result, cross_result, doc_content, workspace,
            prompt_name=agg_prompt,
        )

        result_path = _write_result(
            workspace, rel_path,
            {"critic": p_a, "cross": p_b, "judge": judge},
            f"cross-review ({review_type}, {len(providers)} providers)",
            final,
            trigger_source,
            review_type=review_type,
        )

    _write_notification(workspace, rel_path, result_path)
    print(f"[watcher] Done: {rel_path} → {result_path}")


def _write_notification_skip(workspace: str, rel_path: str, reason: str) -> None:
    """스킵 알림."""
    notif_dir = os.path.join(workspace, NOTIFICATIONS_DIR)
    os.makedirs(notif_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = Path(rel_path).stem
    notif_path = os.path.join(notif_dir, f"{ts}-{stem}.txt")
    with open(notif_path, "w", encoding="utf-8") as f:
        f.write(f"[design-review] Skipped: {rel_path} — {reason}")


# ── 큐 처리 루프 ──────────────────────────────────────────────────────────────

def _move_to_failed(workspace: str, queue_file: str, error: str) -> None:
    """실패 파일을 failed/ 로 이동."""
    failed_dir = os.path.join(workspace, FAILED_DIR)
    os.makedirs(failed_dir, exist_ok=True)
    try:
        with open(queue_file, encoding="utf-8") as f:
            data = json.load(f)
        data["error"] = error
        data["failed_at"] = time.time()
        dest = os.path.join(failed_dir, os.path.basename(queue_file))
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.remove(queue_file)
    except Exception:
        pass


def _scan_pending_dir(
    workspace: str,
    pending_dir: str,
    quiet_period: float,
    review_type: str,
) -> list[tuple[str, dict, str]]:
    """pending 디렉토리에서 처리 가능한 항목 수집.

    Returns:
        list of (queue_file_path, data_dict, review_type)
    """
    full_dir = os.path.join(workspace, pending_dir)
    if not os.path.isdir(full_dir):
        return []

    items = []
    for fname in sorted(f for f in os.listdir(full_dir) if f.endswith(".json")):
        queue_file = os.path.join(full_dir, fname)

        # quiet period 체크
        try:
            mtime = os.path.getmtime(queue_file)
            if time.time() - mtime < quiet_period:
                continue
        except OSError:
            continue

        try:
            with open(queue_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            os.remove(queue_file)
            continue

        items.append((queue_file, data, data.get("review_type", review_type)))

    return items


def process_queue(workspace: str) -> int:
    """pending 큐에서 리뷰 처리. design + code 양쪽 폴링. 처리 건수 반환."""
    # 하위호환: 기존 pending/ 루트에 있는 항목 (design으로 간주)
    items = _scan_pending_dir(workspace, PENDING_DIR, QUIET_PERIOD_DESIGN, "design")
    # 신규: design/code 분리 큐
    items += _scan_pending_dir(workspace, PENDING_DESIGN_DIR, QUIET_PERIOD_DESIGN, "design")
    items += _scan_pending_dir(workspace, PENDING_CODE_DIR, QUIET_PERIOD_CODE, "code")

    if not items:
        return 0

    # 코드 리뷰 예산 체크
    from core.design_review_utils import check_code_review_budget, increment_code_review_count

    processed = 0
    for queue_file, data, review_type in items:
        rel_path = data.get("file_path", "")
        trigger_source = data.get("trigger_source", "unknown")

        # 실제 파일 존재 확인
        if not os.path.exists(os.path.join(workspace, rel_path)):
            os.remove(queue_file)
            continue

        # 코드 리뷰 예산 체크
        if review_type == "code" and not check_code_review_budget(workspace):
            _write_notification_skip(workspace, rel_path, "일일 한도(5회) 도달")
            os.remove(queue_file)
            continue

        try:
            process_review(workspace, rel_path, trigger_source, review_type=review_type)
            os.remove(queue_file)
            processed += 1

            if review_type == "code":
                increment_code_review_count(workspace)
        except Exception as e:
            print(f"[watcher] Error processing {rel_path}: {e}", file=sys.stderr)
            _move_to_failed(workspace, queue_file, str(e))

    return processed


# ── PID 관리 ──────────────────────────────────────────────────────────────────

def _write_pid(workspace: str) -> None:
    pid_dir = os.path.join(workspace, QUEUE_DIR)
    os.makedirs(pid_dir, exist_ok=True)
    pid_path = os.path.join(workspace, PID_FILE)
    now = time.time()
    data = {"pid": os.getpid(), "start_time": now, "heartbeat": now}
    tmp_fd, tmp_path = tempfile.mkstemp(dir=pid_dir)
    with os.fdopen(tmp_fd, "w") as f:
        json.dump(data, f)
    os.replace(tmp_path, pid_path)
    atexit.register(_remove_pid, workspace)


def _remove_pid(workspace: str) -> None:
    pid_path = os.path.join(workspace, PID_FILE)
    try:
        os.remove(pid_path)
    except OSError:
        pass


# ── pending 상태 확인 ─────────────────────────────────────────────────────────

def _has_actionable_pending(workspace: str) -> bool:
    """quiet period를 경과한 처리 가능한 pending이 있는지 확인.
    stuck 파일(MAX_PENDING_AGE 초과)은 무시하여 watcher 영구 생존 방지.
    design + code + 기존 루트 큐 모두 검사."""
    dirs_and_quiet = [
        (os.path.join(workspace, PENDING_DIR), QUIET_PERIOD_DESIGN),
        (os.path.join(workspace, PENDING_DESIGN_DIR), QUIET_PERIOD_DESIGN),
        (os.path.join(workspace, PENDING_CODE_DIR), QUIET_PERIOD_CODE),
    ]
    now = time.time()
    for pending_dir, quiet_period in dirs_and_quiet:
        if not os.path.isdir(pending_dir):
            continue
        for fname in os.listdir(pending_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(pending_dir, fname)
            try:
                age = now - os.path.getmtime(fpath)
            except OSError:
                continue
            if quiet_period <= age <= MAX_PENDING_AGE:
                return True
    return False


# ── 메인 루프 ─────────────────────────────────────────────────────────────────

def run_daemon(workspace: str) -> None:
    """폴링 데몬. idle timeout 후 자동 종료. heartbeat로 생존 증명."""
    # core/ 모듈에서 heartbeat 유틸 import (watcher에서 처음 사용)
    try:
        from core.design_review_utils import _update_heartbeat
    except ImportError:
        _update_heartbeat = None  # type: ignore[assignment]

    _write_pid(workspace)
    print(f"[watcher] Started (pid={os.getpid()}, idle_timeout={IDLE_TIMEOUT}s)")

    last_activity = time.time()

    try:
        while True:
            processed = process_queue(workspace)
            if processed > 0:
                last_activity = time.time()

            # actionable pending이 있으면 idle 타이머 리셋
            if _has_actionable_pending(workspace):
                last_activity = time.time()

            # heartbeat 갱신
            if _update_heartbeat is not None:
                _update_heartbeat(workspace)

            # idle timeout 체크
            if time.time() - last_activity > IDLE_TIMEOUT:
                print("[watcher] Idle timeout, shutting down")
                break

            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("[watcher] Interrupted")
    finally:
        _remove_pid(workspace)


def run_sync_single(workspace: str, rel_path: str) -> None:
    """단일 문서 동기 리뷰."""
    print(f"[watcher] Sync review: {rel_path}")
    process_review(workspace, rel_path, "manual-sync")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Design review watcher daemon")
    parser.add_argument("workspace", help="프로젝트 워크스페이스 루트")
    parser.add_argument("--sync", metavar="REL_PATH", help="단일 문서 동기 리뷰")
    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    if not os.path.isdir(workspace):
        print(f"[watcher] workspace not found: {workspace}", file=sys.stderr)
        sys.exit(1)

    if args.sync:
        run_sync_single(workspace, args.sync)
    else:
        run_daemon(workspace)


if __name__ == "__main__":
    main()
