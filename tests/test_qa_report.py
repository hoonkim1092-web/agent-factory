"""tests/test_qa_report.py — Q-S5 HTML 렌더러 테스트.

설계: docs/2026-06-18-user-perspective-qa-pipeline-design.md §9
불변식 커버: INV-Q2 (provenance=research → [확인 요망] 동시 표기)
"""
import os
import tempfile
import unittest

from core.qa_report import render_html


def _ledger(**kwargs):
    """최소 evidence_ledger dict 헬퍼."""
    base = {"task_id": "T-test", "summary": "1 goals: 0 VERIFIED", "goals": []}
    base.update(kwargs)
    return base


def _goal(verdict="UNVERIFIED", provenance="default", **kwargs):
    g = {
        "goal_id": "G-1",
        "description": "테스트 골",
        "verdict": verdict,
        "provenance": provenance,
    }
    g.update(kwargs)
    return g


class TestRenderHtmlFileOutput(unittest.TestCase):
    def test_creates_file_in_run_dir(self):
        """render_html이 run_dir/qa_report.html 파일을 생성하고 경로를 반환."""
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(), d)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(os.path.basename(path), "qa_report.html")
            self.assertEqual(os.path.dirname(path), d)

    def test_empty_ledger_renders_without_error(self):
        """goals 빈 리스트 → 오류 없이 HTML 생성."""
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(), d)
            content = open(path, encoding="utf-8").read()
            self.assertIn("T-test", content)

    def test_task_id_in_title(self):
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(task_id="MY-TASK"), d)
            content = open(path, encoding="utf-8").read()
            self.assertIn("MY-TASK", content)

    def test_self_contained_no_external_links(self):
        """외부 스크립트·스타일시트 의존 없음 (자기완결 HTML)."""
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[_goal()]), d)
            content = open(path, encoding="utf-8").read()
            self.assertNotIn('<script src=', content)
            self.assertNotIn('<link rel="stylesheet"', content)
            self.assertNotIn('href=', content.split('<style>')[0])  # head에 외부 href 없음


class TestVerifiedSection(unittest.TestCase):
    def _render(self, **kwargs):
        g = _goal(verdict="VERIFIED", **kwargs)
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            return open(path, encoding="utf-8").read()

    def test_verified_section_present(self):
        content = self._render()
        self.assertIn("[VERIFIED]", content)

    def test_verified_shows_command(self):
        content = self._render(command_run="python app.py")
        self.assertIn("python app.py", content)

    def test_verified_shows_expected_output(self):
        content = self._render(expected_output="Hello World")
        self.assertIn("Hello World", content)

    def test_verified_user_badge(self):
        content = self._render(provenance="user")
        self.assertIn("badge-user", content)


class TestFailedSection(unittest.TestCase):
    def _render(self, **kwargs):
        g = _goal(verdict="FAILED", **kwargs)
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            return open(path, encoding="utf-8").read()

    def test_failed_section_present(self):
        content = self._render()
        self.assertIn("[FAILED]", content)

    def test_failed_shows_evidence_value(self):
        content = self._render(evidence_value="Error: not found")
        self.assertIn("Error: not found", content)

    def test_failed_shows_expected_output(self):
        content = self._render(expected_output="expected_output_value")
        self.assertIn("expected_output_value", content)


class TestCannotVerifySection(unittest.TestCase):
    def _render(self, **kwargs):
        g = _goal(verdict="CANNOT_VERIFY", **kwargs)
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            return open(path, encoding="utf-8").read()

    def test_cannot_verify_section_present(self):
        content = self._render()
        self.assertIn("[CANNOT_VERIFY]", content)

    def test_cannot_verify_shows_reason(self):
        content = self._render(cannot_verify_reason="display required")
        self.assertIn("display required", content)


class TestUnverifiedSection(unittest.TestCase):
    def _render(self, **kwargs):
        g = _goal(verdict="UNVERIFIED", **kwargs)
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            return open(path, encoding="utf-8").read()

    def test_unverified_section_present(self):
        content = self._render()
        self.assertIn("[UNVERIFIED]", content)

    def test_unverified_shows_description(self):
        g = _goal(verdict="UNVERIFIED", description="검증법 미정 골")
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            content = open(path, encoding="utf-8").read()
        self.assertIn("검증법 미정 골", content)


class TestConfirmRequiredSection(unittest.TestCase):
    """INV-Q2: provenance=research 골 → [확인 요망] 동시 표기."""

    def test_research_verified_in_both_sections(self):
        """VERIFIED + research → [VERIFIED] 와 [확인 요망] 둘 다 표기."""
        g = _goal(verdict="VERIFIED", provenance="research", expected_output="합성 기대출력")
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            content = open(path, encoding="utf-8").read()
        self.assertIn("[VERIFIED]", content)
        self.assertIn("[확인 요망]", content)
        # 맞나요? 문구 포함
        self.assertIn("맞나요", content)

    def test_research_unverified_in_confirm_section(self):
        """UNVERIFIED + research → [확인 요망] 표기."""
        g = _goal(verdict="UNVERIFIED", provenance="research")
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            content = open(path, encoding="utf-8").read()
        self.assertIn("[확인 요망]", content)

    def test_user_provenance_not_in_confirm(self):
        """provenance=user → [확인 요망] 미표기 (INV-Q2 대칭)."""
        g = _goal(verdict="VERIFIED", provenance="user")
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            content = open(path, encoding="utf-8").read()
        self.assertNotIn("[확인 요망]", content)

    def test_default_provenance_not_in_confirm(self):
        """provenance=default → [확인 요망] 미표기."""
        g = _goal(verdict="VERIFIED", provenance="default")
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            content = open(path, encoding="utf-8").read()
        self.assertNotIn("[확인 요망]", content)

    def test_confirm_shows_expected_output(self):
        """[확인 요망] 섹션에 expected_output 표시."""
        g = _goal(verdict="VERIFIED", provenance="research", expected_output="정답 기준 텍스트")
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            content = open(path, encoding="utf-8").read()
        self.assertIn("정답 기준 텍스트", content)

    def test_research_badge_shown(self):
        """research provenance 배지 표시."""
        g = _goal(verdict="VERIFIED", provenance="research")
        with tempfile.TemporaryDirectory() as d:
            path = render_html(_ledger(goals=[g]), d)
            content = open(path, encoding="utf-8").read()
        self.assertIn("badge-research", content)


class TestBuildEvidenceLedgerProvenance(unittest.TestCase):
    """build_evidence_ledger가 provenance/expected_output을 포함하는지 검증."""

    def test_provenance_included_when_non_default(self):
        from core.completion_contract import GoalContract, GoalEntry, build_evidence_ledger
        entry = GoalEntry(
            goal_id="G-1",
            description="test",
            harness_type="cli",
            provenance="research",
        )
        ledger = build_evidence_ledger(GoalContract(task_id="T", goals=[entry]))
        self.assertEqual(ledger["goals"][0].get("provenance"), "research")

    def test_provenance_omitted_when_default(self):
        from core.completion_contract import GoalContract, GoalEntry, build_evidence_ledger
        entry = GoalEntry(goal_id="G-1", description="test", harness_type="cli")
        ledger = build_evidence_ledger(GoalContract(task_id="T", goals=[entry]))
        self.assertNotIn("provenance", ledger["goals"][0])

    def test_expected_output_included_when_set(self):
        from core.completion_contract import GoalContract, GoalEntry, build_evidence_ledger
        entry = GoalEntry(
            goal_id="G-1",
            description="test",
            harness_type="cli",
            expected_output="Hello",
        )
        ledger = build_evidence_ledger(GoalContract(task_id="T", goals=[entry]))
        self.assertEqual(ledger["goals"][0].get("expected_output"), "Hello")

    def test_expected_output_omitted_when_empty(self):
        from core.completion_contract import GoalContract, GoalEntry, build_evidence_ledger
        entry = GoalEntry(goal_id="G-1", description="test", harness_type="cli")
        ledger = build_evidence_ledger(GoalContract(task_id="T", goals=[entry]))
        self.assertNotIn("expected_output", ledger["goals"][0])


if __name__ == "__main__":
    unittest.main()
