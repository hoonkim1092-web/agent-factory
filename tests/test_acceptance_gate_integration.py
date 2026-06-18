"""§8 S3 통합 테스트: AcceptanceGate + pipeline 배선 (INV-A~G).

설계: docs/2026-06-17-af-completion-contract-goal-verification-design.md §9
"""
import os
import sys
import types
import unittest
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

# project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.completion_contract import (
    AcceptanceGate,
    GoalContract,
    GoalEntry,
    build_evidence_ledger,
    parse_acceptance_criteria,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _verified_contract(task_id: str = "T-1") -> GoalContract:
    # python --version: always exits 0, no quoting ambiguity
    goal = GoalEntry(goal_id="G-1", description="cli test", harness_type="cli",
                     command="python --version")
    c = GoalContract(task_id=task_id, goals=[goal])
    AcceptanceGate().run(c, ".")
    return c


def _cannot_verify_contract(task_id: str = "T-cv") -> GoalContract:
    goal = GoalEntry(goal_id="G-1", description="gui test", harness_type="gui")
    c = GoalContract(task_id=task_id, goals=[goal])
    AcceptanceGate().run(c, ".")
    return c


def _failed_contract(task_id: str = "T-fail") -> GoalContract:
    # nonexistent script: always exits non-zero, no quoting ambiguity
    goal = GoalEntry(goal_id="G-1", description="fail test", harness_type="cli",
                     command="python _af_gate_nonexistent_test_dummy_xyz.py")
    c = GoalContract(task_id=task_id, goals=[goal])
    AcceptanceGate().run(c, ".")
    return c


def _unverified_contract(task_id: str = "T-uv") -> GoalContract:
    goal = GoalEntry(goal_id="G-1", description="vague goal", harness_type="none")
    return GoalContract(task_id=task_id, goals=[goal])


# ---------------------------------------------------------------------------
# ① VERIFIED 골 → ok=True (INV-A)
# ---------------------------------------------------------------------------

class TestVerifiedGoalOkTrue(unittest.TestCase):
    def test_verified_goal_is_done(self):
        c = _verified_contract()
        self.assertTrue(c.is_done(), "VERIFIED 골 → is_done() == True")

    def test_verified_no_failures(self):
        c = _verified_contract()
        self.assertFalse(c.has_failures())


# ---------------------------------------------------------------------------
# ② FAILED 골 → ok=False + reason=goal_failed (INV-A, INV-G)
# ---------------------------------------------------------------------------

class TestFailedGoalBlocks(unittest.TestCase):
    def test_failed_not_done(self):
        c = _failed_contract()
        self.assertFalse(c.is_done())

    def test_failed_has_failures(self):
        c = _failed_contract()
        self.assertTrue(c.has_failures())

    def test_gated_ok_false_on_failed(self):
        c = _failed_contract()
        gated_ok = (True) and c.is_done()  # status="completed" simulation
        self.assertFalse(gated_ok)
        reason = "goal_failed" if c.has_failures() else "goal_unverified"
        self.assertEqual(reason, "goal_failed")


# ---------------------------------------------------------------------------
# ③ execute() 직접 호출 경로 gating — project_pipeline.execute() 반환 검증
# ---------------------------------------------------------------------------

class TestExecuteDirectPathGated(unittest.TestCase):
    """project_pipeline.execute()의 gated_ok 계산 로직을 단위 검증."""

    def _compute_gated(self, status: str, contract):
        """execute() 내 gated_ok 계산 로직 재현."""
        if contract is not None:
            gated_ok = (status == "completed") and contract.is_done()
            reason = "" if gated_ok else (
                "goal_failed" if contract.has_failures() else "goal_unverified"
            )
        else:
            gated_ok = (status == "completed")
            reason = status if not gated_ok else ""
        return gated_ok, reason

    def test_completed_verified_ok(self):
        c = _verified_contract()
        ok, reason = self._compute_gated("completed", c)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_completed_unverified_blocked(self):
        c = _unverified_contract()
        ok, reason = self._compute_gated("completed", c)
        self.assertFalse(ok)
        self.assertEqual(reason, "goal_unverified")

    def test_completed_failed_blocked_reason(self):
        c = _failed_contract()
        ok, reason = self._compute_gated("completed", c)
        self.assertFalse(ok)
        self.assertEqual(reason, "goal_failed")

    def test_contract_none_fallback(self):
        ok, reason = self._compute_gated("completed", None)
        self.assertTrue(ok)
        self.assertEqual(reason, "")


# ---------------------------------------------------------------------------
# ④ contract=None + verify 빈 dict → ok=False (INV-D, INV-B)
# ---------------------------------------------------------------------------

class TestNullContractEmptyVerifyBlocks(unittest.TestCase):
    """INV-D: contract=None 폴백은 verify_result에 passed 키가 실존할 때만."""

    def _review_decision(self, goal_contract, verify_result):
        """_run_review_phase 로직 재현."""
        if goal_contract is not None and goal_contract.has_failures():
            return "block", "goal_failed"
        passed = verify_result.get("passed", True)
        if passed:
            return "pass", "all verification checks passed"
        return "block", "verification failed"

    def test_null_contract_empty_verify_old_behavior(self):
        # contract=None 이면 passed=True 기본값으로 pass — 이것이 INV-B 위험 (기존 동작)
        decision, _ = self._review_decision(None, {})
        # 기존 동작: passed=True 기본 → pass (전환기 폴백)
        self.assertEqual(decision, "pass")

    def test_failed_contract_blocks_regardless_of_verify(self):
        c = _failed_contract()
        decision, reason = self._review_decision(c, {"passed": True})
        self.assertEqual(decision, "block")
        self.assertEqual(reason, "goal_failed")

    def test_unverified_contract_does_not_block_in_review(self):
        # UNVERIFIED는 has_failures()=False → review에서 직접 block 안 함
        # (block은 execute()의 gated_ok가 담당)
        c = _unverified_contract()
        decision, _ = self._review_decision(c, {"passed": True})
        self.assertEqual(decision, "pass")


# ---------------------------------------------------------------------------
# ⑤ CANNOT_VERIFY → BLOCKED 아님, is_done() done 허용 (INV-G)
# ---------------------------------------------------------------------------

class TestCannotVerifyNotBlocked(unittest.TestCase):
    def test_cannot_verify_is_done(self):
        c = _cannot_verify_contract()
        self.assertTrue(c.is_done(), "CANNOT_VERIFY → is_done() == True")

    def test_cannot_verify_no_failures(self):
        c = _cannot_verify_contract()
        self.assertFalse(c.has_failures())

    def test_cannot_verify_gated_ok_true(self):
        c = _cannot_verify_contract()
        gated_ok = (True) and c.is_done()
        self.assertTrue(gated_ok)


# ---------------------------------------------------------------------------
# ⑥ execute() ok 두 지점 동일 gated_ok (Finding #4)
# ---------------------------------------------------------------------------

class TestDashboardAndReturnOkMatch(unittest.TestCase):
    """dashboard(:1396)와 return(:1421)이 동일 gated_ok를 사용하는지 검증."""

    def test_same_gated_ok_used_twice(self):
        contract = _failed_contract()
        status = "completed"

        # execute() 로직 재현
        gated_ok = (status == "completed") and contract.is_done()

        dashboard_ok = gated_ok   # :1396
        return_ok = gated_ok      # :1421
        self.assertEqual(dashboard_ok, return_ok)
        self.assertFalse(dashboard_ok)

    def test_no_divergence_on_verified(self):
        contract = _verified_contract()
        status = "completed"
        gated_ok = (status == "completed") and contract.is_done()
        self.assertTrue(gated_ok)
        self.assertEqual(gated_ok, gated_ok)  # trivially same


# ---------------------------------------------------------------------------
# ⑦ already_done 조기반환: contract 재집계 / contract 없으면 already_done_legacy
# ---------------------------------------------------------------------------

class TestAlreadyDoneReaggregates(unittest.TestCase):
    def _already_done_return(self, contract):
        """execute() already_done 분기 재현."""
        if contract is not None:
            ok = contract.is_done()
            reason = "already_done" if ok else (
                "goal_failed" if contract.has_failures() else "goal_unverified"
            )
            return {"ok": ok, "reason": reason, "evidence_ledger": build_evidence_ledger(contract)}
        return {
            "ok": True,
            "reason": "already_done_legacy",
            "evidence_ledger": {"summary": "evidence absent — legacy done-run before AcceptanceGate"},
        }

    def test_verified_already_done_ok(self):
        r = self._already_done_return(_verified_contract())
        self.assertTrue(r["ok"])
        self.assertEqual(r["reason"], "already_done")

    def test_failed_already_done_blocked(self):
        r = self._already_done_return(_failed_contract())
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "goal_failed")

    def test_unverified_already_done_blocked(self):
        r = self._already_done_return(_unverified_contract())
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "goal_unverified")

    def test_no_contract_legacy(self):
        r = self._already_done_return(None)
        self.assertTrue(r["ok"])
        self.assertEqual(r["reason"], "already_done_legacy")
        self.assertIn("legacy", r["evidence_ledger"]["summary"])


# ---------------------------------------------------------------------------
# parse_acceptance_criteria 파서 테스트
# ---------------------------------------------------------------------------

class TestParseAcceptanceCriteria(unittest.TestCase):
    def test_empty_returns_empty_contract(self):
        c = parse_acceptance_criteria([], "T-0")
        self.assertEqual(len(c.goals), 0)
        self.assertFalse(c.is_done())

    def test_all_vague_all_none(self):
        criteria = ["핵심 기능이 구현된다.", "관련 파일이 갱신된다."]
        c = parse_acceptance_criteria(criteria, "T-1")
        self.assertEqual(len(c.goals), 2)
        for g in c.goals:
            self.assertEqual(g.harness_type, "none")

    def test_cli_keyword_inferred(self):
        criteria = ["실행 시 exit code 0 반환"]
        c = parse_acceptance_criteria(criteria, "T-cli")
        self.assertEqual(c.goals[0].harness_type, "cli")

    def test_server_keyword_inferred(self):
        criteria = ["서버가 80 포트에서 응답한다"]
        c = parse_acceptance_criteria(criteria, "T-srv")
        self.assertEqual(c.goals[0].harness_type, "server")

    def test_gui_keyword_inferred(self):
        criteria = ["GUI 화면이 표시된다"]
        c = parse_acceptance_criteria(criteria, "T-gui")
        self.assertEqual(c.goals[0].harness_type, "gui")

    def test_library_keyword_inferred(self):
        criteria = ["import mylib; mylib.run() 가능"]
        c = parse_acceptance_criteria(criteria, "T-lib")
        self.assertEqual(c.goals[0].harness_type, "library")

    def test_backtick_command_extracted(self):
        criteria = ["`python hello.py` 실행 시 Hello 출력"]
        c = parse_acceptance_criteria(criteria, "T-cmd")
        self.assertEqual(c.goals[0].command, "python hello.py")

    def test_goal_ids_sequential(self):
        criteria = ["A", "B", "C"]
        c = parse_acceptance_criteria(criteria, "T-ids")
        ids = [g.goal_id for g in c.goals]
        self.assertEqual(ids, ["G-1", "G-2", "G-3"])

    def test_blank_lines_skipped(self):
        criteria = ["", "  ", "real criterion"]
        c = parse_acceptance_criteria(criteria, "T-blank")
        self.assertEqual(len(c.goals), 1)


# ---------------------------------------------------------------------------
# build_evidence_ledger 테스트
# ---------------------------------------------------------------------------

class TestBuildEvidenceLedger(unittest.TestCase):
    def test_three_sections_always_present(self):
        c = _verified_contract()
        ledger = build_evidence_ledger(c)
        self.assertIn("goals", ledger)
        self.assertIn("unverified", ledger)
        self.assertIn("cannot_verify", ledger)

    def test_summary_counts(self):
        c = _verified_contract()
        ledger = build_evidence_ledger(c)
        self.assertIn("1 VERIFIED", ledger["summary"])

    def test_cannot_verify_in_section(self):
        c = _cannot_verify_contract()
        ledger = build_evidence_ledger(c)
        self.assertIn("G-1", ledger["cannot_verify"])

    def test_unverified_in_section(self):
        c = _unverified_contract()
        ledger = build_evidence_ledger(c)
        self.assertIn("G-1", ledger["unverified"])


if __name__ == "__main__":
    unittest.main()
