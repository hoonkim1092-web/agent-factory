"""User-facing deep interview workflow.

This module exposes the existing clarification engine as a direct product
surface. It is intentionally lightweight: it does not run the full project
pipeline, but produces an enriched brief that later planning/execution can use.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable

from core.clarification import (
    auto_apply_defaults,
    generate_clarification_questions,
    merge_clarification,
)


PrintFn = Callable[[str], None]
InputFn = Callable[[str], str]


def _default_output_path(workspace: str) -> str:
    return os.path.join(workspace, "planning", "interview_brief.json")


def _write_json(path: str, payload: dict[str, Any]) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, path)


def collect_answers(
    questions: list[dict[str, Any]],
    *,
    input_fn: InputFn = input,
    print_fn: PrintFn = print,
) -> list[str]:
    """Collect answers for generated clarification questions.

    Numeric choices select an option. Empty input selects the default. ``/skip``
    applies defaults for the current and remaining questions.
    """
    answers: list[str] = []
    for index, question in enumerate(questions, 1):
        text = str(question.get("question", "")).strip()
        why = str(question.get("why", "")).strip()
        options = [str(opt) for opt in question.get("options", [])]
        default = str(question.get("default", options[0] if options else "") or "")

        print_fn("")
        print_fn(f"Q{index}. {text}")
        if why:
            print_fn(f"   why: {why}")
        for option_index, option in enumerate(options, 1):
            suffix = " [default]" if option == default else ""
            print_fn(f"   {option_index}. {option}{suffix}")

        try:
            raw = input_fn("   answer: ").strip()
        except (EOFError, KeyboardInterrupt):
            raw = "/skip"

        if raw.lower() == "/skip":
            answers.append(default)
            for remaining in questions[index:]:
                remaining_options = [str(opt) for opt in remaining.get("options", [])]
                answers.append(str(remaining.get("default", remaining_options[0] if remaining_options else "") or ""))
            break
        if not raw:
            answers.append(default)
            continue
        if raw.isdigit():
            selected_index = int(raw) - 1
            if 0 <= selected_index < len(options):
                answers.append(options[selected_index])
                continue
        answers.append(raw)

    return answers


def run_interview(
    task_input: str,
    *,
    workspace: str | None = None,
    run_id: str = "",
    output_path: str | None = None,
    non_interactive: bool = False,
    input_fn: InputFn = input,
    print_fn: PrintFn = print,
) -> dict[str, Any]:
    """Generate clarification questions, collect answers, and save a brief."""
    task = str(task_input or "").strip()
    if not task:
        return {"ok": False, "reason": "empty_task"}

    target_workspace = os.path.abspath(workspace or os.getcwd())
    base_brief: dict[str, Any] = {
        "goal": task,
        "task_input": task,
    }

    questions = generate_clarification_questions(
        base_brief,
        workspace=target_workspace,
        run_id=run_id,
    )
    if non_interactive:
        enriched = auto_apply_defaults(base_brief, questions)
        answers = [entry.get("answer", "") for entry in enriched.get("clarification_log", [])]
    else:
        answers = collect_answers(questions, input_fn=input_fn, print_fn=print_fn) if questions else []
        enriched = merge_clarification(base_brief, questions, answers) if questions else {
            **base_brief,
            "clarification_log": [],
        }

    payload = {
        "task_input": task,
        "questions": questions,
        "answers": answers,
        "project_brief": enriched,
    }
    path = output_path or _default_output_path(target_workspace)
    _write_json(path, payload)
    payload["output_path"] = path
    payload["ok"] = True
    return payload


def cli_main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="af interview")
    parser.add_argument("task", nargs="*", help="요구사항을 구체화할 작업 설명")
    parser.add_argument("--workspace", "-w", default=None, help="결과를 저장할 workspace")
    parser.add_argument("--out", default=None, help="interview JSON 출력 경로")
    parser.add_argument("--non-interactive", action="store_true", help="질문 기본값을 자동 적용")
    args = parser.parse_args(argv)

    task = " ".join(args.task).strip()
    if not task:
        parser.error("task is required")

    result = run_interview(
        task,
        workspace=args.workspace,
        output_path=args.out,
        non_interactive=args.non_interactive,
    )
    if not result.get("ok"):
        raise SystemExit(1)

    print("")
    print(f"[interview] questions={len(result.get('questions', []))}")
    print(f"[interview] saved: {result.get('output_path')}")
