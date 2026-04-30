# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: 2026-04-30 P1 Sprint B (fan-out) 완료 (`74dfa3c5`) → 다음은 T3(exe 빌드) 또는 T4(watcher race 수정) (브랜치: `2026-04-14-build-diet`)

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
| 마지막 커밋 | `74dfa3c5` feat(sprint-b-fan-out): af-cross-review.md 동적 fan-out 재작성 |
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
| 29 | P1 설계문서 + hook 인프라 수정: `docs/2026-04-29-multi-provider-cross-review.md` (350줄, 13섹션) + `scripts/check_design_pending.py` (design 큐 폴링, JSON timestamp debounce, fired pruning) + `core/design_review_utils.py` (날짜패턴·work-items·patterns INCLUDE/EXCLUDE) + `settings.local.json` (PostToolUse 복원, check_design_pending 등록) + `CLAUDE.md` (af-design-review-pending 룰) — 3-Tier 검증 통과 | `6566c459` | 2026-04-29 |
| 30 | Phase 0 Proof-Carrying Review: `scripts/blast_radius.py` (결정적 Tier 분류기, path/regex, LLM 없음) + `review_gate.py` (round_started_at 토큰 모델, claim_id AF-RG format, clear 리셋, BLOCK fall-through) + `enqueue_agent_review.py` (_state_lock RMW + classify_with_content 락 밖 선계산) + `check_pending_review.py` (_state_lock RMW + cap/warn-only 1회 알림) + `af-critic.md` (BLOCK 기준 명시, 0 findings valid) + `tests/test_review_gate_phase0.py` (20 tests, 20 passed) — 모든 High 이슈 해소 | `24be4ace` | 2026-04-30 |
| 31 | P1 Sprint A: `core/provider_detect.py` 신규 — ProviderState(3-state) + 1h 디스크 캐시 + AF_SKIP_PROVIDER 마스킹(캐시 오염 방지) + AGENT_*_CLI_COMMAND env var override + ThreadPoolExecutor 병렬 ping + CLI entry `--json --exclude-self` + `tests/test_provider_detect.py` (20 tests) + `af.spec` hiddenimport — af-critic BLOCK 2건 + af-cross-review ACCEPT 3건 모두 해소 | `3e956d7f` | 2026-04-30 |
| 32 | P1 Sprint B: `af-cross-review.md` 동적 fan-out 재작성 — Step 0(3-gate: BLOCK/SKIP/CONTINUE) + Step 2(timeout 180s, python3 치환 macOS 호환, 오류파일 추적) + Step 3([ACCEPT★] 합의 가중치) + CLAUDE.md Tier 3 fan-out 설명 — af-critic WARN 3건 수정 완료 | `74dfa3c5` | 2026-04-30 |

---

## 미완료 작업 (우선순위순)

> **2026-04-30 정리**: T4(ensure_watcher TOCTOU) 완료 (`b76a6652`). BLOCK-prep 완료 (`630942c7`). 남은 작업: T3(exe 빌드) 1건.

### Sprint 4 — 다음 작업 (우선순위순)

| 우선순위 | 작업 | 파일 | 상세 |
|---------|------|------|------|
| ~~**T1**~~ ✅ | ~~knowledge skill SKILL.md fallback~~ | ~~`core/skill_metadata_adapter.py`~~ | 완료 `cf461e01` — _fill_missing_description + frontmatter 우선, 5개 테스트 |
| ~~**T2**~~ ✅ | ~~`_evolution_failed_skills` per-skill 조건 좁히기~~ | ~~`core/fsa_loop.py`~~ | 완료 `33000436` — _apply_evolution_guard 메서드, 탐지 실패 Level 5 강제, 26개 테스트 |
| **T3** (다음) | exe 빌드 + GitHub Release | `build_exe.py`, `af.spec` | `python build_exe.py` → `dist/af-1.2.22.zip`, `gh release create af-fsa_v1.2.22`. macOS 빌드 환경 확인 필요. |
| ~~**T4**~~ ✅ | ~~ensure_watcher() 동시 스폰 race 수정~~ | ~~`core/design_review_utils.py`~~ | 완료 `b76a6652` — O_CREAT\|O_EXCL spawn lock + double-check 패턴. 3-Tier PASS |

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

**진행 순서**: ~~설계문서(`docs/2026-04-29-multi-provider-cross-review.md`)~~ ✅ → ~~af-critic+af-cross-review 2-agent 검증~~ ✅ → ~~Sprint A: `core/provider_detect.py`~~ ✅ (커밋 `3e956d7f`) → **Sprint B** (`af-cross-review.md` fan-out)

~~**Sprint B**~~ ✅ (커밋 `74dfa3c5`): `.claude/agents/af-cross-review.md` Step 0(3-gate) + Step 2(병렬 fan-out, timeout 180s, macOS 호환) + Step 3([ACCEPT★] 합의 가중치) + CLAUDE.md Tier 3 fan-out 설명 추가

---

### P2 — Cross-Review 정확도·범용성 개선 (2026-04-30 합의)

**배경**: P1 Sprint B로 동적 fan-out 인프라 완성. 그 위에서 ① 외부 LLM 입력 quality, ② Tier 3 출력 표준화, ③ provider-agnostic 일반화 3개 축으로 5단계 로드맵.

**진행 순서**: BLOCK-prep → 1a → (1b dry-run) → 1a 운영 1주 관찰 → 2 → 3 → β2 (수요 신호 시)

- [x] **BLOCK-prep** ✅ `630942c7` — `core/provider_detect.py` ThreadPool race condition 수정
      수정: `_probe_one(provider_id, installed: frozenset)` 시그니처 변경, installed_set을 ThreadPool 전 main thread 1회 계산 후 전달
      추가: `registry.py` double-checked locking + `tests/test_provider_detect.py` T12/T13/T14 — 22/22 PASS
      af-critic WARN (BLOCK 없음), af-cross-review PASS

- [x] **Phase 1a** ✅ `a8025d25` — `.claude/agents/af-cross-review.md` Step 1+2+3 프롬프트 개선
      Step 1: diff 추출 + 50KB 폴백 / Step 2: PRIMARY/BONUS 분리 + 메타 인식 + No-BLOCK 명시 + 자기검증 + [출력 형식] / Step 3: BONUS 분리 처리 + No-BLOCK 무시
      다음: dry-run 1회 (§10.2) — 별도 세션에서 실제 커밋에 cross-review 적용 후 측정

- [ ] **Phase 1b** — `codex review` 빌트인 통합 (위험: 中)
      목적: Codex 0.125.0의 `codex review` 전용 빌트인이 `codex exec` 대비 결함 탐지율이 좋은지 데이터 검증
      산출물: dry-run 보고서 → 긍정 시 codex 호출 라인 교체
      **선행 조건**: `gemini auth login` 실행 (현재 AUTH_EXPIRED 상태) — gemini 합의★ 가중치 회복 필요
      결정 대기: 측정 시점, known-bug 샘플 출처(`docs/code_review/code-review.md` 활용 검토)
      의존: Phase 1a 완료 후

- [ ] **Phase 2** — 최종 판정 라벨 명시화 BLOCK/WARN/PASS (위험: 中)
      목적: CLAUDE.md 정책 3개(BLOCK 정책, WARN-only no-fire, max_rounds=2)가 의지하는 라벨 안정화
      산출물: 매핑 규칙 + Step 4 출력 블록 갱신 + (필요시) `review_gate.py` 파서 갱신
      결정 대기: 단독 [ACCEPT] Critical 처리(BLOCK vs WARN), [HOLD] 처리, Medium 임계
      의존: Phase 1a 1주일 운영 데이터 관찰 후

- [ ] **Phase 3** — Peer verification (외부 CLI 상호 fact-check) (위험: 中~高)
      목적: dedup 한계 보완 (다른 표현의 같은 결함, 한쪽만 본 거짓 양성)
      산출물: Step 2.5 신설 + 비용 측정 보고서
      결정 대기: 비용 2배 수용, 외부 LLM 형식 강제 가능성, fan_out=1 폴백 로직
      의존: Phase 1a + Phase 2 완료 후

- [ ] **β2** — Provider-agnostic orchestrator (위험: 高)
      목적: Claude lock-in 해제, SaaS 전략(`project_saas_strategy_position.md`) 정합
      산출물: `core/cross_review_runner.py` + 판정 프롬프트 3종(Claude/Codex/Gemini) + thin wrapper
      결정 대기: 외부 사용자 수요 검증(현재 0건), Codex plugin marketplace 진입점, 판정 quality 차이 감수
      의존: Phase 1a + 1b + 2 완료, 외부 사용자 수요 ≥ 1건

---

## 세션 종료 체크리스트

1. 완료된 작업을 이 파일 "완료된 작업" 테이블에 추가
2. 미완료 작업의 상태 업데이트
3. `git add NEXT_STEPS.md && git commit -m "chore: NEXT_STEPS 업데이트"`
4. `git push`
5. `python end_db.py agent-factory`  ← Claude Code 메모리 Supabase 동기화
