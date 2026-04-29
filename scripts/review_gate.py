"""
scripts/review_gate.py
======================
Review-gate: 3-tier 교차검증 완료 여부를 판정하고 git commit을 차단한다.

설계: docs/2026-04-19-review-gate-enforcement.md §6.1
판정 순서: env bypass → 큐 없음 → .py 없음 → 티어 누락 → stale → 신규파일 → verdict-block → PASS
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import tempfile
import time

_QUEUE_DIR = ".af_review_queue"
_PENDING_FILE = "pending_agent_review.json"
_LOCK_FILE = "pending_agent_review.json.lock"
_LOG_FILE = "hook_events.log"

# verdict 파싱: 구조화 헤더("Verdict: BLOCK" / "판정: WARN" / "### BLOCK")만 인식
_VERDICT_RE = re.compile(
    r"(?:verdict|판정)\s*[:\-]\s*(block|warn|pass|fail)",
    re.IGNORECASE | re.MULTILINE,
)
_VERDICT_HEADER_RE = re.compile(
    r"^#{1,4}\s+(BLOCK|WARN|PASS|FAIL)\b",
    re.IGNORECASE | re.MULTILINE,
)

_TIER_AGENTS: dict[int, str] = {
    1: "af-test-runner",
    2: "af-critic",
    3: "af-cross-review",
}
_AGENT_TIER: dict[str, int] = {v: k for k, v in _TIER_AGENTS.items()}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _queue_path(workspace: str) -> str:
    return os.path.join(workspace, _QUEUE_DIR, _PENDING_FILE)


def _lock_path(workspace: str) -> str:
    return os.path.join(workspace, _QUEUE_DIR, _LOCK_FILE)


@contextlib.contextmanager
def _state_lock(workspace: str):
    """Exclusive file lock for Read-Modify-Write on pending_agent_review.json.

    병렬 에이전트(af-test-runner · af-critic · af-cross-review)가 동시에
    record_review_done()을 호출해도 서로의 tier 기록을 덮어쓰지 않도록 보장한다.
    POSIX(fcntl) 전용 — Windows fallback은 no-op (hook_runner와 동일 정책).
    """
    lp = _lock_path(workspace)
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    try:
        import fcntl
        fd = os.open(lp, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
    except ImportError:
        # Windows: no-op (best-effort)
        yield


def _log_path(workspace: str) -> str:
    return os.path.join(workspace, _QUEUE_DIR, _LOG_FILE)


def _load_state(workspace: str) -> dict | None:
    path = _queue_path(workspace)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _save_state(workspace: str, state: dict) -> None:
    path = _queue_path(workspace)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dir_ = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _log_event(workspace: str, msg: str) -> None:
    try:
        log = _log_path(workspace)
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}|{msg}\n")
    except Exception:
        pass


# ── 공개 API ──────────────────────────────────────────────────────────────────

def _required_tiers_for(state: dict) -> list[int]:
    """Phase 0: blast_tier에 따라 필수 tier 목록을 반환.

    Tier 1: [1]               — af-test-runner만
    Tier 2~3: [1, 2, 3]       — 정상 3-tier
    """
    blast = int(state.get("blast_tier", 2))
    return [1] if blast == 1 else [1, 2, 3]


def is_gate_blocked(workspace: str) -> tuple[bool, str]:
    """BLOCK 여부 + reason 반환. 게이트 자체 오류는 fail-open (PASS + stderr 경고)."""
    # 1. 환경변수 우회
    if os.environ.get("AF_SKIP_REVIEW_GATE") == "1":
        _log_event(workspace, "[gate-skipped-env]")
        return False, "gate-skipped-env"

    # 2. 상태 로드 (fail-open)
    try:
        state = _load_state(workspace)
    except Exception as exc:
        print(f"[review_gate] 상태 로드 오류 (PASS): {exc}", file=sys.stderr)
        return False, "load-error"

    if state is None:
        return False, "no-queue"

    # 3. .py 파일 유무 확인 (없으면 PASS)
    py_files = [f for f in state.get("files", []) if f.endswith(".py")]
    if not py_files:
        return False, "no-py-files"

    reviews: dict = state.get("reviews") or {}
    updated_at: float = float(state.get("updated_at") or 0.0)

    # 4. 필수 티어 확인 — Phase 0: blast_tier 기반
    required_tiers = _required_tiers_for(state)
    for tier in required_tiers:
        agent = _TIER_AGENTS[tier]
        if agent not in reviews:
            return True, f"missing-tier-{tier}"

    # 5. stale 체크: 어느 필수 리뷰 완료 이후에 파일 편집 발생
    # Phase 0: 필수 tier만 검사 (Tier 1 파일은 af-test-runner만)
    min_completed = min(
        float(reviews[_TIER_AGENTS[tier]].get("completed_at") or 0)
        for tier in required_tiers
    )
    if updated_at > min_completed:
        # Phase 0: max_rounds 도달 후엔 stale 차단만 건너뛰고 BLOCK 검사로 fall-through
        # (Critical fix: BLOCK verdict는 무조건 검사되어야 함 — AF_SKIP_REVIEW_GATE 외 우회 금지)
        if int(state.get("round_count", 0)) < 2:
            return True, "stale-review"

    # 6. 신규 파일 추가 체크: 가장 높은 필수 tier의 snapshot 기준
    highest_tier = max(required_tiers)
    snap_agent = _TIER_AGENTS[highest_tier]
    snap = set(reviews.get(snap_agent, {}).get("files_snapshot") or [])
    new_files = [f for f in py_files if f not in snap]
    if new_files:
        return True, "new-files-added"

    # 7. verdict=block|fail 체크 (FAIL도 BLOCK과 동등하게 차단)
    if not os.environ.get("AF_GATE_ALLOW_VERDICT_BLOCK"):
        for agent, r in reviews.items():
            if r.get("verdict") in ("block", "fail"):
                return True, f"verdict-block:{agent}"

    return False, "all-tiers-passed"


def record_review_done(
    workspace: str,
    agent: str,
    tier: int,
    verdict: str,
    files_snapshot: list[str] | None = None,
) -> None:
    """reviews[agent] 기록. 파일 락 + atomic write.

    병렬 에이전트가 동시에 호출해도 각 tier 기록이 유실되지 않는다.
    files_snapshot=None 이면 락 내부에서 현재 state["files"]를 snapshot으로 사용.
    → TOCTOU 방지: 호출자가 락 밖에서 미리 읽은 snapshot이 stale하더라도 안전.

    Phase 0 라운드 모델:
    - enqueue가 새 라운드 시작 시 round_started_at 설정 (또는 1차 enqueue가 누락 시 첫 record가 보정)
    - 모든 required 에이전트의 completed_at >= round_started_at 일 때만 round_count++
    - 종료 후 round_started_at = None → 다음 enqueue가 새 라운드 토큰 부여
    """
    now = time.time()
    try:
        with _state_lock(workspace):
            state = _load_state(workspace) or {"files": [], "created_at": now}
            if "reviews" not in state or not isinstance(state.get("reviews"), dict):
                state["reviews"] = {}

            # 라운드 토큰 보정: enqueue가 set 안 했고 첫 record 호출이면 여기서 set
            if not state.get("round_started_at"):
                state["round_started_at"] = now

            # M1: snapshot을 락 내부의 최신 state에서 읽어 TOCTOU 해소
            snapshot = list(files_snapshot) if files_snapshot is not None else list(state.get("files") or [])
            current_round = int(state.get("round_count", 0)) + 1  # 다음 라운드 번호 (claim_id에 사용)
            state["reviews"][agent] = {
                "tier": tier,
                "verdict": verdict.lower(),
                "files_snapshot": snapshot,
                "completed_at": now,
                "claim_id": _make_claim_id(agent, current_round, now),
            }

            # 라운드 종료 판정: 모든 required 에이전트가 round_started_at 이후 완료
            required = _required_tiers_for(state)
            round_started = float(state.get("round_started_at") or 0.0)
            all_post_start = round_started > 0 and all(
                _TIER_AGENTS[t] in state["reviews"]
                and float(state["reviews"][_TIER_AGENTS[t]].get("completed_at") or 0) >= round_started
                for t in required
            )
            if all_post_start:
                verdicts = {
                    _TIER_AGENTS[t]: state["reviews"][_TIER_AGENTS[t]].get("verdict")
                    for t in required
                }
                has_block = any(v in ("block", "fail") for v in verdicts.values())
                state["round_count"] = int(state.get("round_count", 0)) + 1
                state["last_round_summary"] = {
                    "round": state["round_count"],
                    "verdicts": verdicts,
                    "has_block": has_block,
                    "completed_at": now,
                    "round_started_at": round_started,
                }
                # 다음 라운드용 토큰 클리어 — 다음 enqueue가 새 round_started_at 부여
                state["round_started_at"] = None
                _log_event(
                    workspace,
                    f"[round-complete] round={state['round_count']} "
                    f"has_block={has_block} verdicts={verdicts}",
                )

            _save_state(workspace, state)
        _log_event(workspace, f"[review-recorded] agent={agent} tier={tier} verdict={verdict}")
    except Exception as exc:
        print(f"[review_gate] record_review_done 실패: {exc}", file=sys.stderr)


def _make_claim_id(agent: str, round_num: int, now: float) -> str:
    """Stable claim ID: AF-RG-YYYYMMDDHHMMSS-R{round}-{agent_short} (UTC).

    UTC + 초 단위 + round 번호 포함 → 분 절단/timezone 의존 없음.
    """
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime(now))
    short = {"af-test-runner": "T1", "af-critic": "T2", "af-cross-review": "T3"}.get(agent, agent)
    return f"AF-RG-{ts}-R{round_num}-{short}"


def clear_committed_files(workspace: str, committed_files: list[str]) -> None:
    """커밋 성공 후 staged 파일만 선택적으로 files/reviews snapshot에서 제거.

    af-critic v1-H4 반영: 통째 삭제하면 동시 편집한 신규 파일 유실.
    파일 락으로 record_review_done()과의 경쟁 조건 방지.

    Phase 0: files가 모두 비면 라운드 메타데이터(round_count, last_round_summary,
    round_started_at, fired_at)도 함께 리셋 → 다음 작업 사이클이 깨끗하게 시작.
    """
    try:
        committed_set = set(committed_files)
        with _state_lock(workspace):
            state = _load_state(workspace)
            if not state:
                return
            state["files"] = [f for f in state.get("files") or [] if f not in committed_set]
            reviews = state.get("reviews") or {}
            for r in reviews.values():
                r["files_snapshot"] = [
                    f for f in (r.get("files_snapshot") or []) if f not in committed_set
                ]
            if not state["files"]:
                # Phase 0: 사이클 종료 — 라운드 메타데이터 전체 리셋
                state["reviews"] = {}
                state.pop("round_count", None)
                state.pop("last_round_summary", None)
                state.pop("round_started_at", None)
                state.pop("fired_at", None)
                state.pop("blast_tier", None)
            _save_state(workspace, state)
        _log_event(
            workspace,
            f"[gate-cleared] committed={len(committed_files)} remaining={len(state['files'])}",
        )
    except Exception as exc:
        print(f"[review_gate] clear_committed_files 실패: {exc}", file=sys.stderr)


# ── CLI ───────────────────────────────────────────────────────────────────────

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


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Review-gate 판정 CLI")
    parser.add_argument("--workspace", "-w", default=None)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="게이트 판정 (exit 0=PASS, 1=BLOCK)")
    group.add_argument("--record", metavar="AGENT", help="리뷰 기록")
    group.add_argument("--clear", action="store_true", help="커밋된 파일 정리")
    group.add_argument("--debug", action="store_true", help="상태 + 판정 출력")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3])
    parser.add_argument("--verdict", choices=["pass", "warn", "block", "fail"])
    parser.add_argument("--files", default="", help="쉼표 구분 파일 목록")
    args = parser.parse_args(argv)

    ws = args.workspace or _detect_workspace()
    files = [f.strip() for f in args.files.split(",") if f.strip()] if args.files else []

    if args.check:
        blocked, reason = is_gate_blocked(ws)
        if blocked:
            print(f"⛔ [review-gate] BLOCK: {reason}", file=sys.stderr)
            print(
                "   af-test-runner → af-critic → af-cross-review 순서로 Agent 실행 후 재시도.",
                file=sys.stderr,
            )
            print("   우회: AF_SKIP_REVIEW_GATE=1 git commit ...", file=sys.stderr)
            return 1
        print(f"✅ [review-gate] PASS: {reason}")
        return 0

    if args.record:
        agent = args.record
        if agent not in _AGENT_TIER:
            print(f"[review_gate] 알 수 없는 agent: {agent}", file=sys.stderr)
            return 1
        tier = args.tier if args.tier is not None else _AGENT_TIER[agent]
        verdict = args.verdict or "pass"
        record_review_done(ws, agent, tier, verdict, files)
        print(f"[review_gate] 기록 완료: {agent} tier={tier} verdict={verdict}")
        return 0

    if args.clear:
        clear_committed_files(ws, files)
        print(f"[review_gate] 정리 완료: {len(files)}개 파일")
        return 0

    if args.debug:
        state = _load_state(ws)
        blocked, reason = is_gate_blocked(ws)
        import pprint
        print("=== review-gate debug ===")
        print(f"workspace : {ws}")
        print(f"verdict   : {'BLOCK' if blocked else 'PASS'} ({reason})")
        if state:
            pprint.pprint(state)
        else:
            print("(큐 없음)")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(_cli())
