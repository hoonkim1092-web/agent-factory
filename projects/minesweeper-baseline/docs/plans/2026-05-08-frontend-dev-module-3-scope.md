# Frontend Dev — Module 3: 승리/패배 판정 및 보드 렌더링 출력 범위 정의

## 메타데이터

| 항목 | 값 |
|------|-----|
| task_id | `frontend_dev_module_3_scope_1` |
| 생성일 | `2026-05-08` |
| 작성 역할 | designer |
| 단계 | scope |
| 참조 문서 | `docs/designer/ui-spec.md`, `docs/architecture.md` |

---

## 1. 범위 (Scope)

Module 3는 `minesweeper.py`에서 **승리/패배 판정**과 **보드 ASCII 렌더링 출력**을 담당한다.

### 포함
- `render_board(board, reveal_mines)`: 게임 상태별 헤더·열 레이블·행 렌더링 문자열 생성
- `check_win(board)`: 모든 비지뢰 셀이 공개됐는지 판정
- `check_lose(board)`: 지뢰 셀이 공개됐는지 판정
- 셀 기호 매핑 (`?` / `F` / `.` / `1`~`8` / `*`)
- 게임 종료 메시지 문자열 상수 (`MSG_WIN`, `MSG_LOSE`, `MSG_QUIT`)
- 상태별 헤더 문자열 생성 (`_make_header`)

### 제외 (다른 모듈 담당)
| 기능 | 담당 |
|------|------|
| CLI 인수 파싱 (`_parse_args`) | frontend_dev Module 1 |
| 게임 루프 (`main`) | frontend_dev Module 1 |
| 입력 파싱 (`_handle_command`, `parse_command`) | frontend_dev Module 1 |
| 지뢰 배치 · 셀 공개 로직 | game_logic_dev |
| 단위 테스트 | qa_engineer |

---

## 2. 공개 인터페이스 (함수 시그니처)

### 2.1 `render_board`

```python
def render_board(board: Board, reveal_mines: bool = False) -> str:
    """
    보드를 UI spec(docs/designer/ui-spec.md §2) 형식의 ASCII 문자열로 반환한다.

    반환값 구조 (줄 순서):
      1. 헤더 라인  (_make_header 참조)
      2. 열 레이블: '   0 1 2 3 4 5 6 7'
      3. 행 0~7:   '{r}  {c0} {c1} {c2} {c3} {c4} {c5} {c6} {c7}'

    reveal_mines=True이면 미공개·미깃발 지뢰 셀을 '*'로 표시한다.
    구분선('--------------------')은 호출부(game_loop)가 상황에 맞게 출력한다.
    """
```

### 2.2 `_make_header` (내부 헬퍼)

```python
def _make_header(board: Board) -> str:
    """
    게임 상태에 따른 헤더 문자열을 반환한다.
      GameState.PLAYING  → '지뢰찾기 8×8 [지뢰: {mine_count}개]'
      GameState.WIN      → '지뢰찾기 8×8 [승리!]'
      GameState.LOSE     → '지뢰찾기 8×8 [게임 오버]'
    """
```

### 2.3 `check_win`

```python
def check_win(board: Board) -> bool:
    """
    모든 비지뢰 셀이 공개된 경우 True를 반환한다.
    board.state == GameState.WIN 과 동치.
    """
```

### 2.4 `check_lose`

```python
def check_lose(board: Board) -> bool:
    """
    지뢰 셀이 공개된(밟은) 경우 True를 반환한다.
    board.state == GameState.LOSE 과 동치.
    """
```

### 2.5 메시지 상수

```python
MSG_WIN  = "축하합니다! 승리했습니다."
MSG_LOSE = "게임 오버! 지뢰를 밟았습니다."
MSG_QUIT = "게임을 종료합니다."
SEPARATOR = "--------------------"  # 하이픈 20자
```

---

## 3. 셀 기호 매핑

| 조건 (우선순위 순) | 기호 |
|--------------------|------|
| `reveal_mines=True` AND `cell.is_mine` AND NOT `cell.flagged` | `*` |
| `cell.revealed` AND `cell.is_mine` | `*` |
| `cell.revealed` AND `cell.adjacent_count == 0` | `.` |
| `cell.revealed` AND `cell.adjacent_count >= 1` | `str(cell.adjacent_count)` (`1`~`8`) |
| `cell.flagged` | `F` |
| 그 외 (미공개) | `?` |

> 깃발이 설정된 셀은 패배 후(`reveal_mines=True`)에도 `F`를 유지한다. (ui-spec §3 기호 우선순위 규칙 1)

---

## 4. 렌더링 출력 형식

### 4.1 헤더 라인
```
지뢰찾기 8×8 [지뢰: 10개]     ← PLAYING 상태
지뢰찾기 8×8 [승리!]           ← WIN 상태
지뢰찾기 8×8 [게임 오버]       ← LOSE 상태
```

### 4.2 열 레이블 라인
```
   0 1 2 3 4 5 6 7
```
- 앞에 공백 3개

### 4.3 행 형식
```
{r}  {c0} {c1} {c2} {c3} {c4} {c5} {c6} {c7}
```
- `{r}`: 행 번호 (0~7), 뒤에 공백 2개
- 셀 기호는 공백 1개로 구분

### 4.4 구분선 (호출부 책임)
```
--------------------
```
- `render_board` 반환값에 포함하지 않는다.
- `game_loop`에서 첫 화면 이후 매 화면 출력 직전에 출력한다.

---

## 5. 현황 분석 — 기존 구현과 UI spec 간 갭

`minesweeper.py`에 이미 `Board.render()` 및 `render_board()` 구현이 있으나 아래 갭이 존재한다.

| 항목 | 현재 구현 | UI spec 요구 | 수정 필요 |
|------|-----------|--------------|-----------|
| 행 형식 | `{r} \| {셀들}` | `{r}  {셀들}` | ✅ 파이프(`\|`) 제거, 공백 2개로 변경 |
| 헤더 라인 | 없음 | 상태별 헤더 포함 | ✅ `_make_header` 추가 |
| 구분선 포함 여부 | 없음 | 호출부 책임 | ✅ 이미 올바름 (render에 포함 X) |
| 초기 화면 메시지 | `"8×8 지뢰찾기 시작!"` | 화면 A 포맷 (헤더+빈줄) | ✅ `main` 수정 필요 |
| `MSG_WIN/LOSE/QUIT` 상수 | 인라인 문자열 | 상수 정의 | 권장 (Module 1 테스트 안정화) |

> **주의**: `Board.render()`의 행 형식 수정 시 기존 테스트(`tests/test_minesweeper_unit.py`)에서 `|` 기호를 기대하는 테스트가 있을 수 있다. 수정 전 grep으로 확인한다.

---

## 6. 의존성

### 선행 의존성 (Module 3 구현 전 확정 필요)
| 의존 대상 | 제공 역할 | 상태 |
|-----------|-----------|------|
| `Board`, `Cell`, `GameState` | backend_dev | ✅ 완료 |
| `docs/designer/ui-spec.md` | designer | ✅ 완료 |
| `Board.cells`, `Board.state`, `Board.mine_count` | backend_dev + game_logic_dev | ✅ 완료 |

### 후행 의존성 (Module 3 완료 후 활성화)
| 소비자 | 사용 항목 | 용도 |
|--------|-----------|------|
| frontend_dev Module 1 (`game_loop`) | `render_board`, `check_win`, `check_lose`, `MSG_WIN`, `MSG_LOSE` | 게임 루프 종료 판정 및 출력 |
| qa_engineer | `render_board`, `check_win` | 수락 기준 AC-06, AC-07 검증 |

---

## 7. 산출물

| 파일 | 변경 내용 | 예상 LOC |
|------|-----------|---------|
| `minesweeper.py` | `Board.render()` 행 형식 수정, `_make_header` 추가, `render_board` 업데이트, `check_win`/`check_lose` 모듈 수준 함수 정비, 메시지 상수 추가 | +15~25 LOC |

---

## 8. 구현 순서 (Build 단계 고정)

```
1단계 — 메시지·구분선 상수 정의
  MSG_WIN, MSG_LOSE, MSG_QUIT, SEPARATOR
  검증: 문자열 리터럴 오탈자 없음

2단계 — _make_header(board) 구현
  검증: PLAYING/WIN/LOSE 상태별 헤더 문자열 반환 확인

3단계 — Board.render() 행 형식 수정 (파이프 → 공백 2개)
  검증: 기존 테스트의 render 관련 assertion 업데이트

4단계 — render_board() 헤더 통합
  검증: render_board(board) 반환값이 헤더+열레이블+8행 포함

5단계 — check_win / check_lose 모듈 수준 함수 정비
  검증: board.state == WIN → check_win() True, LOSE → check_lose() True

6단계 — main() 초기 화면 수정
  검증: 프로그램 시작 시 화면 A 포맷 출력 (빈줄+헤더+보드+빈줄+프롬프트)
```

각 단계는 독립 검증 가능하며, 3단계에서 기존 테스트 수정이 동반된다.

---

## 9. 열린 질문

1. `tests/test_minesweeper_unit.py`에서 `Board.render()` 출력을 직접 비교하는 테스트가 있는가? → build 단계 시작 전 grep 확인 필요.
2. `check_win`이 `board.state` 기반이면 Module 1에서 `board.check_win()` 대신 `check_win(board)` 호환성은 유지되는가? → 현재 구현(`Board.check_win()`)과 동치이므로 무방.
