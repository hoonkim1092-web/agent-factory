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


# ── artifact shape 확장 (§17 Step 1) ─────────────────────────────────────────

def test_artifact_shape_interactive_has_required_fields(tmp_path):
    """Interactive mode: research_questions/risk_hints/assumptions default to []."""
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
            "대시보드 만들기",
            workspace=str(tmp_path),
            input_fn=lambda _prompt: "",
            print_fn=lambda _text: None,
        )

    brief = result["project_brief"]
    assert brief["research_questions"] == []
    assert brief["risk_hints"] == []
    assert brief["assumptions"] == []


def test_artifact_shape_deep_skip_derives_assumptions(tmp_path):
    """deep_skip mode: clarification_log 자동답변이 assumptions로 변환된다."""
    from core.interview import run_interview

    questions = [
        {
            "id": "Q1",
            "category": "ui",
            "question": "UI 형태?",
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
            "팟캐스트 앱",
            workspace=str(tmp_path),
            deep_skip=True,
        )

    brief = result["project_brief"]
    assumptions = brief["assumptions"]
    assert len(assumptions) == 2
    assert assumptions[0]["id"] == "A1"
    assert assumptions[0]["source"] == "deep_skip"
    assert assumptions[0]["confidence"] == "medium"
    assert "UI 형태?" in assumptions[0]["statement"]
    assert "웹" in assumptions[0]["statement"]
    assert assumptions[1]["id"] == "A2"
    assert brief["research_questions"] == []
    assert brief["risk_hints"] == []


def test_artifact_shape_non_interactive_assumptions_empty(tmp_path):
    """non_interactive (non deep_skip) mode: assumptions is [].

    Design intent: non_interactive is batch-interactive (defaults without LLM inference).
    Only deep_skip records auto-answers as assumptions (§17: "Deep Skip = LLM generates
    reasonable defaults and records assumptions"). non_interactive ≠ deep_skip.
    """
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
            "보고서 페이지",
            workspace=str(tmp_path),
            non_interactive=True,
        )

    brief = result["project_brief"]
    assert brief["assumptions"] == []
    assert brief["research_questions"] == []
    assert brief["risk_hints"] == []


def test_artifact_shape_no_questions(tmp_path):
    """질문이 없어도 3개 필드가 present."""
    from core.interview import run_interview

    with patch("core.interview.generate_clarification_questions", return_value=[]):
        result = run_interview(
            "간단한 스크립트",
            workspace=str(tmp_path),
            input_fn=lambda _prompt: "",
            print_fn=lambda _text: None,
        )

    brief = result["project_brief"]
    assert "research_questions" in brief
    assert "risk_hints" in brief
    assert "assumptions" in brief


def test_ensure_artifact_shape_does_not_overwrite_existing(tmp_path):
    """이미 필드가 있으면 _ensure_artifact_shape이 덮어쓰지 않는다."""
    from core.interview import _ensure_artifact_shape

    enriched = {
        "goal": "x",
        "clarification_log": [],
        "research_questions": ["rq1"],
        "risk_hints": ["risk1"],
        "assumptions": [{"id": "A1", "statement": "s", "source": "user", "confidence": "high"}],
    }
    result = _ensure_artifact_shape(enriched, deep_skip=True)
    assert result["research_questions"] == ["rq1"]
    assert result["risk_hints"] == ["risk1"]
    assert len(result["assumptions"]) == 1
    assert result["assumptions"][0]["source"] == "user"
