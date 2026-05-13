# Superpowers / GSD 품질 워크플로우 분석과 AF 적용 판단

작성일: 2026-05-13
분석 대상:
- `docs/codex_논의/2026-05-13-superpowers-11-skills-quality-verification.md`
- `docs/reviews/2026-05-13-142940-2026-05-13-superpowers-11-skills-quality-verification-design-review.md`
- `docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md`
- `docs/reviews/2026-05-11-163128-2026-05-11-domain-gate-superpowers-pattern-absorption-design-design-review.md`
- `docs/2026-04-22-phase-a-gap-analysis.md`
- `docs/2026-04-08-agent_factory_harness_gsd_superpowers_analysis.md`
- `docs/archive/code_review/26_0409_gsd_superpowers_analysis_review.md`
- `docs/archive/research/2026-03-09_gsd_deep_dive_vs_agent_factory.md`

분석 목적:

```text
Superpowers/GSD 패턴 중 AF에 실제로 필요한 것을 선별하고,
기존 AF 기능과의 충돌 지점, 연결 문제, 적용 효과를 판단한다.
```

---

## 1. 핵심 결론

Superpowers/GSD에서 지금 AF가 흡수해야 할 것은 스킬 패키지 자체가 아니다.

핵심은 다음이다.

```text
추측 금지
계획 명시
격리 실행
테스트 우선
검증 증거
리뷰 반영
브랜치 정리
```

즉 AF가 받아들여야 하는 것은 외부 코드가 아니라 **품질 워크플로우의 명시성**이다.

AF는 이미 많은 부품을 가지고 있다.

- planning
- role/task board
- DynamicOrchestrator
- AgentSpecializer
- 3-Tier review gate
- verification-report
- memory / continuity
- context fork
- semantic skill matching
- skill eval harness

하지만 GSD처럼 다음 루프가 사용자와 시스템 양쪽에 선명하게 보이지 않는다.

```text
plan
  -> critique
  -> revise
  -> execute
  -> verify
  -> UAT
  -> gap replan
```

따라서 최종 판단은 다음이다.

```text
Superpowers는 통째로 붙이지 말고,
AF 기존 엔진 위에 명시적 품질 계약으로 흡수해야 한다.
```

---

## 2. 분석 단계

### 2.1 Superpowers 스킬 자체 확인

사용자가 언급한 핵심 스킬은 다음 11개다.

| 스킬 | 핵심 의미 |
| --- | --- |
| `brainstorming` | 요구사항을 질문으로 검증 |
| `systematic-debugging` | root cause 찾기 전 수정 금지 |
| `verification-before-completion` | 증거 없이 완료 선언 금지 |
| `writing-plans` | 큰 기능을 작은 구현 작업으로 분해 |
| `test-driven-development` | 실패하는 테스트를 먼저 작성 |
| `requesting-code-review` | 완료 후 리뷰 요청 |
| `receiving-code-review` | 리뷰 피드백을 맹신하지 않고 검증 후 반영 |
| `using-git-worktrees` | 기능별 격리 작업공간 |
| `finishing-a-development-branch` | merge/PR 전 테스트와 정리 |
| `dispatching-parallel-agents` | 독립 문제를 병렬 에이전트로 처리 |
| `subagent-driven-development` | 작업 단위 구현 + spec review + code review |

이 스킬들의 공통 철학은 다음이다.

```text
임의 추측을 줄이고,
각 단계마다 검증 가능한 산출물과 증거를 요구한다.
```

### 2.2 5/13 Superpowers 문서 검토

`docs/codex_논의/2026-05-13-superpowers-11-skills-quality-verification.md`는 방향성은 좋다.

하지만 그대로 구현 기준으로 삼으면 안 된다.

이 문서는 이미 자체 design review에서 `BLOCK` 판정을 받았다.

주요 문제:

1. `core/project_planning_director.py` 파일이 존재하지 않는다.
   - 실제 `ProjectPlanningDirector`는 `core/bootstrap_roles.py`에 있다.

2. `AgentSpecializer`의 skill cap을 12개로 적었지만 실제 코드는 8개다.
   - `core/agent_specializer.py`는 `return result[:8]`을 사용한다.

3. `AgentSpecializer` memory wire-up 미완이라는 주장은 stale이다.
   - 현재 코드는 `_fetch_episode_context()`를 통해 episodic memory를 조회한다.

4. `domain-review.md` 템플릿이 없다.
   - `docs/work-items/_template/` 목록에도 없다.

5. `work_item_generator`는 extra template로 3개만 복사한다.
   - `verification-report.md`
   - `change-request.md`
   - `bug-fix-spec.md`

6. `review_gate`는 `.py` 파일이 없으면 `no-py-files`로 통과한다.
   - 즉 `SKILL.md`, 템플릿, 문서 변경은 review gate 강제 대상에서 빠질 수 있다.

따라서 해당 문서는 참고 자료로는 유용하지만, v2 정정 전에는 구현 기준으로 사용하면 안 된다.

### 2.3 5/11 Domain Gate 설계 검토

`docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md`의 핵심 방향은 타당하다.

목표:

```text
Phase 2 Domain Gate 신설
Superpowers 패턴 자체 흡수
외부 import 금지
```

하지만 design review에서 `BLOCK`이 나왔다.

핵심 BLOCK 원인:

1. `work_item_kind` 식별자 불일치
   - 설계서: `feature`, `architecture-change`
   - 실제 코드: `new_project`, `maintenance`, `bugfix`, `feature_update`, `refactor`

2. `ApprovalGate`가 `work_kind`를 받지 않는다.
   - 현재 `ApprovalGate.__init__()`은 `workspace`, `slug`, `runtime_workspace`만 받는다.

3. `SkillPackBootstrapper` dead code 처분 판단이 불명확하다.

4. `PROJECT_CONTEXT.md` stale 방지가 Phase A에 없다.

5. ADR 번호 규칙, verdict trigger 시점, frozen build 경로, attribution, 단계 전환 지표가 미정이다.

즉 Domain Gate 방향은 맞지만, 구현 계약이 아직 부족하다.

---

## 3. 기존 AF 기능과 대응 관계

### 3.1 이미 강한 영역

AF는 다음 영역에서 Superpowers/GSD보다 이미 강하거나 동등하다.

| 영역 | AF 대응 |
| --- | --- |
| multi-agent orchestration | `DynamicOrchestrator` |
| task specialization | `AgentSpecializer` |
| review gate | 3-Tier review gate |
| verification report | `verification-report.md` + checker |
| skill eval | `skill_eval_harness.py`, `skill_preflight.py` |
| context fork | `core/hooks/context_fork.py` |
| semantic matching | `semantic_embedder.py`, `skill_loader.py` |
| MCP adapter | `core/mcp_adapter.py` |
| session continuity | manifest / resume brief / memory |

그래서 Superpowers를 외부 패키지로 직접 붙이는 것은 중복과 충돌이 크다.

### 3.2 실제로 약한 영역

AF가 약한 지점은 기능 부재가 아니라 **품질 루프의 전면화 부족**이다.

GSD가 더 선명한 지점:

1. planner와 checker가 분리되어 있다.
2. plan 자체를 critique하고 revise하는 루프가 명시적이다.
3. verification이 goal-backward로 작동한다.
4. UAT가 1급 문서다.
5. 실패하면 gap planning으로 되돌아간다.

AF는 대응 기능이 흩어져 있다.

```text
approval gate
QA role
review gate
verification-report
cross verification
resume brief
memory
```

이 조각들을 하나의 명시적 workflow contract로 묶어야 한다.

---

## 4. 11개 스킬별 판단

### 4.1 강제 흡수 권장

#### 1. brainstorming

판단: 흡수 필요

이유:

- 요구사항이 잘못 이해된 상태에서 work-item으로 승격되는 문제를 줄인다.
- Domain Gate와 자연스럽게 맞는다.

권장 적용:

```text
docs/work-items/_template/domain-review.md
  -> Socratic Questions 섹션 추가
  -> 질문/답변/판정 필드를 machine-readable하게 정의
```

필수 전제:

- `domain-review.md` 파일을 실제로 만들어야 한다.
- `work_item_generator`가 해당 템플릿을 복사해야 한다.
- `ApprovalGate`가 해당 verdict를 읽을 수 있어야 한다.

#### 2. systematic-debugging

판단: 흡수 필요

이유:

- AF의 FSA/ISE 루프는 실패를 자동 복구하려고 한다.
- 이때 root cause 없이 “한 번 더 고쳐보기”로 흐르면 비용과 회귀가 커진다.

권장 적용:

```text
skills/systematic_debugging/SKILL.md
FSA L1 retry 진입 전 root-cause checklist
ISE 분석 prompt에 evidence-first 규칙 주입
```

효과:

- 추측 디버깅 감소
- 실패 원인 기록 품질 상승
- FSA L2/L3/L4 판단 정확도 상승

#### 3. verification-before-completion

판단: 흡수 필요

이유:

- AF에는 이미 `verification-report.md`, `verify_handoff_checker.py`, `ApprovalGate.apply_verification_verdict()`가 있다.
- 하지만 경로가 흩어져 있고 schema/caller contract가 명확하지 않다.

권장 적용:

```text
verification-report.md schema 고정
e2e_command 필수
verdict 필수
BLOCK이면 approval-gate 자동 차단
```

현재 대응 코드:

- `scripts/verify_handoff_checker.py`
- `.githooks/pre-commit`
- `scripts/nightly_tick.py`
- `core/approval_gate.py`

필요한 보강:

- missing report
- empty e2e_command
- verdict BLOCK
- staged path
- nightly sweep
- ProjectPipeline execute 경로

위 케이스를 회귀 테스트로 고정해야 한다.

#### 4. test-driven-development

판단: 선택 흡수가 아니라 핵심 로직 기본 규칙으로 승격

이유:

- bugfix / feature core 작업은 실패 테스트 없이 구현하면 회귀 방지가 어렵다.
- AF의 3-Tier review가 있어도 “테스트가 원래 실패하는지 확인”하지 않으면 테스트 신뢰성이 낮다.

권장 적용:

```text
bugfix / feature_update / refactor 중 core 코드 변경 시
red test evidence 또는 명시적 예외 사유 요구
```

주의:

- 모든 문서 변경에 TDD를 강제하면 과하다.
- runtime/core behavior 변경에만 적용하는 것이 맞다.

#### 5. using-git-worktrees

판단: 필요

이유:

- AF는 병렬 실행, subagent, review, FSA, generated docs가 많다.
- 큰 기능을 같은 작업공간에서 진행하면 변경 충돌과 분석 오염이 커진다.

권장 적용:

```text
큰 기능 / 병렬 구현 / Phase 단위 작업은 worktree 격리 기본
기존 workspace는 분석·리뷰·문서 정리용으로 유지
```

효과:

- 작업공간 오염 감소
- 병렬 구현 충돌 감소
- baseline test와 변경 test 구분 쉬움

---

### 4.2 부분 흡수 권장

#### 6. receiving-code-review

판단: 부분 흡수

AF에는 이미 review aggregation과 WarningRegistry가 있다.

하지만 리뷰 피드백을 받을 때 다음 규칙은 AF에도 중요하다.

```text
외부 리뷰는 명령이 아니라 검증 대상이다.
코드와 테스트로 확인한 뒤 반영한다.
```

권장 적용:

- cross-review finding 반영 전 `file:line` 재검증
- false positive 판정 흐름 유지
- 사용자의 기존 결정과 충돌 시 HOLD

#### 7. subagent-driven-development

판단: 부분 흡수

AF에는 `AgentSpecializer`가 있다.

강점:

- base agent deepcopy
- task metadata 주입
- acceptance/artifacts 포함
- mailbox 포함
- episodic memory top-3 조회
- task 관련 skill filtering

하지만 Superpowers 방식의 장점인 다음은 약하다.

```text
구현 subagent
  -> spec compliance review
  -> code quality review
```

권장 적용:

- AF task 완료 후 review task를 자동 주입할 때
  - 1차: spec compliance
  - 2차: code quality
  로 구분

#### 8. finishing-a-development-branch

판단: 부분 흡수

AF에는 pre-commit hook과 review gate가 있다.

하지만 다음이 부족하다.

- branch 마무리 UX
- merge/PR 선택지
- worktree cleanup
- doc/SKILL/template 변경 검증

권장 적용:

```text
Phase 종료 시:
1. tests
2. verification-report
3. review gate
4. generated docs sync
5. branch/worktree cleanup decision
```

---

### 4.3 기존 AF 유지

#### 9. requesting-code-review

판단: AF 기존 방식 유지

AF의 3-Tier review는 Superpowers 단일 reviewer보다 강하다.

다만 한계가 있다.

현재 `review_gate`는 `.py` 파일이 없으면 `no-py-files`로 PASS한다.

따라서 다음 변경은 별도 gate가 필요하다.

- `SKILL.md`
- `docs/work-items/_template/**`
- `docs/codex_논의/**`
- prompt-only 변경
- policy-only 변경

권장:

```text
code review gate는 유지
doc/skill/template review gate를 별도로 추가
```

#### 10. dispatching-parallel-agents

판단: AF 기존 구조 유지

AF는 이미 다음 구조를 가진다.

- rule-based dispatch
- first cycle LLM intervention
- blocker 감지
- stall 감지
- recent failure 감지

따라서 Superpowers의 병렬 dispatch 패턴을 그대로 가져올 필요는 없다.

필요한 것은 “언제 병렬화 금지인지”를 더 명확히 하는 것이다.

금지 조건:

- 같은 파일 수정
- 같은 work-item artifact 수정
- 같은 approval gate 상태 수정
- 같은 skill registry 수정

---

### 4.4 재구성 필요

#### 11. writing-plans

판단: 그대로 흡수하지 말고 PlanChecker로 재구성

AF에는 이미 planning chain이 있다.

실제 위치:

- `ProjectPlanningDirector`는 `core/bootstrap_roles.py`
- 실제 메서드는 `plan()`
- pipeline은 project brief, role plan, task board, work-item 문서를 만든다.

부족한 것은 plan 생성이 아니라 plan critique다.

권장:

```text
ProjectPlanningDirector.plan()
  -> PlanChecker
  -> revise
  -> approval gate
```

즉 `writing-plans`를 또 추가하는 것보다 `PlanChecker + Goal-backward Verifier`를 만드는 것이 맞다.

---

## 5. 기존 코드와 주요 충돌 지점

### 5.1 work_kind 충돌

설계서의 값:

```text
feature
architecture-change
```

실제 값:

```text
new_project
maintenance
bugfix
feature_update
refactor
```

이 상태에서 설계대로 구현하면 `require_domain_review()`가 제대로 발화하지 않는다.

수정:

```text
feature -> feature_update
architecture-change는 신설할지 폐기할지 결정
```

### 5.2 ApprovalGate 연결 미정

현재 `ApprovalGate`는 `work_kind`를 받지 않는다.

선택지는 셋이다.

1. `ApprovalGate.__init__(..., work_kind=...)`
2. `approve(work_kind=...)`
3. `intake.py` 또는 work-item metadata에 work_kind를 기록하고 ApprovalGate가 읽음

내 판단:

```text
3번이 가장 안정적이다.
```

이유:

- work_kind는 작업 메타데이터다.
- ApprovalGate 생성자에 계속 인자를 늘리면 경로별 호출부가 깨질 가능성이 크다.
- 문서 기반 gate와도 잘 맞는다.

### 5.3 domain-review.md 부재

현재 템플릿이 없다.

필수 작업:

```text
docs/work-items/_template/domain-review.md 생성
work_item_generator extra template copy 목록에 추가
verdict schema 정의
parser/caller 지정
```

### 5.4 verification 경로 분산

현재 verification은 다음에 흩어져 있다.

- `.githooks/pre-commit`
- `scripts/verify_handoff_checker.py`
- `scripts/nightly_tick.py`
- `core/approval_gate.py`

이 자체는 나쁘지 않다.

문제는 contract가 문서화되어 있지 않다는 점이다.

필수 작업:

```text
verification-report.md schema
caller list
failure code
gate propagation rule
test matrix
```

### 5.5 review_gate의 doc/skill 변경 한계

현재 review_gate는 `.py` 파일이 없으면 PASS한다.

이것은 코드 변경에는 합리적이지만, 이번 작업에는 위험하다.

왜냐하면 Superpowers 흡수는 대부분 다음 파일을 건드리기 때문이다.

- `SKILL.md`
- docs template
- design doc
- policy doc

따라서 별도 doc/skill gate가 필요하다.

---

## 6. 적용 시 효과

### 6.1 요구사항 품질 향상

`brainstorming`과 Domain Gate가 들어가면 잘못된 요구사항이 work-item으로 승격되는 것을 줄인다.

효과:

- 구현 전 충돌 발견
- 용어/ADR/기존 결정과의 불일치 감소
- 불필요한 work-item 생성 감소

### 6.2 디버깅 품질 향상

`systematic-debugging`이 FSA/ISE에 연결되면 다음이 줄어든다.

- 원인 없는 재시도
- 증상 패치
- 3회 이상 같은 방향 실패
- 실패 로그 품질 저하

효과:

- root cause 기록 증가
- FSA escalation 판단 정확도 상승
- skill evolution의 입력 품질 상승

### 6.3 완료 선언 신뢰도 상승

`verification-before-completion`이 통합되면 “고쳤다”는 말이 다음 증거 없이는 통과하지 못한다.

필수 증거:

- 실행한 명령
- exit code
- verification-report verdict
- e2e_command
- BLOCK 여부

효과:

- false completion 감소
- 자율 모드 검증 갭 감소
- 사용자 신뢰 증가

### 6.4 병렬 작업 안정성 증가

worktree 격리와 subagent review loop가 들어가면 병렬 작업의 충돌이 줄어든다.

효과:

- 같은 workspace 오염 감소
- 리뷰/검증 baseline 분리
- 실패한 실험 폐기 쉬움

### 6.5 AF 제품 포지션 강화

GSD/Superpowers 패턴을 제대로 흡수하면 AF는 다음 포지션을 갖는다.

```text
역할 기반 오케스트레이션
+ GSD식 품질 워크플로우
+ Superpowers식 검증 습관
+ AF 고유 3-Tier review
```

이는 단순한 코딩 에이전트보다 강한 포지션이다.

---

## 7. 권장 실행 순서

### Step 1. 5/13 문서 v2 정정

먼저 `2026-05-13-superpowers-11-skills-quality-verification.md`를 고쳐야 한다.

정정 항목:

- `core/project_planning_director.py` 제거
- `core/bootstrap_roles.py`로 교체
- `generate_research_brief()` 표현 제거
- `ProjectPlanningDirector.plan()`로 교체
- `AgentSpecializer` 12-cap → 8-cap
- 0.35/0.40/0.25 점수 체계 삭제
- memory wire-up 미완 주장 삭제
- domain-review contract 추가
- verification wiring contract 추가
- “비선형 상승” 같은 정량 표현 약화
- LOC 추정에 ±50% 표시

### Step 2. 5/11 Domain Gate BLOCK 11건 해소

특히 Critical 2건을 먼저 해소해야 한다.

1. `work_kind` 값 정정
2. `ApprovalGate`와 `work_kind` 연결 방식 결정

이 두 개 없이는 Phase A 구현이 시작되어도 바로 막힌다.

### Step 3. domain-review.md 실제 생성

필수 schema:

```text
work_item_id
work_kind
related_terms
related_adr
questions
answers
verdict: PASS | WARN | NEEDS_ADR | BLOCK
reviewer
reviewed_at
```

### Step 4. verification-report contract 고정

필수 schema:

```text
e2e_command
exit_code
evidence
verdict: PASS | WARN | BLOCK
known_gaps
```

### Step 5. systematic_debugging SKILL.md 추가

외부 import 없이 AF 자체 형식으로 작성한다.

메타에는 다음을 남긴다.

```yaml
inspired_by: obra/superpowers/systematic-debugging
```

### Step 6. TDD / worktree 정책을 gate 조건으로 연결

권장:

- bugfix / feature_update / refactor 중 core 코드 변경은 red test evidence 요구
- 큰 기능 / 병렬 구현은 worktree 격리 권장 또는 필수

### Step 7. PlanChecker + Goal-backward Verifier + UAT.md 도입

최종적으로 GSD의 핵심은 여기에 있다.

```text
PlanChecker
Goal-backward Verifier
UAT.md
Gap Replan
```

이 네 가지가 붙으면 AF는 GSD식 품질 루프를 흡수하면서도 기존 role/state orchestration 강점을 유지할 수 있다.

---

## 8. 최종 판단

`docs/codex_논의/2026-05-13-superpowers-11-skills-quality-verification.md`의 결론인 “5개 흡수, 6개 보류”는 절반만 맞다.

내 판단은 다음이다.

```text
강제 흡수:
brainstorming
systematic-debugging
verification-before-completion
test-driven-development
using-git-worktrees

부분 흡수:
receiving-code-review
subagent-driven-development
finishing-a-development-branch

기존 AF 유지:
requesting-code-review
dispatching-parallel-agents

재구성:
writing-plans -> PlanChecker / Goal-backward Verifier
```

가장 중요한 것은 기능 수가 아니다.

핵심은 다음이다.

```text
AF의 기존 기능을 GSD처럼 명시적인 품질 계약으로 전면화하는 것.
```

따라서 최종 권장 방향은 다음이다.

```text
Superpowers 외부 패키지 import 금지
AF-native SKILL / template / gate로 패턴만 흡수
Domain Gate와 verification contract부터 고정
그 다음 PlanChecker / Verifier / UAT로 GSD 품질 루프 완성
```
