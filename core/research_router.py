"""Research Router — project research mode classifier.

§0 책임: retrieval_router.py(local 전략 선택)와 다른 책임.
  plan(request) -> ResearchPlan        : 요청을 mode로 분류
  detect_complexity_gaps(...)          : evidence vs complexity obligation 불일치 감지
두 함수는 _compute_signal_scores()를 공유 (signal drift 방지).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# ResearchGap enum — §6.5 (v1.2 기준 9개 잠금, 변경 금지)
# ---------------------------------------------------------------------------

class ResearchGap(str, Enum):
    # fresh-tier (Phase 1a verifier emit)
    NO_EXTERNAL_EVIDENCE = "no_external_evidence"
    FRESHNESS_REQUIRED_MISSING = "freshness_required_missing"
    OFFICIAL_SOURCE_MISSING = "official_source_missing"
    # deep-tier (Phase 1a router detector emit)
    ARCHITECTURE_COVERAGE_LOW = "architecture_coverage_low"
    HIGH_RISK_CAPABILITY_MISSING = "high_risk_capability_missing"
    MULTI_CLIENT_MISSING = "multi_client_or_distributed_system_missing"
    # quality-tier (Phase 1b verifier emit — 사전 등록, 1a에서는 미사용)
    CITATION_VALIDITY_LOW = "citation_validity_low"
    CLAIM_SOURCE_RATIO_LOW = "claim_source_ratio_low"
    SOURCE_PACK_TOO_SHALLOW = "source_pack_too_shallow"


# ---------------------------------------------------------------------------
# gap-to-mode 매핑 — §4.4.2 (router 소유, verifier 아님)
# ---------------------------------------------------------------------------

# fresh-tier gap → fresh_lookup
_FRESH_TIER_GAPS: frozenset[ResearchGap] = frozenset({
    ResearchGap.NO_EXTERNAL_EVIDENCE,
    ResearchGap.FRESHNESS_REQUIRED_MISSING,
    ResearchGap.OFFICIAL_SOURCE_MISSING,
})

# deep-tier gap → deep_source_research
_DEEP_TIER_GAPS: frozenset[ResearchGap] = frozenset({
    ResearchGap.ARCHITECTURE_COVERAGE_LOW,
    ResearchGap.HIGH_RISK_CAPABILITY_MISSING,
    ResearchGap.MULTI_CLIENT_MISSING,
})

# quality-tier → no-op (mode jump 없음, verifier 내부 retry)
_QUALITY_TIER_GAPS: frozenset[ResearchGap] = frozenset({
    ResearchGap.CITATION_VALIDITY_LOW,
    ResearchGap.CLAIM_SOURCE_RATIO_LOW,
    ResearchGap.SOURCE_PACK_TOO_SHALLOW,
})


def gap_to_mode(gaps: list[ResearchGap]) -> str | None:
    """§4.4.3 Precedence: deep > fresh > no-op.

    Returns target mode string, or None (quality-tier no-op / empty).
    """
    gap_set = set(gaps)
    if gap_set & _DEEP_TIER_GAPS:
        return "deep_source_research"
    if gap_set & _FRESH_TIER_GAPS:
        return "fresh_lookup"
    return None  # quality-tier no-op or empty


# ---------------------------------------------------------------------------
# ResearchPlan dataclass — §6.1
# ---------------------------------------------------------------------------

@dataclass
class ResearchPlan:
    mode: str
    secondary_modes: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)
    reason: str = ""
    requires_web: bool = False
    requires_tavily_extract: bool = False
    requires_notebooklm: bool = False
    requires_deep_source_pack: bool = False
    risk_level: str = "normal"
    # A5: Quality Gate 3종 플래그
    requires_research: bool = False      # deep_source_research / live_project_analysis 또는 external_stack_score >= 2
    domain: str = ""                     # "" | "poker" | <future>
    research_depth: str = "shallow"      # shallow | normal | deep

    @classmethod
    def for_mode(
        cls,
        mode: str,
        secondary_modes: list[str] | None = None,
        scores: dict[str, int] | None = None,
    ) -> "ResearchPlan":
        """escalation 후 mode 변경 시 모든 파생 필드를 atomic하게 재계산."""
        secondary = secondary_modes or []
        requires_web = (
            mode in ("fresh_lookup", "deep_source_research", "live_project_analysis")
            or "fresh_lookup" in secondary
        )
        # A5: escalation 시에도 requires_research/research_depth 재계산
        _scores = scores or {}
        requires_research = (
            mode in ("deep_source_research", "live_project_analysis")
            or _scores.get("external_stack_score", 0) >= 2
        )
        research_depth = (
            "deep" if requires_research and _scores.get("operational_risk_score", 0) >= 3
            else "normal" if requires_research
            else "shallow"
        )
        return cls(
            mode=mode,
            secondary_modes=secondary,
            scores=_scores,
            requires_web=requires_web,
            requires_tavily_extract=mode in ("fresh_lookup", "deep_source_research"),
            requires_notebooklm=mode in ("archive_research", "deep_source_research"),
            requires_deep_source_pack=mode == "deep_source_research",
            risk_level="high" if mode in ("deep_source_research", "live_project_analysis") else "normal",
            requires_research=requires_research,
            research_depth=research_depth,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "secondary_modes": self.secondary_modes,
            "scores": self.scores,
            "reason": self.reason,
            "requires_web": self.requires_web,
            "requires_tavily_extract": self.requires_tavily_extract,
            "requires_notebooklm": self.requires_notebooklm,
            "requires_deep_source_pack": self.requires_deep_source_pack,
            "risk_level": self.risk_level,
            "requires_research": self.requires_research,
            "domain": self.domain,
            "research_depth": self.research_depth,
        }


# ---------------------------------------------------------------------------
# Signal keyword sets — §4.2 (한/영 혼합, v1.3 보강)
# ---------------------------------------------------------------------------

_FRESHNESS_TOKENS: frozenset[str] = frozenset({
    "latest", "current", "2026", "release", "version", "price", "security",
    "최신", "최근", "버전", "릴리스", "가격", "보안", "매주", "회차",
})

_EXTERNAL_STACK_TOKENS: frozenset[str] = frozenset({
    "websocket", "sdk", "api", "framework", "redis", "deployment",
    "browser", "mobile", "server", "client",
    "네트워크", "멀티플레이어", "서버", "클라이언트", "모바일", "웹앱", "풀네트워크",
})

_OPERATIONAL_RISK_TOKENS: frozenset[str] = frozenset({
    "realtime", "multiplayer", "network", "scheduler", "payment", "auth",
    "scaling", "migration", "concurrent",
    "실시간", "결제", "인증", "멀티플레이어", "멀티유저", "동시접속", "동시 접속",
    "다인용", "풀네트워크", "스케줄러",
})

_DATA_PIPELINE_TOKENS: frozenset[str] = frozenset({
    "collection", "aggregate", "statistics", "analytics", "periodic",
    "database", "recommendation", "pattern",
    "수집", "누적", "통계", "분석", "주기적", "업데이트", "데이터베이스",
    "추천", "패턴", "회차",
})

_LIVE_PROJECT_TOKENS: frozenset[str] = frozenset({
    "refactor", "regression", "impact", "maintenance",
    "현재 프로젝트", "유지보수", "리팩터링", "영향 범위", "회귀 테스트",
})

_DEEP_DECISION_TOKENS: frozenset[str] = frozenset({
    "compare", "trade-off", "tradeoff", "architecture", "decision", "high-risk",
    "비교", "트레이드오프", "아키텍처", "기술스택 선택", "고위험 결정", "공신력", "권위 있는",
})

_ARCHIVE_TOKENS: frozenset[str] = frozenset({
    "archive", "my notes", "prior design", "company doc",
    "기존 자료", "내 노트북", "과거 설계", "회사 문서",
})


def _count_matches(text_lower: str, token_set: frozenset[str]) -> int:
    """Boolean OR 매칭 — §4.2 토큰화 규칙."""
    return sum(1 for tok in token_set if tok in text_lower)


# ---------------------------------------------------------------------------
# ResearchRouter
# ---------------------------------------------------------------------------

class ResearchRouter:
    """Project research mode classifier.

    두 public API:
      plan(request) -> ResearchPlan
      detect_complexity_gaps(request, evidence, final_mode) -> list[ResearchGap]
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, request: str) -> ResearchPlan:
        """§4.2.1 알고리즘으로 request → ResearchPlan."""
        scores = self._compute_signal_scores(request)
        result = self._select_mode(scores)
        result.domain = self._detect_domain(request)  # A5: request 텍스트에서 도메인 감지
        return result

    def detect_complexity_gaps(
        self,
        request: str,
        evidence: dict[str, Any],
        final_mode: str,
    ) -> list[ResearchGap]:
        """§4.4.5 detector — evidence vs complexity obligation.

        Phase 1a: deep-tier gap만 emit (quality-tier는 Phase 1b verifier 담당).
        """
        scores = self._compute_signal_scores(request)
        gaps: list[ResearchGap] = []

        # §4.4.4 임계 OR 통합
        deep_signal = (
            scores["operational_risk_score"] >= 3
            or scores["deep_decision_score"] >= 2
            or scores["external_stack_score"] >= 3
        )
        is_pre_deep = final_mode in ("fast_synthesis", "fresh_lookup")

        # §4.4.4 obligation check: web_references가 없으면 source_pack 미충족 (Phase 1a proxy)
        web_obligation_unmet = not evidence.get("web_references")
        if deep_signal and is_pre_deep and web_obligation_unmet:
            # §4.4.2 deep-tier gap 두 종 동시 emit → deep escalation
            gaps.append(ResearchGap.MULTI_CLIENT_MISSING)
            gaps.append(ResearchGap.HIGH_RISK_CAPABILITY_MISSING)

        return gaps

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    # A5: 포커 도메인 토큰셋 (D4 결정)
    _POKER_TOKENS: frozenset[str] = frozenset({
        "포커", "poker", "hold'em", "holdem", "blind", "blinds", "all-in",
        "allin", "flop", "turn", "river", "ante", "showdown",
    })

    def _detect_domain(self, request: str) -> str:
        """A5: 요청 텍스트에서 도메인을 감지. 현재 포커만 지원."""
        text = (request or "").lower()
        if any(tok in text for tok in self._POKER_TOKENS):
            return "poker"
        return ""

    def _compute_signal_scores(self, request: str) -> dict[str, int]:
        """§4.2 7개 신호 점수화. plan()과 detect_complexity_gaps() 공유."""
        text = request.lower()
        return {
            "freshness_score": _count_matches(text, _FRESHNESS_TOKENS),
            "external_stack_score": _count_matches(text, _EXTERNAL_STACK_TOKENS),
            "operational_risk_score": _count_matches(text, _OPERATIONAL_RISK_TOKENS),
            "data_pipeline_score": _count_matches(text, _DATA_PIPELINE_TOKENS),
            "live_project_score": _count_matches(text, _LIVE_PROJECT_TOKENS),
            "deep_decision_score": _count_matches(text, _DEEP_DECISION_TOKENS),
            "archive_score": _count_matches(text, _ARCHIVE_TOKENS),
        }

    def _select_mode(self, scores: dict[str, int]) -> ResearchPlan:
        """§4.2.1 precedence 결정 규칙. 임계 변경 금지 — fixture calibration만."""
        # 1) Primary mode (precedence 순, 첫 매칭에서 종료)
        if scores["archive_score"] >= 2:
            primary = "archive_research"
        elif scores["live_project_score"] >= 2:
            primary = "live_project_analysis"
        elif scores["deep_decision_score"] >= 2 or scores["operational_risk_score"] >= 3:
            primary = "deep_source_research"
        elif scores["freshness_score"] >= 2:
            primary = "fresh_lookup"
        else:
            primary = "fast_synthesis"

        # 2) Secondary modes
        secondary: list[str] = []
        if scores["data_pipeline_score"] >= 1 and primary != "data_pipeline":
            secondary.append("data_pipeline")
        if scores["external_stack_score"] >= 2 and primary == "fast_synthesis":
            secondary.append("fresh_lookup")
        # skill_evolution: capability gap 존재 시 후속 단계에서 결정 (§4.1)

        # 3) flags
        requires_web = (
            primary in ("fresh_lookup", "deep_source_research", "live_project_analysis")
            or "fresh_lookup" in secondary
        )
        requires_notebooklm = primary in ("archive_research", "deep_source_research")
        risk_level = "high" if primary in ("deep_source_research", "live_project_analysis") else "normal"

        # A5: Quality Gate 3종 derivation
        requires_research = (
            primary in ("deep_source_research", "live_project_analysis")
            or scores.get("external_stack_score", 0) >= 2
        )
        research_depth = (
            "deep" if requires_research and scores.get("operational_risk_score", 0) >= 3
            else "normal" if requires_research
            else "shallow"
        )

        return ResearchPlan(
            mode=primary,
            secondary_modes=secondary,
            scores=scores,
            requires_web=requires_web,
            requires_tavily_extract=primary in ("fresh_lookup", "deep_source_research"),
            requires_notebooklm=requires_notebooklm,
            requires_deep_source_pack=primary == "deep_source_research",
            risk_level=risk_level,
            requires_research=requires_research,
            domain="",  # _detect_domain은 plan()에서 별도 호출 — _select_mode는 scores만 봄
            research_depth=research_depth,
        )


__all__ = ["ResearchRouter", "ResearchPlan", "ResearchGap", "gap_to_mode"]
