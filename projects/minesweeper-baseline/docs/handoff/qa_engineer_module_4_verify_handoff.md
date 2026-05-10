# QA Engineer Module 4 검증 완료 Handoff 메모

## 메타데이터

| 항목 | 값 |
|------|-----|
| task_id | `qa_engineer_module_4_verify_3` |
| 작성일 | 2026-05-08 |
| 작성 역할 | qa_engineer |
| 검증 대상 | `tests/test_minesweeper_unit.py`, `tests/test_game_logic.py`, `tests/conftest.py` |
| 최종 판정 | **PASS** |

---

## 테스트 스위트 전체 결과

```bash
pytest tests/ -v
```

```
tests/test_game_logic.py::test_create_game_keeps_first_click_safe         PASS
tests/test_game_logic.py::test_open_mine_transitions_to_lost              PASS
tests/test_game_logic.py::test_toggle_flag_works_only_for_closed_cells    PASS
tests/test_game_logic.py::test_cascade_open_opens_neighbors_for_zero_adjacent PASS
tests/test_game_logic.py::test_win_transition_when_all_safe_opened        PASS
tests/test_minesweeper_unit.py::test_create_board_defaults                PASS
tests/test_minesweeper_unit.py::test_create_board_rejects_invalid_mine_count PASS
tests/test_minesweeper_unit.py::test_create_board_rejects_mine_count_above_safe_limit PASS
tests/test_minesweeper_unit.py::test_parse_command_reveal                 PASS
tests/test_minesweeper_unit.py::test_parse_command_flag                   PASS
tests/test_minesweeper_unit.py::test_parse_command_rejects_invalid        PASS
tests/test_minesweeper_unit.py::test_place_mines_keeps_first_click_safe   PASS
tests/test_minesweeper_unit.py::test_reveal_cell_skips_flagged_cell       PASS
tests/test_minesweeper_unit.py::test_reveal_cell_cascade_on_zero_adjacent PASS
tests/test_minesweeper_unit.py::test_toggle_flag_toggles_state            PASS
tests/test_minesweeper_unit.py::test_check_game_state_lose_after_revealing_mine PASS
tests/test_minesweeper_unit.py::test_check_game_state_win_when_all_safe_revealed PASS
tests/test_minesweeper_unit.py::test_render_board_returns_ascii_grid      PASS
tests/test_minesweeper_unit.py::test_render_board_reveal_all_shows_mine_symbol PASS

============================== 19 passed in 0.13s ==============================
```

---

## AC-10 검증

`feature-spec.md AC-10` 요구사항 달성 여부:

| 시나리오 | 테스트 | 판정 |
|---------|--------|------|
| `adjacent_count` 정확성 | `test_create_game_keeps_first_click_safe` (간접 검증), `test_cascade_open_opens_neighbors_for_zero_adjacent` | ✅ |
| 재귀 공개 경계 안전성 | `test_reveal_cell_cascade_on_zero_adjacent` — mine_count=1, (7,7) 공개 → 1개 이상 연쇄 공개 확인 | ✅ |
| safe-first-click 보장 | `test_place_mines_keeps_first_click_safe` — (3,3) 첫 클릭 시 지뢰 배치 제외 확인 | ✅ |
| WIN 상태 전환 | `test_check_game_state_win_when_all_safe_revealed`, `test_win_transition_when_all_safe_opened` | ✅ |
| LOSE 상태 전환 | `test_check_game_state_lose_after_revealing_mine`, `test_open_mine_transitions_to_lost` | ✅ |

---

## 단위 테스트 스위트 구성 현황

### tests/test_minesweeper_unit.py (14개)

| 슬라이스 | 테스트 | 검증 대상 |
|---------|--------|---------|
| 슬라이스 1 (초기화/파싱) | `test_create_board_defaults` | 8×8 보드 생성, mine_count=10 기본값 |
| | `test_create_board_rejects_invalid_mine_count` | mine_count=0/64 거부 |
| | `test_create_board_rejects_mine_count_above_safe_limit` | mine_count=55 크래시 방지, 54 경계 정상 |
| | `test_parse_command_reveal` | `"3 4"` → `("r", 3, 4)` |
| | `test_parse_command_flag` | `"f 2 5"` → `("f", 2, 5)` |
| | `test_parse_command_rejects_invalid` | 6종 잘못된 입력 거부 확인 |
| 슬라이스 2 (첫 클릭 안전) | `test_place_mines_keeps_first_click_safe` | 첫 클릭 셀 지뢰 없음 + 지뢰 총 수 10 |
| 슬라이스 3 (공개/연쇄) | `test_reveal_cell_skips_flagged_cell` | 깃발 셀 공개 무시 |
| | `test_reveal_cell_cascade_on_zero_adjacent` | 빈 셀 연쇄 공개 (1개 이상) |
| 슬라이스 4 (깃발/상태) | `test_toggle_flag_toggles_state` | 토글 ON/OFF |
| | `test_check_game_state_lose_after_revealing_mine` | LOSE 상태 전환 |
| | `test_check_game_state_win_when_all_safe_revealed` | WIN 상태 전환 |
| 슬라이스 5 (렌더링) | `test_render_board_returns_ascii_grid` | ASCII 보드 출력 (0~7 행/열, `?` 포함) |
| | `test_render_board_reveal_all_shows_mine_symbol` | `reveal_all=True` 시 `*` 표시 |

### tests/test_game_logic.py (5개)

| 테스트 | 검증 대상 |
|--------|---------|
| `test_create_game_keeps_first_click_safe` | `createGame` safe-first-click |
| `test_open_mine_transitions_to_lost` | `openCell` LOSE 전환 |
| `test_toggle_flag_works_only_for_closed_cells` | `toggleFlag` 미공개 셀 전용 |
| `test_cascade_open_opens_neighbors_for_zero_adjacent` | BFS 연쇄 공개 9칸 전체 |
| `test_win_transition_when_all_safe_opened` | WIN 전환 |

---

## 테스트 설계 특이사항

- **mock 없음**: 모든 테스트가 실제 `minesweeper.py`/`src/game_logic.py` 구현에 대해 실행된다.
- **dict/객체 이중 지원**: `_get`, `_cell_get` 헬퍼로 Board가 dict/객체 어느 형태여도 동작하도록 작성됨.
- **동적 모듈 로드**: `importlib.import_module("minesweeper")`를 사용해 모듈 경로 독립성 유지.

---

## 잔여 WARN (기능 영향 없음)

| WARN | 내용 |
|------|------|
| W-01 | `test_game_logic.py` — `won`/`lost` 상태 no-op, 범위 초과 ValueError, 경계값(mineCount=0/max) 미테스트 |
| W-02 | `test_minesweeper_unit.py` — 출력 문자 세부 규약(`■` vs `?`, `' '` vs `.`)을 강제하는 테스트 없음 |

---

## 다음 작업자에게

- 현재 테스트 스위트는 기능 정확성을 충분히 커버한다.
- W-01/W-02 추가 커버리지는 릴리스 전 요구사항 규약 확정 후 작성 권장.
- 전체 테스트 실행: `pytest tests/` → **19/19 PASS**
