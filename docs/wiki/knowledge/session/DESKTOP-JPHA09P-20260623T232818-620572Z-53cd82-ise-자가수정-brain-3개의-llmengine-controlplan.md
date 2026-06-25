---
id: "session/DESKTOP-JPHA09P-20260623T232818-620572Z-53cd82-ise-자가수정-brain-3개의-llmengine-controlplan.md"
type: "session"
scope: "project"
title: "ISE 자가수정 brain 3개의 LLMEngine→ControlPlaneLLM 교체는 이미 커밋 08e04"
author: "Jerry"
source_machine: "DESKTOP-JPHA09P"
created_commit: "68cd91c2"
created_at: "2026-06-24T08:28:18+09:00"
visibility: "private"
links: ["[[code/symbols]]"]
---

ISE 자가수정 brain 3개의 LLMEngine→ControlPlaneLLM 교체는 이미 커밋 08e04ebfd7fd133ad1ef98a8148b199efbcc07a9에서 구현·머지됐으며, 설계문서가 이를 모르고 재구현을 제안해 af-critic BLOCK을 받은 stale-baseline 사건.

## 결정 (Decisions)
- core/ise_analyzer.py:67-68, core/ise_redesigner.py:48-49, core/evaluator.py:15-16 세 곳 모두 ControlPlaneLLM(model_name=model_name)으로 교체 — 커밋 08e04ebfd7fd133ad1ef98a8148b199efbcc07a9('fix(ise-provider-awareness)') 에서 완료, HEAD(68cd91c2) 조상으로 머지됨.
- core/fsa_loop.py:87-95 model_name fallback을 'gemini-1.5-pro-latest' → None으로 변경 — 동일 커밋에서 완료.
- INV-1(ISEAnalyzer ControlPlaneLLM 사용), INV-5(LLMEngine 직접생성 0건) 모두 현재 코드에서 충족 확인 — tests/test_ise_provider_awareness.py 6 passed in 0.63s.
- af-critic BLOCK 판정: 설계문서를 신규 구현 대상이 아니라 'Implemented (08e04ebf)' 상태로 닫고 재리뷰 큐에서 제거할 것을 권고.

## 기각 (Rejections)
- 이 설계문서 기반 신규 구현 착수 기각 — core/evaluator.py:4, core/ise_analyzer.py:68, core/ise_redesigner.py:49 이 이미 ControlPlaneLLM을 import·사용 중이므로 재구현 시 no-op 또는 회귀.
- 설계 §9 baseline 주장('LLMEngine(model_name="gemini-1.5-pro-latest") 3건') 기각 — grep 실측 결과 LLMEngine 직접 생성 0건, baseline 자체가 틀림.
- 설계 §7 'test-first RED' 시나리오 기각 — tests/test_ise_provider_awareness.py 이미 존재하고 6 PASS, RED 전제 성립 안 함.

## 패턴 (Patterns)
- stale-baseline trap: 리뷰-작성 당일 밤 구현까지 완료됐을 때 설계문서 baseline이 실제 코드와 어긋남. 재발 방지: 설계 작성 시 'git merge-base --is-ancestor <제안커밋> HEAD'로 이미 머지됐는지 확인 의무화.
- 구현 머지 후 원본 설계 상태를 Implemented로 닫는 트리거 부재 → 설계문서가 재리뷰 큐에 다시 잡히는 패턴 (docs/reviews/2026-06-11-020117-…design-review.md 존재가 증거).
- ControlPlaneLLM.generate()/generate_json()은 LLMEngine 동일 시그니처 drop-in — 클래스 __init__ 내부 교체만으로 모든 생성처 자동 커버 (core/control_plane_llm.py:147, 161).
- engine_api_keys_disabled()(core/providers/registry.py:96-100) True 시 gemini 키 마스킹 → LLMEngine._client=None → ISE brain 침묵 인과 패턴: CLI-first 아키텍처(ControlPlaneLLM)로만 회피 가능.

## 정밀 참조 (verbatim, INV-K5)
- `INV-1`
- `INV-5`
- `core/ise_analyzer.py:67`
- `core/ise_redesigner.py:48`
- `core/evaluator.py:15`
- `core/llm_engine.py:31`
- `core/providers/registry.py:96`
- `core/control_plane_llm.py:50`
- `core/evaluator.py:4`
- `core/ise_analyzer.py:68`
- `core/ise_redesigner.py:49`
- `control_plane_llm.py:123`
- `registry.py:96`
- `control_plane_llm.py:147`
- `aefa8797`
- `039e55f1`
- `08e04ebf`
- `33543a18`
- `8991cde2`
- `6b53412c`
- `3f8ff28d`
- `143c4d59`
- `5ef256b5`
- `e0d491f0`
- `45670b84`
- `7756aa03`
- `1eed96ee`
- `3eea3e98`
- `a6f53fdc`
- `358f6d77`
- `df3cb933`
- `158aeaf4`
- `08e04ebfd7fd133ad1ef98a8148b199efbcc07a9`

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: DESKTOP-JPHA09P
- session_file: C:/Users/HOME/.claude/projects/D--warkSpaces-agent-factory/ffd644df-1fc2-44f5-bf48-eaf395edc36c.jsonl
- lines: 0-262

## 관련
- [[code/symbols]]

