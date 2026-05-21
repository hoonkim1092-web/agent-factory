#!/usr/bin/env python3
"""
scripts/check_design_pending.py
================================
UserPromptSubmit hook에서 호출.
설계 문서 교차검증 큐(.af_review_queue/pending/design/)를 확인하고,
새 항목이 있으면 [af-design-review-pending] 메시지를 출력한다.

Claude Code는 이 출력을 보고 af-cross-review를 실행한다.

debounce 메커니즘:
  - 큐 파일은 enqueue() 호출마다 덮어써져 mtime이 갱신되므로 mtime 사용 금지.
  - JSON 내부의 `timestamp` 필드(마지막 enqueue 시각)를 last-edit 신호로 사용.
  - 마지막 발화 시각(fired_at)을 별도 marker 파일에 기록 → 같은 timestamp에 대해 재발화 안 함.

항상 exit 0 — hook 차단 방지.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

DESIGN_QUEUE_DIR = os.path.join(".af_review_queue", "pending", "design")
# 마지막 enqueue 이후 이 시간이 지나야 발화 (연속 편집 중 조기 발화 방지)
MIN_BATCH_INTERVAL_SEC = 90
FIRED_MARKER = os.path.join(".af_review_queue", ".design_review_fired.json")


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


def _load_fired(ws: str) -> dict:
    path = os.path.join(ws, FIRED_MARKER)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _coerce_float(value) -> float:
    """방어적 float 변환. 실패/비유한값(nan, inf) → 0.0."""
    import math
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(result):
        return 0.0
    return result


def _save_fired(ws: str, data: dict) -> None:
    path = os.path.join(ws, FIRED_MARKER)
    parent = os.path.dirname(path)
    try:
        os.makedirs(parent, exist_ok=True)
        import tempfile
        fd, tmp = tempfile.mkstemp(prefix=".fired_", dir=parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except Exception:
                pass
    except Exception:
        pass


def main() -> None:
    ws = _detect_workspace()
    queue_dir = os.path.join(ws, DESIGN_QUEUE_DIR)

    if not os.path.isdir(queue_dir):
        return

    # 큐 파일 수집 + JSON 본문 로드 (mtime 사용 금지 — enqueue가 매번 갱신함)
    entries: list[tuple[float, str, str, str]] = []  # (timestamp, fname, file_path, full_path)
    try:
        existing_fnames: set[str] = set()
        for fname in os.listdir(queue_dir):
            if not fname.endswith(".json"):
                continue
            existing_fnames.add(fname)
            fpath = os.path.join(queue_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                ts = _coerce_float(data.get("timestamp", 0))
                file_path = str(data.get("file_path", "") or fname)
            except Exception:
                continue
            entries.append((ts, fname, file_path, fpath))
    except OSError:
        return

    # 발화 이력 로드 + 큐에서 사라진 항목 pruning
    fired = _load_fired(ws)
    pruned = {k: v for k, v in fired.items() if k in existing_fnames}
    if len(pruned) != len(fired):
        _save_fired(ws, pruned)
        fired = pruned

    if not entries:
        return

    # 발화 가능한 항목 필터: timestamp가 fired_at보다 크고 quiet period 경과
    now = time.time()
    candidates: list[tuple[float, str, str]] = []  # (timestamp, fname, file_path)
    for ts, fname, file_path, _ in entries:
        if ts <= 0:
            continue  # timestamp 누락/손상 — 안전을 위해 발화 안 함
        last_fired_at = _coerce_float(fired.get(fname, 0))
        if last_fired_at and ts <= last_fired_at:
            continue  # 마지막 발화 이후 새 편집 없음
        elapsed = now - ts
        if elapsed < MIN_BATCH_INTERVAL_SEC:
            continue  # quiet period 미경과
        candidates.append((ts, fname, file_path))

    if not candidates:
        return

    # 최근 enqueue 우선, 동률은 file_path로 결정론적 정렬
    candidates.sort(key=lambda c: (-c[0], c[2]))
    n = len(candidates)
    file_list = ", ".join(c[2] for c in candidates[:10])
    if n > 10:
        file_list += f" ... (+{n - 10})"

    print(f"[af-design-review-pending] {n}개 설계문서가 교차검증 대기 중입니다: {file_list}")
    print(f"[af-design-review-pending] af-cross-review 에이전트를 실행해주세요. (af-critic은 설계문서에 효과 없음 — 2026-05-01 정책)")

    # 발화 기록 (모든 candidate에 대해 — 같은 턴에 한 번에 다 처리됨)
    for _, fname, _ in candidates:
        fired[fname] = now
    _save_fired(ws, fired)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # exit 0 contract — hook 차단 방지. 디버깅용 로그만 stderr로
        import traceback
        traceback.print_exc(file=sys.stderr)
    sys.exit(0)
