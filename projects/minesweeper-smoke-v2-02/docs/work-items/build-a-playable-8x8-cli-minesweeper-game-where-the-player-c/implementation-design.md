# Implementation Design

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| spec_type | `implementation-design` |
| source_spec | Feature Plan v1.0 (2026-05-08) |
| status | `draft` |
| last_updated | 2026-05-08 |

---

## Design Summary

Python 3.11 표준 라이브러리만으로 동작하는 8×8 CLI 지뢰찾기 게임을 단일 파일(`minesweeper.py`) 기반으로 구현한다. 게임 로직(`Board`, `Cell` 클래스)과 I/O 레이어(렌더러, 입력 파서)를 같은 파일 안에서 명확히 분리하여 역할 경계 모호로 인한 중복 구현 위험(R-3)을 구조적으로 차단한다.

핵심 설계 결정:
- **단일 파일 구조**: `minesweeper.py` 한 파일이 진입점·로직·렌더링을 모두 포함. 외부 의존성 없이 `python3 minesweeper.py`로 즉시 실행 가능.
- **safe-first-click**: 첫 좌표 입력 후 지뢰를 배치(lazy initialization). 첫 클릭 좌표를 `random.sample` 제외 집합에 추가.
- **재귀 flood-reveal**: 방문 집합(`visited`)을 재귀 호출 전 사전 마킹하여 무한루프 방지. 경계 가드 `0 <= r < 8 and 0 <= c < 8` 의무화.
- **단위 테스트 분리**: `test_minesweeper.py`에서 `Board`/`Cell` public API만 테스트. pytest 7.x 전용.

---

## Planned Modules

### `minesweeper.py`

| 클래스/함수 | 책임 역할 | 설명 |
|------------|-----------|------|
| `Cell` (dataclass) | Game Logic Dev | 셀 상태 보관 (`is_mine`, `adjacent_count`, `is_revealed`, `is_flagged`) |
| `Board` | Game Logic Dev | 그리드 초기화, 지뢰 배치, 인접 카운트, flood-reveal, 승패 판정 |
| `Board.place_mines(exclude)` | Game Logic Dev | `random.sample`로 지뢰 위치 결정. `exclude` 좌표 제외 |
| `Board.compute_adjacency()` | Game Logic Dev | 전 셀 8방향 이웃 지뢰 수 계산 |
| `Board.reveal(r, c)` | Game Logic Dev | 단일 셀 공개. `adjacent_count==0`이면 재귀 flood-reveal 호출 |
| `Board._flood(r, c, visited)` | Game Logic Dev | 재귀 연쇄 공개. 경계 가드 + visited 마킹 |
| `Board.toggle_flag(r, c)` | Game Logic Dev | 깃발 토글 |
| `Board.check_win()` | Game Logic Dev | 비지뢰 셀 전체 공개 여부 확인 → `game_state = WIN` |
| `render(board)` | Frontend Dev | ASCII 보드 출력 (열 헤더 0–7, 행 번호 0–7) |
| `parse_input(line)` | Frontend Dev | `"r c"` 또는 `"f r c"` 파싱. 잘못된 입력 → `None` 반환 |
| `main()` | Frontend Dev | 게임 루프: 입력 수신 → 로직 호출 → 렌더 → 승패 판정 → 종료 |

### `test_minesweeper.py`

| 테스트 모듈/함수 | 책임 역할 |
|-----------------|-----------|
| `test_mine_placement_excludes_first_click` | QA Engineer |
| `test_adjacent_count_accuracy` | QA Engineer |
| `test_flood_reveal_no_infinite_loop` | QA Engineer |
| `test_win_condition` | QA Engineer |
| `test_lose_condition` | QA Engineer |
| `test_flag_toggle` | QA Engineer |
| `test_input_parsing` | QA Engineer |

---

## Data Flow

```
사용자 입력 (stdin)
    │
    ▼
parse_input(line) ──[잘못된 형식]──► 경고 출력 → 재입력 요청
    │
    │ (r, c, is_flag)
    ▼
Board.toggle_flag(r, c)  ◄──[is_flag == True]
    또는
Board.reveal(r, c)       ◄──[is_flag == False]
    │
    │  [adjacent_count == 0]
    ▼
Board._flood(r, c, visited)
    │ (재귀, visited 마킹)
    │
    ▼
Board.check_win()  →  game_state = WIN / LOSE / PLAYING
    │
    ▼
render(board)  →  stdout ASCII 출력
    │
    ▼
[PLAYING] → 게임 루프 반복
[WIN/LOSE] → 최종 메시지 출력 후 sys.exit(0)
```

---

## Event Sequence / Phase Flow

### Phase 0: 초기화 (프로그램 시작)

- **진입 조건**: `python3 minesweeper.py [mine_count]` 실행
- **핵심 이벤트**:
  1. `sys.argv`에서 mine_count 파싱 (기본값 10, 범위 검증: 1 ≤ n ≤ 54)
  2. `Board(grid_size=8, mine_count=n)` 인스턴스 생성
  3. 8×8 셀 배열 초기화: 전 셀 `is_mine=False`, `is_revealed=False`, `is_flagged=False`, `adjacent_count=0`
  4. `game_state = "PLAYING"` 설정
  5. `render(board)` 호출 → 빈 보드(전 셀 `·` 표시) 출력
- **다음 Phase 전환 트리거**: 첫 번째 좌표 입력 수신

### Phase 1: 첫 클릭 및 지뢰 배치 (Safe-First-Click)

- **진입 조건**: 플레이어가 첫 번째 `r c` 또는 `f r c` 명령 입력
- **핵심 이벤트**:
  1. `parse_input(line)` 호출 → `(r, c, is_flag)` 반환
  2. `is_flag == False`이고 `board.mines_placed == False`인 경우:
     - `Board.place_mines(exclude={(r, c)})` 호출
     - `random.sample(all_cells - {(r,c)}, mine_count)`로 지뢰 위치 결정
     - `Board.compute_adjacency()` 호출 → 전 셀 `adjacent_count` 계산
     - `board.mines_placed = True` 마킹
  3. `Board.reveal(r, c)` 호출
  4. `adjacent_count == 0`이면 `Board._flood(r, c, visited=set())` 재귀 실행
  5. `Board.check_win()` 호출 (일반적으로 첫 클릭에서 WIN 아님)
  6. `render(board)` 호출
- **다음 Phase 전환 트리거**: 게임 상태가 `PLAYING` 유지 → Phase 2 진입

### Phase 2: 게임 진행 (반복 루프)

- **진입 조건**: `game_state == "PLAYING"` + 지뢰 배치 완료
- **핵심 이벤트** (매 턴 반복):
  1. `parse_input(line)` → 잘못된 형식이면 경고 후 재입력
  2. 이미 공개된 셀 reveal 시도 → 무시 후 재입력
  3. `Board.toggle_flag(r, c)`: 미공개 셀 깃발 토글 → `render(board)` 갱신
  4. `Board.reveal(r, c)`:
     - `is_mine == True` → `game_state = "LOSE"` → Phase 3 진입
     - `adjacent_count > 0` → 단일 셀 공개
     - `adjacent_count == 0` → `_flood` 재귀 연쇄 공개
  5. `Board.check_win()`: 비지뢰 셀 전체 공개 여부 확인
     - 충족 → `game_state = "WIN"` → Phase 4 진입
  6. `render(board)` 호출
- **다음 Phase 전환 트리거**: `game_state == "LOSE"` 또는 `game_state == "WIN"`

### Phase 3: 게임 오버 (LOSE)

- **진입 조건**: `game_state == "LOSE"` (지뢰 셀 공개)
- **핵심 이벤트**:
  1. 모든 지뢰 위치 공개 (`is_revealed = True` 강제 설정)
  2. `render(board)` 호출 → 지뢰 위치 `*` 표시
  3. `"💥 게임 오버! 지뢰를 밟았습니다."` 메시지 출력
  4. `sys.exit(0)` 호출
- **다음 Phase 전환 트리거**: 없음 (종료)

### Phase 4: 승리 (WIN)

- **진입 조건**: `game_state == "WIN"` (비지뢰 셀 전체 공개)
- **핵심 이벤트**:
  1. `render(board)` 호출 → 완성된 보드 출력
  2. `"🎉 축하합니다! 모든 지뢰를 피했습니다."` 메시지 출력
  3. 경과 시간(선택) 출력
  4. `sys.exit(0)` 호출
- **다음 Phase 전환 트리거**: 없음 (종료)

---

## Interface Impact

| 인터페이스 | 변경 내용 | 영향 대상 |
|-----------|-----------|-----------|
| `Board.__init__(grid_size, mine_count)` | 신규 생성 | `main()`, 테스트 |
| `Board.reveal(r, c) -> str` | 신규 생성. 반환값: `"ok"`, `"mine"`, `"already_revealed"` | `main()`, 테스트 |
| `Board.toggle_flag(r, c) -> bool` | 신규 생성. 반환값: 깃발 설정 여부 | `main()`, 테스트 |
| `Board.check_win() -> bool` | 신규 생성 | `main()`, 테스트 |
| `render(board) -> None` | 신규 생성. stdout 직접 출력 | `main()` |
| `parse_input(line: str) -> tuple \| None` | 신규 생성. `(r, c, is_flag)` 또는 `None` | `main()`, 테스트 |

외부 시스템 영향 없음 — stdlib 전용, 네트워크·파일시스템 접근 없음.

---

## State And Data Model

### Cell (dataclass)

```python
@dataclass
class Cell:
    row: int
    col: int
    is_mine: bool = False
    adjacent_count: int = 0
    is_revealed: bool = False
    is_flagged: bool = False
```

### Board

```python
class Board:
    grid_size: int        # 고정값 8
    mine_count: int       # 기본값 10
    cells: list[list[Cell]]   # 8×8 행렬
    mines_placed: bool    # 지뢰 배치 완료 여부 (lazy init)
    game_state: str       # "PLAYING" | "WIN" | "LOSE"
    _mine_positions: set[tuple[int, int]]  # 내부 지뢰 좌표 집합
```

### 상태 전이 다이어그램

```
[초기화] PLAYING (mines_placed=False)
    │
    │ 첫 reveal(r,c) 호출
    ▼
PLAYING (mines_placed=True)
    │                │
    │ 지뢰 셀 reveal  │ 비지뢰 전체 공개
    ▼                ▼
  LOSE             WIN
```

### ASCII 렌더링 기호 규칙

| 셀 상태 | 출력 기호 |
|---------|----------|
| 미공개 | `·` |
| 깃발 표시 | `F` |
| 공개 + adjacent_count > 0 | 숫자 (`1`–`8`) |
| 공개 + adjacent_count == 0 | ` ` (공백) |
| 공개 + 지뢰 (LOSE 시) | `*` |

---

## Compatibility Considerations

- Python 3.11 이상 필요 (`dataclass` 기본 지원, `match-case` 선택적 사용 가능)
- Python 3.9 이하에서는 `list[list[Cell]]` 타입 힌트가 `from __future__ import annotations` 없이 런타임 오류 발생 → `from __future__ import annotations` 상단에 추가하여 3.9+ 호환 확보 (단, 목표 런타임은 3.11)
- pytest 7.x: 테스트 전용, 게임 실행 시 불필요. `minesweeper.py`가 pytest를 import하지 않음을 보장
- 터미널 유니코드 지원: `💥`, `🎉` 이모지는 일부 터미널에서 렌더링 문제 발생 가능 → ASCII 대체 문자열 병기: `"게임 오버!"`, `"승리!"` 우선, 이모지는 부가 표시

---

## Migration Requirement

신규 구현이므로 마이그레이션 요구사항 없음. 기존 코드베이스에 `minesweeper.py`/`test_minesweeper.py`가 존재하지 않음을 전제한다.

---

## Risks

| ID | 위험 | 영향도 | 대응 설계 |
|----|------|--------|-----------|
| R-1 | 재귀 flood-reveal 경계 초과 인덱스 오류 | 높음 | `_flood` 진입 첫 줄에 `if not (0 <= r < self.grid_size and 0 <= c < self.grid_size): return` 가드 의무화. `visited` 집합으로 재방문 차단 |
| R-2 | 지뢰 배치 시 첫 클릭 좌표 충돌 | 중간 | `place_mines(exclude)` 파라미터로 첫 클릭 좌표를 `random.sample` 대상 집합에서 제거 |
| R-3 | game_logic/cli_io 역할 경계 모호, 중복 구현 | 중간 | `Board` 클래스가 로직 전담, `render()`/`parse_input()`가 I/O 전담. 두 레이어 간 직접 stdout 호출은 `render()` 단일 경로로만 허용 |
| R-4 | `random.sample` 편향 | 낮음 | Python stdlib `random.sample`은 균등 분포 보장. 추가 조치 불필요 |
| R-5 | 8×8 = 64셀에서 mine_count > 63 시 `random.sample` 오류 | 낮음 | 진입점에서 `1 ≤ mine_count ≤ 54` (safe-first-click으로 1셀 제외 고려) 범위 검증 후 오류 메시지 출력 |

---

## Alternatives Considered

### A. 다중 파일 분리 (`board.py` + `renderer.py` + `main.py`)

- **장점**: 역할 경계가 파일 단위로 명확해짐
- **단점**: "stdlib 전용 단일 명령 실행" 요건(`python3 minesweeper.py`)과 충돌. 모듈 임포트 경로 관리 복잡도 증가. AF 파이프라인 베이스라인 케이스로서 단순성이 우선
- **기각 이유**: 단일 파일 + 클래스 분리로 동일한 역할 경계 달성 가능

### B. `curses` 기반 인터랙티브 UI

- **장점**: 실시간 커서 이동, 키보드 입력 지원 등 UX 향상
- **단점**: `curses`는 Windows에서 기본 미지원(별도 설치 필요). 구현 복잡도 증가. AF 벤치마크 목적에 과설계
- **기각 이유**: stdlib 전용 + 단순 CLI 요건에 부합하지 않음

### C. 반복 공개에 재귀 대신 BFS(큐) 사용

- **장점**: 스택 오버플로 위험 완전 제거
- **단점**: 8×8 = 최대 64개 셀 → 최대 재귀 깊이 64. Python 기본 recursion limit(1000) 대비 여유 충분
- **기각 이유**: 재귀 방식이 코드 단순성 우선 원칙에 부합. 스택 오버플로 위험 없음 (최대 깊이 64)

---

## Design Evidence

- **safe-first-click 설계 근거**: Feature Plan §위험 요소 R-2 — "배치 루프에서 첫 클릭 좌표를 제외 후 샘플링"
- **단일 파일 구조 선택 근거**: Brief §constraints — "Must run with Python 3.11 stdlib only", "Game must be completable in a single terminal session"
- **역할 분리 기준**: `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑 — Rule Engine → Game Logic Dev, UI/입력 → Frontend Dev, 테스트 → QA Engineer
- **재귀 상한 안전성**: 8×8 = 64셀, Python 기본 recursion limit 1000. 최악 케이스(전 셀 연쇄 공개)도 64회 이내 종료
- **`random.sample` 선택**: Feature Plan §가정 R-4 — "표준 `random.sample` 사용 — 균등 분포 보장됨"

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md` — 실행 명령, 타이밍 JSONL 경로
- `docs/codex/2026-05-08-af-productization-application-guide.md` — 역할 매핑 기준
- Feature Plan v1.0 (2026-05-08) — 목표, 범위, 위험 요소
- `runtime/timing/minesweeper-baseline_baseline.jsonl` — AF 파이프라인 예상 출력 경로

---

## Test Strategy

### 테스트 파일: `test_minesweeper.py`

**도구**: pytest 7.x

#### 필수 테스트 케이스

| 테스트 ID | 대상 | 검증 내용 | 방법 |
|-----------|------|-----------|------|
| T-1 | `Board.place_mines` | 첫 클릭 좌표에 지뢰 없음 (safe-first-click) | `exclude=(r,c)` 후 `cells[r][c].is_mine == False` 단언 |
| T-2 | `Board.compute_adjacency` | 전 셀 `adjacent_count` 정확성 | 수동 배치 후 특정 셀 adjacent_count 검증 |
| T-3 | `Board._flood` | 경계 좌표에서 무한루프 없이 종료 | `(0,0)` 및 `(7,7)` 코너 셀에서 `reveal()` 호출 후 완료 확인 |
| T-4 | `Board.check_win` | 비지뢰 전체 공개 시 WIN 전환 | 수동으로 비지뢰 셀 전부 `is_revealed=True` 설정 후 `check_win() == True` |
| T-5 | `Board.reveal` | 지뢰 셀 공개 시 LOSE 전환 | `cells[r][c].is_mine=True` 후 `reveal(r,c)` → `game_state == "LOSE"` |
| T-6 | `Board.toggle_flag` | 깃발 토글 정확성 | 1회 → `is_flagged=True`, 2회 → `is_flagged=False` |
| T-7 | `parse_input` | 유효/무효 입력 파싱 | `"3 4"` → `(3,4,False)`, `"f 2 5"` → `(2,5,True)`, `"abc"` → `None` |
| T-8 | `Board.reveal` | 이미 공개된 셀 재reveal 무시 | `reveal(r,c)` 2회 호출 → 두 번째 호출 `"already_revealed"` 반환 |

#### e2e 검증 명령

```bash
python3 -c "
import minesweeper
b = minesweeper.Board(8, 10)
b.place_mines(exclude={(3,3)})
b.compute_adjacency()
result = b.reveal(3, 3)
assert result in ('ok', 'mine'), f'예상치 못한 반환값: {result}'
print('e2e 기본 동작 검증 통과')
"
```

#### 테스트 실행 명령

```bash
pytest test_minesweeper.py -v
```

#### 커버리지 기준

- 핵심 게임 로직 경로(지뢰 배치, 인접 계산, flood-reveal, 승패 판정) 100% 라인 커버리지 목표
- `render()` 및 `parse_input()` 단위 테스트 포함
- mock 전용 테스트 금지 — 전 테스트 케이스가 실제 `Board` 인스턴스 사용