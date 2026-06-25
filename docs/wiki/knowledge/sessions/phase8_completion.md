---
name: Phase 8 Retrieval Integration Architecture - Phase 1 완료
description: RetrievalRouter + Evidence Schema 확장 + SemanticEmbedder 연구 통합, 쿼리 분류 4전략
type: project
---

Phase 8 (Retrieval Integration Architecture - Phase 1) 완료 (2026-03-16)

**Why:** agent-factory를 범용 오케스트레이션 플랫폼으로 진화시키기 위해 Knowledge Plane 구축 시작. 기존 Execution Plane에 검색/증거 계층 추가.

**How to apply:** 향후 Phase 2-5 구현 시 이 기반 위에 빌드. RetrievalRouter는 모든 검색 요청의 진입점.

**구현 내용**:
- `core/retrieval_router.py`: RetrievalStrategy(DIRECT_LOCAL, SEMANTIC_SKILL, DOCUMENT_RAG, LIVE_WEB), RetrievalPlan, RetrievalRouter.classify()
- `core/researcher.py` 확장: SemanticEmbedder 통합, _score_candidate 개선 (token 25 + semantic 35 + file 20 + meta 10 + test 10 = 100점)
- evidence_pack 확장 필드: retrieval_strategy, retrieval_confidence, semantic_available, feedback_history
- per-target 확장: matching_rationale, source_type, feedback_history
- 15개 신규 테스트 전부 통과 (총 301개)

**추가 버그 수정 (코드 리뷰)**:
- _StdoutCapturer.write() 크래시 방지
- OptimizedSkillRelevance 캐시 적용
- semantic_tags None 필터링
- "unknown" skill_id 충돌 해결
- run_post_execute 중복 호출 제거
- metadata None 체크 추가

**다음 단계**: Phase 2 - Document Chunking + Hybrid Retrieval
