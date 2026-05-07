# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-07 17:33
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. High findings exist — the keyword/item semantic mismatch (Finding 5) effectively makes the Phase 5 gap-check path behave incorrectly for all multi-keyword contracts. Deployable, but three of these five are straightforward to fix before the next iteration.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Silent `except Exception: return None` — 에러 마스킹
- **Critic**: "`core/researcher.py:616` — `except Exception: return None`이 `ImportError`, `AttributeError`, 로직 버그 등 모든 예외를 삼킴. 로그·메트릭 없어 운영 중 회귀 원인 구분 불가."
- **Cross**: not flagged
- **Judgment**: Critic 단독이나 근거가 명확하다. code-review.md §High의 "Silent fallback" 패턴과 동일하고, diff에서 직접 확인된다. 의도된 실패(계약 미지원 도메인)와 버그(모듈 임포트 실패)를 같은 코드 경로로 처리하면 안 된다.
- **Action Required**:
  ```python
  except QualityContractBuildError:
      return None
  except Exception as e:
      logger.warning("_build_quality_contract failed: %s", e, exc_info=True)
      return None
  ```

#### 2. [ACCEPT] [Medium] `QualityContractBuildError` 임포트 후 미사용 — 설계 의도 소실
- **Critic**: "`core/researcher.py:604` — 임포트됐지만 메서드 본문에서 참조 안 됨. 원래 설계는 예상 실패(`QualityContractBuildError`)와 예상치 못한 예외를 구분하려 했을 것."
- **Cross**: not flagged
- **Judgment**: Finding 1 수정 시 자동 해결된다 — `except QualityContractBuildError`로 사용하거나 제거. 단독 finding이지만 diff에서 명확히 확인된다.
- **Action Required**: Finding 1 수정에 포함됨. `except QualityContractBuildError: return None`으로 사용하면 해소.

#### 3. [ACCEPT] [Medium] 빈 `keywords_for_gap_check()` 결과 — 하드코딩 폴백 우회
- **Critic**: "`core/researcher.py:969-977` — 가드 조건이 `_quality_contract is None and not _domain_checklist`. 계약 빌드 성공(`_quality_contract` is not None)이지만 `keywords_for_gap_check()`가 `[]`를 반환하면 폴백 미발화 → `_identify_unmet_gaps`가 빈 체크리스트로 실행, 갭이 항상 없는 것처럼 동작."
- **Cross**: not flagged (별도 각도 — 키워드/아이템 의미론 이슈로 접근)
- **Judgment**: 코드 경로가 diff에서 직접 확인된다. `_quality_contract is None` 조건 제거로 단순 해결.
- **Action Required**:
  ```python
  if not _domain_checklist:
      _domain_checklist = ["requirements_coverage", "architecture_rationale"]
  ```

#### 4. [ACCEPT] [High] Lazy 임포트 — `af.spec` hiddenimports 미검증
- **Critic**: "`core/researcher.py:601-604` — 메서드 바디 내 lazy import는 PyInstaller 정적 분석에서 누락. `core.research.work_spec`, `quality_contract`, `checklist_merger`가 `af.spec` hiddenimports에 없으면 frozen 빌드에서 `except Exception: return None`이 매번 조용히 발화 — Phase 5 경로가 `dist/af/af.exe`에서 사실상 dead."
- **Cross**: not flagged
- **Judgment**: AF 배포 환경에서 고빈도로 발생하는 패턴이다. Finding 1과 조합하면 frozen 빌드 회귀를 로그 없이 영원히 놓칠 수 있다.
- **Action Required**: `af.spec` hiddenimports에 추가:
  ```python
  'core.research.work_spec',
  'core.research.quality_contract',
  'core.research.checklist_merger',
  ```

#### 5. [ACCEPT] [High] 키워드 vs. 아이템 의미론 불일치 — 갭 검사 로직 깨짐
- **Critic**: not flagged
- **Cross**: "`core/researcher.py:973` — `keywords_for_gap_check()`는 동의어 플랫 리스트 반환(poker 계약: 20 체크리스트 항목 → 117 키워드). `_is_sufficient()`가 70% 이상 키워드 존재를 요구하고, `_identify_unmet_gaps()`가 각 누락 동의어를 독립 갭으로 보고, `_emit_coverage_report()`가 `missing >= 3` 기준 block → '임의 동의어 하나 충족 시 항목 만족'이 '대부분 동의어 존재 필요'로 역전."
- **Judgment**: Cross 단독이나 수치 근거(20 items → 117 keywords)가 명확하다. 현재 구현에서 Phase 5 갭 검사는 모든 다중-키워드 계약에서 의도와 반대로 동작한다. 아키텍처 수정이 필요하다.
- **Action Required**: `keywords_for_gap_check()` 반환 타입을 `dict[str, list[str]]` (`{item_id: [synonym, ...]}`)로 변경하거나, `QualityContractItem` 객체를 경계까지 전달. `_identify_unmet_gaps`는 항목 단위로 평가 — 항목 내 임의 키워드 하나 매칭 시 충족으로 처리. 커버리지 리포트는 raw 동의어 문자열이 아닌 item_id로 출력.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Silent `except Exception` 에러 마스킹 | High | ACCEPT | Critic |
| 2 | `QualityContractBuildError` 미사용 임포트 | Medium | ACCEPT | Critic |
| 3 | 빈 체크리스트 폴백 우회 | Medium | ACCEPT | Critic |
| 4 | af.spec hiddenimports 누락 | High | ACCEPT | Critic |
| 5 | 키워드/아이템 의미론 불일치 | High | ACCEPT | Cross |

### Recommendations

- **즉시 수정 (merge 전)**: Finding 1+2 (예외 구분 + 로깅), Finding 3 (폴백 조건 단순화)
- **배포 전 필수**: Finding 4 — frozen 빌드 테스트로 `_build_quality_contract` 실제 실행 확인
- **다음 이터레이션**: Finding 5 — `keywords_for_gap_check()` 반환 타입 변경은 downstream 인터페이스 수정 동반, 별도 PR 권장
- Finding 2는 Finding 1 수정 시 자동 해소됨 — 별도 작업 불필요