---
name: Research Router Phase 1a 구현 완료
description: core/research_router.py 등 Phase 1a 구현 완료. commit 8654ce2a. 다음 작업은 T3 exe 빌드 + GitHub Release.
type: project
originSessionId: ee6a7612-e8b6-418b-94f9-bb75e4141b16
---
**현재 위치**: `2026-04-14-build-diet` 브랜치, Phase 1a 완료. 커밋 `8654ce2a` 푸시 완료.

**완료된 Phase 1a 작업**:
- `core/research_router.py` 신규: ResearchGap 9종, ResearchPlan, ResearchRouter.plan/detect_complexity_gaps, gap_to_mode, ResearchPlan.for_mode()
- `core/researcher.py`: collect_project_evidence 시그니처 확장 + mode-aware gating + router escalation self-call(max 1 retry)
- `core/project_pipeline.py`: _evidence_fn(**kwargs) + TypeError 분리
- `core/research_verifier.py`: max_retries=1, gap emit enum 값 교체, DeprecationWarning
- `af.spec`: 4개 hiddenimports 신규
- `tests/test_research_router_modes.py`: 18케이스 107 tests PASS (initial/final mode 각 100%)

**3-Tier 검증**:
- af-test-runner 107/107 PASS
- af-critic BLOCK 1건(hint_gaps 타입 불일치) 수정 완료
- af-cross-review BLOCK 1건(detect_complexity_gaps 미연결 + source_pack 키) 수정 완료

**Why**: Research Router Phase 1a는 project_brief 품질 개선의 진입점. fast_synthesis/deep_source_research/fresh_lookup 등 6개 모드로 Tavily/NotebookLM gating을 제어, 복잡한 요청에 deep escalation.

**How to apply (다음 세션)**:
- 다음 작업: T3 exe 빌드 (`python build_exe.py` → `dist/af-1.2.22.zip` → `gh release create`)
- 또는 Phase 1b: structured evidence + deterministic 4-metric verifier
- Phase 4 (Smart routing + Tier 3 조건부 발화): 2시간 예상
