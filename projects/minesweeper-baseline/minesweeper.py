"""8×8 CLI 지뢰찾기 게임."""
from __future__ import annotations

import argparse
import enum
import random
import sys
from dataclasses import dataclass


class GameState(enum.Enum):
    PLAYING = "playing"
    WIN = "win"
    LOSE = "lose"


@dataclass
class Cell:
    is_mine: bool = False
    adjacent_count: int = 0
    revealed: bool = False
    flagged: bool = False


class Board:
    SIZE: int = 8

    def __init__(self, mine_count: int = 10, seed: int | None = None) -> None:
        self.size = self.SIZE
        self.mine_count = mine_count
        self.seed = seed
        self.state = GameState.PLAYING
        self.first_reveal_done = False
        self.cells: list[list[Cell]] = [
            [Cell() for _ in range(self.SIZE)]
            for _ in range(self.SIZE)
        ]

    def place_mines(self, safe_row: int, safe_col: int) -> None:
        """첫 클릭 셀과 인접 셀을 제외하고 지뢰를 배치하고 인접 수를 계산한다."""
        if self.seed is not None:
            random.seed(self.seed)
        # 첫 클릭 셀과 8방향 인접 셀을 안전 영역으로 처리한다
        safe = {
            (safe_row + dr, safe_col + dc)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if 0 <= safe_row + dr < self.SIZE and 0 <= safe_col + dc < self.SIZE
        }
        candidates = [
            (r, c)
            for r in range(self.SIZE)
            for c in range(self.SIZE)
            if (r, c) not in safe
        ]
        chosen = random.sample(candidates, self.mine_count)
        for r, c in chosen:
            self.cells[r][c].is_mine = True
        self._calc_adjacent_counts()

    def _calc_adjacent_counts(self) -> None:
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self.cells[r][c].is_mine:
                    continue
                count = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.SIZE and 0 <= nc < self.SIZE:
                            if self.cells[nr][nc].is_mine:
                                count += 1
                self.cells[r][c].adjacent_count = count

    def reveal_cell(self, row: int, col: int) -> None:
        """셀을 공개한다. 첫 클릭이면 지뢰를 배치 후 공개한다."""
        if not self.first_reveal_done:
            self.place_mines(row, col)
            self.first_reveal_done = True
        self._reveal(row, col)
        if self.state == GameState.PLAYING:
            self._check_win()

    def _reveal(self, row: int, col: int) -> None:
        cell = self.cells[row][col]
        if cell.revealed or cell.flagged:
            return
        cell.revealed = True
        if cell.is_mine:
            self.state = GameState.LOSE
            return
        if cell.adjacent_count == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.SIZE and 0 <= nc < self.SIZE:
                        self._reveal(nr, nc)

    def toggle_flag(self, row: int, col: int) -> str | None:
        """깃발을 토글한다. 오류가 있으면 오류 메시지를, 없으면 None을 반환한다."""
        cell = self.cells[row][col]
        if cell.revealed:
            return "공개된 셀에는 깃발을 설정할 수 없습니다."
        cell.flagged = not cell.flagged
        return None

    def _check_win(self) -> None:
        for row in self.cells:
            for cell in row:
                if not cell.is_mine and not cell.revealed:
                    return
        self.state = GameState.WIN

    def check_win(self) -> bool:
        return self.state == GameState.WIN

    def check_lose(self) -> bool:
        return self.state == GameState.LOSE

    def render(self, reveal_mines: bool = False) -> str:
        """보드를 ASCII 문자열로 렌더링한다."""
        header = "   " + " ".join(str(c) for c in range(self.SIZE))
        lines = [header]
        for r, row in enumerate(self.cells):
            parts = [f"{r} "]
            for cell in row:
                if reveal_mines and cell.is_mine and not cell.flagged:
                    parts.append("*")
                elif cell.revealed:
                    if cell.is_mine:
                        parts.append("*")
                    elif cell.adjacent_count == 0:
                        parts.append(".")
                    else:
                        parts.append(str(cell.adjacent_count))
                elif cell.flagged:
                    parts.append("F")
                else:
                    parts.append("?")
            lines.append(" ".join(parts))
        return "\n".join(lines)


def create_board(size: int = 8, mine_count: int = 10) -> Board:
    """빈 8×8 지뢰찾기 보드를 생성해 반환한다."""
    if not (1 <= mine_count <= 54):
        raise ValueError(f"지뢰 수는 1~54 범위여야 합니다. 입력값: {mine_count}")
    return Board(mine_count=mine_count)


MSG_WIN   = "축하합니다! 승리했습니다."
MSG_LOSE  = "게임 오버! 지뢰를 밟았습니다."
MSG_QUIT  = "게임을 종료합니다."
SEPARATOR = "--------------------"


# ─── 모듈 수준 공개 API (테스트 및 외부 소비용) ───────────────────────

def place_mines(board: Board, first_click: tuple[int, int]) -> None:
    """first_click 좌표를 제외하고 지뢰를 배치하고 인접 수를 계산한다."""
    board.place_mines(first_click[0], first_click[1])
    board.first_reveal_done = True


def reveal_cell(board: Board, row: int, col: int) -> None:
    """셀을 공개한다. 지뢰면 LOSE, 빈 셀이면 연쇄 공개한다."""
    board._reveal(row, col)
    if board.state == GameState.PLAYING:
        board._check_win()


def toggle_flag(board: Board, row: int, col: int) -> None:
    """셀의 깃발을 토글한다. 이미 공개된 셀은 무시한다."""
    cell = board.cells[row][col]
    if not cell.revealed:
        cell.flagged = not cell.flagged


def check_game_state(board: Board) -> str:
    """현재 게임 상태를 'PLAYING'|'WIN'|'LOSE' 문자열로 반환한다."""
    return board.state.value.upper()


def check_win(board: Board) -> bool:
    """board.state == GameState.WIN 이면 True."""
    return board.state == GameState.WIN


def check_lose(board: Board) -> bool:
    """board.state == GameState.LOSE 이면 True."""
    return board.state == GameState.LOSE


def _make_header(board: Board) -> str:
    if board.state == GameState.WIN:
        return "지뢰찾기 8×8 [승리!]"
    if board.state == GameState.LOSE:
        return "지뢰찾기 8×8 [게임 오버]"
    return f"지뢰찾기 8×8 [지뢰: {board.mine_count}개]"


def render_board(board: Board, reveal_all: bool = False) -> str:
    """보드를 헤더·열 레이블·8행으로 구성된 ASCII 문자열로 렌더링한다."""
    return _make_header(board) + "\n" + board.render(reveal_mines=reveal_all)


def print_game_over(won: bool) -> None:
    """게임 종료 메시지를 출력한다."""
    if won:
        print(MSG_WIN)
    else:
        print(MSG_LOSE)


def parse_command(raw: str) -> tuple[str, int, int]:
    """
    입력 문자열을 파싱해 (cmd, row, col)을 반환한다.
    cmd: 'r' (공개) 또는 'f' (깃발).
    범위 또는 형식 오류 시 ValueError를 발생시킨다.
    """
    parts = raw.strip().split()

    if len(parts) == 2:
        try:
            r, c = int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError(f"유효하지 않은 좌표 형식: '{raw}'")
        if not (0 <= r < 8 and 0 <= c < 8):
            raise ValueError(f"좌표 범위 초과: ({r}, {c})")
        return ("r", r, c)

    if len(parts) == 3 and parts[0] == "f":
        try:
            r, c = int(parts[1]), int(parts[2])
        except ValueError:
            raise ValueError(f"유효하지 않은 좌표 형식: '{raw}'")
        if not (0 <= r < 8 and 0 <= c < 8):
            raise ValueError(f"좌표 범위 초과: ({r}, {c})")
        return ("f", r, c)

    raise ValueError(f"명령 형식 오류: '{raw}'")


# ─── CLI 진입점 ──────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="8×8 CLI 지뢰찾기")
    parser.add_argument(
        "--mines", type=int, default=10, metavar="N",
        help="지뢰 수 (기본: 10, 범위: 1~54)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, metavar="N",
        help="난수 시드 (재현용)",
    )
    return parser.parse_args(argv)


def _handle_command(board: Board, line: str) -> str | None:
    """
    입력 한 줄을 파싱해 보드에 적용한다.
    오류 메시지 문자열을 반환하거나, 정상 처리 시 None을 반환한다.
    'quit' 신호면 'QUIT'를 반환한다.
    """
    stripped = line.strip()
    if stripped in ("q", "quit"):
        return "QUIT"

    parts = stripped.split()

    if len(parts) == 3 and parts[0] == "f":
        try:
            r, c = int(parts[1]), int(parts[2])
        except ValueError:
            return "입력 형식이 올바르지 않습니다. 예: f 3 4"
        if not (0 <= r < 8 and 0 <= c < 8):
            return "유효하지 않은 좌표입니다. 0~7 사이의 정수를 입력하세요."
        err = board.toggle_flag(r, c)
        return err

    if len(parts) == 2:
        try:
            r, c = int(parts[0]), int(parts[1])
        except ValueError:
            return "입력 형식이 올바르지 않습니다. 예: 3 4"
        if not (0 <= r < 8 and 0 <= c < 8):
            return "유효하지 않은 좌표입니다. 0~7 사이의 정수를 입력하세요."
        cell = board.cells[r][c]
        if cell.revealed:
            return "이미 공개된 셀입니다."
        if cell.flagged:
            return "깃발이 설정된 셀입니다. 깃발을 해제한 후 공개하세요."
        board.reveal_cell(r, c)
        return None

    return "입력 형식이 올바르지 않습니다. 예: 3 4  또는  f 3 4"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    mines = args.mines
    if not (1 <= mines <= 54):
        print("지뢰 수는 1 이상 54 이하여야 합니다.", file=sys.stderr)
        return 2

    board = Board(mine_count=mines, seed=args.seed)
    print()
    print(render_board(board))
    print()

    while board.state == GameState.PLAYING:
        try:
            line = input("명령 입력 (행 열 / f 행 열 / q): ")
        except (EOFError, KeyboardInterrupt):
            print()
            print(MSG_QUIT)
            return 0

        result = _handle_command(board, line)

        if result == "QUIT":
            print(MSG_QUIT)
            return 0

        if result is not None:
            print(result)
            continue

        if check_lose(board):
            print(SEPARATOR)
            print(render_board(board, reveal_all=True))
            print()
            print_game_over(won=False)
            return 0
        if check_win(board):
            print(SEPARATOR)
            print(render_board(board))
            print()
            print_game_over(won=True)
            return 0

        print(SEPARATOR)
        print(render_board(board))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
