#!/usr/bin/env python3
"""scripts/check_staged_design_review.py

커밋 직전, staged 설계문서에 대해 docs/reviews/ 의 최신 자동 리뷰 verdict 를 확인한다.
최신 리뷰가 BLOCK 이면 exit 1 로 커밋을 차단하고 해당 리뷰 파일 경로를 출력한다.

배경 — surface 단절 해소 (2026-06-18):
  자동 설계리뷰 watcher(scripts/design_review_watcher.py)는 리뷰 결과를
  docs/reviews/*.md 에 산출하지만, 그 결과를 작업자에게 노출하던 채널
  (UserPromptSubmit hook 의 check_design_pending.py)이 제거되면서 끊겼다.
  그 탓에 watcher 가 Critical BLOCK 판정한 설계문서가 안 보인 채 그대로
  커밋된 사례(d1022ecd)가 있었다. 이 스크립트는 그 surface 를 git-native
  pre-commit(프로바이더 무관·사람입력 무관) 에 복원한다.

프로바이더 무관: pre-commit 에서 호출되므로 Claude/Codex/IDE/shell 어디서
  커밋하든 발화한다. CLAUDE.md 등 특정 프로바이더 지침에 의존하지 않는다.
우회: AF_SKIP_REVIEW_GATE=1 git commit ...  (pre-commit 이 호출 전 분기).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

# docs/reviews/{ts}-{stem}-design-review.md  (ts = YYYY-MM-DD-HHMMSS, 정렬 가능)
_DESIGN_REVIEW_SUFFIX = "-design-review.md"
_REVIEWS_REL = os.path.join("docs", "reviews")

# 헤더 `> Source: <rel>` / 본문 `### Verdict: <VERDICT>` 파싱 (watcher _write_result 포맷).
# 볼드체 `### Verdict: **BLOCK**` 도 흡수 — 실측 19개 리뷰가 emphasis markdown 사용(누락 시
# silent false-negative → d1022ecd 재현). `\*{0,2}` 가 선행 `**` 를 건너뛴다.
_SOURCE_RE = re.compile(r"^>\s*Source:\s*(.+?)\s*$", re.MULTILINE)
_VERDICT_RE = re.compile(r"^#+\s*Verdict:\s*\*{0,2}([A-Za-z_]+)", re.MULTILINE)

_BLOCK = "BLOCK"


def _repo_root() -> str:
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


def _staged_files(workspace: str) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, timeout=10, cwd=workspace,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    return [ln.strip().replace("\\", "/") for ln in r.stdout.splitlines() if ln.strip()]


def load_latest_design_verdicts(workspace: str) -> dict[str, tuple[str, str]]:
    """source(정규화 rel) → (verdict, review_rel_path) 의 최신 설계리뷰 맵.

    '최신' = 파일명 ts prefix 가 가장 큰 리뷰. 같은 source 에 새 PASS/WARN 리뷰가
    나중에 산출되면 그것이 최신이 되어 이전 BLOCK 을 덮는다(false-block 방지).
    """
    reviews_dir = os.path.join(workspace, _REVIEWS_REL)
    if not os.path.isdir(reviews_dir):
        return {}

    # source → (review_filename, verdict)  — filename 으로 최신성 비교.
    latest: dict[str, tuple[str, str]] = {}
    for name in sorted(os.listdir(reviews_dir)):
        if not name.endswith(_DESIGN_REVIEW_SUFFIX):
            continue
        try:
            with open(os.path.join(reviews_dir, name), "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        m_src = _SOURCE_RE.search(text)
        m_ver = _VERDICT_RE.search(text)
        if not m_src or not m_ver:
            continue
        source = m_src.group(1).replace("\\", "/")
        verdict = m_ver.group(1).upper()
        prev = latest.get(source)
        if prev is None or name > prev[0]:
            latest[source] = (name, verdict)

    return {
        src: (verdict, os.path.join(_REVIEWS_REL, fname).replace("\\", "/"))
        for src, (fname, verdict) in latest.items()
    }


def find_blocked(workspace: str, staged: list[str]) -> list[tuple[str, str]]:
    """staged 설계문서 중 최신 리뷰가 BLOCK 인 것 → (문서 rel, 리뷰 rel) 목록."""
    # SSOT: is_design_doc / normalize_path 는 core.design_review_utils 재사용.
    if workspace not in sys.path:
        sys.path.insert(0, workspace)
    from core.design_review_utils import is_design_doc, normalize_path

    verdicts = load_latest_design_verdicts(workspace)
    blocked: list[tuple[str, str]] = []
    for rel in staged:
        abspath = os.path.join(workspace, rel)
        if not is_design_doc(abspath, workspace):
            continue
        norm = normalize_path(abspath, workspace)
        info = verdicts.get(norm)
        if info and info[0] == _BLOCK:
            blocked.append((norm, info[1]))
    return blocked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="staged 설계문서의 최신 자동 리뷰 verdict 확인 (BLOCK → 커밋 차단)."
    )
    parser.add_argument("--workspace", "-w", default=None)
    args = parser.parse_args(argv)
    workspace = args.workspace or _repo_root()

    try:
        blocked = find_blocked(workspace, _staged_files(workspace))
    except Exception as exc:
        # 게이트 자체 오작동으로 정상 커밋을 막지 않는다 (surface 는 보조 안전망).
        # 단, 오작동을 silent 로 묻지 않고 stderr 로 가시화한다(import/파싱 버그 조기 발견).
        print(f"[check-staged-design-review] 게이트 비활성(예외, 커밋 비차단): {exc}", file=sys.stderr)
        return 0

    if not blocked:
        return 0

    print("")
    print("🛑 [pre-commit] 설계리뷰 BLOCK 미해결 — 자동 리뷰가 차단 판정한 설계문서가 staged 상태입니다:")
    for doc, review in blocked:
        print(f"   • {doc}")
        print(f"     ↳ 리뷰: {review}")
    print("")
    print("   조치:")
    print("     - 리뷰 BLOCK findings 반영 후 재커밋 (watcher 새 리뷰가 최신 PASS/WARN 이면 BLOCK 을 덮음)")
    print("     - 즉시 재검토: python scripts/design_review_watcher.py . --sync <문서경로>")
    print("     - 우회: AF_SKIP_REVIEW_GATE=1 git commit ...")
    print("")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
