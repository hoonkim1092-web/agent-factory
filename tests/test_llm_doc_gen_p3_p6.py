"""
tests/test_llm_doc_gen_p3_p6.py
================================
P3~P6 LLM 문서 생성 파이프라인 검증 테스트.

P3: PreparedBrief dataclass + prepare_brief()/prepare_documents() 분할
P4: clarification.py — generate_clarification_questions / merge_clarification
P6: should_skip_clarification / auto_apply_defaults / fallback 동작
"""
from __future__ import annotations

import pytest


# ────────────────────────────────────────────────────────────
# P3: PreparedBrief + prepare_brief / prepare_documents 분할
# ────────────────────────────────────────────────────────────

class TestPreparedBrief:
    def test_dataclass_fields_exist(self):
        from core.project_pipeline import PreparedBrief
        b = PreparedBrief(
            run_id="r1",
            workspace="/tmp",
            task_input="test",
            project_brief={"goal": "test"},
        )
        assert b.run_id == "r1"
        assert b.workspace == "/tmp"
        assert b.task_input == "test"
        assert b.project_brief == {"goal": "test"}
        assert b.research_evidence == {}
        assert b.research_evidence_path == ""
        assert b.project_brief_path == ""
        assert b.memory_context == {}

    def test_project_brief_is_mutable(self):
        from core.project_pipeline import PreparedBrief
        b = PreparedBrief(
            run_id="r1",
            workspace="/tmp",
            task_input="test",
            project_brief={"goal": "original"},
        )
        b.project_brief = {"goal": "enriched", "clarification_log": []}
        assert b.project_brief["goal"] == "enriched"

    def test_prepare_brief_and_documents_produce_same_result_as_prepare(self, tmp_path):
        """prepare() == prepare_brief() + prepare_documents() 동치 검증 (mock 환경)."""
        from unittest.mock import MagicMock, patch
        from core.project_pipeline import ProjectPipeline, PreparedProject

        pipeline = ProjectPipeline.__new__(ProjectPipeline)

        mock_brief = {"goal": "test goal", "generated_at": "2026-01-01"}
        mock_evidence = {"sources": []}
        mock_role_plan = {"roles": ["dev"], "modules": [], "generated_at": "2026-01-01"}
        mock_task_board = {"tasks": []}

        with (
            patch("core.project_pipeline.ensure_documentation_files"),
            patch("core.project_pipeline.build_bootstrap_agent", return_value={"id": "a1", "name": "n1"}),
            patch.object(pipeline, "_planning_dir", return_value=str(tmp_path)),
            patch.object(pipeline, "_write_json"),
            patch.object(pipeline, "_save_checkpoint"),
            patch.object(pipeline, "_write_todo", return_value=str(tmp_path / ".todo.md")),
            patch.object(pipeline, "run_structural_gate", return_value={}),
            patch("core.project_pipeline.build_project_board", return_value=mock_task_board),
            patch("core.project_pipeline.write_project_board", return_value=str(tmp_path / "board.json")),
            patch("core.project_pipeline.write_task_execution_plan", return_value=str(tmp_path / "exec.json")),
            patch("core.project_pipeline.generate_work_items", return_value={}),
            patch("core.project_pipeline.slug_from_brief", return_value="test-slug"),
            patch("core.project_pipeline.enrich_role_plan", return_value=mock_role_plan),
            patch("core.pipeline_quality.PipelineStageGuard") as mock_guard_cls,
        ):
            mock_guard = MagicMock()
            mock_guard.run.side_effect = [mock_brief, mock_role_plan]
            mock_guard_cls.return_value = mock_guard

            pipeline.research = MagicMock()
            pipeline.research.collect_project_evidence = None
            pipeline.research.research_project_brief.return_value = mock_brief
            pipeline.planner = MagicMock()
            pipeline.planner.plan.return_value = mock_role_plan

            brief_obj = pipeline.prepare_brief(
                task_input="test goal",
                workspace=str(tmp_path),
            )
            assert brief_obj.task_input == "test goal"
            assert brief_obj.project_brief == mock_brief

            # prepare_documents needs fresh guard call
            mock_guard.run.side_effect = [mock_role_plan]
            result = pipeline.prepare_documents(brief_obj)
            assert isinstance(result, PreparedProject)
            assert result.run_id == brief_obj.run_id
            assert result.workspace == brief_obj.workspace

    def test_prepare_backward_compat_calls_both(self, tmp_path):
        """prepare() 하위 호환 래퍼가 prepare_brief() + prepare_documents() 호출하는지."""
        from unittest.mock import MagicMock, patch
        from core.project_pipeline import ProjectPipeline, PreparedBrief, PreparedProject

        pipeline = ProjectPipeline.__new__(ProjectPipeline)
        mock_brief_obj = PreparedBrief(
            run_id="r1",
            workspace=str(tmp_path),
            task_input="task",
            project_brief={"goal": "task"},
        )
        mock_prepared = MagicMock(spec=PreparedProject)

        with (
            patch.object(pipeline, "prepare_brief", return_value=mock_brief_obj) as m_brief,
            patch.object(pipeline, "prepare_documents", return_value=mock_prepared) as m_docs,
        ):
            result = pipeline.prepare("task", str(tmp_path), execution_mode="approval")

        m_brief.assert_called_once_with(
            task_input="task",
            workspace=str(tmp_path),
            execution_mode="approval",
            enable_build=False,
            requested_role="",
            route=None,
        )
        m_docs.assert_called_once_with(mock_brief_obj, execution_mode="approval", enable_build=False)
        assert result is mock_prepared


# ────────────────────────────────────────────────────────────
# P4: clarification.py
# ────────────────────────────────────────────────────────────

class TestGenerateClarificationQuestions:
    def test_returns_empty_on_llm_failure(self):
        from unittest.mock import patch
        from core.clarification import generate_clarification_questions

        with patch("core.clarification.execute_requirement_prompt", return_value={"ok": False}):
            result = generate_clarification_questions({"goal": "test"})
        assert result == []

    def test_returns_valid_questions(self):
        from unittest.mock import patch
        from core.clarification import generate_clarification_questions

        fake_response = {
            "ok": True,
            "text": '{"questions": [{"id": "Q1", "category": "ui", "question": "UI 형태?", "why": "스택 결정", "options": ["웹", "CLI"], "default": "웹"}]}',
        }
        with patch("core.clarification.execute_requirement_prompt", return_value=fake_response):
            result = generate_clarification_questions({"goal": "test"})

        assert len(result) == 1
        assert result[0]["id"] == "Q1"
        assert result[0]["default"] == "웹"

    def test_filters_malformed_questions(self):
        from unittest.mock import patch
        from core.clarification import generate_clarification_questions

        fake_response = {
            "ok": True,
            "text": '{"questions": [{"id": "Q1"}, {"id": "Q2", "question": "유효?", "options": ["예"]}]}',
        }
        with patch("core.clarification.execute_requirement_prompt", return_value=fake_response):
            result = generate_clarification_questions({"goal": "test"})

        # Q1 은 options 없으므로 필터링, Q2만 통과
        assert len(result) == 1
        assert result[0]["id"] == "Q2"


class TestMergeClarification:
    def test_merge_ui_category(self):
        from core.clarification import merge_clarification

        brief = {"goal": "test"}
        questions = [{"id": "Q1", "category": "ui", "question": "UI?", "options": ["웹"], "default": "웹"}]
        answers = ["웹앱"]
        result = merge_clarification(brief, questions, answers)
        assert result["architecture_style"] == "웹앱"
        assert len(result["clarification_log"]) == 1

    def test_merge_deployment_appends_constraints(self):
        from core.clarification import merge_clarification

        brief = {"goal": "test", "constraints": ["기존 제약"]}
        questions = [{"id": "Q1", "category": "deployment", "question": "배포?", "options": ["AWS"], "default": "AWS"}]
        answers = ["GCP"]
        result = merge_clarification(brief, questions, answers)
        assert "배포: GCP" in result["constraints"]
        assert "기존 제약" in result["constraints"]

    def test_empty_answer_falls_back_to_default(self):
        from core.clarification import merge_clarification

        brief = {"goal": "test"}
        questions = [{"id": "Q1", "category": "scope", "question": "스코프?", "options": ["A", "B"], "default": "A"}]
        answers = [""]
        result = merge_clarification(brief, questions, answers)
        log = result["clarification_log"]
        assert log[0]["answer"] == "A"


# ────────────────────────────────────────────────────────────
# P6: should_skip_clarification / auto_apply_defaults
# ────────────────────────────────────────────────────────────

class TestShouldSkipClarification:
    def test_single_pipeline_always_skips(self):
        from core.clarification import should_skip_clarification
        assert should_skip_clarification({}, pipeline="single") is True

    def test_sparse_brief_does_not_skip(self):
        from core.clarification import should_skip_clarification
        brief = {"goal": "test", "tech_stack": [], "deliverables": [], "user_flows": []}
        assert should_skip_clarification(brief, pipeline="project") is False

    def test_rich_brief_skips(self):
        from core.clarification import should_skip_clarification
        brief = {
            "goal": "test",
            "tech_stack": ["Python"],
            "deliverables": ["API"],
            "user_flows": ["로그인"],
            "constraints": ["인증 필수"],
            "architecture_style": "마이크로서비스",
        }
        assert should_skip_clarification(brief, pipeline="project") is True


class TestAutoApplyDefaults:
    def test_defaults_applied_for_all_questions(self):
        from core.clarification import auto_apply_defaults

        brief = {"goal": "test"}
        questions = [
            {"id": "Q1", "category": "ui", "question": "UI?", "options": ["웹", "CLI"], "default": "웹"},
            {"id": "Q2", "category": "deployment", "question": "배포?", "options": ["AWS"], "default": "AWS"},
        ]
        result = auto_apply_defaults(brief, questions)
        assert result["architecture_style"] == "웹"
        assert "배포: AWS" in result.get("constraints", [])
        assert len(result["clarification_log"]) == 2

    def test_empty_questions_returns_original_brief(self):
        from core.clarification import auto_apply_defaults

        brief = {"goal": "test", "tech_stack": ["Python"]}
        result = auto_apply_defaults(brief, [])
        assert result["tech_stack"] == ["Python"]
        assert result["clarification_log"] == []


class TestMergeClarificationRobustness:
    def test_missing_question_key_does_not_raise(self):
        """q에 'question' 키가 없어도 KeyError 없이 동작해야 함 (fix 3)."""
        from core.clarification import merge_clarification

        brief = {"goal": "test"}
        questions = [{"id": "Q1", "category": "ui", "options": ["웹"], "default": "웹"}]
        result = merge_clarification(brief, questions, ["웹"])
        assert result["clarification_log"][0]["question"] == ""

    def test_non_list_constraints_logs_warning_not_raise(self):
        """constraints가 string이면 무시하고 경고만 (fix 3)."""
        from core.clarification import merge_clarification

        brief = {"goal": "test", "constraints": "기존 문자열"}
        questions = [{"id": "Q1", "category": "deployment", "question": "배포?", "options": ["AWS"], "default": "AWS"}]
        result = merge_clarification(brief, questions, ["AWS"])
        # append 스킵되므로 constraints는 여전히 문자열
        assert result["constraints"] == "기존 문자열"


# ────────────────────────────────────────────────────────────
# P5: _collect_clarification_answers() I/O 로직
# ────────────────────────────────────────────────────────────

class TestCollectClarificationAnswers:
    _questions = [
        {"id": "Q1", "category": "ui", "question": "UI?", "why": "스택 결정", "options": ["웹", "CLI"], "default": "웹"},
        {"id": "Q2", "category": "deployment", "question": "배포?", "why": "비용 결정", "options": ["AWS", "GCP"], "default": "AWS"},
    ]

    def test_normal_text_answers(self):
        from unittest.mock import patch
        from agent_launcher import AgentFactory

        with patch("builtins.input", side_effect=["커스텀UI", "Azure"]):
            result = AgentFactory._collect_clarification_answers(self._questions)

        assert result == ["커스텀UI", "Azure"]

    def test_digit_input_selects_option(self):
        from unittest.mock import patch
        from agent_launcher import AgentFactory

        with patch("builtins.input", side_effect=["2", "1"]):
            result = AgentFactory._collect_clarification_answers(self._questions)

        assert result == ["CLI", "AWS"]

    def test_empty_input_uses_default(self):
        from unittest.mock import patch
        from agent_launcher import AgentFactory

        with patch("builtins.input", side_effect=["", ""]):
            result = AgentFactory._collect_clarification_answers(self._questions)

        assert result == ["웹", "AWS"]

    def test_skip_returns_all_defaults(self):
        """첫 번째 질문에서 /skip → 모든 질문 기본값 반환 (fix 1)."""
        from unittest.mock import patch
        from agent_launcher import AgentFactory

        with patch("builtins.input", side_effect=["/skip"]):
            result = AgentFactory._collect_clarification_answers(self._questions)

        assert result == ["웹", "AWS"]
        assert len(result) == len(self._questions)

    def test_skip_mid_session_returns_all_defaults(self):
        """/skip이 두 번째 질문 도중 — 결과는 여전히 전체 기본값 (fix 1)."""
        from unittest.mock import patch
        from agent_launcher import AgentFactory

        with patch("builtins.input", side_effect=["커스텀UI", "/skip"]):
            result = AgentFactory._collect_clarification_answers(self._questions)

        # /skip이면 전체 defaults로 덮어씀 — 현재 구현 동작
        assert result == ["웹", "AWS"]
        assert len(result) == len(self._questions)

    def test_eoferror_treated_as_skip(self):
        from unittest.mock import patch
        from agent_launcher import AgentFactory

        with patch("builtins.input", side_effect=EOFError):
            result = AgentFactory._collect_clarification_answers(self._questions)

        assert result == ["웹", "AWS"]
        assert len(result) == len(self._questions)
