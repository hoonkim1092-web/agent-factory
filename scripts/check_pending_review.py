#!/usr/bin/env python3
"""
scripts/check_pending_review.py
=================================
UserPromptSubmit hook에서 호출.
편집된 .py 파일이 교차검증 대기 중인지 확인하고,
대기 중이면 Claude Code에 에이전트 실행을 지시하는 메시지를 출력한다.

Phase 0 정책 (2026-04-30 — Proof-Carrying Review 도입 전 단계):
- max_rounds=2 캡: round_count >= 2면 더 이상 발화 안 함
- WARN-only no-fire: 직전 라운드에 BLOCK이 없었으면 (전부 WARN/PASS) 재발화 안 함
- Tier 1 경량화: blast_tier == 1 이면 af-test-runner만 실행 권고

항상 exit 0 — hook 차단 방지.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

MARKER_PATH = os.path.join(".af_review_queue", "pending_agent_review.json")
# 마지막 편집 이후 조용해야 하는 시간 (초) — 연속 편집 중 조기 발화 방지
# updated_at 기준으로 계산 → 재편집 시 타이머 리셋
MIN_BATCH_INTERVAL_SEC = 90

# Phase 0: 한 큐가 발화될 수 있는 최대 라운드 수 — 무한루프 차단
MAX_ROUNDS = 2


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


def _agents_for_tier(tier: int, t3_skip_allowed: bool = False) -> tuple[str, str]:
    """(agent_list_str, instruction) 반환."""
    if tier == 1:
        return (
            "af-test-runner",
            "Tier 1 (저영향) — af-test-runner 1개만 실행하면 충분합니다.",
        )
    if t3_skip_allowed:
        return (
            "af-test-runner → af-critic",
            "Tier 2 cosmetic-only — deterministic classifier가 Tier 3를 생략했습니다.",
        )
    return (
        "af-test-runner → af-critic → af-cross-review",
        "Tier 2~3 — 위 3개 에이전트를 순서대로 실행하세요.",
    )


def _atomic_write(marker: str, data: dict) -> None:
    marker_dir = os.path.dirname(marker)
    fd, tmp_path = tempfile.mkstemp(prefix=".pending_", dir=marker_dir, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, marker)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


def main() -> None:
    workspace = _detect_workspace()
    marker = os.path.join(workspace, MARKER_PATH)

    if not os.path.exists(marker):
        return

    # Import lock from review_gate for consistent RMW protection
    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _scripts_dir)
    # Phase 2 v7 §5.4: project root도 sys.path에 추가 — `from scripts.hook_runner import`
    # 가 hook subprocess 환경(run.py 호출)에서 resolve되도록 보장.
    sys.path.insert(0, os.path.dirname(_scripts_dir))
    try:
        from review_gate import _state_lock  # type: ignore
    except Exception:
        _state_lock = None  # type: ignore

    def _do_check() -> None:
        try:
            with open(marker, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        files = data.get("files", [])
        if not files:
            return

        try:
            updated_at = float(data.get("updated_at") or data.get("created_at") or 0)
            fired_at = float(data.get("fired_at") or 0)
            round_count = int(data.get("round_count") or 0)
            blast_tier = int(data.get("blast_tier") or 2)
        except (TypeError, ValueError):
            updated_at, fired_at, round_count, blast_tier = 0.0, 0.0, 0, 2
        last_summary = data.get("last_round_summary") or {}

        # Phase 0: max_rounds 캡 — 무한루프 방지
        if round_count >= MAX_ROUNDS:
            # 1회 알림: 사용자가 commit 막힘 + 안내 없음 dead-end 방지
            if not data.get("capped_notified_at"):
                print(
                    f"[af-review-capped] round_count={round_count} >= MAX_ROUNDS={MAX_ROUNDS}."
                    f" {MAX_ROUNDS}라운드 검증 완료 — 추가 자동 발화 없음."
                )
                print(
                    "[af-review-capped] BLOCK verdict가 남아 있으면 commit은 계속 차단됩니다."
                    " 우회: AF_SKIP_REVIEW_GATE=1 git commit ..."
                )
                data["capped_notified_at"] = time.time()
                _atomic_write(marker, data)
            return

        # Phase 0: WARN-only no-fire — 이전 라운드가 BLOCK 없이 완료됐다면 재발화 안 함
        if round_count >= 1 and last_summary and not last_summary.get("has_block", True):
            # 1회 알림: WARN-only suppression이 왜 commit을 막을 수 있는지 설명
            if not data.get("warn_only_notified_at"):
                # Phase 2 v7 §5.4: WARN 라운드당 정확히 1건 — 1회-알림과 동일 분기에서
                # 시계열 sink 기록 (§9.2 트리거 #1 falsifiable 재정의 G11 해소).
                try:
                    from scripts.hook_runner import _log_hook_event  # type: ignore
                    _log_hook_event(
                        "warn_only_suppressed",
                        str(round_count),
                        0,
                        error=json.dumps({
                            "agents_present": list(
                                (last_summary.get("verdicts") or {}).keys()
                            ),
                        }),
                    )
                except Exception:
                    pass  # sink 결손은 Phase 2 비목표 (detection-only)
                print(
                    "[af-review-suppressed] 직전 라운드가 WARN/PASS만 포함 — 재발화 보류."
                )
                print(
                    "[af-review-suppressed] commit이 막힌다면:"
                    " AF_SKIP_REVIEW_GATE=1 git commit ... 또는 에이전트 수동 실행."
                )
                data["warn_only_notified_at"] = time.time()
                _atomic_write(marker, data)
            return

        if fired_at:
            # 이미 발화됨 — 마지막 발화 이후 새 편집이 있을 때만 재발화
            if updated_at <= fired_at:
                return
        else:
            # 첫 발화 — 마지막 편집 이후 조용해야 발화 (연속 편집 중 발화 억제)
            elapsed = time.time() - updated_at
            if elapsed < MIN_BATCH_INTERVAL_SEC:
                return

        # 파일 목록 출력 — Claude Code가 이 메시지를 보고 에이전트를 실행한다
        file_list = ", ".join(files[:10])
        if len(files) > 10:
            file_list += f" ... (+{len(files) - 10})"

        try:
            from review_gate import _required_tiers_for  # type: ignore
            t3_skip_allowed = blast_tier != 1 and 3 not in _required_tiers_for(data)
        except Exception:
            t3_skip_allowed = False
        agent_list, instruction = _agents_for_tier(blast_tier, t3_skip_allowed)
        round_info = f" (round {round_count + 1}/{MAX_ROUNDS})"

        print(f"[af-review-pending] {len(files)}개 .py 파일이 교차검증 대기 중입니다{round_info}: {file_list}")
        print(f"[af-review-pending] blast_tier={blast_tier} — {instruction}")
        print(f"[af-review-pending] 실행 에이전트: {agent_list}")

        # fired_at 기록 — 재발화 방지
        data["fired_at"] = time.time()
        _atomic_write(marker, data)

    try:
        if _state_lock is not None:
            with _state_lock(workspace):
                _do_check()
        else:
            _do_check()
    except Exception:
        pass


if __name__ == "__main__":
    main()
