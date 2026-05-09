from src.game_logic import Coord, createGame, getGameStatus, openCell, toggleFlag


def test_create_game_keeps_first_click_safe():
    state = createGame(8, 8, 10, firstClick=Coord(0, 0), seed=42)
    assert state.board[0][0].isMine is False


def test_open_mine_transitions_to_lost():
    state = createGame(3, 3, 1, seed=0)
    mine = next((Coord(x, y) for y, row in enumerate(state.board) for x, cell in enumerate(row) if cell.isMine), None)
    assert mine is not None

    result = openCell(state, mine)
    assert result.status == "lost"
    assert result.board[mine.y][mine.x].isOpen is True


def test_toggle_flag_works_only_for_closed_cells():
    state = createGame(4, 4, 0)
    flagged = toggleFlag(state, Coord(1, 1))
    assert flagged.board[1][1].isFlagged is True

    opened = openCell(flagged, Coord(0, 0))
    unchanged = toggleFlag(opened, Coord(0, 0))
    assert unchanged == opened


def test_cascade_open_opens_neighbors_for_zero_adjacent():
    state = createGame(3, 3, 0)
    result = openCell(state, Coord(1, 1))

    opened = sum(1 for row in result.board for cell in row if cell.isOpen)
    assert opened == 9
    assert getGameStatus(result) == "won"


def test_win_transition_when_all_safe_opened():
    state = createGame(2, 2, 1, firstClick=Coord(0, 0), seed=3)

    for y in range(state.height):
        for x in range(state.width):
            if not state.board[y][x].isMine:
                state = openCell(state, Coord(x, y))

    assert state.status == "won"
