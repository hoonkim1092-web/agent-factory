"""F3 회귀 테스트 — agent_launcher CLI 모드 dispatch.

Round 4 dogfooding에서 발견된 차단성 마찰:
`python agent_launcher.py "free-form task"` 호출 시 argparse subparsers가
첫 positional을 subcommand로 잡아 `invalid choice` 오류 → task 실행 불가.

P4.5x fix: argv[0] 기반 사전 dispatch로 ad-hoc task 입력 경로 복원.
본 테스트는 _detect_mode 헬퍼의 4가지 케이스 + _build_arg_parser ad-hoc 파싱을
검증한다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_launcher import (
    AgentFactory,
    _detect_mode,
    _build_arg_parser,
    _maybe_isolate_project_root_for_self_run,
)  # noqa: E402


class TestDetectMode:
    def test_subcommand_project(self):
        assert _detect_mode(["project", "sync-todo", "/some/dir"]) == "subcommand"

    def test_ad_hoc_free_text(self):
        # Round 4의 실제 실패 케이스: 자연어 task
        assert _detect_mode(["NEXT_STEPS.md를 분리하라"]) == "ad_hoc"

    def test_ad_hoc_with_leading_flag(self):
        # 옵션이 먼저 오는 경우도 ad-hoc로 분류
        assert _detect_mode(["--mode", "approval", "task text"]) == "ad_hoc"

    def test_empty_argv(self):
        # 인자 없음 → ad_hoc (run-time에 prompt_mission_template으로 fallback)
        assert _detect_mode([]) == "ad_hoc"


class TestBuildArgParserAdHoc:
    def test_parses_free_text_task(self):
        parser = _build_arg_parser(ad_hoc_mode=True)
        args = parser.parse_args(["free-form task with spaces"])
        assert args.task == ["free-form task with spaces"]
        assert args.mode == "approval"  # 기본값
        assert args.role == "General"
        assert args.fsa is False
        assert args.build is False

    def test_parses_task_with_mode_flag(self):
        parser = _build_arg_parser(ad_hoc_mode=True)
        args = parser.parse_args(["--mode", "fsa", "task body"])
        assert args.task == ["task body"]
        assert args.mode == "fsa"

    def test_empty_task_allowed(self):
        # nargs="*" → task=[] 허용 (runtime이 interactive prompt로 보낸다)
        parser = _build_arg_parser(ad_hoc_mode=True)
        args = parser.parse_args([])
        assert args.task == []


class TestBuildArgParserSubcommand:
    def test_parses_project_sync_todo(self):
        parser = _build_arg_parser(ad_hoc_mode=False)
        args = parser.parse_args(["project", "sync-todo", "/path/to/project"])
        assert args.subcommand == "project"
        assert args.project_cmd == "sync-todo"
        assert args.project_dir == "/path/to/project"
        assert args.dry_run is False

    def test_parses_project_sync_todo_dry_run(self):
        parser = _build_arg_parser(ad_hoc_mode=False)
        args = parser.parse_args(["project", "sync-todo", "/x", "--dry-run"])
        assert args.dry_run is True

    def test_subcommand_required(self):
        parser = _build_arg_parser(ad_hoc_mode=False)
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestIsolateProjectRootForSelfRun:
    """F12 architectural fix — ad-hoc self-run 격리 회귀 테스트.

    Round 4/4b dogfooding 에서 발견된 projects/default/* + skills/registry.yaml
    leak (F9/F12) 차단. agent_launcher.py 의 isolation 함수가 (a) ad-hoc 모드만
    격리하고 (b) 사용자 명시 env 는 존중하는지 검증한다.
    """

    def test_skips_when_argv_empty(self, monkeypatch):
        monkeypatch.delenv("AGENT_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("AF_DISABLE_REGISTRY_WRITE", raising=False)
        monkeypatch.setattr(sys, "argv", ["agent_launcher.py"])
        _maybe_isolate_project_root_for_self_run()
        assert "AGENT_PROJECT_ROOT" not in os.environ
        assert "AF_DISABLE_REGISTRY_WRITE" not in os.environ

    def test_skips_for_subcommand(self, monkeypatch):
        monkeypatch.delenv("AGENT_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("AF_DISABLE_REGISTRY_WRITE", raising=False)
        monkeypatch.setattr(sys, "argv", ["agent_launcher.py", "project", "sync-todo", "/x"])
        _maybe_isolate_project_root_for_self_run()
        assert "AGENT_PROJECT_ROOT" not in os.environ
        assert "AF_DISABLE_REGISTRY_WRITE" not in os.environ

    def test_isolates_ad_hoc_text(self, monkeypatch):
        import tempfile

        monkeypatch.delenv("AGENT_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("AF_DISABLE_REGISTRY_WRITE", raising=False)
        monkeypatch.setattr(sys, "argv", ["agent_launcher.py", "free-form task"])
        _maybe_isolate_project_root_for_self_run()
        assert "AGENT_PROJECT_ROOT" in os.environ
        # tempdir 하위 + af_self_run prefix
        proj_root = os.environ["AGENT_PROJECT_ROOT"]
        assert proj_root.startswith(tempfile.gettempdir())
        assert "af_self_run_" in os.path.basename(proj_root)
        assert os.environ.get("AF_DISABLE_REGISTRY_WRITE") == "1"

    def test_respects_explicit_project_root(self, monkeypatch):
        """사용자가 AGENT_PROJECT_ROOT 명시 설정한 경우 격리 함수가 무위.

        production 사용 케이스: 사용자가 자기 프로젝트 dir 을 지정한 상태에서
        AF self-run 하면 그 dir 을 그대로 써야 함.
        """
        monkeypatch.setenv("AGENT_PROJECT_ROOT", "/explicit/user/path")
        monkeypatch.delenv("AF_DISABLE_REGISTRY_WRITE", raising=False)
        monkeypatch.setattr(sys, "argv", ["agent_launcher.py", "free-form task"])
        _maybe_isolate_project_root_for_self_run()
        # 사용자 설정 그대로 유지
        assert os.environ["AGENT_PROJECT_ROOT"] == "/explicit/user/path"
        # 격리 미수행 → AF_DISABLE_REGISTRY_WRITE 도 set 안 됨
        assert "AF_DISABLE_REGISTRY_WRITE" not in os.environ


class TestEnvFlagConvention:
    """High finding #1 회귀 — AF_DISABLE_REGISTRY_WRITE truthy semantics.

    cross-review (Round 4b commit 78e6a4be) 에서 발견: 이전 코드
    `os.environ.get("AF_DISABLE_REGISTRY_WRITE")` 는 "0"/"false"/"no" 도
    truthy 로 해석 → AF canonical convention (`core/file_io._env_flag`) 와
    정반대. 본 테스트는 AF 컨벤션 일치를 검증한다.
    """

    @pytest.mark.parametrize("truthy_val", ["1", "true", "yes", "on", "y", "True", "YES"])
    def test_env_flag_truthy_skips_write(self, truthy_val):
        from core.file_io import _env_flag
        os.environ["AF_DISABLE_REGISTRY_WRITE"] = truthy_val
        try:
            assert _env_flag("AF_DISABLE_REGISTRY_WRITE") is True
        finally:
            os.environ.pop("AF_DISABLE_REGISTRY_WRITE", None)

    @pytest.mark.parametrize("falsy_val", ["0", "false", "no", "off", "n", ""])
    def test_env_flag_falsy_allows_write(self, falsy_val):
        from core.file_io import _env_flag
        os.environ["AF_DISABLE_REGISTRY_WRITE"] = falsy_val
        try:
            assert _env_flag("AF_DISABLE_REGISTRY_WRITE") is False
        finally:
            os.environ.pop("AF_DISABLE_REGISTRY_WRITE", None)

    def test_env_flag_unset_allows_write(self, monkeypatch):
        from core.file_io import _env_flag
        monkeypatch.delenv("AF_DISABLE_REGISTRY_WRITE", raising=False)
        assert _env_flag("AF_DISABLE_REGISTRY_WRITE") is False


class TestPromptMissionTemplateImport:
    """잠재 NameError 회귀 — agent_launcher.py 가 empty argv 진입 시
    `prompt_mission_template` 함수를 호출하지만 P4.5x 까지 import 누락.
    별도 tiny fix 로 lazy import (함수 호출 직전) 추가.
    본 테스트는 회귀 방지: lazy import 라인이 누락되지 않았는지 source 에서 확인.
    """

    def test_prompt_mission_template_lazy_import_present(self):
        """empty argv path 에 lazy import 라인이 존재하는지 검증.

        eager import 는 inquirer 의존 때문에 불가 (core/template_input.py:1
        `import inquirer`). 따라서 모듈 top import 가 아니라 함수 안 lazy
        import 로 처리. 본 테스트는 그 lazy import 가 사라지지 않게 보장.
        """
        from pathlib import Path
        launcher_src = (Path(__file__).resolve().parents[1] / "agent_launcher.py").read_text(encoding="utf-8")
        assert "from core.template_input import prompt_mission_template" in launcher_src, (
            "prompt_mission_template lazy import missing — empty argv "
            "path (`if not task_input:`) 에서 NameError 발생할 위험."
        )


class TestSelfRunWorkspaceSplit:
    """F15/F17: user file workspace 와 runtime/internal-state workspace 분리."""

    def test_invoke_runner_forwards_runtime_workspace(self, tmp_path):
        calls = {}

        class Runner:
            def run(self, agent, task_input, run_id=None, auto_approve=False, workspace=None, runtime_workspace=None):
                calls.update(
                    {
                        "workspace": workspace,
                        "runtime_workspace": runtime_workspace,
                        "run_id": run_id,
                        "auto_approve": auto_approve,
                    }
                )
                return {"ok": True}

        factory = object.__new__(AgentFactory)
        factory.runner = Runner()

        user_ws = str(tmp_path / "repo")
        runtime_ws = str(tmp_path / "runtime")
        result = factory._invoke_runner(
            {"name": "agent"},
            "task",
            run_id="run_x",
            auto_approve=False,
            workspace=user_ws,
            runtime_workspace=runtime_ws,
        )

        assert result == {"ok": True}
        assert calls["workspace"] == user_ws
        assert calls["runtime_workspace"] == runtime_ws
        assert calls["run_id"] == "run_x"

    def test_agent_factory_run_splits_user_and_state_workspace(self, tmp_path, monkeypatch):
        factory = object.__new__(AgentFactory)
        factory.request_router = SimpleNamespace(route=lambda **_kwargs: {"pipeline": "single"})

        calls = {"agents": [], "reqs": [], "todos": [], "runner": []}

        def _get_agent(role_spec, workspace=None):
            calls["agents"].append(workspace)
            return {"name": "agent_general", "role": role_spec, "skills": []}

        def _analyze_requirements(_agent, _task_input, workspace=None):
            calls["reqs"].append(workspace)
            return {"missing_skills": [], "risk_level": "normal", "intent": "trivial"}

        def _ensure_single_run_todo(**kwargs):
            calls["todos"].append(kwargs["workspace"])
            return ""

        def _invoke_runner(_agent, _task_input, run_id, auto_approve, workspace=None, runtime_workspace=None):
            calls["runner"].append((workspace, runtime_workspace))
            return {"ok": True}

        factory._get_agent = _get_agent
        factory._analyze_requirements = _analyze_requirements
        factory._ensure_single_run_todo = _ensure_single_run_todo
        factory._missing_local_skill_files = lambda _agent: []
        factory._invoke_runner = _invoke_runner
        monkeypatch.setattr("agent_launcher.append_dashboard_run", lambda _payload: None)

        user_ws = str(tmp_path / "repo")
        runtime_ws = str(tmp_path / "runtime")
        factory.run(
            task_input="doc-only task",
            role_spec="General",
            workspace=user_ws,
            runtime_workspace=runtime_ws,
        )

        assert calls["agents"] == [runtime_ws]
        assert calls["reqs"] == [user_ws]
        assert calls["todos"] == [user_ws]
        assert calls["runner"] == [(user_ws, runtime_ws)]
