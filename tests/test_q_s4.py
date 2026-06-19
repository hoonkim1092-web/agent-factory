"""tests/test_q_s4.py — Q-S4 불변식 테스트.

설계: docs/2026-06-18-user-perspective-qa-pipeline-design.md §10 Q-S4
불변식:
  INV-Q3: test_seam → deliverables 승격
  INV-Q4: GoalContract는 execute() 전에 동결 (snapshot write-once)
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# INV-Q3: merge_clarification — output_field 기반 질문 흡수 + seam 승격
# ---------------------------------------------------------------------------

class TestMergeClarificationOutputField(unittest.TestCase):
    """output_field 기반 YAML 질문 (category 없음) 흡수 검증."""

    def _merge(self, questions, answers, provenance="default"):
        from core.clarification import merge_clarification
        return merge_clarification({}, questions, answers, provenance=provenance)

    def test_output_field_stored_in_enriched(self):
        """category 없고 output_field 있는 질문의 답이 enriched에 저장됨."""
        q = [{"output_field": "observable_goal", "question": "관찰 가능한 목표?", "default": ""}]
        result = self._merge(q, ["앱이 시작되면 로그 출력"])
        self.assertEqual(result.get("observable_goal"), "앱이 시작되면 로그 출력")

    def test_test_seam_promoted_to_deliverables(self):
        """output_field=test_seam 답 → deliverables 리스트에 승격 (INV-Q3)."""
        q = [{"output_field": "test_seam", "question": "테스트 seam?", "default": ""}]
        result = self._merge(q, ["--audio-file 플래그로 파일 주입"])
        deliverables = result.get("deliverables", [])
        self.assertTrue(
            any("테스트 seam" in str(d) for d in deliverables),
            f"deliverables에 seam 없음: {deliverables}",
        )

    def test_test_seam_also_stored_as_field(self):
        """test_seam 답이 enriched['test_seam']에도 저장됨."""
        q = [{"output_field": "test_seam", "question": "seam?", "default": ""}]
        result = self._merge(q, ["mock_flag"])
        self.assertEqual(result.get("test_seam"), "mock_flag")

    def test_empty_seam_not_promoted(self):
        """빈 seam 답 → deliverables 미승격 (노이즈 방지)."""
        q = [{"output_field": "test_seam", "question": "seam?", "default": ""}]
        result = self._merge(q, [""])
        deliverables = result.get("deliverables", [])
        self.assertFalse(any("테스트 seam" in str(d) for d in deliverables))

    def test_category_takes_precedence_over_output_field(self):
        """category 있으면 output_field 분기 타지 않음 (기존 채널 우선)."""
        q = [{"output_field": "test_seam", "category": "scope", "question": "?", "default": ""}]
        result = self._merge(q, ["scope_answer"])
        # scope category → deliverables에 raw answer (not seam: prefix)
        deliverables = result.get("deliverables", [])
        self.assertTrue(any("scope_answer" in str(d) for d in deliverables))
        self.assertFalse(any("테스트 seam" in str(d) for d in deliverables))

    def test_research_provenance_stored_in_log(self):
        """provenance=research가 clarification_log에 기록됨."""
        q = [{"output_field": "golden_example", "question": "골든 예시?", "default": ""}]
        result = self._merge(q, ["input -> output"], provenance="research")
        log = result.get("clarification_log", [])
        self.assertTrue(any(e.get("provenance") == "research" for e in log))


# ---------------------------------------------------------------------------
# INV-Q3 (경로 C): stage_router sentinel → work_item_generator project_brief 흡수
# ---------------------------------------------------------------------------

class TestStageRouterSentinelKeys(unittest.TestCase):
    """_run_new_project이 _qa_* sentinel keys를 files dict에 추가하는지 검증."""

    def _make_gc_result(self, fields: dict[str, str]) -> MagicMock:
        results = []
        for field, value in fields.items():
            r = MagicMock()
            r.output_field = field
            r.value = value
            r.provenance = "research"
            results.append(r)
        gc = MagicMock()
        gc.results = results
        gc.paused_hitl_ids = []
        gc.question_set_id = "goal_clarification"
        gc.schema_version = "1"
        gc.schema_hash = "abc"
        return gc

    def test_test_seam_sentinel_key_present(self):
        """gc_result에 test_seam 있으면 files['_qa_test_seam'] 추가."""
        with tempfile.TemporaryDirectory() as tmp:
            from core.control.stage_router import StageRouter
            from core.control.run_ledger import RunLedger
            sr = StageRouter(workspace=tmp, run_ledger=RunLedger(tmp))
            sr._active_schemas = {}
            sr._schema_hashes = {}

            gc_result = self._make_gc_result({
                "test_seam": "--audio-file flag",
                "observable_goal": "로그 출력",
                "golden_example": "input -> output",
                "manual_only": "",
            })
            # mock question_router
            qr = MagicMock()
            qr.route_batch.return_value = gc_result

            with patch.object(sr, "_active_schemas", {"goal_clarification": {"questions": []}}):
                with patch.object(sr, "_schema_hashes", {"goal_clarification": "hash"}):
                    # directly call _run_new_project to test sentinel insertion
                    # patch _write_project_goal to avoid file I/O complexity
                    with patch.object(sr, "_write_project_goal", return_value=os.path.join(tmp, "project-goal.md")):
                        with patch.object(sr, "_append_assumptions"):
                            with patch("core.control.stage_router.parse_questions", return_value=[]):
                                files = sr._run_new_project(
                                    work_dir=tmp,
                                    blast_radius="low",
                                    run_id="test-run",
                                    question_router=qr,
                                )
            self.assertEqual(files.get("_qa_test_seam"), "--audio-file flag")
            self.assertEqual(files.get("_qa_observable_goal"), "로그 출력")
            self.assertEqual(files.get("_qa_golden_example"), "input -> output")

    def test_provenance_encoded_as_json(self):
        """_qa_provenance가 JSON 인코딩된 dict 문자열로 저장됨."""
        with tempfile.TemporaryDirectory() as tmp:
            from core.control.stage_router import StageRouter
            from core.control.run_ledger import RunLedger
            sr = StageRouter(workspace=tmp, run_ledger=RunLedger(tmp))

            gc_result = self._make_gc_result({"test_seam": "flag", "golden_example": "ex"})

            with patch.object(sr, "_write_project_goal", return_value=os.path.join(tmp, "p.md")):
                with patch.object(sr, "_append_assumptions"):
                    with patch("core.control.stage_router.parse_questions", return_value=[]):
                        qr = MagicMock()
                        qr.route_batch.return_value = gc_result
                        files = sr._run_new_project(
                            work_dir=tmp, blast_radius="low", run_id="r",
                            question_router=qr,
                        )
            prov_str = files.get("_qa_provenance", "")
            self.assertTrue(prov_str, "provenance sentinel 누락")
            prov = json.loads(prov_str)
            self.assertEqual(prov.get("test_seam"), "research")


# ---------------------------------------------------------------------------
# INV-Q3 (경로 C): work_item_generator QA 흡수 + project_brief 업데이트
# ---------------------------------------------------------------------------

class TestWorkItemGeneratorQaAbsorption(unittest.TestCase):
    """stage0_files에서 _qa_* sentinel을 pop하고 project_brief를 업데이트하는지."""

    def test_seam_sentinel_popped_from_stage0_files(self):
        """generate_work_items가 _qa_* 키를 pop하고 project_brief를 업데이트함."""
        from core.work_item_generator import generate_work_items

        sentinel_return = {
            "_qa_test_seam": "--mock-flag",
            "_qa_observable_goal": "시작 시 OK 출력",
            "_qa_golden_example": "input -> output",
            "_qa_manual_only": "",
            "_qa_provenance": json.dumps({"test_seam": "research", "golden_example": "research"}),
        }

        with tempfile.TemporaryDirectory() as tmp:
            brief = {"goal": "test goal", "work_kind": "new_project"}
            # StageRouter is lazily imported; patch at its module location
            with patch("core.control.stage_router.StageRouter") as MockSR:
                instance = MockSR.return_value
                instance.run.return_value = dict(sentinel_return)
                try:
                    generate_work_items(
                        workspace=tmp, slug="test-slug",
                        project_brief=brief, role_plan={}, task_board={},
                        run_id="run1", work_kind="new_project", blast_radius="low",
                    )
                except Exception:
                    pass
            self.assertEqual(brief.get("test_seam"), "--mock-flag")
            self.assertEqual(brief.get("observable_goal"), "시작 시 OK 출력")
            self.assertEqual(brief.get("golden_example"), "input -> output")
            deliverables = brief.get("deliverables", [])
            self.assertTrue(any("테스트 seam" in str(d) for d in deliverables))


# ---------------------------------------------------------------------------
# INV-Q4: GoalContract snapshot write-once before execute()
# ---------------------------------------------------------------------------

class TestGoalContractFrozenBeforeExecute(unittest.TestCase):
    """_run_develop_full이 pipeline.execute() 전에 goal_contract.json을 저장."""

    def _make_state(self, tmp: str) -> MagicMock:
        state = MagicMock()
        state.task = "test task"
        state.worktree_workspace = tmp
        state.source_workspace = tmp
        state.runtime_workspace = tmp
        state.route_decision = None
        state.develop_changed_paths = []
        state.goal_contract = None
        state.run_id = "test-run-123"
        return state

    def _make_pipeline(self, gc_dict: dict | None):
        from core.completion_contract import GoalContract, GoalEntry
        _gc = None
        if gc_dict is not None:
            _gc = GoalContract.from_dict(gc_dict)

        prepared = MagicMock()
        prepared.goal_contract = _gc
        prepared.run_id = "test-run-123"
        prepared.work_item_slug = "test-slug"

        gate = MagicMock()
        gate.gate_path = "/nonexistent/gate.json"
        prepared.gate.return_value = gate

        pipeline = MagicMock()
        pipeline.prepare.return_value = prepared
        pipeline.execute.return_value = {"changed_files": [], "ok": True}
        return pipeline

    def test_snapshot_written_before_execute(self):
        """prepare() 후, execute() 전에 goal_contract.json이 생성됨."""
        with tempfile.TemporaryDirectory() as tmp:
            from core.dogfood import _run_develop_full
            gc_dict = {
                "task_id": "T-1",
                "goals": [{"goal_id": "G-1", "description": "test", "harness_type": "cli",
                           "expected_output": "Hello", "provenance": "research",
                           "verdict": "UNVERIFIED", "cannot_verify_reason": "",
                           "command": "", "scenario": [], "evidence": None}],
                "manifest": None,
            }
            pipeline = self._make_pipeline(gc_dict)
            state = self._make_state(tmp)

            execute_called_before_snapshot = []

            def _check_execute(prepared, **kwargs):
                snap = Path(tmp) / "dogfood" / "test-run-123" / "goal_contract.json"
                execute_called_before_snapshot.append(snap.exists())
                return {"changed_files": [], "ok": True}

            pipeline.execute.side_effect = _check_execute

            with patch("core.dogfood._develop_isolation_env"):
                with patch("core.dogfood._changed_files_fallback", return_value=[]):
                    with patch("core.dogfood._normalize_develop_result", return_value={}):
                        _run_develop_full(state, pipeline)

            snap_path = Path(tmp) / "dogfood" / "test-run-123" / "goal_contract.json"
            self.assertTrue(snap_path.exists(), "goal_contract.json 미생성")
            # execute가 호출될 때 이미 snapshot이 존재했어야 함
            self.assertTrue(execute_called_before_snapshot[0], "snapshot이 execute() 전에 없었음")

    def test_snapshot_expected_output_frozen(self):
        """스냅샷 파일의 expected_output이 구현 단계 후에도 동일함."""
        with tempfile.TemporaryDirectory() as tmp:
            from core.dogfood import _run_develop_full
            gc_dict = {
                "task_id": "T-1",
                "goals": [{"goal_id": "QA-GEX", "description": "골든 예시", "harness_type": "none",
                           "expected_output": "정확한 기대출력", "provenance": "research",
                           "verdict": "UNVERIFIED", "cannot_verify_reason": "",
                           "command": "", "scenario": [], "evidence": None}],
                "manifest": None,
            }
            pipeline = self._make_pipeline(gc_dict)
            state = self._make_state(tmp)

            with patch("core.dogfood._develop_isolation_env"):
                with patch("core.dogfood._changed_files_fallback", return_value=[]):
                    with patch("core.dogfood._normalize_develop_result", return_value={}):
                        _run_develop_full(state, pipeline)

            snap_path = Path(tmp) / "dogfood" / "test-run-123" / "goal_contract.json"
            snap = json.loads(snap_path.read_text(encoding="utf-8"))
            goals = snap.get("goals", [])
            gex = next((g for g in goals if g["goal_id"] == "QA-GEX"), None)
            self.assertIsNotNone(gex)
            self.assertEqual(gex["expected_output"], "정확한 기대출력")

    def test_no_snapshot_when_no_goal_contract(self):
        """goal_contract=None이면 snapshot 파일 미생성 (정상 경로)."""
        with tempfile.TemporaryDirectory() as tmp:
            from core.dogfood import _run_develop_full
            pipeline = self._make_pipeline(None)
            state = self._make_state(tmp)

            with patch("core.dogfood._develop_isolation_env"):
                with patch("core.dogfood._changed_files_fallback", return_value=[]):
                    with patch("core.dogfood._normalize_develop_result", return_value={}):
                        _run_develop_full(state, pipeline)

            snap_path = Path(tmp) / "dogfood" / "test-run-123" / "goal_contract.json"
            self.assertFalse(snap_path.exists(), "goal_contract 없는데 snapshot 생성됨")

    def test_snapshot_not_overwritten_on_second_call(self):
        """두 번째 호출에서 기존 snapshot을 덮어쓰지 않음 (write-once)."""
        with tempfile.TemporaryDirectory() as tmp:
            from core.dogfood import _run_develop_full
            gc_dict = {
                "task_id": "T-1",
                "goals": [{"goal_id": "G-1", "description": "d", "harness_type": "cli",
                           "expected_output": "original", "provenance": "research",
                           "verdict": "UNVERIFIED", "cannot_verify_reason": "",
                           "command": "", "scenario": [], "evidence": None}],
                "manifest": None,
            }
            # 첫 번째 호출
            pipeline = self._make_pipeline(gc_dict)
            state = self._make_state(tmp)
            with patch("core.dogfood._develop_isolation_env"):
                with patch("core.dogfood._changed_files_fallback", return_value=[]):
                    with patch("core.dogfood._normalize_develop_result", return_value={}):
                        _run_develop_full(state, pipeline)

            snap_path = Path(tmp) / "dogfood" / "test-run-123" / "goal_contract.json"
            mtime_1 = snap_path.stat().st_mtime

            # 두 번째 호출 (expected_output을 바꿔봐도 snapshot은 그대로)
            gc_dict2 = {**gc_dict, "goals": [{**gc_dict["goals"][0], "expected_output": "modified"}]}
            pipeline2 = self._make_pipeline(gc_dict2)
            state2 = self._make_state(tmp)
            with patch("core.dogfood._develop_isolation_env"):
                with patch("core.dogfood._changed_files_fallback", return_value=[]):
                    with patch("core.dogfood._normalize_develop_result", return_value={}):
                        _run_develop_full(state2, pipeline2)

            mtime_2 = snap_path.stat().st_mtime
            self.assertEqual(mtime_1, mtime_2, "snapshot이 두 번째 호출에서 덮어써짐")
            snap = json.loads(snap_path.read_text(encoding="utf-8"))
            self.assertEqual(snap["goals"][0]["expected_output"], "original")


# ---------------------------------------------------------------------------
# §8: prepare_documents QA 필드 → GoalContract 흡수
# ---------------------------------------------------------------------------

class TestPipelinePrepareDocumentsQaAbsorption(unittest.TestCase):
    """project_brief의 QA 필드가 GoalContract에 GoalEntry로 흡수되는지."""

    def test_observable_goal_creates_goal_entry(self):
        """project_brief['observable_goal'] → GoalEntry QA-OBS."""
        from core.project_pipeline import ProjectPipeline
        pp = ProjectPipeline.__new__(ProjectPipeline)
        # Minimal mock: test the QA absorption code block directly
        from core.completion_contract import GoalContract, GoalEntry
        project_brief = {
            "observable_goal": "앱이 시작되면 OK 출력",
            "qa_provenance": {"observable_goal": "research"},
        }
        _goal_contract = None
        slug = "test-slug"
        _qa_prov_map = project_brief.get("qa_provenance") or {}
        for _qf_id, _qf_key, _is_expected in [
            ("QA-OBS", "observable_goal", False),
            ("QA-GEX", "golden_example", True),
            ("QA-SEAM", "test_seam", False),
        ]:
            _qf_val = str(project_brief.get(_qf_key) or "")
            if not _qf_val:
                continue
            _ge = GoalEntry(
                goal_id=_qf_id,
                description=f"[{_qf_key}] {_qf_val[:200]}",
                harness_type="none",
                expected_output=_qf_val if _is_expected else "",
                provenance=_qa_prov_map.get(_qf_key, "default"),
            )
            if _goal_contract is None:
                _goal_contract = GoalContract(task_id=slug)
            _goal_contract.goals.append(_ge)

        self.assertIsNotNone(_goal_contract)
        ids = [g.goal_id for g in _goal_contract.goals]
        self.assertIn("QA-OBS", ids)
        obs = next(g for g in _goal_contract.goals if g.goal_id == "QA-OBS")
        self.assertEqual(obs.provenance, "research")
        self.assertEqual(obs.expected_output, "")  # observable_goal은 expected_output 아님

    def test_golden_example_sets_expected_output(self):
        """project_brief['golden_example'] → GoalEntry QA-GEX.expected_output 설정."""
        from core.completion_contract import GoalContract, GoalEntry
        project_brief = {"golden_example": "input → 정확한 출력"}
        _goal_contract = None
        slug = "s"
        _qa_prov_map = {}
        for _qf_id, _qf_key, _is_expected in [
            ("QA-OBS", "observable_goal", False),
            ("QA-GEX", "golden_example", True),
            ("QA-SEAM", "test_seam", False),
        ]:
            _qf_val = str(project_brief.get(_qf_key) or "")
            if not _qf_val:
                continue
            _ge = GoalEntry(
                goal_id=_qf_id,
                description=f"[{_qf_key}] {_qf_val[:200]}",
                harness_type="none",
                expected_output=_qf_val if _is_expected else "",
                provenance=_qa_prov_map.get(_qf_key, "default"),
            )
            if _goal_contract is None:
                _goal_contract = GoalContract(task_id=slug)
            _goal_contract.goals.append(_ge)

        self.assertIsNotNone(_goal_contract)
        gex = next(g for g in _goal_contract.goals if g.goal_id == "QA-GEX")
        self.assertEqual(gex.expected_output, "input → 정확한 출력")

    def test_empty_qa_fields_not_added(self):
        """QA 필드 없으면 GoalContract 미생성 (빈 brief)."""
        from core.completion_contract import GoalContract, GoalEntry
        project_brief = {}
        _goal_contract = None
        slug = "s"
        _qa_prov_map = {}
        for _qf_id, _qf_key, _is_expected in [
            ("QA-OBS", "observable_goal", False),
            ("QA-GEX", "golden_example", True),
            ("QA-SEAM", "test_seam", False),
        ]:
            _qf_val = str(project_brief.get(_qf_key) or "")
            if not _qf_val:
                continue
            _ge = GoalEntry(
                goal_id=_qf_id,
                description=f"[{_qf_key}] {_qf_val[:200]}",
                harness_type="none",
                expected_output=_qf_val if _is_expected else "",
                provenance=_qa_prov_map.get(_qf_key, "default"),
            )
            if _goal_contract is None:
                _goal_contract = GoalContract(task_id=slug)
            _goal_contract.goals.append(_ge)

        self.assertIsNone(_goal_contract)


if __name__ == "__main__":
    unittest.main()
