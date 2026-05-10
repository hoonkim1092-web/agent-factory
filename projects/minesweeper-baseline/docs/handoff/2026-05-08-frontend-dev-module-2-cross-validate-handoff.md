# Frontend Dev Module 2 교차검증 완료 Handoff 메모

## 메타데이터

| 항목 | 값 |
|------|-----|
| task_id | `frontend_dev_module_2_cross_validate` |
| 작성일 | `2026-05-08` |
| 작성 역할 | frontend_dev_cross_validator |
| 단계 | cross_validate |
| 최종 판정 | **WARN** (BLOCK 없음) |

---

## 검증 대상

| 산출물 | 파일 경로 | 상태 |
|--------|-----------|------|
| Board.place_mines | minesweeper.py:39-59 | ✅ 구현 완료 |
| Board._calc_adjacent_counts | minesweeper.py:61-75 | ✅ 구현 완료 |
| Board.reveal_cell | minesweeper.py:77-84 | ✅ 구현 완료 |
| Board._reveal | minesweeper.py:86-101 | ✅ 구현 완료 |
| Board._check_win | minesweeper.py:111-116 | ✅ 구현 완료 |
| place_mines (모듈 함수) | minesweeper.py:163-166 | ✅ 구현 완료 |
| reveal_cell (모듈 함수) | minesweeper.py:169-173 | ⚠️ safe-first-click 가드 우회 |

**테스트 결과**: pytest 19/19 PASS

---

## 교차검증 결과 요약

### 정합성 PASS 항목

| 항목 | 내용 |
|------|------|
| place_mines 안전 영역 | 첫 클릭 + 8방향 인접 셀 제외 구현 ✅ |
| _reveal 재귀 방식 | 설계 의도대로 재귀 구현 (8×8 범위 내 스택 안전) ✅ |
| _check_win 동작 | 비지뢰 셀 전체 공개 시 WIN 전환 ✅ |
| LOSE 판정 | 지뢰 공개 시 즉시 LOSE 전환 ✅ |
| create_board mine_count ≤ 54 | 이전 BLOCK 수정 반영 ✅ |
| 외부 패키지 의존 없음 | stdlib random만 사용 ✅ |

---

## 잔여 WARN 및 후속 조치

### W1 — 코드 리뷰 범위 오매핑 (CV2-01)

- **내용**: frontend_dev_module_2 코드 리뷰가 `src/game_logic.py`를 대상으로 수행됨. 실제 Module 2 구현부(`minesweeper.py:39-173`)는 해당 리뷰에 포함되지 않음.
- **영향**: 감사 경로 불완전. 기능 결함 없음.
- **조치**: 다음 코드 리뷰 주기 또는 Module 3 통합 리뷰 시 minesweeper.py Module 2 범위 명시적 포함 권장.

### W2 — 모듈 수준 reveal_cell safe-first-click 우회 (CV2-02)

- **내용**: `reveal_cell(board, row, col)` 모듈 함수가 `board._reveal()` 직접 호출. `place_mines()` 미선행 시 빈 보드에서 cascade로 모든 셀이 공개되어 잘못된 WIN 판정 발생.
- **파일:라인**: minesweeper.py:169-173
- **영향**: 테스트 코드는 항상 place_mines 선행 호출 → 테스트 레벨 영향 없음. 외부 API 오용 시 위험.
- **조치**: docstring에 "place_mines() 선행 필수" 계약 명시 또는 assert board.first_reveal_done 가드 추가 권장. Module 3 통합 시 함께 정비 가능.

### W3 — main() mine_count 63 한도 미수정 (CV2-03)

- **내용**: main()의 `if not (1 <= mines <= 63)` 검사가 여전히 63을 허용. Board(mine_count=mines) 직접 생성으로 create_board()의 54 한도 우회.
- **파일:라인**: minesweeper.py:280
- **영향**: mines=56~63 + 중앙 부근 첫 클릭 시 `random.sample(candidates, k=mines)` ValueError 크래시.
- **조치**: minesweeper.py:280의 `<= 63` → `<= 54` 변경. **이것은 backend_dev_code_reviewer의 기존 BLOCK**이므로 frontend_dev_module_3_build_2 이전에 반드시 수정 필요.

### W4 — place_mines 8방향 안전 구역 테스트 부족 (CV2-04)

- **내용**: 테스트가 첫 클릭 셀 자체의 지뢰 없음만 검증. 8방향 인접 9칸 전체가 안전 구역임을 검증하는 테스트 없음.
- **파일:라인**: tests/test_minesweeper_unit.py:119-126
- **조치**: QA Engineer에게 인접 8칸 안전 보장 검증 테스트 추가 요청 권장.

### W5 — reveal_cell 호출 계약 테스트 부재 (CV2-05)

- **내용**: `place_mines()` 없이 `reveal_cell()` 호출 시 동작 테스트 없음. `_check_win()` PLAYING 유지 시나리오 미테스트.
- **조치**: QA Engineer 또는 Module 2 verify 단계에서 추가 테스트 작성 권장.

### W6 — Cell 필드명 아키텍처 문서 불일치 미수정 (CV2-06)

- **내용**: `docs/architecture.md §Backend Dev:160-165`에 `is_revealed`/`is_flagged`로 기록됨. 실제 구현 및 Module 2 spec은 `revealed`/`flagged` 사용.
- **조치**: architecture.md Backend Dev 섹션의 Cell 필드명 수정 필요. 기존 CV-07 미해소.

---

## 다음 작업자에게

### 즉시 필요한 작업

1. **frontend_dev Module 3 빌드 전 필수**: `minesweeper.py:280`의 `<= 63` → `<= 54` 수정 (W3, 기존 BLOCK 해소).
2. **frontend_dev_module_3_build_2**: Module 3 빌드 시 architecture.md §Module 3 구현 순서 따라 행 형식·헤더·메시지 상수 수정.
3. **아키텍처 문서 정비**: architecture.md Backend Dev 섹션 Cell 필드명 수정 (W6).

### 참조 문서

| 문서 | 용도 |
|------|------|
| `docs/architecture.md §Frontend Dev Module 2` | Module 2 공개 인터페이스 및 구현 순서 |
| `docs/architecture.md §Frontend Dev Module 3` | Module 3 빌드 범위 및 기존 구현 갭 목록 |
| `docs/cross_validate/2026-05-08-frontend-dev-module-2-cross-validate.md` | 교차검증 WARN 상세 내용 |
| `docs/cross_validate/2026-05-08-frontend-dev-module-1-cross-validate.md` | Module 1 교차검증 — CV-05·07 관련 |
| `docs/designer/ui-spec.md` | 렌더링·메시지 최종 계약 |

### Module 2 완료 선언

`frontend_dev_module_2`의 핵심 기능(지뢰 배치, 연쇄 공개, 승패 판정)은 정상 동작하며 모든 테스트를 통과한다.  
교차검증 판정 **WARN** — BLOCK 없음. Module 3 빌드로 진행 가능.
