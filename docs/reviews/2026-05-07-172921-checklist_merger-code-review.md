# Code Review: checklist_merger

> Source: core/research/checklist_merger.py
> Date: 2026-05-07 17:29
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Two Critical findings — both frozen-build crash paths — must be resolved before merge. One High finding from both reviewers on a known failure mode recreation.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Critical] af.spec hiddenimports — `core.research` 서브패키지 전체 누락

- **Critic**: "hiddenimports에 `core.research_*` 플랫 3개만 있고 `core/research/` 서브패키지 4개 전부 없음 → `ModuleNotFoundError` 즉시 크래시"
- **Cross**: "not flagged"
- **Judgment**: 증거가 명확하다. 새 Python 서브패키지(`core/research/__init__.py` + 3개 모듈)가 af.spec에 반영되지 않으면 frozen 빌드에서 import 자체가 불가능하다. M9 기존 패턴 재발.
- **Action Required**:
  ```python
  # af.spec hiddenimports에 추가
  'core.research',
  'core.research.work_spec',
  'core.research.quality_contract',
  'core.research.checklist_merger',
  ```

---

#### 2. [ACCEPT] [Critical] YAML pack 파일 — af.spec datas 미등록 + `_PACKS_DIR` frozen 비호환

- **Critic**: "`Path(__file__).parent / 'packs'` — frozen 빌드에서 `.pyc` archive 경로, packs/*.yaml 부재 → `QualityContractBuildError`"
- **Cross**: "not flagged"
- **Judgment**: Finding 1과 독립적인 두 번째 크래시 경로. datas 미등록으로 파일 자체가 없고, `__file__` 경로도 frozen 환경에서 무효다. 두 조건이 동시에 실패하므로 둘 다 수정해야 한다.
- **Action Required**:
  ```python
  # af.spec datas에 추가
  ('core/research/packs', 'core/research/packs'),

  # quality_contract.py:67 교체
  import sys as _sys
  _BASE = Path(_sys._MEIPASS) if getattr(_sys, "frozen", False) else Path(__file__).parent
  _PACKS_DIR = _BASE / "core" / "research" / "packs"
  ```

---

#### 3. [ACCEPT] [High] 빈 `ChecklistMerger.merge()` 결과가 quality gate를 무음 통과

- **Critic**: "모든 항목 `id=''`이면 `{}` → `[]` 조용히 반환. Rule 5 선언만 있고 강제 없음."
- **Cross**: "`researcher.py:971-974`에서 빈 체크리스트 → `_domain_checklist = []` → gap 계산 스킵 → 'no checklist means no gaps' 기존 실패 모드 재현"
- **Judgment**: 양쪽이 동일 결과(빈 리스트 통과)를 독립 경로로 확인. Cross 리뷰어가 실행 흐름(`researcher.py:612 → 971-978 → 1062-1063`)까지 추적해 실제 영향을 검증함. High로 상향.
- **Action Required**:
  ```python
  # checklist_merger.py merge() 끝
  result = list(merged.values())
  if not result:
      raise QualityContractBuildError("ChecklistMerger produced empty checklist")
  return result
  ```

---

#### 4. [ACCEPT] [Medium] `_load_pack` — 모든 예외를 `[]`로 소멸

- **Critic**: "YAML 구문 오류·권한 오류가 모두 빈 리스트로 전환. Finding 2와 결합 시 원인 추적 불가. H3 수정 이력의 동일 패턴 재도입."
- **Cross**: "not flagged"
- **Judgment**: 증거 충분. Finding 2(packs 파일 부재)와 결합하면 `QualityContractBuildError` 원인이 datas 누락인지 YAML 손상인지 구분 불가. H3 수정 이력과 정확히 동일한 패턴이 신규 파일에 재도입됨.
- **Action Required**:
  ```python
  except Exception as e:
      logging.getLogger(__name__).warning("Failed to load pack %s: %s", path, e)
      return []
  ```

---

#### 5. [HOLD] [Medium] `llm_addition.reason` 규칙 선언만 있고 강제 없음

- **Critic**: "`merge()`가 `reason=''`인 llm_addition을 그대로 통과시킴"
- **Cross**: "HOLD — 현재 `source='llm_addition'` 생산자가 없어 런타임 영향 없음. LLM addition 연결 시점에 강제할 것"
- **Judgment**: 현재 caller가 없음을 Cross가 확인. 당장 BLOCK 사유는 아니나 규칙 선언과 구현 불일치는 기록. LLM addition 생산자 구현 시 동시에 강제해야 함.
- **Question for Author**: LLM addition 생산자가 언제 연결되는가? 해당 PR에서 강제하거나 TODO 트래킹 중 하나를 명시할 것.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | af.spec hiddenimports — core.research 서브패키지 누락 | Critical | ACCEPT | Critic |
| 2 | YAML packs datas 미등록 + _PACKS_DIR frozen 비호환 | Critical | ACCEPT | Critic |
| 3 | 빈 ChecklistMerger 결과가 quality gate 무음 통과 | High | ACCEPT | Both |
| 4 | _load_pack 예외 전체 소멸 | Medium | ACCEPT | Critic |
| 5 | llm_addition.reason 미강제 | Medium | HOLD | Both |

---

### Recommendations

- **즉시 수정 (BLOCK)**: af.spec에 hiddenimports 4개 + datas 1개 추가, `_PACKS_DIR` frozen-safe 패턴으로 교체
- **즉시 수정 (High)**: `ChecklistMerger.merge()`에 빈 결과 guard — `QualityContractBuildError` raise
- **즉시 수정 (Medium)**: `_load_pack` bare `except`에 `logging.warning` 추가
- **추후 (HOLD)**: LLM addition 생산자 연결 PR에서 `reason` 검증 강제 + 빈 reason 테스트 추가
- Cross 리뷰어가 기각한 Finding 2(domain overlay required 강등)는 `tests/test_quality_contract.py:139-145`로 의도된 동작 확인됨 — 수정 불필요, 주석 명확화만 권장