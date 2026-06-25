---
name: Phase 5 Context Fork + Preflight
description: Context Fork Hook (도구 결과 1줄 요약) + Pre-flight Evaluator (스킬 사전 신뢰도 검증 CLI) 구현
type: project
---

Phase 5a/5b 구현 완료 (2026-03-13)

**Why:** 메인 에이전트 컨텍스트 낭비 방지 + 스킬 품질 게이트 도입

## Context Fork Hook (Phase 5a)
- `core/hooks/context_fork.py` — PRIORITY=15
- post_tool_call에서 500자 초과 결과를 값싼 모델(Flash/Haiku)로 1줄 요약
- LangSmith Hook(5) → ToolOutputTruncator(10) → ContextFork(15) 순서
- 3단계 summarizer: LangChain → Google GenAI → 규칙 기반 fallback
- 환경변수: CONTEXT_FORK_THRESHOLD, CONTEXT_FORK_ENABLED
- agent_runner.py에 자동 등록

## Pre-flight Evaluator (Phase 5b)
- `core/skill_preflight.py` — PreflightEvaluator 클래스 + CLI
- 스킬 test()/apply() N번 반복 실행 → 점수 산출
- 점수: reliability(60%) + consistency(30%) + speed(10%)
- 게이트: ≥0.8 active, ≥0.5 candidate, <0.5 rejected
- registry.yaml 자동 상태 업데이트
- CLI: `python run_factory_cli.py preflight <skill_path> -n 10 -v`

## 테스트
- 15개 신규 테스트 (7 ContextFork + 8 Preflight)
- 전체 245개 테스트 통과

## 관련
- [[code/symbols]]

