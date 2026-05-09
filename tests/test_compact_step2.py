"""
tests/test_compact_step2.py
============================
Phase A Step 2 COMPACT — RunBudget, CWM, SkillPackBootstrapper 직접 테스트.
"""
import shutil
from unittest.mock import patch

import pytest

from core.run_budget import RunBudget, get_run_budget, set_run_budget


@pytest.fixture(autouse=True)
def reset_run_budget():
    """각 테스트 전후에 RunBudget 글로벌 싱글턴을 초기화한다."""
    set_run_budget(0)
    yield
    set_run_budget(0)
from core.context_window_manager import HistoryManager, estimate_tokens
from core.skill_pack_bootstrapper import SkillPackBootstrapper
from core.plan_verifier import PlanVerifier, PlanVerifyResult


# ──────────────────────────────────────────────
# 1. RunBudget.record() — 토큰 누적 및 소진 감지
# ──────────────────────────────────────────────
class TestRunBudgetRecord:
    def test_record_accumulates(self):
        b = RunBudget(max_tokens=1000)
        b.record("hello world")  # 11 chars → 2 tokens (11//4=2)
        assert b.consumed > 0

    def test_record_four_chars_one_token(self):
        b = RunBudget(max_tokens=1000)
        b.record("abcd")  # 4 chars → 1 token
        assert b.consumed == 1

    def test_exhausted_triggers_at_max(self):
        b = RunBudget(max_tokens=1)
        assert not b.is_exhausted()
        b.record("abcd")  # 1 token consumed
        assert b.is_exhausted()

    def test_unlimited_never_exhausted(self):
        b = RunBudget(max_tokens=0)
        b.record("a" * 10_000)
        assert not b.is_exhausted()

    def test_set_run_budget_resets_singleton(self, capsys):
        original = get_run_budget()
        b = set_run_budget(10)
        b.record("a" * 40)  # 10 tokens
        assert b.is_exhausted()
        # reset
        set_run_budget(0)
        assert not get_run_budget().is_exhausted()


# ──────────────────────────────────────────────
# 2. HistoryManager budget enforcement (CWM 핵심)
# ──────────────────────────────────────────────
class TestHistoryManagerBudget:
    def test_entries_evicted_over_budget(self):
        """토큰 예산 초과 시 오래된 엔트리가 제거된다."""
        hm = HistoryManager(budget_tokens=20)
        # 각 엔트리 약 10토큰 (40자)
        for i in range(5):
            hm.add_user_message("x" * 40, turn=i)
        # build_contents()가 _enforce_budget()를 호출한다
        contents = hm.build_contents()
        # 예산 20tok → 최대 2개 엔트리 유지 (최소 2개 보장)
        assert hm.total_tokens <= 20 or len(hm._entries) == 2

    def test_minimum_two_entries_preserved(self):
        """극단적으로 예산이 적어도 최소 2개 엔트리는 유지된다."""
        hm = HistoryManager(budget_tokens=1)
        hm.add_user_message("hello", turn=0)
        hm.add_user_message("world", turn=1)
        hm.build_contents()
        assert len(hm._entries) >= 2

    def test_fresh_history_manager_is_empty(self):
        hm = HistoryManager(budget_tokens=10000)
        assert hm.total_tokens == 0
        assert hm.entries == []


# ──────────────────────────────────────────────
# 3. SkillPackBootstrapper.check_installed()
# ──────────────────────────────────────────────
class TestSkillPackBootstrapper:
    def test_returns_all_plugin_keys(self):
        b = SkillPackBootstrapper()
        result = b.check_installed()
        assert set(result.keys()) == {"claude-code", "codex", "gemini"}

    def test_values_are_bool(self):
        b = SkillPackBootstrapper()
        for v in b.check_installed().values():
            assert isinstance(v, bool)

    def test_missing_returns_list(self):
        b = SkillPackBootstrapper()
        missing = b.missing()
        installed = b.installed()
        assert isinstance(missing, list)
        assert isinstance(installed, list)
        assert set(missing + installed) == {"claude-code", "codex", "gemini"}

    def test_shutil_which_none_means_not_installed(self):
        with patch("core.skill_pack_bootstrapper.shutil.which", return_value=None):
            b = SkillPackBootstrapper()
            result = b.check_installed()
        assert all(v is False for v in result.values())

    def test_shutil_which_path_means_installed(self):
        with patch("core.skill_pack_bootstrapper.shutil.which", return_value="/usr/bin/claude"):
            b = SkillPackBootstrapper()
            result = b.check_installed()
        assert all(v is True for v in result.values())


# ──────────────────────────────────────────────
# 4. PlanVerifier.gate() — Phase Gate 승격 검증
# ──────────────────────────────────────────────
class TestPlanVerifierGate:
    def test_gate_empty_work_items_redirects(self):
        pv = PlanVerifier()
        result = pv.gate("build me a thing", [])
        assert result.passed is False
        assert result.redirect == "create_plan"
        assert any("no_plan" in issue for issue in result.issues)

    def test_gate_empty_list_redirects_2(self):
        """빈 리스트 두 번째 확인 — redirect 값 단독 체크."""
        pv = PlanVerifier()
        result = pv.gate("build me a thing", [])
        assert result.redirect == "create_plan"

    def test_gate_none_treated_as_empty(self):
        """gate()는 work_items=None도 빈 것으로 취급해 리다이렉트해야 한다."""
        pv = PlanVerifier()
        # gate() 시그니처: work_items: list — None 전달 시 if not work_items: 가 True
        result = pv.gate("build me a thing", None)  # type: ignore[arg-type]
        assert result.redirect == "create_plan"

    def test_gate_with_items_calls_verify(self):
        pv = PlanVerifier()
        items = [{"task": "do something"}]
        # verify()가 LLM을 호출하므로 패치
        with patch.object(pv, "verify", return_value=PlanVerifyResult(passed=True, score=0.9)) as mock_verify:
            result = pv.gate("task", items)
        mock_verify.assert_called_once_with("task", items, None)
        assert result.passed is True

    def test_gate_result_redirect_default_empty(self):
        result = PlanVerifyResult(passed=True, score=1.0)
        assert result.redirect == ""
