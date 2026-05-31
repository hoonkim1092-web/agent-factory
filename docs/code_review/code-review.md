# Agent Factory 전체 코드 리뷰

> 작성일: 2026-04-03
> 대상: core/ 175파일, 46,210줄
> 리뷰어: Claude Opus 4.6
> 상태: **스냅샷** — 코드 변경 시 해당 섹션 업데이트 필요

---

## 1. 프로젝트 통계

| 항목 | 수치 |
|------|------|
| core/ 파일 수 | 174 |
| core/ 총 라인 수 | 46,030 |
| 서브디렉토리 | 6개 (control, continuity, hooks, memory_system, providers, synergy) |
| 최대 파일 | agent_runner.py (1,419줄) |
| Dead code 파일 | 2개 (ise_loop, onboarding_wizard) |

### 서브디렉토리별 규모

| 디렉토리 | 파일 수 | 줄 수 | 역할 |
|----------|---------|-------|------|
| core/ (루트) | 113 | 33,637 | 런타임, 스킬, 대화, 연구 |
| core/control/ | 14 | 3,870 | Sidecar 유지보수 레이어 |
| core/memory_system/ | 15 | 2,440 | 에피소드 메모리, KG, decay |
| core/hooks/ | 10 | 1,693 | 실행 전후 훅 체인 |
| core/providers/ | 4 | 1,676 | CLI 프로바이더 추상화 |
| core/synergy/ | 5 | 1,176 | 멀티 에이전트 협업 |
| core/continuity/ | 4 | 352 | 세션 연속성, manifest |
| core/memory_system/adapters/ | 9 | 1,186 | 메모리 백엔드 어댑터 |

---

## 2. 서브시스템별 리뷰

### 2.1 실행 엔진 (Runtime Engine)

| 파일 | 줄 | 역할 |
|------|-----|------|
| `agent_runner.py` | 1,419 | 에이전트 실행 핵심. provider failover loop (L1076), _flush_trace (L863), multi-provider ordering (L966) |
| `agent_worker.py` | 109 | Worker subprocess 진입점. task.json → result.json 파일 IPC |
| `dynamic_orchestrator.py` | 887 | asyncio 5-concurrent 병렬 실행. board 기반 task dispatch, state_board 관리 |
| `model_router.py` | 262 | 역할→모델 매핑. provider-aware 라우팅 |
| `run_budget.py` | 58 | 글로벌 토큰 예산. 4char≈1token 휴리스틱, 80% 경고, 100% 중단 |
| `executor.py` | 120 | 단일 에이전트 실행 래퍼 |
| `evaluator.py` | 68 | 실행 결과 평가 |
| `failure_classifier.py` | 46 | INFRA/IMPLEMENTATION 이분류. _INFRA_PATTERNS로 quota/rate_limit/timeout 등 매칭 |

**문제점:**
- `run_budget.py`: 글로벌 싱글톤, 에이전트별 분해 없음 → v3 Feature 1로 해결 예정
- `agent_runner.py:1076`: failover에서 INFRA/IMPLEMENTATION 분류를 안 함 → v3 Phase 7로 해결 예정
- `dynamic_orchestrator.py:567-571`: frozen/source 분기가 inline → v3 Phase 1A `build_worker_cmd()`로 해결 예정

### 2.2 Control Plane (Sidecar 유지보수)

| 파일 | 줄 | 역할 |
|------|-----|------|
| `control/supervisor.py` | 550 | RuntimeSupervisor. heartbeat 30s, stall 120s, root cause analysis |
| `control/maintenance_pipeline.py` | 456 | prepare→execute 2-phase. conflict blocking wait (max 1hr) |
| `control/run_ledger.py` | 310 | append-only JSONL 저널. LedgerEntry dataclass, thread-safe |
| `control/intake.py` | 281 | ControlPlaneIntake. work_kind 분류 → execution_policy |
| `control/change_impact.py` | 298 | 변경 영향도 분석 |
| `control/continuity_snapshot.py` | 293 | 상태 스냅샷 저장/복원 |
| `control/rollback.py` | 412 | 롤백 메커니즘 |
| `control/regression_gate.py` | 243 | 회귀 테스트 게이트 |
| `control/maintenance_state.py` | 233 | 유지보수 상태 머신 |
| `control/lifecycle_bridge.py` | 238 | 실행 라이프사이클 브릿지 |
| `control/execution_policy.py` | 184 | 실행 정책 결정 |
| `control/issue_context.py` | 197 | 이슈 컨텍스트 수집 |
| `control/work_kind.py` | 119 | 작업 종류 분류 (bugfix/feature/maintenance) |
| `control_plane_llm.py` | 173 | CLI-first, API-fallback LLM 인터페이스 |

**문제점:**
- `control_plane_llm.py:50-56`: `detect_available_cli_providers()`만 호출, `AF_CONTROL_PLANE_PROVIDERS` 환경변수 미지원 → v3에서 연동 필요
- `supervisor.py`: ISELoop 미연결 → v3 Phase 1B에서 deep_update 경로 추가
- `run_ledger.py`: 에이전트별 비용 분해 없음 → v3 Phase 2에서 cost buffer 추가

### 2.3 Provider 레이어

| 파일 | 줄 | 역할 |
|------|-----|------|
| `providers/registry.py` | 253 | CLI_PROVIDER_IDS: claude_cli, gemini_cli, codex_cli. configure_providers(), detect_installed_cli_providers() (60s 캐시) |
| `providers/cli.py` | 764 | CliChatRequest/execute_cli_chat. 실제 CLI subprocess 호출 |
| `providers/session_adapter.py` | 642 | provider별 세션 설정. codex=wrapper_bridge (L110), frozen 빌드에서 hook 건너뜀 (L434) |
| `providers/__init__.py` | 17 | re-export |

**문제점:**
- `session_adapter.py:110`: codex_cli는 `mode="wrapper_bridge"`, `hook_events=()` → native hook 불가, AF EventBus 필요
- `session_adapter.py:434-436`: frozen 빌드에서 claude_cli hook 등록 스킵 → AF-owned checkpoint가 대안
- `registry.py`: `configure_providers()` 있지만 daemon에서 auto_configure 우회 경로 미구현

### 2.4 Hook 시스템

| 파일 | 줄 | 역할 |
|------|-----|------|
| `hooks/event_bus.py` | 155 | HookEventBus. register_hook(), run_pre/post_execute() |
| `hooks/checkpoint.py` | 68 | CheckpointHook. runs/{run_id}/checkpoint.json 저장/복원. PRIORITY=90 |
| `hooks/context_fork.py` | 313 | 컨텍스트 분기 관리 |
| `hooks/memory_consolidation.py` | 217 | 메모리 통합 훅 |
| `hooks/skill_self_evolution.py` | 200 | 스킬 자기 진화 |
| `hooks/langsmith_tracing.py` | 360 | LangSmith 트레이싱 |
| `hooks/lsp_check.py` | 213 | LSP 기반 코드 검증 |
| `hooks/guardrails.py` | 87 | 안전 가드레일 |
| `hooks/human_interrupt.py` | 49 | 사람 개입 포인트 |
| `hooks/base.py` | 31 | ContinuationHook 베이스 클래스 |

**문제점:**
- `event_bus.py`: provider 이벤트 → AF 이벤트 매핑 없음 → v3 Phase 8B에서 `on_provider_event()` 추가
- `checkpoint.py`: wake_checkpoint 미구현 → v3 Phase 5A에서 추가
- checkpoint 진실의 원천이 3개: manifest_store, CheckpointHook, wake_checkpoint(미구현) → v3에서 우선순위 명시 필요

### 2.5 메모리 시스템

| 파일 | 줄 | 역할 |
|------|-----|------|
| `memory_system/facade.py` | 346 | UnifiedMemoryFacade. 프로세스 전역 singleton |
| `memory_system/knowledge_injection.py` | 156 | KnowledgeInjectionHook. 에이전트별 개별 검색 |
| `memory_system/knowledge_forger.py` | 246 | 지식 생성/정제 |
| `memory_system/models.py` | 249 | 데이터 모델 |
| `memory_system/router.py` | 215 | 메모리 라우팅 |
| `memory_system/episode_extractor.py` | 144 | 에피소드 추출 |
| `memory_system/episode_matcher.py` | 140 | 에피소드 매칭 |
| `memory_system/decay.py` | 147 | 시간 기반 decay |
| `memory_system/graph_builder.py` | 138 | Knowledge Graph 빌더 |
| `memory_system/graph_query.py` | 141 | KG 쿼리 |
| `memory_system/issue_tracker.py` | 182 | 이슈 추적 |
| `memory_system/project_lifecycle.py` | 145 | 프로젝트 라이프사이클 |
| `memory_system/cross_project.py` | 64 | 크로스 프로젝트 지식 공유 |
| `memory_system/config.py` | 97 | 메모리 설정 |

**문제점:**
- `facade.py`: 프로세스 전역 singleton → 멀티 프로젝트에서 충돌 가능. Worker 프로세스 격리로 해결 (v3 Phase 8A)
- `knowledge_injection.py`: 에이전트마다 개별 검색 → 5에이전트=5회 중복. SharedContextBuilder (v3 Phase 4)로 해결

### 2.6 ISE (Iterative Self-Enhancement)

| 파일 | 줄 | 역할 |
|------|-----|------|
| `ise_loop.py` | 469 | Level 1~5 에스컬레이션. decompose_task() 호출 가능. **Dead code — 0 import** |
| `ise_redesigner.py` | 264 | decompose_task(): 3~7 서브태스크 생성, 의존성 정렬. ISELoop에서만 호출 |
| `ise_analyzer.py` | 220 | ISE 분석 엔진 |
| `ise_stall_detector.py` | 150 | ISE 정체 감지 |
| `ise_strategy_ledger.py` | 241 | ISE 전략 기록 |

**문제점:**
- `ise_loop.py`: 완전 dead code. 어디서도 import하지 않음
- `ise_redesigner.py`: ISELoop 통해서만 도달 가능 → 역시 dead
- v3 Phase 1B에서 DynamicOrchestrator `_should_decompose()` + Supervisor ISELoop 라우팅으로 활성화 예정

### 2.7 스킬 시스템

| 파일 | 줄 | 역할 |
|------|-----|------|
| `skill_creator.py` | 1,092 | 스킬 생성 엔진 |
| `skill_procurer.py` | 1,146 | 스킬 조달 + forge 품질 파이프라인. `procure_skill()`:119 installable 검증, `evaluate_and_promote()`:170 Eval→Promotion 공통, `_prepare_forge_context()`:225 LLM+도메인힌트+budget, `_generate_and_validate_evals()`:304 evals.yml 자동생성, `_evaluate_promote_and_register()`:360 평가→승격→Registry 등록, `forge_new_skill()`:397 3-helper 오케스트레이터, `FORGE_POLICIES`:158, `MAX_LLM_CALLS=15`:165 |
| `skill_eval_harness.py` | 735 | 스킬 평가 하네스. `_load_skill_callable()`:594 forge parent dir sys.path 스킵 (네임스페이스 충돌 방지) |
| `skill_registry.py` | 536 | 스킬 레지스트리. `external_scanned` property, `should_rescan_external()` (mtime 기반) |
| `skill_preflight.py` | 470 | 스킬 사전 검증 |
| `skill_metadata_adapter.py` | 449 | 메타데이터 어댑터 |
| `skill_feedback.py` | 365 | data/skill-usage.jsonl 기록 |
| `skill_retrieval_engine.py` | 345 | 스킬 검색 엔진 |
| `skill_loader.py` | 341 | 스킬 로더 |
| `skill_enricher.py` | 311 | 스킬 보강 |
| `skill_promotion.py` | 295 | 스킬 승격 |
| `skill_spec_synthesizer.py` | 290 | 스킬 명세 합성 |
| `skill_evolution_bus.py` | 243 | 스킬 진화 버스 |
| `skill_forge.py` | 236 | 스킬 단조 |
| `skill_cache.py` | 171 | 스킬 캐시 |
| `skill_metadata.py` | 129 | 스킬 메타데이터 |
| `skill_autodiscover.py` | 115 | 스킬 자동 발견 |
| `skill_context_config.py` | 110 | 스킬 컨텍스트 설정 |
| `knowledge_skill.py` | 90 | 지식 스킬 |
| `external_skill_sources.py` | — | `CodexOfficialSkillSource`, `ClaudeOfficialSkillSource` (신규), `_extract_skill_id()` (frontmatter name 우선) |
| `external_skill_source_ids.py` | — | 소스 ID 정규화. `claude_official` 추가, `DEFAULT_EXTERNAL_SOURCE_PRIORITY` 갱신 |

**최종 수정**: 2026-04-03

**변경 사항 (cross-cli-skill-discovery v3)**:
- `skill_registry.py`: `ensure_skills_loaded()` — `count()==0` 체크 → `external_scanned` 플래그로 교체. 유지보수 시 신규 외부 스킬 미감지 버그 수정
- `skill_registry.py`: `should_rescan_external()` — 외부 디렉토리 mtime 기반 변경 감지 (기존: 디렉토리 basename 비교)
- `external_skill_sources.py`: `_extract_skill_id()` — frontmatter `name` 우선, 디렉토리명 fallback (기존: 디렉토리명만)
- `external_skill_sources.py`: `ClaudeOfficialSkillSource` — `~/.claude/skills/`, `PROJECT/.claude/skills/` 탐색
- `external_skill_source_ids.py`: `claude_official` 소스 ID + 우선순위 (`codex_official` 다음)

**참고:** 스킬 시스템은 v3 설계 범위 밖. cross-cli-skill-discovery는 완료.

### 2.8 대화/연구 엔진

| 파일 | 줄 | 역할 |
|------|-----|------|
| `interactive_chat.py` | 887 | 대화형 채팅 엔진 |
| `researcher.py` | 894 | 연구 엔진 |
| `conversation_manager.py` | 822 | 대화 관리자 |
| `context_window_manager.py` | 633 | 컨텍스트 윈도우 관리. compaction 미구현 |
| `conversation_prompts.py` | 166 | 대화 프롬프트 |
| `conversation_room.py` | 215 | 대화 룸 |
| `conversation_task_adapter.py` | 142 | 대화↔태스크 어댑터 |

**문제점:**
- `context_window_manager.py`: `should_compact()`, `compact()` 미구현 → v3 Phase 5B에서 추가
- `interactive_chat.py`: 자동 compaction 트리거 없음 → v3 Phase 5B에서 추가

### 2.9 파이프라인/보드

| 파일 | 줄 | 역할 |
|------|-----|------|
| `project_pipeline.py` | 778 | ProjectPipeline. prepare→execute 흐름 |
| `project_task_board.py` | 759 | 프로젝트 태스크 보드. next_board_tasks(), update_project_board_task() |
| `work_item_generator.py` | 541 | 작업 항목 생성 |
| `work_item_parser.py` | 294 | 작업 항목 파싱 |
| `bootstrap_roles.py` | 472 | 역할 부트스트랩 |

### 2.10 인프라/유틸리티

| 파일 | 줄 | 역할 |
|------|-----|------|
| `config_paths.py` | 101 | 모듈 레벨 상수. PROJECT_ROOT, AGENTS_DIR, RUNS_DIR 등 |
| `engine_auth.py` | 182 | auto_configure_cli_provider() — 단일 provider 자동 선택 |
| `concurrency.py` | 207 | BackgroundTaskManager, circuit breaker |
| `utils.py` | 363 | 범용 유틸리티. `resolve_skill_paths()`:226 forge directory 구조 우선+flat fallback, `get_external_skill_roots()` (personal>project 순서, Tier 2에 `PROJECT_ROOT/skills/` 포함, Claude 경로 포함), `get_codex_skill_roots` alias 유지 |
| `file_io.py` | 124 | 파일 I/O 헬퍼 |
| `file_lock.py` | 92 | 크로스 프로세스 파일 락 |
| `git_manager.py` | 94 | Git 조작 |
| `dashboard.py` | 118 | 대시보드 데이터 기록 |
| `llm_engine.py` | 219 | Gemini API 기반 LLM 엔진 |
| `policy.py` | 40 | policy.yaml 로더 |
| `policy_runtime.py` | 54 | 런타임 정책 적용 |

**문제점:**
- `config_paths.py`: 모듈 레벨 상수 → import 시점 고정. Worker 프로세스 격리로 해결 (v3)
- `engine_auth.py`: `auto_configure_cli_provider()` — daemon에서는 부적합, `configure_providers()` 직접 호출 필요

### 2.11 기타

| 파일 | 줄 | 역할 |
|------|-----|------|
| `cross_verification.py` | 760 | 멀티 LLM 교차 검증 |
| `parallel_critique.py` | 371 | 병렬 비평 |
| `consensus_engine.py` | 364 | 합의 엔진 |
| `fsa_loop.py` | 397 | 5-cycle FSA 루프 (EXECUTE→TRACE→EVAL→SUMMARIZE→REFLECT) |
| `pdca_commands.py` | 759 | PDCA 커맨드 |
| `pdca_state.py` | 246 | PDCA 상태 머신 |
| `synergy/bridge.py` | 693 | 시너지 브릿지 |
| `synergy/process.py` | 181 | 시너지 프로세스 |
| `synergy/job.py` | 107 | 시너지 작업 |
| `synergy/tools.py` | 157 | 시너지 도구 |
| `ingestion_pipeline.py` | 144 | 문서 수집 파이프라인. MIN_REINDEX_INTERVAL=60s 하드코딩 |
| `document_index.py` | 406 | 문서 인덱스 |
| `document_chunker.py` | 234 | 문서 청크 분할 |

### 2.12 진입점 및 빌드

| 파일 | 줄 | 역할 |
|------|-----|------|
| `run_factory_cli.py` | 289 | 메인 CLI 진입점. subcommand 라우팅 |
| `af.spec` | 212 | PyInstaller 빌드 명세. hiddenimports 100+개 수동 관리 |
| `version.py` | 1 | `__version__ = "1.2.17"` |
| `policy.yaml` | 99 | 스킬 리스크 분류, 모델 라우팅, 태스크 분해 규칙 |

---

## 3. 상세 버그 및 기술부채

### 3.1 Critical — 크래시 또는 데이터 손실 가능

| ID | 파일 | 라인 | 문제 | 상태 |
|----|------|------|------|------|
| C1 | `ise_loop.py` | 274-278 | 에스컬레이션 결정에 도달 불가 코드 (return 2 unreachable) | ✅ 수정됨 |
| C2 | `hooks/checkpoint.py` | 63-64 | Non-atomic 파일 쓰기. 저장 중 크래시 시 checkpoint 손상 | ✅ 수정됨 |
| C3 | `hooks/context_fork.py` | 211-233 | Thread.join(timeout)이 실제 스레드를 중단하지 않음. 좀비 스레드 가능 | ✅ 수정됨 |
| C4 | `memory_system/issue_tracker.py` | 83-91 | `gh` CLI subprocess에 shell escape 누락. injection 위험 | ✅ 수정됨 |

### 3.2 High — 잘못된 동작

| ID | 파일 | 라인 | 문제 | 상태 |
|----|------|------|------|------|
| H1 | `dynamic_orchestrator.py` | 609,722 | state_board 비동기 업데이트에 asyncio.Lock 없음. race condition | ✅ 수정됨 |
| H2 | `agent_runner.py` | 589-637 | `_skill_module_cache` 무한 증가. 폐기 메커니즘 없음 | ✅ 수정됨 |
| H3 | `ise_redesigner.py` | 111,171 | JSON 파싱 실패 시 silent fallback → 무한 retry 루프 가능 | ✅ 수정됨 |
| H4 | `control/intake.py` | 112 | `continuity_snapshot.get("overall_health")` vs 실제 키 "recovery_health" | ✅ 수정됨 |
| H5 | `dashboard.py` | 17 | 글로벌 `_DASHBOARD_CACHE` 스레드 안전하지 않음 | ✅ 수정됨 |
| H6 | `control_plane_llm.py` | 50-56 | `AF_CONTROL_PLANE_PROVIDERS` 환경변수 미지원 | ✅ 수정됨 |

### 3.2.1 검증 중 추가 발견 (2026-04-03)

수정 검증 과정에서 발견된 추가 버그 및 개선:

| ID | 파일 | 문제 | 상태 |
|----|------|------|------|
| H6a | `control_plane_llm.py:55` | H6 수정에서 `return`이 API 엔진 초기화를 건너뜀 → CLI+API 동시 사용 불가 | ✅ 수정됨 |
| H2a | `agent_runner.py:640` | H2 캐시 퇴거 시 `sys.modules` 엔트리 미정리 → 메모리 누수 | ✅ 수정됨 |
| H5a | `dashboard.py:95,106` | H5는 Lock만 추가. 파일 쓰기 자체가 non-atomic (C2와 동일 유형) | ✅ 수정됨 |
| C4a | `issue_tracker.py:88` | C4에서 `list_issues`의 `labels` 파라미터 미검증 | ✅ 수정됨 |
| C4b | `issue_tracker.py:70` | `_sanitize_arg`가 `\n`을 허용 — issue_id/title에 부적절 | ✅ 수정됨 |

### 3.2.2 Forge 품질 파이프라인 구현 중 발견 (2026-04-07)

| ID | 파일 | 문제 | 상태 |
|----|------|------|------|
| C5 | `skill_procurer.py:380` | `SkillMetadata(path=..., source=...)` — 존재하지 않는 필드명으로 TypeError. `source_path`, `distribution_source`가 올바른 필드명 | ✅ 수정됨 |
| H7 | `skill_procurer.py:124` | `read_skill_lock()` 키 조회 시 `safe_id()` 미적용. `lock_skill_state()`는 `safe_id()`로 키 저장하므로 대문자/특수문자 포함 시 lock 키 불일치 | ✅ 수정됨 |

### 3.2.3 optional-id 정규화 work-item (2026-05-19)

| ID | 파일 | 문제 | 상태 |
|----|------|------|------|
| H8 | `core/utils.py` | `safe_id("")` = `"skill"` 계약 버그 — task_id·owner_role·candidate_id 등 optional 식별자 22개 파일 114곳에서 빈 값→`"skill"` 오염. `if not id` 가드 무력화·유령 수신자·잘못된 중복 제거 발생 | ✅ 수정됨 (`safe_optional_id()` 신설, 114개 B-site 교체) |

### 3.3 Medium — 성능/유지보수

| ID | 파일 | 라인 | 문제 |
|----|------|------|------|
| M1 | `control/run_ledger.py` | 276-292 | `_read_all()` 전체 JSONL 매번 순회. O(n) |
| M2 | `hooks/event_bus.py` | 40-46 | 훅 중복 체크 O(n²) |
| M3 | `hooks/lsp_check.py` | 40 | Pyright 타임아웃 15초 하드코딩. 에이전트 블로킹 |
| M4 | `ise_stall_detector.py` | 35,43 | 매직넘버 threshold (0.5, 0.8) 문서화 없음 |
| M5 | `agent_runner.py` | 352-489 | OpenAI/Anthropic 응답 처리 코드 거의 동일. 중복 |
| M6 | `dynamic_orchestrator.py` | 582-598 | Terminal 모드 0.5초 폴링. 이벤트 기반 전환 권장 |
| M7 | `ise_loop.py` | 91 | 외부 while True 루프에 max meta-cycles 없음 |
| M8 | `run_budget.py` | 전체 | 동시성 Lock 없음. 멀티스레드에서 race condition |
| M9 | `af.spec` | 19-173 | hiddenimports 100+개 수동 관리. 누락 시 frozen 빌드 런타임 크래시 |
| M10 | 다수 파일 | — | Non-atomic JSON 쓰기 패턴 잔존 (아래 참조) |

**M10 상세 — Non-atomic 파일 쓰기 잔존 목록** (C2/H5a와 동일 유형, 미수정):

| 파일 | 쓰기 대상 | 위험도 |
|------|----------|--------|
| `conversation_manager.py:130,145,181` | metadata/consensus/index.json | Medium |
| `document_index.py:351` | INDEX_CACHE_FILE | Low (캐시) |
| `ise_strategy_ledger.py:196` | ise_ledger_{run_id}.json | Medium |
| `pdca_state.py:92` | pdca_state.json | Medium |
| `project_pipeline.py:135` | checkpoint/{stage}.json | Medium |

### 3.4 이미 수정된 버그 (control/ 영역)

| ID | 파일 | 내용 | 상태 |
|----|------|------|------|
| BUG-2 | `rollback.py:248` | path traversal 방어 (pathlib.is_relative_to) | ✅ 수정됨 |
| BUG-3 | `run_ledger.py:96` | 스레드/프로세스 lock 추가 | ✅ 수정됨 |
| BUG-7 | `maintenance_pipeline.py:66` | conflict 무한 대기 → 1시간 timeout | ✅ 수정됨 |
| BUG-8 | `issue_context.py:179` | issue ID 중복 → UUID suffix | ✅ 수정됨 |
| BUG-9 | `continuity_snapshot.py:116` | conflict 시 health 격하 | ✅ 수정됨 |
| BUG-10 | `rollback.py:326` | checkpoint 체크섬 검증 시 dict 변형 방지 | ✅ 수정됨 |
| BUG-14 | `maintenance_state.py:135` | transition_log metadata 타입 통일 | ✅ 수정됨 |
| BUG-15 | `maintenance_state.py:109` | 파일 손상 시 재초기화 금지 | ✅ 수정됨 |

### 3.5 신규 기능 추가 (2026-04-03)

| 파일 | 기능 | 비고 |
|------|------|------|
| `core/hooks/code_review_doc.py` | 에이전트 실행 후 자동 코드 리뷰 + 문서 업데이트 Hook | 신규 (~180줄) |

---

## 4. Dead Code 목록

| 파일 | 줄 | 상태 | 비고 |
|------|-----|------|------|
| `ise_loop.py` | 469 | **0 import** | v3 Phase 1B에서 활성화 예정 |
| `onboarding_wizard.py` | 191 | **0 import** | 삭제 검토 필요 |

---

## 4. Checkpoint 진실의 원천 (Source of Truth)

현재 3개의 checkpoint 메커니즘이 **우선순위 없이** 공존:

| 메커니즘 | 파일 | 저장 위치 | 기록 내용 |
|----------|------|-----------|-----------|
| OrchestratorManifestStore | `core/continuity/manifest_store.py` | `.af_manifest.json` | 오케스트레이터 전체 상태 (board, cycle, config) |
| CheckpointHook | `core/hooks/checkpoint.py` | `runs/{run_id}/checkpoint.json` | 에이전트 상태 (cycle, current_task, eval_history) |
| wake_checkpoint (미구현) | 설계 중 | `.af_runtime/daemon/wake_checkpoint.json` | 데몬 wake 상태 (pending_costs, budget, stage) |

**v3에서 정의할 우선순위:**
1. `wake_checkpoint` — daemon crash 복구 (가장 구체적, 가장 최근)
2. `manifest_store` — 오케스트레이션 중간 상태 복원
3. `CheckpointHook` — 개별 에이전트 사이클 복원 (가장 일반적)

---

## 5. 비용 추적 진실의 원천 (Source of Truth)

현재 비용 관련 데이터가 분산:

| 데이터 | 위치 | 내용 |
|--------|------|------|
| 글로벌 토큰 합계 | `run_budget.py` 싱글톤 | in-memory, 에이전트 구분 없음 |
| 스킬별 사용량 | `data/skill-usage.jsonl` | SkillFeedback, 에이전트별 아님 |
| 실행 트레이스 | `.af_runtime/control/trace_*.jsonl` | 상세 실행 로그 |
| 실행 결과 | `run_ledger.jsonl` | 성공/실패, 메타데이터 |

**v3에서 정의할 canonical source:**
- **상세**: `trace_*.jsonl` (기존 유지, 변경 없음)
- **요약**: `run_ledger.jsonl` → `metadata.tokens_total`, `metadata.tokens_by_provider` 등
- **글로벌 카운터**: `run_budget.py` (기존 유지, 에이전트별 분해는 RunLedger가 담당)

---

## 6. Provider 연동 현황

| 컴포넌트 | claude_cli | gemini_cli | codex_cli | 비고 |
|----------|-----------|-----------|-----------|------|
| `engine_auth.py` | auto-config | auto-config | auto-config | 단일 provider 선택 |
| `agent_runner.py` | failover loop | failover loop | failover loop | INFRA 분류 미적용 |
| `session_adapter.py` | native hook (frozen 제외) | native hook | wrapper_bridge, hook 없음 | codex 가장 제한적 |
| `control_plane_llm.py` | CLI 호출 | CLI 호출 + API fallback | CLI 호출 | AF_CONTROL_PLANE_PROVIDERS 미지원 |
| `providers/registry.py` | configure_providers() | configure_providers() | configure_providers() | daemon용 우회 경로 필요 |

---

## 7. v3 설계와의 매핑

| v3 Phase | 해결하는 문제 | 영향 파일 |
|----------|-------------|-----------|
| 1A (spawn helper) | inline frozen/source 분기 | dynamic_orchestrator.py, utils.py |
| 1B (태스크 분해) | ISE dead code | dynamic_orchestrator.py, supervisor.py |
| 2 (비용 추적) | 글로벌 싱글톤 예산만 | run_ledger.py, agent_runner.py |
| 3 (context 파일) | PROJECT_CONTEXT.md 미생성 | docs/PROJECT_CONTEXT.md |
| 4 (SharedContext) | 에이전트별 중복 검색 | dynamic_orchestrator.py |
| 5A (wake checkpoint) | checkpoint 3중 무질서 | checkpoint.py |
| 5B (compaction) | context_window_manager 미구현 | context_window_manager.py, interactive_chat.py |
| 6 (af serve) | one-shot만 가능 | daemon_supervisor.py, daemon_worker.py |
| 7 (provider policy) | auto_configure 단일 선택 | control_plane_llm.py, agent_runner.py |
| 8A (멀티 프로젝트) | config_paths 모듈 상수 | Worker 프로세스 격리 |
| 8B (훅 브릿지) | codex hook 불가 | event_bus.py, session_adapter.py |

---

## 8. ISE 시스템 상세 (Dead Code 분석)

ISE(Infinite Self-Enhancement)는 5개 파일, 1,344줄로 구성된 완전한 시스템이지만 **0개 파일에서 import됨**.

| 파일 | 줄 | 역할 | 주요 버그 |
|------|-----|------|----------|
| `ise_loop.py` | 469 | Meta-loop 오케스트레이터. Level 1-5 에스컬레이션 | L274-278: unreachable code, L91: 무한 루프 가능 |
| `ise_redesigner.py` | 264 | LLM 기반 태스크 재설계/분해 | L111,171: JSON 실패 시 silent retry, L30-42: 창의성 10개 고정 |
| `ise_analyzer.py` | 220 | 실패 분석 엔진 (6개 카테고리) | L207-217: LLM 타임아웃 없음, L218: 예외 silent pass |
| `ise_strategy_ledger.py` | 241 | 전략 기록/학습/반복 방지 | L225: SHA256 16자 truncation → 충돌 가능 |
| `ise_stall_detector.py` | 150 | 엔트로피 기반 정체 감지 | L35,43: threshold 매직넘버 문서화 없음 |

### ISE 실행 흐름 (활성화 시)

```
ISELoop.run_mission()
  ├─ while True:   ← ★ max meta-cycles 없음
  │   ├─ StallDetector.check(ledger) → "continue" | "creativity_injection" | "human_escalation"
  │   ├─ FSALoop.run_mission()  ← 5-cycle 내부 루프
  │   │   ├─ AgentRunner.run()
  │   │   ├─ CrossVerificationLoop.run() [2+ CLI 시]
  │   │   └─ StrategyEvaluator.evaluate_failure()
  │   ├─ ISEAnalyzer.analyze_failure() → ISEAnalysis
  │   ├─ _decide_escalation(ledger, analysis) → Level 1-5
  │   │   ├─ Level 1: apply_retry_feedback()
  │   │   ├─ Level 2: apply_pivot()
  │   │   ├─ Level 3: redesign_task()
  │   │   ├─ Level 4: evolve_skills()
  │   │   └─ Level 5: decompose_task() → 3-7 subtasks
  │   └─ StrategyLedger.record_attempt() + save()
  └─ 성공 또는 human_escalation 시 종료
```

---

## 9. 핵심 실행 흐름

```
[사용자 요청]
    ↓
[run_factory_cli.py] → argparse → route
    │
    ├─ af run → [ControlPlaneIntake.normalize()]
    │              ├─ WorkKindClassifier → ExecutionPolicy
    │              ├─ ChangeImpactProfiler → ImpactProfile
    │              └─ RunLedger.open_run()
    │              ↓
    │           [MaintenancePipeline.prepare() → execute()]
    │              ├─ _handle_conflicts() (stale auto-close, 1hr timeout)
    │              ├─ RuntimeSupervisor.supervise()
    │              │   ├─ heartbeat 30s, stall 120s
    │              │   └─ DynamicOrchestrator.run_project()
    │              │       ├─ ControlPlaneLLM (Lilith) → task 분배
    │              │       ├─ asyncio 5-concurrent
    │              │       └─ AgentRunner.run() × N
    │              │           └─ provider failover (claude→gemini→codex)
    │              ├─ RegressionSafetyGate.check() (pytest)
    │              └─ RunLedger.close_run()
    │
    ├─ af chat → InteractiveChat (887줄)
    ├─ af serve → DaemonSupervisor (v3 Phase 6, 미구현)
    └─ af worker → AgentWorker → task.json IPC → result.json
```

---

## 2026-04-09 14:17 — `agent-factory_harness_Claude_Setup_and_Pipeline_v1` (05b4acbf)

**Context**: test run

**Changed (13)**: `.claude/settings.local.json, .system_generated/cache/document_index.json, Master_Blueprint.md, core/fsa_loop.py, core/plan_verifier.py, core/project_pipeline.py, data/skill-usage.jsonl, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, resume_brief.md, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-10 10:16 — `agent-factory_harness_Claude_Setup_and_Pipeline_v1` (7c533d17)

**Context**: test: hook 동작 확인

**Changed (403)**: `.claude/settings.local.json, Master_Blueprint.md, build/af/Analysis-00.toc, build/af/COLLECT-00.toc, build/af/EXE-00.toc, build/af/PKG-00.toc, build/af/PYZ-00.pyz, build/af/PYZ-00.toc, build/af/af.exe, build/af/af.pkg, build/af/base_library.zip, build/af/warn-af.txt, build/af/xref-af.html, core/control_plane_llm.py, core/engine_auth.py ... (+388)`

### Findings

- [Low] .claude/settings.local.json — `run_id`가 `run_1775746160_c1`로 하드코딩되어 있어 다음 세션에서 충돌/덮어쓰기 가능성 있음
- [Low] .claude/settings.local.json — 파일 끝 newline 제거됨 (POSIX 비준수, diff noise 유발)
- [Info] .claude/settings.local.json — Windows 경로(`C:/Users/HOON/...`)와 macOS 경로(`/usr/local/Cellar/...`) hook이 동일 설정 파일에 공존 — 의도된 멀티플랫폼 설정인지 확인 필요
- [Info] Master_Blueprint.md — `last_updated` 날짜만 변경, 코드 변경에 대응하는 실질적 섹션 업데이트 없음

No critical/high/medium issues found.

---

## 2026-04-13 22:15 — `2026-04-11-setup-wizard-tavily-notebooklm` (325949e9)

**Context**: Phase 2 잔여: research_engine/researcher/research_assistant 스킬 nlm 전환 + state 기반 archive UUID + install-af.sh 신규 + install-af.ps1 1.2.19 + Chrome/__check-nlm 검증

**Changed (404)**: `.claude/settings.local.json, .gitignore, .system_generated/cache/document_index.json, Master_Blueprint.md, build/af/Analysis-00.toc, build/af/COLLECT-00.toc, build/af/EXE-00.toc, build/af/PKG-00.toc, build/af/PYZ-00.pyz, build/af/PYZ-00.toc, build/af/af.exe, build/af/af.pkg, build/af/base_library.zip, build/af/warn-af.txt, build/af/xref-af.html ... (+389)`

### Findings

```json
{
  "review": [
    "- [Medium] install-af.sh:79 — `rm -rf \"${INSTALL_ROOT}\"` 직전에 `.af_setup_state.json`(사용자별 TAVILY 키 + archive_notebook_id UUID)을 보존하지 않음. 주석(line 13-14)은 schema v1 자동 마이그레이션을 약속하지만, 파일이 먼저 삭제되면 마이그레이션 대상이 사라져 재설치 시 setup 재입력 강제. `_get_env_path()`는 dev 모드에서 `$HOME/.local/share/af/.env` 옆에 state를 저장하므로 INSTALL_ROOT 하위에 상주.",
    "- [Low] core/research_engine.py:159 / skills/research_assistant/skill.py:93 — nlm CLI 서브커맨드 순서를 `query notebook <id>` → `notebook query <id>` 로 역전. 두 파일 모두 동일하게 변경되었지만 nlm 0.x의 실제 verb 순서 검증 흔적이 리뷰 범위에 없음; 잘못되면 모든 NotebookLM 조회가 런타임에 조용히 실패 후 `_is_auth_error` 를 우회(비인증 에러 메시지라) 재인증도 발동하지 않음.",
    "- [Low] skills/research_assistant/skill.py:134 — archive 미설정 시 `_query_notebooklm`이 한국어 안내 문자열을 정상 답변처럼 반환. 상위 `generate_research_report`가 그대로 보고서 본문에 삽입해 산출물 품질 훼손 가능. 빈 문자열 또는 구조화 dict 리턴으로 분리 권장.",
    "- [Low] install-af.sh:92 — macOS BSD `mktemp -t af-src-XXXXXX.tar.gz` 는 접미사를 보존하지 않아 실제 파일명이 `af-src-XXXXXX.tar.gz` 가 아닌 랜덤 문자열일 수 있음. `tar -xzf` 는 동작하므로 기능적 영향 없음(참고용).",
    "- [Info] install-af.sh:124 — requirements.txt 부재 시 fallback 5개 패키지만 설치하여 실제 기동 시 import 누락 가능. 릴리스 태그 tarball에는 항상 포함될 것으로 가정되지만, 실패를 fail() 로 바꾸는 편이 안전."
  ]
}
```

---

## 2026-04-16 22:18 — `2026-04-14-build-diet` (31c70ea4)

**Context**: edit: core/providers/cli.py

**Changed (11)**: `.claude/settings.local.json, .system_generated/cache/document_index.json, Master_Blueprint.md, core/providers/session_adapter.py, data/skill-usage.jsonl, project_board_state.json, projects/smoke_test/dashboard.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

The diff doesn't contain changes to `core/providers/cli.py` — it only shows `.claude/settings.local.json` modifications. Reviewing what's provided:

- **[Medium]** .claude/settings.local.json:60 — `Bash(rm -rf /tmp/af_test ...)` is allow-listed but `Bash(rm:*)` is also in the deny list (line 126). Deny takes precedence in Claude Code, so the explicit `/tmp` rm allowance is effectively dead — verify intent or remove the redundant allow entry.
- **[Medium]** .claude/settings.local.json:104-105 — `Bash(kill 20171 20169)` is allow-listed with hardcoded PIDs. This is a one-off debugging artifact that should be removed; it grants no useful future permission.
- **[Low]** .claude/settings.local.json:178-179 — Hook command changed from `$(git rev-parse ...)` dynamic resolution to hardcoded absolute path `/Users/hoon/workTree/agent-factory`. This breaks if the repo is cloned to a different location or worktree. The `timeout: 15` field was also dropped — hooks without timeout can hang indefinitely.
- **[Low]** .claude/settings.local.json:87-107 — Large batch of one-off `curl`, `awk`, `du`, `md5` commands polluting the allowlist. Consider using wildcard patterns or cleaning up after exploratory sessions.
- **[Info]** .claude/settings.local.json — `settings.local.json` is machine-specific and shouldn't be committed. Verify it's in `.gitignore`.

No `core/providers/cli.py` changes were present in the diff to review.

---

## 2026-04-21 00:46 — `2026-04-14-build-diet` (1f3fb884)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py

**Changed (20)**: `.claude/settings.local.json, core/memory_system/strategy_ledger.py, tests/_tmp/af-test-1d782932/proj_retry/.af/ise_ledger_run_retry_fsa.json, tests/_tmp/af-test-1d782932/proj_retry/.af/lineage_ledger.json, tests/_tmp/af-test-1d782932/proj_retry/.todo.md, tests/_tmp/af-test-26d98d16/proj_retry/.af/ise_ledger_run_retry_fsa.json, tests/_tmp/af-test-26d98d16/proj_retry/.af/lineage_ledger.json, tests/_tmp/af-test-26d98d16/proj_retry/.todo.md, tests/_tmp/af-test-37c2e253/proj_retry/.af/ise_ledger_run_retry_fsa.json, tests/_tmp/af-test-37c2e253/proj_retry/.af/lineage_ledger.json, tests/_tmp/af-test-37c2e253/proj_retry/.todo.md, tests/_tmp/af-test-62ed486c/proj_retry/.af/ise_ledger_run_retry_fsa.json, tests/_tmp/af-test-62ed486c/proj_retry/.af/lineage_ledger.json, tests/_tmp/af-test-62ed486c/proj_retry/.todo.md, tests/_tmp/af-test-82b151a3/proj_retry/.af/ise_ledger_run_retry_fsa.json ... (+5)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-24 13:03 — `2026-04-14-build-diet` (c9e457b8)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/clarification.py

**Changed (210)**: `.claude/settings.local.json, data/skill-usage.jsonl, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/general/codex_chat/user_a2fe66cb4ed5_20260310_060825_410585.json, projects/global_hoon_main/data/memory/general/codex_chat/user_a4de250b37b9_20260310_060825_397333.json, projects/global_hoon_main/data/memory/general/codex_chat/user_a505e86e169e_20260310_060825_468578.json, projects/global_hoon_main/data/memory/general/codex_chat/user_a544bee67f5c_20260226_153246_468128.json, projects/global_hoon_main/data/memory/general/codex_chat/user_a5d3412d72d4_20260310_174038_003526.json, projects/global_hoon_main/data/memory/general/codex_chat/user_a934361c0993_20260309_163142_493745.json, projects/global_hoon_main/data/memory/general/codex_chat/user_ab37978c1537_20260226_153246_773490.json, projects/global_hoon_main/data/memory/general/codex_chat/user_abb725748471_20260310_144545_364924.json, projects/global_hoon_main/data/memory/general/codex_chat/user_agent_factory_a613572954af_20260310_174038_111254.json, projects/global_hoon_main/data/memory/general/codex_chat/user_agent_factory_agent_factory_codex_12f60c8b305d_20260226_153246_147480.json, projects/global_hoon_main/data/memory/general/codex_chat/user_agent_factory_cli_e075b366c1e6_20260310_174038_109765.json ... (+195)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-28 09:04 — `2026-04-14-build-diet` (f08735b9)

**Context**: edit: /Users/hoon/workTree/agent-factory/tests/test_skill_evolution_safety.py

**Changed (104)**: `.claude/settings.local.json, af.spec, core/cross_verification.py, core/dynamic_orchestrator.py, core/fsa_loop.py, projects/global_hoon_main/data/memory/general/codex_chat/user_e382e2aeae16_20260310_144545_389276.json, projects/global_hoon_main/data/memory/general/codex_chat/user_e397d6845625_20260310_065854_438869.json, projects/global_hoon_main/data/memory/general/codex_chat/user_e65d7908b5e0_20260226_153246_782309.json, projects/global_hoon_main/data/memory/general/codex_chat/user_e736364d3199_20260310_144545_344240.json, projects/global_hoon_main/data/memory/general/codex_chat/user_e9c492db6c1f_20260310_065854_379731.json, projects/global_hoon_main/data/memory/general/codex_chat/user_end_db_agent_factory_b68f578618ba_20260309_143912_886620.json, projects/global_hoon_main/data/memory/general/codex_chat/user_end_db_agent_factory_cd779874c3e8_20260310_144545_352957.json, projects/global_hoon_main/data/memory/general/codex_chat/user_end_db_antigravity_201ae2978647_20260226_160958_691630.json, projects/global_hoon_main/data/memory/general/codex_chat/user_end_db_antigravity_5556b0e6aa4e_20260226_153246_733927.json, projects/global_hoon_main/data/memory/general/codex_chat/user_envagent_global_user_key_environmentgetenvironmentvariableagent_global_user_keyuser_e831467de9d1_20260226_153246_477160.json ... (+89)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-29 10:31 — `2026-04-14-build-diet` (9d491d6c)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\core\skill_metadata_adapter.py

**Changed (8)**: `core/skill_metadata_adapter.py, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py, syncCompyne/workspace_context_cli.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-29 13:34 — `2026-04-14-build-diet` (d0947735)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```
- [High]   .claude/settings.local.json:38 — "Bash(codex exec *)" 와일드카드 허용은 임의 codex 명령 실행을 허용하므로 보안 리스크. 허용 범위를 구체적인 서브커맨드로 제한 필요.

- [High]   .claude/settings.local.json:62,72,82,92,102 — python3 + $PWD → 하드코딩된 절대 경로(D:/hoonProJect/worktrees/agent-factory)로 교체. 다른 PC·워크트리에서 hook이 즉시 깨짐. $PWD 또는 상대 경로 유지 권장.

- [Medium] data/skill-usage.jsonl — report_path/promotion_path에 두 가지 절대 경로 혼재: /Users/hoon/workTree/ (Mac) 와 D:\\warkSpaces\\agent-factory\\ (Windows, 오탈자 "warkSpaces"). 경로가 런타임에 쓰인다면 파일 조회 실패.

- [Low]    data/skill-usage.jsonl — skill-eval-report.json 레코드 여러 줄이 contract_pass_rate=0.0, runtime_total=0인 채로 candidate 승격. 평가 데이터 없이 승격되는 로직이 의도적인지 확인 필요.

- [Info]   .claude/settings.local.json — settings.local.json은 PC-로컬 파일이나 git 추적 중. 절대 경로가 커밋되면 팀 공유 시 오염 발생. .gitignore 추가 또는 settings.json과 분리 고려.
```

**요약**: 핵심 문제는 `codex exec *` 와일드카드 허용(보안)과 하드코딩 절대 경로(이식성). 두 항목 모두 수정 권장.

---

## 2026-04-29 13:35 — `2026-04-14-build-diet` (03335e38)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:37 — `Bash(codex exec *)` 와일드카드 허용은 임의의 codex exec 명령을 모두 승인함. 최소 권한 원칙 위반 — 실제 사용 패턴에 맞게 구체적 명령으로 제한 필요.",
    "- [Medium] .claude/settings.local.json:62~106 — 훅 command가 `D:/hoonProJect/worktrees/agent-factory/` 하드코드 절대경로로 고정됨. 다른 PC·워크트리에서 이식 불가. `$PWD` 또는 환경변수 기반으로 복원 권장.",
    "- [Low] .claude/settings.local.json:125 — 파일 끝 개행 없음(no newline at EOF). JSON 파서 무결성 문제는 없으나 컨벤션 불일치.",
    "- [Info] data/skill-usage.jsonl — 신규 skill_promotion 이벤트 행 추가. 기능상 이상 없음.",
    "- [Info] 나머지 14개 파일(docs, memory, syncCompyne) — diff 본문 미포함으로 내용 검토 불가. 주요 변경이 있다면 별도 diff 제공 필요."
  ],
  "summary": "핵심 위험은 두 가지: codex exec 와일드카드 권한(High)과 훅 절대경로 하드코딩(Medium). 나머지는 경미하거나 정보성."
}
```

---

## 2026-04-29 13:35 — `2026-04-14-build-diet` (019cc3ce)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:38 — `\"Bash(codex exec *)\"` 와일드카드 허용은 임의의 codex exec 명령 실행을 허용하므로 권한 범위가 지나치게 넓음. 구체적인 서브커맨드로 제한 필요.",
    "- [High] .claude/settings.local.json:62,72,82,92,102 — 훅 command에 절대경로(`D:/hoonProJect/worktrees/agent-factory`) 하드코딩. 다른 PC/워크트리로 이동 시 훅이 무음 실패하며, settings.local.json이 커밋되므로 다른 개발자에게도 전파됨.",
    "- [Medium] .claude/settings.local.json — `python3` → `python` 변경. Windows에서 `python`이 Microsoft Store 스텁으로 해석될 수 있어 훅 실행 실패 위험. `python3` 유지 또는 전체 경로 명시 권장.",
    "- [Medium] .claude/settings.local.json — `$PWD` 제거로 상대경로 기반 실행이 불가능해짐. worktree 체크아웃 위치가 바뀌면 전체 훅이 고장. 환경변수 또는 git-toplevel 기반 동적 경로 사용 권장.",
    "- [Low] .claude/settings.local.json:125 — 파일 끝 개행 누락(no newline at end of file). 일부 git diff 도구 및 린터에서 경고 발생.",
    "- [Info] data/skill-usage.jsonl, skill-eval-report.json — 자동 생성 데이터 파일이 소스 커밋에 포함됨. `.gitignore` 처리 여부 재검토 권장 (런타임 상태 데이터는 리포에 추적 불필요).",
    "- [Info] syncCompyne/*.py — diff 본문이 잘려 있어 Python 파일 변경 내용 검증 불가. 해당 파일의 실질 변경이 있다면 별도 리뷰 필요."
  ]
}
```

---

## 2026-04-29 13:36 — `2026-04-14-build-diet` (9ff808b7)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:38 — `Bash(codex exec *)` 와일드카드 허용은 임의 codex 명령 실행을 열어줌. 최소 권한 원칙 위반.",
    "- [High] .claude/settings.local.json:62,71,81,92,103 — 훅 커맨드에 절대 경로 하드코딩(`D:/hoonProJect/worktrees/agent-factory`). 다른 PC/경로에서 세션 훅 전체 무음 실패. `$PWD` 또는 상대 경로로 복원 필요.",
    "- [Medium] data/skill-usage.jsonl — `report_path`/`promotion_path`에 macOS 경로(`/Users/hoon/workTree/...`) 혼재. Windows 워크트리 경로와 불일치 — 이벤트 재처리 시 경로 해석 오류 가능.",
    "- [Low] .claude/settings.local.json (마지막 줄) — 파일 끝 개행 제거. diff noise 및 일부 파서 호환성 문제.",
    "- [Info] 변경 범위가 feat(T1) 제목과 불일치. SKILL.md fallback 로직 관련 `.py` 파일 변경이 diff에 없음 — 실제 구현 파일이 누락되었거나 별도 커밋으로 분리 필요."
  ]
}
```

---

## 2026-04-29 13:36 — `2026-04-14-build-diet` (62cb8c0c)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
[
  {
    "severity": "High",
    "file": ".claude/settings.local.json",
    "line": "60-110",
    "finding": "모든 hook command가 `D:/hoonProJect/worktrees/agent-factory` 절대 경로로 하드코딩됨. 다른 PC·워크트리에서 즉시 실패. 원래 `$PWD` 변수 방식으로 복원 필요."
  },
  {
    "severity": "High",
    "file": ".claude/settings.local.json",
    "line": "37",
    "finding": "`Bash(codex exec *)` 와일드카드 허용 추가 — 임의 codex 명령을 무제한 실행할 수 있어 권한 범위가 과도하게 넓음. 허용 패턴을 구체적으로 제한해야 함."
  },
  {
    "severity": "Medium",
    "file": ".claude/settings.local.json",
    "line": "60-110",
    "finding": "`python3` → `python` 변경. Windows 환경에서는 동작하나, `python`이 PATH에 없거나 Python 2를 가리키는 환경에서 hook silent-fail 가능."
  },
  {
    "severity": "Medium",
    "file": "data/skill-usage.jsonl",
    "line": "all new entries",
    "finding": "`report_path` / `promotion_path` 필드에 `/Users/hoon/workTree/agent-factory/` macOS 절대 경로가 기록됨. 현재 Windows 워크스페이스와 불일치 — 경로 해석 시 오류 발생 가능."
  },
  {
    "severity": "Low",
    "file": ".claude/settings.local.json",
    "line": "125",
    "finding": "파일 끝 개행 문자 제거(`\\ No newline at end of file`). JSON 파일 표준 위반이며 일부 파서에서 경고 발생."
  }
]
```

---

## 2026-04-29 13:37 — `2026-04-14-build-diet` (097f0332)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:38 — `Bash(codex exec *)` wildcard allows ANY codex exec command; should be scoped to specific subcommands to prevent unintended privilege escalation.",
    "- [Medium] .claude/settings.local.json:62,72,82,92,102 — Hardcoded absolute Windows path `D:/hoonProJect/worktrees/agent-factory` replaces portable `$PWD`; breaks if repo is moved or used on another machine/worktree.",
    "- [Medium] .claude/settings.local.json — `python3` replaced with `python`; on Windows `python` may resolve to Python 2 or the Store stub, causing silent failures. Use explicit `python3` or full path.",
    "- [Low] .claude/settings.local.json:125 — Trailing newline removed (no newline at end of file). Minor POSIX convention violation; some tools diff-noisily against this.",
    "- [Info] data/skill-usage.jsonl — Appended promotion event rows contain `/Users/hoon/workTree/...` (macOS path) in `report_path`/`promotion_path`; these are log data but indicate the event was generated on a different machine. Not a bug, but suggests the log was partially replayed cross-environment.",
    "- [Info] Changed files list includes syncCompyne/*.py, skills/*, docs/code_review/code-review.md, and bridge state JSONs but no diff was provided for them — review is limited to the supplied diff only."
  ]
}
```

---

## 2026-04-29 13:37 — `2026-04-14-build-diet` (1775d8e6)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:38 — `Bash(codex exec *)` 와일드카드 허용은 codex exec 경로를 통한 임의 명령 실행을 허용함. 최소 권한 원칙 위반 — 필요한 서브커맨드만 명시적으로 열거해야 함.",
    "- [High] .claude/settings.local.json:62~106 — 절대경로 하드코딩(`D:/hoonProJect/worktrees/agent-factory`). 워크스페이스 이동 또는 다른 PC에서 실행 시 모든 hook이 침묵하며 실패. `$PWD` 또는 환경변수 기반으로 복원해야 함.",
    "- [Medium] .claude/settings.local.json:62~106 — `python3` → `python` 변경. Windows 환경에서는 일반적으로 `python`이 맞지만, 일관성 없이 혼용되거나 PATH에 없는 경우 hook 무음 실패 위험.",
    "- [Medium] data/skill-usage.jsonl — `report_path` / `promotion_path` 값이 macOS 경로(`/Users/hoon/workTree/...`)로 기록됨. Windows 환경에서 생성된 이벤트임에도 Mac 경로가 삽입 — 경로 생성 로직이 OS를 감지하지 못하는 버그 의심.",
    "- [Low] .claude/settings.local.json (마지막 줄) — 파일 끝 개행 없음(no newline at EOF). JSON 파싱에는 무해하나 git diff 노이즈 유발.",
    "- [Info] 변경 범위 불일치: 커밋 메시지는 `feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback`이나 diff에서 SKILL.md fallback 관련 코드 변경이 없음. 실제 core 변경이 누락되었거나 커밋 메시지가 잘못된 것으로 보임 — 확인 필요."
  ]
}
```

---

## 2026-04-29 13:38 — `2026-04-14-build-diet` (8f859574)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\tests\test_phase7_dep_graph_evolve.py

**Changed (19)**: `.claude/settings.local.json, Master_Blueprint.md, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md ... (+4)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-29 13:38 — `2026-04-14-build-diet` (8f859574)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (17)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+2)`

### Findings

```
- [High] .claude/settings.local.json:38 — `Bash(codex exec *)` wildcard grants unrestricted codex execution permission; scope is too broad, should be narrowed to specific subcommands.
- [High] .claude/settings.local.json:62,72,83,93,103 — Hardcoded absolute Windows paths (`D:/hoonProJect/worktrees/...`) replace portable `$PWD`. Breaks on any other machine or if the repo is relocated; defeats the purpose of worktree isolation.
- [Medium] core/fsa_loop.py:270-274 — If `_detect_failed_skill_dir()` returns `None` (skill name undetectable from log text), `_cand_name` is `None`, `None in self._evolution_failed_skills` is always `False`, and Level 4 → 5 escalation is silently skipped. A skill that exhausted evolution budget but produces ambiguous error text will loop indefinitely at Level 4.
- [Low] .claude/settings.local.json:125 — Missing newline at end of file (cosmetic, but diff noise in future patches).
- [Info] core/fsa_loop.py:264-278 — The per-skill escalation refinement is correct in intent (avoids blocking unrelated skills), but the silent fallback on detection failure (see Medium above) should at minimum emit a warning log.
```

**Summary:** Two actionable issues — the wildcard `codex exec *` permission needs tightening, and the `None`-detection fallback in the Level 4→5 escalation path can suppress escalation silently. The hardcoded paths are a portability regression that should revert to `$PWD`-relative or an env var.

---

## 2026-04-29 13:39 — `2026-04-14-build-diet` (89a68f56)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- [High] `.claude/settings.local.json:38` — `"Bash(codex exec *)"` wildcard allows any codex exec command. Overly broad; scope to specific subcommands.
- [High] `core/fsa_loop.py:270-274` — If `_detect_failed_skill_dir()` returns `None` (skill dir undetectable from reason string), `_cand_name` is `None`, `None in self._evolution_failed_skills` is always `False`, so Level 4→5 escalation silently never fires — potential infinite loop in FSA.
- [Medium] `.claude/settings.local.json:61,71,81,92,103` — All hook commands hardcoded to `D:/hoonProJect/worktrees/agent-factory`. Breaks on any other machine or if the worktree path changes. Previous `$PWD` was portable.
- [Medium] `.claude/settings.local.json` — `python3` replaced with `python` (Windows-specific). Cross-platform portability lost; inconsistent with rest of codebase convention.
- [Low] `core/fsa_loop.py:266-274` — New logic adds two local variables (`_cand_dir`, `_cand_name`) with leading underscore naming, suggesting temporaries, but they exist only in this branch with no cleanup concern. Minor readability issue.
- [Info] `.claude/settings.local.json:125` — Missing newline at end of file.

**Critical path risk:** The `_cand_name is None` silent no-op in `fsa_loop.py:274` is the most dangerous change — it can cause Level 4 to loop indefinitely if skill name detection fails from the reason string. Add an explicit fallback: escalate to 5 when detection returns `None` to preserve the original safety guarantee.

---

## 2026-04-29 13:40 — `2026-04-14-build-diet` (a27c3bea)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- [High] `.claude/settings.local.json:38` — `Bash(codex exec *)` wildcard allowlist는 임의 codex 명령을 제한 없이 허용. 명시적 허용 패턴으로 좁혀야 함.
- [Medium] `.claude/settings.local.json:62,71,82,93,103` — 절대 경로 하드코딩(`D:/hoonProJect/...`)으로 다른 PC·워크트리에서 hook이 즉시 실패. 원래 `$PWD` 방식이 이식성 우월.
- [Medium] `.claude/settings.local.json:62` — `python3` → `python` 변경. Windows에서 `python`이 Python 2 또는 Microsoft Store 래퍼를 가리킬 수 있어 실행 환경 의존성 생김.
- [Medium] `core/fsa_loop.py:267` — `_detect_failed_skill_dir()` 메서드 호출이 diff에 정의 없음. 메서드 부재 시 `AttributeError`로 FSA 루프 전체 크래시.
- [Low] `core/fsa_loop.py:270` — `_cand_name = None`일 때 `None in self._evolution_failed_skills` 평가는 안전하나, 의도적 fallback인지 주석 없어 의미 모호.
- [Low] `.claude/settings.local.json:EOF` — trailing newline 제거(`\ No newline at end of file`). POSIX 규범 위반, 일부 도구에서 diff 노이즈 발생.
- [Info] `data/skill-usage.jsonl`, `skill-eval-report.json` 등 런타임 생성 데이터 파일이 커밋에 포함 — `.gitignore` 처리 권장.

**핵심 우선순위:** `_detect_failed_skill_dir` 존재 여부 즉시 확인(Medium→Critical 가능), codex exec 와일드카드 범위 축소.

---

## 2026-04-29 13:40 — `2026-04-14-build-diet` (71dabe3f)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- **[High]** `core/fsa_loop.py:273-275` — `_cand_name is None` when `_detect_failed_skill_dir()` returns `None` (e.g., reason string is ambiguous). `None not in self._evolution_failed_skills` → level stays 4 → next cycle re-enters the same path → potential infinite loop at Level 4. Old logic was a safe fallback; new logic removed it without a `None` guard.
- **[High]** `.claude/settings.local.json` — `"Bash(codex exec *)"` wildcard grants execution of any `codex exec` subcommand. Too broad; should enumerate specific allowed subcommands.
- **[Medium]** `.claude/settings.local.json` — All hook `command` values now hardcode `D:/hoonProJect/worktrees/agent-factory`. Breaks on any other machine or worktree path. Prior `$PWD` was portable; the hardcoded path should at minimum be documented as machine-specific and not checked into shared settings.
- **[Low]** `.claude/settings.local.json` — Missing newline at end of file (JSON linters/editors will flag this).
- **[Info]** `core/fsa_loop.py:267-268` — Comment correctly explains the intent of per-skill gating vs. global block; the logic is sound when `_cand_name` is non-`None`. Fix: add `or _cand_name is None` fallback to escalate when skill is undetectable.

**Recommended fix for the High bug:**
```python
if _cand_name is None or _cand_name in self._evolution_failed_skills:
    level = 5
```
This restores safe escalation when skill detection fails.

---

## 2026-04-29 13:41 — `2026-04-14-build-diet` (acae4bb1)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\core\fsa_loop.py

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-29 13:41 — `2026-04-14-build-diet` (edc86894)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\tests\test_phase7_dep_graph_evolve.py

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-29 13:42 — `2026-04-14-build-diet` (7ec39231)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- **High** `.claude/settings.local.json` — Hardcoded absolute Windows paths (`D:/hoonProJect/worktrees/agent-factory`) replace the portable `$PWD`. These paths break on any other machine or if the worktree is relocated.
- **Medium** `.claude/settings.local.json:38` — `Bash(codex exec *)` wildcard is extremely broad; it permits arbitrary `codex exec` commands without restriction. Scope should be narrowed to specific commands or paths.
- **Low** `.claude/settings.local.json` — `python3` → `python`: on Windows this is usually fine, but inconsistent with the rest of the codebase convention; consider keeping one form.
- **Low** `core/fsa_loop.py:588` — `_cand_name` check passes even when `_cand_dir` is set but `_cand_name` is not in `_evolution_failed_skills`; in that case the guard returns `(level, _cand_dir)` at line 590, forwarding a non-None `skill_dir` into `_try_evolve_failed_skill` which will re-detect and may double-process the same skill dir. Verify this is the intended path.
- **Info** `core/fsa_loop.py:574-590` — Refactor is clean overall; extracting `_apply_evolution_guard` and threading `skill_dir` through removes the redundant `_detect_failed_skill_dir` call in `_try_evolve_failed_skill`.
- **Info** `.claude/settings.local.json` — Missing newline at end of file (cosmetic, but some tools warn on this).

**Primary concern is the hardcoded absolute paths in `settings.local.json`** — this file is checked in and will silently fail for anyone else cloning the repo.

---

## 2026-04-29 13:43 — `2026-04-14-build-diet` (df59c73c)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    {
      "severity": "High",
      "location": ".claude/settings.local.json:lines 62-106",
      "finding": "Hardcoded absolute Windows paths (`D:/hoonProJect/worktrees/agent-factory/`) replace portable `$PWD`. Breaks portability across machines or if worktree moves — hooks will silently fail with no error surfaced to the user."
    },
    {
      "severity": "High",
      "location": ".claude/settings.local.json:38",
      "finding": "`\"Bash(codex exec *)\"` in allow list uses a wildcard — effectively permits arbitrary `codex exec` invocations. Should be scoped to a specific subcommand/argument pattern rather than `*`."
    },
    {
      "severity": "Medium",
      "location": "core/fsa_loop.py:_apply_evolution_guard (diff truncated)",
      "finding": "Diff is cut off after the early-return condition (`if level != 4 or not self._evolution_failed_skills:`). Cannot verify the return value on that branch — if it does not return a valid `(int, ...)` tuple, callers unpack incorrectly and raise a `TypeError` at runtime."
    },
    {
      "severity": "Low",
      "location": "core/fsa_loop.py:316",
      "finding": "`_detected_skill_dir` uses a leading-underscore convention (Python idiom for \"intentionally unused\") but is actively passed as a keyword argument. Rename to `detected_skill_dir` for clarity."
    },
    {
      "severity": "Low",
      "location": ".claude/settings.local.json:125",
      "finding": "Missing newline at end of file. Minor but can cause noisy diffs and some tools reject files without EOF newline."
    }
  ]
}
```

---

## 2026-04-29 13:44 — `2026-04-14-build-diet` (90c1d5c5)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```
- [High]   .claude/settings.local.json:37 — `Bash(codex exec *)` wildcard grants unrestricted
           codex execution permission. Any codex subcommand is now auto-approved; scope to
           specific known commands instead.

- [Medium] .claude/settings.local.json:61,71,82,93,103 — Hardcoded absolute Windows paths
           `D:/hoonProJect/worktrees/agent-factory/...` replace the portable `$PWD`. Breaks on
           any other machine or if the worktree is moved. Use an env-var or relative path.

- [Medium] core/fsa_loop.py:582-590 — When `_cand_dir` is None (skill undetectable) but
           `_evolution_failed_skills` is non-empty, level stays 4 and
           `_try_evolve_failed_skill(skill_dir=None)` re-invokes `_detect_failed_skill_dir`
           (double search). Old guard forced level 5 unconditionally in this case. Regression
           risk: if detection is persistently unreliable, the run may loop at level 4 indefinitely
           rather than escalating.

- [Low]    core/fsa_loop.py:574 — Return type `tuple` should be `tuple[int, str | None]` for
           type-checker coverage and call-site clarity.

- [Low]    syncCompyne/memory_store.py — New SQLite store added without visible test coverage
           in the diff. The `ensure_db` / `_get_project_id` flow has no error path for a
           read-only filesystem.

- [Info]   .claude/settings.local.json — Missing newline at EOF (cosmetic, but causes noisy
           git diffs).
```

**Summary:** The `codex exec *` wildcard and hardcoded absolute paths are the two actionable items before merging. The level-4 regression is a logic edge case worth a targeted unit test.

---

## 2026-04-29 13:44 — `2026-04-14-build-diet` (4d1dcd20)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```
- [High]   .claude/settings.local.json — "Bash(codex exec *)" 와일드카드 허용: codex가 실행할 수 있는 모든 명령이 Claude Code 허용 목록에 포함됨. codex exec의 인자 범위를 명시적으로 제한해야 함.

- [Medium] .claude/settings.local.json — 모든 hook command를 하드코딩된 절대 경로(D:/hoonProJect/worktrees/agent-factory/...)로 변경. 다른 PC·경로에서 실행하면 hooks가 무음 실패. 원래 `$PWD` 기반 상대 경로가 더 안전함. settings.local.json이 PC별 설정임을 감안해도 팀 공유 시 문제.

- [Medium] core/fsa_loop.py:571 — _apply_evolution_guard() 구현 본체가 diff에서 잘려 있어 전체 로직 검증 불가. 특히 detected_skill_dir 탐색 실패 시(None 반환) _try_evolve_failed_skill 내부에서 None-guard가 있는지 확인 필요.

- [Low]    core/fsa_loop.py — 반환 타입 힌트가 `tuple` (generic). `tuple[int, str | None]`으로 명시하면 오용 방지.

- [Low]    .claude/settings.local.json — 파일 말미 개행 누락(no newline at EOF). git diff 노이즈 발생.

- [Info]   core/fsa_loop.py:316 — skill_dir를 _apply_evolution_guard에서 함께 반환해 이중 탐색을 제거한 리팩터는 설계상 적절함.
```

**핵심 요약**: `codex exec *` 와일드카드가 가장 위험한 변경. 절대 경로 하드코딩은 이식성 문제. `_apply_evolution_guard` 전체 구현이 보이지 않아 None-safety는 별도 확인 필요.

---

## 2026-04-29 13:45 — `2026-04-14-build-diet` (3fb79b86)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- **High** `.claude/settings.local.json` — `"Bash(codex exec *)"` 와일드카드 허용은 임의 codex 명령 실행을 허용함. 허용 범위가 지나치게 넓음.
- **High** `.claude/settings.local.json` — `$PWD` 상대 경로를 `D:/hoonProJect/worktrees/agent-factory/` 절대 경로로 교체해 머신 이식성 완전 제거. 다른 PC·CI에서 hook 실패함.
- **Medium** `core/fsa_loop.py:574` — 반환 타입 `tuple` 미파라미터화. `tuple[int, str | None]`으로 명시 필요.
- **Medium** `core/fsa_loop.py:582-590` — `_apply_evolution_guard`가 `_cand_name` 미일치 시 `(level, _cand_dir)`를 반환해 Level 4→호출 경로로 `skill_dir`를 전달함. 이전 인라인 로직(`_evolution_failed_skills`만 체크)보다 경로가 추가됐으나 `_cand_dir`가 None이 아닌 경우 하위 `_try_evolve_failed_skill`에서 이중 탐지가 발생할 수 있음 — `_detect_failed_skill_dir` 재호출 분기(line 607)와 충돌 위험.
- **Low** `.claude/settings.local.json` — 파일 말미 개행 제거(EOF newline missing). POSIX 규칙 위반, diff 노이즈 원인.
- **Info** `core/fsa_loop.py:596-598` — `_try_evolve_failed_skill` 시그니처에 `skill_dir: str | None = None` 추가 — `None` 방어 분기(line 606)로 하위 호환성 유지됨. 정상.

---

## 2026-04-29 13:46 — `2026-04-14-build-diet` (3d9f4ae9)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

Code review complete.

---

- **[High]** `.claude/settings.local.json:38` — `"Bash(codex exec *)"` 와일드카드 허용은 모든 인자를 허용하므로 임의 명령 실행 경로가 열림. 구체적인 허용 패턴으로 좁혀야 함.

- **[High]** `.claude/settings.local.json:62,71,81,92,103` — hook `command`에 `D:/hoonProJect/worktrees/agent-factory` 하드코딩. 다른 PC/worktree에서 즉시 broken. `settings.local.json`은 gitignore되어야 하거나 `$PWD` 복원이 맞음. (이 파일이 커밋에 포함된 것 자체가 문제)

- **[Medium]** `core/fsa_loop.py:587` — `_cand_dir`이 `None`일 때 `os.path.basename(None)`은 `AttributeError`. 가드가 `if level != 4 or not self._evolution_failed_skills: return level, None`으로 조기 리턴하므로 이 경로는 `_evolution_failed_skills`가 비어있지 않을 때만 실행되는데, `_detect_failed_skill_dir`이 `None`을 반환할 수 있어 즉시 크래시.

- **[Medium]** `core/fsa_loop.py:321` — `gate_result.skill_path`가 `None`이면 `split(os.sep)[-1]`이 `AttributeError`. `if gate_result.skill_path` 체크가 있지만 전체 삼항식이 `None`을 할당하며 이후 `evolved_skill_name`이 사용될 경우 추적하기 어려운 버그.

- **[Low]** `.claude/settings.local.json` — 파일 끝 개행 제거(`\ No newline at end of file`). JSON 파일 표준 위반, 일부 파서에서 문제 가능.

- **[Info]** `_apply_evolution_guard` 리팩터링 자체는 의도(현재 사이클 스킬이 이미 실패한 경우에만 L5 강제)가 명확하고 `_try_evolve_failed_skill`의 이중 탐색 제거는 개선.

**필수 수정**: `os.path.basename(None)` 크래시 (Medium), `settings.local.json` 하드코딩 제거 (High).

---

## 2026-04-29 13:47 — `2026-04-14-build-diet` (7858bcc5)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

충분한 맥락을 확보했습니다. 리뷰를 작성합니다.

```json
{
  "review": [
    "- [High] .claude/settings.local.json — 훅 명령어에 Windows 절대 경로 하드코딩(`D:/hoonProJect/worktrees/agent-factory`). 다른 PC나 클론 경로에서 즉시 깨짐. `$PWD` 방식으로 되돌리거나 상대 경로 사용 권장.",
    "- [High] .claude/settings.local.json:38 — `Bash(codex exec *)` 와일드카드 허용. `codex exec`에 임의 인수가 통과되므로 악의적 프롬프트가 셸 명령 실행으로 이어질 수 있음. 명시적 서브커맨드로 제한할 것.",
    "- [Medium] core/fsa_loop.py:574–590 — `_apply_evolution_guard`가 `_detect_failed_skill_dir`를 호출하면서, 호출 측(`run` 루프)이 이후 `_try_evolve_failed_skill`에 `skill_dir`를 전달하지 않아도 내부에서 한 번 더 탐색한다. `skill_dir`가 `None`인 채로 `_try_evolve_failed_skill` 진입 시 이중 탐색 가능 — diff:314행 `skill_dir=_detected_skill_dir` 전달로 해소됐는지 확인 필요.",
    "- [Medium] core/fsa_loop.py:587 — `_cand_dir`가 `None`인데 `os.path.basename(None)` 호출 경로 없음. 그러나 `_cand_name` 계산 전에 `_cand_dir` 가드가 `if _cand_dir else None`으로 처리됨 — 정상. 단, `_cand_dir`가 빈 문자열 `\"\"`이면 `basename`이 `\"\"` 반환 → `in self._evolution_failed_skills` 검사 통과 불가. 엣지케이스.",
    "- [Low] .claude/settings.local.json — 파일 끝 개행 제거(`\\ No newline at end of file`). 일부 도구와 diff 출력에서 노이즈 발생. 개행 유지 권장.",
    "- [Info] tests/test_phase7_dep_graph_evolve.py — `_apply_evolution_guard` 신규 로직에 대한 직접 단위 테스트 없음. `level==4 + _evolution_failed_skills` 분기, `level!=4` 분기, `_cand_name not in failed_skills` 분기 각각 커버 필요."
  ],
  "verdict": "High 2건 수정 후 머지 권장"
}
```

**요약:** 절대 경로 하드코딩(이식성 파괴)과 `codex exec *` 와일드카드 허용(보안)이 High 이슈입니다. `_apply_evolution_guard` 리팩터링 자체는 논리적으로 올바르나, 신규 분기에 대한 단위 테스트가 없습니다.

---

## 2026-04-29 13:48 — `2026-04-14-build-diet` (21c3cc59)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

Code review findings:

- **[High]** `.claude/settings.local.json:58–103` — Hook commands hardcoded to absolute Windows path `D:/hoonProJect/worktrees/agent-factory/`. The original `$PWD`-relative form worked cross-machine; this breaks on any other dev box or CI. Should use a portable path or env var.

- **[Medium]** `.claude/settings.local.json:38` — `"Bash(codex exec *)"` wildcard added to allow list. This permits any `codex exec` subcommand without restriction. If `codex exec` can spawn shell commands, this is a broad permission grant with no audit trail.

- **[Low]** `core/fsa_loop.py:587` — `os.path.basename(_cand_dir) if _cand_dir else None` — `_cand_dir` can legitimately be an empty string `""` (falsy), which would silently return `None` and skip the guard even when a dir was detected as empty string. Use `if _cand_dir is not None` for the guard condition.

- **[Low]** `core/fsa_loop.py:574` — Return type annotation is `tuple` (bare). Should be `tuple[int, str | None]` for clarity and static analysis.

- **[Info]** `.claude/settings.local.json` — Missing trailing newline (`\ No newline at end of file`). Minor, but inconsistent with file conventions.

- **[Info]** `core/fsa_loop.py:584–590` — Refactor is correct: guard now fires only when the *currently detected* skill is in `_evolution_failed_skills`, fixing the prior over-eager Level 4→5 promotion on any failure. Logic is sound.

---

## 2026-04-29 13:48 — `2026-04-14-build-diet` (779ee3a9)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- **[High] `.claude/settings.local.json`:35** — `"Bash(codex exec *)"` 와일드카드 허용은 codex를 통한 임의 명령 실행 면을 열어준다. 최소 권한 원칙 위반 — 실제 필요한 패턴으로 제한해야 한다.

- **[Medium] `.claude/settings.local.json`:62,71,81,91,101** — 훅 커맨드에 `D:/hoonProJect/worktrees/agent-factory` 절대 경로 하드코딩. `settings.local.json`이라 기계 종속성은 어느 정도 허용되나, `python3`를 `python`으로 변경한 것이 다른 환경(WSL, CI)에서 깨질 수 있다.

- **[Medium] `core/fsa_loop.py`:574** — `_apply_evolution_guard` 반환 타입이 `tuple`로 비제네릭. `tuple[int, str | None]`으로 명시해야 `_try_evolve_failed_skill(skill_dir=...)` 호출부의 타입 안전성이 보장된다.

- **[Low] `core/fsa_loop.py`:587** — `os.path.basename(_cand_dir)` 에서 `_cand_dir`이 빈 문자열 `""`일 경우 `basename("")` → `""` → `_cand_name`이 falsy가 되어 정상 처리되나, 빈 문자열과 `None`을 구분하지 않아 의미가 불명확하다. `_detect_failed_skill_dir`가 실패 시 `None`을 명시적으로 반환하는지 확인 필요.

- **[Low] `.claude/settings.local.json`:EOF** — 파일 끝 개행 없음(`\ No newline at end of file`). 일부 도구/Git diff에서 노이즈 발생.

- **[Info] `core/fsa_loop.py`:314** — `skill_dir=_detected_skill_dir` 전달로 이중 `_detect_failed_skill_dir` 호출을 제거한 점은 올바른 개선.

---

## 2026-04-29 13:49 — `2026-04-14-build-diet` (597b0b8e)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:38 — `\"Bash(codex exec *)\"` is a broad wildcard allowlist entry. Any `codex exec <anything>` runs without a prompt. Narrow to specific subcommands actually needed.",
    "- [High] .claude/settings.local.json:62~107 — All hook commands now embed hardcoded absolute Windows paths (`D:/hoonProJect/worktrees/agent-factory`). The original `$PWD` was portable; these break on any other machine or directory move. Store the path in an env var instead.",
    "- [Medium] core/fsa_loop.py:572 — `_apply_evolution_guard` return type is untyped `tuple`. Should be `tuple[int, str | None]` for clarity and static-analysis correctness.",
    "- [Medium] core/fsa_loop.py (truncated) — Diff is cut off after `if level != 4 or not self._evolution_failed_skills:`. Cannot verify the else-branch or that all code paths return a 2-tuple. Missing-return risk.",
    "- [Medium] core/fsa_loop.py:316 — `skill_dir=_detected_skill_dir` passes `None` when level ≠ 4. Confirm `_try_evolve_failed_skill` handles `None` gracefully without silent no-ops or AttributeErrors.",
    "- [Low] .claude/settings.local.json:125 — Trailing newline removed (`No newline at end of file`). Minor but causes noisy diffs on future edits; restore it.",
    "- [Info] 14 of 18 changed files are data/log/cursor files (skill-usage.jsonl, session_cursor.json, eval reports, syncCompyne logs). These inflate the diff but carry no logic risk."
  ]
}
```

---

## 2026-04-29 13:50 — `2026-04-14-build-diet` (d30cfa81)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- **[High]** `.claude/settings.local.json:35` — `"Bash(codex exec *)"` wildcard in allowlist permits arbitrary argument execution via codex. Scope to specific subcommands instead.
- **[High]** `.claude/settings.local.json:62,70,81,92,103` — Hardcoded absolute path `D:/hoonProJect/worktrees/agent-factory` replaces portable `$PWD`. Breaks on any other machine or if the worktree moves.
- **[Medium]** `core/fsa_loop.py:267` — `result` is passed as a plain `dict` to `_apply_evolution_guard`; if the execution pipeline ever returns `None` at that point, `result.get("reason", "")` raises `AttributeError`. No null guard exists.
- **[Medium]** `core/fsa_loop.py:582-590` — Behavior change: old code escalated to Level 5 whenever **any** blocked skill existed; new code only escalates if `_detect_failed_skill_dir` matches the current cycle's skill. If detection returns `None` (name not found in reasoning text), a legitimately blocked skill silently stays at Level 4 instead of being force-escalated.
- **[Low]** `core/fsa_loop.py:598` — `skill_dir: str | None = None` uses a union type literal requiring Python 3.10+. Other signatures in this file should be verified for consistency.
- **[Low]** `.claude/settings.local.json` — Missing trailing newline (noted in diff). Minor but can cause noisy git diffs.
- **[Info]** Hook commands changed from `python3` to `python`. On Windows this is usually correct, but worth confirming `python` resolves to the intended interpreter in all shell contexts.

---

## 2026-04-29 13:51 — `2026-04-14-build-diet` (12f56ef6)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- **[High]** `.claude/settings.local.json:64,72,83,93,103` — `python3 ./ + $PWD` → `python D:/hoonProJect/...` 절대경로 하드코딩. 다른 PC/경로에서 hook 전체 무력화됨. `$PWD` 동적 변수가 Windows에서 동작하지 않는다면 환경변수 `%CD%` 또는 별도 launcher 스크립트 사용 권장.
- **[Medium]** `.claude/settings.local.json:38` — `"Bash(codex exec *)"` 와일드카드 허용 추가. `codex exec` 인자 제한 없이 자동 승인되므로 임의 명령 실행 노출 범위가 넓음. 필요한 서브커맨드만 명시적으로 열거할 것.
- **[Medium]** 커밋 메시지(`feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback`)와 실제 변경 범위 불일치. diff에 SKILL.md fallback 로직이 없고 hook 경로 수정 + FSA guard 리팩터가 주 내용. 내용과 다른 커밋 메시지는 bisect/추적 시 혼란 유발.
- **[Low]** `core/fsa_loop.py:320-323` — `gate_result is not None and gate_result.passed` 분기 내에서 `evolved_skill_name`을 설정하지만, `gate_result.passed`가 False인 GateResult가 반환될 수 있는지 타입 계약이 명확하지 않음(`_try_evolve_failed_skill` docstring: "PUBLISHED → GateResult(passed=True), 그 외 → None"이라면 문제없으나 방어적 assert 또는 타입 주석 추가 권장).
- **[Low]** `.claude/settings.local.json` 파일 끝 개행 누락 (`\ No newline at end of file`). JSON 파서 자체는 허용하나 git diff 노이즈 발생 + 일부 도구 경고.
- **[Info]** `_apply_evolution_guard` 추출: 기존 인라인 3줄보다 정밀도 향상 (현재 사이클 탐지 스킬과 차단 목록 교차 확인). 로직 자체는 정상.
- **[Info]** `skill_dir` 파라미터를 `_try_evolve_failed_skill`에 전달해 이중 탐색 방지한 것은 올바른 개선.

---

## 2026-04-29 13:51 — `2026-04-14-build-diet` (85a7d520)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- [High] `.claude/settings.local.json:38` — `"Bash(codex exec *)"` 와일드카드 허용은 임의 `codex exec` 명령 실행을 무제한 허가함. 구체적인 패턴으로 범위 제한 필요.
- [High] `.claude/settings.local.json:62,72,82,92,102` — `$PWD` 대신 `D:/hoonProJect/worktrees/agent-factory` 하드코딩. 다른 머신/경로에서 hook 전체 무력화됨. `settings.local.json`이므로 본인 전용이라도, worktree 이동 시 즉시 고장.
- [Medium] `core/fsa_loop.py:571` — `_apply_evolution_guard` 반환 타입이 `tuple`만 선언됨. `tuple[int, str | None]`로 명시해야 정적 분석 가능.
- [Medium] `core/fsa_loop.py` — diff가 중간에 잘려 `_apply_evolution_guard` 본문 전체 확인 불가. 특히 `detected_skill_dir` 탐색 로직과 `_evolution_failed_skills` 변경 여부를 검증할 수 없음.
- [Low] `.claude/settings.local.json` — 파일 끝 개행 제거(`\ No newline at end of file`). JSON 도구 호환성 문제 가능성.
- [Info] `core/fsa_loop.py:264` — 인라인 3줄 가드를 `_apply_evolution_guard()`로 분리한 것은 테스트 가능성 측면에서 긍정적.

**요약**: `codex exec *` 와일드카드 허용(보안)과 절대 경로 하드코딩(이식성)이 주요 문제. `fsa_loop.py` 리팩터링 방향은 올바르나 diff 잘림으로 전체 검증 불가.

---

## 2026-04-29 13:52 — `2026-04-14-build-diet` (6a7d8ff9)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```
- [High]   .claude/settings.local.json:37 — "Bash(codex exec *)" wildcard pre-approves any
           codex exec invocation without prompting. Unconstrained code execution bypass.

- [Medium] .claude/settings.local.json:61,71,82,92,103 — All hook commands hardcoded to
           absolute path "D:/hoonProJect/worktrees/agent-factory/". Breaks on any other
           machine or repo location. The replaced $PWD was portable; this is a regression.

- [Medium] core/fsa_loop.py:589 — When level is forced to 5, _apply_evolution_guard returns
           (5, _cand_dir). The caller's elif level==5 block calls _decompose_and_execute,
           which never consumes _detected_skill_dir. The skill is not evolved, not logged,
           not added to _evolution_failed_skills — silent discard with no signal to the caller.

- [Low]    core/fsa_loop.py:319-323 — evolved_skill_name assigned only when gate_result is
           non-None AND passed. If it was set by a prior cycle and gate_result is None this
           iteration, stale value is silently carried forward. Initialize to None before the
           elif level==4 block.

- [Low]    tests/test_phase7_dep_graph_evolve.py — No test for _apply_evolution_guard (the
           primary logic change in this PR). The refactor from inline to method is untested.

- [Info]   .claude/settings.local.json: missing newline at end of file (trailing whitespace
           diff noise in future reviews).
```

**Summary**: Two issues warrant attention before merge — the `codex exec *` wildcard (security) and the hardcoded absolute paths (portability regression). The Level 5 skill_dir silent discard is a logic clarity issue but not a crash risk. Add a `_apply_evolution_guard` unit test and initialize `evolved_skill_name = None` before the level-4 branch.

---

## 2026-04-29 13:53 — `2026-04-14-build-diet` (a711e40a)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- **[Medium] `.claude/settings.local.json`:35** — `"Bash(codex exec *)"` 와일드카드 허용은 임의 명령 실행 경로가 될 수 있음. `codex exec` 가 수락하는 인수 범위를 명시적으로 제한할 것을 권장.

- **[Medium] `.claude/settings.local.json`:62,72,82,92,103** — `python3`→`python` + `$PWD`→하드코딩 절대 경로 변경. 다른 머신/워크트리에서 클론하면 hooks가 즉시 깨짐. `settings.local.json` 이므로 의도적일 수 있으나, `.gitignore` 처리가 없으면 타인 환경에서 오동작.

- **[Low] `core/fsa_loop.py`:587** — `_cand_dir`이 `None`일 때 `os.path.basename(None)` 호출이 발생하지 않도록 `_cand_dir` 분기가 먼저 체크됨(정상). 단, `_cand_dir`이 빈 문자열 `""` 인 경우 `basename("")` → `""` 이고 `_cand_name`이 falsy로 처리되므로 Level 5 에스컬레이션이 누락될 수 있음. `_detect_failed_skill_dir`의 반환 계약 확인 필요.

- **[Info] `core/fsa_loop.py`:574-590** — 인라인 3줄 → `_apply_evolution_guard()` 추출은 적절. `skill_dir` 반환을 `_try_evolve_failed_skill`에 전달해 이중 탐색 제거한 점 긍정적.

- **[Info] `.claude/settings.local.json`:125** — EOF 개행 누락. 사소하지만 diff 노이즈 원인.

---

## 2026-04-29 13:53 — `2026-04-14-build-diet` (bed9147e)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:38 — `Bash(codex exec *)` 와일드카드 허용은 임의 codex 명령 실행을 전부 승인함. 최소 권한 원칙 위반; 실제 필요한 하위 명령만 명시적으로 열거해야 함.",
    "- [Medium] .claude/settings.local.json:62,72,82,92,102 — 절대 경로 `D:/hoonProJect/worktrees/agent-factory` 하드코딩. 다른 PC/경로에서 hook 전체 무력화. `$PWD` 기반 동적 경로 또는 env var 치환 필요.",
    "- [Medium] core/fsa_loop.py:316 — `skill_dir=_detected_skill_dir` 전달 시 `_detected_skill_dir`가 `None`일 수 있음. `_try_evolve_failed_skill` 시그니처 및 내부에서 `None` 처리 여부 확인 필요 (diff 잘려서 미확인).",
    "- [Low] core/fsa_loop.py:572 — `_apply_evolution_guard` 반환 타입이 `tuple`로만 선언됨. `tuple[int, str | None]` 명시 권장 (Python 3.9+).",
    "- [Info] .claude/settings.local.json — `python3` → `python` 변경은 Windows 호환성 수정으로 정상. `name` 필드 추가도 가독성 개선으로 적절."
  ],
  "summary": "주요 위험 2건: codex exec 와일드카드 허용(보안) + 절대 경로 하드코딩(이식성). `_detected_skill_dir=None` 전파 경로 확인 후 머지 권장."
}
```

---

## 2026-04-29 13:54 — `2026-04-14-build-diet` (176cbdcd)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "verdict": "CONDITIONAL_PASS",
  "summary": "핵심 로직(Level 4→5 가드 정밀화)은 올바른 버그픽스. settings.local.json의 광범위 허용과 하드코딩 경로가 주요 지적 사항.",
  "findings": [
    {
      "severity": "High",
      "location": ".claude/settings.local.json",
      "finding": "\"Bash(codex exec *)\" 와일드카드 허용 — codex exec 서브커맨드 전체를 무제한 허용. 인가된 codex 명령 패턴으로 범위를 좁혀야 한다."
    },
    {
      "severity": "Medium",
      "location": ".claude/settings.local.json:64,72,81,90,100",
      "finding": "hook command가 D:/hoonProJect/worktrees/agent-factory 절대 경로로 하드코딩 — 다른 PC 또는 clone 경로 변경 시 전 hook이 무음 실패. settings.local.json은 .gitignore 대상이어야 하며, 템플릿 파일로 관리 권장."
    },
    {
      "severity": "Low",
      "location": "core/fsa_loop.py:582-590",
      "finding": "_apply_evolution_guard: _evolution_failed_skills 체크 결과와 무관하게 _detect_failed_skill_dir를 항상 호출. 조건 순서를 바꿔 failed_skills 포함 시에만 탐색하면 불필요한 비용 절감 가능."
    },
    {
      "severity": "Low",
      "location": "core/fsa_loop.py:574",
      "finding": "반환 타입 힌트가 tuple 단순형 — tuple[int, str | None]으로 명시하면 호출 지점에서 언패킹 타입 추론 개선."
    },
    {
      "severity": "Info",
      "location": "core/fsa_loop.py:265-267",
      "finding": "Level 4→5 강제 에스컬레이션 로직 정밀화(전체 failed_skills → 현재 사이클 탐지 스킬 한정) 방향은 올바른 버그픽스. skill_dir 전달로 이중 탐색 제거도 적절."
    },
    {
      "severity": "Info",
      "location": ".claude/settings.local.json (마지막 줄)",
      "finding": "파일 말미 개행 없음(no newline at EOF) — diff 노이즈 유발."
    }
  ],
  "block_items": ["High — codex exec * 와일드카드 허용 범위 축소 필요"],
  "pass_conditions": "High 항목(codex exec 범위 제한) 수정 후 재검토"
}
```

---

## 2026-04-29 13:55 — `2026-04-14-build-diet` (840a8857)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

- **[High]** `.claude/settings.local.json:62,71,82,93,104` — All hook commands replaced `$PWD` with hardcoded absolute Windows paths (`D:/hoonProJect/worktrees/agent-factory`). Breaks cross-machine and cross-OS portability; this file is tracked in git so it will break other contributors/environments.

- **[Medium]** `.claude/settings.local.json:38` — `"Bash(codex exec *)"` wildcard added to the allow list. This permits any `codex exec` subcommand without restriction; should be scoped to the minimum required invocation pattern.

- **[Medium]** `core/fsa_loop.py:571` — `_apply_evolution_guard` diff is truncated at the `if level != 4 or not self._evolution_failed_skills:` line — the early-return path and full tuple construction are not visible. Cannot verify the guard logic is complete or that the returned `_detected_skill_dir` is always a valid value (not `None`) before being passed downstream.

- **[Low]** `core/fsa_loop.py:316` — `skill_dir=_detected_skill_dir` is a new keyword argument passed to the gate call. If the callee's signature was not updated to accept `skill_dir`, this will raise a `TypeError` at runtime on every Level 4 escalation cycle.

- **[Info]** `.claude/settings.local.json` — Trailing newline removed (last line). Minor but creates noisy diffs.

- **[Info]** — 13 of 18 changed files (`syncCompyne/*`, `data/*`, `projects/*`) are data/config files unrelated to the commit title `feat(T1-skill-md-fallback)`. Commit scope is much wider than the feature it describes; consider splitting.

---

## 2026-04-29 13:56 — `2026-04-14-build-diet` (89829ac5)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "line": null,
      "finding": "Hook commands hardcoded to absolute Windows path `D:/hoonProJect/worktrees/agent-factory`. This breaks on any other machine or if the worktree is moved. Previous `$PWD`-relative form was portable; this regression should be reverted or replaced with a portable alternative."
    },
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "line": 38,
      "finding": "`Bash(codex exec *)` wildcard added to `allow` list. Overly broad — allows arbitrary subcommands via `codex exec`. Should be scoped to specific known commands."
    },
    {
      "severity": "Medium",
      "file": "core/fsa_loop.py",
      "line": 576,
      "finding": "`_apply_evolution_guard` return type is annotated as `tuple` without generic params (`tuple[int, str | None]`). Weakens static analysis and IDE support."
    },
    {
      "severity": "Medium",
      "file": "core/fsa_loop.py",
      "line": 587,
      "finding": "If `_cand_dir` is an empty string (falsy but not None), `os.path.basename` returns `''`, so `_cand_name` is falsy and guard silently skips. Should check `if _cand_dir` explicitly before calling `basename`, which is already done — but `_detect_failed_skill_dir` returning `''` vs `None` is not guarded upstream."
    },
    {
      "severity": "Low",
      "file": "core/fsa_loop.py",
      "line": 316,
      "finding": "`skill_dir=_detected_skill_dir` is now passed to `_try_evolve_failed_skill`, which avoids double-detection — good. But the variable name `_detected_skill_dir` with a leading underscore at call-site (not inside a method) is unconventional; rename to `detected_skill_dir` for clarity."
    },
    {
      "severity": "Low",
      "file": ".claude/settings.local.json",
      "line": 125,
      "finding": "Missing newline at end of file (trailing `\\n` removed). Minor but can cause noisy diffs."
    },
    {
      "severity": "Info",
      "file": "core/fsa_loop.py",
      "line": 574,
      "finding": "Refactoring the inline Level 4→5 guard into `_apply_evolution_guard` is the right direction — logic is now testable in isolation and the double-detection elimination via returned `skill_dir` is a clean improvement."
    }
  ]
}
```

---

## 2026-04-29 13:56 — `2026-04-14-build-diet` (a7fc8f67)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:59,70,81,92,103 — 모든 hook command가 하드코딩된 절대 경로 (D:/hoonProJect/worktrees/agent-factory/)로 교체됨. 다른 머신/경로에서 즉시 실패. settings.local.json이 공유될 경우 이식성 0. 기존 $PWD 방식이 더 안전함.",
    "- [High] .claude/settings.local.json:38 — 'Bash(codex exec *)' 와일드카드 허용 추가. codex exec는 임의 명령 실행 가능 — 허용 범위가 너무 광범위하여 권한 상승 경로가 됨.",
    "- [Medium] core/fsa_loop.py:572+ — _apply_evolution_guard() diff가 중간에 잘려 early-return 분기의 반환값을 확인 불가. level != 4 또는 _evolution_failed_skills 미존재 시 (level, None) 반환인지 검증 필요.",
    "- [Medium] core/fsa_loop.py:571 — 반환 타입이 tuple로만 선언됨 (tuple[int, str | None] 미지정). _detected_skill_dir를 None-check 없이 skill_dir=로 전달하면 _try_evolve_failed_skill 내부에서 NoneType 오류 잠재.",
    "- [Low] .claude/settings.local.json:125 — 파일 끝 개행 누락 (No newline at end of file). JSON 파일 관례 위반."
  ]
}
```

---

## 2026-04-29 13:57 — `2026-04-14-build-diet` (da3c48d0)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    {
      "severity": "High",
      "file": "core/fsa_loop.py",
      "line": "~585",
      "finding": "_apply_evolution_guard가 os.path.basename(_cand_dir)로 스킬명을 추출하는데, _cand_dir가 trailing slash로 끝나면 basename이 빈 문자열을 반환하여 매칭 실패. os.path.basename(os.path.normpath(_cand_dir)) 필요."
    },
    {
      "severity": "Medium",
      "file": "core/fsa_loop.py",
      "line": "~316",
      "finding": "_detected_skill_dir가 None일 때 skill_dir=None이 _try_evolve_failed_skill에 전달되면 내부에서 재탐색을 수행하므로 최적화 효과 없음. None 전달 경로가 의도적인지 명시 필요."
    },
    {
      "severity": "Medium",
      "file": ".claude/settings.local.json",
      "line": "N/A",
      "finding": "permissions 블록 전체(allow/deny 목록) 제거됨. 기존 deny 목록에 있던 rm/del/git-reset--hard 등 파괴적 명령 차단이 사라짐. 의도적 제거라면 다른 위치에 동일 deny 규칙이 있는지 확인 필요."
    },
    {
      "severity": "Medium",
      "file": ".claude/settings.local.json",
      "line": "N/A",
      "finding": "hook command가 절대 경로 D:/hoonProJect/worktrees/agent-factory로 하드코딩됨. 다른 머신 또는 경로 이동 시 즉시 브레이크. python3 → python 변경도 포함돼 Unix 계열에서 python 미설치 시 실패 가능성."
    },
    {
      "severity": "Low",
      "file": "tests/test_phase7_dep_graph_evolve.py",
      "line": "~470",
      "finding": "import from unittest.mock가 테스트 메서드 내부에 위치. 모듈 상단 임포트로 이동 권장(기존 패턴과 불일치)."
    },
    {
      "severity": "Low",
      "file": "syncCompyne/memory_store.py",
      "line": "N/A",
      "finding": "diff가 순수 CRLF→LF 또는 인코딩 변환으로 보임(내용 변경 없음). 불필요한 whitespace diff는 git blame 추적을 오염시킴."
    },
    {
      "severity": "Info",
      "file": "core/fsa_loop.py",
      "line": "~571",
      "finding": "커밋 메시지는 'SKILL.md description fallback'이나 diff에서 SKILL.md 읽기 로직이 보이지 않음. 해당 기능이 다른 파일(skill_*.py 등)에 있다면 변경 파일 목록에서 누락된 것."
    }
  ]
}
```

---

## 2026-04-29 13:58 — `2026-04-14-build-diet` (c1757c92)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    {
      "severity": "Medium",
      "file": "core/fsa_loop.py",
      "line": null,
      "finding": "_apply_evolution_guard()의 반환 타입이 `tuple`로만 선언되어 있어 tuple[int, str | None]이 아닌 타입으로 역추적이 어려움. 타입 힌트를 tuple[int, str | None]으로 명시 권장."
    },
    {
      "severity": "Low",
      "file": "core/fsa_loop.py",
      "line": null,
      "finding": "_apply_evolution_guard()에서 analysis 파라미터의 타입 힌트가 누락(Any). analysis.evaluator_reasoning 접근이 런타임까지 검증되지 않음."
    },
    {
      "severity": "Low",
      "file": "core/fsa_loop.py",
      "line": null,
      "finding": "result.get('reason', '')에서 result['reason']이 None인 경우 빈 문자열 대체가 되어 _detect_failed_skill_dir에 None 대신 '' 전달 — 실제 의도와 부합하는지 확인 필요."
    },
    {
      "severity": "Low",
      "file": ".claude/settings.local.json",
      "line": null,
      "finding": "permissions 블록(allow/deny 목록) 전체 제거로 이전에 허용됐던 git, python, pytest 명령에 대한 자동 승인이 사라짐. 로컬 전용 파일이지만 재설정 없이 커밋되면 다른 환경에서 권한 프롬프트 폭증 가능."
    },
    {
      "severity": "Low",
      "file": ".claude/settings.local.json",
      "line": null,
      "finding": "hook command에 절대 경로(D:/hoonProJect/worktrees/agent-factory)가 하드코딩됨. 다른 머신/경로에서 클론 시 hook이 무음 실패함. $PWD 또는 상대 경로 사용이 이식성 면에서 더 안전."
    },
    {
      "severity": "Info",
      "file": "tests/test_phase7_dep_graph_evolve.py",
      "line": null,
      "finding": "신규 테스트 2개가 happy path(같은 스킬→L5)와 guard path(다른 스킬→L4)를 모두 검증함. 커버리지 양호. level != 4 분기(guard 조기 반환)에 대한 테스트는 없으나 자명한 경우라 생략 가능."
    },
    {
      "severity": "Info",
      "file": "syncCompyne/*.py",
      "line": null,
      "finding": "memory_store.py, project_log_cli.py, workspace_context_cli.py diff가 CRLF→LF 줄끝 변환만 발생(논리 변경 없음). 실질적 코드 변경 없음."
    }
  ],
  "summary": "핵심 변경(fsa_loop.py _apply_evolution_guard 분리)은 올바른 방향이며 버그 위험 낮음. 주요 지적: 타입 힌트 미완성(Medium), settings.local.json 하드코딩 절대경로 및 permissions 전체 제거(Low 2건)."
}
```

---

## 2026-04-29 13:59 — `2026-04-14-build-diet` (027d5f39)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "finding": "permissions.deny 블록 전체 제거 — rm/del/git reset --hard/git checkout -- 등 파괴적 명령 차단이 사라짐. CLAUDE.md 'Destructive Action Guard' 정책 위반."
    },
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "finding": "Hook 경로가 절대 경로(D:/hoonProJect/worktrees/agent-factory)로 하드코딩됨. 기존 $PWD 방식이 이식성 있었는데 회귀. 다른 PC/경로에서 모든 hook이 즉시 실패."
    },
    {
      "severity": "Medium",
      "file": "skills/registry.yaml:8-9",
      "finding": "abc 스킬의 meta_path/path가 임시 테스트 디렉터리(tests/_tmp/af-test-ba801729/)를 가리킴. 테스트 아티팩트가 registry에 커밋된 것 — 다음 테스트 실행 시 경로 불일치."
    },
    {
      "severity": "Medium",
      "file": "skills/registry.yaml, skills/new_skill/skill-promotion.json",
      "finding": "절대 Windows 경로(D:\\hoonProJect\\...)가 레지스트리에 하드코딩됨. 프로젝트 이동 또는 다른 머신에서 동작 불가. 상대 경로 또는 런타임 해석 필요."
    },
    {
      "severity": "Low",
      "file": "core/fsa_loop.py:582-590",
      "finding": "_apply_evolution_guard에서 os.path.basename()으로 스킬명 추출. _detect_failed_skill_dir가 후행 슬래시 포함 경로를 반환하면 basename이 빈 문자열이 돼 조건 미충족 — 가드가 침묵하며 실패."
    },
    {
      "severity": "Info",
      "file": "core/fsa_loop.py:574-648",
      "finding": "_apply_evolution_guard 추출 및 skill_dir 전달로 _detect_failed_skill_dir 이중 호출 제거 — 올바른 리팩터링. 테스트 2건(per-skill guard)도 정확히 신규 동작 검증함."
    },
    {
      "severity": "Info",
      "file": "syncCompyne/memory_store.py",
      "finding": "파일 전체 교체이지만 코드 변경 없음(CRLF→LF 줄끝 정규화로 보임). 기능 영향 없음."
    }
  ],
  "summary": "핵심 버그픽스(evolution guard per-skill 정밀화)는 올바름. 그러나 settings.local.json에서 deny 퍼미션 삭제와 hook 절대경로 하드코딩이 High 수준 회귀이며, registry.yaml의 테스트 임시경로 커밋은 Medium 수준 오염임."
}
```

---

## 2026-04-29 14:00 — `2026-04-14-build-diet` (683507da)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```
- [High] .claude/settings.local.json — 하드코딩된 절대 경로(`D:/hoonProJect/worktrees/agent-factory/`)가 모든 hook command에 박혀 있음. 다른 머신/경로에서 클론하면 hook이 즉시 무너짐. `$PWD`/상대경로 또는 별도 env var로 교체 필요.

- [High] .claude/settings.local.json — `permissions.allow` 블록이 완전히 제거됨. 이전엔 허용 목록이 있었으나 지금은 `deny`만 남아 있음. 의도적인 변경이면 OK, 하지만 화이트리스트 제거는 허용 범위 전체를 묵시적 기본값에 맡기는 것이므로 검토 필요.

- [High] .claude/settings.local.json — JSON 구조 누락: 마지막 `"permissions"` 블록이 닫히지 않은 채(`}` 하나 부족) 보임. Bash diff grep 결과에서 `"permissions": { "deny": [ ... ] }` 다음 최종 `}` 누락 — 파일이 유효한 JSON인지 `python -m json.tool` 로 검증 필요.

- [Medium] core/fsa_loop.py `_apply_evolution_guard()` — `_detect_failed_skill_dir()`가 `None`을 반환하면 `os.path.basename(None)`이 아닌 조건부로 처리하고 있어 정상이지만, 반환 타입 어노테이션이 `tuple`(naked)이라 `tuple[int, str | None]`으로 명시하지 않으면 mypy/pyright 경고 발생.

- [Medium] core/skill_metadata_adapter.py `_fill_missing_description()` — `when_to_use`가 비어있을 때 `md_desc`(body 첫 문단)를 그대로 채우는데, 이 값은 `description`과 동일한 텍스트가 됨. 의미상 중복이 발생하며 `when_to_use` 시맨틱이 퇴화됨.

- [Low] skills/registry.yaml — `meta_path`/`path` 필드에 로컬 테스트 임시 경로(`tests/_tmp/af-test-ba801729/`)가 커밋됨. 이 값은 실행 환경에 종속된 ephemeral 경로이므로 registry에 보존되면 안 됨.

- [Low] syncCompyne/*.py — CRLF→LF 경고가 3개 파일에서 발생. `.gitattributes`에 `* text=auto` 또는 `*.py text eol=lf`를 추가해 라인엔딩을 통일할 것.

- [Info] core/fsa_loop.py — `_detected_skill_dir`를 `_apply_evolution_guard`에서 반환해 `_try_evolve_failed_skill`에 재활용하는 구조는 이중 탐색을 올바르게 방지함. 설계 의도 명확.
```

---

## 2026-04-29 14:01 — `2026-04-14-build-diet` (3266a44b)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "verdict": "APPROVE_WITH_NOTES",
  "findings": [
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "line": null,
      "finding": "permissions.allow/deny 블록 전체 삭제됨. 이전에 명시적으로 허용된 Bash 명령(git, python, pytest 등)과 deny 가드(rm, del, git reset --hard 등)가 모두 제거되어 권한 경계가 undefined 상태가 됨. 의도적 정리인지, 글로벌 settings.json으로 이동됐는지 확인 필요."
    },
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "line": null,
      "finding": "hook command가 $PWD 변수 → 하드코딩 경로(D:/hoonProJect/worktrees/agent-factory)로 변경. 다른 머신/경로에서 클론 시 hook이 무조건 실패함. python3 → python 변경도 Windows 전용 가정을 강화함."
    },
    {
      "severity": "Medium",
      "file": "core/fsa_loop.py",
      "line": 583,
      "finding": "_apply_evolution_guard가 tuple을 반환하지만 반환 타입 힌트가 tuple만 표기되어 있음(tuple[int, str | None] 미명시). 호출부에서 언패킹 실수 위험."
    },
    {
      "severity": "Low",
      "file": "core/fsa_loop.py",
      "line": 591,
      "finding": "_cand_dir가 None이면 os.path.basename(None)에서 TypeError 발생. 현재 코드에서 if _cand_dir 가드로 막혀 있으나, os.path.basename 호출이 _cand_dir is not None 조건 내부에 있어 안전하나, 가독성을 위해 early-return 패턴 권장."
    },
    {
      "severity": "Low",
      "file": "syncCompyne/memory_store.py",
      "line": null,
      "finding": "diff가 CRLF→LF 교체로 인한 전체 파일 재작성으로 표시됨. 실제 로직 변경 없음. 줄 끝 설정(.gitattributes)으로 재발 방지 권장."
    },
    {
      "severity": "Info",
      "file": "tests/test_phase7_dep_graph_evolve.py",
      "line": 467,
      "finding": "신규 테스트 2개(_per_skill_guard_*)가 _apply_evolution_guard의 핵심 분기를 정확히 커버함. 정상."
    }
  ]
}
```

---

## 2026-04-29 14:02 — `2026-04-14-build-diet` (1610db1e)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    {
      "severity": "Critical",
      "file": ".claude/settings.local.json",
      "finding": "전체 deny 목록 제거 — rm, del, git reset --hard, git restore 등 파괴적 명령 차단이 사라짐. 교차검증 에이전트가 제한 없이 파괴적 shell 명령 실행 가능."
    },
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "finding": "Hook 명령이 하드코딩된 절대 경로(D:/hoonProJect/worktrees/agent-factory/...)로 고정됨. 다른 머신/경로에서 checkout 시 모든 hook이 즉시 실패. $PWD 변수 또는 상대 경로로 복원 필요."
    },
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "finding": "allow 목록 전체 제거 — python, git, pytest 등 반복 실행 명령에 대해 매번 사용자 승인 프롬프트가 발생해 자동화 파이프라인이 차단됨."
    },
    {
      "severity": "Medium",
      "file": "skills/registry.yaml",
      "finding": "abc 스킬의 meta_path/path가 임시 테스트 디렉터리(tests/_tmp/af-test-ba801729/)를 가리킴. 테스트 아티팩트가 레지스트리에 커밋됨 — 테스트 재실행 시 경로 소멸."
    },
    {
      "severity": "Medium",
      "file": "skills/registry.yaml",
      "finding": "new_skill의 last_eval_report 경로가 하드코딩된 Windows 절대 경로. 머신 이식성 없음. 상대 경로(skills/new_skill/skill-eval-report.json)가 이미 다른 필드에 사용되는데 일관성 없음."
    },
    {
      "severity": "Medium",
      "file": "core/fsa_loop.py:574",
      "finding": "_apply_evolution_guard 반환 타입이 bare `tuple`로 선언됨. tuple[int, str | None]으로 좁혀야 하위 호출부에서 타입 추론이 정확해짐."
    },
    {
      "severity": "Low",
      "file": "tests/test_phase7_dep_graph_evolve.py:470,483",
      "finding": "`from unittest.mock import patch, MagicMock`가 테스트 메서드 내부에 반복 임포트됨. 파일 상단 임포트로 이동 필요."
    },
    {
      "severity": "Info",
      "file": "core/fsa_loop.py:571-600",
      "finding": "_apply_evolution_guard 리팩터링은 정확함. level==4이고 failed_skills가 있을 때만 탐색하며 결과를 하위로 전달해 이중 탐지를 올바르게 방지함."
    },
    {
      "severity": "Info",
      "file": "syncCompyne/*.py",
      "finding": "CRLF → LF 줄바꿈 정규화만 발생. 로직 변경 없음."
    }
  ]
}
```

---

## 2026-04-29 14:03 — `2026-04-14-build-diet` (9f46cdb2)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "line": null,
      "finding": "전체 `permissions` 블록(allow/deny 목록) 삭제 — `git reset --hard`, `rm`, `git clean` 등 파괴적 명령 차단 규칙이 사라져 보호 수준이 낮아짐. 의도적 제거라면 전역 settings.json에 deny 규칙이 존재하는지 확인 필요."
    },
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "line": null,
      "finding": "hook 명령이 `python3 ./scripts/...` + `$PWD`(포터블)에서 하드코딩 절대 경로 `D:/hoonProJect/worktrees/agent-factory`로 변경 — 다른 머신/경로에서 hook이 즉시 실패함. 이식성 완전 파괴."
    },
    {
      "severity": "Medium",
      "file": "core/fsa_loop.py",
      "line": 571,
      "finding": "`_apply_evolution_guard`에서 `_evolution_failed_skills`가 비어 있지 않은 상태에서 `cand_name` 탐지 실패 시 Level 5 강제(`return 5, None`) — 현재 실패가 전혀 다른 원인임에도 Level 4 기회를 박탈할 수 있음. 경고 로그는 있으나 false-positive 에스컬레이션 위험 존재."
    },
    {
      "severity": "Medium",
      "file": "syncCompyne/memory_store.py",
      "line": null,
      "finding": "파일 내용이 동일한데 diff가 전체 라인으로 표시됨 — 줄끝 문자(CRLF↔LF) 변환으로 추정. 실질 코드 변경 없음. `.gitattributes`로 line-ending 정책 통일 권장."
    },
    {
      "severity": "Low",
      "file": "core/fsa_loop.py",
      "line": 607,
      "finding": "`_try_evolve_failed_skill` 시그니처에 `skill_dir: str | None = None` 추가 — `_apply_evolution_guard`에서 전달되므로 이중 탐지 방지는 의도에 맞으나, `None` 전달 시 내부에서 다시 `_detect_failed_skill_dir`를 호출하는 fallback 경로가 여전히 존재함. 두 경로 간 일관성 주의."
    },
    {
      "severity": "Low",
      "file": "tests/test_phase7_dep_graph_evolve.py",
      "line": 498,
      "finding": "`test_per_skill_guard_detection_failure_forces_level5`에서 탐지 실패(None)→Level 5 강제를 검증하지만, 이 경우 `_evolution_failed_skills` 내용과 무관하게 강제되는지(빈 셋이면 안 강제되는지)를 검증하는 음성 케이스가 없음."
    },
    {
      "severity": "Info",
      "file": "syncCompyne/project_log_cli.py, workspace_context_cli.py",
      "line": null,
      "finding": "diff 내용이 CRLF 변환 외 실질 변경 없음 — 의도적 whitespace-only 커밋이라면 commit scope에서 제외하는 것이 이력 노이즈를 줄임."
    }
  ]
}
```

**요약**: 가장 시급한 건 `settings.local.json`의 두 가지 문제 — ① deny 보호 규칙 삭제(파괴적 명령 무방비), ② 하드코딩 절대 경로(이식성 파괴). `core/fsa_loop.py`의 탐지 실패 시 무조건 Level 5 강제 로직은 false-positive 리스크가 있어 추가 케이스 검토 필요.

---

## 2026-04-29 14:04 — `2026-04-14-build-diet` (e89c82b3)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```
- [High]   .claude/settings.local.json — permissions.deny 블록 전체 삭제됨.
           git reset --hard, rm, del 등 파괴적 명령 차단 규칙이 사라져
           CLAUDE.md "Destructive Action Guard" 정책 위반. deny 규칙 복원 필요.

- [High]   skills/registry.yaml:1023,1028 — meta_path/path/last_eval_report에
           절대 경로(D:\hoonProJect\...) 커밋됨. 이전 커밋에도 macOS 절대경로
           (/Users/hoon/...) 존재 — 반복 패턴. 타 머신 실행 불가. 런타임 생성
           또는 상대 경로로 전환해야 함.

- [High]   skills/new_skill/skill-promotion.json:23 — promotion_path도 동일하게
           Windows 절대 경로 하드코딩. 소스 컨트롤에 커밋 부적합.

- [Medium] .claude/settings.local.json — hook command에 $PWD 대신 절대 경로
           (D:/hoonProJect/worktrees/agent-factory/...) 하드코딩. 다른 머신·
           worktree 경로 변경 시 hook 전부 무력화.

- [Medium] core/fsa_loop.py:598 — _apply_evolution_guard()가 cand_dir=None
           반환 후 _try_evolve_failed_skill(skill_dir=None)을 호출하면
           내부에서 _detect_failed_skill_dir()를 한 번 더 실행. 이중 탐색
           비용 발생 (결과는 동일하게 None이라 버그는 아님).

- [Low]    syncCompyne/*.py 5개 파일 — 로직 변경 없이 CRLF→LF 라인 엔딩만
           변환됨. .gitattributes로 처리해야 할 내용이 diff 노이즈로 포함.

- [Info]   data/skill-usage.jsonl, session_cursor.json, skill-eval-report.json —
           런타임 데이터 파일이 커밋에 포함. .gitignore 대상 검토 권고.
```

**핵심 액션 아이템:**
1. `settings.local.json`에 deny 규칙 복원 (보안 정책 준수)
2. `registry.yaml` / `skill-promotion.json`의 절대 경로 → 상대 경로 또는 런타임 생성으로 전환
3. hook command의 절대 경로 → `$PWD` 기반으로 되돌리기

`_apply_evolution_guard()` 리팩터링 자체(Level 4→5 강제 로직 + 테스트 3건)는 정확하고 버그 없음.

---

## 2026-04-29 14:05 — `2026-04-14-build-diet` (cf461e01)

**Context**: feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback

**Changed (18)**: `.claude/settings.local.json, core/fsa_loop.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+3)`

### Findings

```json
{
  "review": [
    {
      "severity": "High",
      "location": ".claude/settings.local.json:24,34,44,54,64",
      "finding": "Hook commands hardcode absolute Windows path `D:/hoonProJect/worktrees/agent-factory/` instead of using `$PWD` or a relative path. This breaks on any other machine or if the worktree is moved. The previous `$PWD`-based form was portable."
    },
    {
      "severity": "High",
      "location": ".claude/settings.local.json (PostToolUse removal)",
      "finding": "`PostToolUse Write|Edit` hook that ran `post_edit_code_review` was removed. This disables the automatic code-review trigger on every file edit — a regression against the Review-Gate policy established in CLAUDE.md."
    },
    {
      "severity": "Medium",
      "location": "core/skill_metadata_adapter.py:465-467",
      "finding": "In `_fill_missing_description`, when `when_to_use` is missing and the frontmatter has no `when_to_use` key, it falls back to `md_desc` (body text). This silently reuses `description` text as `when_to_use`, producing misleading registry entries."
    },
    {
      "severity": "Medium",
      "location": "core/skill_metadata_adapter.py:449",
      "finding": "`_fill_missing_description` returns early only when both `description` AND `when_to_use` are non-empty. If one field is set but the other is empty, the SKILL.md is read. The logic is correct, but the early-return condition comment is missing — subtle invariant worth documenting."
    },
    {
      "severity": "Medium",
      "location": ".claude/settings.local.json:allow",
      "finding": "The `allow` list was collapsed to a single pytest entry, removing previously needed permissions (`git commit`, `python`, `python3`, etc.). If these were removed intentionally (moved to global settings), this is fine — but there is no evidence of that migration, creating a risk of unexpected permission prompts blocking automation."
    },
    {
      "severity": "Low",
      "location": "core/skill_metadata_adapter.py:476-492 (auto_detect_and_convert)",
      "finding": "`_fill_missing_description` is called after YAML/meta.yaml paths but NOT after the `SKILL.md` branch (line 490). A pure SKILL.md skill with a missing frontmatter description and a rich body will not get the body-text fallback applied."
    },
    {
      "severity": "Low",
      "location": "tests/test_phase7_dep_graph_evolve.py",
      "finding": "Test file name suggests Phase 7 / dep-graph scope but the feature under review is T1-skill-md-fallback. No tests cover `_fill_missing_description` or `auto_detect_and_convert` with missing-description scenarios — the core new behavior has zero direct test coverage."
    },
    {
      "severity": "Info",
      "location": "syncCompyne/*.py, syncCompyne/*.md",
      "finding": "Multiple syncCompyne files are modified but no diff is shown. Cannot verify whether these changes are related to the T1 feature or are incidental churn — scope creep risk."
    }
  ]
}
```

**Summary:** Two high-severity issues — hardcoded Windows paths in hooks (portability regression) and removal of the `PostToolUse` code-review hook (policy regression). The core fallback logic in `skill_metadata_adapter.py` has a subtle `when_to_use` shadowing bug and a gap where `SKILL.md`-only skills skip the body-text fallback. No tests cover the new fallback path.

---

## 2026-04-29 14:06 — `2026-04-14-build-diet` (c7ad3e1c)

**Context**: feat(T2-per-skill-escalation): fsa_loop per-skill 에스컬레이션 가드

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "line": "26-66",
      "finding": "Hook commands hardcoded to absolute Windows path `D:/hoonProJect/worktrees/agent-factory`. 이 파일이 레포에 커밋되면 다른 머신/경로에서 hooks가 완전히 동작 불가. `$PWD` 상대 경로 또는 환경변수 사용 권장."
    },
    {
      "severity": "High",
      "file": ".claude/settings.local.json",
      "line": "66-77",
      "finding": "PostToolUse `Write|Edit` 훅 전체 삭제 — CLAUDE.md Review-Gate 규칙에 따르면 `.py` 수정 후 자동 코드리뷰 트리거가 필수인데, 이 훅이 그 역할을 담당하던 것으로 보임. 삭제 시 review-gate tier 1이 자동 우회됨."
    },
    {
      "severity": "Medium",
      "file": ".claude/settings.local.json",
      "line": "8",
      "finding": "allowlist에 특정 커밋 메시지 패턴(`feat\\(T2-per-skill-escalation\\)...`)이 하드코딩됨. 이 패턴은 해당 커밋 이후 의미가 없어지며, 이후 커밋은 매번 권한 프롬프트를 받게 됨."
    },
    {
      "severity": "Medium",
      "file": ".claude/settings.local.json",
      "line": "1-9",
      "finding": "allowlist가 pytest 1개 + git add/commit 2개로 극단적으로 축소됨. `git push`, `python`, `python3` 등 일상적인 작업이 모두 차단되어 운영 중 지속적인 권한 프롬프트 발생 예상."
    },
    {
      "severity": "Low",
      "file": ".claude/settings.local.json",
      "line": "26",
      "finding": "`python3` → `python` 변경은 Windows 환경에서는 맞지만, 이 파일이 macOS worktree에서도 사용될 경우 `python` 명령이 없을 수 있음 (macOS는 기본적으로 `python3`)."
    },
    {
      "severity": "Info",
      "file": "data/skill-usage.jsonl, skill-eval-report.json 등",
      "line": "N/A",
      "finding": "자동 생성 데이터/상태 파일들 — 기능 로직 변경 없음. diff 미제공으로 내용 검증 불가."
    }
  ],
  "summary": "주요 위험: 절대 경로 하드코딩으로 이식성 파괴 + PostToolUse review 훅 삭제로 Review-Gate 규칙 우회. 두 High 이슈 수정 필수."
}
```

---

## 2026-04-29 14:07 — `2026-04-14-build-diet` (37177d91)

**Context**: feat(T2-per-skill-escalation): fsa_loop per-skill 에스컬레이션 가드

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "[High] .claude/settings.local.json:hooks — 훅 커맨드가 하드코딩된 절대 경로(D:/hoonProJect/worktrees/agent-factory/)를 사용. 다른 PC 또는 다른 worktree에서 즉시 broken. python3 → python 변경도 macOS/Linux 호환성 손실.",
    "[High] .claude/settings.local.json:allow — git commit 권한이 특정 커밋 메시지('feat\\(T2-per-skill-escalation\\)...')로만 허용. 이후 어떤 커밋도 차단됨. 임시 변경이 영구 잔류한 것으로 보임.",
    "[Medium] .claude/settings.local.json:allow — 기존 git push, python3, git checkout 등 다수 권한 제거. 다음 작업 세션에서 필수 작업 권한 부재로 반복 허용 프롬프트 발생 예상.",
    "[Medium] .claude/settings.local.json — 머신 고유 절대경로가 포함된 settings.local.json이 레포에 커밋됨. 팀 협업 시 다른 개발자 환경을 덮어쓸 위험. .gitignore에 추가 권장.",
    "[Low] .claude/settings.local.json — PostToolUse Write|Edit 훅(post_edit_code_review) 제거. 자동 코드 리뷰 트리거가 비활성화되어 Review-Gate 파이프라인 커버리지 감소.",
    "[Info] 나머지 변경 파일(syncCompyne/*.py, data/*.jsonl 등)은 diff가 잘려 리뷰 불가. 특히 syncCompyne/memory_store.py 변경은 데이터 손실 위험이 있으므로 별도 확인 필요."
  ]
}
```

---

## 2026-04-29 14:07 — `2026-04-14-build-diet` (33000436)

**Context**: feat(T2-per-skill-escalation): fsa_loop per-skill 에스컬레이션 가드

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```
- [High]   .claude/settings.local.json:hook commands — $PWD → 하드코딩된 절대경로
           (D:/hoonProJect/worktrees/agent-factory) 로 교체되어 다른 PC/worktree에서 hook이 즉시 실패함.
           이전 $PWD 방식이 이식성 면에서 올바른 설계였음.

- [High]   .claude/settings.local.json:PostToolUse — Write|Edit 후 post_edit_code_review를
           트리거하는 hook 전체 제거됨 (diff 마지막 부분에서 확인). CLAUDE.md Review-Gate 규칙
           위반: .py 수정 시 자동 리뷰 트리거가 사라져 게이트가 수동 의존으로 전락함.

- [High]   allow list에 특정 커밋 메시지가 그대로 노출됨:
           "Bash(git commit -m 'feat\\(T2-per-skill-escalation\\)...*)".
           커밋 메시지별 권한 화이트리스트는 다음 커밋부터 전부 차단되는 안티패턴.
           "Bash(git commit *)" 패턴으로 유지해야 함.

- [Medium] python3 → python 변경: Windows 환경에서는 무관하지만,
           Mac/Linux worktree에서 재사용 시 python이 2.x를 가리킬 수 있음.

- [Low]    allow list를 1개 pytest 명령 + 1개 git add + 1개 git commit으로 극단적으로
           축소함. 일반 개발 워크플로(git push, python 실행 등)가 모두 매번 승인 요청으로
           전환되어 생산성 저하 예상.

- [Info]   syncCompyne/*.py, data/*.jsonl, *.json 변경은 상태/로그 파일로
           로직 결함 없음. registry.yaml, skill-eval-report.json도 데이터 갱신에 해당.
```

**핵심 요약**: `$PWD` 제거로 인한 이식성 파괴(High)와 `PostToolUse` hook 삭제(High)가 즉각 수정이 필요한 항목. 커밋 메시지 하드코딩(High)도 다음 세션 시작 즉시 commit 권한이 막히므로 같이 수정 필요.

---

## 2026-04-29 14:08 — `2026-04-14-build-diet` (2dc7397a)

**Context**: feat(T2-per-skill-escalation): fsa_loop per-skill 에스컬레이션 가드

**Changed (17)**: `.claude/settings.local.json, NEXT_STEPS.md, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+2)`

### Findings

```json
{
  "review": [
    "[High] .claude/settings.local.json — 훅 command가 D:/hoonProJect/worktrees/agent-factory 절대 경로로 하드코딩됨. 다른 머신/worktree에서 즉시 깨짐. $PWD 또는 상대 경로 사용 필요.",
    "[High] .claude/settings.local.json — python3 → python 으로 변경됨. Windows 환경에서 python이 Python 2를 가리킬 수 있음. 명시적으로 python3 또는 full path 사용 권장.",
    "[Medium] .claude/settings.local.json — PostToolUse Write|Edit → post_edit_code_review 훅이 제거됨. Review-Gate 자동 트리거 비활성화 — CLAUDE.md의 Review-Gate 규칙 위반 가능.",
    "[Medium] .claude/settings.local.json — allow 목록에 'git commit -m feat\\(T2-per-skill-escalation\\)...' 단일 특정 커밋 메시지만 허용. 임시 잔여물로 보임, 정리 필요.",
    "[Low] .claude/settings.local.json — git checkout/reset/clean/stash 등 다수 권한 일괄 제거. 향후 해당 명령 실행 시 권한 프롬프트 재발생 예상."
  ],
  "summary": "주요 문제: 절대 경로 하드코딩(이식성 파괴) + PostToolUse 리뷰 훅 삭제(Review-Gate 규칙 위반). 나머지 변경(syncCompyne, data, docs)은 diff 잘림으로 미검증."
}
```

---

## 2026-04-29 14:08 — `2026-04-14-build-diet` (b05bb786)

**Context**: feat(T2-per-skill-escalation): fsa_loop per-skill 에스컬레이션 가드

**Changed (17)**: `.claude/settings.local.json, NEXT_STEPS.md, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py ... (+2)`

### Findings

```json
{
  "review": [
    "[High] .claude/settings.local.json:hook_commands — 절대 경로 하드코딩 (D:/hoonProJect/worktrees/agent-factory). 다른 PC/환경에서 hook 실행 즉시 실패. $PWD 또는 상대 경로로 복원 필요.",
    "[High] .claude/settings.local.json:allow_list — PostToolUse(Write|Edit) hook 제거 확인됨(diff 말미 잘림). post-edit 코드리뷰 자동화가 비활성화되어 Review-Gate 파이프라인 단계 누락 위험.",
    "[High] .claude/settings.local.json:allow_list — git checkout/reset/pull/stash/clean 등 대부분의 git 권한 삭제. 정상 개발 워크플로우 차단 가능성.",
    "[Medium] .claude/settings.local.json:6 — 커밋 메시지 허용 패턴이 태스크 특정값 ('feat\\(T2-per-skill-escalation\\)…')으로 고정됨. 이 설정이 커밋에 포함되면 이후 모든 다른 커밋 메시지 거부됨.",
    "[Low] .claude/settings.local.json:hook_commands — python3 → python 변경. python3만 PATH에 있는 환경에서 hook 실패."
  ],
  "summary": "settings.local.json이 특정 PC 경로와 단일 태스크 커밋 메시지에 종속됨. 하드코딩 경로와 task-specific 커밋 권한은 이 커밋에 포함되면 안 됨."
}
```

---

## 2026-04-29 14:47 — `2026-04-14-build-diet` (c530166b)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\scripts\check_design_pending.py

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-29 18:09 — `2026-04-14-build-diet` (d4d7740b)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (15)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py, syncCompyne/workspace_context_cli.py`

### Findings

```json
{
  "review": [
    "- [High] data/skill-usage.jsonl — `new_skill` promoted draft→candidate with contract_pass_rate=0.0, hidden_pass_rate=0.0, runtime_success_rate=0.0 across all 6 entries. Promotion gate appears to not enforce minimum pass-rate thresholds.",
    "- [High] data/skill-usage.jsonl — hardcoded absolute Windows paths (`D:\\hoonProJect\\worktrees\\...`) baked into persisted data records. Cross-machine replay or CI will reference non-existent paths.",
    "- [Medium] data/skill-usage.jsonl — `historical_score` is frozen at 52 across every promotion event despite `feedback_total_events` incrementing (7→11). Score not recalculated on re-evaluation; staleness risk.",
    "- [Medium] data/skill-usage.jsonl — `reason: external_eval_passed` with zero runtime evidence (`runtime_total=0`). 'passed' label is misleading; should reflect evidence gaps.",
    "- [Low] data/skill-usage.jsonl — diff is truncated (last line ends mid-JSON `\"reason\": \"e`). If file on disk is also truncated, downstream JSONL parsers will throw on the malformed record.",
    "- [Info] syncCompyne/*.py / *.md — listed as changed but diff content not provided; unable to review those files."
  ]
}
```

---

## 2026-04-29 18:09 — `2026-04-14-build-diet` (b09f9571)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[Info]** `.claude/settings.local.json:47-72` — `UserPromptSubmit`에 hook 3개 등록. `check_pending_review.py` → `check_design_pending.py` → `cli_hook_bridge` 순서로 실행됨. 이전엔 `UserPromptSubmit`에 `cli_hook_bridge` 하나만 있었는데, 두 check 스크립트가 앞으로 이동한 구조. 동작은 맞으나 이름(`agent_factory_claude_userpromptsubmit`)이 3번째 hook에만 있어 앞 두 개는 디버그 시 식별 불가.

- **[Medium]** `data/skill-usage.jsonl` — `report_path`/`promotion_path`에 macOS 절대경로(`/Users/hoon/workTree/...`) 하드코딩. 현재 환경(`D:/hoonProJect/...`)에서 해당 경로가 존재하지 않으므로, 경로를 참조하는 코드가 있다면 `FileNotFoundError` 발생.

- **[Low]** `.claude/settings.local.json:130` — 파일 끝 개행 누락(`\ No newline at end of file`). 일부 도구에서 파싱 경고 유발 가능.

- **[Info]** hook `name` 필드 추가(SessionStart/PreCompact/Stop/SessionEnd) — 디버그 가시성 향상. 긍정적 변경.

- **[Info]** 나머지 파일(syncCompyne/*.py, skills/registry.yaml 등)은 diff가 제공되지 않아 검토 불가.

**요약:** `skill-usage.jsonl`의 플랫폼 간 경로 불일치(Medium)가 유일한 실질적 위험. hook 재정렬은 의도대로 동작 중.

---

## 2026-04-29 18:10 — `2026-04-14-build-diet` (a1741403)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **Medium** `.claude/settings.local.json:48-67` — Hook commands rotated across event slots without changing the surrounding event-type keys. `check_pending_review.py` now fires on what was previously the UserPromptSubmit bridge slot, and the bridge runner now occupies what was the PreToolUse/design-pending slot. Verify the enclosing `"matcher"` / event-type keys in context to confirm correct event → script mapping after rotation.

- **Low** `.claude/settings.local.json:130` — Trailing newline removed (`\ No newline at end of file`). Inconsistent with original; may cause `git diff` noise on future edits.

- **Low** `data/skill-usage.jsonl` (new entries) — `report_path` and `promotion_path` values use `/Users/hoon/workTree/agent-factory/` (macOS absolute path) instead of the current `D:/hoonProJect/worktrees/agent-factory/`. Stale cross-platform paths in log records will break any tooling that resolves these paths on Windows.

- **Info** `.claude/settings.local.json` — Adding `name` fields to hook entries is good practice for debuggability. No issue.

- **Info** `data/skill-usage.jsonl` — `contract_pass_rate`, `hidden_pass_rate`, `runtime_success_rate` all `0.0` with `shadow_cases: 0` on a skill promoted to `candidate`. Acceptable for a placeholder/new_skill slot but worth flagging if this skill ever targets `active`.

---

## 2026-04-29 18:11 — `2026-04-14-build-diet` (9ef6c366)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [High] `.claude/settings.local.json`:65–72 — `hook_runner.py cli_hook_bridge` was moved from slot 2 to slot 4 within the UserPromptSubmit hooks array. If `check_pending_review.py` and `check_design_pending.py` depend on bridge state written by hook_runner, they now fire before the bridge initializes — potential state read-before-write race.
- [Medium] `data/skill-usage.jsonl` — `report_path` and `promotion_path` contain hardcoded Mac paths (`/Users/hoon/workTree/agent-factory/...`) while the active workspace is `D:/hoonProJect/worktrees/agent-factory/`. If these paths are replayed or resolved at runtime they will silently fail on this machine.
- [Low] `.claude/settings.local.json`:65 — `name` field added to slots 1, 4, 5, 6, 7 but **omitted** from slots 2 and 3 (`check_pending_review.py`, `check_design_pending.py`). Inconsistent — those hooks are unidentifiable in logs.
- [Low] `.claude/settings.local.json`:130 — trailing newline removed (`-}` → `+}\ No newline at end of file`). Minor but breaks POSIX convention and may cause noisy diffs in future edits.
- [Info] `syncCompyne/*.py` and `syncCompyne/*.md` listed as changed but **no diff is shown** — review coverage incomplete for those files.

---

## 2026-04-29 18:12 — `2026-04-14-build-diet` (59706480)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[High]** `.claude/settings.local.json:19` — `Bash(git stash *)` 전역 허용. 스텁 없이 `stash pop`이 누락되면 미커밋 변경사항이 무음으로 소실됨. 범위를 최소화하거나 허용 목록에서 제거 권장.

- **[Medium]** `.claude/settings.local.json:51-68` — 훅 순환 재배치로 `SessionStart`에서 `cli_hook_bridge` 제거됨. 세션 연속성 브릿지가 이제 세 번째 훅(이벤트 불명확)에서 실행 — 세션 재개 요약 생성 타이밍이 달라져 `resume_brief`가 누락될 수 있음.

- **[Medium]** `data/skill-usage.jsonl` — `report_path`/`promotion_path`가 머신별 절대 경로(`/Users/hoon/`, `D:\\warkSpaces\\`)로 하드코딩. 워크트리 경로(`D:\\hoonProJect\\worktrees\\`) 와도 불일치. 상대 경로 또는 프로젝트 루트 기준 경로 사용 권장.

- **[Low]** `data/skill-usage.jsonl` — `new_skill`이 `contract_pass_rate: 0.0`, `runtime_success_rate: 0.0` 상태로 반복 `candidate` 승격. 실질적 검증 없는 자동 승격이 지속되고 있음 — 최소 통과율 임계값 적용 필요.

- **[Info]** `.claude/settings.local.json:18` — `Bash(git pull *)` wildcard 허용으로 원격 변경사항이 검토 없이 자동 적용 가능. `Destructive Action Guard` 정책과 충돌 소지.

---

## 2026-04-29 18:13 — `2026-04-14-build-diet` (25e6d26f)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[High]** `.claude/settings.local.json:17` — `"Bash(git stash *)"` 와일드카드 허용은 `git stash drop`, `git stash clear` 등 비가역적 파괴 작업을 포함. 최소 권한 원칙 위반. `git stash` / `git stash pop`만 명시적으로 허용해야 함.

- **[Medium]** `.claude/settings.local.json:67-70` — `name: "agent_factory_claude_userpromptsubmit"`가 PostToolUse 또는 다른 이벤트 블록에 붙어 있을 가능성 있음 (diff 문맥상 훅 이벤트 순서가 회전됨). 훅 이름과 실제 이벤트 타입 불일치 시 디버깅 혼란 유발.

- **[Medium]** `data/skill-usage.jsonl` — `report_path`/`promotion_path`가 `/Users/hoon/workTree/...` (macOS 절대경로)로 하드코딩됨. Windows 환경(`D:/hoonProJect/...`)에서 이 경로는 무효. 상대경로 또는 환경 독립 경로로 정규화 필요.

- **[Low]** `.claude/settings.local.json:132` — EOF 개행 누락. JSON 파일은 POSIX 표준상 개행으로 끝나야 함 (일부 도구 파싱 이슈).

- **[Info]** 훅 체인 재배치 (SessionStart→UserPromptSubmit→PreToolUse→PostToolUse 순서): `check_pending_review.py`가 UserPromptSubmit으로, `hook_runner.py`가 PostToolUse로 이동. 의도적 재설계면 문제없으나 CLAUDE.md 훅 설명과 실제 배치가 일치하는지 확인 필요.

- **[Info]** `syncCompyne/*.py` 변경분이 diff에 미포함 — Python 파일 변경 시 Review-Gate 3단계(af-test-runner → af-critic → af-cross-review) 완주 여부 확인 필요.

---

## 2026-04-29 18:13 — `2026-04-14-build-diet` (aebc22fc)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[High]** `.claude/settings.local.json:17-18` — `Bash(git pull *)` · `Bash(git stash *)` 와일드카드 허용은 과도하게 넓음. `git stash drop`·`git stash clear` 같은 파괴적 하위명령도 허용됨. `Bash(git pull --rebase=false)` 등 필요한 플래그만 명시적으로 열어야 함.

- **[Medium]** `.claude/settings.local.json:51-68` — `UserPromptSubmit` 훅이 `check_pending_review.py` → (다음 이벤트) `check_design_pending.py` → (또 다음) `hook_runner.py` 순으로 재배치됨. 세 번째 항목이 실제로 `UserPromptSubmit`에 바인딩된 것인지 확인 필요. 이벤트 타입 레이블이 diff에 없어 `check_pending_review`가 원래 실행되던 자리를 `hook_runner`가 잃지 않았는지 검증해야 함.

- **[Medium]** `syncCompyne/memory_store.py`, `project_log_cli.py`, `workspace_context_cli.py` — Changed Files 목록에 포함됐으나 diff가 제공되지 않아 내용을 검토할 수 없음. 리뷰 범위에서 누락된 상태.

- **[Low]** `.claude/settings.local.json` (마지막 줄) — `No newline at end of file`. JSON 파싱엔 무해하나 diff 노이즈를 유발하고 일부 도구에서 경고를 발생시킴.

- **[Info]** `data/skill-usage.jsonl` — macOS 경로(`/Users/hoon/workTree/...`)가 하드코딩된 이벤트가 append됨. 다중 PC 환경에서 경로가 섞이면 `report_path` / `promotion_path` 역참조 시 파일 미존재 오류 발생 가능.

---

## 2026-04-29 18:14 — `2026-04-14-build-diet` (1204cadf)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [High] `.claude/settings.local.json:16-17` — `"Bash(git stash *)"` 와일드카드 허용은 `git stash drop`·`git stash clear` 등 파괴적 서브커맨드를 포함함. 명시적 허용 패턴으로 제한 필요 (`git stash list`, `git stash show` 등 필요한 것만).
- [Medium] `.claude/settings.local.json:16` — `"Bash(git pull *)"` 와일드카드는 임의 remote/ref 지정을 허용. `git pull origin *` 수준으로 범위 좁힘 고려.
- [Medium] `.claude/settings.local.json:51-68` — 훅 명령어가 이벤트 타입별로 이전보다 한 칸씩 shift됨. UserPromptSubmit이 `check_pending_review.py`를 실행하고 그 다음 블록이 `check_design_pending.py`를 실행하도록 재배치됐는데, 이벤트 타입(PreToolUse vs UserPromptSubmit)과 의도된 커맨드 매핑이 실제 JSON 키와 일치하는지 전체 파일로 검증 필요. diff만으로는 이벤트 타입 확인 불가.
- [Low] `.claude/settings.local.json:132` — 파일 끝 개행 누락 (`No newline at end of file`). 일부 도구에서 파싱 오류 가능성.
- [Low] `data/skill-usage.jsonl` — `report_path`/`promotion_path` 필드에 `/Users/hoon/workTree/` 절대 경로 하드코딩. 다른 환경에서 재현 불가.
- [Info] syncCompyne 5개 파일(`.py`, `.md`) 변경 포함됐으나 diff 미제공 — 해당 파일 변경 내용은 검토 불가.

---

## 2026-04-29 18:14 — `2026-04-14-build-diet` (3ac2b865)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:132 — 파일 끝 newline 누락 (POSIX 텍스트 파일 규약 위반, diff 노이즈/일부 도구 경고 유발)",
    "- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 임의 인자 수용 → `git pull origin main` 등 구체 패턴으로 좁히는 편이 안전",
    "- [Info] .claude/settings.local.json:42-103 — UserPromptSubmit 훅 순서가 재배치됨(check_pending_review → check_design_pending → cli_hook_bridge). 병렬 아닌 순차 실행이므로 cli_hook_bridge가 마지막에 실행되어 앞 단계 출력이 누적됨; 의도된 순서인지 확인 필요",
    "- [Info] 코드 변경 없음 — settings.json/jsonl/yaml/md 위주이며 보안/논리 결함 없음. syncCompyne/*.py diff 본문은 제공되지 않아 별도 평가 불가"
  ]
}
```

---

## 2026-04-29 18:15 — `2026-04-14-build-diet` (2f617787)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용은 `git pull origin master; <cmd>` 같은 체이닝 인자를 통과시킬 위험. 정확한 인자 패턴으로 좁히는 것을 권장.
- [Low] .claude/settings.local.json:51-71 — UserPromptSubmit 3개 훅 command 가 한 번에 시프트된 형태(① cli_hook_bridge→check_pending_review, ② check_pending_review→check_design_pending, ③ check_design_pending→cli_hook_bridge). 의도된 순서 변경이라면 OK이나, 동일 이벤트에서 cli_hook_bridge 실행이 마지막으로 밀려 `[af-review-pending]`/`[af-design-review-pending]` 마커보다 먼저 출력되지 않는지 검증 필요(파이프라인 자동 발화 트리거 순서에 영향).
- [Low] .claude/settings.local.json:132 — EOF newline 누락(`\ No newline at end of file`). 일부 도구/CI에서 경고 발생.
- [Info] 기타 파일들(jsonl/json/yaml/md) — 상태·로그 누적 변경이 대부분으로 코드 결함 없음.

---

## 2026-04-29 18:15 — `2026-04-14-build-diet` (dd90b697)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락 (`\\ No newline at end of file`). POSIX 규약 위반, 일부 도구가 마지막 줄 누락 처리할 수 있음.",
    "- [Medium] .claude/settings.local.json:51-70 — UserPromptSubmit 훅 실행 순서 변경: cli_hook_bridge가 첫 번째에서 마지막으로 이동. resume_brief가 check_pending_review/check_design_pending 출력 뒤에 표시되어 사용자 컨텍스트 우선순위가 바뀜. 의도된 변경인지 확인 필요(커밋 메시지엔 'name 필드 추가'만 강조).",
    "- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` allow 추가. git stash는 작업 손실 가능성이 있어 와일드카드 자동 허용은 위험. 최소 stash push/list로 한정 권장.",
    "- [Info] data/skill-usage.jsonl — 이벤트 append만, 리뷰 대상 아님.",
    "- [Info] 나머지 파일 — diff 미제공으로 검토 불가(syncCompyne/*.py, registry.yaml 등). 별도 리뷰 권장."
  ]
}
```

---

## 2026-04-29 18:16 — `2026-04-14-build-diet` (17986244)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:51-72 — UserPromptSubmit 훅 순서가 cli_hook_bridge 선두→말미로 변경됨. resume_brief와 [af-review-pending]/[af-design-review-pending] 출력 순서가 뒤바뀌므로 CLAUDE.md의 트리거 감지 흐름이 의도대로 동작하는지 검증 필요.\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용은 인자 전체를 통과시키므로 권한 범위가 넓다. 필요한 서브명령만 제한하는 패턴 권장.\n- [Low] .claude/settings.local.json:132 — EOF 개행 누락(\\No newline at end of file). 일관성 위해 LF 추가 권장.\n- [Info] 나머지 변경(jsonl append, syncCompyne/* 문서·CLI, registry.yaml, session_cursor 등)은 diff 발췌 범위에서 보안·로직 결함 없음."}

---

## 2026-04-29 18:16 — `2026-04-14-build-diet` (7c985c91)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:18 — `Bash(git pull *)` 와일드카드 허용은 임의 원격에서 pull을 자동 승인. 비파괴 정책상 인터랙티브 확인이 필요한 경우에도 무프롬프트 실행됨 — 패턴을 `git pull` 또는 `git pull origin *`로 좁히는 것 권장.",
    "- [Medium] .claude/settings.local.json:51-70 — UserPromptSubmit 훅 순서가 [bridge, pending_review, design_pending] → [pending_review, design_pending, bridge]로 변경됨. bridge가 이제 pending 체크 이후 실행되므로 bridge가 생성하는 컨텍스트(예: resume_brief)에 의존하던 pending 체크는 stale 상태에서 동작. 의도된 변경이면 PR 본문에 명시 필요.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝에 개행 누락(`\\ No newline at end of file`). POSIX 텍스트 파일 규약 위반, 일부 도구에서 diff 노이즈 유발.",
    "- [Info] .claude/settings.local.json:43,70,81,92,103 — 훅에 `name` 필드 추가는 진단성 향상에 도움. PreCompact/Stop/SessionEnd에 동일 cli_hook_bridge가 동시 발화하므로 race 가능성은 hook_runner 측에서 처리 중인지 확인 필요(별도 검증 권장).",
    "- [Info] data/skill-usage.jsonl, skills/new_skill/* — 본 diff 컨텍스트에서 보이는 부분은 append-only 이벤트 로그/리포트로 보안·버그 이슈 없음.",
    "- [Info] syncCompyne/* 변경분은 diff 컨텍스트에 포함되지 않아 평가 보류."
  ]
}
```

---

## 2026-04-29 18:17 — `2026-04-14-build-diet` (ec7d7a83)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Low] .claude/settings.local.json:132 — Missing trailing newline at end of file (\"\\ No newline at end of file\")\n- [Medium] .claude/settings.local.json:51-72 — UserPromptSubmit hook 순서 변경: cli_hook_bridge가 check_pending_review/check_design_pending 뒤로 이동. CLAUDE.md의 `[af-review-pending]`/`[af-design-review-pending]` 메시지 흐름이 cli_hook_bridge의 추가 컨텍스트와 겹칠 때 출력 순서/우선순위가 의도된 것인지 검증 필요\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용 추가. git pull은 머지/리베이스를 트리거할 수 있으므로 리스크 인지 필요(파괴적 동작은 아니지만 작업 트리 상태 변경 가능)\n- [Info] .claude/settings.local.json:43,70,81,92,103 — 각 hook에 `name` 필드 추가는 좋은 개선(텔레메트리/디버깅 용이). 단, UserPromptSubmit의 다른 두 훅(check_pending_review, check_design_pending)에는 name이 없어 일관성 부족\n- [Info] diff truncated — 16개 파일 중 settings.local.json + skill-usage.jsonl 일부만 노출되어 syncCompyne/*.py, scripts, 설계문서 변경은 리뷰 범위 외. 전체 검증을 위해서는 별도 패스 필요"}

---

## 2026-04-29 18:18 — `2026-04-14-build-diet` (ea00a558)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Medium] .claude/settings.local.json:51-70 — Hook command rotation: `cli_hook_bridge`/`check_pending_review`/`check_design_pending` 위치가 이동됨. 각 블록의 matcher(SessionStart/UserPromptSubmit/PreCompact 등)가 의도한 핸들러와 매칭되는지 확인 필요. 새 `name` 필드로 cli_hook_bridge가 UserPromptSubmit으로 옮겨진 것이 의도라면 OK이지만 회귀 가능성 있음.
- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\ No newline at end of file`). 일부 도구·diff에서 잡음 유발.
- [Low] .claude/settings.local.json:18-19 — `Bash(git stash *)` 광역 허용은 사용자 변경분을 무성으로 숨길 수 있음(`git stash drop` 포함 가능). 필요한 서브커맨드만(`git stash push`, `git stash pop`) 좁히는 게 안전.
- [Info] .claude/settings.local.json:18 — `Bash(git pull *)`은 원격 fast-forward를 무인 허용. 보호 브랜치(main 등)에 대해서는 confirm을 유지하는 정책이 있다면 별도 deny 추가 권장.
- [Info] data/skill-usage.jsonl, registry.yaml, *_eval-report.json — 데이터/스냅샷 업데이트만 보이며 별다른 보안·로직 이슈 없음. (diff 전체 미열람: syncCompyne/*.py 변경분은 본 컨텍스트에 포함되지 않아 검토 보류.)

검토 범위 한계: 제공된 diff가 `.claude/settings.local.json`과 `data/skill-usage.jsonl` 일부에서 잘려 있어 `syncCompyne/memory_store.py`, `project_log_cli.py`, `workspace_context_cli.py`의 코드 변경분은 미검토. 해당 파일은 별도 리뷰 권장.

---

## 2026-04-29 18:18 — `2026-04-14-build-diet` (412b9d27)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"findings":[
"- [Critical] .claude/settings.local.json:132 — 파일 끝 newline 누락(`No newline at end of file`). POSIX 텍스트 파일 규약 위반이며 일부 도구가 마지막 줄을 누락하거나 diff 오염을 유발한다.",
"- [High] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용. `git pull` 은 원격 변경을 자동 머지하여 로컬 작업을 덮어쓸 수 있고, `git stash` 는 작업 트리 상태를 묵시적으로 이동시키므로 무인 승인 대상에서 제외하거나 `git pull --ff-only`/특정 인수로 좁혀야 한다.",
"- [High] .claude/settings.local.json:50-70 — UserPromptSubmit 훅 순서 재배치(체크 스크립트 → cli_hook_bridge). 훅이 순차 실행이라면 bridge 가 마지막에 동작해 pending 큐가 prompt 직전에 갱신되지 않을 수 있다. 의도와 실행 순서(특히 차단/비차단 종료 코드 처리) 검증 필요.",
"- [Medium] .claude/settings.local.json:42-103 — 동일 훅이 SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 5개 위치에 중복 등록되며 새로 부여한 `name` 들이 모두 다르다. 중복 실행 비용·로그 폭주를 유발할 수 있고, 한 곳에서 실패 시 식별이 어려워진다. Stop/SessionEnd 중 하나로 합치거나 재진입 가드를 확인할 것.",
"- [Medium] data/skill-usage.jsonl — `report_path` 가 `/Users/hoon/...`(타 머신 절대경로) 그대로 기록되어 워크스페이스 이식성 깨짐. 상대경로 또는 워크스페이스 기준 정규화 필요.",
"- [Info] 기타 변경(skills/registry.yaml, syncCompyne/*, session_cursor.json 등)은 diff 본문이 잘려 보안·로직 영향 평가 불가 — 추가 컨텍스트 없이 OK 판정 보류."
]}

---

## 2026-04-29 18:19 — `2026-04-14-build-diet` (fde44e15)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락 (\\ No newline at end of file). POSIX 텍스트 파일 규약 위반, 일부 도구가 마지막 줄을 누락 처리할 수 있음.",
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용. `git pull origin main; rm -rf /` 같은 체이닝 시 deny 패턴 우회 가능성 검토 필요. 구체 인자(`git pull origin <branch>`)로 좁히길 권장.",
    "- [Medium] .claude/settings.local.json:51-71 — UserPromptSubmit 훅 실행 순서 변경: 기존 [bridge → check_pending → check_design] → 변경 [check_pending → check_design → bridge]. bridge가 마지막으로 이동하면서 resume_brief 생성이 review-pending 메시지보다 늦게 출력됨. 의도된 변경인지 확인 필요(컨텍스트 노출 시점 차이).",
    "- [Info] .claude/settings.local.json:43,70,81,92,103 — 각 훅에 `name` 필드 추가는 식별성 향상에 긍정적. 다른 훅(check_pending_review, check_design_pending)에는 name이 없어 일관성 부족.",
    "- [Info] data/skill-usage.jsonl, projects/.../session_cursor.json — 자동 생성 상태 파일이 커밋에 포함됨. .gitignore 검토 권장(런타임 노이즈 누적)."
  ]
}
```

---

## 2026-04-29 18:19 — `2026-04-14-build-diet` (e188cf56)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:18-19 — `Bash(git stash *)` 와일드카드는 `git stash drop/clear` 같은 파괴적 하위 명령까지 허용. Destructive Action Guard 정책과 충돌하므로 `git stash push/list/show` 등 안전 부분집합으로 제한 권장.",
    "- [Medium] .claude/settings.local.json:51-70 — hook 매트릭스 재배치 시 이벤트 키(SessionStart/UserPromptSubmit/PreToolUse 등)별 매핑이 diff에서 보이지 않음. 두 번째 항목이 `hook_runner.py` → `check_pending_review.py`로, 네 번째는 `check_design_pending.py` → `hook_runner.py`로 바뀌어 있어 의도된 이벤트-스크립트 짝이 어긋났을 가능성. 풀 파일에서 이벤트명 검증 필요.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝에 개행 없음(`\\ No newline at end of file`). POSIX 도구·diff 호환을 위해 trailing newline 추가.",
    "- [Info] data/skill-usage.jsonl — append-only 이벤트 로그 추가, 검토 사항 없음.",
    "- [Info] 그 외 변경(syncCompyne/*, projects/global_hoon_main/.../session_cursor.json, skill-eval-report.json 등) — diff 본문이 잘려 있어 이 응답에서는 평가 불가; 별도 검토 권장."
  ]
}
```

---

## 2026-04-29 18:20 — `2026-04-14-build-diet` (b0de156b)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:51-72 — UserPromptSubmit 훅 실행 순서가 바뀜 (기존: cli_hook_bridge → check_pending_review → check_design_pending, 변경: check_pending_review → check_design_pending → cli_hook_bridge). resume_brief가 리뷰 체크 이후 출력되도록 의도된 것이라면 OK이지만, 다른 훅이 bridge 컨텍스트(예: session_cursor)를 의존했다면 회귀 위험.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락 (`\\ No newline at end of file`). POSIX 도구·git diff 노이즈 유발.\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)` 와일드카드 허용은 임의 remote/refspec까지 인자 통과시킴. 정책상 의도라면 OK, 아니면 `Bash(git pull)` 또는 `Bash(git pull origin *)`로 좁히는 게 안전.\n- [Info] hook `name` 필드 추가(agent_factory_claude_*) — 식별/디버깅에 유용. 일관 적용됨.\n- [Info] data/skill-usage.jsonl, session_cursor.json, skill-eval-report.json 등은 런타임 산출물로 보임. 의도적 커밋이 맞는지 확인 권장 (git에서 추적 제외 후보)."}

---

## 2026-04-29 18:20 — `2026-04-14-build-diet` (5f6b02a9)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Low] .claude/settings.local.json:132 — missing trailing newline at EOF.\n- [Info] .claude/settings.local.json:53-71 — UserPromptSubmit now has 3 hooks (check_pending_review, check_design_pending, cli_hook_bridge); confirm matcher patterns differ so all fire as intended and ordering matches design (bridge runs after pending checks).\n- [Info] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` added to allow list; benign but `git stash` can hide uncommitted work — verify this is intended for automated flows.\n- [Info] Diff truncated — syncCompyne/memory_store.py, project_log_cli.py, workspace_context_cli.py, skills/registry.yaml changes not visible in this review window; full review requires the remaining hunks."}

---

## 2026-04-29 18:21 — `2026-04-14-build-diet` (b7e2a6a1)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:132 — 파일 끝 개행 누락 (`No newline at end of file`); 일부 도구/diff에서 노이즈 유발\n- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 광범위; `git pull`, `git pull origin *` 등으로 좁히는 편이 안전\n- [Medium] .claude/settings.local.json:51-71 — UserPromptSubmit 훅 3개의 command 매핑이 재배치됨(check_pending_review → check_design_pending → cli_hook_bridge). matcher 블록과 의도된 스크립트가 일치하는지 재검증 필요(매처가 비어 있어 모두 실행되므로 순서가 결과에 영향)\n- [Low] .claude/settings.local.json:43,70,81,92,103 — 다른 훅에는 `name`을 부여했으나 SessionStart의 일부 매처에는 누락 가능; 명명 일관성 확인 권장\n- [Info] data/skill-usage.jsonl, session_cursor.json, skill-eval-report.json — 자동 생성 산출물 커밋. 가능하면 .gitignore 처리 또는 별도 커밋 분리 권장"}

---

## 2026-04-29 18:22 — `2026-04-14-build-diet` (508fd401)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Medium] .claude/settings.local.json:18 — `Bash(git stash *)` allows destructive `git stash drop/clear`; tighten to `Bash(git stash push*)` / `Bash(git stash pop*)`.
- [Medium] .claude/settings.local.json:62-71 — UserPromptSubmit hook commands were reordered between matchers; verify each matcher still maps to its intended script (check_pending_review vs check_design_pending vs cli_hook_bridge) — silent mis-wiring would skip review-gate triggers.
- [Low] .claude/settings.local.json:132 — missing trailing newline (`\ No newline at end of file`).
- [Info] data/skill-usage.jsonl — append-only telemetry, no concerns.
- [Info] Other 14 changed files (docs, session_cursor.json, syncCompyne/*) — diff not shown; cannot review.

---

## 2026-04-29 18:22 — `2026-04-14-build-diet` (afa1e997)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용은 임의 인자 주입 가능, 정책상 인자 범위를 더 좁히는 것이 안전\n- [High] .claude/settings.local.json:51-67 — UserPromptSubmit 슬롯 3개의 command가 회전(cli_hook_bridge↔check_pending_review↔check_design_pending). 각 hook 블록의 matcher와 의도한 스크립트가 실제로 일치하는지(설계 큐 발화 순서 포함) 재확인 필요. 잘못 매핑되면 [af-design-review-pending] 토큰이 안 뜨거나 cli_hook_bridge가 엉뚱한 이벤트에서 동작\n- [Low] .claude/settings.local.json:132 — `No newline at end of file`. JSON은 동작하나 일부 도구에서 diff 노이즈 유발\n- [Info] hook `name` 필드 추가(`agent_factory_claude_*`) — 추적성/관측 향상에 적절\n- [Info] 비-.claude/settings.local.json 변경(syncCompyne/*, skills/*, docs/*)에 대한 diff가 컨텍스트에 포함되지 않아 해당 파일에 대한 리뷰는 보류 — 주요 syncCompyne CLI/메모리스토어 변경은 별도 리뷰 권장"}

---

## 2026-04-29 18:23 — `2026-04-14-build-diet` (e14b9d71)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"findings":[
"- [Medium] .claude/settings.local.json:132 — 파일 끝 newline 누락(EOL). POSIX 텍스트 파일 규약 위반, 일부 도구(git diff, cat 연결)에서 경고/오작동 가능. 한 줄 추가 필요.",
"- [Medium] .claude/settings.local.json:18-19 — 'Bash(git pull *)', 'Bash(git stash *)' 와일드카드 허용. git pull은 원격 변경을 강제 머지하여 로컬 변경 손실 가능, git stash drop/clear까지 와일드카드로 통과될 위험. 'git pull:*', 'git stash push:*' 등 서브커맨드 한정 권장.",
"- [Low] .claude/settings.local.json:43-103 — hook name 필드를 일부 항목(SessionStart/PreCompact/Stop/SessionEnd/UserPromptSubmit)에만 추가. PreToolUse·PostToolUse 등 나머지 hook과 일관성 결여. 전 hook에 name 부여하거나 명명 규칙 문서화 필요.",
"- [Low] .claude/settings.local.json:51-71 — UserPromptSubmit hook 순서 변경(check_pending_review → check_design_pending → cli_hook_bridge). 기존 순서 의존 로직(예: bridge가 pending 상태 소비) 회귀 가능성. 순서 변경 의도가 커밋 메시지에만 있고 코드 주석/문서화 부재.",
"- [Info] data/skill-usage.jsonl, skill-eval-report.json, session_cursor.json — 런타임 산출물이 커밋에 포함됨. .gitignore 처리 검토 권장(반복 충돌·노이즈 유발).",
"- [Info] syncCompyne/* — diff 내용이 본 리뷰 컨텍스트에 잘리지 않음. memory_store.py·*_cli.py 변경에 대한 보안/에러 핸들링 검토는 별도 라운드 필요.",
"- [Info] 전반 — .py 파일 수정 없음으로 Review-Gate 자동 통과 케이스. 단 settings.local.json hook 재배치는 런타임 동작 변경이라 별도 통합 테스트(SessionStart→UserPromptSubmit 시나리오) 권장."
],"summary":"settings.local.json hook 재구성과 권한 와일드카드 확장이 핵심 변경. 기능적 critical 이슈는 없으나 (1) git pull/stash 와일드카드 허용 범위, (2) UserPromptSubmit hook 실행 순서 변경 회귀, (3) EOL 누락 3건 확인 필요. 런타임 산출물 .gitignore 정리 권장."}

---

## 2026-04-29 18:23 — `2026-04-14-build-diet` (0803f346)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review":"- [Medium] .claude/settings.local.json:132 — 파일 끝 개행 누락(`No newline at end of file`). 일부 도구·diff에서 경고를 유발하므로 EOL 추가 권장.\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 원격/스테이시 부수효과가 큰 명령을 무제한 허용. 인자 패턴을 좁히거나 deny와의 우선순위를 재확인 필요.\n- [Info] .claude/settings.local.json:54-71 — UserPromptSubmit 훅 순서 변경(check_pending_review → check_design_pending → cli_hook_bridge). 의도된 재배치인지 NEXT_STEPS/Blueprint에 명시 권장.\n- [Info] diff 컨텍스트 — syncCompyne/*, skills/*, projects/*/_bridge_state/* 등 다수 파일이 status에는 있으나 제공된 diff에는 미포함되어 보안/버그 관점 리뷰 불가. 별도 패스로 검토 필요."}

---

## 2026-04-29 18:24 — `2026-04-14-build-diet` (4e95aae9)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드가 광범위함; 인자 패턴(`git pull origin *`, `git stash push *`)으로 범위 축소 권장
- [Low] .claude/settings.local.json:132 — 파일 끝 개행 제거(`\ No newline at end of file`); JSON 편집기/diff 도구 호환성 위해 trailing newline 복원 권장
- [Info] .claude/settings.local.json:43,70,81,92,103 — hook에 `name` 필드 추가는 진단·로그 식별성 향상에 적합
- [Medium] .claude/settings.local.json:54-71 — UserPromptSubmit 3개 hook의 command가 3-way 재배치됨(`cli_hook_bridge`가 맨 뒤로 이동). hook 실행 순서에 의존하는 소비자(예: `[af-review-pending]` 메시지 출력 → cli_hook_bridge가 후속 처리)가 있다면 회귀 가능성. 순서 의도를 커밋 메시지/주석에 명시 필요
- [Info] data/skill-usage.jsonl, skill-eval-report.json — append-only 운영 데이터 변경; 리뷰 대상 아님 (정책상 산출물)
- [Info] 나머지 13개 파일(syncCompyne/*, docs/code_review/*, projects/.../session_cursor.json 등) — diff 본문이 잘려 검증 불가. 컨텍스트만으로 판단 시 보안/버그 risk 신호 없음

---

## 2026-04-29 18:24 — `2026-04-14-build-diet` (5bcd4e08)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{
  "review": [
    "- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(\"No newline at end of file\"). POSIX 텍스트 파일 규약 위반이며 일부 도구가 마지막 라인을 누락 처리할 수 있음.",
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용 추가. `git pull` 은 임의 원격/리프 인자(`git pull <url> <ref>`)를 받아 예상치 못한 코드 인입이 가능하고, `git stash drop/clear` 같은 파괴적 서브커맨드가 동일 패턴으로 통과될 수 있음. 서브커맨드 단위(`git pull`, `git stash push`, `git stash list`)로 좁힐 것.",
    "- [Medium] .claude/settings.local.json:51-71 — UserPromptSubmit 훅 3개의 실행 순서가 재배치됨(check_pending_review → check_design_pending → cli_hook_bridge). cli_hook_bridge가 마지막에 위치하면서 앞선 두 스크립트가 실패/지연될 경우 bridge 컨텍스트 주입이 누락될 위험. 의도된 순서라면 코멘트/문서로 근거를 남길 것.",
    "- [Low] .claude/settings.local.json:43,70,81,92,103 — `name` 필드를 일부 훅(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd)에만 추가. PreToolUse/PostToolUse 등 누락 훅과 일관성 부재.",
    "- [Info] data/skill-usage.jsonl — 외부 절대경로(`/Users/hoon/workTree/...`)가 이벤트 payload에 그대로 기록됨. 다른 PC에서는 무효한 경로이므로 상대경로 또는 워크스페이스 기준 경로로 정규화 권장."
  ],
  "summary": "settings.local.json 의 권한 와일드카드 확대와 UserPromptSubmit 훅 순서 변경이 가장 주의할 항목. 나머지는 일관성/정리 수준."
}

---

## 2026-04-29 18:25 — `2026-04-14-build-diet` (695765c1)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:54-70 — UserPromptSubmit 훅 실행 순서가 뒤집혔다. 이전: bridge→check_pending_review→check_design_pending. 변경 후: check_pending_review→check_design_pending→bridge. bridge가 마지막에 실행되면 resume_brief 컨텍스트가 review-pending/design-pending 메시지보다 뒤에 주입되어 우선순위가 달라진다. 의도된 변경인지 확인 필요.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 문자(EOL newline) 누락. POSIX 표준 위반이며 일부 도구에서 경고 발생.\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 광범위 와일드카드 허용. 의도된 범위면 OK이지만 예) `git pull origin main --force`도 통과한다. 필요 시 더 좁은 패턴 권장.\n- [Info] 16개 변경 파일 중 본 diff에는 .claude/settings.local.json + data/skill-usage.jsonl 일부만 노출됨. syncCompyne/*.py, scripts/check_design_pending.py 등 핵심 .py 변경은 diff에 포함되지 않아 보안·로직 검토 불가. 전체 diff 제공 또는 별도 커밋 분리 필요.\n- [Info] data/skill-usage.jsonl — 외부 절대 경로(`/Users/hoon/workTree/...`)가 evidence.report_path에 그대로 기록됨. 다중 머신 환경에서 경로 일관성 깨질 수 있으나 로그성 데이터라 영향 제한적."}

---

## 2026-04-29 18:26 — `2026-04-14-build-diet` (ed331a58)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락(`\ No newline at end of file`); POSIX 텍스트 파일 관례 위반, 일부 도구가 마지막 라인 미인식 가능.
- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용. `git pull --rebase --autostash` 등은 무방하지만 `git pull origin main:main` 처럼 로컬 브랜치 강제 이동도 매칭되어 리뷰 게이트 우회 위험 있음. 가능하면 인자 패턴을 좁히는 것을 권장.
- [Low] .claude/settings.local.json:43-72 — UserPromptSubmit 훅 순서 재배치(check_pending_review → check_design_pending → cli_hook_bridge). check_*가 stdin/표준출력으로 컨텍스트를 추가하는데 cli_hook_bridge가 마지막으로 밀려 resume_brief가 이전 훅의 출력 뒤에 오게 됨. 의도한 순서인지 확인 필요(이전엔 cli_hook_bridge가 첫 번째였음).
- [Info] .claude/settings.local.json — `name` 필드 추가는 hook 진단/로그 식별성 향상 차원에서 적절.
- [Info] data/skill-usage.jsonl, skills/registry.yaml, syncCompyne/* — 데이터/문서 변경만 포함되어 보안·버그 관점 영향 없음(diff 컷오프로 전체 확인 불가).

추가 코드 변경이 컷오프된 부분(syncCompyne/*.py)에 대한 검토는 본 응답 범위 밖이며, 실제 Python 변경 사항이 있다면 별도 리뷰가 필요합니다.

---

## 2026-04-29 18:26 — `2026-04-14-build-diet` (4428bfd2)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Medium] .claude/settings.local.json:132 — 파일 끝 개행 누락 (`\ No newline at end of file`). POSIX 표준 위반이며 일부 도구가 마지막 라인을 제대로 처리하지 못할 수 있음. 파일 끝에 개행 추가 필요.
- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 `git pull <임의-원격> <임의-브랜치>` / `git stash push -- <임의경로>` 같은 인자까지 통과시킴. 의도가 단순 `git pull` / `git stash` 라면 더 좁은 패턴 권장.
- [Info] .claude/settings.local.json:43,70,81,92,103 — 훅에 `name` 필드 추가는 진단/로그 가독성 개선에 유효. UserPromptSubmit 훅 순서 재배치(SessionStart → check_pending_review → check_design_pending → cli_hook_bridge)도 의도와 일치하는 것으로 보임. 단, 동일 이벤트 내 훅 실행 순서가 settings 파일 순서에 의존한다는 점을 문서에 명시 권장.
- [Info] data/skill-usage.jsonl, skills/* — 데이터/리포트 파일은 검토 대상 외(자동 생성).
- [Info] 진단 노트 — diff에 listed된 syncCompyne/*.py(memory_store.py, project_log_cli.py, workspace_context_cli.py) 변경 내용은 제공된 diff에 포함되지 않아 직접 검토 불가. .py 변경이 실제로 있다면 Review-Gate 3-Tier 완주 여부 확인 필요.

---

## 2026-04-29 18:26 — `2026-04-14-build-diet` (c58c63bb)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review":"- [High] .claude/settings.local.json:64-72 — UserPromptSubmit hook 순서가 변경되어 check_pending_review.py(PostToolUse 자리)와 check_design_pending.py(UserPromptSubmit 자리)가 잘못된 이벤트에 매핑됨. 원래 PostToolUse는 hook_runner였고 UserPromptSubmit이 check_pending_review였는데, 새 배치에서 PostToolUse=check_pending_review, UserPromptSubmit이 check_design_pending+hook_runner로 묶여 큐 발화 타이밍이 어긋날 수 있음. 의도된 재배치인지 확인 필요.\n- [Medium] .claude/settings.local.json:132 — 파일 끝 newline 누락(\\ No newline at end of file). POSIX 텍스트 파일 규약 위반, 일부 도구(diff/cat/git)에서 경고 발생.\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용 추가. git pull은 원격 변경을 가져와 working tree에 영향, git stash는 로컬 변경을 임시 저장—권한 prompt 없이 자동 실행되면 사용자 의도와 무관한 상태 변경 가능. 명시적 승인 정책과 충돌 여부 검토 권장.\n- [Info] diff context 부족 — syncCompyne/*.py(memory_store, project_log_cli, workspace_context_cli) 변경 내용이 diff에 포함되지 않아 보안/버그 리뷰 불가. 16개 파일 중 코드 파일 변경분 미제공."}

---

## 2026-04-29 18:27 — `2026-04-14-build-diet` (4d9c8b6e)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:51-72 — UserPromptSubmit 훅 실행 순서 변경: 기존 hook_runner.py(첫번째) → check_pending_review → check_design_pending 순서가 check_pending_review → check_design_pending → hook_runner.py로 재배치됨. resume_brief 컨텍스트가 review-pending 검사 이후 주입되므로 의존성 검증 필요.\n- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락 (`\\ No newline at end of file`). POSIX 도구·일부 JSON 파서 호환성에 영향.\n- [Low] .claude/settings.local.json:18-19 — `Bash(git stash *)` 와일드카드 허용은 `git stash drop/clear` 같은 파괴적 하위명령까지 포함. CLAUDE.md의 Destructive Action Guard 정책상 `git stash push|pop|list|show` 로 좁히는 편이 안전.\n- [Info] .claude/settings.local.json — 훅에 `name` 필드 추가는 진단·로깅 측면에서 긍정적. 단 PreCompact/Stop/SessionEnd 모두 동일 hook_runner.py 호출이라 식별값이 단계 구분에 의미 있는지 확인 권장.\n- [Info] data/skill-usage.jsonl, session_cursor.json, skill-eval-report.json — 런타임 산출물 변경. 코드 로직과 무관."}

---

## 2026-04-29 18:28 — `2026-04-14-build-diet` (26867cbc)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:19 — `Bash(git stash *)` 와일드카드 허용은 `git stash drop`/`git stash clear` 같은 파괴적 서브커맨드까지 묻지 않고 통과시킨다. `Bash(git stash push:*)`/`Bash(git stash pop:*)`로 좁힐 것.",
    "- [Medium] .claude/settings.local.json:18 — `Bash(git pull *)` 와일드카드는 `--rebase --autostash` 등 임의 인자를 허용. 안전한 형태(`Bash(git pull)` 또는 `Bash(git pull origin:*)`)로 제한 권장.",
    "- [Medium] .claude/settings.local.json:132 — 파일 끝 newline 누락(`No newline at end of file`). POSIX 도구·diff 호환성 위해 추가 필요.",
    "- [Medium] .claude/settings.local.json UserPromptSubmit 블록 — `cli_hook_bridge`가 1번째→3번째로 이동. resume_brief 컨텍스트가 `check_pending_review`/`check_design_pending` 출력보다 뒤에 합쳐져 우선순위가 바뀔 수 있음. CLAUDE.md의 `[af-review-pending]`/`[af-design-review-pending]` 자동 트리거 동작이 동일한지 검증 필요.",
    "- [Info] hook 항목들에 `name` 필드 추가는 좋음(추적성 향상).",
    "- [Info] 나머지 변경 파일(syncCompyne/*, skills/registry.yaml 등)은 diff 본문에 포함되지 않아 검토 불가. 별도 diff 제공 시 재검토."
  ]
}
```

---

## 2026-04-29 18:28 — `2026-04-14-build-diet` (eeff0853)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `git pull *` / `git stash *` wildcards broaden allow scope; tighten to specific arg patterns to avoid unintended remote/stash ops.\n- [Medium] .claude/settings.local.json:51-71 — Hook commands shifted across matchers (cli_hook_bridge moved from first to third UserPromptSubmit slot, check_pending_review/check_design_pending shifted up); verify each matcher's event pattern still pairs with the intended command, otherwise design-queue and review-queue hooks may fire on the wrong events.\n- [Low] .claude/settings.local.json:132 — Missing trailing newline at EOF.\n- [Info] Other listed files (syncCompyne/*, skills/*, jsonl/json state) not shown in diff body — unable to review substantively.\nNo critical/high issues visible in provided diff."}

---

## 2026-04-29 18:29 — `2026-04-14-build-diet` (13dffbee)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:51-71 — 훅 명령어가 이벤트 블록 간에 회전된 것처럼 보임(이전 cli_hook_bridge → check_pending_review → check_design_pending 순이 한 칸씩 이동). matcher가 동일 이벤트(UserPromptSubmit 등)에 여러 hook을 등록한 것이라면 의도된 재배치일 수 있으나, SessionStart/UserPromptSubmit/PreCompact 매핑이 뒤바뀌면 design 큐 발화/리뷰 게이트 누락 위험. 매처별 이벤트 키를 diff 밖에서 재확인 필요.",
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용. `git pull origin main --force` 같은 비파괴 가정 위반 인자도 무프롬프트 통과. 최소한 `git pull` (인자 없음) 또는 `git pull origin *` 수준으로 좁히는 것을 권장.",
    "- [Low] .claude/settings.local.json:132 — EOF 개행 제거(`\\ No newline at end of file`). POSIX 도구·diff 일관성 저하. 복구 권장.",
    "- [Info] data/skill-usage.jsonl, session_cursor.json 등 — 런타임 산출물(이벤트 로그/세션 커서)이 커밋에 포함됨. 의도된 것이 아니라면 .gitignore 처리 검토."
  ]
}
```

---

## 2026-04-29 18:29 — `2026-04-14-build-diet` (d36304eb)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Low] .claude/settings.local.json:132 — 파일 끝에 개행 없음(`No newline at end of file`); POSIX 도구 호환성을 위해 LF 추가 권장.
- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 광역 허용. `git pull origin --rebase --autostash` 등 임의 인자 통과 가능. 가능하면 구체 패턴(`git pull origin <branch>`)으로 좁힐 것.
- [Medium] .claude/settings.local.json (UserPromptSubmit hooks) — hook 실행 순서가 `check_pending_review.py` → `check_design_pending.py` → `cli_hook_bridge`로 재배치됨. 이전엔 bridge가 첫 번째였음. bridge가 세션 커서/컨티뉴이티 주입 역할이라면, 두 검사 스크립트가 stale state로 동작할 위험. 의도된 순서인지 확인 필요(특히 `[af-review-pending]`/`[af-design-review-pending]` 메시지 출력 타이밍).
- [Low] .claude/settings.local.json — hook `name` 필드 추가는 좋음(중복/디버깅 용이). 다만 동일 hook이 SessionStart/PreCompact/Stop/SessionEnd에서 같은 명령을 호출 — 이벤트 종류 식별이 `name`만으로는 어렵고 명령 인자에 `--event` 같은 식별자 추가 권장.
- [Info] syncCompyne/*, skills/*, data/skill-usage.jsonl, projects/.../session_cursor.json — 본 diff 발췌엔 내용이 보이지 않아 변경 범위/의도를 검증 불가. 커밋 메시지엔 "design 큐 훅 인프라 + Multi-Provider 설계문서"라고 명시되었지만 16개 파일이 그 범위를 넘어서는 듯 — 무관한 파일이 함께 들어왔는지 분리 커밋 검토 권장.
- [Info] docs/code_review/code-review.md — 살아있는 단일 문서 갱신 정책 준수 여부 확인(CLAUDE.md 규칙).

---

## 2026-04-29 18:30 — `2026-04-14-build-diet` (f465714e)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용은 `git stash drop`/`git pull --rebase` 등 작업 손실 가능 변형까지 자동승인되므로 더 좁은 패턴(`git pull`, `git stash push *`) 권장.\n- [Medium] .claude/settings.local.json:54-71 — UserPromptSubmit 훅 순서가 cli_hook_bridge → check_pending_review → check_design_pending에서 check_pending_review → check_design_pending → cli_hook_bridge 로 역전됨. bridge가 session_cursor를 갱신하기 전에 pending 체크가 실행되므로 의도된 변경인지(설계 큐 발화를 brige보다 먼저 보장) 커밋 메시지/문서에 명시 필요.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 없음(`No newline at end of file`). 일부 도구가 마지막 줄을 누락 처리할 수 있음.\n- [Info] .claude/settings.local.json — 6개 훅 중 SessionStart/UserPromptSubmit(bridge)/PreCompact/Stop/SessionEnd 5개에 `name` 추가, PostToolUse 훅에는 `name` 미부여. 일관성 차원에서 PostToolUse도 명명 권장.\n- [Info] data/skill-usage.jsonl — append-only 이벤트 로그 4건 추가, 기존 라인 변경 없음. 안전."}

---

## 2026-04-29 18:31 — `2026-04-14-build-diet` (da4fb2d8)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:67-71 — UserPromptSubmit hook 순서 변경: 이전에는 hook_runner(cli_hook_bridge)가 먼저 실행되어 pending 상태를 기록한 뒤 check_pending_review/check_design_pending이 그 큐를 읽었는데, 새 순서는 check_* 먼저 → hook_runner 마지막. hook_runner가 큐를 적재하는 역할이라면 첫 프롬프트에서 빈 큐가 조회되는 race가 발생할 수 있음. 의도된 변경인지 확인 필요.",
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 인자 전반(`--force`, `pop --index`, 원격 URL 직지정 등)을 자동승인. `git pull origin <branch>` 정도로 좁히거나 명시 deny 보강 권장.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락(`\\ No newline at end of file`). 일부 도구/diff 가독성에 영향. 한 줄 추가 권장.",
    "- [Info] .claude/settings.local.json — SessionStart/PreCompact/Stop/SessionEnd 훅에 `name` 필드 추가는 식별성 개선이지만 UserPromptSubmit의 check_pending_review/check_design_pending 훅에는 `name`이 없어 일관성 부족. 진단 로그에서 구분이 어려워질 수 있음.",
    "- [Info] data/skill-usage.jsonl, projects/.../session_cursor.json, skill-eval-report.json 등 — 자동 생성 로그/상태 산출물이 commit에 함께 포함됨. 로컬 PC 한정 산출물이면 .gitignore 또는 별도 동기화 경로 분리 검토."
  ]
}
```

---

## 2026-04-29 18:31 — `2026-04-14-build-diet` (c609f253)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{
  "review": [
    "- [High] .claude/settings.local.json:132 — 파일 끝 newline 누락(`\\ No newline at end of file`). POSIX 텍스트 파일 규칙 위반 + 일부 도구 파싱 이슈 가능. 마지막 `}` 뒤에 LF 추가 필요.",
    "- [High] .claude/settings.local.json:18 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 `git pull origin main --force`, `git stash drop` 같은 파괴적 변형도 자동 승인됨. 더 좁은 패턴(`git pull`, `git stash push *`)으로 제한 권장.",
    "- [Medium] .claude/settings.local.json:54-70 — UserPromptSubmit hook 순서 재배치. check_pending_review → check_design_pending → cli_hook_bridge 순으로 변경됐는데, 첫 두 훅이 BLOCK exit code(2)를 반환하면 cli_hook_bridge가 실행되지 않아 session_cursor 업데이트가 누락될 수 있음. 비차단 훅을 먼저 두거나 cli_hook_bridge를 별도 SessionStart에서 처리 확인 필요.",
    "- [Medium] data/skill-usage.jsonl:일부 — `report_path`/`promotion_path`에 `/Users/hoon/...` 절대경로 하드코딩(macOS). 현재 워크스페이스는 Windows(`D:\\hoonProJect\\...`)이므로 다른 PC에서 재현·추적 불가. 상대경로 또는 워크스페이스-루트 기준 경로로 정규화 권장.",
    "- [Low] .claude/settings.local.json — 일부 hook block에만 `name` 필드 추가, 나머지는 누락. 일관성 위해 모든 hook에 name 부여 권장(텔레메트리·로그 식별 목적).",
    "- [Info] 커밋 범위 — diff에 syncCompyne/*.py(memory_store.py, project_log_cli.py, workspace_context_cli.py) 코드 변경이 포함되었다고 명시되었으나 본 컨텍스트의 diff에는 settings/jsonl만 노출됨. 실제 .py 변경분은 별도 검토 필요(Review-Gate 3-Tier 통과 표기 확인됨)."
  ]
}

---

## 2026-04-29 18:32 — `2026-04-14-build-diet` (981539c6)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용은 임의 원격/refspec 풀(예: `git pull untrusted-remote`)을 무프롬프트로 허용. 필요 시 `git pull origin *` 처럼 원격을 좁히는 패턴 권장.",
    "- [Low] .claude/settings.local.json:132 — 파일이 newline 없이 종료(`\\ No newline at end of file`). POSIX 텍스트 규약 위반 + 향후 diff 노이즈 유발. 마지막에 개행 추가.",
    "- [Medium] .claude/settings.local.json:48-71 — UserPromptSubmit 훅 순서가 변경되어 `cli_hook_bridge`가 `check_pending_review` / `check_design_pending` 뒤로 밀림. CLAUDE.md 세션 연속성 규칙(resume_brief 주입)이 리뷰 게이트보다 늦게 실행되므로, 리뷰 게이트가 brief를 참조하는 경우 회귀 가능. 의도적이라면 docs에 근거 명시 필요.",
    "- [Info] .claude/settings.local.json:43,70,81,92,103 — 동일 명령에 `name` 필드 부여(`agent_factory_claude_*`)는 가독성 개선이므로 수용 가능. 단 모든 hook이 같은 command를 공유하므로 향후 분기 시 이름 충돌 주의.",
    "- [Info] data/skill-usage.jsonl 등 — 메타/세션/리포트 산출물(JSONL, session_cursor.json, skill-eval-report.json)이 커밋에 포함됨. 정책상 산출물이라면 OK, 아니라면 .gitignore 검토.",
    "- [Info] 본 diff에는 코드 로직 변경(.py)이 보이지 않아 syncCompyne/*.py, memory_store.py 등의 실제 변경 내용은 본 diff 단편에서 확인 불가. 핵심 로직 리뷰는 별도 청크 필요."
  ]
}
```

---

## 2026-04-29 18:32 — `2026-04-14-build-diet` (9064ce80)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` 와 `Bash(git stash *)` 권한이 와일드카드로 추가됨. `git pull` 은 작업 트리를 수정하고 `git stash` 는 변경 사항을 가릴 수 있어, Destructive Action Guard 의 정신과 충돌 가능. 가능하면 인자 패턴을 좁히거나(예: `git pull --ff-only`) 명시적 승인 흐름으로 제한 권장.\n- [Medium] .claude/settings.local.json:48-72 — UserPromptSubmit 훅 실행 순서가 재배치됨 (cli_hook_bridge → check_pending_review → check_design_pending 에서 → check_pending_review → check_design_pending → cli_hook_bridge). 브리지가 마지막으로 밀리면서 pending review/design 큐 메시지가 먼저 출력되는 의도는 합리적이나, 기존 cli_hook_bridge 가 먼저 출력하던 resume_brief 컨텍스트 의존성이 있다면 회귀 가능. 후속 훅이 브리지 출력에 의존하지 않는지 확인 필요.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락 (\\ No newline at end of file). 일부 도구·diff 노이즈 유발.\n- [Info] 다이프 컨텍스트 — syncCompyne/*, skills/registry.yaml, projects/.../session_cursor.json 등 다수 변경이 커밋 메시지(\"hook 인프라 + Multi-Provider 설계문서\") 범주를 벗어남. 무관 변경은 별도 커밋 분리가 리뷰·롤백 용이성 측면에서 권장. 진단 로그/세션 커서·메모리 산출물은 .gitignore 후보.\n- [Info] 진단 — 핵심 변경(.py 코드)이 diff 에 없어 'P1 설계문서' 본문 내용은 본 리뷰 범위 밖. 별도 설계 리뷰(af-critic + af-cross-review 병렬)로 검증 권장."}

---

## 2026-04-29 18:33 — `2026-04-14-build-diet` (03f0497e)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 권한은 `git pull origin main --force` 같은 변형도 허용해 블랙리스트(rm/reset --hard) 보호 의도를 약화시킬 수 있음. 서브커맨드 화이트리스트(`Bash(git pull)`, `Bash(git stash push:*)`)로 좁힐 것.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행(EOF newline) 누락. 일부 도구/diff에서 잡음 유발.\n- [Info] .claude/settings.local.json:43-71 — UserPromptSubmit 훅 순서 변경(bridge가 마지막으로 이동). check_pending_review/check_design_pending이 bridge 상태 업데이트 *이전*에 실행되므로, 이전 세션 기준으로 큐를 판단하는 동작이 의도된 것인지 design 문서에 명시 권장.\n- [Info] data/skill-usage.jsonl, skills/* — 외부 환경 경로(/Users/hoon/...)가 섞인 이벤트가 그대로 추가됨. 머신 간 공유 시 경로 정규화 고려.\n- [Info] 변경 파일 16개 중 핵심 코드(syncCompyne/*.py)는 diff에 노출되지 않아 본 응답에서는 보안/버그 판정 보류. 별도 리뷰 권장."}

---

## 2026-04-29 18:34 — `2026-04-14-build-diet` (d7593227)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Low] .claude/settings.local.json:18 — `Bash(git pull *)` 와일드카드 허용은 임의 원격/리프스펙(`git pull origin main:master` 등)까지 통과시킬 수 있음. 필요한 형태로 좁히는 것을 권장.
- [Low] .claude/settings.local.json:19 — `Bash(git stash *)` 도 `git stash drop`/`clear` 처럼 데이터 손실 명령을 포함. `Destructive Action Guard` 정책과 정합 점검 필요.
- [Info] .claude/settings.local.json:132 — 파일 끝 개행 누락(`No newline at end of file`). 일부 도구에서 diff 노이즈를 유발.
- [Info] .claude/settings.local.json — UserPromptSubmit 훅 3개 순서가 재배치됨(check_pending_review → check_design_pending → cli_hook_bridge). `cli_hook_bridge`가 마지막으로 이동하면서 `[af-review-pending]`/`[af-design-review-pending]` 메시지 출력 후 bridge 컨텍스트가 추가되는 흐름은 유지됨 — 의도된 변경으로 판단.
- [Info] hook 명명(`agent_factory_claude_*`) 추가는 진단/로깅에 도움. 동일 트리거의 다중 훅에는 모두 부여하는 것이 일관됨(현재 UserPromptSubmit의 `check_pending_review`/`check_design_pending` 훅에는 name 미부여).
- [Info] 나머지 변경 파일 (data/skill-usage.jsonl, syncCompyne/*, skills/*) — diff 절단으로 본문 미확인. 본 리뷰 범위 밖.

보안·버그 측면 차단 사유 없음. 와일드카드 권한 범위만 정책 재확인 권장.

---

## 2026-04-29 18:34 — `2026-04-14-build-diet` (9c15b0df)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\\ No newline at end of file`). POSIX 규약 위반, diff 노이즈 유발.\n- [Medium] .claude/settings.local.json:51-71 — UserPromptSubmit 훅 순서가 `cli_hook_bridge` → `check_pending_review` → `check_design_pending` 에서 `check_pending_review` → `check_design_pending` → `cli_hook_bridge` 로 재배치됨. 의도적이라면 OK이나, bridge가 마지막으로 밀리면서 resume_brief 출력 타이밍이 review-pending 메시지보다 뒤로 가는 점 확인 필요(사용자 지각 순서 변경).\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용. `git stash drop/clear` 같은 파괴적 변형까지 자동 승인되므로 `git stash push *`, `git stash list` 정도로 좁히는 편이 안전.\n- [Info] data/skill-usage.jsonl, session_cursor.json, skill-eval-report.json 등 — 자동 생성 산출물. 리뷰 대상 외.\n- [Info] syncCompyne/* — 변경 본문이 diff에 포함되지 않아 검증 불가. 별도 확인 필요."}

---

## 2026-04-29 18:35 — `2026-04-14-build-diet` (5e47a851)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:19 — `Bash(git stash *)` 와일드카드는 `git stash drop/clear` 같은 파괴적 서브커맨드까지 자동 허용. CLAUDE.md의 Destructive Action Guard 정책과 충돌 가능 — `git stash push/pop/list`로 좁힐 것.\n- [Low] .claude/settings.local.json:18 — `Bash(git pull *)` 와일드카드는 `--rebase`, 임의 remote/branch 인자까지 모두 허용. 의도적 범위인지 확인 필요.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행(`\\n`) 누락 (\"No newline at end of file\"). POSIX 텍스트 파일 규약 위반, 일부 도구 diff/머지에서 잡음.\n- [Info] .claude/settings.local.json:51-70 — UserPromptSubmit 훅 실행 순서가 `cli_hook_bridge → check_pending_review → check_design_pending` 에서 `check_pending_review → check_design_pending → cli_hook_bridge` 로 바뀜. resume_brief 컨텍스트가 design-pending 메시지 뒤에 출력되는 순서 변경 — 의도된 변경인지(설계 큐 알림 우선 노출) PR 본문에 명시 권장.\n- [Info] 기타 변경 — data/*.jsonl, session_cursor.json, skill-eval-report.json 등은 자동 생성/append 산출물이며 코드 결함 없음."}

---

## 2026-04-29 18:35 — `2026-04-14-build-diet` (8b58eb32)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{
  "review": [
    "- [Medium] .claude/settings.local.json:18 — `Bash(git stash *)` wildcard allows `git stash drop`/`clear`, which destroys uncommitted work and conflicts with the project's Destructive Action Guard; narrow to specific subcommands (push/pop/list/show/apply).",
    "- [Low] .claude/settings.local.json:18 — `Bash(git pull *)` wildcard permits pulls from arbitrary remotes/refs (e.g., `git pull origin main --rebase --autostash`); consider restricting to known remotes if policy demands.",
    "- [Low] .claude/settings.local.json:132 — file no longer ends with a trailing newline (`\\ No newline at end of file`); some POSIX tooling/diff tools expect a final LF — re-add it.",
    "- [Info] .claude/settings.local.json:43-70 — UserPromptSubmit hook ordering was rearranged so cli_hook_bridge now runs last instead of first; verify downstream consumers don't depend on the bridge's [Agent Factory Continuity] context being available to check_pending_review/check_design_pending earlier in the chain.",
    "- [Info] .claude/settings.local.json — `name` fields added only to bridge hooks, not to check_pending_review/check_design_pending; for consistent telemetry/identification, name all hook entries."
  ],
  "summary": "5 findings: 1 Medium (destructive `git stash *` allowlist), 2 Low (overly broad `git pull *` allowlist, missing trailing newline), 2 Info (hook reorder verification, naming consistency). No diff visible for the other 14 changed files (jsonl/yaml/md/py) — review limited to the truncated portion shown."
}

---

## 2026-04-29 18:36 — `2026-04-14-build-diet` (46cd90d6)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용 범위가 과도; 인자 패턴을 명시적으로 좁힐 것\n- [Medium] .claude/settings.local.json UserPromptSubmit — bridge 훅이 첫 번째에서 마지막으로 이동. check_pending_review/check_design_pending가 bridge가 갱신한 session_cursor 상태를 기대한다면 stale 데이터로 동작할 위험. 의도된 순서 변경인지 확인 필요\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락 (`\\ No newline at end of file`)\n- [Low] .claude/settings.local.json — 5개 훅에 `name` 필드 추가는 일관되나 PreToolUse/PostToolUse 훅(있다면)과 명명 컨벤션이 정렬되었는지 확인\n- [Info] data/skill-usage.jsonl — `/Users/hoon/workTree/...` macOS 경로 레코드와 Windows 워크스페이스 혼재; 크로스-PC 동기화 의도라면 OK이나 경로 정규화 정책 명시 권장\n- [Info] Diff에 syncCompyne/*, skills/registry.yaml, docs/code_review/code-review.md 등 언급된 16개 파일 중 본 diff 발췌에는 포함되지 않아 해당 변경은 별도 리뷰 필요\n- 보안/버그/에러 처리 측면 기타 Critical/High 이슈 없음"}

---

## 2026-04-29 18:36 — `2026-04-14-build-diet` (93f1ed1f)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락 (`No newline at end of file`); POSIX 도구·diff 노이즈 유발",
    "- [Medium] .claude/settings.local.json:54-71 — UserPromptSubmit 훅 순서 변경: cli_hook_bridge가 마지막으로 이동. check_pending_review / check_design_pending이 bridge보다 먼저 실행되며, 이전에 bridge가 주입하던 resume_brief 컨텍스트가 review-pending 판정 시점에 부재할 수 있음. 의도된 변경인지 검증 필요",
    "- [Low] .claude/settings.local.json:18-19 — `Bash(git stash *)` 화이트리스트 추가는 워크트리 변경을 숨길 수 있어 의도치 않은 작업 유실 위험. 좁은 패턴(`git stash push -m *`) 권장",
    "- [Info] .claude/settings.local.json:43,70,81,92,103 — hook `name` 필드 신규 부여는 추적성 향상 측면에서 OK. 단 SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 5곳 모두 동일 command를 공유하므로 name 충돌·중복 모니터링 시 식별자 일관성(`agent_factory_claude_<event>`) 유지 확인",
    "- [Info] diff truncated — syncCompyne/*, skills/registry.yaml, docs/code_review/code-review.md, memory_store.py 등 비가시 변경분에 대한 리뷰는 본 라운드에서 수행 불가. 커밋 메시지가 'design 큐 훅 인프라 + Multi-Provider 설계문서'라 했는데 .claude/settings.local.json 외 핵심 hook_runner/check_design_pending 코드 변경이 diff에 포함되지 않음 — 별도 라운드 필요"
  ]
}
```

---

## 2026-04-29 18:37 — `2026-04-14-build-diet` (dfc082b8)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:48-71 — UserPromptSubmit 훅 순서가 변경됨(cli_hook_bridge가 첫 번째 → 세 번째). check_pending_review/check_design_pending이 bridge 상태 갱신 전에 실행되므로, 리뷰 체크가 이전 세션 커서를 참조할 가능성. 의도된 변경이면 OK이나 회귀 가능성 확인 필요.\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 임의 인자(`--force`, `pop --force` 등)까지 매칭됨. 인자 범위 좁히는 것 권장.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\\ No newline at end of file`). POSIX 도구 호환성/diff 노이즈 유발.\n- [Info] data/skill-usage.jsonl — append-only 로그, 신규 이벤트 추가만 확인됨. 이슈 없음.\n- [Info] 그 외 syncCompyne/*, docs/*, registry.yaml — diff가 잘려 본문 미확인. 별도 검토 필요."}

---

## 2026-04-29 18:38 — `2026-04-14-build-diet` (fa35b107)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` 와일드카드 허용은 임의 원격/브랜치 pull을 자동 승인. 워크트리 상태 오염 위험, 패턴 좁히기 권장 (예: `git pull origin <branch>`).",
    "- [Low] .claude/settings.local.json:54-67 — UserPromptSubmit 훅 순서 재배치(check_pending_review → check_design_pending → cli_hook_bridge). cli_hook_bridge가 마지막으로 밀리면 앞 훅이 비차단 종료 시 bridge 컨텍스트 주입이 보장되는지 확인 필요. 한 훅이 실패해도 후속이 실행되는지 회귀 테스트 권장.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락(`\\ No newline at end of file`). POSIX 도구·diff 노이즈 유발, 한 줄 추가로 정리.",
    "- [Info] data/skill-usage.jsonl:8-11 — `report_path`/`promotion_path`에 macOS 절대경로(`/Users/hoon/workTree/...`)가 잔존. 현재 워크스페이스(Windows)와 불일치하여 후속 자동화가 경로 lookup 시 실패할 수 있음.",
    "- [Info] .claude/settings.local.json — `name` 필드 추가는 hook 식별 가능성을 높이는 좋은 변화이나, UserPromptSubmit의 두 번째·세 번째 훅(`check_pending_review`, `check_design_pending`)에는 name 미부여로 일관성 결여."
  ],
  "summary": "주요 결함은 없으나 `git pull *` 광범위 권한과 hook 순서 변경의 부수효과 검증이 필요. 나머지는 위생 항목."
}
```

---

## 2026-04-29 18:38 — `2026-04-14-build-diet` (b9f3819c)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review":"- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` and `Bash(git stash *)` 와일드카드 허용은 임의 인자(원격/refspec) 주입 위험. `git pull origin <branch>` 형태로 좁히는 것이 안전.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(\\\"No newline at end of file\\\"). POSIX 도구·diff 가독성 저하, 일관성 위해 개행 추가 권장.\n- [Info] .claude/settings.local.json UserPromptSubmit — hook 실행 순서가 [cli_hook_bridge, check_pending_review, check_design_pending] → [check_pending_review, check_design_pending, cli_hook_bridge]로 변경됨. `[af-review-pending]`/`[af-design-review-pending]` 메시지가 cli_hook_bridge의 resume_brief 출력보다 먼저 노출되도록 의도된 변경인지 확인 필요(설계 의도와 일치하면 OK).\n- [Info] 신규 `name` 필드(agent_factory_claude_*) 추가는 hook 식별·로깅에 도움. 다른 PreCompact/Stop/SessionEnd 항목과 명명 규칙 일관(스네이크케이스) 유지 양호.\n- [Info] data/skill-usage.jsonl, session_cursor.json, skill-eval-report.json 등은 런타임 산출물 — 의도적 커밋이 아니라면 .gitignore 검토 권장(과거 정책상 dist/*.zip 제외처럼).\n- 나머지 변경(설계문서·docs/code_review·syncCompyne 문서)은 diff 컨텍스트 부족으로 본 리뷰 범위 외 — 별도 확인 필요."}

---

## 2026-04-29 18:39 — `2026-04-14-build-diet` (f9e38c77)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [High] .claude/settings.local.json:18 — `Bash(git pull *)` 와일드카드 권한은 임의 리모트 pull을 허용. 공급망 위험. 특정 리모트/브랜치로 제한 권장 (예: `Bash(git pull origin *)`).\n- [Medium] .claude/settings.local.json:54-71 — UserPromptSubmit 훅 순서 변경: cli_hook_bridge가 첫 번째에서 세 번째로 이동. check_pending_review/check_design_pending이 bridge보다 먼저 실행되어 세션 상태 동기화 전에 pending 체크가 동작할 수 있음. 의존성 검증 필요.\n- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락 (`\\ No newline at end of file`). POSIX 호환성/diff 노이즈 유발.\n- [Low] .claude/settings.local.json:19 — `Bash(git stash *)` 와일드카드는 `git stash drop/clear`로 작업 손실 가능. 의도가 pull 전 stash라면 `Bash(git stash push*)` / `Bash(git stash pop*)`로 좁히기.\n- [Info] .claude/settings.local.json — 모든 cli_hook_bridge 항목에 `name` 필드 추가 (agent_factory_claude_*). 진단/로깅 측면 개선.\n- [Info] 나머지 14개 파일 — diff 컨텍스트 미노출(상태 파일·로그·등록부 갱신). 기능 변경 검증 불가, 자동 생성물로 추정."}

---

## 2026-04-29 18:39 — `2026-04-14-build-diet` (d3b95d30)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"findings":[
"- [High] .claude/settings.local.json:132 — 파일 끝 newline 누락(`}`로 끝남). POSIX 텍스트 파일 규칙 위반 + 일부 도구(diff/cat/jq 스트리밍)에서 파싱 이슈 가능.",
"- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용. `git stash drop/clear`(파괴적) 까지 자동 승인되어 위험. `git pull` / `git stash push *` / `git stash list`처럼 서브커맨드 단위로 좁힐 것.",
"- [Medium] .claude/settings.local.json:54-70 — UserPromptSubmit 훅 순서 재배치 시, 기존 `check_pending_review.py` → `check_design_pending.py` → `hook_runner.py(cli_hook_bridge)` 가 직렬 실행되는데 앞 단계가 비-zero exit 시 뒤 훅 차단 여부에 대한 문서/테스트 부재. 한 훅 실패가 bridge 세션 커서 갱신을 막으면 연속성(session_cursor) 손상 위험.",
"- [Low] .claude/settings.local.json — 동일 `command` 문자열이 5곳(SessionStart/Submit/PreCompact/Stop/SessionEnd)에 중복. `name`만 다르게 추가했지만 경로 변경 시 5곳 동시 수정 필요. 공통 변수화 또는 wrapper 스크립트 권장.",
"- [Info] 변경 파일 16개 중 실제 코드는 .claude 설정 + syncCompyne/* 뿐. syncCompyne/memory_store.py·project_log_cli.py·workspace_context_cli.py 변경 diff가 컨텍스트에 포함되지 않아 보안/버그 리뷰 불가. 별도 리뷰 라운드 필요.",
"- [Info] data/skill-usage.jsonl, skill-eval-report.json, session_cursor.json 등은 런타임 산출물. 커밋 정책상 .gitignore 후보인지 확인 권장(매 세션마다 diff 노이즈 발생)."
]}

---

## 2026-04-29 18:40 — `2026-04-14-build-diet` (847cbc1e)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락 (`\ No newline at end of file`).
- [Medium] .claude/settings.local.json:44-72 — UserPromptSubmit 훅 순서 변경: `cli_hook_bridge`가 첫 번째에서 마지막으로 이동. `check_pending_review`/`check_design_pending`이 bridge 세션 커서 업데이트 이전에 실행되므로, pending 검사 시점에 최신 세션 상태가 반영되지 않을 수 있음. 의도된 변경인지 확인 필요(특히 resume_brief가 직전 세션 정보를 가리키는 현 동작과 정합).
- [Low] .claude/settings.local.json:18-20 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용. `git pull origin main` 등은 안전하나, 신뢰할 수 없는 remote URL을 인자로 받는 형태(`git pull <url> <ref>`)는 임의 코드 실행 경로가 될 수 있음. 좁은 패턴(`Bash(git pull)`, `Bash(git pull origin *)`) 권장.
- [Info] .claude/settings.local.json:43,67,81,92,103 — hook entry에 `name` 필드 추가는 가독성·로깅 측면에서 개선. 다른 항목들과 네이밍 컨벤션(`agent_factory_claude_<event>`) 일관성 유지됨.
- [Info] data/skill-usage.jsonl, skills/* — 자동 생성 산출물(append-only 로그/리포트)로 보이며 리뷰 대상 외.
- [Info] syncCompyne/* — diff 본문이 잘려 본 변경분의 핵심 로직(memory_store/*_cli.py)을 확인할 수 없음. 별도 패스 필요.

핵심 우려는 UserPromptSubmit 훅 순서 역전 1건. 나머지는 경미.

---

## 2026-04-29 18:40 — `2026-04-14-build-diet` (f6332eb5)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{
  "review": [
    "- [Medium] .claude/settings.local.json:132 — 파일 끝 newline 누락 (\"No newline at end of file\"); POSIX 도구 호환성·diff 노이즈 유발, 한 줄 추가 권장",
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 글로브 allow는 임의 인자 허용. `git pull --rebase`, `git stash drop`처럼 파괴적/원격조작 변형까지 무프롬프트 통과될 수 있음. 더 좁은 패턴(예: `git pull`, `git stash push *`)으로 제한 검토",
    "- [Low] .claude/settings.local.json UserPromptSubmit 훅 순서 — 기존 `check_pending_review.py` → `check_design_pending.py` → `cli_hook_bridge` 순서로 재배치. 의도된 변경이지만, cli_hook_bridge가 `[af-design-review-pending]` 등 큐 메시지를 출력하는 책임이라면 큐 검사 스크립트보다 먼저 실행되어야 일관성 확보 가능. 의도 명시 필요",
    "- [Low] hook name 필드 추가 — Claude Code 훅 스펙에서 `name`이 비표준 필드일 경우 무시되거나 향후 검증으로 거부될 수 있음. 공식 스키마에 `name` 지원 여부 확인 필요",
    "- [Info] data/skill-usage.jsonl, skill-eval-report.json 등 — 자동 생성 산출물 변경. 리뷰 대상 아님",
    "- [Info] syncCompyne/* 변경 사항이 diff에 미포함 — 추가 검토 불가. 별도 리뷰 권장"
  ]
}

---

## 2026-04-29 18:41 — `2026-04-14-build-diet` (309ac62c)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:51-72 — UserPromptSubmit hook 순서 재배치(cli_hook_bridge가 1순위→3순위로 이동). check_pending_review/check_design_pending이 cli_hook_bridge가 갱신하던 상태(session_cursor 등)에 의존한다면, 이제 이전 세션 스냅샷을 읽게 되어 [af-review-pending]/[af-design-review-pending] 신호 누락 가능. 의존성 검증 필요.",
    "- [Low] .claude/settings.local.json:132 — EOF newline 누락(`\\ No newline at end of file`). JSON 파서는 허용하나 일부 도구·diff 가독성 저하.",
    "- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용. `git stash drop/clear` 같은 파괴적 서브커맨드까지 무프롬프트 통과 위험. `git stash push|list|show` 등으로 좁히는 것을 권장.",
    "- [Info] hook 5곳에 `name` 필드 추가는 식별성 향상 측면에서 적절. 다만 `name` 키가 Claude Code 스펙상 인식되는지(무시되어도 무해한지) 확인 필요."
  ]
}
```

---

## 2026-04-29 18:41 — `2026-04-14-build-diet` (6ffd474f)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:18 — `Bash(git stash *)` 와일드카드는 `git stash drop/clear`까지 허용해 작업 유실 위험. `git stash push *`/`git stash list` 등으로 좁히는 편이 안전.",
    "- [Low] .claude/settings.local.json:70 — UserPromptSubmit 훅 순서 재배치(check_pending_review → check_design_pending → cli_hook_bridge)가 의도적인지 확인. cli_hook_bridge의 [af-review-pending]/[af-design-review-pending] 컨텍스트가 이미 앞 두 훅 출력으로 전달되는 흐름과 충돌하지 않는지 점검 필요.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(\"No newline at end of file\"). POSIX 도구·diff 일관성 위해 개행 추가 권장.",
    "- [Info] data/skill-usage.jsonl — `report_path`에 macOS 절대경로(`/Users/hoon/...`)가 그대로 기록됨. Windows 작업트리에서 생성된 이벤트라면 cross-PC 동기화 산물로 추정되며 분석 시 경로 정규화 필요.",
    "- [Info] 변경 16개 파일 중 13개가 상태/세션 커서/리포트류로 보이며 실제 로직 변경은 .claude/settings.local.json 한 건. syncCompyne/*.py·memory_store.py 본문 diff가 컨텍스트에 포함되지 않아 해당 부분은 검증 보류."
  ]
}
```

---

## 2026-04-29 18:42 — `2026-04-14-build-diet` (e5b01369)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [High] .claude/settings.local.json:51-72 — Hook commands rotated across event blocks; verify the new command for each `matcher`/event still matches its intent (UserPromptSubmit vs SessionStart vs design-pending). Diff context hides event names, so silent mis-wiring is plausible.
- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` and `Bash(git stash *)` wildcard allows arbitrary args (e.g., `git pull <attacker-remote>`); consider tightening (`git pull origin *`, `git stash push *`).
- [Low] .claude/settings.local.json:132 — Missing trailing newline at EOF (`\ No newline at end of file`).
- [Info] Non-code artifacts (skill-usage.jsonl, session_cursor.json, skill-eval-report.json, skill-promotion.json, syncCompyne/*) — runtime/state churn; review only intent, not content.
- [Info] Diff truncated; could not inspect syncCompyne/*.py changes — unable to assess error handling there.

---

## 2026-04-29 18:43 — `2026-04-14-build-diet` (315beda7)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:51-72 — UserPromptSubmit 훅 순서가 바뀜: cli_hook_bridge가 첫 번째→마지막으로 이동. check_pending_review/check_design_pending이 먼저 실행되도록 한 의도는 합리적이나(리뷰 큐 메시지 우선), 커밋 메시지에 의도 명시 없음. 회귀 시 bridge 출력이 후속 훅에 가려질 가능성 있음.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝 개행 제거(`\\ No newline at end of file`). JSON 파서엔 무해하나 diff 노이즈 유발, POSIX 텍스트 규약 위반.",
    "- [Low] .claude/settings.local.json:18-19 — `Bash(git stash *)` 허용 추가. 파괴적은 아니지만 작업 은닉 가능. 의도된 권한이면 OK, 자동 승인 범위 확장임을 인지 필요.",
    "- [Info] .claude/settings.local.json:43,70,81,92,103 — 훅 5개에 `name` 필드 부여(agent_factory_claude_*). 진단·로깅 개선 목적으로 적절. 다만 UserPromptSubmit 훅 3개 중 cli_hook_bridge에만 name이 있고 check_pending/check_design 훅엔 없음 — 일관성 위해 모두 부여 권장.",
    "- [Info] diff에 P1 설계문서·hook 인프라 변경이 함께 묶임 — code-review.md/skills/syncCompyne 변경 본문이 diff에 포함되지 않아 이 영역은 검증 불가."
  ]
}
```

---

## 2026-04-29 18:43 — `2026-04-14-build-diet` (8198d402)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용 범위가 넓음. `git pull --rebase --force` 또는 `git stash drop/clear` 같은 데이터 손실 명령까지 통과될 수 있어, 글롭을 좁히거나(예: `git pull`, `git pull origin *`) deny 목록에 destructive 변형을 명시하는 편이 안전.",
    "- [Medium] .claude/settings.local.json:51-70 — UserPromptSubmit 훅 3개 순서가 재배치되어 `cli_hook_bridge`가 마지막으로 이동. 기존엔 bridge가 1번이었기 때문에 컨텍스트 주입 시점이 달라짐. `check_pending_review.py` / `check_design_pending.py`가 bridge 출력에 의존하지 않는지(또는 그 반대) 한 번 더 확인 필요.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\\ No newline at end of file`). 일부 도구·diff에서 잡음 유발.",
    "- [Info] .claude/settings.local.json — 각 hook에 `name` 필드를 추가한 것은 추적성에 도움. PreToolUse/PostToolUse 훅에는 name이 빠져있어 전체에 일관 적용하면 더 깔끔.",
    "- [Info] data/skill-usage.jsonl, skills/new_skill/* — append-only 이벤트 로그/리포트 갱신만 보임. 기능적 이슈 없음.",
    "- [Info] 노출된 diff 범위 내 syncCompyne/*, projects/global_hoon_main/_bridge_state/* 변경분은 본 발췌에 포함되지 않아 본 리뷰 대상 외."
  ]
}
```

---

## 2026-04-29 18:44 — `2026-04-14-build-diet` (b24d58fa)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용은 `--force`, `--rebase --autostash` 등 위험 플래그까지 통과시킨다. `git pull origin *` 등 범위 축소 권장.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝에 개행 누락(\\No newline at end of file). 일부 도구·diff 노이즈 유발.",
    "- [Info] .claude/settings.local.json:54-71 — UserPromptSubmit 훅 순서가 재배치됨(check_pending_review → check_design_pending → cli_hook_bridge). 의도된 변경이면 OK이나, cli_hook_bridge가 마지막으로 밀려 `[Agent Factory Continuity]` 컨텍스트가 design/review 큐 출력 뒤에 나오므로 큐 메시지 우선 인지 효과는 유지됨. 문서화 권장.",
    "- [Info] .claude/settings.local.json:43,70,81,92,103 — 훅에 `name` 필드 추가는 식별 가능성 향상. 일관되게 모든 훅에 부여된 점 양호."
  ],
  "summary": "차단성 결함 없음. 와일드카드 권한 1건과 EOF 개행 1건만 정리 권장."
}
```

---

## 2026-04-29 18:44 — `2026-04-14-build-diet` (b08dff8c)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review":"- [Medium] .claude/settings.local.json:19 — `Bash(git stash *)` 광범위 허용은 `git stash drop/clear` 같은 파괴적 하위 명령까지 무프롬프트 통과시킬 수 있음. `git stash push/list/show/pop`만 화이트리스트로 좁히는 것을 권장.\n- [Low] .claude/settings.local.json:18 — `Bash(git pull *)` 와일드카드는 `--rebase`, 임의 remote/branch 인자도 허용. 공유 워크트리에서 의도치 않은 fast-forward/rebase 발생 가능 — `Bash(git pull)` 단일 형태로 충분한지 검토.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행이 제거됨(`\\ No newline at end of file`). POSIX 텍스트 파일 규약 위반이며 일부 도구가 마지막 라인 누락으로 처리할 수 있음 — 개행 복구 권장.\n- [Info] .claude/settings.local.json:50-71 — UserPromptSubmit 훅 순서 재배치(cli_hook_bridge가 첫 번째 → 마지막). bridge가 resume_brief 컨텍스트를 주입하는 시점이 `check_pending_review`/`check_design_pending` 이후로 밀린 것이 의도인지 확인 필요(브리프 컨텍스트 부재 상태에서 검토 큐 체크가 먼저 실행됨).\n- [Info] data/skill-usage.jsonl, skill-eval-report.json, session_cursor.json 등 — 런타임 산출물/로그 변경. 코드 영향 없음.\n- [Info] syncCompyne/* — diff 본문이 컨텍스트에 포함되지 않아 변경 내용을 검증할 수 없음. 별도 검토 필요."}

---

## 2026-04-29 18:45 — `2026-04-14-build-diet` (d409e515)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Low] .claude/settings.local.json:18 — `Bash(git pull *)` 와일드카드 허용은 `git pull origin main --force` 같은 변형까지 통과시킬 수 있음; 의도된 범위라면 OK.
- [Low] .claude/settings.local.json:19 — `Bash(git stash *)` 도 `git stash drop/clear` 까지 포함되어 작업 손실 가능성. `git stash push *` 정도로 좁히는 것 권장.
- [Medium] .claude/settings.local.json (UserPromptSubmit 블록) — 훅 실행 순서가 `check_pending_review` → `check_design_pending` → `cli_hook_bridge` 로 재배치됨. 앞쪽 훅이 비제로 종료 시 bridge 미실행 위험 — Claude 훅 체인 정책(연속 실행/차단) 확인 필요. 특히 `[af-review-pending]` / `[af-design-review-pending]` 메시지 출력 후 bridge 가 자리잡혀야 세션 cursor 가 갱신됨.
- [Info] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\ No newline at end of file`).
- [Info] settings.local.json — 신규 `name` 필드(agent_factory_claude_*)는 진단 추적용으로 적절. 다른 훅 항목 간 중복 없음 확인 권장.
- [Info] data/skill-usage.jsonl, session_cursor.json 등 — 자동 생성 산출물이므로 리뷰 대상 외. 의도된 커밋인지만 확인.

검토된 변경 중 코드 로직(.py) 변경분은 diff 에 노출되지 않아 syncCompyne/*.py 파일 본문 검증은 수행 못함 — 별도 패치 확인 필요.

---

## 2026-04-29 18:46 — `2026-04-14-build-diet` (e1426223)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:132 — 파일 끝 개행(newline) 누락. POSIX 표준 위반으로 일부 도구·diff에서 경고 발생 가능.",
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 권한 추가. `git pull` 은 원격 변경 자동 병합으로 로컬 작업 유실 위험, `git stash` 는 임시 저장 후 복구 누락 시 변경사항 유실 가능. 명시적 사용자 승인 흐름 권장.",
    "- [Low] .claude/settings.local.json:54-70 — UserPromptSubmit hook 순서가 재배치됨(check_pending_review → check_design_pending → cli_hook_bridge). hook 실행 순서가 의미를 가지면 의도 확인 필요. cli_hook_bridge 가 마지막으로 이동한 이유가 design 큐 발화 후 세션 상태 동기화 목적이면 OK.",
    "- [Info] .claude/settings.local.json:43,70,81,92,103 — hook 항목에 `name` 필드 추가(agent_factory_claude_*). 식별·로깅 용이성 개선. 좋은 변경.",
    "- [Info] data/skill-usage.jsonl, skill-eval-report.json, session_cursor.json 등 — 런타임 산출물 변경. 리뷰 대상 아님."
  ],
  "summary": "주요 우려는 `git pull *` / `git stash *` 와일드카드 권한과 EOF newline 누락 2건. 나머지는 hook 재정비·이름 부여로 긍정적 변경."
}
```

---

## 2026-04-29 18:46 — `2026-04-14-build-diet` (73f3f359)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` and `Bash(git stash *)` 와일드카드 허용은 임의 원격 fetch·`git stash drop` 같은 손실 동작까지 자동 승인. 더 좁은 패턴(`git pull origin`, `git stash push *`)으로 제한 권장.
- [Low] .claude/settings.local.json:51-71 — UserPromptSubmit 훅 순서가 `hook_bridge → check_pending_review → check_design_pending` 에서 `check_pending_review → check_design_pending → hook_bridge` 로 재배치됨. bridge가 마지막으로 밀리면서 `[af-review-pending]`/`[af-design-review-pending]` 출력이 bridge가 누적한 컨텍스트보다 먼저 노출됨 — 의도라면 OK, 무의도라면 회귀.
- [Low] .claude/settings.local.json:132 — `\ No newline at end of file`. 일부 도구·머지 도구가 EOL 누락을 노이즈 diff로 본다. 빈 줄 1개 추가 권장.
- [Info] 나머지 변경(diff 잘림: syncCompyne/*, skills/registry.yaml, skill-eval-report.json, session_cursor.json, code-review.md 등)은 본 컨텍스트에 노출되지 않아 이번 리뷰에서 검증 불가. 보안/버그 관점 영향 큰 파일(`syncCompyne/memory_store.py`, `*_cli.py`)은 별도 리뷰 권장.

---

## 2026-04-29 18:47 — `2026-04-14-build-diet` (86277b62)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Medium] .claude/settings.local.json — UserPromptSubmit 훅 순서가 재배치됨(check_pending_review → check_design_pending → cli_hook_bridge). 앞 훅이 비0 종료 시 bridge가 실행되지 않을 수 있어, 세션 커서/연속성 갱신이 누락될 가능성. 의도된 변경인지 확인 필요.
- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`No newline at end of file`). POSIX 규약 위반 및 일부 도구 diff 노이즈 유발.
- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용. `git stash drop/clear` 같은 파괴적 하위 명령도 무프롬프트 통과 — Destructive Action Guard와 상충 가능. 최소 `git pull origin *`, `git stash push *` 등으로 좁히는 것을 권장.
- [Info] data/skill-usage.jsonl — append-only 이벤트 로그, 결함 없음.
- [Info] 나머지 13개 파일(syncCompyne/*, projects/*, skills/*, docs/*) — diff 본문이 컨텍스트에 포함되지 않아 본 리뷰 범위에서 평가 불가. 별도 검토 필요.

---

## 2026-04-29 18:47 — `2026-04-14-build-diet` (1248e532)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락 (POSIX 텍스트 파일 규칙 위반, 일부 도구 경고 발생 가능)\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 임의 인자 통과 가능. `git stash drop`/`git stash clear`처럼 데이터 손실 가능 명령도 허용되므로 범위를 좁히는 것 권장\n- [Info] .claude/settings.local.json:51-71 — UserPromptSubmit 훅 순서 재배치(check_pending_review → check_design_pending → cli_hook_bridge). 기존 cli_hook_bridge가 마지막으로 이동했는데, 이전 훅이 비정상 종료 시 bridge 미실행 가능성. 각 훅이 독립 실행되는지 확인 필요\n- [Info] 기타 변경(syncCompyne/*, skills/*, data/*.jsonl) — diff가 잘려있어 구조적 이슈 판단 불가. 본 리뷰 범위에서 제외", "severity_summary": {"critical": 0, "high": 0, "medium": 0, "low": 2, "info": 2}}

---

## 2026-04-29 18:48 — `2026-04-14-build-diet` (5975a348)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": "- [Medium] .claude/settings.local.json:51-71 — UserPromptSubmit 훅 순서 변경: 기존 cli_hook_bridge가 1번이었는데 3번(마지막)으로 밀림. check_pending_review/check_design_pending이 비0 exit 또는 표준출력으로 컨텍스트를 차지하면 bridge 실행이 영향받을 수 있음. 의도 확인 + 의존성 문서화 필요.\n- [Low] .claude/settings.local.json:`Bash(git pull *)`,`Bash(git stash *)` — 와일드카드 허용은 광범위. `git pull` 단독/특정 origin만 허용하는 패턴이 더 안전.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\\ No newline at end of file`). JSON 파서는 무관하나 .gitattributes/lint 일관성 깨짐.\n- [Info] data/skill-usage.jsonl — append-only 이벤트 추가만 있음. 이슈 없음.\n- [Info] 나머지 파일(syncCompyne/*, skills/registry.yaml, session_cursor.json 등) diff 미표시로 검토 불가. 이 PR은 'design 큐 훅 인프라' 변경을 표방하므로 syncCompyne 변경이 동봉 적절한지 별도 확인 권장."
}
```

---

## 2026-04-29 18:48 — `2026-04-14-build-diet` (d677ebc3)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{
  "review": [
    "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` 와 `Bash(git stash *)` 와일드카드 허용은 `git pull --rebase`/`git stash drop` 등 의도치 않은 부수효과 명령까지 통과시킴. 더 좁은 패턴(`Bash(git pull)`, `Bash(git stash push *)`) 권장.",
    "- [Medium] .claude/settings.local.json:51-72 — UserPromptSubmit 훅 실행 순서가 [bridge, pending, design] → [pending, design, bridge]로 역전됨. bridge가 pending/design 체크보다 먼저 컨텍스트를 주입해야 정상 동작하던 흐름이라면 회귀 가능. 의도된 변경인지 확인 필요.",
    "- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\\ No newline at end of file`). JSON 파서는 OK지만 Git/POSIX 도구 일관성 위해 개행 추가 권장.",
    "- [Info] .claude/settings.local.json:43,70,81,92,103 — 각 훅에 `name` 필드 추가는 식별성 향상에 긍정적. 단, hook_runner.py가 동일 명령을 5개 이벤트(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd)에서 호출 — 이벤트별 분기 로직이 hook_runner 내부에 있는지 확인 필요.",
    "- [Info] data/skill-usage.jsonl — append-only 이벤트 로그 추가, 기존 라인 변경 없음. 정상.",
    "- [Info] 기타 14개 파일은 diff가 잘려 표시됨 — syncCompyne/*.py 변경사항(memory_store/project_log_cli/workspace_context_cli)은 별도 검토 필요."
  ],
  "summary": "주요 우려: (1) git pull/stash 와일드카드 권한 과다, (2) UserPromptSubmit 훅 순서 역전이 의도된 것인지 확인 필요. 차단 수준 이슈는 없음."
}

---

## 2026-04-29 18:49 — `2026-04-14-build-diet` (31047335)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review":"- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 자동 허용은 워킹트리·스태시 상태를 비대화식으로 변경할 수 있어 destructive guard 경계와 충돌 가능. 최소한 `git pull --ff-only`로 좁히는 것을 권장.\n- [Low] .claude/settings.local.json:54-70 — UserPromptSubmit 훅 순서가 [bridge, check_pending_review, check_design_pending] → [check_pending_review, check_design_pending, bridge]로 바뀜. bridge가 마지막으로 이동하면 review/design pending 결과가 bridge 컨텍스트 주입 전에 출력되는데, 의도된 변경인지 커밋 메시지에 명시 필요.\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\\ No newline at end of file`). POSIX 텍스트 규약 위반, 일부 도구가 마지막 줄 파싱 실패 가능.\n- [Info] .claude/settings.local.json:43,70,81,92,103 — 훅 객체에 `name` 필드 추가는 식별성 향상에 좋음. 단, `agent_factory_claude_userpromptsubmit`는 동일 이벤트의 3개 훅 중 1개에만 부여되어 중복 식별 시 혼란 우려.\n- [Info] diff truncated — syncCompyne/* 6개 파일 및 skills/registry.yaml 변경분 미확인. 본 리뷰는 .claude/settings.local.json 한정."}

---

## 2026-04-29 18:50 — `2026-04-14-build-diet` (171711a8)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Medium] .claude/settings.local.json:51-67 — 훅 명령어 재배치로 이벤트-명령 매핑이 뒤섞임. 기존: UserPromptSubmit → check_pending_review → check_design_pending → hook_runner 순이었는데 변경 후 동일 이벤트 블록 안에서 hook_runner가 마지막으로 이동. 이벤트 키와 명령 의도가 일치하는지(특히 새로 붙은 `agent_factory_claude_userpromptsubmit` name이 실제 UserPromptSubmit 블록 내부인지) 재확인 필요.
- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락(`\ No newline at end of file`). POSIX/일부 도구가 마지막 라인 누락으로 경고.
- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 광범위 와일드카드 허용. `git pull origin main` 등으로 좁히는 것이 안전(임의 원격 fetch/rebase 차단).
- [Info] data/skill-usage.jsonl — `report_path`가 `/Users/hoon/...`(macOS 경로)로 기록됨. 현 워크스페이스(Win)와 혼재. 기존 데이터 append라 재현 가능.
- [Info] diff 본문에 syncCompyne/*.py 코드 변경분이 포함되지 않아 해당 파일은 정적 리뷰 불가. 실제 .py 변경이 있다면 별도 diff 제공 요망(메모리/CLI 보안·예외 처리 점검 누락).

---

## 2026-04-29 18:50 — `2026-04-14-build-diet` (a562ed81)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드는 임의 인자(`--rebase`, `--force`, 원격명) 허용 → 의도치 않은 원격 풀/스태시 가능. 인자를 제한하거나 사용 패턴 좁힐 것.\n- [High] .claude/settings.local.json:51-71 — UserPromptSubmit 계열 hook의 command 값이 위치별로 이동(cli_hook_bridge ↔ check_pending_review ↔ check_design_pending). diff상 hook→event 매핑이 셔플돼 있어, 각 이벤트 키(SessionStart/UserPromptSubmit/PreCompact 등)가 의도한 스크립트를 가리키는지 전체 settings.local.json 구조에서 재확인 필요. 잘못 매핑되면 review-pending/design-pending 큐가 발화하지 않음(CLAUDE.md 교차검증 자동 실행 규칙 위배).\n- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락(`\\ No newline at end of file`). POSIX 도구·일부 머지 도구에서 경고 유발.\n- [Info] hook entry에 `name` 필드 추가(agent_factory_claude_*)는 식별/디버깅에 유용. 동일 이벤트 내 다른 entry에도 일관되게 부여 권장.\n- [Info] data/skill-usage.jsonl, session_cursor.json, skill-eval-report.json 등은 자동 생성 산출물 — 변경 의도가 인프라가 아닌 런타임 부산물이면 .gitignore 검토 권장(반복 diff 노이즈).\n- 실제 디프 외 syncCompyne/* 및 docs/code_review/code-review.md 본문은 컨텍스트에 포함되지 않아 별도 검토 불가."}

---

## 2026-04-29 18:51 — `2026-04-14-build-diet` (2d630e2b)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"findings":[
"- [High] .claude/settings.local.json:132 — 파일 끝 개행 누락(\\\"No newline at end of file\\\"). JSON 파싱은 문제 없으나 일부 도구·git diff에서 경고 유발, POSIX 텍스트 파일 규약 위반",
"- [High] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)`를 allow 목록에 추가. `git pull`은 원격 변경을 로컬에 병합하는 비-순수 작업이며 충돌 시 working tree 상태를 변경. 사용자 확인 없이 자동 허용은 'Executing actions with care' 정책(공유 상태 영향 행위는 confirm 필요)과 충돌",
"- [Medium] .claude/settings.local.json:51-71 — UserPromptSubmit hooks 순서 재배치(check_pending_review → check_design_pending → cli_hook_bridge). hook 실행은 배열 순서대로이므로 cli_hook_bridge가 마지막으로 밀렸는데, bridge가 출력하는 resume_brief가 review-pending 메시지보다 뒤에 와서 컨텍스트 혼선 가능. 의도된 변경인지 확인 필요",
"- [Medium] .claude/settings.local.json — hook 항목에 `name` 필드 추가는 좋지만 PostToolUse(line 122 부근)에는 `name`이 없어 일관성 결여. 전 hook에 식별자 부여 권장",
"- [Low] data/skill-usage.jsonl, skill-eval-report.json, session_cursor.json — 런타임 산출물(JSONL append/state)이 커밋에 포함됨. .gitignore 대상으로 검토 권장 (이전 커밋들과 동일 패턴이라 신규 결함은 아님)",
"- [Info] syncCompyne/* 파일 16개 중 다수가 이 커밋 메시지(hook 인프라 + Multi-Provider 설계)와 직접 관련 없어 보임. 변경 범위 분리(commit hygiene) 권장 — 단, diff 본문이 잘려 syncCompyne 실제 변경 내용은 미검토"
]}

---

## 2026-04-29 18:51 — `2026-04-14-build-diet` (8ff7a84c)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"findings":[
"- [High] .claude/settings.local.json:132 — 파일 끝에 newline 없음 (\\ No newline at end of file). POSIX 텍스트 파일 규약 위반, 일부 도구가 마지막 라인 누락 처리할 수 있음.",
"- [Medium] .claude/settings.local.json:18-19 — 'Bash(git pull *)' 및 'Bash(git stash *)' 와일드카드 허용. git pull은 원격 변경사항을 자동 머지하여 로컬 작업 손실 가능, git stash는 의도치 않은 stash drop 위험. 더 좁은 패턴(예: 'Bash(git pull)', 'Bash(git stash list)') 권장.",
"- [Medium] .claude/settings.local.json:54,62,70 — UserPromptSubmit hook 순서 재배치(check_pending_review → check_design_pending → cli_hook_bridge). 순서 변경의 의도가 commit message에서 불명확. cli_hook_bridge가 마지막에 실행되면 앞선 두 hook 출력이 누적되어 컨텍스트 비대 위험.",
"- [Low] .claude/settings.local.json:43,81,92,103 — 일부 hook에만 'name' 필드 추가됨. SessionStart/PreCompact/Stop/SessionEnd는 추가했으나 UserPromptSubmit의 check_pending_review/check_design_pending hook에는 name 누락. 일관성 결여로 hook 식별/디버깅 시 혼선.",
"- [Info] data/skill-usage.jsonl, skill-eval-report.json, session_cursor.json — 자동 생성 런타임 산출물이 커밋에 포함됨. .gitignore 처리 또는 별도 커밋 분리 검토 권장.",
"- [Info] 커밋 메시지가 'feat(hook-infra+P1-design)'로 두 가지 변경(훅 인프라 + Multi-Provider 설계문서)을 한 커밋에 포함. 그러나 diff에는 설계문서(docs/2026-04-29-*.md) 변경이 보이지 않음 — 별도 커밋이거나 누락 가능성.",
"- [Info] syncCompyne/* 6개 파일 변경이 diff에 표시되지 않아 영향 평가 불가. 본 리뷰 범위에서 제외됨."
]}

---

## 2026-04-29 18:52 — `2026-04-14-build-diet` (84c0098a)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`와 `Bash(git stash *)` 광범위 와일드카드 허용; `git pull origin main` 등으로 좁히는 것이 안전\n- [Medium] .claude/settings.local.json:51-71 — UserPromptSubmit 훅 명령이 재배치됨(check_pending_review/check_design_pending/hook_runner). 실행 순서가 의도대로인지(검토 큐 발화 → bridge 동기화) 검증 필요. bridge가 마지막이면 pending 큐를 못 보고 종료할 위험\n- [Low] .claude/settings.local.json:132 — 파일 말미 개행 누락(`No newline at end of file`); 다음 편집 시 diff 노이즈 유발\n- [Info] settings.local.json — 각 훅에 `name` 필드 부여는 추적성 향상 측면에서 좋음\n- [Info] data/skill-usage.jsonl, session_cursor.json — 자동 생성 로그/상태; 리뷰 대상 아님. 16-파일 변경 중 실제 코드 변화는 settings.local.json이 유일하게 보이며 나머지(syncCompyne/*, docs/*) diff가 잘려 검토 불가 — 전체 patch 재공급 권장"}

---

## 2026-04-29 18:52 — `2026-04-14-build-diet` (da79faf5)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Low] .claude/settings.local.json:132 — 파일 끝 개행 누락 (`No newline at end of file`); POSIX 도구·diff 노이즈 유발 가능, 줄바꿈 추가 권장.\n- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 의도치 않은 인자(`git stash drop`, `git pull --rebase --autostash`)까지 통과시킴; 필요한 서브커맨드만 화이트리스트로 좁히길 권장.\n- [Medium] .claude/settings.local.json:51-72 — UserPromptSubmit 훅 실행 순서가 재배치되어 `check_pending_review.py` → `check_design_pending.py` → `cli_hook_bridge` 순으로 변경됨. 기존에는 bridge가 먼저 컨텍스트를 주입했으나 이제 마지막에 동작 — 두 check 스크립트가 bridge 산출물(resume_brief 등)에 의존하지 않는지 확인 필요.\n- [Low] .claude/settings.local.json — 새로 추가된 `name` 필드(`agent_factory_claude_*`)가 일부 훅(UserPromptSubmit의 check_*) 항목에는 누락됨. 일관성 위해 모든 hook entry에 name 부여 권장(텔레메트리·디버깅 추적성).\n- [Info] data/skill-usage.jsonl, session_cursor.json 등 — 런타임 산출물이 커밋에 포함됨. 의도된 것이 아니라면 .gitignore 처리 검토.\n- [Info] 나머지 13개 파일은 diff 본문이 제공되지 않아 검증 불가 — 본 리뷰 범위 밖."}

---

## 2026-04-29 18:53 — `2026-04-14-build-diet` (99c9a47d)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:18-19 — 새로 추가된 `Bash(git pull *)`, `Bash(git stash *)` 와일드카드가 과도하게 넓다. `git pull origin main` 같은 좁은 패턴 권장 (임의 원격/refspec 허용 위험)",
    "- [Low] .claude/settings.local.json:53-71 — UserPromptSubmit hook 순서가 `cli_hook_bridge → check_pending_review → check_design_pending` 에서 `check_pending_review → check_design_pending → cli_hook_bridge` 로 역전됨. resume_brief 생성 타이밍이 pending 검사 후로 밀리는데 의도 확인 필요",
    "- [Low] .claude/settings.local.json:132 — EOF 개행 누락 (`\\ No newline at end of file`)",
    "- [Info] 기타 변경 파일(skill-usage.jsonl, session_cursor.json, skill-eval-report.json 등)은 런타임 자동 생성 상태 파일로 리뷰 대상 아님",
    "- [Info] syncCompyne/* diff 가 본 컨텍스트에 포함되지 않아 검토 미수행"
  ]
}
```

---

## 2026-04-29 18:53 — `2026-04-14-build-diet` (7dbe21f3)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review":"- [Medium] .claude/settings.local.json:132 — 파일 끝 newline 누락 (POSIX 텍스트 파일 규약 위반, 일부 도구가 마지막 줄을 무시할 수 있음).\n- [Medium] .claude/settings.local.json:54-71 — UserPromptSubmit 훅 순서가 변경됨: 기존 `cli_hook_bridge` → `check_pending_review` → `check_design_pending` 순서가 `check_pending_review` → `check_design_pending` → `cli_hook_bridge` 순서로 재배치됨. bridge가 마지막에 실행되도록 의도된 것인지 확인 필요 — 만약 bridge가 pending review 컨텍스트를 주입해야 한다면 순서가 뒤집혀 검증 메시지가 누락될 수 있음.\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 광범위 와일드카드 허용. `git pull --rebase=false origin main` 같은 의도치 않은 인자 조합도 자동 승인됨. 필요 시 더 좁은 패턴으로 제한 권장.\n- [Info] data/skill-usage.jsonl — 외부(macOS) 경로 `/Users/hoon/workTree/...`가 그대로 기록됨. 운영 영향은 없으나 다중 PC 동기화 시 경로 혼선 가능.\n- [Info] 변경 파일 16개 중 실제 diff 일부만 제공되어 syncCompyne/*.py, memory_store.py, project_log_cli.py, workspace_context_cli.py 등 핵심 Python 변경의 보안/버그 검토는 본 리뷰에서 다루지 못함. 별도 검토 필요."}

---

## 2026-04-29 18:54 — `2026-04-14-build-diet` (013d3af9)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` 와 `Bash(git stash *)` 는 와일드카드 범위가 너무 넓음; 원격/브랜치 인자를 좁히는 패턴 권장\n- [Low] .claude/settings.local.json:132 — 파일 끝 newline 누락 (`\\ No newline at end of file`)\n- [Info] .claude/settings.local.json:51-72 — UserPromptSubmit 훅 순서 변경: cli_hook_bridge 가 check_pending_review · check_design_pending 뒤로 이동. 의도된 변경인지 확인 필요 (브리지가 큐 상태 갱신 후 실행되는 것이 맞는지)\n- [Info] .claude/settings.local.json — 훅에 `name` 필드 추가는 디버깅·식별 측면에서 개선\n- [Info] data/skill-usage.jsonl, session_cursor.json 등 — 자동 생성 산출물; 리뷰 영향 없음", "summary": "주요 결함 없음. settings.local.json 의 git 와일드카드 권한과 EOF newline, UserPromptSubmit 훅 순서 변경 의도만 확인 권장."}

---

## 2026-04-29 18:55 — `2026-04-14-build-diet` (28d84e41)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Info] .claude/settings.local.json:18-20 — `Bash(git pull *)`/`Bash(git stash *)` 와일드카드 허용은 의도적이라면 OK이나, pull/stash 인자에 임의 원격·브랜치가 들어갈 수 있어 권한 범위가 넓다. 필요한 형태(`git pull origin *` 등)로 좁히는 것을 권장.",
    "- [Medium] .claude/settings.local.json:51-70 — 3개 훅 command가 동일 type/위치에서 단순히 자리만 바꿨다. 각 hooks 블록이 어떤 이벤트(SessionStart/UserPromptSubmit/Stop 등)에 매핑되는지 diff에서 확인되지 않는다. 이벤트별 의도(예: design 큐는 UserPromptSubmit에서 발화)와 매핑이 일치하는지 settings.local.json 전체 컨텍스트로 재검증 필요. 매핑이 어긋나면 `[af-design-review-pending]` 자동 발화가 침묵 실패한다.",
    "- [Low] data/skill-usage.jsonl, skills/new_skill/* — `report_path`에 `D:\\warkSpaces\\agent-factory\\...` (오타 'warkSpaces') 경로가 그대로 누적된다. 신규 행은 아니지만 회귀 추적 시 혼동 유발. 후속 정리 권장.",
    "- [Info] syncCompyne/* — 본 diff 컨텍스트만으로는 변경 내용이 노출되지 않아 보안·버그 관점 평가 불가. 별도 리뷰 필요."
  ],
  "severity_summary": {"critical": 0, "high": 0, "medium": 1, "low": 1, "info": 2}
}
```

---

## 2026-04-29 18:55 — `2026-04-14-build-diet` (4a535467)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:133 — 파일 끝에 개행 없음 (`\\ No newline at end of file`); POSIX 도구 호환성 저해\n- [Medium] .claude/settings.local.json:54-72 — UserPromptSubmit hook 3개 순서가 [bridge→pending_review→design_pending] → [pending_review→design_pending→bridge]로 재배열됨. bridge가 마지막으로 이동했으므로, 리뷰 체크가 출력한 [af-review-pending]/[af-design-review-pending] 메시지가 bridge의 세션 커서/리줌 브리프 캡처보다 먼저 주입됨. 의도된 변경인지 확인 필요 (특히 SessionStart는 bridge가 먼저 실행되는데 UserPromptSubmit만 뒤로 빼면 비대칭)\n- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)` 및 `Bash(git stash *)` 와일드카드 허용 추가. `git pull origin main --force` 같은 호출까지 무프롬프트 통과 가능; 필요 시 더 좁은 패턴 권장\n- [Low] .claude/settings.local.json:21 — `mcp__codex__codex` 자동 허용 추가; codex MCP 호출이 사용자 승인 없이 실행됨. 의도 확인 필요\n- [Info] hook `name` 필드 5곳 추가 — 진단/로깅 가독성 향상, 부작용 없음\n- [Info] data/skill-usage.jsonl, session_cursor.json — 런타임 산출물; 리뷰 대상 아님 (.gitignore 검토 권장)"}

---

## 2026-04-29 18:56 — `2026-04-14-build-diet` (6343ff88)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{"findings":[
"- [High] .claude/settings.local.json:133 — 파일 끝 newline 누락 (POSIX 텍스트 파일 규약 위반, 일부 도구가 마지막 줄 처리 실패 가능)",
"- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용은 `git pull --rebase=interactive` 등 대화형/원격 강제 옵션까지 자동 승인. 자주 쓰는 인자만 명시적으로 좁히는 편이 안전",
"- [Medium] .claude/settings.local.json:55-71 — UserPromptSubmit hook 순서 재배치 시 check_pending_review.py → check_design_pending.py → cli_hook_bridge 3개가 직렬 실행됨. 첫 두 스크립트가 비-zero exit 시 cli_hook_bridge가 차단되어 session_cursor 갱신이 누락될 위험. 각 스크립트가 항상 0 종료/예외 격리 보장하는지 확인 필요",
"- [Low] .claude/settings.local.json:20 — `mcp__codex__codex` allow는 MCP 도구 전체 호출을 무조건 허용. 호출 인자/대상 제한이 없어 의도치 않은 외부 호출 가능성 — 권한 범위 검토 권장",
"- [Info] data/skill-usage.jsonl — diff 일부가 잘려 마지막 라인 무결성(JSONL 마지막 newline) 확인 불가. append 시 trailing newline 정책 점검",
"- [Info] 16개 변경 파일 중 syncCompyne/*, projects/global_hoon_main/* 변경분이 diff에 노출되지 않아 본 리뷰 범위 외 — 별도 검토 필요"
]}
```

---

## 2026-04-29 18:56 — `2026-04-14-build-diet` (6b7aea19)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Low] .claude/settings.local.json:133 — 파일 끝 개행 누락 (POSIX 규약 위반, 일부 도구가 마지막 줄 인식 못함)\n- [Medium] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 `git pull --rebase --autostash` 등 부수효과 큰 변형까지 무프롬프트 통과시킴; 의도된 명령만 명시 권장\n- [Info] .claude/settings.local.json:55-72 — UserPromptSubmit 훅 순서가 cli_hook_bridge→check_pending_review→check_design_pending에서 check_pending_review→check_design_pending→cli_hook_bridge로 재배치됨. bridge가 마지막에 실행되므로 앞의 두 스크립트가 stdin/stdout을 변형하면 bridge가 받는 컨텍스트가 달라질 수 있음 — 의도된 변경인지 PR 본문에서 확인 필요\n- [Info] 16개 변경 파일 중 다수(skill-usage.jsonl, session_cursor.json, skill-eval-report.json 등)가 자동 생성 산출물 — 커밋 메시지의 'design 큐 훅 인프라 + Multi-Provider 설계문서' 범위와 무관해 보이므로 .gitignore 추가 또는 별도 커밋 분리 검토\n- [Info] 변경 파일 목록에 docs/2026-04-29-*.md 설계문서 자체가 보이지 않음 — '설계문서' 변경분이 본 diff에 포함되지 않은 것으로 보여 커밋 제목과 실제 변경분 불일치 가능성"}

---

## 2026-04-29 18:57 — `2026-04-14-build-diet` (4412cd31)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{"review": "- [Medium] .claude/settings.local.json:133 — 파일 끝 개행 누락 (`No newline at end of file`); POSIX 도구·diff 호환성 저하\n- [Medium] .claude/settings.local.json:52-71 — UserPromptSubmit 훅 명령 재배치 시 matcher와 command 매핑 검증 필요. diff 상 같은 matcher 블록 내에서 command가 회전된 것처럼 보임 — 의도된 재배치인지(check_pending_review → check_design_pending → cli_hook_bridge 순) 별도 확인 필수\n- [Low] .claude/settings.local.json:18-20 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용은 임의 원격/브랜치 인자 허용. `git pull origin *` 등 더 좁은 패턴 권장\n- [Low] .claude/settings.local.json:20 — `mcp__codex__codex` 전체 허용; 도구별 세분화 가능하면 권장\n- [Info] data/skill-usage.jsonl, skill-eval-report.json, skills/registry.yaml — 런타임 산출물/상태 파일 다수 커밋. .gitignore 정책 재확인 권장 (이전 정책상 일부는 추적 외 대상일 수 있음)\n- [Info] syncCompyne/*, projects/global_hoon_main/.../session_cursor.json — diff 본문이 잘려 미검토. 별도 검토 필요\n- 결론: 차단 결함 없음. EOF 개행 + 훅 매처 정합성만 확인 후 머지 가능."}

---

## 2026-04-29 18:58 — `2026-04-14-build-diet` (7fbf1b93)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Low] .claude/settings.local.json:133 — 파일 끝 개행 누락 (`No newline at end of file`)
- [Info] .claude/settings.local.json:48-72 — UserPromptSubmit 훅 실행 순서 재배치(`cli_hook_bridge`가 마지막으로 이동). `check_pending_review.py`/`check_design_pending.py`가 먼저 실행되도록 의도된 변경인지 확인 필요. 이전엔 resume_brief 컨텍스트 주입이 먼저였음
- [Info] .claude/settings.local.json:18 — `Bash(git pull *)`/`Bash(git stash *)` 와일드카드 권한 추가는 stash drop·pull --rebase 등 부수효과 있는 변형도 통과시킴. 좁힐 여지 있음
- [Info] .claude/settings.local.json:20 — `mcp__codex__codex` MCP 호출 자동 허용. 외부 모델 호출 비용·로그 영향 검토 권장
- [Info] data/skill-usage.jsonl — 윈도우 워크트리에서 `/Users/hoon/...` macOS 경로의 promotion 이벤트가 추가됨. 다른 머신에서 흘러온 동기화 데이터인지 확인(섞이면 path 추적 혼선)

나머지 파일(syncCompyne/*, registry.yaml, code-review.md, session_cursor.json 등)은 diff가 잘려 본문이 보이지 않아 별도 검토하지 못했습니다.

---

## 2026-04-29 18:58 — `2026-04-14-build-diet` (f73c9809)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- [Low] .claude/settings.local.json:133 — 파일 끝에 newline 누락 (`\ No newline at end of file`). POSIX 규약 위반, 일부 도구에서 마지막 줄 처리 이슈 가능.
- [Info] .claude/settings.local.json:18-20 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 권한 추가. `git pull --force` 같은 인자도 허용되므로 의도된 범위인지 확인 필요.
- [Info] .claude/settings.local.json:55-72 — UserPromptSubmit hook 순서가 재배치됨 (cli_hook_bridge가 마지막으로 이동). 다른 hook들이 먼저 실행되어 컨텍스트를 prepend하는 동작에 의존하지 않는지 확인 필요.
- [Info] .claude/settings.local.json — hook `name` 필드 추가는 진단/로깅 목적으로 적절. SessionStart/PreCompact/Stop/SessionEnd 5개 hook에 일관되게 부여됨.
- [Info] data/skill-usage.jsonl, skills/new_skill/* — append-only 텔레메트리 및 평가 리포트 갱신. 코드 변경 없음.
- [Info] projects/global_hoon_main/data/memory/*/session_cursor.json — 런타임 상태 파일. 리뷰 대상 아님.
- [Info] syncCompyne/* 변경분은 diff에 포함되지 않아 평가 불가.

---

## 2026-04-29 18:59 — `2026-04-14-build-diet` (c91cf342)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:18-20 — `Bash(git pull *)` / `Bash(git stash *)` 와일드카드 허용은 임의 원격에서 pull 가능. 원격을 origin 등으로 한정 권장.",
    "- [Medium] .claude/settings.local.json:52-71 — UserPromptSubmit 훅 실행 순서가 변경됨(cli_hook_bridge가 마지막으로 이동). check_pending_review/check_design_pending이 먼저 실행되어 brief 생성 전 큐 검사를 하게 되는데, cli_hook_bridge가 만드는 resume_brief에 의존하는 후속 훅이 없는지 확인 필요.",
    "- [Low] .claude/settings.local.json:133 — `No newline at end of file`. POSIX 규약상 EOL 추가 권장.",
    "- [Info] hooks에 `name` 필드 일관 추가는 식별/디버깅에 도움 — 좋음.",
    "- [Info] diff가 일부 잘려 syncCompyne/*.py, memory_store.py, project_log_cli.py, workspace_context_cli.py 변경 내용은 확인 불가 — 별도 리뷰 필요."
  ]
}
```

---

## 2026-04-29 18:59 — `2026-04-14-build-diet` (2447d7bd)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [Medium] .claude/settings.local.json:55-72 — Hook 명령이 이벤트 간에 회전(rotation)되어 어떤 이벤트가 어떤 스크립트를 트리거하는지 의도와 일치하는지 검증 필요. 기존: UserPromptSubmit→cli_hook_bridge, 추가 이벤트→check_pending_review→check_design_pending. 변경 후: →check_pending_review→check_design_pending→cli_hook_bridge로 한 칸씩 밀림. 이벤트 타입 키가 diff에 가려져 있어 의도된 매핑인지 확인 필요.",
    "- [Low] .claude/settings.local.json:130 — `\\ No newline at end of file` — 파일 끝 개행 누락. JSON 자체는 유효하나 POSIX 관례 위반, 일부 도구가 마지막 라인 처리에서 경고.",
    "- [Low] .claude/settings.local.json:18-19 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 허용. `git pull origin main --force` 같은 위험 변형도 통과. 더 좁은 패턴(`git pull`, `git stash push -m *`) 권장.",
    "- [Info] .claude/settings.local.json:20 — `mcp__codex__codex` MCP 호출 무조건 허용 — Codex로의 외부 LLM 호출 게이트가 사라짐. 의도된 정책이면 OK.",
    "- [Info] data/skill-usage.jsonl, projects/.../session_cursor.json, skill-eval-report.json — 런타임 산출물(런 ID/타임스탬프)이 커밋에 포함됨. .gitignore 후보."
  ]
}
```

---

## 2026-04-29 19:00 — `2026-04-14-build-diet` (7342b1af)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

{
  "review": [
    "- [Low] .claude/settings.local.json:133 — 파일 끝 개행 누락 (\\ No newline at end of file). POSIX 텍스트 파일 규약 위반, 일부 도구가 마지막 줄을 누락 처리할 수 있음.",
    "- [Medium] .claude/settings.local.json:18-20 — `Bash(git pull *)`, `Bash(git stash *)` 와일드카드 권한 추가. `git pull origin malicious-branch` 등 임의 인자 실행을 자동 승인하므로 권한 범위가 넓음. 필요한 형태(`git pull`, `git stash`, `git stash pop`)로 좁히는 편이 안전.",
    "- [Medium] .claude/settings.local.json:55-72 — UserPromptSubmit 훅 순서가 [cli_hook_bridge → check_pending_review → check_design_pending] 에서 [check_pending_review → check_design_pending → cli_hook_bridge] 로 재배치됨. 기존에 cli_hook_bridge가 먼저 실행되어 세션 컨텍스트를 갱신한 뒤 review 검사를 했다면, 이번 변경으로 review 검사가 stale state를 보게 될 가능성. 의도된 재배치인지 PR 본문에 근거 명시 필요.",
    "- [Low] .claude/settings.local.json:21 — `mcp__codex__codex` allow 추가. MCP 서버 호출이 자동 허용되므로 외부 도구 호출 권한 확대. 의도 확인 권장.",
    "- [Info] data/skill-usage.jsonl — append-only 이벤트 로그. 변경 정합성 OK.",
    "- [Info] 기타 상태 파일(skill-eval-report.json, session_cursor.json 등) — 자동 생성 산출물, 리뷰 대상 아님."
  ]
}

---

## 2026-04-29 19:01 — `2026-04-14-build-diet` (99f81b67)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[Medium]** `.claude/settings.local.json:~8` — `"Bash(git pull *)"` and `"Bash(git stash *)"` wildcards are overly broad; allows pulling from arbitrary remotes/refspecs, which could silently overwrite local state or inject unexpected code.

- **[Medium]** `.claude/settings.local.json` hook rotation — UserPromptSubmit hook was `hook_runner.py cli_hook_bridge`, now `check_pending_review.py`; the bridge that syncs session state is pushed down to a later slot. If hook execution order matters for continuity (cursor/session state must be written before prompt handling), this reordering may cause stale-state reads.

- **[Low]** `data/skill-usage.jsonl` — hardcoded Mac path `/Users/hoon/workTree/agent-factory/` in `report_path`/`promotion_path` fields. This file is committed to the repo and will produce broken references on Windows. Paths should be relative or runtime-resolved.

- **[Low]** `.claude/settings.local.json` — trailing newline removed (last line). Minor, but breaks POSIX file convention and may cause diff noise in future patches.

- **[Info]** `projects/.../session_cursor.json`, `skill-eval-report.json`, `skill-promotion.json`, `skills/registry.yaml` — runtime/auto-generated state files committed alongside config changes. These should ideally be in `.gitignore` or a separate data commit to keep config diffs readable.

- **[Info]** `syncCompyne/*.py` and `syncCompyne/*.md` diffs not shown (truncated) — cannot review those files.

---

## 2026-04-29 19:02 — `2026-04-14-build-diet` (0ef3cfc3)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:52–68 — Hook 순환 교체: cli_hook_bridge(세션 연속성)가 SessionStart에서 제거되어 StopTurn으로 이동됨. 세션 시작 시 resume_brief 컨텍스트가 주입되지 않아 NEXT_STEPS 기반 작업 재개 불가.",
    "- [High] .claude/settings.local.json:60 — UserPromptSubmit에 check_design_pending.py가 배정됐으나 SessionStart에는 check_pending_review.py가 배정됨. 두 훅의 의도된 트리거 이벤트가 뒤바뀐 상태 — 설계 큐 검사가 프롬프트 제출 시점에 실행되어야 하는데 세션 시작 시 실행됨.",
    "- [Medium] .claude/settings.local.json:17 — 'Bash(git stash *)' 와일드카드 허용. git stash drop / git stash clear 등 비복구성 삭제 명령 포함됨. Destructive Action Guard 정책과 충돌.",
    "- [Low] .claude/settings.local.json:19 — 'Bash(npm list *)' 추가. 읽기 전용이나 node_modules 대형 트리 출력 시 컨텍스트 낭비 가능. head 제한 없음.",
    "- [Info] data/skill-usage.jsonl — 경로 D:\\\\warkSpaces(오타, workSpaces가 아님)는 이전 항목부터 이어진 레거시이므로 신규 항목 문제 아님. 다만 경로 정규화 미적용 상태.",
    "- [Info] 나머지 파일(syncCompyne/*, session_cursor.json, registry.yaml)은 diff 미포함 — 평가 불가."
  ],
  "summary": "핵심 결함: 세션 연속성 훅(cli_hook_bridge)이 SessionStart에서 탈락하여 재개 컨텍스트 단절. git stash 와일드카드 허용은 Destructive Action Guard 위반 소지. 나머지는 낮음/정보 수준."
}
```

---

## 2026-04-29 19:02 — `2026-04-14-build-diet` (f193e1f9)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[High]** `.claude/settings.local.json:53-72` — Hook slot rotation is suspect. The diff swaps which script occupies which event slot: `UserPromptSubmit` now runs `check_pending_review.py`, the previous `check_pending_review.py` slot becomes `check_design_pending.py`, and `hook_runner.py cli_hook_bridge` (named `agent_factory_claude_userpromptsubmit`) lands in the 4th slot. If hook-to-event binding is positional (array index per event type), `hook_runner.py` may now fire on the wrong lifecycle event, silently breaking session continuity.

- **[Medium]** `.claude/settings.local.json:16-17` — `"Bash(git pull *)"` and `"Bash(git stash *)"` added to the allowlist without remote or ref constraints. These can pull from arbitrary remotes or silently discard/restore uncommitted work, expanding the blast radius of any prompt injection that crafts a git command.

- **[Low]** `data/skill-usage.jsonl` — Hardcoded macOS paths (`/Users/hoon/workTree/agent-factory/skills/...`) committed from a previous machine. `report_path` / `promotion_path` values in these log entries are permanently stale and will break any downstream reader that resolves them.

- **[Low]** `.claude/settings.local.json:131` — Missing newline at EOF (cosmetic but causes noisy diffs).

---

## 2026-04-29 19:03 — `2026-04-14-build-diet` (aed0f172)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

---

- **[High]** `.claude/settings.local.json:15-18` — `Bash(git pull *)` 와일드카드 허용은 remote URL 범위를 제한하지 않아 `.git/config` 에 악의적 remote가 추가된 경우 임의 origin에서 pull 가능. `Bash(git pull origin *)` 등 특정 remote로 제한 권장.

- **[Medium]** `.claude/settings.local.json:51-77` — `UserPromptSubmit` 에 hook 3개가 모두 등록됨 (`check_pending_review.py`, `check_design_pending.py`, `hook_runner.py bridge`). 브릿지가 리뷰 스크립트보다 **뒤에** 실행되므로, 리뷰 스크립트가 `[af-review-pending]` 출력 → Claude가 반응 → 브릿지 hook 아직 실행 전인 타이밍 경합 가능성. 브릿지를 첫 번째 항목으로 이동 고려.

- **[Medium]** `.claude/settings.local.json:18` — `mcp__codex__codex` allow 추가 시 파라미터 범위 제한 없음. MCP 툴은 allow 패턴으로 인자 스코핑이 불가능하므로, 의도된 허용 범위를 주석이나 문서로 명시 필요.

- **[Low]** `.claude/settings.local.json:18` — `Bash(npm list *)` 허용이 추가됨. 읽기 전용 목적이라면 문제없으나 `npm list` 는 `node_modules` 트리 탐색으로 느릴 수 있어 hook 내 timeout 초과 유발 가능.

- **[Low]** `.claude/settings.local.json:131` — 파일 끝 개행(newline) 누락. `\ No newline at end of file` — POSIX 표준 위반, 일부 JSON 파서에서 경고 발생.

- **[Info]** `.claude/settings.local.json` — 각 hook에 `name` 필드 추가는 디버그 가시성 향상에 유효. 단, `check_pending_review.py` / `check_design_pending.py` 두 hook에는 name이 없으므로 일관성을 위해 추가 권장.

- **[Info]** `data/skill-usage.jsonl`, `skill-eval-report.json` — append-only 이벤트 로그, 코드 리스크 없음.

---

## 2026-04-29 19:04 — `2026-04-14-build-diet` (9b229000)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[High]** `.claude/settings.local.json:16` — `"Bash(git stash *)"` allowlist은 `git stash drop *`, `git stash clear` 등 비가역적 작업을 포함. Destructive Action Guard 정책 위반 가능성.
- **[Medium]** `.claude/settings.local.json:15` — `"Bash(git pull *)"` 와일드카드는 임의 remote URL로의 pull을 허용 (`git pull <malicious-url>`). 허용 범위 과도함.
- **[Medium]** `.claude/settings.local.json:53-69` — UserPromptSubmit 훅 순서가 `hook_runner → check_pending → check_design` 에서 `check_pending → check_design → hook_runner` 로 역전됨. `hook_runner`가 컨텍스트 주입 역할이라면 **후행** 실행은 resume_brief가 프롬프트에 도달하지 않음.
- **[Low]** `data/skill-usage.jsonl:11` — `report_path`/`promotion_path`에 맥OS 절대경로 `/Users/hoon/workTree/` 하드코딩. Windows 환경 `D:/hoonProJect/worktrees/`와 불일치 — 경로 의존 코드 실행 시 FileNotFound.
- **[Low]** `.claude/settings.local.json` EOF — `\ No newline at end of file`. JSON 파서는 허용하지만 git diff 노이즈 발생.
- **[Info]** 훅에 `name` 필드 추가는 디버그 가시성 향상으로 긍정적.

**요약**: `git stash *` 허용 범위 축소(`git stash list`, `git stash show`만 허용 권장) 및 UserPromptSubmit 훅 실행 순서 의도 재확인 필요.

---

## 2026-04-29 19:05 — `2026-04-14-build-diet` (0ea37b41)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[Medium]** `.claude/settings.local.json:53–65` — Hook 이벤트 재배치: `check_pending_review.py`와 `check_design_pending.py`가 서로 다른 이벤트 슬롯으로 이동됨. 어떤 이벤트(UserPromptSubmit vs PostToolUse)에 연결되는지 context 없이는 파이프라인 발화 순서가 의도대로인지 확인 불가 — 실제 훅 이벤트 타입 레이블을 diff에서 확인 필요.

- **[Medium]** `.claude/settings.local.json:line ~15` — `Bash(git stash *)` 와일드카드 허용: `git stash drop`·`git stash clear` 같은 파괴적 서브커맨드도 무프롬프트 허용됨. `git stash list`, `git stash push` 등 필요한 서브커맨드만 열거하는 방식으로 좁혀야 함.

- **[Medium]** `.claude/settings.local.json:line ~15` — `Bash(git pull *)` 와일드카드: `git pull --force`, `git pull --rebase --force` 등도 허용범위에 포함됨. 허용 범위를 `git pull origin *` 수준으로 제한하거나 별도 deny 규칙 추가 권장.

- **[Low]** `data/skill-usage.jsonl` — macOS 절대경로 `/Users/hoon/workTree/agent-factory/` 하드코딩: Windows 워크스페이스(`D:/hoonProJect/worktrees/`) 와 불일치. 다른 PC 재개 시 `report_path`·`promotion_path` 참조 실패 가능.

- **[Low]** `.claude/settings.local.json:EOF` — 파일 끝 개행 누락(`\ No newline at end of file`). 일부 JSON 파서·git diff 툴에서 경고 발생.

- **[Info]** 훅에 `name` 필드 추가(`agent_factory_claude_sessionstart` 등) — 디버깅 추적성 향상, 올바른 방향.

---

## 2026-04-29 19:05 — `2026-04-14-build-diet` (9f90a839)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:53 — PostToolUse hook now runs check_pending_review.py instead of hook_runner.py; if PostToolUse was previously the only hook_runner call for that event, session continuity bridge may silently drop for tool-use events.",
    "- [Medium] .claude/settings.local.json:allow — 'Bash(git stash *)' is broad; wildcard allows 'git stash drop'/'git stash clear' which are destructive. Should be scoped to 'git stash push *' or 'git stash list' only.",
    "- [Medium] .claude/settings.local.json:allow — 'mcp__codex__codex' added without scope restriction; grants full Codex MCP tool access from the allowlist. Intentional but worth confirming scope is acceptable.",
    "- [Low] .claude/settings.local.json — Missing newline at EOF (diff shows removal of final newline). Minor but can cause noisy diffs and some JSON tooling warnings.",
    "- [Info] .claude/settings.local.json — Hook name fields added (agent_factory_claude_*) improve traceability in logs. Positive change.",
    "- [Info] data/skill-usage.jsonl — Append-only log entries; no structural issues. historical_score=52 with contract_pass_rate=0.0 in new entries; verify this is expected for the candidate stage.",
    "No issues found in syncCompyne/* or session cursor JSON files from the visible diff."
  ]
}
```

---

## 2026-04-29 19:06 — `2026-04-14-build-diet` (a9e7c8e0)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[Medium]** `.claude/settings.local.json:43-46` — `"Bash(git pull *)"` and `"Bash(git stash *)"` wildcards in the allowlist permit pulling from any remote/ref and stashing without confirmation. A buggy hook could silently overwrite local uncommitted work.

- **[Medium]** `.claude/settings.local.json:53-70` — Hook execution order for `UserPromptSubmit` was reshuffled: `cli_hook_bridge` (session-state init) now fires **last** instead of first. If `check_pending_review.py` or `check_design_pending.py` depend on bridge-initialized session state, they will silently operate on stale/uninitialized context.

- **[Low]** `.claude/settings.local.json:131` — File ends without a trailing newline (`-}` → `+}\ No newline at end of file`). JSON parsers tolerate this but it breaks `diff`/`patch` tooling cleanly.

- **[Low]** `data/skill-usage.jsonl` — Appended entries contain hardcoded Mac paths (`/Users/hoon/workTree/...`) in `report_path` and `promotion_path` fields. On this Windows workspace those paths are unresolvable; any tooling that re-reads these fields to load artifacts will silently fail.

- **[Info]** `data/skill-usage.jsonl` — `contract_pass_rate`, `hidden_pass_rate`, `runtime_success_rate` all `0.0` yet stage promoted to `candidate`. Verify the promotion threshold logic actually gates on non-zero pass rates before `active` promotion.

---

## 2026-04-29 19:07 — `2026-04-14-build-diet` (74f83133)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```json
{
  "review": [
    "- [High] .claude/settings.local.json:53 — Hook 순서 로테이션: UserPromptSubmit 이벤트 블록의 hook_runner.py(브리지)가 check_pending_review.py → check_design_pending.py 이후로 밀렸음. 브리지 상태가 확립되기 전에 check 스크립트가 실행되면 stale 상태로 동작하거나 KeyError로 silent-fail 가능.",
    "- [Medium] .claude/settings.local.json:16 — 'Bash(git pull *)' 허용 추가: remote/branch 무제한 허용. 악성 remote가 등록된 환경에서 자동 pull이 코드 주입 경로가 됨. 'Bash(git pull origin main)' 등 구체적 패턴으로 제한 권장.",
    "- [Medium] .claude/settings.local.json:18 — 'mcp__codex__codex' 를 allowlist에 추가했지만 인자 패턴 제한 없음. 임의 codex 명령 실행이 허용됨. 필요한 최소 scope로 제한할 것.",
    "- [Low] .claude/settings.local.json:131 — 파일 끝 개행 누락(no newline at EOF). JSON 파서에 따라 문제없지만, git diff 노이즈 유발.",
    "- [Low] data/skill-usage.jsonl — 잘린 줄(truncated line) 확인됨. append-only 로그로 보이나 파싱 시 JSONDecodeError 발생 가능. 마지막 줄 완전성 검증 로직 필요.",
    "- [Info] .claude/settings.local.json — SessionStart·PreCompact·Stop·SessionEnd 훅에 name 필드 추가: 가시성 개선, 문제 없음."
  ]
}
```

**요약**: 가장 위험한 부분은 훅 실행 순서 로테이션(High)과 `git pull *` 무제한 허용(Medium) 두 가지입니다. 브리지 훅이 check 스크립트보다 먼저 실행되도록 순서를 복원하고, git pull 패턴을 구체화하는 것을 권장합니다.

---

## 2026-04-29 19:08 — `2026-04-14-build-diet` (23a828ef)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

```
- [High]   .claude/settings.local.json — "Bash(git stash *)" 와일드카드 허용은 `git stash drop`·`git stash clear` 같은 파괴적 하위 명령까지 포함. 허용 범위를 `git stash list`, `git stash push` 등 개별 명령으로 좁혀야 함.
- [Medium] .claude/settings.local.json — "Bash(git pull *)" 허용 시 임의 원격 URL 지정 가능(git pull <attacker-url> main). 허용 범위를 `git pull origin *` 또는 명시적 remote로 한정 권장.
- [Medium] data/skill-usage.jsonl — report_path·promotion_path 값이 macOS 절대경로(/Users/hoon/workTree/...)로 하드코딩됨. 현재 작업 환경(D:\hoonProJect\worktrees\)에서는 경로 불일치로 이벤트 추적 단절 가능.
- [Low]    .claude/settings.local.json — UserPromptSubmit 이벤트에 hook이 2개(check_pending_review.py + hook_runner.py cli_hook_bridge) 등록됨. 실행 순서·중복 트리거 의도가 주석·name 필드 없이 불명확.
- [Low]    .claude/settings.local.json — 파일 끝 개행 제거(no newline at EOF). POSIX 표준 위반이며 git diff 노이즈 유발.
- [Info]   .claude/settings.local.json — hook name 필드(`agent_factory_claude_*`) 추가로 디버그 가독성 향상 — 긍정적 변경.
```

---

## 2026-04-29 19:08 — `2026-04-14-build-diet` (fa28acf3)

**Context**: feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — 3-Tier 검증 통과

**Changed (16)**: `.claude/settings.local.json, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py ... (+1)`

### Findings

- **[High]** `.claude/settings.local.json:16` — `"Bash(git stash *)"` added to allowlist without restriction. Automated hooks triggering `git stash` can silently discard uncommitted work; scope to a safer pattern like `Bash(git stash list)` or remove entirely.
- **[Medium]** `.claude/settings.local.json:69–72` — Hook ordering inversion: `cli_hook_bridge` (now named `agent_factory_claude_userpromptsubmit`) moved to 4th position in the UserPromptSubmit chain, running *after* `check_pending_review.py` and `check_design_pending.py`. If the bridge emits `[af-review-pending]`/`[af-design-review-pending]` signals those scripts depend on, the ordering dependency is now broken.
- **[Medium]** `.claude/settings.local.json:18` — `"mcp__codex__codex"` added to global allowlist with no scope qualifier. This permits unrestricted Codex MCP calls from any context; verify this is intentional and not overly permissive.
- **[Low]** `.claude/settings.local.json:131` — Missing newline at EOF. Not functional but violates POSIX and can cause diff noise in future patches.
- **[Info]** `data/skill-usage.jsonl` — Diff is truncated; new entries reference macOS path `/Users/hoon/workTree/...` while the primary workspace is `D:/hoonProJect/worktrees/...`. Cross-machine path inconsistency in event records may break tooling that reads `report_path`/`promotion_path` fields.
- **[Info]** `syncCompyne/*.py` — Listed as changed but diff is not included. Cannot assess for bugs or security issues without the content.

---

## 2026-04-29 22:51 — `2026-04-14-build-diet` (b23ed4c3)

**Context**: edit: /Users/hoon/workTree/agent-factory/scripts/cli_hook_bridge.py

**Changed (9)**: `.claude/settings.local.json, .gitignore, projects/global_hoon_main/data/memory/general/claude_chat/user_you_are_an_independent_design_document_critic_for_the_agent_factory_projectyour_job_is_to_find_problems_before_impl_41bfa7a6eaa6_20260409_054107_412648.json, projects/global_hoon_main/data/memory/general/claude_chat/user_you_are_an_independent_design_document_critic_for_the_agent_factory_projectyour_job_is_to_find_problems_before_impl_41bfa7a6eaa6_20260422_045634_746431.json, projects/global_hoon_main/data/memory/general/claude_chat/user_you_are_an_independent_design_document_critic_for_the_agent_factory_projectyour_job_is_to_find_problems_before_impl_e93551d557d5_20260409_054107_343939.json, projects/global_hoon_main/data/memory/general/claude_chat/user_you_are_an_independent_design_document_critic_for_the_agent_factory_projectyour_job_is_to_find_problems_before_impl_e93551d557d5_20260422_045634_692606.json, projects/global_hoon_main/data/memory/general/claude_chat/user_your_task_is_to_create_a_detailed_summary_of_the_conversation_so_far_paying_close_attention_to_the_users_explicit_r_dfef392e9ae6_20260409_054107_281213.json, projects/global_hoon_main/data/memory/general/claude_chat/user_your_task_is_to_create_a_detailed_summary_of_the_conversation_so_far_paying_close_attention_to_the_users_explicit_r_dfef392e9ae6_20260422_045634_633539.json, scripts/cli_hook_bridge.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-30 08:09 — `2026-04-14-build-diet` (6566c459)

**Context**: edit: /Users/hoon/workTree/agent-factory/scripts/blast_radius.py

**Changed (2)**: `.claude/settings.local.json, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-04-30 08:51 — `2026-04-14-build-diet` (bee4f070)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/provider_detect.py

**Changed (3)**: `.claude/settings.local.json, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-03 01:18 — `2026-04-14-build-diet` (aac4a784)

**Context**: edit: /Users/hoon/workTree/agent-factory/scripts/review_metrics_logger.py

**Changed (1634)**: `.claude/settings.local.json, .claude/settings.local.template.json, AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md ... (+1619)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-03 09:50 — `2026-04-14-build-diet` (d4cfa9c2)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/web_search.py

**Changed (1634)**: `.claude/settings.local.json, AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml ... (+1619)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-03 17:03 — `2026-04-14-build-diet` (e4feb4e2)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/claim_tracer.py

**Changed (1639)**: `.claude/settings.local.json, AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml ... (+1624)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-05 00:16 — `2026-04-14-build-diet` (5bf0d569)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/researcher.py

**Changed (81)**: `core/researcher.py, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/general/codex_chat/user_codexcmd_login_device_auth_d48548877be8_20260309_143912_905644.json, projects/global_hoon_main/data/memory/general/codex_chat/user_codexcmd_login_device_auth_df29ab435e3f_20260309_143912_925347.json, projects/global_hoon_main/data/memory/general/codex_chat/user_codexcmd_login_device_auth_ebef098f877b_20260309_143912_911019.json, projects/global_hoon_main/data/memory/general/codex_chat/user_cqa_tree_942d1248d0a7_20260309_094922_965871.json, projects/global_hoon_main/data/memory/general/codex_chat/user_cqa_tree_v011pdf_264f7746d448_20260309_094922_955897.json, projects/global_hoon_main/data/memory/general/codex_chat/user_d44fd61b2a1b_20260310_060825_393822.json, projects/global_hoon_main/data/memory/general/codex_chat/user_d70d9e21d013_20260310_174038_011170.json, projects/global_hoon_main/data/memory/general/codex_chat/user_d93d28d31b50_20260309_150354_746159.json, projects/global_hoon_main/data/memory/general/codex_chat/user_db6527603453_20260310_060825_408001.json, projects/global_hoon_main/data/memory/general/codex_chat/user_dcdd80eaeb0f_20260310_174037_955074.json, projects/global_hoon_main/data/memory/general/codex_chat/user_dcea84b69730_20260310_174037_946123.json, projects/global_hoon_main/data/memory/general/codex_chat/user_dd164aa85d51_20260310_060825_413797.json ... (+66)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-05 09:06 — `2026-04-14-build-diet` (376c6eee)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/research_router.py

**Changed (82)**: `core/research_router.py, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/general/codex_chat/user_codexcmd_login_device_auth_d48548877be8_20260309_143912_905644.json, projects/global_hoon_main/data/memory/general/codex_chat/user_codexcmd_login_device_auth_df29ab435e3f_20260309_143912_925347.json, projects/global_hoon_main/data/memory/general/codex_chat/user_codexcmd_login_device_auth_ebef098f877b_20260309_143912_911019.json, projects/global_hoon_main/data/memory/general/codex_chat/user_cqa_tree_942d1248d0a7_20260309_094922_965871.json, projects/global_hoon_main/data/memory/general/codex_chat/user_cqa_tree_v011pdf_264f7746d448_20260309_094922_955897.json, projects/global_hoon_main/data/memory/general/codex_chat/user_d44fd61b2a1b_20260310_060825_393822.json, projects/global_hoon_main/data/memory/general/codex_chat/user_d70d9e21d013_20260310_174038_011170.json, projects/global_hoon_main/data/memory/general/codex_chat/user_d93d28d31b50_20260309_150354_746159.json, projects/global_hoon_main/data/memory/general/codex_chat/user_db6527603453_20260310_060825_408001.json, projects/global_hoon_main/data/memory/general/codex_chat/user_dcdd80eaeb0f_20260310_174037_955074.json, projects/global_hoon_main/data/memory/general/codex_chat/user_dcea84b69730_20260310_174037_946123.json ... (+67)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-06 15:09 — `2026-04-14-build-diet` (5d020004)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\core\researcher.py

**Changed (5)**: `core/researcher.py, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/general/codex_chat/user_taskyou_are_a_senior_code_reviewer_review_the_following_changes_conciselytask_contextexecute_taskchanged_files_9cla_5cd8519161b9_20260409_024321_002878.json, projects/global_hoon_main/data/memory/general/codex_chat/user_taskyou_are_a_senior_code_reviewer_review_the_following_changes_conciselytask_contextreturn_agent_factory_okchanged_5123b91fc595_20260409_024321_007650.json`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-06 16:37 — `2026-04-14-build-diet` (808d072d)

**Context**: feat(researcher): P1 B1~B5 — Quality Gate + Evidence (RecoverySearchLoop + Coverage)

**Changed (5)**: `docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/general/codex_chat/user_taskyou_are_a_senior_code_reviewer_review_the_following_changes_conciselytask_contextexecute_taskchanged_files_9cla_5cd8519161b9_20260409_024321_002878.json, projects/global_hoon_main/data/memory/general/codex_chat/user_taskyou_are_a_senior_code_reviewer_review_the_following_changes_conciselytask_contextreturn_agent_factory_okchanged_5123b91fc595_20260409_024321_007650.json`

### Findings

```json
{
  "summary": "변경 파일 5개 모두 비코드(문서·세션 상태 JSON). 실제 researcher.py 변경분은 이 diff에 포함되지 않음.",
  "findings": [
    {
      "severity": "Info",
      "location": "projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json",
      "note": "Mac 절대경로 → Windows 절대경로 교체. PC 이관 정상 반영."
    },
    {
      "severity": "Info",
      "location": "projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json",
      "note": "동일 — Mac→Windows 경로 이관. written_last_run 0 리셋도 의도된 것으로 보임."
    },
    {
      "severity": "Medium",
      "location": "docs/code_review/code-review.md:3955",
      "note": "커밋 메시지 컨텍스트는 'feat(researcher): P1 B1~B5'이나 리뷰 엔트리에는 'edit: researcher.py'만 기록됨. --no-llm 스킵 사유가 남아 실제 리뷰 내용 없음 — Quality Gate 통과 증거 미흡."
    },
    {
      "severity": "Low",
      "location": "session_cursor.json (양쪽)",
      "note": "하드코딩 절대경로가 버전관리됨. 환경 이식성 문제 — 경로를 env-var 또는 상대 경로로 교체 검토 권장."
    }
  ],
  "verdict": "이 diff 자체의 보안·버그 리스크는 없음. 단, 커밋 제목이 시사하는 researcher.py 핵심 변경분(RecoverySearchLoop·Coverage)이 diff에 빠져 있어 실질 검토 불가 — 해당 파일이 포함된 별도 커밋 리뷰 필요."
}
```

---

## 2026-05-06 17:10 — `2026-04-14-build-diet` (ee0f9d54)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\core\researcher.py

**Changed (6)**: `core/researcher.py, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/general/codex_chat/user_taskyou_are_a_senior_code_reviewer_review_the_following_changes_conciselytask_contextexecute_taskchanged_files_9cla_5cd8519161b9_20260409_024321_002878.json, projects/global_hoon_main/data/memory/general/codex_chat/user_taskyou_are_a_senior_code_reviewer_review_the_following_changes_conciselytask_contextreturn_agent_factory_okchanged_5123b91fc595_20260409_024321_007650.json`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 00:06 — `2026-04-14-build-diet` (deb9d43b)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py

**Changed (3)**: `core/project_pipeline.py, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 00:36 — `2026-04-14-build-diet` (a7b91646)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/work_item_generator.py

**Changed (9)**: `core/work_item_generator.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 02:22 — `2026-04-14-build-diet` (87dcf487)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py

**Changed (9)**: `core/project_pipeline.py, data/skill-usage.jsonl, docs/code_review/code-review.md, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 15:18 — `2026-04-14-build-diet` (0ecf54a9)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/researcher.py

**Changed (8)**: `core/researcher.py, data/skill-usage.jsonl, projects/global_hoon_main/data/memory/claude/_bridge_state/session_cursor.json, projects/global_hoon_main/data/memory/codex/_bridge_state/session_cursor.json, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 16:41 — `2026-05-07-memory-gitignore-cleanup` (21265c53)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\run_factory_cli.py

**Changed (1)**: `run_factory_cli.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 17:12 — `2026-05-07-memory-gitignore-cleanup` (19c95f6f)

**Context**: fix(research_router): P3 D3c — _detect_domain substring 매칭 + 홀덤 토큰 추가

**Changed (1)**: `docs/code_review/code-review.md`

### Findings

No issues found.

The diff is a documentation-only append to `code-review.md` — a skipped-review log entry with no code logic, security surface, or error handling to evaluate.

---

## 2026-05-07 17:58 — `2026-05-07-memory-gitignore-cleanup` (106f8f3a)

**Context**: feat(research): P4 QualityContract — WorkSpec + pack layers + ChecklistMerger

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- **Medium** `data/skill-usage.jsonl:21-23` — 신규 항목의 `report_path`/`promotion_path`가 Windows 절대 경로(`D:\\hoonProJect\\...`)로 하드코딩됨. 이전 항목들은 Unix 경로(`/Users/hoon/...`). 경로가 머신 종속적이어서 다른 PC에서 재현 불가.
- **Medium** `data/skill-usage.jsonl` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0`인 상태에서 `draft → candidate` 프로모션이 반복 발생(이벤트 #18~22). 평가 지표가 전부 0인데도 `external_eval_passed` 사유로 승격되는 것은 프로모션 게이트 로직 결함 가능성.
- **Low** `data/skill-usage.jsonl` — `feedback_total_events`만 18→22로 증가하고 `historical_score`는 52에서 고정. 동일 조건으로 동일 결과를 반복 기록하는 중복 이벤트로 보임 — 이벤트 중복 방지(idempotency) 체크 부재.
- **Low** `data/skill-usage.jsonl:23` — diff 마지막 줄이 잘려 있음(`"installable": false,` 이후 누락). 파일이 JSON Lines 형식이므로 불완전 행이 파서 오류를 유발할 수 있음.
- **Info** `docs/code_review/code-review.md`, `skill-eval-report.json` 등 — diff 내용 미제공으로 해당 파일은 검토 불가.

**요약**: 핵심 우려는 하드코딩 경로(머신 종속)와 평가 지표 전부 0인 상태에서의 반복 프로모션이다. 프로모션 게이트가 실제 pass rate를 검사하고 있는지 확인 필요.

---

## 2026-05-07 17:59 — `2026-05-07-memory-gitignore-cleanup` (f347451b)

**Context**: feat(research): P4 QualityContract — WorkSpec + pack layers + ChecklistMerger

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- **[High]** `data/skill-usage.jsonl:21-23` — `report_path`/`promotion_path`에 하드코딩된 절대 경로 (`D:\\hoonProJect\\worktrees\\...`). 이전 항목은 macOS 경로(`/Users/hoon/...`), 신규 항목은 Windows 경로 — 머신 종속 경로가 영구 로그에 기록됨. 상대 경로 또는 경로 제거 필요.
- **[Medium]** `data/skill-usage.jsonl` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0`인 상태로 `draft → candidate` 승격이 반복됨. 평가 지표 전부 0인 스킬이 승격되는 것은 승격 게이트 로직 결함을 시사함.
- **[Medium]** `data/skill-usage.jsonl` — `historical_score: 52`가 이벤트 18~22 전 구간에서 동일. 점수가 피드백 누적에도 변하지 않으면 계산이 실제로 실행되지 않거나 고정값을 반환하는 것임.
- **[Low]** diff 마지막 줄이 잘림 — 파일 끝에 불완전한 JSON 라인이 있을 수 있음. 파싱 오류 위험.
- **[Info]** 나머지 6개 파일(docs/, skills/) diff 내용이 제공되지 않아 해당 파일은 검토 불가.

---

## 2026-05-07 17:59 — `2026-05-07-memory-gitignore-cleanup` (b2b2f0cd)

**Context**: feat(research): P4 QualityContract — WorkSpec + pack layers + ChecklistMerger

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [High] data/skill-usage.jsonl:22 — 신규 이벤트 2건의 report_path/promotion_path가 Windows 절대경로(D:\\\\hoonProJect\\\\...)로 하드코딩. 기존 항목은 Unix 경로(/Users/hoon/...). 경로가 머신 종속적으로 기록되면 다른 PC에서 경로 역참조 시 FileNotFoundError 발생.",
    "- [High] data/skill-usage.jsonl — contract_pass_rate=0.0, hidden_pass_rate=0.0, shadow_cases=0 상태에서 reason='external_eval_passed'로 candidate 승격. 평가 근거가 전무한 승격이 데이터 무결성 관점에서 잘못된 신호를 남김. 승격 조건 검증 로직 확인 필요.",
    "- [Medium] data/skill-usage.jsonl — 마지막 추가 항목이 diff에서 잘려 있음(truncated). 불완전한 JSON 행이 파일에 기록됐을 경우 JSONL 파서 에러 유발.",
    "- [Low] data/skill-usage.jsonl — feedback_total_events가 18→19→20→21→22로 단순 증가하는데 runtime_success_rate는 계속 0.0. 이벤트 카운터만 올라가고 실제 실행이 없다면 historical_score(52) 계산 기반 재검토 필요.",
    "- [Info] 변경된 7개 파일 중 5개(code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/*, skills/registry.yaml)는 diff에 포함되지 않아 내용 미검증."
  ]
}
```

---

## 2026-05-07 18:00 — `2026-05-07-memory-gitignore-cleanup` (f2bc00c6)

**Context**: feat(research): P4 QualityContract — WorkSpec + pack layers + ChecklistMerger

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [High] `data/skill-usage.jsonl:22-24` — 절대 경로(`D:\\hoonProJect\\worktrees\\...`)가 데이터 파일에 하드코딩되어 커밋됨. 기존 항목은 `/Users/hoon/...` macOS 경로. 머신 종속 경로가 버전 관리되면 다른 PC에서 경로 불일치 발생.
- [High] `data/skill-usage.jsonl` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0`, `runtime_success_rate: 0.0` 전부 0인데 `reason: "external_eval_passed"` + `recommended_stage: "candidate"` 로 승격. 평가 지표와 승격 판정이 모순됨.
- [Medium] `data/skill-usage.jsonl` — 동일 스킬(`new_skill`)이 `draft→candidate`로 이벤트 18~22회 반복 승격. 이미 `candidate`인데 `from_stage: draft`가 계속 기록 — 상태 머신 전환이 멱등하지 않거나 상태가 실제 반영되지 않음.
- [Medium] `data/skill-usage.jsonl` — `historical_score`가 18~22 이벤트 전체에 걸쳐 52로 고정. 반복 평가에도 점수 변화 없으면 평가 루프가 실제 실행되지 않는 것으로 의심.
- [Low] `data/skill-usage.jsonl` — `run_id: ""`, `agent_role: ""`가 모든 항목에 공란. 추적성 부재 — 어떤 실행에서 발생한 이벤트인지 식별 불가.

---

## 2026-05-07 18:00 — `2026-05-07-memory-gitignore-cleanup` (d47509c6)

**Context**: feat(research): P4 QualityContract — WorkSpec + pack layers + ChecklistMerger

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [High] `data/skill-usage.jsonl:22-24` — 신규 항목에 절대 OS 경로 하드코딩 (`D:\\hoonProJect\\worktrees\\...`). 이전 항목은 `/Users/hoon/...` 형태로, 기기 간 이식성 없는 경로가 로그에 영구 기록됨. `report_path`/`promotion_path`는 상대경로 또는 프로젝트 루트 기준 상대값으로 정규화해야 함.

- [Medium] `data/skill-usage.jsonl` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_success_rate: 0.0`인 상태에서 `reason: "external_eval_passed"`로 candidate 승격 반복. 승격 조건이 pass rate와 무관하게 작동하는지 확인 필요. `historical_score: 52` 단독으로 승격을 정당화하는 로직이 의도된 것인지 명시되지 않음.

- [Medium] `data/skill-usage.jsonl` — diff 마지막 항목이 잘린 채로 커밋됨 (`"installable": false,`에서 중단). JSONL 파일이 불완전한 JSON 행을 포함하면 파서 오류 발생.

- [Low] `data/skill-usage.jsonl` — `feedback_total_events`가 18→22로 증가하는 동안 `historical_score`가 52로 고정. 이벤트 누적이 점수에 반영되지 않으면 지표 의미 없음.

- [Info] `data/skill-usage.jsonl` — `run_id: ""`, `agent_role: ""`이 모든 항목에서 비어있음. 추적 목적의 필드라면 채워지지 않는 이유를 확인.

---

## 2026-05-07 18:01 — `2026-05-07-memory-gitignore-cleanup` (10c5879b)

**Context**: feat(research): P4 QualityContract — WorkSpec + pack layers + ChecklistMerger

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [High] data/skill-usage.jsonl:22 — report_path/promotion_path에 Windows 절대경로 하드코딩 (`D:\\hoonProJect\\...`). 이전 항목들은 Unix 경로(`/Users/hoon/...`). 경로는 런타임 동적 해석이어야 하며 JSONL 로그에 머신별 절대경로가 영구 기록되면 크로스 플랫폼 재현 불가.",
    "- [Medium] data/skill-usage.jsonl — contract_pass_rate: 0.0, hidden_pass_rate: 0.0, runtime_total: 0 임에도 `reason: external_eval_passed`로 candidate 승격 반복. 승격 조건 게이트가 실질적으로 비어 있음. historical_score 52가 21→22 이벤트 전반 고정 — 승격 조건 재검토 필요.",
    "- [Low] data/skill-usage.jsonl — diff 끝이 truncated 상태. 마지막 JSON 라인이 불완전할 경우 JSONL 파서 오류 발생 가능. 커밋 전 파일 무결성 확인 필요.",
    "- [Info] 변경된 7개 파일 중 실제 diff가 제공된 것은 skill-usage.jsonl 하나. code-review.md, registry.yaml, meta.yaml, skill-eval-report.json, skill-promotion.json 변경 내용 미포함 — 해당 파일 리뷰 불가."
  ]
}
```

---

## 2026-05-07 18:17 — `2026-05-07-memory-gitignore-cleanup` (5ded4f52)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\core\provider_detect.py

**Changed (8)**: `core/provider_detect.py, data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 18:19 — `2026-05-07-memory-gitignore-cleanup` (f2355a45)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "verdict": "WARN",
  "findings": [
    {
      "severity": "High",
      "file": "data/skill-usage.jsonl",
      "line": "새 항목들",
      "note": "커밋 메시지(provider_detect.py ping 교체)와 실제 변경 파일이 불일치. provider_detect.py 수정분이 diff에 없음 — 실제 버그픽스가 이 커밋에 포함됐는지 확인 필요."
    },
    {
      "severity": "Medium",
      "file": "data/skill-usage.jsonl",
      "line": "21~23번 신규 항목",
      "note": "report_path/promotion_path가 절대 경로(D:\\\\hoonProJect\\\\...) 하드코딩. 이전 항목은 macOS 경로(/Users/hoon/...). 경로는 런타임에 동적으로 결정되어야 하며 JSONL에 기록할 경우 워크스페이스 루트 기준 상대 경로 사용 권장."
    },
    {
      "severity": "Low",
      "file": "data/skill-usage.jsonl",
      "line": "전체 new_skill 항목",
      "note": "contract_pass_rate=0, hidden_pass_rate=0, runtime_success_rate=0, shadow_cases=0인 상태로 21~22회 반복 승격. 실평가 없이 external_eval_passed 사유로 candidate 유지 중 — 평가 파이프라인 미연결 의심."
    },
    {
      "severity": "Info",
      "file": "data/skill-usage.jsonl",
      "line": "23번 항목",
      "note": "diff가 잘림(truncated). 마지막 항목이 완전히 표시되지 않아 전체 내용 검증 불가."
    }
  ]
}
```

**요약**: 실제 버그픽스(`provider_detect.py`) 코드가 diff에 없는 것이 가장 큰 문제입니다. 절대 경로 하드코딩은 CI/다른 PC에서 깨질 수 있으니 상대 경로로 전환 권장합니다.

---

## 2026-05-07 18:19 — `2026-05-07-memory-gitignore-cleanup` (5f00fbff)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [Critical] data/skill-usage.jsonl — 커밋 메시지가 fix(provider_detect)를 명시하나 diff에 provider_detect.py 변경이 없음. 실제 핵심 수정이 스테이지되지 않았거나 누락됐을 가능성.",
    "- [High] data/skill-usage.jsonl:latest — report_path/promotion_path에 머신 종속 절대 경로 하드코딩 (D:\\hoonProJect\\...). CI 또는 타 PC에서 경로 참조 시 실패. 상대 경로 또는 프로젝트 루트 기준 경로로 교체 필요.",
    "- [Medium] data/skill-usage.jsonl — 이전 항목은 macOS 경로(/Users/hoon/...), 신규 항목은 Windows 경로 혼재. 로그 일관성 파괴, 경로 기반 집계·분석 시 오분류 유발.",
    "- [Low] data/skill-usage.jsonl — contract_pass_rate, shadow_delta, runtime_success_rate가 22개 이벤트 내내 0.0 고정. 실제 평가가 실행되지 않거나 결과가 기록되지 않는 구조적 문제 의심.",
    "- [Info] data/skill-usage.jsonl — historical_score=52가 21→22 이벤트 동안 변화 없음. 점수 계산 로직이 feedback_total_events 증가를 반영하는지 확인 필요."
  ]
}
```

---

## 2026-05-07 18:20 — `2026-05-07-memory-gitignore-cleanup` (9143acc6)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [High] data/skill-usage.jsonl:22-24 — `report_path`/`promotion_path`가 Windows 절대경로(`D:\\hoonProJect\\...`)로 하드코딩됨. 이전 항목은 macOS 경로(`/Users/hoon/...`). 경로는 상대경로 또는 project-root 기준으로 정규화해야 다른 환경에서 재현 가능.

- [Medium] data/skill-usage.jsonl — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `shadow_cases: 0`인 상태에서 `candidate`로 22회 반복 승격. 테스트 커버리지 없이 promotion이 계속 발화되는 로직 결함 가능성. `external_eval_passed` 트리거 조건 재검토 필요.

- [Low] data/skill-usage.jsonl — 커밋 메시지(`fix(provider_detect): codex_cli ping 명령 교체`)와 실제 diff 내용(data/스킬 메타 파일만 변경)이 불일치. `core/provider_detect.py` 변경분이 diff에 없음 — 실제 픽스가 이 커밋에 포함됐는지 확인 필요.

- [Info] diff 잘림(truncated) — diff 끝이 잘려 `skills/new_skill/skill-eval-report.json`, `skills/registry.yaml` 등 나머지 파일 변경 내용을 검토하지 못했음. 전체 diff 제공 시 추가 검토 가능.

---

## 2026-05-07 18:20 — `2026-05-07-memory-gitignore-cleanup` (ff186022)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [High] data/skill-usage.jsonl — 커밋 메시지(fix provider_detect codex_cli ping)와 변경 파일 7개가 불일치. core/provider_detect.py가 diff에 없음. 실제 수정이 스테이징됐는지 확인 필요.",
    "- [Medium] data/skill-usage.jsonl:21-23 — report_path/promotion_path에 절대 경로 하드코딩(D:\\hoonProJect\\worktrees\\...). 이전 항목들은 /Users/hoon/... macOS 경로. 머신 종속 경로가 버전관리 데이터에 혼재.",
    "- [Medium] data/skill-usage.jsonl — diff 마지막 줄이 잘림(항목 불완전). jsonl 파싱 시 마지막 레코드 오류 가능.",
    "- [Low] data/skill-usage.jsonl — contract_pass_rate, hidden_pass_rate, runtime_success_rate 전부 0.0, shadow_cases=0 상태로 21회 이상 candidate 승격 반복. 실제 검증 없이 promoted 상태 누적."
  ]
}
```

**핵심 지적**: 커밋 메시지가 `provider_detect` 수정을 명시하지만 diff에 해당 파일이 없습니다. 올바른 파일이 스테이징됐는지 `git diff --staged core/provider_detect.py` 로 확인이 필요합니다.

---

## 2026-05-07 18:21 — `2026-05-07-memory-gitignore-cleanup` (de76f84e)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "verdict": "WARN",
  "findings": [
    {
      "severity": "High",
      "file": "data/skill-usage.jsonl",
      "line": "new entries",
      "note": "report_path / promotion_path에 머신 종속 절대경로 하드코딩 (D:\\\\hoonProJect\\\\worktrees\\\\...). 이전 항목은 macOS 경로(/Users/hoon/...)로 혼재 — 다른 PC에서 재실행 시 경로 불일치로 파일 로드 실패 가능"
    },
    {
      "severity": "Medium",
      "file": "data/skill-usage.jsonl",
      "line": "모든 신규 항목",
      "note": "contract_pass_rate=0.0, hidden_pass_rate=0.0, runtime_success_rate=0.0인데도 reason=external_eval_passed로 기록. 평가 지표가 모두 0인 상태의 승격 근거가 불명확 — 로직 버그 가능성"
    },
    {
      "severity": "Medium",
      "file": "커밋 메시지",
      "line": "N/A",
      "note": "커밋 메시지는 fix(provider_detect): codex_cli ping 교체인데, 실제 변경 파일은 skill-usage.jsonl, code-review.md, skill-eval-report.json 등 — 커밋 범위와 메시지 불일치"
    },
    {
      "severity": "Low",
      "file": "data/skill-usage.jsonl",
      "line": "신규 항목",
      "note": "historical_score가 18→22 이벤트 동안 52에서 고정 — 스코어 업데이트 로직이 실제로 동작하는지 확인 필요"
    },
    {
      "severity": "Info",
      "file": "diff 끝 부분",
      "line": "마지막 줄",
      "note": "diff가 잘려 있어 세 번째 신규 항목 전체 내용 미확인 — 검토 불완전"
    }
  ]
}
```

---

## 2026-05-07 18:22 — `2026-05-07-memory-gitignore-cleanup` (6b062bf9)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [High] data/skill-usage.jsonl:22-24 — report_path/promotion_path에 Windows 절대경로 하드코딩 (D:\\\\hoonProJect\\\\worktrees\\\\...). 이전 항목들은 Unix 경로(/Users/hoon/...). 경로는 상대경로 또는 경로 없이 skill_id만 저장해야 크로스플랫폼 이식성 유지됨.",
    "- [Medium] data/skill-usage.jsonl — 커밋 메시지 'fix(provider_detect)' 와 실제 변경 파일 불일치. provider_detect.py 변경이 diff에 없고 JSONL/YAML/JSON 데이터 파일만 포함됨. 실제 버그픽스 코드가 이 커밋에 포함됐는지 확인 필요.",
    "- [Low] data/skill-usage.jsonl — feedback_events 21→22 증가에도 historical_score가 52로 고정, contract/hidden/runtime pass rate 전부 0.0. 스코어링 로직이 실제로 동작 중인지 점검 필요 (데이터 이슈 vs 로직 버그).",
    "- [Info] 변경된 7개 파일 모두 데이터/메타/문서 파일이며 .py 파일 없음 — Review-Gate Tier 1 적용 대상."
  ]
}
```

---

## 2026-05-07 18:22 — `2026-05-07-memory-gitignore-cleanup` (e23ff481)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{"review": "- [Medium] data/skill-usage.jsonl:22-24 — `report_path`/`promotion_path`에 절대 경로(Windows `D:\\hoonProJect\\...`)가 하드코딩됨. 이전 항목들은 `/Users/hoon/workTree/...` Mac 경로였는데, 이번 커밋부터 Windows 경로로 바뀜. 환경 이식성 없음 — 경로는 상대 경로나 프로젝트 루트 기준으로 정규화해야 함.\n- [Low] data/skill-usage.jsonl — 커밋 제목(provider_detect ping 교체)과 변경 파일(skill-usage.jsonl, registry.yaml 등 스킬 데이터)이 불일치. `provider_detect.py` diff가 포함되지 않았거나, 데이터 파일이 다른 커밋에 번들됨. 추적성 저하.\n- [Info] skills/new_skill/skill-eval-report.json, skill-promotion.json — `contract_pass_rate: 0.0`, `runtime_success_rate: 0.0`, `runtime_ready_for_active: false`인 채로 `candidate` 승격이 반복됨(21→22회). `historical_score: 52` 고정. 실제 평가 없이 승격만 반복되는 구조적 문제 가능성.\n- [Info] docs/code_review/code-review.md, skills/registry.yaml, skills/dp/meta.yaml — diff 미제공으로 내용 확인 불가."}
```

---

## 2026-05-07 18:22 — `2026-05-07-memory-gitignore-cleanup` (5037cc33)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [High] data/skill-usage.jsonl:21-23 — 절대 경로 하드코딩(`D:\\hoonProJect\\worktrees\\agent-factory\\...`). 이전 항목(Mac 경로 `/Users/hoon/...`)과 혼재. 로그가 머신 종속 경로를 포함하면 재현성·이식성이 없음. `report_path`/`promotion_path`는 상대 경로 또는 프로젝트 루트 기준 경로로 기록해야 함.",
    "- [Medium] data/skill-usage.jsonl — `contract_pass_rate`, `hidden_pass_rate`, `runtime_success_rate` 모두 0.0이고 `shadow_cases`=0인 상태에서 `external_eval_passed` 이유로 `draft→candidate` 승격 반복. 평가 근거 없는 자동 승격이 스킬 품질 게이트를 무력화할 수 있음. 승격 조건 검증 로직 점검 필요.",
    "- [Low] data/skill-usage.jsonl — `historical_score`=52가 21~23번 이벤트 내내 변화 없음. 이벤트 누적에도 점수가 갱신되지 않는다면 스코어링 파이프라인이 실제로 호출되지 않고 있을 가능성 있음.",
    "- [Info] data/skill-usage.jsonl — 변경된 파일 7개 중 실제 커밋 제목(`fix(provider_detect): codex_cli ping 명령 교체`)과 관련된 파일이 하나도 없음. 스킬 로그·메타·레지스트리 변경이 `provider_detect` 픽스와 같은 커밋에 묶인 이유 불명확 — 관심사 분리 필요.",
    "No issues found in docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml (diff 미포함 또는 내용 무관)."
  ]
}
```

---

## 2026-05-07 18:23 — `2026-05-07-memory-gitignore-cleanup` (206c3c1d)

**Context**: fix(provider_detect): codex_cli ping 명령 교체 — exec stdin hang → --version

**Changed (7)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/dp/meta.yaml, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] `data/skill-usage.jsonl:22+` — `report_path` / `promotion_path`에 머신별 절대 경로(`D:\\hoonProJect\\...`) 하드코딩. 다른 PC에서 경로가 깨짐. 상대 경로 또는 프로젝트 루트 기준 경로로 교체 필요.
- [Low] `data/skill-usage.jsonl` — 마지막 줄이 diff에서 잘려있어 JSON이 불완전하게 보임. 파일 자체가 올바른지 확인 필요.
- [Low] `data/skill-usage.jsonl` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`이 21회 이벤트 내내 0인데 `candidate`로 반복 승격. 승격 기준에 pass_rate 최솟값 검증이 빠져 있는지 확인 필요.
- [Info] diff에 `core/provider_detect.py`가 없음 — 커밋 메시지의 실제 버그픽스(exec stdin hang → `--version` 교체) 변경분이 이 diff에 포함되지 않았음. 리뷰 대상 파일 목록과 커밋 내용이 불일치.

---

## 2026-05-07 18:23 — `2026-05-07-memory-gitignore-cleanup` (f5e79593)

**Context**: chore(skills): 스킬 평가 이벤트 누적 및 메타데이터 동기화

**Changed (1)**: `docs/code_review/code-review.md`

### Findings

```json
{
  "review": {
    "commit": "206c3c1d",
    "files_reviewed": ["docs/code_review/code-review.md"],
    "findings": [
      {
        "severity": "Info",
        "location": "docs/code_review/code-review.md:4418",
        "note": "커밋 메시지 대상(core/provider_detect.py)이 Changed Files 목록에 없음 — 리뷰 문서 자체가 그 불일치를 [Info]로 기록함. 문서 내용은 정확."
      }
    ],
    "summary": "변경 내용은 코드 리뷰 문서에 새 섹션 추가뿐. 로직·보안·에러핸들링 영향 없음. 문서 내 지적(절대 경로 하드코딩, pass_rate 0 승격)은 실제 data/ 파일의 잠재적 문제이며 이 diff 범위 밖. 현재 diff 자체는 이상 없음.",
    "verdict": "PASS"
  }
}
```

---

## 2026-05-07 18:48 — `2026-05-07-memory-gitignore-cleanup` (1a1387c2)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\scripts\pre_commit_review.py

**Changed (1)**: `scripts/pre_commit_review.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 18:49 — `2026-05-07-memory-gitignore-cleanup` (2e4598d3)

**Context**: fix(pre_commit_review): stale 판정 + Verdict 인식 강화 — 구 리뷰 허위 BLOCK 방지

**Changed (1)**: `docs/code_review/code-review.md`

### Findings

No issues found.

---

## 2026-05-07 21:37 — `2026-05-07-memory-gitignore-cleanup` (9719b5a9)

**Context**: edit: /Users/hoon/workTree/agent-factory/scripts/project_context_sync.py

**Changed (1)**: `scripts/project_context_sync.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 21:42 — `2026-05-07-memory-gitignore-cleanup` (1226b66a)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/research_router.py

**Changed (2)**: `core/research_router.py, docs/code_review/code-review.md`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 23:21 — `2026-05-07-memory-gitignore-cleanup` (5afc01bc)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/pipeline_quality.py

**Changed (71)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+56)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-07 23:37 — `2026-05-07-memory-gitignore-cleanup` (86e3ed83)

**Context**: feat(pipeline): 3-Tier Quality Gate 통합 — provider_detect 위임 + SKIP verdict + work-item rubric

**Changed (70)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+55)`

### Findings

No issues found.

The diff shows only trailing-whitespace normalization across documentation and markdown files — no logic, security surface, or error-handling paths are affected.

---

## 2026-05-10 13:08 — `main` (cea09c5a)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/warning_stats.py

**Changed (15)**: `Master_Blueprint.md, af.spec, core/project_pipeline.py, install-af.ps1, run_factory_cli.py, run_output.txt, runtime/warnings/_index.json, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py, syncCompyne/workspace_context_cli.py, version.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-10 22:44 — `main` (d1a85c70)

**Context**: edit: /Users/hoon/workTree/agent-factory/core/escalation_evaluator.py

**Changed (11)**: `NEXT_STEPS.md, core/escalation_evaluator.py, docs/code_review/code-review.md, run_output.txt, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py, syncCompyne/workspace_context_cli.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-11 11:11 — `main` (d7572c69)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\scripts\blueprint_updater.py

**Changed (1)**: `scripts/blueprint_updater.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-11 11:14 — `main` (72ecea66)

**Context**: fix(blueprint-sync-B): §0 자동 sync hook 보강 — 결함 4건 수정 + 1회 전체 동기

**Changed (1)**: `docs/code_review/code-review.md`

### Findings

No issues found.

The diff appends a log entry to a markdown review file — no code logic, security surface, or error handling involved.

---

## 2026-05-11 12:00 — `main` (1a2b33bf)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\tests\test_gemini_smoke.py

**Changed (1)**: `tests/test_gemini_smoke.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-11 17:45 — `main` (4d7e7665)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\core\review_report.py

**Changed (1)**: `core/review_report.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-11 18:37 — `main` (62293c30)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\core\approval_gate.py

**Changed (1)**: `core/approval_gate.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-11 18:58 — `main` (20e29dc1)

**Context**: edit: D:\hoonProJect\worktrees\agent-factory\core\approval_gate.py

**Changed (1)**: `core/approval_gate.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-13 18:14 — `main` (97dd2b50)

**Context**: edit: core/approval_gate.py

**Changed (6)**: `NEXT_STEPS.md, core/approval_gate.py, docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md, findings.md, progress.md, task_plan.md`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-13 19:06 — `main` (1cba5a1e)

**Context**: Preserve domain gate metadata

**Changed (3)**: `findings.md, progress.md, task_plan.md`

### Findings

You've hit your limit · resets 8:30pm (Asia/Seoul)

---

## 2026-05-13 21:28 — `main` (4adf104b)

**Context**: edit: core/approval_gate.py

**Changed (70)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+55)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-13 22:49 — `main` (0b6500f6)

**Context**: edit: core/work_item_generator.py

**Changed (71)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+56)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-13 23:03 — `main` (ad1acca2)

**Context**: test

**Changed (70)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+55)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-13 23:59 — `main` (f048a468)

**Context**: edit: core/utils.py

**Changed (72)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+57)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-14 00:30 — `main` (892359dd)

**Context**: test

**Changed (69)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+54)`

### Findings

- [Info] AGENTS.md, GEMINI.md, et al. — 전체 변경사항이 줄 끝 공백(trailing whitespace) 제거만 해당. 내용 변경 없음.

No issues found.

---

## 2026-05-14 01:09 — `main` (a15705d0)

**Context**: edit: core/utils.py

**Changed (73)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, Master_Blueprint.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml ... (+58)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-14 01:32 — `main` (f7e91d5c)

**Context**: edit: tests/test_key_combos.py

**Changed (72)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+57)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-14 17:05 — `main` (f69ff076)

**Context**: edit: core/control/verdicts.py

**Changed (1)**: `docs/decisions/ADR-20260514-133054-question-router-stage0.md`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-14 17:28 — `main` (c6acf5fd)

**Context**: feat(stage0-question-router): Question Router Stage 0 P1 구현

**Changed (2)**: `docs/code_review/code-review.md, skill-eval-report.json`

### Findings

- [Low] skill-eval-report.json:last-line — 파일 끝 개행 없음(`No newline at end of file`). JSON 파일은 trailing newline을 갖는 것이 표준.
- [Info] skill-eval-report.json — 절대 경로 → 상대 경로 변환은 이식성 개선으로 적절한 변경.
- [Info] docs/code_review/code-review.md — 리뷰 엔트리의 `Context` 필드가 `edit: core/control/verdicts.py`인데 실제 변경 파일은 `docs/decisions/ADR-*.md`로 불일치. 메타데이터 정확도 문제(기능 버그는 아님).

No security or critical issues found.

---

## 2026-05-14 17:29 — `main` (4c26980c)

**Context**: feat(stage0-question-router): Question Router Stage 0 P1 구현

**Changed (1)**: `skill-eval-report.json`

### Findings

- [Low] skill-eval-report.json:46 — 파일 끝 개행 없음(`No newline at end of file`). 변경 전부터 존재하던 문제이나 이번 커밋에서 정리 가능.

절대 경로 → 상대 경로 전환은 이식성 개선으로 올바른 방향. 나머지 필드 이상 없음.

---

## 2026-05-14 17:29 — `main` (883dd103)

**Context**: feat(stage0-question-router): Question Router Stage 0 P1 구현

**Changed (1)**: `skill-eval-report.json`

### Findings

- [Medium] skill-eval-report.json — 자동 생성 파일(written_at 타임스탬프 포함)이 소스 컨트롤에 커밋됨. 실행 시마다 경로·타임스탬프가 바뀌어 불필요한 diff가 쌓임. `.gitignore`에 추가 권장.
- [Low] skill-eval-report.json — 상대 경로로 변환 후 소비자(reader)가 어느 CWD 기준으로 해석하는지 미검증. 스크립트가 다른 디렉터리에서 이 파일을 로드하면 경로 해석 실패 가능.
- [Low] skill-eval-report.json:44 — 파일 끝 개행 없음(`No newline at end of file`). 일부 JSON 파서 및 diff 도구에서 경고 발생.
- [Info] skill-eval-report.json — `static_gate.ok: false`, `recommended_stage: "draft"` 상태로 커밋됨. 의도적 스냅샷이라면 무시, 아니라면 평가 통과 후 커밋이 적절.

---

## 2026-05-14 17:29 — `main` (73ea112a)

**Context**: feat(stage0-question-router): Question Router Stage 0 P1 구현

**Changed (1)**: `skill-eval-report.json`

### Findings

- [Low] skill-eval-report.json:44 — 파일 끝 개행 없음 (`\ No newline at end of file`). POSIX 표준 위반이며 일부 diff 도구에서 노이즈 발생.

나머지 변경 (절대경로 → 상대경로, 타임스탬프 갱신)은 의도된 정상 수정.

---

## 2026-05-14 17:30 — `main` (b3dd9a03)

**Context**: feat(stage0-question-router): Question Router Stage 0 P1 구현

**Changed (1)**: `skill-eval-report.json`

### Findings

- [Info] skill-eval-report.json:2 — `skill_path`를 절대경로 → 상대경로로 변환. 이식성 개선, 정상 변경.
- [Info] skill-eval-report.json:44 — `report_path`도 동일하게 절대경로 → 상대경로. 일관성 있음.
- [Low] skill-eval-report.json:46 — 파일 끝 개행(EOF newline) 없음. 기존부터 존재하던 문제이나 JSON 파일 표준 관행상 `\n` 추가 권장.

No critical or high issues found.

---

## 2026-05-14 17:30 — `main` (053efbe0)

**Context**: feat(stage0-question-router): Question Router Stage 0 P1 구현

**Changed (1)**: `skill-eval-report.json`

### Findings

- [Low] skill-eval-report.json:46 — 파일 끝 개행 없음 (`\ No newline at end of file`). 일부 도구에서 diff noise 유발.
- [Info] skill-eval-report.json:2,44 — 절대 경로 → 상대 경로 정규화. 포터블하게 개선된 변경.

No functional or security issues found.

---

## 2026-05-14 18:35 — `main` (f625554c)

**Context**: edit: tests/test_stage0_question_router.py

**Changed (6)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml, tests/test_stage0_question_router.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-14 18:36 — `main` (51a47208)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (6)**: `data/skill-usage.jsonl, docs/code_review/code-review.md, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Info] data/skill-usage.jsonl:31 — 신규 항목만 상대 경로 사용; 이전 28~30번 항목은 여전히 절대 경로(`D:\\hoonProJect\\...`). 로그 일관성 깨짐.
- [Low] data/skill-usage.jsonl:31 — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_success_rate: 0.0` 전부 0인데 `recommended_stage: "candidate"` 승격. 승격 기준이 pass rate를 무시하는 로직이라면 의도적이어야 함.
- [Low] data/skill-usage.jsonl:28-31 — `historical_score`가 4회 연속 52로 고정. 이벤트 누적(`feedback_total_events` 27→30)에도 점수 변화 없음 — 점수 계산 로직 미동작 가능성.
- [Info] skill-eval-report.json:2 — `skill_path` 절대→상대 경로 정규화. 포터블 개선.
- [Info] docs/code_review/code-review.md — "Review skipped" 항목이 커밋 컨텍스트(`feat(stage0-yaml)`)와 불일치 (`edit: tests/test_stage0_question_router.py`로 기록됨). 자동 생성 메타데이터 오기입.

No security or critical issues found.

---

## 2026-05-14 18:37 — `main` (ad02fe64)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] data/skill-usage.jsonl:31 — `run_id: ""`, `agent_role: ""` 빈 문자열로 프로비넌스 누락. 이 promotion 이벤트가 어느 세션/역할에서 발생했는지 추적 불가.
- [Medium] skills/new_skill/skill-eval-report.json — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0` 전부 0이지만 `candidate` 승격. 정량 근거 없이 `external_eval_passed` 하나로만 승격 결정 — 승격 기준 충족 여부 불분명.
- [Low] skill-eval-report.json (루트) — `static_gate.ok: false`, `recommended_stage: draft`인 `agent_factory` 스킬 레포트가 루트에 방치. 실제 스킬이 아닌 플레이스홀더면 `.gitignore` 또는 `tests/_tmp/`로 이동 필요.
- [Low] data/skill-usage.jsonl — `feedback_total_events: 27→30` 연속 4개 promotion 이벤트, 모두 `historical_score: 52` 동일. 동일 점수로 반복 재평가된 이유가 불분명 — 멱등성 보장 코드 확인 필요.
- [Info] skill-eval-report.json, skills/new_skill/skill-eval-report.json — 절대 경로(`D:\hoonProJect\...`) → 상대 경로 정규화는 이식성 개선으로 올바른 방향.
- [Info] 커밋 메시지 "P4+P2 question set YAML 추가"와 실제 변경 파일(JSON/JSONL 메타데이터) 불일치 — `skills/registry.yaml` diff가 제공되지 않아 YAML 추가 여부 검증 불가.

---

## 2026-05-14 18:38 — `main` (deda96f8)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] data/skill-usage.jsonl — 신규 항목만 상대 경로(`skills/new_skill/...`)를 사용하고, 이전 29개 항목은 절대 경로(`D:\\hoonProJect\\...`)를 유지. 경로를 읽는 코드가 두 포맷을 동시에 처리하지 않으면 이전 항목 참조 실패.
- [Low] data/skill-usage.jsonl — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0`인 상태에서 `recommended_stage: "candidate"` 승격. 평가 임계값이 실제로 적용되고 있는지 확인 필요.
- [Info] skill-eval-report.json, skills/new_skill/skill-eval-report.json — `skill_path`·`report_path` 절대→상대 경로 전환은 이식성 개선. 단, 이 파일들을 읽는 코드가 CWD 기준으로 경로를 해석하는지 확인 필요.
- [Info] 커밋 메시지("P4+P2 question set YAML 추가")와 실제 변경 파일(JSON/JSONL only)이 불일치. `skills/registry.yaml` diff가 누락됐거나 커밋 메시지가 잘못됨.

---

## 2026-05-14 18:38 — `main` (d3e0eba0)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Low] `data/skill-usage.jsonl` — 이전 29개 엔트리는 절대 경로(`D:\hoonProJect\...`), 새 엔트리만 상대 경로로 혼재. `report_path`/`promotion_path`를 코드에서 직접 열면 OS 이동 시 구 엔트리 모두 파일 접근 실패.
- [Low] `data/skill-usage.jsonl:31` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_success_rate: 0.0`, `shadow_cases: 0` 전부 0인데 `candidate`로 승격. `static_ok: true`와 `historical_score: 52`만으로 승격 조건이 충족된다면 평가 게이트 실효성 의문.
- [Info] `skill-eval-report.json` — 루트에 위치한 `agent_factory` dummy 리포트가 커밋에 포함. 실제 평가 대상이 아닌 픽스처라면 `.gitignore` 처리 검토.
- [Info] 커밋 메시지 "P4+P2 question set YAML 추가"와 실제 diff(경로 정규화 + 카운터 증가) 불일치. `skills/registry.yaml` diff가 잘려 확인 불가 — registry 변경 내용 별도 확인 필요.

No Critical/High issues. 핵심은 경로 혼재(Low)와 0점 지표 승격(Low) 두 건.

---

## 2026-05-14 18:39 — `main` (a204c711)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [Medium] data/skill-usage.jsonl — 이벤트 27~30 모두 contract_pass_rate=0.0, hidden_pass_rate=0.0, runtime_total=0 임에도 candidate 승격. static_ok=true만으로 승격 허용하는 게이트 조건이 지나치게 약함.",
    "- [Low] data/skill-usage.jsonl:28-31 — 동일 historical_score(52)·동일 evidence로 4회 연속 승격 이벤트 기록. 중복 평가 실행 시 idempotency 체크 없음 — 동일 상태라면 기존 이벤트를 갱신하거나 스킵해야 함.",
    "- [Low] skill-eval-report.json:1 — 루트 레벨 report의 static_gate.ok=false, recommended_stage=draft. 자동화 파이프라인이 이 파일을 읽으면 agent_factory 스킬 상태를 잘못 판단할 수 있음. 파일 목적(더미/레거시 여부)을 명확히 표시하거나 제거 필요.",
    "- [Info] 다수 파일 — 절대 Windows 경로 → 상대 경로 정규화는 이식성 개선으로 적절함. 단, 소비자(skill evaluator, promotion loader)가 모두 workspace root 기준으로 경로를 resolve하는지 확인 필요.",
    "- [Info] 커밋 메시지와 diff 불일치 — 'P4+P2 question set YAML 추가'라고 명시됐으나 보이는 diff는 JSON 경로 정규화뿐. skills/registry.yaml 변경 내용이 diff에 없어 실제 YAML 추가 여부 검증 불가."
  ]
}
```

---

## 2026-05-14 18:40 — `main` (c95ed6a4)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] data/skill-usage.jsonl:31 — 신규 항목의 `report_path`/`promotion_path`가 상대 경로(`skills/new_skill/...`)인 반면, 기존 28~30번 항목은 절대 Windows 경로(`D:\\hoonProJect\\...`)를 유지. 이 JSONL을 읽어 경로를 직접 사용하는 코드가 있다면 구 항목은 타 PC에서 깨지고, 신규 항목은 CWD 의존 — 전체 일괄 정규화 또는 소비자 코드의 경로 해석 방식 확인 필요.

- [Low] skill-eval-report.json:3 — `skill_path: "dummy"` 는 실제 경로가 아닌 플레이스홀더. 이 파일을 로드해 `skill_path`를 stat/import하는 경로가 있다면 조용히 실패함. 의도된 stub이면 주석으로 명시 권장.

- [Low] skill-eval-report.json (루트, EOF) — `\ No newline at end of file`. JSON 파서는 문제없지만 diff noise 발생 — 맞춤.

- [Info] data/skill-usage.jsonl 전 항목 — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0` 인 채 `candidate` 승격. 평가 미실행 상태가 의도된 것이라면 무관, 아니라면 승격 로직의 패스율 조건 확인 필요.

- [Info] 이번 커밋의 실질 변경은 **경로 절대→상대 정규화** 1건. YAML 추가(P4+P2 question set)는 diff에 포함되지 않아 `skills/registry.yaml` 변경 내용을 직접 검토하지 못함 — 해당 파일 diff 누락 여부 확인 권장.

---

## 2026-05-14 18:40 — `main` (16417a17)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] `data/skill-usage.jsonl` — `contract_pass_rate`, `hidden_pass_rate`, `runtime_success_rate` 모두 0.0인 상태로 `"reason": "external_eval_passed"` 처리. 실질적 검증 없는 승격 근거.
- [Medium] `data/skill-usage.jsonl` — 동일 스킬(`new_skill`)이 `draft→candidate` 승격 이벤트를 4회 반복(feedback_total_events 27→30). 승격이 누적 재실행되고 있어 멱등성 보장 여부 불명확.
- [Low] `skill-eval-report.json` (루트) — `static_gate.ok: false`, `recommended_stage: "draft"`인 파일이 레포 루트에 상주. 임시 산출물인지 의도된 파일인지 불명확; 커밋 대상에서 제외 검토 필요.
- [Low] 절대 경로 → 상대 경로 변환은 이식성 개선이나, 생성 코드(`skill_evaluator` 등)가 런타임에 절대 경로를 다시 쓰면 다음 실행에서 원복될 수 있음. 생성 로직 확인 필요.
- [Info] 커밋 메시지에 "P4+P2 question set YAML 추가"라 명시됐으나 diff에 YAML 신규 파일이 없음. `skills/registry.yaml` 변경 내용이 diff에서 누락돼 리뷰 불완전.

---

## 2026-05-14 18:41 — `main` (c09fc633)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] data/skill-usage.jsonl — 동일 `skill_id: new_skill`에 대해 `feedback_total_events` 27→28→29→30 인 4개 promotion 이벤트가 연속 기록됨. `historical_score`, 모든 rate 값이 동일(52/0.0). promotion 로직이 중복 발화 중일 가능성 있음 — 트리거 조건 점검 필요.
- [Medium] data/skill-usage.jsonl:31 — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0` 상태에서 `draft → candidate` 승격. `installable: false`로 설치는 막히나, 테스트 커버리지 0인 스킬이 candidate 단계에 머무는 것이 policy상 의도된 것인지 확인 필요.
- [Low] skill-eval-report.json (루트) — `\ No newline at end of file`. JSON 파일 파싱 자체에는 무해하나 일관성 위반.
- [Low] 커밋 메시지 — "P4+P2 question set YAML 추가"라고 명시되나 제공된 diff에 `skills/registry.yaml` 내용이 없음. 실제 YAML 추가 내용이 누락됐거나 diff가 잘린 것 — 변경 범위 불투명.
- [Info] 절대경로 → 상대경로 변환(`D:\\hoonProJect\\...` 제거): 이식성 향상, 올바른 방향.

---

## 2026-05-14 18:42 — `main` (ec8b0d15)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [High] data/skill-usage.jsonl — 이전 29개 항목은 `D:\\hoonProJect\\...` 절대경로, 신규 항목만 `skills/new_skill/...` 상대경로. `report_path`/`promotion_path`를 파일 로드에 사용하는 코드가 있다면 구 항목들은 다른 머신에서 깨짐. 경로 정규화 로직이 없으면 런타임 버그.

- [Medium] skills/new_skill/skill-eval-report.json — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_success_rate: 0.0` 임에도 `recommended_stage: "candidate"` 승격. `historical_score: 52`만으로 gate를 통과하는 경로가 의도된 것인지 검증 필요. 0% 통과율 스킬이 candidate로 올라가면 downstream 사용자에게 노출될 위험.

- [Medium] data/skill-usage.jsonl — `installable: false` + `to_stage: "candidate"` 조합이 30개 항목 전부에서 반복. candidate 단계에서 installable이 영구 false라면 스킬이 실제로 활성화될 수 없음. 정책 상 의도인지, 누락된 상태 전환인지 확인 필요.

- [Low] skill-eval-report.json:46 — 파일 끝 개행 없음(`No newline at end of file`). JSONL/JSON 파서나 git diff 가독성 이슈.

- [Info] 이번 커밋 제목(`P4+P2 question set YAML 추가`)과 실제 변경 파일(평가 리포트·JSONL·registry.yaml) 불일치. YAML 추가 본체가 diff에 없음 — 변경 파일 목록과 커밋 범위 재확인 권장.

---

## 2026-05-14 18:42 — `main` (0f1f8741)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] `data/skill-usage.jsonl`:30 — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_success_rate: 0.0` 모두 0인 상태에서 `external_eval_passed` 이유로 `candidate` 승격. `historical_score: 52` 단독 근거 — 승격 임계값 정책과 일치하는지 확인 필요.
- [Low] `data/skill-usage.jsonl`:30 — 이전 3건은 절대경로(`D:\hoonProJect\...`), 신규 항목만 상대경로. 로그 레코드 간 경로 형식 불일치 — `report_path`/`promotion_path` 해석 코드가 두 형식 모두 처리하는지 확인 필요.
- [Info] `skill-eval-report.json`, `skills/new_skill/skill-eval-report.json` — 절대경로 → 상대경로 정규화는 이식성 개선. 의도적 변경으로 보임.
- [Info] `skill-eval-report.json` — `skill_path: "dummy"` 는 루트 레벨 평가 리포트가 실제 스킬이 아닌 플레이스홀더임을 시사. 프로덕션 평가 경로에서 참조되지 않는지 확인 필요.

---

## 2026-05-14 18:44 — `main` (78cb6664)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] `data/skill-usage.jsonl` — 기존 3개 항목은 절대 경로(`D:\\hoonProJect\\...`), 신규 항목만 상대 경로로 불일치. 이력 로그의 경로 형식이 섞이면 경로 기반 집계/조회 스크립트가 오동작할 수 있다.

- [Medium] `data/skill-usage.jsonl:new entry` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_success_rate: 0.0` 전부 0이지만 `to_stage: candidate`로 승격. `reason: external_eval_passed`이지만 증거 지표가 전부 0인 채로 승격이 허용되는 조건이 명확하지 않음. 평가 게이트가 `historical_score >= 50` 단일 조건으로 동작하는지 확인 필요.

- [Low] `skill-eval-report.json` — 루트에 위치한 `skill-eval-report.json`의 `skill_path: "dummy"`는 실제 스킬 파일 없는 더미 항목. 평가 파이프라인이 이 파일을 실제 스킬로 오인하지 않는지 확인 필요.

- [Info] 절대 경로 → 상대 경로 전환(`report_path`, `promotion_path`)은 이식성 향상으로 올바른 방향. 단, 기존 로그 항목은 소급 수정되지 않아 부분적 상태.

---

## 2026-05-14 18:44 — `main` (bb2bcf3f)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [High] data/skill-usage.jsonl:31 — `new_skill` promoted draft→candidate 4회 연속 (`feedback_total_events` 27→30), 매번 `from_stage: "draft"` 동일. 스테이지가 실제로 advance되지 않고 동일 전환이 반복 append되고 있음 — 프로모션 멱등성 결여 버그.
- [High] skills/new_skill/skill-eval-report.json — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `shadow_cases: 0`, `runtime_total: 0` 전부 0이지만 `recommended_stage: "candidate"` 로 승격. `historical_score: 52` 단일 지표만으로 승격 허용 — 평가 게이트 우회에 해당.
- [Medium] skill-eval-report.json — `recommended_stage: "draft"` 상태의 루트 레벨 평가 파일이 레포에 커밋됨. 어느 스킬에 귀속되는지 불명확하고 `skill_path: "dummy"` 는 실제 경로가 아님 — 더미 artifact가 production artifact로 오인될 수 있음.
- [Medium] data/skill-usage.jsonl:31 — 이전 3개 이벤트(ts: 2026-05-11)는 절대경로(`D:\hoonProJect\...`) 사용, 새 이벤트만 상대경로 — 히스토리 내 경로 포맷 불일치. 경로 정규화가 소급 적용되지 않음.
- [Low] skill-eval-report.json — 파일 끝 개행 없음(`No newline at end of file`).
- [Info] 커밋 메시지 "P4+P2 question set YAML 추가"와 실제 변경 파일(skill eval/promotion artifacts)이 불일치 — `skills/registry.yaml` diff가 제공되지 않아 YAML 추가 내용 검증 불가.

---

## 2026-05-14 18:45 — `main` (69cd406b)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] `data/skill-usage.jsonl:31` — 신규 항목만 상대 경로(`skills/new_skill/...`) 사용, 기존 3개 항목은 절대 경로(`D:\\hoonProJect\\...`). 경로를 파일시스템에서 직접 resolve하는 코드가 있다면 혼재로 인해 경로 미발견 오류 발생 가능.
- [Medium] `data/skill-usage.jsonl:31` — `reason: "external_eval_passed"` 이지만 `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `shadow_cases: 0`. 실제 근거는 `historical_score: 52`인데 reason 문자열이 오해를 유발함. 프로모션 로직이 reason 필드를 조건 분기에 사용한다면 잘못된 경로로 처리될 수 있음.
- [Low] `skill-eval-report.json` (root) — EOF 개행 없음(`No newline at end of file`). JSON 파싱에는 무해하나 일관성 위반.
- [Low] `skills/new_skill/skill-eval-report.json` — diff가 중간에 잘림(`"D:\\h` 에서 截断). 변경 전체가 제공되지 않아 해당 파일의 나머지 수정 내용 검증 불가.
- [Info] `skills/registry.yaml`, `skills/new_skill/skill-promotion.json` — diff에 포함되지 않음. 커밋 메시지가 "P4+P2 question set YAML 추가"를 주장하지만 실제 YAML 내용 변경은 확인 불가.

**요약**: 절대/상대 경로 혼재(Medium)와 reason 필드 불일치(Medium)가 주요 사항. 나머지는 Low/Info 수준.

---

## 2026-05-14 18:46 — `main` (bb75b5cf)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] `data/skill-usage.jsonl` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `shadow_cases: 0`인 상태로 `candidate` 승격 반복. 실질 평가 없는 자동 승격이 정책상 허용되는지 확인 필요.
- [Medium] `data/skill-usage.jsonl`:L31 — 동일 evidence(`historical_score: 52`, 모든 rate 0)로 승격 이벤트가 4회(events 27→30) 중복 발화. 승격 로직에 멱등성 가드 부재 의심.
- [Low] `skill-eval-report.json`:L1 — 루트 레벨 `skill-eval-report.json`의 `recommended_stage`가 `"draft"`인데 `skills/new_skill/`은 `"candidate"` — 두 파일의 역할/소유자가 다름을 명확히 문서화 필요 (혼동 가능성).
- [Info] 절대 경로(`D:\\hoonProJect\\worktrees\\...`) → 상대 경로 정규화는 이식성 향상으로 올바른 변경.
- [Info] 커밋 메시지("P4+P2 question set YAML 추가")와 변경 파일 목록(eval-report, promotion, registry)이 일치하지 않음 — `skills/registry.yaml` diff가 잘려 있어 실제 YAML 추가 내용 미확인. 커밋 단위 분리 고려.

---

## 2026-05-14 18:46 — `main` (c42c9b47)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [High] data/skill-usage.jsonl:31 — 이전 3개 이벤트는 절대경로(`D:\\hoonProJect\\...`), 신규 이벤트만 상대경로(`skills/new_skill/...`). 경로 해석 코드가 두 형식을 동시에 지원하지 않으면 기존 항목 조회 실패.
- [Medium] data/skill-usage.jsonl:31 — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0`인 상태에서 `candidate` 승격. `historical_score: 52`만으로 승격 근거 충분한지 승격 기준 문서 확인 필요.
- [Low] skill-eval-report.json (root) — `recommended_stage: "draft"`인 루트 레벨 report가 커밋에 포함됨. `agent_factory` skill_id가 draft인 채로 추적되는 의도인지 불명확.
- [Info] 커밋 메시지 "P4+P2 question set YAML 추가"와 실제 변경 파일(JSON/JSONL)이 불일치. `skills/registry.yaml` diff가 제공되지 않아 실제 YAML 내용 검증 불가.
- [Info] `skills/new_skill/skill-eval-report.json` diff가 잘려 있어 전체 경로 정규화 범위 확인 불가.

**요약**: 절대경로 → 상대경로 정규화 방향은 올바르나, 기존 JSONL 항목과의 형식 혼재가 핵심 위험. 경로 읽기 코드가 두 형식을 모두 처리하는지 확인 필요.

---

## 2026-05-14 18:47 — `main` (94cd68d4)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [High] data/skill-usage.jsonl — 커밋 메시지("goal_clarification + brainstorming YAML 추가")와 실제 변경 파일(skill-eval-report.json, skill-promotion.json, skill-usage.jsonl) 불일치. 질문 세트 YAML이 diff에 없음. 스테이징 누락 가능성.
- [Medium] data/skill-usage.jsonl:31 — 기존 항목 3건은 절대 경로(`D:\\hoonProJect\\...`), 신규 항목만 상대 경로 사용. 동일 파일 내 경로 형식 혼재 → 경로 파싱 소비자가 구버전 항목에서 실패 가능.
- [Low] data/skill-usage.jsonl — `historical_score`가 27→30 이벤트 내내 52로 고정. 신규 피드백 이벤트에도 점수 재산정 안 됨 — 집계 로직 버그 or 의도된 설계인지 확인 필요.
- [Low] skills/new_skill/skill-eval-report.json — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `shadow_cases: 0`인데 `reason: external_eval_passed`로 candidate 승격. 모든 평가 지표가 0일 때 승격 허용하는 게이트 기준 재검토 필요.
- [Info] skills/registry.yaml — 변경됐다고 표시됐으나 diff에 미포함(잘려있음). registry 내용 일관성 별도 확인 필요.

---

## 2026-05-14 18:48 — `main` (06ee6b61)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] `data/skill-usage.jsonl`:all — 이전 29개 항목은 절대 경로(`D:\\hoonProJect\\...`) 유지, 신규 항목만 상대 경로로 작성. 경로 필드를 실제로 읽는 로직이 있다면 이전 항목에서 경로 해석 실패 가능. 마이그레이션 또는 읽기 시 경로 정규화 필요.
- [Medium] `data/skill-usage.jsonl`:all — `new_skill`이 `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `shadow_cases: 0`인 상태에서 `candidate` 승격 반복 기록(30회). 테스트 데이터 없이 승격 기준을 통과하는 구조라면 평가 게이트 의미가 없음. `static_ok: true` 단독으로 승격 허용하는 로직 검토 필요.
- [Low] `skill-eval-report.json`:47 — 파일 끝 개행 없음(`No newline at end of file`). 일부 도구에서 diff 오염 또는 파싱 오류 유발 가능.
- [Low] `data/skill-usage.jsonl`:all — `run_id: ""`, `agent_role: ""`가 30개 이벤트 전체에서 비어 있음. 이벤트 추적/디버깅 시 출처 식별 불가. 의도된 빈 값이면 Info.
- [Info] `skill-eval-report.json`, `skills/new_skill/skill-eval-report.json` — 절대 경로 → 상대 경로 변환은 이식성 개선. 올바른 방향.

---

## 2026-05-14 18:48 — `main` (ea1c8773)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [Medium] data/skill-usage.jsonl:31 — 이전 3개 엔트리는 절대경로(D:\\hoonProJect\\...), 신규 엔트리만 상대경로로 기록. 경로 해석 코드가 cwd 기준으로 resolve하면 이전 항목과 불일치 발생 가능.",
    "- [Medium] skill-eval-report.json, skills/new_skill/skill-eval-report.json — skill_path·report_path를 상대경로로 일괄 변경. 이 JSON을 읽는 코드가 항상 프로젝트 루트 cwd를 보장하는지 확인 필요. 보장 안 되면 경로 파일 not found 런타임 오류.",
    "- [Low] data/skill-usage.jsonl — contract_pass_rate/hidden_pass_rate/runtime_success_rate 전부 0.0, runtime_total 0인 상태에서 candidate 승격. external_eval_passed + historical_score 52만으로 승격되는 것이 의도된 기준인지 명시 없음.",
    "- [Low] data/skill-usage.jsonl — feedback_total_events 27→28→29→30 증가하는데 historical_score 52로 고정. 피드백 누적이 점수에 반영되지 않는 계산 누락 가능성.",
    "- [Info] 커밋 메시지('P4+P2 question set YAML 추가')와 diff 내용 불일치 — 표시된 diff에는 YAML 추가 없고 JSON 경로 정규화만 있음. skills/registry.yaml diff가 누락되었거나 커밋 메시지가 잘못 기재된 것으로 보임."
  ]
}
```

---

## 2026-05-14 18:49 — `main` (0e948338)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Low] `data/skill-usage.jsonl:31` — 새 이벤트만 상대경로(`skills/new_skill/...`) 사용, 기존 29개 엔트리는 절대 Windows 경로 — 로그 파일 내 경로 포맷 불일치. 소비자가 경로를 직접 참조 시 역방향 호환 문제 발생 가능.
- [Low] `skill-eval-report.json`, `skills/new_skill/skill-eval-report.json` — `skill_path` / `report_path`를 상대경로로 변경. CWD가 repo root가 아닌 경우 경로 해석 실패 위험. 소비 코드에서 절대경로 변환 여부 확인 필요.
- [Medium] `data/skill-usage.jsonl:31` — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0`임에도 `draft → candidate` 승격 — 실질적 평가 없이 `external_eval_passed` reason으로 게이트 통과. 프로모션 임계값이 0이거나 로직이 bypass된 것으로 보임.
- [Info] 커밋 메시지에 "P4+P2 question set YAML 추가"라 했으나, 제공된 diff에 `skills/registry.yaml` 실제 내용 변경이 포함되지 않음 — 리뷰 범위 불완전. YAML 추가분 별도 확인 필요.

---

## 2026-05-14 18:50 — `main` (4851c305)

**Context**: feat(stage0-yaml): P4+P2 question set YAML 추가 (goal_clarification + brainstorming)

**Changed (5)**: `data/skill-usage.jsonl, skill-eval-report.json, skills/new_skill/skill-eval-report.json, skills/new_skill/skill-promotion.json, skills/registry.yaml`

### Findings

- [Medium] data/skill-usage.jsonl:31 — 신규 항목의 `report_path`/`promotion_path`가 상대경로(`skills/new_skill/...`)로 바뀌었으나 이전 29개 항목은 절대 Windows 경로(`D:\\hoonProJect\\...`) 유지. append-only 로그 내 경로 포맷 불일치 — 경로 기반 파일 조회 코드가 혼합 포맷을 처리하지 못하면 구버전 레코드에서 FileNotFoundError 발생 가능.
- [Medium] skills/new_skill/skill-eval-report.json — `contract_pass_rate: 0.0`, `hidden_pass_rate: 0.0`, `runtime_total: 0`, `runtime_success_rate: 0.0`인 상태에서 `recommended_stage: "candidate"` 승격. 유일한 근거는 `historical_score: 52`. 승격 임계값 로직이 런타임/계약 검증 없이도 통과하는지 의도적 설계인지 확인 필요.
- [Low] skill-eval-report.json — 루트 레벨 파일의 `static_gate.ok: false`이고 `recommended_stage: "draft"`인데 커밋에 포함됨. 이 파일이 실제 평가 대상인지, 아니면 더미 fixture인지 명확하지 않음 (`skill_path: "dummy"` 참조).
- [Low] skill-eval-report.json:46 — 파일 끝 newline 누락 (`No newline at end of file`). POSIX 규약 위반, 일부 diff 도구에서 오탐 유발.
- [Info] data/skill-usage.jsonl:31 — 상대경로로의 전환 자체는 이식성 측면에서 올바른 방향. 단, 과거 레코드 소급 수정이 정책상 허용되는지 검토 후 일괄 마이그레이션 권장.

---

## 2026-05-15 00:12 — `af-on-af/round1-hook-fix` (399440de)

**Context**: edit: scripts/review_gate.py

**Changed (2)**: `Master_Blueprint.md, scripts/review_gate.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 01:10 — `af-on-af/round1-hook-fix` (777f0a28)

**Context**: edit: core/approval_gate.py

**Changed (2)**: `Master_Blueprint.md, core/approval_gate.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 12:19 — `af-on-af/round1-hook-fix` (a4cb42e9)

**Context**: edit: agent_launcher.py

**Changed (1)**: `agent_launcher.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 13:51 — `af-on-af/round1-hook-fix` (b1ac6fe4)

**Context**: edit: agent_launcher.py

**Changed (1)**: `agent_launcher.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 14:16 — `af-on-af/round1-hook-fix` (78e6a4be)

**Context**: edit: core/registry_manager.py

**Changed (1)**: `core/registry_manager.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 14:23 — `af-on-af/round1-hook-fix` (1169151b)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

{"findings":"- [Medium] skills/registry.yaml:8,10 — Test-generated tmp paths (`tests/_tmp/af-test-6b8efeb8/...`) committed to a versioned registry. Each test run rewrites these entries, polluting git history and breaking lookups in any environment where that ephemeral tmp dir does not exist.\n- [Low] skills/registry.yaml:12 — `updated_at` churn from test fixtures creates noisy diffs; commit description mentions F12 hardening but this file only shows a fixture artifact, suggesting an unintended staged change.\n- [Info] commit scope mismatch — diff does not contain the env_flag/dual-source/diagnostic logic referenced in the commit message; verify the intended source changes were staged."}

---

## 2026-05-15 14:24 — `af-on-af/round1-hook-fix` (ab50d39a)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [High] skills/registry.yaml:8,10,12 — diff is exactly the F12 bleed the commit claims to harden against: test temp paths (`tests/_tmp/af-test-6b8efeb8/...`) and a fresh `updated_at` were written into the *committed* registry. If the new `_env_flag` gate engaged, this entry should be unchanged; either the gate didn't fire, the test ran without the self-run env flag, or this row was captured before the fix and not reverted.
- [High] skills/registry.yaml:8,10 — `meta_path` / `path` point at ephemeral `tests/_tmp/af-test-*` directories that get cleaned up; any consumer that loads this `abc` entry and resolves the path will hit `FileNotFoundError` at runtime. Stale rows should be pruned, not refreshed with a newer temp hash.
- [Medium] skills/registry.yaml (commit scope) — commit message advertises code-level changes ("env_flag convention + dual-source + diagnostic"), but the only file in this diff is registry data churn. The actual hardening code is either missing from this commit or the registry mutation slipped in unrelated to the claimed scope — both cases warrant splitting/reverting before merge.
- [Medium] skills/registry.yaml — per the prior review thread, `core/registry_manager.py:407 workflow_apply()` still writes `WORKFLOW_PATH` without the `_env_flag` guard; if `skill_procurer` ran during this test, that path likely produced this diff. Until `workflow_apply()` is gated too, F12 hardening cannot prevent registry rewrites end-to-end.
- [Info] No new code in the diff means no unit-test coverage of the env_flag convention is visible here; verify hardening tests live in a separate commit on this branch.

---

## 2026-05-15 14:24 — `af-on-af/round1-hook-fix` (f71ed6b9)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Medium] skills/registry.yaml:8-12 — 테스트 임시 디렉터리(`tests/_tmp/af-test-*`)의 절대 상대 경로가 production 레지스트리에 커밋됨. 테스트 실행 시마다 hash가 바뀌어 무의미한 diff/머지 충돌 유발.
- [Medium] skills/registry.yaml:8,10 — `meta_path`/`path`가 곧 사라질 임시 경로를 가리켜, 다른 환경에서 레지스트리 로드 시 FileNotFoundError 가능 (last_test_ok=true와 모순).
- [Low] skills/registry.yaml — 테스트가 production registry를 직접 쓰고 있음을 시사. 테스트 격리(별도 fixture registry) 또는 `.gitignore`/post-test cleanup으로 분리 필요.
- [Info] 커밋 메시지("F12 hardening — env_flag convention + dual-source + diagnostic")와 실제 diff(레지스트리 타임스탬프/경로 갱신만) 불일치 — 실제 hardening 변경이 누락됐거나 잘못된 파일이 staged.

---

## 2026-05-15 14:25 — `af-on-af/round1-hook-fix` (75adb845)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [High] skills/registry.yaml:8-12 — 테스트 임시 경로(`tests/_tmp/af-test-6b8efeb8/...`)가 production registry에 쓰여 있음. F12 가드(`AF_DISABLE_REGISTRY_WRITE`)가 실제 테스트 실행 경로에서 동작하지 않았다는 증거 — 커밋 메시지("F12 hardening")와 모순.
- [High] skills/registry.yaml:8,10 — `meta_path`/`path`가 절대 경로 성격의 휘발성 tmp 디렉터리를 가리킴. 다음 테스트 라운드에서 즉시 dangling 참조가 되어 registry 무결성 깨짐. 정상이라면 이 항목은 커밋되지 않거나(`abc`가 fixture라면 .gitignore/픽스처 분리), 안정 경로로 정규화돼야 함.
- [Medium] skills/registry.yaml:12 — `updated_at` timestamp만 갱신되는 churn 패턴. 코드 변경 없이 registry diff가 매 self-run마다 발생하면 git 이력 노이즈 + cross-review baseline 오염. F12가 의도대로 동작했다면 이 줄 자체가 안 나와야 함.
- [Info] commit metadata — 커밋 제목은 `fix(self-run): F12 hardening … dual-source + diagnostic`이지만 diff에 실제 가드/진단 코드 변경이 없음. 코드 변경 커밋(75adb845, 78e6a4be)이 별도라면 본 커밋은 "registry 결과물 갱신"으로 분리/재명명 권장.

검증 권고: `git log -p -- core/registry_manager.py core/skill_procurer.py` 로 F12 실제 가드 변경 확인 후, `AF_DISABLE_REGISTRY_WRITE=1`을 self-run 진입 지점(테스트 runner/pytest fixture)에서 export 했는지 재현 — 누락됐다면 본 diff는 F12 미적용의 증상.

---

## 2026-05-15 14:25 — `af-on-af/round1-hook-fix` (eb92f7de)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [High] skills/registry.yaml:8,10 — `tests/_tmp/af-test-*` 경로가 추적 파일에 커밋됨. 테스트 격리 실패 — 테스트가 production registry를 덮어쓰고 있다는 신호 (테스트는 임시 디렉터리에서 분리된 registry를 써야 함).
- [High] skills/registry.yaml — 커밋 메시지("F12 hardening — env_flag convention + dual-source + diagnostic")와 diff 내용 불일치. 실제 F12 hardening 코드 변경은 누락되었고, 테스트 부산물만 staged됨.
- [Medium] skills/registry.yaml:12 — `updated_at` 타임스탬프가 매 테스트 실행마다 churn 발생. 이 파일이 tracked라면 noise 커밋이 반복됨 → `.gitignore` 또는 테스트용 별도 registry 경로 분리 필요.
- [Low] skills/registry.yaml — `af-test-6b8efeb8` 해시 디렉터리는 테스트 종료 후 cleanup되었을 가능성이 높음 → registry의 `meta_path`/`path`는 dangling reference로, lookup 시 FileNotFoundError 위험.

요약: 이 변경은 commit 메시지의 의도(F12 hardening)와 무관한 테스트 누수 부산물로 보입니다. 실제 hardening 패치를 누락한 채 test residue만 stage된 것으로 추정되므로, 1) 진짜 변경을 추가하든가 2) 본 hunk를 unstage하고 테스트가 production registry를 쓰지 않도록 격리하는 fix가 선행되어야 합니다.

---

## 2026-05-15 14:26 — `af-on-af/round1-hook-fix` (617446af)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Low] skills/registry.yaml:8,10 — 테스트 임시 디렉터리(`tests/_tmp/af-test-*`) 경로가 registry에 커밋됨. 테스트 실행마다 경로 hash가 바뀌어 매번 diff 발생, 정작 production skill 경로가 아님. 테스트가 registry.yaml을 직접 쓰지 않도록 격리하거나 `tests/_tmp/` 항목을 커밋 제외해야 함.
- [Info] skills/registry.yaml:12 — `updated_at` 타임스탬프만 갱신되는 noise 커밋. 위 격리가 적용되면 자연 해소.

No security/error-handling issues in this diff.

---

## 2026-05-15 14:26 — `af-on-af/round1-hook-fix` (73fb944d)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [High] skills/registry.yaml:8-12 — Ephemeral test artifact (`tests/_tmp/af-test-6b8efeb8/...`) committed to a tracked registry file. The `meta_path`/`path` point under `tests/_tmp/`, which is a temp scratch dir that won't exist on other checkouts or in the frozen build, breaking any consumer that resolves these paths.
- [High] skills/registry.yaml:1-12 — Test runs are mutating a checked-in registry; each test invocation rewrites `path`/`meta_path`/`updated_at`, producing churn commits and racing with concurrent tests. Tests should write to an isolated registry (tmp dir or fixture copy), not the repo's `skills/registry.yaml`.
- [Medium] skills/registry.yaml — Diff is unrelated to the stated commit subject ("F12 hardening — env_flag convention + dual-source + diagnostic"). Either the wrong file was staged or the real F12 changes are missing from this commit; verify intent before merging.
- [Info] skills/registry.yaml:12 — `updated_at` uses a naive local timestamp (`2026-05-15T14:17:47`, no TZ). Prefer ISO‑8601 UTC with `Z` for reproducibility across machines.

---

## 2026-05-15 14:27 — `af-on-af/round1-hook-fix` (07c062b1)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [Medium] skills/registry.yaml:8-12 — 테스트 임시 디렉터리 경로(`tests/_tmp/af-test-<hash>/...`)가 production registry에 커밋되어 있음. 테스트 격리 누수로, 다른 PC/CI 환경에서 경로 stale → 스킬 로드 실패 가능. 테스트는 자체 임시 registry를 써야 하며, 루트 registry.yaml은 건드리지 말아야 함.",
    "- [Low] skills/registry.yaml:12 — `updated_at` 타임존 부재(naive datetime). registry 다중 PC 동기화 시 비교 모호. ISO 8601 + 'Z' 또는 offset 권장.",
    "- [Info] 커밋 메시지(F12 hardening — env_flag/dual-source/diagnostic)와 실제 diff(테스트 부산물 경로 교체) 불일치. 의도된 변경분이 누락됐거나 본 파일은 커밋에서 제외했어야 함."
  ]
}
```

---

## 2026-05-15 14:27 — `af-on-af/round1-hook-fix` (e719fba2)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Medium] skills/registry.yaml:8-12 — 테스트 임시 경로(`tests/_tmp/af-test-*`)가 production registry에 커밋됨. 테스트 실행 중 실제 registry.yaml이 오염되었으며, 다음 실행 시 존재하지 않는 경로를 참조해 skill 로딩 실패 가능. 테스트는 격리된 registry 사본을 사용해야 함.
- [Low] skills/registry.yaml:1 — 커밋 메시지("F12 hardening — env_flag convention + dual-source + diagnostic")와 실제 diff(테스트 artifact 경로 갱신)가 불일치. 의도된 변경이 아닌 테스트 leak으로 보임.

---

## 2026-05-15 14:28 — `af-on-af/round1-hook-fix` (08fbf36f)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

{"review": "- [Medium] skills/registry.yaml:8-12 — Commit message claims 'F12 hardening — env_flag convention + dual-source + diagnostic' but diff only updates a test temp path (af-test-9648c834 → af-test-6b8efeb8) and timestamp; no env_flag/dual-source/diagnostic code visible here. Either the wrong file is staged or the test artifact leaked into the registry commit.\n- [Medium] skills/registry.yaml:8,10 — `tests/_tmp/af-test-*` paths persisted in production registry. Test tmp dirs are ephemeral; on next run the path becomes a dangling reference. Tests should write to an isolated registry (env-overridden path) rather than mutating the canonical `skills/registry.yaml`.\n- [Low] skills/registry.yaml:12 — `updated_at` bumped without semantic change to the skill (same id/name/version/status). Churn-only diff inflates blame history."}

---

## 2026-05-15 14:28 — `af-on-af/round1-hook-fix` (e796b7fe)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Medium] skills/registry.yaml:8-12 — Test artifact (`tests/_tmp/af-test-*` paths) committed to production registry; ephemeral test skill `abc` should not be persisted in `skills/registry.yaml`. Add tmpdir cleanup or registry isolation for tests.
- [Low] skills/registry.yaml:8,10 — `meta_path`/`path` reference a temp directory (`af-test-6b8efeb8`) that won't exist outside the test run, so any consumer resolving this entry will fail with FileNotFoundError.
- [Info] skills/registry.yaml:12 — Timestamp churn on every test invocation will create noisy diffs; consider writing test registries to a separate fixture path.

---

## 2026-05-15 14:29 — `af-on-af/round1-hook-fix` (e50fe176)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [High] skills/registry.yaml:8-12 — Test fixture pollution: `tests/_tmp/af-test-6b8efeb8/...` paths committed to production registry. These temp dirs are deleted post-test, leaving a broken skill entry whose `path`/`meta_path` resolve to non-existent files at runtime.",
    "- [Medium] skills/registry.yaml:8-12 — Diff scope mismatch with commit message: commit claims `env_flag convention + dual-source + diagnostic` hardening, but the only change is a transient timestamp/hash bump on the `abc` test skill. Either the real hardening code is missing from this commit, or this is unintended leakage from a test run.",
    "- [Low] skills/registry.yaml:5-13 — The `abc` entry appears to be a test-only skill that should never have been persisted to `skills/registry.yaml`; consider registry-write guard for `tests/_tmp/` paths or a separate test registry."
  ]
}
```

---

## 2026-05-15 14:29 — `af-on-af/round1-hook-fix` (34f57246)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

{"review": "No issues found.", "details": "Diff only updates auto-generated test fixture paths (tests/_tmp/af-test-*) and timestamp for the `abc` skill entry in the registry. No code logic, security surface, or error handling changes. The commit message references env_flag convention and diagnostic hardening, but those changes are not present in this file — only registry churn from a test run."}

---

## 2026-05-15 14:30 — `af-on-af/round1-hook-fix` (565aa67d)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Medium] skills/registry.yaml:8-12 — 테스트 임시 경로(`tests/_tmp/af-test-*`)가 운영 레지스트리에 커밋됨. 해당 디렉터리는 테스트 종료 시 사라지므로 production 로드 시 `FileNotFoundError` 발생 가능. 테스트가 registry를 격리 없이 직접 수정하는 것이 근본 원인 — 테스트 전용 fixture/임시 registry로 분리하거나 teardown에서 원복 필요.
- [Low] skills/registry.yaml:12 — `updated_at` 타임스탬프가 매 테스트 실행마다 바뀌어 의미 없는 diff noise를 생성. CI/리뷰 시그널 저하.
- [Info] 커밋 메시지 "F12 hardening"과 실제 변경(테스트 잔재) 불일치 — 의도된 변경이 아니라면 stash/restore 후 재커밋 권장.

---

## 2026-05-15 14:30 — `af-on-af/round1-hook-fix` (c9afe6fd)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Medium] skills/registry.yaml:8-12 — 테스트 임시 경로(`tests/_tmp/af-test-*`)와 타임스탬프가 커밋됨. 테스트 격리 누수로 보임 — `.gitignore` 또는 테스트 정리 훅으로 제외 필요.
- [Low] skills/registry.yaml:8,10 — 휘발성 디렉터리(`af-test-9648c834` → `af-test-6b8efeb8`) 경로가 registry에 영구 저장되면 다음 테스트 실행 시 stale 경로로 깨질 가능성.
- [Info] 커밋 메시지("F12 hardening — env_flag convention + dual-source + diagnostic")와 실제 diff(경로/타임스탬프 갱신만)가 불일치. 본 변경은 실제 hardening이 아닌 테스트 부산물.

---

## 2026-05-15 14:31 — `af-on-af/round1-hook-fix` (b7623224)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [Medium] skills/registry.yaml:8 — Test artifact paths (tests/_tmp/af-test-*) being persisted to the production skill registry. These ephemeral test directories will be invalid after test cleanup, leaving the `abc` skill entry pointing to non-existent paths.",
    "- [Low] skills/registry.yaml:5 — The `abc` skill appears to be a test fixture leaking into the committed registry; consider whether test runs should use an isolated registry file rather than mutating the canonical one.",
    "- [Info] skills/registry.yaml:12 — Only the hash suffix and timestamp changed; commit message references 'F12 hardening — env_flag convention + dual-source + diagnostic' but no code changes are visible in this file. Verify the intended hardening changes (env_flag, dual-source, diagnostic) are committed in the corresponding core/*.py files."
  ]
}
```

---

## 2026-05-15 14:31 — `af-on-af/round1-hook-fix` (253224e3)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

{"review": "- [High] skills/registry.yaml:5-12 — 테스트 임시 경로(`tests/_tmp/af-test-*/`)가 추적되는 registry.yaml에 커밋됨. 테스트 실행마다 hash가 바뀌어 diff churn 발생하고, 다른 환경에서는 존재하지 않는 경로 참조로 skill 로딩 실패 가능.\n- [High] skills/registry.yaml:1 — `abc` 엔트리는 테스트 fixture로 보임. production registry에 테스트 skill이 영구 등록되면 실제 사용자 환경에 노출됨.\n- [Medium] skills/registry.yaml — 커밋 메시지(`F12 hardening — env_flag convention + dual-source + diagnostic`)와 실제 변경(테스트 경로 갱신만)이 불일치. F12 hardening 관련 실질 코드 변경이 누락되었거나 잘못된 파일이 staged됨.\n- [Info] 권장: `tests/_tmp/` 경로는 `.gitignore` 또는 registry write 시 필터링하고, 테스트는 격리된 registry 사본(`AF_TEST_REGISTRY=...`)을 사용하도록 분리."}

---

## 2026-05-15 14:32 — `af-on-af/round1-hook-fix` (18d3d546)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Medium] skills/registry.yaml:5-12 — Test artifact `abc` skill with `tests/_tmp/af-test-*` paths is being persisted in the production registry; this is test pollution that should be cleaned up (registry entry references an ephemeral tmp directory that won't exist post-test).
- [Low] skills/registry.yaml:8,10 — `meta_path`/`path` point to `tests/_tmp/af-test-6b8efeb8/...` which is non-deterministic across runs, causing churn-only diffs every test execution (commit noise, no semantic change).
- [Info] commit scope mismatch — Commit message claims "F12 hardening — env_flag convention + dual-source + diagnostic" but the only changed file is a test-generated registry entry update; the substantive code changes appear missing from this diff.

---

## 2026-05-15 14:32 — `af-on-af/round1-hook-fix` (72363dae)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Medium] skills/registry.yaml:8,10 — Test artifact paths (`tests/_tmp/af-test-*`) committed to production registry; ephemeral test fixture leaking into versioned config will produce broken references after temp dir cleanup.
- [Low] skills/registry.yaml:12 — `updated_at` churn from test runs creates noisy diffs; consider gitignoring or excluding test-generated skill entries from registry.yaml.
- [Info] — Commit message references "F12 hardening — env_flag convention + dual-source + diagnostic" but diff only shows test path/timestamp updates; actual hardening changes appear to be in other commits or missing from this changeset.

---

## 2026-05-15 14:33 — `af-on-af/round1-hook-fix` (2c4d389d)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Low] skills/registry.yaml:8,10,12 — Test artifact paths (tests/_tmp/af-test-*) committed to registry; transient temp directory references will dangle once the tmp dir is cleaned, leaving broken `meta_path`/`path` entries. Consider excluding the `abc` test skill from the tracked registry or resetting it before commit.

---

## 2026-05-15 14:33 — `af-on-af/round1-hook-fix` (5390b170)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

```json
{"review": "- [Medium] skills/registry.yaml:8-12 — 테스트 임시 경로(`tests/_tmp/af-test-*`)가 registry에 영속화됨. 테스트 종료 후 cleanup 누락 또는 registry write가 테스트 격리 외부로 누수. 실제 배포 환경에서는 dead path로 남아 skill 조회 실패 위험.\n- [Low] skills/registry.yaml:12 — `updated_at` 타임스탬프만 갱신되고 본질적 내용 변경 없음. 커밋 노이즈 — `.gitignore` 또는 테스트가 registry.yaml을 건드리지 않도록 격리 필요.\n- [Info] 커밋 메시지(`fix(self-run): F12 hardening`)와 실제 diff(테스트 부산물)가 불일치. F12 hardening 본 변경이 누락되었는지 확인 필요."}
```

---

## 2026-05-15 14:34 — `af-on-af/round1-hook-fix` (2e19ca8c)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [High] skills/registry.yaml:8-12 — 테스트 임시 디렉터리 경로(`tests/_tmp/af-test-*`)가 레지스트리에 커밋됨. 매 테스트 실행마다 hash가 바뀌어 diff churn 발생, 실제 production 스킬 등록과 충돌 가능.
- [High] skills/registry.yaml:1-15 — `abc` 스킬 자체가 테스트 fixture로 보임. 영구 레지스트리에 테스트 산출물이 등록된 상태이므로 등록 로직이 test isolation을 깨고 있을 가능성. F12 hardening 범위에서 registry write path가 tmp 경로를 거부하도록 가드 필요.
- [Medium] skills/registry.yaml:12 — `updated_at` 갱신만으로 의미 있는 변경 없음. 커밋 메시지("F12 hardening")와 실제 diff(경로/타임스탬프 노이즈)가 불일치 — 의도치 않은 부산물이 커밋에 섞여 있는지 확인 필요.
- [Info] 본 diff에는 F12 hardening 관련 실제 코드 변경이 없음. 커밋 본문이 별도 파일에 있는지, 아니면 이 파일만 stage된 누락 커밋인지 검증 권장.

---

## 2026-05-15 14:34 — `af-on-af/round1-hook-fix` (ccfea1f4)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

```json
{
  "review": [
    "- [Info] skills/registry.yaml:8-12 — Test fixture artifact: temp directory path (af-test-9648c834 → af-test-6b8efeb8) and updated_at timestamp churn from test run. Not related to the stated commit message (F12 env_flag/dual-source/diagnostic hardening).",
    "- [Low] skills/registry.yaml:8,10 — `tests/_tmp/af-test-*` paths committed to registry indicate test runs are mutating the tracked registry.yaml. Consider gitignoring test-generated registry entries or using an isolated registry path under AF_TEST_REGISTRY to prevent commit noise.",
    "- [Info] commit-scope mismatch — Diff contains zero F12 hardening changes (no env_flag helper, no dual-source read, no diagnostic). Commit message and payload diverge; the actual F12 code must live in a prior commit or is missing from this changeset."
  ]
}
```

---

## 2026-05-15 14:35 — `af-on-af/round1-hook-fix` (906cfc4a)

**Context**: fix(self-run): F12 hardening — env_flag convention + dual-source + diagnostic

**Changed (1)**: `skills/registry.yaml`

### Findings

- [Low] skills/registry.yaml:8 — Test artifact path (`tests/_tmp/af-test-*`) committed to production registry; transient test sandbox paths leaking into source control will break resolution on other machines once the tmp dir is cleaned.
- [Low] skills/registry.yaml:12 — `updated_at` churn on every test run creates noisy diffs; consider gitignoring or having the test harness restore the registry post-run.
- [Info] commit message — Diff scope (registry.yaml path/timestamp bump) doesn't match commit subject ("F12 hardening — env_flag convention + dual-source + diagnostic"); the substantive code changes appear missing from this changeset.

---

## 2026-05-15 14:35 — `af-on-af/round1-hook-fix` (2211cea8)

**Context**: docs(dogfooding): Round 4c — F12 fix leak verification PASS + F15 finding

**Changed (1)**: `skills/registry.yaml`

### Findings

{"findings":[
"- [High] skills/registry.yaml:8,10 — Test sandbox path leaked into committed registry (tests/_tmp/af-test-6b8efeb8/...). The 'abc' skill entry points to an ephemeral pytest tmpdir that won't exist at runtime, breaking skill resolution in production/deployed builds.",
"- [High] skills/registry.yaml:1-12 — Root cause appears unfixed: a test run is still mutating the real skills/registry.yaml instead of an isolated registry. Round 4c is labeled 'F12 fix leak verification PASS' but this diff is itself evidence of the leak (only the tmp hash + timestamp changed). Re-verify the isolation guard before claiming PASS.",
"- [Medium] skills/registry.yaml:12 — updated_at churn on every test run produces noisy commits and merge conflicts; registry writes from tests should be redirected to a per-run fixture path, not committed.",
"- [Low] skills/registry.yaml — Consider adding the 'abc' test-fixture skill entry to .gitignore-style filtering or pre-commit guard so stray test artifacts cannot reach main."
]}

---

## 2026-05-15 14:55 — `af-on-af/round1-hook-fix` (59e0650d)

**Context**: edit: agent_launcher.py

**Changed (1)**: `agent_launcher.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 15:15 — `af-on-af/round1-hook-fix` (8ad6ea4b)

**Context**: edit: agent_launcher.py

**Changed (1)**: `agent_launcher.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 15:43 — `af-on-af/round1-hook-fix` (225232fc)

**Context**: fix(self-run): split user workspace from runtime state

**Changed (1)**: `docs/code_review/code-review.md`

### Findings

No issues found.

---

## 2026-05-15 15:50 — `af-on-af/round1-hook-fix` (b2d35578)

**Context**: edit: tests/conftest.py

**Changed (3)**: `core/skills/registry.yaml, skills/registry.yaml, tests/conftest.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 20:18 — `af-on-af/round1-hook-fix` (7be43d5a)

**Context**: edit: core/providers/cli.py

**Changed (2)**: `Master_Blueprint.md, core/providers/cli.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 21:35 — `main` (89dc4e8d)

**Context**: edit: agent_launcher.py

**Changed (1)**: `agent_launcher.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-15 22:14 — `main` (4763aa9f)

**Context**: edit: scripts/hook_runner.py

**Changed (2)**: `Master_Blueprint.md, scripts/hook_runner.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 01:27 — `main` (664b638a)

**Context**: edit: core/ise_loop.py

**Changed (11)**: `Master_Blueprint.md, NEXT_STEPS.md, agent_launcher.py, core/agent_worker.py, core/dynamic_orchestrator.py, core/fsa_loop.py, core/ise_loop.py, core/project_pipeline.py, tests/test_dynamic_orchestrator_workspace_scope.py, tests/test_llm_doc_gen_p3_p6.py, tests/test_project_pipeline.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 10:31 — `main` (a709b743)

**Context**: edit: core/agent_worker.py

**Changed (2)**: `Master_Blueprint.md, core/agent_worker.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 10:44 — `main` (3d307f17)

**Context**: edit: core/checkpoint/storage.py

**Changed (2)**: `Master_Blueprint.md, core/checkpoint/storage.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 11:16 — `main` (69f91dba)

**Context**: edit: core/failure_classifier.py

**Changed (1)**: `core/failure_classifier.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 11:35 — `main` (8dddcfdc)

**Context**: edit: tests/test_sync_wrappers.py

**Changed (1)**: `tests/test_sync_wrappers.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 14:31 — `main` (7d7a9030)

**Context**: edit: core/registry_manager.py

**Changed (1)**: `core/registry_manager.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 16:34 — `main` (383afde4)

**Context**: edit: core/registry_manager.py

**Changed (1)**: `core/registry_manager.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 17:27 — `main` (58ec7b09)

**Context**: edit: core/registry_manager.py

**Changed (2)**: `core/registry_manager.py, docs/code_review/code-review.md`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 20:22 — `main` (06cc00d7)

**Context**: edit: tests/test_project_pipeline.py

**Changed (1)**: `tests/test_project_pipeline.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-17 23:02 — `main` (065a5b28)

**Context**: edit: tests/test_ast_engine_smoke.py

**Changed (2)**: `NEXT_STEPS.md, pyproject.toml`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-18 00:07 — `main` (083ea93b)

**Context**: edit: scripts/review_metrics_logger.py

**Changed (3)**: `Master_Blueprint.md, docs/code_review/code-review.md, scripts/review_metrics_logger.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-18 00:49 — `main` (5bd395ce)

**Context**: edit: core/project_task_board.py

**Changed (38)**: `core/project_task_board.py, docs/code_review/code-review.md, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json ... (+23)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-18 11:32 — `main` (2b67b362)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [High] (커밋 전체) — 변경 36개 파일이 전부 `runs/`·`agents/*.yaml`·`dashboard.json`·`context_schema.yaml` 등 데이터/런타임 산출물이다. 커밋 메시지가 명시한 코드 수정(build acceptance `required_capabilities` 주입 제거, `_clean_list` 문자열 가드)에 해당하는 `.py` 소스 변경이 diff에 **전혀 없음** — 메시지와 실제 변경 불일치. 의도한 `core/*.py` 수정이 누락됐거나 다른 커밋에 섞였는지 확인 필요.
- [Medium] 전 파일 — 모든 diff가 줄 끝 문자(CRLF↔LF/trailing whitespace) 정규화 churn뿐, 의미 변경 0. 라인이 통째로 삭제·재추가되어 history·blame 오염. `.gitattributes`로 EOL 고정 후 별도 정리 커밋 권장, 기능 커밋과 분리.
- [Medium] `runs/**/chat_trace.json`, `state.json`, `dp_meta.yaml`, `dp_skill.py`, `dashboard.json` — 파이프라인 실행 시 생성되는 런타임 산출물로 보임. 매 실행마다 재생성되어 diff 노이즈를 유발하므로 `.gitignore` 처리 검토.
- [Info] `architect.yaml`/`logicdev.yaml` 등 페르소나 정의의 trailing whitespace 변경은 동작 영향 없음.

보안·런타임 버그는 발견되지 않음 (검토 범위 내 실행 코드 변경 없음). 핵심은 **커밋 메시지와 변경 내용 불일치** — 실제 `_clean_list`/build acceptance 패치가 어디 있는지 먼저 확인하세요.

---

## 2026-05-18 11:33 — `main` (48fbcb01)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

All 36 files in this changeset are **pure CRLF→LF line-ending churn** — every file reports equal insertions/deletions (1130/1130), content byte-identical apart from line endings. None of the code described in the commit message (`_clean_list` guard, build acceptance `required_capabilities` removal in `core/research_router.py`) is present here.

- [High] (전체 changeset) — 커밋 메시지가 설명하는 `_clean_list` 문자열 가드·build acceptance 주입 제거 코드가 이 변경 세트에 **하나도 없음**. 36개 파일 전부 CRLF→LF 라인엔딩 churn뿐. 메시지와 실제 diff 불일치 — 의도한 `core/*.py` 변경이 누락됐거나 커밋이 잘못 묶임.
- [Medium] projects/agent_factory/runs/** — 생성 산출물(chat_trace.json, state.json, dp_skill.py, dashboard.json)이 라인엔딩만 바뀐 채 커밋됨. git 히스토리 오염. `.gitattributes`에 `* text=auto eol=lf` 지정하거나 `runs/`를 `.gitignore` 처리 권장.
- [Low] projects/agent_factory/runs/r2/dp_skill.py:41 — 파일 끝 newline 없음(`\ No newline at end of file`). 라인엔딩 정규화 시 함께 수정 권장.
- [Info] — `dp_skill.py`의 `propose/apply/_norm` 로직 자체는 변경 없음(라인엔딩만). 보안·버그·에러처리 결함 없음.

권장: 이 커밋은 의도한 코드 변경을 포함하지 않음. `core/research_router.py` 등 실제 수정 파일을 확인하고, 라인엔딩 churn은 별도 정리 커밋으로 분리할 것.

---

## 2026-05-18 11:33 — `main` (1b25bbcf)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Info] projects/agent_factory/* — 제공된 diff 36개 파일은 전부 줄바꿈(CRLF→LF) 정규화 변경뿐. 커밋 메시지가 가리키는 실제 로직 변경(`runs/r2/dp_skill.py`, `runs/r3/dp_skill.py`의 build acceptance `required_capabilities` 주입 제거 + `_clean_list` 문자열 가드)은 truncated diff에 포함되지 않아 검증 불가 — 해당 hunk를 별도로 제출 필요.
- [Low] projects/agent_factory/runs/** — 실행 산출물(`chat_trace.json`, `state.json`, `dp_meta.yaml`)이 줄바꿈 churn만으로 30개 이상 스테이징됨. 런타임 생성물은 `.gitignore` 처리 권장. 의미 없는 diff 노이즈가 실제 코드 리뷰를 가림.
- [Low] 리포지토리 전반 — 줄바꿈 불일치가 반복 발생 중. `.gitattributes`에 `* text=auto eol=lf` 추가로 재발 방지 권장.

보안·에러 처리 관점에서 검토 가능한 변경 없음 — 핵심 변경(`dp_skill.py`)의 실제 diff가 누락되어 `_clean_list` 가드 로직(타입 체크/빈 문자열 처리/주입 제거 후 fallback)을 평가할 수 없습니다. 해당 파일의 변경 hunk를 제공해 주시면 재검토하겠습니다.

---

## 2026-05-18 11:34 — `main` (8e126308)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Info] projects/agent_factory/runs/**, *.yaml, dashboard.json — 36개 파일 변경이 전부 줄바꿈(CRLF↔LF/trailing CR) 차이뿐인 run 아티팩트·설정 노이즈입니다. 커밋 메시지의 실제 코드 수정(`_clean_list`, build acceptance)과 무관하니 이 파일들은 스테이지에서 제외하고 `.gitattributes`로 줄바꿈을 고정하는 게 맞습니다.
- [Info] core/research_router.py — 커밋 제목이 명시한 핵심 변경(`required_capabilities` 주입 제거, `_clean_list` 문자열 가드)이 제공된 diff에 포함돼 있지 않아 검토 불가입니다. 실제 로직 파일 diff를 함께 제시해야 리뷰가 성립합니다.
- [Low] projects/agent_factory/runs/r2/dp_skill.py, runs/r3/dp_skill.py — `.py` 파일이 커밋에 포함되어 Review-Gate(Tier 2~3)가 발화 대상으로 잡을 수 있습니다. 생성된 산출물이라면 diff가 줄바꿈뿐인지 재확인하고 게이트 오발화 여부를 점검하세요.

검토 가능한 diff 범위 내에서는 보안·버그·예외 처리 결함 없음. 단, 핵심 코드 변경이 누락되어 실질 검토는 미완입니다 — `core/research_router.py`의 실제 diff를 제공해 주십시오.

---

## 2026-05-18 11:35 — `main` (b8e27ffb)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Low] projects/agent_factory/runs/**, dashboard.json, *.yaml — 34개 파일이 순수 줄바꿈/후행공백 변경(CRLF↔LF)만 포함. 실제 수정과 무관한 생성물 churn이 diff를 가려 리뷰 신뢰성을 떨어뜨림. `runs/`·`dashboard.json` 등 런타임 산출물은 `.gitignore` 처리 권장, 코드 fix와 별도 커밋 분리.
- [Info] runs/r2/dp_skill.py, runs/r3/dp_skill.py — 커밋 메시지의 핵심 변경(`_clean_list` 문자열 가드, build acceptance `required_capabilities` 주입 제거)이 제공된 diff에 보이지 않음(whitespace-only로 표시). 실제 가드 로직·엣지케이스(빈 문자열/None/비-list 입력)를 이 diff만으로 검증 불가 — 해당 파일의 실 변경분 diff 필요.
- [Info] 보안·에러 처리 관점에서 가시 범위 내 결함 없음. 단, `_clean_list` 가드는 비-iterable·dict 입력 시 동작이 핵심이므로 별도 확인 요망.

No critical/high issues found in the visible diff.

---

## 2026-05-18 11:35 — `main` (dd439f73)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [High] (전체 36개 파일) — diff가 전부 줄바꿈 정규화(CRLF↔LF) 변경뿐. 커밋 메시지가 명시한 `required_capabilities` 주입 제거 / `_clean_list` 문자열 가드 변경이 이 diff에 없음. 실제 수정은 `core/*.py`에 있어야 하나 변경 파일 목록에 코드 파일이 없어 핵심 fix를 검증 불가.
- [Medium] projects/agent_factory/runs/** , dashboard.json, chat_trace.json, state.json — 생성 산출물(run 아티팩트)이 추적 대상. 줄바꿈 변경만으로 36개 파일이 diff에 잡힘 → `.gitignore` 처리 권장. 실코드 변경과 노이즈가 섞여 리뷰·blast-radius 판정 방해.
- [Low] runs/r2/dp_skill.py, runs/r3/dp_skill.py — `.py` 확장자라 review-gate가 Tier 2~3로 오분류할 수 있음. 생성 샘플임을 경로/패턴으로 게이트에서 제외 확인 필요.
- [Info] — 줄바꿈 일관성 자체는 개선이나, 의도된 fix 커밋에 섞으면 회귀 추적이 어려움. 줄바꿈 정규화는 별도 커밋 + `.gitattributes`(`* text=auto eol=lf`)로 고정 권장.

검증 한계: 제공된 diff가 줄바꿈 churn만 담고 있어 B-2 ①(build acceptance / `_clean_list`)의 실제 구현 정합성은 이 입력만으로 평가할 수 없음. 해당 `core` 변경 diff를 별도로 받아야 정상 리뷰 가능.

---

## 2026-05-18 11:36 — `main` (ec0cccf5)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Medium] (commit scope) — 커밋 메시지는 `core/*.py`의 코드 수정(`build acceptance required_capabilities 주입 제거`, `_clean_list 문자열 가드`)을 명시하지만, 제시된 diff 36개 파일은 전부 `projects/agent_factory/runs/`·`agents/`·`dashboard.json` 등 **생성 산출물**뿐임. 실제 리뷰 대상인 소스 변경이 diff에 없어 검증 불가 — `core/research_router.py` diff를 별도로 확인해야 함.

- [Low] all files — 변경 내용이 전부 **줄 끝 공백/개행(CRLF↔LF 추정) churn**임. 의미 있는 데이터 변경 없음. `.gitattributes`에 `* text=auto eol=lf` 미설정으로 추정되며, 매 실행마다 산출물이 무의미하게 diff에 잡힘.

- [Low] projects/agent_factory/runs/**, dashboard.json, skill-lock.yaml — 파이프라인 실행 산출물(`chat_trace.json`, `state.json`, `dp_skill.py`, `dp_meta.yaml`)이 git 추적 중. 코드 fix 커밋에 함께 묶이면 리뷰 노이즈와 머지 충돌을 유발. `.gitignore` 처리 검토 권장.

- [Info] — 제공된 diff 범위에서 보안·버그·에러 처리 결함은 발견되지 않음(데이터 산출물 한정). 실질 리뷰는 `_clean_list` 가드 및 build acceptance 변경 소스 확인 후 가능.

---

## 2026-05-18 11:36 — `main` (00b47e6f)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Medium] projects/agent_factory/runs/**, dashboard.json, agents/*.yaml, context_schema.yaml — 36개 파일 전부 줄바꿈/후행 공백 정규화(CRLF→LF)만 발생한 런타임 생성 산출물. 실제 `_clean_list`/build acceptance 코드 수정과 무관한 노이즈이며, `runs/`·`dashboard.json`·`chat_trace.json`·`state.json`은 생성물이므로 `.gitignore` 처리 후 커밋에서 제외해야 함. 현재 diff로는 실제 변경을 검토 불가.
- [High] (검토 불가) — 커밋 메시지의 핵심 변경(`build acceptance required_capabilities 주입 제거`, `_clean_list` 문자열 가드)에 해당하는 `core/*.py` 파일이 제공된 diff에 전혀 없음. 코드 수정과 산출물 churn이 같은 커밋에 섞여 실제 로직 변경을 리뷰할 수 없음 — 분리 커밋 필요.
- [Info] 산출물 파일의 일괄 line-ending 변경은 OS/에디터 간 체크아웃 차이일 가능성이 큼. `.gitattributes`에 `* text=auto` 또는 해당 경로 `-text` 지정으로 재발 방지 권장.

핵심 코드(`_clean_list` 가드, build acceptance 주입 제거)는 diff에 포함돼 있지 않아 보안·버그·예외처리 관점의 실질 검토가 불가능합니다. 해당 `core/*.py` 변경분을 별도로 제시해 주시면 다시 리뷰하겠습니다.

---

## 2026-05-18 11:37 — `main` (4951e582)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Medium] projects/agent_factory/runs/** — 표시된 diff 전체가 CRLF→LF/후행 공백 정규화 노이즈일 뿐, 커밋 메시지의 실제 변경(`required_capabilities` 주입 제거, `_clean_list` 문자열 가드)은 이 diff에 없음. 로직 변경을 검토할 수 없음.
- [Medium] projects/agent_factory/runs/run_*/chat_trace.json, wf_*/state.json, dashboard.json — 런타임 생성 산출물이 버전 관리되며 매 실행마다 churn 발생. `.gitignore` 처리 대상으로 보임. 36개 파일 중 대부분이 이 부류.
- [Low] (커밋 위생) — 대량 줄바꿈 재작성과 실제 버그 수정이 한 커밋에 섞여 blame/리뷰가 오염됨. 정규화는 별도 커밋으로 분리 권장.
- [Info] agents/*.yaml, context_schema.yaml — 내용 변경 없음, 줄 끝 문자만 변경. 기능 영향 없음.

검토 한계: 커밋 제목이 명시한 핵심 수정(build acceptance 주입 제거, `_clean_list` 가드)에 해당하는 `core/*.py` diff가 제공된 변경분에 포함되어 있지 않아 해당 로직의 보안·버그·예외처리 검증은 불가. 실제 코드 hunk를 제시해 주면 재검토 가능.

---

## 2026-05-18 11:38 — `main` (eee86093)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Info] (전 파일) — 표시된 36개 파일 diff는 전부 생성 산출물(`runs/`, `dashboard.json`, `agents/*.yaml`, `context_schema.yaml`)의 줄끝 공백/개행 정규화 변경뿐. 기능 변경 없음.
- [Medium] 커밋 범위 불일치 — 커밋 메시지는 "build acceptance required_capabilities 주입 제거 + `_clean_list` 문자열 가드" 코드 수정인데, 변경 파일에 해당 소스(`core/*.py`, research_router 모듈)가 없음. 실제 로직 변경 파일이 누락됐거나, 산출물 재생성 노이즈가 커밋에 섞여 의도와 다른 diff가 됨.
- [Low] `runs/r2/dp_skill.py`, `runs/r3/dp_skill.py` — 변경 목록에 포함되나 diff 본문이 제공된 발췌에 없어 `_clean_list` 가드 실체를 검증 불가. 빈 문자열/None/리스트 외 타입 입력에 대한 가드 동작은 별도 확인 필요.
- [Low] 산출물 공백 정규화가 커밋에 동반됨 — 향후 산출물 재생성마다 동일 noise diff 재발 가능. `runs/` 산출물을 `.gitignore` 처리하거나 정규화 규칙을 고정할 것을 권장.

검증 한계: 제공된 diff에는 보안/버그/에러 처리에 영향을 주는 실행 코드 변경이 포함되어 있지 않아, 커밋 제목이 가리키는 실제 수정(주입 제거·문자열 가드)의 정합성은 이 리뷰 범위에서 확인되지 않음. 해당 소스 파일을 diff에 포함해 재리뷰 권장.

---

## 2026-05-18 11:38 — `main` (12983f81)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [High] (commit scope) — 커밋 메시지는 `research_router.py` 빌드 수용/`_clean_list` 변경을 명시하나, 변경 파일 36개는 전부 `projects/agent_factory/runs/` 산출물·에이전트 YAML뿐. 실제 코드 변경이 이 diff에 없어 리뷰로 검증 불가. 코드 파일이 누락 커밋됐는지 확인 필요.
- [Medium] projects/agent_factory/runs/** — `chat_trace.json`, `state.json`, `dp_skill.py`, `dp_meta.yaml` 등은 파이프라인 실행 산출물(generated). 줄바꿈/후행 공백 churn만으로 36개 파일이 스테이징됨 — `.gitignore`에 `runs/` 추가 권장. 매 실행마다 무의미한 diff 노이즈 발생.
- [Low] architect.yaml:1 / logicdev.yaml:1 / context_schema.yaml:1 / dashboard.json:1 — 내용 변경 0, 순수 line-ending 정규화(CRLF↔LF 또는 후행 공백 제거)뿐. 의도된 변경이 아니면 되돌리고, 의도면 `.gitattributes`로 `eol` 고정 권장.

검토 결론: 이 diff에는 보안·버그·에러 처리 관점에서 검토할 **실질 코드 로직이 없습니다**. 전부 생성 산출물의 줄바꿈 churn입니다. 커밋 메시지가 기술한 `_clean_list` 문자열 가드와 build acceptance 주입 제거 코드를 별도로 제시해 주시면 정식 리뷰하겠습니다.

---

## 2026-05-18 11:39 — `main` (704fd2df)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Medium] (commit scope) — 36개 파일 중 대부분이 stated fix(`_clean_list`/build acceptance)와 무관한 생성 산출물(`runs/*/chat_trace.json`, `dashboard.json`, `agents/*.yaml`, `context_schema.yaml`)의 줄바꿈/후행공백 churn임. 커밋 1개에 무관 변경을 섞으면 blast radius·리뷰·revert가 어려워짐. 실제 B2 수정만 분리 커밋 권장.
- [Medium] .gitattributes 부재 — diff 전 줄이 CRLF↔LF(또는 후행 CR) 토글로 재작성됨. 프로젝트가 Windows(`C:\Project`)/darwin 양쪽에서 편집되어 줄바꿈 churn 반복 발생. `* text=auto eol=lf` 또는 해당 경로 `-text` 추가로 재발 방지.
- [Low] `projects/agent_factory/runs/**` — 런타임 실행 산출물(`state.json`, `chat_trace.json`, `dp_skill.py` 등)이 버전관리됨. `.gitignore` 처리 검토 필요. 의도적 픽스처라면 무방.
- [Info] 핵심 수정(`runs/r2,r3/dp_skill.py`의 `_clean_list` 문자열 가드, build acceptance `required_capabilities` 주입 제거)이 제공된 diff에 truncate되어 보이지 않음 — 실질 로직 검토 불가. 해당 diff 제공 시 재검토 필요.

No issues found in the visible diff portion itself (순수 줄바꿈 변경, 의미 변화 없음).

---

## 2026-05-18 11:39 — `main` (53bec06b)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Info] (all 36 files) — 표시된 diff는 전부 CRLF↔LF / 트레일링 `\r` 정규화 churn일 뿐, 의미 있는 코드 변경 없음. `architect.yaml`·`logicdev.yaml`·`context_schema.yaml`·`dashboard.json`·`dp_skill.py` 등 내용은 동일.
- [Low] runs/r2/dp_skill.py, runs/r3/dp_skill.py — 생성 산출물(run artifacts)이 라인엔딩 변경만으로 커밋에 포함됨. `.gitattributes`에 `* text=auto eol=lf` 또는 `runs/` 디렉터리 gitignore 검토 권장 — 매 실행마다 무의미한 diff 재발.
- [Info] 커밋 메시지가 명시한 실제 수정(`_clean_list` 문자열 가드, build acceptance `required_capabilities` 주입 제거)에 해당하는 `core/*.py` 변경이 이 diff 36개 파일에는 **포함되어 있지 않음**. 리뷰 대상 범위와 커밋 의도가 불일치 — 실제 로직 변경분이 별도 커밋/스테이지에 있는지 확인 필요.

보안·버그·에러 처리 관점에서 이 diff 자체에는 결함 없음. 단, 의도된 로직 수정이 리뷰 범위에 누락되어 정상 검증 불가.

---

## 2026-05-18 11:40 — `main` (0ad22863)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

요청한 코드 리뷰입니다. 다만 제공된 diff에는 **커밋 메시지가 말하는 실제 코드 변경(`_clean_list`, `required_capabilities`)이 전혀 없습니다.** 36개 변경 파일 전부 run 산출물·agent config이며, 모든 라인이 줄바꿈(CRLF→LF 추정) 차이로만 삭제·재추가되었습니다.

- [Medium] (commit) — 커밋 메시지는 `build acceptance required_capabilities 주입 제거 + _clean_list 가드` 코드 수정을 표방하나, changeset 36개 파일은 전부 `runs/`, `dashboard.json`, `chat_trace.json`, `agents/*.yaml` 등 생성 산출물의 줄바꿈 정규화뿐. **실제 코드 fix가 이 커밋에 누락**됨 — `core/` 파일이 별도 커밋에 있는지 확인 필요.
- [Low] projects/agent_factory/runs/** — run 산출물(`dp_skill.py`, `chat_trace.json`, `state.json`)이 커밋에 포함. 생성물이라면 `.gitignore` 처리 검토. 줄바꿈 churn이 진짜 변경을 가린다.
- [Info] (전반) — 줄바꿈 혼재 방지를 위해 `.gitattributes`(`* text=auto eol=lf`) 도입 권장. 현재 산출물이 CRLF로 쓰여 매 실행마다 diff 노이즈 발생.
- [Info] (리뷰 범위) — diff가 truncate되어 `core/research_router.py` 등 핵심 로직은 검토 불가. 실제 `_clean_list` 문자열 가드 / 주입 제거 로직은 별도로 제출해 주셔야 정상 리뷰 가능합니다.

핵심: 보안·버그 관점 결함은 보이지 않으나, **이 커밋은 커밋 메시지와 내용이 불일치**합니다. 실제 코드 변경 diff를 받으면 다시 리뷰하겠습니다.

---

## 2026-05-18 11:41 — `main` (fd6723dc)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [High] (commit-wide) — 커밋 메시지는 `required_capabilities` 주입 제거 + `_clean_list` 문자열 가드를 명시하지만, 제시된 diff에는 해당 코드 변경(`dp_skill.py`의 실제 로직, `_clean_list` 정의)이 전혀 없음. 실제 fix가 누락됐거나 별도 미스테이지 상태 — 커밋 내용과 메시지 불일치.
- [Medium] architect.yaml:1-18, logicdev.yaml:1-19, context_schema.yaml:1-8, dashboard.json:1+ — 전 라인이 동일 내용으로 삭제·재추가됨. 트레일링 공백/CRLF 정규화 churn만 발생. 의미 변경 0인데 36개 파일을 오염시켜 실제 diff를 가리고 머지 충돌·blame 손상 유발. 이 커밋에서 분리하거나 되돌릴 것.
- [Medium] runs/run_*/chat_trace.json, runs/wf_*/state.json, runs/r2·r3/dp_meta.yaml — 파이프라인이 매 실행마다 재생성하는 산출물이 git 추적 중. `.gitignore` 처리 후 추적 해제 권장. 현재는 매 실행이 무관한 변경을 만들어 리뷰 신호를 묻음.
- [Info] — `_clean_list` 문자열 가드의 정합성(단일 str 입력 시 char 단위 분해 방지 등)은 해당 함수 diff가 없어 검증 불가. 코드 본문 포함한 재리뷰 필요.

요약: 이 diff는 줄바꿈/공백 정규화 noise가 전부이며, 커밋 메시지가 약속한 실질 수정은 확인되지 않음. 게이트 통과 전 (1) 산출물 파일 언스테이지, (2) 실제 `dp_skill.py`/`_clean_list` 변경 포함 여부 확인 필요.

---

## 2026-05-18 11:41 — `main` (c213166d)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (36)**: `projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473949_Architect/chat_trace.json ... (+21)`

### Findings

- [Low] projects/agent_factory/agents/architect.yaml, logicdev.yaml, context_schema.yaml, dashboard.json — 변경 내용이 전부 trailing whitespace / 줄끝(CRLF↔LF) 정규화 noise. 커밋 메시지(`_clean_list 문자열 가드` 등 로직 수정)와 무관한 churn이 diff를 오염시킴. `.gitattributes`로 줄끝 고정 권장.
- [Low] projects/agent_factory/runs/** (chat_trace.json, state.json, dp_meta.yaml 등 다수) — 런타임 산출물이 버전 관리에 포함돼 매 실행마다 noise 커밋 발생. `.gitignore` 처리 검토 필요.
- [Info] runs/r2/dp_skill.py, runs/r3/dp_skill.py — 커밋 메시지가 지목한 실제 로직 변경(`required_capabilities` 주입 제거, `_clean_list` 가드)이 제공된 diff에 포함되지 않아(절단됨) 검증 불가. 해당 hunk를 별도로 확인해야 함.

제공된 diff 범위 내에서는 보안/버그/에러 처리 결함 없음 — 전부 무해한 공백 변경. 단, 핵심 로직 파일(`dp_skill.py`)의 실제 변경분이 누락되어 완전한 리뷰는 불가하다.

---

## 2026-05-18 11:42 — `main` (6068ea15)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (37)**: `NEXT_STEPS.md, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json ... (+22)`

### Findings

- [Info] (commit `6068ea15`) — 커밋 메시지는 `core/project_task_board.py`의 `_clean_list` 문자열 가드 + build acceptance 주입 제거를 명시하나, 변경 파일 목록 37개에 `core/project_task_board.py`가 없음. 실제 코드 수정이 이 changeset에 포함되지 않았거나 별도 커밋으로 분리됨 — 확인 필요.

- [Medium] projects/agent_factory/runs/** — `chat_trace.json`, `state.json`, `dp_skill.py`, `dp_meta.yaml` 등 파이프라인 런 부산물 30+개가 스테이징됨. CLAUDE.md 및 NEXT_STEPS 본문("`projects/agent_factory/` 변경은 테스트 부산물(커밋 제외)") 정책과 충돌. `.gitignore` 처리 또는 커밋 제외 권장.

- [Low] NEXT_STEPS.md — B-2를 "완료·push (`dd439f73`)"로 기재하나 현재 HEAD는 `6068ea15`. 참조 해시 정합성 확인 필요(다른 브랜치/후속 커밋 해시일 가능성).

- [Info] architect.yaml/logicdev.yaml/context_schema.yaml/settings.yaml — diff가 잘려 실내용 미확인. agent yaml 변경이 의도된 것인지(테스트 부산물 vs 실제 설정 변경) 분리 검토 필요.

검토 한계: 제공된 diff가 NEXT_STEPS.md와 architect.yaml 일부에서 잘렸고, 핵심 코드 파일 diff가 없어 `_clean_list` 가드·acceptance 주입 제거의 정확성은 검증 불가. 실제 `core/project_task_board.py` diff 제공 시 재검토 권장.

---

## 2026-05-18 11:43 — `main` (e0936678)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (37)**: `NEXT_STEPS.md, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json ... (+22)`

### Findings

**Review — `core/project_task_board.py` (commit `e0936678`)**

No issues found.

검증 내역:
- `_clean_list:127` — `isinstance(str)` 가드 정확. 문자열 char-split 버그 제거. 공유 헬퍼라 전 호출처(`depends_on`/`acceptance`/`artifacts`)가 모두 list를 기대하므로 의도적 char-split 호출처 없음 → 회귀 위험 0.
- `build_project_board:598` — `verification_focus`는 루프 밖 1회 계산, 수정된 `_clean_list` 경유라 문자열 값도 안전. None은 `get()` → `or []`로 처리됨.
- `:625-629` — verify phase에만 주입, `line not in acceptance` dedup 가드 존재. `_clean_list`가 이미 입력측 dedup하므로 이중 안전. 정상.

- [Info] working tree — `projects/agent_factory/runs/**`, `dashboard.json`, 에이전트 YAML 등 다수가 `M` 상태(테스트 부산물). 이번 커밋(5파일)엔 미포함이나 트리를 더럽힘. `.gitignore` 처리 또는 정리 권장.

---

## 2026-05-18 11:44 — `main` (6f739a62)

**Context**: fix(research-router-p2-B2): ① 적용 — build acceptance required_capabilities 주입 제거 + _clean_list 문자열 가드

**Changed (37)**: `NEXT_STEPS.md, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/dashboard.json, projects/agent_factory/runs/r2/dp_meta.yaml, projects/agent_factory/runs/r2/dp_skill.py, projects/agent_factory/runs/r3/dp_meta.yaml, projects/agent_factory/runs/r3/dp_skill.py, projects/agent_factory/runs/run_1772473924_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473928_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473932_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473937_LogicDev/chat_trace.json, projects/agent_factory/runs/run_1772473941_Architect/chat_trace.json, projects/agent_factory/runs/run_1772473945_LogicDev/chat_trace.json ... (+22)`

### Findings

**리뷰 결과 — 핵심 코드(`core/project_task_board.py`)는 정상이나, 브랜치 상태에 실질 문제 발견:**

- [High] 브랜치 분기 — `main...origin/main [ahead 1, behind 1]`. 로컬 HEAD `6f739a62`와 origin의 `dd439f73`는 **동일 커밋 메시지의 B-2 fix가 별개 해시로 중복** 존재(`dd439f73`는 HEAD 조상 아님 — amend/rebase 후 push 불일치 추정). `git pull` 시 머지·충돌 발생, B-2 패치가 이중 적용될 수 있음. 추가 작업 전 reconcile 필요(origin에 정렬 또는 중복 커밋 정리).
- [Medium] NEXT_STEPS.md:4 — "B-2 완료·push(`dd439f73`)"로 명시하나 재개 브랜치 HEAD는 `6f739a62`. 연속성 가이드가 **현재 브랜치에 없는 해시**를 가리킴 → 다른 PC에서 `git show dd439f73`/`git log` 불일치.
- [Low] working tree 37개 중 35개가 `projects/agent_factory/` 런 산출물(테스트 부산물). NEXT_STEPS.md 자체 규칙("커밋 제외")대로 staged 금지 — 현재 staged 0건이라 즉각 위험은 없음, 커밋 시 주의.

핵심 코드 변경(`6f739a62`):
- `_clean_list` `isinstance(str)` 가드 — 정확. 공유 헬퍼라 전 호출처 char-split 버그 동시 해소.
- `build_project_board` verify 주입 — `acceptance`는 항상 `_clean_list` 결과(list)라 `.append` 안전, dedup 가드 정상. 이슈 없음.

권고: 코드 자체는 머지 가능. **커밋 push 전 origin/main 분기부터 해소**하고 NEXT_STEPS.md 해시를 실제 HEAD로 정정할 것.

---

## 2026-05-18 17:03 — `main` (b959d1ab)

**Context**: Claude Code edit session

**Changed (7)**: `Master_Blueprint.md, core/project_pipeline.py, core/researcher.py, core/skill_retrieval_engine.py, skills/dp/meta.yaml, skills/dp/skill-spec.yaml, tests/test_skill_retrieval_engine.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-18 18:41 — `main` (27ac77d5)

**Context**: Claude Code edit session

**Changed (5)**: `Master_Blueprint.md, NEXT_STEPS.md, core/project_pipeline.py, skills/dp/meta.yaml, skills/dp/skill-spec.yaml`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-19 00:28 — `main` (e4c8038c)

**Context**: Claude Code edit session

**Changed (5)**: `.claude/settings.json, Master_Blueprint.md, core/dynamic_orchestrator.py, core/project_task_board.py, tests/test_project_task_board_dispatch.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-19 01:03 — `main` (bcc4c223)

**Context**: Claude Code edit session

**Changed (4)**: `.claude/settings.json, Master_Blueprint.md, core/project_task_board.py, tests/test_project_task_board_dispatch.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-19 22:38 — `2026-05-19-optional-id-normalization` (96c834a2)

**Context**: Claude Code edit session

**Changed (30)**: `.claude/settings.json, Master_Blueprint.md, NEXT_STEPS.md, agent_launcher.py, core/agent_runner.py, core/agent_specializer.py, core/bootstrap_roles.py, core/builder.py, core/capability_intent.py, core/dynamic_orchestrator.py, core/external_skill_candidate_importer.py, core/external_skill_source_ids.py, core/external_skill_sources.py, core/install_candidate_utils.py, core/interactive_chat.py ... (+15)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-19 22:59 — `2026-05-19-optional-id-normalization` (59ed39ef)

**Context**: Claude Code edit session

**Changed (5)**: `.claude/settings.json, Master_Blueprint.md, NEXT_STEPS.md, core/skill_procurer.py, tests/test_skill_procurer_reuse_gate.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-19 23:12 — `2026-05-19-optional-id-normalization` (b48bf7cc)

**Context**: Claude Code edit session

**Changed (4)**: `.claude/settings.json, Master_Blueprint.md, core/skill_procurer.py, tests/test_skill_procurer_reuse_gate.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-20 08:57 — `2026-05-20-research-coverage-gate` (f5ba8c05)

**Context**: Claude Code edit session

**Changed (5)**: `.claude/settings.json, Master_Blueprint.md, core/researcher.py, tests/test_coverage_gate_hoist.py, tests/test_research_system_regression.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-20 19:14 — `2026-05-20-research-coverage-gate` (1fd662c5)

**Context**: Claude Code edit session

**Changed (18)**: `Master_Blueprint.md, NEXT_STEPS.md, core/text_integrity.py, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/settings.yaml, projects/agent_factory/workflow.yaml, scripts/blast_radius.py, scripts/check_pending_review.py, scripts/enqueue_agent_review.py, scripts/hook_runner.py, scripts/prompts/code_critic.txt, scripts/review_gate.py, tests/test_hook_runner_builtins.py ... (+3)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-21 00:21 — `2026-05-20-research-coverage-gate` (0d649032)

**Context**: Claude Code edit session

**Changed (4)**: `Master_Blueprint.md, NEXT_STEPS.md, core/work_item_generator.py, tests/test_work_item_generator_structured_evidence.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-21 01:28 — `2026-05-20-research-coverage-gate` (20c48a0e)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, NEXT_STEPS.md, core/work_item_generator.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-21 16:55 — `2026-05-20-research-coverage-gate` (39b527ce)

**Context**: Claude Code edit session

**Changed (7)**: `Master_Blueprint.md, af.spec, core/interview.py, run_factory_cli.py, skills/dp/meta.yaml, skills/dp/skill-spec.yaml, tests/test_interview.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-21 18:16 — `2026-05-20-research-coverage-gate` (8305791f)

**Context**: Claude Code edit session

**Changed (8)**: `Master_Blueprint.md, core/engine_auth.py, core/interview.py, run_factory_cli.py, skills/dp/meta.yaml, skills/dp/skill-spec.yaml, tests/test_engine_auth_provider_priority.py, tests/test_interview.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-21 18:31 — `2026-05-20-research-coverage-gate` (5e8d9ce0)

**Context**: Claude Code edit session

**Changed (6)**: `Master_Blueprint.md, core/interview.py, run_factory_cli.py, skills/dp/meta.yaml, skills/dp/skill-spec.yaml, tests/test_interview.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-24 23:35 — `2026-05-20-research-coverage-gate` (908727c7)

**Context**: Claude Code edit session

**Changed (7)**: `.claude/agents/af-triad-critic.md, Master_Blueprint.md, af.spec, core/dogfood.py, core/triad.py, tests/test_dogfood.py, tests/test_triad.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 01:43 — `2026-05-20-research-coverage-gate` (037c442b)

**Context**: Claude Code edit session

**Changed (7)**: `Master_Blueprint.md, agent_launcher.py, core/dogfood.py, tests/test_dogfood.py, tests/test_dogfood_cli.py, tests/test_dogfood_integration.py, tests/test_dogfood_isolation.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 10:26 — `2026-05-20-research-coverage-gate` (00298ebe)

**Context**: Claude Code edit session

**Changed (5)**: `Master_Blueprint.md, af.spec, core/review_skill_router.py, tests/test_review_skill_router.py, version.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 13:43 — `2026-05-20-research-coverage-gate` (7b1731ef)

**Context**: Claude Code edit session

**Changed (6)**: `Master_Blueprint.md, NEXT_STEPS.md, af.spec, core/express_router.py, tests/test_express_router.py, version.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 14:34 — `2026-05-20-research-coverage-gate` (e53c6093)

**Context**: Claude Code edit session

**Changed (5)**: `Master_Blueprint.md, NEXT_STEPS.md, af.spec, core/architect_agent.py, tests/test_architect_agent.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 16:22 — `2026-05-20-research-coverage-gate` (d423ff71)

**Context**: Claude Code edit session

**Changed (4)**: `Master_Blueprint.md, NEXT_STEPS.md, core/dogfood.py, tests/test_dogfood_integration.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 17:42 — `2026-05-20-research-coverage-gate` (e629af28)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/spec_compiler.py, tests/test_spec_compiler.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 18:10 — `2026-05-20-research-coverage-gate` (73339f1c)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/dogfood.py, tests/test_dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 20:02 — `2026-05-20-research-coverage-gate` (b0a582c8)

**Context**: Claude Code edit session

**Changed (2)**: `Master_Blueprint.md, core/dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 20:26 — `2026-05-20-research-coverage-gate` (07f5c95c)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/spec_compiler.py, tests/test_spec_compiler.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 21:59 — `2026-05-20-research-coverage-gate` (8cf904aa)

**Context**: Claude Code edit session

**Changed (7)**: `Master_Blueprint.md, NEXT_STEPS.md, core/dogfood.py, core/planner.py, tests/test_dogfood.py, tests/test_dogfood_isolation.py, tests/test_planner.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 23:05 — `2026-05-20-research-coverage-gate` (38343f4c)

**Context**: Claude Code edit session

**Changed (13)**: `Master_Blueprint.md, core/dogfood.py, core/premortem.py, core/utils.py, run_output.txt, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py, syncCompyne/workspace_context_cli.py, tests/test_dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-25 23:23 — `2026-05-20-research-coverage-gate` (ea3afeba)

**Context**: Claude Code edit session

**Changed (14)**: `Master_Blueprint.md, core/agent_worker.py, core/utils.py, core/warning_stats.py, run_output.txt, scripts/test_gap_analyzer.py, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py, syncCompyne/workspace_context_cli.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 01:03 — `2026-05-20-research-coverage-gate` (6ae99a08)

**Context**: Claude Code edit session

**Changed (12)**: `Master_Blueprint.md, core/utils.py, docs/code_review/code-review.md, run_output.txt, syncCompyne/AGENTS.md, syncCompyne/LOG_COMMANDS.md, syncCompyne/PROJECT_LOG.md, syncCompyne/WORKSPACE_CONTEXT.md, syncCompyne/memory_store.py, syncCompyne/project_log_cli.py, syncCompyne/workspace_context_cli.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 01:15 — `2026-05-20-research-coverage-gate` (ccd78574)

**Context**: Claude Code edit session

**Changed (2)**: `Master_Blueprint.md, core/providers/cli.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 01:56 — `2026-05-20-research-coverage-gate` (52c26fa5)

**Context**: Claude Code edit session

**Changed (11)**: `Master_Blueprint.md, agent_launcher.py, core/dogfood.py, core/planner.py, core/provider_detect.py, core/spec_compiler.py, core/utils.py, tests/test_dogfood_cli.py, tests/test_planner.py, tests/test_spec_compiler.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 07:20 — `2026-05-20-research-coverage-gate` (6d6fe40a)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 08:01 — `2026-05-20-research-coverage-gate` (b5b2185f)

**Context**: Claude Code edit session

**Changed (2)**: `Master_Blueprint.md, core/dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 08:25 — `2026-05-20-research-coverage-gate` (360a9dc8)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 14:37 — `2026-05-20-research-coverage-gate` (38a4dfe3)

**Context**: Claude Code edit session

**Changed (15)**: `Master_Blueprint.md, NEXT_STEPS.md, agent_launcher.py, core/dogfood.py, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/docs/architecture.md, projects/agent_factory/docs/change_history.md, projects/agent_factory/policies.yaml, projects/agent_factory/settings.yaml, projects/agent_factory/workflow.yaml, tests/test_dogfood.py, tests/test_dogfood_cli.py, tests/test_dogfood_integration.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 17:01 — `2026-05-20-research-coverage-gate` (378977e5)

**Context**: Claude Code edit session

**Changed (8)**: `Master_Blueprint.md, core/dogfood.py, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/settings.yaml, projects/agent_factory/workflow.yaml, tests/test_dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 17:45 — `2026-05-20-research-coverage-gate` (b5a382fd)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/dogfood.py, tests/test_dogfood_isolation.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 17:50 — `2026-05-20-research-coverage-gate` (d35d590f)

**Context**: Claude Code edit session

**Changed (2)**: `Master_Blueprint.md, core/dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 18:40 — `2026-05-20-research-coverage-gate` (d53940b4)

**Context**: finalize-time docs sync for dogfood

**Changed (6)**: `.githooks/post-commit, Master_Blueprint.md, core/dogfood.py, scripts/blueprint_updater.py, tests/test_blueprint_updater.py, tests/test_dogfood_isolation.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 21:12 — `dogfood/1779797383-fa016088` (b781243a)

**Context**: dogfood finalize: core/utils.py에 clamp_ratio(value: float, lo: float = 0.0, hi: float = 1.0) -> float 함수 추가. value를 [lo, hi] 범위로 클램프. test

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-26 23:39 — `2026-05-20-research-coverage-gate` (a787df43)

**Context**: Claude Code edit session

**Changed (4)**: `Master_Blueprint.md, NEXT_STEPS.md, core/dogfood.py, tests/test_dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 00:24 — `2026-05-20-research-coverage-gate` (aec5f14e)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/dogfood.py, tests/test_dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 00:41 — `2026-05-20-research-coverage-gate` (e7a0b523)

**Context**: Claude Code edit session

**Changed (2)**: `Master_Blueprint.md, core/dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 00:45 — `dogfood/1779810109-8664dd2e` (0b0da33b)

**Context**: dogfood finalize: core/utils.py에 mode(values: list[int | float]) -> float 함수 추가. 빈 리스트이면 ValueError. 값이 여러 개이면 첫 번째 최빈값 반환. tests/test_uti

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 01:21 — `2026-05-20-research-coverage-gate` (77f56047)

**Context**: Claude Code edit session

**Changed (4)**: `Master_Blueprint.md, NEXT_STEPS.md, core/premortem.py, tests/test_premortem.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 01:59 — `2026-05-20-research-coverage-gate` (171b7a49)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/premortem.py, tests/test_premortem.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 08:44 — `dogfood/1779838885-d70ad991` (69443656)

**Context**: dogfood finalize: core/utils.py에 variance(values: list[int | float]) -> float 함수 추가. 빈 리스트이면 ValueError. 분산 공식: sum((x - mean)^2 for x in 

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 13:35 — `dogfood/1779856158-36f37033` (778b850f)

**Context**: dogfood finalize: core/utils.py에 std_dev(values: list[int | float]) -> float 함수 추가 (빈 리스트면 ValueError, variance() 활용해 math.sqrt 적용). core/

**Changed (5)**: `Master_Blueprint.md, core/planner.py, core/utils.py, tests/test_planner.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 16:43 — `2026-05-20-research-coverage-gate` (ff5caccb)

**Context**: Claude Code edit session

**Changed (70)**: `AGENTS.md, GEMINI.md, MASTER_SPEC_TEMPLATE.md, Master_Blueprint.md, NEXT_STEPS.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md ... (+55)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-27 17:30 — `2026-05-20-research-coverage-gate` (fe930814)

**Context**: Claude Code edit session

**Changed (4)**: `Master_Blueprint.md, NEXT_STEPS.md, core/planner.py, tests/test_planner.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-28 00:00 — `dogfood/1779893903-873d72fd` (4153b013)

**Context**: dogfood finalize: core/utils.py 에 range_span(values: list[int | float]) -> float 함수 추가. max(values) - min(values) 반환. 빈 리스트면 ValueError 발생

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-28 00:47 — `2026-05-20-research-coverage-gate` (41a3aac3)

**Context**: Claude Code edit session

**Changed (63)**: `AGENTS.md, MASTER_SPEC_TEMPLATE.md, Master_Blueprint.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+48)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-28 00:53 — `2026-05-20-research-coverage-gate` (d275fe21)

**Context**: Claude Code edit session

**Changed (63)**: `AGENTS.md, MASTER_SPEC_TEMPLATE.md, Master_Blueprint.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+48)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-28 01:27 — `2026-05-20-research-coverage-gate` (674a9ec9)

**Context**: Claude Code edit session

**Changed (63)**: `AGENTS.md, MASTER_SPEC_TEMPLATE.md, Master_Blueprint.md, PROJECT_LOG.md, Parallelization_plan.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+48)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-28 07:42 — `dogfood/1779921611-7cd5421d` (074de4de)

**Context**: dogfood finalize: core/string_utils.py를 신규 파일로 작성하라: truncate(s: str, max_len: int, suffix: str = '...') -> str 함수 구현. max_len이 len(suffix

**Changed (22)**: `Master_Blueprint.md, data/memory/smoke/test_cat/test_key_123.json, data/memory/test_cat/test_key_123.json, debug_log.txt, debug_log2.txt, docs/AGENT_FACTORY_PITCH.md, docs/ENGINE_FLOW.md, docs/ai_architecture_guide.md, docs/functional_spec.md, docs/registry_schema.md, docs/runtime_modes.md, docs/technical_plan.md, err.txt, factory_manual.md, final_test_log.txt ... (+7)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-28 17:46 — `2026-05-20-research-coverage-gate` (7ebcdf41)

**Context**: Claude Code edit session

**Changed (4)**: `Master_Blueprint.md, core/dogfood.py, tests/test_dogfood.py, tests/test_dogfood_isolation.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-28 23:19 — `2026-05-20-research-coverage-gate` (d9fa56a0)

**Context**: Claude Code edit session

**Changed (64)**: `AGENTS.md, MASTER_SPEC_TEMPLATE.md, Master_Blueprint.md, PROJECT_LOG.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md, agents/himari-test-agent-agent/profile.md ... (+49)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-29 00:07 — `2026-05-20-research-coverage-gate` (9566ece6)

**Context**: Claude Code edit session

**Changed (63)**: `AGENTS.md, MASTER_SPEC_TEMPLATE.md, Master_Blueprint.md, PROJECT_LOG.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agent_launcher.py, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md ... (+48)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-29 13:14 — `2026-05-20-research-coverage-gate` (dea080f9)

**Context**: Claude Code edit session

**Changed (56)**: `AGENTS.md, Master_Blueprint.md, NEXT_STEPS.md, PROJECT_LOG.md, README.md, SPEC_skill_evolution.md, SYNC_GUIDE.md, agents/BuiltanAIAgentThatBecomesSmarter.md, agents/backend-architect-agent/profile.md, agents/backend-dev-agent/profile.md, agents/calculus-tutor-agent/profile.md, agents/chef-agent/profile.md, agents/deadbyte.yaml, agents/general-assistant-agent/profile.md, agents/himari-test-agent-agent/profile.md ... (+41)`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-29 13:22 — `dogfood/1780028360-9b5d3139` (b4bdbf9c)

**Context**: dogfood finalize: core/utils.py에 flatten(lst: list) -> list 함수 추가. 중첩 리스트를 1단계만 평탄화(shallow flatten). 빈 리스트는 []을 반환. tests/test_utils.py에 

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-29 23:46 — `2026-05-20-research-coverage-gate` (da812bdf)

**Context**: Claude Code edit session

**Changed (5)**: `Master_Blueprint.md, NEXT_STEPS.md, core/dogfood.py, tests/test_dogfood.py, tests/test_dogfood_isolation.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-30 01:06 — `dogfood/1780070580-509da39d` (1c62a73f)

**Context**: dogfood finalize: core/planner.py의 _build_investigation_steps() 함수를 확장하여 R5+ assumption 리스크도 investigation step으로 변환한다. 현재 구현은 R20+ gap ri

**Changed (3)**: `Master_Blueprint.md, core/planner.py, tests/test_planner.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-31 14:16 — `2026-05-20-research-coverage-gate` (62f8f3a9)

**Context**: Claude Code edit session

**Changed (4)**: `Master_Blueprint.md, agent_launcher.py, core/dogfood.py, tests/test_dogfood_isolation.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-31 15:53 — `dogfood/1780210301-3e899fe9` (e2e7d942)

**Context**: dogfood finalize: core/utils.py에 zscore(values: list[int | float]) -> list[float] 함수 추가. 각 원소의 Z-score 반환 (평균 0, 표준편차 1 정규화). 원소 1개이면 [0.0

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-31 21:05 — `2026-05-20-research-coverage-gate` (651dbf30)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/dogfood.py, tests/test_dogfood.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-31 21:11 — `dogfood/1780229193-54d8463a` (4acc6ca1)

**Context**: dogfood finalize: core/premortem.py에 _detect_scope_file_risk() 함수 추가. scope 파일 목록에서 존재하지 않는 파일(예: typo 경로)을 감지해 R11 risk로 리포트. 파일 목록이 비어있거

**Changed (3)**: `Master_Blueprint.md, core/premortem.py, tests/test_premortem.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-31 21:38 — `2026-05-20-research-coverage-gate` (51f688ba)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/planner.py, tests/test_planner.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-31 23:00 — `dogfood/1780235778-8d0d1f80` (d21c0208)

**Context**: dogfood finalize: core/premortem.py에 _detect_stale_test_risk() detector 추가. scope 목록 중 대응하는 tests/test_<stem>.py 파일이 존재하지 않는 .py 파일을 R12 r

**Changed (15)**: `Master_Blueprint.md, core/premortem.py, docs/functional_spec.md, docs/registry_schema.md, docs/runtime_modes.md, docs/technical_plan.md, err.txt, factory_manual.md, implementation_plan.md, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/settings.yaml, projects/agent_factory/workflow.yaml, tests/test_premortem.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-05-31 23:37 — `2026-05-20-research-coverage-gate` (8cced444)

**Context**: Claude Code edit session

**Changed (3)**: `Master_Blueprint.md, core/planner.py, tests/test_planner.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-06-01 00:30 — `dogfood/1780241272-dc1583ae` (d6f30173)

**Context**: dogfood finalize: core/utils.py에 percentile(values: list[int | float], p: float) -> float 함수 추가. values를 정렬해 p번째 백분위수(0.0~100.0)를 선형 보간으로 

**Changed (3)**: `Master_Blueprint.md, core/utils.py, tests/test_utils.py`

_Review skipped (--no-llm or LLM unavailable)_

---

## 2026-06-01 00:53 — `dogfood/1780242570-83d712b2` (5942e745)

**Context**: dogfood finalize: core/premortem.py에 R13 detector 추가: _detect_duplicate_function_risk(intent: str, scope: list[str]) -> PremortomRisk | No

**Changed (13)**: `Master_Blueprint.md, core/premortem.py, docs/runtime_modes.md, docs/technical_plan.md, err.txt, factory_manual.md, implementation_plan.md, projects/agent_factory/agents/architect.yaml, projects/agent_factory/agents/logicdev.yaml, projects/agent_factory/context_schema.yaml, projects/agent_factory/settings.yaml, projects/agent_factory/workflow.yaml, tests/test_premortem.py`

_Review skipped (--no-llm or LLM unavailable)_
