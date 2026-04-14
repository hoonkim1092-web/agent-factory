"""
tests/test_nlm_regression.py — Slow Integration Test (§8.2 WARN-3 해소).

실제 `nlm` 바이너리를 호출해 Phase 0/0.5 실측 포맷의 회귀 감지.
CI 주기 실행: `pytest -m slow --tb=short`

설계 문서: docs/features/2026-04-10-setup-wizard-tavily-notebooklm-integration.md §8.2
"""
from __future__ import annotations

import shutil
import subprocess

import pytest


_HAS_NLM = shutil.which("nlm") is not None

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not _HAS_NLM, reason="nlm 바이너리 미설치 — Slow 통합 테스트 스킵"),
]


def test_nlm_auth_status_output_format():
    """nlm auth status stdout 포맷 회귀 — 실패 시 exit code 2 + 특정 문자열."""
    # regression_test_profile은 존재하지 않는 프로파일 → 실패 출력 확정
    result = subprocess.run(
        ["nlm", "auth", "status", "--profile", "regression_test_profile"],
        capture_output=True, text=True, timeout=15,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert any(p in combined for p in [
        "✗ Not authenticated",
        "Profile not found",
        "Authentication failed",
    ]), f"nlm auth status 출력 포맷 변경 감지: {combined!r}"


def test_nlm_notebook_help_subcommands_exist():
    """nlm notebook 서브커맨드 목록 회귀 — list/create/get/query 반드시 존재."""
    result = subprocess.run(
        ["nlm", "notebook", "--help"],
        capture_output=True, text=True, timeout=10,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    for sub in ("list", "create", "get", "query"):
        assert sub in combined, (
            f"nlm notebook {sub} 서브커맨드 누락 — breaking change 가능성. 전체: {combined!r}"
        )
