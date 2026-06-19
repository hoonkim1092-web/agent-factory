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

# 설계문서 라운드 캡 — 코드(5)보다 낮게, HOW 진동 조기 차단 (§4.1)
MAX_DESIGN_ROUNDS = 3


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


def _normalize_entry(v) -> dict:
    """기존 float 포맷(fired_at만) 또는 신규 dict 포맷을 정규화한다."""
    if isinstance(v, dict):
        raw_sections = v.get("last_block_sections")
        sections = list(raw_sections) if isinstance(raw_sections, (list, tuple)) else []
        return {
            "fired_at": _coerce_float(v.get("fired_at", 0)),
            "round_count": max(0, int(_coerce_float(v.get("round_count", 0)))),
            "last_verdict": str(v.get("last_verdict") or ""),
            "last_block_sections": sections,           # S2: 직전 BLOCK 섹션 목록
            "oscillation_detected": bool(v.get("oscillation_detected", False)),  # S2: 진동 신호
            "capped_notified_at": _coerce_float(v.get("capped_notified_at", 0)),
        }
    # 기존 포맷: fired_at float만 저장됐던 구버전
    return {
        "fired_at": _coerce_float(v),
        "round_count": 0,
        "last_verdict": "",
        "last_block_sections": [],
        "oscillation_detected": False,
        "capped_notified_at": 0.0,
    }


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

    # 발화 가능한 항목 필터: 라운드 캡 체크 + timestamp + quiet period
    now = time.time()
    candidates: list[tuple[float, str, str, dict]] = []  # (timestamp, fname, file_path, entry)
    dirty = False  # 캡 알림 기록용 — 후보 없어도 저장 필요할 수 있음
    for ts, fname, file_path, _ in entries:
        if ts <= 0:
            continue  # timestamp 누락/손상 — 안전을 위해 발화 안 함
        entry = _normalize_entry(fired.get(fname, 0))

        # 라운드 캡 체크 (INV-3): 캡 도달 시 자동 발화 중단
        if entry["round_count"] >= MAX_DESIGN_ROUNDS:
            if not entry["capped_notified_at"]:
                print(
                    f"[af-design-review-capped] {file_path}: "
                    f"round_count={entry['round_count']} >= MAX_DESIGN_ROUNDS={MAX_DESIGN_ROUNDS}."
                    f" {MAX_DESIGN_ROUNDS}라운드 검증 완료 — 추가 자동 발화 없음."
                )
                print(
                    "[af-design-review-capped] BLOCK verdict가 남아 있으면 commit은 계속 차단됩니다."
                    " 우회: AF_SKIP_REVIEW_GATE=1 git commit ..."
                )
                entry["capped_notified_at"] = now
                fired[fname] = entry
                dirty = True
            continue

        # oscillation 감지 (INV-3 §4.2): 직전 BLOCK + 같은 섹션 재발 → 즉시 중단
        if entry["oscillation_detected"]:
            print(
                f"[af-design-review-oscillation] {file_path}: "
                "직전 라운드 수정이 같은 섹션에 새 BLOCK을 유발했습니다(진동 의심)."
            )
            print("[af-design-review-oscillation] 자동 재수정을 중단합니다. 다음 중 택일:")
            print("  - HOW 디테일이면: 해당 항목을 '구현 시 결정'으로 강등하세요")
            print("  - 진짜 논리결함이면: 사용자가 직접 결정하세요")
            # 플래그 리셋 — 사용자가 내용을 바꾸면 다음 라운드 다시 시작
            entry["oscillation_detected"] = False
            fired[fname] = entry
            dirty = True
            continue

        last_fired_at = entry["fired_at"]
        if last_fired_at and ts <= last_fired_at:
            continue  # 마지막 발화 이후 새 편집 없음
        elapsed = now - ts
        if elapsed < MIN_BATCH_INTERVAL_SEC:
            continue  # quiet period 미경과
        candidates.append((ts, fname, file_path, entry))

    if dirty:
        _save_fired(ws, fired)

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

    # 발화 기록: round_count 증가 + dict 포맷으로 저장
    for _, fname, _, entry in candidates:
        fired[fname] = {
            "fired_at": now,
            "round_count": entry["round_count"] + 1,
            "last_verdict": entry["last_verdict"],
            "last_block_sections": entry["last_block_sections"],
            "oscillation_detected": False,
            "capped_notified_at": entry["capped_notified_at"],
        }
    _save_fired(ws, fired)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # exit 0 contract — hook 차단 방지. 디버깅용 로그만 stderr로
        import traceback
        traceback.print_exc(file=sys.stderr)
    sys.exit(0)
