#!/usr/bin/env python3
"""verify-handoff 검증 스크립트 — pre-commit + tick 완료 검증용.

검증 항목:
  1. verification-report.md 존재
  2. e2e_command 필드가 비어있지 않음
  3. verdict 필드가 BLOCK이 아님
  4. verdict == BLOCK 시 ApprovalGate 자동 차단

non-zero exit → pre-commit 차단 또는 tick approval-gate 차단.

사용법:
  python scripts/verify_handoff_checker.py [path/to/work-item-dir | path/to/verification-report.md ...]

  인자 없음 시: git staged에서 verification-report.md 자동 감지.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# e2e_command 빈 값으로 간주할 문자열 집합
_EMPTY_VALUES = {
    "", "(채워야 함)", "(fill in)", "none", "n/a", "-",
    "(needs_backfill)", "(edit required)", "(auto-generate needed)",
}

# document_policy.COMPLETION_CRITERIA 로드 (없으면 기본값 사용)
try:
    _repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_repo_root))
    from core.document_policy import COMPLETION_CRITERIA, FORBIDDEN_TOKENS
except Exception:
    COMPLETION_CRITERIA = {}
    FORBIDDEN_TOKENS = ["(edit required)", "(auto-generate needed)", "TODO: "]


def _check_report(report_path: Path) -> int:
    """단일 verification-report.md 검증. 0=정상, 1=오류."""
    if not report_path.exists():
        print(f"[verify-handoff-checker] FAIL: 파일 없음 — {report_path}", file=sys.stderr)
        return 1

    text = report_path.read_text(encoding="utf-8")
    errors: list[str] = []

    # COMPLETION_CRITERIA 기반 검증
    # 1. e2e_command_exit_code: e2e_command 필드 존재 여부
    if COMPLETION_CRITERIA.get("e2e_command_exit_code") is not None:
        m_cmd = re.search(r"e2e_command:\s*([^\n]*)", text)
        if not m_cmd or m_cmd.group(1).strip().lower() in _EMPTY_VALUES:
            errors.append("e2e_command 필드가 비어있습니다")

    # 2. forbidden_tokens_absent
    forbidden = COMPLETION_CRITERIA.get("forbidden_tokens_absent") or FORBIDDEN_TOKENS
    for token in forbidden:
        if token in text:
            errors.append(f"금지 토큰 발견: {token!r}")

    # 3. verification_report_verdict_not
    blocked_verdict = COMPLETION_CRITERIA.get("verification_report_verdict_not", "BLOCK")
    m_verdict = re.search(r"^\s*-\s*verdict:\s*([^\n]+)", text, re.MULTILINE | re.IGNORECASE)
    verdict = m_verdict.group(1).strip().upper() if m_verdict else ""
    if verdict == (blocked_verdict or "BLOCK").upper():
        errors.append(f"verification verdict={verdict}")
        _propagate_block_to_gate(report_path)

    if errors:
        for err in errors:
            print(f"[verify-handoff-checker] FAIL: {err} — {report_path}", file=sys.stderr)
        return 1

    print(f"[verify-handoff-checker] PASS: {report_path}")
    return 0


def _propagate_block_to_gate(report_path: Path) -> None:
    """verdict=BLOCK → 같은 work-item 폴더의 ApprovalGate를 차단한다."""
    try:
        work_item_dir = report_path.parent
        # docs/work-items/<slug>/approval-gate.md 구조
        gate_path = work_item_dir / "approval-gate.md"
        if not gate_path.exists():
            return
        # workspace는 work-items/ 의 2단계 상위
        workspace = str(work_item_dir.parent.parent)
        slug = work_item_dir.name
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.approval_gate import ApprovalGate
        gate = ApprovalGate(workspace, slug)
        gate.apply_verification_verdict("BLOCK")
        print(f"[verify-handoff-checker] approval-gate 차단: {gate_path}", file=sys.stderr)
    except Exception as exc:
        print(f"[verify-handoff-checker] gate 차단 실패 (무시): {exc}", file=sys.stderr)


def _staged_reports() -> list[Path]:
    """git staged 파일 중 verification-report.md 목록."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5,
        )
        return [
            Path(p) for p in result.stdout.splitlines()
            if p.endswith("verification-report.md")
        ]
    except Exception:
        return []


def main() -> int:
    args = sys.argv[1:]
    if not args:
        targets = _staged_reports()
        if not targets:
            return 0
    else:
        targets = []
        for arg in args:
            p = Path(arg)
            if p.is_dir():
                p = p / "verification-report.md"
            targets.append(p)

    errors = sum(_check_report(p) for p in targets)
    return min(errors, 1)


if __name__ == "__main__":
    sys.exit(main())
