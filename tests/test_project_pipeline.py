import importlib
import json
import os


def _load_launcher(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import core.config_paths
    importlib.reload(core.config_paths)
    import core.utils
    importlib.reload(core.utils)
    import core.agent_runner
    importlib.reload(core.agent_runner)
    import core.project_pipeline
    importlib.reload(core.project_pipeline)
    import agent_launcher
    return importlib.reload(agent_launcher)


def test_factory_routes_complex_task_to_project_pipeline(monkeypatch, tmp_path):
    al = _load_launcher(monkeypatch)
    factory = al.AgentFactory()

    routed = []
    factory.request_router.route = lambda **kwargs: {
        "pipeline": "project",
        "intent": "greenfield",
        "confidence": 99,
        "reasoning": "forced-test",
    }
    # 이제 _run_project_with_approval 가 호출된다
    factory._run_project_with_approval = lambda **kwargs: routed.append(kwargs) or {
        "pipeline": "project",
        "ok": True,
        "reason": "completed",
    }

    runtime_ws = tmp_path / "runtime"
    res = factory.run(
        task_input="build a poker game",
        role_spec="General",
        workspace=str(tmp_path),
        runtime_workspace=str(runtime_ws),
    )

    assert res["pipeline"] == "project"
    assert routed and routed[0]["workspace"] == str(tmp_path)
    assert routed[0]["runtime_workspace"] == str(runtime_ws)
    assert routed[0]["requested_role"] == "General"


def test_factory_routes_project_pipeline_directly_in_fsa_mode(monkeypatch, tmp_path):
    al = _load_launcher(monkeypatch)
    factory = al.AgentFactory()

    routed = []
    approvals = []
    factory.request_router.route = lambda **kwargs: {
        "pipeline": "project",
        "intent": "greenfield",
        "confidence": 99,
        "reasoning": "forced-test",
    }
    factory.project_pipeline.run = lambda **kwargs: routed.append(kwargs) or {
        "pipeline": "project",
        "ok": True,
        "reason": "completed",
    }
    factory._run_project_with_approval = lambda **kwargs: approvals.append(kwargs) or {
        "pipeline": "project",
        "ok": False,
        "reason": "unexpected-approval-path",
    }

    res = factory.run(
        task_input="build a poker game",
        role_spec="General",
        workspace=str(tmp_path),
        runtime_workspace=str(tmp_path / "runtime"),
        execution_mode="fsa",
    )

    assert res["pipeline"] == "project"
    assert routed and routed[0]["workspace"] == str(tmp_path)
    assert routed[0]["runtime_workspace"] == str(tmp_path / "runtime")
    assert routed[0]["requested_role"] == "General"
    assert routed[0]["execution_mode"] == "fsa"
    assert approvals == []



def test_project_pipeline_writes_planning_artifacts_and_roles(monkeypatch, tmp_path):
    monkeypatch.setenv("AF_SKIP_ESCALATION", "1")  # planning artifacts 검증이 목적 — escalation gate 우회
    monkeypatch.setenv("AF_SKIP_DOMAIN_REVIEW", "1")

    # PlanVerifier: 실제 LLM 호출 차단 (20분 → 즉시) + warning_registry 기록 방지
    import core.plan_verifier as _pv_mod
    from core.plan_verifier import PlanVerifyResult
    class _DummyPlanVerifier:
        def __init__(self, workspace=None): pass
        def verify(self, task_input, work_items, project_brief=None):
            return PlanVerifyResult(passed=True, score=1.0)
        def refine(self, *args, **kwargs): return None
        def gate(self, *args, **kwargs): return PlanVerifyResult(passed=True, score=1.0)
    monkeypatch.setattr(_pv_mod, "PlanVerifier", _DummyPlanVerifier)

    al = _load_launcher(monkeypatch)
    factory = al.AgentFactory()
    pipeline = factory.project_pipeline

    pipeline.research.collect_project_evidence = lambda task_input, workspace=None: {
        "workspace_notes": ["existing_todo=.todo.md"],
        "evidence_summary": [
            "Local reference: docs/architecture.md -> game state is split by module.",
            "Web reference: Poker rules -> verify state transitions and winner evaluation.",
        ],
        "local_references": [
            {
                "path": "docs/architecture.md",
                "heading": "# Modules",
                "excerpt": "game state is split by module.",
                "score": 0.9,
            }
        ],
        "web_references": [
            {
                "url": "https://example.com/poker-rules",
                "title": "Poker rules",
                "excerpt": "verify state transitions and winner evaluation.",
                "score": 0.8,
            }
        ],
        "notebook_summary": "Prefer isolated game-rule modules and explicit verification checkpoints.",
    }
    pipeline.research.research_project_brief = lambda agent, task_input, workspace=None, evidence_bundle=None: {
        "goal": "Implement a browser poker game",
        "constraints": ["network_allowed"],
        "required_skills": ["frontend_game_ui", "gameplay_core", "integration_test_guard"],
        "role_hints": ["frontend_dev", "qa_engineer"],
        "deliverables": ["game ui", "game rules", "test checklist"],
        "risks": ["rule evaluation bug"],
        "research_notes": ["seed"],
        "tech_stack": ["vanilla_js"],
        "evidence_summary": list((evidence_bundle or {}).get("evidence_summary") or []),
        "local_references": list((evidence_bundle or {}).get("local_references") or []),
        "web_references": list((evidence_bundle or {}).get("web_references") or []),
        "notebook_summary": str((evidence_bundle or {}).get("notebook_summary") or ""),
    }
    pipeline.planner.plan = lambda task_input, project_brief: {
        "execution_strategy": "parallel",
        "roles": [
            {
                "id": "frontend_dev",
                "name": "Frontend Dev",
                "objective": "Implement the game UI.",
                "required_skills": ["frontend_game_ui"],
            },
            {
                "id": "qa_engineer",
                "name": "QA Engineer",
                "objective": "Verify the core gameplay flow.",
                "required_skills": ["integration_test_guard"],
            },
        ],
        "todo_items": [
            "Frontend Dev: Implement the game UI.",
            "QA Engineer: Verify the core gameplay flow.",
        ],
    }

    def _get_or_create(role_spec, workspace=None):
        return {"name": role_spec, "role": role_spec, "skills": []}

    factory.agent_mgr.get_or_create = _get_or_create
    procure_calls = []
    def _mock_procure(**kwargs):
        procure_calls.append(
            (kwargs["agent"]["role"], list(kwargs["skill_names"]), kwargs["workspace"])
        )
        skills = list(kwargs["skill_names"])
        manifest = [{"skill_id": s, "requested": True, "installed": True, "decision_mode": "direct_install", "reused_from": None, "forge_run_id": None, "fallback_chain": []} for s in skills]
        return skills, manifest
    factory.procurer.procure_multiple = _mock_procure

    import core.project_pipeline as pp

    class _DummyOrchestrator:
        def __init__(self, mr, max_concurrent=5, broker=None, visualizer=None, **kwargs):
            self.mr = mr

        def run_project(self, project_desc, roles, workspace=None, runtime_workspace=None):
            return {
                "current_status": "completed",
                "roles": roles,
                "workspace": workspace,
                "runtime_workspace": runtime_workspace,
            }

    monkeypatch.setattr(pp, "DynamicOrchestrator", _DummyOrchestrator)
    monkeypatch.setattr(pp, "generate_work_items", lambda **_kwargs: {})

    res = pipeline.run(
        task_input="build a poker game",
        workspace=str(tmp_path),
        execution_mode="approval",
        enable_build=True,
        requested_role="General",
        route={"pipeline": "project"},
    )

    assert res["ok"] is True
    assert sorted(res["roles"]) == ["frontend_dev", "qa_engineer"]
    assert os.path.exists(tmp_path / "planning" / "research_evidence.json")
    assert os.path.exists(tmp_path / "planning" / "project_brief.json")
    assert os.path.exists(tmp_path / "planning" / "role_plan.json")
    assert os.path.exists(tmp_path / "project_board_state.json")
    assert os.path.exists(tmp_path / ".todo.md")
    assert os.path.exists(tmp_path / "docs" / "task_execution_plan.md")
    assert os.path.exists(tmp_path / "agents" / "frontend_dev.yaml")
    assert os.path.exists(tmp_path / "agents" / "qa_engineer.yaml")

    frontend_agent = al.read_yaml(tmp_path / "agents" / "frontend_dev.yaml")
    assert "file_handler" in frontend_agent["skills"]
    assert "core_memory" in frontend_agent["skills"]
    assert "file_handler" in frontend_agent["runtime_rules"]["allowed_skills"]
    assert "core_memory" in frontend_agent["runtime_rules"]["allowed_skills"]
    assert frontend_agent["project_role"]["owned_modules"]
    assert frontend_agent["project_role"]["planning_steps"]

    research_data = json.loads((tmp_path / "planning" / "research_evidence.json").read_text(encoding="utf-8"))
    assert research_data["evidence_summary"]

    project_brief_data = json.loads((tmp_path / "planning" / "project_brief.json").read_text(encoding="utf-8"))
    assert project_brief_data["evidence_summary"]
    assert project_brief_data["local_references"][0]["path"] == "docs/architecture.md"

    role_plan_data = json.loads((tmp_path / "planning" / "role_plan.json").read_text(encoding="utf-8"))
    assert role_plan_data["planning_steps"]
    assert role_plan_data["modules"]
    assert role_plan_data["plan_summary"]["task_count"] >= 2

    board_data = json.loads((tmp_path / "project_board_state.json").read_text(encoding="utf-8"))
    assert board_data["summary"]["total_tasks"] >= 2
    assert board_data["modules"]
    assert board_data["tasks"]

    plan_doc = (tmp_path / "docs" / "task_execution_plan.md").read_text(encoding="utf-8")
    assert "# Task Execution Plan" in plan_doc
    assert "## Stage Order" in plan_doc
    assert "## Module Breakdown By Role" in plan_doc
    assert "## Handoff Rules" in plan_doc

    todo_text = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert "Frontend Dev:" in todo_text
    assert "docs/architecture.md" in todo_text
    assert "docs/change_history.md" in todo_text

    assert res["task_board_path"].endswith("project_board_state.json")
    assert res["task_execution_plan_path"].endswith("docs/task_execution_plan.md")
    assert procure_calls == [
        ("Frontend Dev", ["frontend_game_ui"], str(tmp_path)),
        ("QA Engineer", ["integration_test_guard"], str(tmp_path)),
    ]


def test_project_pipeline_routes_runtime_workspace_to_orchestrator(monkeypatch, tmp_path):
    monkeypatch.setenv("AF_SKIP_ESCALATION", "1")
    monkeypatch.setenv("AF_SKIP_DOMAIN_REVIEW", "1")

    # PlanVerifier: 실제 LLM 호출 차단 (타임아웃 → 체크포인트 경로 불일치 방지)
    import core.plan_verifier as _pv_mod
    from core.plan_verifier import PlanVerifyResult
    class _DummyPlanVerifier:
        def __init__(self, workspace=None): pass
        def verify(self, task_input, work_items, project_brief=None):
            return PlanVerifyResult(passed=True, score=1.0)
        def refine(self, *args, **kwargs): return None
        def gate(self, *args, **kwargs): return PlanVerifyResult(passed=True, score=1.0)
    monkeypatch.setattr(_pv_mod, "PlanVerifier", _DummyPlanVerifier)

    al = _load_launcher(monkeypatch)
    factory = al.AgentFactory()
    pipeline = factory.project_pipeline
    runtime_ws = tmp_path / "runtime"

    pipeline.research.collect_project_evidence = lambda task_input, workspace=None: {"sources": []}
    pipeline.research.research_project_brief = lambda agent, task_input, workspace=None, evidence_bundle=None: {
        "goal": task_input,
        "work_kind": "feature",
    }
    pipeline.planner.plan = lambda task_input, project_brief, memory_context=None: {
        "roles": [{"id": "dev", "name": "Dev", "required_skills": []}],
        "modules": [],
        "todo_items": ["Dev: implement"],
    }

    import core.project_pipeline as pp

    calls = {}

    class _DummyOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        def run_project(self, project_desc, roles, workspace=None, runtime_workspace=None):
            calls["workspace"] = workspace
            calls["runtime_workspace"] = runtime_workspace
            return {"current_status": "completed", "roles": roles}

    monkeypatch.setattr(pp, "DynamicOrchestrator", _DummyOrchestrator)
    monkeypatch.setattr(pp, "generate_work_items", lambda **_kwargs: {})

    res = pipeline.run(
        task_input="build a small feature",
        workspace=str(tmp_path),
        runtime_workspace=str(runtime_ws),
        execution_mode="approval",
    )

    assert res["ok"] is True
    assert calls == {"workspace": str(tmp_path), "runtime_workspace": str(runtime_ws)}
    assert (runtime_ws / ".checkpoint" / "evidence_acquisition.json").exists()
    assert (runtime_ws / ".checkpoint" / "draft_brief.json").exists()
    assert (runtime_ws / ".checkpoint" / "role_plan.json").exists()
    assert not (tmp_path / ".checkpoint").exists()


def test_factory_single_run_auto_creates_todo_for_complex_task(monkeypatch, tmp_path):
    al = _load_launcher(monkeypatch)
    factory = al.AgentFactory()

    factory.request_router.route = lambda **kwargs: {
        "pipeline": "single",
        "intent": "forced",
        "confidence": 100,
        "reasoning": "pipeline_mode=single",
    }
    factory.req.analyze = lambda agent, task_input, workspace=None: {
        "goal": task_input,
        "missing_skills": [],
        "constraints": ["network_allowed"],
        "risk_level": "elevated",
    }
    factory._get_agent = lambda role_spec, workspace=None: {
        "name": role_spec,
        "role": role_spec,
        "skills": [],
    }
    factory._invoke_runner = lambda agent, task_input, run_id, auto_approve, workspace=None: {
        "ok": True,
        "reason": "completed",
        "latency_ms": 1,
        "approval_rejects": 0,
    }

    res = factory.run(
        task_input="Create a minimal static web page with one button and verify the click state changes.",
        role_spec="Frontend Architect",
        workspace=str(tmp_path),
        pipeline_mode="single",
    )

    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")

    assert res["ok"] is True
    assert "- [ ] Frontend Architect: Create a minimal static web page with one button and verify the click state changes." in content
    assert "docs/architecture.md" in content
    assert "docs/change_history.md" in content


def test_factory_single_run_keeps_existing_todo_file(monkeypatch, tmp_path):
    al = _load_launcher(monkeypatch)
    factory = al.AgentFactory()

    todo_path = tmp_path / ".todo.md"
    todo_path.write_text("# Existing TODO\n\n- [ ] keep original plan\n", encoding="utf-8")

    factory.request_router.route = lambda **kwargs: {
        "pipeline": "single",
        "intent": "forced",
        "confidence": 100,
        "reasoning": "pipeline_mode=single",
    }
    factory.req.analyze = lambda agent, task_input, workspace=None: {
        "goal": task_input,
        "missing_skills": [],
        "constraints": ["network_allowed"],
        "risk_level": "strict",
    }
    factory._get_agent = lambda role_spec, workspace=None: {
        "name": role_spec,
        "role": role_spec,
        "skills": [],
    }
    factory._invoke_runner = lambda agent, task_input, run_id, auto_approve, workspace=None: {
        "ok": True,
        "reason": "completed",
        "latency_ms": 1,
        "approval_rejects": 0,
    }

    factory.run(
        task_input="Implement a multi-step frontend smoke page and keep the manual checklist intact.",
        role_spec="Frontend Architect",
        workspace=str(tmp_path),
        pipeline_mode="single",
    )

    assert todo_path.read_text(encoding="utf-8") == "# Existing TODO\n\n- [ ] keep original plan\n"
