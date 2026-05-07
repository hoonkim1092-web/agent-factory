# Code Review: quality_contract

> Source: core/research/quality_contract.py
> Date: 2026-05-07 17:33
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Critic는 diff 미수신으로 실질 검증 불가. Cross Review 단독 2건 모두 증거가 구체적이어서 ACCEPT 처리. 보안 이슈(path traversal) 포함으로 WARN 격상.

---

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [High] `keywords_for_gap_check()`가 optional 키워드를 hard gate로 포함

- **Critic**: diff 미수신으로 미검토
- **Cross**: "`keywords_for_gap_check()`가 required 여부 무관하게 `match_keywords` 전체(134개)를 반환 → `core/researcher.py:983,986`이 이를 필수 항목처럼 처리. 동의어("requirements", "요구사항", "scope")가 각각 독립 필수 조건으로 동작."
- **Judgment**: Cross 단독이나 증거가 정량적이다. `checklist=23, required=21, keywords=134` 수치는 optional 항목과 동의어 확장이 70% sufficiency gate에 혼입됨을 직접 보여준다. caller(`researcher.py:807-813`)가 문자열 포함 여부로만 판정하므로 gate 결과가 의도와 다르게 나온다.
- **Action Required**: `keywords_for_gap_check()`를 `required_items()`의 canonical `id`만 반환하도록 변경하거나, caller를 `QualityContractItem` 단위로 바꿔 "required item 하나당 `any(match_keywords)` 판정"으로 수정. optional 항목은 blocking gate에서 제외.

#### 2. [ACCEPT] [High] LLM 출력값이 정규화 없이 filesystem path로 직접 사용

- **Critic**: diff 미수신으로 미검토
- **Cross**: "`quality_contract.py:91,99,113`에서 `artifact_type`, `capabilities`, `domain`, `domain_hints`가 정규화 없이 `_PACKS_DIR / f'{value}.yaml'`로 구성. 이 값들은 `researcher.py:607`의 LLM `WorkSpecExtractor` 출력에서 옴."
- **Judgment**: LLM 출력 → 파일시스템 경로 직행은 path traversal 취약점이다. `../`, `/`, `\`, drive prefix 등이 포함된 값이 실제 pack 경계를 벗어날 수 있다. 프로젝트 내 `safe_id()` 유틸이 이미 존재하므로 수정 비용이 낮다. 보안 이슈 → 최소 High 격상 규칙 적용.
- **Action Required**: `_load_pack()` 진입부에서 `safe_id()` 또는 명시 allowlist(registry key에 없는 값은 skip/log)를 적용. `/`, `\`, `..`, `:` 포함 값을 즉시 거부하는 유닛 테스트 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `keywords_for_gap_check()` optional 항목 hard gate 혼입 | High | ACCEPT | Cross |
| 2 | LLM 출력 → filesystem path 직접 사용 (path traversal) | High | ACCEPT | Cross |

---

### Recommendations

- `keywords_for_gap_check()` 반환값을 required canonical ID 목록으로 좁히고, caller의 sufficiency 계산 로직과 함께 수정
- `_load_pack()` 경계에서 `safe_id()` 적용 또는 pack registry 기반 allowlist 검증 추가; path separator/drive prefix 입력 거부 테스트 추가
- Finding 1의 caller semantics(`researcher.py:983,986` + 70% gate 연산)는 현재 테스트 커버가 없음 — 수정과 함께 테스트 작성 권장
- Critic가 diff를 받지 못한 원인 확인 필요 (`git diff --staged -- core/research/quality_contract.py`로 staged 여부 점검)