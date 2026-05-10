# Frontend Dev Module 1 검증 완료 Handoff 메모

## 메타데이터

| 항목 | 값 |
|------|-----|
| task_id | `frontend_dev_module_1_verify_3` |
| 작성일 | `2026-05-08` |
| 작성 역할 | designer (verify 단계) |
| 검증 대상 | `minesweeper.py` (317 LOC), `tests/test_minesweeper_unit.py` |
| 최종 판정 | **WARN** (신규 BLOCK 없음, 선행 BLOCK 잔존) |

---

## 구현 완료 기능 목록

`minesweeper.py` 단일 파일에 아래 기능이 모두 구현되어 있다.

### 데이터 모델
| 구현체 | 위치 | 상태 |
|--------|------|------|
| `GameState` (enum) | `minesweeper.py:11-14` | ✅ 완료 |
| `Cell` (dataclass) | `minesweeper.py:17-22` | ✅ 완료 |
| `Board.__init__` | `minesweeper.py:28-37` | ✅ 완료 |

### 게임 로직 (Module 2 범위)
| 구현체 | 위치 | 상태 |
|--------|------|------|
| `Board.place_mines` — 첫 클릭 + 8방향 안전 영역 제외 후 지뢰 배치 | `minesweeper.py:39-59` | ✅ 완료 |
| `Board._calc_adjacent_counts` — 인접 지뢰 수 계산 | `minesweeper.py:61-75` | ✅ 완료 |
| `Board.reveal_cell` — 안전 첫 클릭 래퍼 (safe-first-click) | `minesweeper.py:77-84` | ✅ 완료 |
| `Board._reveal` — 재귀 연쇄 공개 | `minesweeper.py:86-101` | ✅ 완료 |
| `Board._check_win` — 비지뢰 셀 전체 공개 여부 검사 | `minesweeper.py:111-116` | ✅ 완료 |

### 보드 렌더링 및 상태 조회 (Module 3 범위 일부 포함)
| 구현체 | 위치 | 상태 |
|--------|------|------|
| `Board.render` — ASCII 보드 렌더링 | `minesweeper.py:124-145` | ✅ 완료 (포맷 갭 존재, 하단 참조) |
| `Board.toggle_flag` — 깃발 토글 | `minesweeper.py:103-109` | ✅ 완료 |
| `Board.check_win` / `Board.check_lose` | `minesweeper.py:118-122` | ✅ 완료 (데드 코드 주의) |

### 모듈 수준 공개 API
| 함수 | 위치 | 상태 |
|------|------|------|
| `create_board(size, mine_count)` | `minesweeper.py:148-152` | ✅ 완료 (상한선 54로 수정됨) |
| `place_mines(board, first_click)` | `minesweeper.py:163-166` | ✅ 완료 |
| `reveal_cell(board, row, col)` | `minesweeper.py:169-173` | ✅ 완료 (주의사항 있음) |
| `toggle_flag(board, row, col)` | `minesweeper.py:176-180` | ✅ 완료 |
| `check_game_state(board)` | `minesweeper.py:183-185` | ✅ 완료 |
| `render_board(board, reveal_all)` | `minesweeper.py:188-190` | ✅ 완료 (파라미터명 불일치 주의) |
| `parse_command(raw)` | `minesweeper.py:193-219` | ✅ 완료 |

### CLI 진입점 (Module 1 핵심)
| 구현체 | 위치 | 상태 |
|--------|------|------|
| `_parse_args` — argparse (`--mines`, `--seed`) | `minesweeper.py:224-234` | ✅ 완료 |
| `_handle_command` — 입력 한 줄 파싱 및 보드 적용 | `minesweeper.py:237-274` | ✅ 완료 |
| `main` — 전체 게임 루프 | `minesweeper.py:277-313` | ✅ 완료 |

### 검증 결과 (2026-05-08 기준)
- `py_compile`: **PASS**
- `pytest tests/`: **18/18 PASS**
- E2E 스모크: 보드 출력, 깃발 토글, quit 정상 종료, `--mines 0` → exit code 2

---

## 알려진 제약 및 이슈

### 🔴 잔존 BLOCK — mine_count 상한선 불일치

| 위치 | 내용 |
|------|------|
| `minesweeper.py:150` | `create_board()` — 상한선 **54**로 수정 완료 |
| `minesweeper.py:280` | `main()` — 상한선 **63** 그대로 남아 있음 |
| `minesweeper.py:229` | `argparse` help 문자열도 `'범위: 1~63'`으로 노출 |

**위험**: 사용자가 `--mines 56` 이상을 전달하면 `main()`이 허용하여 `Board`를 생성하고,  
첫 클릭이 중앙 부근일 경우 `place_mines`에서 `random.sample(candidates=55, k=56)` →  
`ValueError: Sample larger than population` 런타임 크래시가 발생한다.  
`mine_count 61~63`은 어떤 첫 클릭 위치에서도 반드시 크래시한다.

**수정 방법**: `minesweeper.py:280`의 조건과 `minesweeper.py:229`의 help 문자열을 `1~54`로 통일한다.

---

### ⚠️ WARN — Module 3 미구현 UI 갭

아래 항목은 `frontend_dev_module_3_scope_1`에서 이미 수정 계획이 수립되어 있으며,  
**Module 3 구현 작업자가 반드시 처리해야 한다.**

| ID | 위치 | 현재 구현 | ui-spec 계약 |
|----|------|-----------|--------------|
| CV-02 | `minesweeper.py:124-145` | `"{r} \| {셀들}"` (파이프 포함) | `"{r}  {셀들}"` (공백 2개) |
| CV-03 | `minesweeper.py:285-286` | `'8×8 지뢰찾기 시작! ...'` 인라인 | `지뢰찾기 8×8 [지뢰: N개]` 헤더 + 빈 줄 |
| CV-04 | `minesweeper.py:290` | `'명령> '` | `'명령 입력 (행 열 / f 행 열 / q): '` |

---

### ⚠️ WARN — Module 1 GAP: quit 종료 메시지 미출력

| ID | 위치 | 내용 |
|----|------|------|
| CV-05 | `minesweeper.py:157`, `minesweeper.py:297-298` | `MSG_QUIT = "게임을 종료합니다."` 상수가 정의됐지만 `q`/`quit` 입력 시 출력되지 않음 |

`if result == "QUIT": break` 직전에 `print(MSG_QUIT)` 한 줄 추가로 해소 가능.  
ui-spec §1.2 화면 F의 명시적 요구 사항이므로, Module 3 또는 빠른 패치로 처리 권장.

---

### ⚠️ WARN — 아키텍처 문서 계약 오류

| ID | 위치 | 내용 |
|----|------|------|
| CV-01 | `architecture.md:324` | `render_board` 파라미터명: 문서 `reveal_mines` vs 구현 `reveal_all` |
| CV-06 | `architecture.md:317` | `Board.reveal_cell` 반환 타입: 문서 `-> str` vs 구현 `-> None` |
| CV-07 | `architecture.md:160-165` | `Cell` 필드명: Backend Dev 섹션 `is_revealed`/`is_flagged` vs 구현 `revealed`/`flagged` |

기능 버그 없음. 아키텍처 문서 갱신 필요 (다음 `architecture.md` 수정 작업 시 처리).

---

### ⚠️ WARN — 코드 품질 이슈 (Module 3 작업 전 인지 필요)

| 위치 | 내용 |
|------|------|
| `minesweeper.py:187-219` vs `minesweeper.py:237-274` | `parse_command()`와 `_handle_command()` 입력 파싱 로직 중복 |
| `minesweeper.py:118-122` | `Board.check_win()` / `Board.check_lose()` — 데드 코드 (main 루프가 `board.state` 직접 비교) |
| `minesweeper.py:169-173` | 모듈 수준 `reveal_cell()`이 `board._reveal()` 직접 호출 — `place_mines` 선행 계약 미명시 |
| `minesweeper.py:176-180` vs `minesweeper.py:103-109` | 모듈 수준 `toggle_flag()`는 항상 `None` 반환, `Board.toggle_flag()`는 `str \| None` 반환 — 시그니처 불일치 |
| `minesweeper.py:11` vs `src/game_logic.py:25` | `GameState` 이름 충돌 — 통합 시 import 충돌 위험 |

---

## Module 2·3와의 연결 포인트

### Module 2 (지뢰 배치 및 셀 공개)

Module 2 범위의 구현이 **이미 `minesweeper.py` 안에 완료**되어 있다.  
Module 2 스코프 작업(`frontend_dev_module_2_scope_1`)은 경계와 인터페이스를 명문화하는 것이 목적이며,  
별도 파일 생성이나 코드 추가 없이 아래 시그니처를 기준 계약으로 사용한다.

| 인터페이스 | 파일:라인 | 계약 |
|-----------|----------|------|
| `Board.place_mines(safe_row, safe_col)` | `minesweeper.py:39` | 첫 클릭 + 8방향 안전 영역 제외 후 지뢰 배치 |
| `Board.reveal_cell(row, col)` | `minesweeper.py:77` | safe-first-click 래퍼 + 승리 체크 |
| `Board._reveal(row, col)` | `minesweeper.py:86` | 재귀 연쇄 공개 (내부 함수) |
| `Board._check_win()` | `minesweeper.py:111` | 비지뢰 전체 공개 시 WIN 전환 |
| `place_mines(board, first_click)` | `minesweeper.py:163` | 모듈 수준 래퍼 |
| `reveal_cell(board, row, col)` | `minesweeper.py:169` | 모듈 수준 래퍼 (`board._reveal` 직접 호출) |

> **주의**: 모듈 수준 `reveal_cell`은 `board._reveal`을 직접 호출하므로 `place_mines` 선행 필수.  
> `Board.reveal_cell` (메서드)은 자동으로 `place_mines`를 트리거하지만,  
> 모듈 수준 `reveal_cell` (함수)은 그렇지 않다.

### Module 3 (승리/패배 판정 및 보드 렌더링 출력)

Module 3 작업자는 아래 연결 지점에서 `minesweeper.py`를 수정한다.

| 연결 지점 | 현재 구현 | Module 3 수정 대상 |
|-----------|-----------|------------------|
| `render_board(board, reveal_all)` | `minesweeper.py:188` | 파라미터명 `reveal_all` → `reveal_mines`로 통일 (architecture.md 계약) |
| `Board.render` 행 포맷 | `"{r} \| {셀들}"` | `"{r}  {셀들}"` (파이프 제거, 공백 2개) |
| `main()` 헤더 | `'8×8 지뢰찾기 시작! ...'` | `'지뢰찾기 8×8 [지뢰: N개]'` 형식 |
| `main()` 입력 프롬프트 | `'명령> '` | `'명령 입력 (행 열 / f 행 열 / q): '` |
| `main()` WIN/LOSE 화면 | 상태 메시지만 출력 | 헤더 라인 + 구분선 추가 |
| `_handle_command` quit 처리 | `MSG_QUIT` 미출력 | `print(MSG_QUIT)` 추가 |

---

## 다음 작업자가 반드시 알아야 할 주의사항

### 1. 즉시 수정 필요 — mine_count 상한선 BLOCK

`minesweeper.py:280`의 `mines <= 63`을 `mines <= 54`로 수정하고,  
`minesweeper.py:229`의 argparse help 문자열도 동일하게 수정한다.  
`create_board()`와 `main()`이 동일한 상한선(54)을 사용해야 한다.

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

### 2. Module 3 작업 시 파라미터명 통일

`render_board` 함수의 파라미터명이 `reveal_all`(구현)과 `reveal_mines`(architecture.md) 간에 불일치한다.  
Module 3 작업 시 architecture.md의 `reveal_mines`로 통일하거나, architecture.md를 `reveal_all`로 갱신한다.  
테스트(`tests/test_minesweeper_unit.py`)가 `reveal_all=True`로 호출하므로, 변경 시 테스트도 함께 수정한다.

### 3. src/game_logic.py와의 병존 관계

`src/game_logic.py`에 `GameState` (frozen dataclass), `Cell`, 게임 로직 함수가 별도로 존재한다.  
현재 두 모듈은 서로 `import`하지 않는다.  
통합(module_3 이후)이 필요하면 어느 구현을 CLI 진입점으로 사용할지 먼저 결정한 후 진행한다.  
이름 충돌(`GameState` enum vs frozen dataclass)은 통합 시 `import` 충돌을 유발한다.

### 4. MSG_* 상수 활용

`minesweeper.py:155-158`에 `MSG_WIN`, `MSG_LOSE`, `MSG_QUIT`, `SEPARATOR` 상수가 정의되어 있다.  
게임 루프(`main()`)에서 이 상수 대신 인라인 문자열을 사용하는 부분이 있다.  
Module 3 수정 시 인라인 문자열을 이 상수로 교체하면 유지보수성이 향상된다.

---

## 참조 문서

| 문서 | 용도 |
|------|------|
| `minesweeper.py` | 구현 단일 진실 소스 |
| `docs/architecture.md §Frontend Dev Module 1` | Module 1 범위·인터페이스 정의 |
| `docs/architecture.md §Frontend Dev Module 2` | Module 2 범위·인터페이스 정의 |
| `docs/architecture.md §Frontend Dev Module 3` | Module 3 수정 범위 및 순서 |
| `docs/designer/ui-spec.md` | 모든 출력 형식의 단일 기준 |
| `docs/cross_validate/2026-05-08-frontend-dev-module-1-cross-validate.md` | 교차검증 WARN 상세 내용 (8건) |
| `docs/code_review/code-review.md` | backend_dev_code_reviewer BLOCK, frontend_dev_code_reviewer WARN 내용 |
| `docs/plans/2026-05-08-frontend-dev-module-3-scope.md` | Module 3 수정 계획 |
| `tests/test_minesweeper_unit.py` | 18개 단위 테스트 |

---

## Frontend Dev Module 1 완료 선언

`frontend_dev_module_1` 전체 단계(scope → build → cross_validate → verify)가 완료되었다.

- **핵심 기능 완료**: CLI 진입점·입력 파싱·게임 루프·데이터 모델·게임 로직 모두 구현
- **테스트**: 18/18 PASS
- **잔존 작업**:
  1. 🔴 mine_count 상한선 `63→54` 통일 (즉시 처리 권장)
  2. ⚠️ quit 종료 메시지 `MSG_QUIT` 출력 추가 (Module 3 또는 별도 패치)
  3. ⚠️ UI 형식 갭 7건 — `frontend_dev_module_3_build_2`에서 처리
