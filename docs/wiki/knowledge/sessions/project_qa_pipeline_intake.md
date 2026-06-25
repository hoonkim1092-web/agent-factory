---
name: project_qa_pipeline_intake
description: "사용자 시점 QA 파이프라인 — Q-S1~Q-S6 전부 완료(2026-06-20). 직접 통합 테스트 PASS. Full-route dogfood stopped_max_cycles(오케스트레이터 기존 한도, Q-S6 회귀 아님). 다음=product work-item 신규 선정."
metadata: 
  node_type: memory
  type: project
  originSessionId: ba7be35f-9f98-4fed-ad28-921a2e9ce5f8
---

**설계**: `docs/2026-06-18-user-perspective-qa-pipeline-design.md`
**브랜치**: `2026-06-04-right-sized-execution-slice1`
**다운스트림 소비자**: 완료계약(`project_completion_contract_and_review_surfacing`) — 이 설계는 "무엇이 정답이고 어떻게 먹이나"(머리), 완료계약은 실행기.

## ✅ Q-S1 완료 (`bacafe3d`, Sonnet)
`core/completion_contract.py`: `Provenance`(user/research/default) + `GoalEntry` 3개 additive 필드(`scenario`/`expected_output`/`provenance`) + `TestManifest` 신규(required_tools/required_env/seam_requirements/provenance) + `GoalContract.manifest`. 전부 round-trip+레거시 하위호환. 13 신규/30 PASS. 3-Tier: af-critic PASS / af-cross-review PASS[single-vendor] / af-test-runner 252.

## ✅ Q-S2 완료 (`be884287`+`5fb3d8ad`, Sonnet)
- `verdicts.py`: `QuestionRoute.RESEARCH_SYNTHESIZE = "research_synthesize"` (INV-Q1)
- `question_router.route_batch()`: RESEARCH_SYNTHESIZE 분기 → `source="research_synthesize_pending"` (BLOCK/HITL 기여 안 함, value=None)
- `goal_clarification.yaml`: 4문항(`observable_goal`/`golden_example`/`test_seam`/`manual_only`, default_route: research_synthesize)
- `clarification.merge_clarification(provenance="default")`: log 엔트리 provenance 태깅.
- 9 신규/43 PASS. 3-Tier: af-critic WARN→수정 / af-cross-review PASS / af-test-runner 137.

## ✅ Q-S3 완료 (`e4f2dac0`, Sonnet, 2026-06-19)
경로 C 활성화 — BriefBackedQuestionCaller + synthesizer adapter + project-goal.md QA 4필드
24 신규 PASS(INV-Q6/Q7/Q8). 3-Tier: af-critic WARN(수정) / af-cross-review WARN(BLOCK 0) / af-test-runner PASS(24+3469)

## ✅ Q-S4 완료 (`1a27dcce`, Sonnet, 2026-06-19)
seam→deliverables 승격 + GoalContract 동결(INV-Q3/Q4). 16 신규/41 PASS. 3-Tier 완주.

## ✅ Q-S5 완료 (`93f6c45f`, Sonnet, 2026-06-19)
`core/qa_report.py` 신규 — `render_html(evidence_ledger, run_dir) -> str`. 5섹션 HTML. 25 신규/89 PASS. 2-Tier.

## ✅ Q-S6 완료 (`ee119a1b`, Sonnet, 2026-06-20)
wiring: `pipeline.execute()` → `render_html()` + `qa_report_path`, `dogfood._run_verify_phase()` → `state.qa_report_path`, `DogfoodState.qa_report_path` 필드. 8 신규 PASS. 2-Tier.

**직접 통합 테스트 (2026-06-20)**: `AcceptanceGate().run(gc, cwd) → build_evidence_ledger → render_html` 체인 PASS, verdict=VERIFIED, qa_report.html 1619 bytes 생성 확인.

**Full-route dogfood run** (`1781884669-a7502e9b`, Tier-3 core/completion_contract.py 타겟): Floor 2 → design+review+cross_review 강제 → DynamicOrchestrator `stopped_max_cycles` BLOCK. Q-S6 회귀 아님 — 기존 orchestrator 사이클 한도 문제. VERIFY 단계 미도달(DEVELOP blocked).

## ▶ 다음 = product work-item 신규 선정
QA 파이프라인 Q-S1~Q-S6 전부 완료.

연관: [[project_completion_contract_and_review_surfacing]] [[feedback_analysis_doc_baseline_must_be_real_code]]

## 관련
- [[code/symbols]]

