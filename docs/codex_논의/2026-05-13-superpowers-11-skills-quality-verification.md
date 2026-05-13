# Superpowers 11개 스킬 흡수 분석 + AF 우위 품질 검증

- 작성일: 2026-05-13
- 작성자: Claude Opus 4.7 (대화 세션, 사용자 hoon.kim)
- 검증 상태: **정적 분석 + 코드 실측 (file:line 명시)**. 런타임 실측 미수행
- 선행 문서:
  - `docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md` (통합 설계, BLOCK)
  - `docs/reviews/2026-05-11-163128-...design-review.md` (BLOCK 11건)
  - `docs/2026-04-08-agent_factory_harness_gsd_superpowers_analysis.md` (초기 분석)
  - `docs/2026-04-22-phase-a-gap-analysis.md` (Phase A 갭)
- 후속: 5/11 설계서 v2 작성 시 본 문서 §3·§4의 품질 검증 결과를 §4.4 비교 매트릭스에 인용

---

## 0. 문서 목적

사용자가 Superpowers 스킬 11개 추가 흡수를 검토 요청. 본 문서는:
1. **11개 항목 분류** — 5/11 설계서 §4.4 사전 평가 기반
2. **보류 6개의 AF 대응 매핑** — 충돌·연결 영역 식별
3. **AF 우수/동등 판정의 품질 근거** — 코드 실측 (단순 토큰 절감이 아님을 검증)
4. **우선 흡수 5개의 구현 위치 + 효과**
5. **5/11 BLOCK 11건과의 우선순위**

---

## 1. 사용자가 언급한 11개 스킬

| Superpowers 스킬 | 분류 (§4.4) | 점수 |
|---|---|---|
| brainstorming | 즉시 흡수 | 9 |
| systematic-debugging | 즉시 흡수 | 8 |
| verification-before-completion | 선택적 흡수 | 3 |
| test-driven-development | 선택적 흡수 | 1 |
| using-git-worktrees | 선택적 흡수 | 1 |
| writing-plans | 보류 (AF 동등) | -1 |
| requesting-code-review | 보류 (AF 우수) | -3 |
| receiving-code-review | 보류 (AF 우수) | -3 |
| dispatching-parallel-agents | 보류 (AF 동등) | -2 |
| subagent-driven-development | 보류 (AF 동등) | -1 |
| finishing-a-development-branch | 보류 (AF 동등) | 0 |

→ **5개 흡수 가치, 6개 보류**. 11개 일괄 흡수는 중복.

---

## 2. 보류 6개의 AF 대응 매핑

| Superpowers 스킬 | AF 대응 메커니즘 | 핵심 파일 |
|---|---|---|
| requesting-code-review | 3-Tier Review-Gate | `scripts/review_gate.py:65-67`, `core/review_runner.py` |
| receiving-code-review | WarningRegistry + escalation_phase 추적 | `core/warning_registry.py:71`, `core/escalation_evaluator.py` |
| dispatching-parallel-agents | DynamicOrchestrator rule-based + LLM intervention 트리거 | `core/dynamic_orchestrator.py:307`, `:311` |
| subagent-driven-development | AgentSpecializer + 페르소나 deepcopy + 스킬 필터링 | `core/agent_specializer.py:23`, `:44-58` |
| writing-plans | ProjectPlanningDirector + work_item_generator + 3-Tier Quality Gate | `core/project_planning_director.py`, `core/rubric_compiler.py`, `core/critic_skill_router.py` |
| finishing-a-development-branch | pre_commit_review + Blueprint auto-sync + review_gate enforcement | `.githooks/pre-commit`, `core/hooks/code_review_doc.py` |

---

## 3. AF 우수/동등 판정의 품질 검증 (코드 실측)

> **검증 원칙**: 토큰 비용 절감은 *부수 효과*. 우위 근거는 *결함 검출 능력, 결정 신뢰도, 강제력, 컨텍스트 품질* 4축에서 찾는다.

### 3.1 requesting-code-review — AF 우수 (품질 multiplier 3중)

**Superpowers**: 단일 reviewer가 SKILL.md 체크리스트로 리뷰.

**AF 실측** (`scripts/review_gate.py:65-67`):
```python
1: "af-test-runner",       # 구조·테스트
2: "af-critic",            # 전문가 비평 (Sonnet)
3: "af-cross-review",      # 멀티 프로바이더 fan-out
```

**품질 우위 근거** (토큰과 무관):

| 축 | Superpowers 1-tier | AF 3-Tier |
|---|---|---|
| 결함 종류 catch | reviewer의 *단일 관점*만 | 구조/논리/외부 시각 *3종 직교* |
| 동일 에이전트 self-review 사각지대 | 존재 | Tier 3에서 *다른 vendor* 강제 → 같은 사각지대 회피 |
| 합의 메커니즘 | 없음 | 4-Round Deliberation (`docs/reviews/` accumulation) |
| 자동 BLOCK 판정 | 사람이 해석 | verdict 필드 → commit 차단 자동화 |

→ **품질 multiplier**: Tier 2(critic)는 Tier 1(test-runner)이 못 잡는 *논리 결함*을 catch, Tier 3(cross-review)는 Tier 2의 *vendor 편향*을 catch. 토큰을 3배 쓰지만 *결함 검출 곡선*이 비선형 상승.

### 3.2 receiving-code-review — AF 우수 (선언 vs 강제 차이)

**Superpowers**: 피드백 반영 가이드 (사람이 따르는 권고).

**AF 실측** (`core/warning_registry.py:181-186`):
```python
# P4a: single-load policy (split read 금지 — escalation_phase 마커 + decision 동기)
from core.escalation_evaluator import ...
from core.escalation_decision_report import ...
```

**품질 우위 근거**:

| 축 | Superpowers 권고 | AF WarningRegistry |
|---|---|---|
| 강제력 | human-followed (생략 가능) | **commit 차단** (`AF_SKIP_REVIEW_GATE=1` 없이 우회 불가) |
| 진행 추적 | 체크리스트 항목 | escalation_phase P1~P4 자동 진화 |
| Fail-closed 보증 | 없음 | P2 read_block_decision (단일 진실원) |
| BLOCK 흡수 이력 | 사람이 메모 | `docs/reviews/` 자동 누적 + 회귀 검사 |

→ **품질 우위**: 결함이 *반영되었음을 시스템이 검증*. Superpowers는 "사람이 했다"는 자기 신고. 메모리 `project_auto_approve_block_followup.md`의 "BLOCK 5건 흡수 + 24+10 회귀 PASS"가 이 강제력의 산물.

### 3.3 dispatching-parallel-agents — AF 동등 이상 (deterministic + adaptive)

**Superpowers**: LLM이 매번 *어느 서브에이전트에게 무엇을 줄지* 결정.

**AF 실측** (`core/dynamic_orchestrator.py:307-337`):
```python
def _dispatch_from_board(...):
    """Rule-based task dispatch. Board + dependency 기반, LLM 토큰 0."""
    return self._fallback_next_tasks(...)

def _needs_llm_intervention(self, cycle, workspace):
    if cycle == 1: return True              # 첫 사이클
    if blockers: return True                # 블로커 존재
    if cycles_since >= self._stall_threshold: return True  # Stall
    if recent_failures >= 3: return True    # 전략 피벗 필요
```

**품질 우위 근거** (토큰 절감은 부수효과):

| 축 | Superpowers LLM dispatch | AF rule-based + LLM trigger |
|---|---|---|
| 결정 재현성 | LLM 비결정 (같은 board → 다른 dispatch) | **deterministic** (같은 board → 같은 dispatch) |
| 디버깅 가능성 | LLM 응답 trace 필요 | 룰 코드 직접 추적 |
| Hallucination 위험 | 존재 (없는 task 생성 가능) | 0 (board에 있는 task만 dispatch) |
| LLM 활용 정밀도 | 매번 발화 → 일상 결정에 흐려짐 | **품질이 필요한 4 시점에만 발화** (cycle 1, 블로커, stall, 3회 실패) |

→ **품질 우위**: LLM을 *언제 쓸지*를 결정함으로써, LLM이 *진짜 필요한 결정*(피벗·blocker 해결)에 집중. Superpowers는 일상 dispatch까지 LLM이 처리해 *주의 분산*.

### 3.4 subagent-driven-development — AF 동등 이상 (컨텍스트 품질)

**Superpowers**: Fresh context로 서브에이전트 fork (stateless).

**AF 실측** (`core/agent_specializer.py:44-58`):
```python
agent = copy.deepcopy(base_agent)                       # state isolation
agent["system_ko"] = self._build_task_prompt(...)       # task + persona + workspace
agent["skills"] = self._select_task_skills(...)         # 12-cap filtering
```

`_build_task_prompt` 섹션 (`:72-99`):
- Section 1: 축약된 역할 페르소나 (PM/Architect/Dev/Designer/Researcher)
- Section 2: 현재 작업 (task_id / 제목 / 단계 / 지시 / 완료기준 / 산출물)
- Section 3 이후: 에피소드 메모리 주입 (M3 KnowledgeInjectionHook 경유)

**품질 우위 근거**:

| 축 | Superpowers stateless fork | AF AgentSpecializer |
|---|---|---|
| 페르소나 일관성 | 매번 prompt에서 재정의 | base_agent에 영속, deepcopy로 격리 |
| 작업 정보 밀도 | 자연어 지시만 | **완료기준 + 산출물 + acceptance** 구조화 |
| 스킬 노출 | 전체 노출 | **작업 관련 12개만** (점수 0.35×0.40×0.25) |
| 메모리 회상 | 없음 | EpisodeMatcher Jaccard 0.4 임계 (단, M8: 현재 wire-up 미완 — `feedback_post_edit_checklist.md` 참조) |

→ **품질 우위**: 컨텍스트의 *밀도*. 단, `agent_specializer.py`에 memory 심볼 0건이라는 갭(M8)은 5/11-B 메모리 wire-up Step 0~1로 해소 예정.

### 3.5 writing-plans — AF 동등 이상 (5모듈 검증 체인)

**Superpowers**: writing-plans SKILL.md 단일.

**AF 실측** (`core/project_planning_director.py` + `core/work_item_generator.py` + 3-Tier Quality Gate):
- `ProjectPlanningDirector.generate_research_brief()` → role_plan → task_board
- `work_item_generator.generate_work_items()` 3-stages 병렬 (plan / spec/design / outline+tasks)
- T1 `RubricCompiler` 구조 검사 + 1회 refine
- T2 `DocumentReviewSession` critic
- T3 cross/judge (provider ≥ 2)

**품질 우위 근거**:

| 축 | Superpowers writing-plans | AF 5-module chain |
|---|---|---|
| 진실원 일관성 | 사람이 plan 작성 | brief/role/task 단방향 의존 강제 |
| 구조 검증 | reviewer 판단 | RubricCompiler 자동 (필드 누락 차단) |
| 도메인 합치 | 없음 | Domain Spec Gate (P2 C1+C3+C4) |
| 추적성 | 없음 | TraceabilityGenerator 자동 ADR 링크 |
| 외부 검증 | 없음 | T3 multi-provider cross/judge |

→ **품질 우위**: plan이 *기계적으로 검증된 산출물*. 사람이 작성한 plan에서 누락되는 acceptance/artifacts/traceability가 강제됨.

### 3.6 finishing-a-development-branch — AF 동등 이상 (선언 vs 강제)

**Superpowers**: 브랜치 마무리 체크리스트 (PR 전 점검 항목).

**AF 실측**:
- `.githooks/pre-commit` → blueprint_updater + pre_commit_review
- `core/hooks/code_review_doc.py:125-126` git diff → docs append (성공 시)
- review_gate Tier 1~3 강제 발화 (`scripts/review_gate.py:206-415`)

**품질 우위 근거**:

| 축 | Superpowers 체크리스트 | AF pre-commit hook |
|---|---|---|
| 강제력 | 사람이 따름 | 미스테이지 시 commit 차단 |
| Blueprint 동기 | 사람 책임 | blueprint_updater 자동 sync |
| 리뷰 통과 보증 | 자기 신고 | review_gate Tier 1~3 verdict 검증 |
| 우회 추적 | 없음 | `AF_SKIP_REVIEW_GATE=1` → hook_events.log 기록 |

→ **품질 우위**: *선언적 권고*가 아닌 *강제 시스템*. 우회조차 추적됨 (감사 추적, audit trail).

### 3.7 종합 — 품질 우위 4축 요약

| AF 우위 축 | 적용 항목 |
|---|---|
| **다중 관점 검증** (vendor 편향 회피) | requesting-code-review (3-Tier) |
| **강제력 + 자동 추적** (선언 → 강제) | receiving-code-review, finishing-a-development-branch |
| **결정 신뢰도** (deterministic + adaptive LLM) | dispatching-parallel-agents |
| **컨텍스트 품질** (페르소나·메모리·스킬 필터링) | subagent-driven-development |
| **기계적 검증 체인** (다단계 자동) | writing-plans |

→ **토큰 절감은 부수 효과**. 모든 우위는 *결함 검출, 강제력, 컨텍스트 밀도* 등 품질 차원에서 도출.

---

## 4. 우선 흡수 5개의 구현 위치 + 효과

| # | Superpowers 스킬 | AF 흡수 위치 | LOC | 효과 |
|---|---|---|---|---|
| 1 | brainstorming | `docs/work-items/_template/domain-review.md` §1.5 Socratic Questions | ~80 | 잘못된 요구사항이 work-item 되기 전 차단 |
| 2 | systematic-debugging | `skills/systematic_debugging/SKILL.md` (AF 자체 형식) | ~120 | FSA L1 retry 진입 시 추측 디버깅 행동 감소 |
| 3 | verification-before-completion | `core/approval_gate.py` 또는 `scripts/review_gate.py` verdict 강화 | ~50 | 자율 모드 검증 갭 부분 해소 |
| 4 | test-driven-development | systematic-debugging SKILL.md에 "재현 테스트 먼저" 섹션 통합 | 0 (통합) | 한정적 (Tier 1이 이미 강제) |
| 5 | using-git-worktrees | docs 가이드만 | 0 | 신규 사용자 onboarding |

**총 ~250 LOC**, Phase A 안에 포함 가능.

---

## 5. 5/11 BLOCK 11건과의 우선순위

5/11 설계서가 cross-review BLOCK 판정. Phase A 진입 전 Critical 2건 해소 필수.

| # | Severity | 항목 | 해소 방법 |
|---|---|---|---|
| 1 | 🔴 Critical | `work_item_kind` 식별자 불일치 | `core/control/work_kind.py:9` 실제값(`feature_update`)으로 §3.3/§10.2 교체 |
| 2 | 🔴 Critical | ApprovalGate ↔ work_kind 통합 미명세 | `core/approval_gate.py:79-94` 시그니처 i/ii/iii 3택 결정 |
| 3 | 🟠 High | dead code 영향 범위 오판 | 옵션 A(즉시 제거): `core/skill_pack_bootstrapper.py` + `af.spec:122` + `tests/test_compact_step2.py` + `Master_Blueprint.md` §3.8.4 |
| 4 | 🟠 High | Phase C LOC 자가모순 | §5.1 LOC에 ±50% 표기 또는 실측 첨부 |
| 5 | 🟠 High | PROJECT_CONTEXT stale 방지 누락 | Phase A에 30일 trigger 또는 cross-review 체크리스트 추가 |
| 6~11 | 🟡 Medium/Low | ADR race / verdict trigger / frozen build / MIT attribution / 점진 활성 거버넌스 / 체크리스트 ✅ | 텍스트 수정 |

---

## 6. 권장 실행 순서

| # | 작업 | 일정 |
|---|---|---|
| 1 | 5/11 설계서 v2 작성 (BLOCK 11건 흡수) | 0.5일 |
| 2 | Codex cross-review 재시도 (5/13 01:00 KST 이후) | 1회 |
| 3 | Phase A 구현: Domain Gate 인프라 (PROJECT_CONTEXT.md + ADR-0001 + domain-review.md + approval_gate 정책) | 3.5일 |
| 4 | 흡수-1 brainstorming → domain-review.md §1.5 통합 | Phase A 안에 포함 |
| 5 | 흡수-2 systematic-debugging SKILL.md 신설 + FSA L1 진입 시 우선 로드 | 1일 |
| 6 | 흡수-3 verification-before-completion approval_gate verdict 강화 | 0.5일 |
| 7 | 흡수-4·5 (TDD, worktrees) 가이드만 | 0 |
| 8 | 보류 6건은 **영구 보류** | — |

**총 ~5.5일 (Phase A 3.5일 + 흡수 2일)**, LOC **~480** (5/11 §7.4 ~910 LOC에서 보류 6건 ~430 LOC 제외).

---

## 7. 결론

1. **5/11 설계서 §4.4 사전 평가가 옳다** — 14개 중 즉시 흡수 2 / 선택적 3 / 보류 9
2. **보류 6개에 대한 AF 우위는 품질 차원** — 토큰 절감은 부수 효과. 4축(다중 검증·강제력·결정 신뢰도·컨텍스트 품질)에서 모두 우위
3. **시급한 건 11개 흡수가 아니라 5/11 Critical 2건 해소** — 5분짜리 텍스트 수정이 Phase A 첫 줄을 막고 있음
4. **흡수 5개는 Phase A 안에 자연 통합** — brainstorming(domain-review §1.5) + systematic-debugging(SKILL.md) + verification(approval_gate)

---

## 8. 본 문서의 한계

- **정적 분석 + 코드 실측**. 런타임 실측(pytest, 실 워크플로 트리거) 미수행
- 5/11 설계서의 §4.4 점수 자체는 사전 추정 — Phase B 실측으로 ±20% 변동 가능
- 보류 6개의 AF 우위는 *현재 코드 상태* 기준. AgentSpecializer 메모리 wire-up(M8)이 미완이라 §3.4의 "메모리 회상" 부분은 가설값
- Superpowers 자체 코드는 본 분석에서 *공식 SKILL.md 설명*만 참조 (실제 obra/superpowers 레포 읽지 않음)
