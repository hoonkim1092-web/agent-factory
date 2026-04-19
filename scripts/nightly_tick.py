"""야간 자율 파이프라인 tick 진입점.

launchd가 15분마다 이 스크립트를 기동한다.
각 tick은 독립 프로세스이며, flock으로 동시 실행을 방지한다.

동작:
  1. flock 획득 (실패 시 skip)
  2. state_snapshot.json 로드
  3. 자율 모드 활성화 여부 확인
  4. 예산 확인
  5. 이번 tick에 할 일 결정 + 실행
  6. state atomic write + 요약 갱신
  7. flock 해제 + exit
"""
from __future__ import annotations

import fcntl
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 레포 루트를 sys.path에 추가 (launchd가 cwd를 보장하지 않음)
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from core.nightly_state import (
    NightlyState,
    load_state,
    lock_path,
    make_tick_id,
    mark_alert,
    clear_alert,
    save_state,
)
from scripts.nightly_summary import write_summary


# ── 타임아웃 설정 ──────────────────────────────────────────
SOFT_DEADLINE_SEC = 10 * 60   # 10분
HARD_DEADLINE_SEC = 14 * 60   # 14분 (launchd 다음 tick 겹침 방지)
ALERT_AFTER_CONSEC_FAIL = 5

_tick_start: float = 0.0
_deadline_exceeded = False


def _sigterm_handler(signum, frame):
    global _deadline_exceeded
    _deadline_exceeded = True


def deadline_exceeded() -> bool:
    return _deadline_exceeded or (time.monotonic() - _tick_start) >= HARD_DEADLINE_SEC


# ── flock 헬퍼 ────────────────────────────────────────────
def _acquire_flock(lock_file: Path) -> "tuple[bool, int | None]":
    """non-blocking exclusive flock 시도. 성공 시 (True, fd), 실패 시 (False, None)."""
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True, fd
    except OSError:
        os.close(fd)
        return False, None


def _release_flock(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except OSError:
        pass


# ── tick 액션 ─────────────────────────────────────────────
def _dispatch_actions(state: NightlyState, workspace: str, tick_id: str) -> bool:
    """이번 tick에서 할 일을 결정하고 실행한다.

    진전이 있었으면 True, 없었으면 False를 반환한다.
    """
    from core.project_task_board import (
        load_project_board,
        next_board_tasks,
        board_is_complete,
    )
    from core.model_router import ModelRouter

    board = load_project_board(workspace)
    if not board or board_is_complete(board):
        return False

    # 유효 롤 목록 추출
    # board 스키마: top-level `tasks` flat list, 각 task에 `owner_role` (project_task_board.py 구조).
    # 기존 `board["modules"][*]["tasks"][*]["role"]` 접근은 스키마 mismatch로 항상 빈 결과였음 (B2-1).
    roles_in_board: list[str] = []
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        r = task.get("owner_role", "")
        if r and r not in roles_in_board:
            roles_in_board.append(r)

    if not roles_in_board:
        return False

    # 현재 진행 중인 태스크 복원
    active = state.active_assignments or {}
    busy_roles = set(active.keys())
    available_roles = [r for r in roles_in_board if r not in busy_roles]

    if not available_roles:
        return True  # 이미 진행 중 → 진전 있음으로 간주

    try:
        mr = ModelRouter()
        from core.dynamic_orchestrator import DynamicOrchestrator
        orch = DynamicOrchestrator.restore_from(state.to_dict(), mr=mr)
    except Exception as exc:
        print(f"[nightly_tick] orchestrator 복원 실패: {exc}", file=sys.stderr)
        return False

    tasks = orch._dispatch_from_board(available_roles, workspace)
    if not tasks:
        return False

    made_progress = False
    for task_info in tasks:
        if deadline_exceeded():
            break
        # next_board_tasks() 반환 dict: `assigned_role`, `subtask_instruction`, `task_id`.
        # 기존 `role`/`subtask_id`/`subtask` 접근은 전부 KeyError/빈값이었음 (B2-1).
        role = task_info.get("assigned_role", "")
        task_id = task_info.get("task_id", "")
        if not role:
            continue

        state.active_assignments[role] = {
            # `subtask_id` 키는 nightly_summary.py:41이 읽으므로 보존. 내부적으로는 board task_id.
            "subtask_id": task_id,
            "task_id": task_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "tick_id": tick_id,
            "result_path": None,
        }

        try:
            _run_task(orch, task_info, workspace, state, tick_id)
            made_progress = True
        except Exception as exc:
            retry_key = f"{role}:{task_id}"
            state.task_retry_count[retry_key] = state.task_retry_count.get(retry_key, 0) + 1
            print(f"[nightly_tick] 태스크 실행 실패 ({retry_key}): {exc}", file=sys.stderr)
        finally:
            state.active_assignments.pop(role, None)

    return made_progress


def _run_task(orch, task_info: dict, workspace: str, state: NightlyState, tick_id: str) -> None:
    """단일 태스크를 실행한다. 동기 래퍼."""
    import asyncio

    # run_id를 `tick_id:role` 복합 키로 구성 — orchestrator의 active_assignments가
    # run_id를 키로 사용하므로 (core/dynamic_orchestrator.py:682/867) 한 tick에서
    # 여러 롤을 실행하는 경우 키 충돌로 assignment가 무음 유실되는 것을 방지.
    role = task_info["assigned_role"]
    run_id = f"{tick_id}:{role}"

    async def _run():
        await orch._execute_agent_task(
            role=role,
            subtask=task_info["subtask_instruction"],
            run_id=run_id,
            workspace=workspace,
            task_id=task_info.get("task_id", ""),
        )

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(asyncio.wait_for(_run(), timeout=SOFT_DEADLINE_SEC))
    finally:
        loop.close()


# ── 메인 tick 루틴 ────────────────────────────────────────
def tick_once(workspace: str | Path | None = None) -> int:
    """단일 tick 실행. 0=정상, 1=skip(이미 실행 중), 2=오류."""
    global _tick_start, _deadline_exceeded
    _tick_start = time.monotonic()
    _deadline_exceeded = False
    signal.signal(signal.SIGTERM, _sigterm_handler)

    ws = str(workspace) if workspace else str(_REPO_ROOT)
    lock_fp = lock_path(ws)
    got, fd = _acquire_flock(lock_fp)
    if not got:
        print(f"[nightly_tick] 이전 tick 진행 중 — skip", file=sys.stderr)
        return 1

    try:
        tick_id = make_tick_id()
        state = load_state(ws)

        if not state.nightly_autonomy_enabled:
            print(f"[nightly_tick] 자율 모드 비활성 — skip", file=sys.stderr)
            return 0

        if state.budget.is_exhausted():
            state.watchdog.watchdog_level = "CHECKPOINT_ONLY"
            print(f"[nightly_tick] 예산 소진 — CHECKPOINT_ONLY", file=sys.stderr)
            save_state(state, ws)
            write_summary(state, ws)
            return 0

        state.last_tick_id = tick_id
        state.last_tick_at = datetime.now(timezone.utc).isoformat()
        state.budget.tick_count += 1

        active_workspace = state.active_workspace or ws
        made_progress = _dispatch_actions(state, active_workspace, tick_id)

        if made_progress:
            state.watchdog.tick_progress(tick_id)
            state.consecutive_tick_failures = 0
            clear_alert(ws)
        else:
            state.watchdog.tick_no_progress()

        save_state(state, ws)
        write_summary(state, ws)

        print(
            f"[nightly_tick] tick={tick_id} level={state.watchdog.watchdog_level} "
            f"progress={made_progress} budget={state.budget.consumed_tokens}/"
            f"{state.budget.max_tokens or 'unlimited'}",
            file=sys.stderr,
        )
        return 0

    except Exception as exc:
        import traceback
        print(f"[nightly_tick] tick 실패: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        try:
            state = load_state(ws)
            state.consecutive_tick_failures += 1
            if state.consecutive_tick_failures >= ALERT_AFTER_CONSEC_FAIL:
                mark_alert(ws, f"연속 {state.consecutive_tick_failures}회 tick 실패. 마지막 오류: {exc}")
            save_state(state, ws)
        except Exception:
            pass
        return 2

    finally:
        _release_flock(fd)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="야간 자율 파이프라인 1회 tick")
    parser.add_argument("--workspace", "-w", type=str, default=None, help="워크스페이스 루트")
    args = parser.parse_args(argv)
    return tick_once(args.workspace)


if __name__ == "__main__":
    sys.exit(main())
