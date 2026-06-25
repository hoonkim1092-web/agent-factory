---
name: Phase 6 Semantic Matching 완료
description: Phase 6 - Gemini Embedding 기반 시맨틱 매칭으로 스킬 선택 정확도 향상
type: project
---

Phase 6: Semantic Matching 구현 완료 (2026-03-14)

**Why:** 기존 keyword(60%)+category(40%) 점수만으로는 의미적으로 관련된 스킬을 놓치는 문제. 특히 한국어/영어 혼합 입력에서 부정확.

**How to apply:** 시맨틱 가중치 변경 시 `core/semantic_embedder.py` + `core/skill_loader.py` + `core/skill_cache.py`를 함께 수정.

## 완료 항목

1. **adapter 버그 수정**: `convert_meta_yaml_to_metadata()`에 `when_to_use`, `when_NOT_to_use`, `when_to_use_keywords`, `semantic_tags` 4개 필드 추가
2. **SemanticEmbedder**: Gemini Embedding API (`google.genai.Client`) + 순수 Python 코사인 유사도 + 디스크/메모리 캐시
3. **가중치 변경**: API 가용 시 `keyword(35%) + semantic(40%) + category(25%)`, 불가 시 `keyword(60%) + category(40%)` 폴백
4. **OptimizedSkillRelevance**: `_semantic_match_cached()` 메서드 추가, `_semantic_cache` 활성화
5. **12개 테스트** 작성 및 통과, 전체 266개 통과

## 주요 파일
- `core/semantic_embedder.py` — 신규 (시맨틱 엔진)
- `core/skill_metadata_adapter.py` — 수정 (누락 필드 4개 추가)
- `core/skill_loader.py` — 수정 (embedder 통합, 가중치 변경)
- `core/skill_cache.py` — 수정 (_semantic_cache 활성화)
- `tests/test_phase6_semantic_matching.py` — 신규 (12개 테스트)
