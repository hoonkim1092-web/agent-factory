from __future__ import annotations

import json
from unittest.mock import patch


def test_run_interview_collects_answers_and_writes_brief(tmp_path):
    from core.interview import run_interview

    questions = [
        {
            "id": "Q1",
            "category": "ui",
            "question": "UI 형태?",
            "why": "화면 범위 결정",
            "options": ["웹", "CLI"],
            "default": "웹",
        },
        {
            "id": "Q2",
            "category": "deployment",
            "question": "배포 대상?",
            "options": ["로컬", "AWS"],
            "default": "로컬",
        },
    ]

    with patch("core.interview.generate_clarification_questions", return_value=questions):
        result = run_interview(
            "관리자 대시보드 만들기",
            workspace=str(tmp_path),
            input_fn=lambda _prompt: "2",
            print_fn=lambda _text: None,
        )

    assert result["ok"] is True
    assert result["answers"] == ["CLI", "AWS"]
    assert result["project_brief"]["architecture_style"] == "CLI"
    assert "배포: AWS" in result["project_brief"]["constraints"]

    saved = json.loads((tmp_path / "planning" / "interview_brief.json").read_text(encoding="utf-8"))
    assert saved["task_input"] == "관리자 대시보드 만들기"
    assert len(saved["questions"]) == 2


def test_run_interview_non_interactive_applies_defaults(tmp_path):
    from core.interview import run_interview

    questions = [
        {
            "id": "Q1",
            "category": "ui",
            "question": "UI 형태?",
            "options": ["웹", "CLI"],
            "default": "웹",
        }
    ]

    with patch("core.interview.generate_clarification_questions", return_value=questions):
        result = run_interview(
            "보고서 페이지 만들기",
            workspace=str(tmp_path),
            non_interactive=True,
        )

    assert result["ok"] is True
    assert result["answers"] == ["웹"]
    assert result["project_brief"]["architecture_style"] == "웹"
    assert result["auto_answered"] is True
    assert result["deep_skip"] is False
    assert result["interview_mode"] == "non_interactive"


def test_run_interview_deep_skip_applies_llm_defaults_without_prompting(tmp_path):
    from core.interview import run_interview

    questions = [
        {
            "id": "Q1",
            "category": "scope",
            "question": "우선 범위?",
            "options": ["목록만", "목록+상세"],
            "default": "목록+상세",
        }
    ]

    def fail_input(_prompt):
        raise AssertionError("deep-skip must not prompt for input")

    with patch("core.interview.generate_clarification_questions", return_value=questions):
        result = run_interview(
            "팟캐스트 라이브러리 만들기",
            workspace=str(tmp_path),
            deep_skip=True,
            input_fn=fail_input,
        )

    assert result["ok"] is True
    assert result["answers"] == ["목록+상세"]
    assert result["auto_answered"] is True
    assert result["deep_skip"] is True
    assert result["interview_mode"] == "deep_skip"
    assert "목록+상세" in result["project_brief"]["deliverables"]


def test_run_interview_interactive_records_mode(tmp_path):
    from core.interview import run_interview

    questions = [
        {
            "id": "Q1",
            "category": "ui",
            "question": "UI 형태?",
            "options": ["웹", "CLI"],
            "default": "웹",
        }
    ]

    with patch("core.interview.generate_clarification_questions", return_value=questions):
        result = run_interview(
            "설정 화면 만들기",
            workspace=str(tmp_path),
            input_fn=lambda _prompt: "",
            print_fn=lambda _text: None,
        )

    assert result["auto_answered"] is False
    assert result["deep_skip"] is False
    assert result["interview_mode"] == "interactive"


def test_cli_main_requires_task(capsys):
    from core.interview import cli_main

    try:
        cli_main([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("cli_main should exit on empty task")

    captured = capsys.readouterr()
    assert "task is required" in captured.err
