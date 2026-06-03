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
