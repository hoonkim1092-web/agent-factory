#!/usr/bin/env python3
"""
scripts/enqueue_agent_review.py
=================================
PostToolUse hook에서 호출.
.py 파일 편집 시 교차검증 대기 큐에 추가한다.

마커 파일: .af_review_queue/pending_agent_review.json
- 편집된 파일 목록을 누적
- check_pending_review.py가 일정 시간 후 확인

항상 exit 0 — hook 차단 방지.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

MARKER_DIR = ".af_review_queue"
MARKER_PATH = os.path.join(MARKER_DIR, "pending_agent_review.json")

# 교차검증 대상 파일 패턴
_REVIEW_PREFIXES = ("core/", "scripts/")  # Phase 0: scripts/ 추가, Tier로 강도 조절
_REVIEW_EXACT = ("model_utils.py", "run_factory_cli.py")
# skills/ 1-depth skill.py만 추가 — legacy(forge/, warehouse/, evaluator/) 폭발 회피
# (2026-04-23 graphify 통합 시 af-critic BLOCK#1 fix)
import re as _re
_SKILLS_TOPLEVEL_RE = _re.compile(r"^skills/[^/]+/skill\.py$")


def _is_review_target(filepath: str) -> bool:
    if not filepath.endswith(".py"):
        return False
    for prefix in _REVIEW_PREFIXES:
        if filepath.startswith(prefix):
            return True
    if _SKILLS_TOPLEVEL_RE.match(filepath):
        return True
    basename = os.path.basename(filepath)
    return basename in _REVIEW_EXACT


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


def main_for_path(filepath: str, workspace: str | None = None) -> None:
    if not filepath:
        return

    # 절대경로 → 상대경로 변환
    workspace = workspace or _detect_workspace()
    try:
        rel = os.path.relpath(os.path.abspath(filepath), workspace)
    except ValueError:
        rel = filepath
    rel = rel.replace("\\", "/")

    if not _is_review_target(rel):
        return

    marker = os.path.join(workspace, MARKER_PATH)
    marker_dir = os.path.join(workspace, MARKER_DIR)
    os.makedirs(marker_dir, exist_ok=True)

    # Phase 0: review_gate._state_lock과 동일 락으로 RMW 직렬화
    # → record_review_done이 추가한 round_count/last_round_summary/reviews 보존
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from review_gate import _state_lock  # type: ignore
    except Exception:
        _state_lock = None  # type: ignore

    def _do_update(
        new_file_tier: int,
        t3_decision: object | None,
        record_skip_telemetry_func: object | None,
        telemetry_decision: dict | None = None,
        telemetry_skip_enacted_func: object | None = None,
        append_skip_audit_func: object | None = None,
    ) -> None:
        now = time.time()

        # 기존 마커 읽기
        data: dict = {"files": [], "created_at": now}
        if os.path.exists(marker):
            try:
                with open(marker, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {"files": [], "created_at": now}

        # 파일 추가 + updated_at 갱신 (재편집 감지를 위해 기존 파일도 포함)
        if rel not in data.get("files", []):
            data.setdefault("files", []).append(rel)
        data["updated_at"] = now

        # Phase 0: blast_tier 산출 — 새 파일 tier와 기존 최댓값 중 최대
        # classify_with_content는 락 밖에서 미리 수행 (파일 I/O로 인한 3s 타임아웃 방지)
        existing_tier = int(data.get("blast_tier") or 2)
        data["blast_tier"] = max(existing_tier, new_file_tier)

        expected_files = sorted(data.get("files") or [])
        decision_files = sorted(getattr(t3_decision, "files", []) or [])
        if t3_decision is None:
            data["t3_required"] = True
            data["t3_decision"] = {
                "decision": "require_t3",
                "reason": "classifier-unavailable",
                "classifier_version": CLASSIFIER_VERSION,
                "files": expected_files,
                "diff_summary": {},
            }
        elif decision_files != expected_files:
            data["t3_required"] = True
            data["t3_decision"] = {
                "decision": "require_t3",
                "reason": "classifier-stale-file-set",
                "classifier_version": getattr(t3_decision, "classifier_version", CLASSIFIER_VERSION),
                "files": expected_files,
                "diff_summary": getattr(t3_decision, "diff_summary", {}),
            }
        else:
            data["t3_required"] = bool(getattr(t3_decision, "t3_required", True))
            data["t3_decision"] = t3_decision.to_state()
            if not data["t3_required"] and record_skip_telemetry_func is not None:
                try:
                    record_skip_telemetry_func(workspace, t3_decision)
                except Exception:
                    pass

        # Phase 0 라운드 토큰: 새 라운드 시작 시점에만 set
        # round_started_at가 None이면 이전 라운드가 종료됐다는 뜻 → 새 라운드 시작
        if not data.get("round_started_at"):
            data["round_started_at"] = now
            # Phase 4: 새 라운드 → skip-audit 1회 기록 허용 (라운드당 중복 방지)
            data.pop("t3_skip_audit_logged_at", None)
        # round_count는 review_gate가 라운드 종료 시 증가시킴 — enqueue는 보존만
        data.setdefault("round_count", 0)

        # Phase 4: telemetry 기반 Tier 3 skip 결정을 state에 동결 (락 밖 계산값).
        # _required_tiers_for가 이 flag만 읽으므로 순수성 유지. skip이 실제 발효되면
        # (위험군 외 + blast 2) 라운드당 1회 "왜 skip했는지" skip_audit.jsonl 기록.
        if telemetry_decision is not None:
            data["t3_telemetry_skip"] = telemetry_decision
            if (
                telemetry_skip_enacted_func is not None
                and append_skip_audit_func is not None
                and not data.get("t3_skip_audit_logged_at")
            ):
                try:
                    if telemetry_skip_enacted_func(data):
                        append_skip_audit_func(
                            workspace,
                            skipped_tier=3,
                            reason=telemetry_decision.get("reason", "t3-redundant"),
                        )
                        data["t3_skip_audit_logged_at"] = now
                except Exception:
                    pass

        # 저장 (atomic write)
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

    # Phase 0: blast_tier 선계산 — 락 밖에서 파일 I/O 수행 (3s hook 타임아웃 방지)
    try:
        from blast_radius import classify_with_content  # type: ignore
        new_file_tier = int(classify_with_content(rel, workspace))
    except Exception:
        new_file_tier = 2

    t3_decision = None
    record_skip_telemetry_func = None
    try:
        from t3_classifier import (  # type: ignore
            CLASSIFIER_VERSION,
            classify_t3_requirement,
            record_skip_telemetry,
        )
        record_skip_telemetry_func = record_skip_telemetry
        current_files = [rel]
        if os.path.exists(marker):
            try:
                with open(marker, encoding="utf-8") as f:
                    current_data = json.load(f)
                current_files = list(current_data.get("files") or [])
            except Exception:
                current_files = [rel]
        if rel not in current_files:
            current_files.append(rel)
        t3_decision = classify_t3_requirement(workspace, current_files)
    except Exception:
        t3_decision = None
        CLASSIFIER_VERSION = "classifier-unavailable"

    # Phase 4: telemetry 기반 skip 결정 선계산 — review_metrics.jsonl 읽기는
    # 락 밖에서 수행 (파일 I/O로 인한 3s hook 타임아웃 방지, blast_tier 선계산과 동일 패턴).
    telemetry_decision = None
    telemetry_skip_enacted_func = None
    append_skip_audit_func = None
    try:
        from review_metrics_logger import (  # type: ignore
            append_skip_audit,
            compute_t3_telemetry_skip,
        )
        from review_gate import _telemetry_skip_enacted  # type: ignore

        telemetry_decision = compute_t3_telemetry_skip(workspace)
        telemetry_skip_enacted_func = _telemetry_skip_enacted
        append_skip_audit_func = append_skip_audit
    except Exception:
        telemetry_decision = None

    try:
        if _state_lock is not None:
            with _state_lock(workspace):
                _do_update(
                    new_file_tier, t3_decision, record_skip_telemetry_func,
                    telemetry_decision, telemetry_skip_enacted_func, append_skip_audit_func,
                )
        else:
            _do_update(
                new_file_tier, t3_decision, record_skip_telemetry_func,
                telemetry_decision, telemetry_skip_enacted_func, append_skip_audit_func,
            )
    except Exception:
        pass


def main() -> None:
    if len(sys.argv) < 2:
        return
    main_for_path(sys.argv[1])


if __name__ == "__main__":
    main()
