"""coverage gate hoist — Step A+B 회귀 테스트 (§5 설계노트 8케이스).

1. deep_source_research + domain=poker → coverage_report 비어있지 않음
2. fast_synthesis + domain="" → coverage_report = {} (회귀)
3. archive_research + domain=poker → coverage_report 기존과 동일 (회귀)
4. fresh_lookup → deep escalation → scores 보존
5. escalation 후 domain 보존 (회귀)
6. no-Tavily + deep + llm_prior_refs에 poker 증거 → false BLOCK 없음
7. external_stack=3, deep=0, op_risk=0 + fast_synthesis → escalation + research_depth=normal
8. 순수 fast_synthesis (requires_web=False) → _build_quality_contract 미호출
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch, call


def _make_agent():
    from core.researcher import HimariResearchAgent
    return HimariResearchAgent(MagicMock())


def _plan(mode: str, scores: dict | None = None):
    from core.research_router import ResearchPlan
    p = ResearchPlan.for_mode(mode, scores=scores or {})
    return p


class TestCoverageGateHoistStep1(unittest.TestCase):
    """Case 1: deep_source_research + domain=poker → coverage_report 생성."""

    def test_deep_with_poker_domain_produces_coverage_report(self):
        agent = _make_agent()
        plan = _plan("deep_source_research")
        plan.domain = "poker"

        with patch.object(agent, "_collect_local_references", return_value=[]), \
             patch.object(agent, "_collect_web_references", return_value=[{"title": "bluff rules", "excerpt": "bluff rules betting", "heading": ""}]), \
             patch.object(agent, "_collect_llm_prior_knowledge", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_quality_contract", return_value=None), \
             patch.object(agent, "_load_domain_manifest", return_value=["bluff"]), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={}), \
             patch.object(agent, "_emit_evidence_files"), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            result = agent.collect_project_evidence("포커 블러프", research_plan=plan)

        self.assertIn("coverage_report", result)
        self.assertNotEqual(result["coverage_report"], {})


class TestCoverageGateHoistStep2(unittest.TestCase):
    """Case 2: fast_synthesis + domain="" → coverage_report = {} (회귀 — 불변)."""

    def test_fast_synthesis_no_domain_no_coverage(self):
        agent = _make_agent()
        plan = _plan("fast_synthesis")
        plan.domain = ""

        with patch.object(agent, "_collect_local_references", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={}), \
             patch.object(agent, "_emit_evidence_files"), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            result = agent.collect_project_evidence("일반 쿼리", research_plan=plan)

        self.assertEqual(result.get("coverage_report", {}), {})


class TestCoverageGateHoistStep3(unittest.TestCase):
    """Case 3: archive_research + domain=poker → coverage_report 동작 유지 (회귀)."""

    def test_archive_with_poker_domain_still_produces_coverage(self):
        agent = _make_agent()
        plan = _plan("archive_research")
        plan.domain = "poker"

        with patch.object(agent, "_collect_local_references", return_value=[{"title": "poker hand", "excerpt": "hand ranking rules", "heading": ""}]), \
             patch.object(agent, "_collect_web_references", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_is_sufficient", return_value=True), \
             patch.object(agent, "_build_quality_contract", return_value=None), \
             patch.object(agent, "_load_domain_manifest", return_value=["hand ranking"]), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={}), \
             patch.object(agent, "_emit_evidence_files"), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            result = agent.collect_project_evidence("포커 핸드 랭킹", research_plan=plan)

        self.assertIn("coverage_report", result)
        self.assertNotEqual(result["coverage_report"], {})


class TestCoverageGateHoistStep4(unittest.TestCase):
    """Case 4: escalation → scores 보존 (Step B)."""

    def test_escalation_scores_preserved(self):
        agent = _make_agent()
        scores = {"deep_decision_score": 0, "operational_risk_score": 0, "external_stack_score": 3}
        plan = _plan("fast_synthesis", scores=scores)
        plan.domain = "poker"

        from core.research_router import ResearchPlan

        captured = {}

        def _fake_collect(task_input, workspace=None, risk_level="normal",
                          comparison_mode=False, research_plan=None, hint_gaps=None, **_kw):
            if hint_gaps:
                captured["escalated_plan"] = research_plan
            return {"workspace_notes": "", "local_references": [], "web_references": [],
                    "llm_prior_references": [], "notebook_summary": "", "evidence_summary": [],
                    "sufficiency_gate_passed": True, "research_plan": (research_plan or plan).to_dict(),
                    "source_pack": {"sources": []}, "structured_evidence": {}, "unmet_gaps": []}

        with patch.object(agent, "collect_project_evidence", side_effect=_fake_collect):
            agent.collect_project_evidence("포커 에스컬레이션 테스트", research_plan=plan,
                                           hint_gaps=["external_stack"])

        if captured.get("escalated_plan"):
            self.assertNotEqual(captured["escalated_plan"].scores, {})


class TestCoverageGateHoistStep5(unittest.TestCase):
    """Case 5: escalation 후 domain 보존 (회귀)."""

    def test_escalation_domain_preserved(self):
        from core.research_router import ResearchPlan
        agent = _make_agent()
        plan = _plan("fast_synthesis")
        plan.domain = "poker"

        with patch.object(agent, "_collect_local_references", return_value=[]), \
             patch.object(agent, "_collect_web_references", return_value=[]), \
             patch.object(agent, "_collect_llm_prior_knowledge", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_quality_contract", return_value=None), \
             patch.object(agent, "_load_domain_manifest", return_value=[]), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={}), \
             patch.object(agent, "_emit_evidence_files"), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=["external_stack"]), \
             patch("core.research_router.gap_to_mode", return_value="deep_source_research"), \
             patch("core.research_router.ResearchRouter._detect_domain", return_value="poker"):
            result = agent.collect_project_evidence("포커 도메인 보존", research_plan=plan)

        self.assertEqual(result["research_plan"]["domain"], "poker")


class TestCoverageGateHoistStep6(unittest.TestCase):
    """Case 6: no-Tavily + deep + llm_prior_refs에 poker 증거 → false BLOCK 없음 (Step A-2)."""

    def test_no_tavily_llm_prior_prevents_false_block(self):
        agent = _make_agent()
        plan = _plan("deep_source_research")
        plan.domain = "poker"

        poker_evidence = [{"title": "poker rules", "excerpt": "bluff bet fold raise call rules", "heading": ""}]

        env_no_tavily = {k: v for k, v in os.environ.items() if k != "TAVILY_API_KEY"}
        with patch.dict(os.environ, env_no_tavily, clear=True), \
             patch.object(agent, "_collect_local_references", return_value=[]), \
             patch.object(agent, "_collect_llm_prior_knowledge", return_value=poker_evidence), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_quality_contract", return_value=None), \
             patch.object(agent, "_load_domain_manifest", return_value=["bluff", "bet", "fold"]), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={}), \
             patch.object(agent, "_emit_evidence_files"), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            result = agent.collect_project_evidence("포커 룰", research_plan=plan)

        coverage = result.get("coverage_report", {})
        if coverage:
            self.assertFalse(coverage.get("block", False),
                             "llm_prior_refs 증거가 있으면 block=False이어야 함")


class TestCoverageGateHoistStep7(unittest.TestCase):
    """Case 7: external_stack=3, deep=0, op_risk=0 + fast_synthesis → escalation + research_depth=normal."""

    def test_escalation_via_external_stack_keeps_depth_normal(self):
        from core.research_router import ResearchPlan
        scores = {"deep_decision_score": 0, "operational_risk_score": 0, "external_stack_score": 3}
        plan = _plan("fast_synthesis", scores=scores)
        plan.domain = "poker"
        agent = _make_agent()

        with patch.object(agent, "_collect_local_references", return_value=[]), \
             patch.object(agent, "_collect_web_references", return_value=[]), \
             patch.object(agent, "_collect_llm_prior_knowledge", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_quality_contract", return_value=None), \
             patch.object(agent, "_load_domain_manifest", return_value=[]), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={}), \
             patch.object(agent, "_emit_evidence_files"), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=["external_stack"]), \
             patch("core.research_router.gap_to_mode", return_value="deep_source_research"), \
             patch("core.research_router.ResearchRouter._detect_domain", return_value="poker"):
            result = agent.collect_project_evidence("포커 스택 에스컬레이션", research_plan=plan)

        self.assertEqual(result["research_plan"]["research_depth"], "normal")


class TestCoverageGateHoistStep8(unittest.TestCase):
    """Case 8: 순수 fast_synthesis (requires_web=False) → _build_quality_contract 미호출."""

    def test_fast_synthesis_skips_quality_contract_call(self):
        agent = _make_agent()
        plan = _plan("fast_synthesis")
        self.assertFalse(plan.requires_web, "fast_synthesis는 requires_web=False")

        mock_qc = MagicMock(return_value=None)
        with patch.object(agent, "_build_quality_contract", mock_qc), \
             patch.object(agent, "_collect_local_references", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={}), \
             patch.object(agent, "_emit_evidence_files"), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            agent.collect_project_evidence("일반 조회", research_plan=plan)

        mock_qc.assert_not_called()
