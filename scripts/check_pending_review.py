#!/usr/bin/env python3
"""
scripts/check_pending_review.py
=================================
UserPromptSubmit hook에서 호출.
편집된 .py 파일이 교차검증 대기 중인지 확인하고,
대기 중이면 Claude Code에 에이전트 실행을 지시하는 메시지를 출력한다.

Claude Code는 이 출력을 보고 af-critic + af-cross-review를 자동 실행한다.

항상 exit 0 — hook 차단 방지.
"""
from __future__ import annotations

import json
import os
import sys
import time

MARKER_PATH = os.path.join(".af_review_queue", "pending_agent_review.json")
# 첫 발화 전 최소 대기 시간 (초) — 편집이 계속 누적되는 동안 트리거 방지
MIN_BATCH_INTERVAL_SEC = 300


def _detect_workspace() -> str:
    import subprocess
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
    workspace = _detect_workspace()
    marker = os.path.join(workspace, MARKER_PATH)

    if not os.path.exists(marker):
        return

    try:
        with open(marker, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    files = data.get("files", [])
    if not files:
        return

    updated_at = data.get("updated_at", data.get("created_at", 0))
    fired_at = data.get("fired_at", 0)

    if fired_at:
        # 이미 발화됨 — 마지막 발화 이후 새 편집이 있을 때만 재발화
        if updated_at <= fired_at:
            return
    else:
        # 첫 발화 — 편집이 누적될 시간을 줌
        elapsed = time.time() - data.get("created_at", 0)
        if elapsed < MIN_BATCH_INTERVAL_SEC:
            return

    # 파일 목록 출력 — Claude Code가 이 메시지를 보고 에이전트를 실행한다
    file_list = ", ".join(files[:10])
    if len(files) > 10:
        file_list += f" ... (+{len(files) - 10})"

    print(f"[af-review-pending] {len(files)}개 .py 파일이 교차검증 대기 중입니다: {file_list}")
    print(f"[af-review-pending] af-critic + af-cross-review + af-test-runner 에이전트를 백그라운드로 실행해주세요.")

    # consumed 표시 — fired_at 기록 후 atomic 덮어쓰기 (삭제 대신)
    data["fired_at"] = time.time()
    try:
        import tempfile
        marker_dir = os.path.dirname(marker)
        fd, tmp_path = tempfile.mkstemp(prefix=".fired_", dir=marker_dir, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, marker)
        except Exception:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
