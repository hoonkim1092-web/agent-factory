# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-07 17:34
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Cross Review가 실제 테스트 실패(148 calls vs 예상 16)를 입증했고, Critic이 동일 영역의 조건 오류를 독립적으로 발견했습니다. High 이상 결함 3개.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `keywords_for_gap_check()` 결과를 체크리스트 필드로 오용 — recovery loop 폭주

- **Critic**: `_quality_contract is None and not _domain_checklist` 조건이 `_quality_contract`가 존재하나 `[]`를 반환할 때 fallback을 발동하지 않음
- **Cross**: `keywords_for_gap_check()`가 item ID 대신 모든 match keyword를 반환 → `_identify_unmet_gaps()` 입력이 폭발. 테스트에서 `148 calls` (예상 `8×2=16` cap 초과) 확인
- **Judgment**: 두 리뷰어가 같은 코드 경로를 독립적으로 공격. Critic은 조건 오류, Cross는 실제 회귀를 수치로 증명. `diff:976`의 `_quality_contract.keywords_for_gap_check()` 할당이 직접 원인.
- **Action Required**:
  1. `keywords_for_gap_check()` 대신 item-level 필드 목록을 사용 (항목당 1쿼리 bounded)
  2. fallback guard를 `if not _domain_checklist:`로 단순화하여 `_quality_contract` 존재 여부와 분리

---

#### 2. [ACCEPT] [High] `except Exception: return None` — 모든 실패 신호 소거

- **Critic**: `ModuleNotFoundError` / `AttributeError` / `TypeError` 전부 무음 흡수. Phase 5가 frozen 빌드에서 비활성화돼도 운영 중 감지 불가
- **Cross**: "does not crash existing callers"로 crash 우려는 기각했지만 "may hide quality problems" 명시 → Finding 3(af.spec 누락)과 결합 시 **침묵 비활성화** 시나리오 성립
- **Judgment**: `diff:614` 패턴은 code-review.md "Silent fallback: bare `except: pass`" 항목의 반복. Cross가 crash를 기각한 것은 fallback 체인 안전성에 대한 판단이고, 진단 불투명성 문제는 별개로 유효.
- **Action Required**: 최소 `logger.debug("_build_quality_contract fallback: %s", e)` 추가

---

#### 3. [ACCEPT] [High] fallback 체크리스트가 coverage report에 도달하지 않음

- **Critic**: 미플래그
- **Cross**: `_emit_coverage_report()`는 `domain=""`일 때 즉시 `{}` 반환 (`core/researcher.py:724`). `ProjectPipeline._coverage_blocked()`가 `coverage_report["block"]`을 참조(`core/project_pipeline.py:277,924`)하므로 degraded evidence가 block을 트리거하지 않음
- **Judgment**: Cross만 발견했지만 코드 추적 경로(`researcher.py:1102 → :724 → project_pipeline.py:277`)가 구체적이고 검증 가능. `diff:976`의 `_domain_checklist = ["requirements_coverage", "architecture_rationale"]` 할당이 무의미해지는 경로 확인됨.
- **Action Required**: `_emit_coverage_report()`에 `domain` 없을 때 `"general"` 또는 `contract_id`로 대체 emit 처리

---

#### 4. [ACCEPT] [Medium→High] `af.spec` hiddenimports / datas 누락 — frozen 빌드 Phase 5 영구 비활성

- **Critic**: `diff:601-603`의 함수 내부 lazy import는 PyInstaller 정적 분석 대상 외. Finding 2의 silent swallow와 결합 시 배포 빌드에서 무음 비활성화
- **Cross**: 미플래그
- **Judgment**: PyInstaller의 lazy import 미분석은 잘 알려진 동작이며 code-review.md §3.3 M9 기존 패턴의 재현. 증거 강함. Finding 2와 결합 시 사용자에게 전혀 노출되지 않는 silent regression.
- **Action Required**:
  ```python
  # af.spec hiddenimports에 추가
  'core.research.work_spec',
  'core.research.quality_contract',
  'core.research.checklist_merger',
  # datas에 추가
  ('core/research/packs', 'core/research/packs'),
  ```

---

#### 5. [ACCEPT] [Low] `QualityContractBuildError` dead import

- **Critic**: `diff:602` import 후 미참조. broad `except Exception`이 이미 포착하므로 기능도 없음
- **Cross**: 미플래그
- **Judgment**: diff에서 직접 확인 가능한 dead code. 의도가 `except QualityContractBuildError` 분기였다면 구현 누락.
- **Action Required**: 삭제하거나 전용 `except QualityContractBuildError as e:` 분기로 교체

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `keywords_for_gap_check()` → recovery 폭주 (148 calls) | High | ACCEPT | Both |
| 2 | `except Exception: return None` 무음 소거 | High | ACCEPT | Critic |
| 3 | fallback 체크리스트가 coverage block에 미도달 | High | ACCEPT | Cross |
| 4 | `af.spec` hiddenimports 누락 | Medium→High | ACCEPT | Critic |
| 5 | `QualityContractBuildError` dead import | Low | ACCEPT | Critic |

---

### Recommendations

- **#1 우선**: `_quality_contract.checklist` (item 목록)를 recovery loop에 직접 전달. `keywords_for_gap_check()`는 web query 생성에만 사용.
- **#1 연동**: fallback guard를 `if not _domain_checklist:` 단순화 (`_quality_contract is None` 조건 제거)
- **#2**: `except Exception as e: logger.debug(...)` 한 줄 추가로 즉시 해결
- **#3**: `_emit_coverage_report(domain or "general", ...)` 패턴으로 degraded path도 coverage block 가능하게
- **#4**: `af.spec` 수정은 #2 수정과 같은 커밋에 포함 — 현재 frozen 빌드가 Phase 5를 사용 중이라면 즉시 배포 영향
- **#5**: import 한 줄 삭제로 해결, 우선순위 낮음