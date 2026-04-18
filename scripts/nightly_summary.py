"""야간 자율 파이프라인 요약 렌더러.

`.af/nightly_summary.md` 를 state_snapshot에서 매 tick 갱신한다.
사람이 읽을 수 있는 형식으로 현재 상태, 예산, watchdog 레벨을 기술한다.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.nightly_state import NightlyState, save_state, summary_path


_LEVEL_EMOJI = {
    "OK": "✅",
    "STALL_1": "⚠️",
    "STALL_2": "🔶",
    "STALL_3": "🚨",
    "CHECKPOINT_ONLY": "⛔",
}


def render_summary(state: NightlyState, workspace: str | Path | None = None) -> str:
    """state에서 마크다운 요약 문자열을 생성한다."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    level = state.watchdog.watchdog_level
    emoji = _LEVEL_EMOJI.get(level, "❓")

    budget = state.budget
    if budget.max_tokens > 0:
        pct = min(100, int(budget.consumed_tokens * 100 / budget.max_tokens))
        budget_str = f"{budget.consumed_tokens:,} / {budget.max_tokens:,} tokens ({pct}%)"
    else:
        budget_str = f"{budget.consumed_tokens:,} tokens (unlimited)"

    assignments_lines = []
    for role, info in (state.active_assignments or {}).items():
        subtask = info.get("subtask_id", "?")
        since = info.get("started_at", "?")
        assignments_lines.append(f"  - {role}: `{subtask}` (since {since})")

    assignments_section = "\n".join(assignments_lines) if assignments_lines else "  (없음)"

    consecutive_fail = state.consecutive_tick_failures
    fail_note = f" ⚠️ 연속 tick 실패 {consecutive_fail}회" if consecutive_fail > 0 else ""

    lines = [
        "# 야간 자율 파이프라인 상태",
        "",
        f"- **갱신**: {now}{fail_note}",
        f"- **활성 프로젝트**: {state.active_project or '(없음)'}",
        f"- **Watchdog**: {emoji} `{level}` (연속 무진전 tick: {state.watchdog.consecutive_no_progress_ticks})",
        f"- **예산**: {budget_str}",
        f"- **마지막 tick**: {state.last_tick_id or '(없음)'}",
        f"- **자율 모드**: {'활성' if state.nightly_autonomy_enabled else '비활성'}",
        "",
        "## 진행 중 태스크",
        "",
        assignments_section,
    ]

    if state.watchdog.lineage_counters:
        lines += ["", "## Lineage 재시도 현황", ""]
        for lid, info in state.watchdog.lineage_counters.items():
            lines.append(f"  - `{lid}`: level={info.get('level', 0)}, attempts={info.get('attempts', 0)}")

    return "\n".join(lines) + "\n"


def write_summary(state: NightlyState, workspace: str | Path | None = None) -> None:
    """요약 파일을 갱신한다."""
    path = summary_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = render_summary(state, workspace)
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    import json
    from core.nightly_state import load_state
    ws = sys.argv[1] if len(sys.argv) > 1 else None
    st = load_state(ws)
    write_summary(st, ws)
    print(f"Summary written to {summary_path(ws)}")
