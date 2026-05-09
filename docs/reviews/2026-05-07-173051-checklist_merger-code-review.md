# Code Review: checklist_merger

> Source: core/research/checklist_merger.py
> Date: 2026-05-07 17:30
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Critic의 High 2건이 BLOCK 기준을 충족. Cross의 2건은 데이터 손실 결함이며 같은 머지 로직에 존재. 5건 모두 `checklist_merger.py` 머지 경로에 집중되어 있다.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Rule 4 미강제 — `llm_addition` reason 필드 검증 없음
- **Critic**: "신규 항목 추가(line 21-22)와 overlay 병합(line 37) 모두에서 `source=="llm_addition"` AND `reason==""` 조합이 조용히 통과"
- **Cross**: not flagged
- **Judgment**: 클래스 docstring Rule 4가 명시적으로 요구하는 불변을 코드가 전혀 강제하지 않는다. `reason=item.reason or existing.reason` (line 37)은 양쪽 모두 비어있을 때 `""` 를 채운 채 통과시킨다.
- **Action Required**: `merge()` 루프 진입 시점에 검증 추가:
  ```python
  if item.source == "llm_addition" and not item.reason:
      raise ValueError(f"llm_addition item '{item.id}' missing reason")
  ```

---

#### 2. [ACCEPT] [High] Rule 5 미강제 — 빈 결과 리스트 반환 가능
- **Critic**: "모든 항목이 `id==\"\"` 스킵 또는 Rule 3 필터에 걸리면 `[]` 반환. `quality_contract.py:120` 가드는 pack-load 단계에 있어 merger 후 비워지는 경로를 잡지 못함"
- **Cross**: not flagged
- **Judgment**: `return list(merged.values())` (line 40)에 빈 리스트 가드가 없다. 호출자 `QualityContractBuilder`는 이 클래스가 Rule 5를 보장한다고 신뢰할 수 없다.
- **Action Required**:
  ```python
  result = list(merged.values())
  if not result:
      raise QualityContractBuildError("checklist_merger returned empty list")
  return result
  ```

---

#### 3. [ACCEPT] [Medium] `match_keywords` 합집합이 아닌 교체 — 기존 키워드 소실
- **Critic**: not flagged
- **Cross**: "`match_keywords=item.match_keywords or existing.match_keywords` — 새 항목에 keywords가 있으면 기존 keywords를 덮어씀. `Researcher._identify_unmet_gaps()`는 이 키워드에 의존해 gap 탐지를 수행"
- **Judgment**: `or` 단락 평가 때문에 domain overlay가 base/artifact 동의어를 조용히 제거할 수 있다. Gap 탐지에 직접 영향을 주는 데이터 손실 경로다.
- **Action Required**: stable union으로 변경:
  ```python
  match_keywords=list(dict.fromkeys(existing.match_keywords + item.match_keywords))
  ```

---

#### 4. [ACCEPT] [Medium] `domain_overlay`가 non-base required 항목을 강등 가능
- **Critic**: "Rule 3 보호는 `llm_addition`만 가드. `artifact_pack`/`capability_pack` 출처의 `required=True` 항목을 `domain_overlay`가 `required=False`로 강등 가능. 클래스 docstring에 이 비대칭이 문서화되어 있지 않음"
- **Cross**: not flagged
- **Judgment**: line 26-27의 보호 조건이 `item.source == "llm_addition"` 만 체크하므로 `domain_overlay`는 동일 머지 경로에서 보호받지 못한다. 의도적 비대칭이라면 docstring에 명시 필요.
- **Action Required**: 의도가 아니라면 보호 확장:
  ```python
  if existing.required and item.source in ("llm_addition", "domain_overlay") and not item.required:
      continue
  ```
  의도라면 docstring에 비대칭 동작 문서화.

---

#### 5. [ACCEPT] [Medium] priority 기본값과 명시적 override 구분 불가 — 무성 강등
- **Critic**: not flagged
- **Cross**: "`QualityContractItem.priority` 기본값이 `\"medium\"`, `_load_pack()`도 누락 시 `\"medium\"` 기본. 중복 항목이 priority를 생략하면 기존 `\"high\"`를 `\"medium\"`으로 조용히 낮춤"
- **Judgment**: line 35에서 항상 `item.priority`를 채택하므로 overlay YAML에서 priority를 생략해도 `"medium"` 기본값이 기존 `"high"`를 덮어쓴다. 의도와 생략이 구분되지 않는다.
- **Action Required**: overlay 머지 시 priority는 명시된 경우에만 채택. 구현 방법: `Optional[str]` 타입으로 변경 후 `None`이면 `existing.priority` 유지. 또는 overlay 로딩 시 `priority` 키 존재 여부를 별도 추적.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `llm_addition` reason 검증 없음 | High | ACCEPT | Critic |
| 2 | 빈 결과 리스트 반환 가능 | High | ACCEPT | Critic |
| 3 | `match_keywords` 교체로 키워드 소실 | Medium | ACCEPT | Cross |
| 4 | `domain_overlay` required 강등 무보호 | Medium | ACCEPT | Critic |
| 5 | priority 기본값과 명시 override 구분 불가 | Medium | ACCEPT | Cross |

---

### Recommendations

- **즉시 수정 (BLOCK 해제 필수)**: Finding #1, #2 — `merge()` 시작부에 reason 검증, return 전 빈 리스트 가드
- **같은 PR에서 수정 권장**: Finding #3 — `match_keywords` union 헬퍼 추가 (gap 탐지 정확도에 직접 영향)
- **의도 명확화 후 수정**: Finding #4 — `domain_overlay` 보호 확장 또는 docstring 비대칭 명시
- **스키마 레벨 해결**: Finding #5 — `priority` 필드를 `Optional[str]`로 변경, overlay 머지 시 `None` 보존 로직
- **별도 이슈로 추적**: `quality_contract.py:67` frozen-build 크래시 경로(`_PACKS_DIR = Path(__file__).parent / "packs"`)와 `:136-138` silent fallback — 본 diff 범위 외지만 같은 PR에 포함된 미수정 기존 BLOCK 버그