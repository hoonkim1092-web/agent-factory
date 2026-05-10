# Handoff 메모: 지뢰 배치 및 셀 공개 게임 로직 모듈 범위/인터페이스 고정

- 작업 ID: `frontend_dev_module_2_scope_1`
- 작성일: 2026-05-08
- 대상 모듈: 8x8 CLI 지뢰찾기의 지뢰 배치 및 셀 공개 로직

## 1) 현재 구현 상태 파악 결과

- `games/` 디렉토리: 현재 없음
- 로직 모듈: `src/game_logic.py`에 순수 함수형 게임 로직이 이미 구현됨
  - `createGame(width, height, mineCount, firstClick=None, seed=None) -> GameState`
  - `openCell(state, coord) -> GameState`
  - `toggleFlag(state, coord) -> GameState`
  - `getGameStatus(state) -> GameStatus`
  - `getNeighborCoords(state, coord) -> list[Coord]`
- CLI 진입점: `minesweeper.py`는 `Board` 클래스 중심의 상태변경(in-place) 방식으로 별도 구현됨
  - `Board.place_mines`, `Board.reveal_cell`, `Board.toggle_flag` 내장
  - 모듈 레벨 API(`place_mines`, `reveal_cell`, `toggle_flag`, `check_game_state`)도 `Board`에 직접 위임
- 테스트 상태
  - `tests/test_game_logic.py`: `src/game_logic.py` 인터페이스 검증
  - `tests/test_minesweeper_unit.py`: `minesweeper.py` 인터페이스 검증

## 2) 인터페이스 갭 분석 (`src/game_logic.py` vs `minesweeper.py`)

- 데이터 모델 네이밍 불일치
  - `src/game_logic.py`: `Cell.isMine/isOpen/isFlagged/adjacentMines`, `Coord(x,y)`
  - `minesweeper.py`: `Cell.is_mine/revealed/flagged/adjacent_count`, `(row,col)` 튜플
- 상태 모델 불일치
  - `src/game_logic.py`: 문자열 상태 `"ready"|"playing"|"won"|"lost"`
  - `minesweeper.py`: Enum 기반 `PLAYING|WIN|LOSE` (ready 없음)
- 실행 모델 불일치
  - `src/game_logic.py`: 불변 상태 입력/출력(새 `GameState` 반환)
  - `minesweeper.py`: 가변 객체 직접 수정(in-place)
- 첫 클릭 안전 규칙 차이
  - `src/game_logic.py`: 기본적으로 첫 클릭 셀 1칸만 제외
  - `minesweeper.py`: 첫 클릭 + 8방향 인접 9칸 안전 영역
- 결과적으로 동일 도메인 로직이 이중화되어 유지보수 리스크 존재

## 3) 모듈 범위 고정 (Module 2)

- 포함
  - 지뢰 배치
  - 인접 지뢰 수 계산
  - 셀 공개(지뢰 공개, 빈 셀 연쇄 공개 포함)
  - 승패 상태 갱신에 필요한 상태 반환
- 제외
  - 입력 파싱 (`parse_command`)
  - CLI 루프/출력 (`main`, 렌더링 문자열 포맷)

## 4) API 함수 목록/시그니처 확정 (Module 2 계약)

다음 시그니처를 `minesweeper.py`의 모듈 레벨 공개 API 기준으로 고정한다.

```python
def place_mines(board: Board, first_click: tuple[int, int]) -> None

def reveal_cell(board: Board, row: int, col: int) -> None

def toggle_flag(board: Board, row: int, col: int) -> None

def check_game_state(board: Board) -> str  # "PLAYING" | "WIN" | "LOSE"
```

보조 규약:
- 좌표 체계: `(row, col)` (0~7)
- 첫 공개 전 `place_mines`는 `first_click`을 안전 셀로 보장
- `reveal_cell`은 깃발 셀 공개를 무시하고, 0 인접 셀은 연쇄 공개
- `toggle_flag`는 공개된 셀에서 no-op

## 5) 빌드 단계 구현 순서 고정

1. `place_mines` 고정
- 안전 영역 정책 확정(현재 테스트/CLI와 정합: 첫 클릭 + 인접 8칸)
- 지뢰 배치 수 정확성 보장

2. 인접 지뢰 수 계산 내부 루틴 고정
- `place_mines` 직후 전체 셀 `adjacent_count` 계산

3. `reveal_cell` 고정
- 첫 공개 시 지뢰 미배치 상태라면 지뢰 배치 트리거
- 지뢰 공개 시 LOSE
- 빈 셀 연쇄 공개(DFS/BFS 중 한 방식 일관 적용)

4. `toggle_flag` 고정
- 공개 셀 no-op, 비공개 셀 토글

5. `check_game_state` 고정
- 모든 비지뢰 셀 공개 시 WIN, 아니면 PLAYING/LOSE 유지

6. 통합 확인
- `tests/test_minesweeper_unit.py`의 API 기대값과 시그니처/동작 정합 점검

## 6) 의존성과 산출물

- 의존성
  - 데이터 모델: `minesweeper.py`의 `Board`, `Cell`, `GameState`
  - 테스트 계약: `tests/test_minesweeper_unit.py`
- 산출물
  - 본 handoff 문서
  - `docs/architecture.md` 반영 항목
  - `docs/change_history.md` 변경 이력 추가

[game_logic_dev] 작업 결과를 파일로 남깁니다.
