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

4개 Medium 결함, Critical/High 없음. 빈 체크리스트가 quality gate를 우회하는 경로(Cross #1)가 가장 위험도가 높으나 Critical 기준에는 미달. 문서화된 리스크로 머지 가능하나 즉시 후속 커밋 권고.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] `llm_addition` reason 필드 미검증

- **Critic**: "`reason=item.reason or existing.reason` (line 37)이 reason 없는 llm_addition을 조용히 통과시킴. QualityContractItem.reason 기본값이 `\"\"`이라 타입 시스템도 강제 안 함."
- **Cross**: "ACCEPT — `quality_contract.py:22` 및 머저 docstring 모두 llm_addition에 reason 필수라 명시하나, 기존 테스트는 'LLM이 required 삭제 불가' 케이스만 커버하고 reason 누락은 미검증."
- **Judgment**: 두 리뷰어 모두 동일 규칙 위반(Rule 4)을 지적, docstring 계약과 코드가 불일치. 강한 증거.
- **Action Required**: `checklist_merger.py` merge() 내부에 `if item.source == "llm_addition" and not item.reason.strip(): raise ValueError(...)` 추가. reason 누락 llm_addition 케이스 테스트 추가.

---

#### 2. [ACCEPT] [Medium] 빈 체크리스트가 quality gate를 우회

- **Critic**: "전체 입력 id가 비거나 continue로 건너뛰면 `[]` 반환. `QualityContractBuilder.build()`는 동일 조건에 `QualityContractBuildError` 발생 — 일관성 없음."
- **Cross**: "ACCEPT — `researcher.py:612`에서 caller가 contract를 교체하고, `researcher.py:971-978`에서 non-None contract를 valid로 취급하므로, merge가 `[]` 반환 시 degraded fallback이 완전히 스킵됨."
- **Judgment**: Cross가 실제 bypass 경로(`researcher.py:971-978`)까지 추적해 위험도를 확인. 단순 빈 리스트 반환이 아니라 quality gate 전체를 무력화하는 경로.
- **Action Required**: `merge()` 끝에 `if not merged: raise QualityContractBuildError("...")` 추가. 빈 id 아이템만 입력 시 회귀 테스트 추가.

---

#### 3. [ACCEPT] [Medium] `domain_overlay`의 `required` 필드 처리 불일치

- **Critic**: "Rule 3 가드는 llm_addition만 차단. artifact_pack/capability_pack의 required=True 항목을 domain_overlay가 required=False로 조용히 downgrade 가능. 의도 여부 판별 불가."
- **Cross**: "ACCEPT — 설계 문서는 overlay가 required/priority/acceptance를 override할 수 있다고 명시하나, 현재 코드는 base_pack 항목의 required를 항상 원본 유지. optional base 항목(예: test_strategy)도 upgrade 불가."
- **Judgment**: 두 리뷰어가 같은 코드를 반대 방향에서 지적(Critic: downgrade 위험 / Cross: upgrade 불가). 근본 원인은 동일 — `required` 병합 로직이 설계 의도를 반영하지 않음. 설계 문서 명세와 코드 동작 불일치가 핵심.
- **Action Required**: 설계 의도 결정 필요. (A) 단조 증가 의도라면 `required = existing.required or item.required`로 변경. (B) overlay 전면 override 허용이라면 `base_pack` 가드를 llm_addition 전용으로 좁힘. 어느 쪽이든 docstring에 명시.

---

#### 4. [ACCEPT] [Medium] `af.spec` hiddenimports에 `core.research` 서브패키지 미등록 (M9)

- **Critic**: "af.spec:61-63에 flat 모듈(core.research_router 등)은 있으나 신규 서브패키지 core.research.*가 전부 누락. frozen 빌드에서 ModuleNotFoundError 발생 — known issue M9 반복."
- **Cross**: "not flagged"
- **Judgment**: Critic 단독 지적이나 증거가 강함 — M9는 code-review.md §3.3에 기록된 반복 패턴이고, af.spec에 서브패키지가 없다는 사실은 파일 내용으로 직접 확인 가능. 빌드 검증 없이는 frozen 환경에서 크래시 보장.
- **Action Required**: `af.spec` hiddenimports에 `'core.research'`, `'core.research.checklist_merger'`, `'core.research.quality_contract'`, `'core.research.work_spec'` 추가. `python build_exe.py` 후 import 검증.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | llm_addition reason 미검증 | Medium | ACCEPT | Both |
| 2 | 빈 체크리스트 quality gate 우회 | Medium | ACCEPT | Both |
| 3 | domain_overlay required 처리 불일치 | Medium | ACCEPT | Both |
| 4 | af.spec hiddenimports 누락 (M9) | Medium | ACCEPT | Critic |

---

### Recommendations

- `checklist_merger.py`: merge() 에 Rule 4(reason), Rule 5(빈 결과) 검증 추가 — 2개 라인 추가로 해결 가능
- `required` 병합 로직: 설계 문서 의도 확인 후 단조 증가(`or`) vs overlay 전면 허용 중 택일, docstring에 반영
- `af.spec`: core.research 서브패키지 4개 모듈 hiddenimports 등재 후 빌드 검증
- 테스트 갭: reason 누락 llm_addition, 빈 id 전체 입력 2개 케이스 추가 — Cross가 명시한 미커버 경로