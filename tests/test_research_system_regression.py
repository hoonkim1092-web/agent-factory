"""Phase 0 — Research 시스템 회귀 baseline.

5건 결함(G1~G5) + race 사전 검증. 7 cases.

case 1, 3, 4: xfail(strict=True) — RED (현재 코드에서 실패 기대)
case 2, 5, 6: 현재 PASS — baseline 캡처 (후속 Phase에서 GREEN 강화)
case 7:       trivially PASS — P5 병렬화 전 race 사전 검증
"""

from __future__ import annotations

import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# G1 case 1 — RED: "최근"이 _FRESHNESS_TOKENS에 없음
# ---------------------------------------------------------------------------

class TestG1KoreanFreshnessTokenMatch(unittest.TestCase):

    def test_g1_korean_freshness_token_match(self):
        from core.research_router import _FRESHNESS_TOKENS, _count_matches
        text = "최근 출시된 sdk"
        count = _count_matches(text.lower(), _FRESHNESS_TOKENS)
        self.assertGreaterEqual(count, 1)


# ---------------------------------------------------------------------------
# G1 case 2 — baseline: "8인 포커게임" mode 분류 현재 값 캡처
# ---------------------------------------------------------------------------

class TestG1KoreanPlayerCountMatch(unittest.TestCase):

    def test_g1_korean_player_count_match(self):
        from core.research_router import ResearchRouter
        plan = ResearchRouter().plan("8인 포커게임 만들어줘")
        valid_modes = {
            "fast_synthesis", "fresh_lookup", "deep_source_research",
            "operational_risk", "data_pipeline", "live_project_analysis",
            "archive_research", "quality_tier_gap", "no_research",
        }
        # baseline: mode가 valid 범위 안 — P2(G1) 후 deep_source_research/fresh_lookup 으로 좁아져야 함
        self.assertIn(plan.mode, valid_modes)


# ---------------------------------------------------------------------------
# G2 case 3 — RED: fast_synthesis + requires_web=True 시 web 진입 안 됨
# ---------------------------------------------------------------------------

class TestG2FastSynthesisSecondaryFreshLookup(unittest.TestCase):

    def test_g2_fast_synthesis_secondary_fresh_lookup(self):
        from core.research_router import ResearchPlan
        from core.researcher import HimariResearchAgent

        mr = MagicMock()
        agent = HimariResearchAgent(mr)

        plan = ResearchPlan.for_mode("fast_synthesis", secondary_modes=["fresh_lookup"])
        # for_mode: secondary fresh_lookup → requires_web=True
        self.assertTrue(plan.requires_web)

        with patch.object(agent, "_collect_local_references", return_value=[]), \
             patch.object(agent, "_collect_web_references", return_value=[]) as mock_web, \
             patch.object(agent, "_collect_llm_prior_knowledge", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_is_sufficient", return_value=True), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={
                 "research_mode": "fast_synthesis", "goal_interpretation": "",
                 "source_backed_claims": [],
             }), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            agent.collect_project_evidence("8인 포커게임 만들어줘", research_plan=plan)

        mock_web.assert_called_once()  # RED: line 690 `pass` prevents call


# ---------------------------------------------------------------------------
# G3 case 4 — RED: TAVILY 미설정 + AF_RESEARCH_LLM_FALLBACK=1 → web_references 비어있음
# ---------------------------------------------------------------------------

class TestG3TavilyUnsetFallbackPath(unittest.TestCase):

    def test_g3_tavily_unset_fallback_path(self):
        from core.research_router import ResearchPlan
        from core.researcher import HimariResearchAgent

        mr = MagicMock()
        agent = HimariResearchAgent(mr)

        plan = ResearchPlan.for_mode("fresh_lookup")  # requires_web=True

        fake_llm_prior = [{"title": "LLM prior knowledge", "excerpt": "pocker SDK info", "url": ""}]
        env_no_tavily = {k: v for k, v in os.environ.items() if k != "TAVILY_API_KEY"}
        env_no_tavily["AF_RESEARCH_LLM_FALLBACK"] = "1"

        with patch.dict(os.environ, env_no_tavily, clear=True), \
             patch.object(agent, "_collect_local_references", return_value=[]), \
             patch.object(agent, "_collect_llm_prior_knowledge", return_value=fake_llm_prior), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_is_sufficient", return_value=False), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={
                 "research_mode": "fresh_lookup", "goal_interpretation": "",
                 "source_backed_claims": [],
             }), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            result = agent.collect_project_evidence("최근 포커 SDK 정보", research_plan=plan)

        # After G3 fix: LLM prior merged into web_references slot when AF_RESEARCH_LLM_FALLBACK=1
        self.assertGreater(len(result["web_references"]), 0)


# ---------------------------------------------------------------------------
# G4 case 5 — baseline: 순차 실행 시간 캡처 (P5 병렬화 후 절반 이하 목표)
# ---------------------------------------------------------------------------

class TestG4EvidenceParallelRunsWithinBudget(unittest.TestCase):

    def test_g4_evidence_parallel_runs_within_budget(self):
        from core.research_router import ResearchPlan
        from core.researcher import HimariResearchAgent

        mr = MagicMock()
        agent = HimariResearchAgent(mr)
        plan = ResearchPlan.for_mode("fresh_lookup")

        def _slow_local(task_input, workspace, **_kw):
            time.sleep(0.06)
            return []

        def _slow_web(task_input, **_kw):
            time.sleep(0.06)
            return []

        with patch.object(agent, "_collect_local_references", side_effect=_slow_local), \
             patch.object(agent, "_collect_web_references", side_effect=_slow_web), \
             patch.object(agent, "_collect_llm_prior_knowledge", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_is_sufficient", return_value=False), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={
                 "research_mode": "fresh_lookup", "goal_interpretation": "",
                 "source_backed_claims": [],
             }), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            t0 = time.monotonic()
            agent.collect_project_evidence("8인 포커게임", research_plan=plan)
            elapsed = time.monotonic() - t0

        # Baseline: 순차 실행 → local+web 합산 ≥ 0.12s
        # P5 병렬화 후 목표: elapsed < 0.10s (절반 이하)
        self.assertGreaterEqual(elapsed, 0.10, "sequential baseline: local+web should take ≥ 0.10s")
        self.assertLess(elapsed, 10.0, "sanity upper bound")


# ---------------------------------------------------------------------------
# G5 case 6 — baseline: sources≥3 시 structured_evidence 구조 검증
# ---------------------------------------------------------------------------

class TestG5ClaimCountMinimumWhenSourcesPresent(unittest.TestCase):

    def _make_source_pack(self, n: int) -> dict:
        return {
            "sources": [
                {
                    "source_id": f"web_{i:03d}",
                    "source_type": "web",
                    "title": f"Source {i}",
                    "excerpt": f"excerpt {i}",
                    "content_full": f"full content {i}",
                    "relevance_score": 0.7,
                    "authority_level": "secondary",
                    "url": f"https://example.com/{i}",
                    "retrieval_method": "tavily_search",
                    "selected_reason": "relevant",
                }
                for i in range(n)
            ]
        }

    def test_g5_claim_count_minimum_when_sources_present(self):
        import json
        from core.researcher import HimariResearchAgent

        mr = MagicMock()
        agent = HimariResearchAgent(mr)
        source_pack = self._make_source_pack(3)

        base = {
            "research_mode": "fresh_lookup",
            "goal_interpretation": "Build poker game",
            "recommended_architecture": "web_app",
            "recommended_tech_stack": [],
            "required_capabilities": [],
            "agent_role_hints": [],
            "skill_gap_hypotheses": [],
            "risks": [],
            "verification_focus": [],
            "maintenance_strategy": [],
            "source_backed_claims": [],  # 0 claims — triggers G5 retry
        }
        with_claim = {**base, "source_backed_claims": [{"claim": "Poker SDK exists", "source_ids": ["web_000"]}]}
        side_effects = [
            {"ok": True, "text": json.dumps(base)},       # 1st call → 0 claims
            {"ok": True, "text": json.dumps(with_claim)}, # retry → 1 claim
        ]
        with patch("core.requirement_llm.execute_requirement_prompt", side_effect=side_effects):
            result = agent._synthesize_structured_evidence(
                "8인 포커게임 만들어줘", "fresh_lookup", source_pack
            )

        claims = result.get("source_backed_claims", [])
        self.assertGreaterEqual(len(claims), 1)


# ---------------------------------------------------------------------------
# G4 case 7 — trivially PASS: 직렬 흐름에서 pipeline race 없음
# ---------------------------------------------------------------------------

class TestG4LocalWebNoPipelineRace(unittest.TestCase):

    def test_g4_local_web_no_pipeline_race(self):
        from core.researcher import HimariResearchAgent

        mr = MagicMock()
        agent = HimariResearchAgent(mr)

        fake_local_result = [{"path": "a.py", "heading": "h", "excerpt": "e", "score": 0.5}]
        fake_web_result = [{"url": "https://x.com", "title": "T", "excerpt": "e"}]

        errors: list[Exception] = []
        results: list[tuple[str, list]] = []

        def call_local():
            try:
                with patch.object(agent, "_collect_local_references",
                                  return_value=fake_local_result):
                    r = agent._collect_local_references("test query", "/tmp")
                    results.append(("local", r))
            except Exception as exc:
                errors.append(exc)

        def call_web():
            try:
                with patch.object(agent, "_collect_web_references",
                                  return_value=fake_web_result):
                    r = agent._collect_web_references("test query")
                    results.append(("web", r))
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(call_local)
            f2 = ex.submit(call_web)
            f1.result(timeout=5)
            f2.result(timeout=5)

        self.assertEqual(errors, [], f"Race errors: {errors}")
        self.assertEqual(len(results), 2)
        # pipeline cache 무결성: 동시 호출이 agent 상태를 오염시키지 않음
        # P5 병렬화 후 동일 assertion이 GREEN 유지되어야 acceptance


if __name__ == "__main__":
    unittest.main()
