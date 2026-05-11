"""
tests/test_review_runner_vendor_label.py
=========================================
Tier 2 Phase 2 회귀 테스트 — vendor 모드 라벨링.

검증 대상:
  - core/review_runner.py:_extract_vendor_label()
  - core/review_report.py:ReviewerResult.vendor_mode 필드
  - core/review_runner.py:run_aggregation() single-vendor notice 자동 prepend
"""
from __future__ import annotations

from core.review_runner import _extract_vendor_label, _parse_verdict
from core.review_report import ReviewerResult


# ── _extract_vendor_label ────────────────────────────────────────────────────


def test_critic_role_always_same_vendor():
    """critic role은 출력 내용 무관하게 항상 same-vendor (Anthropic 셀프)."""
    assert _extract_vendor_label("PASS", "critic") == "same-vendor"
    assert _extract_vendor_label("[single-vendor] something", "critic") == "same-vendor"
    assert _extract_vendor_label("multi-provider verified", "critic") == "same-vendor"


def test_cross_role_single_vendor_marker():
    """cross role 출력에 [single-vendor] 마커 발견 → single."""
    raw = "## Tier 3 판정: PASS [single-vendor]\n사유: 외부 프로바이더 0개"
    assert _extract_vendor_label(raw, "cross") == "single"


def test_cross_role_single_vendor_korean_phrase():
    """cross role 출력에 'single-vendor 모드' 한글 표현 → single."""
    raw = "본 변경의 검증은 same-vendor(Anthropic) 단일 시각에 의존합니다.\n single-vendor 모드 통과 간주."
    assert _extract_vendor_label(raw, "cross") == "single"


def test_cross_role_multi_vendor_default():
    """cross role 출력에 single-vendor 마커 없음 → multi (정상 fan-out)."""
    raw = "## Tier 3 판정: PASS\n사유: BLOCK/WARN 기여 finding 0건 (codex_cli 참여)"
    assert _extract_vendor_label(raw, "cross") == "multi"


def test_cross_role_block_with_multi_provider():
    """cross role BLOCK + multi-provider 정상 → multi."""
    raw = "## Tier 3 판정: BLOCK\n사유: ACCEPT★ High 1건 (codex+gemini fan-out)"
    assert _extract_vendor_label(raw, "cross") == "multi"


# ── ReviewerResult.vendor_mode ───────────────────────────────────────────────


def test_reviewer_result_default_vendor_mode():
    """ReviewerResult vendor_mode 기본값은 multi."""
    r = ReviewerResult(provider="claude", role="critic", raw_output="PASS")
    assert r.vendor_mode == "multi"


def test_reviewer_result_vendor_mode_explicit():
    """vendor_mode 명시 설정 가능."""
    r = ReviewerResult(
        provider="claude", role="critic", raw_output="PASS",
        vendor_mode="same-vendor",
    )
    assert r.vendor_mode == "same-vendor"

    r2 = ReviewerResult(
        provider="codex", role="cross", raw_output="PASS [single-vendor]",
        vendor_mode="single",
    )
    assert r2.vendor_mode == "single"


# ── _parse_verdict 회귀 (vendor 라벨 추가가 verdict 파싱을 깨지 않음) ─────────


def test_verdict_parsing_unaffected_by_vendor_label():
    """vendor 라벨 마커가 verdict 파싱에 영향 X."""
    # [single-vendor]는 BLOCK/PASS/WARN 키워드를 포함하지 않음
    raw = "## Tier 3 판정: PASS [single-vendor]\n사유: SKIP 통과"
    assert _parse_verdict(raw) == "PASS"

    raw2 = "## Tier 3 판정: BLOCK\n사유: 외부 프로바이더 인증 만료 (single-vendor 모드 우회)"
    assert _parse_verdict(raw2) == "BLOCK"


# ── run_aggregation single-vendor notice (단위 검증) ────────────────────────


def test_aggregation_notice_text_present_in_module():
    """run_aggregation의 single-vendor notice 텍스트가 코드에 존재.

    실 LLM 호출은 비싸므로 텍스트 존재만 검증 (run_aggregation 자체는 통합 환경에서 검증).
    """
    import inspect
    from core import review_runner

    src = inspect.getsource(review_runner.run_aggregation)
    assert "SINGLE-VENDOR MODE" in src
    assert "single-vendor-validated" in src
    assert "_extract_vendor_label" in src
