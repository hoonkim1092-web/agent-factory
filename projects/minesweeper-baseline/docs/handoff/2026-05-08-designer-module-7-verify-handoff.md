# Designer Module 7 검증 완료 Handoff 메모

## 메타데이터

| 항목 | 값 |
|------|-----|
| task_id | `designer_module_7_verify_3` |
| 작성일 | `2026-05-08` |
| 작성 역할 | designer |
| 단계 | verify |
| 최종 판정 | **PASS** (BLOCK 없음) |

---

## 검증 결과 요약

### Designer 산출물 검증

| 산출물 | 존재 여부 | 완성도 |
|--------|-----------|--------|
| `docs/plans/2026-05-08-designer-scope.md` | ✅ | 범위·인터페이스·대안·교차검증 요청 상태 완비 |
| `docs/designer/ui-spec.md` | ✅ | 화면 흐름 6종·보드 포맷·기호 사전·메시지·프롬프트·예시·AC 대응표 완비 |
| `docs/architecture.md` Product Designer 섹션 | ✅ | 범위·인터페이스·구현 순서·빌드 결과 반영 완료 |
| `docs/change_history.md` | ✅ | scope(13:00), build(15:00) 2개 이력 항목 기록 완료 |

### ui-spec.md 내부 정합성

| 검증 항목 | 결과 |
|-----------|------|
| 화면 흐름(§1) ↔ 기호 사전(§3) | ✅ 일치 |
| 화면 흐름(§1) ↔ 메시지 문자열(§4) | ✅ 일치 |
| 보드 포맷(§2) ↔ 전체 화면 예시(§6) | ✅ 일치 |
| 입력 프롬프트(§5) ↔ 화면 예시(§6) | ✅ 일치 |
| 수락 기준 대응표(§7) ↔ 본문 참조 | ✅ 일치 |

### ui-spec.md ↔ feature-spec.md 정합성

| feature-spec 항목 | ui-spec 대응 | 일치 |
|-------------------|-------------|------|
| FR-08 셀 기호 5종 | §3 기호 사전 | ✅ |
| FR-09 입력 형식 | §5.2 입력 형식 | ✅ |
| EX-01~EX-05 오류 메시지 | §4.2 EX-01~EX-05 | ✅ 문자열 동일 |
| FR-06 승리 메시지 | §4.1 | ✅ 문자열 동일 |
| FR-07 패배 메시지 | §4.1 | ✅ 문자열 동일 |

### 교차검증 결과 (designer_cross_validator)

- **최종 판정: WARN** (BLOCK 없음)
- designer_module_7 자체 결함 없음
- WARN 6건은 전부 **Frontend Dev 미준수** 또는 QA 테스트 커버리지 갭이 원인

---

## 잔여 리스크 및 후속 작업

### Frontend Dev 대상 — WARN (필수 대응 권장)

교차검증에서 `minesweeper.py`가 `ui-spec.md` 계약의 7개 항목을 이행하지 않았음을 확인했다.  
`frontend_dev_module_3_scope_1`에서 이미 수정 계획이 수립되어 있으며, `frontend_dev_module_3_build_2`에서 처리해야 한다.

| 번호 | 미준수 항목 | 현재 구현 | ui-spec 계약 | 파일:라인 |
|------|------------|-----------|--------------|----------|
| R-01 | 입력 프롬프트 | `명령> ` | `명령 입력 (행 열 / f 행 열 / q): ` | `minesweeper.py:278` |
| R-02 | 보드 행 포맷 | `{r} \| {셀들}` | `{r}  {셀들}` (공백 2개) | `minesweeper.py:122` |
| R-03 | PLAYING 헤더 | `8×8 지뢰찾기 시작! ...` | `지뢰찾기 8×8 [지뢰: {n}개]` | `minesweeper.py:272-299` |
| R-04 | WIN 헤더 | 없음 | `지뢰찾기 8×8 [승리!]` | `minesweeper.py` |
| R-05 | LOSE 헤더 | 없음 | `지뢰찾기 8×8 [게임 오버]` | `minesweeper.py` |
| R-06 | 구분선 20자 | 없음 | `--------------------` (턴·승리·패배 화면 전) | `minesweeper.py` |
| R-07 | quit 종료 메시지 | 없음 | `게임을 종료합니다.` | `minesweeper.py:231-232` |

> **참고**: `frontend_dev_module_3_scope_1` 설계 문서(`docs/architecture.md §Frontend Dev Module 3`)에서 동일한 갭이 이미 식별·계획되었다. Frontend Dev가 해당 scope 문서를 따르면 자동 해소된다.

### QA Engineer 대상 — WARN (권장)

`tests/test_minesweeper_unit.py`에 ui-spec.md 포맷 계약 검증 테스트가 없다.
Frontend Dev가 수정한 뒤에도 자동 탐지가 되지 않는 구조이므로, 아래 테스트 보강을 권장한다:

| 테스트 대상 | 검증 내용 |
|-------------|-----------|
| 보드 행 포맷 | `{r}  {셀들}` 형식 (파이프 없음) |
| 헤더 라인 | `지뢰찾기 8×8 [지뢰: N개]` / `[승리!]` / `[게임 오버]` |
| 구분선 | `--------------------` 20자 위치 |

### Designer 재량 수정 (WARN — 낮은 우선순위)

| 항목 | 내용 |
|------|------|
| ui-spec.md §1 메타데이터 | `EX-01~EX-06` → `EX-01~EX-05 (EX-06은 내부 처리, 사용자 메시지 없음)` 정정 |
| ui-spec.md §3 | 승리 시 깃발 셀(`F`)은 그대로 유지 규칙 명시 추가 |

> Phase 0 정책상 WARN은 수정 의무 없음. 다음 버전 업데이트 시 함께 처리 가능.

---

## 다음 작업자에게

### 즉시 필요한 작업

1. **Frontend Dev `frontend_dev_module_3_build_2`**: 위 R-01~R-07 7개 항목을 `minesweeper.py`에서 수정한다. 수정 순서는 `docs/architecture.md §Frontend Dev Module 3 구현 순서` 참조.
2. **QA Engineer**: Frontend Dev 수정 완료 후 `tests/test_minesweeper_unit.py`에 렌더링 포맷 검증 테스트를 추가한다.

### 참조 문서

| 문서 | 용도 |
|------|------|
| `docs/designer/ui-spec.md` | **단일 진실 소스** — 모든 출력 형식의 기준 |
| `docs/architecture.md §Frontend Dev Module 3` | Frontend Dev 수정 범위 및 순서 |
| `docs/cross_validate/2026-05-08-designer-module-7-cross-validate.md` | 교차검증 WARN 상세 내용 |
| `docs/plans/2026-05-08-designer-scope.md` | Designer 역할 범위 정의 |

### ui-spec.md 핵심 계약 (Frontend Dev가 반드시 준수해야 하는 항목)

```
프롬프트:  명령 입력 (행 열 / f 행 열 / q): 
행 포맷:   {r}  {c0} {c1} {c2} {c3} {c4} {c5} {c6} {c7}
구분선:    -------------------- (하이픈 20자, 새 화면 헤더 직전)
PLAYING:  지뢰찾기 8×8 [지뢰: {n}개]
WIN:       지뢰찾기 8×8 [승리!]
LOSE:      지뢰찾기 8×8 [게임 오버]
승리:      축하합니다! 승리했습니다.
패배:      게임 오버! 지뢰를 밟았습니다.
quit:      게임을 종료합니다.
```

---

## Designer 역할 완료 선언

`designer_module_7` 전체 단계(scope → build → cross_validate → verify)가 완료되었다.  
`docs/designer/ui-spec.md`는 확정 상태이며, 변경이 필요한 경우 `change_history.md`에 기록하고 Frontend Dev에게 통보해야 한다.
