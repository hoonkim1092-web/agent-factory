# 교차검증 보고서 — frontend_dev_module_1

## 메타데이터

| 항목 | 값 |
|------|-----|
| task_id | `frontend_dev_module_1_cross_validate` |
| 검증 대상 | `minesweeper.py`, `tests/test_minesweeper_unit.py` |
| 검토 기준 문서 | `docs/architecture.md`, `docs/designer/ui-spec.md`, `docs/work-items/.../feature-spec.md`, `docs/code_review/code-review.md` |
| 검증 역할 | frontend_dev_cross_validator |
| 생성일 | 2026-05-08 |
| 판정 | **WARN** |

---

## 판정 JSON

```json
{
  "verdict": "WARN",
  "issues": [
    {
      "severity": "WARN",
      "id": "CV-01",
      "location": "minesweeper.py:182 vs docs/architecture.md:324",
      "description": "`render_board` 파라미터명 불일치. 아키텍처 문서(Module 1 소비 인터페이스)는 `render_board(board: Board, reveal_mines: bool = False)`를 정의하나, 실제 구현은 `reveal_all: bool = False`를 사용한다. 테스트(`test_minesweeper_unit.py:196`)도 `reveal_all=True` 키워드로 호출하므로 구현-테스트 간 정합은 유지되나 아키텍처 계약 문서가 틀렸다. 아키텍처 문서 갱신 또는 구현 파라미터명 통일 필요."
    },
    {
      "severity": "WARN",
      "id": "CV-02",
      "location": "minesweeper.py:124-145 vs docs/designer/ui-spec.md §2.3",
      "description": "보드 행 렌더링 형식 미수정. ui-spec §2.3은 `{r}  {c0} {c1}...` (행 번호 + 공백 2개 + 셀 공백 구분) 형식을 요구하나, 현재 구현은 `{r} | {c0} {c1}...` (파이프 문자 포함) 형식을 사용한다. architecture.md(Module 3 scope §기존 구현 갭)에서 이 수정을 Module 3 담당으로 명시하고 있으나 아직 미구현 상태다. Module 3 구현 전까지 AC-06, AC-07 수락 기준 충족 불가."
    },
    {
      "severity": "WARN",
      "id": "CV-03",
      "location": "minesweeper.py:279-280 vs docs/designer/ui-spec.md §1.2 화면 A",
      "description": "초기 화면(화면 A) 형식 미구현. ui-spec은 `(빈 줄) → 지뢰찾기 8×8 [지뢰: N개] → 열 레이블 → 8행 보드 → (빈 줄) → 프롬프트` 순서를 요구한다. 현재 구현은 `'8×8 지뢰찾기 시작! ...'` 인라인 문자열 + `board.render()` 출력 후 `'명령> '` 프롬프트를 사용한다. 헤더 라인, 빈 줄, 프롬프트 문자열 모두 ui-spec과 불일치한다. Module 3 구현 범위이나 Module 3 미구현 상태."
    },
    {
      "severity": "WARN",
      "id": "CV-04",
      "location": "minesweeper.py:284 vs docs/designer/ui-spec.md §5.1",
      "description": "입력 프롬프트 문자열 불일치. ui-spec은 `'명령 입력 (행 열 / f 행 열 / q): '`를 요구하나, 현재 구현은 `'명령> '`를 사용한다. Module 3 담당 범위이나 Module 1 코드에 인라인으로 정의되어 있어 Module 3 구현 시 충돌 가능성."
    },
    {
      "severity": "WARN",
      "id": "CV-05",
      "location": "minesweeper.py:291 vs docs/designer/ui-spec.md §1.2 화면 F",
      "description": "quit 종료 메시지 미출력. ui-spec §화면 F는 `q`/`quit` 입력 시 `'게임을 종료합니다.'` 출력을 요구하나, 현재 구현은 메시지 없이 break한다. Module 1 범위(게임 루프)이므로 Module 1에서 수정이 필요한 GAP."
    },
    {
      "severity": "WARN",
      "id": "CV-06",
      "location": "docs/architecture.md §Frontend Dev Module 1 공개 인터페이스:317",
      "description": "아키텍처 문서 내 `Board.reveal_cell` 반환 타입 오류. architecture.md(Module 1 소비 인터페이스)는 `reveal_cell(self, row, col) -> str` ('mine'|'already_revealed'|'flagged'|'ok')를 정의하나, 실제 구현(`minesweeper.py:77`)은 `-> None`을 반환한다. `_handle_command`가 `board.reveal_cell(r, c)` 반환값을 무시하고 `board.state`를 직접 확인하므로 기능 버그는 없지만 문서 계약이 구현과 불일치한다."
    },
    {
      "severity": "WARN",
      "id": "CV-07",
      "location": "docs/architecture.md §Backend Dev 공개 인터페이스:160-165 vs minesweeper.py:17-22",
      "description": "Cell 필드명 양방 불일치. architecture.md Backend Dev 섹션은 `is_revealed: bool`, `is_flagged: bool`을 공식 API로 정의하나, Module 2 섹션과 실제 구현은 `revealed: bool`, `flagged: bool`을 사용한다. 동일 문서 내 두 섹션 간 계약이 충돌한다. 테스트는 `revealed`/`flagged`를 사용하므로 기능 정합은 유지되나 아키텍처 문서 갱신 필요."
    },
    {
      "severity": "WARN",
      "id": "CV-08",
      "location": "minesweeper.py:150-151 (mine_count 상한선 63)",
      "description": "mine_count 상한선 63이 실제 place_mines 후보 셀(최소 55개)을 초과하는 BLOCK 이슈가 backend_dev_code_reviewer에서 이미 BLOCK 판정됨. 이 이슈가 해소되지 않으면 Module 1 게임 루프도 동일 RuntimeError에 노출된다. frontend_dev_module_1 범위에서 추가 BLOCK 판정하지 않으나 선행 해결 필요."
    }
  ],
  "summary": "BLOCK 판정 기준에 해당하는 신규 이슈 없음. frontend_dev_module_1(진입점·입력 파싱·게임 루프) 핵심 로직은 동작하며 18/18 테스트 PASS 확인됨. 주요 WARN 8건: (1) render_board 파라미터명 아키텍처 불일치, (2) 행 렌더링 형식 파이프→공백 미전환(Module 3 담당), (3) 초기 화면 A 형식 미구현(Module 3 담당), (4) 프롬프트 문자열 불일치(Module 3 담당), (5) quit 종료 메시지 미출력(Module 1 GAP — ui-spec과 직접 충돌), (6) reveal_cell 반환 타입 문서 오류, (7) Cell 필드명 문서 섹션 간 충돌, (8) mine_count BLOCK 선행 해결 필요. Module 3 미구현 이슈(CV-02, CV-03, CV-04)는 별도 TODO로 관리 중이므로 Module 1 단독 진행 가능. CV-05(quit 메시지)는 Module 1 GAP으로 Module 3 구현 시 포함하거나 별도 수정 필요."
}
```

---

## 검증 항목 상세

### 1. 모듈 간 인터페이스 일관성

| 인터페이스 | 문서 계약 | 실제 구현 | 판정 |
|-----------|-----------|-----------|------|
| `render_board` 파라미터명 | `reveal_mines` (architecture.md) | `reveal_all` (minesweeper.py:182) | WARN (CV-01) |
| `Board.reveal_cell` 반환 | `str` ('mine'\|'ok' 등) | `None` | WARN (CV-06) |
| `Board.toggle_flag` 반환 | `str\|None` (architecture.md) | `str\|None` (구현 일치) | PASS |
| `Cell.revealed` 필드명 | `is_revealed` (Backend Dev 섹션) | `revealed` (구현, Module 2 섹션) | WARN (CV-07) |
| `check_game_state` 반환 | 명세 없음 (모듈 함수) | `'PLAYING'\|'WIN'\|'LOSE'` | PASS |

### 2. 설계 문서와 구현의 괴리

| 항목 | ui-spec / architecture.md 요구 | 현재 구현 |
|------|-------------------------------|-----------|
| 보드 행 형식 | `{r}  {셀들}` (공백 2개) | `{r} \| {셀들}` (파이프) |
| 초기 화면 헤더 | `지뢰찾기 8×8 [지뢰: N개]` | `8×8 지뢰찾기 시작! ...` 인라인 |
| 입력 프롬프트 | `명령 입력 (행 열 / f 행 열 / q): ` | `명령> ` |
| quit 종료 메시지 | `게임을 종료합니다.` | 미출력 (break만) |
| 턴 구분선 | `--------------------` (20자) | 미출력 |

> 보드 행 형식, 구분선, 헤더는 Module 3 담당으로 별도 TODO 존재. quit 메시지(CV-05)는 Module 1 게임 루프 GAP.

### 3. 테스트 커버리지 갭

| 시나리오 | 테스트 존재 여부 | 비고 |
|---------|----------------|------|
| 첫 클릭 안전 보장 | ✅ `test_place_mines_keeps_first_click_safe` | - |
| 연쇄 공개 (cascade) | ✅ `test_reveal_cell_cascade_on_zero_adjacent` | - |
| LOSE 상태 전환 | ✅ `test_check_game_state_lose_after_revealing_mine` | - |
| WIN 상태 전환 | ✅ `test_check_game_state_win_when_all_safe_revealed` | - |
| 깃발 토글 | ✅ `test_toggle_flag_toggles_state` | - |
| 공개 셀 깃발 설정 시도 | ❌ 미테스트 | EX-04 시나리오 |
| quit/q 입력 처리 | ❌ 미테스트 | _handle_command 경로 |
| EOFError/KeyboardInterrupt 처리 | ❌ 미테스트 | main() 게임 루프 |
| mine_count 경계값 (--mines 0, --mines 64) | ❌ E2E 미테스트 | create_board 레벨만 테스트 |

### 4. 의존성 그래프 정합성

- `argparse` 사용: feature-spec NFR-01에 `random`, `sys`, `os`만 명시하나 argparse는 stdlib이므로 기능 위반 없음. 스펙 문서 갱신 권장.
- Module 1 → Module 3 의존성: `render_board`, `check_win` 호출 계약이 파라미터명 불일치로 불안정 (CV-01).
- Module 1 → game_logic_dev 의존성: `Board.reveal_cell` 반환 타입 계약 불일치 (CV-06), 실제 동작에 영향 없음.

### 5. 문서 업데이트 누락

| 문서 | 누락 항목 |
|------|---------|
| `docs/architecture.md` §Module 1 소비 인터페이스 | `reveal_cell` 반환 타입 `str` → `None`으로 수정 필요 |
| `docs/architecture.md` §Module 1 소비 인터페이스 | `render_board` 파라미터명 `reveal_mines` → `reveal_all`로 수정 필요 |
| `docs/architecture.md` §Backend Dev 공개 인터페이스 | `is_revealed`/`is_flagged` → `revealed`/`flagged`로 수정 필요 (Module 2 섹션과 통일) |

---

## 판정 요약

- **BLOCK**: 없음 (신규 발견 기준)
  - mine_count 상한선 BLOCK은 backend_dev_code_reviewer에서 이미 판정됨 — 선행 해결 필요
- **WARN**: 8건
  - CV-01: `render_board` 파라미터명 문서-구현 불일치
  - CV-02: 보드 행 형식 파이프→공백 미전환 (Module 3 담당)
  - CV-03: 초기 화면 A 형식 미구현 (Module 3 담당)
  - CV-04: 프롬프트 문자열 불일치 (Module 3 담당)
  - CV-05: quit 종료 메시지 미출력 (Module 1 GAP)
  - CV-06: `Board.reveal_cell` 반환 타입 문서 오류
  - CV-07: `Cell` 필드명 문서 섹션 간 충돌
  - CV-08: mine_count BLOCK 미해결 선행 조건
- **진행 가능**: Module 1 핵심 기능(입력 파싱, 게임 루프) 정상 동작. Module 3 구현 후 UI 갭 해소 예상.
