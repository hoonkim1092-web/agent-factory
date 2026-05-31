#!/usr/bin/env python3
"""
scripts/review_metrics_logger.py
==================================
Phase 3.5: 리뷰 메트릭 수집 인프라.

review_metrics.jsonl: 에이전트 완료 이벤트마다 1행 기록.
skip_audit.jsonl: Tier 3 skip 후 BLOCK 발견 사례 기록 (Phase 4 routing 검증용).

주요 public API:
- append_metric()        에이전트 완료 시 hook_runner에서 호출
- parse_findings_count() agent 응답 텍스트에서 finding 수 추출
- parse_extension_log_count() extension log 항목 수 추출
- compute_report()       T3-only 기여도 + 비용 요약 반환 (CLI 출력)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

METRICS_FILE = "review_metrics.jsonl"
SKIP_AUDIT_FILE = "skip_audit.jsonl"

# ── Phase 4 conservative Tier-3 skip thresholds (SSOT) ─────────────────────────
# compute_t3_telemetry_skip() only authorises a skip when ALL conditions hold.
# These are deliberately conservative — raising any of them never makes skip more
# aggressive, only rarer.
T3_SKIP_BLOCK_ONLY_RATE_MAX = 10.0   # %: T3 BLOCK-only commit rate must be below this
T3_SKIP_MIN_COMMITS = 10             # sample floor: commits carrying a T3 record
T3_SKIP_MIN_SPAN_DAYS = 7.0          # recency floor: data must span >= 1 week
T3_SKIP_RECENT_WINDOW = 10           # last-N T3 commits checked for a BLOCK

# finding 마커 패턴 (구조화된 verdict 라인만 인식)
# Phase 2 v7 §5.6: `[ACCEPT-ADV]` (Medium/Low advisory) + `[BONUS]` (변경 무관 advisory)
# 라벨 추가. ACCEPT 변형 4종(`[ACCEPT]`, `[ACCEPT★]`, `[ACCEPT*]`, `[ACCEPT-ADV]`) 통합.
# `[HOLD]`는 §4.5 결정으로 Phase 3 이관 — 발화 금지.
_FINDING_RE = re.compile(
    r'\[(?:ACCEPT(?:[★*]|-ADV)?|WARN|BLOCK|REJECTED|BONUS)\]',
    re.IGNORECASE,
)

# extension log 블록: "Extension Log:" 헤더 이후
_EXT_LOG_HEADER_RE = re.compile(r'Extension Log[：:]\s*', re.IGNORECASE)
_EXT_LOG_NONE_RE = re.compile(r'Extension Log[：:]\s*(?:없음|None|없다)', re.IGNORECASE)
_EXT_LOG_ITEM_RE = re.compile(r'^\s*[-*]\s+\S', re.MULTILINE)

# scope-creep 마커 (>5건 이상임을 나타냄)
# Phase 2 v7 §5.6: scope-creep 마커는 verdict 라벨이 아니므로 fence 외부도 검색 유지
# (§5.3 verdict 파서는 fence 내부 한정 — 책임 분리).
_SCOPE_CREEP_RE = re.compile(r'\[scope-creep\]', re.IGNORECASE)


# ── File lock ────────────────────────────────────────────────────────────────

try:
    import fcntl as _fcntl

    def _flock(f: Any) -> None:
        try:
            _fcntl.flock(f, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        except OSError:
            pass  # non-blocking: skip if already locked
except ImportError:
    def _flock(f: Any) -> None:
        pass  # Windows fallback


# ── Paths ─────────────────────────────────────────────────────────────────────

def _queue_dir(workspace: str) -> str:
    return os.path.join(workspace, ".af_review_queue")


def _metrics_path(workspace: str) -> str:
    return os.path.join(_queue_dir(workspace), METRICS_FILE)


def _skip_audit_path(workspace: str) -> str:
    return os.path.join(_queue_dir(workspace), SKIP_AUDIT_FILE)


# ── Git helpers ───────────────────────────────────────────────────────────────

def _git_sha(workspace: str) -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


# ── JSONL writer ──────────────────────────────────────────────────────────────

def _append_jsonl(path: str, record: dict) -> None:
    """Append a JSON record to a JSONL file (best-effort file locking)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    try:
        with open(path, "a", encoding="utf-8") as f:
            _flock(f)
            f.write(line)
    except Exception:
        pass  # metrics is best-effort — never block review flow


# ── Parsing helpers ───────────────────────────────────────────────────────────

def parse_findings_count(content: str) -> int:
    """Count structured finding markers ([ACCEPT★], [WARN], [BLOCK], etc.)."""
    return len(_FINDING_RE.findall(content))


def parse_extension_log_count(content: str) -> int:
    """Count extension log entries from agent response.

    Returns:
        0  if 'Extension Log: 없음'
        6  if [scope-creep] marker present (>5 entries)
        N  actual item count from the log block
    """
    if _EXT_LOG_NONE_RE.search(content):
        return 0

    # scope-creep marker → at least 6
    if _SCOPE_CREEP_RE.search(content):
        return 6

    # Find log block after "Extension Log:" header
    m = _EXT_LOG_HEADER_RE.search(content)
    if not m:
        return 0

    block = content[m.end():]
    # Count bullet lines until an empty line or non-bullet
    items = 0
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            break
        if stripped.startswith(("-", "*")):
            items += 1
        elif items > 0:
            break  # end of block
    return items


# ── Public API ────────────────────────────────────────────────────────────────

def append_metric(
    workspace: str,
    agent: str,
    tier: int,
    verdict: str,
    findings_count: int = 0,
    extension_log_count: int = 0,
    duration_ms: int | None = None,
    tokens: int | None = None,
    tool_calls: int | None = None,
    evidence_present: bool = False,
    evidence_items: int = 0,
    evidence_cited: int = 0,
) -> None:
    """Record a completed review agent event to review_metrics.jsonl."""
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "commit_sha": _git_sha(workspace),
        "tier": tier,
        "agent": agent,
        "verdict": verdict,
        "findings_count": findings_count,
        "extension_log_count": extension_log_count,
        "duration_ms": duration_ms,
        "tokens": tokens,
        "tool_calls": tool_calls,
        "evidence_present": evidence_present,
        "evidence_items": evidence_items,
        "evidence_cited": evidence_cited,
    }
    _append_jsonl(_metrics_path(workspace), record)


def append_skip_audit(
    workspace: str,
    skipped_tier: int,
    reason: str,
    subsequent_block: bool = False,
) -> None:
    """Record a tier-skip event for Phase 4 routing validation."""
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "commit_sha": _git_sha(workspace),
        "skipped_tier": skipped_tier,
        "reason": reason,
        "subsequent_block": subsequent_block,
    }
    _append_jsonl(_skip_audit_path(workspace), record)


# ── Analytics ─────────────────────────────────────────────────────────────────

def _load_records(workspace: str) -> list[dict]:
    path = _metrics_path(workspace)
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def _load_skip_audit_records(workspace: str) -> list[dict]:
    path = _skip_audit_path(workspace)
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def compute_report(workspace: str) -> str:
    """Compute T3-only contribution rate and cost summary from collected metrics.

    Phase 4 routing thresholds (from plan §Phase 3.5):
      >30%: T3 고유 가치 큼  → skip 보수적
      10~30%: 중간           → 위험군 외 검토
      <10%: T3 대체로 중복   → 공격적 skip 가능
    """
    records = _load_records(workspace)
    if not records:
        return "review_metrics.jsonl 비어 있음 — 데이터 없음."
    skip_records = _load_skip_audit_records(workspace)

    # Group by commit SHA
    by_commit: dict[str, dict[int, dict]] = defaultdict(dict)
    for r in records:
        sha = r.get("commit_sha") or ""
        tier = int(r.get("tier") or 0)
        by_commit[sha][tier] = r  # last record per tier per commit

    total_records = len(records)
    t3_records = sum(1 for r in records if r.get("tier") == 3)

    # T3-only contribution metrics
    t3_findings = 0
    t2_findings = 0
    t1_findings = 0
    t3_block_only_commits = 0  # T3 BLOCK but T1+T2 not BLOCK
    commits_with_t3 = 0

    for sha, tiers in by_commit.items():
        t3_rec = tiers.get(3)
        t2_rec = tiers.get(2)
        t1_rec = tiers.get(1)

        fc3 = int((t3_rec or {}).get("findings_count") or 0)
        fc2 = int((t2_rec or {}).get("findings_count") or 0)
        fc1 = int((t1_rec or {}).get("findings_count") or 0)
        t3_findings += fc3
        t2_findings += fc2
        t1_findings += fc1

        if t3_rec:
            commits_with_t3 += 1
            v3 = (t3_rec.get("verdict") or "pass").lower()
            v2 = (t2_rec.get("verdict") or "pass").lower() if t2_rec else "pass"
            v1 = (t1_rec.get("verdict") or "pass").lower() if t1_rec else "pass"
            if v3 == "block" and v2 != "block" and v1 != "block":
                t3_block_only_commits += 1

    all_findings = t1_findings + t2_findings + t3_findings
    t3_rate = (t3_findings / all_findings * 100) if all_findings else 0.0

    # Verdict distribution per agent
    verdict_by_agent: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        agent = r.get("agent") or "unknown"
        verdict = (r.get("verdict") or "pass").lower()
        verdict_by_agent[agent][verdict] += 1

    # Extension log stats for T3
    t3_ext_logs = [
        int(r.get("extension_log_count") or 0)
        for r in records if r.get("tier") == 3
    ]
    avg_ext = (sum(t3_ext_logs) / len(t3_ext_logs)) if t3_ext_logs else 0.0

    # Skip audit summary
    skip_total = len(skip_records)
    skip_subsequent_block = sum(1 for r in skip_records if r.get("subsequent_block"))

    # Timestamp span check for 1-week data gate (Finding 3)
    try:
        first_ts = datetime.fromisoformat(records[0]["ts"])
        last_ts = datetime.fromisoformat(records[-1]["ts"])
        span_days = (last_ts - first_ts).total_seconds() / 86400
    except Exception:
        span_days = 0.0

    # Build report
    lines = [
        "=== Review Metrics Report (Phase 3.5) ===",
        f"기간: {records[0].get('ts','?')[:10]} ~ {records[-1].get('ts','?')[:10]}",
        f"총 레코드: {total_records} (T3: {t3_records} / 커밋: {len(by_commit)})",
        "",
        "── T3-only 기여도 ──",
        f"  전체 findings: T1={t1_findings}  T2={t2_findings}  T3={t3_findings}",
        f"  T3 finding share (단순 비율, T3 고유값 ≠): {t3_rate:.1f}%",
        f"  [Phase 4 primary] T3 BLOCK-only 커밋: {t3_block_only_commits} / {commits_with_t3}",
        f"  skip audit: 총 {skip_total}건 (이후 BLOCK 발견: {skip_subsequent_block}건)",
    ]

    # Finding 2: suppress guidance if any skip has subsequent_block=True
    if skip_subsequent_block > 0:
        lines.append(
            f"  ⚠️  Phase 4 판단 불가 — skip 후 BLOCK 발견 {skip_subsequent_block}건 (skip audit 검토 필요)"
        )
    elif commits_with_t3 < 10 or span_days < 7:
        # Finding 3: gate on both minimum commits AND 7-day span
        lines.append(
            f"  ⚠️  Phase 4 판단 불가 — 데이터 부족 (커밋: {commits_with_t3}/10, 기간: {span_days:.1f}일/7일)"
        )
    else:
        # Finding 1: guidance keyed on t3_block_only_commits (primary), not raw t3_rate
        block_only_rate = (t3_block_only_commits / commits_with_t3 * 100) if commits_with_t3 else 0.0
        if block_only_rate > 30:
            lines.append("  → T3 고유 가치 큼 — skip 보수적 유지 권고")
        elif block_only_rate >= 10:
            lines.append("  → 중간 — 위험군 외 선택적 skip 검토 가능")
        else:
            lines.append("  → T3 대체로 중복 — 공격적 skip 가능 (Phase 4 진입 검토)")

    lines += [
        f"  T3 평균 extension log: {avg_ext:.1f}건",
        "",
        "── 에이전트별 verdict 분포 ──",
    ]
    for agent in sorted(verdict_by_agent):
        counts = verdict_by_agent[agent]
        total = sum(counts.values())
        dist = "  ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
        lines.append(f"  {agent}: {dist}  (총 {total})")

    lines += [
        "",
        "── 미지원 필드 ──",
        "  tokens/tool_calls: 미지원 (API 통합 필요)",
    ]
    return "\n".join(lines)


def compute_t3_telemetry_skip(workspace: str) -> dict:
    """Conservative telemetry-based Tier-3 skip decision (Phase 4).

    Returns {"skip": bool, "reason": str, "metrics": {...}}.

    skip=True is granted ONLY when EVERY conservative condition holds:
      1. Data sufficiency  — commits_with_t3 >= T3_SKIP_MIN_COMMITS AND
                              span_days >= T3_SKIP_MIN_SPAN_DAYS (sample + recency floor).
      2. Block-only rate   — T3 BLOCK-only commit rate < T3_SKIP_BLOCK_ONLY_RATE_MAX.
                              BLOCK-only (T3 blocked when T1/T2 did not) is the
                              severity signal — a BLOCK is the highest-severity
                              outcome, so this stands in for the design's
                              "Critical/High severity" caveat (§397) that raw
                              finding share cannot express.
      3. Recent window     — the last T3_SKIP_RECENT_WINDOW T3 commits contain zero
                              af-cross-review BLOCK (guards a fresh regression in
                              T3 value that the all-history rate would dilute).
      4. Skip-audit clean  — no prior skip later proved to need a block
                              (skip_subsequent_block == 0) — mirrors compute_report's
                              Finding-2 guard.

    Any failing condition → skip=False with a specific reason ("why NOT skipped").
    Fail-closed: empty/insufficient data never authorises a skip.

    The BLOCK-only counting mirrors compute_report() (last record per tier per
    commit; v3==block AND v2!=block AND v1!=block). Kept self-contained rather than
    refactoring compute_report so the working report code is untouched; the two
    definitions MUST stay in sync.
    """
    records = _load_records(workspace)
    if not records:
        return {"skip": False, "reason": "no-data", "metrics": {}}
    skip_records = _load_skip_audit_records(workspace)

    # Group by commit (last record per tier) + remember T3 commit order (time order
    # of first T3 appearance) for the recency window.
    by_commit: dict[str, dict[int, dict]] = defaultdict(dict)
    t3_order: list[str] = []
    t3_seen: set[str] = set()
    for r in records:
        sha = r.get("commit_sha")
        if not sha:
            # SHA-less records (detached HEAD / non-git workspace) cannot be
            # attributed to a commit; collapsing them into one "" bucket would
            # distort the recency window. Excluding them only lowers
            # commits_with_t3 → fail-closed (insufficient-data).
            continue
        tier = int(r.get("tier") or 0)
        by_commit[sha][tier] = r
        if tier == 3 and sha not in t3_seen:
            t3_seen.add(sha)
            t3_order.append(sha)

    commits_with_t3 = 0
    t3_block_only_commits = 0
    for sha in t3_order:
        tiers = by_commit[sha]
        t3_rec = tiers.get(3)
        if not t3_rec:
            continue
        commits_with_t3 += 1
        v3 = (t3_rec.get("verdict") or "pass").lower()
        v2 = (tiers.get(2) or {}).get("verdict") or "pass"
        v1 = (tiers.get(1) or {}).get("verdict") or "pass"
        if v3 == "block" and str(v2).lower() != "block" and str(v1).lower() != "block":
            t3_block_only_commits += 1

    block_only_rate = (
        t3_block_only_commits / commits_with_t3 * 100 if commits_with_t3 else 100.0
    )

    # Recent window: zero af-cross-review BLOCK among the last N T3 commits.
    recent_shas = t3_order[-T3_SKIP_RECENT_WINDOW:]
    recent_block = any(
        ((by_commit[s].get(3) or {}).get("verdict") or "pass").lower() == "block"
        for s in recent_shas
    )

    # Timestamp span over T3 data specifically (not all records). The gate asks
    # whether T3 itself has accumulated >= 1 week; a recent Tier-1-only event must
    # not inflate the span (af-cross-review High advisory). Falls back to 0.0
    # (→ insufficient-data, fail-closed) when no T3 commits or parsing fails.
    try:
        if t3_order:
            t3_first_ts = datetime.fromisoformat(by_commit[t3_order[0]][3]["ts"])
            t3_last_ts = datetime.fromisoformat(by_commit[t3_order[-1]][3]["ts"])
            span_days = (t3_last_ts - t3_first_ts).total_seconds() / 86400
        else:
            span_days = 0.0
    except Exception:
        span_days = 0.0

    skip_subsequent_block = sum(1 for r in skip_records if r.get("subsequent_block"))

    metrics = {
        "commits_with_t3": commits_with_t3,
        "t3_block_only_commits": t3_block_only_commits,
        "block_only_rate": round(block_only_rate, 2),
        "span_days": round(span_days, 2),
        "recent_window": len(recent_shas),
        "recent_block": recent_block,
        "skip_subsequent_block": skip_subsequent_block,
    }

    # Fail-closed evaluation — data sufficiency first, then conservative blockers.
    if commits_with_t3 < T3_SKIP_MIN_COMMITS or span_days < T3_SKIP_MIN_SPAN_DAYS:
        reason = "insufficient-data"
    elif skip_subsequent_block > 0:
        reason = "prior-skip-caught-block"
    elif recent_block:
        reason = "recent-t3-block"
    elif block_only_rate >= T3_SKIP_BLOCK_ONLY_RATE_MAX:
        reason = "t3-block-only-rate-high"
    else:
        return {"skip": True, "reason": "t3-redundant", "metrics": metrics}
    return {"skip": False, "reason": reason, "metrics": metrics}


if __name__ == "__main__":
    import sys
    ws = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(compute_report(ws))
