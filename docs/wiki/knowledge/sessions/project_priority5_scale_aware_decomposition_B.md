---
name: project-priority5-scale-aware-decomposition-b
description: 우선순위5 규모인지 분해(B안) 구현 완료(2026-06-20). 우선순위3 gear 폐기.
metadata: 
  node_type: memory
  type: project
  originSessionId: f61d494f-989e-4af5-8a7a-416d9a7f0d17
---

# 우선순위 5 규모인지 분해 (B안) — ✅ 구현 완료 (2026-06-20)

**✅ 구현 완료 (2026-06-20, Opus)**: `core/bootstrap_roles.py`(D1+D3) + `core/dogfood.py:1772`(D2). 3-Tier: af-critic PASS / af-cross-review R1 BLOCK(F1·F2)→R2 WARN(해소) / af-test-runner PASS(64). 테스트 `tests/test_scale_aware_decomposition.py` 27건.
- **cross-review 흡수**: F1(`_build_policy_rules()`가 minimal에 "At least 2 roles" 주입 충돌) + F2(policy.yaml QA MANDATORY가 qa_relaxed에도 LLM 도달) → `_build_policy_rules(decomposition_strength, qa_relaxed)` 파라미터화. F-NEW-1(fallback QA 잔존)=INV-F1 의도대로 보류(advisory).
- **보류(별개 트랙)**: Part 4(Tier3-small minimal 분해 = 분해축≠리뷰축 분리 필요), gear 승격(2번째 소비자 생기면).

**결정 (2026-06-20, Opus 세션)**: 우선순위 3·5 설계 중 **우선순위 3(RSE small-full gear) 폐기, 우선순위 5만 B안으로 구현.**

## 경위 (재분석 금지 — 이 결론만 사용)
- 우선순위 3·5 설계를 병렬 Opus 에이전트로 초안 작성 → 둘 다 `project_brief["route"]["gear"]` seam 공유(우선순위3 생산, 우선순위5 소비). 통합버그 1건(`small-full` vs `small_full` 리터럴) 발견·수정.
- 우선순위3 cross-review **R1 BLOCK**(F1: `is_small_full()`이 `set ⊆ SMALL_FULL_STAGES`만 검사 → `{impl,test}` review-less 집합도 통과 → INV-G5 위반) → 수정(review/cross 실재 가드) → **R2 PASS**.
- **R2가 더 근본 결함 표면화**: `core/project_pipeline.py`는 **design·plan 단계를 `_stage_enabled`로 게이팅하지 않음**. 게이팅되는 건 research(:749)·review/cross_review(:1142)뿐. `grep design project_pipeline.py` = 0건. → small-full의 "research·design·plan 생략" 전제 중 **design·plan 스킵 무효** = small-full ≡ full − research.
- gear의 유일 실효 가치 = 우선순위5 분해 축소 입력. 우선순위5는 이미 `project_brief["route"]["required_stages"]`를 받음(`project_pipeline.py:848` seam) → **gear 없이 직접 규모 판단 가능**. 소비자 1개 = YAGNI → 라우터 무변경(B안).

## B안 구현 명세 (다음 세션, 설계=`docs/2026-06-20-scale-aware-role-decomposition-design.md`)
대상: `core/bootstrap_roles.py`(plan) + `core/project_pipeline.py`(어댑터), 둘 다 Tier-3.
1. **규모 신호(B안 핵심)**: `route["required_stages"]`에서 유도 — `STAGE_RESEARCH ∉ stages AND STAGE_DESIGN ∉ stages` → `decomposition_strength="minimal"`, else `"standard"`. (gear 키 의존 삭제)
2. `plan()`에 `decomposition_strength="standard"` additive 파라미터 + minimal 프롬프트 분기(정체성/분해지침/역할≤2). standard 골든=바이트동일.
3. `_ensure_qa_role`(`:513`) skip은 `minimal AND merge_mode∈{never,manual}` 교집합만. merge_mode 배선 = `dogfood.py:1774` 인근 `route["_merge_mode"]` 주입. auto_policy→QA강제.
4. 모듈0 금지는 모든 규모 유지. `_fallback_roles`는 규모 인지 미적용.
5. 배포 동등성: caller `project_pipeline.py:911` 도달 grep. 픽스처-only 미허용.

## 보류 (별개 트랙)
- **Part 4**: Tier3-small → minimal 분해는 분해축(규모) ≠ 리뷰축(blast Tier) 분리 필요 → 보류. 현 B안은 Tier3(Floor2가 design 강제)면 standard 분해.
- **gear 승격**: 향후 task 규모 **2번째 소비자**(예산·모델라우팅·머지정책) 생기면 우선순위3 doc 재활용해 라우터 gear 필드로 승격(SSOT). 그 전까지 미구현.

부모 진단: [[project_dogfood_false_success_spin]]. 교차검증 정책: [[feedback_grep_before_rejecting_crossreview]], [[feedback_review_verdict_vs_bug_substance]], [[feedback_cross_review_stale_baseline_repeat]]. 모델: [[feedback_model_per_phase]].

## 관련
- [[code/symbols]]

