#!/usr/bin/env python3
"""
scripts/check_model_escalation.py
===================================
UserPromptSubmit hook: P4.5b 모델 escalation 대기 상태를 오케스트레이터에게 알린다.

대기 중인 escalation 권장이 있으면 출력 후 상태를 지운다 (one-shot).
항상 exit 0 — hook 차단 방지.
"""
from __future__ import annotations

import os
import subprocess
import sys


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


def main() -> None:
    # Hook 스크립트는 시스템 Python으로 실행됨 (frozen 빌드에서 실행되지 않음).
    # frozen 환경이 감지되면 안전하게 종료한다.
    if getattr(sys, "frozen", False):
        return

    workspace = _detect_workspace()

    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(_scripts_dir))

    try:
        from scripts.agent_model_selector import (  # type: ignore[import]
            get_pending_escalation,
            clear_pending_escalation,
        )
        state = get_pending_escalation(workspace)
        if state:
            agent = state.get("agent", "?")
            model = state.get("model", "?")
            triggers = state.get("triggers", [])
            print(
                f"⚠️  [model-escalation] {agent}: model='{model}' 사용 권장"
                f"  (triggers: {', '.join(triggers)})"
            )
            print(
                f"   → Agent tool 호출 시 model='{model}' 파라미터를 명시하세요."
            )
            clear_pending_escalation(workspace)
    except Exception:
        pass


if __name__ == "__main__":
    main()
