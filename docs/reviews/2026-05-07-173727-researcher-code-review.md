# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-07 17:37
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Three High-severity findings — two from the critic (condition bug, silent error swallow) and one from the cross reviewer (uncached LLM call in retry boundary). At least one Critical-adjacent finding must be fixed before merge.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] 빈 `keywords_for_gap_check()` 반환 시 갭 체크 무음 스킵

- **Critic**: `_quality_contract is None` 가드로 인해 QC가 존재하지만 빈 체크리스트를 반환할 때 폴백이 실행되지 않음. `_domain_checklist = []`인 채로 recovery loop 즉시 탈출.
- **Cross**: "not flagged"
- **Judgment**: 코드 증거 명확. diff L978의 조건 `if _quality_contract is None and not _domain_checklist:`는 QC 객체가 존재하면 절대 진입하지 않는다. `keywords_for_gap_check()`가 빈 리스트를 반환하는 경우(팩 파일 없음, 불일치 도메인 등)는 실제 발생 가능한 경로다.
- **Action Required**: 조건을 `if not _domain_checklist:`로 단순화. `_quality_contract is None` 분기 제거.

---

#### 2. [ACCEPT] [High] `except Exception: return None` — 모든 런타임 오류 무음 삼킴

- **Critic**: `_build_quality_contract()` L614의 bare `except Exception: return None`이 `ImportError`, `AttributeError`, 버그까지 로그 없이 흡수. Phase 5 경로 전체가 비활성화돼도 탐지 불가.
- **Cross**: "not flagged"
- **Judgment**: code-review.md에 이미 H3 패턴으로 기록된 anti-pattern의 재도입. diff에서 직접 확인 가능. `return None`이 호출부에서 `_load_domain_manifest` 폴백으로 조용히 이어지는 구조가 관찰 불가능성을 높인다.
- **Action Required**: 최소 `logger.warning("QualityContract build failed: %s", e, exc_info=True)` 추가. `ImportError`는 별도 catch로 설치 미완료 경고 명시 권장.

---

#### 3. [ACCEPT] [High] 증거 수집 retry 경계 내 비캐시 LLM 호출

- **Critic**: "not flagged"
- **Cross**: `collect_project_evidence()` → `_build_quality_contract()` → `WorkSpecExtractor.extract()` → `execute_requirement_prompt()` 체인이 `ResearchVerifier.verify_with_retry()`의 `evidence_fn()` 내부에 포함됨. verifier가 `evidence_fn()`을 최대 2회 호출하면(`core/research_verifier.py:334, 344`) WorkSpec LLM 호출이 중복 발화. 회귀 테스트에서 실제 `claude_cli` 호출 확인.
- **Judgment**: 실제 관찰된 회귀 증거가 있으므로 ACCEPT. LLM 호출 비용과 rate limit 관점에서 High. 캐시 없이 retry 루프에 LLM 호출이 묶이는 것은 예측 불가한 지출을 초래한다.
- **Action Required**: `_build_quality_contract()` 결과를 `(task_input, research_plan.mode, research_plan.domain)` 키로 한 번만 계산하고 캐시. 또는 `collect_project_evidence()` 호출 전 단계에서 한 번만 빌드하도록 상위 호출 경로 재조정.

---

#### 4. [ACCEPT] [Medium] Dead import: `QualityContractBuildError` 미사용

- **Critic**: `except Exception:`이 모든 예외를 흡수하므로 `QualityContractBuildError`를 catch하는 블록이 없음. frozen 빌드 `af.spec` hiddenimports에 의도치 않은 의존성 추가.
- **Cross**: "not flagged"
- **Judgment**: diff L603에서 임포트, except 절 어디에도 참조 없음. Finding #2 수정(except 절 분리) 시 자연히 해소될 수 있으므로 #2와 연동해 처리.
- **Action Required**: `QualityContractBuildError`를 별도 `except` 블록으로 분리하거나 임포트에서 제거.

---

#### 5. [ACCEPT] [Low] 폴백 매직 리터럴 미문서화

- **Critic**: `["requirements_coverage", "architecture_rationale"]` 선택 근거 없음. 도메인 무관 범용성 불명확.
- **Cross**: "not flagged"
- **Judgment**: 코드 내 근거 없이 두 문자열이 최악 경로의 갭 체크 기준이 됨. Low severity — 즉각적 버그는 아니나 Finding #1 수정 후 이 폴백의 실제 사용 빈도가 달라진다.
- **Action Required**: 모듈 상수로 추출 + 한 줄 주석.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 빈 keywords_for_gap_check() 폴백 조건 버그 | High | ACCEPT | Critic |
| 2 | except Exception: return None 무음 삼킴 | High | ACCEPT | Critic |
| 3 | retry 경계 내 비캐시 LLM 호출 | High | ACCEPT | Cross |
| 4 | QualityContractBuildError dead import | Medium | ACCEPT | Critic |
| 5 | 폴백 매직 리터럴 미문서화 | Low | ACCEPT | Critic |

---

### Recommendations

- **Finding #1 즉시 수정**: `if _quality_contract is None and not _domain_checklist:` → `if not _domain_checklist:` (1줄 변경)
- **Finding #2 즉시 수정**: `except Exception: return None` → `except Exception as e: logger.warning(...); return None`; `ImportError`를 선행 블록으로 분리
- **Finding #3 캐시 추가**: `_build_quality_contract()` 결과를 evidence 수집 루프 진입 전 단 1회만 실행되도록 보장. `collect_project_evidence()` 시그니처에 pre-built contract를 선택적 인자로 받는 방식도 검토
- **Finding #4는 #2 수정과 묶어서**: except 절 분리 시 `QualityContractBuildError`를 의미있게 catch하거나 임포트 제거
- **Finding #5는 별도 마이너 커밋**: 상수화 + 주석 1줄