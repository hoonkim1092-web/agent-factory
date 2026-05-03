"""Phase 1b 단위 테스트.

A. web_search.py — excerpt + content_full 분리
B. researcher._build_source_pack() — §6.2 source_pack 구조
C. researcher._synthesize_structured_evidence() — LLM normalizer mock
D. research_verifier — deterministic 4-metric (§9.2)
E. quality-tier gap emission (no-op mode jump)
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# A. web_search — excerpt + content_full
# ---------------------------------------------------------------------------

class TestWebSearchFieldSplit(unittest.TestCase):

    def _make_tavily_response(self, content: str) -> dict:
        return {
            "results": [
                {
                    "url": "https://example.com",
                    "title": "Test Page",
                    "content": content,
                    "score": 0.9,
                }
            ],
            "answer": "",
        }

    def _call_tavily_search(self, content: str, query: str = "test"):
        import urllib.request
        import urllib.parse

        body_bytes = json.dumps(self._make_tavily_response(content)).encode()

        class FakeResp:
            def read(self):
                return body_bytes
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass

        with patch("urllib.request.urlopen", return_value=FakeResp()), \
             patch("os.getenv", return_value="fake_key"):
            from core.web_search import tavily_search
            return tavily_search(query, max_results=1)

    def test_excerpt_is_first_200_chars(self):
        long = "x" * 500
        results = self._call_tavily_search(long)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["excerpt"], "x" * 200)

    def test_content_full_is_untruncated(self):
        long = "x" * 500
        results = self._call_tavily_search(long)
        self.assertEqual(results[0]["content_full"], long)

    def test_short_content_excerpt_equals_full(self):
        short = "hello world"
        results = self._call_tavily_search(short)
        self.assertEqual(results[0]["excerpt"], short)
        self.assertEqual(results[0]["content_full"], short)

    def test_no_legacy_content_key(self):
        results = self._call_tavily_search("sample")
        self.assertNotIn("content", results[0])


# ---------------------------------------------------------------------------
# B. researcher._build_source_pack — §6.2
# ---------------------------------------------------------------------------

class TestBuildSourcePack(unittest.TestCase):

    def _make_agent(self):
        mr = MagicMock()
        # Minimal stub — avoid heavy imports
        import importlib
        spec = importlib.util.find_spec("core.researcher")
        self.assertIsNotNone(spec, "core.researcher must be importable")
        from core.researcher import HimariResearchAgent
        return HimariResearchAgent(mr)

    def setUp(self):
        self.agent = self._make_agent()

    def test_web_ref_becomes_source(self):
        web = [{"url": "https://x.com", "title": "X", "excerpt": "e", "content_full": "full", "score": 0.8}]
        sp = self.agent._build_source_pack(web, [], [])
        self.assertEqual(len(sp["sources"]), 1)
        src = sp["sources"][0]
        self.assertEqual(src["source_type"], "web")
        self.assertEqual(src["source_id"], "web_001")
        self.assertEqual(src["content_full"], "full")

    def test_local_ref_authority_primary(self):
        local = [{"path": "core/foo.py", "excerpt": "bar", "score": 0.7}]
        sp = self.agent._build_source_pack([], local, [])
        self.assertEqual(sp["sources"][0]["authority_level"], "primary")
        self.assertEqual(sp["sources"][0]["source_type"], "local")

    def test_llm_prior_ref_authority_tertiary(self):
        llm = [{"title": "LLM concept", "excerpt": "detail", "score": 0.4}]
        sp = self.agent._build_source_pack([], [], llm)
        self.assertEqual(sp["sources"][0]["authority_level"], "tertiary")
        self.assertEqual(sp["sources"][0]["source_type"], "llm_prior")

    def test_multiple_refs_sequential_ids(self):
        web = [
            {"url": "https://a.com", "title": "A", "excerpt": "", "content_full": "", "score": 0.5},
            {"url": "https://b.com", "title": "B", "excerpt": "", "content_full": "", "score": 0.5},
        ]
        sp = self.agent._build_source_pack(web, [], [])
        ids = [s["source_id"] for s in sp["sources"]]
        self.assertEqual(ids, ["web_001", "web_002"])

    def test_empty_refs_return_empty_sources(self):
        sp = self.agent._build_source_pack([], [], [])
        self.assertEqual(sp["sources"], [])

    def test_source_pack_required_fields(self):
        web = [{"url": "https://x.com", "title": "X", "excerpt": "e", "content_full": "f", "score": 0.5}]
        sp = self.agent._build_source_pack(web, [], [])
        required = {"source_id", "source_type", "retrieval_method", "url", "title",
                    "excerpt", "content_full", "authority_level", "relevance_score", "selected_reason"}
        self.assertTrue(required.issubset(sp["sources"][0].keys()))


# ---------------------------------------------------------------------------
# C. researcher._synthesize_structured_evidence — LLM normalizer
# ---------------------------------------------------------------------------

class TestSynthesizeStructuredEvidence(unittest.TestCase):

    def setUp(self):
        mr = MagicMock()
        from core.researcher import HimariResearchAgent
        self.agent = HimariResearchAgent(mr)

    def _source_pack(self):
        return {
            "sources": [
                {"source_id": "web_001", "source_type": "web", "title": "Docs",
                 "excerpt": "sample", "content_full": "full content", "relevance_score": 0.8,
                 "authority_level": "secondary", "url": "", "retrieval_method": "tavily_search",
                 "selected_reason": "r"},
            ]
        }

    def test_returns_structured_evidence_on_llm_success(self):
        fake_se = {
            "research_mode": "fresh_lookup",
            "goal_interpretation": "Build X",
            "recommended_architecture": "web_app",
            "recommended_tech_stack": ["Python 3.11"],
            "required_capabilities": ["cap1"],
            "agent_role_hints": ["backend_dev"],
            "skill_gap_hypotheses": [],
            "risks": [],
            "verification_focus": [],
            "maintenance_strategy": [],
            "source_backed_claims": [
                {"claim": "X is needed", "source_ids": ["web_001"]}
            ],
        }
        with patch("core.requirement_llm.execute_requirement_prompt",
                   return_value={"ok": True, "text": json.dumps(fake_se)}):
            result = self.agent._synthesize_structured_evidence(
                "Build a lottery app", "fresh_lookup", self._source_pack()
            )
        self.assertEqual(result["research_mode"], "fresh_lookup")
        self.assertEqual(result["recommended_architecture"], "web_app")
        self.assertEqual(len(result["source_backed_claims"]), 1)

    def test_returns_fallback_on_llm_failure(self):
        with patch("core.requirement_llm.execute_requirement_prompt",
                   return_value={"ok": False, "text": ""}):
            result = self.agent._synthesize_structured_evidence(
                "Build X", "fresh_lookup", self._source_pack()
            )
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("source_backed_claims"), [])
        self.assertEqual(result.get("research_mode"), "fresh_lookup")

    def test_fallback_on_bad_json(self):
        with patch("core.requirement_llm.execute_requirement_prompt",
                   return_value={"ok": True, "text": "not-json"}):
            result = self.agent._synthesize_structured_evidence(
                "Build X", "deep_source_research", {}
            )
        self.assertEqual(result["research_mode"], "deep_source_research")
        self.assertIsInstance(result.get("required_capabilities"), list)

    def test_research_mode_set_in_result(self):
        fake_se = {"goal_interpretation": "OK"}  # missing research_mode
        with patch("core.requirement_llm.execute_requirement_prompt",
                   return_value={"ok": True, "text": json.dumps(fake_se)}):
            result = self.agent._synthesize_structured_evidence(
                "x", "archive_research", {}
            )
        self.assertEqual(result["research_mode"], "archive_research")


# ---------------------------------------------------------------------------
# D. ResearchVerifier — 4-metric scoring
# ---------------------------------------------------------------------------

class TestVerifier4Metric(unittest.TestCase):

    def setUp(self):
        from core.research_verifier import ResearchVerifier
        self.verifier = ResearchVerifier()

    def _evidence(self, source_pack=None, structured_evidence=None, extra=None):
        ev = {
            "local_references": [
                {"score": 0.5, "excerpt": "a"},
                {"score": 0.5, "excerpt": "b"},
                {"score": 0.5, "excerpt": "c"},
            ],
            "web_references": [{"url": "https://x.com", "score": 0.7, "excerpt": "x"}],
            "llm_prior_references": [],
            "evidence_summary": ["s1", "s2", "s3", "s4"],
            "sufficiency_gate_passed": True,
            "source_pack": source_pack or {},
            "structured_evidence": structured_evidence or {},
        }
        if extra:
            ev.update(extra)
        return ev

    def _make_source_pack(self, n_web=1, n_primary=0, content_full_len=0):
        sources = []
        for i in range(n_web):
            sources.append({
                "source_id": f"web_{i+1:03d}",
                "source_type": "web",
                "authority_level": "primary" if i < n_primary else "secondary",
                "content_full": "x" * content_full_len,
                "excerpt": "",
            })
        return {"sources": sources}

    def _make_se(self, claims):
        return {"source_backed_claims": claims}

    # citation_validity tests

    def test_citation_validity_pass_all_valid(self):
        sp = self._make_source_pack(1)
        se = self._make_se([{"claim": "c", "source_ids": ["web_001"]}])
        sub, gaps = self.verifier._evaluate_4_metric(sp, se)
        self.assertNotIn("citation_validity_low", gaps)

    def test_citation_validity_fail_invalid_id(self):
        sp = self._make_source_pack(1)
        se = self._make_se([{"claim": "c", "source_ids": ["nonexistent"]}])
        sub, gaps = self.verifier._evaluate_4_metric(sp, se)
        self.assertIn("citation_validity_low", gaps)

    def test_citation_validity_no_claims_pass(self):
        sp = self._make_source_pack(1)
        se = self._make_se([])
        sub, gaps = self.verifier._evaluate_4_metric(sp, se)
        self.assertNotIn("citation_validity_low", gaps)

    # claim_source_ratio tests

    def test_claim_source_ratio_pass(self):
        sp = self._make_source_pack(2)
        se = self._make_se([
            {"claim": "c1", "source_ids": ["web_001"]},
            {"claim": "c2", "source_ids": ["web_002"]},
        ])
        sub, gaps = self.verifier._evaluate_4_metric(sp, se)
        self.assertNotIn("claim_source_ratio_low", gaps)

    def test_claim_source_ratio_fail(self):
        sp = self._make_source_pack(1)
        se = self._make_se([
            {"claim": "c1", "source_ids": []},
            {"claim": "c2", "source_ids": []},
            {"claim": "c3", "source_ids": []},
            {"claim": "c4", "source_ids": ["web_001"]},
        ])
        sub, gaps = self.verifier._evaluate_4_metric(sp, se)
        # 1/4 = 0.25 < 0.3 threshold
        self.assertIn("claim_source_ratio_low", gaps)

    def test_claim_source_ratio_no_claims_pass(self):
        sp = self._make_source_pack(1)
        se = self._make_se([])
        sub, gaps = self.verifier._evaluate_4_metric(sp, se)
        self.assertNotIn("claim_source_ratio_low", gaps)

    # primary_source_ratio tests

    def test_primary_source_ratio_pass(self):
        sp = self._make_source_pack(2, n_primary=1)
        sub, gaps = self.verifier._evaluate_4_metric(sp, {})
        # 1/2 = 0.5 >= 0.2
        # no gap for primary_source_ratio (별도 gap 미방출)
        self.assertIsInstance(gaps, list)

    def test_primary_source_ratio_score_added_when_above_threshold(self):
        sp = self._make_source_pack(2, n_primary=1)
        sub_with, _ = self.verifier._evaluate_4_metric(sp, {})
        sp_none = self._make_source_pack(2, n_primary=0)
        sub_without, _ = self.verifier._evaluate_4_metric(sp_none, {})
        self.assertGreater(sub_with, sub_without)

    # source_pack_chars tests

    def test_source_pack_chars_pass(self):
        sp = self._make_source_pack(1, content_full_len=600)
        sub, gaps = self.verifier._evaluate_4_metric(sp, {})
        self.assertNotIn("source_pack_too_shallow", gaps)

    def test_source_pack_chars_fail(self):
        sp = self._make_source_pack(1, content_full_len=100)
        sub, gaps = self.verifier._evaluate_4_metric(sp, {})
        self.assertIn("source_pack_too_shallow", gaps)

    def test_empty_source_pack_gaps(self):
        sub, gaps = self.verifier._evaluate_4_metric({}, {})
        self.assertIn("source_pack_too_shallow", gaps)
        # citation_validity: no claims → 1.0, no gap
        self.assertNotIn("citation_validity_low", gaps)

    # overall verify() integration

    def test_verify_4metric_contributes_to_score(self):
        sp = self._make_source_pack(2, n_primary=1, content_full_len=1000)
        se = self._make_se([{"claim": "c", "source_ids": ["web_001"]}])
        ev = self._evidence(source_pack=sp, structured_evidence=se)
        result = self.verifier.verify(ev, "task")
        self.assertGreater(result.score, 0.0)

    def test_verify_no_source_pack_backward_compat(self):
        ev = self._evidence()
        result = self.verifier.verify(ev, "task")
        self.assertIn(result.status, ("pass", "partial", "warn"))


# ---------------------------------------------------------------------------
# E. quality-tier gap — no mode jump
# ---------------------------------------------------------------------------

class TestQualityTierGapNoJump(unittest.TestCase):

    def test_quality_gap_does_not_trigger_mode_jump(self):
        from core.research_router import gap_to_mode, ResearchGap
        quality_gaps = [
            ResearchGap.CITATION_VALIDITY_LOW,
            ResearchGap.CLAIM_SOURCE_RATIO_LOW,
            ResearchGap.SOURCE_PACK_TOO_SHALLOW,
        ]
        mode = gap_to_mode(quality_gaps)
        self.assertIsNone(mode)

    def test_quality_gap_mixed_with_fresh_tier_escalates(self):
        from core.research_router import gap_to_mode, ResearchGap
        mixed = [ResearchGap.CITATION_VALIDITY_LOW, ResearchGap.NO_EXTERNAL_EVIDENCE]
        mode = gap_to_mode(mixed)
        self.assertEqual(mode, "fresh_lookup")

    def test_quality_gap_mixed_with_deep_tier_escalates_deep(self):
        from core.research_router import gap_to_mode, ResearchGap
        mixed = [ResearchGap.CITATION_VALIDITY_LOW, ResearchGap.MULTI_CLIENT_MISSING]
        mode = gap_to_mode(mixed)
        self.assertEqual(mode, "deep_source_research")


if __name__ == "__main__":
    unittest.main(verbosity=2)
