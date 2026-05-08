"""8x8 CLI 지뢰찾기 단위 테스트 스위트.

테스트 대상 공개 인터페이스:
- create_board(size: int = 8, mine_count: int = 10) -> Board
- place_mines(board: Board, first_click: tuple[int, int]) -> None
- reveal_cell(board: Board, row: int, col: int) -> None
- toggle_flag(board: Board, row: int, col: int) -> None
- check_game_state(board: Board) -> str
- render_board(board: Board, reveal_all: bool = False) -> str
- parse_command(raw: str) -> tuple[str, int, int]
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable

import pytest


@pytest.fixture(scope="module")
def ms():
    """테스트 대상 모듈을 동적으로 로드한다."""
    return importlib.import_module("minesweeper")


def _get(board, key: str, default=None):
    """Board가 dict/객체 어느 형태여도 값을 가져온다."""
    if isinstance(board, dict):
        return board.get(key, default)
    return getattr(board, key, default)


def _cells_iter(board) -> Iterable:
    """보드 셀을 순회 가능한 형태로 정규화한다."""
    cells = _get(board, "cells")
    if cells is None:
        pytest.fail("Board에 cells 속성/키가 없습니다.")
    return cells


def _cell(board, row: int, col: int):
    cells = _cells_iter(board)
    try:
        return cells[row][col]
    except Exception as exc:  # pragma: no cover - 실패 메시지 품질 강화
        pytest.fail(f"cells[row][col] 접근 실패: {exc}")


def _cell_get(cell, key: str, default=None):
    if isinstance(cell, dict):
        return cell.get(key, default)
    return getattr(cell, key, default)


def _count_mines(board) -> int:
    mines = 0
    for row in _cells_iter(board):
        for cell in row:
            if _cell_get(cell, "is_mine", False):
                mines += 1
    return mines


def _count_revealed_safe_cells(board) -> int:
    revealed = 0
    for row in _cells_iter(board):
        for cell in row:
            if _cell_get(cell, "revealed", False) and not _cell_get(cell, "is_mine", False):
                revealed += 1
    return revealed


# 슬라이스 1: 초기화/입력 파싱

def test_create_board_defaults(ms):
    board = ms.create_board()
    assert _get(board, "size") == 8
    assert _get(board, "mine_count") == 10
    cells = _cells_iter(board)
    assert len(cells) == 8
    assert all(len(row) == 8 for row in cells)


def test_create_board_rejects_invalid_mine_count(ms):
    with pytest.raises((ValueError, AssertionError)):
        ms.create_board(size=8, mine_count=0)
    with pytest.raises((ValueError, AssertionError)):
        ms.create_board(size=8, mine_count=64)


def test_parse_command_reveal(ms):
    cmd, row, col = ms.parse_command("3 4")
    assert (cmd, row, col) == ("r", 3, 4)


def test_parse_command_flag(ms):
    cmd, row, col = ms.parse_command("f 2 5")
    assert (cmd, row, col) == ("f", 2, 5)


def test_parse_command_rejects_invalid(ms):
    invalid_inputs = ["abc", "r 1", "f a b", "9 0", "f 8 1"]
    for raw in invalid_inputs:
        with pytest.raises((ValueError, AssertionError)):
            ms.parse_command(raw)


# 슬라이스 2: 첫 클릭 안전 지뢰 배치

def test_place_mines_keeps_first_click_safe(ms):
    board = ms.create_board(size=8, mine_count=10)
    first_click = (3, 3)
    ms.place_mines(board, first_click)

    cell = _cell(board, first_click[0], first_click[1])
    assert _cell_get(cell, "is_mine", False) is False
    assert _count_mines(board) == 10


# 슬라이스 3: 공개/연쇄 공개

def test_reveal_cell_skips_flagged_cell(ms):
    board = ms.create_board(size=8, mine_count=10)
    ms.place_mines(board, (0, 0))
    ms.toggle_flag(board, 1, 1)
    ms.reveal_cell(board, 1, 1)

    cell = _cell(board, 1, 1)
    assert _cell_get(cell, "revealed", False) is False


def test_reveal_cell_cascade_on_zero_adjacent(ms):
    board = ms.create_board(size=8, mine_count=1)
    ms.place_mines(board, (7, 7))
    ms.reveal_cell(board, 7, 7)

    assert _count_revealed_safe_cells(board) > 1


# 슬라이스 4: 깃발/상태 전이

def test_toggle_flag_toggles_state(ms):
    board = ms.create_board(size=8, mine_count=10)
    ms.toggle_flag(board, 2, 2)
    assert _cell_get(_cell(board, 2, 2), "flagged", False) is True

    ms.toggle_flag(board, 2, 2)
    assert _cell_get(_cell(board, 2, 2), "flagged", False) is False


def test_check_game_state_lose_after_revealing_mine(ms):
    board = ms.create_board(size=8, mine_count=1)
    ms.place_mines(board, (0, 0))

    mine_pos = None
    for r, row in enumerate(_cells_iter(board)):
        for c, cell in enumerate(row):
            if _cell_get(cell, "is_mine", False):
                mine_pos = (r, c)
                break
        if mine_pos is not None:
            break

    assert mine_pos is not None
    ms.reveal_cell(board, mine_pos[0], mine_pos[1])
    assert ms.check_game_state(board) == "LOSE"


def test_check_game_state_win_when_all_safe_revealed(ms):
    board = ms.create_board(size=8, mine_count=1)
    ms.place_mines(board, (0, 0))

    for r, row in enumerate(_cells_iter(board)):
        for c, cell in enumerate(row):
            if not _cell_get(cell, "is_mine", False):
                ms.reveal_cell(board, r, c)

    assert ms.check_game_state(board) == "WIN"


# 슬라이스 5: 렌더링

def test_render_board_returns_ascii_grid(ms):
    board = ms.create_board(size=8, mine_count=10)
    rendered = ms.render_board(board)

    assert isinstance(rendered, str)
    assert "0" in rendered
    assert "7" in rendered
    assert "?" in rendered or "F" in rendered


def test_render_board_reveal_all_shows_mine_symbol(ms):
    board = ms.create_board(size=8, mine_count=1)
    ms.place_mines(board, (0, 0))

    rendered = ms.render_board(board, reveal_all=True)
    assert "*" in rendered
