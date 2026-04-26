# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: 2026-04-27 T3-7 Audit/Cost/Approval → RunEvent 통합 (브랜치: `2026-04-14-build-diet`)

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
| 마지막 커밋 | `a4965cf1 feat(T3-7): Audit/Cost/Approval → RunEvent 통합` |
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
| 13 | 통합 결함 10건 일괄 수정 — Sonnet/Codex 5.5/af-critic 3-Tier 검증 통과 (audit 4건 + Codex 신규 1건 + critic 2건 P0/P1 + cross-review 후속 5건) | `d809e72f` | 2026-04-25 |
| 14 | P0-C: event_bus.py W2 per-hook exception handling | `d809e72f` | 2026-04-25 |
| 15 | T1-1: canonical Checkpoint + RunEvent + af resume 서브커맨드 — 3-Tier 검증 통과 | `7b546ca0` | 2026-04-26 |
| 16 | T1-2: Atomic Task idempotency + RunEvent per-step — 3-Tier 검증 통과 | `0320d311` | 2026-04-26 |
| 17 | T2-5: 벡터 영속화 — similarity 전파 + project_id 동적화 + dedup tiebreaker — 3-Tier 검증 통과 | `2c1eb81a` | 2026-04-26 |
| 18 | T2-4: search_all_backends() memory_type/scope 필터 + cross-project 격리 수정 + cortex apply() project_id — 3-Tier 검증 통과 | `cb5adfcd` | 2026-04-26 |
| 19 | T3-7: Audit/Cost/Approval → RunEvent 통합 — COST_INCURRED + APPROVAL_REQUESTED/GRANTED + W3 fix + check_validity 신규 문서 감지 — 3-Tier 검증 통과 | `a4965cf1` | 2026-04-27 |

---

## 미완료 작업 (우선순위순)

### T1-2: ✅ 완료 (0320d311)

- DynamicOrchestrator idempotency guard + RunEvent per-step 방출
- _completed_subtask_keys() RunEventStore 세 번째 소스 (재시작 복원)
- restore_from() run_id 복원

### T2-5: ✅ 완료 (2c1eb81a)

- CortexVectorAdapter: similarity 점수 캡처, project_id 동적화, transient 값 영속화 방지
- facade: _vector_score 우선 랭킹, dedup tiebreaker, TTL 필터
- cortex: project_id 동적화, save_memory caller 우선

### T2-4: ✅ 완료 (cb5adfcd)

- search_all_backends() memory_type/scope 필터 추가 (search_semantic()과 인터페이스 통일)
- cortex_vector.py cross-project 격리 수정 (project_id=None → recall에 None 직통 전달)
- cortex.py apply() recall에 project_id 명시 전달, filter_dict={} if project_id is None
- cross_project.py find_similar_solutions() memory_type 파라미터 위임
- fetch_limit=limit*3 버퍼, TimeoutError 로깅 분기, expired debug 로그
- 신규 테스트 4건 + mock fix

### T3-7: ✅ 완료 (a4965cf1)

- RunBudget COST_INCURRED RunEvent (80%/exhausted 마일스톤)
- ApprovalGate APPROVAL_REQUESTED/GRANTED RunEvent
- is_execution_open() W3 fix — check_validity 항상 실행
- check_validity 신규 문서 감지 (승인 당시 없던 파일 사후 추가)
- generate_work_items/project_pipeline run_id 전파

**다음 작업 후보**:
- T3-7 ACCEPT 2 후속: CLI --budget 플래그에 run_id 연결 (set_run_budget 실제 호출 경로)
- agent_launcher.py approve() run_id 연결

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
