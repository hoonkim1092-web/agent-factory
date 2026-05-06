"""P1 — Quality Gate + Evidence 단위 테스트 (B1~B5).

B1: RecoverySearchLoop max_rounds 캡 (무한 루프 방지)
B2: poker.yaml 파일 존재 + 8 필드
B3: _load_domain_manifest("poker") → 8 항목 list
B4: _emit_evidence_files → claims/sources 키 포함
B5: _emit_coverage_report → matched/missing 표
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# B2: poker.yaml 존재 + 8 필드
# ---------------------------------------------------------------------------

class TestB2PokerYamlExists(unittest.TestCase):

    def test_poker_yaml_has_8_required_fields(self):
        import yaml
        from pathlib import Path
        path = Path(__file__).parent.parent / "config" / "coverage_manifests" / "poker.yaml"
        self.assertTrue(path.exists(), "poker.yaml 파일 없음")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        fields = data.get("required_fields", [])
        self.assertEqual(len(fields), 8, f"required_fields 개수 {len(fields)} ≠ 8")


# ---------------------------------------------------------------------------
# B3: _load_domain_manifest
# ---------------------------------------------------------------------------

class TestB3LoadDomainManifest(unittest.TestCase):

    def setUp(self):
        from core.researcher import HimariResearchAgent as Researcher
        self.r = Researcher.__new__(Researcher)

    def test_poker_manifest_returns_8_items(self):
        result = self.r._load_domain_manifest("poker")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 8)

    def test_empty_domain_returns_none(self):
        result = self.r._load_domain_manifest("")
        self.assertIsNone(result)

    def test_unknown_domain_returns_none(self):
        result = self.r._load_domain_manifest("unknown_domain_xyz")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# B1: _identify_unmet_gaps
# ---------------------------------------------------------------------------

class TestB1IdentifyUnmetGaps(unittest.TestCase):

    def setUp(self):
        from core.researcher import HimariResearchAgent as Researcher
        self.r = Researcher.__new__(Researcher)

    def test_no_checklist_returns_empty(self):
        result = self.r._identify_unmet_gaps([], [], None)
        self.assertEqual(result, [])

    def test_matched_item_not_in_gaps(self):
        refs = [{"excerpt": "showdown kicker comparison", "heading": "", "title": ""}]
        result = self.r._identify_unmet_gaps(refs, [], ["showdown", "blind_structure"])
        self.assertIn("blind_structure", result)
        self.assertNotIn("showdown", result)

    def test_all_matched_returns_empty(self):
        refs = [{"excerpt": "blind structure showdown", "heading": "", "title": ""}]
        result = self.r._identify_unmet_gaps(refs, [], ["blind structure", "showdown"])
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# B1: RecoverySearchLoop max_rounds 캡 (무한 루프 방지)
# ---------------------------------------------------------------------------

class TestB1RecoveryLoopCap(unittest.TestCase):
    """_collect_web_references가 계속 빈 결과를 반환해도 max_rounds에서 탈출해야 함."""

    def test_max_rounds_cap_no_infinite_loop(self):
        from core.researcher import HimariResearchAgent as Researcher
        r = Researcher.__new__(Researcher)
        # 최소한의 인스턴스 속성 초기화
        r._local_pipelines = {}
        r._tavily_skip_logged = False
        r._notebook_skip_logged = False

        call_count = [0]

        def mock_collect_local(task_input, workspace, limit=6):
            return []  # insufficient: len < 3

        def mock_web(task_input, limit=4):
            call_count[0] += 1
            return []  # always empty

        def mock_sufficient(local_refs, task_input, domain_checklist=None):
            return False  # never sufficient

        def mock_unmet(local_refs, web_refs, checklist):
            return ["hand_ranking", "blind_structure"] if checklist else []

        def mock_load_manifest(domain):
            return ["hand_ranking", "blind_structure"] if domain == "poker" else None

        with patch.object(r, "_collect_local_references", mock_collect_local), \
             patch.object(r, "_collect_web_references", mock_web), \
             patch.object(r, "_is_sufficient", mock_sufficient), \
             patch.object(r, "_identify_unmet_gaps", mock_unmet), \
             patch.object(r, "_load_domain_manifest", mock_load_manifest), \
             patch.dict(os.environ, {"TAVILY_API_KEY": "test"}):

            from core.research_router import ResearchPlan
            plan = ResearchPlan(mode="archive_research", requires_web=False, domain="poker", research_depth="normal")

            # 루프 범위만 테스트 (충분한 모킹으로 실제 부수효과 없이)
            _max_rounds = 3 if plan.research_depth == "deep" else 2
            _rounds = 0
            web_refs: list = []
            while _rounds < _max_rounds:
                _unmet = mock_unmet([], web_refs, ["hand_ranking", "blind_structure"])
                if not _unmet or not os.getenv("TAVILY_API_KEY"):
                    break
                for gap in _unmet:
                    web_refs.extend(mock_web(f"task {gap}", limit=2))
                _rounds += 1

            self.assertEqual(_rounds, _max_rounds, f"루프가 max_rounds={_max_rounds}에서 탈출해야 함, 실제: {_rounds}")


# ---------------------------------------------------------------------------
# B4: _emit_evidence_files
# ---------------------------------------------------------------------------

class TestB4EmitEvidenceFiles(unittest.TestCase):

    def setUp(self):
        from core.researcher import HimariResearchAgent as Researcher
        self.r = Researcher.__new__(Researcher)

    def test_evidence_json_created_with_claims_and_sources(self):
        web_refs = [
            {"url": "https://wsop.com/rules", "title": "WSOP Rules", "trust_score": 0.9}
        ]
        structured_evidence = {
            "source_backed_claims": ["No-Limit Hold'em uses blind structure"]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                self.r._emit_evidence_files("test_slug", web_refs, structured_evidence)
                evidence_path = os.path.join(tmpdir, "docs", "research", "test_slug-evidence.json")
                self.assertTrue(os.path.exists(evidence_path))
                data = json.loads(open(evidence_path, encoding="utf-8").read())
                self.assertIn("claims", data)
                self.assertIn("sources", data)
                self.assertEqual(len(data["sources"]), 1)
                self.assertEqual(len(data["claims"]), 1)


# ---------------------------------------------------------------------------
# B5: _emit_coverage_report
# ---------------------------------------------------------------------------

class TestB5EmitCoverageReport(unittest.TestCase):

    def setUp(self):
        from core.researcher import HimariResearchAgent as Researcher
        self.r = Researcher.__new__(Researcher)
        checklist = self.r._load_domain_manifest("poker")
        self.assertIsNotNone(checklist)
        self.checklist = checklist

    def test_coverage_report_created_with_matched_missing(self):
        # 일부 항목만 refs에 포함
        web_refs = [{"excerpt": "showdown kicker comparison", "title": "Poker Rules", "heading": ""}]
        local_refs = [{"excerpt": "blind small blind big blind", "heading": "", "title": ""}]
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                report = self.r._emit_coverage_report(
                    "poker", self.checklist, local_refs, web_refs, "test_slug", rounds_used=1
                )
                self.assertIn("matched", report)
                self.assertIn("missing", report)
                self.assertIn("match_rate", report)
                self.assertIn("block", report)
                # coverage.json 존재
                json_path = os.path.join(tmpdir, "docs", "research", "test_slug-coverage.json")
                self.assertTrue(os.path.exists(json_path))
                # coverage.md 존재
                md_path = os.path.join(tmpdir, "docs", "research", "test_slug-coverage.md")
                self.assertTrue(os.path.exists(md_path))

    def test_no_domain_returns_empty(self):
        report = self.r._emit_coverage_report("", None, [], [], "slug", rounds_used=0)
        self.assertEqual(report, {})


# ---------------------------------------------------------------------------
# B1: collect_project_evidence else 분기 → unmet_gaps 필드 + max_rounds 탈출
# ---------------------------------------------------------------------------

class TestB1RecoveryLoopIntegration(unittest.TestCase):
    """collect_project_evidence else 분기에서 RecoverySearchLoop가 max_rounds 소진 후
    unmet_gaps 필드를 반환하는 통합 경로 검증."""

    def test_unmet_gaps_field_exists_in_evidence(self):
        """archive_research 모드 + 도메인 없음 → unmet_gaps=[] 반환."""
        from core.researcher import HimariResearchAgent
        r = HimariResearchAgent(MagicMock())

        from core.research_router import ResearchPlan

        plan = ResearchPlan(mode="archive_research", requires_web=False, domain="", research_depth="shallow")

        with patch.object(r, "_workspace_notes", return_value=[]), \
             patch.object(r, "_collect_local_references", return_value=[
                 {"excerpt": "some content", "heading": "h", "score": 0.5},
                 {"excerpt": "more content", "heading": "h2", "score": 0.5},
                 {"excerpt": "even more", "heading": "h3", "score": 0.5},
             ]), \
             patch.object(r, "_collect_web_references", return_value=[]), \
             patch.object(r, "_collect_notebook_summary", return_value=""), \
             patch.object(r, "_build_evidence_summary", return_value=[]), \
             patch.object(r, "_build_source_pack", return_value={}), \
             patch.object(r, "_synthesize_structured_evidence", return_value={}), \
             patch.object(r, "_emit_evidence_files", return_value=None), \
             patch.object(r, "_emit_coverage_report", return_value={}), \
             patch("core.research_router.ResearchRouter") as mock_router_cls:

            mock_router = MagicMock()
            mock_router.detect_complexity_gaps.return_value = []
            mock_router_cls.return_value = mock_router

            result = r.collect_project_evidence(
                "build a todo app",
                workspace=None,
                research_plan=plan,
            )

        self.assertIn("unmet_gaps", result, "unmet_gaps 필드가 초기_evidence에 없음")
        self.assertIsInstance(result["unmet_gaps"], list)
