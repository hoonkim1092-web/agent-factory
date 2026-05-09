from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Literal

GameStatus = Literal["ready", "playing", "won", "lost"]


@dataclass(frozen=True)
class Cell:
    isMine: bool = False
    isOpen: bool = False
    isFlagged: bool = False
    adjacentMines: int = 0


@dataclass(frozen=True)
class Coord:
    x: int
    y: int


@dataclass(frozen=True)
class GameState:
    board: list[list[Cell]]
    width: int
    height: int
    mineCount: int
    openedCount: int
    status: GameStatus


def _in_bounds(state: GameState, coord: Coord) -> bool:
    return 0 <= coord.x < state.width and 0 <= coord.y < state.height


def _clone_board(board: list[list[Cell]]) -> list[list[Cell]]:
    return [row[:] for row in board]


def getNeighborCoords(state: GameState, coord: Coord) -> list[Coord]:
    neighbors: list[Coord] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            next_coord = Coord(coord.x + dx, coord.y + dy)
            if _in_bounds(state, next_coord):
                neighbors.append(next_coord)
    return neighbors


def _with_adjacent_counts(board: list[list[Cell]], width: int, height: int) -> list[list[Cell]]:
    temp_state = GameState(board=board, width=width, height=height, mineCount=0, openedCount=0, status="ready")
    new_board = _clone_board(board)
    for y in range(height):
        for x in range(width):
            current = new_board[y][x]
            if current.isMine:
                continue
            count = sum(1 for n in getNeighborCoords(temp_state, Coord(x, y)) if new_board[n.y][n.x].isMine)
            new_board[y][x] = replace(current, adjacentMines=count)
    return new_board


def createGame(width: int, height: int, mineCount: int, firstClick: Coord | None = None, seed: int | None = None) -> GameState:
    if width <= 0 or height <= 0:
        raise ValueError("width와 height는 1 이상이어야 합니다.")
    max_mines = width * height - (1 if firstClick is not None else 0)
    if mineCount < 0 or mineCount > max_mines:
        raise ValueError("mineCount가 유효 범위를 벗어났습니다.")

    board = [[Cell() for _ in range(width)] for _ in range(height)]
    if mineCount == 0:
        return GameState(board=board, width=width, height=height, mineCount=mineCount, openedCount=0, status="ready")

    rnd = Random(seed)
    candidates = [Coord(x, y) for y in range(height) for x in range(width)]
    if firstClick is not None:
        if not (0 <= firstClick.x < width and 0 <= firstClick.y < height):
            raise ValueError("firstClick 좌표가 보드 범위를 벗어났습니다.")
        candidates = [coord for coord in candidates if coord != firstClick]

    mine_positions = rnd.sample(candidates, mineCount)
    for coord in mine_positions:
        board[coord.y][coord.x] = replace(board[coord.y][coord.x], isMine=True)

    board = _with_adjacent_counts(board, width, height)
    return GameState(board=board, width=width, height=height, mineCount=mineCount, openedCount=0, status="ready")


def getGameStatus(state: GameState) -> GameStatus:
    if state.status == "lost":
        return "lost"
    safe_cells = state.width * state.height - state.mineCount
    if state.openedCount >= safe_cells:
        return "won"
    if state.openedCount == 0:
        return "ready"
    return "playing"


def _cascade_open(board: list[list[Cell]], width: int, height: int, start: Coord) -> int:
    opened = 0
    stack = [start]
    temp_state = GameState(board=board, width=width, height=height, mineCount=0, openedCount=0, status="playing")

    while stack:
        coord = stack.pop()
        cell = board[coord.y][coord.x]
        if cell.isOpen or cell.isFlagged or cell.isMine:
            continue

        board[coord.y][coord.x] = replace(cell, isOpen=True)
        opened += 1

        if cell.adjacentMines == 0:
            for neighbor in getNeighborCoords(temp_state, coord):
                next_cell = board[neighbor.y][neighbor.x]
                if not next_cell.isOpen and not next_cell.isFlagged and not next_cell.isMine:
                    stack.append(neighbor)

    return opened


def openCell(state: GameState, coord: Coord) -> GameState:
    if state.status in ("won", "lost"):
        return state
    if not _in_bounds(state, coord):
        raise ValueError("좌표가 보드 범위를 벗어났습니다.")

    target = state.board[coord.y][coord.x]
    if target.isOpen or target.isFlagged:
        return state

    board = _clone_board(state.board)
    if target.isMine:
        board[coord.y][coord.x] = replace(target, isOpen=True)
        return replace(state, board=board, status="lost")

    opened_delta = _cascade_open(board, state.width, state.height, coord)
    next_state = replace(state, board=board, openedCount=state.openedCount + opened_delta)
    return replace(next_state, status=getGameStatus(next_state))


def toggleFlag(state: GameState, coord: Coord) -> GameState:
    if state.status in ("won", "lost"):
        return state
    if not _in_bounds(state, coord):
        raise ValueError("좌표가 보드 범위를 벗어났습니다.")

    cell = state.board[coord.y][coord.x]
    if cell.isOpen:
        return state

    board = _clone_board(state.board)
    board[coord.y][coord.x] = replace(cell, isFlagged=not cell.isFlagged)
    return replace(state, board=board)
