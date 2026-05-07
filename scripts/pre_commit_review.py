#!/usr/bin/env python3
"""
scripts/pre_commit_review.py
==============================
Pre-commit hook에서 호출되는 교차검증 결과 확인 스크립트.

claude CLI를 호출하지 않는다. 기존 watcher가 생성한 docs/reviews/ 결과를
수집하여 severity를 집계하고 판정한다.

호출 방식:
  1. .githooks/pre-commit (자동)
  2. CLI: python3 scripts/pre_commit_review.py [--status] [--block-on critical|high]

종료 코드:
  0 = PASS 또는 WARN (커밋 진행)
  1 = BLOCK (커밋 차단)

항상 비차단 원칙: 인프라 장애(파싱 실패, 파일 없음 등)로 커밋을 차단하지 않는다.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
from datetime import datetime


# ── 설정 ─────────────────────────────────────────────────────────────────────

REVIEWS_DIR = os.path.join("docs", "reviews")

# severity 키워드 매칭 패턴 (리뷰 마크다운에서 추출)
_SEVERITY_PATTERNS = {
    "critical": re.compile(r"\[Critical\]", re.IGNORECASE),
    "high": re.compile(r"\[High\]", re.IGNORECASE),
    "medium": re.compile(r"\[Medium\]", re.IGNORECASE),
    "low": re.compile(r"\[Low\]", re.IGNORECASE),
}


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

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


def _staged_py_files(workspace: str) -> list[str]:
    """스테이지된 .py 파일 목록을 반환한다."""
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        if r.returncode != 0:
            return []
        files = []
        for line in r.stdout.splitlines():
            f = line.strip()
            if not f.endswith(".py"):
                continue
            # 교차검증 대상: core/*.py, model_utils.py, run_factory_cli.py
            if f.startswith("core/") or f in ("model_utils.py", "run_factory_cli.py"):
                files.append(f)
        return files
    except Exception:
        return []


def _file_stem(filepath: str) -> str:
    """core/providers/cli.py → cli"""
    return os.path.splitext(os.path.basename(filepath))[0]


def _find_latest_review(stem: str, workspace: str) -> str | None:
    """docs/reviews/ 에서 stem에 해당하는 가장 최신 리뷰 파일을 찾는다."""
    reviews_dir = os.path.join(workspace, REVIEWS_DIR)
    if not os.path.isdir(reviews_dir):
        return None

    pattern = os.path.join(reviews_dir, f"*-{stem}-code-review.md")
    matches = glob.glob(pattern)
    if not matches:
        # 좀 더 넓은 패턴으로 재시도
        pattern = os.path.join(reviews_dir, f"*-{stem}-*.md")
        matches = glob.glob(pattern)

    if not matches:
        return None

    # mtime 기준 최신 파일
    return max(matches, key=os.path.getmtime)


# 리뷰 본문에서 참조되는 소스 파일 경로 추출 패턴
# 예: "core/research/quality_contract.py:67", "`af.spec`", "core/research_router.py"
_REFERENCED_FILE_PATTERN = re.compile(
    r"(?:core/[\w/]+\.py|[\w/]+\.spec|model_utils\.py|run_factory_cli\.py|version\.py)",
)

# Final Verdict 추출 — "### Verdict: BLOCK" / "### Verdict: WARN" / "### Verdict: PASS"
_VERDICT_PATTERN = re.compile(r"^###?\s*Verdict:\s*(BLOCK|WARN|PASS)", re.MULTILINE | re.IGNORECASE)


def _read_review(review_path: str) -> str:
    try:
        with open(review_path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _extract_verdict(review_content: str) -> str:
    """리뷰 본문에서 최상위 Verdict(BLOCK/WARN/PASS) 추출. 없으면 'UNKNOWN'."""
    m = _VERDICT_PATTERN.search(review_content)
    return m.group(1).upper() if m else "UNKNOWN"


def _extract_referenced_files(review_content: str) -> set[str]:
    """리뷰 본문이 지적한 소스 파일 경로 집합 추출 (중복 제거)."""
    return {p for p in _REFERENCED_FILE_PATTERN.findall(review_content)}


def _is_stale(review_path: str, source_path: str, workspace: str) -> bool:
    """리뷰가 stale인지 판정.

    조건 (둘 중 하나라도 충족 시 stale):
      A) 트리거 소스 파일(source_path) mtime > review mtime
      B) 리뷰 본문이 참조한 다른 소스 파일들이 모두 review mtime 이후 수정됨
         (= 리뷰가 지적한 결함이 모두 수정 시도됨)
    """
    try:
        review_mtime = os.path.getmtime(review_path)
    except OSError:
        return True

    # A) 트리거 파일 자체 변경
    abs_source = os.path.join(workspace, source_path)
    if os.path.exists(abs_source):
        try:
            if os.path.getmtime(abs_source) > review_mtime:
                return True
        except OSError:
            pass

    # B) 본문 참조 파일들이 모두 review 이후 변경됐다면 stale
    content = _read_review(review_path)
    refs = _extract_referenced_files(content)
    refs.discard(source_path)  # 트리거 파일은 위에서 처리
    if refs:
        all_newer = True
        any_exists = False
        for ref in refs:
            abs_ref = os.path.join(workspace, ref)
            if not os.path.exists(abs_ref):
                continue
            any_exists = True
            try:
                if os.path.getmtime(abs_ref) <= review_mtime:
                    all_newer = False
                    break
            except OSError:
                all_newer = False
                break
        if any_exists and all_newer:
            return True

    return False


def _parse_severity(review_path: str) -> dict[str, int]:
    """리뷰 파일에서 severity별 건수를 추출한다.

    Verdict가 BLOCK이 아니면 (WARN/PASS) 모든 건수를 0으로 보고한다 — advisory 정책.
    """
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    content = _read_review(review_path)
    if not content:
        return counts
    verdict = _extract_verdict(content)
    if verdict != "BLOCK":
        return counts  # WARN/PASS/UNKNOWN → 자동 차단 안 함
    for severity, pattern in _SEVERITY_PATTERNS.items():
        counts[severity] = len(pattern.findall(content))
    return counts


# ── 메인 로직 ────────────────────────────────────────────────────────────────

def collect_results(workspace: str) -> dict:
    """스테이지된 파일별 리뷰 결과를 수집한다."""
    staged = _staged_py_files(workspace)
    if not staged:
        return {"files": [], "total": _zero_counts(), "reviewed": 0, "missing": 0, "stale": 0}

    total = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    reviewed = 0
    missing = 0
    stale = 0
    file_results = []

    for filepath in staged:
        stem = _file_stem(filepath)
        review = _find_latest_review(stem, workspace)

        if review is None:
            missing += 1
            file_results.append({"file": filepath, "status": "missing"})
            continue

        if _is_stale(review, filepath, workspace):
            stale += 1
            file_results.append({"file": filepath, "status": "stale"})
            continue

        counts = _parse_severity(review)
        reviewed += 1
        for k in total:
            total[k] += counts[k]
        file_results.append({"file": filepath, "status": "reviewed", "severity": counts})

    return {
        "files": file_results,
        "total": total,
        "reviewed": reviewed,
        "missing": missing,
        "stale": stale,
    }


def _zero_counts() -> dict[str, int]:
    return {"critical": 0, "high": 0, "medium": 0, "low": 0}


def judge(results: dict, block_on: str = "high") -> tuple[str, int]:
    """결과를 판정한다. (verdict, exit_code)를 반환."""
    total = results["total"]
    reviewed = results["reviewed"]
    missing = results["missing"]
    stale = results["stale"]

    # 결과가 하나도 없으면 WARN (비차단)
    if reviewed == 0:
        return "WARN", 0

    # BLOCK 판정
    if block_on == "critical":
        blocked = total["critical"] > 0
    else:  # "high"
        blocked = total["critical"] > 0 or total["high"] > 0

    if blocked:
        return "BLOCK", 1

    # WARN 또는 PASS
    if total["medium"] > 0 or missing > 0 or stale > 0:
        return "WARN", 0

    return "PASS", 0


def print_result(results: dict, verdict: str) -> None:
    """결과를 터미널에 출력한다."""
    total = results["total"]
    reviewed = results["reviewed"]
    missing = results["missing"]
    stale = results["stale"]
    total_files = reviewed + missing + stale

    if verdict == "PASS":
        print(
            f"  \u2705 [\uad50\ucc28\uac80\uc99d] PASS \u2014 "
            f"{total_files} \ud30c\uc77c \uac80\uc99d, "
            f"{total['critical']} Critical, {total['high']} High, "
            f"{total['medium']} Medium, {total['low']} Low"
        )
    elif verdict == "WARN":
        if reviewed == 0:
            print(
                f"  \u26a0\ufe0f  [\uad50\ucc28\uac80\uc99d] \ub9ac\ubdf0 \uacb0\uacfc \uc5c6\uc74c \u2014 "
                f"{missing + stale}/{total_files} \ud30c\uc77c \ubbf8\uac80\uc99d "
                f"(watcher \uc2e4\ud589 \ub300\uae30 \uc911\uc77c \uc218 \uc788\uc74c)"
            )
            print(
                f"     \ucee4\ubc0b\uc744 \uc9c4\ud589\ud569\ub2c8\ub2e4."
            )
        else:
            print(
                f"  \u26a0\ufe0f  [\uad50\ucc28\uac80\uc99d] WARN \u2014 "
                f"{total_files} \ud30c\uc77c ({reviewed} \uac80\uc99d, {missing} \ubbf8\uac80\uc99d, {stale} stale), "
                f"{total['critical']} Critical, {total['high']} High, "
                f"{total['medium']} Medium, {total['low']} Low"
            )
    elif verdict == "BLOCK":
        print(
            f"  \u274c [\uad50\ucc28\uac80\uc99d] BLOCK \u2014 "
            f"{total['critical']} Critical, {total['high']} High \ubc1c\uacac"
        )
        # BLOCK 원인 파일 출력
        for fr in results["files"]:
            if fr.get("status") == "reviewed":
                sev = fr.get("severity", {})
                if sev.get("critical", 0) > 0 or sev.get("high", 0) > 0:
                    print(f"     \u2192 {fr['file']}: {sev.get('critical', 0)} Critical, {sev.get('high', 0)} High")


def show_status(workspace: str) -> None:
    """현재 교차검증 상태를 출력한다."""
    results = collect_results(workspace)
    verdict, _ = judge(results)
    print_result(results, verdict)
    print()
    print(f"  \ub9ac\ubdf0 \ub514\ub809\ud1a0\ub9ac: {os.path.join(workspace, REVIEWS_DIR)}")
    reviews_dir = os.path.join(workspace, REVIEWS_DIR)
    if os.path.isdir(reviews_dir):
        review_files = glob.glob(os.path.join(reviews_dir, "*-review.md"))
        print(f"  \ub9ac\ubdf0 \ud30c\uc77c \uc218: {len(review_files)}")
    else:
        print(f"  \ub9ac\ubdf0 \ub514\ub809\ud1a0\ub9ac \uc5c6\uc74c")


# ── 진입점 ───────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-commit cross-verification result checker")
    parser.add_argument("--status", action="store_true", help="현재 교차검증 상태 출력")
    parser.add_argument(
        "--block-on",
        default=os.getenv("AF_PRE_COMMIT_REVIEW_BLOCK_ON", "high"),
        choices=["critical", "high"],
        help="BLOCK 기준 (기본: high)",
    )
    args = parser.parse_args()

    workspace = _detect_workspace()

    if args.status:
        show_status(workspace)
        return 0

    try:
        results = collect_results(workspace)
        verdict, exit_code = judge(results, block_on=args.block_on)
        print_result(results, verdict)
        return exit_code
    except Exception as exc:
        # 인프라 장애는 비차단
        print(f"  \u26a0\ufe0f  [\uad50\ucc28\uac80\uc99d] \ub0b4\ubd80 \uc624\ub958: {exc}")
        print(f"     \ucee4\ubc0b\uc744 \uc9c4\ud589\ud569\ub2c8\ub2e4.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
