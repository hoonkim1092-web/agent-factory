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

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_launcher import (
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
