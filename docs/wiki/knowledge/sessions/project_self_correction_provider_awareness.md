---
name: project_self_correction_provider_awareness
description: "자가수정 brain(ISEAnalyzer/ISERedesigner/StrategyEvaluator) gemini-API 하드와이어 제거 — 설계+구현 완료(2026-06-11). 커밋 08e04ebf. 다음=product-value work-item."
metadata: 
  node_type: memory
  type: project
  originSessionId: a7b6f996-b450-45f9-850a-d7e5135d4746
---

## 상태: ✅ 완료 (2026-06-11, Sonnet, `08e04ebf`)

설계(Opus) → 구현(Sonnet) 완료.

## 문제 (해소됨)
FSA/ISE 자가수정 두뇌 3개가 gemini-API 전용 `LLMEngine`에 하드와이어:
- `core/ise_analyzer.py` / `core/ise_redesigner.py` / `core/evaluator.py`
- CLI 환경에서 `engine_api_keys_disabled()` 마스킹으로 `generate()=""`→휴리스틱 폴백으로 눈감고 작동하던 실재 결함

## 해법 (적용됨)
3개 `LLMEngine(...)` → `ControlPlaneLLM(...)` drop-in 교체.
- model_name default `"gemini-1.5-pro-latest"` → `None` (D1)
- `fsa_loop.py:87` fallback도 `None`으로 통일
- 테스트 `tests/test_ise_provider_awareness.py` INV-1~6 신규

## 3-Tier 결과
af-critic PASS / af-cross-review WARN(BLOCK 0, Medium 2·Low 1 수용) / af-test-runner PASS

## 동작 변화
CLI 환경에서 FSA 자가수정이 실제 LLM 호출로 전환됨 (비용↑·품질↑). max_cycles=5 상한 유지.

## 다음
product-value work-item 신규 선정.

**Why:** 마스킹된 gemini-API에 갇혀 self-correction이 눈감고 작동하던 결함. full/야간 FSA 직접 수혜.
**How to apply:** RESOLVED — 참고 이력용.

관련: [[project_model_routing_facts]] [[feedback_design_review_mandatory]]

## 관련
- [[code/symbols]]

