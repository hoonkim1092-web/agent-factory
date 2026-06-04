---
generated_at: 2026-06-04T18:21:39+09:00
source_commit: 82cc7fb8
sources:
  - Master_Blueprint.md
  - docs/code_review/code-review.md
  - NEXT_STEPS.md
---

# Architecture — 모듈 네비게이션
> Source: Master_Blueprint.md §0 + §3
> 관련: [[index]] | [[source_refs]]

## 루트 파일

| 파일 | 역할 | Source |
|------|------|--------|
| `run_factory_cli.py` | CLI 진입점 (STAGE 1/2/3) | Master_Blueprint.md §0 |
| `agent_launcher.py` | AgentFactory 부트스트랩. CLI 진입 시 stdin/stdout/stderr 및 child env를 UTF-8 기본값으로 고정해 Windows/macOS 출력 깨짐을 방지. | Master_Blueprint.md §0 |
| `model_utils.py:1-845` | 모델 선택·티어 관리 | Master_Blueprint.md §0 |
| `version.py` | 버전 문자열 | Master_Blueprint.md §0 |
| `build_exe.py` | PyInstaller 빌드 | Master_Blueprint.md §0 |
| `install-af.ps1` | Windows 설치 스크립트 | Master_Blueprint.md §0 |
| `install-af.sh` | macOS/Linux 설치 스크립트 (소스모드, venv 기반) | Master_Blueprint.md §0 |
| `af.spec` | PyInstaller 스펙 | Master_Blueprint.md §0 |
| `policy.yaml` | 전역 정책 | Master_Blueprint.md §0 |

## core/ 주요 모듈

| 파일 | 역할 | Source |
|------|------|--------|
| `core/string_utils.py` | 문자열 유틸리티 | Master_Blueprint.md §0 |
| `core/agent_runner.py:1-1411` | 에이전트 CLI 실행 | Master_Blueprint.md §0 |
| `core/agent_specializer.py` | 태스크 전용 에이전트 커스터마이즈 | Master_Blueprint.md §0 |
| `core/agent_worker.py` | PyInstaller worker 진입점. stdout/stderr `errors=replace`로 Windows/macOS 콘솔 인코딩 차이로 인한 worker 조기 종료를 방지. | Master_Blueprint.md §0 |
| `core/approval_gate.py` | 실행 승인 게이트 | Master_Blueprint.md §0 |
| `core/control/verdicts.py` | Stage 0 verdict/route/cause enum 단일 원천 | Master_Blueprint.md §0 |
| `core/control/stage_artifacts.py` | Stage 0 아티팩트 dataclass | Master_Blueprint.md §0 |
| `core/control/question_router.py` | Stage 0 순수 분류기 (파일 쓰기 없음) | Master_Blueprint.md §0 |
| `core/control/stage_router.py` | Stage 0 오케스트레이터 | Master_Blueprint.md §0 |
| `core/control/context_scanner.py` | LightContextScanner (LLM 0회) | Master_Blueprint.md §0 |
| `core/escalation_evaluator.py` | P2 에스컬레이션 규칙 평가 | Master_Blueprint.md §0 |
| `core/escalation_decision_report.py` | 에스컬레이션 결정 보고서 생성 (P2 신규) | Master_Blueprint.md §0 |
| `core/warning_overrides.py` | false-positive override 관리 (P2 신규) | Master_Blueprint.md §0 |
| `core/warning_registry.py` | WARN 기록 SoT + summarize + decision 트리거 | Master_Blueprint.md §0 |
| `core/warning_stats.py` | P3 read-only 분석 도구 — workspace fan-out + 분포 통계. malformed JSONL 경고 경로는 OS와 무관하게 `/` 포맷으로 출력. | Master_Blueprint.md §0 |
| `core/ast_engine.py` | AST 분석 엔진 (ast-grep-py wrapper) | Master_Blueprint.md §0 |
| `core/ast_memory_hub.py` | AST 기반 메모리 허브 | Master_Blueprint.md §0 |
| `core/review_bundle.py` | 8섹션 리뷰 번들 생성기 (Phase 2) — 100KB cap, source_hash, stale 감지 | Master_Blueprint.md §0 |
| `scripts/build_review_bundle.py` | review_bundle.md 빌드 스크립트 (Phase 2) — build_full() 호출 | Master_Blueprint.md §0 |
| `scripts/build_llm_wiki.py` | LLM Wiki Phase 0 — 무-LLM 결정적 knowledge view 생성기. Blueprint+code-review+NEXT_STEPS → docs/generated/llm_wiki/ 5페이지 | Master_Blueprint.md §0 |
| `scripts/agent_model_selector.py` | P4.5b runtime model escalation helper | Master_Blueprint.md §0 |
| `scripts/check_model_escalation.py` | UserPromptSubmit hook — pending escalation 오케스트레이터 알림 (one-shot) | Master_Blueprint.md §0 |
| `scripts/review_gate.py` | 3-Tier review gate 단일 판정 지점. `.py` 커밋 전 tier 완료·stale·new-files·verdict-block 검사. T3 skip은 cosmetic classifier(+af-critic `t3_required: no`) 또는 Phase 4 telemetry 보수적 AND-게이트일 때만 허용, 위험군은 ALWAYS-Tier-3 강제. CLI: `--check`, `--record`, `--clear`, `--debug`, `--t3-required {yes,no,unknown}` | Master_Blueprint.md §0 |
| `scripts/t3_classifier.py` | deterministic Tier-3 classifier. hard-guard/risk-token/non-python/semantic Python 변경은 T3 요구, docstring/comment 수준 cosmetic Python 변경만 T3 skip 후보. classifier version 단일 원천 | Master_Blueprint.md §0 |
| `scripts/review_metrics_logger.py` | Phase 3.5 리뷰 메트릭 수집 + Phase 4 telemetry skip 판정. T3-only 기여도 리포트 + 보수적 AND-게이트 skip 결정(SSOT 임계 4개) | Master_Blueprint.md §0 |
| `scripts/enqueue_agent_review.py` | PostToolUse edit hook 큐잉. review 대상 `.py` 누적, blast_tier max-merge, T3 classifier + telemetry skip 결정을 `.af_review_queue/pending_agent_review.json`에 atomic write, 발효 시 skip_audit 기록 | Master_Blueprint.md §0 |
| `core/bootstrap_roles.py` | 프로젝트 계획 부트스트랩 에이전트 | Master_Blueprint.md §0 |
| `core/builder.py` | 스킬 코드 생성 샌드박스 | Master_Blueprint.md §0 |
| `core/config_paths.py` | 경로 상수 중앙화 | Master_Blueprint.md §0 |
| `core/control_plane_llm.py` | Control-plane CLI-first LLM | Master_Blueprint.md §0 |
| `core/cross_verification.py:1-758` | 멀티 CLI 교차검증 | Master_Blueprint.md §0 |
| `core/dashboard.py` | 실행 이력 모니터링 | Master_Blueprint.md §0 |
| `core/destructive_guard.py` | 위험 명령 차단 | Master_Blueprint.md §0 |
| `core/design_review_utils.py` | 설계문서 교차검증 공유 유틸 (watcher 관리, 큐 관리, 패턴 매칭) | Master_Blueprint.md §0 |
| `core/document_chunker.py` | 문서 청킹 (RAG) | Master_Blueprint.md §0 |
| `core/document_index.py` | Dense+Sparse 하이브리드 검색 | Master_Blueprint.md §0 |
| `core/documentation_policy.py` | 주석/문서화 정책 주입 + `.todo.md` board 동기화 | Master_Blueprint.md §0 |
| `core/dynamic_orchestrator.py:1-887` | 멀티 에이전트 비동기 오케스트레이터 (sparse governor) | Master_Blueprint.md §0 |
| `core/nightly_state.py` | 야간 자율 파이프라인 상태 관리 (state_snapshot.json) | Master_Blueprint.md §0 |
| `core/watchdog.py` | tick 기반 stall 감지 + lineage 상한 감지 | Master_Blueprint.md §0 |
| `core/lineage_ledger.py` | lineage 기반 Level 누적 원장 (atomic file write, `_MAX_LEVEL=5`, success 시 level/attempts 리셋) | Master_Blueprint.md §0 |
| `core/memory_system/strategy_ledger.py` | 역할 배정·실패 패턴 영구 원장 (Phase 4) | Master_Blueprint.md §0 |
| `core/engine_auth.py` | CLI 프로바이더 자동 감지·설정 (API 키 유무 기반 우선순위 정렬) | Master_Blueprint.md §0 |
| `core/evaluator.py` | 실패 분석 (retry/pivot/abort) | Master_Blueprint.md §0 |
| `core/executor.py` | 태스크 실행 래퍼 | Master_Blueprint.md §0 |
| `core/failure_classifier.py` | 실패 분류 (infra/impl) | Master_Blueprint.md §0 |
| `core/run_budget.py` | 글로벌 토큰 예산 추적 | Master_Blueprint.md §0 |
| `core/skill_pack_bootstrapper.py` | 외부 CLI 플러그인 감지 (claude-code/codex/gemini) | Master_Blueprint.md §0 |
| `core/fsa_loop.py:1-540` | FSA 에스컬레이션 루프 (ISE 파이프라인, 5사이클 제한). `run_mission(..., runtime_workspace=None)`로 Git/user 작업 범위와 `.af`/runner state 범위를 분리 | Master_Blueprint.md §0 |
| `core/git_manager.py` | 워크스페이스 git 연산 | Master_Blueprint.md §0 |
| `core/hooks/event_bus.py` | 훅 라이프사이클 버스 | Master_Blueprint.md §0 |
| `core/hooks/skill_self_evolution.py` | 주기적 스킬 품질 감사 | Master_Blueprint.md §0 |
| `core/hooks/code_review_doc.py` | 실행 후 자동 코드 리뷰 + 문서 업데이트 | Master_Blueprint.md §0 |
| `core/hooks/guardrails.py` | 실행 가드레일 | Master_Blueprint.md §0 |
| `core/ingestion_pipeline.py` | 문서 인덱싱 파이프라인 | Master_Blueprint.md §0 |
| `core/interactive_chat.py` | 대화형 PDCA 모드 (autosave/resume) | Master_Blueprint.md §0 |
| `core/ise_loop.py` | 무한 자가진화 루프 | Master_Blueprint.md §0 |
| `core/llm_engine.py` | LLM API 호출 엔진 | Master_Blueprint.md §0 |
| `core/manager.py` | 에이전트 생성·로드 | Master_Blueprint.md §0 |
| `core/memory_system/facade.py` | 메모리 단일 진입점 | Master_Blueprint.md §0 |
| `core/message_broker.py` | TCP/인메모리 메시지 브로커 | Master_Blueprint.md §0 |
| `core/model_router.py` | CLI 프로바이더 선택 | Master_Blueprint.md §0 |
| `core/policy_runtime.py` | 정책 런타임 래퍼 | Master_Blueprint.md §0 |
| `core/project_mailbox.py` | 파일 기반 에이전트 간 메시지함 | Master_Blueprint.md §0 |
| `core/project_pipeline.py` | Phase1(문서)+Phase2(실행) 파이프라인. **F15**: `runtime_workspace`로 `.checkpoint/`, `runtime/warnings/`, strategy ledger, orchestrator `runs/data/artifacts`를 사용자 workspace와 분리. **P2 C1**: `ResearchGateBlocked` + `_verify_domain_spec()` + `_save_specs()` + `_coverage_blocked()`. **P2 C3+C4**: `_load_evidence`, `_save_adr()`, `_save_traceability()` (원자 write, Path 반환, planning_files 추가). **P3 D1**: `_save_specs()` → list 반환, spec content → `project_brief["domain_specs_summary"]` 주입(generate_work_items 호출 전), _spec_paths → planning_files 추가. **P3 D3**: `research_evidence.research_plan` → `project_brief` 주입 (domain 감지용, None-guard 포함). **P5**: `prepare_documents()` 내 `generate_work_items()` 직전 `ChangeImpactProfiler().profile()` 호출 → `project_brief["blast_radius"]` 주입 (LLM brief에 blast_radius 미포함 시 git-diff+board 휴리스틱으로 보완, 배포 동등성 보장) | Master_Blueprint.md §0 |
| `core/spec_generator.py` | **P2 C2**: 포커 5종 명세. **P2 C3**: `AdrGenerator.generate()` — evidence claims/sources 기반 ADR 생성, LLM 실패 시 fallback (fallback은 LLM 호출 후만 적용). **P2 C4**: `TraceabilityGenerator.generate()` — claims=[] 시 `""` 반환, 휴리스틱 claim↔spec↔task 매핑 MD 표. `_call_llm_raw()` 실패 시 `""` (sentinel 명확화). 저장 위치: ADR=`docs/decisions/<slug>-rule-baseline.md`, trace=`docs/research/<slug>-traceability.md` | Master_Blueprint.md §0 |
| `core/project_task_board.py` | 태스크 보드 상태 관리 + `.todo.md` 동기화 훅 | Master_Blueprint.md §0 |
| `core/providers/cli.py` | CLI 프로바이더 실행 + 진행 표시. **F10**: `_collect_git_context()` — git HEAD/branch/log/status 수집 후 `_compose_prompt()`의 `[Git State]` 섹션으로 gemini/claude/codex_cli 3개 provider에 자동 주입 | Master_Blueprint.md §0 |
| `core/providers/session_adapter.py` | CLI 세션 hook 설정·연속성 브리지. **Phase D**: `_write_claude_settings` 본문을 `locked_file(timeout=5)` wrap, `prepare_cli_session`에 `TimeoutError` catch (settings 미작성 후 계속 진행). **Hook Unicode hardening**: hook payload JSON 저장/출력을 ASCII-safe로 escape하고 lone surrogate를 sanitize | Master_Blueprint.md §0 |
| `core/provider_detect.py` | 3-state CLI 프로바이더 감지 + 1h 디스크 캐시 + AF_SKIP_PROVIDER 처리. ThreadPool race condition 수정: installed_set을 ThreadPool 전 1회 계산 후 각 worker에 frozenset 전달. codex_cli ping: --version (exec stdin hang 수정). CLI ping stdout/stderr는 UTF-8/errors=replace로 디코딩. | Master_Blueprint.md §0 |
| `core/providers/registry.py` | 설치된 CLI 목록 (Unix npm fallback 포함) + 교차검증 provider 선택. 멀티스레드 안전: `_installed_cli_cache_lock` double-checked locking 패턴 | Master_Blueprint.md §0 |
| `core/research_engine.py` | NotebookLM 통합 엔진 (사서) | Master_Blueprint.md §0 |
| `core/research_router.py` | Phase 1a: project research mode 분류 + complexity gap 탐지. P0 A5: `ResearchPlan` 3종 필드 + `_detect_domain_hints()` (overlay 선택 보조, gate 아님). **P3 D3c**: substring 매칭 + `"홀덤"` 토큰 추가. **P4**: `_detect_domain()` deprecated → `_detect_domain_hints()` 위임. | Master_Blueprint.md §0 |
| `core/researcher.py` | Himari 리서치 에이전트. **P4**: RecoverySearchLoop에 `_build_quality_contract()` 연결. **coverage-gate hoist (2026-05-20)**: `_build_quality_contract`/`_domain_checklist` 계산을 3분기 진입 전으로 hoist — 조건 `requires_web or mode != "fast_synthesis"` (순수 fast_synthesis 제외). `_emit_coverage_report`/`_identify_unmet_gaps`에 `llm_prior_refs` 파라미터 추가(no-Tavily 배포 false BLOCK 방지). escalation 재귀 호출에 `research_plan=` 전달 + `ResearchPlan.for_mode(scores=...)` (관측성). | Master_Blueprint.md §0 |
| `core/research/__init__.py` | P4 QualityContract 서브패키지 진입점 | Master_Blueprint.md §0 |
| `core/research/work_spec.py` | P4: 사용자 요청 → WorkSpec 구조화. `WorkSpecExtractor`가 LLM 호출로 `artifact_type/domain/capabilities/risk_areas/constraints` 추출. `domain_hints`는 regex hint만 (advisory). | Master_Blueprint.md §0 |
| `core/research/quality_contract.py` | P4: QualityContract 모델 + Builder. pack 레이어 순서: base → artifact → capability → domain overlay. 빈 체크리스트 → `QualityContractBuildError`. | Master_Blueprint.md §0 |
| `core/research/checklist_merger.py` | P4: 동일 id 항목 병합. overlay/llm_addition이 required=True 항목 삭제 불가. | Master_Blueprint.md §0 |
| `core/security_guard.py` | AST 분석 + 격리 실행 | Master_Blueprint.md §0 |
| `core/setup_wizard.py` | 외부 리서치 도구(TAVILY/NotebookLM) 점검·복구 단일 진입점 | Master_Blueprint.md §0 |
| `core/skill_cache.py` | 스킬 관련성 LRU 캐시 | Master_Blueprint.md §0 |
| `core/skill_creator.py` | 스킬 생성·진화 | Master_Blueprint.md §0 |
| `core/skill_metadata_adapter.py` | YAML/Markdown → SkillMetadata 변환 + SKILL.md fallback | Master_Blueprint.md §0 |
| `core/skill_enricher.py` | 스킬 메타데이터 자동 생성 | Master_Blueprint.md §0 |
| `core/skill_eval_harness.py` | 계약/숨겨진/섀도우 테스트 | Master_Blueprint.md §0 |
| `core/skill_quality_gate.py` | 스킬 품질 게이트 (Quality Plane) — knowledge skill early-return + auto_register 지원 | Master_Blueprint.md §0 |
| `core/evolution_types.py` | Stage-1 공유 타입 (Sprint 1 신규) | Master_Blueprint.md §0 |
| `core/skill_evolution_bus.py:1-241` | 7단계 캐시 무효화 체인 | Master_Blueprint.md §0 |
| `core/skill_evolution_safety.py` | 스킬 진화 안전망 헬퍼 (Stage 0 임시, Stage 1 흡수 예정) | Master_Blueprint.md §0 |
| `core/skill_forge.py` | 코드 생성→비평→수정 루프 | Master_Blueprint.md §0 |
| `core/skill_procurer.py` | 스킬 조달·forge·평가·승격 | Master_Blueprint.md §0 |
| `core/skill_loader.py` | 런타임 스킬 동적 로딩 | Master_Blueprint.md §0 |
| `core/skill_promotion.py` | 스킬 라이프사이클 전환 | Master_Blueprint.md §0 |
| `core/skill_registry.py` | 스킬 메타데이터 중앙 저장소 | Master_Blueprint.md §0 |
| `core/swarm_council.py` | 다중 역할 계획·승인 | Master_Blueprint.md §0 |
| `core/document_policy.py` | 금지 토큰 스캔·입력 계약·Jaccard | Master_Blueprint.md §0 |
| `core/work_item_generator.py` | LLM 기반 work-item 생성 + chained refinement. **Phase E (C-3stages 병렬화)**: `TOTAL_BUDGET=600s`, `STAGE_BUDGET{1:90/2:400/3:110}`. `_build_full_run_id` doc_type별 격리. `_exec_stage2` (ThreadPoolExecutor×2 + `cf.wait(ALL_COMPLETED)`). `_extract_section_outline` → tasks prev_spec_outline 전달. 텔레메트리 → `write_initial_record`. **v3.1 (2026-05-11)**: `_GRACE_SEC=5`. `_exec_stage1`(plan+EpisodeHints) / `_exec_stage3`(spec_outline+tasks) 신설. `_generate_and_refine` `deadline` + refine loop deadline guard (F1). `_extract_section_outline` mismatch→`""` (F9). `_exec_stage2` `deadline=` 전달. Stage3 진입 전 `time.sleep(_GRACE_SEC)` (R7). **B-1 (2026-05-21)**: `_inline(value, limit)` sanitizer(`\s+→" "`, `\n##` 분리 방지) + `_skill_gap_bullets(brief, limit)` list[dict] formatter + `_structured_evidence_block(brief)` — structured evidence 3필드(required_capabilities/verification_focus/skill_gap_hypotheses)를 fallback plan/spec/design `## Evidence` 내부 sub-bullet으로 보존. 새 `##` 헤더 신설 없음(`_extract_section_outline` count=12 회귀 방지). **B-1 후행 (2026-05-21)**: `_generate_feature_plan`/`_generate_feature_spec`/`_generate_implementation_design` LLM 프롬프트 Rules에 structured evidence 명시 — required_capabilities=스킬조달신호, verification_focus=Evidence 하위 검증기준, skill_gap_hypotheses=reuse/enhance/forge계획신호, 새 ## 섹션 금지. | Master_Blueprint.md §0 |
| `core/cli_session_cleanup.py` | `.af_runtime/cli_sessions/` 하위 30일 초과 CLI 세션 파일 TTL 정리 (Phase A, v2 finding #2). **v3.1 R8**: 디렉토리 cleanup 시 dir mtime 대신 자식 파일 max mtime 사용 (POSIX dir mtime 의미 불일치 수정). | Master_Blueprint.md §0 |
| `core/work_item_telemetry.py` | work-item 생성 텔레메트리 — T1 retry 횟수 atomic JSON 기록 (Phase A). **simplify**: `write_initial_record(workspace, slug, results)` 신규 (초기 dump, locked_file + atomic write). **v3.1 F7**: 경로 `workspace_runtime_dir(workspace) / "work_item_telemetry"` (컨벤션 통일). | Master_Blueprint.md §0 |
| `core/requirement_llm.py` | LLM 요구사항 분석 + 마크다운 문서 생성. **Phase C**: `return_usage=False` 옵션, `execute_document_prompt` 응답에 `elapsed_sec`+`usage_tokens` 추가. **simplify**: `_make_usage(prompt_t, completion_t)` 헬퍼 추출 (3× 인라인 중복 제거). **v3.1 F2**: `_call_google/openai/anthropic_api`에 `timeout_sec: int = 120` 추가; google → ThreadPoolExecutor manual + `fut.result(timeout=)`; openai → `client.with_options(timeout=)`; anthropic → `urlopen(timeout=timeout_sec)`. `execute_document_prompt` 3개 API 호출에 `timeout_sec=` 전달. | Master_Blueprint.md §0 |
| `core/work_item_parser.py` | 편집된 마크다운 재파싱 | Master_Blueprint.md §0 |
| `core/control/supervisor.py` | 유지보수 감독 루프 | Master_Blueprint.md §0 |
| `core/agent_reservation.py` | agent reservation | Master_Blueprint.md §0 |
| `core/capability_intent.py` | capability intent | Master_Blueprint.md §0 |
| `core/clarification.py` | clarification | Master_Blueprint.md §0 |
| `core/interview.py` | user-facing deep interview workflow | Master_Blueprint.md §0 |
| `core/research_brief.py` | §17 Step 3 — interview artifact → ResearchBrief; evidence tagger | Master_Blueprint.md §0 |
| `core/spec_compiler.py` | §17 Step 4 — interview + research → CompiledSpec | Master_Blueprint.md §0 |
| `core/premortem.py` | §17 Step 5 — CompiledSpec → repo-aware risks + verification steps | Master_Blueprint.md §0 |
| `core/planner.py` | §17 Step 6 — CompiledSpec + PremortomResult → ExecutablePlan. P2(2026-05-25): `_build_implementation_steps`가 core/*.py scope item에 `Master_Blueprint.md`를 artifacts에 자동 추가 — Blueprint 동기화 allowlist 연동. 2026-05-27: `implementation_steps(plan)` 헬퍼 신설 — `id`에 'IMPLEMENT' 포함 step만 필터. 2026-05-27 (advisory): `PlanStep.reference_artifacts` 필드 추가 — research_findings 의 companion test/sibling pattern 경로를 read-only context로 노출(`_references_for_scope_item()` 헬퍼). dogfood `_build_ai_task` 가 "Reference files (read-only ...)" 섹션으로 surface. 2026-05-31: `_build_investigation_steps()`에 R11(scope_file) 연동 — `_extract_scope_file_paths()` 헬퍼로 missing 경로 파싱 후 경로별 "경로 확인" step 생성(`shlex.quote` 안전 처리). 2026-05-31: R12(stale_test) 연동 — `_extract_stale_test_paths()` 헬퍼로 stale 파일→`tests/test_<stem>.py` 경로 변환, "테스트 작성" investigation step 생성. 2026-06-01: R16(complexity) 연동 — `_extract_complexity_pairs()` 헬퍼 + complexity investigation branch. **risk ID 계약 정리**: `_is_assumption_risk()`를 category-only로 축소(brittle `[5,20)` ID-레인지 제거 — 신규 fixed detector 오분류 방지), `pattern_consistency`(R10) 전용 investigation branch 신설(레인지 제거로 인한 R10 step 누락 회귀 차단). 2026-06-01: R17(nesting_depth) 연동 — `_extract_nesting_depth_pairs()` 헬퍼 + nesting_depth investigation branch(R16 패턴 미러, 구현 전 "중첩 깊은 함수 검토" step 생성). last_updated: 2026-06-01 | Master_Blueprint.md §0 |
| `core/dogfood.py` | §17 Step 7~16 — Dogfood state machine + worktree isolation + auto-merge lifecycle. 14-phase pipeline (ISOLATE/FINALIZE/MERGE 추가). DogfoodState 3-path 분리(source/worktree/runtime), MergePolicy 정책 게이트, prepare_isolated_worktree() 1-retry, finalize_dogfood_result(), merge_dogfood_branch() crash recovery+reset--merge. P1(2026-05-25): IMPLEMENT no-op guard — 모든 steps가 commands=[] (AI executor 미연결)이면 BLOCKED. P3(2026-05-25): finalize_dogfood_result() selective staging — plan allowlist(artifacts+tests_required) 교집합만 stage; 나머지는 scope_violations로 기록. P4(2026-05-26): dogfood shell/git subprocess env + decoding을 UTF-8로 고정. P0(2026-05-26): run_all strict_contract, phase_trace.jsonl, RunBudget accounting, pre-IMPLEMENT static smoke 추가. R-PHASE(2026-05-26): _run_research_phase stub→실 구현 — scope .py 파일 + companion test 파일 읽기 → evidence bundle {local_refs:[...]}. DogfoodState.research_path 신규. last_updated: 2026-05-26 | Master_Blueprint.md §0 |
| `core/concurrency.py` | concurrency | Master_Blueprint.md §0 |
| `core/consensus_engine.py` | consensus engine | Master_Blueprint.md §0 |
| `core/context_window_manager.py` | context window manager | Master_Blueprint.md §0 |
| `core/conversation_manager.py` | conversation manager | Master_Blueprint.md §0 |
| `core/conversation_prompts.py` | conversation prompts | Master_Blueprint.md §0 |
| `core/conversation_room.py` | conversation room | Master_Blueprint.md §0 |
| `core/conversation_task_adapter.py` | conversation task adapter | Master_Blueprint.md §0 |
| `core/external_skill_candidate_importer.py` | external skill candidate importer | Master_Blueprint.md §0 |
| `core/external_skill_source_ids.py` | external skill source ids | Master_Blueprint.md §0 |
| `core/external_skill_sources.py` | external skill sources | Master_Blueprint.md §0 |
| `core/file_io.py` | file io | Master_Blueprint.md §0 |
| `core/file_lock.py` | file lock | Master_Blueprint.md §0 |
| `core/hashline_editor.py` | hashline editor | Master_Blueprint.md §0 |
| `core/implementation_language_policy.py` | implementation language policy | Master_Blueprint.md §0 |
| `core/install_candidate_utils.py` | install candidate utils | Master_Blueprint.md §0 |
| `core/intent.py` | intent | Master_Blueprint.md §0 |
| `core/ise_stall_detector.py` | ise stall detector | Master_Blueprint.md §0 |
| `core/knowledge_skill.py` | knowledge skill | Master_Blueprint.md §0 |
| `core/langchain_adapter.py` | langchain adapter | Master_Blueprint.md §0 |
| `core/lsp_bridge.py` | lsp bridge | Master_Blueprint.md §0 |
| `core/mcp_adapter.py` | mcp adapter | Master_Blueprint.md §0 |
| `core/memory.py` | memory | Master_Blueprint.md §0 |
| `core/onboarding_wizard.py` | onboarding wizard | Master_Blueprint.md §0 |
| `core/parallel_critique.py` | parallel critique | Master_Blueprint.md §0 |
| `core/pdca_commands.py` | pdca commands | Master_Blueprint.md §0 |
| `core/pdca_state.py` | pdca state | Master_Blueprint.md §0 |
| `core/pipeline_quality.py` | pipeline quality | Master_Blueprint.md §0 |
| `core/plan_verifier.py` | plan verifier | Master_Blueprint.md §0 |
| `core/policy.py` | policy | Master_Blueprint.md §0 |
| `core/project_init.py` | project init | Master_Blueprint.md §0 |
| `core/registry.py` | registry | Master_Blueprint.md §0 |
| `core/registry_manager.py` | registry manager | Master_Blueprint.md §0 |
| `core/request_router.py` | request router | Master_Blueprint.md §0 |
| `core/critic_skill_router.py` | Tier 2 Phase 3 단계 1 — 변경 파일 → 영역 → SKILL ID 매핑 | Master_Blueprint.md §0 |
| `core/retrieval_router.py` | retrieval router | Master_Blueprint.md §0 |
| `core/review_report.py` | review report (Tier 2 Phase 2: `ReviewerResult.vendor_mode` 필드 추가) | Master_Blueprint.md §0 |
| `core/review_runner.py` | review runner (Tier 2 Phase 2: `_extract_vendor_label()` + single-vendor notice) | Master_Blueprint.md §0 |
| `core/role_decomposer.py` | role decomposer | Master_Blueprint.md §0 |
| `core/rubric_compiler.py` | rubric compiler | Master_Blueprint.md §0 |
| `core/runner.py` | runner | Master_Blueprint.md §0 |
| `core/security_scanner.py` | security scanner | Master_Blueprint.md §0 |
| `core/semantic_embedder.py` | semantic embedder | Master_Blueprint.md §0 |
| `core/skill_autodiscover.py` | skill autodiscover | Master_Blueprint.md §0 |
| `core/skill_context_config.py` | skill context config | Master_Blueprint.md §0 |
| `core/skill_feedback.py` | skill feedback | Master_Blueprint.md §0 |
| `core/skill_metadata.py` | skill metadata | Master_Blueprint.md §0 |
| `core/skill_preflight.py` | skill preflight | Master_Blueprint.md §0 |
| `core/skill_retrieval_engine.py` | skill retrieval engine | Master_Blueprint.md §0 |
| `core/skill_spec_synthesizer.py` | skill spec synthesizer | Master_Blueprint.md §0 |
| `core/synergy_runner.py` | synergy runner | Master_Blueprint.md §0 |
| `core/template_input.py` | template input | Master_Blueprint.md §0 |
| `core/terminal_bridge.py` | terminal bridge | Master_Blueprint.md §0 |
| `core/terminal_visualizer.py` | terminal visualizer | Master_Blueprint.md §0 |
| `core/text_integrity.py` | text integrity. Detects UTF-8/BOM/newline drift, mojibake, and literal carriage-return control characters such as repeated `\r` at line ends. | Master_Blueprint.md §0 |
| `core/tool_runtime.py` | tool runtime | Master_Blueprint.md §0 |
| `core/utils.py` | utils. last_updated: 2026-06-04 (weighted_mean 추가) | Master_Blueprint.md §0 |
| `core/triad.py` | §17 Step 15 — 正反合 Triad 오케스트레이션. 反(Critic) injectable executor + evidence contract 강제 + Critical finding 미해소 시 TriadBlockedError. 合(Architect) injectable executor. | Master_Blueprint.md §0 |
| `core/review_skill_router.py` | §17 Step 17 — Skill-specialized 3-tier review routing. changed-file paths·blast tier·work kind·risk tokens 기반으로 각 review tier의 skill profile을 결정적으로(no LLM) 라우팅. last_updated: 2026-05-25 | Master_Blueprint.md §0 |
| `core/express_router.py` | §17 Step 18 — Express Router. task description → direct/light/full/dogfood 4-경로 결정적 라우팅(no LLM). self-mod 토큰·risk·research·complexity 기반 분류. Windows 경로 정규화. force_route 오버라이드. last_updated: 2026-05-25 | Master_Blueprint.md §0 |
| `core/right_sized_router.py` | RSE 슬라이스1 — LLM 분류 + 결정적 안전 floor 강제. `classify(task, workspace, *, changed_files)→RouteDecision`. Floor 1: self-mod→isolation≥worktree. Floor 2: blast_radius Tier3→design+review+cross_review 강제. 보수적 fallback(예외/{}→full+worktree). `is_light()` True → `_run_develop_light` 경로(leaf codegen). `_max_tier(changed_files, workspace)` — scope 파일들의 blast_radius Tier 최댓값; `classify_with_content` 사용(content 기반 Tier3 상향 포함); 신규 파일은 Tier2 fallback. last_updated: 2026-06-04 (2) | Master_Blueprint.md §0 |
| `core/architect_agent.py` | §17 Step 19 — Triad 合(Synthesis) Architect executor. TriadCriticReport findings를 Master_Blueprint.md §섹션 + accepted ADR로 검증하여 ACCEPT/REJECT 결정. prefix false match 방지(`(?![\d.])` lookahead), set 기반 중복 키워드 제거, deepcopy 불변성. last_updated: 2026-05-25 | Master_Blueprint.md §0 |

## §3 서브시스템

| ID | 이름 | 파일 | Source |
|----|------|------|--------|
| §3.1 | ProjectPipeline | `core/project_pipeline.py` | Master_Blueprint.md §3.1 |
| §3.2 | DynamicOrchestrator | `core/dynamic_orchestrator.py` | Master_Blueprint.md §3.2 |
| §3.3 | AgentRunner | `core/agent_runner.py` | Master_Blueprint.md §3.3 |
| §3.4 | AgentSpecializer | `core/agent_specializer.py` | Master_Blueprint.md §3.4 |
| §3.5 | 스킬 시스템 | `` | Master_Blueprint.md §3.5 |
| §3.6 | 메모리 시스템 | `core/memory_system/` | Master_Blueprint.md §3.6 |
| §3.7 | CrossVerification | `core/cross_verification.py` | Master_Blueprint.md §3.7 |
| §3.8 | Warning Registry & Stats (`core/warning_registry.py`, `core/escalation_evaluator.py`, `core/escalation_decision_report.py`, `core/warning_overrides.py`, `core/warning_stats.py`) | `` | Master_Blueprint.md §3.8 |
| §3.9 | Evaluator | `core/evaluator.py` | Master_Blueprint.md §3.9 |
| §3.8.1 | ControlPlaneLLM | `core/control_plane_llm.py` | Master_Blueprint.md §3.8.1 |
| §3.8.2 | FailureClassifier | `core/failure_classifier.py` | Master_Blueprint.md §3.8.2 |
| §3.8.3 | RunBudget | `core/run_budget.py` | Master_Blueprint.md §3.8.3 |
| §3.8.4 | SkillPackBootstrapper | `core/skill_pack_bootstrapper.py` | Master_Blueprint.md §3.8.4 |
| §3.9 | Continuity | `core/continuity/` | Master_Blueprint.md §3.9 |
| §3.10 | Control 서브시스템 | `core/control/` | Master_Blueprint.md §3.10 |
| §3.11 | Setup Wizard + External Research (`core/setup_wizard.py`, `core/research_engine.py`) | `` | Master_Blueprint.md §3.11 |
| §3.13 | Dogfood Pipeline | `core/dogfood.py` | Master_Blueprint.md §3.13 |
| §3.12 | 자동 Core 변경 요약 | `` | Master_Blueprint.md §3.12 |
