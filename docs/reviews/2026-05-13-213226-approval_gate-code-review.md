# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-13 21:32
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

BLOCK = Finding #1(체크박스 fallback 명세 위반) + Finding #3(0-caller 미완성 배포) 두 건이 동시에 High 이상.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] 체크박스 fallback이 설계 명세 위반

- **Critic**: "설계 문서가 fallback 없음·대소문자 strict를 명시. 이전 review에서도 같은 이유로 체크박스 제거 Action Required 발행됐으나 미반영."
- **Cross**: 명시적으로 플래그하지 않음 (Cross Finding #4는 explicit `- verdict:` 줄의 대소문자 정책을 올바르다고 확인하는 것이므로 체크박스 분기와 무관).
- **Judgment**: Critic 단독이지만 증거가 세 겹 — (a) 설계 문서 240-242줄 "fallback 없음" 명시, (b) 이전 review에서 동일 Action Required 기발행, (c) 코드 docstring 자체가 "없으면 `- [x] CHECKBOX` 체크박스 fallback"이라 적어 설계와 모순임을 드러냄. `re.I` 플래그로 대소문자 무시하는 점도 "strict" 규칙 위반.
- **Action Required**: `core/approval_gate.py:108-113` (checked 분기 전체) 제거. explicit 매치 0건이면 `""` 반환.

---

#### 2. [ACCEPT] [Medium] `"MULTIPLE"` 반환값이 타입 계약 위반

- **Critic**: "설계 스펙 반환 타입은 `Literal['PASS','NEEDS_ADR','BLOCK','']`. `''` 하나가 missing/invalid/multiple 전부 포괄하는 fail-closed 값."
- **Cross**: 플래그 없음.
- **Judgment**: Finding #1이 수용되어 체크박스 분기가 제거되면 `"MULTIPLE"` 반환 경로가 하나 사라지지만, explicit 분기(줄 106)의 `else "MULTIPLE"` 경로는 여전히 남는다. 호출자가 아직 없어 즉각 런타임 장애는 없으나, wiring 시점에 타입 불일치가 묵시적 버그로 전환될 수 있음.
- **Action Required**: `core/approval_gate.py:106` — `return explicit[0] if len(explicit) == 1 else ""`. Finding #1 수정 후 "MULTIPLE" 경로 전부 제거.

---

#### 3. [ACCEPT] [High] 호출자 0건 — 기능이 실제로는 동작하지 않는 silent no-op 배포

- **Critic**: "`approve()`·`is_execution_open()` wiring 없이 상수+함수만 커밋. domain review gate가 배포 기간 동안 무음 작동하지 않는 상태."
- **Cross**: "RuntimeGate는 여전히 `check_validity()`만 호출하며 `_DOMAIN_REVIEW_FILE`을 읽지 않음. `rg _read_domain_review_verdict` 결과 정의만 존재." (Cross Finding #1 ACCEPT)
- **Judgment**: 두 리뷰어 모두 독립적으로 grep으로 확인. `is_execution_open()` → `check_validity()` 경로는 `_DOC_FILES` snapshot 비교만 수행. 새 함수는 어디서도 호출되지 않아 설계(:174)가 요구하는 enforcement path가 없음.
- **Action Required**: 이 PR에 `approve()` 또는 `is_execution_open()` 내 `_read_domain_review_verdict()` 호출을 함께 포함하거나, wiring 커밋이 준비될 때까지 이 diff를 별도 브랜치로 격리.

---

#### 4. [ACCEPT] [Medium] 새 파서에 대한 테스트 없음

- **Critic**: 언급 없음.
- **Cross**: "6 tests pass, but none cover PASS / NEEDS_ADR / BLOCK / missing file / multiple verdicts / post-approval drift." (Cross Finding #2 ACCEPT)
- **Judgment**: Cross가 직접 `pytest`를 실행해 확인. Finding #3(호출자 없음)이 수정되면 테스트 커버리지도 함께 확보되어야 함.
- **Action Required**: `_read_domain_review_verdict()` 단위 테스트 (PASS/NEEDS_ADR/BLOCK/missing/multiple 케이스) + `approve()` 통합 테스트 1건 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 체크박스 fallback — 설계 명세 위반 | High | ACCEPT | Critic |
| 2 | `"MULTIPLE"` 반환값 타입 계약 위반 | Medium | ACCEPT | Critic |
| 3 | 호출자 0건 — silent no-op 배포 | High | ACCEPT | Both |
| 4 | 새 파서 테스트 미작성 | Medium | ACCEPT | Cross |

---

### Recommendations

- `core/approval_gate.py:108-113` checked 분기 전체 삭제, explicit 0건 → `""` 반환으로 단순화.
- `core/approval_gate.py:106` `else "MULTIPLE"` → `else ""` 로 타입 계약 일치.
- `approve()` 또는 `is_execution_open()` 내에 `_read_domain_review_verdict()` 호출 경로 추가 (또는 wiring PR이 준비될 때까지 이 diff 격리).
- Finding #3 수정과 동시에 `tests/test_approval_gate_domain_review.py`에 5-케이스 table test 추가.