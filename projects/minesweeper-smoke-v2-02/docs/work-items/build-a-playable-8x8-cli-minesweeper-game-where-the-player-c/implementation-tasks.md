# Implementation Tasks

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| source_design | Implementation Design v1.0 (2026-05-08) |
| status | `completed` |
| last_updated | 2026-05-08 |

---

## Preconditions

- Python 3.11 런타임 설치 확인 (`python3 --version`)
- pytest 7.x 설치 확인 (`pytest --version`) — 테스트 전용, `minesweeper.py` 실행 시 불필요
- 워크스페이스 경로 `/Users/hoon/workTree/agent-factory/projects/minesweeper-smoke-v2-02` 내에 `minesweeper.py`, `test_minesweeper.py` 미존재 확인 (신규 구현)
- 외부 의존성 없음 — stdlib(`random`, `sys`, `dataclasses`) 전용

---

## Task Evidence

| 근거 | 참조 |
|------|------|
| 단일 파일 + stdlib 전용 제약 | Brief §constraints |
| safe-first-click 설계 | Implementation Design §Phase 1, Risks R-2 |
| 재귀 flood-reveal 상한 안전성 | Implementation Design §Alternatives C — 최대 깊이 64, Python recursion limit 1000 |
| 역할 분리 기준 | `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑 |
| 테스트 케이스 목록 | Implementation Design §Test Strategy T-1~T-8 |
| mine_count 범위 검증 기준 | Implementation Design §Risks R-5 — `1 ≤ mine_count ≤ 54` |
| ASCII 렌더링 기호 규칙 | Implementation Design §State And Data Model — 렌더링 기호 테이블 |

---

## Task List

---

### Scope — 범위와 계약 정의

- [ ] **Game Logic 인터페이스 범위 정의**
  - task_id: T-001
  - owner_role: game_logic_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `Board.__init__(grid_size, mine_count)`, `place_mines(exclude)`, `compute_adjacency()`, `reveal(r,c)`, `_flood(r,c,visited)`, `toggle_flag(r,c)`, `check_win()` 시그니처가 문서화된다 (spec §Functional Requirements)
    - 반환 타입이 명확히 고정된다: `reveal` → `"ok" | "mine" | "already_revealed"`, `toggle_flag` → `bool`, `check_win` → `bool`
    - `game_state` 전이 규칙(`PLAYING → WIN | LOSE`)이 명시된다
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: Implementation Design §Interface Impact 테이블과 §State And Data Model을 기준으로 작성. `Board` 클래스가 stdout을 직접 호출하지 않음을 명시 (R-3 방지)

- [ ] **CLI I/O 인터페이스 범위 정의**
  - task_id: T-002
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `render(board) -> None` 출력 기호 규칙이 고정된다: 미공개=`·`, 깃발=`F`, 숫자=`1–8`, 빈 공개=` `, 지뢰=`*`
    - `parse_input(line: str) -> tuple | None` 입출력 계약이 고정된다: `"r c"` → `(r,c,False)`, `"f r c"` → `(r,c,True)`, 잘못된 형식 → `None`
    - 열 헤더(`0–7`), 행 번호(`0–7`) 포함 레이아웃이 명시된다
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: Implementation Design §Planned Modules `render`, `parse_input` 행 참조. 이모지 출력은 ASCII 대체 문자열 병기 방식으로 처리 (§Compatibility Considerations)

- [ ] **테스트 스코프 및 케이스 목록 정의**
  - task_id: T-003
  - owner_role: qa_engineer
  - phase: scope
  - depends_on: [T-001, T-002]
  - acceptance:
    - T-1~T-8 테스트 케이스 ID와 검증 대상이 열거된다 (Implementation Design §Test Strategy)
    - mock 전용 테스트를 허용하지 않는다는 제약이 명시된다
    - `pytest test_minesweeper.py -v` 실행 명령이 고정된다
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: 테스트 케이스별로 `Board` 인스턴스를 직접 생성하는 방식. `minesweeper.py`를 import한 뒤 public API만 호출

---

### Build — 기능 슬라이스 구현

- [ ] **Cell dataclass 구현**
  - task_id: T-004
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - `@dataclass class Cell` 에 `row: int`, `col: int`, `is_mine: bool = False`, `adjacent_count: int = 0`, `is_revealed: bool = False`, `is_flagged: bool = False` 필드가 존재한다
    - `from __future__ import annotations`가 파일 상단에 추가된다 (Python 3.9+ 호환, spec §Compatibility)
  - artifacts: [`minesweeper.py` — Cell 클래스]
  - estimated_complexity: XS
  - implementation_hint: `from dataclasses import dataclass`만 import. `row`, `col` 필드는 `field(default=0)`으로 초기화하지 않고 위치 인자로 유지

- [ ] **Board 초기화 및 8×8 그리드 생성**
  - task_id: T-005
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-004]
  - acceptance:
    - `Board.__init__(grid_size=8, mine_count=10)` 호출 시 8×8 `Cell` 배열이 생성된다
    - `mines_placed: bool = False`, `game_state: str = "PLAYING"`, `_mine_positions: set = set()` 초기화된다
    - `mine_count` 범위 검증: `1 ≤ mine_count ≤ 54`; 범위 외 값은 오류 메시지 출력 후 `sys.exit(1)` (spec §Functional Requirements, R-5)
  - artifacts: [`minesweeper.py` — Board.__init__]
  - estimated_complexity: S
  - implementation_hint: `self.cells = [[Cell(r, c) for c in range(grid_size)] for r in range(grid_size)]`

- [ ] **place_mines(exclude) — safe-first-click 지뢰 배치**
  - task_id: T-006
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-005]
  - acceptance:
    - `exclude` 집합에 포함된 좌표에는 지뢰가 배치되지 않는다 (T-1 검증 기준)
    - `random.sample`로 균등 분포 지뢰 위치 결정 (R-4)
    - 호출 후 `mines_placed = True`로 설정된다
    - 배치 완료 후 `_mine_positions`에 모든 지뢰 좌표가 기록된다
  - artifacts: [`minesweeper.py` — Board.place_mines]
  - estimated_complexity: S
  - implementation_hint: `all_cells = {(r,c) for r in range(8) for c in range(8)} - exclude`; `random.sample(list(all_cells), mine_count)` 호출

- [ ] **compute_adjacency() — 인접 지뢰 수 계산**
  - task_id: T-007
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-006]
  - acceptance:
    - 전 셀의 `adjacent_count`가 8방향 이웃 지뢰 수와 일치한다 (T-2 검증 기준)
    - 경계 셀(코너, 모서리)에서 범위 초과 인덱스 오류 없이 실행된다
    - `place_mines()` 호출 후에만 의미 있는 결과를 반환한다
  - artifacts: [`minesweeper.py` — Board.compute_adjacency]
  - estimated_complexity: S
  - implementation_hint: 8방향 델타 `[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]` 사용. `if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size` 경계 가드

- [ ] **reveal(r, c) + _flood(r, c, visited) — 재귀 연쇄 공개**
  - task_id: T-008
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-007]
  - acceptance:
    - `reveal(r, c)` 반환값: `"already_revealed"` | `"mine"` | `"ok"` (T-8, T-5 검증 기준)
    - `is_mine == True` 공개 시 `game_state = "LOSE"` 전환된다
    - `adjacent_count == 0` 셀 공개 시 `_flood` 재귀 호출로 연쇄 공개된다 (T-3)
    - `_flood` 첫 줄 경계 가드 `if not (0 <= r < self.grid_size and 0 <= c < self.grid_size): return` 의무화 (R-1)
    - `visited` 집합으로 재방문 차단 — 무한루프 없이 종료된다 (T-3)
    - 최악 케이스(전 셀 연쇄)에서 재귀 깊이 ≤ 64로 Python recursion limit 초과 없음
  - artifacts: [`minesweeper.py` — Board.reveal, Board._flood]
  - estimated_complexity: M
  - implementation_hint: `reveal` 호출 전 `visited.add((r,c))`를 재귀 진입 전에 수행하여 사전 마킹. `_flood` 내 각 이웃 호출 전 `if (nr,nc) not in visited` 체크

- [ ] **toggle_flag(r, c) — 깃발 토글**
  - task_id: T-009
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-005]
  - acceptance:
    - 미공개 셀에서 1회 호출 시 `is_flagged = True`로 변경되고 `True` 반환 (T-6)
    - 같은 셀 2회 호출 시 `is_flagged = False`로 복원되고 `False` 반환 (T-6)
    - 이미 공개된 셀에서 호출 시 상태 변경 없이 `False` 반환
  - artifacts: [`minesweeper.py` — Board.toggle_flag]
  - estimated_complexity: XS
  - implementation_hint: `cell = self.cells[r][c]; if cell.is_revealed: return False; cell.is_flagged = not cell.is_flagged; return cell.is_flagged`

- [ ] **check_win() — 승리 판정 및 game_state 전이**
  - task_id: T-010
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-008]
  - acceptance:
    - 비지뢰 셀 전체가 공개된 경우 `game_state = "WIN"` 전환 후 `True` 반환 (T-4)
    - 아직 미공개 비지뢰 셀이 존재하면 `False` 반환
    - `game_state == "LOSE"` 상태에서는 호출해도 `WIN`으로 덮어쓰지 않는다
  - artifacts: [`minesweeper.py` — Board.check_win]
  - estimated_complexity: XS
  - implementation_hint: `all(c.is_revealed for r in self.cells for c in r if not c.is_mine)` 평가 후 결과가 `True`이면 `game_state` 업데이트

- [ ] **render(board) — ASCII 보드 출력**
  - task_id: T-011
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002, T-004]
  - acceptance:
    - 열 헤더 `  0 1 2 3 4 5 6 7` 형식으로 출력된다
    - 각 행 앞에 행 번호 `r|` 형식으로 출력된다
    - 셀 기호 규칙 준수: 미공개=`·`, 깃발=`F`, 숫자=`1–8`, 빈 공개=` `, 지뢰=`*` (§State And Data Model 렌더링 기호 테이블)
    - `render()` 외부에서 `Board` 클래스가 직접 stdout을 호출하지 않는다 (R-3)
  - artifacts: [`minesweeper.py` — render 함수]
  - estimated_complexity: S
  - implementation_hint: `sys.stdout.write` 대신 `print()` 사용. `board.cells` 순회 시 `cell.is_revealed`, `cell.is_flagged`, `cell.is_mine`, `cell.adjacent_count` 순서로 조건 분기

- [ ] **parse_input(line) — 입력 파서**
  - task_id: T-012
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002]
  - acceptance:
    - `"3 4"` → `(3, 4, False)` 반환 (T-7)
    - `"f 2 5"` → `(2, 5, True)` 반환 (T-7)
    - `"abc"`, 범위 초과 좌표(`9 9`), 토큰 수 오류 → `None` 반환 (T-7)
    - 좌표 범위 `0 ≤ r, c ≤ 7` 검증 포함
  - artifacts: [`minesweeper.py` — parse_input 함수]
  - estimated_complexity: S
  - implementation_hint: `tokens = line.strip().split()`; `len(tokens) not in (2, 3)` 검사 후 `int()` 변환 실패 시 `except ValueError: return None`. `is_flag = tokens[0].lower() == "f"`

- [ ] **main() — 게임 루프 진입점**
  - task_id: T-013
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-005, T-006, T-008, T-009, T-010, T-011, T-012]
  - acceptance:
    - `python3 minesweeper.py` 실행 시 mine_count 기본값 10으로 빈 보드 출력 후 입력 대기
    - `python3 minesweeper.py 15` 실행 시 mine_count=15 적용 (범위 검증 포함)
    - 첫 `reveal` 호출 시 `place_mines` + `compute_adjacency` 실행 (lazy initialization, Phase 1)
    - 잘못된 입력 → 경고 메시지 출력 후 재입력 요청 (반복 종료 없음)
    - `game_state == "LOSE"` 시 모든 지뢰 공개 후 게임 오버 메시지 출력 → `sys.exit(0)` (Phase 3)
    - `game_state == "WIN"` 시 완성 보드 출력 후 승리 메시지 → `sys.exit(0)` (Phase 4)
  - artifacts: [`minesweeper.py` — main 함수, `if __name__ == "__main__"` 진입점]
  - estimated_complexity: M
  - implementation_hint: 게임 루프는 `while board.game_state == "PLAYING":` 구조. `mines_placed` 플래그로 첫 클릭 분기. `sys.argv[1:]` 파싱 시 `try/except ValueError` 처리

- [ ] **test_minesweeper.py — 단위 테스트 스위트**
  - task_id: T-014
  - owner_role: qa_engineer
  - phase: build
  - depends_on: [T-003, T-006, T-007, T-008, T-009, T-010, T-012]
  - acceptance:
    - T-1~T-8 테스트 케이스 전체 구현 (Implementation Design §Test Strategy)
    - `pytest test_minesweeper.py -v` 실행 시 전 케이스 PASS
    - mock 객체 사용 없음 — 전 테스트가 실제 `Board` 인스턴스 호출
    - `test_flood_reveal_no_infinite_loop`: `(0,0)` 및 `(7,7)` 코너 셀에서 `reveal()` 정상 완료 확인 (T-3)
    - `test_mine_placement_excludes_first_click`: `exclude={(r,c)}` 후 해당 셀 `is_mine == False` 단언 (T-1)
  - artifacts: [`test_minesweeper.py`]
  - estimated_complexity: M
  - implementation_hint: `Board` 인스턴스 생성 후 `_mine_positions`를 직접 조작하거나 `place_mines(exclude=set())` 호출로 결정론적 상태 생성. 인접 계산 정확성 테스트(T-2)는 수동 지뢰 배치(`cells[r][c].is_mine = True`) 후 `compute_adjacency()` 호출로 검증

---

### Integrate — 통합과 핸드오프

- [ ] **minesweeper.py 단일 파일 통합 검증**
  - task_id: T-015
  - owner_role: frontend_dev
  - phase: integrate
  - depends_on: [T-013]
  - acceptance:
    - `python3 -c "import minesweeper; b = minesweeper.Board(8,10); b.place_mines(exclude={(3,3)}); b.compute_adjacency(); result = b.reveal(3,3); assert result in ('ok','mine')"` 오류 없이 실행 완료 (Implementation Design §Test Strategy e2e 명령)
    - `minesweeper.py` 내 `import pytest` 구문이 없다 (게임 실행 시 pytest 미의존)
    - `from __future__ import annotations` 파일 첫 줄에 존재한다
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: e2e 명령 직접 실행 후 출력 확인. `python3 -c "import py_compile, sys; py_compile.compile('minesweeper.py', doraise=True)"` 로 문법 오류 사전 검증

- [ ] **pytest 전체 실행 및 커버리지 확인**
  - task_id: T-016
  - owner_role: qa_engineer
  - phase: integrate
  - depends_on: [T-014, T-015]
  - acceptance:
    - `pytest test_minesweeper.py -v` 실행 결과 전 케이스 PASSED
    - 실패 케이스 0건
    - 핵심 게임 로직 경로(지뢰 배치, 인접 계산, flood-reveal, 승패 판정) 커버리지 목표 달성 확인
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: `pytest test_minesweeper.py -v --tb=short` 실행. 실패 시 traceback 전문을 handoff 메모에 첨부

---

### Verify — 검증과 마감

- [ ] **e2e 게임 플레이 시나리오 검증**
  - task_id: T-017
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-015, T-016]
  - acceptance:
    - 정상 게임 플레이: 빈 보드 출력 → 좌표 입력 → 셀 공개 → 깃발 토글 → 보드 갱신 순서대로 동작 확인 (spec §User Scenarios)
    - 지뢰 클릭 시 전체 지뢰 위치 공개 후 게임 오버 메시지 출력 및 `sys.exit(0)` 확인 (Phase 3)
    - 잘못된 입력(`abc`, `9 9`, 빈 입력) 입력 시 경고 후 재입력 요청 확인 (spec §Exceptions)
    - `python3 minesweeper.py 5` (mine_count=5) 실행 시 정상 동작
    - `python3 minesweeper.py 55` (범위 초과) 실행 시 오류 메시지 출력 후 종료 (R-5)
  - artifacts: []
  - estimated_complexity: S
  - implementation_hint: stdin 파이프 방식 자동화: `echo "3 4" | python3 minesweeper.py`로 첫 입력 검증. 게임 오버 시나리오는 `Board._mine_positions`를 조작한 단위 테스트로 대체 가능

- [ ] **코드 리뷰 — 품질·보안·설계 검토**
  - task_id: T-018
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-017]
  - acceptance:
    - `parse_input`/`main` 간 입력 처리 중복 없음 (WARN 방지)
    - `check_win`/`reveal` 간 game_state 설정 경로가 단일화되어 있다
    - `Board` 클래스 내 직접 stdout 호출(`print`) 없음 (R-3 준수)
    - BLOCK 판정 항목 0건; WARN 항목은 handoff 메모에 기록
  - artifacts: [`docs/code_review/code-review.md`]
  - estimated_complexity: S
  - implementation_hint: af-critic 에이전트 실행. WARN 6건 이하로 유지 목표 (Task Board `frontend_dev_module_1_code_review` 이력 참조)

- [ ] **교차 검증 및 최종 handoff**
  - task_id: T-019
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-018]
  - acceptance:
    - af-cross-review 실행 결과 BLOCK 판정 0건
    - `minesweeper.py`와 `test_minesweeper.py` 모두 최종 상태로 커밋된다
    - handoff 메모에 잔여 WARN 목록, 후속 작업(있는 경우), 실행 명령이 기록된다
    - `python3 minesweeper.py`가 README 또는 handoff 메모 내 실행 방법에 명시된다
  - artifacts: [`docs/handoff/minesweeper-smoke-v2-02-handoff.md`]
  - estimated_complexity: S
  - implementation_hint: codex_cli 프로바이더로 교차 검증 실행. BLOCK 발견 시 해당 항목만 수정 후 1회 재실행 (max_rounds=2 캡 적용)

---

## Blockers

현재 알려진 blocker 없음.

잠재적 blocker 후보:

| 항목 | 유형 | 영향 작업 | 대응 |
|------|------|-----------|------|
| Python 3.11 미설치 | 환경 | T-013, T-015, T-017 | `python3 --version` 확인 후 3.9 이상이면 `from __future__ import annotations` 추가로 우회 가능 |
| pytest 미설치 | 환경 | T-014, T-016 | `pip install pytest` 또는 `pip install --user pytest` |
| codex_cli 인증 만료 | 검증 | T-019 | 재인증 후 재실행. 프로바이더 0개이면 T-019 SKIP(통과 간주) |

---

## Rollback Sign-Off

| 조건 | 롤백 범위 | 방법 |
|------|-----------|------|
| T-008 (_flood 무한루프 재현) | `minesweeper.py` 전체 | `git checkout minesweeper.py` 후 T-008 재구현 |
| T-016 테스트 FAIL (T-1~T-8 중 1건 이상) | `test_minesweeper.py` 전체 | T-014 재작업 |
| T-019 BLOCK 판정 (2라운드 초과) | 해당 모듈 파일만 | 사용자 수동 결정 — `AF_SKIP_REVIEW_GATE=1`로 우회 또는 항목별 재수정 |

신규 구현이므로 마이그레이션 롤백 불필요. 기존 파일 덮어쓰기 위험 없음.

---

## Definition Of Done

아래 항목 전체 충족 시 완료로 간주한다.

- [ ] `python3 minesweeper.py` 실행 시 8×8 빈 보드가 출력되고 입력 대기 상태 진입
- [ ] `pytest test_minesweeper.py -v` 결과 전 케이스 PASSED, 실패 0건
- [ ] T-1~T-8 테스트 케이스 전체 구현 및 통과 (Implementation Design §Test Strategy)
- [ ] `minesweeper.py` 내 `import pytest` 구문 없음 (게임 실행 시 pytest 미의존)
- [ ] safe-first-click 동작 확인: 첫 클릭 좌표에 지뢰 미배치 검증 (T-1)
- [ ] flood-reveal 경계 안전성 확인: `(0,0)`, `(7,7)` 코너에서 무한루프 없이 종료 (T-3)
- [ ] 승리·패배 조건 전이 확인 (T-4, T-5)
- [ ] 코드 리뷰 BLOCK 판정 0건 (T-018)
- [ ] 교차 검증 BLOCK 판정 0건 (T-019)
- [ ] `minesweeper.py`, `test_minesweeper.py` 최종 상태 커밋 완료
- [ ] handoff 메모에 실행 방법, 잔여 WARN 목록, 후속 작업 기록 완료