"""합성 tick 시뮬레이션 — §6.1 설계 기반.

판정 기준:
  GE-1: 48회 tick 완주 (budget.tick_count == 48)
  GE-2: 어느 tick도 예외를 상위로 전파하지 않음 (exit_code ∈ {0, 1, 2})
  GE-3: 각 tick 후 nightly_summary.md mtime 단조증가
  GE-4: 48회 no-progress → watchdog가 CHECKPOINT_ONLY 레벨로 정상 에스컬레이션
  GE-5: 연속 5회 이상 tick 예외 → alert.flag 생성

실행:
  pytest tests/e2e/tick_simulator.py -m e2e -v
"""
from __future__ import annotations

import pytest
from pathlib import Path

from scripts.nightly_tick import tick_once, ALERT_AFTER_CONSEC_FAIL
from core.nightly_state import load_state, summary_path, alert_flag_path

TICK_COUNT = 48
_SHORT_DEADLINE = 2  # 테스트 가속: SOFT/HARD deadline을 2초로 단축


@pytest.mark.e2e
def test_48_ticks_no_crash(
    sim_workspace: Path,
    no_dispatch,
) -> None:
    """GE-1 ~ GE-3: 48 tick 동안 크래시 없이 summary mtime이 단조증가한다.

    의존성:
      - sim_workspace가 nightly_autonomy_enabled=True, max_tokens=0(unlimited)로 초기화되어야
        tick_once()가 조기 return하지 않는다.
      - scripts.nightly_summary.write_summary()가 매 tick마다 summary 파일을 쓰는 것을 전제.
        이 전제가 깨지면 GE-3 assert가 i>=1에서 실패한다(의도된 통합 검증).
    """

    prev_mtime: float = 0.0

    for i in range(TICK_COUNT):
        exit_code = tick_once(workspace=sim_workspace)
        # GE-2: tick_once()는 내부에서 예외를 catch하고 0/1/2만 반환한다
        assert exit_code in (0, 1, 2), f"tick {i}: 예상 외 exit_code={exit_code}"

        # GE-3: 첫 tick 이후 summary 파일 반드시 존재 + mtime 단조증가
        s = summary_path(sim_workspace)
        if i >= 1:
            assert s.exists(), f"tick {i}: nightly_summary.md 파일이 없다"
        if s.exists():
            mtime = s.stat().st_mtime
            assert mtime >= prev_mtime, (
                f"tick {i}: summary mtime이 역행했다 (prev={prev_mtime}, cur={mtime})"
            )
            prev_mtime = mtime

    # GE-1: 48회 tick 완주
    state = load_state(sim_workspace)
    assert state.budget.tick_count == TICK_COUNT, (
        f"예상 tick_count={TICK_COUNT}, 실제={state.budget.tick_count}"
    )


@pytest.mark.e2e
def test_watchdog_escalation_after_no_progress(
    sim_workspace: Path,
    no_dispatch,
) -> None:
    """GE-4: no-progress 에스컬레이션 경계 조건.

    n=CHECKPOINT_ONLY_THRESHOLD-1 → STALL_3 유지,
    n=CHECKPOINT_ONLY_THRESHOLD → CHECKPOINT_ONLY 전환을 모두 검증한다.
    """
    from core.watchdog import WatchdogState

    threshold = WatchdogState.CHECKPOINT_ONLY_THRESHOLD  # 16

    # threshold-1회 → STALL_3 단계 유지 (n in [8, 15])
    for _ in range(threshold - 1):
        tick_once(workspace=sim_workspace)
    state = load_state(sim_workspace)
    assert state.watchdog.watchdog_level == "STALL_3", (
        f"{threshold - 1}회 no-progress 후 STALL_3 기대, "
        f"실제={state.watchdog.watchdog_level}"
    )

    # 1회 더 → CHECKPOINT_ONLY 전환 (n == threshold)
    tick_once(workspace=sim_workspace)
    state = load_state(sim_workspace)
    assert state.watchdog.watchdog_level == "CHECKPOINT_ONLY", (
        f"{threshold}회 no-progress 후 CHECKPOINT_ONLY 기대, "
        f"실제={state.watchdog.watchdog_level}"
    )


@pytest.mark.e2e
def test_alert_flag_after_consecutive_failures(
    sim_workspace: Path,
    fail_dispatch,
) -> None:
    """GE-5: 연속 tick 예외 발생 시 alert.flag 생성."""
    # ALERT_AFTER_CONSEC_FAIL(=5)회 초과 실패를 유발
    for _ in range(ALERT_AFTER_CONSEC_FAIL + 1):
        tick_once(workspace=sim_workspace)  # exit_code=2 허용

    assert alert_flag_path(sim_workspace).exists(), (
        f"연속 {ALERT_AFTER_CONSEC_FAIL + 1}회 tick 실패 후 alert.flag가 생성돼야 한다"
    )

    state = load_state(sim_workspace)
    assert state.consecutive_tick_failures >= ALERT_AFTER_CONSEC_FAIL
