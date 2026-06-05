"""
next_board_tasks 디스패치 순서 단위 테스트.

2026-04-15 `lotto-pattern-predictor` FSA 실측에서 발견된 회귀를 고정한다:
- 구 동작(phase 우선): 모든 모듈의 scope를 먼저 소화 → max_cycles 소진 전 build 단계 진입 실패.
- 신 동작(module 우선): 같은 module을 scope→build→verify까지 끝낸 뒤 다음 module로.

또한 단순 smoke import로 `core.project_pipeline`의 `_safe_print` 미import 회귀를 감지한다.
"""
from __future__ import annotations

from core.project_task_board import next_board_tasks


def _make_task(task_id: str, module_id: str, phase: str, owner: str = "backend_dev") -> dict:
    return {
        "task_id": task_id,
        "instruction": f"{owner}: {module_id}/{phase}",
        "owner_role": owner,
        "module_id": module_id,
        "phase": phase,
        "depends_on": [],
        "status": "pending",
    }


def test_next_board_tasks_prefers_same_module_build_after_scope_completes():
    # module_1 scope가 끝난 직후, 같은 모듈의 build가 다른 모듈의 scope보다 먼저 선택되어야 함.
    board = {
        "tasks": [
            _make_task("backend_dev_module_1_scope_1", "backend_dev_module_1", "scope"),
            _make_task("backend_dev_module_1_build_2", "backend_dev_module_1", "build"),
            _make_task("backend_dev_module_1_verify_3", "backend_dev_module_1", "verify"),
            _make_task("backend_dev_module_2_scope_1", "backend_dev_module_2", "scope"),
            _make_task("backend_dev_module_2_build_2", "backend_dev_module_2", "build"),
        ]
    }
    # module_1 scope 완료된 상태
    completed = {"backend_dev_module_1_scope_1"}
    chosen = next_board_tasks(board, available_roles=["backend_dev"], completed_ids=completed)
    assert len(chosen) == 1
    assert chosen[0]["task_id"] == "backend_dev_module_1_build_2", (
        f"module waterfall 위반: {chosen[0]['task_id']} (module_1 build가 선택되어야 함)"
    )


def test_next_board_tasks_module_numeric_suffix_sorted_as_int():
    # module_10이 module_2보다 **뒤에** 와야 함(문자열 정렬 회귀 방지).
    board = {
        "tasks": [
            _make_task("t10", "backend_dev_module_10", "scope"),
            _make_task("t2", "backend_dev_module_2", "scope"),
        ]
    }
    chosen = next_board_tasks(board, available_roles=["backend_dev"], completed_ids=set())
    assert chosen[0]["task_id"] == "t2"


def test_next_board_tasks_falls_through_completed_module_to_next():
    # module_1의 scope/build/verify 전부 완료 시 module_2 scope로 넘어가야 함.
    board = {
        "tasks": [
            _make_task("m1_scope", "backend_dev_module_1", "scope"),
            _make_task("m1_build", "backend_dev_module_1", "build"),
            _make_task("m1_verify", "backend_dev_module_1", "verify"),
            _make_task("m2_scope", "backend_dev_module_2", "scope"),
        ]
    }
    completed = {"m1_scope", "m1_build", "m1_verify"}
    # 완료된 태스크는 board의 status도 completed로 있어야 실제 선택에서 빠짐
    for t in board["tasks"]:
        if t["task_id"] in completed:
            t["status"] = "completed"
    chosen = next_board_tasks(board, available_roles=["backend_dev"], completed_ids=completed)
    assert chosen and chosen[0]["task_id"] == "m2_scope"


def test_project_pipeline_imports_without_nameerror():
    # 2026-04-15 `_safe_print` 미import NameError 회귀 방지용 smoke.
    import core.project_pipeline  # noqa: F401
    assert hasattr(core.project_pipeline, "_safe_print"), (
        "_safe_print이 project_pipeline 네임스페이스에 노출되어야 함"
    )


def test_module_sort_key_handles_id_without_numeric_suffix():
    # af-critic 2026-04-15 WARN-1: lazy `(.*?)` 패턴이 접미사 없는 id를 빈 prefix로
    # 파싱해 모든 정렬 버킷 앞으로 끌려오는 silent sort 오염 회귀 방지.
    from core.project_task_board import _module_sort_key
    assert _module_sort_key("backend_dev") == ("backend_dev", 0)
    assert _module_sort_key("backend_dev_module_1") == ("backend_dev_module", 1)
    assert _module_sort_key("") == ("", 0)
    # 같은 prefix 계열이 module_N 보다 앞에 오되 빈 문자열로 붕괴되지 않는다.
    assert _module_sort_key("backend_dev") < _module_sort_key("backend_dev_module_1")
    # 혼재 상황 — "backend_dev" 태스크가 여전히 같은 prefix 모듈과 같은 정렬 버킷에 속한다.
    assert _module_sort_key("backend_dev")[0] != "", "빈 prefix로 붕괴되면 안 됨"


# ----- compute_max_cycles (모듈 함수) 단위 테스트 -----
# af-critic 2026-04-15 WARN-4 대응: 기존 closure 복제 테스트를 제거하고 실제 모듈 함수를
# 그대로 호출해 "테스트가 구현을 복제해야 한다"는 딜레마를 해소한다. board를 monkeypatch로
# 치환해 I/O 없이 공식과 예외 경로까지 직접 검증.


def test_compute_max_cycles_pending_zero_falls_back_to_floor(monkeypatch):
    import core.project_task_board as ptb
    monkeypatch.setattr(ptb, "load_project_board", lambda ws: {})
    assert ptb.compute_max_cycles("/fake") == ptb.MAX_CYCLES_FLOOR
    monkeypatch.setattr(ptb, "load_project_board", lambda ws: None)
    assert ptb.compute_max_cycles("/fake") == ptb.MAX_CYCLES_FLOOR
    monkeypatch.setattr(ptb, "load_project_board", lambda ws: {"tasks": []})
    assert ptb.compute_max_cycles("/fake") == ptb.MAX_CYCLES_FLOOR


def test_compute_max_cycles_scales_with_pending_count(monkeypatch):
    import core.project_task_board as ptb
    # phase 미지정 → 기본 "build" → 가중치 25
    build_weight = ptb._PHASE_CYCLE_WEIGHTS["build"]  # 25
    monkeypatch.setattr(
        ptb, "load_project_board",
        lambda ws: {"tasks": [{"status": "pending"} for _ in range(24)]}
    )
    assert ptb.compute_max_cycles("/fake") == 24 * build_weight  # 600
    monkeypatch.setattr(
        ptb, "load_project_board",
        lambda ws: {"tasks": [{"status": "pending"} for _ in range(100)]}
    )
    assert ptb.compute_max_cycles("/fake") == 100 * build_weight  # 2500
    # 소수 태스크는 floor 유지 (3 * 25 = 75 < 100)
    monkeypatch.setattr(
        ptb, "load_project_board",
        lambda ws: {"tasks": [{"status": "pending"} for _ in range(3)]}
    )
    assert ptb.compute_max_cycles("/fake") == ptb.MAX_CYCLES_FLOOR


def test_compute_max_cycles_counts_only_open_tasks(monkeypatch):
    import core.project_task_board as ptb
    monkeypatch.setattr(ptb, "load_project_board", lambda ws: {
        "tasks": [
            {"status": "pending"},
            {"status": "pending"},
            {"status": "completed"},
            {"status": "failed"},
            {"status": "blocked"},  # blocked도 pending 취급(재시도 대상)
        ]
    })
    # pending 2 + blocked 1 = 3, build 가중치 25 → 75 < MAX_CYCLES_FLOOR(100) → floor
    assert ptb.compute_max_cycles("/fake") == ptb.MAX_CYCLES_FLOOR


def test_compute_max_cycles_defends_against_malformed_board(monkeypatch):
    import core.project_task_board as ptb
    # tasks가 list 아닌 경우
    monkeypatch.setattr(ptb, "load_project_board", lambda ws: {"tasks": "not_a_list"})
    assert ptb.compute_max_cycles("/fake") == ptb.MAX_CYCLES_FLOOR
    # tasks 원소가 dict 아닌 잡음
    monkeypatch.setattr(ptb, "load_project_board", lambda ws: {"tasks": [None, "string", 123]})
    assert ptb.compute_max_cycles("/fake") == ptb.MAX_CYCLES_FLOOR


def test_dependency_satisfied_module_dep_uses_task_level_when_status_is_stale():
    # af-cross-review 2026-04-15 Q1 race 회귀 방지:
    # module 내부 task는 모두 completed이지만 `_recalculate_board`가 아직 안 돌아
    # module.status가 stale한 "pending" 상태일 때, module_id를 depends_on으로 가진 태스크가
    # 정상 dispatch되는지 확인.
    from core.project_task_board import _dependency_satisfied

    board = {
        "modules": [
            {"id": "mod_1", "task_ids": ["t_a", "t_b"], "status": "pending"},  # stale!
        ],
        "tasks": [
            {"task_id": "t_a", "status": "completed"},
            {"task_id": "t_b", "status": "completed"},
            {"task_id": "t_dependent", "status": "pending", "depends_on": ["mod_1"]},
        ],
    }
    # module.status="pending"이어도 내부 task가 전부 completed면 의존성 만족으로 판정.
    assert _dependency_satisfied("mod_1", board, completed_ids=set()) is True


def test_dependency_satisfied_module_dep_blocks_when_any_task_pending():
    # 모듈 내부 일부 task가 pending인 경우 — 의존성 미충족이어야 함 (race와 무관한 안전장치).
    from core.project_task_board import _dependency_satisfied

    board = {
        "modules": [
            {"id": "mod_1", "task_ids": ["t_a", "t_b"], "status": "pending"},
        ],
        "tasks": [
            {"task_id": "t_a", "status": "completed"},
            {"task_id": "t_b", "status": "in_progress"},
        ],
    }
    assert _dependency_satisfied("mod_1", board, completed_ids=set()) is False


def test_compute_max_cycles_logs_on_load_failure(monkeypatch):
    # af-critic WARN-3: I/O 실패가 silent로 묻히지 않도록 logger 경로 검증.
    import core.project_task_board as ptb
    def _boom(ws):
        raise OSError("simulated disk error")
    monkeypatch.setattr(ptb, "load_project_board", _boom)
    captured = []
    result = ptb.compute_max_cycles("/fake", logger=captured.append)
    assert result == ptb.MAX_CYCLES_FLOOR
    assert len(captured) == 1
    assert "OSError" in captured[0] and "simulated disk error" in captured[0]


# ----- build_project_board: verification_focus → verify acceptance 주입 (B-2) -----
# Research Router Phase 2 — researcher.py가 project_brief에 채우는 verification_focus가
# verify 태스크 acceptance 까지 전파되는지 고정한다.
# required_capabilities는 build acceptance에 주입하지 않는다 (B-3 capability-gap 경로 위임).


def _role_plan_with_tasks() -> dict:
    return {
        "execution_strategy": "sequential",
        "modules": [
            {
                "id": "backend_dev_module_1",
                "name": "API",
                "summary": "build the API",
                "owner_role": "backend_dev",
                "depends_on": [],
                "deliverables": ["api"],
                "feature_slices": [],
                "tasks": [
                    {"id": "t_scope", "title": "scope", "instruction": "scope it",
                     "phase": "scope", "acceptance": ["범위 정리"]},
                    {"id": "t_build", "title": "build", "instruction": "build it",
                     "phase": "build", "acceptance": ["기능 구현"]},
                    {"id": "t_verify", "title": "verify", "instruction": "verify it",
                     "phase": "verify", "acceptance": ["검증 정리"]},
                ],
            }
        ],
    }


def test_build_project_board_injects_verification_focus_into_acceptance():
    from core.project_task_board import build_project_board
    brief = {
        "goal": "build app",
        "verification_focus": ["reconnect handling", "multi-client test"],
        "required_capabilities": ["websocket_server", "session_state"],
    }
    board = build_project_board(brief, _role_plan_with_tasks())
    by_id = {t["task_id"]: t for t in board["tasks"]}
    # verify 태스크는 verification_focus를 받는다.
    assert "검증 초점: reconnect handling" in by_id["t_verify"]["acceptance"]
    assert "검증 초점: multi-client test" in by_id["t_verify"]["acceptance"]
    # 기존 acceptance는 보존된다.
    assert "검증 정리" in by_id["t_verify"]["acceptance"]
    # build 태스크는 required_capabilities를 받지 않는다 (B-3 capability-gap 경로 위임).
    assert by_id["t_build"]["acceptance"] == ["기능 구현"]
    # scope 태스크는 손대지 않는다.
    assert by_id["t_scope"]["acceptance"] == ["범위 정리"]


def test_build_project_board_without_structured_evidence_keeps_acceptance():
    from core.project_task_board import build_project_board
    board = build_project_board({"goal": "build app"}, _role_plan_with_tasks())
    by_id = {t["task_id"]: t for t in board["tasks"]}
    assert by_id["t_verify"]["acceptance"] == ["검증 정리"]
    assert by_id["t_build"]["acceptance"] == ["기능 구현"]
    assert by_id["t_scope"]["acceptance"] == ["범위 정리"]


def test_build_project_board_acceptance_injection_is_idempotent():
    # 이미 동일 라인이 있으면 중복 추가하지 않는다.
    from core.project_task_board import build_project_board
    plan = _role_plan_with_tasks()
    for module in plan["modules"]:
        for task in module["tasks"]:
            if task["phase"] == "verify":
                task["acceptance"].append("검증 초점: reconnect")
    board = build_project_board({"goal": "g", "verification_focus": ["reconnect"]}, plan)
    by_id = {t["task_id"]: t for t in board["tasks"]}
    assert by_id["t_verify"]["acceptance"].count("검증 초점: reconnect") == 1


# ----- board_prompt_digest: task_id/acceptance 노출 (P1-C, finding #1) -----
# LLM dispatch(dynamic_orchestrator._lilith_decide_next)는 board_prompt_digest로만
# 보드를 본다. task_id가 노출돼야 LLM이 echo → _resolve_task_meta() 성공 →
# build_project_board()가 주입한 acceptance(검증 초점)가 AgentSpecializer에 도달한다.


def test_board_prompt_digest_exposes_task_id_phase_and_acceptance():
    from core.project_task_board import build_project_board, board_prompt_digest
    brief = {"goal": "build app", "verification_focus": ["reconnect handling"]}
    board = build_project_board(brief, _role_plan_with_tasks())
    digest = board_prompt_digest(board)
    # LLM이 echo할 수 있도록 task_id가 노출된다.
    assert "task_id=t_verify" in digest
    assert "phase=verify" in digest
    # 주입된 검증 초점이 digest를 통해 LLM 프롬프트에 도달한다.
    assert "검증 초점: reconnect handling" in digest


def test_board_prompt_digest_bounds_acceptance_length():
    # public funnel이므로 과대 acceptance가 들어와도 프롬프트가 부풀지 않게 절단된다.
    from core.project_task_board import board_prompt_digest
    long_item = "x" * 600
    board = {
        "goal": "g", "execution_strategy": "parallel", "summary": {},
        "tasks": [{
            "task_id": "t1", "phase": "verify", "owner_role": "qa",
            "instruction": "verify", "status": "pending", "depends_on": [],
            "acceptance": [long_item],
        }],
    }
    digest = board_prompt_digest(board)
    accept_line = next(l for l in digest.splitlines() if l.strip().startswith("acceptance:"))
    # max_acceptance_chars=240 기본값에서 정확히 240자 + "..." 로 절단된다.
    assert accept_line == "    acceptance: " + "x" * 240 + "..."


def test_board_prompt_digest_empty_board_unchanged():
    from core.project_task_board import board_prompt_digest
    assert board_prompt_digest({}) == "No project board available."


# ----- verification_focus 주입 상한 (finding #3) + plan 문서 반영 (finding #2) -----


def test_build_project_board_caps_verification_focus_count():
    # 8개 초과 verification_focus는 MAX_VERIFICATION_FOCUS_ITEMS까지만 주입된다.
    from core.project_task_board import build_project_board, MAX_VERIFICATION_FOCUS_ITEMS
    focus = [f"검증항목{i}" for i in range(20)]
    board = build_project_board({"goal": "g", "verification_focus": focus}, _role_plan_with_tasks())
    by_id = {t["task_id"]: t for t in board["tasks"]}
    injected = [a for a in by_id["t_verify"]["acceptance"] if a.startswith("검증 초점:")]
    assert len(injected) == MAX_VERIFICATION_FOCUS_ITEMS


def test_build_project_board_trims_long_verification_focus_item():
    # 항목 길이가 MAX_VERIFICATION_FOCUS_ITEM_CHARS를 넘으면 절단된다.
    from core.project_task_board import build_project_board, MAX_VERIFICATION_FOCUS_ITEM_CHARS
    board = build_project_board(
        {"goal": "g", "verification_focus": ["y" * 500]}, _role_plan_with_tasks())
    by_id = {t["task_id"]: t for t in board["tasks"]}
    injected = next(a for a in by_id["t_verify"]["acceptance"] if a.startswith("검증 초점:"))
    assert injected == "검증 초점: " + "y" * MAX_VERIFICATION_FOCUS_ITEM_CHARS + "..."


def test_write_task_execution_plan_includes_injected_verification_focus(tmp_path):
    # finding #2: docs/task_execution_plan.md가 board의 주입 `검증 초점:`을 반영해야 한다.
    # 태스크 행을 role_plan이 아닌 board["tasks"]에서 렌더하므로 누락되지 않는다.
    from core.project_task_board import build_project_board, write_task_execution_plan
    brief = {"goal": "build app", "verification_focus": ["reconnect handling"]}
    role_plan = _role_plan_with_tasks()
    board = build_project_board(brief, role_plan)
    path = write_task_execution_plan(str(tmp_path), brief, role_plan, board)
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    assert "검증 초점: reconnect handling" in content
    # 기존 build 태스크 acceptance도 그대로 렌더된다 (회귀 방지).
    assert "기능 구현" in content


def test_clean_list_string_not_split_into_chars():
    # str 입력이 문자 단위로 분해되지 않고 1-item 리스트로 반환돼야 한다.
    from core.project_task_board import _clean_list
    assert _clean_list("hello") == ["hello"]


def test_clean_list_list_input_unchanged():
    from core.project_task_board import _clean_list
    assert _clean_list(["a", "b", "c"]) == ["a", "b", "c"]


def test_clean_list_none_returns_empty():
    from core.project_task_board import _clean_list
    assert _clean_list(None) == []


# ----- inject_review_tasks: review_provider 연결 (WI-2) -----


def _write_board(tmp_path, tasks: list) -> None:
    import json
    from core.project_task_board import BOARD_FILENAME
    (tmp_path / BOARD_FILENAME).write_text(json.dumps({"tasks": tasks}), encoding="utf-8")


def _completed_build(module_id: str = "backend_dev_module_1", provider_id: str = "claude_cli") -> dict:
    return {
        "task_id": f"{module_id}_build",
        "owner_role": "backend_dev",
        "phase": "build",
        "module_id": module_id,
        "provider_id": provider_id,
    }


def test_inject_review_tasks_single_available_provider_no_cross_validate(tmp_path, monkeypatch):
    # 가용 provider 1개 → cross_validate 태스크 미생성
    monkeypatch.setattr("core.providers.registry.detect_available_cli_providers", lambda: ["claude_cli"])
    _write_board(tmp_path, [{"task_id": "backend_dev_module_1_build", "owner_role": "backend_dev",
                              "module_id": "backend_dev_module_1", "phase": "build",
                              "status": "completed", "depends_on": []}])
    from core.project_task_board import inject_review_tasks
    result = inject_review_tasks(str(tmp_path), _completed_build())
    phases = [t["phase"] for t in result]
    assert "cross_validate" not in phases


def test_inject_review_tasks_two_available_providers_sets_review_provider(tmp_path, monkeypatch):
    # 가용 provider 2개 → cross_validate 태스크 생성 + review_provider 필드 설정
    monkeypatch.setattr(
        "core.providers.registry.detect_available_cli_providers",
        lambda: ["claude_cli", "codex_cli"],
    )
    monkeypatch.setattr(
        "core.providers.registry.pick_review_provider",
        lambda author: "codex_cli",
    )
    _write_board(tmp_path, [{"task_id": "backend_dev_module_1_build", "owner_role": "backend_dev",
                              "module_id": "backend_dev_module_1", "phase": "build",
                              "status": "completed", "depends_on": []}])
    from core.project_task_board import inject_review_tasks
    result = inject_review_tasks(str(tmp_path), _completed_build(provider_id="claude_cli"))
    cv_tasks = [t for t in result if t["phase"] == "cross_validate"]
    assert len(cv_tasks) == 1
    assert cv_tasks[0]["review_provider"] == "codex_cli"
