# Agent Factory — Master Blueprint
<!-- last_updated: 2026-04-30 | version: v1.2.22 -->

> **사용 목적**: 전체 코드를 다시 읽지 않고 이 파일만으로 수정·유지보수·기능 추가를 수행한다.
> 코드 수정 시 반드시 해당 섹션을 **같은 커밋**에서 업데이트할 것.

---

## 목차

- [§0 빠른 참조 테이블](#0-빠른-참조-테이블)
- [§1 아키텍처 개요](#1-아키텍처-개요)
- [§2 실행 흐름 (데이터 플로우)](#2-실행-흐름)
- [§3 핵심 서브시스템](#3-핵심-서브시스템)
- [§4 자가진화 루프](#4-자가진화-루프)
- [§5 에이전트 간 통신](#5-에이전트-간-통신)
- [§6 모델 라우팅](#6-모델-라우팅)
- [§7 안전장치](#7-안전장치)
- [§8 빌드 & 배포](#8-빌드--배포)
- [§9 설정 레퍼런스](#9-설정-레퍼런스)
- [§10 의존성 그래프 & 영향 매트릭스](#10-의존성-그래프--영향-매트릭스)
- [§11 알려진 제약·이슈](#11-알려진-제약이슈)
- [§12 변경 이력](#12-변경-이력)

---

## §0 빠른 참조 테이블

### 루트 파일

| 파일 | 역할 | 주요 클래스/함수 |
|------|------|----------------|
| `run_factory_cli.py` | CLI 진입점 (STAGE 1/2/3) | `main()`, `_STAGE1_DISPATCH` (dispatch dict), `_STAGE1_USAGE`, `_is_help_arg()`, `_run_setup_gate()`, `_invoke_nlm_app()`, `__nlm` / `__check-nlm` 숨은 서브커맨드 |
| `agent_launcher.py` | AgentFactory 부트스트랩 | `AgentFactory` |
| `model_utils.py:1-845` | 모델 선택·티어 관리 | `_ROLE_ENGINE_MAP`, `_ROLE_CLI_PREFERENCE`, `pick_provider()` |
| `version.py` | 버전 문자열 | `__version__` |
| `build_exe.py` | PyInstaller 빌드 | `main()` |
| `install-af.ps1` | Windows 설치 스크립트 | Chrome 감지(레지스트리), `__check-nlm` 검증 |
| `install-af.sh` | macOS/Linux 설치 스크립트 (소스모드, venv 기반) | Chrome 감지, `__check-nlm` 검증, curl/wget fallback |
| `af.spec` | PyInstaller 스펙 | hiddenimports 목록 |
| `policy.yaml` | 전역 정책 | engines, skills, task_decomposition |

### core/ 파일

| 파일 | 역할 | 주요 클래스/함수 |
|------|------|----------------|
| `core/agent_runner.py:1-1411` | 에이전트 CLI 실행 | `AgentRunner`, `run()` |
| `core/agent_specializer.py` | 태스크 전용 에이전트 커스터마이즈 | `AgentSpecializer.specialize()` |
| `core/agent_worker.py` | PyInstaller worker 진입점 | `main()` |
| `core/approval_gate.py` | 실행 승인 게이트 | `ApprovalGate` |
| `core/ast_engine.py` | AST 분석 엔진 | — |
| `core/ast_memory_hub.py` | AST 기반 메모리 허브 | `AstMemoryHub` |
| `core/bootstrap_roles.py` | 프로젝트 계획 부트스트랩 에이전트 | `ProjectPlanningDirector` |
| `core/builder.py` | 스킬 코드 생성 샌드박스 | `SandboxedBuilder` |
| `core/config_paths.py` | 경로 상수 중앙화 | `PROJECT_ROOT`, `POLICIES_PATH`, `CANDIDATES_DIR` |
| `core/control_plane_llm.py` | Control-plane CLI-first LLM | `ControlPlaneLLM` |
| `core/cross_verification.py:1-758` | 멀티 CLI 교차검증 | `CrossVerificationLoop` |
| `core/dashboard.py` | 실행 이력 모니터링 | `append_dashboard_run()` |
| `core/destructive_guard.py` | 위험 명령 차단 | `inject_destructive_guard_contract()` |
| `core/design_review_utils.py` | 설계문서 교차검증 공유 유틸 (watcher 관리, 큐 관리, 패턴 매칭) | `is_design_doc()`, `is_code_file()`, `enqueue()`, `ensure_watcher()`, `_try_acquire_spawn_lock()`, `_release_spawn_lock()`, `_matches_glob()`, `INCLUDE_PATTERNS`, `EXCLUDE_PATTERNS`, `SPAWN_LOCK_FILE`, `SPAWN_LOCK_TTL` |
| `core/document_chunker.py` | 문서 청킹 (RAG) | `DocumentChunker`, `DocumentChunk` |
| `core/document_index.py` | Dense+Sparse 하이브리드 검색 | `DocumentIndex` |
| `core/documentation_policy.py` | 주석/문서화 정책 주입 + `.todo.md` board 동기화 | `inject_documentation_contract()`, `write_project_todo()`, `_instruction_status_map()` |
| `core/dynamic_orchestrator.py:1-887` | 멀티 에이전트 비동기 오케스트레이터 (sparse governor) | `DynamicOrchestrator`, `restore_from()` (tick 재기동 복원) |
| `core/nightly_state.py` | 야간 자율 파이프라인 상태 관리 (state_snapshot.json) | `NightlyState`, `load_state()`, `save_state()`, `BudgetState` |
| `core/watchdog.py` | tick 기반 stall 감지 + lineage 상한 감지 | `WatchdogState`, `tick_progress()`, `tick_no_progress()`, `is_lineage_maxed()`, `degrade_lineage()` |
| `core/lineage_ledger.py` | lineage 기반 Level 누적 원장 (atomic file write, `_MAX_LEVEL=5`, success 시 level/attempts 리셋) | `LineageEntry`, `LineageLedger`, `get_lineage_ledger()` |
| `core/memory_system/strategy_ledger.py` | 역할 배정·실패 패턴 영구 원장 (Phase 4) | `StrategyLedger`, `get_strategy_ledger()`, `lookup_best_role()`, `record_role_batch()` |
| `core/engine_auth.py` | CLI 프로바이더 자동 감지·설정 | `auto_configure_cli_provider()` |
| `core/evaluator.py` | 실패 분석 (retry/pivot/abort) | `StrategyEvaluator` |
| `core/executor.py` | 태스크 실행 래퍼 | — |
| `core/failure_classifier.py` | 실패 분류 (infra/impl) | `classify_failure()`, `FailureCategory` |
| `core/run_budget.py` | 글로벌 토큰 예산 추적 | `RunBudget`, `set_run_budget()`, `get_run_budget()` |
| `core/skill_pack_bootstrapper.py` | 외부 CLI 플러그인 감지 (claude-code/codex/gemini) | `SkillPackBootstrapper`, `check_installed()`, `missing()`, `installed()` |
| `core/fsa_loop.py:1-480` | FSA 에스컬레이션 루프 (ISE 파이프라인, 5사이클 제한) | `FSALoop`, `run_mission()`, `_decide_escalation()`, `_try_evolve_failed_skill()`, `_evolution_failed_skills` (run-scoped set) |
| `core/git_manager.py` | 워크스페이스 git 연산 | `GitManager` |
| `core/hooks/event_bus.py` | 훅 라이프사이클 버스 | `HookEventBus` |
| `core/hooks/skill_self_evolution.py` | 주기적 스킬 품질 감사 | `SkillSelfEvolutionHook` |
| `core/hooks/code_review_doc.py` | 실행 후 자동 코드 리뷰 + 문서 업데이트 | `CodeReviewDocHook` |
| `core/hooks/guardrails.py` | 실행 가드레일 | `IntentGateHook` |
| `core/ingestion_pipeline.py` | 문서 인덱싱 파이프라인 | `IngestionPipeline` |
| `core/interactive_chat.py` | 대화형 PDCA 모드 (autosave/resume) | `run_interactive()`, `InteractiveChat.load_session()`, `resume_from_session()` |
| `core/ise_loop.py` | 무한 자가진화 루프 | `ISELoop` |
| `core/llm_engine.py` | LLM API 호출 엔진 | `LLMEngine` |
| `core/manager.py` | 에이전트 생성·로드 | `AgentManager`, `RequirementAnalyzer` |
| `core/memory_system/facade.py` | 메모리 단일 진입점 | `UnifiedMemoryFacade` |
| `core/message_broker.py` | TCP/인메모리 메시지 브로커 | `MessageBroker` |
| `core/model_router.py` | CLI 프로바이더 선택 | `ModelRouter` |
| `core/policy_runtime.py` | 정책 런타임 래퍼 | `PolicyRuntime` |
| `core/project_mailbox.py` | 파일 기반 에이전트 간 메시지함 | `send_agent_message()`, `read_inbox()` |
| `core/project_pipeline.py:1-778` | Phase1(문서)+Phase2(실행) 파이프라인 | `ProjectPipeline` |
| `core/project_task_board.py` | 태스크 보드 상태 관리 + `.todo.md` 동기화 훅 | `update_project_board_task()`, `sync_todo_from_board()` |
| `core/providers/cli.py` | CLI 프로바이더 실행 + 진행 표시 | `execute_cli_chat()`, `_progress_printer()` |
| `core/providers/session_adapter.py` | CLI 세션 hook 설정·연속성 브리지 | `prepare_cli_session()`, `handle_hook_event()` |
| `core/provider_detect.py` | 3-state CLI 프로바이더 감지 + 1h 디스크 캐시 + AF_SKIP_PROVIDER 처리. ThreadPool race condition 수정: installed_set을 ThreadPool 전 1회 계산 후 각 worker에 frozenset 전달 | `ProviderState`, `ProviderProbeResult`, `detect_provider_states()`, `invalidate_cache()`, `_resolve_ping_cmd()`, `_probe_one(provider_id, installed)` |
| `core/providers/registry.py` | 설치된 CLI 목록 (Unix npm fallback 포함) + 교차검증 provider 선택. 멀티스레드 안전: `_installed_cli_cache_lock` double-checked locking 패턴 | `get_requested_cli_providers()`, `pick_review_provider()`, `_unix_npm_global_dirs()`, `_installed_cli_cache_lock` |
| `core/research_engine.py` | NotebookLM 통합 엔진 (사서) | `query_notebooklm()`, `create_notebook()`, `inject_sources()`, `_nlm_cmd_base()`, `_get_archive_notebook_id()` |
| `core/researcher.py` | Himari 리서치 에이전트 (로컬+웹+NotebookLM) | `HimariResearchAgent`, `_collect_web_references()`, `_collect_notebook_summary()` |
| `core/security_guard.py` | AST 분석 + 격리 실행 | `quick_guard()`, `run_isolated()` |
| `core/setup_wizard.py` | 외부 리서치 도구(TAVILY/NotebookLM) 점검·복구 단일 진입점 | `ensure_external_research_capabilities()`, `_find_or_create_archive_notebook()` |
| `core/skill_cache.py` | 스킬 관련성 LRU 캐시 | `OptimizedSkillRelevance` |
| `core/skill_creator.py` | 스킬 생성·진화 | `evolve_skill()` |
| `core/skill_metadata_adapter.py` | YAML/Markdown → SkillMetadata 변환 + SKILL.md fallback | `auto_detect_and_convert()`, `_fill_missing_description()`, `convert_meta_yaml_to_metadata()` |
| `core/skill_enricher.py` | 스킬 메타데이터 자동 생성 | `enrich_skill_metadata()`, `bulk_enrich_all_skills()` |
| `core/skill_eval_harness.py` | 계약/숨겨진/섀도우 테스트 | `SkillEvalHarness` |
| `core/skill_quality_gate.py` | 스킬 품질 게이트 (Quality Plane) — knowledge skill early-return + auto_register 지원 | `SkillQualityGate`, `GateResult`, `_register_knowledge_skill()` |
| `core/evolution_types.py` | Stage-1 공유 타입 (Sprint 1 신규) | `EvolutionDecision`, `EvolutionResult` |
| `core/skill_evolution_bus.py:1-241` | 7단계 캐시 무효화 체인 | `SkillEvolutionBus.on_skill_evolved()` |
| `core/skill_evolution_safety.py` | 스킬 진화 안전망 헬퍼 (Stage 0 임시, Stage 1 흡수 예정) | `verify_evolved_skill_sandbox()`, `rollback_evolved_skill()` |
| `core/skill_forge.py` | 코드 생성→비평→수정 루프 | `SkillForge` |
| `core/skill_procurer.py` | 스킬 조달·forge·평가·승격 | `procure_skill()`, `forge_new_skill()`, `evaluate_and_promote()`, `SkillOrchestrator` |
| `core/skill_loader.py` | 런타임 스킬 동적 로딩 | `AdaptiveSkillLoader` |
| `core/skill_promotion.py` | 스킬 라이프사이클 전환 | `SkillPromotionManager` |
| `core/skill_registry.py` | 스킬 메타데이터 중앙 저장소 | `SkillRegistry` (싱글톤) |
| `core/swarm_council.py` | 다중 역할 계획·승인 | `SwarmCouncil` |
| `core/document_policy.py` | 금지 토큰 스캔·입력 계약·Jaccard | `scan_forbidden_tokens()`, `jaccard_similarity()` |
| `core/work_item_generator.py` | LLM 기반 work-item 생성 + 금지 토큰 보강 + chained refinement | `generate_work_items()`, `_generate_and_refine()`, `_generate_doc_with_llm()` |
| `core/requirement_llm.py` | LLM 요구사항 분석 + 마크다운 문서 생성 | `execute_requirement_prompt()`, `execute_document_prompt()` |
| `core/work_item_parser.py` | 편집된 마크다운 재파싱 | `sync_board_from_work_items()` |
| `core/control/supervisor.py` | 유지보수 감독 루프 | `Supervisor` |

### 서브디렉토리

| 디렉토리 | 역할 |
|---------|------|
| `core/continuity/` | 오케스트레이터 체크포인트·재개 |
| `core/control/` | 유지보수·감독·롤백 파이프라인 |
| `core/events/` | RunEvent 스키마·FileRunEventStore·SKILL_EVOLVED 등 이벤트 타입 |
| `core/hooks/` | 실행 라이프사이클 훅 |
| `core/memory_system/` | 에피소드·그래프·시맨틱 메모리 |
| `core/providers/` | CLI 프로바이더 (Claude/Gemini/Codex) |
| `skills/` | 스킬 YAML+Python 구현체 |
| `agents/` | 역할별 에이전트 YAML |
| `config/` | Pydantic 설정 스키마 |
| `syncCompyne/` | 세션 간 공유 메모리 (SQLite) |

---

## §1 아키텍처 개요

### 5-레이어 시스템

```
┌─────────────────────────────────────────────────────────┐
│  Layer 5: 사용자 인터페이스                               │
│  run_factory_cli.py ─── interactive_chat.py             │
├─────────────────────────────────────────────────────────┤
│  Layer 4: 파이프라인 오케스트레이션                        │
│  project_pipeline.py ── fsa_loop.py ── ise_loop.py      │
├─────────────────────────────────────────────────────────┤
│  Layer 3: 멀티 에이전트 실행                              │
│  dynamic_orchestrator.py ── agent_specializer.py        │
├─────────────────────────────────────────────────────────┤
│  Layer 2: 단일 에이전트 실행                              │
│  agent_runner.py ── providers/cli.py ── skill_loader.py │
├─────────────────────────────────────────────────────────┤
│  Layer 1: 공유 인프라                                     │
│  memory_system/ ── message_broker.py ── hooks/          │
│  model_router.py ── skill_evolution_bus.py              │
└─────────────────────────────────────────────────────────┘
```

### 실행 모드별 진입점

| 모드 | 플래그 | 진입 경로 | 루프 |
|------|--------|----------|------|
| Interactive (기본) | 인자 없음 | `interactive_chat.py` | 사용자 입력 반복 |
| Approval | `--mode approval` | `project_pipeline.py` | Phase1→승인→Phase2 |
| FSA | `--mode fsa` | `fsa_loop.py` | ISE 에스컬레이션 (Level 1-5), 최대 5 사이클 |
| ISE | `--mode ise` | `ise_loop.py` | 무한 자가진화 |
| Worker | `worker` 서브커맨드 | `agent_worker.py` | 단일 태스크 실행 (PyInstaller 전용) |

---

## §2 실행 흐름

### Flow A: Project Pipeline (Approval 모드)

```
run_factory_cli.py:main()
  │
  ├─ STAGE 1: 내부/숨은 서브커맨드 즉시 분기 (setup gate 우회)
  │   └─ {setup, worker, skill-create, skill-spec, preflight,
  │       skill-eval, skill-promote, __nlm, __check-nlm}
  │       ※ __nlm은 _invoke_nlm_app() 경유로 nlm Typer app을
  │         standalone_mode=False + sys.argv 백업/복원 패턴으로 호출
  │         → frozen exe 환경에서도 SystemExit/argv 오염 없이 안전
  │
  ├─ STAGE 2: _run_setup_gate()
  │   └─ core.setup_wizard.ensure_external_research_capabilities(mode="auto")
  │       (TAVILY/NotebookLM 인증·노트북 점검; 실패해도 stderr 경고만 후 진행)
  │
  ├─ STAGE 3: 일반 실행 분기 (인자 없음 → 대화형, argparse → 태스크 모드)
  │
  ├─ [Phase 1] ProjectPipeline.prepare()
  │   ├─ bootstrap_roles.ProjectPlanningDirector
  │   │   ├─ generate_research_brief()  → project_brief.json
  │   │   ├─ generate_role_plan()       → role_plan.json
  │   │   └─ generate_task_board()      → project_board_state.json
  │   ├─ ingestion_pipeline.run()       → document_index (RAG)
  │   ├─ work_item_generator.generate_work_items()
  │   │   → docs/work-items/{slug}/*.md
  │   └─ approval_gate.initialize()     → execution_open: false
  │
  ├─ [사용자 검토·편집]
  │
  ├─ [Phase 2] ProjectPipeline.execute()
  │   ├─ approval_gate.is_execution_open() → True
  │   ├─ work_item_parser.sync_board_from_work_items()
  │   └─ DynamicOrchestrator.run()
  │       ├─ print_startup_routing_notice()  [model_utils]
  │       ├─ MessageBroker TCP 서버 시작
  │       └─ Lilith LLM 사이클 루프 (max_cycles=compute_max_cycles(), 동적):
  │           ├─ _lilith_decide_next() → 다음 태스크 선택
  │           ├─ AgentSpecializer.specialize(agent, task)
  │           ├─ _run_agent_in_terminal() 또는 _run_agent_inline()
  │           │   ├─ frozen=True → [af.exe worker --task-file ...]
  │           │   └─ frozen=False → [python core/agent_worker.py ...]
  │           └─ _cross_verified_evaluate() on failure
  │               ├─ CrossVerificationLoop.run()
  │               └─ _try_evolve_from_patterns()
  │
  └─ dashboard.append_dashboard_run()
```

### Flow B: FSA 에스컬레이션 루프 (ISE 파이프라인, 5사이클 제한)

> **Phase 3 배선 완료 (2026-04-18)**: `AF_ISE_ENABLED=1`(기본) 시 implementation 실패 경로에서
> `DynamicOrchestrator._execute_agent_task`가 `FSALoop.run_mission`에 위임한다.
> `ISELoop`은 `FSALoop` 얇은 래퍼로 축소됨 (API 호환 유지).
> `lineage_id`는 task.lineage_id 필드에서 읽어 `lineage_ledger.json`에 누적 기록된다.
> `AF_ISE_ENABLED=0` 시 기존 evaluator 경로(retry/blocked)로 fallback.
>
> **Phase A Step 1 갱신 (2026-04-22)**: ISELoop 독자 차별화는 Phase B 이후 예정.
> 현재 `ISELoop`은 `FSALoop` 위임 래퍼이며 단일 에이전트 경로(`--mode ise`)에서만 호출된다.
> 프로젝트 파이프라인 경로(`execution_mode="ise"`)는 `AF_ISE_ENABLED=1` 환경 변수로 FSA 경로를 활성화한다.
> `_should_decompose()` 신규 구현: L5 에스컬레이션 판정(3회 logic/architecture 실패 → 분해 신호).
> 분해 로직 본체(subtask 생성)는 Phase B에서 구현 예정.

```
DynamicOrchestrator._execute_agent_task()  [실 배선 — Phase 3]
  │
  ├─ runner.run() → result
  │   └─ ok=True → RETURN SUCCESS
  │
  ├─ failure_classifier.classify_failure() → INFRA | IMPL
  │   └─ INFRA → board "failed", no retry
  │
  └─ IMPL + AF_ISE_ENABLED=1 (기본):
      ├─ lineage_ledger.is_maxed(lineage_id)?
      │   └─ yes → board "failed" (lineage_maxed), degrade
      └─ FSALoop.run_mission(initial_failure_result=result, lineage_id=...)
          │
          ├─ StrategyLedger + LineageLedger 초기화
          │
          └─ For cycle in 1..5:
              ├─ cycle==1: initial_failure 사용 (실행 건너뜀)
              ├─ StallDetector.check()           [정체 감지]
              ├─ git.commit() / git.rollback()   [워크스페이스 스냅샷]
              ├─ runner.run() → result
              │   └─ ok=True → lineage_ledger.on_success() → RETURN
              ├─ ISEAnalyzer.analyze_failure()   [구조화 분석]
              ├─ _decide_escalation()            [에스컬레이션 레벨 결정]
              ├─ ledger.record_attempt()         [전략 원장 기록]
              ├─ lineage_ledger.on_task_failure(lineage_id, level)  [lineage 누적]
              └─ Level별 ACT:
                  ├─ L1: ISERedesigner.apply_retry_feedback()
                  ├─ L2: ISERedesigner.apply_pivot()
                  ├─ L3: ISERedesigner.redesign_task()
                  ├─ L4: _try_evolve_failed_skill() + redesign_task()
                  └─ L5: _decompose_and_execute() (서브태스크 분할)
```

### Flow D: Phase 4 에피소드 Memory 재사용

> **Phase 4 배선 완료 (2026-04-18)**: `AF_MEMORY_REPLAY=1`(기본) 시 유사 에피소드 top-k
> 힌트가 feature-plan.md에 주입되고, `_pick_owner_role`은 `StrategyLedger` 우선 조회 후
> 키워드 폴백을 수행한다.

```
generate_work_items()                     [work_item_generator.py]
  │
  ├─ _build_episode_hints_section()
  │   ├─ AF_MEMORY_REPLAY=0 → skip
  │   └─ _search_seed_episodes(brief_text, top_k=5)
  │       ├─ memory/episodes/*.md 스캔 (keyword_similarity)
  │       └─ hints 추출 → "Episode Hints" 섹션 주입
  │
  └─ feature-plan.md 생성 + 에피소드 힌트 append

_pick_owner_role(deliverable, roles, workspace)  [project_task_board.py]
  │
  ├─ StrategyLedger.lookup_best_role(deliverable)
  │   └─ 성공률 > 50% + 샘플 ≥ 3건 → ledger role 반환
  └─ 키워드 폴백 (기존 keyword_map)

StrategyLedger (memory/episodes/strategy_ledger.json)
  ├─ record_role_success/failure()        [성공·실패 기록 (단건)]
  ├─ record_role_batch(entries)           [다수 패턴 1회 _save() 일괄 기록 — B2-4]
  ├─ record_failure_pattern()             [패턴 기록]
  ├─ can_auto_save() → bool              [PASS ≥ 80% gate]
  └─ get_warnings_for(task) → [hints]    [경고 주입]
```

### Flow C: 에이전트 단일 실행

```
AgentRunner.run(agent, task_input, workspace)
  │
  ├─ ModelRouter.pick_provider(agent)   → preferred_provider
  ├─ all_cli_providers = get_requested_cli_providers()
  ├─ cli_providers = [preferred] + [fallbacks]
  ├─ inject contracts:
  │   ├─ documentation_policy
  │   ├─ destructive_guard
  │   └─ implementation_language_policy
  ├─ AdaptiveSkillLoader.load(task) → skills (max 12)
  ├─ HookEventBus.run_pre_execute()
  ├─ providers/cli.execute_cli_chat()   → output
  ├─ HookEventBus.run_post_execute()
  └─ return {ok, output, ...}
```

---

## §3 핵심 서브시스템

### §3.1 ProjectPipeline (`core/project_pipeline.py`)
<!-- last_updated: 2026-04-21 -->

**클래스:** `ProjectPipeline`

| 메서드 | 역할 | 출력 |
|--------|------|------|
| `prepare(brief)` | Phase 1: 문서 생성 | `PreparedProject` |
| `execute(prepared)` | Phase 2: 에이전트 실행 | board state |
| `run(brief)` | prepare + execute 통합 | — |

**핵심 내부 흐름:**
- `terminal_per_agent=True` 설정 → `DynamicOrchestrator` 생성 (`project_pipeline.py:700`)
- `print_startup_routing_notice()` 호출 후 오케스트레이션 시작
- `execute()` 완료 후 `_record_ledger_outcomes()` 호출: 모듈별 3-value 판정 (B2-6 fix — 이전에는 전역 status로 전 모듈에 일괄 fail 기록)
  - `status ∈ {crashed, unknown}` → 전체 skip
  - `completed/partial/stopped_max_cycles` → `module_outcome_from_board()` + `detect_owner_drift()` 판정
- `write_project_board()` atomic write 보장: tempfile + os.replace (C0 fix)

---

### §3.2 DynamicOrchestrator (`core/dynamic_orchestrator.py`)
<!-- last_updated: 2026-04-03 (event-driven sparse governor, run budget, stall detection, state_board asyncio.Lock) -->

**클래스:** `DynamicOrchestrator`

**초기화 파라미터:**
```python
DynamicOrchestrator(mr, max_concurrent=5, terminal_per_agent=True, broker=..., visualizer=...)
```

**핵심 상태:**
```python
self.state_board              # 전체 프로젝트 보드 상태
self.active_assignments       # 진행 중인 태스크 {role: {subtask, result_future}}
self._task_retry_count        # 태스크별 재시도 횟수 {retry_key: count}
self._max_task_retries        # = 3 (초과 시 skip)
self._last_completion_cycle   # 마지막 태스크 완료 사이클 (stall 감지용)
self._stall_threshold         # = 15 (env AGENT_STALL_THRESHOLD로 조절 가능)
max_cycles                    # = compute_max_cycles() — max(30, pending*3), 10사이클마다 재산정
```

**핵심 메서드:**

| 메서드 | 역할 |
|--------|------|
| `_orchestration_loop()` | 메인 실행 루프 (event-driven sparse governor) |
| `_dispatch_from_board()` | Rule-based 태스크 디스패치 (LLM 토큰 0) |
| `_needs_llm_intervention()` | LLM 개입 필요 여부 판단 (blocker/stall/pivot) |
| `restore_from(snapshot, mr)` | state_snapshot.json에서 tick 재기동 시 상태 복원 (classmethod) |
| `_lilith_intervene()` | LLM 기반 태스크 결정 (필요시에만 호출) |
| `_lilith_decide_next()` | Lilith LLM 프롬프트 + 응답 파싱 |
| `_run_agent_in_terminal()` | 터미널 워커 실행 |
| `_cross_verified_evaluate()` | 교차검증 실패 평가 |

**Event-Driven Sparse Governor 동작:**
```
매 사이클:
  1. RunBudget 체크 → 소진 시 중단
  2. idle 에이전트 확인
  3. _dispatch_from_board() — rule-based (0 tokens)
  4. board에 태스크 없고 _needs_llm_intervention() == True 일 때만 LLM 호출
     트리거: 첫 사이클 / blocker 존재 / stall 감지 / 연속 impl 실패 3+건
  5. Dispatch (retry gate, infra gate 적용)
```

**실패 분류 (`_execute_agent_task`):**
```python
from core.failure_classifier import classify_failure, FailureCategory
category = classify_failure(reason)
if category == FailureCategory.INFRA:
    # evaluator 호출 안 함 → 즉시 "failed" → retry 안 함
else:
    # 기존 evaluator 경로 (retry/pivot/abort)
```

**LLM 엔진:** `ControlPlaneLLM` (CLI-first, API-fallback) — `core/control_plane_llm.py`

**완료 상태 결정:**
```python
if cycle >= max_cycles:       → "stopped_max_cycles"  # max_cycles는 compute_max_cycles() 동적 값
elif failed_subtasks:         → "partial"
else:                         → "completed"
```

---

### §3.3 AgentRunner (`core/agent_runner.py`)
<!-- last_updated: 2026-04-10 (CLI 멀티 프로바이더 감지 + timeout 증가 + 진행 표시) -->

**클래스:** `AgentRunner`

**역할 기반 프로바이더 라우팅 (`line 958-969`):**
```python
preferred = self.mr.pick_provider(agent_config=agent)
cli_providers = [preferred] + [fallbacks...]
```

**스킬 로딩:** `AdaptiveSkillLoader` → 최대 12개, 관련성 점수 기반 선택

**컨트랙트 주입 순서:**
1. `documentation_policy.inject_documentation_contract()`
2. `destructive_guard.inject_destructive_guard_contract()`
3. `implementation_language_policy.inject_implementation_language_contract()`

---

### §3.4 AgentSpecializer (`core/agent_specializer.py`)
<!-- last_updated: 2026-04-24 -->

**메서드:** `specialize(base_agent, task_meta, workspace)`

시스템 프롬프트 구성 순서:
1. 역할 페르소나 (200자 요약)
2. 현재 태스크 (id, title, instruction, phase)
3. 수락 기준 + 아티팩트
4. 선행 작업 결과
5. **과거 에피소드 메모리** (M8 fix — `_fetch_episode_context()`, 이벤트루프 안팎 양쪽 안전)
6. 범위 제한

`_fetch_episode_context()`: `UnifiedMemoryFacade.search_semantic(EPISODIC, limit=3)` 호출. 이미 실행 중인 루프가 있으면 `ThreadPoolExecutor` 경유.

---

### §3.5 스킬 시스템

**로딩 파이프라인:**
```
SkillRegistry (싱글톤) → AdaptiveSkillLoader → OptimizedSkillRelevance
                                 ↓
                         최대 12개 관련 스킬 선택
                         점수 = keyword(0.35) × semantic(0.40) × category(0.25)
```

**스킬 라이프사이클:**
```
draft → candidate → canary → active → archived
  ↑          ↑          ↑        ↑
계약테스트  숨겨진테스트 섀도우테스트 런타임 성공률
```

**진화 경로:**
```
evolve_skill() → quick_guard() → run_isolated() → version bump → SkillEvolutionBus
```

**Forge 품질 파이프라인 (`core/skill_procurer.py`):**
```
forge_new_skill()
  ├─ _prepare_forge_context()     # LLM 초기화 + 도메인 힌트 + budget 카운터 (MAX_LLM_CALLS=15)
  ├─ SkillForge                   # Implementer→Critic→Repair 루프
  ├─ _generate_and_validate_evals() # evals.yml 자동 생성 (MIN_EVAL_CASES=3)
  └─ _evaluate_promote_and_register() # Eval→Promotion→Registry 직접 등록
```
- **디렉토리 구조**: `skills/forge/{skill_name}/{skill_name}.py` (directory 우선, flat fallback)
- **함수 시그니처**: `propose(ctx)`, `apply(ctx)`, `test(ctx)` — `apply()`가 핵심 실행
- **FORGE_POLICIES**: `installable_statuses=["candidate","canary","active"]`
- **메모리 등록**: `get_global_registry().register()` 직접 호출 (`_SKIP_DIRS`에 "forge" 포함되어 auto_load 불가)
- **sys.path 보호**: `skill_eval_harness.py`에서 forge parent dir 스킵하여 네임스페이스 충돌 방지

**`evaluate_and_promote()` 공통 함수** — forge와 SkillOrchestrator 양쪽에서 사용:
```
evaluate_and_promote(skill_name, code_path, ...) → dict
  ├─ SkillEvalHarness().evaluate()
  └─ SkillPromotionManager().apply()
```

**캐시 무효화 (7단계, `skill_evolution_bus.py`):**
1. SkillRegistry 재로드
2. DependencyGraph 무효화
3. SemanticEmbedder 재계산
4. OptimizedSkillRelevance 캐시 클리어
5. AgentRunner 모듈 캐시 제거
6. AdaptiveSkillLoader 인스턴스 캐시 클리어
7. HookEventBus 이벤트 브로드캐스트

**외부 도구 wrapper 스킬 패턴 (2026-04-23, graphify 케이스)**
- 외부 CLI 도구(예: `graphify`)를 agent-factory에 통합할 때:
  - `skills/<tool>/skill.py` — `shutil.which("<cli>")` 가드 + `subprocess.run([cli, ...])` 호출. **runtime lazy install 금지**(권한·PATH·네트워크 unguarded)
  - `skills/<tool>/meta.yaml` — 좁은 capability(`<TOOL>_BUILD`/`<TOOL>_QUERY`)로 다른 skill 점수 오염 회피
  - `skills/<tool>_guide/SKILL.md` — knowledge skill로 분리 등록(retrieval engine이 자동 발견·컨텍스트 주입). action+knowledge 동일 skill_id 회피
  - 설치는 `install-af.sh --with-<tool>` / `install-af.ps1 -With<Tool>` 옵션으로만
  - 외부 도구의 자체 인스톨러(`<tool> install` 등)는 **사용 금지** — CLAUDE.md/hooks 자동 주입으로 agent-factory 규칙과 충돌

---

### §3.6 메모리 시스템 (`core/memory_system/`)

**진입점:** `UnifiedMemoryFacade` (싱글톤)

| 메서드 | 역할 |
|--------|------|
| `record_episode()` | 실행 에피소드 기록 (facade 공식 심볼) |
| `search_semantic()` | 시맨틱 검색 — keyword_similarity 기반 semantic_scores 전달 (NEW-H2 fix) |
| `search_all_backends()` | 전체 백엔드 크로스-프로젝트 검색 — 동일 semantic_scores 패치 |
| `query_graph()` | 지식 그래프 탐색 |
| `decay()` | 메모리 자동 에이징 |

**메모리 타입:** EPISODIC, SEMANTIC, PROCEDURAL, WORKING, GRAPH

**MemoryScope:** LOCAL, GLOBAL, SESSION, **PROJECT** (Phase A Step 4 추가)

**어댑터:** ast_hub, continuity, core_memory, cortex_vector, knowledge_graph, sync_compyne, trace_log

**scope 할당 정책:** `node.project_id is None → GLOBAL, else → PROJECT` (router.py + knowledge_graph.py 통일)

**EpisodeRecord 확장 필드:** `event_type: str`, `failure_pattern: str`, `root_cause: str` (3순위, to_dict/from_dict 포함)

**EpisodeRecord 채움 사이트 (2026-04-25 통합 결함 수정):**
- `dynamic_orchestrator._execute_agent_task` finally — `state_board.failed_subtasks`에서 latest 매칭 entry의 `failure_category`/`reason` 추출 (`_state_lock` 안에서 캡처)
- `fsa_loop._record_episode` — `result.failure_patterns` (list) `;` join + `result.root_cause`. 실패 종료 경로(`final_result`/KeyboardInterrupt)는 `last_analysis.error_category`/`root_cause`를 채워 전달

**EpisodeMatcher facade 주입 (P0 FATAL 수정):** `work_item_generator._build_episode_hints_section`이 이전엔 `EpisodeMatcher()`를 facade 없이 호출 → seed-only mode로 런타임 에피소드 회상 차단됐음. `UnifiedMemoryFacade.get_instance()._initialised`일 때 주입.

---

### §3.7 CrossVerification (`core/cross_verification.py`)
<!-- last_updated: 2026-04-10 (as_completed timeout 600→960초, CLI 기본 900초와 동기화) -->

**클래스:** `CrossVerificationLoop`

**5단계 파이프라인:**
```
Phase 1: 병렬 실행 (ThreadPoolExecutor, N CLIs)
Phase 2: 순환 피어 리뷰 (A→B→C→A)
Phase 3.1: Opus 판정 (JSON, verdict/confidence/failure_patterns)
Phase 3.2: 합성 (keep_parts 기반 머지)
Phase 4: 자가진화 트리거 (failure_patterns → evolve_skill)
```

**판정:** `pass` | `fail` | `partial` | `abort`

**레벨별 라운드:** starter=0, dynamic=1, enterprise=3

**Opus 판정 JSON 스키마:**
```json
{
  "verdict": "pass|fail|partial|abort",
  "selected_provider": "claude_cli",
  "keep_parts": ["provider: reason"],
  "discard_parts": ["provider: reason"],
  "failure_patterns": ["pattern1"],
  "confidence": 0.0-1.0
}
```

---

### §3.8 Evaluator (`core/evaluator.py`)
<!-- last_updated: 2026-04-02 (ControlPlaneLLM으로 전환) -->

**클래스:** `StrategyEvaluator`

단일 CLI 환경 폴백. 판정: `retry` | `pivot` | `abort`

**LLM 엔진:** `ControlPlaneLLM` (CLI-first, API-fallback) — GOOGLE_API_KEY 없이도 동작

### §3.8.1 ControlPlaneLLM (`core/control_plane_llm.py`)
<!-- last_updated: 2026-04-10 (CLI timeout 120→300초) -->

Control-plane(Lilith, Evaluator)용 LLM 인터페이스.

**해결 순서:** CLI providers (claude_cli > gemini_cli > codex_cli) → Gemini API → 빈 결과
**인터페이스:** `generate(prompt) → str`, `generate_json(prompt) → dict`
**CLI 실패 시:** infra 실패면 다음 CLI로 failover

> **설계 결정: 프로바이더 우선순위 분리**
> - Control-plane (`ControlPlaneLLM`): Claude 우선 — 정확한 JSON 판정이 핵심
> - FSA 일반 실행 (`engine_auth`): Gemini 우선 — 리서치/탐색 작업에 최적화
> - 이 분리는 의도적이며 통합하지 않는다

### §3.8.2 FailureClassifier (`core/failure_classifier.py`)

reason 문자열 기반 실패 분류. `classify_failure(reason) → FailureCategory.INFRA | IMPLEMENTATION`

INFRA 패턴: `missing_api_key`, `quota`, `429`, `503`, `cli_timeout`, `worker_timeout` 등

### §3.8.3 RunBudget (`core/run_budget.py`)
<!-- last_updated: 2026-04-27 -->

글로벌 토큰 예산 추적. 4-char ≈ 1-token 휴리스틱.

**API:** `set_run_budget(max_tokens, *, run_id, project_id)`, `get_run_budget()` (모듈 싱글턴)
**동작:** 80% 경고 출력, 100% `is_exhausted()=True` → orchestrator 자동 중단. run_id 설정 시 80%/100% 마일스톤에 COST_INCURRED RunEvent 방출.
**CLI:** `af nightly-start --budget 50000` → `state.budget.max_tokens` → nightly_tick에서 `set_run_budget(max_tokens, run_id=tick_id)` 호출

**연결 포인트:**
- `agent_runner.py:_flush_trace()` — transcript `assistant` 엔트리에서 텍스트 합산 후 `record()` 호출
- `fsa_loop.py:FSALoop.run_mission()` — 각 사이클 시작 시 `is_exhausted()` 체크로 조기 탈출
- `dynamic_orchestrator.py:_orchestration_loop()` — while 루프 최상단 `is_exhausted()` 체크
- `scripts/nightly_tick.py:tick_once()` — tick 시작 시 `set_run_budget(state.budget.max_tokens, run_id=tick_id)` + `rb.consumed` 사전 로드 + tick 종료 시 `state.budget.consumed_tokens` 역기록 (T3-7 ACCEPT 2, 2026-04-27)
- `scripts/nightly_tick.py:_dispatch_actions()` — 루프 내 `is_exhausted()` 즉시 중단 체크

### §3.8.4 SkillPackBootstrapper (`core/skill_pack_bootstrapper.py`)
<!-- last_updated: 2026-04-22 -->

외부 CLI 플러그인 감지 전용. 설치는 하지 않고 shutil.which()로 PATH 탐색만 수행.

**지원 플러그인:** claude-code, codex, gemini
**API:** `check_installed() → dict[str, bool]`, `missing() → list[str]`, `installed() → list[str]`

---

### §3.9 Continuity (`core/continuity/`)

**`manifest_store.py:OrchestratorManifestStore`**
- 저장: `.af_manifest.json` (atomic write: tmpfile→rename)
- 복구: `load_resume_state()` → 중단된 실행 재개

---

### §3.10 Control 서브시스템 (`core/control/`)

| 파일 | 역할 |
|------|------|
| `supervisor.py` | 유지보수 감독 루프 |
| `maintenance_pipeline.py` | 유지보수 파이프라인 |
| `rollback.py` | 롤백 전략 |
| `regression_gate.py` | 회귀 검증 게이트 |
| `run_ledger.py` | 실행 원장 |
| `change_impact.py` | 변경 영향 분석 |

### §3.11 Setup Wizard + External Research (`core/setup_wizard.py`, `core/research_engine.py`)

**목적**: 모든 실행 모드(`af`, `af setup`, `af worker`, `af __nlm` 등)에서 파이프라인 진입 직전 외부 리서치 도구(TAVILY / NotebookLM)의 상태를 점검·복구하고, 사용자별 아카이브 노트북 UUID를 영속 저장해 `research_engine.query_notebooklm()`가 하드코딩 없이 동작하도록 만드는 단일 진입점 계층. 설계 문서: `docs/features/2026-04-10-setup-wizard-tavily-notebooklm-integration.md` (v3.3, Implemented).

#### 데이터 흐름

```
run_factory_cli.main()
   │
   ├── STAGE 1: _STAGE1_DISPATCH (setup / worker / __nlm / __check-nlm / skill-* / preflight)
   │              → gate 우회, 즉시 분기 (재귀 방지)
   │
   ├── STAGE 2: _run_setup_gate()
   │              → setup_wizard.ensure_external_research_capabilities(mode="auto")
   │                    ├── _load_setup_state()  (.af_setup_state.json, filelock)
   │                    ├── _ensure_tavily(state, mode)  — Y/N 재확인 루프
   │                    ├── _ensure_notebooklm(state, mode)
   │                    │      ├── _check_chrome_installed()
   │                    │      ├── _check_notebooklm_auth(profile)  — exit code 0/2 우선 판정
   │                    │      ├── _run_notebooklm_login()          — subprocess nlm login
   │                    │      └── _find_or_create_archive_notebook()
   │                    │             ├── nlm notebook list → _parse_notebook_list_for_title()
   │                    │             └── nlm notebook create → _parse_notebook_create_output()
   │                    └── _save_setup_state(state)  — atomic write + filelock
   │
   └── STAGE 3: 기존 로직 (project / chat / fsa / ...)
```

#### 주요 함수 (`core/setup_wizard.py`)

| 함수 | 역할 |
|------|------|
| `ensure_external_research_capabilities(mode)` | 외부 공개 API — 모든 파이프라인이 호출하는 단일 진입점 |
| `_load_setup_state()` / `_save_setup_state(state)` | `.af_setup_state.json` schema v2 atomic I/O + `filelock` 크로스플랫폼 락 |
| `_check_notebooklm_auth(profile)` | `nlm auth status` exit code 0/2 우선 판정 (Phase 0.5 실측) |
| `_find_or_create_archive_notebook(profile, title)` | 기존 노트북 title 매칭 → 없으면 `nlm notebook create` → UUID 반환 (BLOCK-C 해결) |
| `_parse_notebook_create_output(stdout)` | 생성 출력 뒤의 JSON 블록에서 UUID 추출 |
| `_parse_notebook_list_for_title(stdout, title)` | `nlm notebook list` 순수 JSON 배열에서 title 매칭 UUID 추출 |
| `_validate_notebook_uuid(nb_id, profile)` | UUID 포맷/접근성 검증 (수동 입력 fallback 보호) |
| `_ensure_tavily(state, mode)` | TAVILY_API_KEY 입력 UI + Y/N 스킵 재확인 |
| `_ensure_notebooklm(state, mode)` | Chrome 감지 → 로그인 유도 → 아카이브 노트북 확보 |

#### 주요 함수 (`core/research_engine.py`, 재작성 완료)

| 함수 | 역할 |
|------|------|
| `_get_archive_notebook_id()` | `setup_wizard._load_setup_state()` **lazy import** → `notebooklm.archive_notebook_id` 로드 (하드코딩 UUID 제거) |
| `_nlm_cmd_base()` | frozen exe → `[sys.executable, "__nlm"]` / 소스 → `["nlm"]` (PATH 의존 — venv 활성화 또는 `PATH`에 `nlm` 필요) |
| `_reauth_notebooklm()` | 401/auth 오류 감지 시 1회 자동 재로그인 시도 |
| `_nlm_cli(*args, timeout=120)` | subprocess 래퍼 + 인증 만료 감지 시 `_reauth_notebooklm()` 후 1회 자동 재시도 |
| `query_notebooklm(query, notebook_id=None, mode=None) -> str` | `notebook_id` 미지정 시 `_get_archive_notebook_id()` fallback; archive 미설정 시 `""` graceful skip(`_ARCHIVE_SKIP_LOGGED`로 stderr 1회 경고); `mode=None`이면 `classify_research_depth()` 자동 결정 |
| `create_notebook(title)` / `inject_source_url/text/sources()` | 사서 API — 노트북 생성·소스 주입 |

#### `.af_setup_state.json` 스키마 v2 (실제 `_default_state()`와 동기화)

```json
{
  "schema_version": 2,
  "tavily": {
    "decision": "pending | configured | skipped",
    "last_prompt_at": "ISO8601 | null"
  },
  "notebooklm": {
    "decision": "pending | logged_in | skipped | unknown",
    "profile": "default",
    "archive_notebook_id": "UUID | null",
    "archive_notebook_title": "Agent Factory Archive",
    "archive_possibly_duplicate": false,
    "last_login_attempt_at": "ISO8601 | null",
    "last_login_error": "string | null"
  }
}
```

- `tavily.decision` 허용 값은 `_VALID_TAVILY_DECISIONS = {"pending", "configured", "skipped"}` (`core/setup_wizard.py:195`).
- `notebooklm.decision`은 `_check_notebooklm_auth()` 반환에 따라 wizard가 갱신 (`logged_in` / `skipped` / `unknown` / `pending`).
- `archive_possibly_duplicate`는 `_find_or_create_archive_notebook()`이 동일 title 노트북 다중 존재 감지 시 `True`.

#### 순환 방지 규칙 (중요)

- `core/setup_wizard.py`는 **top-level에서 `core.*` 모듈을 import하지 않는다** (stdlib + `filelock`만 허용).
- `core/research_engine._get_archive_notebook_id()`는 함수 내부에서 `setup_wizard._load_setup_state()`를 lazy import. 역방향은 금지.

#### BLOCK 해소 매핑

| 설계 단계 BLOCK | 해소 메커니즘 | 참조 |
|-----|------|------|
| BLOCK-A (Windows `fcntl` 미지원) | `filelock>=3.0` 크로스플랫폼 패키지 | `_save_setup_state()` |
| BLOCK-B (Typer `standalone_mode` `SystemExit` 전파) | `_invoke_nlm_app()`: `standalone_mode=False` + `sys.argv` try/finally + `SystemExit` try/except | `run_factory_cli.py` |
| BLOCK-C (하드코딩 `DEFAULT_ARCHIVE_NOTEBOOK_ID` → 신규 사용자 전면 실패) | `_find_or_create_archive_notebook()` + state 저장 + `_get_archive_notebook_id()` 로드 | `setup_wizard.py`, `research_engine.py` |
| Low-1 (archive 미설정 시 보고서 본문에 에러 문자열 삽입) | `_query_notebooklm()` tuple `(ok, reason)` 반환 → `apply()`가 구조화된 실패 반환 | `skills/research_assistant/skill.py` v3.2 |

#### 배포 의존성 (§8과 연동)

- `requirements.txt`: `notebooklm-cli`, `tavily-python`, `filelock>=3.0` 추가
- `af.spec` `hiddenimports`: `nlm.*` 27개 + `typer/rich/shellingham/websocket/annotated_doc/filelock/tavily` + `collect_submodules('typer'|'rich'|'nlm')`
- `install-af.ps1` / `install-af.sh`: Chrome 감지 + `__check-nlm` 검증 + 재설치 시 `.env`/`.af_setup_state.json` 자동 복원

---

## §4 자가진화 루프

### 완전한 루프 추적

```
태스크 실패 감지
  │
  ├─ [DynamicOrchestrator] _cross_verified_evaluate()
  │   └─ CrossVerificationLoop.run()
  │       ├─ 병렬 실행 → 결과 수집
  │       ├─ 순환 피어 리뷰
  │       ├─ Opus 판정 → failure_patterns 추출
  │       └─ verdict 반환
  │
  ├─ [DynamicOrchestrator] _try_evolve_from_patterns(failure_patterns)
  │   ├─ 패턴 키워드 → 스킬 이름 매핑
  │   └─ evolve_skill(skill_dir, feedback)
  │       ├─ .bak 백업 생성
  │       ├─ LLM으로 개선 코드 생성
  │       ├─ quick_guard() AST 검증
  │       ├─ run_isolated() 샌드박스 테스트
  │       └─ version bump (0.x.y → 0.x.(y+1))
  │
  ├─ [SkillEvolutionBus] on_skill_evolved() → 7단계 캐시 무효화
  │
  ├─ [재시도] _task_retry_count 확인
  │   └─ count >= 3 → SKIP (스킵 후 다음 태스크)
  │
  └─ 다음 사이클에서 진화된 스킬로 재실행
```

### 스킬 자동 품질 감사 (백그라운드)

`SkillSelfEvolutionHook` (실행 우선순위=80):
- 에이전트 10회 실행마다 → `bulk_enrich_all_skills(max_skills=5)`
- 품질 점수 < 0.5인 스킬 자동 메타데이터 개선
- 백그라운드 스레드에서 실행 (메인 파이프라인 블로킹 없음)

**품질 점수 공식:**
```
description(>10자)  +0.20
when_to_use         +0.20
keywords            +0.20
semantic_tags       +0.20
category(비기본값)   +0.10
when_NOT_to_use     +0.10
──────────────────────────
최대                  1.0
```

### 자동 코드 리뷰 + 문서 업데이트 (백그라운드)

`CodeReviewDocHook` (실행 우선순위=85):
- 에이전트 실행 성공(`result["ok"]==True`) 후 자동 트리거
- `git diff`로 변경 파일 감지 → `ControlPlaneLLM`으로 코드 리뷰
- `docs/code_review.md`에 리뷰 결과 append
- `docs/change_history.md`에 변경 이력 append
- LLM 미사용 시 파일 목록만 기록 (graceful degradation)
- 백그라운드 daemon 스레드 (메인 파이프라인 블로킹 없음, Lock으로 중복 방지)

---

## §5 에이전트 간 통신

### 두 가지 통신 채널

| 채널 | 파일 | 특징 |
|------|------|------|
| **TCP MessageBroker** | `core/message_broker.py` | DynamicOrchestrator 내부 pub/sub, 포트 동적 할당 |
| **파일 기반 Mailbox** | `core/project_mailbox.py` | JSONL 파일, 에이전트 간 비동기 메시지 |

### Mailbox 메시지 타입 (우선순위 순)

| 타입 | 우선순위 | 용도 |
|------|---------|------|
| `blocker` | 0 | 차단 이슈, 즉시 해결 필요 |
| `decision_request` | 1 | 결정 요청 |
| `review_request` | 2 | 검토 요청 |
| `handoff` | 3 | 작업 인계 |
| `result` | 6 | 완료 결과 |

**메시지 파일 위치:** `{workspace}/data/comm/messages.jsonl`

**핵심 함수:**
```python
send_agent_message(workspace, from_role, to_role, msg_type, content, task_id)
read_inbox(workspace, role, task_id, status_filter)
ack_mailbox_message(workspace, message_id)
mailbox_prompt_digest(workspace, role)  # LLM 컨텍스트용 포맷
```

---

## §6 모델 라우팅

### 역할→엔진→프로바이더 매핑

**`model_utils.py:_ROLE_ENGINE_MAP` (우선순위 순):**
```python
["qa", "tester", "quality", "test_eng"]    → "codex"
["architect", "design", "blueprint"]        → "architect_claude"
["coder", "developer", "_dev", "engineer"]  → "coder_claude"
["researcher", "analyst", "planner"]        → "researcher_gemini"
["writer", "docs", "document"]             → "writer_claude"
```

**`model_utils.py:_ROLE_CLI_PREFERENCE` (프로바이더 우선순위):**
```python
"codex"           → ["codex_cli", "claude_cli", "gemini_cli"]
"architect_claude" → ["claude_cli", "codex_cli", "gemini_cli"]
"coder_claude"    → ["claude_cli", "codex_cli", "gemini_cli"]
"researcher_gemini"→ ["gemini_cli", "claude_cli", "codex_cli"]
```

**라우팅 결정 흐름:**
```
_infer_engine_id(role_name) → engine_id
  ↓
_ROLE_CLI_PREFERENCE[engine_id] → [provider1, provider2, ...]
  ↓
get_requested_cli_providers() 와 교집합
  ↓
첫 번째 가용 프로바이더 선택
```

**단일 프로바이더 모드:** 설치된 CLI가 1개면 모든 역할이 동일 프로바이더 사용 (startup notice 출력)

---

## §7 안전장치

### 4-레이어 보안 체계

```
Layer 1: 정책 검증
  policy.yaml → 태스크 분해 규칙, 역할 수 제한

Layer 2: 코드 정적 분석 (AST)
  security_guard.quick_guard() → 금지 import/함수 차단
  금지: os, sys, subprocess, shutil, importlib, eval, exec, __import__

Layer 3: 격리 실행
  security_guard.run_isolated() → 서브프로세스 + 타임아웃 (10초)
  파일 I/O: DATA_DIR, ARTIFACTS_DIR 만 허용

Layer 4: 위험 명령 차단
  destructive_guard → rm, del, git reset/clean/checkout 차단
  에이전트 시스템 프롬프트에 가드 컨트랙트 주입

Layer 5: 인간 승인 게이트
  ApprovalGate → SHA256 해시 기반 문서 변경 감지
  execution_open: false → 승인 후 true
```

### ApprovalGate 상태 전환

`is_execution_open()` 판단 조건: `execution_open == true` **AND** `status == "approved"` (둘 다 충족해야 통과).
`approved`는 `status` 필드 값이며 `execution_open` 별칭이 아님.

```
initialize() → execution_open: false, status: "pending"
     ↓
[사용자 검토]
     ↓
approve() → SHA256 스냅샷 저장, execution_open: true, status: "approved"
     ↓
[문서 수정 감지]
     ↓
invalidate() → execution_open: false (재승인 필요)
```

### Pre-commit 교차검증 게이트
<!-- last_updated: 2026-04-10 -->

커밋 시 `core/*.py` 변경이 포함되면 기존 watcher의 리뷰 결과를 자동 확인한다.

**실행 흐름:**
```
git commit → .githooks/pre-commit
  ├─ Blueprint 스테이징 체크 (기존)
  └─ scripts/pre_commit_review.py (결과 확인 전용, claude 미호출)
       ├─ docs/reviews/ 에서 파일별 최신 리뷰 수집
       ├─ severity 집계 (Critical/High/Medium/Low)
       └─ 판정: PASS(exit 0) / WARN(exit 0) / BLOCK(exit 1)
```

**판정 기준:** `AF_PRE_COMMIT_REVIEW_BLOCK_ON=high` (기본) → High 1건 이상 차단
**비차단 원칙:** 인프라 장애(결과 없음, 파싱 실패 등)로 커밋을 차단하지 않음
**비활성화:** `AF_PRE_COMMIT_REVIEW=0` 또는 `git commit --no-verify`

### 3-Tier Review-Gate (§9)
<!-- last_updated: 2026-04-20 -->

`.py` 파일을 포함한 커밋은 **af-test-runner → af-critic → af-cross-review** 순서로 3단계 교차검증을 완료해야 한다.

**아키텍처:**
```
Layer 6: 3-Tier Review Gate
  PreToolUse(Bash)  → hook_runner.py pre_bash_review_gate
    └─ git commit 명령 감지 시 review_gate.is_gate_blocked() 호출
    └─ BLOCK → exit 2 (Bash 툴 자체 차단)
  PostToolUse(Task) → hook_runner.py post_agent_record
    └─ af-test-runner/af-critic/af-cross-review 완료 시 tier 기록
  PostToolUse(Bash) → hook_runner.py post_commit_clear
    └─ git commit 성공 시 큐에서 커밋 파일 제거
  .githooks/pre-commit → review_gate.py --check (이중 차단)
```

**상태 파일:** `.af_review_queue/pending_agent_review.json`
```json
{
  "files": ["core/foo.py"],
  "created_at": 1234567890,
  "updated_at": 1234567891,
  "reviews": {
    "af-test-runner": {"tier": 1, "verdict": "pass", "files_snapshot": [...], "completed_at": ...},
    "af-critic":      {"tier": 2, "verdict": "pass", "files_snapshot": [...], "completed_at": ...},
    "af-cross-review":{"tier": 3, "verdict": "pass", "files_snapshot": [...], "completed_at": ...}
  }
}
```

**BLOCK 조건 (순서대로 평가):**

| 조건 | reason |
|------|--------|
| `.py` 파일 없음 | `no-py-files` → PASS |
| tier 1(af-test-runner) 미완료 | `missing-tier-1` |
| tier 2(af-critic) 미완료 | `missing-tier-2` |
| tier 3(af-cross-review) 미완료 | `missing-tier-3` |
| 리뷰 완료 후 파일 재편집 | `stale-review` |
| tier-3 snapshot에 없는 `.py` 신규 추가 | `new-files-added` |
| 어느 tier에서든 verdict=block/fail | `verdict-block:<agent>` |

**우회:**
- `AF_SKIP_REVIEW_GATE=1 git commit ...` — hook_events.log에 기록됨
- `AF_GATE_ALLOW_VERDICT_BLOCK=1` — verdict-block 조건만 무시
- `git commit --no-verify` — .githooks/pre-commit 전체 우회

**디버그:** `python scripts/review_gate.py --debug`

---

## §8 빌드 & 배포

### 빌드 프로세스

```bash
python build_exe.py
# 1. PyInstaller 확인
# 2. build/, dist/ 정리
# 3. pyinstaller af.spec
# 4. dist/af-{version}.zip 생성
```

**출력:** `dist/af/af.exe` (12.5 MB), `dist/af-1.x.x.zip` (40 MB — 2026-04-14 Phase B 다이어트 이후; 이전 87MB)

### PyInstaller 핵심 설정 (`af.spec`)

```python
from PyInstaller.utils.hooks import collect_submodules

# lazy-import 패키지 안전망 (설계문서 §4.6.2)
_auto_hiddenimports = []
for pkg in ("typer", "rich", "nlm"):
    try:
        _auto_hiddenimports.extend(collect_submodules(pkg))
    except Exception:
        pass

Analysis(
  entry='run_factory_cli.py',
  datas=[('skills', 'skills'), ('config', 'config'), ('policy.yaml', '.')],
  hiddenimports=[
    'core.agent_worker',   # worker 서브커맨드용 (중요!)
    'core.setup_wizard',   # STAGE 2 gate 대상 + __nlm 체인
    # NotebookLM CLI (import name: nlm) — 27 submodules
    'nlm', 'nlm.cli.main', 'nlm.cli.auth', 'nlm.cli.notebook', ...
    # Typer/Rich + 체인
    'typer', 'rich', 'shellingham', 'websocket', 'annotated_doc',
    # 파일락·Tavily
    'filelock', 'tavily',
    ... 100+ 모듈
  ] + _auto_hiddenimports,
)
```

**주의**: PyInstaller 6.x는 `.spec` 파일을 CLI에 넘기면 `--collect-submodules`,
`--hidden-import` 등 makespec 옵션을 거부한다(`makespec options not valid when
a .spec file is given`). 따라서 `build_exe.py`는 옵션 없이 `pyinstaller af.spec`만
호출하고, 서브모듈 안전망은 spec 내부에서 `collect_submodules()`로 건다.

**새 core/*.py 파일 추가 시 af.spec `hiddenimports`에 반드시 추가 필요.**
**nlm/typer/rich 마이너 버전 업그레이드 시 `collect_submodules` 결과 재검증.**

### Phase B 빌드 다이어트 (2026-04-14)

**PYZ 생성 직전 `a.datas` 필터 (af.spec B1)** — googleapiclient discovery_cache 전량 제거:

```python
_DISCOVERY_PATTERNS = (
    "googleapiclient/discovery_cache/documents",
    "googleapiclient\\discovery_cache\\documents",  # Windows 경로
)
_DEFENSIVE_KEEP = ("drive.v3.json", "customsearch.v1.json", "gmail.v1.json")

a.datas = [d for d in a.datas if not _is_discovery_doc(d[0]) or _should_keep(d[0])]
```

- **근거**: 주 경로(google.genai)는 REST/gapic을 직접 호출하며 580개 JSON을 쓰지 않음.
- **방어 whitelist**: LangChain Google 툴이 실수로 `build()`를 호출할 경우 `ImportError`가 아니라 `UnknownApiNameOrVersion`으로 낮춤.
- **회귀 감지**: `tests/test_gemini_smoke.py` (pytest.mark.slow) — 신/구 SDK 경로 + import 시점 discovery_cache 미필요 확인.

**hiddenimports 제거 (B2/B3)**:
- `langchain_community` → orphan(langchain 1.0 Required-by 없음, 우리 코드 import 0건) → numpy/SQLAlchemy 등 ~40MB 간접 의존 배제.
- `google.generativeai` → `skills/core/cortex.py`를 신 SDK(`google.genai`)로 마이그레이션 완료 후 제거. 구 SDK `agents/*/tools/cortex.py` 26개는 **소스 모드 런타임 호환용으로 보류** (binary에는 무관).

**결과**: zip 87MB → 40MB (-54%), unpacked 200MB+ → 68MB (-66%).

### Worker 서브커맨드 (PyInstaller 전용)

`run_factory_cli.py` — STAGE 1 dispatch (`_STAGE1_DISPATCH["worker"]`):
```python
def _run_worker_subcommand(rest: list[str]) -> None:
    from core.agent_worker import main as worker_main
    saved_argv = sys.argv
    try:
        sys.argv = ["af-worker"] + list(rest)
        worker_main()
    finally:
        sys.argv = saved_argv
```

`dynamic_orchestrator.py:515-521`:
```python
if getattr(sys, "frozen", False):
    cmd = [sys.executable, "worker", "--task-file", ..., "--result-file", ...]
else:
    cmd = [sys.executable, "core/agent_worker.py", ...]
```

### 배포 체인

```
1. version.py → __version__ = "1.x.x" 업데이트
2. install-af.ps1 → 버전 문자열 수정 (Windows, 모든 1.x.x 치환)
3. install-af.sh → `AF_VERSION` 및 URL 문자열 수정 (macOS/Linux)
4. python build_exe.py → dist/af-1.x.x.zip 생성
5. git add dist/af-1.x.x.zip (LFS 자동 추적)
6. git commit + git push origin 브랜치
7. git tag af-fsa_v1.x.x + git push origin refs/tags/...
8. GitHub Release 생성 (PyGithub 또는 gh CLI)
```

**설치 URL 패턴:**
```
raw URL:   https://github.com/hoonkim1092-web/af-fsa/raw/af-fsa_v1.x.x/dist/af-1.x.x.zip
installer: https://raw.githubusercontent.com/hoonkim1092-web/af-fsa/af-fsa_v1.x.x/install-af.ps1
```

---

## §9 설정 레퍼런스

### 핵심 환경 변수

| 변수 | 기본값 | 역할 |
|------|--------|------|
| `AGENT_PROJECTS_DIR` | `~/projects` | 프로젝트 루트 |
| `AGENT_PROJECT_ID` | — | 현재 프로젝트 ID |
| `AGENT_PROJECT_ROOT` | — | 현재 워크스페이스 |
| `AGENT_CHAT_MODEL` | — | 모델 오버라이드 |
| `AGENT_CHAT_PROVIDER` | — | 프로바이더 오버라이드 |
| `AGENT_TERMINAL_MODE` | false | 에이전트당 별도 터미널 |
| `AGENT_AUTO_INSTALL_CLI` | 1 | CLI 자동 설치 여부 |

### policy.yaml 구조

```yaml
engines:
  gemini_flash: {tier: 1}     # 속도 우선
  codex:        {tier: 2}     # 코드 정밀도
  research_pro: {tier: 3}     # 추론

skills:
  read_file:  {risk: LOW,      engine_id: gemini_flash}
  write_file: {risk: HIGH,     engine_id: codex}
  run_command:{risk: CRITICAL, engine_id: codex}

task_decomposition:
  roles:   {min: 2, max: 5}
  modules: {independent: true}
  tasks:   {granularity: small, require_verify: true}
  required_roles: [qa_engineer]
```

### 스킬 레지스트리 (`skills/registry.yaml`)

```yaml
skills:
  skill_id:
    name: "스킬 이름"
    path: "skills/skill_id/"
    status: active|draft|archived
    version: "0.x.x"
    updated_at: "YYYY-MM-DD"
```

**스킬 디렉토리 구조:**
```
skills/{skill_id}/
  ├── meta.yaml    (메타데이터)
  ├── skill.py     (구현체, action 스킬)
  └── SKILL.md     (구현체, knowledge 스킬)
```

---

## §10 의존성 그래프 & 영향 매트릭스

### 수정 시 영향 범위 (Blast Radius)

| 수정 대상 | 직접 영향 | 간접 영향 |
|----------|----------|----------|
| `model_utils.py` | `agent_runner.py`, `dynamic_orchestrator.py`, `model_router.py` | 모든 에이전트 실행 |
| `core/skill_loader.py` | `agent_runner.py` | `skill_cache.py`, `skill_evolution_bus.py` |
| `core/skill_evolution_bus.py` | 스킬 시스템 전체 | `agent_runner.py`, `skill_cache.py`, `skill_loader.py` |
| `core/dynamic_orchestrator.py` | `project_pipeline.py` | 전체 Phase 2 실행 |
| `core/agent_worker.py` | `dynamic_orchestrator.py`, `run_factory_cli.py` | `af.spec` hiddenimports |
| `core/agent_runner.py` | `dynamic_orchestrator.py`, `fsa_loop.py` | 모든 에이전트 실행 |
| `core/cross_verification.py` | `dynamic_orchestrator.py` | 검증 결과 품질 |
| `core/ise_analyzer.py` | `fsa_loop.py`, `ise_loop.py` | 실패 분석 에스컬레이션 |
| `core/ise_redesigner.py` | `fsa_loop.py`, `ise_loop.py` | 태스크 재설계/분해 |
| `core/ise_strategy_ledger.py` | `fsa_loop.py`, `ise_loop.py` | 전략 원장 |
| `core/project_pipeline.py` | `run_factory_cli.py`, `interactive_chat.py` | Phase 1/2 전체 |
| `core/message_broker.py` | `dynamic_orchestrator.py` | 에이전트 간 통신 |
| `core/project_task_board.py:update_project_board_task` | `core/documentation_policy.py:write_project_todo` (lock 내부 훅), `.todo.md` 파일 | board 상태 전이 시 `.todo.md` 동기화. `AF_TODO_SYNC=0`으로 비활성화 가능 |
| `core/documentation_policy.py:write_project_todo` | `.todo.md` 파일 | `_instruction_status_map` 기반 board→todo 단방향 재생성 (safe_id 아닌 전체 문자열 정규화 매칭) |
| `core/project_mailbox.py` | `agent_runner.py`, `agent_specializer.py` | 에이전트 컨텍스트 |
| `core/setup_wizard.py` | `run_factory_cli.py` (STAGE 2 gate), 외부 리서치 능력 | 모든 일반 af 실행 — `af setup`, `__nlm`/`__check-nlm` 진입점, `.af_setup_state.json` 스키마 소스 |
| `core/research_engine.py` | `core/researcher.py`, `skills/research_assistant/skill.py`, `skills/hound_librarian/skill.py` | `_get_archive_notebook_id()` → `setup_wizard._load_setup_state` 의존. state 미설정 시 NotebookLM 쿼리 graceful skip |
| `core/researcher.py` | `core/research_engine.py`, `core/web_search`, `core/retrieval_router` | Himari 리서치 결과 품질. TAVILY/nlm 미설치 시 `sys.stderr` 1회 로그 후 스킵 |
| `run_factory_cli.py` | `core/setup_wizard.py`, `nlm.cli.main` (소프트, frozen 시 hiddenimports 필요) | STAGE 1/2/3 진입점, `__nlm`/`__check-nlm` 숨은 서브커맨드 |
| `af.spec` | 빌드 출력 | `agent_worker.py` 미포함 시 worker_exited_code_2; `nlm.*`/`typer`/`rich` 미포함 시 `__nlm` ImportError(127) |
| `policy.yaml` | `bootstrap_roles.py`, `config/schema.py` | 태스크 분해 규칙 |

### 핵심 import 체인

```
run_factory_cli.py
  └─ core/project_pipeline.py
       └─ core/dynamic_orchestrator.py
            ├─ core/agent_runner.py
            │    ├─ core/skill_loader.py → core/skill_registry.py
            │    ├─ core/hooks/event_bus.py
            │    └─ core/providers/cli.py
            ├─ core/agent_specializer.py
            ├─ core/cross_verification.py
            ├─ core/message_broker.py
            └─ core/continuity/manifest_store.py
```

```
model_utils.py (독립 모듈)
  ├─ _ROLE_ENGINE_MAP → _infer_engine_id()
  ├─ _ROLE_CLI_PREFERENCE → pick_cli_provider_for_role()
  └─ pick_provider() ← agent_runner.py가 호출
```

---

## §11 알려진 제약·이슈

### 현재 제약사항

| 항목 | 내용 | 해결 방안 |
|------|------|----------|
| **Self-hosting 제한** | af.exe는 자기 소스(`core/*.py`)를 수정 불가 | 소스 모드(`python run_factory_cli.py`)로 실행 |
| **GOOGLE_API_KEY 없음** | ~~Lilith LLM 실패 → cycle 낭비~~ **해결됨**: ControlPlaneLLM이 CLI-first로 동작 | — |
| **TCP Broker 미연결** | agent_worker.py가 TCP 브로커에 실제 연결 안 함 | 파일 기반 Mailbox는 정상 동작 |
| **max_cycles 소진** | ~~Lilith LLM 오류 누적 시 사이클 낭비~~ **완화됨**: `compute_max_cycles()` 동적 산정(max(30, pending*3)), infra 실패 즉시 종료, ControlPlaneLLM CLI fallback | — |
| **cross_verification level** | DynamicOrchestrator에서 항상 dynamic(1라운드) 고정 | enterprise 모드 옵션 추가 가능 |
| **LFS zip 빌드 반복** | 매 버전마다 44MB zip LFS 푸시 필요 | 릴리스 asset URL 사용 시 PowerShell 리다이렉트 실패 |

### 에러 코드 해설

| 에러 | 원인 | 수정 위치 |
|------|------|----------|
| `worker_exited_code_2` | frozen exe에서 `python agent_worker.py` 실행 시도 | `dynamic_orchestrator.py:515` frozen 분기 |
| `stopped_max_cycles` | `compute_max_cycles()` 사이클 내 완료 못함 (기본 max(30, pending*3)) | Lilith LLM 실패율, 태스크 재시도 횟수 확인 |
| `worker_timeout` | 에이전트 3600초 초과 | `dynamic_orchestrator.py:526` max_wait 조정 |
| `empty_llm_response` | LLM 호출 실패 (API 키 없음 등) | 환경 변수 및 CLI 설치 확인 |
| 다운로드 연결 끊김 | GitHub release asset 리다이렉트 실패 | raw LFS URL 사용 (`install-af.ps1:98`) |
| `NameError: name '_safe_print' is not defined` | `core/project_pipeline.py` 780/782/848/850이 `_safe_print`를 미import — plan verify WARN + structural gate 예외 + doc cross-review 예외 분기에서만 노출됨 | `core/agent_runner.py`에서 import (`from core.agent_runner import _safe_print`) — 2026-04-15 fix |
| 파이프라인이 `src/` 구현 태스크에 도달 못 하고 Cycle 30에 exit | `core/project_task_board.py::next_board_tasks`의 정렬 key가 `(phase, module_id, task_id)`로 phase 우선이었음 → 모든 모듈의 scope를 먼저 소화하다가 `max_cycles=30` 소진. 실측(`lotto-pattern-predictor`, 2026-04-15): 24 태스크 중 scope 4개만 완료, build 단계 0건. | 정렬을 `(_module_sort_key(module_id), phase, task_id)` 순으로 변경해 module waterfall로 전환 + `dynamic_orchestrator._orchestration_loop`의 `max_cycles`를 `max(30, pending*3)`로 동적화 — 2026-04-15 fix |
| `SessionStart:startup hook error` + `ModuleNotFoundError: No module named 'yaml'` | Claude native hook가 절대경로 Homebrew `python3.14`로 `scripts/cli_hook_bridge.py`를 직접 실행했고, 해당 인터프리터에 `PyYAML`이 없어 `core.providers.__init__` import 단계에서 즉시 실패. legacy unnamed hook와 빈 hook group이 `.claude/settings.local.json`에 누적되어 같은 에러가 반복 노출됨. | `core/providers/session_adapter.py`가 hook 명령을 `python3 scripts/hook_runner.py cli_hook_bridge ...` 경유로 생성하도록 변경해 프로젝트 `.venv` Python을 다시 찾게 함 + legacy bridge hook/빈 group 자동 정리 — 2026-04-16 fix |
| **PostToolUse hook no-op** (증상: `[af-review-pending]` 트리거 0회) | PostToolUse 훅 명령이 `$TOOL_INPUT_file_path` 환경변수를 참조하지만 Claude Code는 hook 데이터를 **stdin JSON**으로만 전달 → `$fp`가 항상 빈 문자열 → `case "$fp" in *.py)` 매칭 실패 → 전체 no-op. 세션 통계 상 PostToolUse 0회 발화. 감지: `.af_review_queue/hook_events.log` 없음 + `.af_review_queue/pending_agent_review.json` 없음 | `.claude/settings.local.json`의 5개 PostToolUse 명령을 `python3 scripts/hook_runner.py post_edit_*` builtin 형식으로 교체. `hook_runner.py`에 `_BUILTINS` 분기 테이블 + `_read_hook_stdin_once()` + `_extract_file_path()` 신설해 stdin JSON을 파싱하여 파일 경로를 추출 — 2026-04-17 fix |
| **review-gate: 첫 커밋(HEAD~1 없음)** | `post_commit_clear` hook이 `git diff HEAD~1 --name-only`를 실행하는데, 레포 첫 커밋에서는 HEAD~1이 없어 returncode != 0 → `clear_committed_files` 미호출 → 큐 잔류 | `_post_commit_clear`에서 returncode != 0이면 즉시 return 0(fail-open). 큐가 남아도 다음 커밋 성공 시 정리되므로 실질적 영향 없음 |
| **review-gate: 병렬 tier 기록 경쟁** | af-test-runner·af-critic·af-cross-review 세 에이전트가 동시에 `record_review_done()`을 호출하면 JSON 덮어쓰기로 일부 tier 유실 가능 | `_state_lock()` fcntl exclusive lock (POSIX 전용; Windows는 best-effort no-op) + atomic rename으로 해결. TOCTOU 방지: files_snapshot은 락 내부 최신 state에서 읽음 |

---

## §12 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-04-30 | v1.2.22 | chore(settings): Windows 환경 hook 경로·권한 정비 — macOS 절대경로→Windows 절대경로 마이그레이션, 중복 hook 엔트리 병합 및 name 필드 추가, hookpy.sh 래퍼로 check_pending_review·check_design_pending 실행, codex·gemini·git 신규 권한 허용 확장 |
| 2026-04-30 | v1.2.22 | `chore(config): settings.local.json Mac→Windows hook 경로 마이그레이션 및 정리 — 중복 hook 항목 제거·hook name 필드 신규 추가, hookpy.sh cross-platform launcher 전환, gemini/codex 허용 명령어 추가, episode_matcher.py 수정, skills/registry.yaml 갱신` |
| 2026-04-30 | v1.2.22 | chore(settings): Windows 경로로 hook 일괄 마이그레이션 — macOS 절대경로→Windows 경로 전환, 중복 hook 항목 제거, hook name 필드 추가(sessionstart/userpromptsubmit/precompact/stop), gemini·codex·git Bash 권한 허용 추가 |
| 2026-04-30 | v1.2.22 | fix(BLOCK-prep): `core/provider_detect.py` ThreadPool race condition 수정 — `_probe_one(provider_id, installed: frozenset[str])` 시그니처 변경, `installed_set`을 ThreadPool 전 main thread 1회 계산 후 각 worker에 전달, `core/providers/registry.py` `_installed_cli_cache_lock` 추가 double-checked locking 패턴 적용 + `invalidate_installed_cli_cache()` lock 보호, `tests/test_provider_detect.py` T13(1회 호출 검증) + T14(6 스레드 concurrent 검증) 추가 + T12 patch 위치 수정 — 22 tests, af-critic WARN, af-cross-review PASS |
| 2026-04-30 | v1.2.22 | feat(provider-detect): Multi-Provider Cross-Review Sprint A — `core/provider_detect.py` 신규 (3-state 감지 AVAILABLE/AUTH_EXPIRED/NOT_INSTALLED, 1h 디스크 캐시 원자 write, AF_SKIP_PROVIDER 마스킹, AGENT_*_CLI_COMMAND env var override 반영, ThreadPoolExecutor 병렬 ping, CLI entry `--json --exclude-self`), `tests/test_provider_detect.py` 20 tests, `af.spec` hiddenimport 추가 |
| 2026-04-29 | v1.2.22 | chore(hook-infra+syncCompyne): 훅 name 필드 추가·순서 재정렬 및 syncCompyne CLI 갱신 — settings.local.json 훅 5개(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd)에 name 필드 부여, UserPromptSubmit 훅을 check_pending_review→check_design_pending 순으로 재배치, git pull·stash/mcp__codex__codex/npm list 권한 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정 |
| 2026-04-29 | v1.2.22 | chore(hook-infra+syncCompyne): hook name 식별자 추가 및 UserPromptSubmit 라우팅 정비 — SessionStart/PreCompact/Stop/SessionEnd hook에 name 필드 신규 추가, UserPromptSubmit을 check_pending_review.py → hook_runner.py로 교체, git pull·stash·npm list·mcp__codex__codex 허용 명령 추가, syncCompyne memory_store/project_log_cli/workspace_context_cli 업데이트 |
| 2026-04-29 | v1.2.22 | chore(hook-config+syncCompyne): 훅 name 식별자 추가 및 UserPromptSubmit 체인 재정비 — settings.local.json 각 훅에 agent_factory_claude_* name 필드 신규 추가, UserPromptSubmit→check_pending_review·StopAsTool→check_design_pending·UserPromptSubmit2→cli_hook_bridge 순서 재배치, git pull/stash·mcp__codex__codex·npm list 권한 신규 허용, syncCompyne memory_store.py·project_log_cli.py·workspace_context_cli.py 수정 |
| 2026-04-29 | v1.2.22 | chore(hook-infra): 훅 설정 재편 및 syncCompyne CLI 신규 추가 — UserPromptSubmit 훅을 hook_runner.py로 전환·PostToolUse를 check_design_pending.py로 이동, 각 훅에 name 필드 추가, allowlist에 git pull/stash·mcp__codex__codex·npm list 추가, syncCompyne/memory_store.py·project_log_cli.py·workspace_context_cli.py 신규 |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): 훅 name 필드 추가·권한 확장 및 syncCompyne 다수 파일 업데이트 — SessionStart/Stop/PreCompact/SessionEnd 훅에 name 태그 신규, git pull·stash·npm list·mcp__codex 허용 추가, UserPromptSubmit 훅을 check_pending_review.py로 재배치, memory_store·project_log_cli·workspace_context_cli 변경 |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): 훅 name 레이블 추가 및 허용 명령어 확장 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 훅에 name 필드 부여, git pull·stash·npm list·mcp__codex__codex 허용 추가, UserPromptSubmit 훅 check_design_pending.py 재배치, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정 |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): 훅 name 필드 추가 및 허용 명령어 확장 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 훅에 name 식별자 신규 추가, git pull·git stash·npm list·mcp__codex__codex 허용 목록 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 업데이트, skill 평가 보고서·승격 파일 갱신 |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): 훅 name 레이블 추가 및 권한 확장, syncCompyne CLI 업데이트 — settings.local.json 훅 항목에 name 필드 신규 부여(sessionstart/userpromptsubmit/precompact/stop/sessionend), UserPromptSubmit·Stop 훅 명령어 재배치, git pull·stash·mcp__codex·npm list 권한 신규, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정 |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): 훅 name 식별자 추가·커맨드 재배치 및 syncCompyne 모듈 갱신 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 5개 훅에 name 필드 추가, UserPromptSubmit 훅을 check_pending_review.py로 재연결, git pull·stash·npm list 허용 커맨드 추가, memory_store·project_log_cli·workspace_context_cli 수정 |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): 훅 트리거 순서 재배열 및 신규 허용 명령어 추가 — SessionStart↔UserPromptSubmit 훅 명령어 위치 교체(hook_runner→check_pending_review→check_design_pending 순 재정렬), git pull/stash·mcp__codex__codex·npm list 허용 목록 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정, new_skill 평가리포트·프로모션 이벤트 누적 |
| 2026-04-29 | v1.2.22 | chore(hook-infra+syncCompyne): 훅 name 레이블 추가 및 UserPromptSubmit 훅 재배치 — settings.local.json 전 훅에 name 필드 신규, UserPromptSubmit을 hook_runner.py로 교체·check_design_pending.py 이동, git pull/stash/mcp__codex 허용 권한 추가, syncCompyne CLI 3개(memory_store·project_log_cli·workspace_context_cli) 업데이트, 스킬 레지스트리 갱신 |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude settings.local 훅 정리 및 syncCompyne 갱신 — UserPromptSubmit 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), 각 hook에 agent_factory_claude_* name 부여, allow 목록에 git pull/stash·mcp__codex__codex 추가, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 및 skills/registry·skill-eval/promotion 리포트 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 명명·UserPromptSubmit 순서 정리 및 syncCompyne 동기화 — settings.local.json hook name 추가(sessionstart/userpromptsubmit/precompact/stop/sessionend), UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash·mcp__codex__codex 권한 허용, skill-usage.jsonl·skill-eval-report·registry.yaml·session_cursor.json 갱신, syncCompyne(AGENTS/LOG_COMMANDS/PROJECT_LOG/WORKSPACE_CONTEXT·memory_store·project_log_cli·workspace_context_cli) 업데이트"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 이름 부여 및 SessionStart/UserPromptSubmit 명령 재배치 — settings.local.json hook name 5종(sessionstart/userpromptsubmit/precompact/stop/sessionend) 추가, UserPromptSubmit 훅을 cli_hook_bridge로 교체하고 check_pending_review/check_design_pending 순서 재배치, mcp__codex__codex·git pull/stash allow 권한 추가, syncCompyne 모듈(memory_store/project_log_cli/workspace_context_cli) 및 docs 갱신, skill-usage.jsonl·skills/registry.yaml 이벤트 누적"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-config+sync-tools): Claude 훅 이름 명명 + 동기화 도구 갱신 — settings.local.json 5개 훅에 agent_factory_claude_* name 부여, UserPromptSubmit/PreCompact 훅 순서 재배치, syncCompyne 메모리·로그·워크스페이스 CLI 갱신, skill-usage.jsonl 프로모션 이벤트 추가, registry.yaml 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude settings 훅 정비 + syncCompyne 도구 동기화 — settings.local.json hook 매트릭스에 name 식별자/check_pending_review·check_design_pending 분리 추가, mcp__codex__codex·git pull/stash 권한 허용, syncCompyne(AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT·memory_store·project_log_cli·workspace_context_cli) 갱신, skill-usage.jsonl·registry.yaml·skill-eval-report·skill-promotion 메타데이터 갱신, bridge_state session_cursor·code-review.md 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 이벤트 분기 정리 + syncCompyne 도구 갱신 — settings.local.json hook 이름/명령 재배치(SessionStart·UserPromptSubmit·PreCompact·Stop·SessionEnd), check_pending_review/check_design_pending 분기 분리, mcp__codex__codex·git pull/stash 권한 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 및 AGENTS/LOG_COMMANDS/PROJECT_LOG/WORKSPACE_CONTEXT 문서 갱신, skill registry/usage·promotion 이벤트 기록"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 매트릭스 + syncCompyne 통합 갱신 — settings.local.json hook name 추가 및 UserPromptSubmit/SessionStart/PreCompact/Stop/SessionEnd 훅 정렬, mcp__codex__codex/git pull·stash 권한 추가, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 및 AGENTS·LOG_COMMANDS·WORKSPACE_CONTEXT 문서 갱신, skill-usage.jsonl/registry.yaml 및 new_skill 평가·승급 리포트 동기화, code-review.md 및 bridge session_cursor 상태 업데이트"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): claude settings hook 정리 + syncCompyne 스킬 사용 로그 갱신 — UserPromptSubmit 훅을 check_pending_review→check_design_pending→cli_hook_bridge 순으로 재배열, 각 훅에 name 식별자(agent_factory_claude_*) 부여, allow 목록에 git pull/stash·mcp__codex__codex 추가, skill-usage.jsonl·session_cursor·registry.yaml 등 런타임 상태 파일 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): 훅 명명 정리 + syncCompyne 워크스페이스 컨텍스트 갱신 — .claude/settings.local.json 훅 name 추가(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd) 및 git pull/stash·mcp__codex__codex 권한 허용, UserPromptSubmit 훅 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), syncCompyne AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT 문서/CLI 갱신, skill-usage.jsonl·registry.yaml·session_cursor.json 상태 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 순서 재정렬 및 syncCompyne 갱신 — settings.local.json hook 순서 변경(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash·mcp__codex 권한 추가, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 업데이트, skill-usage.jsonl 프로모션 이벤트 추가, code-review.md 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude SessionStart/Stop 훅에 name 부여 및 UserPromptSubmit 순서 재정렬 — settings.local.json 훅 5종 name 추가, check_pending_review/check_design_pending/cli_hook_bridge 순서 정리, git pull/stash 권한 허용, skill-usage.jsonl 이벤트 누적, syncCompyne 메모리/로그 CLI 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 이름 부여 + sync 도구 갱신 — settings.local.json 5개 hook에 agent_factory_claude_* name 추가, UserPromptSubmit hook 순서 재배치(check_pending_review→check_design_pending→hook_runner), git pull/stash 권한 허용, syncCompyne CLI 6종(memory_store/project_log_cli/workspace_context_cli/AGENTS.md/LOG_COMMANDS.md/WORKSPACE_CONTEXT.md) 동기화"} |
| 2026-04-29 | v1.2.22 | {"type":"text","text":"chore(hook-config): Claude hook 명명 + 설계 큐 훅 정렬 — settings.local.json hook 5개에 agent_factory_claude_* name 부여, UserPromptSubmit 훅 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용 추가, syncCompyne 로그·메모리 CLI 갱신, skill-usage/registry 스냅샷 업데이트"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 설정 정비 + syncCompyne 동기화 — settings.local.json 훅 name/command 재배치(SessionStart·UserPromptSubmit·PreCompact·Stop·SessionEnd), git pull/stash 권한 추가, syncCompyne AGENTS/PROJECT_LOG/WORKSPACE_CONTEXT/memory_store 갱신, skill-usage.jsonl 이벤트 추가, registry.yaml 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 라우팅 정비 + sync/syncCompyne 메모리 도구 갱신 — settings.local.json hook 매트릭스 재배치(SessionStart/UserPromptSubmit name 부여, check_pending_review/check_design_pending 분리), git pull/stash 권한 허용, skill-usage.jsonl 프로모션 이벤트 추가, syncCompyne memory_store/project_log_cli/workspace_context_cli 갱신, registry.yaml 및 bridge session_cursor 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-config+sync): Claude settings.local.json 훅 명명·재배치 + syncCompyne 동기화 산출물 갱신 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 훅에 agent_factory_claude_* name 부여, UserPromptSubmit 슬롯 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), permissions allow에 'git pull *'·'git stash *' 추가, skill-usage.jsonl·skill-eval-report·session_cursor·registry.yaml 등 동기화 데이터 업데이트"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 이름표·SessionStart 매핑 정리 + syncCompyne 동기화 산출물 갱신 — UserPromptSubmit에 check_pending_review/check_design_pending/cli_hook_bridge 3단 매핑 재정렬, SessionStart/PreCompact/Stop/SessionEnd hook에 agent_factory_claude_* name 부여, settings.local.json allow에 'git pull *'·'git stash *' 추가, syncCompyne memory_store/project_log_cli/workspace_context_cli 및 AGENTS/LOG_COMMANDS/PROJECT_LOG/WORKSPACE_CONTEXT 문서 업데이트, skill-usage.jsonl·skill-eval-report·session_cursor 등 런타임 산출물 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 명명·재배치 + syncCompyne 동기화 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd hook에 name 부여, UserPromptSubmit 슬롯 재배치(check_pending_review→check_design_pending→cli_hook_bridge), settings.local.json에 git pull/stash 권한 추가, syncCompyne 다수 파일 갱신, skill-usage·registry·세션 커서 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude 훅 이름 부여 + 디자인 큐 훅 정렬 + 동기화 도구 갱신 — settings.local.json 5개 훅에 agent_factory_claude_* 이름 추가, UserPromptSubmit 순서를 check_pending_review→check_design_pending→hook_bridge로 재배열, git pull/stash allowlist 등록, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 갱신, skill-usage/registry/세션 커서 메타 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 이름 부여 및 SessionStart 큐 정리 — settings.local.json hook 5종 name 추가(sessionstart/userpromptsubmit/precompact/stop/sessionend), git pull/stash 권한 허용, UserPromptSubmit 큐에 check_design_pending 추가, syncCompyne 문서·CLI 갱신, skill-usage/registry/skill-eval 상태 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 정리 + syncCompyne 동기화 — settings.local.json hook name 부여, UserPromptSubmit/check_pending_review/check_design_pending 순서 재배치, git pull/stash 권한 추가, syncCompyne 모듈 갱신, skill-usage/registry 상태 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 이름 부여 + syncCompyne 도구 정비 — 5개 hook에 agent_factory_claude_* name 추가, UserPromptSubmit 순서를 check_pending_review→check_design_pending→cli_hook_bridge로 재배열, git pull/stash allow 권한 추가, syncCompyne의 memory_store/project_log_cli/workspace_context_cli 갱신, skill-usage.jsonl/registry.yaml 메트릭 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(claude-hooks): Claude Code 훅 설정 정비 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 훅에 agent_factory_claude_* 이름 부여, UserPromptSubmit 훅 순서 재정렬(check_pending_review → check_design_pending → cli_hook_bridge), git pull/git stash 권한 허용, skill-usage.jsonl 프로모션 이벤트 누적"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(claude-hooks): Claude Code 훅 설정 정비 및 동기화 산출물 갱신 — settings.local.json 훅 5종에 name 식별자 추가, UserPromptSubmit/SessionStart 명령 재배치, git pull/stash 권한 허용, skill-usage·session_cursor·syncCompyne 산출물 자동 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 이름표 + check_design_pending 라우팅 정리 — settings.local.json hooks에 agent_factory_claude_* name 5종 부여, UserPromptSubmit 체인을 check_pending_review→check_design_pending→cli_hook_bridge 순으로 재배열, git pull/stash allow 추가, syncCompyne(memory_store·project_log_cli·workspace_context_cli·AGENTS/LOG_COMMANDS/PROJECT_LOG/WORKSPACE_CONTEXT) 갱신, skill-usage.jsonl·skill-eval/promotion·registry.yaml 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 명명·재배치 + syncCompyne 메타 갱신 — settings.local.json hook entry name 추가(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd), UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용 추가, syncCompyne 메모리·로그 CLI 메타 동기화, skill-usage/registry/세션 커서 상태 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude Code 훅 이름 부여 및 동기화 도구 갱신 — settings.local.json 훅에 agent_factory_claude_* name 추가 및 UserPromptSubmit 순서 재배치, git pull/stash 권한 허용, syncCompyne 모듈(memory_store, project_log_cli, workspace_context_cli) 및 문서(AGENTS.md, LOG_COMMANDS.md, PROJECT_LOG.md, WORKSPACE_CONTEXT.md) 업데이트, skill-usage.jsonl·registry.yaml·세션 커서 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 이름 부여 + sync 도구 업데이트 — settings.local.json hook에 agent_factory_claude_* name 추가, git pull/stash 권한 허용, UserPromptSubmit hook 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), syncCompyne 도구(memory_store/project_log_cli/workspace_context_cli) 갱신, skill-usage/registry 메타 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(claude-hooks+sync-tools): Claude settings 훅 정리·이름 부여 + 스킬 사용 로그 기록 — UserPromptSubmit 훅을 check_pending_review→check_design_pending→cli_hook_bridge 순서로 재배치, SessionStart/PreCompact/Stop/SessionEnd 훅에 agent_factory_claude_* name 부여, git pull/stash 권한 허용 추가, data/skill-usage.jsonl에 new_skill candidate 승격 이벤트 누적, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 및 docs/skills 산출물 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude hook 이름 부여 및 sync 도구 갱신 — settings.local.json hook 5종 name 추가(sessionstart/userpromptsubmit/precompact/stop/sessionend), UserPromptSubmit 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용, syncCompyne 도구(memory_store·project_log_cli·workspace_context_cli) 및 문서(AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT) 갱신, skill-usage·registry·promotion 메타데이터 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hooks 이름 추가 + sync state 갱신 — UserPromptSubmit/SessionStart/Stop 등 5개 훅에 agent_factory_claude_* name 부여, settings.local.json permissions에 git pull/stash 허용 추가, UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), syncCompyne 워크스페이스 상태 및 skill-usage 로그 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude 훅 이름 부여 + sync 도구 업데이트 — settings.local.json 훅 5개에 agent_factory_* name 추가, UserPromptSubmit 순서 재배치(check_pending_review→check_design_pending→hook_runner), git pull/stash 권한 허용, syncCompyne CLI/메모리 스토어 갱신, skill-usage 이벤트 누적"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 라우팅 정정 + syncCompyne 스킬 동기화 — UserPromptSubmit/PreCompact/Stop 등 hook 항목에 name 필드 추가, UserPromptSubmit→check_pending_review/check_design_pending/cli_hook_bridge 순서 재배치, settings.local.json allow에 git pull/stash 추가, syncCompyne(AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT·memory_store·project_log_cli·workspace_context_cli) 갱신, skill-usage·registry·new_skill 평가 산출물 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 이름 부여 및 syncCompyne 메모리/로그 갱신 — settings.local.json 훅에 agent_factory_claude_* name 추가, git pull/stash allow 권한 추가, syncCompyne memory_store/project_log_cli/workspace_context_cli 업데이트, skill-usage.jsonl 신규 promotion 이벤트 기록, 설계 큐 검토 산출물 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hooks 이름 부여 + UserPromptSubmit 명령 재배치 — settings.local.json hook entries에 name 필드 추가(sessionstart/userpromptsubmit/precompact/stop/sessionend), check_pending_review·check_design_pending·cli_hook_bridge 실행 순서 정리, git pull/stash 권한 추가, syncCompyne 문서·CLI(memory_store·project_log_cli·workspace_context_cli) 동반 갱신, skill-usage·registry·promotion 메타 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(claude-hooks): Claude CLI 훅 설정 정비 및 동기화 관련 파일 갱신 — settings.local.json 훅에 name 필드(agent_factory_claude_*) 추가, UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용, syncCompyne 워크스페이스/프로젝트 로그 CLI 동기화, skill-usage 이벤트 기록 추가"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 라우팅 정리 및 syncCompyne 워크플로 갱신 — settings.local.json 훅에 name 필드 부여 및 SessionStart/UserPromptSubmit 명령 재배치, git pull/stash 권한 허용, skill-usage.jsonl·new_skill 평가 리포트 갱신, syncCompyne의 memory_store·project_log_cli·workspace_context_cli 및 관련 문서 업데이트, claude/codex 브리지 session_cursor 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(claude-hooks+sync): SessionStart 큐 훅 정상화 + sync 도구 정비 — .claude/settings.local.json 훅 name 부여 및 SessionStart→cli_hook_bridge / UserPromptSubmit→check_pending_review→check_design_pending→cli_hook_bridge 4단계 재배치, git pull/stash allowlist 추가, syncCompyne(memory_store/project_log_cli/workspace_context_cli + AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT 문서) 갱신, skills/registry.yaml·skill-usage.jsonl·new_skill 평가/승급 리포트 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude Code hook 정비 + syncCompyne 모듈 갱신 — UserPromptSubmit에 check_pending_review·check_design_pending 분리, hook 명칭 부여(agent_factory_claude_*), git pull/stash 권한 추가, syncCompyne(memory_store·project_log_cli·workspace_context_cli) 및 skill registry/eval 보고서 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude 훅 이름 부여 및 syncCompyne 동기화 — settings.local.json 훅에 agent_factory_claude_* name 추가, UserPromptSubmit 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용, syncCompyne 도구·문서 갱신, skill-usage/registry/세션 커서 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 이름 부여 및 SessionStart/UserPromptSubmit 핸들러 재배치 — settings.local.json에 agent_factory_claude_* 이름 추가, UserPromptSubmit를 cli_hook_bridge로 이관, SessionStart에 check_pending_review/check_design_pending 분리 배치, git pull/stash allow 추가, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude Code 훅 이름 부여 및 큐 발화 순서 정리 — settings.local.json에 SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 훅 name 추가, UserPromptSubmit 단계에 check_pending_review→check_design_pending→cli_hook_bridge 순서 재배치, git pull/git stash 권한 추가, syncCompyne 모듈·문서 갱신, skill-usage 이벤트 누적"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hook-infra+sync): Claude Code 훅 이름 부여 + syncCompyne 동기화 갱신 — settings.local.json 훅에 agent_factory_claude_* 이름 부착 및 git pull/stash 권한 추가, UserPromptSubmit/SessionStart 훅 명령 재배치, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 갱신, skill-usage 이벤트 추가, 세션 커서·skill 평가 리포트 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 명명·설계 큐 라우팅 정비 + syncCompyne 갱신 — UserPromptSubmit 훅에 check_pending_review/check_design_pending/cli_hook_bridge 3단계 명시화, agent_factory_claude_* hook name 부여, settings.local.json allow에 git pull/stash 추가, skill-usage.jsonl·registry.yaml·skill-eval-report 동기화, syncCompyne 문서·CLI 모듈 업데이트"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-config): Claude Code 훅 인프라 정리 + 동기화 도구 업데이트 — settings.local.json hook name 식별자 추가(sessionstart/userpromptsubmit/precompact/stop/sessionend), git pull/stash 권한 허용, UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), syncCompyne 모듈 갱신(memory_store·project_log_cli·workspace_context_cli), skill-usage·session_cursor 상태 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 명명·설계큐 연동 정비 + syncCompyne 동기화 — settings.local.json 훅에 agent_factory_claude_* name 부여 및 UserPromptSubmit 순서를 check_pending_review→check_design_pending→cli_hook_bridge로 재배치, git pull/stash allow 추가, skill-usage.jsonl·skill-eval-report·skill-promotion·registry.yaml 갱신, syncCompyne(memory_store/project_log_cli/workspace_context_cli/AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT) 문서·CLI 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude 훅 이름 부여 + 동기화 도구 갱신 — settings.local.json hook name 5종(sessionstart/userpromptsubmit/precompact/stop/sessionend) 추가, design/review 큐 훅 순서 재배치, syncCompyne memory_store/project_log_cli/workspace_context_cli 갱신, skills/registry.yaml 업데이트, skill-usage.jsonl 이벤트 추가"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(claude-hooks+sync): Claude Code 훅 정렬 및 syncCompyne 갱신 — UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), 각 훅에 name 식별자 추가, git pull/stash 권한 허용, skill-usage/registry/promotion 데이터 갱신, syncCompyne 메모리·로그·워크스페이스 CLI 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude hook 라우팅 재배치 + syncCompyne 동기화 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 훅에 name 식별자 부여, UserPromptSubmit 순서를 check_pending_review→check_design_pending→cli_hook_bridge로 재정렬, settings.local.json allow에 git pull/stash 추가, skill-usage.jsonl·skill-eval-report·skill-promotion·registry.yaml 갱신, syncCompyne 메모리/로그/컨텍스트 CLI 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 이름 부여 및 순서 정정 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 훅에 agent_factory_claude_* name 추가, UserPromptSubmit 훅 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용, syncCompyne 메모리/로그 CLI 갱신 및 skill-usage.jsonl 이벤트 추가"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 설정 정비 및 syncCompyne 도구 갱신 — settings.local.json hook name 부여 및 SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 식별자 추가, git pull/stash 권한 허용, syncCompyne AGENTS.md·LOG_COMMANDS.md·PROJECT_LOG.md·WORKSPACE_CONTEXT.md 문서 갱신, memory_store.py·project_log_cli.py·workspace_context_cli.py 수정, skill-usage.jsonl·registry.yaml·skill-eval-report.json 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(claude-hooks): Claude Code 훅 설정 정비 및 권한 추가 — settings.local.json hook 엔트리에 name 필드 부여(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd), UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), 'git pull *'·'git stash *' allow 권한 추가, syncCompyne 워크스페이스 컨텍스트·프로젝트 로그·메모리 스토어 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude hook 매핑 정정 및 syncCompyne 동기화 — UserPromptSubmit 훅을 cli_hook_bridge로 환원, PreToolUse/SessionEnd 등에 name 식별자 추가, settings.local.json allow에 git pull/stash 등록, skill-usage.jsonl·skill-eval-report·registry 갱신, syncCompyne 문서·CLI 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 정리 및 syncCompyne 동기화 — UserPromptSubmit에 check_pending_review/check_design_pending 분리, 각 훅에 name 식별자 부여, git pull/stash 권한 추가, syncCompyne 메모리·로그·워크스페이스 CLI 갱신, skill-usage·registry·promotion 리포트 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude hook 정리 및 syncCompyne 동기화 — UserPromptSubmit hook 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), 각 hook에 agent_factory_claude_* name 부여, settings.local.json 권한 추가(git pull/stash), syncCompyne 메모리·로그·워크스페이스 CLI 갱신, skills/registry.yaml 및 new_skill 평가/프로모션 리포트 업데이트"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 설정 정리 및 syncCompyne 동기화 — settings.local.json hook name 부여(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd), UserPromptSubmit 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 추가, syncCompyne 메모리·로그·워크스페이스 컨텍스트 갱신, skill-usage·registry·session_cursor 상태 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 이름 부여 및 sync 도구 갱신 — settings.local.json 훅에 agent_factory_claude_* name 5종 추가, git pull/stash 권한 허용, UserPromptSubmit 훅 순서 재배치, syncCompyne memory_store/project_log_cli/workspace_context_cli 갱신, skills/registry.yaml + new_skill 평가·승격 리포트 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 훅에 agent_factory_claude_* name 부여 — UserPromptSubmit hook 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), settings.local.json allow에 git pull/stash 추가, skill-usage.jsonl new_skill candidate 승격 이벤트 누적, syncCompyne 도구 일괄 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 이름 부여 및 SessionStart/UserPromptSubmit 순서 정리 — settings.local.json에 agent_factory_claude_* name 5종 추가, UserPromptSubmit hook 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 및 docs/code-review·skill-usage·session_cursor 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude hook 라우팅 재정렬 + syncCompyne 정비 — settings.local.json hook 명명(name 필드)·SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd 매트릭스 재배치, git pull/stash 권한 추가, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 갱신, skill-usage·registry·session_cursor 상태 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude hook 이름 부여 및 동기화 워크스페이스 확장 — settings.local.json hook 5종에 name 부여(sessionstart/userpromptsubmit/precompact/stop/sessionend), git pull/stash 권한 추가, UserPromptSubmit hook 순서 재배치(check_pending_review→check_design_pending→hook_runner), syncCompyne 워크스페이스 컨텍스트/메모리/프로젝트 로그 CLI 갱신, skill-usage/registry 이벤트 추가"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 이름 부여 및 syncCompyne 동기화 — settings.local.json hook name 5개(sessionstart/userpromptsubmit/precompact/stop/sessionend) 추가, UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→hook_runner), git pull/stash 권한 허용, syncCompyne 문서·CLI·memory_store 갱신, skills/registry+new_skill 메타데이터 업데이트"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(claude-hooks): Claude Code 훅 설정 정리 + 권한 추가 — UserPromptSubmit 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), 각 훅에 agent_factory_claude_* name 부여, git pull/stash 권한 허용, skill-usage.jsonl·session_cursor·skill-eval-report 등 런타임 산출물 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 이름 부여·체크 스크립트 재배치 + syncCompyne 도구 갱신 — settings.local.json 훅에 agent_factory_claude_* name 5종 추가, UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용, syncCompyne memory_store·project_log_cli·workspace_context_cli 갱신, skills/registry.yaml·skill-eval-report·skill-promotion 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 이름 부여·재배치와 syncCompyne 도구 정비 — SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd hook에 agent_factory_claude_* name 추가 및 check_pending_review/check_design_pending 순서 재배치, settings.local.json에 git pull/stash 권한 허용, syncCompyne의 memory_store·project_log_cli·workspace_context_cli 갱신, skill-usage.jsonl 및 registry/skill-eval-report 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude 훅 인프라 정리 및 동기화 도구 업데이트 — settings.local.json 훅에 name 필드 부여(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd), git pull/stash 권한 추가, UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), syncCompyne CLI/문서 갱신, 스킬 사용 로그 누적"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude settings 훅 정리 + syncCompyne 갱신 — UserPromptSubmit 훅에 check_pending_review/check_design_pending 분리 등록, SessionStart/PreCompact/Stop/SessionEnd 훅에 agent_factory_claude_* name 부여, git pull/stash 권한 추가, skill-usage.jsonl·skill-eval-report·skill-promotion 갱신, syncCompyne(memory_store·project_log_cli·workspace_context_cli) 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(claude-hooks+sync): Claude hook 정비 및 syncCompyne 갱신 — settings.local.json hook name 부여(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd) 및 design/review hook 순서 재배치, git pull/stash 권한 추가, syncCompyne(AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT·memory_store·project_log_cli·workspace_context_cli) 갱신, skill-usage·registry·세션 커서 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude 훅 이름 부여 + 디자인 큐 훅 순서 정리 + syncCompyne 도구 갱신 — settings.local.json hooks에 agent_factory_claude_* name 추가, UserPromptSubmit에 check_pending_review→check_design_pending→cli_hook_bridge 3단 체인 재배치, git pull/stash 권한 허용, syncCompyne memory_store/project_log_cli/workspace_context_cli 및 AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT 문서 동기화, skill-usage.jsonl·skill-eval-report·skill-promotion·registry.yaml 결과 반영"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hooks+sync): Claude Code 훅 이름 부여 및 SessionStart/UserPromptSubmit 명령 재배치 — settings.local.json 훅 5종(sessionstart/userpromptsubmit/precompact/stop/sessionend)에 name 추가, UserPromptSubmit/SessionStart 훅 명령 재정렬, git pull/stash 권한 추가, syncCompyne 문서·CLI(memory_store/project_log_cli/workspace_context_cli) 동기화, skill-usage/registry/리뷰 메타 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 라우팅 재배치 및 syncCompyne 갱신 — settings.local.json hook name 추가(SessionStart/UserPromptSubmit/PreCompact/Stop/SessionEnd) 및 UserPromptSubmit 3개 명령 순서 재정렬, git pull/stash 권한 허용, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 및 docs 갱신, skill-usage·registry·session_cursor 상태 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 정리 및 syncCompyne 동기화 — settings.local.json hook name/순서 재정렬, git pull/stash 권한 추가, skill-usage·registry·promotion 갱신, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 갱신, bridge session_cursor 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog": "chore(hook-infra+sync): Claude SessionStart/UserPromptSubmit 훅 정리 및 syncCompyne 동기화 — settings.local.json 훅 name 부여(agent_factory_claude_sessionstart/userpromptsubmit/precompact/stop/sessionend), git pull/stash 권한 추가, UserPromptSubmit에 check_pending_review/check_design_pending/cli_hook_bridge 3단 체인 정렬, skill-usage.jsonl·session_cursor·skill-eval-report 갱신, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 라우팅 정리 및 syncCompyne 도구 갱신 — UserPromptSubmit/SessionStart 훅에 name 식별자 추가, check_pending_review/check_design_pending 매트릭스 재배치, settings.local.json에 git pull/stash 권한 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 갱신, skill-usage.jsonl·registry.yaml·session_cursor 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): Claude hook 이름 부여 및 sync 도구 갱신 — settings.local.json hook name 5종 추가(sessionstart/userpromptsubmit/precompact/stop/sessionend), git pull/stash 권한 추가, UserPromptSubmit hook 순서 재배열(check_pending_review→check_design_pending→cli_hook_bridge), syncCompyne CLI/메모리 스토어 갱신, skill-usage.jsonl 신규 promotion 이벤트 기록"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 설정 정리 및 syncCompyne 동기화 — settings.local.json hook 이름 부여(agent_factory_claude_*)·UserPromptSubmit 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 추가, skill-usage.jsonl·skill-eval/promotion 갱신, syncCompyne(memory_store·project_log_cli·workspace_context_cli) 및 docs(AGENTS·LOG_COMMANDS·PROJECT_LOG·WORKSPACE_CONTEXT) 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 설정 정비 + syncCompyne 동기화 — settings.local.json hook name 추가/순서 재배치, git pull·stash 권한 추가, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 갱신, skills/registry·new_skill eval 보고 동기화, code-review.md·세션 커서 갱신"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hook-infra+sync): 훅 이름 정규화 및 syncCompyne 갱신 — settings.local.json 훅에 agent_factory_claude_* name 부여, UserPromptSubmit 훅 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 추가, skill-usage.jsonl 이벤트 추가, syncCompyne 워크스페이스/메모리 스토어 문서 및 CLI 동기화"} |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 정의 정리 및 syncCompyne 워크스페이스 갱신 — settings.local.json 훅 name 부여(sessionstart/userpromptsubmit/precompact/stop/sessionend), git pull/stash 권한 추가, UserPromptSubmit hook 순서 재배치(check_pending_review→check_design_pending→cli_hook_bridge), syncCompyne 메모리/로그/워크스페이스 CLI 및 문서 갱신, skills/new_skill 평가·승급 리포트와 registry/skill-usage 업데이트"} |
| 2026-04-29 | v1.2.22 | chore(hooks+sync): Claude hook 설정 정비 + syncCompyne 모듈 동기화 — settings.local.json hook name 추가 및 SessionStart/UserPromptSubmit 순서 재배치, git pull/stash 권한 허용, syncCompyne(AGENTS/LOG_COMMANDS/PROJECT_LOG/WORKSPACE_CONTEXT 문서 + memory_store/project_log_cli/workspace_context_cli) 갱신, skill-usage·registry·promotion 메타 동기화 |
| 2026-04-29 | v1.2.22 | {"changelog":"chore(hooks+sync): Claude hook 이름·순서 정비 및 syncCompyne 동기화 — SessionStart/PreCompact/Stop/SessionEnd hook에 agent_factory_claude_* name 부여, UserPromptSubmit 3-step 순서 재정렬(check_pending_review→check_design_pending→cli_hook_bridge), git pull/stash 권한 허용, syncCompyne AGENTS/LOG/PROJECT_LOG/WORKSPACE_CONTEXT 및 memory_store/CLI 갱신, skill-usage·registry·session_cursor 상태 동기화"} |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): 훅 순서 재배치·name 태그 추가 및 syncCompyne CLI 업데이트 — UserPromptSubmit 훅을 check_pending_review.py로 재배치, Stop 훅을 check_design_pending.py로 재배치, 훅 엔트리 5개에 name 필드 추가, git pull/stash 허용 명령 신규 등록, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정 |
| 2026-04-29 | v1.2.22 | chore(hook-infra+syncCompyne): 훅 name 필드 추가 및 hook 체인 재정렬 — sessionstart/userpromptsubmit/precompact/stop/sessionend에 name 필드 부여, UserPromptSubmit 훅 커맨드를 check_pending_review→hook_runner 순으로 재정렬, git pull/stash 허용 권한 추가, syncCompyne 모듈 업데이트 |
| 2026-04-29 | v1.2.22 | chore(hook-infra+syncCompyne): 훅 name 식별자 추가 및 커맨드 재배치, syncCompyne 모듈 갱신 — settings.local.json 훅 5개에 name 필드 추가(sessionstart/userpromptsubmit/precompact/stop/sessionend), UserPromptSubmit 훅을 check_pending_review.py → hook_runner.py로 교체, git pull/stash 허용 명령 추가, syncCompyne 4개 파일(memory_store.py·project_log_cli.py·workspace_context_cli.py·WORKSPACE_CONTEXT.md) 업데이트 |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): hook 실행 순서 재편성 및 syncCompyne 모듈 업데이트 — SessionStart→check_pending_review·UserPromptSubmit→check_design_pending·Stop→hook_runner 순서 재배치, git pull/stash 허용 권한 추가, syncCompyne memory_store/project_log_cli/workspace_context_cli 갱신, new_skill 평가 이벤트 신규 기록 |
| 2026-04-29 | v1.2.22 | chore(settings+syncCompyne): hook name 식별자 추가 및 UserPromptSubmit 훅 재배치 — SessionStart/PreCompact/Stop/SessionEnd hook에 name 필드 추가, UserPromptSubmit hook을 hook_runner cli_hook_bridge로 교체, PostToolUse hook 순서 재정렬(check_pending_review→check_design_pending), syncCompyne memory_store·project_log_cli·workspace_context_cli 수정 |
| 2026-04-29 | v1.2.22 | chore(hook-infra+syncCompyne): 훅 name 식별자 추가 및 UserPromptSubmit 재배열 — SessionStart/PreCompact/Stop/SessionEnd 훅에 name 필드 신규 추가, UserPromptSubmit을 cli_hook_bridge로 교체, syncCompyne 4개 모듈(memory_store·project_log_cli·workspace_context_cli·AGENTS) 업데이트, 스킬 레지스트리·평가 보고서 갱신 |
| 2026-04-29 | v1.2.22 | chore(hook-infra+syncCompyne): 훅 name 필드 추가 및 UserPromptSubmit 명령어 재연결 — SessionStart·PreCompact·Stop·SessionEnd 훅 name 태그 신규, UserPromptSubmit 훅을 hook_runner.py로 재라우팅, syncCompyne memory_store/project_log_cli/workspace_context_cli 수정, 스킬 레지스트리·평가 보고서 데이터 갱신 |
| 2026-04-29 | v1.2.22 | chore(syncCompyne+skills): syncCompyne CLI·메모리 모듈 업데이트 및 스킬 평가 데이터 갱신 — memory_store.py·project_log_cli.py·workspace_context_cli.py 수정, new_skill 프로모션 이벤트 추가(feedback_events 9→11), skills/registry.yaml 갱신, 브리지 세션 커서 동기화 |
| 2026-04-29 | v1.2.22 | `chore(settings): 권한 목록 정리·훅 절대경로 전환 및 syncCompyne 일괄 갱신 — 불필요 Bash 권한 32개 제거, 훅에 name 필드 신규 추가(SessionStart/UserPromptSubmit/PreCompact/Stop), python3→python 절대경로 변환, syncCompyne memory_store·project_log_cli·workspace_context_cli·문서 6개 수정, skills registry·eval·promotion 보고서 갱신` |
| 2026-04-29 | v1.2.22 | chore(settings/syncCompyne): hook 명령 절대경로·이름 필드 추가 및 권한 목록 정리 — settings.local.json 불필요 Bash 권한 30개 제거, hook command python3→python 절대경로 변환, hook name 필드 신규 추가, syncCompyne 모듈 4종(memory_store/project_log_cli/workspace_context_cli/AGENTS) 업데이트, skills registry·eval-report 갱신 |
| 2026-04-29 | v1.2.22 | `chore(settings/syncCompyne): Claude hook 절대 경로 전환 및 permissions 정리 — hook 명령 python3/$PWD → python/Windows 절대경로 교체, 각 hook에 name 필드 신규 추가, 불필요 permissions 30여 항목 제거, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정, skills registry·eval-report 갱신` |
| 2026-04-29 | v1.2.22 | chore(settings): Windows 절대경로 hook 명령어로 전환 — permissions 불필요 항목 정리, 각 hook에 name 필드 추가, PostToolUse 훅 제거, syncCompyne(memory_store/project_log_cli/workspace_context_cli) 업데이트, 스킬 레지스트리·평가 리포트 갱신 |
| 2026-04-29 | v1.2.22 | chore(settings): Windows worktree 환경 맞게 설정 재정비 — permissions 허용 목록 대폭 축소·재정비, hook 명령을 `python3 $PWD` 상대경로 → `python D:/hoonProJect/worktrees/…` 절대경로로 변경, PostToolUse 코드리뷰 hook 제거, syncCompyne CLI 3종(memory_store·project_log_cli·workspace_context_cli) 업데이트, skills registry/eval-report 갱신 |
| 2026-04-29 | v1.2.22 | chore(settings,syncCompyne): Windows 워크트리 환경 적응 및 스킬 레지스트리 갱신 — hook 커맨드를 `python3 ./$PWD` 상대경로에서 Windows 절대경로로 전환, 불필요한 allow 권한 36개 제거 및 PostToolUse Write\|Edit hook 삭제, syncCompyne 4개 파일(AGENTS.md·PROJECT_LOG·memory_store·context_cli) 업데이트, skills/registry.yaml·eval-report·promotion 갱신, fsa_loop.py·test_phase7 수정 |
| 2026-04-29 | v1.2.22 | `refactor(settings+syncCompyne): settings.local.json permissions 블록 제거 및 hook 절대경로 전환 — allow/deny 목록 삭제, hook command python3→python 절대경로+name 필드 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정, skills registry 업데이트` |
| 2026-04-29 | v1.2.22 | chore(settings/syncCompyne): 훅 절대경로 전환·권한목록 제거 및 syncCompyne 다중 파일 업데이트 — settings.local.json allow/deny 권한 블록 삭제, 훅 명령어 `$PWD`→절대경로+`name` 필드 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정, skills registry·new_skill 평가 결과 갱신 |
| 2026-04-29 | v1.2.22 | `chore(settings,syncCompyne): hook 절대경로·명칭 적용 및 permissions 블록 정리 — settings.local.json permissions(allow/deny) 섹션 전체 제거, hook 커맨드에 name 필드 추가 및 python3/$PWD→python/절대경로(Windows) 교체, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정, skills registry/eval 갱신` |
| 2026-04-29 | v1.2.22 | chore(settings/syncCompyne): settings.local.json permissions 제거·hook 절대경로 적용 — allow/deny permissions 블록 전면 삭제, hook 4개에 name 필드 추가 및 Windows 절대경로 변환, syncCompyne 모듈(memory_store·project_log_cli·workspace_context_cli) 수정, skills registry/eval-report 갱신 |
| 2026-04-29 | v1.2.22 | chore(settings,syncCompyne): Windows 절대경로 hook 전환 및 syncCompyne CLI 모듈 신규 추가 — settings.local.json 권한 블록 제거·hook 명칭 부여·python3→python 절대경로 고정, syncCompyne/memory_store.py 신규, syncCompyne/project_log_cli.py 신규, syncCompyne/workspace_context_cli.py 신규, skills/registry.yaml 스킬 승격 반영 |
| 2026-04-29 | v1.2.22 | `chore(settings/syncCompyne): settings.local.json 권한 블록 제거 및 훅 절대경로 전환 — permissions allow/deny 전체 삭제, 훅 name 필드 신규 추가, python3→python 절대경로 전환, syncCompyne 4파일(memory_store·project_log_cli·workspace_context_cli·AGENTS) 수정, skills registry·eval 갱신` |
| 2026-04-29 | v1.2.22 | chore(settings/syncCompyne): settings permissions 제거·hook 절대경로화 및 syncCompyne 모듈 정비 — settings.local.json permissions 블록 전체 제거, hook 4종에 name 필드 추가·절대경로 지정, syncCompyne/memory_store·project_log_cli·workspace_context_cli 수정, skills/registry.yaml 및 new_skill 평가·프로모션 갱신 |
| 2026-04-29 | v1.2.22 | `chore(settings,syncCompyne): hook 절대경로 고정 및 permissions 블록 정리 — settings.local.json allow/deny 전체 제거, hook command python3→python 절대경로(Windows) 전환, hook name 필드 신규 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정, skills registry 평가 결과 갱신` |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): `_apply_evolution_guard()` 메서드 신규 추출 — Level 4→5 강제 에스컬레이션 인라인 로직을 별도 메서드로 분리, `skill_dir` 반환값 추가해 `_try_evolve_failed_skill`에 전달, hook 커맨드 절대경로·name 필드 추가, `Bash(codex exec *)` 권한 신규 등록 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): _apply_evolution_guard() 신규 메서드 추출 및 hook 절대경로 고정 — Level 4→5 에스컬레이션 가드를 _apply_evolution_guard()로 분리(신규), skill_dir 반환값 추가로 이중 탐색 방지, hook 커맨드 $PWD→절대경로 변경 + 명칭 필드 추가, Bash(codex exec *) 권한 신규 허용, syncCompyne CLI 다수 수정 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop,settings): FSA 에스컬레이션 가드 추출 및 훅 설정 개선 — `_apply_evolution_guard()` 신규 메서드로 Level 4→5 강제 로직 분리·`skill_dir` 반환 추가, 훅 커맨드 절대경로·name 필드 추가, `Bash(codex exec *)` 권한 추가, syncCompyne memory_store·log_cli·workspace_context_cli 업데이트 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop,settings): `_apply_evolution_guard()` 신규 메서드 추출 및 훅 절대 경로 전환 — Level4→5 강제 에스컬레이션 로직 분리+`skill_dir` 반환값 추가, hook `name` 필드 추가 및 `$PWD` → 절대 경로 고정, `codex exec *` 권한 허용, syncCompyne CLI 다수 수정 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): Level 4→5 에스컬레이션 가드를 `_apply_evolution_guard()` 메서드로 추출 — `_apply_evolution_guard()` 신규 메서드(탐지 스킬 dir 반환), `skill_dir` 파라미터를 `_try_evolve_failed_skill` 호출에 전달, settings.local.json 훅 명칭·절대경로 변환 및 `codex exec` 권한 추가, syncCompyne 메모리·로그·컨텍스트 CLI 갱신 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): _apply_evolution_guard() 신규 메서드 추출 — Level 4→5 에스컬레이션 가드 로직 분리(신규 메서드), skill_dir 반환값을 _try_evolve_failed_skill에 전달, settings.local.json hook에 name 필드+절대경로 고정, Bash(codex exec *) 허용 추가 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): `_apply_evolution_guard()` 신규 메서드로 Level 4→5 에스컬레이션 가드 추출 — `skill_dir` 반환값 추가로 이중 탐색 방지, settings.local.json 훅 name 필드·절대경로 고정·`codex exec *` 허용 추가, syncCompyne CLI 및 skills registry 갱신 |
| 2026-04-29 | v1.2.22 | refact(fsa_loop): `_apply_evolution_guard()` 메서드 신규 추출 및 훅 설정 절대경로 고정 — Level 4→5 가드 인라인 로직을 `_apply_evolution_guard()`로 분리, `skill_dir` 반환값을 `_try_evolve_failed_skill`에 전달(이중 탐색 방지), settings.local.json 훅 커맨드 절대경로 변경(python3→python), 훅 name 필드 추가, `codex exec *` 권한 허용 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): Level 4→5 에스컬레이션 가드를 `_apply_evolution_guard()` 신규 메서드로 추출 — `skill_dir` 반환값 추가로 이중 탐색 방지, hook 커맨드 절대경로 전환, hook `name` 필드 추가, `codex exec *` 권한 허용 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop/settings): evolution guard 메서드 분리 및 훅 설정 절대경로화 — `_apply_evolution_guard()` 신규 메서드 추출(Level 4→5 강제 로직 캡슐화), `skill_dir` 파라미터 downstream 전달 추가, Claude 훅 name 필드 추가 및 `python3 ./` → `python D:/` 절대경로 변환, `Bash(codex exec *)` 권한 신규 허용, syncCompyne CLI 모듈(memory_store·project_log·workspace_context) 갱신 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): evolution guard 메서드 분리 및 hook 설정 개선 — `_apply_evolution_guard()` 신규 추출(Level 4→5 강제 로직 캡슐화), `skill_dir` 파라미터 `_try_evolve_failed_skill` 전달로 이중 탐색 방지, hook 명령어 name 필드·절대 경로 적용(python3→python), `codex exec` 허용 목록 추가 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): Level 4→5 에스컬레이션 가드를 `_apply_evolution_guard()` 메서드로 추출 — `skill_dir` 반환값으로 이중 탐색 방지, settings.local.json hook 커맨드 절대경로화+name 필드 추가, `codex exec *` 허용 등록, syncCompyne CLI 다수 수정 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): `_apply_evolution_guard()` 신규 메서드로 Level 4→5 강제 에스컬레이션 가드 분리 — `skill_dir` 파라미터를 `_try_evolve_failed_skill` 호출부에 전달, `.claude/settings.local.json` hook 절대경로+이름 명시 및 `codex exec` 권한 추가, syncCompyne `memory_store`·`project_log_cli`·`workspace_context_cli` 업데이트, `skills/registry.yaml` 및 `skill-eval-report` 갱신 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): 진화 가드 로직 `_apply_evolution_guard()` 메서드로 추출 — Level 4→5 인라인 조건 제거·`skill_dir` 반환값 추가, hook 커맨드 절대경로+이름 필드 전환, `codex exec` 권한 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 다중 수정 |
| 2026-04-29 | v1.2.22 | ``` |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): `_apply_evolution_guard()` 신규 추출로 Level 4→5 에스컬레이션 가드 분리 — `skill_dir` 반환값 추가로 이중 탐색 방지, settings.local.json hook 명령을 절대경로로 고정 및 `name` 필드 추가, `Bash(codex exec *)` 허용 권한 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 업데이트 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): `_apply_evolution_guard()` 신규 추출로 Level 4→5 진화 가드 로직 분리 — 인라인 조건을 메서드로 리팩터링, `detected_skill_dir` 반환으로 이중 탐색 방지, 훅 절대경로·이름 필드 고정, `codex exec` Bash 권한 추가 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): `_apply_evolution_guard()` 신규 메서드 추출 및 hook 절대경로 고정 — Level 4→5 강제 에스컬레이션 로직을 `_apply_evolution_guard()`로 분리·`skill_dir` 반환값 추가, hook command `python3 ./` → `python D:/...` 절대경로로 교체 + hook name 필드 추가, `codex exec *` allow 권한 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정 |
| 2026-04-29 | v1.2.22 | `refactor(fsa-loop): _apply_evolution_guard() 신규 추출 — Level4→5 강제 에스컬레이션 분리·skill_dir 반환으로 이중 탐색 방지, hook 명령 절대경로 전환+name 필드 추가, codex exec 권한 허용, syncCompyne CLI 3종 업데이트` |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): `_apply_evolution_guard()` 메서드 신규 추출로 Level 4→5 에스컬레이션 가드 분리 — `skill_dir` 반환으로 이중 탐색 방지, settings.local.json 훅 명칭·절대경로 전환, `codex exec *` 권한 신규 허용, syncCompyne CLI·메모리스토어 업데이트 |
| 2026-04-29 | v1.2.22 | refactor(fsa_loop): FSALoop 진화 가드 로직 메서드 분리 — `_apply_evolution_guard()` 신규 추출(Level 4→5 강제 조건 캡슐화), `skill_dir` 파라미터를 `_try_evolve_failed_skill` 호출로 전달, settings.local.json hook 명칭 추가 및 절대경로 적용, `Bash(codex exec *)` 허용 권한 추가 |
| 2026-04-29 | v1.2.22 | chore(settings+fsa_loop): Windows hook 절대경로 고정 및 에스컬레이션 가드 리팩터 — settings.local.json hook 경로 `python3/$PWD`→`python/절대경로` 변경 및 name 필드 추가, `Bash(codex exec *)` 허용 권한 추가, `fsa_loop._apply_evolution_guard()` 신규 메서드 추출(인라인 레벨4→5 강제 로직 제거), syncCompyne `memory_store`·`project_log_cli`·`workspace_context_cli` 수정 |
| 2026-04-29 | v1.2.22 | fix(fsa_loop): Level 4→5 에스컬레이션 과잉 차단 수정 — 전역 차단을 사이클별 per-skill 차단으로 변경(`_detect_failed_skill_dir` 활용), settings.local.json 훅에 name 필드 추가 및 절대경로 고정, `codex exec *` 권한 허용 추가, 스킬 프로모션 이벤트 기록 갱신 |
| 2026-04-29 | v1.2.22 | fix(fsa_loop): Level 4→5 에스컬레이션 전역 차단 제거 — 사이클별 탐지 스킬 단위로 강제 적용(`_detect_failed_skill_dir`), settings 훅 절대경로+name 필드 전환, `Bash(codex exec *)` 권한 신규, syncCompyne 다중 CLI 파일 수정 |
| 2026-04-29 | v1.2.22 | fix(fsa_loop): Level 4→5 에스컬레이션을 전역 차단에서 사이클별 스킬 단위 차단으로 수정 — `_detect_failed_skill_dir` 활용해 현재 탐지 스킬만 Level 5 강제, hook 명령어 절대경로화 및 이름 추가, `Bash(codex exec *)` 권한 신규, syncCompyne CLI(`memory_store`·`project_log_cli`·`workspace_context_cli`) 갱신 |
| 2026-04-29 | v1.2.22 | fix(fsa_loop): Level 4→5 에스컬레이션 전역 차단 제거 — 현재 탐지 스킬만 `_evolution_failed_skills` 조회하도록 `_decide_escalation` 수정, `.claude/settings.local.json` hook에 `name` 필드·절대경로 적용, `codex exec *` 허용 추가, `syncCompyne` CLI 3종(`memory_store`, `project_log_cli`, `workspace_context_cli`) 갱신 |
| 2026-04-29 | v1.2.22 | fix(fsa_loop): Level 4→5 에스컬레이션 전역 차단을 사이클별 차단으로 교체 — `_detect_failed_skill_dir`로 현재 사이클 탐지 스킬만 Level 5 강제(`_evolution_failed_skills` 전역 블록 제거), 훅 커맨드 절대 경로+`name` 필드 추가, `codex exec *` 권한 허용, syncCompyne 워크스페이스·로그·메모리 CLI 업데이트 |
| 2026-04-29 | v1.2.22 | chore(settings,syncCompyne): 훅 절대경로·이름 지정 및 syncCompyne 전면 갱신 — settings.local.json 훅 명령을 `python3` 상대경로→`python` 절대경로로 교체, SessionStart·UserPromptSubmit·PreCompact·Stop·SessionEnd 훅 5개에 `name` 필드 추가, `Bash(codex exec *)` 허용권한 신규 추가, syncCompyne `memory_store.py`·`project_log_cli.py`·`workspace_context_cli.py`·`AGENTS.md` 수정 |
| 2026-04-29 | v1.2.22 | `chore(settings/syncCompyne): hook 명령어 절대경로 전환 및 syncCompyne 정비 — python3 상대경로→python 절대경로 수정, hook name 필드 5개 신규(agent_factory_claude_*), Bash(codex exec *) 권한 추가, syncCompyne CLI 3종(memory_store·project_log_cli·workspace_context_cli) 갱신` |
| 2026-04-29 | v1.2.22 | chore(settings): hook 커맨드 Windows 절대경로 고정 및 syncCompyne 모듈 업데이트 — settings.local.json 훅 5개에 `name` 필드 추가 및 `$PWD` 상대경로를 절대경로로 교체, `Bash(codex exec *)` 허용 목록 추가, syncCompyne memory_store·project_log_cli·workspace_context_cli 수정, skill-eval-report 및 registry.yaml 갱신 |
| 2026-04-29 | v1.2.22 | chore(settings): Claude hook 경로 절대경로로 고정 및 훅 이름 부여 — python3→python+절대경로 변환(5개 훅), 각 훅에 name 필드 추가(agent_factory_claude_*), Bash allowlist에 `codex exec *` 허용 추가, skill-usage.jsonl 이벤트 누적, syncCompyne 문서·CLI 업데이트 |
| 2026-04-29 | v1.2.22 | `chore(settings+syncCompyne): CLI hook 절대경로·명칭 고정 및 syncCompyne 모듈 업데이트 — hook 명령어 python3→python 절대경로 전환, 5개 hook에 name 필드 추가, Bash(codex exec *) 권한 허용, memory_store·project_log_cli·workspace_context_cli 수정` |
| 2026-04-29 | v1.2.22 | ``` |
| 2026-04-29 | v1.2.22 | chore(settings,syncCompyne): Windows 절대 경로 hook 설정 전환 및 syncCompyne 다중 파일 갱신 — hook_runner.py 경로를 python3+상대경로→python+절대경로로 수정, `codex exec *` 허용 권한 추가, skill-eval-report/promotion 이벤트 누적, syncCompyne memory_store·project_log_cli·workspace_context_cli 로직 업데이트 |
| 2026-04-28 | v1.2.22 | chore(settings): Claude hook 절대 경로 전환 및 Stage-1 gitignore 추가 — 5개 hook에 `name` 필드 추가·`python3 ./` → `python D:/...` 절대 경로 전환, Bash allowlist에 `git log/status/rev-list`·`codex exec` 등 9개 항목 신규 허용, `.gitignore`에 `/candidates/`·`/data/evolution/` Stage-1 런타임 산출물 제외 규칙 추가, skills/registry.yaml 스킬 평가 결과 반영 |
| 2026-04-28 | v1.2.22 | chore(settings): hook 명령어 절대경로·name 필드로 업그레이드 — settings.local.json hook 5종에 name 필드 신규 추가 및 python3 상대경로→python 절대경로 변환, Bash allowlist에 git log/status/codex exec 등 8개 패턴 확장, .gitignore에 Stage-1 진화 파이프라인 산출물 경로(/candidates/, /data/evolution/) 추가, skills/registry.yaml + new_skill 평가·프로모션 파일 반영 |
| 2026-04-28 | v1.2.22 | chore(settings): Claude hook 절대경로·이름 적용 및 Stage-1 gitignore 추가 — hook_runner.py 5개 훅 명령을 `$PWD` 상대경로→Windows 절대경로로 고정, 각 훅에 `name` 필드 추가, git log/status/codex exec 등 Bash 허용 항목 확장, `.gitignore`에 Stage-1 진화 런타임 산출물(`/candidates/` `/data/evolution/`) 제외 규칙 신규 추가 |
| 2026-04-28 | v1.2.22 | chore(settings): Claude hook 절대경로 고정 및 allowlist 확장 — hook 명령 `python3 ./` → `python D:/hoonProJect/...` 절대경로 변경 + name 필드 신규 추가, bash allowlist에 git·codex exec 패턴 추가, `.gitignore` Stage-1 진화 파이프라인 산출물(`/candidates/`, `/data/evolution/`) 제외 규칙 추가, `syncCompyne/memory_store.py` 수정, `skills/registry.yaml` 업데이트 |
| 2026-04-28 | v1.2.22 | chore(settings): Windows 절대경로 hook 마이그레이션 및 Stage-1 gitignore 추가 — hook 명령 `python3`+`$PWD` → `python`+절대경로 전환, `codex exec`·`git log/status/rev-list` Bash 권한 신규 추가, `.gitignore`에 `/candidates/`·`/data/evolution/` Stage-1 런타임 경로 추가, `skills/registry.yaml` 및 스킬 평가 리포트 갱신 |
| 2026-04-30 | (unreleased) | fix(T4-watcher-race): ensure_watcher TOCTOU 제거 — `core/design_review_utils.py`: `SPAWN_LOCK_FILE`/`SPAWN_LOCK_TTL`(10s) 상수 추가, `_try_acquire_spawn_lock()` O_CREAT|O_EXCL 원자적 lock 취득+stale 자동 제거, `_release_spawn_lock()` finally 보장, `ensure_watcher()` 1차 alive→spawn lock→2차 alive(double-check)→start 패턴으로 변경. PostToolUse 병렬 호출 시 watcher 중복 spawn 방지. §0 `design_review_utils` 행 신규 public API 반영. 3-Tier 검증: Tier1 PASS / Tier2 WARN(advisory) / Tier3 PASS. |
| 2026-04-29 | (unreleased) | feat(hook-infra+P1-design): design 큐 훅 인프라 + Multi-Provider 설계문서 — `scripts/check_design_pending.py` 신규(design 큐 폴링, JSON timestamp debounce 90s, fired pruning, `_coerce_float` OverflowError/nan/inf 방어, exit 0 contract). `core/design_review_utils.py`: INCLUDE에 날짜패턴(`docs/**/20??-??-??-*.md` + flat), EXCLUDE에 `docs/work-items/**`+`docs/patterns/**` 추가. `.claude/settings.local.json`: PostToolUse 복원(post_edit_code_review+design_review), UserPromptSubmit에 check_pending_review+check_design_pending 추가. `CLAUDE.md`: af-design-review-pending 룰 추가. `docs/2026-04-29-multi-provider-cross-review.md` 신규(P1 설계문서, 350줄, 13섹션). §0 core/ 테이블에 `design_review_utils` 행 추가. 3-Tier 검증 통과(af-test-runner PASS / af-critic WARN→PASS / af-cross-review PASS). |
| 2026-04-29 | (unreleased) | feat(T2-per-skill-escalation): fsa_loop per-skill 에스컬레이션 가드 — `_apply_evolution_guard(level, result, analysis) -> tuple[int, str|None]` 신규: 탐지 실패(_cand_name=None) → logger.warning + Level 5 강제(무한 루프 방지), 차단 스킬 일치 → Level 5, 그 외 → level 유지+cand_dir 반환(이중 탐색 방지). `_try_evolve_failed_skill`에 `skill_dir=None` 선택 파라미터 추가. 반환 타입 `tuple[int, str|None]` 구체화. `test_phase7_dep_graph_evolve.py` 3개 신규 테스트(_apply_evolution_guard 직접 호출, 탐지 실패 케이스 포함). 26 테스트 통과. af-critic WARN 3건(이중 호출·None 가드·테스트 복사) + af-cross-review ACCEPT 2건(탐지 실패 Level 5 복원·경고 로그) 반영. |
| 2026-04-29 | (unreleased) | feat(T1-skill-md-fallback): knowledge skill SKILL.md description fallback — `core/skill_metadata_adapter.py`: `_fill_missing_description()` 신규(description/when_to_use 비어있을 때 SKILL.md frontmatter 우선 → body 텍스트 fallback, `dataclasses.replace` 불변 패턴, logger.debug 예외 가시성), `auto_detect_and_convert()`에서 skill.yaml/meta.yaml 성공 후 호출, `import dataclasses/logging` 추가. Blueprint §0 `skill_metadata_adapter` 행 신규 추가. `tests/test_skill_metadata_adapter.py` 신규 5건(fallback 채움, 기존 값 보존, frontmatter 우선순위, SKILL.md 없음). 3-Tier 검증 통과(af-test-runner PASS / af-critic WARN→ACCEPT 2건 / af-cross-review ACCEPT 2건). |
| 2026-04-29 | (unreleased) | fix(sprint3-warn-clear): Sprint 3 WARN 클리어 — 9-라운드 3-Tier 검증 통과. (1) fsa_loop.py: `_evolution_failed_skills: set[str]` 신규 + `run_mission()` 초기화, Level 4→5 강제 에스컬레이션(set 비어있지 않을 때), `_try_evolve_failed_skill` REJECTED/DEFERRED/ERROR 모두 `None` 반환+set 차단, Level 4 분기 dead `elif/else` 제거(if None→apply_pivot, else→redesign). (2) skill_quality_gate.py: knowledge skill early-return에 `auto_register=True` 시 `_register_knowledge_skill()` 호출 추가 + warning 로그 정비, `_register_knowledge_skill()` silent fail→logger.warning 교체. (3) skill_creator.py: `update_skill()` `meta.setdefault("type", skill_type)` 추가 — knowledge→action 타입 오염 방지. (4) skill_evolution_safety.py: DEPRECATED 주석 정비. (5) tests/test_phase7_dep_graph_evolve.py: `test_rollback_skill` 제거(Sprint 3에서 삭제된 메서드), `_setup_fsa_module` fixture originals dict save/restore 패턴으로 오염 방지, 신규 테스트 4건(PUBLISHED→GateResult(passed=True), REJECTED/DEFERRED/ERROR→None+retry 차단). 81 테스트 통과(--ignore=tests/test_gemini_smoke.py). |
| 2026-04-29 | (unreleased) | feat(stage1-sprint3): Stage-1 Sprint 3 — 호출 사이트 3개 교체(fsa_loop._try_evolve_failed_skill, cross_verification._trigger_evolution, dynamic_orchestrator._try_evolve_from_patterns → SelfEvolutionController.submit() 단일 호출), _verify_evolved_skill/_rollback_skill/_cleanup_skill_baks 3메서드 제거, CANDIDATES_DIR 절대경로 도입(config_paths.py+_create_candidate), knowledge skill 지원(_is_knowledge_skill staticmethod + SkillQualityGate.validate() SKILL.md early-return), skill_creator.py meta.yaml.bak 생성 블록 제거 + knowledge skill _write_meta 호출 복원, fsa_loop GateResult 필수 필드(recommended_stage/eval_report_path) 추가, .gitignore candidates//data/evolution/ 추가. 70 테스트 통과(af-test-runner PASS / af-critic BLOCK→수정→PASS / af-cross-review BLOCK→수정→PASS). |
| 2026-04-28 | (unreleased) | feat(stage1-sprint2): Stage-1 Sprint 2 — core/skill_evolution_controller.py 신규(SelfEvolutionController 7단계 파이프라인: budget guard → candidate staging → evolve_skill → record_budget → sandbox verify → quality gate → publish), core/evolution_ledger.py 신규(EvolutionLedger append-only JSONL, threading.Lock, stats/list_for_skill/list_for_run), _publish() live-snapshot rollback(신규 파일 잔류 방지 + snap 복원 실패 시 snap 정리) + .bak 배포 방지 필터, _emit_rolled_back_event() REJECTED/DEFERRED/ERROR 시 EVOLUTION_ROLLED_BACK RunEvent 직접 기록(BLOCK fix), get_default_store() double-checked locking thread-safe 싱글톤, af.spec hiddenimport 추가, tests/conftest.py AF_CHECKPOINT_DIR + singleton reset fixture, 60 테스트 통과(af-test-runner PASS / af-critic WARN→ACCEPT / af-cross-review ACCEPT). |
| 2026-04-28 | (unreleased) | feat(stage1-sprint1): Stage-1 Sprint 1 — core/evolution_types.py 신규(EvolutionDecision 4종 + EvolutionResult dataclass), RunEventType 4분화(METADATA_ENRICHED/EVOLUTION_REQUESTED/EVOLUTION_PUBLISHED/EVOLUTION_ROLLED_BACK), SkillSelfEvolutionHook run_id= 주입 + update_run_id(thread-safe) + _METADATA_TRIGGERS/_CODE_EVOLUTION_TRIGGERS frozenset whitelist + _record_evolution_to_memory decision 라우팅, HookEventBus.run_skill_evolved/SkillEvolutionBus.on_skill_evolved/SkillEvolutionBus._step7_broadcast decision 파라미터 체인 연결, memory_consolidation register_active_hook/request_consolidation_hint + threading.Lock, agent_runner SkillSelfEvolutionHook(run_id=run_id) + update_run_id 재진입 갱신 + register_active_hook. 3-Tier 검증 통과(af-test-runner PASS / af-critic WARN→PASS / af-cross-review PASS). af.spec core.evolution_types 등록 + Sprint 2/3 placeholder 주석. |
| 2026-04-28 | (unreleased) | fix(C7): Stage-0 Hotfix C7 — skill_evolution_safety 공용 모듈 신규 + 3곳 sandbox 검증 통합. (1) core/skill_evolution_safety.py 신규: verify_evolved_skill_sandbox(quick_guard+run_isolated), rollback_evolved_skill(shutil.move 원자 복원), logger.info 통과 로그, bak 없음 warning. (2) core/fsa_loop.py: _verify_evolved_skill/_rollback_skill을 공용 모듈 위임 래퍼로 교체(인라인 제거). (3) core/cross_verification.py: _trigger_evolution에 sandbox 검증 + rollback 추가. (4) core/dynamic_orchestrator.py: _try_evolve_from_patterns에 H7' sandbox 검증 + rollback 추가. (5) af.spec: core.skill_evolution_safety hiddenimport 추가. (6) tests/test_skill_evolution_safety.py 신규 7건. §0에 skill_evolution_safety 행 추가. |
| 2026-04-28 | (unreleased) | design(stage1-evolution): `docs/2026-04-28-self-evolution-stage1-design.md` v3 작성 — SelfEvolutionController(단일 진입점·candidate staging·sandbox 검증·rollback), CandidateStagingArea(live 파일 직접 수정 금지), EvolutionLedger(영속 이력), core/evolution_types.py 분리(Sprint 1 경량 배치), trigger whitelist(_METADATA_TRIGGERS/_CODE_EVOLUTION_TRIGGERS frozenset), RunBudget record()/is_exhausted() 통합, RunEventType 4분기(METADATA_ENRICHED/EVOLUTION_REQUESTED/PUBLISHED/ROLLED_BACK), hook run_id= 주입. 3-라운드 교차검증(af-critic + af-cross-review/Codex) 통과. |
| 2026-04-28 | (unreleased) | fix(C5): Stage-0 Hotfix C5 — meta.yaml.bak 생성 (skill_creator + skill_enricher). (1) core/skill_creator.py: skill.py.bak/SKILL.md.bak/meta.yaml.bak not-exists 체크 + meta.yaml.bak try-except OSError (stale .bak 보존·백업 실패 시 write 계속). (2) core/skill_enricher.py: import shutil 추가, skill.py 존재 여부(action type proxy) + not exists 체크 + try-except OSError + knowledge 타입 .bak 생성 방지. |
| 2026-04-28 | (unreleased) | fix(C4): Stage-0 Hotfix C4 — fsa_loop gate 3분기 rollback + cleanup + logger. (1) core/fsa_loop.py: FAIL→_rollback_skill, PASS→외부 try/finally+_cleanup_skill_baks(항상 실행), None→_rollback_skill 3분기 명시. (2) _rollback_skill: 5파일("skill.py","SKILL.md","skill.md","meta.yaml","meta.json") 확장, shutil.copy2+os.remove→shutil.move(atomic rename). (3) _cleanup_skill_baks: gate PASS 후 stale .bak 정리 신규 메서드. (4) dead read(new_version line 616) 제거. (5) import logging + logger 추가. |
| 2026-04-28 | (unreleased) | fix(C3): Stage-0 Hotfix C3 — SkillSelfEvolutionHook lazy singleton + thread-safe 카운터. (1) core/agent_runner.py: self._sse_hook = None 초기화 + getattr fallback 단일화. (2) core/hooks/skill_self_evolution.py: _audit_lock으로 카운터 증가+조건+reset 원자화(parallel to_thread race 봉쇄), % check_interval==0 → >=check_interval+reset(스킵 없는 발화 보장), get_stats 일관 스냅샷. |
| 2026-04-28 | (unreleased) | fix(C2): Stage-0 Hotfix C2 — on_bulk_enriched broadcast (_step7) 추가. (1) core/skill_evolution_bus.py: on_bulk_enriched에서 step1~6 완료 후 skill_ids별 _step7_broadcast(trigger="metadata_enriched") 호출, docstring trigger 허용값에 "metadata_enriched" 추가. (2) tests/test_phase_a_step3_evolution.py: _step7_broadcast mock + call_count/arg 검증 추가. |
| 2026-04-28 | (unreleased) | fix(C1): Stage-0 Hotfix C1 — SkillEvolutionBus 싱글톤 + skill_id kwarg + logger. (1) core/dynamic_orchestrator.py: SkillEvolutionBus() 새 인스턴스 → get_instance() 싱글톤(runner/loader 바인딩 보존), skill_name= → skill_id= (TypeError silent fail 봉쇄), except Exception: pass → logger.error(silent fail 제거), name = "(unknown)" fallback 초기화(NameError 방지). |
| 2026-04-28 | (unreleased) | fix(C6): Stage-0 Hotfix C6 — RunEvent SKILL_EVOLVED 타입 추가·진화 이벤트 기록 경로 수정. (1) core/events/run_event.py: `SKILL_EVOLVED` enum 추가, `logging`+`_SIZE_WARN_THRESHOLD`+`_size_warned_paths` 추가, FileRunEventStore.append `except:pass`→`logger.error`+파일 크기 경고. (2) core/hooks/skill_self_evolution.py: `_record_evolution_to_memory` asyncio+threading+UnifiedMemoryFacade(항상 silently fail) → 동기 RunEventStore.append로 교체; run_id fallback sentinel `"_skill_evolution"` + docstring 명시. (3) tests/test_phase_a_step3_evolution.py: `test_record_evolution_emits_run_event`(SKILL_EVOLVED 방출 검증) + `test_on_skill_evolved_logs` store patch으로 격리 개선. (4) .gitignore: `/runs/` 루트 패턴 추가. §0 서브디렉토리 테이블에 `core/events/` 행 추가. |
| 2026-04-25 | v1.2.22 | fix(integration-2): af-critic + Codex 5.5 후속 검증 5건 수정 — (a) approval_gate.apply_verification_verdict 멱등화: 이미 BLOCK 상태이고 마커 존재 시 early return → _sweep_verify_handoffs 매 tick 호출에 따른 review_notes 무한 누적 차단, (b) fsa_loop _record_episode root_cause 우선순위 변경: result.reason은 max_cycles 종료 시 고정 문자열이므로 last_analysis가 채운 root_cause를 우선해야 의미 보존, (c) lineage_ledger lifetime_attempts(=50) 필드 신규: attempts(연속 streak, success 시 0)와 분리하여 fail-success-fail 패턴이 라이프타임 캡 우회 못하게 함. 레거시 데이터(lifetime_attempts 미존재)는 attempts에서 복사. tests/test_lineage_ledger.py 회귀 테스트 2건 추가, (d) work_item_generator EpisodeMatcher 호출을 asyncio.run → _run_async_safe로 변경: orchestrator의 running loop 안에서도 별도 스레드로 안전 실행 → facade 주입 효과 확보, (e) dynamic_orchestrator._execute_agent_task finally의 record_episode를 ensure_future → await으로 변경: nightly_tick의 loop.close() 시점에 pending task가 폐기되어 episode 유실되던 회귀 차단 |
| 2026-04-25 | v1.2.22 | fix(integration): 통합 결함 4건 + Codex 추가 발견 1건 일괄 수정 — (1) DynamicOrchestrator._execute_agent_task finally의 EpisodeRecord에 failure_pattern/root_cause 채우기(state_board.failed_subtasks의 failure_category/reason을 _state_lock 안에서 캡처), (2) FSALoop._record_episode 동일 채움 + last_analysis 보존하여 max_cycles/KeyboardInterrupt 종료 시 final_result에 root_cause/패턴 노출, (3) work_item_generator._build_episode_hints_section에 EpisodeMatcher(facade=UnifiedMemoryFacade.get_instance()) 주입 — 이전엔 facade=None으로 seed-only mode였음(P0 FATAL), (4) lineage_ledger _MAX_LEVEL=5 상수화 + is_maxed의 dead-code(`level>5`)를 `>=_MAX_LEVEL`로 수정 + on_task_success가 level/attempts를 1/0으로 리셋(history는 보존)하여 분해 성공 후 다음 lineage 진입에서 즉시 maxed 차단되는 회귀 방지, (5) nightly_tick에 _sweep_verify_handoffs() 추가하여 docs/work-items/*/verification-report.md를 매 made_progress tick마다 검증(verdict=BLOCK 자동 approval-gate 차단). tests/test_lineage_ledger.py 7건 신규(P3 회귀 테스트 포함) |
| 2026-04-25 | v1.2.22 | feat(3순위): CheckpointHook 등록(agent_runner.py), EpisodeRecord에 event_type/failure_pattern/root_cause 추가(models.py), DynamicOrchestrator._execute_agent_task finally 블록에 record_episode 추가(success+failure 모두) |
| 2026-04-25 | v1.2.22 | feat(C2-summary): nightly_summary.py 모듈별 상태 섹션 추가 — _render_modules_section(load_project_board → module.status 집계), ws 우선순위: param > state.active_workspace, tests/test_nightly_summary.py 4건 신규 |
| 2026-04-25 | v1.2.22 | fix(B2-6): strategy ledger 모듈별 granularity — project_pipeline.py 전역 status 단일 플래그 → _record_ledger_outcomes() 추출(모듈별 3-value 판정), project_task_board.py helpers 4개 추가(_INFRA_NOTE_PREFIXES/_task_is_infra_failure/_build_board_maps/module_outcome_from_board/detect_owner_drift), tests/test_strategy_ledger.py 12건 추가 |
| 2026-04-25 | v1.2.22 | fix(C0-board): write_project_board atomic write — tempfile+os.replace(crash-safe JSON persistence) |
| 2026-04-25 | v1.2.22 | chore(version): 1.2.21 → 1.2.22 bump — version.py + install-af.ps1 |
| 2026-04-24 | v1.2.22 | feat(Phase-A-Step3+4): EVOLUTION+MEMORY 구현 — GateResult.quality_delta, SkillEvolutionBus/SkillQualityGate/SkillSelfEvolutionHook 직접 테스트(29건), MemoryScope.PROJECT, _recall_graph scope 수정, facade semantic_scores 전달(NEW-H2), agent_specializer 에피소드 주입(M8), knowledge_graph.py LOCAL→PROJECT 통일 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 크로스 PC 환경 전환 후 런타임 세션 상태 갱신 — claude/codex/gemini CLI 워크스페이스 경로 `warkSpaces`→`hoonProJect/worktrees` 마이그레이션, 사용자 홈 `HOME`→`HOON` 적용, codex shell guard·auth·models_cache 파일 갱신, document_index 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): PC 이전 후 워크스페이스 경로 및 CLI 세션 상태 동기화 — workspace `warkSpaces→hoonProJect/worktrees` + 사용자명 `HOME→HOON` 경로 수정, claude/codex/gemini CLI 세션 JSON 갱신, codex_home auth·config·state_5.sqlite 업데이트, benchmark_oh_my_opencode.md 삭제 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 새 PC 환경으로 CLI 세션 경로 마이그레이션 — workspace `warkSpaces→hoonProJect/worktrees` 일괄 갱신, claude/codex/gemini 세션 설정 파일 경로 업데이트(HOME→HOON), document_index.json 캐시 갱신, benchmark_oh_my_opencode.md 삭제 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 신규 PC 런타임 경로 마이그레이션 — workspace `D:\warkSpaces` → `D:\hoonProJect\worktrees` 일괄 갱신, 사용자 경로 `HOME` → `HOON` 변경, Codex shell-guard 스크립트 업데이트, document_index 캐시 재생성, benchmark_oh_my_opencode.md 제거 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 크로스 PC 환경 이전으로 런타임 경로 일괄 갱신 — workspace 경로 교체(warkSpaces→hoonProJect/worktrees), 사용자 경로 교체(HOME→HOON), claude/codex/gemini CLI 세션 ID 및 transcript 경로 업데이트, codex 인증·모델캐시·설정 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 크로스 PC 세션 연속성 워크스페이스 이전 — workspace 경로 `warkSpaces`→`hoonProJect/worktrees` 전환, CLI 사용자 `HOME`→`HOON` 갱신, claude/codex/gemini 세션 상태 파일 업데이트, skill-usage.jsonl 실행 기록 추가, benchmark_oh_my_opencode.md 제거 |
| 2026-04-23 | v1.2.21 | chore(runtime): PC 이전 워크스페이스 경로·세션 상태 일괄 갱신 — workspace `D:\warkSpaces→D:\hoonProJect\worktrees` 마이그레이션, 사용자 경로 `HOME→HOON` 변경, claude/codex/gemini CLI 런타임 세션 상태 업데이트, codex 홈 config·auth·모델캐시 갱신, benchmark_oh_my_opencode.md 삭제 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 크로스 PC 세션 연속성 경로 마이그레이션 — workspace `warkSpaces→hoonProJect/worktrees` 전환, 사용자 `HOME→HOON` 경로 업데이트, CLI 세션 상태·Codex 런타임 파일 갱신, settings.local.json 워크스페이스 경로 동기화, document_index 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 마이그레이션 — claude/codex/gemini CLI 세션 workspace `D:\warkSpaces` → `D:\hoonProJect\worktrees` 일괄 수정, 사용자 경로 `HOME` → `HOON` 반영, settings.local.json·document_index.json·NEXT_STEPS.md 신규 경로 동기화 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 — cli_sessions workspace `warkSpaces→hoonProJect/worktrees` 업데이트, 사용자 홈 경로 `HOME→HOON` 변경, CLAUDE.md 세션 연속성 규칙 추가, NEXT_STEPS.md 상태 갱신, skill-usage.jsonl 신규 항목 추가 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 이전 및 CLI 세션 상태 초기화 — workspace 경로 `warkSpaces→hoonProJect/worktrees` 수정, claude/codex/gemini CLI 세션 파일 업데이트, CLAUDE.md 세션 연속성 규칙 추가, document_index 캐시 갱신, skill-usage.jsonl 사용 로그 업데이트 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 및 사용자 계정 마이그레이션 — cli_sessions workspace `D:\warkSpaces` → `D:\hoonProJect\worktrees` 경로 갱신, 사용자 `HOME` → `HOON` 계정 전환, codex_home 인증·설정·모델캐시 신규 PC 동기화, document_index 캐시 재생성, NEXT_STEPS.md 작업 상태 업데이트 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 런타임 세션 갱신 — 경로 `warkSpaces→hoonProJect/worktrees` 변경, 사용자 `HOME→HOON` 갱신, claude/codex/gemini CLI 세션 파일 업데이트, NEXT_STEPS.md·CLAUDE.md 상태 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 런타임 세션 갱신 — 경로 `warkSpaces→hoonProJect/worktrees` 변경, 사용자 `HOME→HOON` 갱신, claude/codex/gemini CLI 세션 파일 업데이트, NEXT_STEPS.md·CLAUDE.md 상태 동기화 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 이전 및 런타임 세션 상태 갱신 — warkSpaces→hoonProJect/worktrees 경로 전환, claude·codex·gemini CLI 세션 파일 업데이트, CLAUDE.md 세션 연속성 규칙 추가, skill-usage.jsonl 이력 갱신 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 이전 동기화 — cli_sessions workspace/user 경로 `warkSpaces/HOME` → `hoonProJect/worktrees/HOON` 업데이트, codex·gemini CLI 세션 설정 갱신, CLAUDE.md·NEXT_STEPS.md 상태 반영, skill-usage.jsonl 사용 이력 동기화 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 PC 마이그레이션 — CLI 세션 workspace `warkSpaces→hoonProJect/worktrees` 갱신, 사용자 경로 `HOME→HOON` 변경, 세션 ID·transcript 경로 업데이트, Codex/Gemini CLI 세션 설정 동기화, NEXT_STEPS.md·skill-usage.jsonl 상태 반영 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 — cli_sessions workspace `warkSpaces→hoonProJect/worktrees` 경로 수정, 사용자 홈 경로 `HOME→HOON` 업데이트, codex_home 상태·인증 파일 갱신, document_index 캐시 재생성, skill-usage 데이터 추가 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 — `D:\warkSpaces\agent-factory` → `D:\hoonProJect\worktrees\agent-factory` 경로 전환, claude/codex/gemini CLI 세션 상태 갱신(session_id·transcript_path 업데이트), CLAUDE.md·NEXT_STEPS.md 세션 연속성 규칙 반영, skill-usage.jsonl 신규 사용 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 — cli_sessions workspace `D:\warkSpaces` → `D:\hoonProJect\worktrees` 갱신, 사용자 디렉토리 `HOME` → `HOON` 변경, 세션 ID·transcript_path 업데이트, codex_home 런타임 상태(auth/config/sqlite) 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 — `warkSpaces`→`hoonProJect/worktrees` 경로 갱신, 사용자명 `HOME`→`HOON` 변경, CLI 세션 설정(claude/codex/gemini) 전체 재동기화, `.system_generated/cache` 문서 인덱스 갱신, `NEXT_STEPS.md` 작업 상태 업데이트 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 — `warkSpaces`→`hoonProJect/worktrees` 경로 갱신, 사용자명 `HOME`→`HOON` 변경, CLI 세션 설정(claude/codex/gemini) 전체 재동기화, `.system_generated/cache` 문서 인덱스 갱신 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 — `warkSpaces`→`hoonProJect/worktrees` 경로 일괄 수정, `HOME`→`HOON` 사용자 디렉터리 변경, CLI 세션 상태(claude/codex/gemini) 갱신, `settings.local.json` 경로 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로를 새 PC 환경으로 마이그레이션 — claude_cli/codex_cli/gemini_cli 세션 JSON의 workspace·user 경로 `HOME→HOON` 일괄 교체, `.claude/settings.local.json` 경로 동기화, `document_index.json` 캐시 갱신, `CLAUDE.md` 세션 연속성 규칙 보강 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 — `D:\warkSpaces\agent-factory` → `D:\hoonProJect\worktrees\agent-factory` 전환, 사용자 `HOME` → `HOON` 반영, claude/codex/gemini CLI 세션 상태 갱신, CLAUDE.md·NEXT_STEPS.md 업데이트 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 — `D:\warkSpaces` → `D:\hoonProJect\worktrees` 경로 전환, 사용자 `HOME` → `HOON` 반영, claude/codex/gemini CLI 세션 상태 갱신, `CLAUDE.md`·`NEXT_STEPS.md` 업데이트 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 갱신 — claude_cli/codex_cli/gemini_cli 세션 workspace `warkSpaces→hoonProJect/worktrees` 경로 교체, 사용자 경로 `HOME→HOON` 업데이트, codex_home 인증·캐시·SQLite 상태 파일 동기화, settings.local.json 및 document_index.json 재생성 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 hoonProJect/worktrees로 마이그레이션 — claude/codex/gemini CLI 세션 workspace 경로 일괄 수정, 사용자 경로 HOME→HOON 업데이트, settings.local.json 경로 동기화, CLAUDE.md 세션 연속성 규칙 추가, NEXT_STEPS.md 작업 상태 갱신 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로를 hoonProJect/worktrees로 마이그레이션 — claude/codex/gemini CLI 세션 workspace 경로 일괄 수정, 사용자 HOME→HOON 경로 업데이트, settings.local.json 경로 동기화, CLAUDE.md 세션 연속성 규칙 추가, NEXT_STEPS.md 작업 상태 갱신 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 및 CLI 세션 환경 마이그레이션 — workspace `warkSpaces` → `hoonProJect/worktrees` 경로 갱신, CLI 사용자 `HOME` → `HOON` 업데이트, 세션 ID·transcript 경로 초기화(신규 세션 `5433faef`), document_index 캐시 갱신, CLAUDE.md·NEXT_STEPS.md 반영 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 갱신 — workspace `warkSpaces`→`hoonProJect/worktrees` 경로 수정, 사용자 홈 `HOME`→`HOON` 업데이트, claude/codex/gemini CLI 세션 state 파일 갱신, skill-usage.jsonl 데이터 추가, document_index.json 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 이전 및 런타임 세션 상태 갱신 — claude_cli_run.json workspace `D:\warkSpaces`→`D:\hoonProJect\worktrees` 이전, 불필요 필드(mode/command/task_preview) 제거, codex_home 세션·캐시 업데이트, NEXT_STEPS.md 및 skill-usage.jsonl 갱신 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 세션 상태 갱신 — `warkSpaces` → `hoonProJect/worktrees` 경로 전환, `HOME` → `HOON` 사용자 경로 수정, CLI 세션 파일(claude/codex/gemini) 최신 세션 ID·transcript 경로 업데이트, CLAUDE.md·NEXT_STEPS.md·skill-usage.jsonl 동기화 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 갱신 — `warkSpaces` → `hoonProJect/worktrees` 경로 변경, claude/codex/gemini CLI 세션 JSON 갱신, codex_home 런타임 파일(auth.json·config.toml·models_cache.json) 업데이트, skill-usage.jsonl 사용 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 갱신 — warkSpaces→hoonProJect/worktrees 경로 이전, claude/codex/gemini 세션 파일 업데이트, codex_home 런타임 파일(auth·cache·sqlite) 동기화, CLAUDE.md 세션 연속성 규칙 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 동기화 — workspace `warkSpaces`→`hoonProJect/worktrees` 경로 수정, 사용자 `HOME`→`HOON` 프로필 경로 정정, claude/codex/gemini CLI 세션 상태 갱신, document_index 캐시 재생성, skill-usage.jsonl 사용 로그 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 동기화 — workspace `warkSpaces`→`hoonProJect/worktrees` 경로 수정, 사용자 `HOME`→`HOON` 프로필 경로 정정, claude/codex/gemini CLI 세션 상태 갱신, document_index 캐시 재생성, skill-usage.jsonl 사용 로그 추가 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 마이그레이션 및 세션 상태 갱신 — `warkSpaces→hoonProJect/worktrees` 경로 교체, 사용자 디렉토리 `HOME→HOON` 수정, CLI 세션 ID·트랜스크립트 경로 업데이트, document_index.json·skill-usage.jsonl 동기화, CLAUDE.md·NEXT_STEPS.md 상태 반영 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 (warkSpaces → hoonProJect/worktrees) — CLI 세션 workspace·command 경로 일괄 갱신(HOME→HOON), codex 런타임 상태·auth 파일 동기화, skill-usage.jsonl 업데이트, document_index.json 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 (warkSpaces→hoonProJect/worktrees) — claude_cli/codex_cli/gemini_cli 세션 파일 경로 갱신, HOME→HOON 사용자 환경 전환, codex_home auth·config·sqlite 상태 갱신, skill-usage.jsonl 세션 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 세션 상태 갱신 — `.af_runtime` 세션 JSON workspace `warkSpaces→hoonProJect/worktrees` 경로 수정, shell-guard cmd 파일 경로 갱신, `document_index.json` 캐시 재생성, `skill-usage.jsonl` 스킬 사용 이력 추가, `CLAUDE.md`·`NEXT_STEPS.md` 세션 연속성 규칙 업데이트 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 런타임 세션 갱신 — workspace `warkSpaces`→`hoonProJect/worktrees/agent-factory` 수정, 사용자 경로 `HOME`→`HOON` 변경, CLI 세션 상태·transcript 경로 동기화, document_index.json 캐시 재생성, skill-usage.jsonl 스킬 사용 이력 갱신 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 HOON PC로 마이그레이션 — claude_cli_run.json에서 mode·command·task_preview·prepared_at 필드 제거, workspace 경로 `warkSpaces→hoonProJect/worktrees` 갱신, codex shell guard(cmd/git/powershell/pwsh) 업데이트, 세션 ID·transcript_path 신규 환경으로 교체 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 런타임 상태 동기화 — `D:\\warkSpaces` → `D:\\hoonProJect\\worktrees` 경로 이전, claude/codex/gemini 세션 상태 파일 갱신, codex shell guard 스크립트(cmd/git/powershell/pwsh) 업데이트, CLAUDE.md·NEXT_STEPS.md 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 PC 이전 반영 — `D:\warkSpaces` → `D:\hoonProJect\worktrees` 경로 전환, 사용자 홈 `HOME` → `HOON` 갱신, CLI 세션 상태 파일 동기화, CLAUDE.md 세션 연속성 규칙 추가 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): PC 워크스페이스 경로 마이그레이션 및 런타임 상태 갱신 — `warkSpaces\agent-factory`→`hoonProJect\worktrees\agent-factory` 경로 변경, 사용자 경로 `HOME`→`HOON` 변경, claude_cli·codex_cli·gemini_cli 세션 상태 파일 갱신, CLAUDE.md·NEXT_STEPS.md 업데이트, skill-usage.jsonl·document_index.json 동기화 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 갱신 — claude/codex/gemini 세션 workspace `warkSpaces→hoonProJect/worktrees` 업데이트, 사용자 경로 `HOME→HOON` 변경, codex_home 인증·세션 상태 파일 갱신, document_index 캐시 재생성, skill-usage.jsonl 사용 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 갱신 — `warkSpaces/HOME` → `hoonProJect/worktrees/HOON` 경로 전환, claude_cli_run.json에서 mode·command·task_preview·settings_path 필드 제거, session_id/transcript_path 신규 세션으로 교체, codex_home·gemini_cli·document_index 런타임 캐시 전체 갱신 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 — `D:\warkSpaces` → `D:\hoonProJect\worktrees` 경로 전환, 사용자 HOME→HOON 변경, claude/codex/gemini CLI 세션 상태 갱신, document_index 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 반영 — `warkSpaces` → `hoonProJect\worktrees` 경로 전환, Claude/Codex/Gemini CLI 세션 상태 파일 갱신, `settings.local.json` 사용자 경로 수정(`HOME`→`HOON`), `document_index.json` 캐시 재생성, `skill-usage.jsonl` 사용 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 동기화 — claude_cli/codex_cli/gemini_cli 경로 `warkSpaces→hoonProJect/worktrees` 전환, 사용자 `HOME→HOON` 경로 수정, session_id·transcript_path 갱신, prepared_at/updated_at 타임스탬프 업데이트, skill-usage.jsonl 신규 사용 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 마이그레이션 및 런타임 세션 상태 갱신 — `HOME`→`HOON` 사용자 경로 변경, `warkSpaces`→`hoonProJect/worktrees` 워크스페이스 재배치, claude/codex/gemini CLI 세션 설정 업데이트, shell guard 스크립트 경로 수정, codex 런타임 상태 파일 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 갱신 — `warkSpaces` → `hoonProJect/worktrees` 경로 전환, claude/codex/gemini 세션 파일 초기화, skill-usage.jsonl 스킬 사용 이력 추가, document_index.json 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): PC 이전 워크스페이스 경로 갱신 — workspace `warkSpaces`→`hoonProJect/worktrees` 전체 치환, 사용자 경로 `HOME`→`HOON` 수정, CLI 세션 상태·Codex 홈 런타임 파일 업데이트, document_index 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): PC 환경 워크스페이스 경로 마이그레이션 — `HOME→HOON` 사용자 경로 변경, `warkSpaces→hoonProJect/worktrees` 경로 수정, CLI 세션 상태 갱신(claude/codex/gemini), `NEXT_STEPS.md`·`CLAUDE.md` 세션 연속성 업데이트, `skill-usage.jsonl` 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 이전 및 CLI 세션 상태 갱신 — `warkSpaces→hoonProJect/worktrees` 경로 교체, `HOME→HOON` 사용자 경로 변경, claude/codex/gemini 세션 파일 동기화, CLAUDE.md·NEXT_STEPS.md 업데이트, document_index 캐시 갱신 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 후 런타임 상태 일괄 갱신 — claude/codex/gemini CLI 세션 workspace 경로 `warkSpaces→hoonProJect/worktrees` 수정, codex_home auth·config·models_cache·sqlite 세션 상태 갱신, document_index 캐시 재생성, CLAUDE.md 세션 연속성 규칙 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 이전 및 런타임 상태 갱신 — claude_cli_run.json workspace 경로 교정(warkSpaces→hoonProJect/worktrees) 및 불필요 CLI 커맨드 필드 제거, codex 런타임 파일(auth.json·models_cache.json·state_5.sqlite) 갱신, CLAUDE.md 세션 연속성 규칙 반영, skill-usage.jsonl 스킬 사용 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 마이그레이션 — workspace `D:\warkSpaces\agent-factory`→`D:\hoonProJect\worktrees\agent-factory`, 사용자 디렉터리 `HOME`→`HOON`, CLI 세션 런타임 상태(claude/codex/gemini) 갱신, `CLAUDE.md`·`NEXT_STEPS.md` 세션 연속성 규칙 업데이트 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 — `D:\warkSpaces` → `D:\hoonProJect\worktrees` 경로 일괄 갱신, 사용자 `HOME` → `HOON` 변경, CLI 세션 상태·설정 파일 업데이트, document_index 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 이전 및 CLI 세션 상태 갱신 — claude_cli 세션 workspace `D:\warkSpaces` → `D:\hoonProJect\worktrees` 경로 교체, codex_cli·gemini_cli 세션 JSON 동기화, codex_home auth·config·models_cache 최신화, document_index.json 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 런타임 상태 동기화 — claude_cli_run.json workspace 경로 hoonProJect/worktrees로 전환·불필요 필드(mode/command/task_preview) 제거, codex/gemini CLI 세션 파일 갱신, CLAUDE.md 세션 연속성 규칙 추가, document_index.json 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 — `warkSpaces` → `hoonProJect/worktrees` 경로 변경, 사용자 `HOME` → `HOON` 갱신, claude/codex/gemini CLI 세션 상태 업데이트, document_index 캐시 재생성, skill-usage.jsonl 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스·사용자 경로 마이그레이션 및 런타임 상태 갱신 — cli_sessions workspace 경로 재설정(warkSpaces→hoonProJect/worktrees), 사용자 프로파일 경로 재설정(HOME→HOON), codex_home 런타임 상태(auth/cap_sid/state_5.sqlite) 갱신, code-review.md 업데이트, document_index 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 이전 및 런타임 상태 갱신 — claude/codex/gemini 세션 경로 `warkSpaces→hoonProJect/worktrees` 수정, 사용자 경로 `HOME→HOON` 업데이트, codex_home 런타임 파일(auth.json·config.toml·state_5.sqlite) 갱신, skill-usage·document_index 캐시 동기화 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 이전 및 CLI 세션 상태 갱신 — claude/codex/gemini 세션 경로 `warkSpaces→hoonProJect/worktrees` 수정, 사용자 경로 `HOME→HOON` 업데이트, codex_home 런타임 파일(auth.json·config.toml·state_5.sqlite) 갱신, skill-usage·document_index 캐시 동기화 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 — HOME→HOON 사용자 경로 전환, claude/codex/gemini CLI 세션 설정 업데이트, settings.local.json 경로 재설정, bridge_state session_cursor 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 후 런타임 상태 동기화 — workspace `D:\warkSpaces\agent-factory` → `D:\hoonProJect\worktrees\agent-factory` 경로 변경, 사용자 경로 `HOME` → `HOON` 업데이트, claude/codex/gemini CLI 세션 파일 갱신, `.system_generated/cache/document_index.json` 캐시 재생성, `session_cursor.json` 브리지 커서 업데이트 |
| 2026-04-23 | v1.2.21 | {"changelog": "chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 갱신 — D:\\\\warkSpaces→D:\\\\hoonProJect\\\\worktrees 경로 일괄 변경, claude/codex/gemini CLI 세션 메타데이터 재생성, codex_home auth/state/sandbox 로그 갱신, settings.local.json 및 document_index 캐시 동기화"} |
| 2026-04-23 | v1.2.21 | {"changelog": "chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 런타임 상태 동기화 — claude/codex/gemini 세션 메타데이터를 D:\\\\hoonProJect\\\\worktrees\\\\agent-factory 경로로 갱신, 사용자 홈 경로 HOME→HOON 정정, codex_home auth·config·sandbox·state 재생성, .claude/settings.local.json 및 docs/code_review/code-review.md 최신화"} |
| 2026-04-23 | v1.2.21 | {"changelog": "chore(runtime): 워크스페이스 경로 HOON 사용자로 전환 — claude_cli/codex_cli/gemini_cli 세션 메타데이터 갱신, codex_home auth/config/state 재초기화, shell_guard 래퍼 스크립트 경로 재생성, code-review/document_index/skill-usage 로그 업데이트"} |
| 2026-04-23 | v1.2.21 | {"type":"chore","scope":"runtime","summary":"chore(runtime): 런타임 상태 파일 경로·세션 정보 갱신 — 워크스페이스 경로 D:\\hoonProJect\\worktrees\\agent-factory 이전, claude/codex/gemini CLI 세션 ID·트랜스크립트 경로 재생성, shell_guard 래퍼 재구성, codex_home auth/config/state 동기화, code-review.md 및 document_index 캐시 업데이트"} |
| 2026-04-23 | v1.2.21 | {"changelog": "chore(runtime): AF 런타임 세션 상태 갱신 — claude_cli/codex_cli/gemini_cli 세션 JSON 워크스페이스 경로 이관(D:\\warkSpaces→D:\\hoonProJect\\worktrees), codex_home auth/state/config 재생성, code-review.md 및 skill-usage.jsonl 이력 반영, .claude/settings.local.json 동기화"} |
| 2026-04-23 | v1.2.21 | {"changelog":"chore(runtime): CLI 세션·런타임 상태 메타데이터 갱신 — claude_cli/codex_cli/gemini_cli 세션 workspace 경로 D:\\\\hoonProJect로 이전, codex_home auth/config/state_5.sqlite 갱신, code-review.md 및 session_cursor.json 동기화, skill-usage.jsonl·document_index.json 인덱스 업데이트"} |
| 2026-04-23 | v1.2.21 | {"changelog":"chore(runtime): 사용자 환경 경로 및 CLI 세션 스냅샷 동기화 — workspace 경로를 D:\\hoonProJect\\worktrees\\agent-factory로 갱신, claude/codex/gemini CLI 세션 상태·shell_guard·codex_home 런타임 재생성, code-review.md 및 skill-usage.jsonl 최신화, session_cursor.json 브리지 커서 업데이트"} |
| 2026-04-23 | v1.2.21 | chore(runtime): CLI 세션 런타임 상태 갱신 — claude_cli workspace 경로 `D--hoonProJect-worktrees-agent-factory`로 이전, codex_home auth·sandbox·sqlite 세션 상태 업데이트, shell_guard 래퍼 스크립트 재생성, code-review.md 최신 리뷰 결과 반영 |
| 2026-04-23 | v1.2.21 | chore(runtime): CLI 세션 런타임 상태 갱신 — 워크스페이스 경로 D:\hoonProJect\worktrees\agent-factory로 재설정, claude/codex/gemini 세션 메타데이터 및 shell guard 스크립트 재생성, codex_home auth/state/sandbox 로그 업데이트, skill-usage 및 document_index 캐시 재구성 |
| 2026-04-23 | v1.2.21 | {"changelog":"chore(runtime): 워크스페이스 경로 마이그레이션 (D:\\warkSpaces → D:\\hoonProJect\\worktrees) — CLI 세션 상태 파일(claude/codex/gemini) workspace·command·settings_path 갱신, session_id·transcript_path·updated_at 재발급, codex_home auth/config/sandbox 런타임 상태 동기화, session_cursor.json 브릿지 상태 재초기화, code-review.md·document_index 캐시 업데이트"} |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 이전 및 CLI 런타임 상태 갱신 — claude/codex/gemini 세션 JSON workspace를 D:\hoonProJect\worktrees\agent-factory로 이전, 사용자 홈 경로 HOME→HOON 교정, codex_home auth.json·state_5.sqlite·cap_sid 등 런타임 파일 재생성, code-review.md 최신화 및 skill-usage.jsonl 이벤트 기록 |
| 2026-04-23 | v1.2.21 | {"changelog":"chore(runtime): CLI 세션/런타임 상태 파일 경로 갱신 — claude_cli 세션 ID·트랜스크립트 경로를 D:\\hoonProJect\\worktrees\\agent-factory 워크스페이스로 갱신, codex_home auth/state/sandbox 로그 업데이트, shell_guard cmd 스크립트 4종 및 gemini_cli 기본 설정 동기화, code-review.md·document_index.json·skill-usage.jsonl 런타임 캐시 반영"} |
| 2026-04-23 | v1.2.21 | {"changelog":"chore(runtime): 워크스페이스 경로 마이그레이션 및 런타임 상태 갱신 — warkSpaces→hoonProJect/worktrees 경로 이전, Claude/Codex/Gemini CLI 세션 상태 재초기화, codex_home auth·state·sandbox 로그 업데이트, shell_guard 스크립트 재생성, code-review.md 및 document_index 캐시 동기화"} |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 및 세션 런타임 상태 갱신 — claude/codex/gemini CLI 세션 워크스페이스를 `D:\hoonProJect\worktrees\agent-factory`로 이전, 사용자 홈 경로 `HOME`→`HOON` 정정, codex_home 런타임 상태(auth/cap_sid/state_5.sqlite/config.toml) 갱신, shell_guard 래퍼 스크립트 4종 재생성, code-review.md 및 document_index 캐시 동기화 |
| 2026-04-23 | v1.2.21 | {"changelog": "chore(runtime): 워크스페이스 경로 및 세션 상태 동기화 — claude/codex/gemini CLI 세션 워크스페이스를 D:\\\\hoonProJect\\\\worktrees\\\\agent-factory로 갱신, 사용자 홈 경로 HOME→HOON 정정, 코드리뷰 세션 ID·트랜스크립트 경로 재바인딩, 런타임 auth·state·sandbox 로그 최신화"} |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 런타임 세션 상태 갱신 — warkSpaces→hoonProJect/worktrees 경로 전환, HOME→HOON 사용자 경로 일괄 교체, CLI 세션 파일(claude/codex/gemini) workspace·settings_path 업데이트, 브리지 세션 커서(session_cursor.json) 갱신, code-review.md 코드리뷰 내용 업데이트 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 CLI 세션 상태 일괄 갱신 — workspace `warkSpaces→hoonProJect/worktrees` 경로 수정, 사용자명 `HOME→HOON` 정정, claude/codex/gemini 세션 JSON 갱신, 세션 커서 및 스킬 사용 로그 업데이트 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 런타임 세션 상태 갱신 — claude/codex/gemini CLI 세션 경로 `warkSpaces`→`hoonProJect/worktrees` 일괄 교정, 사용자 `HOME`→`HOON` 경로 수정, code-review.md LLM 문서 생성 파이프라인 보안 이슈(auth.json 토큰 노출·.gitignore 누락) 리뷰 결과 반영, document_index 캐시 갱신 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 반영 — claude_cli/codex_cli/gemini_cli 세션 JSON 경로 `warkSpaces→hoonProJect/worktrees` 수정, 사용자명 `HOME→HOON` 일괄 교체, session_cursor.json·document_index.json·skill-usage.jsonl 런타임 상태 동기화, code-review.md 최신 리뷰 결과 반영 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션 및 런타임 세션 상태 갱신 — workspace `D:\warkSpaces` → `D:\hoonProJect\worktrees` 경로 수정, CLI 사용자명 `HOME→HOON` 업데이트, 세션 ID·transcript_path 신규 등록, skill-usage.jsonl·document_index.json·session_cursor.json 상태 동기화 |
| 2026-04-23 | v1.2.21 | chore(af-runtime): 워크스페이스 경로 이전 및 런타임 상태 동기화 — `D:\warkSpaces` → `D:\hoonProJect\worktrees` 경로 갱신, `HOME` → `HOON` 사용자 경로 일괄 교체, claude/codex/gemini CLI 세션 상태(session_id·transcript_path) 갱신, codex auth·config·models_cache 런타임 파일 동기화 |
| 2026-04-23 | v1.2.21 | {"changelog":"chore(runtime): 워크스페이스 경로 재구성 및 CLI 런타임 상태 갱신 — claude/codex/gemini 세션 메타데이터 경로를 D:\\hoonProJect\\worktrees\\agent-factory로 이전, 사용자 홈을 HOME→HOON으로 교정, codex_home 인증·sandbox·state 갱신, .claude/settings.local.json 및 skill-usage 로그 동기화"} |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 이전 반영 — CLI 세션 경로 `warkSpaces→hoonProJect/worktrees` 업데이트, 사용자 홈 `HOME→HOON` 수정, 세션 커서·브리지 상태 동기화, settings.local.json 경로 갱신, skill-usage 기록 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 이전 후 런타임 상태 동기화 — claude/codex/gemini CLI 세션 파일 갱신, workspace 경로 `warkSpaces→hoonProJect/worktrees` 반영, bridge_state 세션 커서 업데이트, document_index 캐시 재생성 |
| 2026-04-23 | v1.2.21 | chore(runtime): 워크스페이스 경로 마이그레이션(warkSpaces→hoonProJect/worktrees) — claude_cli_run.json 사용자·경로 업데이트(HOME→HOON), codex_home 런타임 상태(auth.json·config.toml·models_cache.json) 갱신, session_cursor.json 브릿지 포인터 이동, document_index.json 캐시 재생성, skill-usage.jsonl 사용 이력 추가 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 런타임 세션 상태 갱신 — claude_cli 워크스페이스 경로 변경(warkSpaces→hoonProJect/worktrees), 세션 ID·트랜스크립트 경로 교체, codex_home auth/config/캐시 업데이트, code-review.md 보안 이슈 기록 추가 |
| 2026-04-23 | v1.2.21 | chore(runtime): 런타임 환경 경로 마이그레이션 — workspace `HOME→HOON` 및 `warkSpaces→hoonProJect/worktrees` 경로 수정, claude/codex/gemini CLI 세션 상태 갱신, document_index 캐시 재생성, session_cursor 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 런타임 세션 상태 일괄 갱신 — `D:\\warkSpaces` → `D:\\hoonProJect\\worktrees` 경로 교체, 사용자 홈 `HOME` → `HOON` 반영, claude/codex/gemini CLI 세션 상태 파일 갱신, codex_home 인증·모델캐시·상태DB 업데이트, session_cursor 동기화 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 및 세션 상태 갱신 — claude_cli workspace `D:\\warkSpaces` → `D:\\hoonProJect\\worktrees` 경로 변경, session_id·transcript_path 신규 세션으로 교체, codex_home auth/config/state 파일 갱신, document_index.json 캐시 업데이트 |
| 2026-04-23 | v1.2.21 | chore(af_runtime): 워크스페이스 경로 마이그레이션 — `D:\warkSpaces\agent-factory` → `D:\hoonProJect\worktrees\agent-factory` 전환, Claude/Codex/Gemini CLI 세션 설정 경로 일괄 갱신, 사용자 HOME→HOON 경로 동기화, bridge state session_cursor 리셋 |
| 2026-04-23 | v1.2.22 | feat(llm-doc-gen): LLM 기반 work-item 문서 생성 파이프라인 — `core/requirement_llm.py`에 `_DOCUMENT_SYSTEM_PROMPT` + `execute_document_prompt()` 추가(마크다운 전용, execute_requirement_prompt와 CLI/API 경로 대칭). `core/work_item_generator.py` 전면 재구성: ① 기존 4개 f-string 생성 함수를 `_fallback_*`으로 이름 변경(본체 무변경), ② LLM 래퍼 `_generate_feature_plan`/`_generate_feature_spec`/`_generate_implementation_design`/`_generate_implementation_tasks` 신규 (각각 `prev_*` 파라미터로 이전 문서 컨텍스트 수신), ③ `_generate_doc_with_llm()` — LLM 실패 시 fallback 자동 전환, 실패 시 WARNING 로깅, ④ `_generate_and_refine()`에 `_prev_doc=""` kwarg + inspect.signature 기반 dispatch 추가, ⑤ `generate_work_items`에 `doc_gen_deadline=300s` + chained refinement(5a plan→5b spec→5c design→5d tasks) 추가. 3-tier review: Tier1 WARN(선행 버그 2건만), Tier2 WARN(effective_prompt CLI 분리 적용), Tier3 PASS |
| 2026-04-23 | v1.2.22 | feat(graphify): Graphify 외부 도구 wrapper skill 통합 — `skills/graphify/`(action, capabilities: GRAPHIFY_BUILD/GRAPHIFY_QUERY/KNOWLEDGE_GRAPH_INDEX) + `skills/graphify_guide/`(knowledge, retrieval engine 자동 발견용) 신규. Graphify 공식 인스톨러(`graphify install`) 미사용 → CLAUDE.md/.githooks 자동 주입 회피. `subprocess.run(["graphify", ...])`로 외부 CLI 호출(uv tool 격리, Python 3.13). `install-af.sh --with-graphify` / `install-af.ps1 -WithGraphify` 옵션으로 명시적 설치(F1+F2). **Review-gate 범위 확장**: `scripts/enqueue_agent_review.py:26` `_REVIEW_PREFIXES`에 `skills/` 추가, `.githooks/pre-commit:46` 정규식에 `skills/.*\.py` 추가 — 기존엔 `skills/` 변경이 게이트 밖이라 정책 1번이 공허하게 PASS되던 사각지대 해소(F5). `skills/registry.yaml`에 두 엔트리 첫 커밋 동시 추가(F4). 좁은 capability 명명으로 `core_memory.MEMORY_SEARCH` 등과 점수 오염 회피(F3). af-cross-review FIX_FIRST 4건 모두 적용, F6은 Q5(b) action+knowledge skill_id 분리로 해소 |
| 2026-04-22 | v1.2.22 | feat(phase-a-step1): ISE 배선 복구 B1~B7 + Review-Gate BLOCK 3건 해소 — (B1) project_pipeline.execute() ise 모드 AF_ISE_ENABLED 강제 활성화; (B2) _orchestration_loop에서 _should_decompose() 호출 연결; (B3) ise_strategy_ledger.load() 레거시 해시 경고; (B4) 모든 실패 경로(FSA/evaluator/crash)에 failure_category 필드 추가; (B5) skill_procurer auto_approve ise 포함; (B6) CLI --mode ise routing 수정(L665 elif 추가); (B7) Blueprint §3.2 Phase A Step 1 노트. _needs_llm_intervention crash 카테고리 제외. 테스트: 787P/17F(pre-existing)/3S |
| 2026-04-21 | v1.2.22 | fix(B2-4): strategy_ledger에 deliverables 패턴 등록 경로 추가 — `record_role_batch` 신규, project_pipeline.py 모듈명+deliverables(앞 4단어) 배치 저장, `tests/test_strategy_ledger.py` 12개 테스트 신규 |
| 2026-04-21 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/tests/test_strategy_ledger.py — settings.local.json, Master_Blueprint.md, strategy_ledger.py, project_pipeline.py, code-review.md (+18) |
| 2026-04-21 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/tests/test_strategy_ledger.py — settings.local.json, Master_Blueprint.md, strategy_ledger.py, project_pipeline.py, code-review.md (+18) |
| 2026-04-21 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/tests/test_strategy_ledger.py — settings.local.json, Master_Blueprint.md, strategy_ledger.py, project_pipeline.py, code-review.md (+18) |
| 2026-04-21 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py — settings.local.json, Master_Blueprint.md, strategy_ledger.py, project_pipeline.py, code-review.md (+18) |
| 2026-04-21 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/tests/test_strategy_ledger.py — settings.local.json, Master_Blueprint.md, strategy_ledger.py, project_pipeline.py, code-review.md (+18) |
| 2026-04-21 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py — settings.local.json, Master_Blueprint.md, strategy_ledger.py, project_pipeline.py, code-review.md (+18) |
| 2026-04-21 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py — settings.local.json, Master_Blueprint.md, strategy_ledger.py, project_pipeline.py, code-review.md (+18) |
| 2026-04-21 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, strategy_ledger.py, ise_ledger_run_retry_fsa.json, lineage_ledger.json, .todo.md (+15) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/run_factory_cli.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/work_item_generator.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/approval_gate.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_task_board.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+30) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/work_item_generator.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+29) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+28) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+28) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+28) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/approval_gate.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+27) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/approval_gate.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+27) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/approval_gate.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, lineage_ledger.py (+27) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, lineage_ledger.py, episode_matcher.py (+26) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/run_factory_cli.py — settings.local.json, document_index.json, Master_Blueprint.md, lineage_ledger.py, project_pipeline.py (+25) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/run_factory_cli.py — settings.local.json, document_index.json, Master_Blueprint.md, lineage_ledger.py, project_pipeline.py (+25) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/run_factory_cli.py — settings.local.json, document_index.json, Master_Blueprint.md, lineage_ledger.py, project_pipeline.py (+25) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py — settings.local.json, document_index.json, Master_Blueprint.md, lineage_ledger.py, project_pipeline.py (+24) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py — settings.local.json, document_index.json, Master_Blueprint.md, lineage_ledger.py, project_pipeline.py (+24) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, lineage_ledger.py, skill-usage.jsonl (+23) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, lineage_ledger.py, skill-usage.jsonl (+23) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, lineage_ledger.py, skill-usage.jsonl, code-review.md (+22) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+24) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+24) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/review_gate.py — settings.local.json, document_index.json, skill-usage.jsonl, code-review.md, review_gate.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/tests/test_review_gate.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+25) |
| 2026-04-20 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+24) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, hook_runner.py (+23) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/review_gate.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, review_gate.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/review_gate.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, review_gate.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/review_gate.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, review_gate.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/review_gate.py — document_index.json, skill-usage.jsonl, code-review.md, review_gate.py, skill-eval-report.json (+21) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, hook_runner.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, hook_runner.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/test_review_gate.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+21) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/review_gate.py — document_index.json, skill-usage.jsonl, code-review.md, skill-eval-report.json, skill-eval-report.json (+20) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, nightly_tick.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, nightly_tick.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, skill-usage.jsonl, code-review.md, nightly_tick.py, skill-eval-report.json (+21) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, nightly_tick.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, nightly_tick.py (+22) |
| 2026-04-27 | v1.2.22 | feat(T3-7-followup): CLI --budget → set_run_budget run_id 연결 + nightly_tick consumed_tokens 역기록 + approve() run_id 전달 — 3-Tier 검증 통과 |
| 2026-04-20 | v1.2.21 | fix(review-gate-REVISE): cross-review REVISE 2건 해소 — M1: record_review_done files_snapshot 파라미터 Optional로 변경, None 시 락 내부에서 state["files"] 직접 읽음 → TOCTOU 해소; _post_agent_record는 files_snapshot 없이 호출(lock 내 최신 snapshot 사용). M2: _post_commit_clear에서 git diff HEAD~1 returncode 체크 추가 → 첫 커밋(HEAD~1 없음) 시 silent empty 방지. L1: _post_agent_record sys.path.insert 중복 제거. tests 13종 ALL PASS. |
| 2026-04-20 | v1.2.21 | fix(review-gate): 교차검증 BLOCK 2건+WARN 2건 해소 — (1) record_review_done/clear_committed_files에 fcntl 파일 락(_state_lock ctx manager) 추가 → 병렬 에이전트 RMW 경쟁 조건 해소; (2) verdict='fail'도 'block'과 동등하게 게이트 차단; (3) post_commit_clear exit_code fail-safe: None 또는 파싱 불가 시 skip; (4) post_agent_record verdict 파싱: 구조화 패턴(_VERDICT_RE/_VERDICT_HEADER_RE)으로 본문 키워드 오탐 방지. tests 13종 ALL PASS. |
| 2026-04-20 | v1.2.21 | fix(appendix-b): B1-1~5+B2-5+B2-7+B2-8+B3-1+B3-2 수정 — lineage_ledger threading.Lock+_CACHE_LOCK+is_maxed+reset Lock 전면 보호; project_pipeline _write_json atomic(mkstemp+cleanup)+gate.initialize() 가드; run_factory_cli spec None 가드+AGENT_CHAT_PROVIDER 항상 설정; episode_matcher _SEED_STOP_WORDS 모듈 레벨+EpisodeMatcher facade=None 기본값; approval_gate 섹션 상수화+check_validity no-docs PASS; strategy_ledger key에 owner_role+_load merge+from_dict 기본값 0; work_item_generator asyncio.run 폴백 확대; project_task_board e2e_command 키+BOM 제거. 3-tier 교차검증 ALL PASS. |
| 2026-04-20 | v1.2.21 | feat(review-gate): 3-tier 교차검증 게이트 구현 — `scripts/review_gate.py` 신규(is_gate_blocked/record_review_done/clear_committed_files + CLI); `tests/test_review_gate.py` 12종 ALL PASS; `scripts/hook_runner.py` 3 builtin 추가(pre_bash_review_gate·post_agent_record·post_commit_clear); `.claude/settings.local.json` 훅 배선 3개(PreToolUse Bash·PostToolUse Task·PostToolUse Bash); `.githooks/pre-commit` review-gate 블록 삽입. |
| 2026-04-19 | v1.2.21 | fix(nightly-tick-REVISE): `scripts/nightly_tick.py` 교차검증 후속 REVISE 2건 해소 — (1) F2 save_state 경로 불일치: `_dispatch_actions`에 `state_root` 파라미터 추가, `save_state(state, state_root or workspace)` 사용 → `load_state(ws)`와 동일 경로 보장(active_workspace≠ws 시 crash 복원 무력화 방지); (2) save_state OSError 시 stale active_assignments 방지: try/except 감싸 실패 시 즉시 pop+continue. |
| 2026-04-19 | v1.2.21 | fix(nightly-tick-F1~F4): `scripts/nightly_tick.py` 교차검증 BLOCK 4건 해소 — F1: `_run_task()` bool 반환 + `state_board["completed_subtasks"]` 증분으로 내부 실패 판정 (`made_progress` 오보 방지); F2: `state.active_assignments` 갱신 직후 `save_state()` 호출 — crash 복원 시 assignment 유실 방지; F3: `run_id` 구분자 `':'`→`'_'` (orchestrator `runs/{run_id}/` 경로에서 Windows 불법 문자 제거) + POSIX 전용 guard `if sys.platform == "win32": raise ImportError`; F4: 예외 없이 완료된 모든 tick(idle 포함)에서 `consecutive_tick_failures=0`·`clear_alert()` — healthy idle 이후 false-alarm 방지. |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, nightly_tick.py (+22) |
| 2026-04-20 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, skill-usage.jsonl, code-review.md, nightly_tick.py, skill-eval-report.json (+21) |
| 2026-04-19 | v1.2.21 | hardening(B2-1/B2-2 교차검증 후속): (1) `.gitignore`에 `.af/` 추가 — `watchdog_lineage_counters.json` 등 런타임 파생 파일 실수 커밋 방지 (af-critic BLOCK #2). (2) `core/lineage_ledger.py:_load` legacy map-shape 감지 추가 — B2-2 회귀 기간 동안 map-shape으로 오염된 `.af/lineage_ledger.json`을 `.corrupt.<ts>.json`으로 백업 후 빈 원장 시작하여 FSA `is_maxed` 안전장치 복원 (af-cross-review REVISE #3). (3) `scripts/nightly_tick.py` `run_id=f"{tick_id}:{role}"` 복합 키 — orchestrator `active_assignments[run_id]` 키 충돌 잠재성 제거 (af-critic WARN #1, 미래 병렬화 대비). (4) `docs/2026-04-18-nightly-autonomous-pipeline.md` §2 I5 / §3.6 / Phase 3 / §12 체크리스트 4지점 갱신 — `.af/lineage_ledger.json`을 파생 파일 목록에서 제외, LineageLedger 단일 소유 명시 (af-doc-qa WARN). |
| 2026-04-20 | v1.2.21 | chore(.gitignore): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — .gitignore, document_index.json, Master_Blueprint.md, lineage_ledger.py, nightly_state.py (+26) |
| 2026-04-20 | v1.2.21 | chore(.gitignore): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — .gitignore, document_index.json, Master_Blueprint.md, lineage_ledger.py, nightly_state.py (+26) |
| 2026-04-19 | v1.2.21 | fix(B2-1): `scripts/nightly_tick.py` board 스키마 mismatch 복원 — `_dispatch_actions`가 `board["modules"][*]["tasks"][*]["role"]`을 읽어 항상 빈 `roles_in_board` → early return으로 tick이 실제 dispatch를 전혀 수행하지 못하던 회귀. (1) top-level `board["tasks"]` flat list를 직접 순회 + `owner_role` 사용, (2) `next_board_tasks()` 반환 dict의 실제 키(`assigned_role`/`subtask_instruction`/`task_id`)로 접근 정정, (3) `_execute_agent_task`에 필수 인자 `run_id=tick_id` 전달 추가. Phase 0 자율 tick 불변식(태스크 dispatch) 복원. |
| 2026-04-19 | v1.2.21 | fix(B2-2): `core/nightly_state.py` `.af/lineage_ledger.json` 스키마 충돌 해소 — `_render_derived_files`가 매 tick 종료마다 `state.watchdog.lineage_counters`(dict)를 이 파일에 덮어써 `LineageLedger` 클래스의 `{"entries":[...]}` 포맷을 파괴 → FSA loop의 실패/성공 history 유실. 파생 파일 경로를 `watchdog_lineage_counters.json`으로 분리하고, `.af/lineage_ledger.json`은 `LineageLedger` 단일 소유 확정. E2E: LineageLedger 3 history 저장 → save_state 후 intact 검증 PASS. |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/nightly_state.py — document_index.json, Master_Blueprint.md, nightly_state.py, skill-usage.jsonl, code-review.md (+23) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/nightly_state.py — document_index.json, Master_Blueprint.md, nightly_state.py, skill-usage.jsonl, code-review.md (+23) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, nightly_tick.py (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/nightly_tick.py — document_index.json, skill-usage.jsonl, code-review.md, nightly_tick.py, skill-eval-report.json (+21) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, verify_handoff_checker.py (+22) |
| 2026-04-19 | v1.2.21 | fix(B2-3): `scripts/verify_handoff_checker.py:88-106` `_propagate_block_to_gate` 경로 계산 복원 — 기존 `workspace = work_item_dir.parent.parent`(=docs)가 ApprovalGate 내부 `os.path.join(workspace, "docs", "work-items", slug)` 재조합과 만나 `docs/docs/work-items/<slug>` 이중 경로 → BLOCK 전파 no-op이던 회귀 해소. `report_path.resolve()` 선행 후 `work_item_dir.parent.parent.parent`(=repo root)로 정정하여 pre-commit/CLI/서브디렉토리/절대경로 전부 일관된 workspace 계산. af-critic BLOCK(CWD 의존성+gate_path 기준 불일치) + af-cross-review ACCEPT + af-test-runner 77/77 PASS + af-doc-qa WARN 해소. |
| 2026-04-19 | v1.2.21 | design(review-gate): `docs/2026-04-19-review-gate-enforcement.md` §10 Q5 실증 결과 확정 (exit 2 Bash 차단 ✅, `tool_input.command`/`subagent_type` 경로 ✅, matcher≠tool_name + 서브에이전트 Bash 발동 + settings 리로드 발견), §6.2/§6.3 Q5 추가 발견 반영, §9 구현 순서 #1 ✅ 완료 표기, §11 롤백 #1·#2 "세션 재시작 불필요" 명시, §12 DoD Appendix A 체크, Appendix B.4 B2-1/B2-2 잔여 상태 기록. |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, verify_handoff_checker.py (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/.af_runtime/probe_block.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+21) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/.af_runtime/probe_hook.py — document_index.json, skill-usage.jsonl, code-review.md, skill-eval-report.json, skill-eval-report.json (+20) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/run_factory_cli.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, run_factory_cli.py (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/run_factory_cli.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, run_factory_cli.py (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/run_factory_cli.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, run_factory_cli.py (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/run_factory_cli.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, run_factory_cli.py (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/install_scheduler.py — document_index.json, skill-usage.jsonl, code-review.md, skill-eval-report.json, skill-eval-report.json (+20) |
| 2026-04-19 | v1.2.21 | feat(e2e): §6.1 tick_simulator 합성 테스트 (GE-1~5) — `tests/e2e/tick_simulator.py` 신규(48-tick 완주·mtime 단조증가·watchdog 에스컬레이션·alert.flag 검증), `tests/e2e/conftest.py` sim_workspace/no_dispatch/fail_dispatch 픽스처, `core/watchdog.py` `_VALID_LEVELS` → `ClassVar[frozenset]` 수정(dataclasses JSON 직렬화 버그 해소), `pytest.ini` e2e 마커 추가, af-critic WARN 3건 + af-cross-review ACCEPT 2건 해소 |
| 2026-04-19 | v1.2.21 | feat(phase2): approval-gate ← verify-handoff 연결 — `scripts/verify_handoff_checker.py` 5항목 검증(placeholder `{{...}}` 스캔·forbidden token·verdict≠BLOCK·e2e exit_code·severity 비율), `docs/templates/verify-handoff.md.tpl` 신규, `core/approval_gate.py` checker 통합, af-critic BLOCK 2건+WARN 4건 해소 |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/tick_simulator.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/tick_simulator.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/conftest.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+23) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/tick_simulator.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/tick_simulator.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/tick_simulator.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/tick_simulator.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+22) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/watchdog.py — document_index.json, Master_Blueprint.md, watchdog.py, skill-usage.jsonl, code-review.md (+23) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/watchdog.py — document_index.json, Master_Blueprint.md, watchdog.py, skill-usage.jsonl, code-review.md (+23) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/tick_simulator.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+21) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/conftest.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+21) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/tests/e2e/__init__.py — document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md, skill-eval-report.json (+21) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — document_index.json, Master_Blueprint.md, code-review.md, verify_handoff_checker.py, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — document_index.json, Master_Blueprint.md, code-review.md, verify_handoff_checker.py, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — document_index.json, Master_Blueprint.md, code-review.md, verify_handoff_checker.py, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — document_index.json, Master_Blueprint.md, code-review.md, verify_handoff_checker.py, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — document_index.json, Master_Blueprint.md, code-review.md, verify_handoff_checker.py, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — document_index.json, Master_Blueprint.md, code-review.md, verify_handoff_checker.py, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/work_item_generator.py — document_index.json, Master_Blueprint.md, work_item_generator.py, code-review.md, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — document_index.json, Master_Blueprint.md, episode_matcher.py, code-review.md, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — document_index.json, Master_Blueprint.md, episode_matcher.py, project_pipeline.py, code-review.md (+19) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py — document_index.json, Master_Blueprint.md, project_pipeline.py, code-review.md, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/project_pipeline.py — document_index.json, Master_Blueprint.md, project_pipeline.py, code-review.md, skill-eval-report.json (+18) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — document_index.json, Master_Blueprint.md, episode_matcher.py, project_pipeline.py, project_task_board.py (+2) |
| 2026-04-19 | v1.2.21 | chore(.system_generated): edit: /Users/hoon/workTree/agent-factory/core/project_task_board.py — document_index.json, Master_Blueprint.md, project_pipeline.py, project_task_board.py, code-review.md (+1) |
| 2026-04-19 | v1.2.21 | chore(core): edit: /Users/hoon/workTree/agent-factory/core/project_task_board.py — project_pipeline.py, project_task_board.py |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, episode_matcher.py (+28) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, episode_matcher.py (+28) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, episode_matcher.py (+28) |
| 2026-04-18 | v1.2.22 | feat(phase4): 에피소드 Memory + 재사용 — strategy_ledger.py 신규, episode_matcher.py top-k 확장, work_item_generator 힌트 주입, _pick_owner_role ledger 우선, memory/episodes/ 시드 3종, af.spec hiddenimports 추가, §0/§4 Flow D 추가 |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_task_board.py — settings.local.json, document_index.json, Master_Blueprint.md, episode_matcher.py, project_task_board.py (+27) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/work_item_generator.py — settings.local.json, document_index.json, Master_Blueprint.md, episode_matcher.py, work_item_generator.py (+26) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/work_item_generator.py — settings.local.json, document_index.json, Master_Blueprint.md, episode_matcher.py, work_item_generator.py (+26) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, episode_matcher.py, skill-usage.jsonl (+25) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/episode_matcher.py — settings.local.json, document_index.json, Master_Blueprint.md, episode_matcher.py, skill-usage.jsonl (+25) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/memory_system/strategy_ledger.py — settings.local.json, document_index.json, skill-usage.jsonl, code-review.md, app.py (+23) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/fsa_loop.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, dynamic_orchestrator.py (+31) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/watchdog.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, dynamic_orchestrator.py (+31) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/watchdog.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, dynamic_orchestrator.py (+31) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, dynamic_orchestrator.py (+31) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, dynamic_orchestrator.py (+31) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/dynamic_orchestrator.py — settings.local.json, document_index.json, Master_Blueprint.md, af.spec, dynamic_orchestrator.py (+31) |
| 2026-04-18 | v1.2.21 | feat(phase3): ISE 배선 + lineage 기반 Level 누적 — lineage_ledger.py 신규, watchdog.py is_lineage_maxed/degrade_lineage 추가, fsa_loop.py lineage_id+initial_failure_result 파라미터, dynamic_orchestrator IMPL 실패→FSALoop 위임(AF_ISE_ENABLED 제어), ise_loop.py FSALoop 얇은 래퍼로 축소, task.lineage_id 필드 추가, §4 Flow B 실 배선 반영 |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/tests/test_dynamic_orchestrator_workspace_scope.py — settings.local.json, document_index.json, Master_Blueprint.md, dynamic_orchestrator.py, fsa_loop.py (+30) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/tests/test_dynamic_orchestrator_workspace_scope.py — settings.local.json, document_index.json, Master_Blueprint.md, dynamic_orchestrator.py, fsa_loop.py (+27) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/ise_loop.py — settings.local.json, document_index.json, Master_Blueprint.md, dynamic_orchestrator.py, fsa_loop.py (+17) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/dynamic_orchestrator.py — settings.local.json, document_index.json, Master_Blueprint.md, dynamic_orchestrator.py, fsa_loop.py (+10) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/fsa_loop.py — settings.local.json, document_index.json, Master_Blueprint.md, fsa_loop.py, project_task_board.py (+9) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/fsa_loop.py — settings.local.json, document_index.json, Master_Blueprint.md, fsa_loop.py, project_task_board.py (+9) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/fsa_loop.py — settings.local.json, document_index.json, Master_Blueprint.md, fsa_loop.py, project_task_board.py (+9) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/fsa_loop.py — settings.local.json, document_index.json, Master_Blueprint.md, fsa_loop.py, project_task_board.py (+9) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/watchdog.py — settings.local.json, document_index.json, Master_Blueprint.md, project_task_board.py, watchdog.py (+8) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/project_task_board.py — settings.local.json, document_index.json, Master_Blueprint.md, project_task_board.py, skill-usage.jsonl (+7) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/lineage_ledger.py — settings.local.json, document_index.json, skill-usage.jsonl, code-review.md, app.py (+5) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — settings.local.json, pre-commit, document_index.json, Master_Blueprint.md, approval_gate.py (+14) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — settings.local.json, pre-commit, document_index.json, Master_Blueprint.md, approval_gate.py (+14) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/migrate_workitem_e2e.py — settings.local.json, pre-commit, document_index.json, Master_Blueprint.md, approval_gate.py (+14) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/approval_gate.py — settings.local.json, pre-commit, document_index.json, Master_Blueprint.md, approval_gate.py (+14) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — settings.local.json, pre-commit, document_index.json, Master_Blueprint.md, approval_gate.py (+14) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/migrate_workitem_e2e.py — settings.local.json, pre-commit, document_index.json, Master_Blueprint.md, approval_gate.py (+14) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/work_item_generator.py — settings.local.json, pre-commit, document_index.json, Master_Blueprint.md, approval_gate.py (+14) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/work_item_generator.py — settings.local.json, pre-commit, document_index.json, Master_Blueprint.md, approval_gate.py (+14) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/verify_handoff_checker.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, document_policy.py (+12) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/document_policy.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, document_policy.py (+12) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/core/approval_gate.py — settings.local.json, document_index.json, Master_Blueprint.md, approval_gate.py, skill-usage.jsonl (+10) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+9) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+9) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+9) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/blueprint_updater.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+9) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/code_review_updater.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+8) |
| 2026-04-18 | v1.2.21 | chore(.claude): edit: /Users/hoon/workTree/agent-factory/scripts/hook_runner.py — settings.local.json, document_index.json, Master_Blueprint.md, skill-usage.jsonl, code-review.md (+7) |
| 2026-04-18 | v1.2.21 | chore(settings/hooks): 훅 설정 정리 및 권한 확장 — hook name 필드 5개 제거, curl·awk·venv python 허용 권한 추가, hook_runner.py 수정, 로또 프로젝트(app.py·cli.py) 업데이트, skills registry·eval 리포트 갱신 |
| 2026-04-18 | v1.2.21 | feat(lotto-mobile-web): 추천 서비스 및 로또 예측기 개선 — recommendation.py 로직 수정, draw_cache.py 캐시 서비스 변경, http_client.py 백엔드 연동 업데이트, CLI 오프라인 모드 지원, settings에 curl·venv python 허용 커맨드 추가 |
| 2026-04-18 | v1.2.21 | feat(lotto-mobile-web): draw_cache 및 로또 예측 서버 개선 — draw_cache.py 캐시 로직 수정, app.py API 엔드포인트 업데이트, http_client.py 백엔드 통신 개선, cli.py 명령 흐름 조정, settings.local.json curl·venv 권한 추가 |
| 2026-04-18 | v1.2.21 | feat(lotto): 로또 모바일웹 오프라인 지원 및 시드 갱신 스크립트 개선 — lotto_mobile_web 서버 API 추가, lotto_predictor_v2 CLI·http_client 수정, refresh_lotto_seed.py 업데이트, settings.local.json curl·venv 권한 추가, skills registry 갱신 |
| 2026-04-18 | v1.2.21 | chore(multi): 개발 환경 권한 확장 및 lotto 프로젝트 개선 — settings.local.json에 curl·ipconfig·venv python 허용 권한 추가, lotto_mobile_web 추천 서비스(recommendation.py) 수정, lotto_mobile_web app.py 엔드포인트 조정, lotto_predictor_v2 CLI 수정, document_index 캐시 갱신 |
| 2026-04-18 | v1.2.21 | feat(lotto): refresh_lotto_seed.py 신규 추가 및 추천 서비스 개선 — scripts/refresh_lotto_seed.py 신규, recommendation.py 로직 수정, app.py API 엔드포인트 업데이트, cli.py 변경, settings.local.json curl·venv 권한 추가 |
| 2026-04-18 | v1.2.21 | feat(recommendation): 로또 추천 서비스 개선 및 개발 환경 권한 확장 — recommendation.py 오프라인 모드 로직 수정, app.py API 엔드포인트 조정, .venv/curl/ipconfig bash 권한 추가, document_index 캐시 갱신, cli.py 출력 포맷 개선 |
| 2026-04-18 | v1.2.21 | feat(lotto-mobile-web): 추천 서비스 오프라인 모드 및 API 권한 확장 — recommendation.py 오프라인 추천 로직 수정, app.py API 엔드포인트 연동, settings.local.json에 curl·ipconfig·venv python 권한 추가, document_index.json 캐시 갱신 |
| 2026-04-18 | v1.2.21 | chore(lotto+settings): 권한 허용 및 lotto 서버/CLI 개선 — settings.local.json curl·python3 실행 권한 추가, lotto_mobile_web recommendation.py 수정, lotto_mobile_web app.py 수정, lotto_predictor_v2 cli.py 수정, document_index 캐시 갱신 |
| 2026-04-18 | v1.2.21 | chore(lotto-web): 로컬 권한 확장 및 추천 서비스 개선 — settings.local.json에 curl·ipconfig·python3 실행 권한 추가, lotto_mobile_web recommendation.py 수정, lotto_predictor_v2 cli.py 업데이트, document_index.json 캐시 갱신 |
| 2026-04-18 | v1.2.21 | chore(work_item_generator): 권한 설정 확장 및 문서 인덱스 갱신 — settings.local.json에 curl/ipconfig/.venv python3 허용 규칙 추가, document_index 청크 해시 갱신, lotto-mobile-web 추천 서비스 수정, work_item_generator.py 업데이트 |
| 2026-04-18 | v1.2.21 | chore(settings,watchdog): 개발 환경 허용 명령어 및 훅 설정 정리 — curl·venv python 실행 허용 추가, 훅 name 필드 제거, lotto 추천 API 오프라인 모드 개선, CLI 리포트 출력 개선, document_index 캐시 갱신 |
| 2026-04-18 | v1.2.21 | feat(lotto-mobile-web): 오프라인 추천 모드 및 팩토리 CLI 개선 — recommendation.py 오프라인 지원 추가, app.py API 엔드포인트 수정, run_factory_cli.py 안정성 개선, dynamic_orchestrator.py 업데이트, curl/ipconfig 허용 권한 추가 |
| 2026-04-18 | v1.2.21 | feat(dynamic_orchestrator): 오케스트레이터 개선 및 lotto 프로젝트 안정화 — dynamic_orchestrator.py 로직 수정, lotto_mobile_web 추천 API(recommendation.py/app.py) 업데이트, lotto_predictor_v2 CLI 개선, curl/ipconfig 권한 허용 추가 |
| 2026-04-18 | v1.2.21 | feat(nightly-phase1): Phase 1 외부 의존 3-티어 + 금지 토큰 스캐너 — `core/document_policy.py`(금지 토큰 리스트·스캔·Jaccard), `core/work_item_generator.py`(`_generate_and_refine` LLM 보강 루프 max 2회), `projects/lotto_predictor_v2/seed_draws.json`(100회차 seed), `lotto_predictor_v2/backend/http_client.py`(`ThreeTierLotteryClient` live→cache→seed), `lotto_mobile_web/recommendation.py`(Tier3 `_load_seed()`), `docs/patterns/2026-04-18-external-api-3tier.md`(표준), `scripts/refresh_lotto_seed.py`(월 1회 갱신), `scripts/measure_goal_overlap.py`(GH Jaccard 측정) |
| 2026-04-18 | v1.2.21 | feat(nightly): Phase 0 야간 자율 파이프라인 인프라 — `core/watchdog.py`(WatchdogState), `core/nightly_state.py`(NightlyState·state_snapshot.json), `scripts/nightly_tick.py`(tick CLI, flock, SIGTERM), `scripts/nightly_summary.py`, `scripts/install_launchd.sh`(plist 이중 스케줄), `DynamicOrchestrator.restore_from()`, `run_factory_cli.py` nightly-start/stop/status/tick 서브커맨드, `policy.yaml` nightly_autonomy 섹션 추가 |
| 2026-04-18 | v1.2.21 | docs(blueprint): Phase -1 드리프트 동기화 — §2 Flow A `max_cycles=50`→동적, §3.2 `_stall_threshold=5`→`15` + `max_cycles`→`compute_max_cycles()`, §2 Flow B ISE 배선 누락 현황 명시(FSALoop dead), §7 ApprovalGate `execution_open` + `status=="approved"` AND 조건 명시, §11 `stopped_max_cycles` 에러 코드 동적 공식 반영 |
| 2026-04-17 | v1.2.21 | {"changelog":"test(pending-review): check_pending_review 테스트 보강 — tests/test_pending_review.py 갱신, scripts/check_pending_review.py 수정, Master_Blueprint.md·code-review.md 동기화, skill-eval-report.json·document_index.json 재생성"} |
| 2026-04-17 | v1.2.21 | {"type":"text","text":"docs(review-pipeline): 교차검증 파이프라인 문서·스크립트 정비 — Master_Blueprint.md 업데이트, code-review.md 갱신, scripts/check_pending_review.py 수정, skill-eval-report.json 갱신, document_index.json 캐시 재생성"} |
| 2026-04-17 | v1.2.21 | {"changelog": "chore(review): 교차검증 파이프라인 산출물 갱신 — scripts/check_pending_review.py 편집, docs/code_review/code-review.md 갱신, document_index.json 캐시 확장, skill-eval-report.json 리포트 업데이트"} |
| 2026-04-22 | (unreleased) | feat(compact-step2): Phase A Step 2 COMPACT 연동 활성화 — ① agent_runner.py `_flush_trace()`: `result["text"]` 빈 문자열 버그 → transcript `assistant` 엔트리 합산으로 RunBudget.record() 실제 연결. ② fsa_loop.py: 각 FSA 사이클 시작 시 RunBudget.is_exhausted() 조기 탈출 체크 추가. ③ policy.yaml: phase_gate + context_window 섹션 신설(placeholder, 코드 미연결 명시). ④ plan_verifier.py: PlanVerifyResult.redirect 필드 + PlanVerifier.gate() Phase Gate 메서드 신설(work_items 없으면 redirect="create_plan"). PhaseGateResult 하위 호환 별칭. ⑤ core/skill_pack_bootstrapper.py 신규: shutil.which 기반 claude-code/codex/gemini 감지(설치 없음). ⑥ tests/test_compact_step2.py 신규 18개(autouse RunBudget fixture). af.spec hiddenimport 추가. §0·§3.8.3·§3.8.4·§12 갱신 |
| 2026-04-17 | v1.2.21 | feat(hooks): PostToolUse에 post_edit_test 훅 추가 — settings.local.json에 테스트 실행 스텝 신규 삽입, hook_runner.py에 post_edit_test 핸들러 구현, test_hook_runner_builtins.py에 검증 케이스 추가, document_index.json 청크 갱신, code-review.md·Master_Blueprint.md·CLAUDE.md 문서 동기화 |
| 2026-04-17 | v1.2.21 | feat(hooks): PostToolUse에 편집 후 자동 테스트 훅 추가 — `post_edit_test` 커맨드 신규 등록, `hook_runner.py` 실행 분기 추가, `check_pending_review.py` 관련 로직 갱신, `document_index.json` 캐시 갱신, Blueprint·코드리뷰 문서 동기화 |
| 2026-04-17 | v1.2.21 | feat(hook_runner): `.py` 편집 후 즉시 pytest 실행 — `_post_edit_test` 신규 추가, 편집 파일명 기반 `test_<module>.py` 자동 탐지, 매칭 실패 시 `tests/` 전체 fallback, `_BUILTINS` 등록 완료 |
| 2026-04-17 | v1.2.21 | fix(scripts): hook_runner·enqueue_agent_review 리뷰 파이프라인 개선 — hook_runner.py 실행 흐름 수정, enqueue_agent_review.py 큐잉 로직 변경, document_index.json 청크 캐시 갱신, Master_Blueprint.md 반영, code-review.md 체크리스트 업데이트 |
| 2026-04-17 | v1.2.21 | fix(review-pipeline): hook_runner·enqueue_agent_review 안정화 — hook_runner.py stdin JSON 파싱 방식 개선, enqueue_agent_review.py cross_validate 주입 로직 수정, code-review.md 리뷰 체크리스트 갱신, Blueprint §12 이력 업데이트, document_index 캐시 재색인 |
| 2026-04-17 | v1.2.21 | fix(scripts): hook subprocess stdout 누수 차단 + enqueue updated_at 항상 갱신 — hook_runner.py 모든 subprocess.run에 capture_output=True 추가, _post_edit_py_compile 실패 시 r.returncode 정확히 로깅, enqueue_agent_review.py에서 중복 파일 여부 무관하게 updated_at 갱신, code-review.md에 2026-04-17 리뷰 세션 2건 추가 |
| 2026-04-17 | v1.2.21 | chore(hook_runner): hook_runner.py 정비 및 문서 동기화 — hook_runner.py 수정, Master_Blueprint.md §섹션 갱신, code-review.md 인플레이스 업데이트, document_index.json 청크 해시 재색인 |
| 2026-04-17 | v1.2.21 | ``` |
| 2026-04-17 | v1.2.21 | ``` |
| 2026-04-17 | v1.2.21 | ``` |
| 2026-04-17 | v1.2.21 | ``` |
| 2026-04-17 | v1.2.21 | ``` |
| 2026-04-17 | (unreleased) | fix(hooks): **PostToolUse hook no-op 복구 — stdin JSON 파싱으로 전환** — `.claude/settings.local.json`의 5개 PostToolUse 명령(`$TOOL_INPUT_file_path` env var 참조 — 존재하지 않는 변수로 no-op)을 `python3 scripts/hook_runner.py post_edit_*` builtin 형식으로 교체. `scripts/hook_runner.py`에 `_BUILTINS` 분기 테이블 신설 + `_read_hook_stdin_once()` / `_extract_file_path()` / `_log_hook_event()` 헬퍼 추가. 5종 builtin 함수: `post_edit_py_compile`, `post_edit_enqueue`, `post_edit_code_review`, `post_edit_blueprint`, `post_edit_design_review`. `scripts/enqueue_agent_review.py` atomic write(`tempfile + os.replace`) 전환. `scripts/check_pending_review.py`에 consumed 타임스탬프(`fired_at`) 로직 추가 + `MIN_BATCH_INTERVAL_SEC` 300초로 상향. `.af_review_queue/hook_events.log` 관측성 로그 신설. 테스트 18종 신규(`tests/test_hook_runner_builtins.py`). E2E smoke: `echo '{"tool_input":{"file_path":"core/x.py"}}' | python3 scripts/hook_runner.py post_edit_enqueue` → 마커 생성 확인. §11 에러 코드 "PostToolUse hook no-op" 항목 추가 |
| 2026-04-17 | (unreleased) | feat(todo-sync): **board → `.todo.md` 단방향 동기화** — `core/documentation_policy.py`에 `_normalize_instruction`, `_mark_for_status`, `_instruction_status_map` 헬퍼 신설 + `write_project_todo` 시그니처에 `board` 인자 추가. board의 task.instruction을 공백 정규화 완전 일치로 매칭(safe_id 60자 절단 허위 매칭 회피). `completed`→`[x]`, `in_progress`→`[/]`, `blocked/failed`→`[!]`, `pending`→`[ ]`. 동일 instruction이 여럿이면 가장 덜 완료된 상태 채택(보수적). `core/project_task_board.py:update_project_board_task`의 `locked_file` 컨텍스트 **내부**에 `write_project_todo` 훅 추가(lock 바깥 race 방지). `sync_todo_from_board()` 모듈 함수 신설. `core/dynamic_orchestrator.py:_open_todo_items`에서 `[!]` prefix를 open items에서 제외. `agent_launcher.py`에 `project sync-todo <dir> [--dry-run]` CLI 서브커맨드 추가. 환경 변수 `AF_TODO_SYNC=0`으로 훅 비활성화 가능(kill-switch). 테스트 11종 신규(`tests/test_documentation_policy.py`). `projects/lotto_predictor_v2/.todo.md` 복구 실행(23 `[x]`, 3 `[/]`, 10 `[ ]`). 설계 문서 `docs/2026-04-17-todo-md-board-sync.md` v3 작성(af-critic PASS) |
| 2026-04-16 | (unreleased) | fix(review-pipeline): `pick_review_provider()` 연결 — `inject_review_tasks()`가 cross_validate 태스크 생성 시 `pick_review_provider(author_provider)`로 작성자와 다른 CLI provider를 `review_provider` 필드에 기록. 테스트 2건 hook 경로 assert를 `cli_hook_bridge.py` → `hook_runner.py` + `cli_hook_bridge`로 수정(session_adapter hook 경유 전환 반영). `project_board_state.json` 루트 정적 파일 삭제(workspace별 동적 보드로 전환 완료) |
| 2026-04-16 | v1.2.21 | chore(settings): 빌드 다이어트 및 훅 안정화 — settings.local.json 허용/차단 규칙 50건 추가, SessionStart 훅 경로를 절대경로로 변경, UserPromptSubmit 훅 command 동일 패치, rm 와일드카드 deny 추가, skill-eval/registry/dashboard 메타데이터 갱신 |
| 2026-04-16 | (unreleased) | fix(session-hooks): Claude/Gemini native hook를 절대경로 `sys.executable` 직접 호출에서 `hook_runner.py` 경유 실행으로 전환. `core/providers/session_adapter.py`에 legacy bridge hook 판별 로직을 추가해 unnamed 구형 hook, `python3.14` 절대경로 hook, 빈 hook group을 재생성 시 자동 제거하도록 정리. `tests/test_cli_session_adapter.py`에는 hook 명령이 `hook_runner.py`를 사용하고, 중복된 Claude `SessionStart` hook가 단일 named hook로 정규화되는 회귀 테스트를 추가. 목적은 macOS Homebrew Python 3.14에 `PyYAML`이 없는 환경에서도 Claude startup hook가 import 단계에서 죽지 않게 하는 것 |
| 2026-04-15 | (unreleased) | refactor(dispatch): **af-critic WARN-3/WARN-4 완전 해소 + af-cross-review Q1 race 수정** — (1) `core/project_task_board.py`에 `compute_max_cycles(workspace, logger=None)` 모듈 함수 추출 + `MAX_CYCLES_TASK_MULTIPLIER=4` / `MAX_CYCLES_FLOOR=30` 상수화. `dynamic_orchestrator._orchestration_loop`의 closure를 제거하고 모듈 함수 호출로 전환 → 테스트가 더 이상 규칙을 복제할 필요 없음(단일 진실원천). (2) `except Exception` 블록에 `logger` 파라미터 주입 → I/O 실패 시 silent가 아닌 `print_agent_msg("Lilith", ...)`로 가시화. (3) `_dependency_satisfied`에서 module-level 의존성 판정 시 `module.status` 대신 module 내부 task들이 전부 completed인지 직접 검증 → `_recalculate_board` 호출 시점 race(`module.status`가 stale "pending"으로 남아 depends_on=[module_id]인 태스크가 blocked되는 false negative) 원천 차단. (4) 테스트의 `_simulate_compute_max_cycles` 복제본 제거 → 실제 `compute_max_cycles`를 monkeypatch로 직접 호출하는 방식으로 변경, logger 캡처 검증 테스트 1종 추가. (5) Q1 race 회귀 테스트 2종 신규(`test_dependency_satisfied_module_dep_uses_task_level_when_status_is_stale`, `..._blocks_when_any_task_pending`). 총 12/12 PASS |
| 2026-04-15 | (unreleased) | fix(dispatch): **af-critic WARN 4종 반영** — (WARN-1 High) `_MODULE_SUFFIX_RE` 정규식을 lazy `^(.*?)(?:_(\d+))?$` → greedy `^(.+)_(\d+)$`로 교체하고 접미사 없는 id는 원본을 prefix로 유지해 빈 prefix `("", 0)` silent sort 오염 회귀 차단. (WARN-2 High) `max_cycles` 배수 3→**4**로 상향 + 근거 주석(`used_roles` 가드로 cycle-per-task ≈1, 상태 업데이트 지연 1, 의존성 체인 여유 1, stall/재시도 1 = 4). (WARN-3 Medium) `_compute_max_cycles()` 로컬 closure 추출 + loop 내부 10 cycle마다 재평가해 동적 태스크 추가 시 상한 **연장만** 반영(단축 안 함). (WARN-4 Medium) `tests/test_project_task_board_dispatch.py`에 max_cycles 경계 테스트 5종 추가(pending=0 fallback, 24/100 정상 스케일, completed/failed 제외/blocked 포함, malformed board 방어). 총 9/9 PASS |
| 2026-04-15 | (unreleased) | fix(dispatch): **module waterfall + dynamic max_cycles** — `core/project_task_board.py::next_board_tasks` 정렬 key를 `(phase, module_id, task_id)` → `(_module_sort_key(module_id), phase, task_id)`로 뒤집어 같은 모듈의 scope→build→verify가 완주한 뒤 다음 모듈로 넘어가도록 변경. `_MODULE_SUFFIX_RE` + `_module_sort_key()` 헬퍼 신규(module_10 > module_2 문자열 정렬 회귀 방지). `core/dynamic_orchestrator.py::_orchestration_loop`의 `max_cycles = 30` 하드코딩을 `max(30, pending*3)`로 동적 계산(진입 시 `load_project_board`로 pending 태스크 집계). **근본 원인**: 2026-04-15 `lotto-pattern-predictor` FSA 실측에서 24 태스크 중 scope 4개만 완료한 채 Cycle 30 도달로 exit — `src/` 구현 태스크가 한 번도 dispatch되지 않음. phase 우선 정렬이 "모든 모듈의 scope를 먼저 소화하다가 max_cycles 소진" 경로를 만들었고 그 위에 하드 max_cycles=30 제약이 겹쳐진 복합 버그. **실측 매핑**: Cycle 2 → module_1 scope + qa scope / Cycle 16 → module_**2** scope(phase 우선 결과) / Cycle 29 → qa build / Cycle 30 → exit. 신규 테스트 4종(`tests/test_project_task_board_dispatch.py`): `test_next_board_tasks_prefers_same_module_build_after_scope_completes`, `test_next_board_tasks_module_numeric_suffix_sorted_as_int`, `test_next_board_tasks_falls_through_completed_module_to_next`, `test_project_pipeline_imports_without_nameerror`. 로컬 4/4 PASS. Blueprint §11 에러 코드 표에 "파이프라인이 `src/` 구현 태스크에 도달 못 하고 Cycle 30에 exit" 행 추가. role당 1태스크 제한(`used_roles` 가드)은 이번에 손대지 않음 — waterfall + 동적 max_cycles 조합으로 완주 가능한지 다음 실측에서 검증 예정. 교차검증(af-critic/af-cross-review)은 Anthropic API 500 장애로 대기 중 |
| 2026-04-15 | (unreleased) | fix(project_pipeline): `NameError: name '_safe_print' is not defined` — `core/project_pipeline.py` 780/782/848/850에서 `_safe_print`를 import 없이 호출하던 잠재 버그. 정상 경로(structural gate OK, doc cross-review OK, plan verify OK/PASS)에서는 해당 분기가 실행되지 않아 묻혀 있었고, **2026-04-15 `lotto-pattern-predictor` FSA 실측 중** plan verify WARN(score=0.44, LLM refine claude_cli timeout + codex_cli failed) 직후 최초 재현. `from core.agent_runner import _safe_print` 모듈-레벨 import 추가로 해소(순환 없음 — agent_runner는 project_pipeline을 import하지 않음, 기존 `_run_async_safe` 지연 import 패턴과 일관). §11 에러 코드 해설 표에도 등재 |
| 2026-04-14 | (unreleased) | build(phase-b): 빌드 다이어트 — **zip 87MB → 40MB (-54%)**, unpacked 200MB+ → 68MB (-66%). **B0**(`d6d7add7`): `tests/test_gemini_smoke.py` 신규(신/구 SDK 경로 + import-time discovery_cache 미필요 회귀, `@pytest.mark.slow`). **B1**(`08b6f19f`): `af.spec`에 PYZ 직전 `a.datas` 필터 도입 — `googleapiclient/discovery_cache/documents/*.json` 580개 전량 제거, 방어 whitelist(`drive.v3.json`/`customsearch.v1.json`/`gmail.v1.json`)로 LangChain Google 툴 실수 호출 시 `ImportError` 대신 `UnknownApiNameOrVersion` 유지. googleapiclient 94MB 제거. **B2**(`eb0e0969`): `langchain_community` hiddenimport 제거(langchain 1.0 Required-by 없음 + 우리 코드 import 0건 grep 검증 → numpy/SQLAlchemy/langchain-classic 등 ~40MB 간접 의존 배제). **B3**(`17fdda4e`): `skills/core/cortex.py`를 구 SDK(`google.generativeai`) → 신 SDK(`google.genai`, `genai.Client.models.embed_content()` + `EmbedContentConfig(output_dimensionality=768)`)로 마이그레이션, `af.spec`에서 `google.generativeai` hiddenimport 제거. `agents/*/tools/cortex.py` 26개는 소스 모드 런타임 호환을 위해 구 SDK 유지(binary 무관). af-critic(BLOCK 3 무-테스트)·af-cross-review(discovery_cache 전량 제거 동치성) ACCEPT 기반. §8 `af.spec` 설명에 Phase B 섹션 신설 | B3 클래스 수정 묶어 1.2.19 → 1.2.20 patch bump. **이유**: 1.2.19 태그(`af-fsa_v1.2.19`@`0d2b7e78`)는 이미 push되어 reflog/CI에 박혀 있는데 이후 두 fix(`e024ed8f` --version 가드, `07e57c5d` gate 위치 구조 변경)가 동일 1.2.19 버전 zip 내부 코드를 변경 → SemVer 위반(버전 표기 ↔ 실제 코드 불일치). `version.py` 1.2.19→1.2.20, `install-af.ps1`/`install-af.sh` 버전 문자열 7+5곳 일괄 교체(`AF_VERSION` env 기본값 포함), PyInstaller 재빌드 → `dist/af-1.2.20.zip`(86.9MB). 신규 빌드 회귀 PASS(`af --version` → "af 1.2.20" 단독, `--invalid-flag` exit 2 + gate 미실행). 새 태그 `af-fsa_v1.2.20`. **부수 정책 변경**: 빌드 zip(91MB)이 git-lfs 미구성 환경에서 GitHub 100MB 한계로 push 실패 → CLAUDE.md "LFS로 커밋" 규칙 폐기 + `dist/*.zip` `.gitignore` 처리 + `gh release create af-fsa_v{version}`로 배포 전환(`.gitignore`/`CLAUDE.md` 동시 갱신). **부수**: B3 1차 검증 시 사용자 NotebookLM에 부작용으로 생성됐던 빈 아카이브 노트북 `638f9ff2-c955-49c1-bf7b-58b5764dce18` 정리(`nlm notebook delete -y`) |
| 2026-04-14 | v1.2.19 | fix(run_factory_cli): B3 fix follow-up — af-critic WARN 2 + af-cross-review Q1/Q2/Q3/Q5/Q6 ACCEPT 통합 반영. **구조 변경**: `_run_setup_gate()`를 `parse_args()` **뒤로** 이동(STAGE 4 신설) → `af --version`/`-V`/`--help`/`-h`/`--invalid-flag` 등 argparse가 SystemExit으로 즉시 종료시키는 모든 경로에서 setup_wizard가 돌아갈 수 없게 됨(Q1/Q2 ACCEPT의 `af --invalid-flag` 부작용 클래스까지 구조적으로 차단). 모듈 최상위 `_is_help_only` → `_is_meta_only`로 확장 + `_META_FLAGS` 사용으로 통일 → `af --version`에서 `[Auto-Config]` 배너 stdout 오염 제거(Q3/Q6 ACCEPT 실측 해소). 상수 DRY: `_HELP_FLAGS = ("--help","-h"); _META_FLAGS = _HELP_FLAGS + ("--version","-V")` 합성(Q5). `parse_args(argv)` → `parse_args(effective_argv)` 단일 진실원천(WARN-1). STAGE 2 짧은 경로(empty argv / `--interactive` 단독)는 argparse 미경유라 gate 직접 호출 유지. 단위 테스트 +2(test_setup_gate_skips_invalid_flag, test_setup_gate_skips_help_flag) + capsys 단언 추가(test_setup_gate_skips_version_flag) → 24/24 PASS. PyInstaller 재빌드 + 4종 실측 PASS(`af --version` → `af 1.2.19` 단독 / `-V` 동일 / `--invalid-flag` exit 2 + gate 미실행 / `--help` 배너 없음). 부작용 노트북 추가 생성 0건(이전 B3 첫 검증 시 생성된 `638f9ff2-...` 1개 외 증가 없음 검증 완료) |
| 2026-04-14 | v1.2.19 | fix(run_factory_cli): B3 실측 버그 — `af --version` 실행 시 setup_wizard가 돌아가 NotebookLM에 아카이브 노트북이 부작용으로 생성되던 문제. 신규 `_META_FLAGS=("--help","-h","--version","-V")` + `_is_meta_arg()` 도입, STAGE 2 gate 조건을 `_is_help_arg` → `_is_meta_arg`로 교체. argparse에 `--version/-V action='version'` 등록(`version=f"af {__version__}"`). STAGE 1 서브커맨드 레벨 `_is_help_arg`는 `--help`/`-h`만 유지(하위 Typer/argparse가 자체 `--version` 처리 — `af __nlm --version`). `build_exe.py` OS 분기 수정: exe 경로 `af.exe`(win)/`af`(macOS·Linux) 분리, 배포 안내도 분기. 단위 테스트 +2(`test_setup_gate_skips_version_flag` SystemExit(0) + gate 미호출 단언, `test_is_meta_arg_matches_help_and_version` 경계 조건). PyInstaller 재빌드 후 B3 PASS(`af 1.2.19` + exit 0 + 노트북 생성 메시지 없음), `-V` 단축 PASS, `--help` 회귀 PASS |
| 2026-04-14 | v1.2.19 | test(setup-wizard): Phase 5 — §8.1 단위 테스트 20종(`tests/test_setup_wizard_gate.py`) + §8.2 Slow Integration 2종(`tests/test_nlm_regression.py`, `@pytest.mark.slow`) 신규 작성. 22/22 PASS. `pytest.ini`에 `slow` 마커 등록(PytestUnknownMarkWarning 제거). 커버리지: TAVILY 플로우 5종(configured/interactive 저장/skip 재확인 y/skip 루프/noninteractive 경고박스), NotebookLM 플로우 6종(nlm 미설치/Chrome 미설치/auth exit 0·2 파싱/login 성공/noninteractive skip), state I/O 4종(atomic write crash 무손상/v1→v2 migration/corrupted 복구/filelock contention), STAGE 1 gate 3종(setup/__nlm/worker 분기 + gate 미호출 검증), `_invoke_nlm_app` 1종(standalone_mode=False + sys.argv 복원 + SystemExit 차단), `_find_or_create_archive_notebook` UUID 파싱 1종. Slow 2종: `nlm auth status` exit 2 패턴 회귀 + `nlm notebook --help` 서브커맨드 존재 회귀(R5/R11 감지). M1/M3/M5/M7/M9 자동 스모크 PASS 기록 |
| 2026-04-14 | v1.2.19 | docs(blueprint): Phase 6 문서 동기화 — §3.11 Setup Wizard + External Research 신규 작성(데이터 흐름·주요 함수 매트릭스·`.af_setup_state.json` 스키마 v2·순환 방지 규칙·BLOCK-A/B/C + Low-1 해소 매핑·배포 의존성 요약). §0 core 파일 테이블에 `core/setup_wizard.py` 행 추가. `docs/2026-04-03-session-handoff.md:172` `notebooklm-tools` → `notebooklm-cli` + "미완료" → "완료" 정정. Feature 문서 `docs/features/2026-04-10-setup-wizard-tavily-notebooklm-integration.md` 상태 Draft → Implemented, Phase 6 체크리스트 `[x]` 완료 |
| 2026-04-13 | v1.2.19 | feat(setup-wizard): Phase 2 잔여 — `core/research_engine.py` 전면 재작성(DEFAULT_ARCHIVE_NOTEBOOK_ID 하드코딩 제거, `_get_archive_notebook_id()` state 로드, `_nlm_cmd_base()` frozen-aware prefix, `notebooklm_tools.cli.main` → `nlm` 전환, 모듈 레벨 `_ARCHIVE_SKIP_LOGGED`로 archive 미설정 stderr 1회 제한, `--mode` 인자 제거로 180s×2 더블 spawn 버그 해소). `core/researcher.py` `find_spec("notebooklm_tools")` → `find_spec("nlm")` + frozen 분기, `_tavily_skip_logged`/`_notebook_skip_logged` 인스턴스 플래그로 스킵 1회 로그(stderr). `core/setup_wizard.py` 상단에 `core.*` top-level import 금지 경고 주석(research_engine 순환 방지). `skills/research_assistant/skill.py` nlm 헬퍼를 `core.research_engine`에서 import하도록 공통화(중복 제거, 인증 재시도 자동 승계). v3.2에서 `_query_notebooklm`이 `(ok, content_or_reason)` tuple 반환으로 변경 → `apply()`가 archive 미설정·빈 응답·연결 실패 시 에러 문자열을 보고서 본문에 삽입하지 않고 `{"ok": False, "error": ..., "hint": ...}`로 구조화된 실패를 반환(af-cross-review Low-1). `install-af.sh` 신규(macOS/Linux 소스 설치: curl/wget fallback, python3>=3.10 체크, `${INSTALL_ROOT}.new` staging → `mv` 원자적 교체, 실패 시 `.bak` 복원, Chrome 감지, `__check-nlm` 검증, tarball root `<repo>-<tag>/` 주석 명시, **재설치 시 `${BACKUP_ROOT}`의 `.env`/`.af_setup_state.json`을 새 트리로 자동 복원 → 사용자 재입력 방지**, `AF_VERSION`/`AF_INSTALL_ROOT`/`AF_BIN_DIR` 환경변수 override 지원 — `/tmp`에 드라이런 가능하며 로컬 `AF_VERSION=1.2.18 AF_INSTALL_ROOT=/tmp/af_test bash install-af.sh` + 재설치 2회로 tarball·staging·venv·Chrome·`__check-nlm`·state 복원까지 end-to-end 통과 확인). `install-af.ps1` 1.2.18→1.2.19 bump + Chrome 레지스트리 감지 + `__check-nlm` 검증(실패 시 `$nlmCheck` 출력 보존). `.gitignore`에 `.af_setup_state.json` 추가. af-critic BLOCK-1/3 + WARN-2/4 + af-cross-review Q1/Q2/Q4 반영 |
| 2026-04-11 | v1.2.18 | feat(setup-wizard): Phase 2 — `run_factory_cli.py` STAGE 1/2/3 진입점 통합. `_STAGE1_DISPATCH` dict(단일 진실원천, setup/worker/skill-*/preflight + 신규 `__nlm`/`__check-nlm`), `_STAGE1_USAGE` dict(서브커맨드 레벨 `--help` 가드 — `af setup --help`가 wizard를 트리거하지 않음), `_is_help_arg()`(최상위 `--help` 가드 — setup gate 우회), `_run_setup_gate()` STAGE 2에서 `ensure_external_research_capabilities(mode="auto")` 호출, `_invoke_nlm_app()`이 nlm Typer app을 standalone_mode=False + sys.argv 백업/복원으로 안전하게 호출(BLOCK-B/WARN-1 해소). `af.spec`에 `nlm.*` 27개 + `typer/rich/shellingham/websocket/annotated_doc/filelock/tavily` hiddenimports 추가 + `collect_submodules('typer'/'rich'/'nlm')` 안전망(spec 내부; CLI `--collect-submodules`는 PyInstaller 6.x가 `.spec`과 병용 거부). frozen exe에서 setup_wizard 내부 nlm 호출 재귀 차단 |
| 2026-04-10 | v1.2.18 | feat(pre-commit): 교차검증 게이트 + 멀티 프로바이더 + CLI 개선 — pre_commit_review.py 신규(결과 수집+판정), .githooks/pre-commit 교차검증 호출 추가, engine_auth 멀티 프로바이더 등록, registry.py macOS/Linux npm fallback, cli.py timeout 900초+진행 표시기, cross_verification timeout 동기화, PostToolUse hook venv python 절대경로 |
| 2026-04-09 | v1.2.20 | refactor(fsa_loop): FSA 파이프라인을 ISE와 동일한 에스컬레이션 구조로 교체 — ISEAnalyzer/ISERedesigner/StrategyLedger/StallDetector 도입, _decide_escalation(Level 1-5), _decompose_and_execute(서브태스크 분할), _request_human_help(정체 시 사용자 힌트), 기존 _run_cross_verified_evaluator 제거(ISEAnalyzer로 대체), max_cycles=5 유지 |
| 2026-04-09 | v1.2.19 | fix(cross-review-2): BLOCK 2건 + WARN 3건 수정 — plan_verifier 예외 시 passed=False(silent pass 제거), fsa_loop gate_result=None 시 hot_reload 제거(미검증 스킬 등록 방지), project_pipeline __new__→정상 인스턴스, cycle=0 에피소드 기록 가드, refine 루프 동일 결과 break |
| 2026-04-09 | v1.2.19 | fix(cross-review): 교차검증 버그 4개 수정 — project_pipeline PlanVerifier 파일내용 전달(경로→content dict), workspace 전달, fsa_loop gate_result=None 시 EvolutionBus 스킵, control/intake MemoryType enum 명시화(GRAPH/WORKING 오염 방지) |
| 2026-04-09 | v1.2.19 | feat(3-plane): 3-Plane 통합 구현 — skill_quality_gate.py 신규(SkillQualityGate/GateResult), fsa_loop._try_evolve_failed_skill() gate 삽입 + GateResult 반환, _run_quality_gate()/_record_episode() 추가, run_mission() 에피소드 기록(UnifiedMemoryFacade), control/intake.py NormalizedRequest.memory_context 필드 + _recall_from_memory(), bootstrap_roles.plan() memory_context 파라미터 + 과거 교훈 프롬프트 주입, af.spec hiddenimports에 core.skill_quality_gate 추가 |
| 2026-04-08 | v1.2.18 | fix(config_paths): PyInstaller exe에서 BASE_DIR이 임시 언팩 폴더(_MEI...)로 잡히는 버그 수정 — sys.frozen 감지 후 sys.executable 기준으로 전환, 프로젝트가 올바른 경로(af.exe 옆)에 생성됨 |
| 2026-04-07 | v1.0.3 | feat(forge): forge 스킬 품질 파이프라인 — forge_new_skill() 3-helper 분할, evaluate_and_promote() 공통 추출, FORGE_POLICIES, LLM budget 카운터(MAX_LLM_CALLS=15), directory 구조(forge/{name}/{name}.py), sys.path forge guard, propose/apply/test 함수 시그니처, evals.yml 자동 생성(MIN_EVAL_CASES=3), Registry 직접 등록 |
| 2026-04-04 | v1.0.3 | feat(session): revision_loop 학습 루프 (critique_fn + revision_history + best_artifact), run_factory_cli .env 자동로드, JudgmentLedger 설계, 세션 핸드오프 문서 |
| 2026-04-03 | v1.0.3 | feat(skill-discovery): cross-cli-skill-discovery v3 — get_external_skill_roots(personal>project 순서), ClaudeOfficialSkillSource 추가, _extract_skill_id(frontmatter name 우선), should_rescan_external(mtime 기반), ensure_skills_loaded(external_scanned 플래그), claude_official 소스 ID, 하위 호환 alias 유지 |
| 2026-04-03 | v1.0.3 | feat(policy): roles.max 상한 제거 — 리서치 기반 LLM 자율 역할 결정. prefer를 single_responsibility로 변경하여 각 에이전트가 한 가지 책임만 담당하도록 유도 |
| 2026-04-03 | v1.0.3 | fix(bootstrap): _build_policy_rules() — granularity 및 max/min_tasks_per_module이 LLM 프롬프트에 미주입되는 버그 수정. policy.yaml 태스크 분할 정책이 실제 LLM에 전달됨 |
| 2026-04-03 | v1.0.3 | feat(hooks): CodeReviewDocHook — 에이전트 실행 성공 후 자동 코드 리뷰 + docs/code_review.md, docs/change_history.md 자동 업데이트. ControlPlaneLLM 연동, LLM 미사용 시 파일 목록만 기록 |
| 2026-04-03 | v1.0.3 | fix(code-review): Critical 4건 + High 6건 버그 수정 — checkpoint 원자적 쓰기, orchestrator state_board asyncio.Lock, ise_loop 도달불가 코드, issue_tracker 인자 주입 방지, dashboard 스레드 안전, control_plane_llm 환경변수, intake 키 불일치, agent_runner 캐시 제한, ise_redesigner 무한 폴백 방지, context_fork 타임아웃 경고 |
| 2026-04-02 | v1.0.3 | feat(orchestrator): event-driven sparse governor — rule-based dispatch 기본(0 tokens), LLM은 blocker/stall/pivot 시만 호출. RunBudget 글로벌 토큰 예산(--budget), chat autosave/resume(--resume-chat), stall 감지(5-cycle threshold), max_cycles 50→30 |
| 2026-04-02 | v1.2.17+ | feat(control-plane): ControlPlaneLLM CLI-first LLM + FailureClassifier infra/impl 분류 — GOOGLE_API_KEY 없이 Lilith/Evaluator 동작, infra 실패 retry 차단 |
| 2026-04-02 | v1.2.17 | fix(bugs): 6개 파일 크리티컬 버그 수정 — worker 안전성, orchestrator 안정성, cross_verification timeout, fsa_loop 검증, skill_evolution_bus None처리 |
| 2026-04-02 | v1.2.16 | **Blueprint 초기 생성** — v1.2.16 기준 전체 아키텍처 문서화 |
| 2026-04-02 | v1.2.16 | fix(worker): PyInstaller frozen exe → `worker` 서브커맨드 추가 |
| 2026-04-02 | v1.2.15 | fix(installer): LFS에 zip 커밋, raw URL로 다운로드 방식 전환 |
| 2026-04-02 | v1.2.14→15 | fix(installer): release asset URL → raw URL 수정 |
| 2026-04-01 | v1.2.14 | feat(orchestrator): 6개 이슈 수정 — worker, routing, evolution, completion |
| 2026-04-01 | v1.2.13 | feat(pipeline): 문서 품질 개선, 프로젝트 경로 라우팅 수정 |

---

## 유지보수 가이드

### Blueprint 업데이트 규칙

1. **새 파일 추가** → §0 테이블에 추가
2. **클래스/메서드 변경** → §3 해당 서브시스템 `last_updated` 갱신
3. **의존성 변경** → §10 영향 매트릭스 업데이트
4. **버그 수정** → §11 에러 테이블에서 제거 또는 업데이트
5. **버전 릴리스** → §12 변경 이력에 한 줄 추가
6. **af.spec 변경** → §8 hiddenimports 설명 업데이트

### 효율적 검색법

```
기능 수정    → §3 해당 서브시스템 → 파일:라인 참조로 이동
에러 디버그  → §11 에러 코드 테이블
라우팅 변경  → §6 모델 라우팅 → model_utils.py 직접 수정
빌드 문제    → §8 빌드 & 배포
의존성 파악  → §10 Blast Radius 테이블
신규 기능    → §1 아키텍처 → §2 플로우 → §3 관련 서브시스템
```

### Self-Hosting 가능 범위

```
가능 ✅:
  - skills/ 스킬 코드 수정·진화
  - agents/*.yaml 에이전트 정의 수정
  - policy.yaml 정책 변경
  - docs/ 문서 생성·수정

소스 모드에서만 가능 ⚠️:
  - core/*.py 소스 코드 수정
    → python run_factory_cli.py로 실행 필요

불가 ❌:
  - af.exe → 자기 자신 리빌드
  - 빌드 중 빌드 (python build_exe.py는 소스 환경 필요)
```
