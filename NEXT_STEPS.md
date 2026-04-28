# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: 2026-04-28 Stage-1 설계 완료 + Blueprint §12 C1~C5 동기화 (브랜치: `2026-04-14-build-diet`)

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
| 마지막 커밋 | `32c42196 docs(stage1-design): Stage-1 설계 v3 + Blueprint §12 C1~C5 동기화` |
| origin 푸시 | ✅ 완료 (origin/2026-04-14-build-diet 동기화됨) |
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
| 13 | 통합 결함 10건 일괄 수정 — Sonnet/Codex 5.5/af-critic 3-Tier 검증 통과 (audit 4건 + Codex 신규 1건 + critic 2건 P0/P1 + cross-review 후속 5건) | `d809e72f` | 2026-04-25 |
| 14 | P0-C: event_bus.py W2 per-hook exception handling | `d809e72f` | 2026-04-25 |
| 15 | T1-1: canonical Checkpoint + RunEvent + af resume 서브커맨드 — 3-Tier 검증 통과 | `7b546ca0` | 2026-04-26 |
| 16 | T1-2: Atomic Task idempotency + RunEvent per-step — 3-Tier 검증 통과 | `0320d311` | 2026-04-26 |
| 17 | T2-5: 벡터 영속화 — similarity 전파 + project_id 동적화 + dedup tiebreaker — 3-Tier 검증 통과 | `2c1eb81a` | 2026-04-26 |
| 18 | T2-4: search_all_backends() memory_type/scope 필터 + cross-project 격리 수정 + cortex apply() project_id — 3-Tier 검증 통과 | `cb5adfcd` | 2026-04-26 |
| 19 | T3-7: Audit/Cost/Approval → RunEvent 통합 — COST_INCURRED + APPROVAL_REQUESTED/GRANTED + W3 fix + check_validity 신규 문서 감지 — 3-Tier 검증 통과 | `a4965cf1` | 2026-04-27 |
| 20 | T3-7 ACCEPT 2 후속: CLI --budget → set_run_budget run_id 연결 + approve() run_id 전달 + consumed_tokens 역기록 + 즉시 중단 가드 — 3-Tier 검증 통과 | `59b89f72` | 2026-04-27 |
| 21 | Stage-0 Hotfix C1~C7: self-evolution silent failure 7종 봉쇄 — 3-Tier 검증 통과 | `3145c224` | 2026-04-28 |
| 22 | Stage-1 설계: `docs/2026-04-28-self-evolution-stage1-design.md` v3 (14섹션, 3-라운드 교차검증 통과) + Blueprint §12 C1~C5 동기화 | `32c42196` | 2026-04-28 |

---

## 미완료 작업 (우선순위순)

> **2026-04-28 정리**: 모든 우선순위 항목이 완료되어 "완료된 작업" 테이블로 이동 완료.
> 현재 미완료 작업 없음. 새 작업이 시작되면 이 섹션에 추가.

### 다음 후보 (선택)

- **Stage-1 구현 Sprint 1**: `core/evolution_types.py` (EvolutionDecision enum/dataclass) + hook `run_id=` 파라미터 추가 + trigger whitelist (`_METADATA_TRIGGERS` / `_CODE_EVOLUTION_TRIGGERS`) — 설계: `docs/2026-04-28-self-evolution-stage1-design.md` §6/§7/§3
- **Stage-1 구현 Sprint 2**: `SelfEvolutionController` + `EvolutionLedger` 신규 파일 — 설계: §1/§4
- **Stage-1 구현 Sprint 3**: `CandidateStagingArea` candidate 격리 + `.bak` 제거 — 설계: §2/§5
- **exe 빌드 + Release**: Phase A Step 5에서 version 1.2.22 bump만 됐고 `python build_exe.py` + `gh release create af-fsa_v1.2.22` 미실행

---

## 세션 종료 체크리스트

1. 완료된 작업을 이 파일 "완료된 작업" 테이블에 추가
2. 미완료 작업의 상태 업데이트
3. `git add NEXT_STEPS.md && git commit -m "chore: NEXT_STEPS 업데이트"`
4. `git push`
5. `python end_db.py agent-factory`  ← Claude Code 메모리 Supabase 동기화
