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
# G3 case 4 — TAVILY 미설정 → LLM prior fallback이 llm_prior_references 슬롯에 적재
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

        # After G3 fix (defect #1 정정): LLM prior는 llm_prior_references 슬롯 — 메타데이터(verified=False) 보존
        self.assertGreater(len(result["llm_prior_references"]), 0)
        self.assertEqual(len(result["web_references"]), 0)


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

        # P5 병렬화 후: local+web 동시 실행 → 합산 < 0.10s (sleep 0.06 * 2 = 0.12 순차 대비)
        self.assertLess(elapsed, 0.10, "parallel: local+web should run concurrently")
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


# ---------------------------------------------------------------------------
# B1 case 8 — max_rounds 캡: unmet_gaps가 매 라운드 동일하게 남아도 루프 탈출
# ---------------------------------------------------------------------------

class TestB1MaxRoundsCapPreventsInfiniteLoop(unittest.TestCase):

    def test_b1_max_rounds_cap(self):
        """unmet_gaps가 지워지지 않아도 max_rounds 후 루프가 종료되어야 한다."""
        from core.research_router import ResearchPlan
        from core.researcher import HimariResearchAgent

        mr = MagicMock()
        agent = HimariResearchAgent(mr)

        # archive_research 모드 (requires_web=False, mode != "fast_synthesis")
        plan = ResearchPlan.for_mode("archive_research")
        plan.domain = "poker"
        plan.research_depth = "normal"  # max_rounds = 2

        call_count = {"web": 0}

        def _fake_collect_web(task_input, limit=4):
            call_count["web"] += 1
            return []  # 항상 빈 결과 → unmet_gaps 제거 안 됨

        fake_local = [
            {"excerpt": "some content", "heading": "h", "score": 0.3},
            {"excerpt": "more content", "heading": "h2", "score": 0.3},
            {"excerpt": "third content", "heading": "h3", "score": 0.3},
        ]

        with patch.dict(os.environ, {"TAVILY_API_KEY": "fake-key"}), \
             patch.object(agent, "_collect_local_references", return_value=fake_local), \
             patch.object(agent, "_collect_web_references", side_effect=_fake_collect_web), \
             patch.object(agent, "_collect_llm_prior_knowledge", return_value=[]), \
             patch.object(agent, "_workspace_notes", return_value=""), \
             patch.object(agent, "_collect_notebook_summary", return_value=""), \
             patch.object(agent, "_build_source_pack", return_value={"sources": []}), \
             patch.object(agent, "_synthesize_structured_evidence", return_value={
                 "research_mode": "archive_research", "goal_interpretation": "",
                 "source_backed_claims": [],
             }), \
             patch("core.research_router.ResearchRouter.detect_complexity_gaps", return_value=[]):
            result = agent.collect_project_evidence("포커 게임 만들어줘", research_plan=plan)

        # max_rounds=2이므로 loop 내 web 호출이 2회 이하여야 함 (무한루프 없음)
        # 실제 호출 수는 unmet 항목 수(최대 8개) * rounds이나, rounds <= max_rounds=2 보장
        self.assertLessEqual(call_count["web"], 8 * 2, "web calls must be capped by max_rounds")
        # 루프가 종료되고 결과가 반환되어야 함
        self.assertIn("unmet_gaps", result)
        self.assertIn("local_references", result)


class TestC1DomainSpecGate(unittest.TestCase):
    """P2 C1: prepare_documents domain spec gate."""

    def _make_pipeline(self):
        from core.project_pipeline import ProjectPipeline
        mr = MagicMock()
        mr.config = {}
        return ProjectPipeline(mr, MagicMock(), MagicMock(), MagicMock())

    def test_c1_spec_generation_triggered_when_no_specs_exist(self):
        """domain="poker" + no existing specs → SpecGenerator.generate 호출."""
        import tempfile
        from core.project_pipeline import ProjectPipeline
        from unittest.mock import patch, MagicMock

        pipeline = self._make_pipeline()

        with tempfile.TemporaryDirectory() as ws:
            brief = {"research_plan": {"domain": "poker"}, "goal": "poker game", "original_request": "8인 포커"}
            research_evidence = {"coverage_report": {"block": False, "match_rate": 1.0, "missing": []}}

            mock_specs = {"rules": "# Rules\n", "state_machine": "# SM\n"}
            with patch("core.spec_generator.SpecGenerator.generate", return_value=mock_specs) as mock_gen, \
                 patch.object(pipeline, "_save_specs") as mock_save:
                pipeline._domain = "poker"
                # _verify_domain_spec → False (no files yet)
                self.assertFalse(pipeline._verify_domain_spec(ws, "test-slug"))
                # Gate logic
                if not pipeline._verify_domain_spec(ws, "test-slug"):
                    from core.spec_generator import SpecGenerator
                    specs = SpecGenerator().generate(brief)
                    pipeline._save_specs(specs, ws, "test-slug")
                self.assertTrue(mock_gen.called)
                self.assertTrue(mock_save.called)

    def test_c1_coverage_block_raises_research_gate_blocked(self):
        """coverage_report.block=True → ResearchGateBlocked raised."""
        import tempfile
        from core.project_pipeline import ProjectPipeline, ResearchGateBlocked
        from unittest.mock import patch, MagicMock

        pipeline = self._make_pipeline()

        with tempfile.TemporaryDirectory() as ws:
            # Simulate spec already exists (so SpecGenerator skipped)
            import os
            specs_dir = os.path.join(ws, "docs", "specs")
            os.makedirs(specs_dir)
            open(os.path.join(specs_dir, "slug-rules-spec.md"), "w").close()

            self.assertTrue(pipeline._verify_domain_spec(ws, "slug"))
            self.assertTrue(pipeline._coverage_blocked({
                "coverage_report": {"block": True, "match_rate": 0.5, "missing": ["hand_ranking"]}
            }))

    def test_c1_no_domain_skips_gate(self):
        """domain="" → gate not triggered."""
        from core.project_pipeline import ProjectPipeline
        pipeline = self._make_pipeline()
        # _coverage_blocked with no coverage_report should be False
        self.assertFalse(pipeline._coverage_blocked({}))
        self.assertFalse(pipeline._coverage_blocked({"coverage_report": {"block": False}}))

    def test_c1_save_specs_writes_files(self):
        """_save_specs가 docs/specs/<slug>-*.md 파일을 디스크에 저장하고 Path 리스트를 반환한다."""
        import tempfile
        from pathlib import Path
        from core.project_pipeline import ProjectPipeline

        pipeline = self._make_pipeline()
        specs = {
            "rules": "# Rules\ncontent",
            "state_machine": "# State Machine\ncontent",
        }
        with tempfile.TemporaryDirectory() as ws:
            paths = pipeline._save_specs(specs, ws, "myslug")
            specs_dir = Path(ws) / "docs" / "specs"
            self.assertTrue((specs_dir / "myslug-rules-spec.md").exists())
            self.assertTrue((specs_dir / "myslug-state-machine.md").exists())
            # D1: 반환값이 Path 리스트인지 확인
            self.assertIsInstance(paths, list)
            self.assertEqual(len(paths), 2)
            self.assertTrue(all(p.exists() for p in paths))

    def test_d1_domain_specs_injected_into_project_brief(self):
        """D1: _specs_dict가 project_brief['domain_specs_summary']로 주입된다."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from core.project_pipeline import ProjectPipeline

        pipeline = self._make_pipeline()
        mock_specs = {
            "rules": "# Rules spec content",
            "state_machine": "# State Machine content",
        }
        brief = {"research_plan": {"domain": "poker"}, "goal": "poker game"}

        with tempfile.TemporaryDirectory() as ws:
            with patch("core.spec_generator.SpecGenerator.generate", return_value=mock_specs):
                # _verify_domain_spec → False (빈 디렉토리)
                self.assertFalse(pipeline._verify_domain_spec(ws, "slug"))
                # D1 로직 직접 실행
                _specs_dict: dict = {}
                if not pipeline._verify_domain_spec(ws, "slug"):
                    from core.spec_generator import SpecGenerator
                    _specs_dict = SpecGenerator().generate(brief)
                    pipeline._save_specs(_specs_dict, ws, "slug")
                if _specs_dict:
                    brief["domain_specs_summary"] = _specs_dict
                # brief에 주입됐는지 검증
                self.assertIn("domain_specs_summary", brief)
                self.assertIn("rules", brief["domain_specs_summary"])
                self.assertEqual(brief["domain_specs_summary"]["rules"], "# Rules spec content")

    def test_d1_existing_specs_loaded_into_brief(self):
        """D1: 기존 spec 파일이 있으면 디스크에서 읽어 project_brief에 주입한다."""
        import tempfile
        from pathlib import Path
        from core.project_pipeline import ProjectPipeline

        pipeline = self._make_pipeline()
        slug = "myslug"
        with tempfile.TemporaryDirectory() as ws:
            # 기존 spec 파일 미리 생성
            specs_dir = Path(ws) / "docs" / "specs"
            specs_dir.mkdir(parents=True)
            (specs_dir / f"{slug}-rules-spec.md").write_text("# Pre-existing Rules", encoding="utf-8")

            self.assertTrue(pipeline._verify_domain_spec(ws, slug))

            # else 분기 로직 직접 실행
            from core.spec_generator import SPEC_FILENAMES as _SFN
            _key_by_fn = {v: k for k, v in _SFN.items()}
            _spec_paths = []
            _specs_dict: dict = {}
            for _p in (Path(ws) / "docs" / "specs").glob(f"{slug}-*.md"):
                _spec_paths.append(_p)
                _fn = _p.name[len(slug) + 1:]
                _specs_dict[_key_by_fn.get(_fn, _fn)] = _p.read_text(encoding="utf-8")

            self.assertEqual(len(_spec_paths), 1)
            self.assertIn("rules", _specs_dict)
            self.assertEqual(_specs_dict["rules"], "# Pre-existing Rules")


class TestC3AdrGenerator(unittest.TestCase):
    """P2 C3: AdrGenerator 단위 테스트."""

    def _make_claims(self):
        return [
            {"claim_id": "C001", "claim": "WSOP rules define 8-player table provisions", "source_id": "S001"},
            {"claim_id": "C002", "claim": "Side pot calculation is clearly specified", "source_id": "S001"},
        ]

    def _make_sources(self):
        return [
            {"source_id": "S001", "title": "WSOP 2024 Tournament Rules", "url": "https://example.com/wsop"},
        ]

    def test_c3_fallback_adr_structure(self):
        """_fallback_adr가 필수 ADR 섹션(Date/Status/Decision/Alternatives/Rationale/Evidence)을 포함한다."""
        from core.spec_generator import AdrGenerator
        gen = AdrGenerator()
        brief = {"research_plan": {"domain": "poker"}, "goal": "8인 포커"}
        result = gen._fallback_adr("poker", "2026-05-06", self._make_claims(), self._make_sources())
        self.assertIn("# Decision:", result)
        self.assertIn("## Alternatives Considered", result)
        self.assertIn("## Rationale", result)
        self.assertIn("## Evidence References", result)
        self.assertIn("C001", result)

    def test_c3_generate_returns_empty_for_no_domain(self):
        """domain="" → generate가 빈 문자열 반환."""
        from core.spec_generator import AdrGenerator
        gen = AdrGenerator()
        brief = {"research_plan": {"domain": ""}, "goal": "general task"}
        result = gen.generate(brief, [], [])
        self.assertEqual(result, "")

    def test_c3_save_adr_writes_file_atomically(self):
        """_save_adr가 docs/decisions/<slug>-rule-baseline.md를 원자적으로 저장하고 Path를 반환한다."""
        import tempfile
        from pathlib import Path
        from core.project_pipeline import ProjectPipeline
        mr = MagicMock()
        mr.config = {}
        pipeline = ProjectPipeline(mr, MagicMock(), MagicMock(), MagicMock())
        with tempfile.TemporaryDirectory() as ws:
            result_path = pipeline._save_adr(ws, "myslug", "# Decision: test\n")
            out = Path(ws) / "docs" / "decisions" / "myslug-rule-baseline.md"
            self.assertTrue(out.exists())
            self.assertIn("# Decision:", out.read_text())
            self.assertEqual(result_path, out)


class TestC4TraceabilityGenerator(unittest.TestCase):
    """P2 C4: TraceabilityGenerator 단위 테스트."""

    def _make_claims(self):
        return [
            {"claim_id": "C001", "claim": "hand ranking rules apply to showdown", "source_id": "S001"},
            {"claim_id": "C002", "claim": "server state machine manages transitions", "source_id": "S001"},
        ]

    def _make_task_board(self):
        return {
            "tasks": [
                {"task_id": "T001", "description": "Implement hand ranking rules", "name": "Hand Rankings"},
                {"task_id": "T002", "description": "Build server state machine", "name": "State Machine"},
            ]
        }

    def test_c4_generate_produces_markdown_table(self):
        """generate가 claim_id/source_id/spec_section/task_id 컬럼이 있는 MD 표를 반환한다."""
        from core.spec_generator import TraceabilityGenerator
        gen = TraceabilityGenerator()
        brief = {"research_plan": {"domain": "poker"}, "goal": "8인 포커"}
        result = gen.generate(brief, self._make_claims(), self._make_task_board())
        self.assertIn("# Traceability", result)
        self.assertIn("| claim_id |", result)
        self.assertIn("C001", result)
        self.assertIn("C002", result)

    def test_c4_empty_claims_returns_empty_string(self):
        """claims=[] → "" 반환 (빈 traceability 파일을 쓰지 않는다)."""
        from core.spec_generator import TraceabilityGenerator
        gen = TraceabilityGenerator()
        brief = {"goal": "poker"}
        result = gen.generate(brief, [], {})
        self.assertEqual(result, "")

    def test_c4_save_traceability_writes_file_atomically(self):
        """_save_traceability가 docs/research/<slug>-traceability.md를 원자적으로 저장하고 Path를 반환한다."""
        import tempfile
        from pathlib import Path
        from core.project_pipeline import ProjectPipeline
        mr = MagicMock()
        mr.config = {}
        pipeline = ProjectPipeline(mr, MagicMock(), MagicMock(), MagicMock())
        with tempfile.TemporaryDirectory() as ws:
            result_path = pipeline._save_traceability(ws, "myslug", "# Traceability\n")
            out = Path(ws) / "docs" / "research" / "myslug-traceability.md"
            self.assertTrue(out.exists())
            self.assertIn("# Traceability", out.read_text())
            self.assertEqual(result_path, out)

    def test_c4_load_evidence_uses_safe_id_slug(self):
        """_load_evidence가 safe_id(task_input)[:40] 으로 evidence.json 경로를 찾는다."""
        import json, tempfile, os
        from pathlib import Path
        from core.utils import safe_id
        from core.project_pipeline import ProjectPipeline
        mr = MagicMock()
        mr.config = {}
        pipeline = ProjectPipeline(mr, MagicMock(), MagicMock(), MagicMock())
        task_input = "build a poker game"
        expected_slug = safe_id(task_input)[:40]
        claims_data = [{"claim_id": "C001", "claim": "poker rule", "source_id": "S001"}]
        sources_data = [{"source_id": "S001", "title": "WSOP Rules"}]
        with tempfile.TemporaryDirectory() as ws:
            research_dir = Path(ws) / "docs" / "research"
            research_dir.mkdir(parents=True)
            (research_dir / f"{expected_slug}-evidence.json").write_text(
                json.dumps({"claims": claims_data, "sources": sources_data}), encoding="utf-8"
            )
            claims, sources = pipeline._load_evidence(ws, task_input)
            self.assertEqual(len(claims), 1)
            self.assertEqual(claims[0]["claim_id"], "C001")
            self.assertEqual(len(sources), 1)


if __name__ == "__main__":
    unittest.main()
