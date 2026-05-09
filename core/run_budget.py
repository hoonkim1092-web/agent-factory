"""
core/run_budget.py
==================
글로벌 토큰 예산 추적 모듈.

4-char ≈ 1-token 휴리스틱으로 소비량을 추정하며,
80% 경고 + 100% 자동 중단을 제공한다.

사용:
    set_run_budget(50000, run_id=run_id)  # CLI에서 --budget 50000
    get_run_budget().record(text)         # agent_runner 결과마다
    get_run_budget().is_exhausted()       # orchestrator 매 사이클 체크

T3-7: run_id 설정 시 80%/100% 마일스톤에 COST_INCURRED RunEvent를 방출한다.
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class RunBudget:
    max_tokens: int = 0       # 0 = unlimited
    consumed: int = 0
    warned_80: bool = False
    stopped: bool = False
    run_id: str = ""
    project_id: str = ""

    def record(self, text: str) -> None:
        """4-char ≈ 1-token 휴리스틱으로 소비량을 갱신한다."""
        self.consumed += max(1, len(text) // 4)
        if self.max_tokens <= 0:
            return
        if not self.warned_80 and self.consumed >= self.max_tokens * 0.8:
            self.warned_80 = True
            print(f"[RunBudget] WARNING: 80% budget consumed ({self.consumed}/{self.max_tokens})")
            self._emit_cost_event("80_pct")
        if not self.stopped and self.consumed >= self.max_tokens:
            self.stopped = True
            print(f"[RunBudget] STOP: budget exhausted ({self.consumed}/{self.max_tokens})")
            self._emit_cost_event("exhausted")

    def _emit_cost_event(self, milestone: str) -> None:
        """COST_INCURRED RunEvent 방출 — run_id 없으면 no-op."""
        if not self.run_id:
            return
        try:
            from core.events.run_event import RunEvent, RunEventType, get_default_store
            get_default_store().append(RunEvent(
                run_id=self.run_id,
                event_type=RunEventType.COST_INCURRED,
                project_id=self.project_id,
                payload={
                    "consumed": self.consumed,
                    "max_tokens": self.max_tokens,
                    "milestone": milestone,
                },
            ))
        except Exception:
            pass  # fire-and-forget — budget logging must not crash the caller

    def is_exhausted(self) -> bool:
        return self.stopped

    def remaining(self) -> int:
        if self.max_tokens <= 0:
            return 999_999_999
        return max(0, self.max_tokens - self.consumed)


# ── 모듈 싱글턴 ──────────────────────────────────────────────
_budget: RunBudget = RunBudget()


def set_run_budget(
    max_tokens: int,
    *,
    run_id: str = "",
    project_id: str = "",
) -> RunBudget:
    global _budget
    _budget = RunBudget(max_tokens=max_tokens, run_id=run_id, project_id=project_id)
    return _budget


def get_run_budget() -> RunBudget:
    return _budget
