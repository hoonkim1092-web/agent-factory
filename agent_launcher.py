# agent_factory_lite_secure.py
import os
import re
import time
import json
import ast
import yaml
import hashlib
import subprocess
import sys
import importlib.util
import inspect
import functools
import shutil
import atexit
from datetime import datetime
import getpass

# =============================================================================
# F12 architectural fix — ad-hoc self-run 격리 (Round 4 + 4b 발견)
# =============================================================================
# core.config_paths 가 import 시점에 AGENT_PROJECT_ROOT 를 읽어 PROJECT_ROOT 및
# 모든 derived path 상수(DASHBOARD_PATH, AGENTS_DIR, ...)를 frozen 한다. 따라서
# ad-hoc CLI 진입(자연어 task 입력)에서 default fallback(`projects/default/`)으로
# 떨어지지 않게 하려면 모든 core.* import 이전에 env 를 set 해야 한다.
# 동시에 skills/registry.yaml (SKILLS_DIR=BASE_DIR/skills 기반, PROJECT_ROOT 무관)
# 글로벌 write 도 차단 flag 로 막는다. 짝 코드: core/skill_preflight.py,
# core/registry_manager.py 의 _env_flag("AF_DISABLE_REGISTRY_WRITE") 가드.

# subcommand allowlist — isolation guard 와 아래 _detect_mode 양쪽이 공유 (single source of truth)
_KNOWN_SUBCOMMANDS = {"project", "dogfood"}


def _configure_cli_text_streams() -> None:
    """Keep CLI text output stable across Windows/macOS/Linux consoles."""
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("LC_ALL", "C.UTF-8")
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            if stream_name == "stdin":
                reconfigure(encoding="utf-8", errors="replace")
            else:
                reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _utf8_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")
    return env


_configure_cli_text_streams()


def _git_modified_files(cwd: str) -> list[str]:
    """현재 git working tree에서 수정된 파일 목록 반환 (staged + unstaged vs HEAD)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=cwd, timeout=10, env=_utf8_subprocess_env(),
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.splitlines() if f.strip()]
        # HEAD 없는 초기 커밋 환경 — unstaged + staged 모두 수집
        r_unstaged = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=cwd, timeout=10, env=_utf8_subprocess_env(),
        )
        r_staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=cwd, timeout=10, env=_utf8_subprocess_env(),
        )
        seen: set[str] = set()
        files: list[str] = []
        for line in r_unstaged.stdout.splitlines() + r_staged.stdout.splitlines():
            f = line.strip()
            if f and f not in seen:
                seen.add(f)
                files.append(f)
        return files
    except Exception:
        return []


def _scope_guard_report(cwd: str, allowed: list | None, baseline: frozenset | None = None) -> None:
    """FSA 실행 후 scope leak 자동 검사 (R3 scope guard enforce).

    allowed=None   : report-only (AF_SCOPE_GUARD_PATHS 미설정 시 변경 파일 목록 출력)
    allowed=[...]  : allowlist 대조 후 PASS/WARN 출력
    baseline       : FSA 실행 전 이미 수정된 파일 집합 — 제외 후 FSA 순 변경만 검사
    """
    all_modified = _git_modified_files(cwd)
    pre = baseline or frozenset()
    modified = [f for f in all_modified if f not in pre]

    if not modified:
        print("[Scope Guard] PASS - FSA 실행 중 변경 파일 없음")
        return

    if allowed is None:
        print(f"[Scope Guard] REPORT - FSA 변경 파일 {len(modified)}개 (AF_SCOPE_GUARD_PATHS 미설정):")
        for f in modified:
            print(f"  {f}")
        return

    allowed_norm = {os.path.normpath(p) for p in allowed}
    leaked = [f for f in modified if os.path.normpath(f) not in allowed_norm]
    if leaked:
        print(f"[Scope Guard] WARN - scope leak {len(leaked)}개: {leaked}")
        print(f"  허용: {sorted(allowed_norm)}")
        print(f"  FSA 변경: {modified}")
    else:
        print(f"[Scope Guard] PASS - 허용 파일 {len(modified)}개만 변경됨: {modified}")


def _maybe_isolate_project_root_for_self_run():
    """ad-hoc CLI 진입 시 isolated PROJECT_ROOT + 글로벌 registry write 차단 flag set.

    Skip 조건:
      - 사용자가 AGENT_PROJECT_ROOT 를 명시 설정 → 그대로 존중
      - argv 가 비어 있음 → interactive TUI 경로 (default fallback OK)
      - argv[0] in _KNOWN_SUBCOMMANDS → subcommand 일반 작업
    """
    if "AGENT_PROJECT_ROOT" in os.environ:
        return
    argv = sys.argv[1:]
    if not argv:
        return
    if argv[0] in _KNOWN_SUBCOMMANDS:
        return
    import tempfile
    isolated = os.path.join(
        tempfile.gettempdir(),
        f"af_self_run_{int(time.time())}_{os.getpid()}",
    )
    os.environ["AGENT_PROJECT_ROOT"] = isolated
    os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")
    os.environ.setdefault("AF_SELF_RUN", "1")  # skills/ 격리 신호 (core/utils.py 참조)
    atexit.register(shutil.rmtree, isolated, True)


if __name__ == "__main__":
    _maybe_isolate_project_root_for_self_run()
    # R3 scope guard: __main__ 경로에서만 등록 (test import 시 atexit 오염 방지)
    if os.getenv("AF_SELF_RUN"):
        _sg_raw = os.getenv("AF_SCOPE_GUARD_PATHS", "").strip()
        _sg_allowed = [p.strip() for p in _sg_raw.split(",") if p.strip()] if _sg_raw else None
        _sg_cwd = os.getcwd()
        _sg_baseline = frozenset(_git_modified_files(_sg_cwd))  # FSA 실행 전 baseline
        atexit.register(_scope_guard_report, _sg_cwd, _sg_allowed, _sg_baseline)

from config.schema import factory_config

# Core utilities are now imported from core.utils
from core.utils import *

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from core.registry import ToolRegistry
from core.tool_runtime import ToolRuntimeWrapper
from core.policy_runtime import PolicyRuntime
from core.hooks.event_bus import HookEventBus, IntentGateHook, TodoContinuationEnforcer, ToolOutputTruncator

# =============================================================================
# config.schema is loaded at top
from core.config_paths import *

# [Modularized] 프로젝트 초기화 — core/project_init.py 로 추출
from core.project_init import ensure_project_files
ensure_project_files()

# Constants are now imported from core.utils

# Internal classes and core utilities have been moved to the core/ directory
# for modularity and "Provision Readiness".

# =============================================================================
# Utils
# =============================================================================
# from core.utils import * # Now imported explicitly at the top
# Core components imported from specialized modules
from core.manager import AgentManager, RequirementAnalyzer
from core.researcher import HimariResearchAgent
from core.builder import SandboxedBuilder
from core.registry_manager import RegistryManager
from core.skill_procurer import SkillOrchestrator
from core.agent_runner import ModelRouter, AgentRunner
from core.git_manager import GitManager
from core.fsa_loop import FSALoop
from core.ise_loop import ISELoop
from core.dynamic_orchestrator import DynamicOrchestrator
from core.request_router import RequestRouter
from core.project_pipeline import ProjectPipeline
from core.message_broker import MessageBroker
from core.agent_reservation import AgentReservationManager
from core.conversation_manager import ConversationManager
from core.documentation_policy import ensure_documentation_files, single_task_todo_items, write_project_todo
# Redundant AST and Sandbox logic removed (handled by core.utils and core.executor)

# =============================================================================
# 4) Agent / Requirements
# =============================================================================
# AgentManager, RequirementAnalyzer, HimariResearchAgent, SandboxedBuilder, RegistryManager
# classes have been moved to core/manager.py for better modularity.
# =============================================================================
# 6) Registry / Workflow / Git
# =============================================================================
# RegistryManager moved to core/registry_manager.py

def _safe_write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class AgentFactory:
    def __init__(self):
        self.mr = ModelRouter()
        self.agent_mgr = AgentManager(self.mr)
        self.req = RequirementAnalyzer(self.mr)
        self.research = HimariResearchAgent(self.mr)
        self.builder = SandboxedBuilder(self.mr)
        self.registry = RegistryManager()
        self.git = GitManager()
        self.runner = AgentRunner(self.mr)

        # [VISUAL] 터미널 시각화 엔진 — 모든 컴포넌트가 공유
        from core.terminal_visualizer import TerminalVisualizer, set_visualizer
        self.visualizer = TerminalVisualizer()
        set_visualizer(self.visualizer)

        self.ultra = FSALoop(self.runner, self.agent_mgr, visualizer=self.visualizer)
        self.ise = ISELoop(fsa_loop=self.ultra, runner=self.runner, agent_mgr=self.agent_mgr, visualizer=self.visualizer)
        self.request_router = RequestRouter()

        # [COLLAB] 싱글톤 broker + reservation: 모든 오케스트레이터가 공유
        self.broker = MessageBroker()
        self.reservation_mgr = AgentReservationManager()

        # [GAP-3] Unified pipeline: Himari(Skeleton) + Builder(Release)
        self.procurer = SkillOrchestrator(
            registry=self.registry,
            research_agent=self.research,
            builder=self.builder,
            agent_mgr=self.agent_mgr,
        )
        self.project_pipeline = ProjectPipeline(
            mr=self.mr,
            agent_mgr=self.agent_mgr,
            research_agent=self.research,
            procurer=self.procurer,
            broker=self.broker,
            reservation_mgr=self.reservation_mgr,
            visualizer=self.visualizer,
        )

    def make_conversation_manager(self, project_id: str, workspace: str):
        """프로젝트별 ConversationManager 생성 (싱글톤 broker/reservation/visualizer 공유)."""
        return ConversationManager(
            project_id=project_id,
            workspace=workspace,
            broker=self.broker,
            agent_runner=self.runner,
            agent_mgr=self.agent_mgr,
            reservation_mgr=self.reservation_mgr,
            mr=self.mr,
            visualizer=self.visualizer,
        )

    def _missing_local_skill_files(self, agent: dict) -> list[str]:
        missing: list[str] = []
        for sid_raw in (agent.get("skills") or []):
            sid = safe_optional_id(str(sid_raw))
            if not sid:
                continue
            if not has_local_skill(sid):
                missing.append(sid)
        return list(dict.fromkeys(missing))

    def _read_autonomy_policy(self) -> dict:
        policies = read_project_policies()
        ap = policies.get("autonomy", {}) if isinstance(policies.get("autonomy"), dict) else {}
        return {
            "max_stage_retries": int(ap.get("max_stage_retries", 2) or 2),
            "strict_quality_gate": bool(ap.get("strict_quality_gate", True)),
            "stop_on_stage_failure": bool(ap.get("stop_on_stage_failure", True)),
        }

    def _read_approval_policy(self) -> dict:
        policies = read_project_policies()
        ap = policies.get("approval_policy", {}) if isinstance(policies.get("approval_policy"), dict) else {}
        return {
            "require_skill_change_approval": bool(ap.get("require_skill_change_approval", False))
        }

    def _ask_skill_change_approval(self, role_spec: str, skills: list[str], action: str, auto_approve: bool = False) -> bool:
        if not skills:
            return True
        if auto_approve:
            print(f"\n[FSA Mode] 스킬 자동 승인: {action} ({skills})")
            return True
        print("\n[승인 요청] 스킬 변경")
        print(f"- 대상 에이전트: {role_spec}")
        print(f"- 작업: {action}")
        print(f"- 스킬 목록: {skills}")
        ans = input("위 스킬 변경을 허용할까요? (yes/no): ").strip().lower()
        return ans in ("y", "yes")

    def _create_workflow_state(self, run_id: str, workflow_path: str, stages: list, base_roles: list[str]) -> str:
        run_dir = os.path.join(RUNS_DIR, run_id)
        os.makedirs(run_dir, exist_ok=True)
        state_path = os.path.join(run_dir, "state.json")
        data = {
            "run_id": run_id,
            "project_id": PROJECT_ID,
            "workflow_path": to_portable_path(workflow_path),
            "status": "running",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "base_roles": base_roles,
            "stages": [
                {
                    "id": str(s.get("id", "STAGE")),
                    "name": str(s.get("name", s.get("id", "STAGE"))),
                    "status": "pending",
                    "attempts": 0,
                    "last_error": "",
                    "updated_at": now_iso(),
                }
                for s in stages
            ],
        }
        _safe_write_json(state_path, data)
        return state_path

    def _update_workflow_state(self, state_path: str, stage_id: str, status: str, attempts: int = 0, last_error: str = ""):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        if str(data.get("workflow_path", "")).strip():
            data["workflow_path"] = to_portable_path(str(data.get("workflow_path")))
        for s in data.get("stages", []):
            if str(s.get("id")) == str(stage_id):
                s["status"] = status
                if attempts:
                    s["attempts"] = attempts
                if last_error:
                    s["last_error"] = last_error[:300]
                s["updated_at"] = now_iso()
                break
        data["updated_at"] = now_iso()
        _safe_write_json(state_path, data)

    def _finish_workflow_state(self, state_path: str, status: str):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        if str(data.get("workflow_path", "")).strip():
            data["workflow_path"] = to_portable_path(str(data.get("workflow_path")))
        data["status"] = status
        data["updated_at"] = now_iso()
        _safe_write_json(state_path, data)

    def _invoke_runner(
        self,
        agent: dict,
        task_input: str,
        run_id: str,
        auto_approve: bool,
        workspace: str | None = None,
        runtime_workspace: str | None = None,
    ):
        params = inspect.signature(self.runner.run).parameters
        kwargs = {}
        if "run_id" in params:
            kwargs["run_id"] = run_id
        if "auto_approve" in params:
            kwargs["auto_approve"] = auto_approve
        if "workspace" in params:
            kwargs["workspace"] = workspace
        if "runtime_workspace" in params:
            kwargs["runtime_workspace"] = runtime_workspace
        return self.runner.run(agent, task_input, **kwargs) or {}

    def _ensure_single_run_todo(
        self,
        task_input: str,
        role_spec: str,
        workspace: str,
        route: dict | None = None,
        reqs: dict | None = None,
    ) -> str:
        todo_path = os.path.join(workspace, ".todo.md")
        if os.path.exists(todo_path):
            return todo_path

        route_data = route if isinstance(route, dict) else {}
        req_data = reqs if isinstance(reqs, dict) else {}
        intent = str(req_data.get("intent") or route_data.get("intent") or "trivial").strip() or "trivial"
        risk_level = str(req_data.get("risk_level") or "normal").strip() or "normal"
        if not TodoContinuationEnforcer.requires_plan(task_input, intent=intent, risk_level=risk_level):
            return ""

        ensure_documentation_files(workspace)
        return write_project_todo(workspace, single_task_todo_items(task_input, role_spec))

    def _get_agent(self, role_spec: str, workspace: str | None = None) -> dict:
        params = inspect.signature(self.agent_mgr.get_or_create).parameters
        if "workspace" in params:
            return self.agent_mgr.get_or_create(role_spec, workspace=workspace)
        return self.agent_mgr.get_or_create(role_spec)

    def _analyze_requirements(self, agent: dict, task_input: str, workspace: str | None = None) -> dict:
        params = inspect.signature(self.req.analyze).parameters
        if "workspace" in params:
            return self.req.analyze(agent, task_input, workspace=workspace)
        return self.req.analyze(agent, task_input)

    @staticmethod
    def _collect_clarification_answers(questions: list) -> list[str]:
        """Clarification 질문을 출력하고 사용자 답변을 수집한다.

        Returns:
            답변 문자열 리스트 (질문 수와 동일한 길이).
            /skip 입력 시 모든 질문의 기본값으로 채운 리스트.
        """
        print()
        print("\033[36m" + "─" * 60 + "\033[0m")
        print("\033[1;36m  Clarification — 설계 정확도 향상\033[0m")
        print("\033[36m" + "─" * 60 + "\033[0m")
        print("  프로젝트를 더 정확하게 설계하기 위해 몇 가지 확인이 필요합니다.")
        print("  Enter = 기본값 사용,  /skip = 전체 스킵 (기본값 일괄 적용)")
        print()

        answers: list[str] = []
        for q in questions:
            q_id = q.get("id", "Q?")
            question_text = q.get("question", "")
            why = q.get("why", "")
            options = q.get("options") or []
            default = q.get("default", options[0] if options else "")

            print(f"  \033[33m{q_id}.\033[0m {question_text}")
            if why:
                print(f"      \033[90m→ {why}\033[0m")
            for i, opt in enumerate(options, 1):
                marker = "  \033[32m[기본값]\033[0m" if opt == default else ""
                print(f"      {i}) {opt}{marker}")

            try:
                raw = input("      답변: ").strip()
            except (EOFError, KeyboardInterrupt):
                raw = "/skip"

            if raw.lower() == "/skip":
                print("  \033[90m[스킵] 전체 질문 기본값 적용\033[0m")
                return [q.get("default", "") for q in questions]

            # 숫자 입력 → 해당 옵션 선택
            if raw.isdigit():
                idx = int(raw) - 1
                raw = options[idx] if 0 <= idx < len(options) else default

            answers.append(raw if raw else default)
            print()

        print("\033[36m" + "─" * 60 + "\033[0m")
        return answers

    def _run_project_with_approval(
        self,
        task_input: str,
        workspace: str,
        runtime_workspace: str | None,
        execution_mode: str,
        enable_build: bool,
        requested_role: str,
        route: dict,
    ) -> dict:
        """
        프로젝트 파이프라인을 2-Phase 로 실행한다.

        Phase 1a — prepare_brief(): Evidence + Brief 생성
        Phase 1.5 — Clarification: 모호성 제거 (approval 모드에서만)
        Phase 1b — prepare_documents(): RolePlan + TaskBoard + Documents
        승인 게이트: 사용자가 문서를 검토하고 승인 또는 편집
        Phase 2 — execute(): 승인 확인 → 에이전트 실행
        """
        # Phase 1a: Brief 생성
        print("\n[Pipeline] Phase 1a: Evidence + Brief 생성 중...")
        try:
            prepared_brief = self.project_pipeline.prepare_brief(
                task_input=task_input,
                workspace=workspace,
                runtime_workspace=runtime_workspace,
                execution_mode=execution_mode,
                enable_build=enable_build,
                requested_role=requested_role,
                route=route,
            )
        except Exception as exc:
            print(f"\n  [오류] Brief 생성 실패: {exc}")
            return {"ok": False, "reason": "prepare_failed", "message": str(exc)}

        # Phase 1.5: Clarification (approval 모드에서만)
        if execution_mode == "approval":
            try:
                from core.clarification import (
                    generate_clarification_questions,
                    should_skip_clarification,
                    merge_clarification,
                )
                pipeline_type = str((route or {}).get("pipeline", "project"))
                if not should_skip_clarification(
                    prepared_brief.project_brief,
                    pipeline=pipeline_type,
                    execution_mode=execution_mode,
                ):
                    questions = generate_clarification_questions(
                        prepared_brief.project_brief,
                        workspace=workspace,
                        run_id=prepared_brief.run_id,
                    )
                    if questions:
                        answers = self._collect_clarification_answers(questions)
                        prepared_brief.project_brief = merge_clarification(
                            prepared_brief.project_brief, questions, answers
                        )
                        # Clarification 반영 후 disk의 project_brief.json 원자적 갱신
                        _pb_path = prepared_brief.project_brief_path
                        if _pb_path:
                            try:
                                self.project_pipeline._write_json(
                                    _pb_path, prepared_brief.project_brief
                                )
                            except Exception as _write_exc:
                                print(f"  [Clarification] brief 파일 갱신 실패: {_write_exc}")
            except Exception as _clar_exc:
                print(f"  [Clarification] 스킵 (오류): {_clar_exc}")

        # Phase 1b: 문서 생성
        print("\n[Pipeline] Phase 1b: 문서 생성 중...")
        try:
            prepared = self.project_pipeline.prepare_documents(
                prepared_brief,
                execution_mode=execution_mode,
                enable_build=enable_build,
            )
        except Exception as exc:
            print(f"\n  [오류] 프로젝트 문서 생성 실패: {exc}")
            return {"ok": False, "reason": "prepare_failed", "message": str(exc)}

        # 생성된 문서 목록 출력
        print("\n" + "=" * 60)
        print("  프로젝트 문서가 생성되었습니다.")
        print("=" * 60)
        for line in prepared.summary_lines():
            print(line)
        print("\n  생성된 파일:")
        for path in prepared.planning_files:
            print(f"    - {path}")

        # 승인 루프
        gate = prepared.gate()
        while True:
            print("\n" + "-" * 60)
            print("  다음 중 선택하세요:")
            print("  [1] 승인하고 에이전트 실행 시작 (approve)")
            print("  [2] 문서를 편집한 후 다시 검토 (edit)")
            print("  [3] 실행 취소 (cancel)")
            print("-" * 60)

            try:
                choice = input("  선택 (1/2/3): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n\n  실행이 취소되었습니다.")
                return {"ok": False, "reason": "cancelled_by_user"}

            if choice in ("1", "approve", "a"):
                approved = gate.approve(approver="user", run_id=prepared.run_id)
                if not approved:
                    reason = gate.last_block_reason or "gate_file_missing"
                    print(f"  [오류] 승인 실패: {reason}")
                    return {"ok": False, "reason": reason}
                print("\n  승인 완료. Phase 2: 에이전트 실행을 시작합니다...")
                break

            elif choice in ("2", "edit", "e"):
                print(f"\n  문서 편집 위치: {prepared.work_item_dir()}")
                print("  다음 파일을 편집하세요:")
                for fname in ["feature-plan.md", "feature-spec.md",
                              "implementation-design.md", "implementation-tasks.md"]:
                    print(f"    - {fname}")
                print("\n  편집이 완료되면 Enter 를 누르세요.")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass
                print("  변경사항을 확인했습니다. 다시 검토 메뉴로 돌아갑니다.")
                gate.invalidate(reason="사용자 편집으로 재검토 필요")
                continue

            elif choice in ("3", "cancel", "c", "q"):
                print("\n  실행이 취소되었습니다.")
                return {"ok": False, "reason": "cancelled_by_user"}

            else:
                print("  올바른 선택지를 입력하세요: 1, 2, 3")

        # Phase 2: 실행
        result = self.project_pipeline.execute(
            prepared=prepared,
            enable_build=enable_build,
            execution_mode=execution_mode,
        )

        if result.get("ok"):
            roles = result.get("roles", [])
            board = result.get("board", {})
            completed = len(board.get("completed_subtasks", []))
            failed = len(board.get("failed_subtasks", []))
            print("\n" + "=" * 60)
            print("  프로젝트 실행 완료.")
            print(f"  역할: {', '.join(roles) if roles else '-'}")
            print(f"  완료 태스크: {completed}  실패 태스크: {failed}")
            print("=" * 60)
        else:
            reason = result.get("reason", "unknown")
            print(f"\n  [실패] {reason}: {result.get('message', '')}")
            if result.get("changed_files"):
                print(f"  변경된 파일: {result['changed_files']}")

        return result

    def run(
        self,
        task_input: str,
        role_spec: str = "General",
        enable_build: bool = False,
        execution_mode: str = "approval",
        workspace: str | None = None,
        runtime_workspace: str | None = None,
        pipeline_mode: str = "auto",
    ):
        run_id = f"run_{int(time.time())}"
        print(f"\nRUN={run_id}")
        print(f"- Role: {role_spec}")
        print(f"- Mode: {execution_mode}")
        print(f"- Task: {task_input}")

        route = self.request_router.route(task_input=task_input, role_spec=role_spec, pipeline_mode=pipeline_mode)
        state_workspace = runtime_workspace or workspace or PROJECT_ROOT
        if route.get("pipeline") == "project":
            target_workspace = workspace or PROJECT_ROOT
            print(f"\n[Router] project pipeline selected: {route.get('reasoning', '')}")
            if execution_mode in ("fsa", "ise"):
                return self.project_pipeline.run(
                    task_input=task_input,
                    workspace=target_workspace,
                    runtime_workspace=state_workspace,
                    execution_mode=execution_mode,
                    enable_build=enable_build,
                    requested_role=role_spec,
                    route=route,
                )
            return self._run_project_with_approval(
                task_input=task_input,
                workspace=target_workspace,
                runtime_workspace=state_workspace,
                execution_mode=execution_mode,
                enable_build=enable_build,
                requested_role=role_spec,
                route=route,
            )

        user_workspace = workspace or PROJECT_ROOT

        agent = self._get_agent(role_spec, workspace=state_workspace)
        reqs = self._analyze_requirements(agent, task_input, workspace=user_workspace)
        self._ensure_single_run_todo(
            task_input=task_input,
            role_spec=role_spec,
            workspace=user_workspace,
            route=route,
            reqs=reqs,
        )
        file_missing = self._missing_local_skill_files(agent)

        skills = reqs.get("missing_skills", [])
        initial_targets = list(dict.fromkeys([safe_optional_id(s) for s in skills] + file_missing))

        skipped_build_targets: list[str] = []
        if initial_targets and not enable_build:
            skipped_build_targets = list(initial_targets)
            print(f"\n[RunOnly] build disabled, skipping: {skipped_build_targets}")

        if initial_targets and enable_build:
            approval_policy = self._read_approval_policy()
            approval_gate = self._ask_skill_change_approval if approval_policy.get("require_skill_change_approval", False) else None
            # [GAP-3] Unified Pipeline: Himari(Skeleton) -> Builder(Release) -> Registry
            installed, _manifest = self.procurer.procure_multiple(
                agent=agent,
                skill_names=initial_targets,
                reqs=reqs,
                run_id=run_id,
                execution_mode=execution_mode,
                approval_gate=approval_gate,
                workspace=state_workspace,
            )
            if installed:
                agent = self._get_agent(role_spec, workspace=state_workspace)

        if execution_mode == "fsa":
            ultra_params = inspect.signature(self.ultra.run_mission).parameters
            ultra_kwargs = {"run_id": run_id}
            if "workspace" in ultra_params:
                ultra_kwargs["workspace"] = user_workspace
            if "runtime_workspace" in ultra_params:
                ultra_kwargs["runtime_workspace"] = state_workspace
            run_metrics = self.ultra.run_mission(agent, task_input, **ultra_kwargs) or {}
        elif execution_mode == "ise":
            ise_params = inspect.signature(self.ise.run_mission).parameters
            ise_kwargs = {"run_id": run_id}
            if "workspace" in ise_params:
                ise_kwargs["workspace"] = user_workspace
            if "runtime_workspace" in ise_params:
                ise_kwargs["runtime_workspace"] = state_workspace
            run_metrics = self.ise.run_mission(agent, task_input, **ise_kwargs) or {}
        else:
            invoke_params = inspect.signature(self._invoke_runner).parameters
            invoke_kwargs = {
                "run_id": run_id,
                "auto_approve": False,
                "workspace": user_workspace,
            }
            if "runtime_workspace" in invoke_params:
                invoke_kwargs["runtime_workspace"] = state_workspace
            run_metrics = self._invoke_runner(agent, task_input, **invoke_kwargs)

        append_dashboard_run(
            {
                "ts": now_iso(),
                "type": "single_run",
                "project_id": PROJECT_ID,
                "role": role_spec,
                "task": (task_input or "")[:300],
                "skills_loaded": list(agent.get("skills", []) if isinstance(agent, dict) else []),
                "ok": bool(run_metrics.get("ok", False)),
                "reason": str(run_metrics.get("reason", "")),
                "latency_ms": int(run_metrics.get("latency_ms", 0) or 0),
                "approval_rejects": int(run_metrics.get("approval_rejects", 0) or 0),
                "build_enabled": bool(enable_build),
                "missing_skills_detected": skipped_build_targets,
            }
        )
        return {
            "run_id": run_id,
            "ok": bool(run_metrics.get("ok", False)),
            "reason": str(run_metrics.get("reason", "")),
            "latency_ms": int(run_metrics.get("latency_ms", 0) or 0),
            "approval_rejects": int(run_metrics.get("approval_rejects", 0) or 0),
            "build_enabled": bool(enable_build),
            "missing_skills_detected": skipped_build_targets,
        }

    def run_dynamic_workflow(self, task_input: str, role_specs: list[str]):
        print(f"\n🧭 [DynamicWorkflow] 진정한 리더(Lilith) 주도의 동적 병렬 실행을 시작합니다.")
        orchestrator = DynamicOrchestrator(self.mr, visualizer=self.visualizer)
        state_board = orchestrator.run_project(task_input, role_specs)
        print(f"\n✅ [DynamicWorkflow] 완료. 보드 상태: {json.dumps(state_board, ensure_ascii=False)}")
        return state_board

    def run_workflow(self, task_input: str, workflow_path: str | None = None, role_specs: list[str] | None = None, use_dynamic: bool = False):
        # V3 Pivot: Only use dynamic orchestrator if explicitly requested
        if use_dynamic and role_specs:
            return self.run_dynamic_workflow(task_input, role_specs)

        if not workflow_path:
            policies = read_project_policies()
            wf_cfg = policies.get("workflow", {}) if isinstance(policies, dict) else {}
            default_tpl = str(wf_cfg.get("default_template", "")).strip()
            if default_tpl:
                cand = os.path.join(BASE_DIR, default_tpl)
                workflow_path = cand if os.path.exists(cand) else PROJECT_WORKFLOW_PATH
            else:
                workflow_path = PROJECT_WORKFLOW_PATH

        wf = read_yaml(workflow_path)
        if not wf:
            print(f"⚠️ [Workflow] 워크플로우를 읽을 수 없습니다: {workflow_path}")
            return

        owner = str(wf.get("owner_agent", "")).strip()
        stages = wf.get("stages", []) if isinstance(wf.get("stages"), list) else []
        picked_roles = [r.strip() for r in (role_specs or []) if str(r).strip()]
        if not picked_roles:
            picked_roles = [owner] if owner else ["General"]

        # ... (rest of the static workflow)
        if not stages:
            stages = [{"id": "MAIN", "name": "Main", "objective": task_input}]

        policies = read_project_policies()
        role_map = {}
        if isinstance(policies, dict):
            wf_cfg = policies.get("workflow", {}) if isinstance(policies.get("workflow"), dict) else {}
            role_map = wf_cfg.get("role_map", {}) if isinstance(wf_cfg.get("role_map"), dict) else {}

        print(f"\n🧭 [Workflow] 정적 파이프라인 시작: {workflow_path}")
        print(f"👥 [Workflow] 대상 에이전트: {picked_roles}")
        workflow_run_id = f"wf_{int(time.time())}"
        state_path = self._create_workflow_state(workflow_run_id, workflow_path, stages, picked_roles)
        autonomy = self._read_autonomy_policy()
        max_stage_retries = max(1, int(autonomy.get("max_stage_retries", 2)))
        strict_quality_gate = bool(autonomy.get("strict_quality_gate", True))
        stop_on_stage_failure = bool(autonomy.get("stop_on_stage_failure", True))
        run_count = 0
        failed = False
        for stage in stages:
            sid = str(stage.get("id", "STAGE"))
            sname = str(stage.get("name", sid))
            objective = str(stage.get("objective", "")).strip()
            mapped_roles = role_map.get(sid)
            stage_roles = [r.strip() for r in mapped_roles if str(r).strip()] if isinstance(mapped_roles, list) else picked_roles
            stage_task = (
                f"{task_input}\n"
                f"[Workflow Stage] id={sid}, name={sname}\n"
                f"[Stage Objective] {objective if objective else 'N/A'}"
            )
            print(f"\n📍 [Workflow] Stage {sid}: {sname}")
            self._update_workflow_state(state_path, sid, "in_progress")
            stage_ok = True
            stage_error = ""
            stage_attempts = 0
            for role in stage_roles:
                print(f"🤝 [Workflow] 실행 에이전트: {role}")
                role_ok = False
                role_reason = ""
                for attempt in range(1, max_stage_retries + 1):
                    stage_attempts = max(stage_attempts, attempt)
                    run_params = inspect.signature(self.run).parameters
                    run_kwargs = {"task_input": stage_task, "role_spec": role}
                    if "pipeline_mode" in run_params:
                        run_kwargs["pipeline_mode"] = "single"
                    result = self.run(**run_kwargs) or {}
                    run_count += 1
                    role_ok = bool(result.get("ok", False))
                    role_reason = str(result.get("reason", ""))
                    if role_ok:
                        break
                    print(f"⚠️ [Workflow] 재시도 예정: stage={sid}, role={role}, attempt={attempt}/{max_stage_retries}, reason={role_reason}")
                if not role_ok:
                    stage_ok = False
                    stage_error = f"role={role}, reason={role_reason}"
                    print(f"❌ [Workflow] 단계 실패: {stage_error}")
                    break
            if stage_ok:
                self._update_workflow_state(state_path, sid, "completed", attempts=stage_attempts)
            else:
                self._update_workflow_state(state_path, sid, "failed", attempts=stage_attempts, last_error=stage_error)
                failed = True
                if strict_quality_gate or stop_on_stage_failure:
                    print(f"🛑 [QualityGate] Stage `{sid}` 실패로 다음 단계를 중단합니다.")
                    break

        self._finish_workflow_state(state_path, "failed" if failed else "completed")
        append_dashboard_run(
            {
                "ts": now_iso(),
                "type": "workflow_run",
                "project_id": PROJECT_ID,
                "workflow_path": workflow_path,
                "stage_count": len(stages),
                "run_count": run_count,
                "base_roles": picked_roles,
                "ok": not failed,
                "state_path": state_path,
            }
        )
    
# =============================================================================
# CLI dispatch helpers (P4.5x — F3 fix)
# =============================================================================
# argparse subparsers greedily consume the first positional arg as a subcommand
# choice, which made `agent_launcher.py "free-form task text"` unreachable
# (Round 4 dogfooding F3). We pre-dispatch on argv[0] so both invocation styles
# work: `agent_launcher.py project sync-todo …` and `agent_launcher.py "task …"`.
# Note: _KNOWN_SUBCOMMANDS is defined near top of module (before heavy imports)
# because the isolation guard at module load also needs it.


def _detect_mode(argv):
    """Return 'subcommand' if argv[0] is a known subcommand, else 'ad_hoc'."""
    if not argv:
        return "ad_hoc"
    if argv[0] in _KNOWN_SUBCOMMANDS:
        return "subcommand"
    return "ad_hoc"


def _build_arg_parser(ad_hoc_mode):
    """Build argparse parser for either subcommand or ad-hoc task mode."""
    import argparse
    parser = argparse.ArgumentParser(description="Agent Factory CLI")
    if ad_hoc_mode:
        parser.add_argument("task", nargs="*", help="Task description (자연어)")
        parser.add_argument("--mode", choices=["approval", "fsa", "ise"], default="approval", help="Execution mode")
        parser.add_argument("--fsa", action="store_true", help="Shortcut for --mode fsa")
        parser.add_argument("--role", default="General", help="Agent role")
        parser.add_argument("--build", action="store_true", help="Enable skill building")
    else:
        subparsers = parser.add_subparsers(dest="subcommand", required=True)
        sync_todo_parser = subparsers.add_parser("project", help="프로젝트 관리 명령")
        sync_todo_sub = sync_todo_parser.add_subparsers(dest="project_cmd", required=True)
        sync_parser = sync_todo_sub.add_parser("sync-todo", help="board 상태로 .todo.md 재생성")
        sync_parser.add_argument("project_dir", help="프로젝트 디렉토리 경로")
        sync_parser.add_argument("--dry-run", action="store_true", help="diff만 출력, 파일 미수정")

        dogfood_parser = subparsers.add_parser("dogfood", help="Dogfood 파이프라인 실행")
        dogfood_sub = dogfood_parser.add_subparsers(dest="dogfood_cmd", required=True)

        df_run = dogfood_sub.add_parser("run", help="파이프라인 전체 실행 (PENDING → COMPLETE)")
        df_run.add_argument("task", help="태스크 설명 (자연어)")
        df_run.add_argument("--workspace", default=None, help="작업 디렉토리 (기본: CWD)")
        df_run.add_argument("--run-id", default=None, dest="run_id", help="런 ID (기본: 자동 생성)")
        df_run.add_argument(
            "--from-file", default=None, dest="from_file", metavar="PATH",
            help="사전 생성한 interview artifact JSON 경로 (지정 시 interview 단계 건너뜀)",
        )
        df_run.add_argument(
            "--non-interactive", action="store_true", dest="non_interactive",
            help="인터뷰를 자동으로 진행 (TTY 없는 환경에서 자동 활성)",
        )
        df_run.add_argument(
            "--merge", default="auto-policy", dest="merge_mode",
            choices=["auto-policy", "manual", "never"],
            help="머지 정책 (기본: auto-policy)",
        )

        df_interview = dogfood_sub.add_parser("interview", help="인터랙티브 인터뷰 실행 후 artifact 저장")
        df_interview.add_argument("task", nargs="+", help="요구사항을 구체화할 작업 설명")
        df_interview.add_argument("--workspace", default=None, help="작업 디렉토리 (기본: CWD)")
        df_interview.add_argument("--out", default=None, help="artifact JSON 저장 경로")
        df_interview.add_argument(
            "--non-interactive", action="store_true", dest="non_interactive",
            help="질문 기본값을 자동 적용 (배치 모드)",
        )
        df_interview.add_argument(
            "--deep-skip", action="store_true", dest="deep_skip",
            help="LLM이 기본값을 생성하고 가정(assumptions)으로 기록",
        )

        df_status = dogfood_sub.add_parser("status", help="런 상태 조회 (CWD 무관)")
        df_status.add_argument("run_id", help="런 ID")

        df_merge = dogfood_sub.add_parser("merge", help="manual 머지 실행")
        df_merge.add_argument("run_id", help="런 ID")
        df_merge.add_argument("--workspace", default=None, help="소스 작업 디렉토리 (기본: CWD)")
    return parser


# =============================================================================
# Example Entry Point
# =============================================================================
if __name__ == "__main__":
    _cli_mode = _detect_mode(sys.argv[1:])
    parser = _build_arg_parser(ad_hoc_mode=(_cli_mode == "ad_hoc"))
    args = parser.parse_args()

    if _cli_mode == "subcommand":
        if args.subcommand == "project" and getattr(args, "project_cmd", None) == "sync-todo":
            from core.project_task_board import sync_todo_from_board, load_project_board, board_todo_items
            from core.documentation_policy import write_project_todo, normalize_project_todo_items, _normalize_instruction, _mark_for_status, _instruction_status_map
            import os
            project_dir = os.path.abspath(args.project_dir)
            if args.dry_run:
                board = load_project_board(project_dir)
                if not board or not board.get("tasks"):
                    print("[sync] board가 비어있거나 없음 — 변경 없음")
                else:
                    status_map = _instruction_status_map(board)
                    items = normalize_project_todo_items(board_todo_items(board))
                    print(f"[sync] dry-run: {len(items)} items")
                    for item in items:
                        mark = _mark_for_status(status_map.get(_normalize_instruction(item)))
                        print(f"  - [{mark}] {item}")
            else:
                ok, msg = sync_todo_from_board(project_dir)
                prefix = "[sync]" if ok else "[sync] ERROR:"
                print(f"{prefix} {msg}")
            sys.exit(0)
        elif args.subcommand == "dogfood":
            from core.dogfood import (
                run_all, load_state, merge_dogfood_branch,
                MergePolicy, _default_runtime_workspace,
            )
            workspace = os.path.abspath(getattr(args, "workspace", None) or os.getcwd())
            if args.dogfood_cmd == "interview":
                from core.interview import run_interview
                task = " ".join(args.task).strip()
                print(f"[interview] task      : {task}")
                print(f"[interview] workspace : {workspace}")
                result = run_interview(
                    task,
                    workspace=workspace,
                    output_path=args.out,
                    non_interactive=args.non_interactive,
                    deep_skip=args.deep_skip,
                )
                if not result.get("ok"):
                    print(f"[interview] ERROR: {result.get('reason', 'unknown')}")
                    sys.exit(1)
                print(f"[interview] questions : {len(result.get('questions', []))}")
                print(f"[interview] saved     : {result.get('output_path')}")
                sys.exit(0)
            elif args.dogfood_cmd == "run":
                interview_artifact = None
                from_file = getattr(args, "from_file", None)
                if from_file:
                    import json as _json
                    try:
                        interview_artifact = _json.loads(
                            open(os.path.abspath(from_file), encoding="utf-8").read()
                        )
                    except (OSError, ValueError) as exc:
                        print(f"[dogfood] ERROR: --from-file 로드 실패: {exc}")
                        sys.exit(1)
                # Normalize CLI merge mode: "auto-policy" → "auto_policy"
                raw_mode = getattr(args, "merge_mode", "auto-policy")
                merge_mode = raw_mode.replace("-", "_")
                print(f"[dogfood] task      : {args.task}")
                print(f"[dogfood] workspace : {workspace}")
                print(f"[dogfood] merge     : {merge_mode}")
                if from_file:
                    print(f"[dogfood] from-file : {from_file}")
                state = run_all(
                    args.task, workspace, run_id=args.run_id,
                    interview_artifact=interview_artifact,
                    non_interactive=getattr(args, "non_interactive", False),
                    merge_mode=merge_mode,
                    strict_contract=True,
                )
                print(f"[dogfood] run_id    : {state.run_id}")
                print(f"[dogfood] phase     : {state.phase.value}")
                print(f"[dogfood] isolation : {state.isolation_status}")
                print(f"[dogfood] merge     : {state.merge_status}")
                if state.merged_commit:
                    print(f"[dogfood] merged_at : {state.merged_commit[:8]}")
                if state.last_failure:
                    print(f"[dogfood] failure   : {state.last_failure}")
                sys.exit(0 if state.phase.value == "complete" else 1)
            elif args.dogfood_cmd == "status":
                # CWD-independent: resolve runtime workspace from run_id only
                rt_ws = _default_runtime_workspace(args.run_id)
                try:
                    state = load_state(rt_ws, args.run_id)
                except FileNotFoundError:
                    print(f"[dogfood] run_id '{args.run_id}' 를 찾을 수 없음")
                    sys.exit(1)
                print(f"run_id            : {state.run_id}")
                print(f"phase             : {state.phase.value}")
                print(f"task              : {state.task}")
                print(f"source_branch     : {state.source_branch}")
                print(f"dogfood_branch    : {state.dogfood_branch}")
                print(f"base_ref          : {state.base_ref[:8] if state.base_ref else ''}")
                print(f"dogfood_commit    : {state.dogfood_commit[:8] if state.dogfood_commit else ''}")
                print(f"merge_mode        : {state.merge_mode}")
                print(f"merge_status      : {state.merge_status}")
                print(f"isolation_status  : {state.isolation_status}")
                print(f"worktree_workspace: {state.worktree_workspace}")
                print(f"runtime_workspace : {state.runtime_workspace}")
                print(f"attempts          : {state.attempts}")
                if state.last_failure:
                    print(f"last_failure      : {state.last_failure}")
                sys.exit(0)
            elif args.dogfood_cmd == "merge":
                rt_ws = _default_runtime_workspace(args.run_id)
                try:
                    state = load_state(rt_ws, args.run_id)
                except FileNotFoundError:
                    print(f"[dogfood] run_id '{args.run_id}' 를 찾을 수 없음")
                    sys.exit(1)
                merge_dogfood_branch(state)
                from core.dogfood import save_state
                save_state(state)
                print(f"[dogfood] merge_status: {state.merge_status}")
                if state.merged_commit:
                    print(f"[dogfood] merged_at  : {state.merged_commit[:8]}")
                if state.last_failure:
                    print(f"[dogfood] failure    : {state.last_failure}")
                sys.exit(0 if state.merge_status == "merged" else 1)
        else:
            parser.print_help()
            sys.exit(1)

    # Ad-hoc task mode
    task_input = " ".join(args.task).strip()
    if args.fsa or args.mode == "fsa":
        execution_mode = "fsa"
    elif args.mode == "ise":
        execution_mode = "ise"
    else:
        execution_mode = "approval"

    if not task_input:
        # Lazy import: prompt_mission_template 이 inquirer 의존이라 모듈 top
        # eager import 하면 inquirer 미설치 환경에서 모든 agent_launcher import 실패.
        # empty argv 경로에서만 호출되므로 함수 안에서 import.
        from core.template_input import prompt_mission_template
        task_input = prompt_mission_template("Agent Factory")

    AgentFactory().run(
        task_input=task_input,
        role_spec=args.role,
        enable_build=args.build,
        execution_mode=execution_mode,
        workspace=os.getcwd(),
        runtime_workspace=PROJECT_ROOT,
    )

