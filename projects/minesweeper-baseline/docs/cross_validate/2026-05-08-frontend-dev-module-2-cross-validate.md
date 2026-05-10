# 교차검증 보고서 — frontend_dev_module_2

## 메타데이터

| 항목 | 값 |
|------|-----|
| task_id | `frontend_dev_module_2_cross_validate` |
| 검증 대상 | `minesweeper.py:39-173` (Board.place_mines, _calc_adjacent_counts, reveal_cell, _reveal, _check_win, 모듈 수준 place_mines/reveal_cell), `tests/test_minesweeper_unit.py` (슬라이스 2·3) |
| 검토 기준 문서 | `docs/architecture.md §Frontend Dev Module 2`, `docs/work-items/.../feature-spec.md`, `docs/code_review/code-review.md` |
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
      "id": "CV2-01",
      "location": "docs/code_review/code-review.md §Review — frontend_dev_module_2 vs docs/architecture.md:395-527",
      "description": "코드 리뷰 범위 오매핑. frontend_dev_module_2의 실제 구현 범위는 docs/architecture.md §Module 2에 따라 minesweeper.py:39-173(Board.place_mines, _calc_adjacent_counts, reveal_cell, _reveal, _check_win 및 모듈 수준 래퍼)이다. 그러나 frontend_dev_code_reviewer는 src/game_logic.py(game_logic_dev 산출물)를 대상 파일로 리뷰했다. 결과적으로 minesweeper.py의 Module 2 구현부는 frontend_dev_module_2 코드 리뷰의 공식 대상이 되지 않았다. 기능 BLOCK은 발생하지 않지만 문서 감사 경로가 불완전하다."
    },
    {
      "severity": "WARN",
      "id": "CV2-02",
      "location": "minesweeper.py:169-173 vs docs/architecture.md:454-455",
      "description": "모듈 수준 reveal_cell()이 Board.reveal_cell() 안전 래퍼를 우회한다. minesweeper.py:169의 모듈 수준 reveal_cell(board, row, col)은 board._reveal(row, col)을 직접 호출하며, Board.reveal_cell()이 제공하는 safe-first-click 가드(first_reveal_done 검사 및 place_mines 자동 호출)를 건너뛴다. 테스트 코드(test_minesweeper_unit.py)는 항상 place_mines()를 먼저 호출하기 때문에 테스트 레벨에서는 문제가 없지만, 모듈 공개 API 사용자가 place_mines() 없이 reveal_cell()만 호출하면 지뢰 미배치 상태에서 reveal이 실행되어 비지뢰 셀 전체가 즉시 WIN 판정될 수 있다. 호출 전제 계약이 docstring이나 assertion으로 보호되지 않음. backend_dev_code_reviewer, frontend_dev_code_reviewer 모두 동일 WARN 확인(기존 이슈 재확인)."
    },
    {
      "severity": "WARN",
      "id": "CV2-03",
      "location": "minesweeper.py:280 vs minesweeper.py:150-151",
      "description": "main()의 mine_count 상한선 불일치 미수정. create_board()는 mine_count <= 54로 올바르게 제한하지만, main()의 _parse_args 검증(minesweeper.py:280)은 여전히 mines <= 63을 허용한다. main()은 Board(mine_count=mines)를 직접 생성하여 create_board()의 54 한도를 우회하므로, mines=56~63 + 첫 클릭 위치에 따라 place_mines()의 random.sample이 ValueError로 크래시한다. 이 BLOCK은 backend_dev_code_reviewer에서 이미 판정됐으나 아직 해소되지 않았다. Module 2 교차검증 시점에서 선행 BLOCK으로 재확인."
    },
    {
      "severity": "WARN",
      "id": "CV2-04",
      "location": "tests/test_minesweeper_unit.py:119-126 (place_mines 안전 구역 검증 범위)",
      "description": "place_mines 안전 구역 테스트 범위 부족. test_place_mines_keeps_first_click_safe는 safe_click 셀(3,3) 자체에 지뢰가 없음만 검증한다. minesweeper.py:39의 place_mines는 첫 클릭의 8방향 인접 셀(최대 9칸)을 안전 영역으로 제외하는 확장 보장을 제공하지만, 인접 8칸에 지뢰가 없음을 검증하는 테스트가 없다. 이 보장이 깨져도 현재 테스트는 PASS한다."
    },
    {
      "severity": "WARN",
      "id": "CV2-05",
      "location": "tests/test_minesweeper_unit.py 전체 vs minesweeper.py:163-173",
      "description": "모듈 수준 reveal_cell() 호출 전제 계약 테스트 부재. place_mines() 없이 reveal_cell()만 호출한 경우의 동작(잘못된 WIN 판정 또는 빈 보드 오픈)을 검증하는 테스트가 없다. 설계 의도가 'place_mines 선행 필수'이지만 테스트로 강제되지 않는다. 또한 _check_win()이 비지뢰 셀이 남아 있을 때 PLAYING을 유지하는지 독립 테스트가 없다."
    },
    {
      "severity": "WARN",
      "id": "CV2-06",
      "location": "docs/architecture.md §Backend Dev 공개 인터페이스:160-165 vs minesweeper.py:17-22",
      "description": "Cell 필드명 아키텍처 문서 내 섹션 간 충돌 미수정. architecture.md Backend Dev 섹션은 is_revealed, is_flagged를 정의하나 Module 2 섹션 및 실제 구현(minesweeper.py:17-22)은 revealed, flagged를 사용한다. Module 1 교차검증(CV-07)에서 이미 WARN으로 등록됐으나 문서 갱신이 이루어지지 않았다."
    }
  ],
  "summary": "Module 2 핵심 기능(지뢰 배치, 인접 수 계산, 연쇄 공개, 승리/패배 판정) 정상 동작 확인. pytest 19/19 PASS. 신규 BLOCK 없음. 주요 WARN 6건: (1) 코드 리뷰가 src/game_logic.py를 대상으로 하여 minesweeper.py Module 2 구현부가 공식 리뷰 미포함, (2) 모듈 수준 reveal_cell()이 safe-first-click 가드 우회 — 호출 계약 미보호, (3) main()의 mine_count 63 한도 미수정(선행 BLOCK 미해소), (4) place_mines 8방향 안전 구역 테스트 범위 부족, (5) reveal_cell 호출 계약 테스트 부재, (6) Cell 필드명 문서 섹션 간 충돌 미수정. 모두 WARN 수준으로 Module 2 진행 가능."
}
```

---

## 검증 항목 상세

### 1. 모듈 간 인터페이스 일관성

| 인터페이스 | 문서 계약 (architecture.md §Module 2) | 실제 구현 | 판정 |
|-----------|--------------------------------------|-----------|------|
| `Board.place_mines(safe_row, safe_col) -> None` | `-> None`, 8방향 인접 제외 | minesweeper.py:39 일치 | PASS |
| `Board.reveal_cell(row, col) -> None` | `-> None`, first_reveal_done 가드 | minesweeper.py:77 일치 | PASS |
| `Board._reveal(row, col) -> None` | 재귀 공개, flagged 무시, LOSE 전환 | minesweeper.py:86 일치 | PASS |
| `Board._check_win() -> None` | 비지뢰 전부 공개 시 WIN | minesweeper.py:111 일치 | PASS |
| `place_mines(board, first_click)` 모듈 함수 | `-> None`, first_reveal_done=True 설정 | minesweeper.py:163-166 일치 | PASS |
| `reveal_cell(board, row, col)` 모듈 함수 | board.reveal_cell() 래퍼 역할 기대 | board._reveal() 직접 호출 — safe-first-click 우회 | WARN (CV2-02) |
| `Cell.revealed` / `Cell.flagged` 필드명 | Module 2 spec `revealed`/`flagged` ✅, Backend Dev spec `is_revealed`/`is_flagged` ❌ | `revealed`/`flagged` | WARN (CV2-06) |

### 2. 설계 문서와 구현의 괴리

| 항목 | 설계 요구 | 현재 구현 | 판정 |
|------|-----------|-----------|------|
| place_mines 안전 영역 범위 | 첫 클릭 + 8방향 (architecture §Module 2) | 8방향 포함 구현 (minesweeper.py:44-55) ✅ | PASS |
| _reveal 재귀 방식 | 재귀 (architecture §Module 2, BFS 대안 채택 안 함) | 재귀 구현 ✅ | PASS |
| mine_count 상한선 create_board | ≤ 54 (backend BLOCK 수정 반영) | minesweeper.py:150 `<= 54` ✅ | PASS |
| mine_count 상한선 main() | ≤ 55 (place_mines 안전 구역 보장) | minesweeper.py:280 `<= 63` ❌ | WARN (CV2-03) |
| 코드 리뷰 대상 파일 | minesweeper.py:39-173 (Module 2 범위) | src/game_logic.py 리뷰 — 오매핑 | WARN (CV2-01) |

### 3. 테스트 커버리지 갭

| 시나리오 | 테스트 존재 여부 | 비고 |
|---------|----------------|------|
| 첫 클릭 셀 지뢰 제외 | ✅ `test_place_mines_keeps_first_click_safe` | 셀 자체만 검증 |
| 첫 클릭 8방향 인접 셀 지뢰 제외 | ❌ 미테스트 | 안전 구역 확장 보장 불검증 (CV2-04) |
| 연쇄 공개 (cascade) | ✅ `test_reveal_cell_cascade_on_zero_adjacent` | - |
| 깃발 셀 공개 무시 | ✅ `test_reveal_cell_skips_flagged_cell` | - |
| LOSE 상태 전환 | ✅ `test_check_game_state_lose_after_revealing_mine` | - |
| WIN 상태 전환 | ✅ `test_check_game_state_win_when_all_safe_revealed` | - |
| _check_win PLAYING 유지 (비지뢰 남음) | ❌ 미테스트 (CV2-05) | 메서드 단독 검증 없음 |
| 모듈 수준 reveal_cell 호출 전 place_mines 미호출 시 동작 | ❌ 미테스트 (CV2-05) | 잘못된 WIN 판정 위험 무방비 |
| _calc_adjacent_counts 정확도 독립 검증 | ❌ 미테스트 | 연쇄 공개 테스트에서 간접 검증만 됨 |

### 4. 의존성 그래프 정합성

| 의존성 항목 | 예상 | 실제 | 판정 |
|------------|------|------|------|
| `random` stdlib | 사용 | minesweeper.py:6 ✅ | PASS |
| 외부 패키지 | 없음 | 없음 ✅ | PASS |
| `src/game_logic.py` ↔ `minesweeper.py` 교차 import | 없음 (별도 구현체) | import 없음 ✅ | PASS (INFO: 미연결) |
| Module 2 → Module 3 의존성 | 없어야 함 | Module 2 함수가 render/check_win 미호출 ✅ | PASS |

> **INFO**: `src/game_logic.py`(game_logic_dev)와 `minesweeper.py`(frontend_dev)는 각각 독립적인 게임 로직 구현체로 공존하며, 현재 상호 연결되지 않는다. Module 3 통합 시 CLI 진입점이 어느 구현체를 사용할지 명시적 결정이 필요하다.

### 5. 문서 업데이트 누락

| 문서 | 누락 항목 | 우선순위 |
|------|---------|---------|
| `docs/architecture.md §Backend Dev 공개 인터페이스:160-165` | `is_revealed`/`is_flagged` → `revealed`/`flagged`로 수정 필요 | WARN |
| `docs/architecture.md §Module 1 소비 인터페이스:317` | `reveal_cell -> str` → `-> None`으로 수정 필요 | WARN |
| `docs/code_review/code-review.md §Review — frontend_dev_module_2` | 대상 파일이 `src/game_logic.py`로 잘못 기록됨. Module 2 실제 범위는 `minesweeper.py:39-173` | WARN |

---

## 판정 요약

- **BLOCK**: 없음 (신규 발견 기준)
  - mine_count main() 상한선 BLOCK은 backend_dev_code_reviewer에서 이미 판정됨 — 선행 해결 필요
- **WARN**: 6건
  - CV2-01: 코드 리뷰 범위 오매핑 (src/game_logic.py 리뷰 — Module 2 실제 범위는 minesweeper.py)
  - CV2-02: 모듈 수준 `reveal_cell()`이 safe-first-click 가드 우회 (기존 WARN 재확인)
  - CV2-03: `main()` mine_count 63 한도 미수정 (선행 BLOCK 미해소)
  - CV2-04: `place_mines` 8방향 안전 구역 테스트 범위 부족
  - CV2-05: 모듈 수준 `reveal_cell()` 호출 계약 테스트 부재
  - CV2-06: Cell 필드명 아키텍처 문서 섹션 간 충돌 미수정 (기존 WARN CV-07 재확인)
- **진행 가능**: Module 2 핵심 기능(지뢰 배치, 연쇄 공개, 승패 판정) 정상 동작. 19/19 테스트 PASS.
