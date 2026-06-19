"""Q-S3 경로 C 활성화 테스트 — INV-Q6/Q7/Q8 (설계 §6.3, §11)."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core.clarification import (
    synthesize_research_answers,
    synthesize_via_research,
)
from core.control.question_router import (
    BriefBackedQuestionCaller,
    Question,
    QuestionResult,
    QuestionRouter,
    QuestionRouterLLMCaller,
)
from core.control.verdicts import QuestionRoute
from core.control.stage_artifacts import ProjectGoalArtifact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rs_question(output_field: str) -> Question:
    return Question(
        id=output_field,
        text="",
        output_field=output_field,
        default_route=QuestionRoute.RESEARCH_SYNTHESIZE,
    )


def _make_llm_question(
    output_field: str,
    required: bool = False,
    fallback: Any = None,
) -> Question:
    return Question(
        id=output_field,
        text="",
        output_field=output_field,
        required=required,
        fallback=fallback,
        default_route=QuestionRoute.LLM_DELEGATE,
    )


DUMMY_SCHEMA = {
    "question_set_id": "goal_clarification",
    "schema_version": 1,
    "questions": [],
}


# ---------------------------------------------------------------------------
# INV-Q6: BriefBackedQuestionCaller — HITL 0 보장
# ---------------------------------------------------------------------------

class TestBriefBackedCaller:
    def test_returns_goal_summary_always(self):
        """goal_summary는 항상 반환 — brief["goal"] 사용."""
        caller = BriefBackedQuestionCaller({"goal": "build a CLI tool"})
        result = caller.batch_route(
            [_make_llm_question("goal_summary", required=True)], {}, 30.0
        )
        assert result.get("goal_summary") == "build a CLI tool"

    def test_returns_deployment_target_always(self):
        """deployment_target은 항상 반환 — 부재 시 'development' fallback."""
        caller = BriefBackedQuestionCaller({})
        result = caller.batch_route(
            [_make_llm_question("deployment_target", required=True)], {}, 30.0
        )
        assert result.get("deployment_target") == "development"

    def test_deployment_target_from_constraints(self):
        """constraints에 '배포:' 항목이 있으면 추출."""
        brief = {"goal": "x", "constraints": ["배포: production", "기타: 제한없음"]}
        caller = BriefBackedQuestionCaller(brief)
        result = caller.batch_route(
            [_make_llm_question("deployment_target")], {}, 30.0
        )
        assert result.get("deployment_target") == "production"

    def test_success_criteria_from_deliverables(self):
        """deliverables이 있으면 success_criteria로 매핑."""
        brief = {"goal": "x", "deliverables": ["feature A", "feature B"]}
        caller = BriefBackedQuestionCaller(brief)
        result = caller.batch_route(
            [_make_llm_question("success_criteria")], {}, 30.0
        )
        assert result.get("success_criteria") == ["feature A", "feature B"]

    def test_does_not_raise_on_empty_brief(self):
        """빈 brief에서도 예외 없이 fallback 반환."""
        caller = BriefBackedQuestionCaller({})
        result = caller.batch_route([], {}, 30.0)
        assert isinstance(result, dict)

    def test_no_hitl_when_used_in_router(self):
        """BriefBackedQuestionCaller를 QuestionRouter에 주입하면 HITL 0 (INV-Q6)."""
        brief = {"goal": "make something", "deliverables": ["thing"]}
        caller = BriefBackedQuestionCaller(brief)
        router = QuestionRouter(llm_caller=caller)
        questions = [
            _make_llm_question("goal_summary", required=True),
            _make_llm_question("deployment_target", required=True),
        ]
        result = router.route_batch(questions, DUMMY_SCHEMA, "", "single_file")
        assert result.paused_hitl_ids == []
        assert result.block_results == []


# ---------------------------------------------------------------------------
# INV-Q6: route_batch HITL 0 on skip (경로 C 활성화 전체 경로)
# ---------------------------------------------------------------------------

class TestPathCNoHitlOnSkip:
    def test_path_c_no_hitl_with_brief_backed_caller(self):
        """경로 C 활성화 시 llm_delegate 필수 질문에서 HITL 미발생 (INV-Q6)."""
        brief = {"goal": "deploy API", "constraints": ["배포: AWS"]}
        caller = BriefBackedQuestionCaller(brief)
        router = QuestionRouter(llm_caller=caller)
        questions = [
            _make_llm_question("goal_summary", required=True),
            _make_llm_question("deployment_target", required=True),
            _make_llm_question("success_criteria"),
        ]
        batch = router.route_batch(questions, DUMMY_SCHEMA, "", "cross_module")
        assert batch.paused_hitl_ids == []
        goal_r = next(r for r in batch.results if r.output_field == "goal_summary")
        assert goal_r.question_route == QuestionRoute.LLM_DELEGATE
        assert goal_r.value == "deploy API"
        deploy_r = next(r for r in batch.results if r.output_field == "deployment_target")
        assert deploy_r.value == "AWS"


# ---------------------------------------------------------------------------
# INV-Q7: QuestionResult.provenance 전파
# ---------------------------------------------------------------------------

class TestQuestionResultProvenance:
    def test_provenance_default_on_pending(self):
        """synthesizer 없으면 RESEARCH_SYNTHESIZE는 provenance=default (pending)."""
        router = QuestionRouter()
        questions = [_make_rs_question("observable_goal")]
        result = router.route_batch(questions, DUMMY_SCHEMA, "", "single_file")
        r = result.results[0]
        assert r.provenance == "default"
        assert r.source == "research_synthesize_pending"
        assert r.value is None

    def test_provenance_research_on_synthesized(self):
        """synthesizer가 값을 반환하면 provenance=research."""
        synthesizer = lambda qs: {"observable_goal": "CLI exits 0"}
        router = QuestionRouter(synthesizer=synthesizer)
        questions = [_make_rs_question("observable_goal")]
        result = router.route_batch(questions, DUMMY_SCHEMA, "", "single_file")
        r = result.results[0]
        assert r.provenance == "research"
        assert r.value == "CLI exits 0"
        assert r.source == "research_synthesize"

    def test_provenance_default_on_synthesizer_returns_empty(self):
        """synthesizer가 빈 dict 반환 → provenance=default."""
        synthesizer = lambda qs: {}
        router = QuestionRouter(synthesizer=synthesizer)
        questions = [_make_rs_question("golden_example")]
        result = router.route_batch(questions, DUMMY_SCHEMA, "", "single_file")
        r = result.results[0]
        assert r.provenance == "default"

    def test_provenance_default_on_synthesizer_exception(self):
        """synthesizer 예외 → provenance=default (무정지)."""
        def bad_synthesizer(qs):
            raise RuntimeError("oops")

        router = QuestionRouter(synthesizer=bad_synthesizer)
        questions = [_make_rs_question("test_seam")]
        result = router.route_batch(questions, DUMMY_SCHEMA, "", "single_file")
        r = result.results[0]
        assert r.provenance == "default"
        assert r.value is None

    def test_multiple_rs_questions_batch(self):
        """여러 RESEARCH_SYNTHESIZE 질문이 1회 synthesizer 호출로 처리됨."""
        call_count = {"n": 0}

        def counting_synthesizer(qs):
            call_count["n"] += 1
            return {q.output_field: f"val_{q.output_field}" for q in qs}

        router = QuestionRouter(synthesizer=counting_synthesizer)
        questions = [
            _make_rs_question("observable_goal"),
            _make_rs_question("golden_example"),
            _make_rs_question("test_seam"),
            _make_rs_question("manual_only"),
        ]
        result = router.route_batch(questions, DUMMY_SCHEMA, "", "single_file")
        assert call_count["n"] == 1
        for r in result.results:
            assert r.provenance == "research"
            assert r.value == f"val_{r.output_field}"


# ---------------------------------------------------------------------------
# INV-Q7: ProjectGoalArtifact 4필드 + qa_provenance
# ---------------------------------------------------------------------------

class TestProjectGoalArtifactQaFields:
    def test_artifact_has_qa_fields(self):
        """ProjectGoalArtifact에 4 QA 필드 + qa_provenance 존재 (additive)."""
        a = ProjectGoalArtifact(
            artifact_type="project_goal",
            question_set_id="goal_clarification",
            schema_version=1,
            schema_hash="abc",
            work_kind="new_project",
            goal_summary="goal",
            deployment_target="dev",
        )
        assert hasattr(a, "observable_goal")
        assert hasattr(a, "golden_example")
        assert hasattr(a, "test_seam")
        assert hasattr(a, "manual_only")
        assert hasattr(a, "qa_provenance")
        # additive defaults
        assert a.observable_goal == ""
        assert a.qa_provenance == {}

    def test_artifact_with_qa_values(self):
        """4 QA 필드가 값 설정/조회 가능."""
        a = ProjectGoalArtifact(
            artifact_type="project_goal",
            question_set_id="gc",
            schema_version=1,
            schema_hash="x",
            work_kind="new_project",
            goal_summary="g",
            deployment_target="d",
            observable_goal="CLI exits 0",
            golden_example="af sandbox off → disabled",
            test_seam="--dry-run flag",
            manual_only="physical device tests",
            qa_provenance={"observable_goal": "research", "golden_example": "default"},
        )
        assert a.observable_goal == "CLI exits 0"
        assert a.qa_provenance["observable_goal"] == "research"


# ---------------------------------------------------------------------------
# INV-Q7: stage_router._write_project_goal — 4필드 수집
# ---------------------------------------------------------------------------

class TestWriteProjectGoalQaFields:
    def test_write_project_goal_collects_qa_fields(self, tmp_path):
        """_write_project_goal가 RESEARCH_SYNTHESIZE 결과를 4필드+provenance에 수집."""
        from core.control.stage_router import _render_project_goal
        from core.control.question_router import QuestionBatchResult

        results = [
            QuestionResult(
                question_id="goal_summary",
                output_field="goal_summary",
                question_route=QuestionRoute.LLM_DELEGATE,
                value="build CLI",
                source="llm_delegate",
            ),
            QuestionResult(
                question_id="deployment_target",
                output_field="deployment_target",
                question_route=QuestionRoute.LLM_DELEGATE,
                value="development",
                source="llm_delegate",
            ),
            QuestionResult(
                question_id="observable_goal",
                output_field="observable_goal",
                question_route=QuestionRoute.RESEARCH_SYNTHESIZE,
                value="exit code 0",
                source="research_synthesize",
                provenance="research",
            ),
            QuestionResult(
                question_id="golden_example",
                output_field="golden_example",
                question_route=QuestionRoute.RESEARCH_SYNTHESIZE,
                value="",
                source="research_synthesize_pending",
                provenance="default",
            ),
        ]
        batch = QuestionBatchResult(
            question_set_id="goal_clarification",
            schema_version=1,
            schema_hash="abc",
            results=results,
        )

        from core.control.stage_router import StageRouter
        from unittest.mock import MagicMock
        sr = StageRouter.__new__(StageRouter)

        path = sr._write_project_goal(str(tmp_path), batch, "single_file")
        content = open(path, encoding="utf-8").read()

        assert "exit code 0" in content
        assert "research" in content
        assert "default" in content
        assert "Observable Goal" in content
        assert "Golden Example" in content

    def test_render_project_goal_has_qa_sections(self):
        """_render_project_goal에 4개 QA 섹션 + provenance 뱃지 포함."""
        from core.control.stage_router import _render_project_goal

        a = ProjectGoalArtifact(
            artifact_type="project_goal",
            question_set_id="gc",
            schema_version=1,
            schema_hash="x",
            work_kind="new_project",
            goal_summary="g",
            deployment_target="d",
            observable_goal="observable",
            golden_example="golden",
            test_seam="seam",
            manual_only="manual",
            qa_provenance={
                "observable_goal": "research",
                "golden_example": "default",
                "test_seam": "research",
                "manual_only": "default",
            },
        )
        rendered = _render_project_goal(a)
        assert "## Observable Goal" in rendered
        assert "[출처: research]" in rendered
        assert "## Golden Example" in rendered
        assert "[출처: default]" in rendered
        assert "## Test Seam" in rendered
        assert "## Manual Only" in rendered
        assert "observable" in rendered
        assert "seam" in rendered


# ---------------------------------------------------------------------------
# INV-Q8: generate_work_items가 question_router 실주입
# ---------------------------------------------------------------------------

class TestGenerateWorkItemsPassesQuestionRouter:
    def test_generate_work_items_passes_question_router(self, tmp_path):
        """generate_work_items가 StageRouter.run()에 question_router를 전달 (INV-Q8)."""
        called_with: dict = {}

        class FakeStageRouter:
            def __init__(self, workspace, run_ledger):
                pass

            def run(self, **kwargs):
                called_with.update(kwargs)
                return {}

        class FakeRunLedger:
            def __init__(self, workspace):
                pass

        brief = {"goal": "test goal", "target_path": str(tmp_path)}

        import core.work_item_generator as wig
        with (
            patch.object(wig, "_LOGGER"),
            patch("core.control.stage_router.StageRouter", FakeStageRouter),
            patch("core.control.run_ledger.RunLedger", FakeRunLedger),
        ):
            try:
                wig.generate_work_items(
                    workspace=str(tmp_path),
                    slug="test-slug",
                    project_brief=brief,
                    role_plan={},
                    task_board={},
                    run_id="run1",
                    work_kind="new_project",
                    blast_radius="single_file",
                )
            except Exception:
                pass  # 후속 스테이지 실패는 무관

        assert "question_router" in called_with, "question_router가 StageRouter.run()에 전달되지 않음"
        qr = called_with["question_router"]
        from core.control.question_router import QuestionRouter
        assert isinstance(qr, QuestionRouter)


# ---------------------------------------------------------------------------
# synthesize_research_answers / synthesize_via_research
# ---------------------------------------------------------------------------

class TestSynthesizeResearchAnswers:
    def test_returns_empty_on_llm_failure(self):
        """LLM 실패 시 빈 dict 반환 (무정지)."""
        with patch("core.clarification.execute_requirement_prompt") as mock_llm:
            mock_llm.return_value = {"ok": False}
            result = synthesize_research_answers("goal", [])
        assert result == {}

    def test_returns_empty_on_bad_json(self):
        """JSON 파싱 실패 시 빈 dict."""
        with patch("core.clarification.execute_requirement_prompt") as mock_llm:
            mock_llm.return_value = {"ok": True, "text": "not json"}
            result = synthesize_research_answers("goal", [])
        assert result == {}

    def test_extracts_qa_fields(self):
        """올바른 JSON 응답에서 4 QA 필드 추출."""
        import json
        payload = json.dumps({
            "observable_goal": "CLI exits 0",
            "golden_example": "input → output",
            "test_seam": "--dry-run",
            "manual_only": "none",
        })
        with patch("core.clarification.execute_requirement_prompt") as mock_llm:
            mock_llm.return_value = {"ok": True, "text": payload}
            result = synthesize_research_answers("make CLI", [])
        assert result["observable_goal"] == "CLI exits 0"
        assert result["golden_example"] == "input → output"
        assert result["test_seam"] == "--dry-run"
        assert result["manual_only"] == "none"

    def test_skips_empty_values(self):
        """빈 문자열 값은 결과에서 제외."""
        import json
        payload = json.dumps({
            "observable_goal": "CLI exits 0",
            "golden_example": "",
            "test_seam": "  ",
            "manual_only": "manual check",
        })
        with patch("core.clarification.execute_requirement_prompt") as mock_llm:
            mock_llm.return_value = {"ok": True, "text": payload}
            result = synthesize_research_answers("goal", [])
        assert "observable_goal" in result
        assert "golden_example" not in result
        assert "test_seam" not in result
        assert "manual_only" in result


class TestSynthesizeViaResearch:
    def test_research_provenance_on_success(self):
        """합성 성공 시 clarification_log에 provenance=research."""
        import json
        payload = json.dumps({"observable_goal": "CLI exits 0"})
        with patch("core.clarification.execute_requirement_prompt") as mock_llm:
            mock_llm.return_value = {"ok": True, "text": payload}
            result = synthesize_via_research(
                {"goal": "make CLI"}, []
            )
        log = result.get("clarification_log", [])
        for entry in log:
            assert entry.get("provenance") == "research"

    def test_default_provenance_on_failure(self):
        """합성 실패 시 clarification_log에 provenance=default."""
        with patch("core.clarification.execute_requirement_prompt") as mock_llm:
            mock_llm.return_value = {"ok": False}
            result = synthesize_via_research({"goal": "x"}, [])
        log = result.get("clarification_log", [])
        for entry in log:
            assert entry.get("provenance") == "default"

    def test_returns_enriched_dict(self):
        """synthesize_via_research는 enriched dict 반환 (goal 포함)."""
        with patch("core.clarification.execute_requirement_prompt") as mock_llm:
            mock_llm.return_value = {"ok": False}
            result = synthesize_via_research({"goal": "my goal"}, [])
        assert result.get("goal") == "my goal"
