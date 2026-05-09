# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-04 15:13
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: **WARN**

Cross 리뷰는 provider error로 빈 결과(Codex stdin 처리 단계에서 끊김). Critic + diff 직접 검증으로 판정합니다. 핵심 정정(LLM prior → `llm_prior_refs` 슬롯)은 정확하나 **`AF_RESEARCH_LLM_FALLBACK` 토글이 무력화**되었고 회귀 테스트가 두 정정 사이트 중 한쪽만 커버하는 갭이 남아 있습니다. 기능 정확성은 회복됐으므로 BLOCK 아님.

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] `AF_RESEARCH_LLM_FALLBACK` 토글이 의미 상실 — on/off 양 분기가 동일 호출
- **Critic**: `core/researcher.py:714-718, 723-726`에서 `elif AF_RESEARCH_LLM_FALLBACK=="1"` 분기와 `else` 분기가 모두 `llm_prior_refs = self._collect_llm_prior_knowledge(...)`로 귀결. 토글 OFF로 명시 설정해도 LLM prior가 호출됨.
- **Cross**: 응답 없음 (provider error)
- **Judgment**: diff 직접 확인 결과 사실. 정정 전(`web_refs = ...` vs `llm_prior_refs = ...`)에는 토글이 슬롯 결정을 했으나, 정정 후 양쪽이 동일 슬롯·동일 호출이라 토글이 동작에 영향 0. 커밋 `c55fa99e`의 의도("토글 보존")와 코드 의미가 어긋남.
- **Action Required**: 둘 중 하나 결정 후 한 커밋:
  - (a) 토글 살림: `else` 분기에서 호출 제거 (`else: pass`) — 토글 미설정 시 LLM 호출 차단
  - (b) 토글 폐기: `elif`/`else` 통합·환경변수 제거 → Master_Blueprint §0/§12에 deprecate 기록

#### 2. [ACCEPT] [Medium] 회귀 테스트가 두 정정 사이트 중 한쪽만 커버
- **Critic**: `tests/test_research_system_regression.py:90-122`는 `for_mode("fresh_lookup")`(`requires_web=True`)로 첫 번째 elif(researcher.py:710-718)만 진입. 두 번째 정정 사이트(`elif not sufficient`, researcher.py:719-726)는 미커버.
- **Cross**: 응답 없음
- **Judgment**: 테스트 코드 직접 확인 결과 사실. 두 번째 사이트가 추후 회귀(누가 다시 `web_refs`로 되돌림)해도 잡히지 않음.
- **Action Required**: `requires_web=False` + `_is_sufficient=False` 케이스 추가 (예: `for_mode("archive_research")`) — 동일 assertion 반복.

#### 3. [ACCEPT] [Medium] 변경된 주석이 코드 동작과 불일치
- **Critic**: `core/researcher.py:715` 주석 "Tavily 미설정 + fallback 토글: …"이 토글이 분기 결정에 기여한다고 암시하나 실제로는 `else` 분기도 동일 호출. 유지보수자가 토글 역할을 잘못 추론할 위험.
- **Cross**: 응답 없음
- **Judgment**: Finding 1과 동일 근거. Finding 1 결정에 종속.
- **Action Required**: Finding 1 결정 후 주석을 동작과 일치시킴. 토글 폐기 시 주석에서 "fallback 토글" 문구도 제거.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `AF_RESEARCH_LLM_FALLBACK` 토글 무력화 | High | ACCEPT | Critic + diff 검증 |
| 2 | 회귀 테스트가 1/2 사이트만 커버 | Medium | ACCEPT | Critic + 테스트 검증 |
| 3 | 주석이 코드 동작과 불일치 | Medium | ACCEPT | Critic |

### Recommendations

1. **(우선) Finding 1 의사결정** — 토글을 살릴지 폐기할지 사용자 확인. v2 메모리(`project_research_system_gaps.md`)의 G3 개선안은 "WebSearch fallback 추가"라 **토글 폐기·LLM prior 항상 호출** 방향이 자연스러움.
2. **Finding 2 테스트 보강** — `archive_research` 모드 + `_is_sufficient=False` 케이스 5분 작업.
3. **Finding 3** — Finding 1 결정 후 주석 정합화.
4. Cross 리뷰 provider error는 별건 — Codex CLI stdin 처리 또는 hook launcher 측 회귀 가능성. 다음 라운드에서 재시도 권장.
5. **WARN advisory** — 자동 수정 의무 없음 (CLAUDE.md Phase 0 정책). 사용자 결정에 따라 후속 commit.