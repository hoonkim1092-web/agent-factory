# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: 2026-04-23 (브랜치: `2026-04-14-build-diet`)

---

## 세션 시작 체크리스트

```bash
cd D:\hoonProJect\worktrees\agent-factory
git pull
python start_db.py agent-factory   # Claude Code 메모리 + DB 동기화
```

---

## 현재 브랜치 상태

| 항목 | 상태 |
|------|------|
| 브랜치 | `2026-04-14-build-diet` |
| 마지막 커밋 | `eeb7cc37 feat(llm-doc-gen)` |
| origin 푸시 | ✅ 완료 |
| Review-Gate | 활성화 (`.githooks/pre-commit`) |

---

## 완료된 작업 (오늘 세션, 2026-04-23)

| # | 작업 | 커밋 |
|---|------|------|
| 1 | Graphify 크로스 프로바이더 스킬 통합 Phase 1+2 | `28ae5477` |
| 2 | Graphify COMPACT 연동 (Phase A Step 2) | `5f42ccba` |
| 3 | LLM 기반 work-item 문서 생성 파이프라인 P1+P2 | `af1bd81e` |

---

## 미완료 작업 (우선순위순)

### P0: LLM 문서 생성 파이프라인 Phase 3~6

**설계 문서**: `docs/features/2026-04-07-llm-powered-document-generation.md`

| Phase | 파일 | 작업 내용 |
|-------|------|----------|
| **P3** | `core/project_pipeline.py` | `prepare()` → 3분할: `prepare_brief()` + `prepare_documents()` + 기존 하위호환 |
| **P4** | `core/clarification.py` | 신규: Clarification 질문 생성 + Brief 병합 (MacBook에 존재할 수 있음 — 확인 필요) |
| **P5** | `interactive_chat.py` | Clarification 질문/답변 UI |
| **P6** | 검증 | 파서 호환, fallback, Clarification 스킵/기본값 |

**Why**: `(edit required)` 플레이스홀더 없는 실행 가능한 work-item 문서 생성.

---

### P1: gitignore 보안 정리 ⚠️ 중요

**문제**: `auth.json` (OAuth 토큰) 등이 git 추적 중 — 즉시 처리 필요

```bash
# 확인
git ls-files | grep -E "auth.json|\.af_runtime|_internal"
```

처리 대상:
- `.af_runtime/cli_sessions/*.json` — 런타임 세션 상태
- `.system_generated/logs/` — 런타임 로그
- `dist/af/_internal/` — 빌드 산출물

---

### P2: Cross-PC 세션 연속성 (현재 세션에서 구현 진행 중)

| Phase | 작업 | 상태 |
|-------|------|------|
| **A** | `NEXT_STEPS.md` 재작성 + `CLAUDE.md` 규칙 추가 | 🔄 진행 중 |
| **B** | `scripts/sync_claude_memory.py` 구현 + start_db 통합 | ⏳ 대기 |
| **C** | Supabase `claude_memory` 테이블 확장 | ⏳ 대기 |

---

### P3: Code-Review 문서 자동 업데이터

- `scripts/code_review_updater.py` (파일 존재), `core/hooks/code_review_doc.py` 구현 대기
- 현재 `code-review.md`는 수동 갱신 중

---

### P4: 기존 테스트 실패 (pre-existing, 별도 추적)

- `tests/test_requirement_llm.py` — 커밋 `a517e419` 이후 2건 실패
- 별도 이슈로 추적 (오늘 작업과 무관)

---

## 다음 세션에서 바로 시작할 명령

```bash
# P0: LLM 문서 생성 Phase 3
# 먼저 MacBook core/clarification.py 확인
ls core/clarification.py 2>/dev/null && echo "exists" || echo "not found"

# P1: gitignore 보안 (즉시 처리 권장)
git ls-files | grep -E "auth\.json|\.af_runtime/cli_sessions|\.system_generated/logs"
```

---

## 세션 종료 체크리스트

1. 완료된 작업을 이 파일 "완료된 작업" 테이블에 추가
2. 미완료 작업의 상태 업데이트
3. `git add NEXT_STEPS.md && git commit -m "chore: NEXT_STEPS 업데이트"`
4. `git push`
5. `python end_db.py agent-factory`  ← Claude Code 메모리 Supabase 동기화
