# Implementation Tasks

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| source_design | Implementation Design (2026-05-08, Lilith Bootstrap) |
| status | 완료 |
| last_updated | 2026-05-08 |

---

## Preconditions

- Python 3.11 이상 설치 확인 (`python3 --version`)
- pytest 7.x 설치 확인 (`pytest --version`) — 런타임 의존성 아님, 테스트 전용
- 작업 디렉터리: `/Users/hoon/workTree/agent-factory/projects/minesweeper-smoke-v2-01`
- 외부 네트워크 불필요 — stdlib만 사용
- 기존 충돌 파일 없음 (신규 프로젝트, 포커 게임 베이스라인과 경로 분리)

---

## Task Evidence

| 태스크 ID | 근거 출처 |
|-----------|-----------|
| T-001 ~ T-005 | Implementation Design §Planned Modules, §State And Data Model |
| T-006 ~ T-010 | Implementation Design §Data Flow, §Interface Impact `game_logic.py` 공개 API |
| T-011 ~ T-014 | Implementation Design §Interface Impact `minesweeper.py` 공개 함수, Brief `user_flows` |
| T-015 | Implementation Design §Test Strategy, Brief `verification_focus` |
| T-016 ~ T-017 | Implementation Design §Event Sequence Phase 0~2, §Compatibility Considerations |
| T-018 ~ T-021 | Implementation Design §Risks R-1~R-4, §Test Strategy e2e 검증 명령 |

---

## Task List

---

### Phase: Scope

- [ ] **game_logic.py 모듈 범위 및 인터페이스 정의**
  - task_id: T-001
  - owner_role: game_logic_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `game_logic.py`가 노출할 공개 API(`Board`, `Cell`, `GameState`) 목록이 문서화된다.
    - `minesweeper.py`에서 import할 심볼 목록이 확정된다.
    - stdout 미사용 원칙이 범위 메모에 명시된다.
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: Implementation Design §Planned Modules "game_logic.py — Game Logic Dev" 행 참조. stdout 사용 금지 경계를 주석 없이 모듈 docstring 1줄로 명시.

---

- [ ] **minesweeper.py 진입점·렌더링 범위 정의**
  - task_id: T-002
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `minesweeper.py`가 담당하는 함수 목록(`parse_input`, `render_board`, `main`)이 확정된다.
    - 게임 규칙 로직(지뢰 배치, BFS 등)을 직접 구현하지 않음이 범위에 명시된다.
    - `argparse` `--mines` 옵션 범위(기본값 10, 범위 1~54)가 확정된다.
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: Implementation Design §Interface Impact `minesweeper.py` 공개 함수 블록 참조. 렌더링 기호 규약 표를 범위 메모에 그대로 인용.

---

- [ ] **tests/test_game_logic.py 테스트 범위 정의**
  - task_id: T-003
  - owner_role: qa_engineer
  - phase: scope
  - depends_on: []
  - acceptance:
    - 검증할 5개 시나리오(T-1~T-5) 목록과 각 검증 방법이 확정된다.
    - mock/stub을 사용하지 않는 실제 `Board` 인스턴스 기반 테스트임이 명시된다.
    - `tests/` 디렉터리 분리 구조가 확정된다.
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: Implementation Design §Test Strategy "커버 대상" 표의 T-1~T-5 항목을 범위 메모로 전환.

---

- [ ] **CLI 화면 흐름 및 ASCII 렌더링 규격 정의**
  - task_id: T-004
  - owner_role: designer
  - phase: scope
  - depends_on: []
  - acceptance:
    - 5가지 셀 상태(`?`, `F`, `.`, `1~8`, `*`)에 대한 기호 규약이 확정된다.
    - Phase 0~4 화면 전환 흐름(초기화→플레이→종료)이 텍스트로 정리된다.
    - `os.system('clear')` 같은 플랫폼별 화면 초기화를 사용하지 않음이 명시된다.
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: Implementation Design §Interface Impact "렌더링 셀 기호 규약" 표 및 §Compatibility Considerations 참조.

---

- [ ] **Backend 상태 저장 범위 확인**
  - task_id: T-005
  - owner_role: backend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - CLI 전용 게임으로 별도 서버·DB 레이어가 없음이 문서화된다.
    - 메모리 내 `Board` 인스턴스가 유일한 상태 저장소임이 확정된다.
    - 상태 관리 역할이 `game_logic.py`의 `Board` 클래스에 통합됨이 명시된다.
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: Implementation Design §Planned Modules "Backend Dev 역할 통합" 주석 참조.

---

### Phase: Build

- [ ] **GameState Enum + Cell/Board dataclass 구현**
  - task_id: T-006
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - `GameState(Enum)`에 `PLAYING`, `WIN`, `LOSE` 세 값이 정의된다.
    - `Cell` dataclass에 `row`, `col`, `is_mine`, `adjacent_count`, `is_revealed`, `is_flagged` 필드가 존재한다.
    - `Board.__init__`이 `size=8`, `mine_count=N`을 받아 `cells[8][8]`를 초기화한다.
    - `mines_placed = False`, `state = GameState.PLAYING`으로 초기 상태가 설정된다.
  - artifacts: [game_logic.py]
  - estimated_complexity: S
  - implementation_hint: Implementation Design §State And Data Model 참조. `@dataclass`는 Python 3.7+ stdlib 범위이므로 사용 가능.

---

- [ ] **_place_mines(exclude) 구현**
  - task_id: T-007
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-006]
  - acceptance:
    - `exclude` 집합에 포함된 좌표에 지뢰가 배치되지 않는다 (safe-first-click 보장).
    - `random.sample(candidates, mine_count)`로 중복 없이 정확히 `mine_count`개 지뢰가 배치된다.
    - 호출 후 `mines_placed = True`로 전환된다.
    - `mine_count > 63` 케이스는 `ValueError`를 발생시킨다 (§4 기능 요구사항 대응).
  - artifacts: [game_logic.py]
  - estimated_complexity: S
  - implementation_hint: Implementation Design §Risks R-2 완화 전략 참조. `candidates = [(r,c) for r,c in all_cells if (r,c) not in exclude]`.

---

- [ ] **_compute_adjacent() 구현**
  - task_id: T-008
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-007]
  - acceptance:
    - 전체 64셀의 `adjacent_count`가 지뢰 배치 직후 한 번 계산된다.
    - 8방향 이웃에 경계 클리핑(`0 <= r < 8`, `0 <= c < 8`)이 적용된다.
    - 지뢰 셀 자신의 `adjacent_count`는 변경되지 않는다(미사용).
    - 모서리(0,0) 및 가장자리(0,4) 셀에서 IndexError가 발생하지 않는다.
  - artifacts: [game_logic.py]
  - estimated_complexity: S
  - implementation_hint: Implementation Design §State And Data Model "adjacent_count 계산 대상" 참조.

---

- [ ] **_bfs_reveal() BFS 연쇄 공개 구현**
  - task_id: T-009
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-008]
  - acceptance:
    - `adjacent_count == 0`인 셀 공개 시 8방향 이웃이 큐에 추가된다.
    - 이미 공개된 셀·깃발 셀은 큐에 추가되지 않아 무한 루프가 방지된다.
    - 재귀 대신 명시적 `collections.deque` 또는 `list` 스택 기반으로 구현된다.
    - 경계 초과(`r < 0`, `r >= 8`, `c < 0`, `c >= 8`) guard가 큐 진입 전에 적용된다.
  - artifacts: [game_logic.py]
  - estimated_complexity: M
  - implementation_hint: Implementation Design §Alternatives Considered "재귀 DFS 기각" 근거 및 §Risks R-1 완화 전략 참조.

---

- [ ] **Board.reveal() + WIN/LOSE 상태 감지 구현**
  - task_id: T-010
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-009]
  - acceptance:
    - 첫 번째 호출 시 `_place_mines(exclude={(row,col)})` → `_compute_adjacent()` 순서로 실행된다.
    - 지뢰 셀 공개 시 `state = GameState.LOSE`로 전환된다.
    - `_revealed_count == size² - mine_count` 조건 충족 시 `state = GameState.WIN`으로 전환된다.
    - 이미 공개된 셀·깃발 셀에 대한 `reveal()` 호출은 무시된다.
    - `GameState`를 반환한다.
  - artifacts: [game_logic.py]
  - estimated_complexity: M
  - implementation_hint: Implementation Design §Risks R-4 "_revealed_count 카운터 오동작" 완화 전략 참조. 실제 상태 변경이 일어난 셀만 카운터 증가.

---

- [ ] **Board.flag() 깃발 토글 구현**
  - task_id: T-011
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-006]
  - acceptance:
    - 미공개 셀에 대해 `is_flagged`를 토글한다(True ↔ False).
    - 이미 공개된 셀에 대한 `flag()` 호출은 무시된다.
    - LOSE/WIN 상태에서는 `flag()` 호출이 무시된다.
  - artifacts: [game_logic.py]
  - estimated_complexity: XS
  - implementation_hint: Implementation Design §Event Sequence Phase 2 "f <row> <col>" 분기 참조.

---

- [ ] **parse_input() 입력 파싱 구현**
  - task_id: T-012
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002]
  - acceptance:
    - `"3 4"` → `("reveal", 3, 4)` 를 반환한다.
    - `"f 2 5"` → `("flag", 2, 5)`를 반환한다.
    - `"q"` 또는 `"quit"` → `("quit", -1, -1)`을 반환한다.
    - 범위 초과(`row < 0`, `row > 7`, `col < 0`, `col > 7`) 입력은 `None`을 반환한다.
    - 비정수 입력은 `None`을 반환해 재입력을 유도한다.
  - artifacts: [minesweeper.py]
  - estimated_complexity: S
  - implementation_hint: Implementation Design §Interface Impact `parse_input` 반환 타입 참조.

---

- [ ] **render_board() ASCII 렌더링 구현**
  - task_id: T-013
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-004, T-012]
  - acceptance:
    - 미공개 셀→`?`, 깃발→`F`, 공개 빈 셀→`.`, 공개 숫자→`1~8`, 지뢰 공개→`*` 5가지 규약을 모두 구현한다.
    - `reveal_all=True`이면 지뢰 위치를 포함한 전체 보드를 출력한다.
    - 행·열 인덱스 헤더가 포함된다 (가독성, §6 출력 요구사항 대응).
    - 반환값은 `str`이며 stdout 직접 호출은 `main()`에서만 수행된다.
  - artifacts: [minesweeper.py]
  - estimated_complexity: S
  - implementation_hint: Implementation Design §Interface Impact "렌더링 셀 기호 규약" 표 참조. `render_board` 는 `str`을 반환하고 `print()`는 `main()`에서만 호출.

---

- [ ] **main() 게임 루프 구현**
  - task_id: T-014
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-013]
  - acceptance:
    - `argparse`로 `--mines N` 인수를 파싱하며 기본값 10, 범위 1~54 검사를 포함한다.
    - Phase 0(초기화) → Phase 1(첫 클릭) → Phase 2(반복) → Phase 3/4(종료) 전환이 게임 루프 내에서 동작한다.
    - `board.state == GameState.LOSE` 시 전체 지뢰 위치(`reveal_all=True`)가 출력된다.
    - `board.state == GameState.WIN` 시 승리 메시지가 출력된다.
    - `parse_input()` 반환이 `None`이면 오류 메시지와 함께 재입력을 요청한다.
  - artifacts: [minesweeper.py]
  - estimated_complexity: M
  - implementation_hint: Implementation Design §Event Sequence Phase 0~4 흐름 전체 참조.

---

- [ ] **pytest 단위 테스트 T-1~T-5 구현**
  - task_id: T-015
  - owner_role: qa_engineer
  - phase: build
  - depends_on: [T-010, T-011, T-003]
  - acceptance:
    - T-1: 고정 시드로 지뢰 배치 후 전체 64셀 `adjacent_count` 수동 계산값과 일치한다.
    - T-2: 모서리(0,0), 가장자리(0,4), 내부(3,3) 셀 클릭 시 `IndexError`가 발생하지 않는다.
    - T-3: 100회 무작위 시드 반복에서 첫 클릭 셀에 지뢰가 배치된 케이스가 0건이다.
    - T-4: 지뢰 외 모든 셀을 순서대로 `reveal()` 호출 후 `board.state == GameState.WIN`이 된다.
    - T-5: 지뢰 셀 좌표 직접 `reveal()` 호출 후 `board.state == GameState.LOSE`가 된다.
    - 모든 테스트가 mock/stub 없이 실제 `Board` 인스턴스를 사용한다.
  - artifacts: [tests/test_game_logic.py]
  - estimated_complexity: M
  - implementation_hint: Implementation Design §Test Strategy "비mock 실행 경로 보장" 및 T-3은 `for i in range(100): random.seed(i)` 루프 참조.

---

### Phase: Integrate

- [ ] **game_logic.py ↔ minesweeper.py 연동**
  - task_id: T-016
  - owner_role: frontend_dev
  - phase: integrate
  - depends_on: [T-010, T-011, T-014]
  - acceptance:
    - `minesweeper.py`에서 `from game_logic import Board, GameState`가 정상 import된다.
    - `python3 minesweeper.py --mines 10` 실행 시 ImportError 없이 초기 보드가 출력된다.
    - `Board.reveal()` 반환값(`GameState`)을 `main()` 루프가 올바르게 분기 처리한다.
    - R-3 위험 점검: `minesweeper.py`에 게임 규칙 로직이 직접 구현된 코드가 없다.
  - artifacts: [minesweeper.py, game_logic.py]
  - estimated_complexity: S
  - implementation_hint: Implementation Design §Risks R-3 "역할 경계 모호" 완화 전략 참조. `game_logic.py`는 stdout 미호출, `minesweeper.py`는 규칙 미구현 확인.

---

- [ ] **tests/ 실행 환경 및 import 경로 연동**
  - task_id: T-017
  - owner_role: qa_engineer
  - phase: integrate
  - depends_on: [T-015, T-016]
  - acceptance:
    - 프로젝트 루트에서 `pytest tests/ -v` 실행 시 `ModuleNotFoundError` 없이 5개 테스트가 수집된다.
    - `tests/test_game_logic.py`에서 `from game_logic import Board, GameState`가 정상 동작한다.
    - `conftest.py` 또는 `sys.path` 조작 없이도 import가 성공하거나, 필요 시 최소 설정을 추가한다.
  - artifacts: [tests/test_game_logic.py]
  - estimated_complexity: XS
  - implementation_hint: 프로젝트 루트에서 `PYTHONPATH=.` 또는 `pytest --rootdir=.` 옵션으로 경로를 확보. `conftest.py`에 `sys.path.insert(0, '.')` 최소 설정 허용.

---

### Phase: Verify

- [ ] **pytest 전체 통과 검증**
  - task_id: T-018
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-017]
  - acceptance:
    - `pytest tests/ -v` 실행 결과 5개 테스트 모두 PASS, 0 FAILED.
    - T-3(100회 반복) 포함 전체 실행 시간이 30초 이내.
    - 테스트 출력에 deprecation warning이 없거나 pytest 버전 호환 범위 내에서만 발생한다.
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: `pytest tests/ -v --tb=short` 로 실행 후 결과 스크린샷 또는 출력 텍스트를 handoff 메모에 첨부.

---

- [ ] **e2e 수동 플레이 검증 (5개 시나리오)**
  - task_id: T-019
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-016, T-018]
  - acceptance:
    - 시나리오 1: `python3 minesweeper.py --mines 10` 기동 → 8×8 `?` 보드 출력 확인.
    - 시나리오 2: 좌표 입력(`3 4`) → 셀 공개 및 인접 지뢰 수 또는 연쇄 공개 확인.
    - 시나리오 3: 깃발 명령(`f 2 5`) → 해당 셀 `F` 표시 후 재입력 시 `?` 복귀 확인.
    - 시나리오 4: 지뢰 셀 공개 → "게임 오버" 메시지 및 전체 지뢰 `*` 표시 확인.
    - 시나리오 5: `q` 입력 → 프로그램 즉시 종료 확인.
  - artifacts: []
  - estimated_complexity: S
  - implementation_hint: Implementation Design §Event Sequence Phase 0~4 흐름 순서대로 직접 실행. Brief `user_flows` 5가지와 대응.

---

- [ ] **경계 조건 및 회귀 점검**
  - task_id: T-020
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-019]
  - acceptance:
    - R-1 점검: 모서리(0,0), (7,7) 첫 클릭 시 BFS 연쇄 공개가 `IndexError` 없이 완료된다.
    - R-2 점검: 첫 클릭 좌표에 지뢰가 없음을 10회 연속 새 게임으로 확인한다.
    - R-4 점검: 지뢰 외 모든 셀 공개 시 `GameState.WIN`으로 정확히 전환된다 (카운터 오동작 없음).
    - 잘못된 입력(`abc`, `-1 0`, `9 9`, 빈 입력) 시 재입력 요청이 정상 동작한다.
    - `--mines 1` 및 `--mines 54` 경계값 옵션으로 기동이 성공한다.
  - artifacts: []
  - estimated_complexity: S
  - implementation_hint: Implementation Design §Risks R-1~R-4 완화 전략 기준으로 체크. `--mines 55`는 argparse 범위 검사로 거부됨을 확인.

---

- [ ] **잔여 리스크 및 핸드오프 기록**
  - task_id: T-021
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-020]
  - acceptance:
    - 발견된 WARN 수준 이슈(code_review_report 기준 6건 포함)가 목록화된다.
    - 해소되지 않은 리스크 항목이 있으면 다음 작업자를 위한 재현 방법과 함께 기록된다.
    - `python3 minesweeper.py --mines 10` 및 `pytest tests/ -v` 두 명령이 handoff 메모에 포함된다.
    - 프로젝트 디렉터리 구조(`minesweeper.py`, `game_logic.py`, `tests/test_game_logic.py`)가 최종 확인된다.
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: Task Board `frontend_dev_module_1_code_review` notes의 WARN 6건(parse_command/_handle_command 중복, check_win/check_lose 데드코드, QUIT 센티넬 타입 혼입, _reveal 직접 호출, size 파라미터 무시)을 handoff 메모에 그대로 인용.

---

## Blockers

현재 식별된 BLOCK 수준 이슈 없음.

**WARN 수준 항목 (advisory, 자동 수정 의무 없음)**

| 항목 | 출처 | 권고 조치 |
|------|------|-----------|
| `parse_command`와 `_handle_command` 간 로직 중복 | frontend_dev_module_1_code_review | 다음 리팩토링 사이클에서 통합 검토 |
| `check_win`/`check_lose` 데드코드 가능성 | frontend_dev_module_1_code_review | 호출 경로 추적 후 제거 여부 결정 |
| `QUIT` 센티넬 타입 혼입 | frontend_dev_module_1_code_review | `parse_input` 반환 타입을 `tuple[str,int,int]`로 일원화 |
| `_reveal` 직접 호출 노출 | frontend_dev_module_1_code_review | 공개 API `reveal()`로만 호출하도록 경로 정리 |
| `size` 파라미터 무시 | frontend_dev_module_1_code_review | 현재 8×8 고정이므로 파라미터 제거 또는 실제 사용으로 전환 |

---

## Rollback Sign-Off

| 체크포인트 | 롤백 방법 |
|-----------|-----------|
| `game_logic.py` 작성 후 테스트 실패 | 파일 삭제 후 T-006부터 재구현 |
| `minesweeper.py` 연동 실패 | `import` 경로 확인 → `game_logic.py` 공개 API 재점검 |
| pytest 경로 오류 | `conftest.py`에 `sys.path` 설정 추가 후 T-017 재실행 |
| 데이터 손실 없음 | 신규 파일만 생성, 기존 파일 미수정 — 롤백 비용 낮음 |

---

## Definition Of Done

아래 항목 전체가 충족될 때 이 work-item을 완료로 간주한다.

1. `minesweeper.py`, `game_logic.py`, `tests/test_game_logic.py` 세 파일이 프로젝트 루트 및 `tests/` 디렉터리에 존재한다.
2. `python3 minesweeper.py --mines 10` 실행 시 8×8 보드가 출력되고 입력 프롬프트가 표시된다.
3. `pytest tests/ -v` 실행 결과 5개 테스트 모두 PASS, 0 FAILED.
4. e2e 5개 시나리오(T-019) 수동 검증 완료.
5. 경계 조건 점검(T-020) 완료 — R-1~R-4 모두 이상 없음.
6. 잔여 WARN 항목이 handoff 메모에 기록되어 다음 작업자가 맥락을 이어받을 수 있다.
7. stdlib 외 런타임 의존성이 없음이 확인된다 (`pytest`는 테스트 전용 제외).