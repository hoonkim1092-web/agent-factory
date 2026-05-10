# Implementation Design

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| spec_type | cli-game |
| source_spec | Feature Plan (2026-05-08) |
| status | draft |
| last_updated | 2026-05-09 |

---

## Design Summary

Python 3.11 표준 라이브러리(`random`, `sys`, `os`)만으로 동작하는 단일 파일 구조의 8×8 CLI 지뢰찾기 게임을 구현한다. 게임 상태는 `Board` 객체가 소유하고, I/O는 `minesweeper.py`의 메인 루프에서만 담당한다. 역할 경계를 함수 계층으로 분리하여 게임 로직(`board.py` 또는 동일 파일 내 모듈 영역)과 CLI 루프(`main()`)가 서로 직접 상태를 변경하지 않도록 한다.

핵심 설계 결정:
- **단일 파일 배포** — `minesweeper.py` 하나로 실행 가능. 표준 라이브러리 전용 제약에 자연스럽게 부합.
- **safe-first-click** — 지뢰 배치는 첫 번째 `reveal` 호출 시점에 수행. 초기화 시점에는 배치하지 않는다.
- **재귀 flood-reveal** — 인접 지뢰 수가 0인 셀 공개 시 8방향 인접 셀을 재귀 탐색. 8×8 최대 64셀이므로 Python 기본 재귀 한도(1000) 내에서 안전.
- **mine_count CLI 인자** — `python3 minesweeper.py [mine_count]` 형태로 수신. 기본값 10, 유효 범위 1–63.

---

## Planned Modules

| 모듈/파일 | 담당 역할 | 책임 범위 |
|-----------|-----------|-----------|
| `minesweeper.py` | Frontend Dev + Game Logic Dev | 진입점(`main`), 입력 루프, 보드 렌더링, 게임 로직 함수 전체 포함 |
| `test_minesweeper.py` | QA Engineer | pytest 7.x 기반 단위 테스트 스위트 |

> **단일 파일 선택 근거**: 외부 의존성 0, stdlib 전용 제약, 벤치마크용 경량 케이스. 다수 파일 분리는 import 경로 복잡성만 추가한다.

### 내부 계층 (동일 파일 내 논리 분리)

```
minesweeper.py
├── Board (class)          ← game_logic_dev 영역
│   ├── __init__
│   ├── place_mines(first_row, first_col)
│   ├── compute_adjacent()
│   ├── reveal(row, col) → GameState
│   ├── flag(row, col)
│   ├── check_win() → bool
│   └── render() → str
├── GameState (enum/const) ← game_logic_dev 영역
│   ├── PLAYING
│   ├── WIN
│   └── LOSE
└── main()                 ← frontend_dev 영역
    ├── parse_args()
    ├── input loop
    └── print / sys.exit
```

---

## Data Flow

```
사용자 입력 (stdin)
    │
    ▼
main() — 입력 파싱 및 유효성 검사
    │ (row, col) 또는 (flag, row, col)
    ▼
Board.reveal(row, col) 또는 Board.flag(row, col)
    │
    ├─[첫 reveal 호출]─▶ Board.place_mines(first_row, first_col)
    │                        └─▶ Board.compute_adjacent()
    │
    ├─[reveal]─▶ _flood_reveal(row, col) [재귀]
    │                 └─▶ 셀 상태 갱신 (revealed=True)
    │
    ├─[check_win]─▶ GameState.WIN 또는 PLAYING
    │
    └─[지뢰 셀 공개]─▶ GameState.LOSE
         │
         ▼
Board.render() → 문자열
    │
    ▼
stdout 출력
```

---

## Event Sequence / Phase Flow

### Phase 0: 초기화 (Initialization)

- **진입 조건**: `python3 minesweeper.py [mine_count]` 실행
- **핵심 이벤트**:
  1. `parse_args()` — `sys.argv`에서 `mine_count` 파싱. 범위(1–63) 검증. 실패 시 오류 메시지 출력 후 종료.
  2. `Board.__init__(size=8, mine_count)` — 8×8 셀 배열 생성. 모든 셀을 미공개·비지뢰·카운트 0으로 초기화. **지뢰 미배치 상태 유지**.
  3. `Board.render()` 호출 — 빈 보드 출력.
  4. 첫 번째 좌표 입력 프롬프트 표시.
- **다음 Phase 전환 트리거**: 사용자가 유효한 좌표를 입력.

---

### Phase 1: 첫 클릭 처리 및 지뢰 배치 (Mine Placement)

- **진입 조건**: 게임 상태 `PLAYING`, `mines_placed == False`, 유효한 reveal 명령 수신.
- **핵심 이벤트**:
  1. `Board.place_mines(first_row, first_col)` — `random.sample`으로 전체 64셀에서 `(first_row, first_col)`을 제외한 63개 위치 중 `mine_count`개 선택. 선택 셀에 `is_mine=True` 표시.
  2. `Board.compute_adjacent()` — 전체 셀 순회. 각 비지뢰 셀에 대해 8방향 인접 셀 중 지뢰 수를 세어 `adjacent_count` 저장.
  3. `mines_placed = True` 플래그 설정.
  4. 첫 번째 셀 reveal 진행 (Phase 2로 연속 진입).
- **다음 Phase 전환 트리거**: 지뢰 배치 완료 후 즉시 Phase 2 실행.

---

### Phase 2: 셀 공개 (Cell Reveal)

- **진입 조건**: 게임 상태 `PLAYING`, `mines_placed == True`, reveal 명령 수신.
- **핵심 이벤트**:
  1. 좌표 범위 검사 (`0 ≤ row < 8`, `0 ≤ col < 8`). 실패 시 오류 메시지 출력 후 재입력 대기.
  2. 이미 공개된 셀 또는 깃발 셀이면 무시.
  3. 대상 셀이 지뢰인 경우: `is_revealed=True`, `game_state=LOSE` → Phase 4 진입.
  4. 대상 셀이 비지뢰인 경우:
     - `_flood_reveal(row, col)` 재귀 실행.
     - 인접 수 > 0: 해당 셀만 공개.
     - 인접 수 == 0: 해당 셀 공개 후 8방향 미공개 비지뢰 셀 재귀 탐색.
  5. `Board.check_win()` — 공개된 비지뢰 셀 수 == 64 - mine_count이면 `game_state=WIN` → Phase 3 진입.
  6. `Board.render()` 호출 후 출력. 다음 입력 프롬프트 표시.
- **다음 Phase 전환 트리거**: WIN 조건 충족 → Phase 3, LOSE 조건 충족 → Phase 4, 아니면 Phase 2 반복.

---

### Phase 3: 승리 처리 (Win Termination)

- **진입 조건**: `game_state == WIN`.
- **핵심 이벤트**:
  1. 최종 보드 렌더링 (모든 비지뢰 셀 공개 상태).
  2. 승리 메시지 출력: `"축하합니다! 지뢰를 모두 피했습니다."`.
  3. `sys.exit(0)`.
- **다음 Phase 전환 트리거**: 프로세스 종료.

---

### Phase 4: 패배 처리 (Lose Termination)

- **진입 조건**: `game_state == LOSE`.
- **핵심 이벤트**:
  1. 모든 지뢰 셀의 위치를 공개 상태로 전환하여 렌더링.
  2. 패배 메시지 출력: `"지뢰를 밟았습니다. 게임 오버."`.
  3. `sys.exit(0)`.
- **다음 Phase 전환 트리거**: 프로세스 종료.

---

### Phase 5: 깃발 토글 (Flag Toggle) — Phase 2 병렬 처리

- **진입 조건**: 게임 상태 `PLAYING`, `f <row> <col>` 명령 수신.
- **핵심 이벤트**:
  1. 좌표 범위 검사. 실패 시 오류 메시지 출력 후 재입력 대기.
  2. 이미 공개된 셀이면 무시.
  3. `is_flagged` 토글: `True → False`, `False → True`.
  4. `Board.render()` 호출 후 출력.
- **다음 Phase 전환 트리거**: Phase 2로 복귀.

---

## Interface Impact

### CLI 입력 인터페이스

| 명령 형식 | 동작 |
|-----------|------|
| `<row> <col>` (예: `3 4`) | 셀 공개 |
| `f <row> <col>` (예: `f 2 5`) | 깃발 토글 |
| `q` | 게임 종료 |

- row, col은 0-indexed (0~7).
- 잘못된 입력은 오류 메시지 출력 후 재입력 대기. 예외 발생 없이 루프 계속.

### Board.render() 출력 형식

```
   0 1 2 3 4 5 6 7
0  . . . . . . . .
1  . 1 1 1 . . . .
2  . 1 * 1 . . . .
3  . 1 1 1 . . . .
4  . . . . . . . .
...
```

| 기호 | 의미 |
|------|------|
| `.` | 미공개 셀 |
| ` ` (공백) | 공개된 빈 셀 (adjacent_count = 0) |
| `1`~`8` | 공개된 셀의 인접 지뢰 수 |
| `F` | 깃발 표시 셀 |
| `*` | 지뢰 (LOSE 시 공개) |

---

## State And Data Model

### Board

```python
class Board:
    size: int = 8
    mine_count: int          # 1 ≤ mine_count ≤ 63
    cells: list[list[Cell]]  # [row][col]
    mines_placed: bool = False
    game_state: str          # 'PLAYING' | 'WIN' | 'LOSE'
```

### Cell

```python
class Cell:  # 또는 dataclass
    row: int
    col: int
    is_mine: bool = False
    adjacent_count: int = 0
    is_revealed: bool = False
    is_flagged: bool = False
```

### GameState 상수

```python
PLAYING = 'PLAYING'
WIN     = 'WIN'
LOSE    = 'LOSE'
```

### 상태 전이 요약

```
PLAYING ──[reveal 지뢰]──▶ LOSE
PLAYING ──[비지뢰 전체 공개]──▶ WIN
PLAYING ──[flag/reveal 비지뢰]──▶ PLAYING (자기 전이)
WIN, LOSE ──▶ 터미널 상태 (입력 불가)
```

---

## Compatibility Considerations

- **Python 버전**: 3.11 이상. `match` 문 미사용으로 3.9 이상에서도 실행 가능하나 공식 지원 범위는 3.11.
- **pytest 버전**: 7.x. 게임 실행 코드에 pytest 의존성 없음. `test_minesweeper.py`에서만 import.
- **플랫폼**: `os.system('clear')` / `os.system('cls')` 없이 순수 print만 사용. macOS·Linux·Windows 모두 동작.
- **인코딩**: 모든 문자열 ASCII 범위 내. 한국어 메시지는 UTF-8 터미널 환경 가정.

---

## Migration Requirement

신규 구현이므로 마이그레이션 없음. 기존 포커 게임 기준선과 파일명 충돌 없음.

---

## Risks

| # | 리스크 | 영향도 | 완화 방안 |
|---|--------|--------|-----------|
| R1 | 재귀 flood-reveal에서 방문 체크 누락 → 무한 루프 | 높음 | `_flood_reveal` 진입 즉시 `is_revealed=True` 표시. 재진입 차단. |
| R2 | 첫 클릭 셀 지뢰 충돌 | 높음 | `place_mines(first_row, first_col)` 호출 시 해당 좌표를 `random.sample` 제외 목록에 포함. |
| R3 | mine_count ≥ 64 입력 시 `random.sample` 오류 | 중간 | Phase 0에서 1~63 범위 검증 후 오류 메시지 출력. |
| R4 | game_logic_dev와 frontend_dev 경계 모호로 중복 구현 | 낮음 | `main()`은 I/O 전용. 상태 변경은 반드시 `Board` 메서드 호출로만 수행. |
| R5 | 깃발 표시 셀을 실수로 공개 | 낮음 | `reveal()`에서 `is_flagged=True` 셀은 무시 처리. |

---

## Alternatives Considered

| 대안 | 기각 이유 |
|------|-----------|
| 다중 파일 구조 (`board.py` + `minesweeper.py`) | 벤치마크 경량 케이스에 import 복잡성 추가. 단일 파일이 stdlib 전용 제약에 자연스럽게 부합. |
| 첫 클릭 이전 지뢰 배치 후 충돌 시 재배치 | 반복 재배치 루프는 worst-case 무한. safe-first-click은 단순히 첫 클릭 후 배치하는 것이 결정론적. |
| dataclass 사용 for Cell | Python 3.7+ 지원이지만 stdlib임. 단순 클래스와 기능 차이 없고 가독성 이점만 있어 선택 가능. 최종 구현자 재량. |
| `curses` 기반 TUI | 표준 라이브러리지만 Windows 지원 불안정. 단순 print 방식이 플랫폼 중립적. |
| 인터랙티브 mine_count 프롬프트 | CLI 인자로만 수신하는 방식이 자동화·파이프라인 계측에 적합. 승인된 설계 결정. |

---

## Design Evidence

| 설계 결정 | 근거 출처 |
|-----------|-----------|
| Python 3.11 stdlib 전용 | Feature Plan §Constraints |
| 8×8 고정 크기 | Feature Plan §Constraints |
| mine_count CLI 인자 (기본값 10) | Feature Plan §Goals #4 |
| safe-first-click 구현 — 첫 reveal 시점에 지뢰 배치 | Feature Plan §Risks R2 |
| 단위 테스트는 pytest 7.x | Feature Plan §Tech Stack |
| 역할 매핑: Rule Engine → Game Logic Dev | `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑 |
| 단일 파일 구조 | Feature Plan §Non-Goals (GUI 및 복잡 구조 제외) + 경량 벤치마크 목적 |

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md` — 실행 명령 및 타이밍 산출물 명세
- `docs/codex/2026-05-08-af-productization-application-guide.md` — AF 역할 매핑 가이드
- Feature Plan (2026-05-08) — 목표, 범위, 리스크 정의 원본

---

## Test Strategy

### 테스트 파일

`test_minesweeper.py` — pytest 7.x, 표준 라이브러리 외 의존성 없음.

### 필수 테스트 케이스

| 테스트 ID | 검증 항목 | 방법 |
|-----------|-----------|------|
| T1 | `place_mines` 후 지뢰 수 == mine_count | `sum(c.is_mine for row in b.cells for c in row)` |
| T2 | 첫 클릭 셀에 지뢰 미배치 (safe-first-click) | `board.cells[fr][fc].is_mine == False` |
| T3 | `compute_adjacent` 정확성 — 전 셀 | 수동 배치 후 모든 셀 adjacent_count 검증 |
| T4 | flood-reveal — 경계 셀 (코너, 엣지) | `reveal(0,0)`, `reveal(7,7)` 후 공개 셀 수 확인 |
| T5 | flood-reveal 무한루프 없음 | 지뢰 없는 보드에서 `reveal(0,0)` → 전 64셀 공개 |
| T6 | 지뢰 셀 reveal → LOSE | 수동 지뢰 배치 후 해당 셀 reveal, `game_state == 'LOSE'` |
| T7 | 비지뢰 전체 공개 → WIN | 지뢰 외 63셀 reveal, `game_state == 'WIN'` |
| T8 | 깃발 셀 reveal 무시 | flag 후 reveal → `is_revealed == False` |
| T9 | mine_count 범위 외 입력 → 오류 처리 | `parse_args` 0, 64, -1 입력 시 SystemExit |
| T10 | `render()` 출력 형식 — 미공개·공개·깃발·지뢰 기호 | 고정 보드 상태 기준 문자열 포함 확인 |

### 비mock 실행 경로 보장

- T5: 실제 `Board` 인스턴스 생성 + 실제 `reveal()` 호출. stub 없음.
- T6, T7: 실제 게임 상태 전이 경로 실행 확인.