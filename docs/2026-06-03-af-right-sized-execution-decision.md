# AF Right-Sized Execution Decision

Date: 2026-06-03
Status: Decision recorded, not implemented

## Summary

AF의 핵심 제품 가치는 사용자가 큰 목표를 던졌을 때 AF가 스스로 적절한 작업 단위로 나누고, 각 작업 크기에 맞는 실행 경로를 선택하는 것이다.

따라서 LLM Wiki + Obsidian 같은 큰 작업을 사람이 전부 잘게 쪼개서 넣는 방식은 임시 우회일 수는 있지만, AF를 쓰려는 본래 이유와 맞지 않는다.

## Background

T3 dogfood 재검증에서 source-write leak은 차단되었다.

- `allow_file_edit=False`로 control-plane Claude CLI의 `bypassPermissions` 경로를 막았다.
- `merge=never` dogfood run에서 worktree에는 변경이 생겼고 source repo는 baseline과 동일했다.
- 따라서 확인된 source-write leak 경로는 닫힌 것으로 본다.

하지만 같은 검증에서 별도 문제가 드러났다.

- `geometric_mean` 같은 작은 leaf 함수에도 `ProjectPipeline.run()` 전체가 실행됐다.
- designer, backend, QA, reviewer, cross-validator 등 멀티에이전트 프로젝트로 과분해됐다.
- 200+ cycle busy-wait/stall이 발생했다.

즉 AF는 이제 안전하게 격리된 작업을 수행할 수 있지만, 아직 작업 크기에 맞게 실행 경로를 고르는 능력이 부족하다.

## Decision

다음 핵심 개선은 단순한 내부 배관 정리가 아니라 AF의 제품 기능으로 본다.

> AF Right-Sized Execution: 요청을 분석해 leaf task, multi-step task, project task, risky self-modification task를 구분하고, 그에 맞는 실행 경로를 선택한다.

이 기능이 있어야 사용자가 다음처럼 큰 목표를 던질 수 있다.

```text
LLM Wiki + Obsidian 연동을 구현해줘.
```

그리고 AF가 스스로 다음처럼 나눌 수 있어야 한다.

```text
1. ContextPack 최소 구현
2. LLM Wiki generated pages 연결
3. Obsidian export 구조 생성
4. Agent prompt/context 주입
5. 테스트와 검증
```

## Non-Goal

지금 당장 LLM Wiki + Obsidian 전체를 한 번에 구현하지 않는다.

또한 단순히 `max_cycles`를 낮추는 방식만으로 해결하지 않는다. cycle cap은 안전망일 뿐이고, 핵심은 작업 크기 판단이다.

## Required Behavior

AF는 DEVELOP 진입 전에 최소한 다음 분류를 해야 한다.

```text
leaf code task
  -> 단일 agent/codegen 경로

small multi-file task
  -> 제한된 planner + 단일 구현 agent + 테스트

project task
  -> 기존 ProjectPipeline / DynamicOrchestrator

risky self-modification
  -> dogfood isolation + review gate
```

각 분류는 state/artifact에 이유와 함께 기록되어야 한다.

## First Implementation Slice

나중에 구현할 때 첫 slice는 작게 잡는다.

1. dogfood DEVELOP 진입 전에 task complexity를 판정한다.
2. leaf task면 full `ProjectPipeline.run()` 대신 경량 codegen 경로를 사용한다.
3. project task면 기존 `ProjectPipeline.run()`을 유지한다.
4. no-progress cutoff는 보조 안전망으로만 둔다.
5. source-write isolation invariant는 기존 T3 기준으로 유지한다.

## Relation To LLM Wiki

기존 설계상 LLM Wiki + Obsidian의 순서는 다음이다.

```text
ContextPack first
-> LLM Wiki generated pages
-> Git Nexus
-> Obsidian export
```

따라서 LLM Wiki + Obsidian은 AF Right-Sized Execution을 검증하기 좋은 큰 product-value target이다. 다만 AF가 스스로 slice를 나눌 수 있게 된 뒤에 전체 목표로 던지는 것이 맞다.

그 전에는 사람이 `ContextPack 최소 구현` 같은 product slice를 지정해 dogfood 또는 수동 구현으로 진행할 수 있다.

## Current Operating Rule

당분간은 다음 기준을 사용한다.

```text
큰/위험한 AF 자기수정 작업 -> dogfood
작고 명확한 leaf 작업 -> 직접 구현 또는 경량 경로
LLM Wiki + Obsidian 전체 목표 -> Right-Sized Execution 준비 후 dogfood 대상
```

## Open Questions

- leaf task 판정 기준을 AST scope, 파일 수, intent token, 위험 파일 패턴 중 무엇으로 시작할 것인가?
- 기존 `express_router`를 top-level route 용도로만 둘지, dogfood 내부 complexity signal 일부로 재사용할지?
- 경량 codegen 경로는 기존 dogfood implement executor를 재사용할지, AgentRunner 단일 호출로 둘지?
- `terminal_per_agent=True`는 project task에만 허용할지?

## Converged Design (2026-06-03 세션 합의)

설계 대화로 아래가 확정됨. 위 Open Questions를 해소/대체한다.

### Stage-Aware RightSizedRouter

"작냐/크냐" 단일 축이 아니라 **필요한 stage를 고른다**. 작업량이 작아도 설계/리뷰가 필요할 수 있기 때문이다(예: `allow_file_edit=False` 1줄 = 보안 변경, pre-commit 7줄 = hook/EOL 위험). 따라서 동사·파일명·토큰 룰로는 불가 — LLM이 의도·범위·위험·설계필요도를 종합 판단해야 한다.

출력 shape:
```
{ isolation, required_stages, review_depth, confidence, reason }
  isolation: none | source | worktree | dogfood
  required_stages ⊆ [research, design(spec/premortem), plan, implement, test, review, cross_review]
  review_depth: 검토 강도
```
엔진: `ControlPlaneLLM.generate_json()` (`allow_file_edit=False`, 파일편집 없이 JSON 판단만). **하드코딩 토큰 룰 아님 — 지능형 하네스.**

### 두 결정적 안전 floor (LLM 위 — 기존 메커니즘 재사용)

- **isolation 하한**: self-mod 감지(`workspace == agent-factory` + `core/`·`.githooks/` 등 변경) → 최소 `worktree`. LLM이 `source`로 오판해도 override. **source-write leak 재발 방지**(이번 세션에 막은 그 leak을 라우터가 되열지 않도록).
- **review/design 하한**: `scripts/blast_radius.py` tier 재사용. Tier3 파일(core/provider/permission/hook/auth/merge)은 코드량이 작아도 design+review+cross_review 강제 포함.
- "하드코딩 금지"는 **경로 선택**에 적용되고, **안전 하한은 결정적**이어야 한다(서로 다른 층).

### 보수적 비대칭 fallback

LLM 예외 / JSON 파싱 실패 / confidence < 임계 / 근거 부족 → `required_stages = full`, `isolation = worktree`. **"research는 생략 가능해도 design/review는 안 낮춘다."** under-route(큰 일을 작게 처리)는 절대 금지 — 경량화는 확신할 때만.

### 기존 코드 정합 (사실 확인)

- `express_router._PHASES` = stage 어휘·preset이 **이미 존재**(direct/light/full/dogfood 각 phase 리스트) → 재사용. 정적 mode 고정 → LLM 지능형 선택으로 전환. 하드코딩 라우팅 로직은 은퇴.
- dogfood phase dispatch는 **모듈러**(`_run_implement/verify/review_phase` 개별 핸들러) → stage 부분집합 실행 가능.
- `ProjectPipeline.run(task_input, workspace, runtime_workspace)`는 **monolithic**(stage 선택 파라미터 없음) → 임의 stage 조합(no-research pipeline 등)은 리팩토링 필요 = **슬라이스 2**.

### 슬라이스 경계 (over-build 방지)

- **슬라이스 1 실행 = 보수적 2-way**: `required_stages ⊆ {plan, implement, test}` + 고신뢰 → dogfood 네이티브 light(`build_plan→_run_implement_phase→_run_verify_phase`). 그 외(design/research 필요·sensitive area·저신뢰) → 기존 `ProjectPipeline.run()`. **"작아도 설계 필요"는 슬라이스 1에서 full pipeline로** 보낸다(분리 실행은 슬라이스 2).
- **슬라이스 2**: `ProjectPipeline`에 stage-선택 파라미터 → no-research pipeline 등 임의 조합. 슬라이스 1 경험적 검증 후 가치 판정.

### 구현 단계 (다음 세션 진입점)

```
Step 1  core/right_sized_router.py — classify(task, workspace, *, changed_files=None)
        -> RouteDecision{isolation, required_stages, review_depth, confidence, reason}
        ControlPlaneLLM.generate_json() 사용, injectable(_router_llm 모듈 전역)
Step 2  안전 floor: self-mod → isolation>=worktree / blast_radius Tier3 → design+review+cross_review 강제 (LLM override)
Step 3  보수적 fallback: 실패/저신뢰 → required_stages=full, isolation=worktree
Step 4  하네스 테스트(LLM stub injectable): light/full 분기 / floor override(source→worktree, Tier3→cross_review) / invalid JSON·low-conf·예외 → full fallback
Step 5  dogfood DEVELOP 연결: _run_develop_phase 진입부 classify →
          required_stages⊆{plan,implement,test}&고신뢰 → 네이티브 light, else → ProjectPipeline.run()
          분류+floor override 이유를 dogfood state/artifact 기록
Step 6  acceptance: 실제 dogfood run — geometric_mean(leaf)→light(orchestrator/터미널 0) /
          sensitive 1줄 변경→blast_radius floor로 full / LLM실패 주입→full fallback
Step 7  (슬라이스 2, 별도) ProjectPipeline stage-선택 파라미터 → 임의 stage 조합
```
설계 Opus → 구현 `/model sonnet`. `core/` Tier3 → test-first + 3-Tier(cross-review 포함).
