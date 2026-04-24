# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: 2026-04-25 B2-6 + 3순위 완료 (브랜치: `2026-04-14-build-diet`)

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
| 마지막 커밋 | `63990a71 fix(B2-6+C0+3순위)` |
| origin 푸시 | ✅ 완료 |
| Review-Gate | 활성화 (`.githooks/pre-commit`) |

---

## 완료된 작업

| # | 작업 | 커밋 | 날짜 |
|---|------|------|------|
| 1 | Graphify 크로스 프로바이더 스킬 통합 Phase 1+2 | `28ae5477` | 2026-04-23 |
| 2 | Graphify COMPACT 연동 (Phase A Step 2) | `5f42ccba` | 2026-04-23 |
| 3 | LLM 기반 work-item 문서 생성 파이프라인 P1+P2 | `af1bd81e` | 2026-04-23 |
| 4 | Phase A Step 2 COMPACT (RunBudget, FSA guard, PlanVerifier.gate, SkillPackBootstrapper) | `3b42cb06` | 2026-04-23 |
| 5 | LLM 문서 생성 P3~P6 (prepare 3분할, Clarification UI) | `a12f4493` | 2026-04-24 |
| 6 | gitignore 보안 정리 (.system_generated/logs+cache untrack) | `0defdfba` | 2026-04-24 |
| 7 | Cross-PC 메모리 동기화 — Supabase claude_memory 테이블 생성 + push/pull 검증 | — | 2026-04-24 |
| 8 | P3: PostToolUse hook 연결 — `.py` 편집 시 code-review.md 자동 갱신 | — | 2026-04-24 |
| 9 | Phase A Step 3+4: EVOLUTION(quality_delta+테스트) + MEMORY(semantic_scores, MemoryScope.PROJECT, M8 에피소드 주입) | `ffc9eaf5` | 2026-04-24 |
| 10 | version bump 1.2.21→1.2.22 + install-af.ps1 | `63990a71` | 2026-04-25 |
| 11 | B2-6 C0+C1+C2: write_project_board atomic write, strategy ledger 모듈별 granularity, nightly summary 모듈 섹션 | `63990a71` | 2026-04-25 |
| 12 | 3순위: CheckpointHook 등록, EpisodeRecord 필드 확장, DynamicOrchestrator record_episode | `63990a71` | 2026-04-25 |

---

## 미완료 작업 (우선순위순)

### Phase A: Step 3+4+5 ✅ 완료

- Step 3 (EVOLUTION): GateResult.quality_delta, SkillEvolutionBus/QualityGate/SelfEvolution 직접 테스트 29건
- Step 4 (MEMORY): MemoryScope.PROJECT, semantic_scores 전달, _recall_graph scope 수정, M8 에피소드 주입
- Step 5: version 1.2.22 bump + Blueprint 갱신 완료 (exe 빌드는 Windows에서 수행)

### B2-6: ✅ 완료

- C0: write_project_board atomic write
- C1: strategy ledger 모듈별 granularity (_record_ledger_outcomes, module_outcome_from_board, detect_owner_drift)
- C2: nightly summary 모듈 섹션, 12건 테스트

### 3순위: ✅ 완료

- CheckpointHook 등록 (agent_runner.py)
- EpisodeRecord.event_type/failure_pattern/root_cause 필드 추가
- DynamicOrchestrator._execute_agent_task finally에 record_episode

### P0 & P1 & P2: ✅ 모두 완료

- P0: LLM 문서 생성 파이프라인 P3~P6 (`a12f4493`)
- P1: gitignore 보안 (`0defdfba`)
- P2: Cross-PC 세션 연속성 — Supabase `claude_memory` 테이블 생성 완료, `end_db`/`start_db` 정상 동작 확인

### (구) P0: LLM 문서 생성 파이프라인 ✅ 완료 (P3~P6)

**설계 문서**: `docs/features/2026-04-07-llm-powered-document-generation.md`

모두 `a12f4493` 커밋에서 완료. 남은 작업 없음.

---

## 세션 종료 체크리스트

1. 완료된 작업을 이 파일 "완료된 작업" 테이블에 추가
2. 미완료 작업의 상태 업데이트
3. `git add NEXT_STEPS.md && git commit -m "chore: NEXT_STEPS 업데이트"`
4. `git push`
5. `python end_db.py agent-factory`  ← Claude Code 메모리 Supabase 동기화
