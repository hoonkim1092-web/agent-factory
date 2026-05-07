# Code Review: checklist_merger

> Source: core/research/checklist_merger.py
> Date: 2026-05-07 17:28
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High 1건 + Medium 5건. Critical 없음 — 문서화된 리스크로 머지 가능하나 즉시 후속 커밋 권고.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] `base_pack` required 필드가 `domain_overlay`로 변경 불가 — docstring 위반
- **Critic**: "domain_overlay가 base_pack item의 required를 내릴 수 없음. 상단 계약 docstring과 모순."
- **Cross**: "not flagged (priority 쪽 동일 패턴만 지적)"
- **Judgment**: `checklist_merger.py:34`의 `existing.source != "base_pack"` 가드가 `llm_addition`뿐 아니라 `domain_overlay`도 차단한다. 코드 증거가 명확하고 docstring과 직접 모순되므로 단독 flagging임에도 ACCEPT.
- **Action Required**: 가드를 `item.source == "llm_addition" and not item.required and existing.required`로 좁히거나, docstring Rule 3b에 "domain_overlay도 base_pack의 required를 내릴 수 없다"를 명시.

#### 2. [ACCEPT] [Medium] 빈 merged checklist가 degraded fallback을 우회
- **Critic**: "Rule 5 미적용 — id 없는 item이 drop되면 `[]` 반환 후 에러 없음"
- **Cross**: "`researcher.py:807`의 `_is_sufficient()`가 빈 contract를 유효로 처리해 체크리스트 강제 적용 전체를 건너뜀"
- **Judgment**: 양쪽 모두 동일 결함 확인. Cross가 downstream까지 추적해 실제 영향 경로를 입증.
- **Action Required**: `merge()` 종료 직전에 `if not merged: raise ValueError("ChecklistMerger produced empty checklist")` 추가. 회귀 테스트: 모든 item의 id가 비어있을 때 caller가 degraded fallback으로 진입하는지 검증.

#### 3. [ACCEPT] [Medium] `llm_addition` reason 없는 항목 무검증 통과
- **Critic**: "Rule 4 미적용 — 빈 reason의 llm_addition이 silently 수용됨"
- **Cross**: "id 중복 없는 llm_addition은 reason 검증 전 바로 삽입. `to_dict()` 경유 노출."
- **Judgment**: 동일 결함을 양쪽이 독립 확인. 코드 경로도 일치 (`checklist_merger.py:21`의 `if item.id not in merged`).
- **Action Required**: merge 루프 내 삽입 전 `if item.source == "llm_addition" and not item.reason: continue` (또는 raise) 추가.

#### 4. [ACCEPT] [Medium] overlay default priority `"medium"`이 기존 `"high"` 항목을 묵시적으로 강등
- **Critic**: "not flagged"
- **Cross**: "`quality_contract.py:145`의 `_load_pack()` default가 `"medium"`이므로 priority 미지정 overlay가 high→medium 강등 유발."
- **Judgment**: Cross만 flagging이나 `_load_pack()` 코드 증거가 명확하고 Finding 1의 required 문제와 동일 overlay 메커니즘 결함. ACCEPT.
- **Action Required**: `priority` 필드를 overlay pack에서 Optional로 처리하거나, `_load_pack()`에서 명시 지정 여부를 별도 flag로 전달해 `None`(미지정)과 `"medium"`(명시)을 구분.

#### 5. [ACCEPT] [Medium] 입력 순서 의존성 — 순서 계약 미문서화
- **Critic**: "`base_pack` 이전에 `domain_overlay`가 오면 overlay가 base가 되고 base_pack이 overlay로 취급돼 업데이트 안 됨."
- **Cross**: "not flagged"
- **Judgment**: `checklist_merger.py:21-22`의 first-wins 패턴 + `(source not in ("domain_overlay","llm_addition"))` 조합으로 Critic 주장이 코드에서 직접 추적됨. Caller가 현재는 올바른 순서를 지키지만 `ChecklistMerger`는 public API — 방어 불필요하지 않음.
- **Action Required**: 클래스 진입부에 `_SOURCE_ORDER` dict 기반 정렬 추가, 또는 docstring에 "items must be ordered base→artifact/capability→overlay→llm" 계약 명시.

#### 6. [ACCEPT] [Medium] `core.research.checklist_merger` af.spec hiddenimports 미등록
- **Critic**: "M9 패턴 반복 — frozen 빌드에서 런타임 시 ModuleNotFoundError, 시작 시가 아닌 실제 research 경로 진입 시 발생."
- **Cross**: "not flagged (직전 리뷰에서 `__init__.py` 관련 동일 패턴 ACCEPT됨)"
- **Judgment**: M9는 이 프로젝트에서 확립된 결함 패턴. Critic 단독이나 af.spec 구조와 직전 리뷰 선례로 증거 충분.
- **Action Required**: `af.spec` hiddenimports에 `core.research.checklist_merger` + `core.research` 하위 신규 모듈 전체 bulk 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | base_pack required domain_overlay 차단 — docstring 위반 | High | ACCEPT | Critic |
| 2 | 빈 merged checklist → degraded 우회 | Medium | ACCEPT | Both |
| 3 | llm_addition reason 무검증 | Medium | ACCEPT | Both |
| 4 | overlay default priority 묵시적 강등 | Medium | ACCEPT | Cross |
| 5 | 입력 순서 의존성 미문서화 | Medium | ACCEPT | Critic |
| 6 | af.spec hiddenimports 미등록 | Medium | ACCEPT | Critic |

---

### Recommendations

- **즉시 필수**: Finding 2 (빈 체크리스트 raise) + Finding 3 (llm_addition reason 검증) — 두 invariant는 downstream gap-check 오동작의 직접 원인.
- **Finding 1 우선**: docstring 수정이든 코드 가드 수정이든 택일. High severity는 계약 모순 때문이므로 docstring만 고쳐도 severity 해소.
- **Finding 4**: `_load_pack()`에서 field presence 구분이 필요해 범위가 넓을 수 있음 — Finding 1 수정과 묶어 overlay 메커니즘 일괄 정리 권장.
- **Finding 5**: 정렬 추가가 안전하나 기존 caller 순서도 검증 후 적용.
- **Finding 6**: `af.spec` hiddenimports는 `core/research/` 하위 파일 전수 bulk 업데이트 1회로 처리.