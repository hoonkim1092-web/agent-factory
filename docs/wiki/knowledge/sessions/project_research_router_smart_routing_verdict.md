---
name: project_research_router_smart_routing_verdict
description: "ResearchRouter 재논의 결론 — coverage gate 우회 버그 수정 완료(9e610a5d, 2026-05-20). 잔여: escalation keyword-reuse 안전망 결함, C(ordering), D(Width/Permission) — 각각 별도."
metadata: 
  node_type: memory
  type: project
  originSessionId: fbb33910-7d4b-4990-bd28-28dc992f6ffe
---

2026-05-19 1차 분석 → 2026-05-20 재논의 완료. Codex가 Depth/Width/Permission 단계 적용안 제시 → Claude가 코드로 팩트 재검증.

## 2026-05-20 재논의 결론 (확정)
- **전면 재설계·ResearchRouter 대형화·3라우터 신설 = 불필요** (Codex·Claude·1차 verdict 3자 합의).
- Codex가 짚은 3개 팩트 전부 실재하나 **영향도 순위는 Codex 제시 순서의 역순**:
  1. **coverage gate 우회 = 유일한 실제 동작 버그 (실제 #1).** `collect_project_evidence`의 `_domain_checklist`가 `else` 분기(`researcher.py:995`)에서만 할당 → `requires_web`(deep/fresh/live)·`fast_synthesis` 분기는 None → `_emit_coverage_report`가 `{}` 반환(`:747`) → `_coverage_blocked` 항상 False. **risk_level="high" 모드가 coverage gate 0.** 게이트가 사실상 archive_research 전용.
  2. escalation `scores` 손실(재귀 `:1109`이 `research_plan=` 미전달, `for_mode` `:952`가 `scores=` 미전달) = **관측성만 손실, 동작 불변.** escalation 경로는 `operational_risk<3` 구조적 보장 → `research_depth`는 어차피 "normal". → 1차 memory의 "1순위=escalation"은 하향 정정.
  3. planner ordering(`project_pipeline.py:888` vs `:927`) = standalone 효과 약함. planner는 project_brief를 JSON 통째로 받지만(`bootstrap_roles.py:402`) prompt rule이 research_plan을 안 씀 → Width 도입+prompt rule과 묶어야 의미.

## 완료 (2026-05-20, 커밋 `9e610a5d`)
- Step A-1: checklist hoist (`requires_web or mode != "fast_synthesis"`)
- Step A-2: `_emit_coverage_report`/`_identify_unmet_gaps`에 `llm_prior_refs` 파라미터 추가 (no-Tavily false BLOCK 방지)
- Step B: escalation 재귀에 `research_plan=` 전달 + `ResearchPlan.for_mode(scores=...)`
- 테스트 8건 신규(`tests/test_coverage_gate_hoist.py`) + G2/G3/G4 mock 보강
- 3-Tier: af-critic PASS / af-cross-review WARN(해소) / af-test-runner PASS. 1772 PASS.
- Blueprint §3 researcher.py 행 + §12 이력 갱신

## 아직 열려 있음 (이번 설계 비범위)
- **escalation 안전망 keyword-reuse 결함** — `detect_complexity_gaps`가 `plan()`과 `_compute_signal_scores`(키워드)를 공유. 어휘 miss(의역)는 1·2차 분류 모두 통과 = 안전망 무력. Step B는 이걸 **안 고침**(Step B는 scores 보존만). 별도 항목.
- depth→architect width 데이터 흐름 단절(=C), Permission 계층 얇음(=D) — 신규 work-item.

## 3라우터 판정 (1차에서 확정, 유지)
Depth=분류기(라우터 맞음), Width=생성 분해기(라우터 아님 — architect LLM→project_task_board.py→dynamic_orchestrator.py), Permission=정책 가드(라우터 아님 — policies.yaml+core/approval_gate.py). Width를 키워드 라우터로 만들면 escalation 버그 재생산, Permission을 키워드로 만들면 보안 취약점.

**Why:** 재논의가 끝났고 구현 대기 상태. 다음 세션이 baseline을 다시 정독하지 않고 바로 Sonnet 구현에 진입하기 위함.
**How to apply:** Step A+B는 설계노트가 baseline 확정 — `collect_project_evidence`를 재정독하지 말 것. 구현 진입 시 `/model` Sonnet 권장. keyword-reuse 안전망 결함은 Step A+B와 무관 — 별도로 재론의.

관련: [[project_research_router_b3_pending]] [[feedback_design_review_mandatory]] [[feedback_pipeline_deploy_parity]] [[feedback_review_verdict_vs_bug_substance]]
