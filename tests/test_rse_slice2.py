"""RSE Slice 2 — Stage-gate tests (§8 step-by-step).

Step 0  : E-*  SSOT enforcement  (RED before Step 1 + Step 3)
Step 2  : G-*  _stage_enabled unit  (RED before Step 3)
Step 4  : inv-*  gate behavior    (RED before Step 5)
Step 6  : inv-WIRE*  dogfood wiring  (RED before Step 7)
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Step 0: SSOT Enforcement
# ---------------------------------------------------------------------------

def test_e_ssot_member():
    """gate에 쓰는 상수가 STAGE_VOCAB 멤버여야 함."""
    from core.right_sized_router import (
        STAGE_RESEARCH, STAGE_REVIEW, STAGE_CROSS_REVIEW, STAGE_VOCAB,
    )
    assert STAGE_RESEARCH in STAGE_VOCAB
    assert STAGE_REVIEW in STAGE_VOCAB
    assert STAGE_CROSS_REVIEW in STAGE_VOCAB


def test_e_import_identity():
    """project_pipeline이 STAGE_* 상수를 재선언이 아닌 import로 가져와야 함."""
    import core.project_pipeline as pp
    import core.right_sized_router as r
    assert pp.STAGE_RESEARCH is r.STAGE_RESEARCH
    assert pp.STAGE_REVIEW is r.STAGE_REVIEW
    assert pp.STAGE_CROSS_REVIEW is r.STAGE_CROSS_REVIEW


def test_e_no_magic():
    """project_pipeline.py의 _stage_enabled 호출 인자에 단계 이름 리터럴 없어야 함."""
    src_path = Path(__file__).parent.parent / "core" / "project_pipeline.py"
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    stage_names = {
        "research", "design", "plan", "implement", "test", "review", "cross_review",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_stage_enabled = (
                (isinstance(func, ast.Name) and func.id == "_stage_enabled")
                or (isinstance(func, ast.Attribute) and func.attr == "_stage_enabled")
            )
            if not is_stage_enabled:
                continue
            for arg in node.args[1:]:  # skip route arg (first)
                if isinstance(arg, ast.Constant) and arg.value in stage_names:
                    pytest.fail(
                        f"Magic stage literal {arg.value!r} in _stage_enabled call "
                        f"at line {node.lineno}. Use STAGE_* constant instead."
                    )


def test_e_floor_const():
    """_apply_safety_floors가 stage 이름 리터럴 튜플 대신 상수를 써야 함."""
    src_path = Path(__file__).parent.parent / "core" / "right_sized_router.py"
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_safety_floors":
            func_src = ast.get_source_segment(src, node) or ""
            assert '("design", "review", "cross_review")' not in func_src, (
                "_apply_safety_floors must use STAGE_* constants, not literal tuple"
            )
            assert "('design', 'review', 'cross_review')" not in func_src, (
                "_apply_safety_floors must use STAGE_* constants, not literal tuple"
            )


# ---------------------------------------------------------------------------
# Step 2: _stage_enabled unit tests
# ---------------------------------------------------------------------------

def test_g_none():
    """route=None → True (전체 실행)."""
    from core.project_pipeline import _stage_enabled
    assert _stage_enabled(None, "research") is True


def test_g_empty():
    """required_stages=[] → True (전체 실행)."""
    from core.project_pipeline import _stage_enabled
    assert _stage_enabled({"required_stages": []}, "research") is True


def test_g_nokey():
    """required_stages 키 없음 → True (하위호환)."""
    from core.project_pipeline import _stage_enabled
    assert _stage_enabled({"risk_level": "low"}, "research") is True


def test_g_in():
    """required_stages에 포함 → True."""
    from core.project_pipeline import _stage_enabled
    assert _stage_enabled({"required_stages": ["research", "plan"]}, "research") is True


def test_g_out():
    """required_stages에 미포함 → False."""
    from core.project_pipeline import _stage_enabled
    assert _stage_enabled({"required_stages": ["plan", "implement", "test"]}, "research") is False


def test_g_or_hit():
    """OR 인자 중 하나라도 포함 → True."""
    from core.project_pipeline import _stage_enabled
    assert _stage_enabled({"required_stages": ["review"]}, "review", "cross_review") is True


def test_g_or_miss():
    """OR 인자 모두 미포함 → False."""
    from core.project_pipeline import _stage_enabled
    assert _stage_enabled({"required_stages": ["plan"]}, "review", "cross_review") is False


# ---------------------------------------------------------------------------
# Step 4: prepare_brief / prepare_documents gate tests
# ---------------------------------------------------------------------------

def _make_passthrough_guard():
    """PipelineStageGuard mock that just calls fn()."""
    guard = MagicMock()
    guard.run.side_effect = lambda stage, fn, fallback=None: fn()
    return guard


def _minimal_pipeline(tmp_path):
    """ProjectPipeline with mocked heavy deps for gate testing."""
    import core.project_pipeline as pp

    mr = MagicMock()
    research = MagicMock()
    research.research_project_brief.return_value = {
        "goal": "test goal",
        "pipeline_level": "dynamic",
    }

    pipeline = pp.ProjectPipeline(
        mr=mr,
        agent_mgr=MagicMock(),
        research_agent=research,
        procurer=MagicMock(),
    )
    pipeline.planner.plan = MagicMock(return_value={
        "execution_strategy": "parallel",
        "roles": [],
        "modules": [],
        "todo_items": [],
    })
    return pipeline, research


# ------ inv-RESEARCH-SKIP -------

def test_inv_research_skip(monkeypatch, tmp_path):
    """required_stages에 research 없으면 collect_project_evidence 미호출."""
    import core.project_pipeline as pp

    pipeline, research = _minimal_pipeline(tmp_path)
    collect_mock = MagicMock(return_value={})
    research.collect_project_evidence = collect_mock

    mock_guard = _make_passthrough_guard()

    with patch("core.project_pipeline.build_bootstrap_agent", return_value={"id": "t", "name": "t"}), \
         patch("core.pipeline_quality.PipelineStageGuard", return_value=mock_guard):

        route = {"required_stages": ["design", "plan", "implement", "test", "review"]}
        result = pipeline.prepare_brief("add func", str(tmp_path), route=route)

    collect_mock.assert_not_called()
    assert result.research_evidence == {}

    ev_path = Path(tmp_path) / "planning" / "research_evidence.json"
    assert ev_path.exists(), "research_evidence.json must always exist (빈 dict라도)"
    assert json.loads(ev_path.read_text()) == {}


# ------ inv-RESEARCH-RUN -------

def test_inv_research_run(monkeypatch, tmp_path):
    """route=None → collect_project_evidence 호출됨 (기존 행위 회귀)."""
    import core.project_pipeline as pp

    pipeline, research = _minimal_pipeline(tmp_path)
    collect_mock = MagicMock(return_value={"evidence": "data"})
    research.collect_project_evidence = collect_mock

    mock_guard = _make_passthrough_guard()

    class _MockVerifier:
        def verify_with_retry(self, evidence_fn, task_input):
            result = evidence_fn()
            return result, MagicMock(status="pass", score=1.0, gaps=[])

    with patch("core.project_pipeline.build_bootstrap_agent", return_value={"id": "t", "name": "t"}), \
         patch("core.pipeline_quality.PipelineStageGuard", return_value=mock_guard), \
         patch("core.research_verifier.ResearchVerifier", return_value=_MockVerifier()):

        result = pipeline.prepare_brief("add func", str(tmp_path), route=None)

    assert collect_mock.called, "route=None → collect_project_evidence must be called"


def test_prepare_brief_sets_target_path_to_workspace(monkeypatch, tmp_path):
    """Production caller workspace is preserved as the work-item doc root."""
    pipeline, research = _minimal_pipeline(tmp_path)
    research.collect_project_evidence = MagicMock(return_value={})

    mock_guard = _make_passthrough_guard()

    with patch("core.project_pipeline.build_bootstrap_agent", return_value={"id": "t", "name": "t"}), \
         patch("core.pipeline_quality.PipelineStageGuard", return_value=mock_guard):

        result = pipeline.prepare_brief("add func", str(tmp_path), route={"required_stages": []})

    assert result.project_brief["target_path"] == str(tmp_path.resolve())


# ------ helper: PreparedBrief factory -------

def _prepared_brief(tmp_path, route):
    """Build a PreparedBrief with the given route embedded in project_brief."""
    import core.project_pipeline as pp

    planning_dir = Path(tmp_path) / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)

    project_brief = {
        "goal": "test",
        "pipeline_level": "dynamic",
        "route": route or {},
    }
    ev_path = planning_dir / "research_evidence.json"
    ev_path.write_text("{}", encoding="utf-8")
    pb_path = planning_dir / "project_brief.json"
    pb_path.write_text(json.dumps(project_brief), encoding="utf-8")

    return pp.PreparedBrief(
        run_id="test-run",
        workspace=str(tmp_path),
        runtime_workspace=str(tmp_path),
        task_input="test task",
        project_brief=project_brief,
        research_evidence={},
        research_evidence_path=str(ev_path),
        project_brief_path=str(pb_path),
        memory_context={},
    )


def _run_prepare_documents_with_mocks(pipeline, prepared, tmp_path, *, drs_mock):
    """Call pipeline.prepare_documents() with all heavy deps mocked.

    Returns result — caller asserts on drs_mock.
    """
    import core.project_pipeline as pp
    from core.plan_verifier import PlanVerifyResult

    # Minimal work-item .md file so _documents dict is non-empty
    wi_file = Path(tmp_path) / "requirements.md"
    wi_file.write_text("# Requirements\ntest req", encoding="utf-8")

    mock_guard = _make_passthrough_guard()

    # Mock PlanVerifier to avoid real LLM calls and file content mutation
    mock_pv = MagicMock()
    mock_pv.verify.return_value = PlanVerifyResult(passed=True, score=1.0)
    mock_pv_cls = MagicMock(return_value=mock_pv)

    # Mock run_structural_gate to pass (avoid T1 QA _refine_document LLM calls)
    pipeline.run_structural_gate = MagicMock(return_value={"pass": True, "errors": []})

    with patch("core.project_pipeline.build_bootstrap_agent", return_value={"id": "t", "name": "t"}), \
         patch("core.pipeline_quality.PipelineStageGuard", return_value=mock_guard), \
         patch("core.project_pipeline.build_project_board", return_value={"tasks": []}), \
         patch("core.project_pipeline.write_project_board", return_value=str(tmp_path / "task_board.json")), \
         patch("core.project_pipeline.write_task_execution_plan", return_value=str(tmp_path / "exec_plan.json")), \
         patch("core.project_pipeline.enrich_role_plan", side_effect=lambda ti, pb, rp, **kw: rp), \
         patch("core.project_pipeline.generate_work_items", return_value={"requirements.md": str(wi_file)}), \
         patch("core.plan_verifier.PlanVerifier", mock_pv_cls), \
         patch("core.review_report.DocumentReviewSession", drs_mock):

        result = pipeline.prepare_documents(prepared)

    return result


def test_prepare_documents_resolves_relative_target_path_against_workspace(tmp_path):
    """Relative target_path is resolved from the target workspace, not AF cwd."""
    pipeline, _ = _minimal_pipeline(tmp_path)
    prepared = _prepared_brief(tmp_path, route={"required_stages": ["plan"]})
    prepared.project_brief["target_path"] = "artifact-root"
    drs_mock = MagicMock()

    result = _run_prepare_documents_with_mocks(
        pipeline, prepared, tmp_path, drs_mock=drs_mock
    )

    assert result.doc_root == str((tmp_path / "artifact-root").resolve())


# ------ inv-REVIEW-SKIP -------

def test_inv_review_skip(tmp_path):
    """route에 review/cross_review 없으면 DocumentReviewSession 미생성."""
    pipeline, _ = _minimal_pipeline(tmp_path)
    prepared = _prepared_brief(tmp_path, route={"required_stages": ["plan", "implement", "test"]})
    drs_mock = MagicMock()

    _run_prepare_documents_with_mocks(pipeline, prepared, tmp_path, drs_mock=drs_mock)

    drs_mock.assert_not_called()


# ------ inv-REVIEW-RUN -------

def test_inv_review_run(tmp_path):
    """route=None → DocumentReviewSession 생성됨 (기존 행위 회귀)."""
    pipeline, _ = _minimal_pipeline(tmp_path)
    prepared = _prepared_brief(tmp_path, route=None)
    # project_brief["route"] = {} (route=None → _stage_enabled True)

    drs_inst = MagicMock()
    drs_inst.max_rounds = 1
    drs_inst.run_review.return_value = MagicMock(
        judge=MagicMock(verdict="PASS", fix_instructions=None),
        save=MagicMock(return_value=""),
    )
    drs_mock = MagicMock(return_value=drs_inst)

    _run_prepare_documents_with_mocks(pipeline, prepared, tmp_path, drs_mock=drs_mock)

    drs_mock.assert_called_once()


# ------ inv-NORM -------

def test_inv_norm(tmp_path):
    """research skip/run 양쪽 PreparedBrief의 필드 키 동일 + research_evidence_path 항상 존재."""
    import core.project_pipeline as pp

    pipeline, research = _minimal_pipeline(tmp_path)

    mock_guard = _make_passthrough_guard()

    class _MockVerifier:
        def verify_with_retry(self, evidence_fn, task_input):
            return evidence_fn(), MagicMock(status="pass", score=1.0, gaps=[])

    tmp_skip = Path(tmp_path) / "skip"
    tmp_run = Path(tmp_path) / "run"
    tmp_skip.mkdir()
    tmp_run.mkdir()

    with patch("core.project_pipeline.build_bootstrap_agent", return_value={"id": "t", "name": "t"}), \
         patch("core.pipeline_quality.PipelineStageGuard", return_value=mock_guard), \
         patch("core.research_verifier.ResearchVerifier", return_value=_MockVerifier()):

        research.collect_project_evidence = MagicMock(return_value={})
        result_skip = pipeline.prepare_brief(
            "add func", str(tmp_skip),
            route={"required_stages": ["plan", "implement", "test"]},
        )

        result_run = pipeline.prepare_brief(
            "add func", str(tmp_run),
            route=None,
        )

    skip_fields = set(vars(result_skip).keys())
    run_fields = set(vars(result_run).keys())
    assert skip_fields == run_fields, f"Field set mismatch: {skip_fields ^ run_fields}"

    assert result_skip.research_evidence_path, "research_evidence_path must be set even when research skipped"
    assert result_run.research_evidence_path, "research_evidence_path must always be set"

    # research skip → evidence 비어있음
    assert result_skip.research_evidence == {}


# ------ inv-STARTER -------

def test_inv_starter(tmp_path):
    """level=starter → review in required_stages여도 DocumentReviewSession 미생성 (AND 게이트)."""
    pipeline, _ = _minimal_pipeline(tmp_path)
    prepared = _prepared_brief(tmp_path, route={"required_stages": ["review", "plan", "implement"]})
    # Override pipeline_level to "starter"
    prepared.project_brief["pipeline_level"] = "starter"

    drs_mock = MagicMock()

    _run_prepare_documents_with_mocks(pipeline, prepared, tmp_path, drs_mock=drs_mock)

    drs_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Step 6: dogfood wiring tests
# ---------------------------------------------------------------------------

def _make_dogfood_state(tmp_path, route_decision):
    """DogfoodState with minimal required fields for _run_develop_full."""
    from core.dogfood import DogfoodState, DogfoodPhase
    state = DogfoodState(
        run_id="test-run-id",
        task="add func",
        phase=DogfoodPhase.DEVELOP,
        source_workspace=str(tmp_path),
        runtime_workspace=str(tmp_path),
        worktree_workspace=str(tmp_path),
    )
    state.route_decision = route_decision
    return state


def test_inv_wire(tmp_path):
    """_run_develop_full → pipeline.run이 route=state.route_decision 로 호출됨."""
    from core.dogfood import _run_develop_full

    route_dict = {
        "isolation": "worktree",
        "required_stages": ["plan", "implement", "test"],
        "review_depth": "none",
        "confidence": 0.9,
        "reason": "test",
        "floors_applied": [],
        "source": "llm",
    }

    state = _make_dogfood_state(tmp_path, route_decision=route_dict)

    pipeline = MagicMock()
    pipeline.run.return_value = {"ok": True, "changed_files": []}

    with patch("core.dogfood._develop_isolation_env") as mock_env:
        mock_env.return_value.__enter__ = MagicMock(return_value=None)
        mock_env.return_value.__exit__ = MagicMock(return_value=False)
        _run_develop_full(state, pipeline)

    call_kwargs = pipeline.run.call_args.kwargs
    assert "route" in call_kwargs, "pipeline.run must receive route= kwarg"
    assert call_kwargs["route"] == route_dict


def test_inv_wire_fallback(tmp_path):
    """state.route_decision=None/{}  → pipeline.run(route=None) (방어)."""
    from core.dogfood import _run_develop_full

    for empty_route in (None, {}):
        state = _make_dogfood_state(tmp_path, route_decision=empty_route)

        pipeline = MagicMock()
        pipeline.run.return_value = {"ok": True, "changed_files": []}

        with patch("core.dogfood._develop_isolation_env") as mock_env:
            mock_env.return_value.__enter__ = MagicMock(return_value=None)
            mock_env.return_value.__exit__ = MagicMock(return_value=False)
            _run_develop_full(state, pipeline)

        call_kwargs = pipeline.run.call_args.kwargs
        assert call_kwargs.get("route") is None, (
            f"route_decision={empty_route!r} → pipeline.run(route=None) expected, "
            f"got {call_kwargs.get('route')!r}"
        )
