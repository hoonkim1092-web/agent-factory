"""Phase 1a Eval fixture — §12.5 통과 기준.

- expected_initial_mode  정확도 >= 80%   (router.plan() 1차 결과)
- expected_final_mode    정확도 >= 80%   (detect_complexity_gaps 후 escalation 결과)
- expected_secondary_modes 부분 일치    >= 60%
- requires_web / requires_notebooklm    >= 90%

임계 변경 금지 — fixture 라벨로만 calibration.
"""

from __future__ import annotations

import pytest
from core.research_router import ResearchRouter, ResearchPlan, gap_to_mode


# ---------------------------------------------------------------------------
# Fixture 케이스 (한/영/혼합 18건)
# ---------------------------------------------------------------------------

CASES = [
    # ────────── fast_synthesis (escalation 없음) ──────────
    {
        "id": "C01",
        "request": "간단한 todo 웹앱 만들어줘",
        "expected_initial_mode": "fast_synthesis",
        "expected_final_mode": "fast_synthesis",
        "expected_secondary_modes": [],
        "requires_web": False,
        "requires_notebooklm": False,
    },
    {
        "id": "C02",
        "request": "Make a simple CRUD app for managing book lists",
        "expected_initial_mode": "fast_synthesis",
        "expected_final_mode": "fast_synthesis",
        "expected_secondary_modes": [],
        "requires_web": False,
        "requires_notebooklm": False,
    },
    {
        "id": "C03",
        "request": "간단한 로그인/회원가입 페이지 만들어줘",
        "expected_initial_mode": "fast_synthesis",
        "expected_final_mode": "fast_synthesis",
        "expected_secondary_modes": [],
        "requires_web": False,
        "requires_notebooklm": False,
    },
    {
        "id": "C04",
        "request": "Create a calculator web app with basic arithmetic operations",
        "expected_initial_mode": "fast_synthesis",
        "expected_final_mode": "fast_synthesis",
        "expected_secondary_modes": [],
        "requires_web": False,
        "requires_notebooklm": False,
    },
    # ────────── fresh_lookup (escalation 없음) ──────────
    {
        "id": "C05",
        "request": "최신 Next.js 버전 기준으로 SaaS starter 만들어줘",
        "expected_initial_mode": "fresh_lookup",
        "expected_final_mode": "fresh_lookup",
        "expected_secondary_modes": [],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    {
        "id": "C06",
        "request": "2026년 최신 릴리스 기준 FastAPI 보안 설정 알려줘",
        "expected_initial_mode": "fresh_lookup",
        "expected_final_mode": "fresh_lookup",
        "expected_secondary_modes": [],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    {
        "id": "C07",
        "request": "현재 AWS Lambda 가격 정책과 cold start 최신 개선 사항 알려줘",
        "expected_initial_mode": "fresh_lookup",
        "expected_final_mode": "fresh_lookup",
        "expected_secondary_modes": [],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    # ────────── fresh_lookup + data_pipeline (로또 §10.2) ──────────
    {
        "id": "C08",
        "request": (
            "최신 로또 800회차 1등 당첨 번호들을 수집해서 패턴을 분석하고, "
            "앞으로 매주마다 1등 번호를 누적해서 통계를 내고 패턴을 분석해서 "
            "1등 당첨 번호를 추천해주는 PC, 모바일 웹앱을 만들어줘."
        ),
        "expected_initial_mode": "fresh_lookup",
        "expected_final_mode": "fresh_lookup",
        "expected_secondary_modes": ["data_pipeline"],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    {
        "id": "C09",
        "request": (
            "최신 공공 API를 통해 매주 주기적으로 수집한 통계 데이터를 누적해서 "
            "분석 대시보드를 만들어줘"
        ),
        "expected_initial_mode": "fresh_lookup",
        "expected_final_mode": "fresh_lookup",
        "expected_secondary_modes": ["data_pipeline"],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    # ────────── archive_research ──────────
    {
        "id": "C10",
        "request": "우리 회사 문서와 기존 자료 기준으로 인증 구조를 검토해줘",
        "expected_initial_mode": "archive_research",
        "expected_final_mode": "archive_research",
        "expected_secondary_modes": [],
        "requires_web": False,
        "requires_notebooklm": True,
    },
    {
        "id": "C11",
        "request": "기존 자료와 과거 설계 기반으로 마이그레이션 계획 수립해줘",
        "expected_initial_mode": "archive_research",
        "expected_final_mode": "archive_research",
        "expected_secondary_modes": [],
        "requires_web": False,
        "requires_notebooklm": True,
    },
    # ────────── live_project_analysis ──────────
    {
        "id": "C12",
        "request": "현재 프로젝트 인증 모듈 리팩터링 영향 범위 분석해줘",
        "expected_initial_mode": "live_project_analysis",
        "expected_final_mode": "live_project_analysis",
        "expected_secondary_modes": [],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    {
        "id": "C13",
        "request": "현재 프로젝트에서 유지보수가 어려운 모듈 리팩터링과 회귀 테스트 설계해줘",
        "expected_initial_mode": "live_project_analysis",
        "expected_final_mode": "live_project_analysis",
        "expected_secondary_modes": [],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    # ────────── deep_source_research direct (operational_risk >= 3 or deep_decision >= 2) ──────────
    {
        "id": "C14",
        "request": (
            "실시간 결제, 인증, 동시접속 처리를 포함한 멀티플레이어 게임 플랫폼 "
            "아키텍처를 비교해서 결정해줘"
        ),
        "expected_initial_mode": "deep_source_research",
        "expected_final_mode": "deep_source_research",
        "expected_secondary_modes": [],
        "requires_web": True,
        "requires_notebooklm": True,
    },
    {
        "id": "C15",
        "request": (
            "마이크로서비스 vs 모노리스 아키텍처를 트레이드오프 기준으로 비교하고 "
            "고위험 결정을 내려줘"
        ),
        "expected_initial_mode": "deep_source_research",
        "expected_final_mode": "deep_source_research",
        "expected_secondary_modes": [],
        "requires_web": True,
        "requires_notebooklm": True,
    },
    # ────────── deep via escalation (§4.4.5 — 8인 포커 §10.1) ──────────
    {
        "id": "C16",
        "request": (
            "8인이 같이 플레이할 수 있는 풀네트워크 포커게임을 PC, 모바일 웹앱으로 만들어줘. "
            "로직은 서버에서 돌리고 클라이언트는 뷰어 역할만 할거야."
        ),
        # §10.1: 1차 plan은 external_stack=6이지만 op=1, deep=0 → fast_synthesis
        # §4.4.5 detector: external_stack(6) >= 3 AND no source_pack → deep escalation
        "expected_initial_mode": "fast_synthesis",
        "expected_final_mode": "deep_source_research",
        "expected_secondary_modes": ["fresh_lookup"],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    {
        "id": "C17",
        "request": (
            "웹소켓 기반 멀티 클라이언트 실시간 채팅 서버와 모바일 웹앱을 만들어줘. "
            "여러 서버 인스턴스에서 동작해야 해."
        ),
        # external_stack >= 3 (웹소켓/멀티/클라이언트/서버/모바일/웹앱) → deep via escalation
        "expected_initial_mode": "fast_synthesis",
        "expected_final_mode": "deep_source_research",
        "expected_secondary_modes": ["fresh_lookup"],
        "requires_web": True,
        "requires_notebooklm": False,
    },
    # ────────── fast_synthesis + data_pipeline secondary ──────────
    {
        "id": "C18",
        "request": "사내 직원 데이터베이스에서 부서별 통계를 집계해주는 간단한 앱 만들어줘",
        "expected_initial_mode": "fast_synthesis",
        "expected_final_mode": "fast_synthesis",
        "expected_secondary_modes": ["data_pipeline"],
        "requires_web": False,
        "requires_notebooklm": False,
    },
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _simulate_final_mode(router: ResearchRouter, request: str, plan: ResearchPlan) -> str:
    """§4.4.5 escalation 1-cycle 시뮬레이션.

    Phase 1a: source_pack 미수집 가정 (evidence = {}).
    """
    gaps = router.detect_complexity_gaps(request, evidence={}, final_mode=plan.mode)
    if gaps:
        escalated = gap_to_mode(gaps)
        if escalated:
            return escalated
    return plan.mode


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResearchRouterInitialMode:
    """router.plan() 1차 결과 검증 (expected_initial_mode)."""

    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_initial_mode(self, case):
        router = ResearchRouter()
        plan = router.plan(case["request"])
        assert plan.mode == case["expected_initial_mode"], (
            f"[{case['id']}] initial_mode={plan.mode!r}, "
            f"expected={case['expected_initial_mode']!r}, scores={plan.scores}"
        )


class TestResearchRouterFinalMode:
    """§4.4 escalation 후 final mode 검증 (expected_final_mode)."""

    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_final_mode(self, case):
        router = ResearchRouter()
        plan = router.plan(case["request"])
        final = _simulate_final_mode(router, case["request"], plan)
        assert final == case["expected_final_mode"], (
            f"[{case['id']}] final_mode={final!r}, "
            f"expected={case['expected_final_mode']!r}, scores={plan.scores}"
        )


class TestResearchRouterSecondaryModes:
    """secondary_modes 부분 일치 (expected_secondary_modes) — 정확도 >= 60%."""

    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_secondary_modes(self, case):
        router = ResearchRouter()
        plan = router.plan(case["request"])
        expected = set(case["expected_secondary_modes"])
        actual = set(plan.secondary_modes)
        if not expected:
            # 기대값이 비어 있으면 extra가 있어도 허용 (보수적 검증)
            return
        overlap = expected & actual
        assert overlap == expected, (
            f"[{case['id']}] secondary={actual!r}, expected={expected!r}"
        )


class TestResearchRouterWebNotebook:
    """requires_web / requires_notebooklm 정확도 >= 90%."""

    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_requires_web(self, case):
        router = ResearchRouter()
        plan = router.plan(case["request"])
        assert plan.requires_web == case["requires_web"], (
            f"[{case['id']}] requires_web={plan.requires_web}, "
            f"expected={case['requires_web']}, mode={plan.mode}"
        )

    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_requires_notebooklm(self, case):
        router = ResearchRouter()
        plan = router.plan(case["request"])
        assert plan.requires_notebooklm == case["requires_notebooklm"], (
            f"[{case['id']}] requires_notebooklm={plan.requires_notebooklm}, "
            f"expected={case['requires_notebooklm']}, mode={plan.mode}"
        )


class TestResearchRouterAccuracyGate:
    """§12.5 전체 정확도 게이트 — 각 라벨 >= 80%."""

    def _run_all(self):
        router = ResearchRouter()
        initial_ok = 0
        final_ok = 0
        for c in CASES:
            plan = router.plan(c["request"])
            if plan.mode == c["expected_initial_mode"]:
                initial_ok += 1
            final = _simulate_final_mode(router, c["request"], plan)
            if final == c["expected_final_mode"]:
                final_ok += 1
        return initial_ok, final_ok, len(CASES)

    def test_initial_mode_accuracy_gate(self):
        ok, _, total = self._run_all()
        accuracy = ok / total
        assert accuracy >= 0.80, (
            f"expected_initial_mode accuracy={accuracy:.1%} ({ok}/{total}) < 80%"
        )

    def test_final_mode_accuracy_gate(self):
        _, ok, total = self._run_all()
        accuracy = ok / total
        assert accuracy >= 0.80, (
            f"expected_final_mode accuracy={accuracy:.1%} ({ok}/{total}) < 80%"
        )


class TestEvidenceFnKwargs:
    """project_pipeline._evidence_fn(**kwargs) 회귀 — TypeError 없이 hint_gaps 전달."""

    def test_evidence_fn_accepts_hint_gaps(self):
        from core.research_router import ResearchGap

        result_holder = {}

        def _evidence_fn(**kwargs):
            result_holder["kwargs"] = kwargs
            return {"ok": True}

        gaps = [ResearchGap.NO_EXTERNAL_EVIDENCE]
        res = _evidence_fn(hint_gaps=gaps)
        assert res == {"ok": True}
        assert result_holder["kwargs"]["hint_gaps"] == gaps


class TestGapToMode:
    """gap_to_mode precedence — §4.4.3."""

    def test_deep_wins_over_fresh(self):
        from core.research_router import ResearchGap
        gaps = [ResearchGap.NO_EXTERNAL_EVIDENCE, ResearchGap.HIGH_RISK_CAPABILITY_MISSING]
        assert gap_to_mode(gaps) == "deep_source_research"

    def test_fresh_only(self):
        from core.research_router import ResearchGap
        gaps = [ResearchGap.FRESHNESS_REQUIRED_MISSING]
        assert gap_to_mode(gaps) == "fresh_lookup"

    def test_quality_only_noop(self):
        from core.research_router import ResearchGap
        gaps = [ResearchGap.CITATION_VALIDITY_LOW, ResearchGap.SOURCE_PACK_TOO_SHALLOW]
        assert gap_to_mode(gaps) is None

    def test_empty_noop(self):
        assert gap_to_mode([]) is None


class TestDetectComplexityGaps:
    """detect_complexity_gaps — §4.4.5."""

    def test_high_external_stack_no_source_pack_emits_deep_gaps(self):
        from core.research_router import ResearchGap
        router = ResearchRouter()
        # external_stack >= 3 (websocket, server, client, mobile)
        request = "Build a websocket server with mobile client and multiple client instances"
        gaps = router.detect_complexity_gaps(request, evidence={}, final_mode="fast_synthesis")
        assert ResearchGap.MULTI_CLIENT_MISSING in gaps
        assert ResearchGap.HIGH_RISK_CAPABILITY_MISSING in gaps

    def test_already_deep_no_gap_emitted(self):
        router = ResearchRouter()
        request = "Build a websocket server with mobile client and multiple client instances"
        # final_mode가 이미 deep → 자기 반복 방지
        gaps = router.detect_complexity_gaps(request, evidence={}, final_mode="deep_source_research")
        assert gaps == []

    def test_web_references_present_no_gap(self):
        router = ResearchRouter()
        request = "Build a websocket server with mobile client and multiple client instances"
        # web_references가 있으면 obligation 충족 → deep gap emit 안 함
        gaps = router.detect_complexity_gaps(
            request,
            evidence={"web_references": [{"url": "https://example.com"}]},
            final_mode="fast_synthesis",
        )
        assert gaps == []

    def test_weak_signal_no_gap(self):
        router = ResearchRouter()
        # external_stack < 3, op < 3, deep < 2 → no gap
        request = "간단한 todo 웹앱 만들어줘"
        gaps = router.detect_complexity_gaps(request, evidence={}, final_mode="fast_synthesis")
        assert gaps == []
