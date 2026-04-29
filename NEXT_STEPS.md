# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: 2026-04-29 Sprint 3 WARN 클리어 완료 + 커밋 푸시 완료 → 다음 PC에서 Sprint 4 진행 (브랜치: `2026-04-14-build-diet`)

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
| 마지막 커밋 | `875d5081` fix(sprint3-warn-clear): Sprint 3 WARN 클리어 — 9-라운드 3-Tier 검증 통과 |
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
| 23 | Stage-1 Sprint 1: `core/evolution_types.py`(EvolutionDecision/EvolutionResult) + RunEventType 4종 + `_METADATA_TRIGGERS`/`_CODE_EVOLUTION_TRIGGERS` whitelist + SkillSelfEvolutionHook `run_id=` + decision 체인(bus→event_bus→hook) + memory_consolidation Lock + agent_runner 연결 — 3-Tier 검증 통과 | `6235ad9d` | 2026-04-28 |
| 27 | T1: knowledge skill SKILL.md description fallback — `_fill_missing_description()` 신규, frontmatter 우선+body fallback, 5개 테스트 — 3-Tier 검증 통과 | `cf461e01` | 2026-04-29 |
| 28 | T2: fsa_loop per-skill 에스컬레이션 가드 — `_apply_evolution_guard()` 신규, 탐지 실패 Level 5 강제, 이중 탐색 제거, 26개 테스트 — 3-Tier 검증 통과 | `33000436` | 2026-04-29 |
| 24 | Stage-1 Sprint 2: `core/skill_evolution_controller.py`(SelfEvolutionController 7단계 파이프라인) + `core/evolution_ledger.py`(EvolutionLedger JSONL) + EVOLUTION_ROLLED_BACK RunEvent 직접 기록 + _publish() live-snapshot rollback + .bak 배포 방지 + get_default_store() thread-safe 싱글톤 + conftest AF_CHECKPOINT_DIR 픽스처 — 60 테스트 3-Tier 검증 통과 | (커밋 예정) | 2026-04-28 |
| 25 | Stage-1 Sprint 3: 호출사이트 3개(fsa_loop._try_evolve_failed_skill, cross_verification._trigger_evolution, dynamic_orchestrator._try_evolve_from_patterns) → SelfEvolutionController.submit() 교체, 3메서드 제거(_verify_evolved_skill/_rollback_skill/_cleanup_skill_baks), CANDIDATES_DIR 절대경로(config_paths.py), knowledge skill 지원(_is_knowledge_skill + SkillQualityGate early-return), skill_creator meta.yaml.bak 제거, GateResult 필수 필드 추가 — 70 테스트 3-Tier 검증 통과 | `0778ed42` | 2026-04-29 |
| 26 | Sprint 3 WARN 클리어 (9-라운드 3-Tier): fsa_loop DEFERRED/ERROR/REJECTED→None+_evolution_failed_skills 차단, Level 4 apply_pivot 조건 정리, gate_result is None 단순화, Level 4→5 강제에스컬레이션, run_mission 초기화, skill_quality_gate knowledge skill auto_register+_register_knowledge_skill, skill_creator update_skill knowledge type 보존(setdefault), skill_evolution_safety DEPRECATED 마커, fixture 모듈 속성 복원, 테스트 4종 신규 추가 — 81 테스트 통과 | `875d5081` | 2026-04-29 |

---

## 미완료 작업 (우선순위순)

> **2026-04-29 정리**: Sprint 3 + WARN 클리어 완료. Sprint 4 기술부채 2건 + Release 대기 중.

### Sprint 4 — 다음 작업 (우선순위순)

| 우선순위 | 작업 | 파일 | 상세 |
|---------|------|------|------|
| ~~**T1**~~ ✅ | ~~knowledge skill SKILL.md fallback~~ | ~~`core/skill_metadata_adapter.py`~~ | 완료 `cf461e01` — _fill_missing_description + frontmatter 우선, 5개 테스트 |
| ~~**T2**~~ ✅ | ~~`_evolution_failed_skills` per-skill 조건 좁히기~~ | ~~`core/fsa_loop.py`~~ | 완료 `33000436` — _apply_evolution_guard 메서드, 탐지 실패 Level 5 강제, 26개 테스트 |
| **T3** (다음) | exe 빌드 + GitHub Release | `build_exe.py`, `af.spec` | `python build_exe.py` → `dist/af-1.2.22.zip`, `gh release create af-fsa_v1.2.22`. macOS 빌드 환경 확인 필요. |

---

## 후순위 작업 (Sprint 4 완료 후)

### P1 — Multi-Provider Cross-Review 동적 fan-out

**목적**: 3-Tier 검증 파이프라인의 Tier 3(af-cross-review)을 구독 중인 AI 프로바이더에 따라 자동으로 확장·축소.

**핵심 동작**:
- 프로바이더 1개(Claude만) → Tier 3 skip
- 프로바이더 2개 이상 → 가용 외부 프로바이더 전부에 병렬 리뷰 요청 → 결과 합산 판정

**감지 3-state**:
| 상태 | 조건 | 동작 |
|------|------|------|
| `available` | CLI 설치 + ping 성공 | cross-check 포함 |
| `auth_expired` | CLI 설치 + ping 실패 | **블로킹** — 재인증 명령어 안내 (`AF_SKIP_PROVIDER=codex`로 1회 우회 가능) |
| `not_installed` | CLI PATH에 없음 | 조용히 skip |

**변경 파일**:
| 파일 | 작업 |
|------|------|
| `core/provider_detect.py` (신규) | CLI 설치·인증 감지, TTL 1h 캐시(`~/.af/provider_cache.json`) |
| `af.spec` | `hiddenimports`에 `core.provider_detect` 추가 |
| `.claude/agents/af-cross-review.md` | Step 0에서 감지 → 동적 fan-out (codex/gemini 병렬 호출) |
| `CLAUDE.md` | "교차검증 자동 실행" 룰: "Codex 호출" → "가용 외부 프로바이더 모두 호출 (없으면 skip)" |

**진행 순서**: 설계문서(`docs/2026-XX-XX-multi-provider-cross-review.md`) → af-critic+af-cross-review 2-agent 검증 → 구현 → 3-Tier 검증 → 커밋

---

## 세션 종료 체크리스트

1. 완료된 작업을 이 파일 "완료된 작업" 테이블에 추가
2. 미완료 작업의 상태 업데이트
3. `git add NEXT_STEPS.md && git commit -m "chore: NEXT_STEPS 업데이트"`
4. `git push`
5. `python end_db.py agent-factory`  ← Claude Code 메모리 Supabase 동기화
