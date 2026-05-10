# Frontend Dev Module 2 검증 완료 Handoff 메모

## 메타데이터

| 항목 | 값 |
|------|-----|
| task_id | `frontend_dev_module_2_verify_3` |
| 작성일 | `2026-05-08` |
| 작성 역할 | frontend_dev |
| 검증 대상 | `minesweeper.py:39-173` (지뢰 배치 및 셀 공개 게임 로직), `tests/test_minesweeper_unit.py` (슬라이스 2·3) |
| 최종 판정 | **WARN** (신규 BLOCK 없음, 선행 BLOCK 잔존, Module 3 관련 테스트 1건 실패) |

---

## 검증 결과 요약

### 테스트 실행 결과 (2026-05-08)

```
pytest tests/test_minesweeper_unit.py tests/test_game_logic.py -v
```

| 파일 | 결과 | 세부사항 |
|------|------|---------|
| `test_minesweeper_unit.py` | 13/14 PASS, **1 FAIL** | `test_render_board_reveal_all_shows_mine_symbol` 실패 |
| `test_game_logic.py` | 5/5 PASS | `src/game_logic.py` 전체 PASS |
| **합계** | **18/19** | |

### Module 2 범위 테스트 (슬라이스 2·3) — 전체 PASS

| 테스트 | 결과 | 검증 항목 |
|--------|------|---------|
| `test_place_mines_keeps_first_click_safe` | ✅ PASS | 첫 클릭 셀 지뢰 배제 |
| `test_reveal_cell_skips_flagged_cell` | ✅ PASS | 깃발 셀 공개 무시 |
| `test_reveal_cell_cascade_on_zero_adjacent` | ✅ PASS | 인접 수 0 연쇄 공개 |

### 실패 테스트 — Module 3 범위 (`render_board` 파라미터명 불일치)

```
FAILED tests/test_minesweeper_unit.py::test_render_board_reveal_all_shows_mine_symbol
TypeError: render_board() got an unexpected keyword argument 'reveal_all'
```

**원인**: 
- 테스트: `render_board(board, reveal_all=True)` 사용
- 구현: `render_board(board, reveal_mines=False)` — `reveal_mines` 파라미터명 사용

이 불일치는 Module 1 handoff의 CV-01에서 이미 문서화된 WARN이다.  
Module 3 작업에서 파라미터명을 통일해야 한다 (테스트가 `reveal_all`을 사용하므로 구현을 `reveal_all`로 수정하거나 테스트를 `reveal_mines`로 변경).

---

## Module 2 구현 완료 기능 목록

`minesweeper.py`에 아래 기능이 모두 구현되어 있으며 정상 동작한다.

| 구현체 | 위치 | 상태 |
|--------|------|------|
| `Board.place_mines(safe_row, safe_col)` — 첫 클릭 + 8방향 안전 영역 제외 후 지뢰 배치 | `minesweeper.py:39-59` | ✅ 완료 |
| `Board._calc_adjacent_counts()` — 인접 지뢰 수 계산 | `minesweeper.py:61-75` | ✅ 완료 |
| `Board.reveal_cell(row, col)` — safe-first-click 래퍼 | `minesweeper.py:77-84` | ✅ 완료 |
| `Board._reveal(row, col)` — 재귀 연쇄 공개 + 승리 체크 | `minesweeper.py:86-101` | ✅ 완료 |
| `Board._check_win()` — 비지뢰 전체 공개 시 WIN 전환 | `minesweeper.py:111-116` | ✅ 완료 |
| `place_mines(board, first_click)` — 모듈 수준 래퍼 | `minesweeper.py:163-166` | ✅ 완료 |
| `reveal_cell(board, row, col)` — 모듈 수준 래퍼 | `minesweeper.py:169-173` | ✅ 완료 (주의사항 있음) |

**참고**: `src/game_logic.py`(game_logic_dev 산출물)의 함수형 구현(`createGame`, `openCell`, `toggleFlag`)도 5/5 PASS로 독립 검증 완료.

---

## 알려진 이슈 및 잔여 리스크

### 🔴 잔존 BLOCK — mine_count 상한선 불일치 (Module 1에서 이어짐)

| 위치 | 내용 |
|------|------|
| `minesweeper.py:150` | `create_board()` — 상한선 **54**로 수정 완료 |
| `minesweeper.py:280` | `main()` — 상한선 **63** 그대로 남아 있음 |
| `minesweeper.py:229` | argparse help 문자열도 `'범위: 1~63'`으로 노출 |

**위험**: `--mines 56` 이상 입력 시 `place_mines`에서 `random.sample` `ValueError` 크래시 발생.  
**수정 방법**: `minesweeper.py:280`의 `<= 63`을 `<= 54`로, `minesweeper.py:229`의 help 문자열도 `1~54`로 통일.

### 🔴 테스트 실패 — `render_board` 파라미터명 불일치 (Module 3에서 처리)

| 위치 | 내용 |
|------|------|
| `tests/test_minesweeper_unit.py:206` | `render_board(board, reveal_all=True)` 호출 |
| `minesweeper.py:206` | `render_board(board, reveal_mines=False)` 구현 |

**수정 방법 (두 가지 중 선택)**:
- 옵션 A: `minesweeper.py:206`의 파라미터명 `reveal_mines` → `reveal_all`로 변경 (+ `minesweeper.py:208`, `131` 내부 참조도 일괄 수정), `architecture.md §Module 3`도 갱신
- 옵션 B: 테스트의 `reveal_all=True` → `reveal_mines=True`로 변경

> **권장**: 옵션 A (테스트가 먼저 작성된 계약이며 `reveal_all`이 더 직관적). Module 3 build 단계에서 처리.

### ⚠️ WARN — 모듈 수준 reveal_cell() 호출 계약 미명시 (CV2-02)

| 위치 | 내용 |
|------|------|
| `minesweeper.py:169-173` | `board._reveal(row, col)` 직접 호출 — `Board.reveal_cell()` safe-first-click 가드 우회 |

`place_mines()` 없이 `reveal_cell()` 호출 시 지뢰 미배치 상태에서 모든 셀이 공개되어 즉시 WIN 판정 가능.  
**Module 3 작업 전 인지 필요**. 호출 계약이 docstring 또는 assertion으로 보호되지 않음.

### ⚠️ WARN — 테스트 갭 (CV2-04, CV2-05)

| ID | 미테스트 시나리오 |
|----|----------------|
| CV2-04 | `place_mines` 8방향 안전 구역 인접 셀 지뢰 제외 검증 없음 |
| CV2-05 | `reveal_cell()` 호출 전 `place_mines()` 미호출 시 동작 검증 없음 |
| CV2-05 | `_check_win()` PLAYING 유지 독립 테스트 없음 |

### ⚠️ WARN — 아키텍처 문서 섹션 간 필드명 충돌 (CV2-06)

| 위치 | 내용 |
|------|------|
| `docs/architecture.md:160-165` | Backend Dev 섹션: `is_revealed`, `is_flagged` 사용 |
| `minesweeper.py:17-22` | 실제 구현: `revealed`, `flagged` 사용 |

기능 오류 없음. 다음 `architecture.md` 갱신 시 수정 권장.

### ⚠️ INFO — 두 구현체 병존 관계

`src/game_logic.py` (game_logic_dev: 함수형 immutable 모델)와 `minesweeper.py` (frontend_dev: 객체형 mutable Board)가 서로 독립적으로 공존한다. `GameState` 이름 충돌 존재 (enum vs frozen dataclass). 통합 시 진입점 결정 필요.

---

## Module 3 작업자를 위한 필수 사항

### 1. render_board 파라미터명 통일 (BLOCK 수준 테스트 실패)

`minesweeper.py:206`의 `render_mines` → `reveal_all`로 일괄 변경 (또는 반대 방향으로 테스트 수정).  
변경 후 `pytest tests/test_minesweeper_unit.py` 19/19 PASS 확인.

```python
# 현재 (minesweeper.py:206)
def render_board(board: Board, reveal_mines: bool = False) -> str:

# 수정 후 (옵션 A)
def render_board(board: Board, reveal_all: bool = False) -> str:
```

### 2. mine_count 상한선 BLOCK 처리

```python
# minesweeper.py:280 — 현재 (BLOCK)
if not (1 <= mines <= 63):

# 수정 후
if not (1 <= mines <= 54):
```

```python
# minesweeper.py:229 — 현재
help="지뢰 수 (기본: 10, 범위: 1~63)",

# 수정 후
help="지뢰 수 (기본: 10, 범위: 1~54)",
```

### 3. Module 3 렌더링 갭 목록 (Module 1 handoff CV-02~05)

| ID | 위치 | 현재 구현 | 요구 사항 |
|----|------|-----------|---------|
| CV-02 | `minesweeper.py:124-145` | `"{r} \| {셀들}"` | `"{r}  {셀들}"` (파이프 제거, 공백 2개) |
| CV-03 | `minesweeper.py:285-286` | `'8×8 지뢰찾기 시작! ...'` | `'지뢰찾기 8×8 [지뢰: N개]'` 헤더 |
| CV-04 | `minesweeper.py:290` | `'명령> '` | `'명령 입력 (행 열 / f 행 열 / q): '` |
| CV-05 | `minesweeper.py:297-298` | `MSG_QUIT` 미출력 | `q` 입력 시 `print(MSG_QUIT)` |

---

## 참조 문서

| 문서 | 용도 |
|------|------|
| `minesweeper.py` | 구현 단일 진실 소스 |
| `docs/architecture.md §Frontend Dev Module 2` | Module 2 범위·인터페이스 정의 |
| `docs/architecture.md §Frontend Dev Module 3` | Module 3 수정 범위 및 순서 |
| `docs/designer/ui-spec.md` | 모든 출력 형식의 단일 기준 |
| `docs/cross_validate/2026-05-08-frontend-dev-module-2-cross-validate.md` | Module 2 교차검증 WARN 상세 (6건) |
| `docs/frontend_dev_module_2_cross_validate_result.md` | Module 2 교차검증 결과 PASS 요약 |
| `docs/plans/2026-05-08-frontend-dev-module-3-scope.md` | Module 3 수정 계획 |
| `docs/handoff/frontend_dev_module_1_handoff.md` | Module 1 잔존 이슈 전체 목록 |
| `tests/test_minesweeper_unit.py` | 단위 테스트 (19개) |

---

## Frontend Dev Module 2 완료 선언

`frontend_dev_module_2` 전체 단계(scope → build → cross_validate → verify)가 완료되었다.

- **핵심 기능 완료**: 지뢰 배치(첫 클릭 안전 영역), 인접 수 계산, 연쇄 공개, 승리/패배 판정 모두 구현
- **Module 2 전용 테스트**: 슬라이스 2·3 (3개 테스트) 전부 PASS
- **교차검증 판정**: WARN (BLOCK 없음)
- **잔존 작업**:
  1. 🔴 `render_board` 파라미터명 통일 (`reveal_all` vs `reveal_mines`) — Module 3 build에서 처리
  2. 🔴 `mine_count` 상한선 63→54 통일 — Module 3 build 또는 별도 패치로 처리
  3. ⚠️ Module 3 UI 형식 갭 4건 — `frontend_dev_module_3_build_2`에서 처리
