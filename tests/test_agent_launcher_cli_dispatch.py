"""F3 회귀 테스트 — agent_launcher CLI 모드 dispatch.

Round 4 dogfooding에서 발견된 차단성 마찰:
`python agent_launcher.py "free-form task"` 호출 시 argparse subparsers가
첫 positional을 subcommand로 잡아 `invalid choice` 오류 → task 실행 불가.

P4.5x fix: argv[0] 기반 사전 dispatch로 ad-hoc task 입력 경로 복원.
본 테스트는 _detect_mode 헬퍼의 4가지 케이스 + _build_arg_parser ad-hoc 파싱을
검증한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_launcher import _detect_mode, _build_arg_parser  # noqa: E402


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
