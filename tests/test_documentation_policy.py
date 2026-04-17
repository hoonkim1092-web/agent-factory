import importlib
import os


def test_ensure_documentation_files_creates_korean_skeletons(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_DOC_LANGUAGE_CODE", "ko-KR")

    from core.documentation_policy import ensure_documentation_files

    result = ensure_documentation_files(str(tmp_path))

    architecture_path = tmp_path / "docs" / "architecture.md"
    history_path = tmp_path / "docs" / "change_history.md"

    assert architecture_path.exists()
    assert history_path.exists()
    assert result["architecture_path"] == str(architecture_path)
    assert result["change_history_path"] == str(history_path)
    architecture_text = architecture_path.read_text(encoding="utf-8")
    history_text = history_path.read_text(encoding="utf-8")

    assert "# 아키텍처" in architecture_text
    assert "## 문서 규칙" in architecture_text
    assert "`ko-KR`" in architecture_text
    assert "# 변경 이력" in history_text
    assert "## 이력" in history_text


def test_documentation_policy_falls_back_to_english_templates(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_DOC_LANGUAGE_CODE", "en_US.UTF-8")

    from core.documentation_policy import ensure_documentation_files, get_document_language_code

    result = ensure_documentation_files(str(tmp_path))

    assert get_document_language_code() == "en-US"
    assert "# Architecture" in (tmp_path / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert "# Change History" in (tmp_path / "docs" / "change_history.md").read_text(encoding="utf-8")
    assert result["architecture_path"] == str(tmp_path / "docs" / "architecture.md")


def test_inject_documentation_contract_is_idempotent(monkeypatch):
    monkeypatch.setenv("AGENT_DOC_LANGUAGE_CODE", "ko-KR")

    from core.documentation_policy import inject_documentation_contract

    base = "system prompt"
    combined = inject_documentation_contract(base)

    assert "system prompt" in combined
    assert "docs/architecture.md" in combined
    assert "docs/change_history.md" in combined
    assert "ko-KR" in combined
    assert "한국어" in combined
    assert "[Design Review Contract]" in combined
    assert "docs/plans/" in combined
    assert "review_request" in combined
    assert inject_documentation_contract(combined) == combined


def _make_board(*tasks):
    return {"tasks": [{"instruction": instr, "status": status} for instr, status in tasks]}


def test_write_project_todo_no_board_all_unchecked(tmp_path):
    from core.documentation_policy import write_project_todo
    write_project_todo(str(tmp_path), ["Task A", "Task B"])
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert "- [ ] Task A" in content
    assert "- [ ] Task B" in content


def test_write_project_todo_board_completed(tmp_path):
    from core.documentation_policy import write_project_todo
    board = _make_board(("Task A", "completed"), ("Task B", "pending"))
    write_project_todo(str(tmp_path), ["Task A", "Task B"], board=board)
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert "- [x] Task A" in content
    assert "- [ ] Task B" in content


def test_write_project_todo_board_in_progress(tmp_path):
    from core.documentation_policy import write_project_todo
    board = _make_board(("Task A", "in_progress"))
    write_project_todo(str(tmp_path), ["Task A"], board=board)
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert "- [/] Task A" in content


def test_write_project_todo_board_blocked_failed(tmp_path):
    from core.documentation_policy import write_project_todo
    board = _make_board(("Task B", "blocked"), ("Task F", "failed"))
    write_project_todo(str(tmp_path), ["Task B", "Task F"], board=board)
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert "- [!] Task B" in content
    assert "- [!] Task F" in content


def test_write_project_todo_documentation_items_always_unchecked(tmp_path):
    from core.documentation_policy import write_project_todo, documentation_todo_items
    doc_items = documentation_todo_items()
    board = _make_board()
    write_project_todo(str(tmp_path), [], board=board)
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    for item in doc_items:
        assert f"- [ ] {item}" in content


def test_write_project_todo_duplicate_instruction_conservative(tmp_path):
    from core.documentation_policy import write_project_todo
    board = {"tasks": [
        {"instruction": "Task A", "status": "completed"},
        {"instruction": "Task A", "status": "pending"},
    ]}
    write_project_todo(str(tmp_path), ["Task A"], board=board)
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    # pending 우선 → [ ]
    assert "- [ ] Task A" in content
    assert "- [x]" not in content


def test_write_project_todo_long_instruction_no_truncation(tmp_path):
    from core.documentation_policy import write_project_todo
    instr_a = "Implement unit tests for the authentication module and verify edge cases thoroughly"
    instr_b = "Implement unit tests for the authentication module and verify boundary conditions"
    board = _make_board((instr_a, "completed"), (instr_b, "pending"))
    write_project_todo(str(tmp_path), [instr_a, instr_b], board=board)
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert f"- [x] {instr_a}" in content
    assert f"- [ ] {instr_b}" in content


def test_write_project_todo_whitespace_normalization(tmp_path):
    from core.documentation_policy import write_project_todo
    board = _make_board(("Task  A", "completed"))
    write_project_todo(str(tmp_path), ["Task  A"], board=board)
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert "- [x]" in content


def test_update_project_board_task_syncs_todo(tmp_path, monkeypatch):
    import json
    from core.project_task_board import update_project_board_task, write_project_board

    board = {
        "tasks": [
            {"task_id": "t1", "instruction": "Do something", "owner_role": "dev", "status": "pending"},
        ]
    }
    write_project_board(str(tmp_path), board)
    monkeypatch.setenv("AF_TODO_SYNC", "1")
    update_project_board_task(str(tmp_path), "dev", "Do something", "completed", task_id="t1")
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert "- [x] Do something" in content


def test_update_project_board_task_todo_sync_disabled(tmp_path, monkeypatch):
    import json
    from core.project_task_board import update_project_board_task, write_project_board

    board = {
        "tasks": [
            {"task_id": "t1", "instruction": "Do something", "owner_role": "dev", "status": "pending"},
        ]
    }
    write_project_board(str(tmp_path), board)
    monkeypatch.setenv("AF_TODO_SYNC", "0")
    (tmp_path / ".todo.md").write_text("original\n", encoding="utf-8")
    update_project_board_task(str(tmp_path), "dev", "Do something", "completed", task_id="t1")
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")
    assert content == "original\n"


def test_project_pipeline_todo_includes_documentation_tasks(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_DOC_LANGUAGE_CODE", "ko-KR")

    import core.config_paths

    importlib.reload(core.config_paths)

    from core.project_pipeline import ProjectPipeline

    pipeline = ProjectPipeline.__new__(ProjectPipeline)
    todo_path = pipeline._write_todo(str(tmp_path), {"todo_items": ["Implement starter workflow"]})
    content = (tmp_path / ".todo.md").read_text(encoding="utf-8")

    assert todo_path == str(tmp_path / ".todo.md")
    assert "- [ ] Implement starter workflow" in content
    assert "docs/architecture.md" in content
    assert "docs/change_history.md" in content
    assert "# 프로젝트 TODO" in content
    assert "운영체제 언어 코드 `ko-KR`" in content
