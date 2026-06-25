---
generated_at: 2026-06-25T15:43:56+09:00
source_commit: 10ff6a75
sources:
  - "Master_Blueprint.md"
  - "docs/code_review/code-review.md"
  - "NEXT_STEPS.md"
---

# Architecture — 모듈 네비게이션
> Source: Master_Blueprint.md §0 + §3
> 관련: [[index]] | [[symbols]] | [[source_refs]]

## 루트 파일

| 파일 | 역할 | Source |
|------|------|--------|
| `run_factory_cli.py` | CLI 진입점 (STAGE 1/2/3). `--project` 실행 시 `project_root`를 `AgentFactory.run(workspace=...)`에 전달하고 `runtime_workspace=FACTORY_DIR`로 AF 상태와 사용자 산출물 경로를 분리. | Master_Blueprint.md §0 |
| `agent_launcher.py` | AgentFactory 부트스트랩. CLI 진입 시 stdin/stdout/stderr 및 child env를 UTF-8 기본값으로 고정해 Windows/macOS 출력 깨짐을 방지. ad-hoc 실행은 `--workspace` > `AF_CALLER_CWD` > CWD 순으로 대상 폴더를 확정하고, AF 루트 TTY 실행 시 폴더 입력을 요청. | Master_Blueprint.md §0 |
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
| `core/agent_runner.py:1-1617` | 에이전트 CLI 실행 | Master_Blueprint.md §0 |
| `core/agent_specializer.py` | 태스크 전용 에이전트 커스터마이즈 | Master_Blueprint.md §0 |
| `core/agent_worker.py` | PyInstaller worker 진입점. stdout/stderr `errors=replace`로 Windows/macOS 콘솔 인코딩 차이로 인한 worker 조기 종료를 방지. | Master_Blueprint.md §0 |
| `core/approval_gate.py` | 실행 승인 게이트 | Master_Blueprint.md §0 |
| `core/control/verdicts.py` | Stage 0 verdict/route/cause enum 단일 원천 | Master_Blueprint.md §0 |
| `core/control/stage_artifacts.py` | Stage 0 아티팩트 dataclass | Master_Blueprint.md §0 |
| `core/control/question_router.py` | Stage 0 순수 분류기 (파일 쓰기 없음) | Master_Blueprint.md §0 |
| `core/control/stage_router.py` | Stage 0 오케스트레이터. **Q-S4(2026-06-19)**: `_run_new_project()`이 `gc_result` 처리 후 `_qa_{output_field}` sentinel keys + `_qa_provenance`(JSON)를 files dict에 추가 → `work_item_generator.py`가 pop해 `project_brief`에 흡수(INV-Q3 경로 C). last_updated: 2026-06-19 | Master_Blueprint.md §0 |
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
| `scripts/codebase_symbols.py` | 외부 프로젝트 코드 심볼 인덱서. Python은 표준 `ast`, C#은 보수적 선언 패턴으로 `.py`/`.cs` 파일의 클래스·함수·메서드를 결정적으로 수집하고 `symbols.md`를 렌더링. | Master_Blueprint.md §0 |
| `scripts/build_llm_wiki.py` | LLM Wiki/Obsidian용 무-LLM 결정적 knowledge view 생성기. Blueprint+code-review+NEXT_STEPS+Python/C# AST symbols → docs/generated/llm_wiki/ 41페이지. 섹션 파일명은 Obsidian 탐색기에서 읽히도록 제목 기반 slug 사용. **외부 프로젝트 지원**: AF 문서 3종 부재 시 해당 페이지 skip + AST 디렉터리/모듈 navigation(`_build_codebase_tree`)만으로 full-wiki 생성(`af project wiki <path>`). | Master_Blueprint.md §0 |
| `scripts/agent_model_selector.py` | P4.5b runtime model escalation helper | Master_Blueprint.md §0 |
| `scripts/check_model_escalation.py` | UserPromptSubmit hook — pending escalation 오케스트레이터 알림 (one-shot) | Master_Blueprint.md §0 |
| `scripts/review_gate.py` | 3-Tier review gate 단일 판정 지점. `.py` 커밋 전 tier 완료·stale·new-files·verdict-block 검사. T3 skip은 cosmetic classifier(+af-critic `t3_required: no`) 또는 Phase 4 telemetry 보수적 AND-게이트일 때만 허용, 위험군은 ALWAYS-Tier-3 강제. **Phase 1 BLOCK Learning**: BLOCK/FAIL finding을 7개 known family(`hiddenimport`/`production_caller_wiring`/`blueprint_update`/`absolute_path`/`fixture_only`/`pre_commit_bypass`/`provider_instruction_drift`)로 정규화해 `data/review-block-patterns.jsonl`에 capture. CLI: `--check`, `--record`, `--clear`, `--debug`, `--t3-required {yes,no,unknown}`. last_updated: 2026-06-21 | Master_Blueprint.md §0 |
| `scripts/af_evolution.py` | `af evolution list` CLI — `data/review-block-patterns.jsonl`에서 패턴별 발생 횟수를 집계하고 재발(≥2) 패턴을 강조 출력. `unknown:*`는 집계 제외(v1 Scope). last_updated: 2026-06-21 | Master_Blueprint.md §0 |
| `scripts/t3_classifier.py` | deterministic Tier-3 classifier. hard-guard/risk-token/non-python/semantic Python 변경은 T3 요구, docstring/comment 수준 cosmetic Python 변경만 T3 skip 후보. classifier version 단일 원천 | Master_Blueprint.md §0 |
| `scripts/review_metrics_logger.py` | Phase 3.5 리뷰 메트릭 수집 + Phase 4 telemetry skip 판정. T3-only 기여도 리포트 + 보수적 AND-게이트 skip 결정(SSOT 임계 4개) | Master_Blueprint.md §0 |
| `scripts/enqueue_agent_review.py` | PostToolUse edit hook 큐잉. review 대상 `.py` 누적, blast_tier max-merge, T3 classifier + telemetry skip 결정을 `.af_review_queue/pending_agent_review.json`에 atomic write, 발효 시 skip_audit 기록 | Master_Blueprint.md §0 |
| `scripts/enqueue_staged_review.py` | provider/OS 독립 pre-commit 큐잉 fallback. Claude hook 없이 Codex·IDE·shell에서 staged review 대상 `.py`가 커밋될 때 Git index 기준으로 review queue를 먼저 채움 | Master_Blueprint.md §0 |
| `scripts/af_doctor.py` | AF 실행 환경 진단 도구 (`af doctor`). Python·git·provider·hook·pytest·dogfood runtime 7개 항목을 ok/warn/fail로 진단. --fast(설치만)·--refresh(auth ping)·--json·--strict 지원. `main()` → int 반환 | Master_Blueprint.md §0 |
| `scripts/af_sandbox.py` | `af sandbox on\ | Master_Blueprint.md §0 |
| `scripts/af_project_inspect.py` | `af project inspect` — Python 프로젝트 컨텍스트 팩 생성. LLM/네트워크 없음, deterministic. doctor 재사용(run_checks fast)하되 표시에서 cwd-git 항목(`_DOCTOR_CWD_GIT_CHECKS`) 제외 — doctor 섹션은 "AF 실행 환경"만, 대상 git은 `_git_info(root)`가 담당. risks schema `{kind,severity,message,source}` + `recommended_next_steps`(p0~p2 착수 안내). 테스트 감지는 루트 indicator(pyproject는 pytest 섹션 있을 때만) → 없으면 하위 `test_*.py`/`*_test.py` 재귀(`_find_nested_test_file`). entrypoint 후보에서 test 파일 제외. Markdown+JSON 출력. `--json`/`--out DIR` 지원 | Master_Blueprint.md §0 |
| `scripts/af_symbols.py` | `af symbols <경로>` — 외부 Python/C# 프로젝트의 코드 심볼 인덱스를 `<경로>/.af_index/symbols.md`에 생성. LLM/네트워크 없음, deterministic. 새 AST 로직 없이 `codebase_symbols.build()` 재사용(mkdir 전 content 계산 → self-indexing 방지). 상대경로는 `af.py` `_forward_args()`가 호출 cwd 기준 절대경로로 변환 | Master_Blueprint.md §0 |
| `scripts/review_consensus.py` | finding-level 증거수집기 (S4+S5, LLM 미호출). `cr_findings.json`의 ACCEPT/ACCEPT★ finding마다 surrounding_code·callers·callees(AST 1-hop)·tests를 수집해 `cr_evidence.json` 생성. af-cross-review Step 6가 이 증거를 기반으로 합의 판정(ACCEPT/REJECT/UNVERIFIED). 프로바이더 중립(INV-2). | Master_Blueprint.md §0 |
| `core/bootstrap_roles.py` | 프로젝트 계획 부트스트랩 에이전트. **규모 인지 분해(B안, 2026-06-20)**: `plan()`에 `decomposition_strength` additive 파라미터 — `route["required_stages"]`에 `research`·`design` 둘 다 부재 시 `minimal`(역할/모듈 최소화 프롬프트), 아니면 `standard`(기존 director 프롬프트, 바이트 동일). Tier3는 Floor2가 design 강제→항상 standard. `_ensure_qa_role` skip은 `minimal AND merge_mode∈{never,manual}` 교집합만(auto_policy는 QA 강제 유지). merge_mode는 `dogfood.py:1774` `route["_merge_mode"]` 주입으로 도달. last_updated: 2026-06-20 | Master_Blueprint.md §0 |
| `core/builder.py` | 스킬 코드 생성 샌드박스 | Master_Blueprint.md §0 |
| `core/config_paths.py` | 경로 상수 중앙화 | Master_Blueprint.md §0 |
| `core/output_paths.py` | ad-hoc 새 제품/수정 출력 격리 (O-S1, 2026-06-22; in-place 복원 개정) — 일반 폴더는 cwd 그대로 in-place(INV-O3, 기존 프로젝트 수정·분석 보존), AF 소스 repo 안 실행 시에만 `<base_dir>/projects/<slug>` 로 graceful 리다이렉트(INV-O2, 에러 없이 오염 격리). `_is_within`(normcase+realpath, Windows 케이스 비민감)로 BASE_DIR 하위 판정. explicit override(`--workspace`)는 최우선(INV-O5). dogfood worktree 모델은 미적용(INV-O4). 설계: `docs/2026-06-18-product-output-isolation-design.md`. | Master_Blueprint.md §0 |
| `core/knowledge/note.py` | 자가진화 지식 도서관 STAGE 1 (2026-06-23) — 내구성 지식 노트 단일 타입(frontmatter 계약 SSOT). `to_md`/`from_md` round-trip(json.dumps 스칼라/links 인코딩=콜론·따옴표 안전, JSON⊂YAML Obsidian 호환). `new_note()` 작성 헬퍼=author/source_machine(`socket.gethostname()`)/created_commit(`git rev-parse --short`)/created_at/id 자동 스탬프. id 네임스페이스 `{type}/{machine}-{micro시각}-{rand}-{slug}.md`(마이크로초+6자 rand 무충돌 INV-K11, Windows 안전 §12.9). `scope`(기본 project, D12 seam)/`visibility`(기본 private, D11 seam)는 데이터 seam일 뿐 enforcement 코드 0건(INV-K6). 설계: `docs/2026-06-23-knowledge-library-evolution-design.md`. | Master_Blueprint.md §0 |
| `core/knowledge/distill.py` | 지식 도서관 STAGE 2 (2026-06-23) — 세션 raw events → 증류 KnowledgeNote (provider-neutral). `mask_secrets`(sk-/ghp_/xox/AKIA/Bearer/PEM/라벨=값 → [REDACTED], 정밀참조 보존) → `extract_precise_refs`(commit/file:line/INV명 verbatim·순서·중복제거, INV-K5) → `control_plane_llm.generate_json` 증류(INV-K4 멀티프로바이더, 지연 싱글턴 `_get_distill_llm`) → 본문 렌더(출력도 마스킹) → `new_note`. raw 포인터 `{originating_pc, session_file, line}`(§3.3). LLM 의존성 주입(테스트). LLM 실패해도 정밀참조+포인터로 노트 생성. **S2-3 배선 완료(2026-06-23)**: `session_adapter._distill_to_vault`가 두 발화점(`:583` codex finalize·`:691` claude/gemini hook SessionEnd/PreCompact)에서 호출, vault=`repo_root/docs/wiki/knowledge`(INV-K1). 설계 §5 STAGE2. | Master_Blueprint.md §0 |
| `core/knowledge/retrieve.py` | 지식 도서관 STAGE R (2026-06-25) — `af knowledge search` read-only 검색 엔진. 순수 Python 결정론 sparse (임베딩 0, INV-R1). `load_notes`(vault_root glob `**/*.md`, 관용 frontmatter 3종 파싱·파싱실패도 본문 포함 INV-R3) + `score_notes`(용어 빈도 가중합 title=3/desc=2/정밀참조섹션=2/본문=1 + 파일 exact=5/basename=3, tie-break created_at desc→path INV-R5) + `format_results`(사람용 표+`--json`). `extract_precise_refs` SSOT 재사용(INV-R2). write/create/delete 경로 0(INV-R4 grep 테스트). vault=`<repo_root>/docs/wiki/knowledge`(절대경로 하드코딩 금지). 두 진입점: `agent_launcher.py` + `run_factory_cli._STAGE1_DISPATCH["knowledge"]`. last_updated: 2026-06-25 | Master_Blueprint.md §0 |
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
| `core/fsa_loop.py:1-540` | FSA 에스컬레이션 루프 (ISE 파이프라인, 5사이클 제한). `run_mission(..., runtime_workspace=None)`로 Git/user 작업 범위와 `.af`/runner state 범위를 분리. B2: INFRA 실패(`classify_failure==INFRA`) 시 rollback 전 즉시 return — AUTH_EXPIRED 등 100+ 재시도 차단. | Master_Blueprint.md §0 |
| `core/git_manager.py` | 워크스페이스 git 연산 | Master_Blueprint.md §0 |
| `core/hooks/event_bus.py` | 훅 라이프사이클 버스 | Master_Blueprint.md §0 |
| `core/hooks/skill_self_evolution.py` | 주기적 스킬 품질 감사 | Master_Blueprint.md §0 |
| `core/hooks/code_review_doc.py` | 실행 후 자동 코드 리뷰 + 문서 업데이트 | Master_Blueprint.md §0 |
| `core/hooks/guardrails.py` | 실행 가드레일 | Master_Blueprint.md §0 |
| `core/ingestion_pipeline.py` | 문서 인덱싱 파이프라인 | Master_Blueprint.md §0 |
| `core/interactive_chat.py` | 대화형 PDCA 모드 (autosave/resume). 내장 슬래시 명령 `/output <경로>` 로 결과 저장 폴더(`self.workspace`)를 세션 중 변경 — 매 턴 `_run_single_turn`/`_run_project_turn` 가 `self.workspace` 를 read 해 runner/factory.run 으로 전달하므로 즉시 반영(배포 동등성). 프로바이더 무관(AF 상위 레이어). | Master_Blueprint.md §0 |
| `core/ise_loop.py` | 무한 자가진화 루프 | Master_Blueprint.md §0 |
| `core/llm_engine.py` | LLM API 호출 엔진 | Master_Blueprint.md §0 |
| `core/manager.py` | 에이전트 생성·로드 | Master_Blueprint.md §0 |
| `core/memory_system/facade.py` | 메모리 단일 진입점 | Master_Blueprint.md §0 |
| `core/message_broker.py` | TCP/인메모리 메시지 브로커 | Master_Blueprint.md §0 |
| `core/model_router.py` | CLI 프로바이더 선택 | Master_Blueprint.md §0 |
| `core/policy_runtime.py` | 정책 런타임 래퍼 | Master_Blueprint.md §0 |
| `core/project_mailbox.py` | 파일 기반 에이전트 간 메시지함 | Master_Blueprint.md §0 |
| `core/project_pipeline.py` | Phase1(문서)+Phase2(실행) 파이프라인. **F15**: `runtime_workspace`로 `.checkpoint/`, `runtime/warnings/`, strategy ledger, orchestrator `runs/data/artifacts`를 사용자 workspace와 분리. **Target workspace fix (2026-06-21)**: `prepare_brief()`가 `project_brief["target_path"] = target_workspace`를 보존하고, `prepare_documents()`는 상대 `target_path`도 대상 workspace 기준으로 `doc_root` 해석. **P2 C1**: `ResearchGateBlocked` + `_verify_domain_spec()` + `_save_specs()` + `_coverage_blocked()`. **P2 C3+C4**: `_load_evidence`, `_save_adr()`, `_save_traceability()` (원자 write, Path 반환, planning_files 추가). **P3 D1**: `_save_specs()` → list 반환, spec content → `project_brief["domain_specs_summary"]` 주입(generate_work_items 호출 전), _spec_paths → planning_files 추가. **P3 D3**: `research_evidence.research_plan` → `project_brief` 주입 (domain 감지용, None-guard 포함). **P5**: `prepare_documents()` 내 `generate_work_items()` 직전 `ChangeImpactProfiler().profile()` 호출 → `project_brief["blast_radius"]` 주입 (LLM brief에 blast_radius 미포함 시 git-diff+board 휴리스틱으로 보완, 배포 동등성 보장). **Q-S4(2026-06-19)**: `prepare_documents()` GoalContract 생성 직후 `project_brief`의 QA 필드(`observable_goal`/`golden_example`/`test_seam`) → `GoalEntry`(QA-OBS/QA-GEX/QA-SEAM) 흡수. `golden_example`은 `expected_output` 설정(INV-Q2 연결). `qa_provenance` dict로 provenance 태깅. last_updated: 2026-06-21 | Master_Blueprint.md §0 |
| `core/spec_generator.py` | **P2 C2**: 포커 5종 명세. **P2 C3**: `AdrGenerator.generate()` — evidence claims/sources 기반 ADR 생성, LLM 실패 시 fallback (fallback은 LLM 호출 후만 적용). **P2 C4**: `TraceabilityGenerator.generate()` — claims=[] 시 `""` 반환, 휴리스틱 claim↔spec↔task 매핑 MD 표. `_call_llm_raw()` 실패 시 `""` (sentinel 명확화). 저장 위치: ADR=`docs/decisions/<slug>-rule-baseline.md`, trace=`docs/research/<slug>-traceability.md` | Master_Blueprint.md §0 |
| `core/project_task_board.py` | 태스크 보드 상태 관리 + `.todo.md` 동기화 훅 | Master_Blueprint.md §0 |
| `core/providers/cli.py` | CLI 프로바이더 실행 + 진행 표시. **F10**: `_collect_git_context()` — git HEAD/branch/log/status 수집 후 `_compose_prompt()`의 `[Git State]` 섹션으로 gemini/claude/codex_cli 3개 provider에 자동 주입. **sandbox 후처리**: `_apply_sandbox_mode()`가 `build_cli_command()` 최종 `return cmd` 직전에 완성 argv를 받아 `sandbox_enabled()` 값에 따라 codex는 `--sandbox danger-full-access`(off 시), gemini는 `--sandbox` 제거(off 시, `--approval-mode yolo` 보존 — INV-S7 hang 방지) | Master_Blueprint.md §0 |
| `core/sandbox_config.py` | sandbox 활성 여부 SSOT. 우선순위: env `AF_SANDBOX` > `~/.af/sandbox.json` > 플랫폼 기본(Windows=False, 그 외=True). `set_sandbox_enabled()`는 `~/.af/sandbox.json` write-through. `core/providers/cli.py`의 `_apply_sandbox_mode()`가 이를 읽어 provider argv를 후처리. | Master_Blueprint.md §0 |
| `core/providers/session_adapter.py` | CLI 세션 hook 설정·연속성 브리지. **Phase D**: `_write_claude_settings` 본문을 `locked_file(timeout=5)` wrap, `prepare_cli_session`에 `TimeoutError` catch (settings 미작성 후 계속 진행). **Hook Unicode hardening**: hook payload JSON 저장/출력을 ASCII-safe로 escape하고 lone surrogate를 sanitize. **STAGE2 S2-3(2026-06-23)**: `_distill_to_vault(events, repo_root, provider_id)` — `run_bridge` 반환 events(pop)를 증류해 `repo_root/docs/wiki/knowledge`에 best-effort 기록(`finalize_cli_session` codex + `handle_hook_event` SessionEnd/PreCompact, INV-K4 parity). | Master_Blueprint.md §0 |
| `core/provider_detect.py` | 4-state CLI 프로바이더 감지 + 1h 디스크 캐시 + AF_SKIP_PROVIDER 처리. **RATE_LIMITED 상태 추가(2026-06-10)**: `mark_rate_limited()` + `detect_rate_limit_signal()` + `_apply_rate_limit_override()`로 usage limit 사후 캐시 학습 → fan_out 자동 제외 + 노티. CLI `--mark-rate-limited --until`. force_refresh 시에도 미래 until이면 RATE_LIMITED 유지. ThreadPool race condition 수정. | Master_Blueprint.md §0 |
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
| `core/skill_quality_gate.py` | 스킬 품질 게이트 (Quality Plane) — **shadow delta 게이트(2026-06-10)**: baseline 경로 정규화(디렉터리→skill.py 파일) + `_shadow_not_regressed()` + `MIN_SHADOW_CASES=3`. delta>0일 때만 publish(무변화/퇴화 차단). `GateResult.quality_delta` 반환. knowledge skill early-return + auto_register 지원 | Master_Blueprint.md §0 |
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
| `core/work_item_generator.py` | LLM 기반 work-item 생성 + chained refinement. **Target path fix (2026-06-21)**: `project_brief["target_path"]`가 상대경로이면 process CWD/AF 루트가 아니라 `workspace` 기준으로 `doc_root`를 계산. **Phase E (C-3stages 병렬화)**: `TOTAL_BUDGET=600s`, `STAGE_BUDGET{1:90/2:400/3:110}`. `_build_full_run_id` doc_type별 격리. `_exec_stage2` (ThreadPoolExecutor×2 + `cf.wait(ALL_COMPLETED)`). `_extract_section_outline` → tasks prev_spec_outline 전달. 텔레메트리 → `write_initial_record`. **v3.1 (2026-05-11)**: `_GRACE_SEC=5`. `_exec_stage1`(plan+EpisodeHints) / `_exec_stage3`(spec_outline+tasks) 신설. `_generate_and_refine` `deadline` + refine loop deadline guard (F1). `_extract_section_outline` mismatch→`""` (F9). `_exec_stage2` `deadline=` 전달. Stage3 진입 전 `time.sleep(_GRACE_SEC)` (R7). **B-1 (2026-05-21)**: `_inline(value, limit)` sanitizer(`\s+→" "`, `\n##` 분리 방지) + `_skill_gap_bullets(brief, limit)` list[dict] formatter + `_structured_evidence_block(brief)` — structured evidence 3필드(required_capabilities/verification_focus/skill_gap_hypotheses)를 fallback plan/spec/design `## Evidence` 내부 sub-bullet으로 보존. 새 `##` 헤더 신설 없음(`_extract_section_outline` count=12 회귀 방지). **B-1 후행 (2026-05-21)**: `_generate_feature_plan`/`_generate_feature_spec`/`_generate_implementation_design` LLM 프롬프트 Rules에 structured evidence 명시 — required_capabilities=스킬조달신호, verification_focus=Evidence 하위 검증기준, skill_gap_hypotheses=reuse/enhance/forge계획신호, 새 ## 섹션 금지. **Q-S4(2026-06-19)**: `stage_router.run()` 후 `_qa_*` sentinel keys pop → `project_brief` in-place 업데이트(test_seam→deliverables 승격 INV-Q3 경로 C). last_updated: 2026-06-21 | Master_Blueprint.md §0 |
| `core/cli_session_cleanup.py` | `.af_runtime/cli_sessions/` 하위 30일 초과 CLI 세션 파일 TTL 정리 (Phase A, v2 finding #2). **v3.1 R8**: 디렉토리 cleanup 시 dir mtime 대신 자식 파일 max mtime 사용 (POSIX dir mtime 의미 불일치 수정). | Master_Blueprint.md §0 |
| `core/work_item_telemetry.py` | work-item 생성 텔레메트리 — T1 retry 횟수 atomic JSON 기록 (Phase A). **simplify**: `write_initial_record(workspace, slug, results)` 신규 (초기 dump, locked_file + atomic write). **v3.1 F7**: 경로 `workspace_runtime_dir(workspace) / "work_item_telemetry"` (컨벤션 통일). | Master_Blueprint.md §0 |
| `core/requirement_llm.py` | LLM 요구사항 분석 + 마크다운 문서 생성. **Phase C**: `return_usage=False` 옵션, `execute_document_prompt` 응답에 `elapsed_sec`+`usage_tokens` 추가. **simplify**: `_make_usage(prompt_t, completion_t)` 헬퍼 추출 (3× 인라인 중복 제거). **v3.1 F2**: `_call_google/openai/anthropic_api`에 `timeout_sec: int = 120` 추가; google → ThreadPoolExecutor manual + `fut.result(timeout=)`; openai → `client.with_options(timeout=)`; anthropic → `urlopen(timeout=timeout_sec)`. `execute_document_prompt` 3개 API 호출에 `timeout_sec=` 전달. | Master_Blueprint.md §0 |
| `core/work_item_parser.py` | 편집된 마크다운 재파싱 | Master_Blueprint.md §0 |
| `core/control/supervisor.py` | 유지보수 감독 루프 | Master_Blueprint.md §0 |
| `core/agent_reservation.py` | agent reservation | Master_Blueprint.md §0 |
| `core/capability_intent.py` | capability intent | Master_Blueprint.md §0 |
| `core/clarification.py` | clarification. **Q-S4(2026-06-19)**: `merge_clarification()`에 `elif not category and q.get("output_field"):` 분기 추가 — YAML 질문(output_field 기반)의 답을 `enriched[output_field]`에 저장 + `test_seam` 이면 `deliverables`에도 승격(INV-Q3 경로 A/B). last_updated: 2026-06-19 | Master_Blueprint.md §0 |
| `core/interview.py` | user-facing deep interview workflow | Master_Blueprint.md §0 |
| `core/research_brief.py` | §17 Step 3 — interview artifact → ResearchBrief; evidence tagger | Master_Blueprint.md §0 |
| `core/spec_compiler.py` | §17 Step 4 — interview + research → CompiledSpec | Master_Blueprint.md §0 |
| `core/premortem.py` | §17 Step 5 — CompiledSpec → repo-aware risks + verification steps | Master_Blueprint.md §0 |
| `core/planner.py` | §17 Step 6 — CompiledSpec + PremortomResult → ExecutablePlan. P2(2026-05-25): `_build_implementation_steps`가 core/*.py scope item에 `Master_Blueprint.md`를 artifacts에 자동 추가 — Blueprint 동기화 allowlist 연동. 2026-05-27: `implementation_steps(plan)` 헬퍼 신설 — `id`에 'IMPLEMENT' 포함 step만 필터. 2026-05-27 (advisory): `PlanStep.reference_artifacts` 필드 추가 — research_findings 의 companion test/sibling pattern 경로를 read-only context로 노출(`_references_for_scope_item()` 헬퍼). dogfood `_build_ai_task` 가 "Reference files (read-only ...)" 섹션으로 surface. 2026-05-31: `_build_investigation_steps()`에 R11(scope_file) 연동 — `_extract_scope_file_paths()` 헬퍼로 missing 경로 파싱 후 경로별 "경로 확인" step 생성. **2026-06-07 fix**: 존재확인 command가 `shlex.quote`(셸 인용)로 `python -c` 내부 Python 리터럴을 만들어 셸-특수문자 없는 경로가 따옴표 없이 들어가 NameError로 실패하던 버그를 `repr()`로 교정(greenfield light run false-negative "pipeline blocked" 해소). 2026-05-31: R12(stale_test) 연동 — `_extract_stale_test_paths()` 헬퍼로 stale 파일→`tests/test_<stem>.py` 경로 변환, "테스트 작성" investigation step 생성. 2026-06-01: R16(complexity) 연동 — `_extract_complexity_pairs()` 헬퍼 + complexity investigation branch. **risk ID 계약 정리**: `_is_assumption_risk()`를 category-only로 축소(brittle `[5,20)` ID-레인지 제거 — 신규 fixed detector 오분류 방지), `pattern_consistency`(R10) 전용 investigation branch 신설(레인지 제거로 인한 R10 step 누락 회귀 차단). 2026-06-01: R17(nesting_depth) 연동 — `_extract_nesting_depth_pairs()` 헬퍼 + nesting_depth investigation branch(R16 패턴 미러, 구현 전 "중첩 깊은 함수 검토" step 생성). last_updated: 2026-06-07 | Master_Blueprint.md §0 |
| `core/dogfood.py` | §17 Step 7~16 — Dogfood state machine + worktree isolation + auto-merge lifecycle. 14-phase pipeline (ISOLATE/FINALIZE/MERGE 추가). DogfoodState 3-path 분리(source/worktree/runtime), MergePolicy 정책 게이트, prepare_isolated_worktree() 1-retry, finalize_dogfood_result(), merge_dogfood_branch() crash recovery+reset--merge. P1(2026-05-25): IMPLEMENT no-op guard — 모든 steps가 commands=[] (AI executor 미연결)이면 BLOCKED. P3(2026-05-25): finalize_dogfood_result() selective staging — plan allowlist(artifacts+tests_required) 교집합만 stage; 나머지는 scope_violations로 기록. P4(2026-05-26): dogfood shell/git subprocess env + decoding을 UTF-8로 고정. P0(2026-05-26): run_all strict_contract, phase_trace.jsonl, RunBudget accounting, pre-IMPLEMENT static smoke 추가. R-PHASE(2026-05-26): _run_research_phase stub→실 구현 — scope .py 파일 + companion test 파일 읽기 → evidence bundle {local_refs:[...]}. DogfoodState.research_path 신규. S1-완료계약(2026-06-18): `DogfoodState.goal_contract: GoalContract | Master_Blueprint.md §0 |
| `core/completion_contract.py` | 완료 계약 데이터 계층 — "생성=완료" 패턴 A 차단. acceptance criteria를 검증 가능한 골로 모델링하고 실행 증거로 판정. **S1(2026-06-18)**: 구조체 + 직렬화만(하니스 실행은 S2 예정). `GoalContract.is_done()`=모든 골 VERIFIED/CANNOT_VERIFY여야 done(빈 계약 불가, INV-A). `from_dict(to_dict(x))==x` round-trip. 생성 SSOT는 `project_pipeline.prepare()`(S3), `DogfoodState.goal_contract`는 persist 채널. **Q-S1(2026-06-19)**: `Provenance` 타입(`user`/`research`/`default`), `GoalEntry` 3개 additive 필드(`scenario`/`expected_output`/`provenance`), `TestManifest` 신규(`required_tools`/`required_env`/`seam_requirements`/`provenance`), `GoalContract.manifest: TestManifest | Master_Blueprint.md §0 |
| `core/qa_report.py` | QA 리포트 렌더러 (Q-S5, 2026-06-19) — `evidence_ledger` dict → 자기완결 HTML 파일. **섹션**: [VERIFIED]/[FAILED]/[CANNOT_VERIFY]/[UNVERIFIED]/[확인 요망]. **INV-Q2**: `provenance=research` 골은 verdict 섹션 외 [확인 요망]에도 동시 표기(거짓 통과 비동기 검출). 외부 CSS/JS 의존 없음. wiring deferred — Q-S4/Q-S6 또는 project_pipeline.py. 설계: `docs/2026-06-18-user-perspective-qa-pipeline-design.md §9`. last_updated: 2026-06-19 | Master_Blueprint.md §0 |
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
| `core/review_runner.py` | review runner (WI-4: `_run_provider` → `execute_cli_chat` 위임. Tier 2 Phase 2: `_extract_vendor_label()` + single-vendor notice. AUTH_EXPIRED 1회 재인증 안내 SSOT) | Master_Blueprint.md §0 |
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
| `core/utils.py` | utils. last_updated: 2026-06-10 (get_external_skill_roots 신설) | Master_Blueprint.md §0 |
| `core/triad.py` | §17 Step 15 — 正反合 Triad 오케스트레이션. 反(Critic) injectable executor + evidence contract 강제 + Critical finding 미해소 시 TriadBlockedError. 合(Architect) injectable executor. | Master_Blueprint.md §0 |
| `core/review_skill_router.py` | §17 Step 17 — Skill-specialized 3-tier review routing. changed-file paths·blast tier·work kind·risk tokens 기반으로 각 review tier의 skill profile을 결정적으로(no LLM) 라우팅. last_updated: 2026-05-25 | Master_Blueprint.md §0 |
| `core/express_router.py` | §17 Step 18 — Express Router. task description → direct/light/full/dogfood 4-경로 결정적 라우팅(no LLM). self-mod 토큰·risk·research·complexity 기반 분류. Windows 경로 정규화. force_route 오버라이드. last_updated: 2026-05-25 | Master_Blueprint.md §0 |
| `core/right_sized_router.py` | RSE 슬라이스1 + Phase 1+2 갱신 — LLM 분류 + 결정적 안전 floor 강제. `classify(task, workspace, *, changed_files)→RouteDecision`. Phase 1: scope=[] → `_classify_empty_scope()`(CoT LLM+0.82 임계+`ROUTE_MARKER_SCOPE_UNCERTAIN` marker); 기존 `_fallback_decision` early-exit 교체. Floor 1: self-mod→isolation≥worktree. Floor 2: Tier3→design+review+cross_review 강제(빈-scope는 changed_files=[] 라 생략 — 안전성은 dispatch INV-5에 위임). `is_light()`: marker 유무로 0.82/0.7 threshold SSOT(외부리뷰#5). `RouteDecision.markers` 신규 필드 + `to_dict()` 갱신. `_build_empty_scope_prompt()`·`_build_prompt()` CoT 구조(Step 1~4 추론 후 JSON — 변동성 감소). last_updated: 2026-06-21 | Master_Blueprint.md §0 |
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

## 코드베이스 구조 (AST)

> Source: scripts/codebase_symbols.py (read-only AST) — 디렉터리별 모듈/심볼

### `(root)`

30 modules · 3 classes · 121 functions

- `af.py` — 0 class / 2 func
- `agent_launcher.py` — 1 class / 9 func
- `agt.py` — 0 class / 1 func
- `antigravity_link.py` — 1 class / 8 func
- `build_exe.py` — 0 class / 2 func
- `cdx.py` — 0 class / 2 func
- `check_rel.py` — 0 class / 1 func
- `demo_runner.py` — 0 class / 1 func
- `end_db.py` — 0 class / 4 func
- `end_git.py` — 0 class / 2 func
- `end_sync.py` — 0 class / 2 func
- `extract_phase3.py` — 0 class / 1 func
- `factory_manager.py` — 0 class / 3 func
- `lm.py` — 0 class / 1 func
- `model_utils.py` — 1 class / 27 func
- `probe_openai.py` — 0 class / 0 func
- `project_orchestrator.py` — 0 class / 6 func
- `repo_shortcuts.py` — 0 class / 3 func
- `run_eval_loop.py` — 0 class / 2 func
- `run_factory_cli.py` — 0 class / 30 func
- `set_utf8.py` — 0 class / 1 func
- `setup-dev.py` — 0 class / 0 func
- `setup_dev.py` — 0 class / 2 func
- `start_db.py` — 0 class / 4 func
- `start_git.py` — 0 class / 2 func
- `start_sync.py` — 0 class / 2 func
- `test_fallback.py` — 0 class / 1 func
- `verify_project_memory.py` — 0 class / 1 func
- `verify_project_memory_quick.py` — 0 class / 1 func
- `version.py` — 0 class / 0 func

### `agents/backend-architect-agent/tools`

1 modules · 1 classes · 4 functions

- `agents/backend-architect-agent/tools/cortex.py` — 1 class / 4 func

### `agents/backend-dev-agent/tools`

5 modules · 1 classes · 5 functions

- `agents/backend-dev-agent/tools/cortex.py` — 1 class / 4 func
- `agents/backend-dev-agent/tools/database_performance_tuning.py` — 0 class / 0 func
- `agents/backend-dev-agent/tools/retrofit_cortex.py` — 0 class / 1 func
- `agents/backend-dev-agent/tools/scalable_api_architecture.py` — 0 class / 0 func
- `agents/backend-dev-agent/tools/zero_downtime_deployment_playbook.py` — 0 class / 0 func

### `agents/calculus-tutor-agent/tools`

1 modules · 1 classes · 4 functions

- `agents/calculus-tutor-agent/tools/cortex.py` — 1 class / 4 func

### `agents/chef-agent/tools`

3 modules · 1 classes · 10 functions

- `agents/chef-agent/tools/core_module.py` — 0 class / 5 func
- `agents/chef-agent/tools/cortex.py` — 1 class / 4 func
- `agents/chef-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `agents/general-assistant-agent/tools`

2 modules · 1 classes · 5 functions

- `agents/general-assistant-agent/tools/cortex.py` — 1 class / 4 func
- `agents/general-assistant-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `agents/himari-test-agent-agent/tools`

1 modules · 1 classes · 4 functions

- `agents/himari-test-agent-agent/tools/cortex.py` — 1 class / 4 func

### `agents/iguro_obanai/tools`

4 modules · 1 classes · 10 functions

- `agents/iguro_obanai/tools/api_security_vetting.py` — 0 class / 2 func
- `agents/iguro_obanai/tools/cortex.py` — 1 class / 4 func
- `agents/iguro_obanai/tools/db_optimizer.py` — 0 class / 2 func
- `agents/iguro_obanai/tools/infrastructure_scaler.py` — 0 class / 2 func

### `agents/japanese-restaurant-master-chef-agent/tools`

9 modules · 2 classes · 32 functions

- `agents/japanese-restaurant-master-chef-agent/tools/core_module.py` — 0 class / 5 func
- `agents/japanese-restaurant-master-chef-agent/tools/cortex.py` — 1 class / 4 func
- `agents/japanese-restaurant-master-chef-agent/tools/edomae_sushi_shikomi_playbook.py` — 0 class / 7 func
- `agents/japanese-restaurant-master-chef-agent/tools/omakase_service_pacing_control.py` — 0 class / 0 func
- `agents/japanese-restaurant-master-chef-agent/tools/perishable_inventory_control.py` — 0 class / 8 func
- `agents/japanese-restaurant-master-chef-agent/tools/precision_knife_techniques.py` — 1 class / 1 func
- `agents/japanese-restaurant-master-chef-agent/tools/retrofit_cortex.py` — 0 class / 1 func
- `agents/japanese-restaurant-master-chef-agent/tools/seasonal_ingredient_procurement.py` — 0 class / 6 func
- `agents/japanese-restaurant-master-chef-agent/tools/seasonal_omakase_inventory_optimization.py` — 0 class / 0 func

### `agents/lilith-agent/tools`

3 modules · 1 classes · 10 functions

- `agents/lilith-agent/tools/core_module.py` — 0 class / 5 func
- `agents/lilith-agent/tools/cortex.py` — 1 class / 4 func
- `agents/lilith-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `agents/marketer-agent/tools`

3 modules · 1 classes · 10 functions

- `agents/marketer-agent/tools/core_module.py` — 0 class / 5 func
- `agents/marketer-agent/tools/cortex.py` — 1 class / 4 func
- `agents/marketer-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `agents/stock-analyst-agent/tools`

1 modules · 1 classes · 4 functions

- `agents/stock-analyst-agent/tools/cortex.py` — 1 class / 4 func

### `agents/system-admin-(uses-run_command-tool)-agent/tools`

3 modules · 1 classes · 10 functions

- `agents/system-admin-(uses-run_command-tool)-agent/tools/core_module.py` — 0 class / 5 func
- `agents/system-admin-(uses-run_command-tool)-agent/tools/cortex.py` — 1 class / 4 func
- `agents/system-admin-(uses-run_command-tool)-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `agents/system-admin-agent/tools`

3 modules · 1 classes · 10 functions

- `agents/system-admin-agent/tools/core_module.py` — 0 class / 5 func
- `agents/system-admin-agent/tools/cortex.py` — 1 class / 4 func
- `agents/system-admin-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `agents/test-agent-agent/tools`

1 modules · 1 classes · 4 functions

- `agents/test-agent-agent/tools/cortex.py` — 1 class / 4 func

### `agents/test-assistant-agent/tools`

1 modules · 1 classes · 4 functions

- `agents/test-assistant-agent/tools/cortex.py` — 1 class / 4 func

### `agents/web-app-specialist-agent/tools`

1 modules · 1 classes · 4 functions

- `agents/web-app-specialist-agent/tools/cortex.py` — 1 class / 4 func

### `artifacts`

1 modules · 0 classes · 10 functions

- `artifacts/db_customization_loader.py` — 0 class / 10 func

### `config`

1 modules · 8 classes · 1 functions

- `config/schema.py` — 8 class / 1 func

### `core`

155 modules · 220 classes · 865 functions

- `core/agent_reservation.py` — 2 class / 0 func
- `core/agent_runner.py` — 2 class / 3 func
- `core/agent_specializer.py` — 1 class / 0 func
- `core/agent_worker.py` — 0 class / 2 func
- `core/approval_gate.py` — 1 class / 7 func
- `core/architect_agent.py` — 0 class / 8 func
- `core/ast_engine.py` — 0 class / 8 func
- `core/ast_memory_hub.py` — 1 class / 0 func
- `core/bootstrap_roles.py` — 1 class / 3 func
- `core/builder.py` — 1 class / 0 func
- `core/capability_intent.py` — 2 class / 5 func
- `core/clarification.py` — 0 class / 7 func
- `core/cli_session_cleanup.py` — 0 class / 1 func
- `core/completion_contract.py` — 7 class / 4 func
- `core/concurrency.py` — 3 class / 0 func
- `core/config_paths.py` — 0 class / 2 func
- `core/consensus_engine.py` — 1 class / 0 func
- `core/context_window_manager.py` — 6 class / 1 func
- `core/control_plane_llm.py` — 1 class / 1 func
- `core/conversation_manager.py` — 3 class / 1 func
- `core/conversation_prompts.py` — 0 class / 4 func
- `core/conversation_room.py` — 4 class / 0 func
- `core/conversation_task_adapter.py` — 1 class / 2 func
- `core/critic_skill_router.py` — 0 class / 3 func
- `core/cross_verification.py` — 3 class / 1 func
- `core/dashboard.py` — 0 class / 7 func
- `core/design_review_utils.py` — 0 class / 19 func
- `core/destructive_guard.py` — 0 class / 7 func
- `core/document_chunker.py` — 2 class / 1 func
- `core/document_index.py` — 4 class / 2 func
- `core/document_policy.py` — 0 class / 3 func
- `core/documentation_policy.py` — 0 class / 20 func
- `core/dogfood.py` — 7 class / 76 func
- `core/dynamic_orchestrator.py` — 1 class / 0 func
- `core/engine_auth.py` — 0 class / 9 func
- `core/escalation_decision_report.py` — 0 class / 7 func
- `core/escalation_evaluator.py` — 3 class / 6 func
- `core/evaluator.py` — 1 class / 0 func
- `core/evolution_ledger.py` — 2 class / 0 func
- `core/evolution_types.py` — 2 class / 0 func
- `core/executor.py` — 0 class / 1 func
- `core/express_router.py` — 1 class / 4 func
- `core/external_skill_candidate_importer.py` — 0 class / 19 func
- `core/external_skill_source_ids.py` — 0 class / 4 func
- `core/external_skill_sources.py` — 8 class / 10 func
- `core/failure_classifier.py` — 1 class / 1 func
- `core/file_io.py` — 0 class / 8 func
- `core/file_lock.py` — 0 class / 2 func
- `core/fsa_loop.py` — 1 class / 1 func
- `core/git_manager.py` — 1 class / 1 func
- `core/hashline_editor.py` — 1 class / 0 func
- `core/implementation_language_policy.py` — 0 class / 5 func
- `core/ingestion_pipeline.py` — 1 class / 0 func
- `core/install_candidate_utils.py` — 0 class / 6 func
- `core/intent.py` — 1 class / 0 func
- `core/interactive_chat.py` — 2 class / 8 func
- `core/interview.py` — 0 class / 7 func
- `core/ise_analyzer.py` — 2 class / 0 func
- `core/ise_loop.py` — 1 class / 0 func
- `core/ise_redesigner.py` — 1 class / 0 func
- `core/ise_stall_detector.py` — 1 class / 0 func
- `core/ise_strategy_ledger.py` — 2 class / 0 func
- `core/knowledge_skill.py` — 1 class / 4 func
- `core/langchain_adapter.py` — 3 class / 0 func
- `core/lineage_ledger.py` — 2 class / 2 func
- `core/llm_engine.py` — 1 class / 6 func
- `core/lsp_bridge.py` — 1 class / 0 func
- `core/manager.py` — 2 class / 0 func
- `core/mcp_adapter.py` — 2 class / 4 func
- `core/memory.py` — 0 class / 6 func
- `core/message_broker.py` — 1 class / 2 func
- `core/model_router.py` — 1 class / 4 func
- `core/nightly_state.py` — 2 class / 12 func
- `core/onboarding_wizard.py` — 1 class / 5 func
- `core/output_paths.py` — 0 class / 3 func
- `core/parallel_critique.py` — 3 class / 0 func
- `core/pdca_commands.py` — 1 class / 4 func
- `core/pdca_state.py` — 4 class / 0 func
- `core/pipeline_quality.py` — 3 class / 0 func
- `core/plan_verifier.py` — 2 class / 0 func
- `core/planner.py` — 2 class / 18 func
- `core/policy.py` — 0 class / 4 func
- `core/policy_runtime.py` — 1 class / 2 func
- `core/premortem.py` — 3 class / 17 func
- `core/project_init.py` — 0 class / 2 func
- `core/project_mailbox.py` — 0 class / 11 func
- `core/project_pipeline.py` — 4 class / 1 func
- `core/project_task_board.py` — 0 class / 35 func
- `core/provider_detect.py` — 2 class / 17 func
- `core/qa_report.py` — 0 class / 9 func
- `core/registry.py` — 1 class / 0 func
- `core/registry_manager.py` — 1 class / 2 func
- `core/request_router.py` — 1 class / 0 func
- `core/requirement_llm.py` — 1 class / 12 func
- `core/research_brief.py` — 1 class / 6 func
- `core/research_engine.py` — 1 class / 13 func
- `core/research_router.py` — 3 class / 2 func
- `core/research_verifier.py` — 2 class / 0 func
- `core/researcher.py` — 1 class / 0 func
- `core/retrieval_router.py` — 3 class / 0 func
- `core/review_bundle.py` — 0 class / 17 func
- `core/review_report.py` — 4 class / 0 func
- `core/review_runner.py` — 0 class / 15 func
- `core/review_skill_router.py` — 3 class / 4 func
- `core/right_sized_router.py` — 1 class / 12 func
- `core/role_decomposer.py` — 0 class / 6 func
- `core/rubric_compiler.py` — 3 class / 0 func
- `core/run_budget.py` — 1 class / 2 func
- `core/runner.py` — 1 class / 0 func
- `core/sandbox_config.py` — 0 class / 2 func
- `core/security_guard.py` — 0 class / 4 func
- `core/security_scanner.py` — 0 class / 1 func
- `core/semantic_embedder.py` — 1 class / 0 func
- `core/setup_wizard.py` — 0 class / 31 func
- `core/skill_autodiscover.py` — 1 class / 2 func
- `core/skill_cache.py` — 2 class / 0 func
- `core/skill_context_config.py` — 1 class / 2 func
- `core/skill_creator.py` — 0 class / 22 func
- `core/skill_enricher.py` — 0 class / 7 func
- `core/skill_eval_harness.py` — 5 class / 20 func
- `core/skill_evolution_bus.py` — 1 class / 0 func
- `core/skill_evolution_controller.py` — 1 class / 0 func
- `core/skill_evolution_safety.py` — 0 class / 2 func
- `core/skill_feedback.py` — 3 class / 0 func
- `core/skill_forge.py` — 3 class / 0 func
- `core/skill_loader.py` — 4 class / 0 func
- `core/skill_metadata.py` — 3 class / 4 func
- `core/skill_metadata_adapter.py` — 0 class / 26 func
- `core/skill_pack_bootstrapper.py` — 1 class / 0 func
- `core/skill_preflight.py` — 2 class / 6 func
- `core/skill_procurer.py` — 1 class / 14 func
- `core/skill_promotion.py` — 2 class / 4 func
- `core/skill_quality_gate.py` — 2 class / 0 func
- `core/skill_registry.py` — 1 class / 12 func
- `core/skill_retrieval_engine.py` — 3 class / 0 func
- `core/skill_spec_synthesizer.py` — 2 class / 4 func
- `core/spec_compiler.py` — 1 class / 6 func
- `core/spec_generator.py` — 3 class / 1 func
- `core/swarm_council.py` — 1 class / 1 func
- `core/synergy_runner.py` — 0 class / 0 func
- `core/template_input.py` — 0 class / 1 func
- `core/terminal_bridge.py` — 1 class / 2 func
- `core/terminal_visualizer.py` — 4 class / 3 func
- `core/text_integrity.py` — 2 class / 9 func
- `core/tool_runtime.py` — 1 class / 0 func
- `core/triad.py` — 5 class / 5 func
- `core/utils.py` — 0 class / 56 func
- `core/warning_overrides.py` — 0 class / 6 func
- `core/warning_registry.py` — 2 class / 5 func
- `core/warning_stats.py` — 2 class / 5 func
- `core/watchdog.py` — 2 class / 0 func
- `core/web_search.py` — 0 class / 4 func
- `core/work_item_generator.py` — 1 class / 33 func
- `core/work_item_parser.py` — 0 class / 7 func
- `core/work_item_telemetry.py` — 0 class / 2 func

### `core/checkpoint`

3 modules · 3 classes · 3 functions

- `core/checkpoint/__init__.py` — 0 class / 0 func
- `core/checkpoint/canonical.py` — 1 class / 1 func
- `core/checkpoint/storage.py` — 2 class / 2 func

### `core/continuity`

4 modules · 1 classes · 13 functions

- `core/continuity/__init__.py` — 0 class / 0 func
- `core/continuity/manifest_store.py` — 1 class / 1 func
- `core/continuity/resume_brief.py` — 0 class / 10 func
- `core/continuity/runtime_paths.py` — 0 class / 2 func

### `core/control`

19 modules · 39 classes · 10 functions

- `core/control/__init__.py` — 0 class / 0 func
- `core/control/change_impact.py` — 2 class / 0 func
- `core/control/context_scanner.py` — 1 class / 1 func
- `core/control/continuity_snapshot.py` — 2 class / 0 func
- `core/control/execution_policy.py` — 2 class / 0 func
- `core/control/intake.py` — 2 class / 0 func
- `core/control/issue_context.py` — 2 class / 0 func
- `core/control/lifecycle_bridge.py` — 2 class / 0 func
- `core/control/maintenance_pipeline.py` — 1 class / 0 func
- `core/control/maintenance_state.py` — 2 class / 0 func
- `core/control/question_router.py` — 6 class / 3 func
- `core/control/regression_gate.py` — 1 class / 0 func
- `core/control/rollback.py` — 2 class / 0 func
- `core/control/run_ledger.py` — 2 class / 0 func
- `core/control/stage_artifacts.py` — 6 class / 0 func
- `core/control/stage_router.py` — 1 class / 6 func
- `core/control/supervisor.py` — 1 class / 0 func
- `core/control/verdicts.py` — 3 class / 0 func
- `core/control/work_kind.py` — 1 class / 0 func

### `core/events`

2 modules · 4 classes · 3 functions

- `core/events/__init__.py` — 0 class / 0 func
- `core/events/run_event.py` — 4 class / 3 func

### `core/hooks`

12 modules · 16 classes · 15 functions

- `core/hooks/base.py` — 2 class / 0 func
- `core/hooks/checkpoint.py` — 1 class / 0 func
- `core/hooks/code_review_doc.py` — 1 class / 0 func
- `core/hooks/context_fork.py` — 1 class / 4 func
- `core/hooks/design_review_hook.py` — 1 class / 2 func
- `core/hooks/event_bus.py` — 1 class / 0 func
- `core/hooks/guardrails.py` — 3 class / 0 func
- `core/hooks/human_interrupt.py` — 1 class / 0 func
- `core/hooks/langsmith_tracing.py` — 2 class / 1 func
- `core/hooks/lsp_check.py` — 1 class / 6 func
- `core/hooks/memory_consolidation.py` — 1 class / 2 func
- `core/hooks/skill_self_evolution.py` — 1 class / 0 func

### `core/knowledge`

4 modules · 3 classes · 28 functions

- `core/knowledge/__init__.py` — 0 class / 0 func
- `core/knowledge/distill.py` — 1 class / 8 func
- `core/knowledge/note.py` — 1 class / 8 func
- `core/knowledge/retrieve.py` — 1 class / 12 func

### `core/memory_system`

16 modules · 32 classes · 26 functions

- `core/memory_system/__init__.py` — 0 class / 0 func
- `core/memory_system/config.py` — 5 class / 4 func
- `core/memory_system/cross_project.py` — 1 class / 0 func
- `core/memory_system/decay.py` — 1 class / 1 func
- `core/memory_system/episode_extractor.py` — 0 class / 4 func
- `core/memory_system/episode_matcher.py` — 1 class / 4 func
- `core/memory_system/facade.py` — 1 class / 2 func
- `core/memory_system/graph_builder.py` — 0 class / 4 func
- `core/memory_system/graph_query.py` — 1 class / 0 func
- `core/memory_system/issue_tracker.py` — 4 class / 0 func
- `core/memory_system/knowledge_forger.py` — 1 class / 1 func
- `core/memory_system/knowledge_injection.py` — 1 class / 0 func
- `core/memory_system/models.py` — 8 class / 3 func
- `core/memory_system/project_lifecycle.py` — 2 class / 0 func
- `core/memory_system/router.py` — 3 class / 1 func
- `core/memory_system/strategy_ledger.py` — 3 class / 2 func

### `core/memory_system/adapters`

9 modules · 8 classes · 2 functions

- `core/memory_system/adapters/__init__.py` — 0 class / 0 func
- `core/memory_system/adapters/ast_hub.py` — 1 class / 0 func
- `core/memory_system/adapters/base.py` — 1 class / 0 func
- `core/memory_system/adapters/continuity.py` — 1 class / 0 func
- `core/memory_system/adapters/core_memory.py` — 1 class / 1 func
- `core/memory_system/adapters/cortex_vector.py` — 1 class / 1 func
- `core/memory_system/adapters/knowledge_graph.py` — 1 class / 0 func
- `core/memory_system/adapters/sync_compyne.py` — 1 class / 0 func
- `core/memory_system/adapters/trace_log.py` — 1 class / 0 func

### `core/providers`

4 modules · 3 classes · 92 functions

- `core/providers/__init__.py` — 0 class / 0 func
- `core/providers/cli.py` — 2 class / 35 func
- `core/providers/registry.py` — 0 class / 21 func
- `core/providers/session_adapter.py` — 1 class / 36 func

### `core/research`

4 modules · 7 classes · 1 functions

- `core/research/__init__.py` — 0 class / 0 func
- `core/research/checklist_merger.py` — 1 class / 0 func
- `core/research/quality_contract.py` — 4 class / 0 func
- `core/research/work_spec.py` — 2 class / 1 func

### `core/synergy`

5 modules · 5 classes · 4 functions

- `core/synergy/__init__.py` — 0 class / 0 func
- `core/synergy/bridge.py` — 2 class / 0 func
- `core/synergy/job.py` — 2 class / 0 func
- `core/synergy/process.py` — 1 class / 2 func
- `core/synergy/tools.py` — 0 class / 2 func

### `projects/gemini_live_edit/artifacts`

1 modules · 0 classes · 1 functions

- `projects/gemini_live_edit/artifacts/live_edit_check.py` — 0 class / 1 func

### `projects/lotto_mobile_web`

1 modules · 0 classes · 0 functions

- `projects/lotto_mobile_web/conftest.py` — 0 class / 0 func

### `projects/lotto_mobile_web/server`

6 modules · 10 classes · 15 functions

- `projects/lotto_mobile_web/server/__init__.py` — 0 class / 0 func
- `projects/lotto_mobile_web/server/app.py` — 1 class / 4 func
- `projects/lotto_mobile_web/server/bootstrap.py` — 0 class / 3 func
- `projects/lotto_mobile_web/server/dependencies.py` — 0 class / 2 func
- `projects/lotto_mobile_web/server/errors.py` — 2 class / 6 func
- `projects/lotto_mobile_web/server/schemas.py` — 7 class / 0 func

### `projects/lotto_mobile_web/server/services`

3 modules · 3 classes · 1 functions

- `projects/lotto_mobile_web/server/services/__init__.py` — 0 class / 0 func
- `projects/lotto_mobile_web/server/services/draw_cache.py` — 2 class / 0 func
- `projects/lotto_mobile_web/server/services/recommendation.py` — 1 class / 1 func

### `projects/lotto_mobile_web/tests/api`

2 modules · 2 classes · 11 functions

- `projects/lotto_mobile_web/tests/api/conftest.py` — 2 class / 6 func
- `projects/lotto_mobile_web/tests/api/test_recommend_endpoint.py` — 0 class / 5 func

### `projects/lotto_mobile_web/tests/frontend`

4 modules · 1 classes · 14 functions

- `projects/lotto_mobile_web/tests/frontend/conftest.py` — 1 class / 6 func
- `projects/lotto_mobile_web/tests/frontend/test_offline_cache_contract.py` — 0 class / 3 func
- `projects/lotto_mobile_web/tests/frontend/test_param_panel_contract.py` — 0 class / 1 func
- `projects/lotto_mobile_web/tests/frontend/test_smoke_render.py` — 0 class / 4 func

### `projects/lotto_pattern_predictor/scripts`

1 modules · 1 classes · 14 functions

- `projects/lotto_pattern_predictor/scripts/run_qa_checks.py` — 1 class / 14 func

### `projects/lotto_pattern_predictor/src`

1 modules · 0 classes · 0 functions

- `projects/lotto_pattern_predictor/src/__init__.py` — 0 class / 0 func

### `projects/lotto_pattern_predictor/src/lotto`

6 modules · 12 classes · 3 functions

- `projects/lotto_pattern_predictor/src/lotto/__init__.py` — 0 class / 0 func
- `projects/lotto_pattern_predictor/src/lotto/analysis.py` — 4 class / 0 func
- `projects/lotto_pattern_predictor/src/lotto/cache_store.py` — 1 class / 2 func
- `projects/lotto_pattern_predictor/src/lotto/exceptions.py` — 5 class / 0 func
- `projects/lotto_pattern_predictor/src/lotto/fetcher.py` — 1 class / 1 func
- `projects/lotto_pattern_predictor/src/lotto/models.py` — 1 class / 0 func

### `projects/lotto_pattern_predictor/tests`

8 modules · 28 classes · 25 functions

- `projects/lotto_pattern_predictor/tests/__init__.py` — 0 class / 0 func
- `projects/lotto_pattern_predictor/tests/test_analysis.py` — 8 class / 3 func
- `projects/lotto_pattern_predictor/tests/test_analyzer.py` — 5 class / 7 func
- `projects/lotto_pattern_predictor/tests/test_cache_store.py` — 8 class / 1 func
- `projects/lotto_pattern_predictor/tests/test_fetcher.py` — 2 class / 6 func
- `projects/lotto_pattern_predictor/tests/test_fetcher_integration.py` — 1 class / 1 func
- `projects/lotto_pattern_predictor/tests/test_models.py` — 1 class / 0 func
- `projects/lotto_pattern_predictor/tests/test_recommender.py` — 3 class / 7 func

### `projects/lotto_predictor_v2/src/lotto`

6 modules · 4 classes · 28 functions

- `projects/lotto_predictor_v2/src/lotto/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto/__main__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto/cli.py` — 0 class / 8 func
- `projects/lotto_predictor_v2/src/lotto/collector.py` — 3 class / 1 func
- `projects/lotto_predictor_v2/src/lotto/recommender.py` — 1 class / 10 func
- `projects/lotto_predictor_v2/src/lotto/report.py` — 0 class / 9 func

### `projects/lotto_predictor_v2/src/lotto/analytics`

2 modules · 1 classes · 9 functions

- `projects/lotto_predictor_v2/src/lotto/analytics/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto/analytics/patterns.py` — 1 class / 9 func

### `projects/lotto_predictor_v2/src/lotto/cache`

2 modules · 2 classes · 0 functions

- `projects/lotto_predictor_v2/src/lotto/cache/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto/cache/store.py` — 2 class / 0 func

### `projects/lotto_predictor_v2/src/lotto_predictor`

2 modules · 0 classes · 1 functions

- `projects/lotto_predictor_v2/src/lotto_predictor/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/__main__.py` — 0 class / 1 func

### `projects/lotto_predictor_v2/src/lotto_predictor/analytics`

2 modules · 2 classes · 7 functions

- `projects/lotto_predictor_v2/src/lotto_predictor/analytics/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/analytics/patterns.py` — 2 class / 7 func

### `projects/lotto_predictor_v2/src/lotto_predictor/backend`

5 modules · 11 classes · 6 functions

- `projects/lotto_predictor_v2/src/lotto_predictor/backend/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/backend/http_client.py` — 2 class / 1 func
- `projects/lotto_predictor_v2/src/lotto_predictor/backend/models.py` — 7 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/backend/serialization.py` — 0 class / 2 func
- `projects/lotto_predictor_v2/src/lotto_predictor/backend/storage.py` — 2 class / 3 func

### `projects/lotto_predictor_v2/src/lotto_predictor/cache`

4 modules · 10 classes · 4 functions

- `projects/lotto_predictor_v2/src/lotto_predictor/cache/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/cache/core.py` — 2 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/cache/json_store.py` — 4 class / 4 func
- `projects/lotto_predictor_v2/src/lotto_predictor/cache/models.py` — 4 class / 0 func

### `projects/lotto_predictor_v2/src/lotto_predictor/collector`

3 modules · 6 classes · 0 functions

- `projects/lotto_predictor_v2/src/lotto_predictor/collector/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/collector/core.py` — 3 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/collector/models.py` — 3 class / 0 func

### `projects/lotto_predictor_v2/src/lotto_predictor/game_logic`

4 modules · 15 classes · 0 functions

- `projects/lotto_predictor_v2/src/lotto_predictor/game_logic/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/game_logic/engine.py` — 2 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/game_logic/errors.py` — 3 class / 0 func
- `projects/lotto_predictor_v2/src/lotto_predictor/game_logic/models.py` — 10 class / 0 func

### `projects/lotto_predictor_v2/tests`

9 modules · 4 classes · 38 functions

- `projects/lotto_predictor_v2/tests/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/tests/conftest.py` — 0 class / 1 func
- `projects/lotto_predictor_v2/tests/test_analytics_integration.py` — 0 class / 5 func
- `projects/lotto_predictor_v2/tests/test_cache_store.py` — 0 class / 7 func
- `projects/lotto_predictor_v2/tests/test_lotto_collector.py` — 3 class / 5 func
- `projects/lotto_predictor_v2/tests/test_patterns.py` — 1 class / 0 func
- `projects/lotto_predictor_v2/tests/test_pyinstaller_e2e.py` — 0 class / 7 func
- `projects/lotto_predictor_v2/tests/test_recommender.py` — 0 class / 5 func
- `projects/lotto_predictor_v2/tests/test_report.py` — 0 class / 8 func

### `projects/lotto_predictor_v2/tests/cache`

6 modules · 2 classes · 29 functions

- `projects/lotto_predictor_v2/tests/cache/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/tests/cache/_fakes.py` — 2 class / 2 func
- `projects/lotto_predictor_v2/tests/cache/test_cache_continuity.py` — 0 class / 6 func
- `projects/lotto_predictor_v2/tests/cache/test_cache_ensure_ready.py` — 0 class / 7 func
- `projects/lotto_predictor_v2/tests/cache/test_cache_reads.py` — 0 class / 8 func
- `projects/lotto_predictor_v2/tests/cache/test_cache_status.py` — 0 class / 6 func

### `projects/lotto_predictor_v2/tests/collector`

5 modules · 7 classes · 2 functions

- `projects/lotto_predictor_v2/tests/collector/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/tests/collector/_fakes.py` — 2 class / 2 func
- `projects/lotto_predictor_v2/tests/collector/test_collector_detect.py` — 1 class / 0 func
- `projects/lotto_predictor_v2/tests/collector/test_collector_failures.py` — 2 class / 0 func
- `projects/lotto_predictor_v2/tests/collector/test_collector_sync.py` — 2 class / 0 func

### `projects/lotto_predictor_v2/tests/fixtures`

2 modules · 0 classes · 1 functions

- `projects/lotto_predictor_v2/tests/fixtures/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/tests/fixtures/mock_responses.py` — 0 class / 1 func

### `projects/lotto_predictor_v2/tests/fixtures/e2e`

2 modules · 0 classes · 0 functions

- `projects/lotto_predictor_v2/tests/fixtures/e2e/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/tests/fixtures/e2e/pyinstaller_samples.py` — 0 class / 0 func

### `projects/lotto_predictor_v2/tests/fixtures/recommender`

2 modules · 0 classes · 8 functions

- `projects/lotto_predictor_v2/tests/fixtures/recommender/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/tests/fixtures/recommender/mock_stats.py` — 0 class / 8 func

### `projects/lotto_predictor_v2/tests/game_logic`

2 modules · 1 classes · 0 functions

- `projects/lotto_predictor_v2/tests/game_logic/__init__.py` — 0 class / 0 func
- `projects/lotto_predictor_v2/tests/game_logic/test_engine.py` — 1 class / 0 func

### `projects/minesweeper-baseline`

1 modules · 3 classes · 14 functions

- `projects/minesweeper-baseline/minesweeper.py` — 3 class / 14 func

### `projects/minesweeper-baseline/src`

2 modules · 3 classes · 9 functions

- `projects/minesweeper-baseline/src/__init__.py` — 0 class / 0 func
- `projects/minesweeper-baseline/src/game_logic.py` — 3 class / 9 func

### `projects/minesweeper-baseline/tests`

3 modules · 0 classes · 25 functions

- `projects/minesweeper-baseline/tests/conftest.py` — 0 class / 0 func
- `projects/minesweeper-baseline/tests/test_game_logic.py` — 0 class / 5 func
- `projects/minesweeper-baseline/tests/test_minesweeper_unit.py` — 0 class / 20 func

### `projects/minesweeper/agents/architect-agent/tools`

9 modules · 1 classes · 17 functions

- `projects/minesweeper/agents/architect-agent/tools/ast_grep.py` — 0 class / 1 func
- `projects/minesweeper/agents/architect-agent/tools/core_module.py` — 0 class / 5 func
- `projects/minesweeper/agents/architect-agent/tools/cortex.py` — 1 class / 3 func
- `projects/minesweeper/agents/architect-agent/tools/file_handler.py` — 0 class / 3 func
- `projects/minesweeper/agents/architect-agent/tools/lsp_hover.py` — 0 class / 1 func
- `projects/minesweeper/agents/architect-agent/tools/mcp_client.py` — 0 class / 1 func
- `projects/minesweeper/agents/architect-agent/tools/mcp_exa_search.py` — 0 class / 1 func
- `projects/minesweeper/agents/architect-agent/tools/memory_pruner.py` — 0 class / 1 func
- `projects/minesweeper/agents/architect-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `projects/minesweeper/agents/logicdeveloper-agent/tools`

9 modules · 1 classes · 17 functions

- `projects/minesweeper/agents/logicdeveloper-agent/tools/ast_grep.py` — 0 class / 1 func
- `projects/minesweeper/agents/logicdeveloper-agent/tools/core_module.py` — 0 class / 5 func
- `projects/minesweeper/agents/logicdeveloper-agent/tools/cortex.py` — 1 class / 3 func
- `projects/minesweeper/agents/logicdeveloper-agent/tools/file_handler.py` — 0 class / 3 func
- `projects/minesweeper/agents/logicdeveloper-agent/tools/lsp_hover.py` — 0 class / 1 func
- `projects/minesweeper/agents/logicdeveloper-agent/tools/mcp_client.py` — 0 class / 1 func
- `projects/minesweeper/agents/logicdeveloper-agent/tools/mcp_exa_search.py` — 0 class / 1 func
- `projects/minesweeper/agents/logicdeveloper-agent/tools/memory_pruner.py` — 0 class / 1 func
- `projects/minesweeper/agents/logicdeveloper-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `projects/minesweeper/agents/uideveloper-agent/tools`

9 modules · 1 classes · 17 functions

- `projects/minesweeper/agents/uideveloper-agent/tools/ast_grep.py` — 0 class / 1 func
- `projects/minesweeper/agents/uideveloper-agent/tools/core_module.py` — 0 class / 5 func
- `projects/minesweeper/agents/uideveloper-agent/tools/cortex.py` — 1 class / 3 func
- `projects/minesweeper/agents/uideveloper-agent/tools/file_handler.py` — 0 class / 3 func
- `projects/minesweeper/agents/uideveloper-agent/tools/lsp_hover.py` — 0 class / 1 func
- `projects/minesweeper/agents/uideveloper-agent/tools/mcp_client.py` — 0 class / 1 func
- `projects/minesweeper/agents/uideveloper-agent/tools/mcp_exa_search.py` — 0 class / 1 func
- `projects/minesweeper/agents/uideveloper-agent/tools/memory_pruner.py` — 0 class / 1 func
- `projects/minesweeper/agents/uideveloper-agent/tools/retrofit_cortex.py` — 0 class / 1 func

### `pyinstaller_hooks`

1 modules · 0 classes · 0 functions

- `pyinstaller_hooks/hook-ast_grep_py.py` — 0 class / 0 func

### `scripts`

60 modules · 9 classes · 503 functions

- `scripts/af_doctor.py` — 1 class / 13 func
- `scripts/af_evolution.py` — 0 class / 4 func
- `scripts/af_knowledge_doctor.py` — 1 class / 9 func
- `scripts/af_ponytail.py` — 0 class / 6 func
- `scripts/af_project_inspect.py` — 0 class / 13 func
- `scripts/af_provider.py` — 0 class / 6 func
- `scripts/af_sandbox.py` — 0 class / 7 func
- `scripts/af_symbols.py` — 0 class / 2 func
- `scripts/agent_model_selector.py` — 0 class / 6 func
- `scripts/blast_radius.py` — 0 class / 7 func
- `scripts/blueprint_updater.py` — 0 class / 28 func
- `scripts/build_knowledge_wiki.py` — 0 class / 5 func
- `scripts/build_llm_wiki.py` — 0 class / 24 func
- `scripts/build_review_bundle.py` — 0 class / 5 func
- `scripts/check_changed_text_integrity.py` — 1 class / 6 func
- `scripts/check_design_pending.py` — 0 class / 6 func
- `scripts/check_model_escalation.py` — 0 class / 2 func
- `scripts/check_pending_review.py` — 0 class / 6 func
- `scripts/check_staged_design_review.py` — 0 class / 12 func
- `scripts/claude_session_bridge.py` — 0 class / 0 func
- `scripts/clean_agents_yaml.py` — 0 class / 1 func
- `scripts/cli_hook_bridge.py` — 0 class / 2 func
- `scripts/code_review_updater.py` — 0 class / 14 func
- `scripts/codebase_symbols.py` — 0 class / 9 func
- `scripts/codex_session_bridge.py` — 0 class / 0 func
- `scripts/design_review_trigger.py` — 0 class / 2 func
- `scripts/design_review_watcher.py` — 0 class / 16 func
- `scripts/destructive_guard_proxy.py` — 0 class / 2 func
- `scripts/enqueue_agent_review.py` — 0 class / 4 func
- `scripts/enqueue_staged_review.py` — 0 class / 11 func
- `scripts/fix_runner_cwm.py` — 0 class / 0 func
- `scripts/gemini_session_bridge.py` — 0 class / 0 func
- `scripts/generate_agents_md.py` — 1 class / 18 func
- `scripts/hook_runner.py` — 0 class / 23 func
- `scripts/import_external_skill_candidates.py` — 0 class / 0 func
- `scripts/install_scheduler.py` — 0 class / 11 func
- `scripts/measure_cot_variability.py` — 0 class / 6 func
- `scripts/measure_goal_overlap.py` — 0 class / 4 func
- `scripts/migrate_registry.py` — 0 class / 2 func
- `scripts/migrate_workitem_e2e.py` — 0 class / 3 func
- `scripts/nightly_summary.py` — 0 class / 3 func
- `scripts/nightly_tick.py` — 0 class / 9 func
- `scripts/project_context_git_sync.py` — 0 class / 5 func
- `scripts/project_context_sync.py` — 0 class / 31 func
- `scripts/refresh_lotto_seed.py` — 0 class / 3 func
- `scripts/replace_react_loop.py` — 0 class / 0 func
- `scripts/review_consensus.py` — 0 class / 7 func
- `scripts/review_gate.py` — 0 class / 28 func
- `scripts/review_metrics_logger.py` — 0 class / 13 func
- `scripts/review_metrics_report.py` — 0 class / 2 func
- `scripts/run.py` — 0 class / 2 func
- `scripts/session_bridge.py` — 1 class / 23 func
- `scripts/sync_claude_memory.py` — 0 class / 14 func
- `scripts/sync_provider_instructions.py` — 0 class / 6 func
- `scripts/sync_skill_registry.py` — 0 class / 11 func
- `scripts/t3_classifier.py` — 2 class / 13 func
- `scripts/t3_skip_report.py` — 0 class / 5 func
- `scripts/test_gap_analyzer.py` — 2 class / 27 func
- `scripts/verify_handoff_checker.py` — 0 class / 4 func
- `scripts/write_resume_brief.py` — 0 class / 2 func

### `skills/ai_funnel_routing`

1 modules · 0 classes · 3 functions

- `skills/ai_funnel_routing/skill.py` — 0 class / 3 func

### `skills/core`

8 modules · 1 classes · 13 functions

- `skills/core/ast_grep.py` — 0 class / 1 func
- `skills/core/cortex.py` — 1 class / 4 func
- `skills/core/file_handler.py` — 0 class / 3 func
- `skills/core/lsp_hover.py` — 0 class / 1 func
- `skills/core/mcp_client.py` — 0 class / 1 func
- `skills/core/mcp_exa_search.py` — 0 class / 1 func
- `skills/core/memory_pruner.py` — 0 class / 1 func
- `skills/core/retrofit_cortex.py` — 0 class / 1 func

### `skills/core_memory`

1 modules · 0 classes · 16 functions

- `skills/core_memory/skill.py` — 0 class / 16 func

### `skills/create_design_system`

1 modules · 0 classes · 3 functions

- `skills/create_design_system/skill.py` — 0 class / 3 func

### `skills/css_styling`

1 modules · 0 classes · 3 functions

- `skills/css_styling/skill.py` — 0 class / 3 func

### `skills/data_visualize`

1 modules · 0 classes · 3 functions

- `skills/data_visualize/skill.py` — 0 class / 3 func

### `skills/domain/langchain`

1 modules · 0 classes · 12 functions

- `skills/domain/langchain/langchain_guidelines.py` — 0 class / 12 func

### `skills/dp`

1 modules · 0 classes · 6 functions

- `skills/dp/skill.py` — 0 class / 6 func

### `skills/eval`

1 modules · 0 classes · 4 functions

- `skills/eval/langsmith_eval.py` — 0 class / 4 func

### `skills/evaluator`

1 modules · 0 classes · 0 functions

- `skills/evaluator/__init__.py` — 0 class / 0 func

### `skills/evaluator/doc_qa`

1 modules · 1 classes · 0 functions

- `skills/evaluator/doc_qa/skill.py` — 1 class / 0 func

### `skills/evaluator/generate_eval_dataset`

1 modules · 0 classes · 12 functions

- `skills/evaluator/generate_eval_dataset/skill.py` — 0 class / 12 func

### `skills/evaluator/summarize_failure`

1 modules · 0 classes · 13 functions

- `skills/evaluator/summarize_failure/skill.py` — 0 class / 13 func

### `skills/evaluator/trace_execution`

1 modules · 0 classes · 10 functions

- `skills/evaluator/trace_execution/skill.py` — 0 class / 10 func

### `skills/forge`

16 modules · 1 classes · 48 functions

- `skills/forge/api_security_vetting.py` — 0 class / 6 func
- `skills/forge/core_module.py` — 0 class / 5 func
- `skills/forge/database_performance_tuning.py` — 0 class / 0 func
- `skills/forge/db_optimizer.py` — 0 class / 6 func
- `skills/forge/edomae_sushi_shikomi_playbook.py` — 0 class / 7 func
- `skills/forge/file_handler.py` — 0 class / 3 func
- `skills/forge/infrastructure_scaler.py` — 0 class / 6 func
- `skills/forge/needs_issue.py` — 0 class / 0 func
- `skills/forge/new_skill.py` — 0 class / 0 func
- `skills/forge/omakase_service_pacing_control.py` — 0 class / 0 func
- `skills/forge/perishable_inventory_control.py` — 0 class / 8 func
- `skills/forge/precision_knife_techniques.py` — 1 class / 1 func
- `skills/forge/scalable_api_architecture.py` — 0 class / 0 func
- `skills/forge/seasonal_ingredient_procurement.py` — 0 class / 6 func
- `skills/forge/seasonal_omakase_inventory_optimization.py` — 0 class / 0 func
- `skills/forge/zero_downtime_deployment_playbook.py` — 0 class / 0 func

### `skills/frontend_ui_ux`

1 modules · 1 classes · 0 functions

- `skills/frontend_ui_ux/skill.py` — 1 class / 0 func

### `skills/generate_image`

1 modules · 0 classes · 3 functions

- `skills/generate_image/skill.py` — 0 class / 3 func

### `skills/gherkin_sdd_authoring`

1 modules · 0 classes · 3 functions

- `skills/gherkin_sdd_authoring/skill.py` — 0 class / 3 func

### `skills/git_master`

1 modules · 1 classes · 0 functions

- `skills/git_master/skill.py` — 1 class / 0 func

### `skills/graphify`

1 modules · 1 classes · 1 functions

- `skills/graphify/skill.py` — 1 class / 1 func

### `skills/hash_edit`

1 modules · 0 classes · 5 functions

- `skills/hash_edit/skill.py` — 0 class / 5 func

### `skills/hashline_edit`

1 modules · 1 classes · 0 functions

- `skills/hashline_edit/skill.py` — 1 class / 0 func

### `skills/hound_librarian`

1 modules · 0 classes · 3 functions

- `skills/hound_librarian/skill.py` — 0 class / 3 func

### `skills/issue_tracker`

1 modules · 0 classes · 5 functions

- `skills/issue_tracker/skill.py` — 0 class / 5 func

### `skills/liability_traceability_design`

1 modules · 0 classes · 3 functions

- `skills/liability_traceability_design/skill.py` — 0 class / 3 func

### `skills/new_skill`

1 modules · 0 classes · 3 functions

- `skills/new_skill/skill.py` — 0 class / 3 func

### `skills/perform_web_design_review`

1 modules · 0 classes · 3 functions

- `skills/perform_web_design_review/skill.py` — 0 class / 3 func

### `skills/react_coding`

1 modules · 0 classes · 3 functions

- `skills/react_coding/skill.py` — 0 class / 3 func

### `skills/research_assistant`

1 modules · 0 classes · 5 functions

- `skills/research_assistant/skill.py` — 0 class / 5 func

### `skills/roi_defense_modeling`

1 modules · 0 classes · 3 functions

- `skills/roi_defense_modeling/skill.py` — 0 class / 3 func

### `skills/state_machine_exception_planning`

1 modules · 0 classes · 3 functions

- `skills/state_machine_exception_planning/skill.py` — 0 class / 3 func

### `skills/stitch_design`

1 modules · 0 classes · 3 functions

- `skills/stitch_design/skill.py` — 0 class / 3 func

### `skills/trigger_rule_design`

1 modules · 0 classes · 3 functions

- `skills/trigger_rule_design/skill.py` — 0 class / 3 func

### `skills/user_flow_optimization`

1 modules · 0 classes · 3 functions

- `skills/user_flow_optimization/skill.py` — 0 class / 3 func

### `skills/zero_integration_parsing_spec`

1 modules · 0 classes · 3 functions

- `skills/zero_integration_parsing_spec/skill.py` — 0 class / 3 func

### `tests`

235 modules · 438 classes · 1996 functions

- `tests/check_models.py` — 0 class / 0 func
- `tests/conftest.py` — 0 class / 4 func
- `tests/run_verify_agent.py` — 0 class / 1 func
- `tests/test_acceptance_gate.py` — 5 class / 6 func
- `tests/test_acceptance_gate_integration.py` — 9 class / 4 func
- `tests/test_af_doctor.py` — 0 class / 27 func
- `tests/test_af_ponytail.py` — 0 class / 9 func
- `tests/test_af_project_inspect.py` — 11 class / 4 func
- `tests/test_af_project_symbols.py` — 4 class / 1 func
- `tests/test_af_provider.py` — 4 class / 1 func
- `tests/test_af_symbols.py` — 4 class / 1 func
- `tests/test_agent_launcher_cli_dispatch.py` — 8 class / 0 func
- `tests/test_agent_model_selector.py` — 4 class / 0 func
- `tests/test_agent_runner_false_success.py` — 2 class / 1 func
- `tests/test_agent_runner_force_provider.py` — 1 class / 1 func
- `tests/test_agent_specializer.py` — 1 class / 2 func
- `tests/test_agent_worker.py` — 0 class / 5 func
- `tests/test_approval_gate_auto_approve.py` — 0 class / 26 func
- `tests/test_approval_gate_block_decision.py` — 0 class / 8 func
- `tests/test_approval_gate_domain_gate.py` — 6 class / 14 func
- `tests/test_approval_gate_domain_review.py` — 0 class / 3 func
- `tests/test_approval_gate_metadata_persistence.py` — 0 class / 6 func
- `tests/test_approval_gate_runtime_workspace.py` — 0 class / 4 func
- `tests/test_architect_agent.py` — 8 class / 2 func
- `tests/test_ast_engine_smoke.py` — 0 class / 8 func
- `tests/test_block_learning.py` — 0 class / 17 func
- `tests/test_blueprint_updater.py` — 0 class / 6 func
- `tests/test_bootstrap_policy_rules.py` — 0 class / 8 func
- `tests/test_build_llm_wiki.py` — 3 class / 0 func
- `tests/test_build_review_bundle.py` — 0 class / 15 func
- `tests/test_builder_cli_fallback.py` — 0 class / 3 func
- `tests/test_builder_multi_pass.py` — 0 class / 2 func
- `tests/test_bulk_enrich_trigger_routing.py` — 1 class / 0 func
- `tests/test_capability_intent.py` — 0 class / 1 func
- `tests/test_check_design_pending.py` — 6 class / 4 func
- `tests/test_check_model_escalation.py` — 0 class / 5 func
- `tests/test_check_pending_review.py` — 1 class / 0 func
- `tests/test_check_staged_design_review.py` — 9 class / 1 func
- `tests/test_cli_providers.py` — 3 class / 31 func
- `tests/test_cli_session_adapter.py` — 0 class / 10 func
- `tests/test_codebase_symbols.py` — 0 class / 26 func
- `tests/test_coding_conventions.py` — 0 class / 7 func
- `tests/test_compact_step2.py` — 4 class / 1 func
- `tests/test_completion_contract.py` — 0 class / 32 func
- `tests/test_context_window_manager.py` — 6 class / 0 func
- `tests/test_conversation_collaboration.py` — 10 class / 0 func
- `tests/test_coverage_gate_hoist.py` — 8 class / 2 func
- `tests/test_cp949_robustness.py` — 0 class / 4 func
- `tests/test_critic_skill_router.py` — 0 class / 17 func
- `tests/test_cross_cli_skill_discovery.py` — 0 class / 23 func
- `tests/test_cross_review_agent_invariants.py` — 0 class / 3 func
- `tests/test_cross_schema.py` — 0 class / 1 func
- `tests/test_decision_report.py` — 0 class / 4 func
- `tests/test_default_context_schema.py` — 2 class / 1 func
- `tests/test_destructive_guard.py` — 0 class / 4 func
- `tests/test_distill_wiring.py` — 1 class / 8 func
- `tests/test_documentation_policy.py` — 0 class / 15 func
- `tests/test_dogfood.py` — 9 class / 142 func
- `tests/test_dogfood_cli.py` — 0 class / 37 func
- `tests/test_dogfood_integration.py` — 0 class / 16 func
- `tests/test_dogfood_isolation.py` — 0 class / 72 func
- `tests/test_dogfood_realignment.py` — 1 class / 6 func
- `tests/test_dynamic_orchestrator_workspace_scope.py` — 8 class / 16 func
- `tests/test_engine_auth_provider_priority.py` — 0 class / 11 func
- `tests/test_enqueue_staged_review.py` — 0 class / 5 func
- `tests/test_escalation_evaluator.py` — 0 class / 11 func
- `tests/test_escalation_evaluator_p4a.py` — 0 class / 8 func
- `tests/test_escalation_policy_yaml_p4a.py` — 0 class / 2 func
- `tests/test_evolution_ledger.py` — 3 class / 1 func
- `tests/test_executor.py` — 0 class / 3 func
- `tests/test_express_router.py` — 0 class / 46 func
- `tests/test_external_skill_candidate_importer.py` — 0 class / 10 func
- `tests/test_external_skill_sources.py` — 0 class / 9 func
- `tests/test_factory_evolution.py` — 0 class / 4 func
- `tests/test_failure_classifier.py` — 0 class / 2 func
- `tests/test_fallback_auto_gen.py` — 0 class / 1 func
- `tests/test_fsa_runtime_workspace.py` — 2 class / 3 func
- `tests/test_gemini_smoke.py` — 0 class / 3 func
- `tests/test_hook_event_bus.py` — 3 class / 2 func
- `tests/test_hook_runner.py` — 0 class / 4 func
- `tests/test_hook_runner_builtins.py` — 0 class / 40 func
- `tests/test_implementation_language_policy.py` — 0 class / 4 func
- `tests/test_inject_review_tasks_e2e_command.py` — 0 class / 4 func
- `tests/test_interactive_chat_output_cmd.py` — 0 class / 11 func
- `tests/test_interview.py` — 0 class / 10 func
- `tests/test_ise_integration.py` — 0 class / 7 func
- `tests/test_ise_provider_awareness.py` — 0 class / 6 func
- `tests/test_key_combos.py` — 0 class / 1 func
- `tests/test_knowledge_distill.py` — 1 class / 17 func
- `tests/test_knowledge_doctor.py` — 0 class / 24 func
- `tests/test_knowledge_note.py` — 0 class / 18 func
- `tests/test_knowledge_retrieve.py` — 9 class / 1 func
- `tests/test_knowledge_skill.py` — 5 class / 3 func
- `tests/test_knowledge_wiki_stage0.py` — 6 class / 0 func
- `tests/test_korean_encoding.py` — 0 class / 1 func
- `tests/test_lineage_ledger.py` — 0 class / 11 func
- `tests/test_llm_doc_gen_p3_p6.py` — 7 class / 0 func
- `tests/test_llm_engine_auto_upgrade_scope.py` — 0 class / 2 func
- `tests/test_llm_wiki_precommit.py` — 0 class / 3 func
- `tests/test_manager.py` — 0 class / 1 func
- `tests/test_midori_skills.py` — 0 class / 2 func
- `tests/test_model_name_normalization.py` — 2 class / 6 func
- `tests/test_nightly_summary.py` — 0 class / 5 func
- `tests/test_nlm_regression.py` — 0 class / 2 func
- `tests/test_omo_env_parse.py` — 0 class / 2 func
- `tests/test_optional_id_calib.py` — 0 class / 13 func
- `tests/test_orchestrator_manifest.py` — 6 class / 2 func
- `tests/test_output_paths.py` — 0 class / 15 func
- `tests/test_pending_review.py` — 0 class / 30 func
- `tests/test_phase10_memory_foundation.py` — 7 class / 1 func
- `tests/test_phase11_adapters.py` — 6 class / 1 func
- `tests/test_phase12_episodic_memory.py` — 2 class / 1 func
- `tests/test_phase13_knowledge_graph.py` — 3 class / 1 func
- `tests/test_phase14_decay_cross_project.py` — 2 class / 1 func
- `tests/test_phase15_lifecycle_issues.py` — 3 class / 1 func
- `tests/test_phase16_integration.py` — 3 class / 1 func
- `tests/test_phase1_2_integration.py` — 1 class / 1 func
- `tests/test_phase1_blast_tier_invariant.py` — 0 class / 9 func
- `tests/test_phase3_langsmith_tracing.py` — 3 class / 0 func
- `tests/test_phase4_evaluator_skills.py` — 3 class / 4 func
- `tests/test_phase5_context_fork_preflight.py` — 2 class / 0 func
- `tests/test_phase6_semantic_matching.py` — 7 class / 1 func
- `tests/test_phase7_dep_graph_evolve.py` — 3 class / 0 func
- `tests/test_phase8_retrieval_router.py` — 2 class / 0 func
- `tests/test_phase9_hybrid_retrieval.py` — 6 class / 0 func
- `tests/test_phase_a_step3_evolution.py` — 6 class / 0 func
- `tests/test_pipeline_block_enforcement.py` — 0 class / 3 func
- `tests/test_planner.py` — 9 class / 51 func
- `tests/test_policy_runtime.py` — 1 class / 2 func
- `tests/test_premortem.py` — 7 class / 49 func
- `tests/test_project_context_sync.py` — 0 class / 14 func
- `tests/test_project_overrides.py` — 0 class / 6 func
- `tests/test_project_pipeline.py` — 0 class / 7 func
- `tests/test_project_policy_defaults.py` — 0 class / 2 func
- `tests/test_project_scope.py` — 0 class / 4 func
- `tests/test_project_task_board_dispatch.py` — 0 class / 30 func
- `tests/test_provider_detect.py` — 0 class / 35 func
- `tests/test_provider_instruction_sync.py` — 0 class / 25 func
- `tests/test_q_s3_path_c.py` — 8 class / 2 func
- `tests/test_q_s4.py` — 5 class / 0 func
- `tests/test_qa_report.py` — 7 class / 2 func
- `tests/test_qa_report_wiring.py` — 3 class / 1 func
- `tests/test_quality_contract.py` — 2 class / 2 func
- `tests/test_registry.py` — 0 class / 3 func
- `tests/test_registry_manager_codex_skills.py` — 0 class / 8 func
- `tests/test_repo_shortcuts.py` — 0 class / 2 func
- `tests/test_request_router.py` — 1 class / 2 func
- `tests/test_requirement_llm.py` — 0 class / 2 func
- `tests/test_research_brief.py` — 0 class / 12 func
- `tests/test_research_depth.py` — 1 class / 0 func
- `tests/test_research_p1_quality_gate.py` — 7 class / 0 func
- `tests/test_research_router_modes.py` — 8 class / 1 func
- `tests/test_research_router_phase1b.py` — 5 class / 0 func
- `tests/test_research_system_regression.py` — 11 class / 0 func
- `tests/test_researcher_feedback_ranking.py` — 0 class / 1 func
- `tests/test_resume_brief.py` — 0 class / 2 func
- `tests/test_resume_brief_session_adapter.py` — 0 class / 1 func
- `tests/test_review_bundle.py` — 0 class / 16 func
- `tests/test_review_consensus.py` — 9 class / 2 func
- `tests/test_review_gate.py` — 0 class / 68 func
- `tests/test_review_gate_phase0.py` — 0 class / 22 func
- `tests/test_review_metrics_logger.py` — 0 class / 54 func
- `tests/test_review_runner_auth_expired.py` — 0 class / 10 func
- `tests/test_review_runner_execute_cli.py` — 2 class / 2 func
- `tests/test_review_runner_vendor_label.py` — 0 class / 9 func
- `tests/test_review_skill_router.py` — 0 class / 36 func
- `tests/test_right_sized_router.py` — 1 class / 10 func
- `tests/test_rse_router_decoupling.py` — 5 class / 1 func
- `tests/test_rse_slice2.py` — 0 class / 26 func
- `tests/test_run_build_separation.py` — 0 class / 3 func
- `tests/test_run_event_evolution_split.py` — 2 class / 0 func
- `tests/test_run_factory_cli.py` — 0 class / 4 func
- `tests/test_runner_contracts.py` — 0 class / 10 func
- `tests/test_safe_optional_id.py` — 0 class / 6 func
- `tests/test_sandbox_config.py` — 8 class / 2 func
- `tests/test_scale_aware_decomposition.py` — 5 class / 4 func
- `tests/test_session_bridge.py` — 0 class / 8 func
- `tests/test_setup_wizard_gate.py` — 0 class / 27 func
- `tests/test_signatures.py` — 0 class / 1 func
- `tests/test_skill_eval_harness.py` — 0 class / 12 func
- `tests/test_skill_evolution_controller.py` — 9 class / 3 func
- `tests/test_skill_evolution_safety.py` — 2 class / 0 func
- `tests/test_skill_evolution_trigger_routing.py` — 2 class / 0 func
- `tests/test_skill_feedback.py` — 0 class / 11 func
- `tests/test_skill_forge.py` — 0 class / 2 func
- `tests/test_skill_loader_phase2.py` — 0 class / 5 func
- `tests/test_skill_loader_phase4.py` — 2 class / 0 func
- `tests/test_skill_lock_utils.py` — 0 class / 4 func
- `tests/test_skill_metadata_adapter.py` — 1 class / 1 func
- `tests/test_skill_metadata_phase1.py` — 3 class / 0 func
- `tests/test_skill_metadata_v2_compat.py` — 0 class / 3 func
- `tests/test_skill_procurer_exact_reuse.py` — 0 class / 2 func
- `tests/test_skill_procurer_external_fallback.py` — 3 class / 4 func
- `tests/test_skill_procurer_logging.py` — 3 class / 3 func
- `tests/test_skill_procurer_reuse_gate.py` — 1 class / 11 func
- `tests/test_skill_quality_gate.py` — 0 class / 13 func
- `tests/test_skill_retrieval_engine.py` — 0 class / 16 func
- `tests/test_skill_self_evolution_hook_runid.py` — 1 class / 0 func
- `tests/test_skill_spec_synthesizer.py` — 0 class / 1 func
- `tests/test_spec_compiler.py` — 0 class / 28 func
- `tests/test_stage0_question_router.py` — 13 class / 1 func
- `tests/test_stage4_7_knowledge_pipeline.py` — 7 class / 2 func
- `tests/test_strategy_ledger.py` — 0 class / 28 func
- `tests/test_summary_schema_repeat_count.py` — 0 class / 1 func
- `tests/test_sync_claude_memory.py` — 0 class / 3 func
- `tests/test_sync_skill_registry.py` — 0 class / 3 func
- `tests/test_sync_wrappers.py` — 3 class / 0 func
- `tests/test_t3_7_run_event_integration.py` — 4 class / 2 func
- `tests/test_t3_classifier.py` — 0 class / 9 func
- `tests/test_t3_skip_report.py` — 0 class / 2 func
- `tests/test_task_template_e2e_command.py` — 0 class / 3 func
- `tests/test_test_gap_analyzer.py` — 0 class / 11 func
- `tests/test_text_integrity.py` — 0 class / 9 func
- `tests/test_triad.py` — 0 class / 29 func
- `tests/test_utils.py` — 31 class / 0 func
- `tests/test_utils_cache.py` — 0 class / 7 func
- `tests/test_warning_override_cli.py` — 0 class / 4 func
- `tests/test_warning_registry.py` — 0 class / 11 func
- `tests/test_warning_registry_cli.py` — 0 class / 4 func
- `tests/test_warning_registry_migration_callsites.py` — 0 class / 5 func
- `tests/test_warning_registry_p4a.py` — 0 class / 3 func
- `tests/test_warning_registry_schema_evolution.py` — 0 class / 1 func
- `tests/test_warning_stats.py` — 0 class / 10 func
- `tests/test_warning_stats_cli.py` — 0 class / 13 func
- `tests/test_watcher_portability.py` — 4 class / 0 func
- `tests/test_web_project_scope.py` — 0 class / 3 func
- `tests/test_wig_summarize_wiring.py` — 0 class / 1 func
- `tests/test_wiring_parity.py` — 0 class / 13 func
- `tests/test_work_item_generator_backfill.py` — 0 class / 10 func
- `tests/test_work_item_generator_references.py` — 0 class / 5 func
- `tests/test_work_item_generator_structured_evidence.py` — 0 class / 16 func
- `tests/test_workflow_autonomy.py` — 0 class / 3 func
- `tests/test_workspace_scoped_storage.py` — 0 class / 6 func
- `tests/verify_aee_cli.py` — 0 class / 2 func
- `tests/verify_audit_hash.py` — 0 class / 1 func

### `tests/e2e`

3 modules · 0 classes · 6 functions

- `tests/e2e/__init__.py` — 0 class / 0 func
- `tests/e2e/conftest.py` — 0 class / 3 func
- `tests/e2e/tick_simulator.py` — 0 class / 3 func

### `utils`

1 modules · 0 classes · 1 functions

- `utils/audit_logger.py` — 0 class / 1 func

### `web`

1 modules · 0 classes · 3 functions

- `web/app.py` — 0 class / 3 func

### `web/api`

4 modules · 4 classes · 24 functions

- `web/api/__init__.py` — 0 class / 0 func
- `web/api/agents.py` — 2 class / 20 func
- `web/api/run.py` — 1 class / 2 func
- `web/api/settings.py` — 1 class / 2 func

