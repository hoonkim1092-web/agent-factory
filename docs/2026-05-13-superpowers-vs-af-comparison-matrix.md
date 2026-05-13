# Superpowers vs AF 비교 매트릭스 — Phase B 실측 보고서

> **Status**: Completed (Phase B)
> **Date**: 2026-05-13
> **Author**: Sonnet 4.6 (Phase B 실측)
> **근거 설계문서**: `docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md` §4
> **방법**: Explore agent가 Superpowers 스킬 파일 실독 + AF 코드베이스 grep, 본 문서로 종합

---

## §1 평가 축 정의 (§4.2 재확인)

| 축 | 설명 | 점수 범위 |
|---|---|---|
| **A** | AF 자체 구현 여부 | 0=없음 / 1=부분 / 2=완전 |
| **B** | AF 구현 품질 | 0–10 |
| **C** | Superpowers 패턴의 차별 가치 | 0–10 |
| **D** | 흡수 비용 (pattern-only, §5.2 원칙 기준) | Low / Medium / High |

**흡수 우선순위 결정 규칙** (§4.3):
- **즉시 흡수**: C ≥ 7 AND B ≤ 2 AND D ∈ {Low, Medium}
- **선택적 흡수**: C ≥ 5 AND B ≤ 5 AND D ∈ {Low, Medium}
- **보류**: 그 외 (특히 B ≥ 8 — AF 자체 구현 우수)

---

## §2 14개 스킬 실측 평가 매트릭스

| Superpowers 스킬 | A | B | C | D | 결정 | 근거 요약 |
|---|---|---|---|---|---|---|
| using-superpowers | 1 | 7 | 2 | Low | 보류 | `core/skill_loader.py` + `core/skill_enricher.py`로 AF가 동등한 스킬 디스패치 보유. 명시적 우선순위 규칙만 미흡하나 C=2로 흡수 가치 낮음 |
| **brainstorming** | 0 | 0 | 9 | Medium | **즉시 흡수** | Socratic 9단계 설계 검증 프로세스 — AF 완전 미보유. `core/design_review_utils.py`는 검토 결과 파싱 유틸리티로 brainstorming 대화 프로세스와 무관. C=9, B=0, D=Medium(~80 LOC SKILL.md) |
| writing-plans | 2 | 8 | 3 | High | 보류 | `core/work_item_generator.py` + `core/project_pipeline.py`가 TDD 단위 작업 분해 커버. 완전 코드 포함/검증 일부 미흡하나 B=8로 AF 우수. High 비용 불균형 |
| using-git-worktrees | 1 | 3 | 6 | Low | **선택적** | 4단계 격리 워크스페이스 자동화. Harness 수준의 EnterWorktree 있으나 `core/` 레벨 미구현. C=6 ≥ 5, B=3 ≤ 5, D=Low → 선택적 |
| test-driven-development | 1 | 6 | 8 | Low | 보류 | C=8 높고 D=Low이지만 B=6 > 5로 보류 기준 초과. AF 이미 1000+ 테스트로 TDD 실천 중. 30개 합리화 차단 패턴이 유일한 차별점이나 프로세스 강제는 문서로 해결 가능 |
| subagent-driven-development | 2 | 8 | 5 | High | 보류 | `core/dynamic_orchestrator.py` + `core/agent_runner.py` 병렬 디스패치 동등 수준. D=High, B=8 |
| executing-plans | 2 | 8 | 3 | High | 보류 | `core/executor.py` + `core/project_pipeline.py` 실행 파이프라인 동등. B=8, D=High |
| requesting-code-review | 2 | 9 | 2 | High | 보류(AF우수) | AF 3-tier cross-verification 시스템(af-critic → af-cross-review → af-test-runner)이 우수. subagent 템플릿 패턴 차별점 적음 |
| receiving-code-review | 2 | 9 | 2 | High | 보류(AF우수) | approval_gate.py + review_gate.py가 피드백 승인/거부 체계화. AF 시스템이 더 구조화됨 |
| **systematic-debugging** | 0 | 0 | 10 | Low | **즉시 흡수** | 4단계 디버깅 프레임워크(근본원인→패턴분석→가설→구현) — AF 완전 미보유. `core/intent.py`는 의도 파싱 유틸로 디버깅 프레임워크 아님. C=10, B=0, D=Low(~120 LOC SKILL.md) |
| **verification-before-completion** | 1 | 4 | 8 | Low | **선택적** | Iron Law(검증 전 완료선언 금지) + 12항목 합리화 차단. `core/skill_eval_harness.py`가 부분 검증. C=8 ≥ 5, B=4 ≤ 5, D=Low(~50 LOC) |
| finishing-a-development-branch | 1 | 3 | 6 | Low | **선택적** | 6단계 브랜치 마무리 자동화(환경감지→옵션제시→실행→정리). `core/git_manager.py` 부분 구현. C=6 ≥ 5, B=3 ≤ 5, D=Low |
| dispatching-parallel-agents | 2 | 8 | 4 | Medium | 보류 | `core/dynamic_orchestrator.py` 병렬 디스패치 동등. B=8 > 5. focused task 구조화만 미흡 |
| writing-skills | 1 | 6 | 6 | Medium | 보류 | `core/skill_creator.py` scaffold 있으나 TDD 검증 메커니즘 부족. B=6 > 5로 보류 |

**총계**: 즉시 흡수 2개 / 선택적 흡수 3개 / 보류 9개

---

## §3 §4.4 사전 추정과의 비교

| 스킬 | 사전 추정 결정 | 실측 결정 | 변경 사유 |
|---|---|---|---|
| using-superpowers | 보류 (B=7, C=2) | 보류 | 일치 |
| brainstorming | **즉시** (B=0, C=9, D=Medium) | **즉시** | 일치. D 재확인: Medium(~80 LOC SKILL.md) |
| writing-plans | 보류 (B=8, C=3) | 보류 | 일치 |
| using-git-worktrees | 선택적 (B=5, C=4) | **선택적** | C 상향 조정(4→6): 실제 파일 확인 시 AF core 미구현 확인 |
| test-driven-development | 선택적 (B=6, C=5) | **보류** | B=6 > 5로 보류 기준 적용. 사전 추정은 공식 사용(폐기됨) 기반이었음 |
| subagent-driven-development | 보류 (B=8, C=4) | 보류 | 일치 |
| executing-plans | 보류 (B=8, C=2) | 보류 | 일치 |
| requesting-code-review | 보류(AF우수) | 보류(AF우수) | 일치 |
| receiving-code-review | 보류(AF우수) | 보류(AF우수) | 일치 |
| systematic-debugging | **즉시** (B=0, C=8, D=Low) | **즉시** | 일치. C 상향(8→10): 4단계 완전 프레임워크 확인 |
| verification-before-completion | 선택적 (B=5, C=7) | **선택적** | B 하향(5→4), C 상향(7→8). 결정 동일 |
| finishing-a-development-branch | 보류 (B=6, C=4) | **선택적** | B 하향(6→3), C 상향(4→6). 실측에서 AF git_manager 부족 확인. 결정 변경 |
| dispatching-parallel-agents | 보류 (B=8, C=3) | 보류 | 일치 |
| writing-skills | 보류 (B=7, C=5) | 보류 | 일치. B 하향(7→6), 결정 동일 |

**변경**: test-driven-development 선택적→보류, finishing-a-development-branch 보류→선택적

---

## §4 Phase C 후보 확정

### 4.1 즉시 흡수 (Phase C 1순위, 2개)

| 스킬 | 흡수 형태 | 신규/수정 위치 | 예상 LOC | inspired_by |
|---|---|---|---|---|
| **brainstorming** | Socratic 검증 패턴 → domain-review.md 통합 + SKILL.md 신설 | `docs/work-items/_template/domain-review.md` §Socratic 섹션 추가 | ~80 | `superpowers/brainstorming` |
| **systematic-debugging** | 4단계 디버깅 가이드 SKILL.md 신설 | `skills/systematic_debugging/SKILL.md` | ~120 | `superpowers/systematic-debugging` |

### 4.2 선택적 흡수 (Phase C 2순위, 3개 — 우선순위 순)

| 스킬 | 흡수 형태 | 신규/수정 위치 | 예상 LOC | inspired_by |
|---|---|---|---|---|
| **verification-before-completion** | Iron Law 완료선언 게이트 강화 | `scripts/review_gate.py` 또는 SKILL.md 신설 | ~50 | `superpowers/verification-before-completion` |
| **finishing-a-development-branch** | 6단계 브랜치 마무리 가이드 SKILL.md 신설 | `skills/finishing_branch/SKILL.md` | ~80 | `superpowers/finishing-a-development-branch` |
| **using-git-worktrees** | 4단계 워크스페이스 격리 가이드 SKILL.md 신설 | `skills/git_worktrees/SKILL.md` | ~60 | `superpowers/using-git-worktrees` |

### 4.3 보류 (9개 — 재론 방지용 기록)

| 스킬 | 보류 이유 |
|---|---|
| using-superpowers | AF skill_loader 우수, C=2 낮음 |
| writing-plans | AF work_item_generator 동등, B=8 |
| test-driven-development | B=6>5, AF 이미 TDD 실천 |
| subagent-driven-development | D=High, B=8 |
| executing-plans | B=8, D=High |
| requesting-code-review | AF 3-tier 시스템 우수(B=9) |
| receiving-code-review | AF 시스템 우수(B=9) |
| dispatching-parallel-agents | B=8>5 |
| writing-skills | B=6>5 |

---

## §5 검증 기준 달성 확인 (§4.5)

| # | 검증 항목 | 결과 |
|---|---|---|
| 1 | 14개 모두 평가 완료 | ✅ 14행 완성 |
| 2 | A점수 근거 명시 | ✅ 전 행에 grep 결과/AF 파일 경로 포함 |
| 3 | 우선순위 ≥ 즉시흡수 후보 1개 이상 | ✅ 2개 (brainstorming, systematic-debugging) |
| 4 | Phase C 후보 확정 | ✅ 즉시 2개 + 선택적 3개 = 5개 후보 |

---

## §6 Phase C 진입 조건

Phase C 진입 전 사용자 명시 승인 필요. 진입 범위 옵션:

- **Option A (최소)**: 즉시 흡수 2개만 (brainstorming + systematic-debugging)
- **Option B (권장)**: 즉시 2개 + verification-before-completion 1개 = 3개
- **Option C (전체)**: 즉시 2개 + 선택적 3개 = 5개

예상 총 LOC:
- Option A: ~200 LOC
- Option B: ~250 LOC
- Option C: ~390 LOC

---

## §7 다음 단계

Phase C 작업 (사용자 범위 결정 후):
1. `skills/systematic_debugging/SKILL.md` 신설
2. `docs/work-items/_template/domain-review.md` Socratic 섹션 추가
3. (Option B+) `skills/verification_before_completion/SKILL.md` 또는 `scripts/review_gate.py` 강화
4. 모든 흡수 파일에 `inspired_by:` 메타 추가 (CLAUDE.md §스킬흡수귀속정책)
5. `core/skill_loader.py` 자동 발견 + `data/skill-usage.jsonl` 호출 기록 (§5.3 검증 #3)
