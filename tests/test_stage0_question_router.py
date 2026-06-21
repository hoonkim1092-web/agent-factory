"""Stage 0 Question Router P1 테스트 (설계 §14 P1, P1.5, P1.6, P5)."""
from __future__ import annotations

import os
import tempfile
import textwrap

import pytest

from core.control.verdicts import BlockCause, DomainVerdict, QuestionRoute
from core.control.stage_artifacts import (
    AssumptionLedgerEntry,
    ContextScanArtifact,
    DomainReviewArtifact,
    PausedHitlArtifact,
    PausedHitlQuestion,
    ProjectGoalArtifact,
)
from core.control.question_router import (
    Question,
    QuestionBatchResult,
    QuestionResult,
    QuestionRouter,
    QuestionRouterLLMCaller,
    _validate_schema,
    load_question_schema,
    parse_questions,
)
from core.control.context_scanner import LightContextScanner


# ===========================================================================
# verdicts.py — enum 단일 원천
# ===========================================================================

class TestVerdicts:
    def test_question_route_values(self):
        assert QuestionRoute.PASS.value == "pass"
        assert QuestionRoute.LLM_DELEGATE.value == "llm_delegate"
        assert QuestionRoute.HITL.value == "hitl"
        assert QuestionRoute.BLOCK.value == "block"

    def test_domain_verdict_values(self):
        assert DomainVerdict.PASS.value == "pass"
        assert DomainVerdict.NEEDS_ADR.value == "needs_adr"
        assert DomainVerdict.BLOCK.value == "block"

    def test_block_cause_values(self):
        causes = {c.value for c in BlockCause}
        assert causes == {
            "missing_required_input",
            "design_conflict",
            "high_risk",
            "policy_violation",
            "safety",
        }


# ===========================================================================
# stage_artifacts.py — dataclass 구조
# ===========================================================================

class TestStageArtifacts:
    def test_context_scan_artifact_defaults(self):
        a = ContextScanArtifact(
            artifact_type="context_scan",
            schema_version=1,
            schema_hash="abc",
            work_dir="/tmp/x",
            work_kind="maintenance",
            blast_radius="module",
        )
        assert a.relevant_files == []
        assert a.existing_tests == []

    def test_domain_review_artifact_with_verdict(self):
        a = DomainReviewArtifact(
            artifact_type="domain_review",
            question_set_id="brainstorming",
            schema_version=1,
            schema_hash="abc",
            domain_verdict=DomainVerdict.NEEDS_ADR,
            block_cause=None,
        )
        assert a.domain_verdict == DomainVerdict.NEEDS_ADR
        assert a.block_cause is None

    def test_paused_hitl_artifact_structure(self):
        q = PausedHitlQuestion(question_set_id="goal_clarification", question_id="q1")
        a = PausedHitlArtifact(
            artifact_type="paused_hitl",
            status="paused_hitl",
            terminal_success=False,
            report_required=True,
            questions=[q],
            schema_version=1,
            schema_hash="def",
            resume_entrypoint="ProjectPipeline",
            reason="needs HITL",
        )
        assert a.terminal_success is False
        assert a.questions[0].question_id == "q1"

    def test_assumption_ledger_entry(self):
        e = AssumptionLedgerEntry(
            artifact_type="assumption",
            schema_version=1,
            schema_hash="abc",
            timestamp="2026-05-14T00:00:00+00:00",
            question_set_id="brainstorming",
            question_id="deployment_target",
            output_field="deployment_target",
            value="production",
            source="llm_delegate",
        )
        assert e.source == "llm_delegate"
        assert e.question_set_id == "brainstorming"


# ===========================================================================
# question_router.py — YAML validation
# ===========================================================================

class TestYAMLValidation:
    def _make_yaml(self, content: str) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(textwrap.dedent(content))
            return f.name

    def test_valid_schema_loads(self):
        path = self._make_yaml("""\
            schema_version: 1
            question_set_id: test_set
            questions:
              - id: q1
                text: "질문?"
                output_field: q1
                required: true
                fallback: null
                default_route: llm_delegate
                block_category_if_missing: missing_required_input
        """)
        schema, sha = load_question_schema(path)
        os.unlink(path)
        assert schema["question_set_id"] == "test_set"
        assert len(sha) == 64

    def test_missing_schema_version_fails(self):
        schema = {"question_set_id": "x", "questions": []}
        with pytest.raises(ValueError, match="schema_version"):
            _validate_schema(schema, "test")

    def test_missing_question_set_id_fails(self):
        schema = {"schema_version": 1, "questions": []}
        with pytest.raises(ValueError, match="question_set_id"):
            _validate_schema(schema, "test")

    def test_duplicate_question_id_fails(self):
        schema = {
            "schema_version": 1,
            "question_set_id": "x",
            "questions": [
                {"id": "q1", "output_field": "q1", "default_route": "llm_delegate"},
                {"id": "q1", "output_field": "q1", "default_route": "llm_delegate"},
            ],
        }
        with pytest.raises(ValueError, match="중복"):
            _validate_schema(schema, "test")

    def test_invalid_default_route_fails(self):
        schema = {
            "schema_version": 1,
            "question_set_id": "x",
            "questions": [
                {"id": "q1", "output_field": "q1", "default_route": "invalid_route"}
            ],
        }
        with pytest.raises(ValueError, match="QuestionRoute"):
            _validate_schema(schema, "test")

    def test_invalid_block_category_fails(self):
        schema = {
            "schema_version": 1,
            "question_set_id": "x",
            "questions": [
                {
                    "id": "q1",
                    "output_field": "q1",
                    "default_route": "llm_delegate",
                    "required": True,
                    "block_category_if_missing": "bad_cause",
                }
            ],
        }
        with pytest.raises(ValueError, match="BlockCause"):
            _validate_schema(schema, "test")

    def test_required_without_block_category_fails(self):
        schema = {
            "schema_version": 1,
            "question_set_id": "x",
            "questions": [
                {
                    "id": "q1",
                    "output_field": "q1",
                    "default_route": "llm_delegate",
                    "required": True,
                }
            ],
        }
        with pytest.raises(ValueError, match="block_category_if_missing"):
            _validate_schema(schema, "test")

    def test_forbidden_routing_metadata_fails(self):
        schema = {
            "schema_version": 1,
            "question_set_id": "x",
            "questions": [
                {"id": "q1", "output_field": "q1", "default_route": "llm_delegate", "risk": "high"}
            ],
        }
        with pytest.raises(ValueError, match="허용되지 않은"):
            _validate_schema(schema, "test")


# ===========================================================================
# QuestionRouter — route 로직
# ===========================================================================

class _FakeLLM(QuestionRouterLLMCaller):
    def __init__(self, answers: dict):
        self._answers = answers

    def batch_route(self, questions, context, timeout_sec):
        return {q.id: self._answers.get(q.id) for q in questions}


class _FailLLM(QuestionRouterLLMCaller):
    def batch_route(self, questions, context, timeout_sec):
        raise TimeoutError("llm timeout")


def _make_schema(questions: list[dict]) -> dict:
    return {"schema_version": 1, "question_set_id": "test", "questions": questions}


class TestQuestionRouterRouting:
    def test_hitl_route_goes_to_paused(self):
        router = QuestionRouter()
        schema = _make_schema([
            {
                "id": "sensitive_q",
                "output_field": "sensitive_q",
                "default_route": "hitl",
                "text": "sensitive?",
            }
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "module")
        assert "sensitive_q" in result.paused_hitl_ids

    def test_llm_delegate_uses_fake_llm(self):
        llm = _FakeLLM({"q1": "prod"})
        router = QuestionRouter(llm_caller=llm)
        schema = _make_schema([
            {
                "id": "q1",
                "output_field": "q1",
                "default_route": "llm_delegate",
                "text": "target?",
            }
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "isolated")
        r = next(r for r in result.results if r.question_id == "q1")
        assert r.value == "prod"
        assert r.source == "llm_delegate"

    def test_llm_failure_required_no_fallback_promotes_hitl(self):
        llm = _FailLLM()
        router = QuestionRouter(llm_caller=llm)
        schema = _make_schema([
            {
                "id": "q1",
                "output_field": "q1",
                "default_route": "llm_delegate",
                "required": True,
                "block_category_if_missing": "missing_required_input",
            }
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "module")
        assert "q1" in result.paused_hitl_ids

    def test_llm_failure_optional_with_fallback_uses_fallback(self):
        llm = _FailLLM()
        router = QuestionRouter(llm_caller=llm)
        schema = _make_schema([
            {
                "id": "q1",
                "output_field": "q1",
                "default_route": "llm_delegate",
                "required": False,
                "fallback": "development",
            }
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "isolated")
        r = next(r for r in result.results if r.question_id == "q1")
        assert r.used_fallback is True
        assert r.value == "development"

    def test_llm_failure_optional_no_fallback_skip(self):
        llm = _FailLLM()
        router = QuestionRouter(llm_caller=llm)
        schema = _make_schema([
            {"id": "q1", "output_field": "q1", "default_route": "llm_delegate", "required": False}
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "isolated")
        r = next(r for r in result.results if r.question_id == "q1")
        assert r.question_route == QuestionRoute.PASS

    def test_llm_failure_required_with_fallback_high_blast_promotes_hitl(self):
        llm = _FailLLM()
        router = QuestionRouter(llm_caller=llm)
        schema = _make_schema([
            {
                "id": "q1",
                "output_field": "q1",
                "default_route": "llm_delegate",
                "required": True,
                "fallback": "some_default",
                "block_category_if_missing": "missing_required_input",
            }
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "cross_module")
        assert "q1" in result.paused_hitl_ids

    def test_llm_invalid_block_cause_promotes_hitl(self):
        llm = _FakeLLM({"q1": {"block_cause": "not_a_valid_cause"}})
        router = QuestionRouter(llm_caller=llm)
        schema = _make_schema([
            {"id": "q1", "output_field": "q1", "default_route": "llm_delegate"}
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "isolated")
        r = next(r for r in result.results if r.question_id == "q1")
        assert r.question_route == QuestionRoute.HITL
        assert "llm_schema_violation" in r.warning


# ===========================================================================
# StageRouter — cross-yaml uniqueness
# ===========================================================================

class TestStageRouterCrossYamlUniqueness:
    def test_cross_yaml_id_collision_raises(self):
        from core.control.stage_router import StageRouter

        schemas = {
            "set_a": {
                "schema_version": 1,
                "question_set_id": "set_a",
                "questions": [{"id": "shared_id", "output_field": "shared_id", "default_route": "llm_delegate"}],
            },
            "set_b": {
                "schema_version": 1,
                "question_set_id": "set_b",
                "questions": [{"id": "shared_id", "output_field": "shared_id", "default_route": "llm_delegate"}],
            },
        }
        with tempfile.TemporaryDirectory() as ws:
            from core.control.run_ledger import RunLedger
            router = StageRouter.__new__(StageRouter)
            router._workspace = ws
            router._run_ledger = RunLedger(ws)
            with pytest.raises(RuntimeError, match="Cross-YAML question.id collision"):
                router._validate_cross_yaml_id_uniqueness(schemas)


# ===========================================================================
# ApprovalGate.initialize() — 시그니처 변경 (§8.3)
# ===========================================================================

class TestApprovalGateInitializeSignature:
    def test_initialize_default_status_backward_compatible(self, tmp_path):
        from core.approval_gate import ApprovalGate
        ws = str(tmp_path)
        gate = ApprovalGate(ws, "test-slug")
        gate.initialize(run_id="r1")
        content = (tmp_path / "docs" / "work-items" / "test-slug" / "approval-gate.md").read_text(encoding="utf-8")
        assert "review_pending" in content
        assert "execution_open: false" in content.lower() or "false" in content

    def test_initialize_with_paused_hitl_status(self, tmp_path):
        from core.approval_gate import ApprovalGate
        ws = str(tmp_path)
        gate = ApprovalGate(ws, "test-slug")
        gate.initialize(run_id="r1", status="paused_hitl", execution_open=False)
        content = (tmp_path / "docs" / "work-items" / "test-slug" / "approval-gate.md").read_text(encoding="utf-8")
        assert "paused_hitl" in content


# ===========================================================================
# LightContextScanner — LLM 0회
# ===========================================================================

class TestLightContextScanner:
    def test_scan_produces_artifact(self, tmp_path):
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "main.py").write_text("x = 1")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test_x(): pass")

        scanner = LightContextScanner()
        art = scanner.scan(str(tmp_path), "maintenance", "module", schema_hash="abc")
        assert art.artifact_type == "context_scan"
        assert any("main.py" in f for f in art.relevant_files)
        assert any("test_main.py" in t for t in art.existing_tests)

    def test_scan_no_llm_calls(self, tmp_path):
        scanner = LightContextScanner()
        art = scanner.scan(str(tmp_path), "bugfix", "isolated")
        assert art.work_kind == "bugfix"
        assert art.blast_radius == "isolated"


# ===========================================================================
# StageRouter.run() — work_kind 분기
# ===========================================================================

class TestStageRouterWorkKind:
    def _make_router(self, ws: str):
        from core.control.run_ledger import RunLedger
        from core.control.stage_router import StageRouter

        router = StageRouter.__new__(StageRouter)
        router._workspace = ws
        router._run_ledger = RunLedger(ws)
        router._active_schemas = {}
        router._schema_hashes = {}
        return router

    def test_empty_work_kind_returns_empty(self, tmp_path):
        ws = str(tmp_path)
        router = self._make_router(ws)
        result = router.run(work_dir=ws, work_kind="", blast_radius="isolated")
        assert result == {}

    def test_non_enum_work_kind_returns_empty(self, tmp_path):
        ws = str(tmp_path)
        router = self._make_router(ws)
        result = router.run(work_dir=ws, work_kind="unknown_kind", blast_radius="isolated")
        assert result == {}

    def test_new_project_no_yaml_returns_empty(self, tmp_path):
        ws = str(tmp_path)
        router = self._make_router(ws)
        result = router.run(work_dir=ws, work_kind="new_project", blast_radius="isolated")
        # YAML 없으면 빈 dict
        assert isinstance(result, dict)

    def test_maintenance_produces_context_scan(self, tmp_path):
        ws = str(tmp_path)
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir, exist_ok=True)
        router = self._make_router(ws)
        result = router.run(work_dir=work_dir, work_kind="maintenance", blast_radius="module")
        assert "context_scan" in result
        assert os.path.exists(result["context_scan"])

    def test_bugfix_produces_context_scan(self, tmp_path):
        ws = str(tmp_path)
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir, exist_ok=True)
        router = self._make_router(ws)
        result = router.run(work_dir=work_dir, work_kind="bugfix", blast_radius="isolated")
        assert "context_scan" in result

    def test_refactor_produces_context_scan(self, tmp_path):
        ws = str(tmp_path)
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir, exist_ok=True)
        router = self._make_router(ws)
        result = router.run(work_dir=work_dir, work_kind="refactor", blast_radius="cross_module")
        assert "context_scan" in result


# ===========================================================================
# 실제 YAML 파일 로드 + cross-yaml uniqueness (P4/P2)
# ===========================================================================

class TestActiveYamlFiles:
    """goal_clarification.yaml / brainstorming.yaml 실제 파일 검증."""

    def test_goal_clarification_yaml_loads(self):
        from pathlib import Path
        from core.control.question_router import load_question_schema, parse_questions

        yaml_path = Path(__file__).parent.parent / "core/control/questions/goal_clarification.yaml"
        schema, sha = load_question_schema(str(yaml_path))
        assert schema["schema_version"] == 1
        assert schema["question_set_id"] == "goal_clarification"
        questions = parse_questions(schema)
        ids = {q.id for q in questions}
        assert "goal_summary" in ids
        assert "deployment_target" in ids
        assert len(sha) == 64  # sha256 hex
        # Q-S2: 4개 신규 질문 포함 확인
        assert "observable_goal" in ids
        assert "golden_example" in ids
        assert "test_seam" in ids
        assert "manual_only" in ids
        # Q-S2: default_route=research_synthesize 파싱 확인
        rs_questions = [q for q in questions if q.default_route == QuestionRoute.RESEARCH_SYNTHESIZE]
        assert len(rs_questions) == 4

    def test_brainstorming_yaml_loads(self):
        from pathlib import Path
        from core.control.question_router import load_question_schema, parse_questions

        yaml_path = Path(__file__).parent.parent / "core/control/questions/brainstorming.yaml"
        schema, sha = load_question_schema(str(yaml_path))
        assert schema["schema_version"] == 1
        assert schema["question_set_id"] == "brainstorming"
        questions = parse_questions(schema)
        ids = {q.id for q in questions}
        assert "domain_verdict" in ids
        assert len(sha) == 64

    def test_stage_router_loads_both_yaml_no_collision(self):
        from core.control.run_ledger import RunLedger
        from core.control.stage_router import StageRouter
        import tempfile

        with tempfile.TemporaryDirectory() as ws:
            router = StageRouter(workspace=ws, run_ledger=RunLedger(ws))
            assert "goal_clarification" in router._active_schemas
            assert "brainstorming" in router._active_schemas
            all_ids = set()
            for schema in router._active_schemas.values():
                for q in schema["questions"]:
                    assert q["id"] not in all_ids, f"collision: {q['id']}"
                    all_ids.add(q["id"])


# ===========================================================================
# Q-S2: QuestionRoute.RESEARCH_SYNTHESIZE + route_batch 분기 + provenance
# ===========================================================================

class TestResearchSynthesizeRoute:
    """Q-S2: RESEARCH_SYNTHESIZE enum + route_batch 분기 검증."""

    def test_research_synthesize_enum_exists(self):
        assert QuestionRoute.RESEARCH_SYNTHESIZE.value == "research_synthesize"

    def test_route_batch_research_synthesize_returns_pending(self):
        router = QuestionRouter()
        schema = _make_schema([
            {
                "id": "observable_goal",
                "output_field": "observable_goal",
                "default_route": "research_synthesize",
                "text": "어떻게 확인합니까?",
            }
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "isolated")
        r = next(r for r in result.results if r.question_id == "observable_goal")
        assert r.question_route == QuestionRoute.RESEARCH_SYNTHESIZE
        assert r.source == "research_synthesize_pending"
        assert r.question_id not in result.paused_hitl_ids
        assert r.question_id not in [b.question_id for b in result.block_results]

    def test_route_batch_research_synthesize_multiple(self):
        """4개 RESEARCH_SYNTHESIZE 질문 전부 pending 결과 반환."""
        router = QuestionRouter()
        schema = _make_schema([
            {"id": "observable_goal", "output_field": "observable_goal", "default_route": "research_synthesize"},
            {"id": "golden_example", "output_field": "golden_example", "default_route": "research_synthesize"},
            {"id": "test_seam", "output_field": "test_seam", "default_route": "research_synthesize"},
            {"id": "manual_only", "output_field": "manual_only", "default_route": "research_synthesize"},
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "isolated")
        rs_results = [r for r in result.results if r.question_route == QuestionRoute.RESEARCH_SYNTHESIZE]
        assert len(rs_results) == 4
        assert result.paused_hitl_ids == []
        assert result.block_results == []

    def test_route_batch_mixed_routes(self):
        """LLM_DELEGATE + RESEARCH_SYNTHESIZE 혼합 시 각각 정상 처리."""
        llm = _FakeLLM({"q_llm": "some answer"})
        router = QuestionRouter(llm_caller=llm)
        schema = _make_schema([
            {"id": "q_llm", "output_field": "q_llm", "default_route": "llm_delegate"},
            {"id": "q_rs", "output_field": "q_rs", "default_route": "research_synthesize"},
        ])
        questions = parse_questions(schema)
        result = router.route_batch(questions, schema, "hash", "isolated")

        llm_r = next(r for r in result.results if r.question_id == "q_llm")
        rs_r = next(r for r in result.results if r.question_id == "q_rs")
        assert llm_r.question_route == QuestionRoute.LLM_DELEGATE
        assert llm_r.value == "some answer"
        assert rs_r.question_route == QuestionRoute.RESEARCH_SYNTHESIZE


class TestMergeClarificationProvenance:
    """Q-S2: merge_clarification provenance 전파 검증."""

    def test_default_provenance_in_log(self):
        from core.clarification import merge_clarification
        questions = [{"question": "Q?", "category": "scope"}]
        result = merge_clarification({}, questions, ["answer"])
        entry = result["clarification_log"][0]
        assert entry["provenance"] == "default"

    def test_user_provenance_in_log(self):
        from core.clarification import merge_clarification
        questions = [{"question": "Q?", "category": "scope"}]
        result = merge_clarification({}, questions, ["answer"], provenance="user")
        assert result["clarification_log"][0]["provenance"] == "user"

    def test_research_provenance_in_log(self):
        from core.clarification import merge_clarification
        questions = [{"question": "Q?", "category": "scope"}, {"question": "R?", "category": "data"}]
        result = merge_clarification({}, questions, ["ans1", "ans2"], provenance="research")
        for entry in result["clarification_log"]:
            assert entry["provenance"] == "research"

    def test_provenance_backward_compat_no_param(self):
        """기존 호출(provenance 없음)도 기본값 default로 동작."""
        from core.clarification import merge_clarification
        questions = [{"question": "Q?", "category": "scope"}]
        result = merge_clarification({}, questions, ["answer"])
        assert "provenance" in result["clarification_log"][0]
        assert result["clarification_log"][0]["provenance"] == "default"

    def test_auto_apply_defaults_still_works(self):
        """auto_apply_defaults()가 merge_clarification 변경으로 깨지지 않음."""
        from core.clarification import auto_apply_defaults
        questions = [{"question": "Q?", "category": "scope", "default": "기본값"}]
        result = auto_apply_defaults({}, questions)
        assert result["clarification_log"][0]["answer"] == "기본값"
        assert result["clarification_log"][0]["provenance"] == "default"
