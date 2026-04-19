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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GE-1 ~ GE-4: 48 tick 동안 크래시 없이 상태가 올바르게 전이된다."""
    import scripts.nightly_tick as _tick_mod

    monkeypatch.setattr(_tick_mod, "SOFT_DEADLINE_SEC", _SHORT_DEADLINE)
    monkeypatch.setattr(_tick_mod, "HARD_DEADLINE_SEC", _SHORT_DEADLINE)

    prev_mtime: float = 0.0

    for i in range(TICK_COUNT):
        exit_code = tick_once(workspace=sim_workspace)
        # GE-2: tick_once()는 내부에서 예외를 catch하고 0/1/2만 반환한다
        assert exit_code in (0, 1, 2), f"tick {i}: 예상 외 exit_code={exit_code}"

        # GE-3: summary mtime 단조증가 (summary가 생성된 이후부터 확인)
        s = summary_path(sim_workspace)
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

    # GE-4: no-progress 48회 → CHECKPOINT_ONLY 레벨로 정상 에스컬레이션
    # (CHECKPOINT_ONLY_THRESHOLD=16, 48회 > 16 → 정상 동작)
    assert state.watchdog.watchdog_level == "CHECKPOINT_ONLY", (
        f"예상 watchdog_level=CHECKPOINT_ONLY, 실제={state.watchdog.watchdog_level}"
    )
    assert state.watchdog.consecutive_no_progress_ticks == TICK_COUNT


@pytest.mark.e2e
def test_alert_flag_after_consecutive_failures(
    sim_workspace: Path,
    fail_dispatch,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GE-5: 연속 tick 예외 발생 시 alert.flag 생성."""
    import scripts.nightly_tick as _tick_mod

    monkeypatch.setattr(_tick_mod, "SOFT_DEADLINE_SEC", _SHORT_DEADLINE)
    monkeypatch.setattr(_tick_mod, "HARD_DEADLINE_SEC", _SHORT_DEADLINE)

    # ALERT_AFTER_CONSEC_FAIL(=5)회 초과 실패를 유발
    for _ in range(ALERT_AFTER_CONSEC_FAIL + 1):
        tick_once(workspace=sim_workspace)  # exit_code=2 허용

    assert alert_flag_path(sim_workspace).exists(), (
        f"연속 {ALERT_AFTER_CONSEC_FAIL + 1}회 tick 실패 후 alert.flag가 생성돼야 한다"
    )

    state = load_state(sim_workspace)
    assert state.consecutive_tick_failures >= ALERT_AFTER_CONSEC_FAIL
