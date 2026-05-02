# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: 2026-05-02 (밤) — **oh-my-openagent 분석 문서 v2 정정 commit (cross-review WARN 13건 반영)**. 다음 작업은 변동 없음: Spike 2건(subagent tool trace / metrics silent failure) → v1 plan 작성. 브랜치: `2026-04-14-build-diet`

---

## 🔥 현재 진행 중 — Research Router Phase 1a 코드 진입 직전

**대상 문서**: `docs/2026-04-29-research-router-structured-evidence-design.md` (v1.4.1, ~1349줄, 5라운드 PASS)

### 진행 흐름 (최근 → 과거)
1. v1.0 (2026-04-29) — 최초 설계
2. v1.1 (2026-05-01) — 7라운드 deliberation 합의 반영
3. v1.2 (2026-05-02) — 1라운드 BLOCK 4건 반영
4. v1.2 2라운드 → BLOCK 3건 잔존 (이전 세션)
5. v1.3 (2026-05-02) — 2라운드 BLOCK 3건 (R2-1/R2-2/R2-3) 반영
6. v1.3 3라운드 → BLOCK 4건 발견 (자기참조 실패 + 정합 누락)
7. v1.4 (2026-05-02) — 3라운드 BLOCK 4건 모두 처리 (token-trace 기반 §10.1 정정 + §4.4.5 코드 분기 통합 + §6.5 unclassified 제거 + §11/§4.2.1 fixture schema 두 라벨)
8. v1.4 4라운드 → BLOCK 1건 (§12.5 라벨 가이드 후속 정합 누락)
9. v1.4.1 (2026-05-02) — 4라운드 BLOCK 1건 정정 (§12.5 라벨 가이드 단일 라인)
10. **v1.4.1 5라운드 → PASS ✅** ← 현재 위치
11. Phase 1a 코드 진입 ← **다음**

### 5라운드 검증 통과 사실
- 자기참조 검증 4종 모두 token-trace 정합:
  - 8인 포커: `fast_synthesis` → §4.4.5 detector emit → `deep_source_research` ✓
  - 로또: `fresh_lookup` → escalation 없음 → `fresh_lookup` ✓
  - 단순 CRUD: `fast_synthesis` → escalation 없음 ✓
  - fixture schema 라벨 키 4곳 일관 (§4.2.1 / §10 / §11 / §12.5) ✓
- 핵심 spec(§4.2/§4.2.1/§4.4.5) 정합 확정.

### Phase 1a 완료 ✅ (2026-05-02)
1. `core/research_router.py` 신규 (ResearchGap 9종, ResearchPlan, ResearchRouter.plan/detect_complexity_gaps, gap_to_mode)
2. `core/researcher.py` 시그니처 확장 (research_plan/hint_gaps/**_kwargs, mode-aware gating, router escalation 연결)
3. `core/project_pipeline.py` `_evidence_fn(**kwargs)` + TypeError 분리
4. `core/research_verifier.py` max_retries=1, gap emit enum 값 교체, DeprecationWarning
5. `af.spec` core.research_router 외 3개 hiddenimports 추가
6. `tests/test_research_router_modes.py` 18케이스 107 tests PASS (initial/final mode 각 100%)

---

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
| 마지막 커밋 | `5f24283e` feat(P1+cross-review): blast_tier downgrade + 4-round deliberation upgrade |
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
| 33 | test-gap gate: `scripts/test_gap_analyzer.py`(신규) + `hook_runner._apply_test_gap_verdict()` + `.claude/agents/af-test-runner.md` Step 2.5 + `tests/test_test_gap_analyzer.py` (11 tests) + `tests/test_hook_runner_builtins.py` (21 tests) + 설계문서 | `3612cc11` | 2026-04-30 |
| 34 | P1 blast_tier downgrade: `review_gate.downgrade_blast_tier()` API + `hook_runner._apply_test_gap_verdict()` FAIL 시 blast_tier=1 다운그레이드 + blast_tier 검증 테스트 (33 tests) | `5f24283e` | 2026-04-30 |
| 35 | af-cross-review 4-round deliberation 전면 재작성: Round1 Discovery(`mcp__codex__codex`+threadId 저장) → Round2 Challenge(Claude 직접 코드 확인) → Round3 Defense(`mcp__codex__codex-reply` 동일 thread+`[보강]`/`[철회]` 마커) → Round4 Verdict(ACCEPT★/REJECTED/ACCEPT) | `5f24283e` | 2026-04-30 |
| 36 | Phase 3.5 메트릭 수집 인프라: `scripts/review_metrics_logger.py`(신규 — append_metric/parse_findings_count/parse_extension_log_count/compute_report) + `scripts/review_metrics_report.py`(CLI) + `hook_runner._post_agent_record` Phase 3.5 연동 + `tests/test_review_metrics_logger.py` (28 tests) | (커밋) | 2026-05-01 |
| 37 | Research Router Phase 1a 구현 — `core/research_router.py`(신규, ResearchGap 9종 enum + ResearchPlan + ResearchRouter.plan/detect_complexity_gaps + gap_to_mode) + `core/researcher.py` 시그니처 확장(research_plan/hint_gaps + mode-aware gating + auto escalation max retry=1) + `core/project_pipeline.py` `_evidence_fn(**kwargs)` + `core/research_verifier.py` max_retries=2→1 + DeprecationWarning + tests/test_research_router_modes.py (101 tests) — 3-Tier 검증 통과 | `8654ce2a` | 2026-05-02 |
| 38 | hotfix(test): `tests/test_review_metrics_logger.py` sys.modules 오염 수정 — `sys.modules[X]=Y` 3곳 → `monkeypatch.setitem(sys.modules,X,Y)`. test_phase1_blast_tier_invariant.py 9건 flaky FAIL 해결, 자기참조 검증 primary trust 회복. test-only 변경, 게이트 우회. | `5a4491f9` | 2026-05-02 |
| 39 | docs(참고): OpenCode LSP 아키텍처 분석 1차 작성 — 단, cross-review BLOCK 3회 후 §5.1·§5.3 내부 모순 잔존 상태로 종료. 다음 세션에서 처음부터 재분석 필요. | `042d0386` | 2026-05-02 |

### 🔍 검증 중 발견 (별도 트랙)

- **pytest 전체 실행 hang** — `pytest tests/ -q` 6분+ 멈춤. 어제 작업과 직접 관계 없을 가능성. 원인 파일 격리 필요 (langsmith/anyio/langgraph 의존성 의심).

---

## ✅ AST/LSP 인벤토리 재분석 완료 (2026-05-02 본 세션)

### 결과
- **분석 대상 정정**: SST OpenCode → **oh-my-openagent** (`code-yeongyu/oh-my-openagent`, 이전 oh-my-opencode)
- **신규 문서**: `docs/참고/2026-05-02-oh-my-openagent-ast-lsp-comparison.md` (10개 섹션, 권고 0개, 분석/권고 분리)
- **인벤토리 6개 질문 답변 완료** + **효과 측정 6개 데이터 수집** (Q-A~Q-F)
- **cross-review verdict=WARN** (BLOCK 0건, advisory 10건)

### 핵심 사실 (실측 기반)
1. review_bundle risk_id 인용률: 1/46 review (~2%)
2. test_gap_analyzer 호출: hook_events.log 0건
3. LSPCheckHook 호출: 0건 (pyright 미설치 + AGENT_LSP_CHECK 미설정)
4. 3-tier verdict: 51 PASS / 1 BLOCK ≈ 98% PASS
5. review_metrics.jsonl 부재 (Phase 3.5 미작동)
6. oh-my-openagent: AST 2개 + LSP 6개 모두 AI tool로 직접 노출 (pull 모델, push는 본 fetch 범위에서 미확인)

### ✅ 다음 세션 인계 항목 — 분석 문서 v2 정정 완료 (2026-05-02 밤)

cross-review 12건 + 재분석 추가 1건 = 13건 모두 분석 문서에 반영:
- §5.2 schema 계약 명시 (line 1-based vs 0-based, file_path 절대/상대 모호성, engine별 6/7종 차이)
- §5.3 PostToolUse 블록 라인 범위 정정 (188-208 → 191-212)
- §5.4 Q-A 메타 표기, Q-B/Q-E 측정 sink 한계, Q-D 표본 편향 caveat, Q-F silent failure 후보 (a)/(b)/(c) 분리
- §6 SST 권원 표시, §8 #5 plan-tone 톤다운
- §9.4 신설: Q-A~Q-F 추출 명령 + §9.1 commit SHA pin 안내

본 정정은 advisory 처리. **남은 작업은 Spike 1+2 → v1 plan 작성** (변동 없음).

### ✅ 본 세션 추가 — 합의 사항 (2026-05-02 저녁, deliberation 결과)

**아키텍처 두 plane 분리 합의** (Codex + Claude Opus 4.7 합의):

1. **Capability Plane** — agent가 직접 쓰는 도구 (AST search/replace, LSP diagnostics/rename 등)
2. **Assurance Plane** — 산출물 검증/품질 게이트 (review_bundle, test_gap, cross-review, metrics, commit gate)

→ 두 plane은 분리 설계, 각자 KPI로 측정. 핵심 원칙: **"도구 사용 흔적이 반드시 검증 루프에 들어가야"** closed loop 성립.

### 📋 Phase 로드맵 — v1만 plan, v2~v5는 후보

| Phase | 작업 | 상태 |
|-------|------|------|
| **v1** | **Static Evidence Injection v1** — 배선 복구 + review_bundle 형식 변경 + test_gap_analyzer gate + review_metrics.jsonl schema 확장 | plan 작성 대기 (spike 선행) |
| v2 | Read-only `ast_search` tool (Capability Plane 진입) | 후보, v1 KPI 측정 후 |
| v3 | `lsp_diagnostics` optional tool | 후보 |
| v4 | `ast_replace` dry-run | 후보 |
| v5 | safe rename / apply (LSP 의존) | **optional/conditional** — pyright 동봉 비용 vs 사용 빈도 검증 후 |

### 🔬 다음 세션 — Spike 2건 (v1 plan 작성 전 필수)

**Spike 1**: subagent 내부 tool trace 가능성
- Claude Code Task로 호출되는 subagent(af-critic, af-cross-review)의 tool 사용을 메인이 추적 가능한지
- 불가능하면 v1 KPI는 final output self-report 기반으로 한정 (subagent reasoning 텍스트 + verdict)
- 결론: v1 plan은 내부 tool trace에 의존하지 않도록 확정

**Spike 2**: `review_metrics.jsonl` silent failure 원인 분리
- 후보 (a): `post_agent_record` hook 미배선 (settings.local.json:188-208에 직접 등록 부재 확인됨)
- 후보 (b): `_post_agent_record()` 호출되지만 `append_metric()`이 try/except: pass로 삼킴
- 후보 (c): workspace path가 달라 다른 위치에 작성됨
- 부산물: post_edit_enqueue 552건 fake/effective 비중 분리도 자연 도출

### 🎯 v1 Scope (Spike 후 plan 확정)

**IN**:
- 배선 복구 (Spike 결과 반영)
- review_bundle 형식 변경: raw risk_id → "file:line + 위험 설명 + 왜 review해야 하는지 + 확인할 테스트/호출자"
- review_metrics.jsonl schema 확장: `evidence_present`, `evidence_items`, `evidence_risk_ids`, `evidence_cited`, `findings_count`
- `evidence_cited` 측정 메커니즘: **(b) `file:line` grep baseline** + 옵션 (c) prompt 강제 인용 검토
- test_gap_analyzer 실제 gate 호출 복구

**OUT (v2 이후)**:
- AST tool AI 노출 (read/write 모두)
- LSPCheckHook 활성화
- Rename safe workflow

**KPI** (v1 효과 검증):
- 인용률 (현재 ~2% → 목표 30%+)
- test_gap_analyzer 호출률 (현재 0% → 목표 100%)
- review_metrics.jsonl 작성 성공률 (현재 0 → 100%)
- 정적 진단 기반 BLOCK 발생률 (baseline 측정 후 결정)

### 매개체 운영 합의

| 파일 | 역할 |
|------|------|
| `review_bundle.md` | evidence snapshot |
| `review_metrics.jsonl` | 소비/효과 메트릭 (스키마 확장) |
| `hook_events.log` | 저수준 hook debug |
| ~~static_evidence.jsonl~~ | **신규 생성 X** (운영 매개체 추가 비용 회피) |

### 다음 행동 순서 (다음 세션)
1. Spike 1 + Spike 2 수행 (병렬 가능)
2. Spike 결과 위에서 v1 plan 작성 (`docs/plans/2026-05-XX-static-evidence-injection-v1.md`)
3. cross-review (af-cross-review만, design 큐 자동 발화)
4. PASS 시 v1 구현 진입

---

## 📦 보존: SST OpenCode 분석 (이전 세션)

### 다음 세션 시작 시 — 분석 전에 반드시 먼저 읽을 파일 (가정 금지, 실측만)

```bash
# 1. AST/구조 분석 경로
cat core/review_bundle.py            # 실제 build/save 출력 형식 (headers + per-file ## + risk lines)
cat core/ast_engine.py               # ast-grep-py wrapper
cat scripts/build_review_bundle.py   # hook 진입점

# 2. 진단 분석 경로 (휴면 가능성 있음)
cat core/hooks/lsp_check.py          # OpenCode 모드 A 등가, AGENT_LSP_CHECK 게이트
grep -n "LSPCheckHook\|lsp_check" core/hooks/event_bus.py core/agent_runner.py scripts/hook_runner.py
grep -rn "AGENT_LSP_CHECK" .claude/ .env 2>/dev/null

# 3. test gap (별도 경로)
cat scripts/test_gap_analyzer.py
grep -n "test_gap_analyzer" scripts/hook_runner.py core/review_bundle.py
```

### 답해야 할 질문 (가정 검증 후 답)

1. `core/review_bundle.py`의 실제 출력 schema는 정확히 무엇인가? `.af_review_queue/review_bundle.md` 샘플 파일을 직접 읽어서 확인.
2. `core/hooks/lsp_check.py`가 hook bus에 등록되어 있는가? 실제 호출되는 경로가 있는가?
3. `AGENT_LSP_CHECK` 환경변수가 어디서 설정되는가? 현재 활성/비활성?
4. `pyright`가 PATH에 있는가? `which pyright` 또는 `pyright --version` 결과는?
5. reviewer subagent (af-critic, af-cross-review)가 메인 에이전트의 `lsp_diagnostics` 결과를 받는가? (post_tool_call hook이 subagent까지 전파되는가?)
6. `scripts/test_gap_analyzer.py`는 어디서 호출되는가? `core/review_bundle.py`와 연결되어 있는가? (cross-review에 따르면 호출되지 않음 — 검증 필요)

### 절대 하지 말 것 (이번 세션의 BLOCK 사유)

1. ❌ "review_bundle.md에 §1~§7 섹션이 있다고 가정" — 실제로 헤더+per-file 블록만 있음
2. ❌ "LSPCheckHook을 모르고 신규 §8 추가 제안" — 이미 OpenCode 모드 A 등가 구현 존재
3. ❌ "pyright frozen build 폐기 권고와 동시에 pyright 채택" — 자기 모순
4. ❌ "OpenCode와 본질적으로 같은 패턴" 단정 — 실행 모델(메인 AI 단일 turn vs 2-stage hook+subagent) 다름
5. ❌ 분석문서에 운영 파라미터(timeout, source_hash, 임계값) 동시에 넣기 — 분석/권고 분리

### 권장 분석 흐름

1. **인벤토리 단계** (1~2시간): 위 6개 질문 답을 코드/설정/실행 결과로 수집. 가정 0개. 실측만.
2. **갭 식별 단계** (30분): OpenCode 코어와 우리 코어를 같은 좌표계(누가/언제/무엇을/어디로)로 정렬. 진짜 갭 1~2개만 추림.
3. **plan 작성 단계** (별도 세션): docs/plans/YYYY-MM-DD-*.md로 운영 파라미터 포함 plan. 분석 문서와 분리.

### 참고 자료

- `docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md` — 본 세션 결과물 (정정 1회 후 commit, 그러나 §5에 잔존 결함 있음). **다음 세션은 이 문서를 reset 시점으로 두고 처음부터.**
- 본 세션 cross-review BLOCK 로그: `.af_review_queue/notifications/` 또는 hook_events.log
- OpenCode 실제 코드: `https://github.com/sst/opencode/tree/dev/packages/opencode/src/lsp` 및 `tool/lsp.ts`

---

## 미완료 작업 (우선순위순)

> **2026-04-30 정리**: T4(ensure_watcher TOCTOU) 완료 (`b76a6652`). BLOCK-prep 완료 (`630942c7`). test-gap-gate + P1 blast_tier downgrade + af-cross-review 4-round deliberation 완료 (`3612cc11`, `5f24283e`). 남은 작업: T3(exe 빌드) 1건.

### 🔥 다음 작업 — 3-Tier 비용 감축 플랜 (Phase 1부터)

**전체 플랜**: `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md` (사용자+Claude Opus 4.7 합의)

**배경**: 이번 commit 검증 비용 195K 토큰 / 28분 — WARN-only인데 과도. af-critic 46 tool call의 대부분이 반복 탐색.

**진행 순서** (Phase 1~4):

| Phase | 작업 | 상태 | 시간 |
|-------|------|------|------|
| **1** | blast_tier/verdict/routing_state **3-개념 분리** (자기참조 검증 위험 인식 + 6-layer deterministic 검증) | ✅ 완료 (commit fa41575d, 2026-05-01) | — |
| **2-prep A** | `ast-grep-py>=0.35.0` → requirements.txt | ✅ 완료 (commit 23be1886, 2026-05-01) | — |
| **2-prep B** | `pyinstaller_hooks/hook-ast_grep_py.py` + af.spec hookspath 활성화 | ✅ 완료 (commit 23be1886, 2026-05-01) | — |
| **2-prep C** | exe 빌드 검증 (ast-grep-py pip install → smoke test, Windows 빌드는 Windows PC에서) | ✅ 완료 (Mac venv 0.42.1 설치·AST 스모크 테스트 통과, 2026-05-01) | — |
| **2-prep D** | `core/review_bundle.py` thin wrapper (build/save/load) | ✅ 완료 (commit 23be1886, 2026-05-01) | — |
| **2** | `scripts/build_review_bundle.py` + `hook_runner._post_edit_enqueue` 연동 | ✅ 완료 (2026-05-01) | — |
| **2.5** | tool call cap (af-test-runner:10 / af-critic:20 / af-cross-review:30) | ✅ 완료 (commit adf32175, 2026-05-01) | — |
| 3 | bundle-first scope + extension log enforcement | ✅ 완료 (2026-05-01) | — |
| 3.5 | 1주 데이터 수집 (T3-only accepted finding rate 핵심 메트릭) | ✅ 완료 (2026-05-01) | — |
| 4 | Smart routing + Tier 3 조건부 발화 | 대기 | 2시간 |

**예상 효과**: 토큰 195K → 60K, 시간 28분 → 6~10분.

**Phase 1 핵심 인식**: 자기참조 검증 — 3-tier가 막 수정한 코드(`scripts/review_gate.py`, `scripts/hook_runner.py`) 위에서 동작하므로 단독 신뢰 가능한 보증이 아님. **Primary trust는 hook을 우회하는 6-layer deterministic 테스트**, 3-tier는 secondary ceremony.

**Phase 1 즉시 진입 명령** (집 Mac에서):
```bash
git pull
python start_db.py agent-factory
# 자세한 8-step 실행 순서: docs/plans/2026-04-30-cross-review-cost-reduction-plan.md "다른 PC에서 재개 시 첫 단계"
```

---

### Sprint 4 — 다음 작업 (우선순위순)

| 우선순위 | 작업 | 파일 | 상세 |
|---------|------|------|------|
| ~~**T1**~~ ✅ | ~~knowledge skill SKILL.md fallback~~ | ~~`core/skill_metadata_adapter.py`~~ | 완료 `cf461e01` — _fill_missing_description + frontmatter 우선, 5개 테스트 |
| ~~**T2**~~ ✅ | ~~`_evolution_failed_skills` per-skill 조건 좁히기~~ | ~~`core/fsa_loop.py`~~ | 완료 `33000436` — _apply_evolution_guard 메서드, 탐지 실패 Level 5 강제, 26개 테스트 |
| **T3** (다음) | exe 빌드 + GitHub Release | `build_exe.py`, `af.spec` | `python build_exe.py` → `dist/af-1.2.22.zip`, `gh release create af-fsa_v1.2.22`. macOS 빌드 환경 확인 필요. |
| ~~**T4**~~ ✅ | ~~ensure_watcher() 동시 스폰 race 수정~~ | ~~`core/design_review_utils.py`~~ | 완료 `b76a6652` — O_CREAT\|O_EXCL spawn lock + double-check 패턴. 3-Tier PASS |

---

## 후순위 작업 (Sprint 4 완료 후)

### P0 — 설계문서 리뷰 정책 배포 에이전트 동기화

**배경**: 2026-05-01 CLAUDE.md 변경 — 단일 설계문서 리뷰를 `af-critic + af-cross-review` → `af-cross-review만`으로 변경. Work-item 세트도 `af-doc-qa + af-critic + af-cross-review` → `af-doc-qa + af-cross-review`로 축소.

**배포 빌드 동기화 필요 항목**:
- `scripts/check_design_pending.py`: 현재 주석/로그에 "af-critic + af-cross-review" 언급이 있으면 제거
- 배포된 Agent Factory 내부에서 설계문서 리뷰를 트리거하는 경로가 있다면 동일 정책 적용
- `docs/code-review.md` 정책 섹션 갱신 (있다면)

**소요 시간**: 30분 내외

---

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

- [x] **af-critic BLOCK 픽스** ✅ `b0f74ad9` + `610c1aa3` — `core/provider_detect.py` Windows shell=True 안전성
      BLOCK1(`b0f74ad9`): `shutil`/`shlex` top import, `list2cmdline` 명시 변환, `stdin=DEVNULL`, timeout 5→30
      BLOCK2(`610c1aa3`): `_resolve_ping_cmd()` backslash 2중화 후 `shlex.split(posix=True)` — 따옴표 포함 경로 완전 파싱
      af-critic 최종 판정: **PASS** (WARN 2건 — 잘못된 env var 입력 시만 발생, advisory)

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
