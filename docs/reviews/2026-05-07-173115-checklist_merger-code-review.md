# Code Review: checklist_merger

> Source: core/research/checklist_merger.py
> Date: 2026-05-07 17:31
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High findings exist across both reviews — no Critical-severity issues. Can merge with documented risks, but the three Rule violations are straightforward to fix and should be addressed before next iteration.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Rule 5 미강제 — `merge()` 빈 리스트 반환 가능
- **Critic**: "`return list(merged.values())`에 후처리 가드 없음. `id=""`인 항목이 모두 line 19에서 skip되면 `[]` 반환. `QualityContractBuildError`는 build() 단계에서 발화해 post-merge 공백을 잡지 못함."
- **Cross**: "not flagged (별도 각도 — optional 항목 downstream 처리 이슈로 접근)"
- **Judgment**: Critic 단독이지만 코드 경로가 명확함. `_load_pack()`이 `id=""`를 만들 수 있고(YAML 항목에 `id` 키 없을 때), line 19의 `if not item.id: continue`가 전체를 소거하면 `[]`가 조용히 반환된다. docstring Rule 5 위반.
- **Action Required**:
  ```python
  result = list(merged.values())
  if not result:
      raise QualityContractBuildError("checklist_merger produced empty checklist")
  return result
  ```

#### 2. [ACCEPT] [High] Rule 4 미강제 — `llm_addition` 항목의 `reason` 검증 없음
- **Critic**: "docstring Rule 4 명시: 'llm_addition은 reason 필드가 있어야 한다.' 신규 항목(line 21-22)·overlay 병합(line 29-39) 모두 reason 비어있음 검사 없음. `QualityContractItem` dataclass default가 `reason=""`이라 조용히 통과."
- **Cross**: "not flagged"
- **Judgment**: Critic 단독이지만 docstring 계약과 코드 구현 간 gap이 명시적임. `reason=item.reason or existing.reason`(line 37) 패턴이 있으나, 이 or 체인은 reason이 없는 신규 항목 경로(line 21-22)에 적용되지 않는다.
- **Action Required**: overlay 분기 진입 전에 추가:
  ```python
  if item.source == "llm_addition" and not item.reason:
      continue  # 또는 raise — enforcement 정책에 따라 결정
  ```

#### 3. [ACCEPT] [High] Priority 묵시적 다운그레이드 — overlay `"medium"` default가 `"high"` 덮어씀
- **Critic**: "`_load_pack()`이 `priority` 키 부재 시 `"medium"` 기본값 설정. `domain_overlay` YAML이 `priority` 생략하면 `item.priority="medium"`이 기존 base_pack `priority="high"`를 덮어씀. sentinel 없어 '명시적 medium'과 '누락'을 구분 불가."
- **Cross**: "not flagged"
- **Judgment**: Critic 단독이지만 data flow가 검증 가능함. `_load_pack()`의 `priority=entry.get("priority", "medium")` 패턴과 merger line 36의 `priority=item.priority` 무조건 대입이 결합하면 누락 YAML 항목이 기존 high 우선순위를 조용히 강등한다.
- **Action Required**:
  1. `_load_pack()`을 `priority=entry.get("priority")` (None 반환)으로 변경
  2. `QualityContractItem.priority`를 `Optional[str]`으로 업데이트
  3. merger line 36: `priority=item.priority if item.priority is not None else existing.priority`

#### 4. [ACCEPT] [High] Optional 항목이 downstream에서 mandatory 게이트로 처리됨
- **Critic**: "not flagged"
- **Cross**: "`researcher.py:971-983`의 `keywords_for_gap_check()`가 merged checklist 전체를 사용하고, `_is_sufficient()`(line 807-814)가 70% 충족 요구. `base.yaml`의 `test_strategy required:false`, `multiplayer.yaml`의 `concurrency_handling required:false`가 blocking 게이트로 취급됨."
- **Judgment**: Cross 단독이지만 caller 코드 증거가 구체적(line numbers 제시). `required=False` 항목이 gap 체크에서 blocking 역할을 한다면 계약 위반이 API 경계 밖에서 드러남.
- **Action Required**: `keywords_for_gap_check(required_only=True)` 파라미터 추가 또는 `contract.required_items()` 별도 API 노출. Optional 항목은 non-blocking 리포트 전용으로 분리.

#### 5. [ACCEPT] [Medium] ID 정규화 없음 — 공백/대소문자 차이로 중복 항목 생성
- **Critic**: "not flagged"
- **Cross**: "merger line 19가 raw `item.id`로 key. `\"hand_ranking\"`과 `\" hand_ranking \"`이 별개 항목으로 취급. `llm_addition` 입력에서 특히 발생 가능성 높음."
- **Judgment**: Cross 단독이지만 LLM 생성 입력이 관여하는 경로라 whitespace 변형이 현실적 리스크임. Medium으로 수용.
- **Action Required**: `_load_pack()` 또는 merger 진입 시점에 `canonical_id = item.id.strip().lower()` 적용. 정규화 후 empty인 ID는 skip.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Rule 5 미강제 — 빈 리스트 반환 | High | ACCEPT | Critic |
| 2 | Rule 4 미강제 — `llm_addition` reason 검증 없음 | High | ACCEPT | Critic |
| 3 | Priority 묵시적 다운그레이드 | High | ACCEPT | Critic |
| 4 | Optional 항목 mandatory 게이트 처리 | High | ACCEPT | Cross |
| 5 | ID 정규화 없음 | Medium | ACCEPT | Cross |

---

### Recommendations

- **즉시 수정 (1~3번)**: 모두 `checklist_merger.py` 내부 변경만 필요. docstring이 명시한 계약을 코드에 강제하는 것으로, 범위가 좁고 테스트 추가도 직관적.
- **4번**: `researcher.py`의 caller 경계 변경이 필요하므로 별도 PR 또는 같은 PR에 `required_only` 파라미터 추가 후 기존 테스트 통과 확인.
- **5번**: 정규화 로직을 `_load_pack()`에 한 곳에서 처리해 merger는 이미 clean한 ID를 받도록 설계. whitespace/case 중복 케이스 단위 테스트 추가.
- **Cross REJECT 확인됨**: `merge()` 시그니처 호환성은 `pytest tests/test_quality_contract.py` 30 pass로 검증 완료 — 별도 조치 불필요.