# Implementation Tasks

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| source_design | Implementation Design (2026-05-09) |
| status | completed |
| last_updated | 2026-05-09 |

---

## Preconditions

- Python 3.11 이상 설치 확인
- `pytest` 7.x 설치 확인 (`pip install pytest`)
- 작업 디렉터리: `/Users/hoon/workTree/agent-factory/projects/minesweeper-smoke-v2-03`
- 외부 의존성 없음 — stdlib(`random`, `sys`, `os`) 전용
- 기존 파일 충돌 없음 (신규 구현, 마이그레이션 불필요)

---

## Task Evidence

| 태스크 ID | 근거 문서 | 섹션 |
|-----------|-----------|------|
| T-001 | Implementation Design | Planned Modules, Data Flow |
| T-002 | Implementation Design | State And Data Model — Board, Cell |
| T-003 | Implementation Design | Phase 1: 첫 클릭 처리 및 지뢰 배치 |
| T-004 | Implementation Design | Phase 1: Mine Placement — compute_adjacent |
| T-005 | Implementation Design | Phase 2: 셀 공개, _flood_reveal |
| T-006 | Implementation Design | Phase 2, 3, 4: 승리/패배 판정 |
| T-007 | Implementation Design | Phase 0: 초기화, Interface Impact — CLI |
| T-008 | Implementation Design | Phase 2, 5: 입력 루프 및 명령 처리 |
| T-009 | Implementation Design | Interface Impact — Board.render() 출력 형식 |
| T-010 | Implementation Design | Phase 5: 깃발 토글 |
| T-011 | Implementation Design | Test Strategy — 필수 테스트 케이스 T1~T10 |
| T-012 | Implementation Design | Data Flow, Risks R1~R5 |
| T-013 | Implementation Design | Test Strategy — 비mock 실행 경로 보장 |
| T-014 | Implementation Design | Risks, Alternatives Considered |

---

## Task List

---

- [ ] **모듈 범위와 인터페이스 정의**
  - task_id: T-001
  - owner_role: game_logic_dev, frontend_dev, qa_engineer
  - phase: scope
  - depends_on: []
  - acceptance:
    - `minesweeper.py` 단일 파일 구조 및 `test_minesweeper.py` 분리 구조가 확정된다
    - `Board`, `Cell`, `GameState` 경계와 메서드 시그니처가 문서로 정리된다
    - 역할별 담당 계층(`main()` ↔ `Board`)이 명확히 분리된다
    - 의존성(stdlib 전용, pytest 7.x 테스트 전용)이 명시된다
  - artifacts: []
  - estimated_complexity: XS
  - implementation_hint: 설계 문서의 내부 계층 다이어그램을 기준으로 함수 시그니처 목록을 먼저 확정한다. `main()`이 `Board` 내부 상태를 직접 읽지 않도록 인터페이스를 설계한다.

---

- [ ] **Board 및 Cell 데이터 모델 구현**
  - task_id: T-002
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - `Board(size=8, mine_count)` 생성자가 8×8 셀 배열을 초기화한다
    - 초기화 후 모든 셀의 `is_mine=False`, `is_revealed=False`, `is_flagged=False`, `adjacent_count=0`이 보장된다
    - `mines_placed=False`, `game_state='PLAYING'` 초기 상태가 설정된다
    - `Cell` 데이터 구조가 6개 필드(`row`, `col`, `is_mine`, `adjacent_count`, `is_revealed`, `is_flagged`)를 가진다
    - `GameState` 상수(`PLAYING`, `WIN`, `LOSE`)가 정의된다 (§State And Data Model 참조)
  - artifacts: [`minesweeper.py` — Board, Cell, GameState 정의]
  - estimated_complexity: S
  - implementation_hint: `Cell`은 단순 클래스 또는 `dataclass` 사용 가능 (설계 근거: Alternatives Considered). 64셀 전체를 `[[Cell(r, c) for c in range(8)] for r in range(8)]` 리스트 컴프리헨션으로 초기화한다.

---

- [ ] **지뢰 배치 알고리즘 구현 (safe-first-click)**
  - task_id: T-003
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-002]
  - acceptance:
    - `place_mines(first_row, first_col)` 호출 후 지뢰 수 == `mine_count`임이 보장된다 (§Test Strategy T1)
    - `(first_row, first_col)` 위치에 지뢰가 배치되지 않는다 (§Test Strategy T2 — safe-first-click)
    - `random.sample`으로 63개 후보에서 `mine_count`개를 결정론적으로 선택한다
    - 이미 `mines_placed=True`인 상태에서 재호출 시 상태 변경이 없다
  - artifacts: [`minesweeper.py` — `Board.place_mines`]
  - estimated_complexity: S
  - implementation_hint: `all_cells = [(r, c) for r in range(8) for c in range(8)]`에서 `(first_row, first_col)`을 제거한 63개 목록에 `random.sample(..., mine_count)` 적용. 설계 리스크 R2 완화 기준.

---

- [ ] **인접 지뢰 수 계산 구현**
  - task_id: T-004
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-003]
  - acceptance:
    - `compute_adjacent()` 호출 후 모든 비지뢰 셀의 `adjacent_count`가 8방향 인접 지뢰 수와 일치한다 (§Test Strategy T3)
    - 보드 경계 셀(코너, 엣지)에서 범위 초과 없이 정상 계산된다
    - 지뢰 셀 자체의 `adjacent_count`는 변경하지 않는다
  - artifacts: [`minesweeper.py` — `Board.compute_adjacent`]
  - estimated_complexity: S
  - implementation_hint: `directions = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]` 8방향 순회. `0 <= nr < 8 and 0 <= nc < 8` 경계 체크 포함.

---

- [ ] **재귀 flood-reveal 구현**
  - task_id: T-005
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-004]
  - acceptance:
    - `reveal(row, col)` 호출 시 지뢰 셀이면 `game_state='LOSE'`로 전환된다 (§Test Strategy T6)
    - `adjacent_count == 0`인 셀 공개 시 8방향 미공개 비지뢰 셀을 재귀 탐색한다 (§Test Strategy T5)
    - 경계 셀(`(0,0)`, `(7,7)`)에서 무한루프 없이 정상 종료된다 (§Test Strategy T4)
    - `_flood_reveal` 진입 즉시 `is_revealed=True` 설정으로 재진입을 차단한다 (§Risks R1 완화)
    - `is_flagged=True` 셀은 공개를 무시한다 (§Test Strategy T8)
    - 이미 공개된 셀에 재호출 시 상태 변경 없이 즉시 반환한다
  - artifacts: [`minesweeper.py` — `Board.reveal`, `Board._flood_reveal`]
  - estimated_complexity: M
  - implementation_hint: `_flood_reveal` 첫 줄에서 `is_revealed=True` 설정 후 인접 수가 0인 경우에만 8방향 재귀. 8×8 = 64셀 최대 깊이는 Python 기본 재귀 한도(1000) 내 안전.

---

- [ ] **승리/패배 판정 구현**
  - task_id: T-006
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: [T-005]
  - acceptance:
    - `check_win()` 호출 시 공개된 비지뢰 셀 수 == `64 - mine_count`이면 `True`를 반환한다 (§Test Strategy T7)
    - `reveal()` 내부에서 `check_win()` 통과 시 `game_state='WIN'`으로 전환된다
    - 지뢰 셀 공개 시 `game_state='LOSE'`로 전환되고 `check_win()`은 호출되지 않는다
    - 상태 전이 다이어그램(`PLAYING → WIN`, `PLAYING → LOSE`)이 단방향임이 보장된다 (§State And Data Model 참조)
  - artifacts: [`minesweeper.py` — `Board.check_win`, `Board.reveal` 상태 전이]
  - estimated_complexity: S
  - implementation_hint: `check_win`은 `sum(1 for row in self.cells for c in row if c.is_revealed and not c.is_mine) == 64 - self.mine_count`로 단순 계산.

---

- [ ] **CLI 진입점 및 인자 파싱 구현**
  - task_id: T-007
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - `python3 minesweeper.py` 실행 시 `mine_count=10` 기본값으로 게임이 시작된다
    - `python3 minesweeper.py 15` 실행 시 `mine_count=15`로 게임이 시작된다
    - `mine_count` 범위 외 입력(0, 64, -1, 문자열)에서 오류 메시지 출력 후 `SystemExit`이 발생한다 (§Test Strategy T9)
    - 유효 범위: 1 ≤ mine_count ≤ 63 (§Risks R3 완화)
  - artifacts: [`minesweeper.py` — `parse_args()`, `main()` 진입점]
  - estimated_complexity: S
  - implementation_hint: `sys.argv[1:]`에서 파싱. 실패 시 `print("오류: 지뢰 수는 1에서 63 사이여야 합니다.")` 출력 후 `sys.exit(1)`.

---

- [ ] **입력 루프 및 명령 처리 구현**
  - task_id: T-008
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-007, T-005, T-006]
  - acceptance:
    - `<row> <col>` 형식 입력이 `Board.reveal(row, col)` 호출로 이어진다
    - `f <row> <col>` 형식 입력이 깃발 토글을 수행한다
    - `q` 입력 시 게임이 즉시 종료된다 (`sys.exit(0)`)
    - 잘못된 입력(빈 문자열, 범위 초과 좌표, 알 수 없는 명령)에서 예외 없이 오류 메시지 출력 후 루프를 계속한다
    - `game_state`가 `WIN` 또는 `LOSE`인 상태에서는 입력을 받지 않는다
    - row, col은 0-indexed 0~7 범위가 적용된다 (§Interface Impact 참조)
  - artifacts: [`minesweeper.py` — `main()` 입력 루프]
  - estimated_complexity: M
  - implementation_hint: `try/except ValueError`로 입력 파싱 실패를 포착. `game_state != 'PLAYING'` 체크를 루프 조건으로 사용해 터미널 상태 재입력을 차단.

---

- [ ] **보드 렌더링 구현**
  - task_id: T-009
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002]
  - acceptance:
    - `render()` 출력이 열 헤더(`0 1 2 3 4 5 6 7`)와 행 번호를 포함한다
    - 미공개 셀은 `.`, 공개된 빈 셀(adjacent_count=0)은 공백, 1~8은 인접 수 숫자로 표시된다
    - 깃발 셀은 `F`, 지뢰는 `*`(LOSE 시에만 공개)로 표시된다 (§Test Strategy T10)
    - LOSE 상태에서 모든 지뢰 셀이 `*`로 노출된다
    - WIN 상태에서 최종 보드가 모든 비지뢰 셀 공개 상태로 출력된다
  - artifacts: [`minesweeper.py` — `Board.render()`]
  - estimated_complexity: S
  - implementation_hint: `reveal_all = (self.game_state == 'LOSE')`로 지뢰 노출 여부를 제어. 각 셀 기호를 `_cell_symbol(cell, reveal_all)` 헬퍼로 분리하면 테스트 편의성이 높아진다.

---

- [ ] **깃발 토글 구현**
  - task_id: T-010
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002, T-008]
  - acceptance:
    - `flag(row, col)` 호출 시 미공개 셀의 `is_flagged`가 토글된다
    - 이미 공개된 셀(`is_revealed=True`)에 대한 깃발 호출은 무시된다
    - 깃발 셀에 `reveal()` 호출 시 상태 변경 없이 반환된다 (§Test Strategy T8)
    - 범위 외 좌표 입력 시 오류 메시지 출력 후 루프를 계속한다
  - artifacts: [`minesweeper.py` — `Board.flag()`]
  - estimated_complexity: XS
  - implementation_hint: `if cell.is_revealed: return` 즉시 반환. `cell.is_flagged = not cell.is_flagged`로 단순 토글.

---

- [ ] **단위 테스트 스위트 구현**
  - task_id: T-011
  - owner_role: qa_engineer
  - phase: build
  - depends_on: [T-003, T-004, T-005, T-006, T-007, T-009, T-010]
  - acceptance:
    - T1: `place_mines` 후 지뢰 수 == `mine_count` 검증
    - T2: 첫 클릭 셀에 지뢰 미배치 검증 (`safe-first-click`)
    - T3: `compute_adjacent` 정확성 — 수동 배치 기준 전 셀 인접 수 검증
    - T4: flood-reveal 경계 셀(`(0,0)`, `(7,7)`) 정상 공개 확인
    - T5: 지뢰 없는 보드에서 `reveal(0,0)` → 전 64셀 공개 (무한루프 없음)
    - T6: 지뢰 셀 `reveal` → `game_state == 'LOSE'`
    - T7: 비지뢰 전체 공개 → `game_state == 'WIN'`
    - T8: 깃발 셀 `reveal` 무시 (`is_revealed == False` 유지)
    - T9: `mine_count` 범위 외(0, 64, -1) → `SystemExit`
    - T10: `render()` 출력에 `.`, 공백, 숫자, `F`, `*` 기호 포함 확인
    - `pytest -v`로 10개 테스트 케이스 전체 PASS
    - stub 없이 실제 `Board` 인스턴스로 실행 (§Test Strategy 비mock 실행 경로 보장)
  - artifacts: [`test_minesweeper.py`]
  - estimated_complexity: M
  - implementation_hint: T5는 `mine_count=0`인 보드를 직접 생성해 `place_mines` 없이 지뢰 셀이 없는 상태로 `reveal(0,0)` 호출. T6, T7은 `Board._cells[r][c].is_mine = True/False` 수동 조작으로 결정론적 보드 구성.

---

- [ ] **전체 통합 및 E2E 실행 검증**
  - task_id: T-012
  - owner_role: game_logic_dev, frontend_dev
  - phase: integrate
  - depends_on: [T-008, T-009, T-010, T-011]
  - acceptance:
    - `python3 minesweeper.py` 실행 시 8×8 빈 보드가 출력되고 입력 프롬프트가 표시된다
    - `0 0` 입력 후 safe-first-click이 동작하고 지뢰 배치가 수행된다
    - 지뢰 셀 공개 시 `*` 위치 공개 + `"지뢰를 밟았습니다. 게임 오버."` 메시지 후 종료된다
    - 모든 비지뢰 셀 공개 시 `"축하합니다! 지뢰를 모두 피했습니다."` 메시지 후 종료된다
    - `f 3 4` 명령 후 해당 셀에 `F`가 표시된다
    - `q` 입력 시 정상 종료된다
    - 잘못된 입력(`abc`, `10 10`, ``) 후 루프가 계속된다
    - `python3 minesweeper.py 5` 실행 시 지뢰 5개 게임이 시작된다
  - artifacts: [`minesweeper.py` — 통합 E2E 검증 완료]
  - estimated_complexity: S
  - implementation_hint: `echo "0 0\nq" | python3 minesweeper.py` 파이프 입력으로 비대화형 E2E 검증 가능. `sys.stdin`이 EOF를 만나면 `EOFError`를 처리해 루프가 깨끗하게 종료되도록 한다.

---

- [ ] **테스트 통과 및 커버리지 확인**
  - task_id: T-013
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-012]
  - acceptance:
    - `pytest test_minesweeper.py -v` 실행 시 10개 테스트 케이스 전체 PASS
    - FAIL 또는 ERROR가 0건이다
    - 핵심 게임 로직 함수(`place_mines`, `compute_adjacent`, `reveal`, `flag`, `check_win`)에 대한 테스트가 누락 없이 존재한다
    - 테스트 실행 시간이 10초 미만이다 (외부 I/O 없음)
  - artifacts: [`test_minesweeper.py` — pytest 결과 PASS]
  - estimated_complexity: XS
  - implementation_hint: `pytest test_minesweeper.py -v --tb=short` 옵션으로 실패 원인을 즉시 확인. 테스트 실패 시 해당 태스크(T-003~T-010)로 역추적해 수정.

---

- [ ] **잔여 리스크 및 후속 작업 기록**
  - task_id: T-014
  - owner_role: game_logic_dev, frontend_dev, qa_engineer
  - phase: verify
  - depends_on: [T-013]
  - acceptance:
    - 설계 문서의 리스크 R1~R5에 대한 완화 여부가 기록된다
    - 구현 중 발견된 추가 WARN 항목이 목록화된다 (예: `parse_command`/`_handle_command` 중복, `check_win`/`check_lose` 데드코드 가능성)
    - 현재 구현에서 미지원 항목(GUI, 리더보드, 동적 크기)이 Non-Goals로 재확인된다
    - 후속 작업 후보(예: `size` 파라미터 활성화, `mine_count` 상한 인터랙티브 프롬프트)가 명시된다
    - 구현 완료 상태가 커밋 메시지 또는 NEXT_STEPS.md에 반영된다
  - artifacts: [NEXT_STEPS.md 또는 handoff 메모]
  - estimated_complexity: XS
  - implementation_hint: 설계 문서의 Risks 섹션을 기준으로 체크리스트 형태로 작성. BLOCK 수준 리스크만 즉시 수정하고 WARN은 advisory로 기록.

---

## Blockers

현재 확인된 블로커 없음.

> **주의**: `mine_count >= 64` 입력 시 `random.sample`이 `ValueError`를 발생시킨다. T-007(인자 파싱)에서 1~63 범위 검증이 완료되어야 T-003이 안전하게 실행된다. (§Risks R3)

---

## Rollback Sign-Off

- 신규 구현이므로 롤백 대상 기존 상태 없음
- 롤백 필요 시: `minesweeper.py`, `test_minesweeper.py` 파일 삭제로 완전 복구 가능
- 기존 코드베이스 영향 없음 (단일 프로젝트 디렉터리 내 독립 파일)
- 커밋 단위: T-002~T-006(게임 로직) → T-007~T-010(CLI/I/O) → T-011(테스트) → T-012~T-014(통합+검증) 순서 권장

---

## Definition Of Done

| 항목 | 기준 |
|------|------|
| 기능 완성 | `python3 minesweeper.py` 실행 후 지뢰 공개(LOSE) 또는 전체 비지뢰 공개(WIN)까지 플레이 가능 |
| 테스트 통과 | `pytest test_minesweeper.py -v` 10개 케이스 전체 PASS, ERROR 0건 |
| safe-first-click | 첫 번째 `reveal` 좌표에 지뢰가 배치되지 않음이 T2로 검증됨 |
| 재귀 안전성 | 지뢰 없는 보드 전체 공개(T5)에서 무한루프 없이 정상 종료됨 |
| 입력 견고성 | 잘못된 입력 및 범위 외 좌표에서 예외 없이 루프 유지됨 |
| stdlib 전용 | `import` 목록에 `random`, `sys` 외 서드파티 패키지 없음 |
| 플랫폼 중립 | `os.system('clear'/'cls')` 미사용, macOS·Linux·Windows 동작 보장 |
| 리스크 해소 | 설계 R1~R5 전원 완화 조치가 코드에 반영됨 |
| 세션 연속성 | 구현 완료 후 `NEXT_STEPS.md` 업데이트 + git commit + git push 완료 |