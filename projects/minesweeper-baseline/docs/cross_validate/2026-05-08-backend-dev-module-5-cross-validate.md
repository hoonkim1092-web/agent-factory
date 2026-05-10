# backend_dev_module_5 교차검증 보고서

- 작성일: 2026-05-08
- 검증자: backend_dev_cross_validator
- 작업 ID: backend_dev_module_5_cross_validate
- 최종 판정: **BLOCK**

---

## 검토 범위

- `minesweeper.py` (Backend Dev 산출물: `GameState`, `Cell`, `Board.__init__`, `create_board`)
- `docs/architecture.md` (§Backend Dev 구현 범위 / 공개 인터페이스 명세)
- `docs/implementation-design.md` (mine_count 상한 스펙)
- `tests/test_minesweeper_unit.py` (Backend Dev 산출물 대상 테스트)
- `docs/code_review/code-review.md` (선행 코드 리뷰 결과)
- `docs/change_history.md` (구현 이력)

---

## 판정 JSON

```json
{
  "verdict": "BLOCK",
  "issues": [
    {
      "category": "인터페이스",
      "severity": "BLOCK",
      "description": "minesweeper.py의 create_board()와 main()이 mine_count 상한선을 63으로 검증하나, place_mines()는 첫 클릭 셀 + 8방향 인접 최대 9칸을 안전구역으로 제외해 후보 셀이 최소 55개로 줄어든다. mine_count=56+ + 중앙 클릭 시 random.sample(candidates=55, k=56) → ValueError 크래시. mine_count=61+ 는 코너 클릭에서도 반드시 크래시(후보 60개 < 61). implementation-design.md 스펙은 상한을 54(= 64 - 10)로 명시하나 실제 코드는 63. 런타임 크래시가 재현됨(검증 완료).",
      "location": "minesweeper.py:150-151, 274"
    },
    {
      "category": "테스트",
      "severity": "BLOCK",
      "description": "test_create_board_rejects_invalid_mine_count는 mine_count=0과 mine_count=64만 거부됨을 검증하지만, mine_count=61~63은 create_board()를 통과한 뒤 place_mines() 호출 시 크래시를 유발한다. 해당 범위 크래시에 대한 테스트가 전무하다.",
      "location": "tests/test_minesweeper_unit.py:85-89"
    },
    {
      "category": "문서",
      "severity": "WARN",
      "description": "architecture.md §Backend Dev Public API의 Cell 명세가 is_revealed / is_flagged 필드명을 사용하나 실제 구현은 revealed / flagged를 사용한다. change_history.md에 의도적 변경으로 기록되어 있으나 architecture.md 자체는 갱신되지 않아 두 문서가 불일치한다.",
      "location": "docs/architecture.md:155-165"
    },
    {
      "category": "문서",
      "severity": "WARN",
      "description": "verification-report.md가 이전 실패 상태(7 passed, 11 failed)를 기록하고 있으나 현재는 18/18 PASS 상태다. Frontend Dev Module 1 빌드 이후 갱신되지 않았다.",
      "location": "docs/work-items/.../verification-report.md"
    },
    {
      "category": "의존성",
      "severity": "WARN",
      "description": "src/game_logic.py는 minesweeper.py의 GameState/Cell/Board를 전혀 사용하지 않는 완전히 독립된 별개 구현체다. 두 구현체 간 관계(어느 쪽이 정규 구현인지, src/game_logic.py가 언제 사용되는지)가 architecture.md에 명시되지 않았다.",
      "location": "src/game_logic.py:1 / minesweeper.py:1"
    }
  ],
  "summary": "BLOCK 2건: (1) mine_count 상한선이 63으로 설정되어 있으나 place_mines의 안전구역 제외 로직(최대 9칸) 때문에 mine_count=56+에서 중앙 클릭 시, mine_count=61+에서 모든 클릭 시 random.sample ValueError가 발생한다 — 실제 크래시 재현 완료. implementation-design.md는 상한을 54로 명시하나 코드는 63. (2) 이 크래시 경로에 대한 테스트가 없어 AC-10(단위 테스트 전체 통과) 기준으로는 통과되지만 런타임 계약이 미검증 상태다. WARN 3건: architecture.md의 Cell 필드명 불일치, verification-report.md 미갱신, src/game_logic.py와 minesweeper.py 간 역할 관계 미명시."
}
```

---

## 항목별 검증 결과

### 1. 모듈 간 인터페이스 일관성 — BLOCK

Backend Dev 산출물(`GameState`, `Cell`, `Board`)은 game_logic_dev, frontend_dev, qa_engineer가 올바르게 소비하고 있다. 그러나 `create_board()`의 상한선 검증과 `place_mines()`의 실제 가용 후보 수 사이에 계약 불일치가 존재한다.

| 케이스 | mine_count | 클릭 위치 | 결과 |
|--------|-----------|-----------|------|
| 안전 | ≤55 | 모든 위치 | OK |
| 위험 | 56~60 | 중앙 (후보 55개) | **CRASH** |
| 위험 | 61~63 | 코너 포함 모든 위치 | **CRASH** |

재현 명령:
```bash
python3 -c "
from minesweeper import Board
b = Board(mine_count=61)
b.place_mines(3, 3)  # ValueError 발생
"
```

**수정 방향**: `create_board()` 및 `main()`의 상한선을 54(implementation-design.md 스펙) 또는 55(64-9, 최악의 안전구역 크기)로 낮춘다.

### 2. 설계 문서와 구현의 괴리 — WARN

`architecture.md` §Backend Dev 공개 인터페이스에서 `Cell` 필드명이 `is_revealed`/`is_flagged`로 명세되어 있으나 `minesweeper.py` 실제 구현은 `revealed`/`flagged`를 사용한다.

`change_history.md`에는 `2026-05-08T14:35:00` 항목에 "주의: 아키텍처 spec의 is_revealed/is_flagged 대신 revealed/flagged 사용 — tests/test_minesweeper_unit.py 기대값과 정합하기 위해"라고 기록되어 있으나, `architecture.md` 자체는 갱신되지 않았다.

### 3. 테스트 커버리지 갭 — BLOCK

현재 pytest 실행 결과: **18/18 PASS** ✅

그러나 Backend Dev 담당 인터페이스의 런타임 크래시 경로가 테스트되지 않았다:

| 미테스트 시나리오 | 위치 |
|----------------|------|
| mine_count=56, 중앙 클릭 시 crach | create_board 상한 버그 |
| mine_count=61~63, 임의 클릭 시 crash | create_board 상한 버그 |

`test_create_board_rejects_invalid_mine_count`는 mine_count=64만 거부함을 검증하지만, mine_count=61~63은 허용되면서 런타임에 크래시를 유발한다.

### 4. 의존성 그래프 정합성 — WARN

`minesweeper.py`의 Backend Dev 산출물을 소비하는 역할:
- `frontend_dev` (Module 1, 2, 3) ✅ — 정상 소비
- `qa_engineer` (`tests/test_minesweeper_unit.py`) ✅ — 정상 소비

`src/game_logic.py`는 `minesweeper.py`와 전혀 관계 없는 독립 구현체로, Backend Dev 산출물을 사용하지 않는다. 이 두 구현체의 관계가 `architecture.md`에 정의되지 않았다.

순환 의존성: 없음 ✅

### 5. 문서 업데이트 누락 — WARN

| 문서 | 현재 상태 | 요구 사항 |
|------|-----------|-----------|
| `docs/architecture.md` §Backend Dev Cell 명세 | `is_revealed`/`is_flagged` | `revealed`/`flagged`로 갱신 필요 |
| `docs/work-items/.../verification-report.md` | 7 passed, 11 failed 기록 | 18/18 PASS 현행화 필요 |

---

## 수정 우선순위

### 즉시 수정 필요 (BLOCK)

**1. mine_count 상한선 수정 (minesweeper.py:150, 274)**

```python
# 수정 전 (현재)
if not (1 <= mine_count <= 63):
    raise ValueError(f"지뢰 수는 1~63 범위여야 합니다. 입력값: {mine_count}")

# 수정 후 (implementation-design.md 스펙 기준)
if not (1 <= mine_count <= 54):
    raise ValueError(f"지뢰 수는 1~54 범위여야 합니다. 입력값: {mine_count}")
```

main()의 검증도 동일하게 수정:
```python
# minesweeper.py:274
if not (1 <= mines <= 54):
```

**2. 크래시 시나리오 테스트 추가 (tests/test_minesweeper_unit.py)**

```python
def test_create_board_rejects_mine_count_above_limit(ms):
    with pytest.raises((ValueError, AssertionError)):
        ms.create_board(size=8, mine_count=55)  # 상한 초과
    # 상한값 이하는 허용
    board = ms.create_board(size=8, mine_count=54)
    assert board is not None
```

### 권장 수정 (WARN)

- `architecture.md` §Backend Dev Cell 명세의 `is_revealed` → `revealed`, `is_flagged` → `flagged` 갱신
- `verification-report.md`를 현재 테스트 결과(18/18 PASS)로 갱신
- `architecture.md`에 `src/game_logic.py`와 `minesweeper.py` 역할 분리 명시
