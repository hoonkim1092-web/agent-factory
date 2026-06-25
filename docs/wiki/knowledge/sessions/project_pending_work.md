---
name: 미완료 작업 목록
description: 다음 세션에서 이어서 진행할 작업들
type: project
originSessionId: 3a21fa1a-3fc5-4355-9319-6f1bdf985f12
---
## 완료된 작업 (2026-04-23 오늘 세션)

- **Graphify 크로스 프로바이더 스킬 통합 Phase 1+2** — 커밋 `28ae5477`, `5f42ccba`
- **LLM 기반 work-item 문서 생성 파이프라인 P1+P2** — 커밋 `1db9e5be`
  - `core/requirement_llm.py`: `execute_document_prompt()` + `_DOCUMENT_SYSTEM_PROMPT`
  - `core/work_item_generator.py`: `_fallback_*` 분리 + LLM 래퍼 4개 + `_generate_and_refine` + deadline 300s + chained refinement
- **크로스 PC 세션 연속성 3-Phase** — 커밋 `d3980d6b`
  - Phase A: `NEXT_STEPS.md` 재작성 + `CLAUDE.md` 세션 연속성 규칙
  - Phase B: `scripts/sync_claude_memory.py` (Claude memory ↔ Supabase) + start_db/end_db 통합
  - Phase C: `artifacts/claude_memory_schema.sql` Supabase DDL

## 다음 세션에서 할 작업

### 우선순위 0: LLM 문서 생성 파이프라인 Phase 3~6

설계 문서: `docs/features/2026-04-07-llm-powered-document-generation.md`

**완료된 Phase**: P1+P2 (커밋 `1db9e5be`)

**미완료 Phase**:
- P3: `core/project_pipeline.py` — `prepare()` 3분할 (`prepare_brief` + `prepare_documents` + 기존 하위 호환)
- P4: `core/clarification.py` 신규 (MacBook에 존재할 수 있음 — `ls core/clarification.py` 먼저 확인)
- P5: `interactive_chat.py` — Clarification 질문/답변 UI
- P6: 검증 (파서 호환, fallback, Clarification 스킵/기본값)

### 우선순위 1: gitignore 보안 정리 ⚠️ 중요

문제: `auth.json` (OAuth 토큰) 등이 git에 추적 중
```bash
git ls-files | grep -E "auth\.json|\.af_runtime/cli_sessions|\.system_generated/logs"
```

처리 대상:
- `.af_runtime/cli_sessions/*.json` — 런타임 세션 상태
- `.system_generated/logs/` — 런타임 로그
- `dist/af/_internal/` — 빌드 산출물

### 우선순위 2: Supabase claude_memory 테이블 생성 (Phase C 실행)

- `artifacts/claude_memory_schema.sql` 를 Supabase SQL Editor에서 실행
- 이후 `python end_db.py agent-factory` 로 현재 메모리 push 테스트

### 우선순위 3: Code-Review 문서 자동 업데이터

- `scripts/code_review_updater.py` (파일 존재), `core/hooks/code_review_doc.py` 구현 대기

### 우선순위 4: 기존 테스트 실패 (별도 이슈)

- `tests/test_requirement_llm.py` 2건 — 커밋 `a517e419` 이후 발생, 오늘 작업과 무관

## 관련
- [[code/symbols]]

