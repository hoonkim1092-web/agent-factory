"""`/output` 슬래시 명령 테스트.

비개발자가 `/output <폴더>` 한 줄로 결과 저장 폴더를 바꿀 수 있어야 하고,
그 변경이 self.workspace 에 반영돼 다음 턴 run 으로 흘러가야 한다(배포 동등성).
"""
import os

import pytest

from core.interactive_chat import InteractiveChat


def _make_chat(workspace: str) -> InteractiveChat:
    # __init__ 은 start() 없이 가볍게 동작 — workspace/project_id 만 필요.
    return InteractiveChat(agent={"name": "T", "role": "tester"}, workspace=workspace)


def test_set_output_dir_changes_workspace(tmp_path):
    chat = _make_chat(str(tmp_path / "old"))
    target = tmp_path / "new_out"
    ok, msg = chat.set_output_dir(str(target))
    assert ok
    assert chat.workspace == os.path.abspath(str(target))
    # 다음 턴 run 이 읽는 바로 그 필드가 바뀌어야 한다.
    assert os.path.isdir(chat.workspace)
    assert str(target.name) in msg or chat.workspace in msg


def test_set_output_dir_creates_missing_folder(tmp_path):
    chat = _make_chat(str(tmp_path / "old"))
    target = tmp_path / "deep" / "nested" / "out"
    assert not target.exists()
    ok, _ = chat.set_output_dir(str(target))
    assert ok
    assert os.path.isdir(chat.workspace)


def test_set_output_dir_strips_surrounding_quotes(tmp_path):
    chat = _make_chat(str(tmp_path / "old"))
    target = tmp_path / "quoted"
    ok, _ = chat.set_output_dir(f'"{target}"')
    assert ok
    assert chat.workspace == os.path.abspath(str(target))


def test_set_output_dir_expands_user(tmp_path, monkeypatch):
    chat = _make_chat(str(tmp_path / "old"))
    # ~ 가 확장되는지만 검증 (실제 홈에 폴더 생성 방지 위해 HOME 을 tmp 로)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    ok, _ = chat.set_output_dir(os.path.join("~", "afout"))
    assert ok
    assert "~" not in chat.workspace


def test_set_output_dir_empty_is_rejected(tmp_path):
    chat = _make_chat(str(tmp_path / "keep"))
    before = chat.workspace
    ok, msg = chat.set_output_dir("   ")
    assert not ok
    assert chat.workspace == before  # 실패 시 기존 폴더 유지
    assert "사용법" in msg


def test_handle_command_output_no_arg_prints_current(tmp_path, capsys):
    ws = str(tmp_path / "cur")
    chat = _make_chat(ws)
    handled = chat.handle_command("/output")
    assert handled is True
    out = capsys.readouterr().out
    assert ws in out


def test_handle_command_output_with_arg_sets(tmp_path, capsys):
    chat = _make_chat(str(tmp_path / "old"))
    target = tmp_path / "via_cmd"
    handled = chat.handle_command(f"/output {target}")
    assert handled is True
    assert chat.workspace == os.path.abspath(str(target))


def test_handle_command_output_preserves_path_case(tmp_path):
    """cmd 는 소문자화되지만 경로는 원본에서 떼므로 대소문자가 보존돼야 한다(멀티OS)."""
    chat = _make_chat(str(tmp_path / "old"))
    target = tmp_path / "MixedCaseDir"
    chat.handle_command(f"/output {target}")
    # 경로 마지막 구성요소의 대소문자가 살아있어야 한다.
    assert os.path.basename(chat.workspace) == "MixedCaseDir"


def test_handle_command_unknown_returns_false(tmp_path):
    chat = _make_chat(str(tmp_path))
    assert chat.handle_command("/nope") is False


def test_banner_shows_output_folder(tmp_path, capsys):
    from core.interactive_chat import _print_banner

    ws = str(tmp_path / "내작업폴더")
    _print_banner("proj", "tester", "claude_cli", "auto", ws)
    out = capsys.readouterr().out
    assert ws in out
    assert "결과 저장" in out
    assert "/output" in out
