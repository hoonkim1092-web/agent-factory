---
name: Retrieval Integration Architecture 남은 Phase 목록
description: Phase 2-5 구현 계획, 각 Phase별 구체적 작업 내용과 참고 파일
type: project
---

# Retrieval Integration Architecture 남은 작업

**Why:** agent-factory를 "근거 기반 오케스트레이션 플랫폼"으로 진화시키기 위한 Knowledge Plane 구축.

**How to apply:** Phase 2부터 순서대로 진행. 각 Phase는 이전 Phase에 의존.

## 완료됨

### Phase 1: Retrieval Router + Evidence Schema ✅ (2026-03-16)
- `core/retrieval_router.py` 생성 (RetrievalRouter, 4전략 분류)
- `core/researcher.py` 확장 (SemanticEmbedder 통합, evidence_pack 확장)
- `tests/test_phase8_retrieval_router.py` (15개 테스트)

---

## 남은 Phase

### Phase 2: Internal Hybrid Retrieval
**목표**: 프로젝트 문서를 청킹하고 dense+sparse 검색 도입

**구현 항목**:
1. **DocumentChunker** - README, SKILL.md, docs/, logs/ 파일을 청크로 분할
   - RecursiveCharacterTextSplitter 또는 자체 구현
   - 청크 사이즈/오버랩 설정 가능
2. **DocumentIndex** - dense(Gemini Embedding) + sparse(BM25/TF-IDF) 하이브리드 인덱스
   - 기존 `core/semantic_embedder.py`의 Gemini Embedding 재활용
   - sparse는 TF-IDF 또는 keyword 기반
3. **Ingestion Pipeline** - 프로젝트 시작 시 자동 인덱싱
   - freshness timestamp으로 stale 방지
   - 증분 업데이트 (변경된 파일만)
4. **metadata filtering** - RetrievalRouter.classify()의 filters를 검색에 반영
5. **RetrievalRouter 연동** - DOCUMENT_RAG 전략일 때 DocumentIndex 호출

**참고 파일**:
- `core/semantic_embedder.py` (기존 Gemini Embedding 인프라)
- `core/retrieval_router.py` (DOCUMENT_RAG 전략)
- `docs/agent_factory_retrieval_integration_architecture.md` 라인 523-528

**테스트**: `tests/test_phase9_hybrid_retrieval.py` (예정)

---

### Phase 3: Reranker + External Trust Gate
**목표**: top-K 후보를 reranker로 재평가, 외부 소스 신뢰도 관리

**구현 항목**:
1. **Reranker** - top-K 검색 결과를 cross-encoder 또는 LLM 기반으로 재정렬
   - 비용 통제: top-K에만 적용 (전체 문서 X)
2. **Source Trust Score** - 출처별 신뢰 점수 (local > verified_registry > external)
3. **External Install Preflight 강화** - allowlist, checksum, license check
   - 기존 `core/skill_preflight.py` 확장

**참고**: `docs/agent_factory_retrieval_integration_architecture.md` 라인 529-533

---

### Phase 4: Feedback Memory
**목표**: 실행 결과를 재인덱싱하여 학습 루프 구축

**구현 항목**:
1. **FeedbackIndexer** - 설치/생성/실행 결과를 벡터 인덱스에 저장
2. **실패 패턴 저장** - 실패 원인을 retrieval 자산으로 변환
3. **Builder Feedback Loop** - 빌드 실패 시 유사 실패 사례 검색

**참고**: `docs/agent_factory_retrieval_integration_architecture.md` 라인 535-538

---

### Phase 5: Optional Multimodal Layer
**목표**: PDF, 표, 이미지 문서가 필요할 때만 도입

**구현 항목**:
1. **RAG-Anything 통합** (조건부) - 멀티모달 문서 인덱싱
2. **도입 판단 기준**: 문서가 Markdown/코드가 아닌 PDF/Office 위주일 때만

**참고**: `docs/agent_factory_retrieval_integration_architecture.md` 라인 540-555

---

## 현재 Git 상태 (2026-03-16)

**브랜치**: `feat/unified-project-pipeline-subscription`

**커밋되지 않은 변경사항** (Phase 1-8 전체):
- 수정: agent_runner.py, researcher.py, skill_loader.py, skill_registry.py, skill_metadata_adapter.py, skill_cache.py, langsmith_tracing.py, event_bus.py, fsa_loop.py, test_cli_providers.py, test_phase3_langsmith_tracing.py, run_factory_cli.py, registry.yaml
- 신규: retrieval_router.py, semantic_embedder.py, skill_preflight.py, context_fork.py, evaluator/ 스킬 3개, test_phase4~8 테스트들
- 총 301개 테스트 통과

**⚠️ 다른 PC에서 작업 전 필요 사항**:
1. `git add` + `git commit`으로 현재 변경사항 커밋 (아직 안 됨)
2. `git push`로 리모트에 동기화
3. 다른 PC에서 `git pull`
