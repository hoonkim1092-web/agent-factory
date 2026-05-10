# Implementation Design

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| spec_type | `cli-game` |
| source_spec | Feature Plan (2026-05-08, Lilith Bootstrap) |
| status | 초안 |
| last_updated | 2026-05-08 |

---

## Design Summary

Python 3.11 표준 라이브러리만 사용하는 8×8 CLI 지뢰찾기 게임을 단일 터미널 세션에서 완주 가능하도록 설계한다. 게임 로직(`game_logic.py`)과 CLI 진입점·렌더링(`minesweeper.py`)을 파일 단위로 분리해 역할 경계를 고정한다. 지뢰는 첫 번째 클릭 이후 배치(safe-first-click)하며, 재귀 연쇄 공개는 명시적 스택 기반 BFS로 구현해 8×8 경계 초과를 방지한다. 단위 테스트는 `tests/test_game_logic.py`에 pytest로 작성하며 핵심 검증 항목 5개를 전부 커버한다.

---

## Planned Modules

| 모듈 파일 | 역할 | 주요 책임 |
|-----------|------|-----------|
| `minesweeper.py` | Frontend Dev (진입점·렌더링) | `main()` 루프, 입력 파싱·검증, 보드 ASCII 렌더링, 게임 종료 메시지 출력 |
| `game_logic.py` | Game Logic Dev (규칙·상태) | `Board` 클래스, 지뢰 배치, adjacent_count 계산, BFS 연쇄 공개, 깃발 토글, WIN/LOSE 감지 |
| `tests/test_game_logic.py` | QA Engineer (단위 테스트) | pytest 기반 5개 핵심 시나리오 검증 |

> Backend Dev 역할(`backend_dev_module_5`)은 CLI 전용 게임이므로 별도 서버·데이터 레이어가 없다. 메모리 내 `Board` 인스턴스가 유일한 상태 저장소이며, 해당 역할의 산출물은 `game_logic.py`의 상태 관리 부분에 통합된다.

> Product Designer 역할(`designer_module_7`)의 시각 디자인 산출물은 ASCII 렌더링 규격으로 대체된다.

---

## Data Flow

```
사용자 입력 (stdin)
    │
    ▼
minesweeper.py: parse_input()
    │  좌표 유효성 검사, 명령 분기 (reveal / flag / quit)
    ▼
game_logic.py: Board.reveal(row, col)
              Board.flag(row, col)
    │  셀 상태 변경, BFS 연쇄 공개, WIN/LOSE 감지
    ▼
Board.state (GameState.PLAYING / WIN / LOSE)
    │
    ▼
minesweeper.py: render_board(board)
    │  현재 셀 상태를 ASCII 문자열로 변환
    ▼
stdout 출력
```

첫 번째 `reveal()` 호출 시에만 `Board._place_mines(exclude)` 가 실행되어 클릭 셀을 제외한 위치에 지뢰를 무작위 배치한다. 이후 `_compute_adjacent()` 로 전체 셀의 인접 지뢰 수를 계산한다.

---

## Event Sequence / Phase Flow

### Phase 0 — 초기화 (프로그램 기동)

- **진입 조건**: `python3 minesweeper.py [--mines N]` 실행
- **핵심 이벤트**:
  1. `argparse`로 `--mines` 인수 파싱 (기본값 10, 범위 1~54 검사)
  2. `Board(size=8, mine_count=N)` 인스턴스 생성 — 셀 배열 초기화, 지뢰 미배치 상태
  3. `render_board(board)` 호출 → 전체 셀이 `?`(미공개)로 출력
  4. 좌표 입력 프롬프트 표시
- **다음 Phase 전환 트리거**: 사용자가 유효한 좌표를 입력하고 Enter

---

### Phase 1 — 첫 번째 공개 (safe-first-click)

- **진입 조건**: `GameState.PLAYING` + `board.mines_placed == False`
- **핵심 이벤트**:
  1. `parse_input()` → `(row, col)` 추출, 범위 검사 (0~7)
  2. `Board.reveal(row, col)` 내부에서 `_place_mines(exclude={(row,col)})` 실행
  3. `_compute_adjacent()` — 전체 64셀의 인접 지뢰 수 갱신
  4. `_bfs_reveal(row, col)` — 빈 셀이면 연쇄 공개 시작
  5. WIN 조건 즉시 점검 (`revealed_count == size² - mine_count`)
  6. `render_board()` 호출
- **다음 Phase 전환 트리거**: 게임이 `PLAYING` 상태 유지 → Phase 2, WIN → Phase 4

---

### Phase 2 — 반복 플레이 (정상 게임 루프)

- **진입 조건**: `GameState.PLAYING` + `board.mines_placed == True`
- **핵심 이벤트**:
  1. `parse_input()` — 명령 분기
     - `<row> <col>`: `Board.reveal(row, col)` → 이미 공개·깃발 셀 무시
     - `f <row> <col>`: `Board.flag(row, col)` → 깃발 토글 (미공개 셀만 허용)
     - `q`: 게임 즉시 종료
  2. 지뢰 셀 공개 시: `GameState` → `LOSE`, 전체 지뢰 위치 노출
  3. 비지뢰 셀 공개 후 WIN 조건 충족: `GameState` → `WIN`
  4. `render_board()` 호출
- **다음 Phase 전환 트리거**: `LOSE` → Phase 3, `WIN` → Phase 4, `PLAYING` → Phase 2 반복

---

### Phase 3 — 게임 오버 (LOSE)

- **진입 조건**: `GameState.LOSE`
- **핵심 이벤트**:
  1. 전체 지뢰 위치를 `*`로 표시한 보드 렌더링
  2. "게임 오버" 메시지 및 지뢰 위치 목록 출력
  3. 프로그램 종료 (exit code 0)
- **다음 Phase 전환 트리거**: 없음 (종단 상태)

---

### Phase 4 — 승리 (WIN)

- **진입 조건**: `GameState.WIN`
- **핵심 이벤트**:
  1. 전체 보드 공개 렌더링 (깃발·지뢰 포함)
  2. "승리" 메시지 및 경과 정보 출력
  3. 프로그램 종료 (exit code 0)
- **다음 Phase 전환 트리거**: 없음 (종단 상태)

---

## Interface Impact

### `game_logic.py` 공개 API

```python
class GameState(Enum):
    PLAYING = "playing"
    WIN = "win"
    LOSE = "lose"

class Cell:
    row: int
    col: int
    is_mine: bool
    adjacent_count: int   # 0~8
    is_revealed: bool
    is_flagged: bool

class Board:
    size: int             # 고정 8
    mine_count: int       # 기본 10
    cells: list[list[Cell]]
    state: GameState
    mines_placed: bool

    def reveal(self, row: int, col: int) -> GameState: ...
    def flag(self, row: int, col: int) -> None: ...
```

### `minesweeper.py` 공개 함수

```python
def parse_input(raw: str) -> tuple[str, int, int] | None:
    # 반환: ("reveal", row, col) | ("flag", row, col) | ("quit", -1, -1) | None(재입력)

def render_board(board: Board, reveal_all: bool = False) -> str:
    # ASCII 보드 문자열 반환

def main() -> None: ...
```

### 렌더링 셀 기호 규약

| 상태 | 기호 |
|------|------|
| 미공개 | `?` |
| 깃발 | `F` |
| 공개 (빈 셀) | `.` |
| 공개 (숫자) | `1`~`8` |
| 지뢰 공개 | `*` |

---

## State And Data Model

```
Board
├── size: int = 8
├── mine_count: int = 10 (기본값)
├── mines_placed: bool = False
├── state: GameState = PLAYING
├── cells: list[list[Cell]]  # cells[row][col], row/col 0-indexed
└── _revealed_count: int = 0  # WIN 조건 판정용

Cell
├── row: int
├── col: int
├── is_mine: bool = False
├── adjacent_count: int = 0
├── is_revealed: bool = False
└── is_flagged: bool = False
```

**GameState 전이 규칙**

```
PLAYING ──(지뢰 공개)──► LOSE
PLAYING ──(비지뢰 전부 공개)──► WIN
LOSE, WIN → 전이 없음 (종단)
```

**adjacent_count 계산 대상**: 8방향 이웃 셀 (경계 클리핑 적용), 지뢰 셀은 adjacent_count 미사용.

**BFS 연쇄 공개 조건**: `adjacent_count == 0`인 셀을 공개할 때 8방향 이웃을 큐에 추가. 이미 공개된 셀·깃발 셀은 큐에 추가하지 않아 무한 루프를 방지한다.

---

## Compatibility Considerations

- **Python 버전**: 3.11 stdlib만 사용 (`random`, `sys`, `argparse`, `enum`). `dataclass` 는 3.7+이므로 사용 가능.
- **테스트 의존성**: `pytest 7.x` — 런타임 의존성 아님. `tests/` 디렉터리 분리.
- **플랫폼**: Windows/macOS/Linux 터미널 모두 지원. `os.system('cls'/'clear')` 같은 플랫폼별 화면 초기화는 사용하지 않는다 (스크롤 기반 출력 유지).
- **인코딩**: ASCII 기호만 사용해 터미널 인코딩 문제를 배제한다.

---

## Migration Requirement

신규 프로젝트이므로 마이그레이션 요구 사항 없음. 기존 포커 게임 기준 태스크와 파일 시스템 충돌 없음.

---

## Risks

| ID | 위험 | 심각도 | 완화 전략 |
|----|------|--------|-----------|
| R-1 | BFS 연쇄 공개 시 경계 초과 IndexError | 높음 | BFS 큐 진입 전 `0 <= r < 8` and `0 <= c < 8` guard 추가. pytest 경계 케이스(모서리·가장자리 셀) 별도 검증 |
| R-2 | safe-first-click 보장 실패 (첫 클릭 셀에 지뢰 배치) | 중간 | `_place_mines(exclude)` 에 `exclude` 집합 전달, `random.sample(candidates)` 에서 후보 풀 제외 |
| R-3 | game_logic/cli_io 역할 경계 모호로 중복 구현 | 중간 | `game_logic.py`는 stdout 미사용, `minesweeper.py`는 게임 규칙 로직 미포함으로 파일 단위 경계 고정 |
| R-4 | `_revealed_count` 카운터 오동작으로 WIN 조건 오감지 | 낮음 | `reveal()` 호출 시 실제 상태 변경이 일어난 셀만 카운터 증가. pytest로 WIN 전환 시점 단위 검증 |

---

## Alternatives Considered

| 대안 | 검토 결과 | 기각 이유 |
|------|-----------|-----------|
| 재귀 DFS로 연쇄 공개 구현 | 구현이 단순하나 8×8 최대 64셀 재귀 깊이 → Python 기본 재귀 한도(1000) 이내지만 스택 프레임 낭비 | 명시적 큐 기반 BFS 선택. 경계 조건 추적이 명확하고 단위 테스트 용이 |
| 단일 파일(`minesweeper.py`) 구현 | 파일 수 최소화 가능 | R-3 위험 현실화. 역할 경계 모호, QA Engineer의 단위 테스트가 CLI 루프와 결합 → 테스트 격리 불가 |
| `dataclass` 대신 `dict` 로 셀 표현 | 코드 줄 수 감소 | 타입 안정성 저하, IDE 지원 불가. `@dataclass` 사용이 stdlib 범위 내에서 더 명시적 |
| `curses` 기반 TUI | 화면 갱신이 깔끔 | stdlib이지만 Windows `curses` 지원 불안정, 환경 편차 발생. ASCII 스크롤 출력으로 대체 |

---

## Design Evidence

| 출처 | 근거 내용 |
|------|-----------|
| Feature Plan §Risks R-1 | "재귀 셀 공개 시 8×8 범위 초과 인덱스 오류 → 경계 조건 guard + pytest 커버" |
| Feature Plan §Risks R-2 | "지뢰 배치를 첫 클릭 이후로 지연, 클릭 셀 제외 집합 전달" |
| Feature Plan §Risks R-3 | "`minesweeper.py`(진입점·렌더링)와 `game_logic.py`(규칙·상태)를 파일 단위로 명확히 분리" |
| Brief `verification_focus` | "재귀 공개가 경계 조건에서 무한루프 없이 종료" → BFS 큐 방식 선택 근거 |
| Brief `tech_stack` | "Python 3.11, stdlib only (random, sys)" → argparse, enum, dataclass 포함 확인 |
| Brief `data_model` | Board/Cell 엔티티·필드 정의 → `@dataclass` 로 구현 |
| `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑 | "Rule Engine → Game Logic Dev, UI/입력 → Frontend Dev, 테스트 → QA Engineer" |

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md`
- `docs/codex/2026-05-08-af-productization-application-guide.md`
- Feature Plan: `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` (2026-05-08)

---

## Test Strategy

### 커버 대상 (pytest, `tests/test_game_logic.py`)

| 테스트 ID | 검증 항목 | 검증 방법 |
|-----------|-----------|-----------|
| T-1 | `adjacent_count` 정확성 | 고정 시드로 지뢰 배치 후 전체 64셀 인접 수 수동 계산값과 비교 |
| T-2 | BFS 연쇄 공개 경계 조건 | 모서리(0,0), 가장자리(0,4), 내부(3,3) 셀 클릭 시 IndexError 미발생 확인 |
| T-3 | safe-first-click 보장 | 100회 무작위 시드 반복, 첫 클릭 셀이 지뢰인 케이스 0건 검증 |
| T-4 | WIN 상태 전환 | 지뢰 외 모든 셀을 순서대로 reveal() 호출 후 `board.state == GameState.WIN` 확인 |
| T-5 | LOSE 상태 전환 | 지뢰 셀 좌표를 직접 reveal() 호출 후 `board.state == GameState.LOSE` 확인 |

### 비mock 실행 경로 보장

- 모든 테스트는 실제 `Board` 인스턴스를 생성하고 실제 메서드를 호출한다.
- stub/mock 전용 테스트는 작성하지 않는다 (Episode Hints 준수).
- T-3은 `random.seed(i)` 루프로 실제 `_place_mines` 실행 경로를 통과한다.

### e2e 검증 명령

```bash
python3 minesweeper.py --mines 10    # 수동 플레이 기동 확인
pytest tests/ -v                     # 전체 단위 테스트
```