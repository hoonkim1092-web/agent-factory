# designer_module_7 교차검증 보고서

- 작성일: 2026-05-08
- 검증자: designer_cross_validator
- 작업 ID: designer_module_7_cross_validate
- 최종 판정: **WARN**

---

## 판정 JSON

```json
{
  "verdict": "WARN",
  "issues": [
    {
      "category": "인터페이스",
      "severity": "WARN",
      "description": "minesweeper.py 입력 프롬프트가 ui-spec.md §5.1 계약을 준수하지 않음. ui-spec: '명령 입력 (행 열 / f 행 열 / q): ' / 실제 구현: '명령> '. Frontend Dev가 ui-spec 계약을 이행하지 않은 상태이며, 테스트 스위트도 이 불일치를 탐지하지 못함.",
      "location": "docs/designer/ui-spec.md §5.1 / minesweeper.py:278"
    },
    {
      "category": "인터페이스",
      "severity": "WARN",
      "description": "minesweeper.py 보드 행 렌더링 포맷이 ui-spec.md §2.3 계약과 불일치. ui-spec: '{r}  {c0} {c1}...' (행번호 + 공백 2개 + 셀들) / 실제 구현: '{r} | {c0} {c1}...' (행번호 + ' |' 파이프 구분자). 예: ui-spec='0  ? ? ? ? ? ? ? ?', 실제='0 | ? ? ? ? ? ? ? ?'. 파이프 구분자는 ui-spec에 명시된 포맷이 아님.",
      "location": "docs/designer/ui-spec.md §2.3 / minesweeper.py:122"
    },
    {
      "category": "인터페이스",
      "severity": "WARN",
      "description": "minesweeper.py 게임 시작 및 턴 갱신 화면 헤더가 ui-spec.md §2.1 계약과 불일치. ui-spec PLAYING 헤더: '지뢰찾기 8×8 [지뢰: {n}개]' / 실제: '8×8 지뢰찾기 시작! (명령: R C — 공개, f R C — 깃발, q — 종료)'. 상태별 헤더(PLAYING/WIN/LOSE) 전환 로직 및 구분선(----- 20자)도 구현 누락.",
      "location": "docs/designer/ui-spec.md §2.1, §2.4 / minesweeper.py:272-299"
    },
    {
      "category": "인터페이스",
      "severity": "WARN",
      "description": "사용자 종료(quit) 메시지 미구현. ui-spec.md §4.1 계약: 'quit/q 입력 시 게임을 종료합니다. 출력' / 실제: 메시지 없이 루프 종료. 화면 F 명세 미이행.",
      "location": "docs/designer/ui-spec.md §1.2 화면 F, §4.1 / minesweeper.py:231-232, 284-285"
    },
    {
      "category": "테스트",
      "severity": "WARN",
      "description": "QA 테스트 스위트(test_minesweeper_unit.py)가 ui-spec.md 포맷 계약을 검증하지 않음. test_render_board_returns_ascii_grid는 '?','F' 포함 여부만 확인하고 행 포맷('{r}  ...' vs '{r} |...'), 헤더 형식, 구분선, 프롬프트 문자열을 검증하지 않아 Frontend Dev 미준수가 테스트로 탐지되지 않음.",
      "location": "tests/test_minesweeper_unit.py:184-199 / docs/designer/ui-spec.md §2, §5"
    },
    {
      "category": "문서",
      "severity": "WARN",
      "description": "code-review.md designer_module_7 리뷰의 WARN 2건(EX-06 메타데이터 참조 불일치, 승리 판정 후 깃발 렌더링 규칙 미명시)이 ui-spec.md에 미반영. Phase 0 정책상 WARN은 수정 의무 없으나, 향후 Frontend Dev 구현 시 혼란 소지 존재.",
      "location": "docs/code_review/code-review.md:96-104 / docs/designer/ui-spec.md §1 메타데이터, §3"
    }
  ],
  "summary": "BLOCK 기준 항목 없음. designer_module_7의 직접 산출물(ui-spec.md, scope.md, architecture.md 갱신, change_history.md 기록)은 완성도가 높고 내부 일관성이 있다. feature-spec.md의 FR-08/FR-09/EX-01~EX-05와 정확히 정합하며, 수락 기준(AC-05~AC-08) 대응표도 완비됐다. WARN 6건의 핵심은 두 가지다: (1) Frontend Dev가 ui-spec.md 계약의 3개 핵심 항목(입력 프롬프트, 보드 행 포맷, 상태별 헤더/구분선)을 준수하지 않아 AC-01 시나리오에서 ui-spec 기준 불일치 발생 — Frontend Dev 모듈 재작업 필요. (2) QA 테스트가 ui-spec 포맷 계약을 검증하지 않아 이 불일치가 자동 탐지되지 않음 — 렌더링 포맷 테스트 보강 필요. designer_module_7 자체의 설계 결함은 없으므로 판정: WARN."
}
```

---

## 검토 범위

- `docs/designer/ui-spec.md` (주 산출물)
- `docs/plans/2026-05-08-designer-scope.md` (범위·의존성 정의)
- `docs/architecture.md` (Product Designer 섹션)
- `docs/change_history.md` (변경 이력)
- `docs/work-items/.../feature-spec.md` (입력 기준 문서)
- `docs/work-items/.../implementation-design.md` (입력 기준 문서)
- `minesweeper.py` (후행 소비자 구현체)
- `tests/test_minesweeper_unit.py` (QA 검증 커버리지)
- `docs/code_review/code-review.md` (designer 코드 리뷰 결과)

---

## 항목별 검증 결과

### 1. 모듈 간 인터페이스 일관성 — WARN

#### 1-1. ui-spec.md 내부 일관성 ✓

| 항목 | 검증 결과 |
|------|---------|
| 화면 흐름(§1) ↔ 기호 사전(§3) 정합 | ✓ 일치 |
| 화면 흐름(§1) ↔ 메시지 문자열(§4) 정합 | ✓ 일치 |
| 보드 포맷(§2) ↔ 전체 화면 예시(§6) 정합 | ✓ 일치 |
| 입력 프롬프트(§5) ↔ 화면 예시(§6) 정합 | ✓ 일치 |
| 수락 기준 대응표(§7) ↔ 본문 참조 정합 | ✓ 일치 |

#### 1-2. ui-spec.md ↔ feature-spec.md 정합 ✓

| feature-spec 항목 | ui-spec 대응 | 일치 여부 |
|-------------------|-------------|---------|
| FR-08 셀 기호 5종(`?`,`F`,`1~8`,`.`,`*`) | §3 기호 사전 | ✓ |
| FR-09 입력 형식(R C / f R C / q) | §5.2 입력 형식 | ✓ |
| EX-01 범위 초과 메시지 | §4.2 EX-01 | ✓ 문자열 동일 |
| EX-02 형식 오류 메시지 | §4.2 EX-02 | ✓ 문자열 동일 |
| EX-03 이미 공개 메시지 | §4.2 EX-03 | ✓ 문자열 동일 |
| EX-04 깃발 불가 메시지 | §4.2 EX-04 | ✓ 문자열 동일 |
| EX-05 지뢰 수 범위(1~63) 메시지 | §4.2 EX-05 | ✓ 문자열 동일 |
| FR-06 승리 메시지 | §4.1 | ✓ 문자열 동일 |
| FR-07 패배 메시지 | §4.1 | ✓ 문자열 동일 |

#### 1-3. ui-spec.md → minesweeper.py (소비자 준수) — WARN

| ui-spec 계약 | 실제 구현 | 준수 여부 |
|-------------|---------|---------|
| 입력 프롬프트: `명령 입력 (행 열 / f 행 열 / q): ` | `명령> ` | ✗ 불일치 |
| 행 포맷: `{r}  {c0} {c1}...` (공백 2개) | `{r} \| {c0} {c1}...` (파이프 사용) | ✗ 불일치 |
| PLAYING 헤더: `지뢰찾기 8×8 [지뢰: N개]` | `8×8 지뢰찾기 시작! ...` | ✗ 불일치 |
| WIN 헤더: `지뢰찾기 8×8 [승리!]` | 없음 | ✗ 불일치 |
| LOSE 헤더: `지뢰찾기 8×8 [게임 오버]` | 없음 | ✗ 불일치 |
| 구분선 20자 (`--------------------`) | 없음 | ✗ 불일치 |
| 종료 메시지: `게임을 종료합니다.` | 없음 | ✗ 불일치 |
| 패배 메시지: `게임 오버! 지뢰를 밟았습니다.` | 동일 | ✓ |
| 승리 메시지: `축하합니다! 승리했습니다.` | 동일 | ✓ |
| EX-01~EX-04 오류 메시지 | 동일 | ✓ |
| EX-05 지뢰 수 오류 메시지 | 동일 | ✓ |
| 깃발 기호 `F` | 동일 | ✓ |
| 지뢰 기호 `*` (reveal_mines=True) | 동일 | ✓ |

**소결**: Frontend Dev가 ui-spec.md 계약 중 렌더링·헤더·프롬프트 관련 7개 항목을 이행하지 않음. 이는 designer_module_7 자체의 결함이 아니라 **Frontend Dev 미준수**이나, 교차검증 관점에서 인터페이스 불일치로 기록.

### 2. 설계 문서와 구현의 괴리 ✓ (designer 산출물 자체)

| 산출물 | 존재 여부 | 내용 완성도 |
|--------|---------|-----------|
| `docs/plans/2026-05-08-designer-scope.md` | ✓ | 의도·영향 범위·인터페이스·대안 완비 |
| `docs/designer/ui-spec.md` | ✓ | 화면 흐름 6종·포맷·기호·메시지·프롬프트·예시·AC 대응표 완비 |
| `docs/architecture.md` Product Designer 섹션 | ✓ | 범위·인터페이스·순서·빌드결과 반영 |
| `docs/change_history.md` 이력 | ✓ | scope(13:00), build(15:00) 2개 항목 기록 |

scope.md 선행 의존성:
- `feature-spec.md` 완료 확인 ✓
- `implementation-design.md` 완료 확인 ✓

### 3. 테스트 커버리지 갭 — WARN

| 검증 시나리오 | 테스트 존재 여부 |
|-------------|--------------|
| 보드 행 포맷(`{r}  cells`) 정확성 | ✗ 없음 |
| 헤더 라인 형식(`지뢰찾기 8×8 [지뢰: N개]`) | ✗ 없음 |
| 입력 프롬프트 문자열 정확성 | ✗ 없음 |
| 구분선(`--------------------`) 출력 위치 | ✗ 없음 |
| 승리·패배 화면 헤더 전환 | ✗ 없음 |
| 종료 메시지(`게임을 종료합니다.`) | ✗ 없음 |
| `reveal_all=True` 시 `*` 포함 여부 | ✓ test_render_board_reveal_all_shows_mine_symbol |
| 보드 ASCII 최소 검증(`?`·`F`·`0`·`7` 포함) | ✓ test_render_board_returns_ascii_grid |

ui-spec.md가 엄격하게 계약한 포맷 요소들(행 포맷, 헤더, 구분선, 프롬프트)에 대한 테스트가 없어 Frontend Dev 미준수가 자동 탐지되지 않는다.

### 4. 의존성 그래프 정합성 ✓

- designer_module_7은 순수 문서 산출물이므로 코드 의존성 없음
- 입력 의존성(`feature-spec.md`, `implementation-design.md`) 모두 확인됨
- 후행 의존성 방향(`ui-spec.md → Frontend Dev / QA Engineer`) 올바르게 명시됨
- 순환 의존성 없음

### 5. 문서 업데이트 누락 — WARN (경미)

- code-review.md의 WARN 2건이 ui-spec.md에 미반영:
  - EX-06 참조 표기 혼란 (메타데이터 `EX-01~EX-06` vs §4.2 `EX-01~EX-05`)
  - 승리 판정 시 깃발 셀 렌더링 규칙 미명시
- Phase 0 정책상 WARN은 수정 의무 없음 — 권고 수준

---

## 수정 우선순위

### BLOCK 없음

designer_module_7 자체에 즉시 수정 필요 항목 없음.

### 권장 수정 (WARN — Frontend Dev 대상)

다음 항목은 **Frontend Dev**가 `minesweeper.py`를 수정해야 한다:

1. 입력 프롬프트를 `"명령 입력 (행 열 / f 행 열 / q): "`로 변경 (minesweeper.py:278)
2. 보드 행 렌더링 포맷을 `f"{r}  " + " ".join(cells)` 형식으로 변경 (파이프 제거) (minesweeper.py:122)
3. 상태별 헤더 출력 구현:
   - PLAYING: `지뢰찾기 8×8 [지뢰: {n}개]`
   - WIN: `지뢰찾기 8×8 [승리!]`
   - LOSE: `지뢰찾기 8×8 [게임 오버]`
4. 턴 갱신·승리·패배 화면 전 구분선 20자 출력 구현
5. quit 시 `게임을 종료합니다.` 메시지 출력 구현

### 권장 추가 (WARN — QA Engineer 대상)

- 보드 행 포맷 정확성 테스트 추가 (헤더·행 포맷·구분선 검증)
- 입력 프롬프트 문자열 검증 테스트 추가 (단, 프롬프트는 `input()` 인자라 모킹 필요)

### 권고 (WARN — designer 재량)

- ui-spec.md §1 메타데이터의 `EX-01~EX-06`을 `EX-01~EX-05 (EX-06은 내부 처리, 사용자 메시지 없음)`으로 정정
- ui-spec.md §3에 `승리 시 깃발 셀은 F를 유지한다` 규칙 추가
