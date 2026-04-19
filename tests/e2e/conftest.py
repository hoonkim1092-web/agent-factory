"""e2e 테스트 공통 픽스처."""
from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def sim_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """격리된 임시 workspace + nightly 자율 모드 활성화."""
    ws = tmp_path / "af_sim"
    (ws / ".af").mkdir(parents=True)
    (ws / ".system_generated" / "logs").mkdir(parents=True)

    # 실제 LLM 호출 원천 차단
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    # 자율 모드 활성화 상태로 초기 snapshot 생성
    from core.nightly_state import NightlyState, save_state
    state = NightlyState(nightly_autonomy_enabled=True)
    save_state(state, ws)

    return ws


@pytest.fixture
def no_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """_dispatch_actions → 항상 False (태스크 진전 없음, 예외 없음)."""
    import scripts.nightly_tick as _tick_mod
    monkeypatch.setattr(_tick_mod, "_dispatch_actions", lambda *a, **kw: False)


@pytest.fixture
def fail_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """_dispatch_actions → 항상 RuntimeError (연속 실패 시나리오)."""
    import scripts.nightly_tick as _tick_mod

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated agent failure")

    monkeypatch.setattr(_tick_mod, "_dispatch_actions", _raise)
