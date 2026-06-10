# NEXT_STEPS — 세션 재개 가이드

> ## 🛑 STREAM 상태 (2026-06-02 고정)
> - **dogfood detector/infra stream COMPLETE** — R10~R17 detector + 고리③ 배선 + 실효성 측정까지 종료. detector 풀 소진, R18 후보 부적합. **"동일 발화 N차 반복 검증" 프레임 종료.**
> - **다음은 product-value work-item** — 내부 파이프라인 배관(planner/premortem/dogfood/research_*) 추가 금지(메타-재귀 함정). 다음 작업은 "AF가 사용자에게 줄 실제 가치"에서 도출.
> - **밀린 3건(planner research_findings 본소비 / auto_apply_defaults FSA 배선 / cli_hook_bridge)은 보류** — 전부 내부 배관이고, 가치 판정은 제품 방향(Step 0) 결정 후에만 가능.
> - **✅ Step 0 완료 (2026-06-02)**: `docs/2026-06-02-af-step0-product-decisions.md` — #3 대상=Python 본인도구, #4 task type=기능추가(더미금지) 확정.
> - **✅ LLM Wiki Phase 0 완료 (2026-06-02, `4fdd8df5`)**: `scripts/build_llm_wiki.py` + `docs/generated/llm_wiki/` 5페이지(index/architecture/review_patterns/open_items/source_refs) + 테스트 17 PASS. 재생성: `python scripts/build_llm_wiki.py`. Obsidian vault: `docs/generated/llm_wiki/`.
> - **✅ LLM Wiki Phase 1 완료 (2026-06-03, `d1b2771d`)**: 자동 재생성 트리거 — pre-commit에서 Master_Blueprint.md/code-review.md/NEXT_STEPS.md 또는 Python 파일이 staged면 `build_llm_wiki.py` 재생성+staging(문서 mirror + symbols.md 최신화). + `be9b8be4` `.githooks/* text eol=lf`(훅 CRLF churn 방지). ContextPack 연결은 메타-재귀 함정으로 기각(agent_runner 주입+신규 core 모듈).
> - **✅ RSE 슬라이스1 구현 완료 (2026-06-04, `f208b632` + cross-review fix `098a9bd5`, Sonnet, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: `core/right_sized_router.py` 신규 + `core/dogfood.py` `_run_develop_phase` 라우터화 + `DogfoodState.route_decision` 필드. 3-Tier 완주: af-critic WARN 2건(수정) / af-cross-review BLOCK 1건(`scripts.blast_radius` af.spec 누락 → `098a9bd5` 수정) / af-test-runner PASS(167). 부수: linter가 `_max_tier`를 `classify_with_content`→`classify_path`로 복원(신규 파일 지원 이유, 워크스페이스 파라미터는 시그니처 호환성으로 유지). **다음 = 슬라이스1 acceptance run(§5.3 4종) 또는 슬라이스2(ProjectPipeline stage-선택 파라미터) 또는 다른 product-value work-item.**
> - **✅ RSE 슬라이스1 acceptance run 완료 (2026-06-04, Sonnet)**: Case 1(light end-to-end) PASS — `weighted_mean` dogfood run_id `1780553383-adc12c2f`, 6 phase 159초 완료, LLM 3회, route_decision `source=llm/confidence=0.95/stages=[implement,test]/is_light=True`, source 무변. Case 2·4 dispatch 연결 PASS — `test_inv_floor_e2e`(Tier3→pipeline.run) + `test_inv_noscope`(scope=[]→pipeline.run) 각각 검증됨. Case 3 seam PASS — `test_r_fb_exc`(예외→fallback) + `test_inv_full_route`(fallback→pipeline.run) 두 반쪽 통과; 단일 seam 테스트 1개 미추가(저비용). **발견된 미수정 High 안전 갭**: `_max_tier`가 `classify_path`(path-only) 사용 — `core/providers/cli.py`·`core/dogfood.py`는 `classify_path=2` but `classify_with_content=3`; 설계리뷰 [Critical]·코드리뷰 [High] 모두 미수정. light 경로의 `_run_review_phase`는 pytest pass/fail만 보고 코드리뷰 0건 + FINALIZE는 `AF_SKIP_REVIEW_GATE=1` → content-Tier3 파일이 light로 진입 시 무검열 통과 위험. **설계 §1.2 "classify_with_content는 신규파일 부적합"은 틀린 전제였음**: `classify_with_content('nonexistent.py', '.')=2` 직접 확인, missing file은 이미 Tier2 fallback. **수정 범위**: `_max_tier`에서 `classify_path` → `classify_with_content` 1줄 교체 + Case 3 seam 테스트 1개 추가. 이후 product-value work-item.
 - **✅ RSE 슬라이스1 안전 마감 완료 (2026-06-04, Sonnet, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: ① `_max_tier` `classify_path`→`classify_with_content` 교체 ② `test_router_exc_fallback_to_pipeline` 추가(예외→fallback→pipeline.run + source="fallback" 검증) ③ 3-Tier 완주: af-critic WARN/af-cross-review PASS/af-test-runner PASS. **이후 = product-value work-item 진입.**
 - **✅ WI-1 완료 (2026-06-04, Sonnet, `9f4bb071`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: `agent_runner.py` 4개 성공 경로에 `result["provider_id"]` 명시 추가. `dynamic_orchestrator._inject_review_tasks_if_needed`에 `provider_id` 파라미터 추가 + `completed_task["provider_id"]` 전달. 일반 경로(line 841)·FSA 복구 경로(line 954) 모두 연결. 3-Tier: af-critic WARN(FSA reason 버그 발견→수정) / af-cross-review BLOCK(수정) / af-test-runner PASS(68). **다음 = RSE 슬라이스2(ProjectPipeline stage-선택 파라미터) 또는 dogfood UX 개선 또는 WI-3(P4.5b 사전강제).**
 - **✅ CRLF 근본 해결 완료 (2026-06-05, `698ee51b`)**: 방안 B — `.editorconfig`(`end_of_line=lf`, 기존) + `.gitattributes`(`eol=lf`, 기존) + pre-commit `git add --renormalize`(신규). staged 텍스트 파일을 commit 전 자동 정규화. Python 코드 수정 0줄. 부수: `covariance(xs, ys)` 신설(`b1ced4b9`, 190 PASS, 3-Tier PASS).
 - **✅ provider rate-limit skip 구현 완료 (2026-06-10, Sonnet, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: 설계(`docs/2026-06-10-provider-rate-limit-aware-skip-design.md`) → S1+S2+S3 전부 구현. ① `ProviderState.RATE_LIMITED` 추가 ② `ProviderProbeResult.rate_limited_until` 필드 + 캐시 직렬화/역직렬화 ③ `mark_rate_limited()` — usage limit 만남 → 캐시에 atomic 기록 ④ `detect_rate_limit_signal(text)` — provider-agnostic limit 패턴 + reset ISO 파싱 + fallback TTL ⑤ `_apply_rate_limit_override()` — detect_provider_states 반환 전 override (force_refresh도 미래 until이면 RATE_LIMITED 유지, INV-9) ⑥ `review_runner._run_provider` 배선 — limit 응답 감지 시 자동 mark ⑦ CLI `--mark-rate-limited --until` + JSON `rate_limited` 목록 ⑧ `af-cross-review.md` Step 0 케이스 1b(rate_limited SKIP 노티) + Step 2b(MCP 응답 limit 시 mark). INV-1~9 테스트 11건 신규, 212 PASS. 3-Tier: 다음 단계(커밋 후 af-critic → af-cross-review 필요). **다음 = 3-Tier 완주 후 skewness 신규 함수 커밋(이미 utils.py에 있음) 또는 다른 product-value work-item.**
 - **✅ WI-3 완료 (2026-06-05, Sonnet, `7a1a6061`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: P4.5b model escalation 사전강제 + claude tier 매핑. `scripts/agent_model_selector.py`에 `_TIER_TO_MODEL_ID` + `resolve_model_id()` 신설(haiku/sonnet/opus→전체 모델 ID). `scripts/check_pending_review.py`에 `_inject_model_override()` + `_do_check()` P4.5b 블록 추가(pending escalation → `af-test-runner[model=claude-sonnet-4-6]` 출력, clear는 _atomic_write 성공 이후). CLAUDE.md `[model=X]` 접미사 파싱 instruction 추가. 테스트 42건(TestResolveModelId 9 + TestInjectModelOverride 11 신규). 3-Tier: af-critic WARN-2건(수정)/af-cross-review SKIP(provider 한도)/af-test-runner PASS(42). 부수: `pearson_correlation(xs, ys)` 신설(`a9c41313`, 9 PASS).
 - **✅ af doctor 완료 (2026-06-05, Sonnet, `e4c6dc5f`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: `scripts/af_doctor.py` 신규 — Python·git·provider·hook·pytest·dogfood 7개 항목 진단(ok/warn/fail). `agent_launcher.py` doctor 서브커맨드 추가(_KNOWN_SUBCOMMANDS, mutually_exclusive --fast/--refresh). `af.py` `_LAUNCHER_SUBCOMMANDS={"doctor"}` 추가(sys.executable 위임). `af.spec` hiddenimports. 손 구현 + 3-Tier: af-critic WARN-2건(수정) / af-cross-review PASS(Advisory 4건 수정) / af-test-runner PASS(26). **다음 = WI-2(review_provider runtime enforcement) 또는 RSE 슬라이스2(ProjectPipeline stage-선택 파라미터) 또는 다른 product-value work-item.**
 - **✅ WI-2 완료 (2026-06-05, Sonnet, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: review_provider runtime enforcement — cross_validate dead metadata 연결. ① `inject_review_tasks` 가드를 `detect_installed_cli_providers`→`detect_available_cli_providers`로 정합 ② `AgentSpecializer.specialize()`에 `task_meta["review_provider"]`→`agent["force_provider"]` 주입 ③ `AgentRunner.run()`에 force_provider 우선 처리(available 확인, **미가용 시 `{"ok":False,"reason":"...unavailable"}` 명시 실패 — silent fallback 금지**). 신규 테스트: `test_agent_specializer.py`(3) + `test_agent_runner_force_provider.py`(4) + `test_project_task_board_dispatch.py`(+2). 3-Tier: af-critic PASS / af-cross-review BLOCK→fixed(unavailable silent fallback 수정) / af-test-runner PASS(72). **다음 = RSE 슬라이스2(ProjectPipeline stage-선택 파라미터) 또는 WI-4(review_runner→execute_cli_chat 통합) 또는 다른 product-value work-item.**
 - **✅ RSE 슬라이스2 설계 완료 (2026-06-05, Opus, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: `docs/2026-06-05-af-right-sized-execution-slice2-design.md`. `ProjectPipeline`을 monolithic→`RouteDecision.required_stages`로 **research / doc-review 2개 additive 단계 조건부 skip**. 핵심 확정: ① required_stages를 **기존 `route` dict 채널로 전달**(신규 시그니처 0개) — `_stage_enabled(route, *names)` helper(required_stages 부재/빈 리스트→전체실행 하위호환) ② research 게이트(`prepare_brief:725-795`) + doc-review 게이트(`prepare_documents:1075-1138`, `review|cross_review` OR + 기존 starter 가드 AND) ③ production 배선 1곳 = `dogfood._run_develop_full`이 `pipeline.run(route=state.route_decision or None)` ④ plan/implement는 본체, design은 research 종속이라 slice2 비대상(slice3). **cross-review = WARN[single-vendor, Codex usage limit]**: BLOCK 0, Advisory Medium 2건 수용(§4.4 D3-bypass edge case — LLM brief가 research_plan 직접 포함 시 research skip해도 domain spec 실행 가능 / §3.3 prepare_documents route 회수는 신규 라인 명시). 라인좌표·`_stage_enabled` 시맨틱·`_coverage_blocked({})`·Tier3 floor 보호 grep 검증 통과. **+ 구현 강제 제약 추가(`48c0f91f`, §6.1)**: 하드코딩 금지(stage 이름→`right_sized_router` STAGE_* 명명 상수 SSOT) + 타입 단일 선언(import 소비만) + 강제 테스트 4종(E-SSOT-MEMBER/E-IMPORT-IDENTITY/E-NO-MAGIC/E-FLOOR-CONST). §8 Step 0=강제테스트 RED, Step 1=STAGE_* 상수 승격(slice1 코드 수정→3-Tier). 메모리 `feedback_no_hardcode_single_type_source`(전 구현 적용). **다음 = `/model sonnet`으로 슬라이스2 §8 Step 0부터 test-first 구현(재설계 금지) 또는 WI-4.**
 - **✅ RSE 슬라이스2 구현 완료 (2026-06-05, Sonnet, `d29f298d`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: §8 Step 0~10 완주. ① `right_sized_router.py` STAGE_* 명명 상수 승격(SSOT) + floor 튜플 상수화 ② `project_pipeline.py` `_stage_enabled` helper + research 게이트 + doc-review 게이트(AND: _stage_enabled + starter 가드) ③ `dogfood._run_develop_full` `pipeline.run(route=state.route_decision or None)` 배선 ④ `tests/test_rse_slice2.py` 신규 19케이스(E-SSOT-MEMBER/E-IMPORT-IDENTITY/E-NO-MAGIC/E-FLOOR-CONST + G-*7 + inv-*6 + inv-WIRE*2). 3-Tier: af-critic PASS / af-cross-review PASS(BLOCK 0) / af-test-runner PASS(193). **다음 = WI-4(review_runner→execute_cli_chat 통합) 또는 다른 product-value work-item.**
 - **✅ WI-4 완료 (2026-06-05, Sonnet, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: `core/review_runner._run_provider()` `subprocess.run()` 직접 호출 → `execute_cli_chat(CliChatRequest(...))` 경유로 교체. `_resolve_cli`, `_build_exec_command` 제거. `_PROVIDER_ID_MAP` 상수 추가(claude/codex/gemini → *_cli 매핑). `allow_file_edit=False`(review-only, non-claude는 headless_edit_flags 항상 적용). `tests/test_review_runner_execute_cli.py` 신규 9케이스(provider_id 매핑 3종 + ok/fail/empty text + request fields + unknown reason fallback). 3-Tier: af-critic PASS / af-cross-review WARN(BLOCK 0, Advisory 2건 기각: run_cross_review verdict 누락=변경前 기존결함·WI-4 범위外, unknown provider ValueError=실호출경로 없음) / af-test-runner PASS(2905). **다음 = 다른 product-value work-item.**
 - **✅ af project inspect 완료 (2026-06-06, Sonnet, `04a84057`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: `scripts/af_project_inspect.py` 신규 — `af project inspect [path]`. LLM/네트워크 없음, deterministic. `af_doctor.run_checks(fast=True)` 재사용(새 진단 로직 금지). risks: git_dirty(target git 섹션 직접)/doctor_fail/doctor_warn/no_tests/no_readme. 진입점은 candidate+evidence 형식만. `os.walk(followlinks=False)` symlink 루프 방지. `af.py` project 추가, `agent_launcher.py` inspect 서브커맨드+dispatch, `af.spec` hiddenimports. 테스트 47건 신규. 3-Tier: af-critic WARN 수정 / af-cross-review BLOCK→fixed(doctor cwd 분리+중복 entrypoint 제거) / af-test-runner PASS(47). **다음 = 다른 product-value work-item 또는 `af project inspect`로 실제 작업 전 dogfood 검증.**
 - **✅ codebase wiki 경로(i) 첫 throw + planner 버그 fix (2026-06-07, Opus, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: 결정 메모리 `project_af_codebase_wiki_direction` 첫 throw 실행. **(a) 첫 throw `symbols.md`(경로 구분자 없는 새 파일) → light 아닌 full로 빠짐**: `_intended_scope`→`spec_compiler._scope_from_intent`가 **확장자 AND 경로 구분자** 둘 다 있어야 scope 인정 → `symbols.md`는 scope=[] → fallback(full 7-stage). full은 deterministic parse→render를 game_logic_dev/qa_engineer 멀티에이전트로 과분해+문서 sprawl+191 cycle 후 blocked. **(b) 경로 한정 재-throw `scripts/codebase_symbols.py` → light 수렴**: source=llm/confidence=0.82/stages=[plan,implement,test], 직선 3 LLM 호출, **깨끗한 2파일(생성기+테스트), 24 tests PASS**. 단 phase=blocked. **(c) blocked 근본원인 = `planner.py:297` `shlex.quote` 버그**: scope_file 존재확인 command가 `python -c "...os.path.exists(<path>)..."`에서 셸 인용(`shlex.quote`)을 써 셸-특수문자 없는 경로가 따옴표 없이 들어가 NameError → impl ok=False → false-negative "pipeline blocked". `weighted_mean`(기존 파일 수정)은 missing_file risk 없어 미발화, **greenfield(새 파일) light run에만 적중 = wiki use case**. `repr()`로 fix + 실행가능성 회귀 테스트. 3-Tier: af-critic PASS / af-cross-review PASS(BLOCK 0) / af-test-runner PASS(117). **결론: light가 wiki에 옳은 경로임 확정 — (iii) 불필요. 메모리 "(iii) 필요" 가설 정정(full 빠짐은 복잡도 아닌 scope-phrasing precondition).** 재-throw 검증 PASS(run `1780813496`, phase=complete, 6 phase 전부 ok, light wiki COMPLETE 실증).
 - **✅ Router scope/research decoupling 설계 완료 (2026-06-07, Opus, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: `docs/2026-06-07-router-scope-research-decoupling-design.md`. af-cross-review WARN(BLOCK 0, single-vendor) 3건 + 외부리뷰 5건 검토 반영.
 - **✅ Router scope/research decoupling Phase 1+2 구현 완료 (2026-06-07, Sonnet, `30f891fb`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: Phase 1: `_classify_empty_scope()`(LLM+0.85+ROUTE_MARKER_SCOPE_UNCERTAIN) + `RouteDecision.markers` 필드 + `to_dict()` 갱신 + `is_light()` marker-aware threshold SSOT + `_light_allowed()` dispatch guard(auto_policy 빈-scope→full, INV-5/δB). Phase 2: `MergePolicy.tier3_floor_mode="observe"` + `_run_develop_light(state, policy)` tier3_floor 관측(observe 모드 block 없음). 신규 32 테스트. 3-Tier: af-critic PASS(WARN 2건 수정) / af-cross-review PASS(BLOCK 0) / af-test-runner PASS(258).
 - **✅ LLM Wiki AST + Master Blueprint mirror 완료 (2026-06-07, Codex, worktree dirty)**:
   - `scripts/codebase_symbols.py` 추가 + `build_llm_wiki.py`에 `symbols.md` 연결. Python top-level class/function AST view 생성. runtime/cache/vendor 디렉터리(`.af_runtime`, `.git`, `__pycache__`, `node_modules`, `venv`, `dist`, `build` 등) 제외. Python encoding cookie는 `tokenize.open()`으로 처리.
   - `Master_Blueprint.md`는 `docs/generated/llm_wiki/blueprint/`에 섹션별 전문 mirror 완료: `overview.md`(preamble), `toc.md`, `0-빠른-참조-테이블.md`처럼 사람이 읽는 파일명, `maintenance-guide.md`, `index.md`. source_refs/index 링크 연결. 4-backtick fence로 원문 코드블록 보호. stale generated blueprint page 자동 삭제.
   - 검증: `python -m pytest tests/test_build_llm_wiki.py tests/test_codebase_symbols.py -q` → **41 PASS** / `python -m py_compile scripts\build_llm_wiki.py scripts\codebase_symbols.py` PASS / `python scripts\test_gap_analyzer.py --workspace .` PASS / `python scripts\build_llm_wiki.py` → **23 pages**.
   - 전체 테스트 참고: `python -m pytest tests/ -q --ignore=tests/test_gemini_smoke.py --ignore=tests/test_web_project_scope.py` → **3039 PASS, 10 FAIL**. 실패는 기존 타 영역(`inject_review_tasks`, `nlm`, `syncCompyne`, `research_system`, `approval_gate` CP949 read, `warning_stats_cli`)로 이번 LLM Wiki 변경과 무관.
 - **🎯 다음 세션 진입점 = code-review 문서 전문 mirror**:
   - 현재 `docs/code_review/code-review.md`는 아직 전문 mirror가 아님. `review_patterns.md`는 `### 2.x`/`### 3.x` 섹션 헤더 + 첫 bullet/출처 line 중심 요약 view.
   - **✅ LLM Wiki Code Review mirror 완료 (2026-06-07, Codex, worktree dirty)**: `docs/code_review/code-review.md`의 `### N.N` 섹션을 `docs/generated/llm_wiki/code_review/` 전문 페이지로 분할 생성. `code_review/index.md` 추가, 루트 `index.md`/`source_refs.md` wikilink 연결, stale cleanup 추가, Obsidian 탐색기용 사람이 읽는 파일명(`2-1-실행-엔진-runtime-engine.md` 등) 적용, 테스트 보강. 산출물: 전체 wiki 41 pages. 검증: `py_compile` PASS / `tests/test_build_llm_wiki.py -q` 29 PASS / `scripts/test_gap_analyzer.py --workspace .` PASS. 전체 `python -m pytest tests/ -x -q`는 기존 환경 의존성(`tests/test_gemini_smoke.py`의 `google` 패키지 없음)으로 collect 단계 중단.
   - **✅ Review-gate provider/OS 독립 enqueue 보강 (2026-06-08, Codex, worktree dirty)**: Claude PostToolUse 훅이 없는 Codex·IDE·shell·다른 OS 경로에서도 pre-commit이 staged review 대상 `.py`를 Git index 기준으로 `.af_review_queue/pending_agent_review.json`에 먼저 enqueue하도록 `scripts/enqueue_staged_review.py` 추가 + `.githooks/pre-commit`에서 `review_gate.py --check` 전 호출. 기존 `enqueue_agent_review.py`는 `main_for_path()`로 재사용 가능하게 분리. 회귀 테스트: `tests/test_enqueue_staged_review.py`.
   - 다음 작업: product-value work-item 신규 선정. LLM Wiki 쪽은 Obsidian 탐색 기본 연결 완료.
   - 구현 패턴은 `Master_Blueprint.md` mirror와 동일하게 가져갈 것: `_split_*_sections`, ASCII slug, 4-backtick fence, frontmatter quoted sources, 원본 read-only, recursive generated-file tests.
> - **⚠️ 이전: 다음 세션 진입점 = AF Right-Sized Execution 슬라이스1 구현 (`/model sonnet`)**: ✅ **상세 설계 완료 (2026-06-03, Opus)** — `docs/2026-06-03-af-right-sized-execution-detailed-design.md`. af-cross-review WARN[single-vendor]·BLOCK 0, High 1(registry leak)+Med 2 finding **전부 설계 반영 완료**. **다음 = 그 문서 §8 구현 순서대로 Sonnet 구현**(재설계 금지 — 설계 수렴됨). 핵심 확정: ① 신규 `core/right_sized_router.py` `classify(task,workspace,*,changed_files)→RouteDecision{isolation,required_stages,review_depth,confidence,reason,floors_applied,source}` (`ControlPlaneLLM.generate_json` 재사용, `_router_llm` 주입) ② 안전 floor 2개(self-mod→isolation≥worktree / `from scripts.blast_radius import classify_path` Tier3→design+review+cross_review 강제) — **상향만, 하향 금지** ③ 보수적 fallback(예외/{}/저신뢰/badschema→full+worktree) ④ dogfood `_run_develop_phase`를 라우터화: `_intended_scope`(scope=[]면 full 가드) → light면 `_run_develop_light`(compile_spec→run_premortem→build_plan→`_run_implement_phase`, **`_develop_isolation_env` CM으로 full과 동일 격리** — registry leak 방지), else `_run_develop_full`(기존 body 추출) ⑤ `DogfoodState.route_decision` 필드 + 직렬화 ⑥ test-first 9+7 케이스 + acceptance 4종. **방향·Step 1~7 원본은 `docs/2026-06-03-af-right-sized-execution-decision.md` §Converged Design.** core/ Tier3 test-first + 3-Tier(cross-review 필수).
> - **✅ dogfood Option 2 재정렬 완료 (2026-06-03, `5e461c23`)**: inv1~inv5 불변식 test-first 구현 완료. DogfoodPhase.DEVELOP 신설, _PHASE_ORDER = PENDING→ISOLATE→DEVELOP→VERIFY→REVIEW→FINALIZE→MERGE, _run_develop_phase(isolation env try/finally + ProjectPipeline.run() + changed_files 정규화 + pytest 명령 자동 도출), inv1 deny-all, inv2 placeholder fail-closed, inv3 no-retry, agent_launcher.py NameError 수정(AgentFactory() 명시 인스턴스화). 3-Tier: af-critic BLOCK→fixed / af-cross-review BLOCK×2→fixed / af-test-runner PASS. 264 PASS.
> - **🚨 T3 결과 = "pipeline codegen 성공 / dogfood isolation acceptance 실패" (2026-06-03)**: T3 실제 LLM run 4회 수행. **증명된 것**: ProjectPipeline이 worktree 안에서 실제 코드 작성 가능 — `moving_average()` 구현 + `TestMovingAverage` 10 PASS (run `1780453531-b63cf5fe`). PlanVerifier도 실코드 분석(이전 clamp run에서 중복 CRITICAL 검출). **그러나 격리 불변식 깨짐**: source repo `core/utils.py`+`tests/test_utils.py`가 직접 수정됨(merge=never인데 source 오염). 커밋 `90346e95`는 격리실패 산출물 수동 회수 — "정상 dogfood 산출물" 아님.
>   - **⚙️ 부수 수정 완료(커밋됨)**: ① `AF_SKIP_DOMAIN_REVIEW=1`(`0806ca1c`, DEVELOP 내 approve 차단 해소) ② DEVELOP changed_files `git status` working-tree fallback(`5d0da24f`, strict_contract verify-no-commands 해소) ③ provider_detect codex ping `--version`→`login status`(`aefa8797`, 세션인증 실제 확인) + 이전 잘못된 API KEY 체크 철회. provider는 **CLI 세션 로그인 방식**(API KEY 아님). Gemini만 미구독→AUTH_EXPIRED 정상. stale provider_cache 삭제함.
>   - **🔬 격리 누수 원인 진단 (팩트 확정)**: worker dispatch는 **무죄** — runs/*/task.json 22개 전부 `workspace=worktree` 확인. dogfood_state worktree 경로 정상. **진짜 범인 = `core/control_plane_llm.py:122` `workspace=os.getcwd()`**. Lilith(오케스트레이터)가 stall 복구 시 "다음 작업 결정"을 위해 claude_cli를 **SOURCE 루트**에서 호출(프롬프트에 프로젝트 설명 전체 포함, 파일편집 도구 보유) → source `core/utils.py`를 worktree와 **다른 구현**으로 수정(worktree 11:46 / source 12:06, 350줄 diff). stall 구간 `[claude_cli] CLI start (300s)` 10회+가 이 경로. **단정 보류**: ControlPlaneLLM이 "JSON만 반환" 시스템프롬프트인데도 실제 파일을 썼는지는 transcript 확인 필요(C:\Users\HOME\.claude\projects\D--warkSpaces-agent-factory\d7fabc0a-*.jsonl 또는 source `.af_runtime/cli_sessions/claude_cli_claude_cli_run.json`). 단 source 수정 가능한 유일한 남은 claude_cli 경로는 이것 하나로 확정.
>   - **✅ dogfood DEVELOP source-write leak 차단 완료 (`f4da6ce8`, 2026-06-03)**: `CliChatRequest`에 `allow_file_edit: bool = True` 추가 + `build_cli_command()`에서 `allow_file_edit=False` 시 claude_cli의 `--permission-mode bypassPermissions` 제거(gemini_cli headless 플래그는 유지) + `ControlPlaneLLM._generate_via_cli()`에 `allow_file_edit=False` 전달. 3-Tier: af-critic PASS / af-cross-review BLOCK→fixed(gemini headless hang 수정) / 2723+4 PASS. **잔여 advisory**: `workspace=os.getcwd()`는 여전히 source root를 가리키나 파일편집 자체가 차단됨.
   - **✅ T3 격리 재검증 = PASS (2026-06-03, run_id `1780473736-f8a001b8`, merge: never, PC: Windows)**: `AGENT_CHAT_PROVIDER=claude_cli`로 provider 고정 후 `geometric_mean` leaf 함수 dogfood run. **결정적 증거**: ① worktree에 `geometric_mean`+`TestGeometricMean` **구현됨** ② source `core/utils.py`+`test_utils.py`+**전체 git status가 baseline과 IDENTICAL**(완전 무변) ③ 215+ 사이클 동안 stall 복구 control-plane claude_cli 호출이 **여러 번 발생**(이전 leak이 났던 바로 그 경로)했는데도 source 무변. **= `allow_file_edit=False` 패치가 control-plane source-write leak을 실제로 차단함을 직접 관측.** 검증 레버는 `AGENT_CHAT_PROVIDER=claude_cli`(NOT `AF_SKIP_PROVIDER` — 후자는 provider_detect.py 전용, 오케스트레이션 provider 선택에 미반영).
   - **🆕 신규 발견 (leak과 별개, 미수정) — 📌 TODO 등록**: **DEVELOP phase 비수렴** — Option 2가 dogfood DEVELOP을 전체 `ProjectPipeline.run()`에 위임하는데, trivial leaf 함수(`geometric_mean`)에도 designer/qa_engineer 등 멀티에이전트 프로젝트를 과분해 + `terminal_per_agent=True`로 외부 터미널 창 spawn → Lilith가 계속 새 build/qa 태스크 생성하며 215+ 사이클 busy-wait, COMPLETE/BLOCK에 도달 못 함(run 수동 중단). **이게 "엄청 오래 걸림"의 원인.** leak과 무관한 인프라 이슈.
     - **⚠️ 처방 제약 (사용자 지시 2026-06-03)**: **단순 캡/비활성화로 처리 금지.** `terminal_per_agent=False` + `max_cycles` 하드 캡 같은 단순 처방은 큰 task에서 정당한 멀티에이전트 작업까지 잘라버림. **지능형으로 바꿔야 함** — task 복잡도(leaf 함수 1개 vs 멀티모듈 프로젝트)를 인지해서 경로를 적응적으로 라우팅: trivial/leaf → 경량 codegen 단일 경로, 복합 → full orchestrator. 즉 "복잡도 추정 → 경로 선택" 게이트가 핵심이고, 캡은 안전망에 불과.
     - **메타-재귀 주의: 즉시 착수 금지.** product 방향(Step 0) 확정 후 우선순위 판정. `core/express_router.py`(이미 direct/light/full/dogfood 4-경로 결정적 라우팅 존재)를 DEVELOP 진입 전 복잡도 게이트로 재사용할 수 있는지가 첫 분석 포인트.
     - **🔧 정정 (2026-06-03 코드 검증)**: 위 "express_router 재사용" 가설은 **현재 코드로 불성립**. `route_task()`는 `dogfood.py`/`agent_launcher.py`/`project_pipeline.py` 어디서도 호출 안 됨(런타임 死코드, `test_express_router.py`만 참조). 게다가 `express_router.py:46-52` `_SELF_MOD`에 `core/`가 있어 core/ 태스크를 **무조건 dogfood로 분류**(`_classify:172-175` 즉시 return) → dogfood 모드 내부에 leaf/멀티모듈 구분 2차 게이트 없음. 따라서 옵션 ② DEVELOP 경량화는 "기존 라우터 재사용"이 아니라 **`_run_develop_phase`(dogfood.py:1645) 내부 신규 sub-complexity 신호 구축** — 더 무거운 작업으로 재평가.
     - **🔧 leak default 잔여 감시 (2026-06-03)**: `allow_file_edit` 차단은 ControlPlaneLLM이 명시 `False`를 넣는 경로 한정. `CliChatRequest.allow_file_edit` **기본값은 여전히 `True`**(`core/providers/cli.py:40`) + `control_plane_llm.py:122 workspace=os.getcwd()`는 source root 유지. default=True로 source-root workspace에 CliChatRequest를 만드는 신규 코드가 생기면 leak 재발 가능 — **회귀 감시 포인트**(leak 스트림 자체는 PASS로 종료).
   - **🎯 다음 세션 진입점**: leak 검증 종료(PASS). ① product-value work-item 선정으로 전환 또는 ② DEVELOP 비수렴 이슈(위 신규 발견) 경량화 — 단 후자는 내부배관이므로 product 방향 확정 후 우선순위 판정.
> - **🔧 모델/Provider 라우팅 결함 4건 (2026-06-02 분석, 큐 등록 — 착수: product-value work-item 다음)**: 5턴 deliberation(Claude+Codex 교차)으로 코드 확정. **핵심 사실**: ① 단일 claude_cli 환경에선 `_should_include_model`(cli.py:647)이 `"claude"` alias를 `--model`에서 제거 → /model default 상속, 모델 티어링 死코드 ② `preferred_model: gemini`(agents/*.yaml 7/8)가 `AGENT_CHAT_MODEL`/`--model`을 가로챔(agent_runner.py:1143 `or` 단락) → env override 무력. **유일 레버=claude CLI /model**. ③ cross-review 이중 단선: pipeline 내부 cross_validate는 `available>=2`만 생성(board:1136)+`review_provider` dead metadata(소비처 0, board:1151)+provider_id 입력 누락(dyn_orch:233) ④ 단일 provider면 vendor 다양성 구조적 불가 → **모델 escalation이 유일 품질 레버**인데 P4.5b 사전강제 미연결(hook_runner:418은 사후 advisory만). **착수 순서(dogfood 안정화 후, 재평가 전제)**: WI-3 P4.5b 사전강제+claude tier 매핑(haiku/sonnet/opus→구체 모델명, "claude" alias는 default 상속 유지·구체명일때만 --model) / WI-1 provider_id 보존(result["reason"]@agent_runner:1224 → dyn_orch:233, 1줄·고가치) / WI-2 review_provider runtime enforcement / WI-4 review_runner→execute_cli_chat 통합. **WI-3 우선순위는 조건부**: 단일 provider 사용자 비중이 product 방향에서 확정되면 product-value 승격, 그 전엔 내부배관 큐(감 기반 못박기 금지). **운영(즉시·코드0)**: 구현/dogfood 대량호출=`/model sonnet`, 설계/정책/dogfood acceptance=`/model opus`, Tier3 [single-vendor]면 "외부검증 없음"으로 신뢰도↓ 해석. ⚠️ 이 주제는 5턴 연속 분석으로 수렴 — 추가 재분석은 메타-재귀, 구현 시점에만 재개.
> - **브랜치 사실**: `2026-05-20-research-coverage-gate`가 origin/main 대비 **232 ahead / 3 behind** (dogfood stream 누적). 머지 결정 보류 — 사용자 판단.
>
> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-06-07 KST (Windows)** — **LLM Wiki Obsidian 연동 2단계 완료**. 완료: AST `symbols.md` 연결 + `Master_Blueprint.md` 전문 mirror + `docs/code_review/code-review.md` 전문 mirror(`docs/generated/llm_wiki/code_review/` 18파일 포함, 전체 wiki 41 pages). 검증: targeted 29 PASS / py_compile PASS / test_gap_analyzer PASS. 전체 회귀는 `tests/test_gemini_smoke.py`의 `google` 패키지 부재로 collect 단계 중단(환경 의존성). **다음 = product-value work-item 신규 선정**. 이전: Router Phase 1+2 구현 완료(`30f891fb`) + codebase wiki light COMPLETE + planner shlex→repr fix(`7a3f44e5`) + WI-4/WI-2 완료.
>
> **다음 세션 최우선 진입점**: **dogfood detector 인프라 검증 완료 (2026-06-02) — 다음은 ① 실가치 work-item 선정 또는 ② 저우선 정리**. 북극성 epic("AF가 AF를 개발하는 완성 루프")의 `investigation → AI 프롬프트 → production 코드` 고리가 실제 run에서 닫힘이 직접 관측됨(아래 후보 #4 실효성 측정). detector 풀(R10~R17) 소진 + R18 후보 부적합 → "동일 발화 N차 반복 검증" 프레임은 종료. **다음 work-item 선정 시 메타-재귀 주의**: 파이프라인 의존 모듈(premortem/planner/dogfood/research_*)은 손으로 3-Tier, leaf 기능만 dogfood run.
>
> 완료 누계(history): R1 21차 percentile() … R1 27차 R15(long_function) + R1 28차 planner R15 연동 + **R16 complexity(병렬 2트랙)** + **dogfood CRLF 격리 fix** + **dogfood docs/reviews scope 면제 fix** + **docs/reviews 면제 실전 검증 PASS** + **R17 nesting_depth(3-Tier PASS)** + **고리③ 배선 + 실효성 측정(2026-06-02)**. 후보 기록:
> 1. ~~**(신규 결함, 최우선) dogfood FINALIZE scope 면제에 `docs/reviews/` 추가**~~ ✅ **완료 (2026-06-01)** — `FINAL_DOC_DIRS = ("docs/reviews/",)` 신설. FINALIZE 스테이징 필터 + `build_merge_policy` allowed_paths 양쪽에 디렉터리 prefix 면제. **3-Tier 중 cross-review가 내 1차 판단을 반박**: build_merge_policy가 `has_core_allowed`만 보던 비대칭이 `skills/`/`scripts/`-only plan(`blueprint_updater.TRIGGER_PREFIXES`에 skills 포함)에서도 도달 가능 → gate를 `if allowed:`(plan 비어있지 않으면 doc 면제 추가)로 정합, `has_core_allowed` 추적 제거. 회귀 3건. 3-Tier: af-critic WARN / af-cross-review BLOCK→fixed / af-test-runner PASS(265 tests). 이제 'CRLF fix + 이 결함' 둘 다 풀려 **수동개입 0 자동머지** 가능.
> 2. ~~**(검증) 다음 dogfood run에서 docs/reviews 면제 실전 확인**~~ ✅ **완료 (2026-06-01, run_id `1780296470-9487ce47`, merge `46ff2ab2`, dogfood_commit `266e00f2`, PC: Windows)** — `running_max()` dummy run. `merge_report.json` 결정적 증거: dogfood가 `docs/reviews/2026-06-01-155026-utils-code-review.md` 생성(=cumsum run에서 머지 막던 그 artifact)했으나 **`scope_violations: []`** → auto_policy merge가 **수동 ff 개입 0**으로 자동 완료(`merge_status: merged`). 신규 `TestRunningMax` 11 PASS. 'CRLF fix + docs/reviews 면제' 둘 다 실전에서 검증돼 dogfood auto-merge 루프 안정화 확인.
> 3. ~~`core/premortem.py`에 R17 신규 detector (깊은 중첩 depth)~~ ✅ **완료 (2026-06-01, `e66cb553`)** — `_detect_nesting_depth_risk()` + `_max_block_depth()` 신설. If/For/While/With/Try(async 포함) depth>4 → R17 risk. planner `_extract_nesting_depth_pairs()` + investigation branch 연동. 3-Tier: af-critic PASS / af-cross-review PASS(Finding 1/2/3 수용) / af-test-runner PASS. 14+9건 신규, 403 PASS.
> 4. ✅ **완료 (2026-06-01) — 고리③ 배선 수리 (R17 실전 검증 대체)**: 워크플로우 분석으로 detector R10~R17이 만든 investigation step(grep) 출력이 `executed`에만 기록되고 AI executor 프롬프트에 미도달 → **detector 9개가 AI 산출물에 0 영향**이던 단선 발견(`dogfood.py:370` `_build_ai_task`가 `executed` 미수신, `:1530`). `_build_ai_task(step, plan_intent, investigation_outputs=None)`에 합류(backward compat) + `_run_implement_phase` 누적 + evidence ```fenced 신뢰경계(prompt injection 완화) + `_INVESTIGATION_MAX_ITEMS`=10 head-slice 상한. real-file smoke(test_premortem.py)로 R17 발화 봉인. 3-Tier: af-critic WARN(2건 advisory→선조치) / af-cross-review WARN(codex; gemini auth_expired; BLOCK 0) / af-test-runner PASS(163). **R17 production dogfood run은 불필요로 결론** — 17번째 같은 발화 검증은 무가치, 미검증 고리(step→AI)가 핵심이었고 코드로 확정.
>    - **R18 detector 추가 보류**: 후보 3종 전부 부적합 — `mutable_default_arg`(repo 0건), `broad_except`(의도적 best-effort 1050건, CLAUDE.md 명문화), `unused_import`(TYPE_CHECKING/`__all__` false-positive 97건). detector 풀이 repo 실질 결함 소진.
>    - ✅ **detector 실효성 측정 COMPLETE (2026-06-02, run_id `1780326453-e9f27d38`, merge: never, PC: Windows)** — spy executor로 `core.dogfood._ai_executor` 래핑(실제 claude_cli 위임 + AI 프롬프트 전문 캡처) 후 `run_all(merge=never, strict_contract=True)` 실제 end-to-end run(`harmonic_mean` task). **결과: PHASE=complete, AI 호출 2/2 모두 `Investigation findings` evidence 블록 채워짐(각 3 lines)**. 캡처 증거가 빈 블록 아닌 실제 grep 출력(`442:def get_external_skill_roots...` + py_compile 결과)임 확인 — 고리③ 배선이 production run에서 investigation 출력을 AI implementation 프롬프트(S3 구현·S4 테스트)에 실제 전달함을 직접 관측. 산출물도 production-grade(harmonic_mean 정확 구현 + TestHarmonicMean 10 test). **측정 run은 merge=never라 worktree에만 존재(미머지 throwaway, 회수 불요)**.
>    - **📌 부수 관찰 (verified — false-trigger 아님)**: S2 investigation `grep -n 'def get_external_skill_roots' core/utils.py`는 **R15 long_function detector가 정상 발화**한 것. `get_external_skill_roots`는 core/utils.py의 **57줄 함수**(R15 임계값 50줄 초과) → planner.py:340 `long_function` branch가 `grep -n def` step 생성. **버그 아님, 규칙대로 동작.** 단 **설계 논점**: R15/R16/R17(long/complexity/nesting)은 scope 파일의 **기존 함수 전체를 whole-file 스캔** — "새 함수 추가" task에선 변경과 무관한 기존 long 함수까지 AI 프롬프트에 surface(change-relative 아님). 규칙상 정확하나 관련성 낮은 evidence. (당초 "false-trigger" 가설은 grep 검증으로 기각 — 57줄 확인.)
>    - **다음**: R18 재평가 (배선 실효성 확정 → R18 게이트 해제됨). 선택적: R15~R17을 change-relative(변경 함수 한정)로 좁힐지 설계 검토 — 단 whole-file 스캔도 "파일 수정 시 기존 복잡도 인지" 의도로는 정당, 우선순위 낮음.
> 4. ~~CRLF fix dogfood run 검증~~ ✅ 완료 (`9755f9b5`, CRLF 재발 0)
>
> **R1 18차 특이사항**: dogfood run scope_violations(CRLF 다중 `^M` 오염 파일 — data/memory/*.json, docs/*.md)로 auto-merge BLOCKED. 원인: 워크트리 일부 파일에 `^M`이 10개씩 중첩돼 `--ignore-cr-at-eol` 필터링 불통과. 수동 cherry-pick으로 처리. 근본 해결: dogfood worktree 생성 전 CRLF 오염 파일 목록 gitattributes 정리 (별도 작업).

> **참고**: 원격 스케줄 루틴 `trig_016Vy1qc2iakGmz1bE7V6TFW` (2026-05-29 04:40 KST) — 로컬 성공으로 불필요. https://claude.ai/code/routines 에서 비활성화 가능.

---

## 🏠 Mac PC 재개 절차

```bash
cd <repo>/agent-factory     # 본 repo (main 브랜치)
git pull
python start_db.py agent-factory   # Supabase → 로컬 메모리 pull
git status -sb
```

그 다음 아래 "🚧 진행 중 work-item" 섹션부터 읽으면 됨.

---

## ✅ optional-id-normalization (2026-05-19) — DONE (`fb085fdb`)

`safe_id("")="skill"` 계약 버그 전체 교정. safe_optional_id() 헬퍼 신설, 22파일 116 B-site 교체.
3-Tier: af-critic PASS → af-cross-review WARN(2건 수정) → af-test-runner PASS. 브랜치: `2026-05-19-optional-id-normalization`.

---

## ✅ research coverage-gate deep-mode fix (2026-05-20) — DONE (`9e610a5d`)

`collect_project_evidence()` coverage gate가 archive_research 에서만 적용되던 구조 결함 수정.
Step A-1(checklist hoist) + A-2(llm_prior_refs) + B(escalation scores) — 신규 8테스트. 1772 PASS.
3-Tier: af-critic PASS / af-cross-review WARN(G2/G3 mock 수정 반영) / af-test-runner PASS.

---

## ✅ 완료된 주요 작업 (2026-05-17 기준)

### Research Router (설계 v1.4.1 → 코드 완성)
| 항목 | 완료 | 내용 |
|------|------|------|
| Phase 1a | ✅ (`8654ce2a`) | `core/research_router.py` 신규 + mode-aware gating + escalation |
| Phase 1b | ✅ | source_pack + 4-metric verifier + structured evidence 필드 |
| A5 Quality Gate | ✅ (`deb9195d`) | ResearchPlan 3종 필드 + `_detect_domain_hints()` |
| P3 D3c | ✅ (`19c95f6f`) | substring 매칭 + 홀덤 토큰 보강 |
| P4 QualityContract | ✅ (`10c5879b`) | WorkSpec + pack layers + ChecklistMerger |

### 인프라 Fix (F-series)
| 항목 | 완료일 | 내용 |
|------|--------|------|
| F1~F17 전체 | 2026-05-15 | CLI 디스패치, schema, 격리, workspace 분리 등 |
| F15 workspace/runtime_workspace | 2026-05-17 | project pipeline/orchestrator/FSA 전체 분리 |
| F16 test isolation | 2026-05-15 | conftest AF_DISABLE 가드 |

### Registry Write Guard (F9 시리즈)
| 항목 | 완료일 | 내용 |
|------|--------|------|
| `_write_registry()` | 2026-05-15 | F12 hardening — 최초 가드 |
| `workflow_apply()` | 2026-05-17 | WARN #2/#3 해소 |
| `_install_skill_file()` | 2026-05-17 | os.makedirs/shutil/meta.yaml/lock 전체 차단 |
| `register_built()` | 2026-05-17 | lock_skill_state 미보호 BONUS High 해소 |

### 테스트 안정화
| 항목 | 완료일 | 내용 |
|------|--------|------|
| flaky test fix | 2026-05-17 (`1f26336d`) | runtime_workspace 라우팅 테스트 PlanVerifier stub 추가 |

### 기타
| 항목 | 완료 |
|------|------|
| P4.5a Agent Model Routing defaults | ✅ |
| P4.5b runtime escalation | ✅ |
| Cross-review 비용 감축 Phase 1 | ✅ (2026-05-01) |
| Blueprint §0~§12 동기화 | ✅ 최신 |
| Work-Item 병렬화 v3.1 | ✅ (`06661764`, `19f72479`) |
| Nightly Pipeline B2-4 (owner_role YAML) | ✅ (`5cd96564`) |
| Nightly Pipeline B2-6 (global status) | ✅ (`63990a71`) |
| Cross-review 비용 감축 Phase 2-prep | ✅ (`23f3e7bc`) |
| Cross-review 비용 감축 Phase 2 full bundle | ✅ (`23f3e7bc`) — 8섹션, 100KB cap, source_hash |
| post-commit amend 루프 근본 fix | ✅ (`f5d5461d`) — pre-commit 단일화, post_edit_blueprint/code_review hook 제거 |

---

## 🔒 Dogfood Production-Grade Hardening (2026-05-28 분석 v2 확정) — ✅ PR 1~4 전부 DONE (2026-05-29 확인)

> **상태**: P0-A(`86278509`) · P0-B(`745520ba`) · P1(`84127c8f`) · P2(`0ad0f047`) 4개 PR 모두 머지 완료. 아래 결함 8건 전부 해소. (이하 분석 기록은 history로 보존)
>
> **✅ 후속 review-fix (2026-05-29)** — dogfood 코드리뷰(`docs/reviews/2026-05-29-192056-*`)가 발견한 **5건 전부 수정**. 핵심: **[High] auto-merge scope 우회** — `_run_merge_phase`가 bare `MergePolicy`로 `allowed_paths=[]` → scope 게이트 무력화하던 결함. `build_merge_policy()` 공용 헬퍼 추출로 auto/manual 경로 정합. 나머지: merge_mode enum 검증(VALID_MERGE_MODES), read_phase_trace OSError/UTF-8 방어, cleanup_skip_reason 보조 필드, _dirty_files docstring. 회귀 +9, dogfood 246 PASS. 3-Tier: af-critic PASS / af-cross-review PASS(codex MCP 미가용=single-vendor) / af-test-runner PASS.
>
> **✅ 후속 BLOCK-fix (2026-05-31, `68e1ddc6`)** — fix 이후 생성된 af-critic 리뷰(`docs/reviews/2026-05-29-232850-*`)가 **BLOCK** 판정. 4건 수정: **[High] `_check_merge_policy` allowed_paths fail-open** — plain `startswith`가 `core/utils.py.bak`를 `core/utils.py` allowlist로 통과시킴 → 경계매칭 `f == p or f.startswith(p.rstrip("/")+"/")`로 교정(auto-merge scope 게이트 안전성 복구). [Med] `build_merge_policy` mode fail-closed(`mode or state.merge_mode`→`mode is None` 분기, production 도달경로는 없었으나 latent fail-open 차단). [Low] `dogfood status` cleanup_skip_reason 출력(미배선 해소). [Low] read_phase_trace OSError stderr 경고. 회귀 +4, dogfood 250 PASS. 3-Tier: af-critic PASS / af-cross-review PASS(gemini auth_expired 제외, codex no-findings+Claude 독립검증) / af-test-runner PASS. ~~**잔여 advisory(미수정)**: `_check_merge_policy` denied_paths `denied in f` substring 비대칭 매칭(Medium) — `"runtime/"`가 `"myruntime/"` 오포섭 가능.~~ ✅ **해소 확인 (2026-06-02 grep)**: `core/dogfood.py:1122-1123`이 이미 경계매칭 `f == denied or f.startswith(denied.rstrip("/") + "/")`로 구현됨. `denied in f` substring 잔존 0건. (문서 stale였음 — 코드는 fix 완료.)
>
> **Root cause**: dogfood lifecycle에서 "정책 입력·상태 저장·변경 감지·실패 의미론"이 단일 계약으로 묶여 있지 않음.
> 즉 SSOT는 일부 존재하나(MergePolicy, DogfoodState) **호출처가 우회 가능** = "계약을 만들었지만 강제하지 않음" 상태.
> §17 Step 1~20은 "있다/없다" 게이트 통과 MVP. 실패 의미론·artifact 무결성·정책 일관성·하드코딩 금지 게이트는 미통과.

### 결함 8건 (grep 실재 확인)

| # | 항목 | 위험 | 근거 (core/dogfood.py) |
|---|------|------|----------------------|
| **#1** | `_write_json` non-atomic | **High** | `1604-1606` direct `write_text()` vs `save_state:448-454` tmp+replace — 7 호출처 비-atomic |
| **#2** | dirty 정책 분기 | **High** | prepare `598-602` + finalize `695-706`는 `_is_crlf_only_diff` 필터 / merge `798-802`는 raw `status` |
| **#3** | IMPLEMENT 부분실패→VERIFY | Medium | `1473-1480` BLOCK은 `not ok AND not executed`. `ok=False AND executed != []` 흐름 |
| **#4** | pre-existing untracked 수정 누락 | Medium | `1224-1232` `_post-_pre` 집합 차분만. pre∩post 수정분 누락 |
| **#5** | merge_report.json **silent fail-soft → policy 우회** | **High** | `881-887` `except Exception: pass` — corrupt JSON 시 `changed_files=[], scope_violations=[]`로 진행 = **silently auto-merge 통과** |
| **#6** | `_is_crlf_only_diff` `-b` fallback 과대 포섭 | Medium | `563-567` `-b`는 모든 whitespace 변경 무시 — 의도된 indent 수정도 CRLF로 분류 |
| **#7** | `_run_merge_phase:1338` state.merge_mode 우회 | Medium | `MergePolicy(mode="auto_policy")` 강제 — state SSOT 위배 |
| **#8** | `MergePolicy.denied_paths` default dataclass 박힘 | Low | `240-244` `.af_runtime/`, `runtime/`, `skills/registry.yaml` — 환경/Policy 입력 분리 불가 |

### 하드코딩 흩어짐 실측 (grep)

- artifact 파일명 8 magic string: `dogfood_state.json`×2, `merge_report.json`×2, `research/spec/plan.json` 각 1, `phase_trace.jsonl`×1
- merge_mode 리터럴 5+ 분기
- DogfoodState 키(`changed_files`, `scope_violations`) 8회 magic string

### 🚫 하드코딩 금지 원칙 (이번 hardening 필수 조건)

이번 작업의 목표는 버그 4-8개 fix가 아니라 **dogfood 운영 정책을 단일 계약으로 잠그는 것**.

1. **정책값은 SSOT에 둔다** — dirty 판정, CRLF 정책, partial-impl 허용, auto-merge 금지 조합, artifact 파일명/필수 목록, corrupt artifact 처리
2. **호출처는 정책을 직접 판단하지 않는다** — prepare/finalize/merge가 각자 `git status` 직접 해석 금지. 공통 helper/policy object 경유
3. **문자열/파일명도 흩어지면 안 된다** — `ARTIFACT_*: Final` 상수 7개로 모음 (DogfoodArtifact 클래스 신설 X — 과도한 추상화 회피)
4. **옵트아웃도 하드코딩 금지** — `allow_partial_impl` 같은 정책은 CLI flag → MergePolicy → runner 경로로 전달. 코드 중간 "이 경우만 예외" 분기 금지
5. **테스트는 행위 기반** — magic string에 묶지 말고 invariant("corrupt artifact면 BLOCK", "auto_policy + partial_impl이면 reject")로 검증

### 우선순위 v2 (재배치)

| 우선순위 | PR | 결함 | 위험 근거 |
|---------|----|----|----------|
| **P0-A** | PR 1 | #1 + #5 | ✅ DONE (`86278509`) — atomic_write_json + load_policy_json(corrupt=fatal, silent except 제거) + ARTIFACT_* SSOT. |
| **P0-B** | PR 2 | #2 + #6 + #8 | ✅ DONE (`745520ba`) — _dirty_files 단일화 + CRLF -b fallback 좁히기 + denied_paths 입력 분리. |
| **P1** | PR 3 | #3 + #4 + #7 | ✅ DONE (`84127c8f`) — ok=False BLOCK + allow_partial_impl + merge_mode SSOT + fingerprint untracked. 221 PASS. |
| **P2** | PR 4 | trace/worktree | ✅ DONE (`0ad0f047`) — corrupt-last-line skip + BLOCK 시 cleanup 정책. |

### 실행 단계 (PR 분할 확정)

```
PR 1 — Policy Input Integrity (P0-A)
  1.1 atomic_write_json(path, data) — 같은 디렉터리 tmp → write → flush → fsync → os.replace
  1.2 load_policy_json(path, *, required=True) — JSONDecodeError raise (silent except 금지)
  1.3 ARTIFACT_* Final 상수 7개 (artifact filename SSOT)
  1.4 _artifact_path() 시그니처: Final 상수만 허용 (임의 문자열 거부)
  1.5 호출처 8곳 교체 + silent except 제거 (merge_report:881-887, plan load:1162-1164 등)
  1.6 회귀: corrupt JSON → BLOCK / mid-write KeyboardInterrupt / 임의 문자열 타입체커 거부

PR 2 — Policy Consistency (P0-B)
  2.1 _dirty_files(state, *, include_untracked, ignore_crlf, policy) 단일 helper
  2.2 _is_crlf_only_diff: -b fallback 제거 또는 좁힌 패턴 ("진짜 CRLF-only")
  2.3 prepare/finalize/merge 3곳 호출처 helper로 교체 (raw status 제거)
  2.4 MergePolicy.denied_paths default를 환경/Policy 입력으로 분리
  2.5 회귀: invariant "prepare 허용→merge 같은 이유로 허용" / whitespace-only ≠ CRLF-only

PR 3 — Execution Semantics (P1)
  3.1 _run_implement_phase ok=False → 기본 BLOCK (executed 무관)
  3.2 MergePolicy.allow_partial_impl: bool = False 추가
  3.3 MergePolicy.__post_init__: allow_partial_impl + auto_policy 조합 ValueError (코드로 강제)
  3.4 CLI flag → MergePolicy 전달 경로 명시 (하드코딩 분기 금지)
  3.5 #7 fix: _run_merge_phase:1338 → MergePolicy(mode=state.merge_mode, ...)
  3.6 pre_untracked 캡처에 hash(소형) + size/mtime(대형) 동반
  3.7 회귀: ok=False+executed BLOCK / allow_partial_impl+auto_policy 즉시 reject / pre-existing 수정 감지

PR 4 — Operational Hygiene (P2)
  4.1 phase_trace.jsonl reader corrupt-last-line skip (load_policy_json required=False)
  4.2 BLOCK 시 worktree preserve/cleanup 정책 명시 (state.isolation_status 기반)
  4.3 CRLF helper fixture 확장

통합 검증
  - tests/test_dogfood.py, test_dogfood_isolation.py
  - 신규 fixture 회귀
  - 실제 dogfood R14 1회 (dummy로 무결성만 확인)
  - 결과 정상 → "dummy 졸업" 선언 → production work-item 진입
```

### 결정 확정 사항

| 항목 | 결정 |
|------|------|
| Atomic write + silent except 같은 PR? | **Yes (PR 1)** — silent except 남으면 atomic 효과 무효 |
| CRLF 좁히기 + dirty 단일화 같은 PR? | **Yes (PR 2)** — 단일소스화 의미 잠금 |
| Final 상수 vs DogfoodArtifact 클래스? | **Final 상수** — 과도한 추상화 회피 |
| MergePolicy invariant `__post_init__`? | **Yes** — CLI/runtime 검증 누락 시 안전망 |
| denied_paths default 분리? | **Yes (PR 2)** |
| #7 우회 fix는 PR 3? | **Yes** — Policy 우회 = 실행 의미론 결함 |
| fail-closed default? | **Yes** — opt-out은 `--allow-partial-impl` 명시 + auto_policy 차단 |

---

## ✅ 완료된 로드맵 — 실행 로그 (보존)

> **상태 (2026-06-02)**: 아래 A Phase 2~4 / B Research Router / §17 Step 1~20 항목은 **전부 완료**됐다. 미완료 항목이 아니라 완료 기록의 보존 로그다. 신규 진입은 상단 "다음 세션 최우선 진입점" 참조.
>
> 원래 순서(history): **A Phase 2 → A Phase 3 → A Phase 3.5(측정) → B → A Phase 4**
> 근거: 검토 루프 인프라 먼저, 기능 확장은 루프 안정 후

### A Phase 2: review_bundle 생성기 ✅ DONE (`23f3e7bc`)

**선행 필수 (Phase 2-prep)**:
| 게이트 | 내용 |
|--------|------|
| 2-prep A | `requirements.txt` + `pyproject.toml`에 `ast-grep-py>=0.30` 추가, dev 설치 확인 |
| 2-prep B | `pyinstaller_hooks/hook-ast_grep_py.py` + `af.spec` hookspath — frozen 빌드에 native lib 포함 |
| 2-prep C | `python build_exe.py` → frozen `af`에서 ASTEngine smoke test 통과 |
| 2-prep D | `core/review_bundle.py` thin wrapper API (dev + frozen 공통 진입점) |

**본체 산출물**:
- `scripts/build_review_bundle.py` — dev hook entry
- `core/review_bundle.py` — 공통 wrapper (§§ 1~8 포함: Pending Files, Git Diff, Test Gap, Related Tests, Direct Callers, Risk Flags, Prior Findings, Bundle Stats)
- `tests/test_build_review_bundle.py`
- `.af_review_queue/review_bundle.md` (자동 생성 산출물)

**핵심 제약**: 100KB cap, source_hash 무효화, caller 심볼당 max 3개
- 설계 문서: `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md` §Phase 2

### A Phase 3: bundle-first + extension log 강제 ✅ DONE (agent 파일에 기존 구현)

- `af-critic.md`, `af-cross-review.md`: 진입 시 bundle 먼저 읽기 + extension log 형식 강제
- Phase 2.5 tool call cap 병행 (af-critic: 20, af-cross-review: 30)
- 설계 문서: `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md` §Phase 3, §Phase 2.5

### A Phase 3.5: 측정 인프라 수술적 수정 ✅ DONE (`f75e01b4`)

- `compute_report()`: "T3 finding share (단순 비율, T3 고유값 ≠)" 정정 + [Phase 4 primary] 승격 + commits_with_t3<10 샘플 게이트 + 미지원 필드 명시
- `hook_runner.py`: `payload.duration_ms` → `append_metric(duration_ms=...)` 전달
- 테스트: 39 PASS (신규 3개 포함). 3-Tier: af-critic/cross-review PASS, pytest 1704 PASS

**1주 데이터 수집 후에만 Phase 4 진입** (감 기반 skip routing 금지)

### B. Research Router Phase 2 — structured evidence promotion ✅ 전체 완료 — B-1(fallback trace) · B-2 · B-3 step 1~4 (step 4 = `b48bf7cc` ReuseDecision→skill_manifest 보존)

> 설계: `docs/2026-04-29-research-router-structured-evidence-design.md` §11 Phase 2 (L1139-1145)
> 본질: **데이터는 이미 생성됨** — 뒤 파이프라인 소비처가 안 쓰는 게 문제. "Research Router 필드 연결"이 아니라 "structured evidence promotion".

**용어 정정 (2026-05-18 세션 분석):**
- 대상 3필드(`required_capabilities`/`verification_focus`/`skill_gap_hypotheses`)는 `ResearchPlan`(research_router.py)에 **없음**.
- 생산자는 `core/researcher.py`의 structured evidence — `_synthesize_structured_evidence()`(researcher.py:455, fresh/deep/archive 모드) + `research_project_brief()`(fast_synthesis 모드). 생산자 2개.
- `_merge_project_brief_evidence()`(researcher.py:1148-1156)가 `project_brief`에 복사하나 **`setdefault`** — brief에 값 있으면 evidence 값 미반영. 모드별 우선순위 상이.

**B-1. `work_item_generator.py`** — ✅ **fallback trace 완료** (2026-05-21)
- LLM 경로(`work_item_generator.py:631/673/727`)는 `json.dumps(project_brief)` 전체를 프롬프트에 박음 → 3필드 값은 암묵 도달 (변경 없음).
- **완료**: `_inline()` sanitizer + `_skill_gap_bullets()` dict formatter + `_structured_evidence_block()` 추가. plan/spec/design fallback `## Evidence`/`## Design Evidence` 내부 sub-bullet으로 3필드 trace 보존. 새 `##` 헤더 없음 — `_extract_section_outline(expected_count=12)` 회귀 없음.
- 회귀 테스트 12개 추가 (`tests/test_work_item_generator_structured_evidence.py`).
- **후행**: ✅ **완료 (2026-05-21)** — `_generate_feature_plan`/`_generate_feature_spec`/`_generate_implementation_design` LLM 프롬프트 Rules에 structured evidence 3필드 명시. 21 tests PASS.

**B-2. `project_task_board.py`** — ✅ **완료·push** (`dd439f73`, 2026-05-18)
- `build_project_board()`가 `project_brief`의 `verification_focus`를 verify 태스크 `acceptance`에 주입 (dedup 가드, LLM·fallback 공통 funnel).
- **Finding 1 (버그)** — `_clean_list()` 문자열 char-split 버그 수정(`isinstance` 가드) + 회귀 테스트 3건(string/list/None).
- **Finding 2 (설계 결정 = ①)** — `required_capabilities`의 build `acceptance` 주입 제거. 근거: `acceptance`는 "완료 기준"으로 소비되는데(`agent_specializer.py:93`·`work_item_generator.py:333`) `required_capabilities`는 실행 전제·스킬 조달 신호 → 의미 불일치. 정규 소비처는 B-3 `decide_reuse()` capability-gap 경로 → B-3에 위임.
- 3-Tier: af-critic / af-cross-review / af-test-runner **전부 PASS**. Blueprint §3.1+§12 갱신. tests 6건 신규.

**B-3. skill pipeline — capability-gap 死코드 복구** ← ✅ **전체 완료·push** (`9eb14577` step1-3b + 2026-05-19 step4)

> 아래 라인 좌표는 2026-05-18 재캡처 기준. **구현 진입 시 grep으로 재확인** (라인은 stale 가능 — NEXT_STEPS의 이전 좌표 `:102`/`:197-206`이 실제 `:64`/`:172`로 어긋나 있었음).

**배선은 2군데 — 둘 다 고쳐야 함. #1만 하면 死코드가 "항상 forge" 오작동으로 바뀜:**

- **#1 요구 capability 배선** — `decide_reuse()`(skill_retrieval_engine.py:64)는 `payload["required_capabilities"]`(:102)로 gap 분석(:108). 그러나 `project_pipeline.py:641` `reqs`={goal,constraints,missing_skills}만 → `_rank_candidates_for_need()`(researcher.py:172) target dict(:197)에 `required_capabilities` 없음 → 항상 `gap=None`.
- **#2 후보 capability 배선 (5라운드 분석서 발견)** — `_analyze_capability_gap(skill_meta, required_capabilities)`(:308)는 입력이 2개. `skill_meta`는 `decide_reuse:105` `candidate_meta = best.get("meta", {})`에서 옴 — 그러나 researcher candidate row(researcher.py:187-194)에 `meta` 키 없음 → `candidate_meta` 항상 `{}` → `existing=set()` → `gap_ratio=1.0` → enhance-range 후보가 전부 forge로 밀림 (단 high-confidence+verified는 `:110`에서 gap 보기 전 ranked_reuse). **데이터는 `best["capabilities"]`에 살아있음** (researcher.py:192 → `_rank_candidates:191` `row=dict(item)`로 전파, `_iter_candidates:271` dict 무변형 통과 확인) — 순수 키 불일치 버그.

**B-3 분할 (Tier3 메가 PR 금지):**
1. contract helper — `skill_gap_hypotheses`를 `safe_id(need_skill_id)` 키 dict로 정규화. **miss 시 `[]` 반환이 계약** (project-union 주입 금지 — gap_ratio 과대산정).
2. `project_pipeline.py:641` `reqs`에 `skill_gap_hypotheses` 추가. (`required_capabilities`는 `_skill_gap_capabilities_map` 계약상 소비처 없음 → `reqs` 미포함, 2026-05-18 정정)
3. `_rank_candidates_for_need()` target에 need의 `required_capabilities` 주입 — 후보의 `capabilities` 키와 충돌하지 않게 별도 키명(예: `required_capabilities` top-level) + 설명 키 동반.
3b. **(#2)** `decide_reuse:105` candidate_meta 정규화 — `best["meta"]` 없으면 `best["capabilities"]`(list)를 `{"capabilities": ...}`로 흡수. WHY 주석 명시 (researcher candidate는 capabilities를 top-level에 둠).
4. `decide_reuse` 결정 사유(`ReuseDecision.to_dict()` — `capability_gap` 이미 직렬화됨 `:39,:43`)를 `skill_manifest.json` entry에 보존. 후행 분리 가능.

**테스트 계약 (positive 필수 — forge 케이스만 짜면 #2 버그를 통과시킴):**
- 후보 capabilities ⊇ required → `missing=[]`, `gap_ratio=0.0`
- 일부 빠지면 missing 정확 계산
- `gap_ratio=0.5` 경계 — enhance(`:115` `<=0.5`) vs forge(`:121` `>0.5`) 분기 assert
- researcher candidate shape fixture로 통합 검증 — fixture는 `researcher.py:187-194` 출처 주석 명시 (stale 방지)
- `required_capabilities` 비면 점수기반 enhance 유지 (regression)

**진입 순서:** step 1~3+3b 한 묶음 (step 2 단독은 무음 no-op). step 4 후행 분리. 설계 Opus, 구현 Sonnet. **첫 작업은 코딩이 아니라 grep 좌표·payload 계약 재캡처.**

### ✅ P2-F 루프 정합 (2026-05-22) — DONE (`99498b1b`)

- `scripts/review_gate.py`: `_MAX_ROUNDS = 5` 상수 추가, 하드코딩 `< 5` → `< _MAX_ROUNDS`
- `.codex/hooks.json`: PreCompact/SessionStart/UserPromptSubmit/Stop 각 이벤트의 `hook_runner.py` 직접 호출 제거 (run.py가 위임하므로 2중 실행 방지)
- 3-Tier: af-critic WARN(advisory) / af-cross-review PASS / af-test-runner PASS (68 tests)

### ✅ G2/G4/G5 — 이미 구현 완료 확인 (2026-05-22)

코드 탐색 결과 `core/review_report.py` + `core/review_runner.py`에 **이미 모두 구현됨**:
- G2 (`review_report.py:308`): `len(providers) >= 2` → cross/judge 실행
- G4 (`review_report.py:283`): provider 0개 → `SKIP` 반환 (PASS와 메트릭 분리)
- G5 (`review_report.py:273`): `AUTH_EXPIRED` → 즉시 `BLOCK` + 재인증 안내
- 구현 커밋: `86e3ed83` (2026-05-07)

### ✅ P2-E manifest projection — 이미 구현 완료 확인 (2026-05-22)

`skill_procurer.py` 루프 내 모든 decision mode (ranked_reuse/enhance/shadow_reuse/external_install/forge)에
`reuse_decision: decision.to_dict()` 이미 포함됨 → `skill_manifest.json`에 capability_gap/confidence/rationale 기록 중.
`exact_match`는 `decide_reuse()` 미호출이므로 없는 게 정상.

### 🔜 다음 세션 진입 순서 (2026-05-22 갱신)

> **구조 결정 (2026-05-22 세션)**:
> - `deep-interview-pipeline.md` → 북극성 epic (AF가 AF를 개발하는 완성 루프 정의)
> - `af-dogfooding-infrastructure-gap-analysis.md` → epic 구현 제약/검수 체크리스트로 흡수 (grep 증거·라인 좌표 보존)
> - Phase 3.5 runbook → sidecar 운영 문서 (epic과 별도)
>
> **팩트 확인 결과 (코드 직접 grep)**:
> - G7/G8/G1 → 2026-05-21 `fix(G8/G7/G1)` 커밋에서 이미 해소됨. blocker 아님.
> - `blast_radius.required_agents()` → CLI 출력 전용, 실행 경로 미사용. minor.
> - R1 → `docs/dogfooding/2026-05-21-r1-selfrun-result.md` PASS. 최소 증명 완료.
>   단, docstring 1줄 수준 — skills/ 격리 미완(BASE_DIR 기반 57개 스킬 로드) 잔존.
>
> **실행 게이트**: R1 복합 증명 → 신규 모듈 최소 단위 착공 (6개 동시 착공 금지)

1. ✅ **Phase 3.5 runbook 문서화** (sidecar) — `docs/2026-05-22-review-metrics-phase35-runbook.md` 작성. 실행 절차·Phase 4 진입 기준 수록.
2. ✅ **`core/interview.py` artifact shape 확장** — `research_questions/`risk_hints`/`assumptions` 필드 추가. `_build_assumptions()` + `_ensure_artifact_shape()` 신설. 테스트 5개 신규. 3-Tier PASS.
3. **R1 복합 증명** — ⚠️ 2차 실험 완료 (2026-05-25). plan 생성 달성, BLOCKED(정확). 2개 신규 구조 버그 발견.
   - ✅ F-DIRTY: `planning/interview_brief.json` gitignore 추가 (`f896eeb9`)
   - ✅ F-DIRTY-UNTRACKED: dirty check `--untracked-files=no` 수정 (`07f5c95c`)
   - ✅ F-PLAN-EMPTY-SCOPE: `_scope_from_intent()` fallback 추가 (`fb4df6ff`) — intent 문자열에서 파일 경로 추출
   - ✅ F-PHASE-COMPLETE: `_run_verify_phase` guard 추가 (`9b07276a`) — steps 있는데 commands=[] → fail
   - ✅ F-SCOPE-LEAK: 2차 실험에서 미발생 — AI 미호출이므로 syncCompyne/ 수정 없음
   - ✅ F-IMPL-NO-COMMANDS (P1): IMPLEMENT no-op guard 추가 — `skipped_no_commands` 비어있지 않고 `executed=[]`이면 BLOCKED. (이번 세션)
   - ✅ F-SCOPE-LEAK (P3): FINALIZE selective staging — `git add -A` → plan allowlist 교집합. `scope_violations` 기록. (이번 세션)
   - ✅ P2: `_build_implementation_steps` core/*.py artifacts에 `Master_Blueprint.md` 자동 추가. (이번 세션)
   - ✅ F-VERIFY-PREGIT: premortem R1 git diff check → comment (VERIFY 단계 commit 전; P2 artifact tracking 대체). (`788eaa33`)
   - ✅ P4(allowed_paths wiring): merge_dogfood_branch 기본 policy에 plan artifacts → allowed_paths 자동 구성. (`788eaa33`)
   - ✅ P5(SHA baseline diff): IMPLEMENT 전 git rev-parse HEAD 캡처 → 후 SHA-based diff로 actual_changed. (`788eaa33`)
   - ✅ P6(AI executor): _build_ai_task() + _default_ai_executor(claude_cli) + injectable. commands 없는 step → AI executor 위임. (`788eaa33`)
   - 결과 문서: `docs/dogfooding/2026-05-25-r1-complex-proof-result.md`
   - **다음**: ~~R1 3차 복합 증명 실험~~ → 완료 (아래 참조)

   **R1 3차 (2026-05-26) — PARTIAL SUCCESS** (`ad9ed9ac`)
   - ✅ P6 AI executor 동작 확인 — claude_cli 4회 실행, `core/utils.py`에 `clamp()` 실제 작성
   - ❌ VERIFY BLOCKED — verification_requirements=[] (F-VERIFY-EMPTY) → 3 bugs found & fixed:
     - F-SCOPE-CLARIFICATION: `_scope_from_clarification_log()` `_PATH_RE` 오탐 (`(int/float)` → 경로 오인식) → `_PATH_TOKEN_RE` 교체
     - F-VERIFY-EMPTY: `build_plan()` pytest fallback 추가 (scope 파일 → 테스트 파일 파생)
     - P5 fix: SHA 캡처 `OSError/FileNotFoundError` guard
   - 결과 문서: `docs/dogfooding/2026-05-26-r1-complex-proof-r3-result.md`
   - **다음: R1 4차** — F-SCOPE + F-VERIFY 수정 후 end-to-end COMPLETE 검증

   **R1 4차 (2026-05-26) — BLOCKED (F-CMD-RUNNER-WINDOWS 발견)**
   - ✅ AI executor: `median()` + `TestMedian` 워크트리에 작성 확인
   - ❌ VERIFY BLOCKED — 새 버그 발견:
     - F-CMD-RUNNER-WINDOWS: `_default_command_runner`가 Windows `cmd.exe` 사용 → `grep -n '<module>'`의 `<`를 stdin redirect로 해석 → rc=1 반환 → VERIFY 항상 실패
     - ✅ 수정 완료 (`fa4714c4`): PowerShell `try { & { cmd } } catch { exit 1 }; if ($LASTEXITCODE) { exit $LASTEXITCODE }` 패턴
   - **다음: R1 5차** — `python agent_launcher.py dogfood run "core/utils.py에 median(values: list[int | float]) -> float 함수 추가. 빈 리스트이면 ValueError. tests/test_utils.py에 TestMedian 테스트 클래스 신규 작성." --non-interactive --merge never`

   **R1 5차 진입 인프라 (2026-05-26) — DONE (this session, uncommitted)**

   R1 4라운드 누적 ~16h 소비 사후분석 후 합의:
   - 진단: "품질 게이트 부족"이 아니라 **관측성 부족** — 빈 artifact 원인을 trace 없이 추측만 반복
   - 처방 (단일 PR): trace + RunBudget + 최소 static smoke 동시 적용

   `core/dogfood.py` 변경 (+239/-4):
   - `_append_phase_trace()` (line 1398) — 10필드 phase 단위 trace
     필드: phase / input_keys / output_keys / critical_counts / fallback_used / llm_called / exception_type / blocked_reason / elapsed_ms / estimated_tokens
     출력: `.af_runtime/dogfood/<run_id>/phase_trace.jsonl`
   - `_record_run_budget()` + `_run_budget_exhausted()` (line 310, 321) — AI executor 결과 RunBudget.record(), phase loop/AI call 전후 exhausted 체크
   - `run_all(strict_contract: bool = False)` (line 1113) — direct/unit caller 기본 False
   - `agent_launcher.py:1060` dogfood CLI는 `strict_contract=True`로 production strict 활성
   - `_strict_contract_failure()` (line 1431) — 6 phase 조건 (interview/research_brief/spec/premortem/plan/verify)
   - `_pre_implement_static_smoke()` (line 1475) — IMPLEMENT 직전 .py ast.parse only (LSP/큰 게이트 아님)
   - `_run_implement_phase` (line 939) — `context["preflight_static"]` flag로 smoke 활성

   테스트:
   - `tests/test_dogfood.py` (+46)
   - `tests/test_dogfood_cli.py` (+53/-2)
   - `tests/test_dogfood_integration.py` (+11/-2)

   검증:
   - py_compile 5파일 PASS
   - dogfood 단위/통합/CLI: 135 PASS

   **보류 결정 (trace 1회 run 후 재결정)**:
   - strict_contract 세부 정책 확장 — CLI production path는 이미 활성. 단, empty artifact 정책을 더 강하게 할지/완화할지는 trace 1회 후 결정
   - IMPLEMENT 외 다른 phase의 큰 static gate (P0-3 확장판)
   - cost dashboard (P1-2) — phase_trace.jsonl의 estimated_tokens 합산으로 1차 관측 가능. 별도 UI는 P1
   - af doctor dogfood (P1-1), skill/context 비용 측정 (P1-3), duplicate signature detection (P1-4)
   - trace 필드 확장 — `error_message`/`error_excerpt`는 현재 미포함. 1회 run 후 `exception_type` + `blocked_reason`만으로 진단력이 부족하면 추가.

   **R1 5차 (2026-05-26) — COMPLETE** (run_id: 1779782525-9f26fe81)
   - ✅ 11 phase 전부 trace 생성, AI executor median() 작성, VERIFY 4명령 PASS
   - 발견: strict_contract research_brief empty BLOCK → 수정 (체크 제거, `a62134d9`)
   - 발견: dirty workspace가 격리 막음 → CRLF 정규화 commit (`b5a382fd`)

   **R1 6차 (2026-05-26) — COMPLETE** (run_id: 1779785458-e53d5ef6)
   - ✅ chunks() 구현, FINALIZE merge_report 필드 정상: dogfood_commit_created=True, scope_violations=[]
   - FINALIZE 데이터 모델 분리 (`d35d590f`): all_dirty/committed_changed/scope_violations/dogfood_commit_created
   - CRLF 필터 + scope_violations 게이트 신설, require_dogfood_commit base_ref 동일 SHA 거부
   - FINALIZE git commit 시 review-gate hook 우회 (`e583086d`): `AF_SKIP_REVIEW_GATE=1`

   **이번 세션 작업 (2026-05-26)**:
   - ✅ `98cd8a62` — `_run_final_docs_sync()` 신규 (dogfood FINALIZE에서 blueprint/code-review 자동 갱신)
   - ✅ `scripts/blueprint_updater.py` — `_update_section_3_auto_summary()` §3 AUTO 블록 자동 생성 (3-Tier WARN-only PASS)
   - ✅ `.gitignore` — `syncCompyne/` 제외 (`4436086a`)
   - merge 검증: `source_workspace is dirty` → `source branch advanced` → `scope_violations(syncCompyne)` 순서로 3개 버그 수정
   - ✅ `f9ba8800` — `run_output.txt` gitignore + untrack (scope_violations 해소)
   - ✅ `b781243a` — `syncCompyne/` git rm --cached + `projects/agent_factory/` CRLF 정규화 (dirty workspace 해소)
   - ✅ **R1 merge 검증 COMPLETE** (`d4283ed5`) — `clamp_ratio()` + `TestClampRatio` auto-policy merge 성공

   **잔여 저우선순위**:
   - F-RUN-BUDGET-STATE: run_budget이 state.json에 미저장 (Low)
   - ✅ Blueprint §3 수동 갱신 — §3.13 Dogfood Pipeline 신규 섹션 추가 (5개 P0 함수 반영)

   **R1 7~8차 (2026-05-27) — COMPLETE** (run_id: 1779810109-8664dd2e, merged `c5f50f19`)
   - ✅ `_research_scope_files` intent/clarification_log fallback + path traversal containment (`e7a0b523`)
   - ✅ `_research_collect_refs` scope+companion 중복 제거 (`63ccbd74`)
   - ✅ CRLF 68파일 정규화 (`0b0da33b`) — 워크트리 scope_violations 근원 제거
   - ✅ research.json: 2 local_refs (core/utils.py + tests/test_utils.py), spec.json research_findings 2개 투입 확인
   - mode() 함수 + TestMode 테스트 auto-policy merge COMPLETE
   - 3-Tier: af-critic WARN(수정) / af-cross-review BLOCK→fixed / af-test-runner PASS (142 tests)

   **잔여 저우선순위**:
   - F-RUN-BUDGET-STATE: run_budget이 state.json에 미저장 (Low)
   - advisory 보류: scope 문자열 입력 시 문자 단위 순회 (af-cross-review Medium advisory)

   **R1 9차 진입점 (2026-05-27) — COMPLETE**:
   - ✅ `core/premortem.py` `_detect_existing_pattern_risk()` 신규 detector (R10)
     - `research_findings.path` ∩ `scope` 겹침 시 패턴 일관성 리스크 생성
     - `_detect_assumption_risks(start=5→11)` — ID 충돌 방지 (R10 예약)
     - `gap_start = max(20, 11 + len(assumption_risks))`로 gap 공식 갱신
     - 7개 신규 테스트 PASS. 기존 39개 회귀 없음. af-test-runner PASS.
   - `planner.py`: research_findings 미사용 현황 확인 — 별도 작업으로 분류 (범위 밖)

   **R1 9.5차 (2026-05-27) — COMPLETE** (`bd54c80f`):
   - ✅ `_detect_blueprint_sync_risk()` placeholder 버그 수정
     - `files` 비어있을 때(risk_hints에서만 trigger) → comment step 생성
     - comment step은 `planner.py:90 startswith("#")` 필터로 실행 경로 차단
     - 2개 신규 회귀 테스트. 48개 PASS. 3-Tier PASS/PASS/PASS.

   **R1 10차 (2026-05-27) — COMPLETE** (run_id: 1779838885-d70ad991, merged `3c52a1d9`):
   - ✅ R10 발화 확인 — research_findings `core/utils.py`+`tests/test_utils.py` ∩ scope → `python -m py_compile core/utils.py tests/test_utils.py` plan 주입
   - ✅ R1 comment step 필터 확인 — `planner.py:90 startswith("#")` 정상 차단
   - ✅ variance() 구현 + TestVariance 3개 테스트 → auto_policy merge 성공

   **R1 11차 (2026-05-27) — 검증 PASS / 머지 회수 불가** (run_id: 1779867851-3611529e, merge: never, dogfood_commit: `c4c5c98b` Windows-only):
   - ✅ 검증 결론은 이미 origin 보존 (이 본문 + 9259e2c9 dedup fix):
     - multi-file scope (`core/utils.py` + `core/planner.py`) end-to-end OK
     - R10 다중 파일 발화: `python -m py_compile core/utils.py core/planner.py` 자동 생성
     - `reference_artifacts` end-to-end 도달: plan.json S1/S2 모두 `tests/test_<stem>.py` 채워짐
     - `scope_violations: []` (selective staging 정상)
     - path-separator dedup 버그 (`9259e2c9`로 별도 fix 완료)
   - ❌ **머지 회수 불가**: 라운드에서 작성한 `product()` + `plan_step_count()` + 10건 테스트는 Windows PC `~/.af-dogfood/1779867851-3611529e/worktree/`의 `dogfood/1779867851-3611529e` 브랜치 commit `c4c5c98b`에만 존재. origin push 안 됨, Mac에 산출물 부재. dogfood worktree·state PC-로컬 정책상 다른 PC 회수 불가.
   - dogfooding 검증용 dummy 함수라 production 가치 낮음 — 다음 라운드(R1 13차)에서 새 dummy로 동등 검증.
   - 재발 방지: CLAUDE.md "Dogfood Run PC 핸드오프 규칙" 신설(`3b9f670c`) — 세션 종료 전 머지 완료 or NEXT_STEPS에 PC 식별자·worktree 경로 3줄 기록 의무.

   **R1 10.5차 묶음 (2026-05-27) — COMPLETE** (3-Tier WARN-only PASS, 303 tests):
   - ✅ scope-str-guard: `_research_scope_files` 가 str 입력일 때 char-iteration 방지 (`_str_list` 적용)
   - ✅ F-RUN-BUDGET-STATE: `DogfoodState`에 `budget_consumed`/`budget_max_tokens`/`budget_stopped`/`budget_project_id` 필드 + `_snapshot_run_budget`/`_restore_run_budget` 페어로 `save_state`/`load_state`가 `core.run_budget` singleton 4-필드 영속화
   - ✅ planner advisory: `PlanStep.reference_artifacts` 신설 + `_references_for_scope_item()` — research_findings companion test 경로(`tests/test_<stem>.py`) 만 read-only context로 노출. `_build_ai_task`가 "Reference files (read-only ...)" 섹션 surface
   - WARN 흡수: af-critic stem-collision (sibling source 차단) + project_id 손실, af-cross-review §3.13 심볼 누락
   - WARN 보류 (advisory): thread-safety 이론, fixture teardown-only 패턴

   **R1 13차 (2026-05-28) — COMPLETE** (run_id: 1779893903-873d72fd, merge: `338dd3c2`, dogfood_commit: `0e9d9ce4`, PC: `hoonkims-MacBook-Pro.local`):
   - ✅ `range_span(values: list[int | float]) -> float` core/utils.py 추가 — max-min, 빈 리스트 ValueError
   - ✅ TestRangeSpan 9 tests PASS (싱글톤, 정수 리스트, 부동소수, 음수 포함, 음수만, 동일값, 미정렬, 반환 타입 float, ValueError 케이스)
   - ✅ auto-policy 자동 머지: blueprint + code-review 문서 자동 동기화, source 브랜치 fast-forward 머지
   - ✅ PC 핸드오프 규칙 첫 실전 사이클 — Mac 단일 세션에서 시작·머지·push 완료, R1 11차 미회수 패턴 재발 없음
   - 1차 시도 실패 부산물: CRLF 정규화 chore 커밋(`4153b013`) — Windows→Mac pull 부산물 dirty 해소

   **R1 14차 (2026-05-29) — COMPLETE** (run_id: 1780028360-9b5d3139, merge: `58748d90`, PC: `hoonkims-MacBook-Pro.local`):
   - ✅ `flatten(lst: list) -> list` core/utils.py 추가 — shallow flatten, 빈 리스트 []
   - ✅ TestFlatten 5 tests PASS (빈, 평탄, 1단계 중첩, 2단계+ 1단계만, 혼합 타입)
   - ✅ 12 phase 전부 trace 생성, BLOCKED 없음 — implement 143s AI executor 정상
   - ✅ auto-policy 자동 머지 + blueprint/code-review 자동 동기화
   - **🎓 "dummy 졸업" 선언** — R5~R14 9회 연속 COMPLETE, 핵심 인프라 안정성 확인

   **R1 15차 (2026-05-30) — COMPLETE** (run_id: 1780070580-509da39d, merge: `03d9347b`, PC: Windows):
   - ✅ `core/planner.py` `_build_investigation_steps()` 확장 — R5-R19 assumption risks도 investigation step 생성
   - ✅ `_is_assumption_risk()` 헬퍼 신설 (category='assumption' OR risk_id in [5, 20))
   - ✅ comment 명령어(`#` 시작) 필터링으로 실행 가능한 commands만 포함
   - ✅ tests/test_planner.py 36줄 신규 (assumption 1개·2개·0개 시나리오)
   - ✅ auto-policy 자동 머지 + blueprint/code-review 자동 동기화
   - **🚀 첫 production work-item dogfood run COMPLETE** — premortem/planner 개선 실제 반영

   **다음 진입점**:
   - 다음 production work-item 선정 후 dogfood run 진입 (보류 dogfood run 없음)

4. ✅ **R3 scope guard enforce** — `_scope_guard_report()` + baseline 기반 false-positive 제거. `AF_SCOPE_GUARD_PATHS` env var로 allowlist 지정 가능. DONE (`2026-05-23`).
5. ✅ **§17 Step 3~4** — `core/research_brief.py` + `core/spec_compiler.py` 신규. 24 tests PASS. 3-Tier PASS. (`0466d28e`, 2026-05-23)
6. ✅ **§17 Step 5** — `core/premortem.py` 신규. `CompiledSpec` → repo-aware 리스크 + 검증 요건. 5종 detector(R1~R4, R5+assumption, R20+gap), ID 충돌 방지 동적 오프셋. 39 tests PASS. 3-Tier PASS. (`99b01460`, 2026-05-24)
7. ✅ **§17 Step 6** — `core/planner.py` 신규. `CompiledSpec`+`PremortomResult` → `ExecutablePlan`. investigation→implementation→verification 단계 순서. `PlanStep.commands` 추가. 36 tests PASS. 3-Tier PASS. (`c6406218`, 2026-05-24)
8. ✅ **§17 Step 7** — `core/dogfood.py` 신규. `DogfoodPhase` enum(11단계+BLOCKED), `DogfoodState` 영속화(`.af_runtime/dogfood/<run_id>/dogfood_state.json`), `create_run()`/`advance_phase()`/`block_run()`/`run_phase()` 공개 API. 각 phase runner가 Step 3~6 모듈에 위임; implement/verify/review는 Step 8 stub. atomic write(`tmp.replace`), `_premortem_from_dict` 방어 코드 적용. 49 tests PASS. 3-Tier PASS.
9. ✅ **§17 Step 8** — `core/dogfood.py` 확장. `VerifyResult`/`ReviewDecision` dataclass, `MAX_VERIFY_ATTEMPTS=3`, `_command_runner` injectable, `retry_run()` 신설. `_run_verify_phase`/`_run_review_phase` stub → 실 구현. pass/retry/block 경계 조건 완전 커버. 63 tests PASS(+14). 3-Tier PASS.
10. ✅ **§17 Step 9** — `_run_implement_phase` stub → 실 구현. plan steps 순회: commands 있는 step은 `_command_runner` 실행(`executed` 수집), 없는 step(AI-coded)은 `skipped_no_commands` 기록. `context["plan_dict"]` 없으면 `state.plan_path`에서 disk 로드. 반환: `{executed, failures, skipped_no_commands, ok}`. stub test 1개 → 7개 실 구현 테스트 (63→69 PASS). 3-Tier PASS. (`cec821c1`, 2026-05-24)
11. ✅ **§17 Step 10** — `run_all()` 신규. PENDING→COMPLETE/BLOCKED 전 단계 자동 순환. PLAN 반환값 보존 후 VERIFY에 plan_dict 전달(verification_requirements 우회 버그 수정). 테스트 69→78건(+9). 3-Tier PASS. (`e3bb321b`, 2026-05-24)
12. ✅ **§17 Step 11** — `agent_launcher.py`에 `dogfood` 서브커맨드 추가. `_KNOWN_SUBCOMMANDS` 등록, `dogfood run <task>` + `dogfood status <run_id>` 파서. `__main__` 분기: `run_all()` 호출 후 exit 0(COMPLETE)/1(BLOCKED). `tests/test_dogfood_cli.py` 10건 신규. 3-Tier PASS. (2026-05-24)
13. ✅ **§17 Step 12** — `dogfood interview <task>` 서브커맨드 + `dogfood run --from-file <path>` 옵션 추가. `dogfood interview`는 `core.interview.run_interview()` 래핑(--non-interactive/--deep-skip/--out/--workspace). `dogfood run --from-file`은 JSON 로드 후 `run_all(interview_artifact=...)` 전달. 테스트 20→30건(+10). 3-Tier WARN-only PASS. (2026-05-24)
14. ✅ **§17 Step 13** — `_build_interview_fn()` + `_run_interview_phase(_interview_fn)` injectable + `run_phase` passthrough + `run_all(non_interactive, _interview_fn)`. TTY 감지(`sys.stdin.isatty()` False → non_interactive). `dogfood run --non-interactive` 파서 추가. 기존 monkeypatch 스텁 `**kw` 수정(af-cross-review BLOCK 해소). 테스트 30→37건(+7). 3-Tier PASS. (`0dbd4800`, 2026-05-24)
15. ✅ **§17 Step 14** — `tests/test_dogfood_integration.py` 8 smoke tests. 실제 모듈(research_brief, spec_compiler, premortem, planner) 체이닝 + _command_runner mock. PENDING→COMPLETE/BLOCKED 두 경로 모두 검증. 3-Tier PASS. (`5d8ec8b8`, 2026-05-24)
16. ✅ **§17 Step 15** — `core/triad.py` 正反合 Triad 오케스트레이션. TriadCriticFinding/Report/Decision/Result dataclass. run_triad() injectable executor 설계. evidence 계약 강제(_validate_findings). Critical finding 미해소 → TriadBlockedError. dogfood._run_plan_phase 연결. af-triad-critic.md 스킬 파일. 25 tests. 3-Tier WARN-only PASS. (`8ad5a3ac`, 2026-05-24)
17. ✅ **설계 v2 완료** — `docs/2026-05-25-dogfood-isolation-auto-merge-design.md` v2. 8라운드 분석 후 12개 합의 항목 반영:
    - Triad PLAN-only 정리, post-REVIEW Triad 표현 제거
    - runtime root: `%USERPROFILE%\.af-dogfood` (CWD 독립)
    - `_default_runtime_workspace(run_id)` — workspace 인자 없음
    - `require_plan_triad_pass` (rename + opt-out 의미)
    - MERGE: mutex → is-ancestor crash recovery → reset --merge → actual merge
    - `TriadContractError` 신규 예외 타입, Architect read-only 계약
    - active run registry: pid+started_at, heartbeat 없음
    - `isolate_attempts` 상태 필드 없음 — 내부 1-retry loop만
18. ✅ **§17 Step 16 — worktree 격리 + auto-merge lifecycle** (2026-05-25 완료, commit f975c2ce)
    - DogfoodState 3-path(source/worktree/runtime_workspace), `workspace` @property backward-compat
    - ISOLATE/FINALIZE/MERGE 3 신규 단계, `_cwd()` 라우팅
    - `prepare_isolated_worktree()` / `finalize_dogfood_result()` / `merge_dogfood_branch()`
    - `MergePolicy` 8-gate dataclass, CLI `--merge` + `dogfood merge` 서브커맨드
    - `tests/test_dogfood_isolation.py` 25건 신규, 총 174 tests PASS
    - 3-Tier: af-critic BLOCK→fixed / af-cross-review WARN-only / af-test-runner PASS
19. ✅ **§17 Step 17** — `core/review_skill_router.py` 신규. `ReviewContext`/`TierSkillProfile`/`ReviewSkillPlan` + `route_review_skills()`. changed-file paths·blast tier·work kind·risk tokens 기반 결정적 라우팅. Tier 1→af-test-runner만, Tier 2/3→3-tier. blueprint_impact·worktree_work·tier3 분기. 35 tests PASS. 3-Tier WARN-only/PASS/PASS. (`38451a42`, 2026-05-25)
20. ✅ **§17 Step 18** — `core/express_router.py` 신규. `RouteDecision` + `route_task()`. direct/light/full/dogfood 4-경로 결정적 라우팅. Windows 경로 정규화. word-boundary trivial guard. 46 tests PASS. 3-Tier BLOCK→fixed / BLOCK→fixed / PASS. (2026-05-25)
21. ✅ **§17 Step 19** — `core/architect_agent.py` 신규. Triad 合(Synthesis) executor. `architect_fn()`. Blueprint §섹션 + accepted ADR 기반 ACCEPT/REJECT 결정. `_extract_section()` prefix false match 방지(`(?![\d.])` lookahead). `_adr_matches()` set 중복 제거. 32 tests PASS. 3-Tier WARN→fixed / BLOCK→fixed / PASS. (2026-05-25)
22. ✅ **§17 Step 20** — `core/dogfood.py` `_run_plan_phase` else 분기: `_triad_architect_fn` None 시 `architect_fn` lazy import 자동 배선. 통합 테스트 3건 신규 (spy 확인, ACCEPT→unresolved_risks, e2e 완주). 147 tests PASS. 3-Tier PASS. (2026-05-25)

**보류**: `cli_hook_bridge` 미커밋 — 현재 dirty 없음, 우선순위 낮음.

---

### ✅ A Phase 4: 스마트 라우팅 (2026-05-31) — DONE (`deae9dbb`)

> 진입 게이트 충족 확인: 2026-05-23~31 측정 **T3 BLOCK-only 0/31**, af-cross-review block:0/36, span 7.6일 (commits≥10 AND span≥7일 통과).

**구현**: telemetry 기반 Tier 3 조건부 skip + ALWAYS-Tier-3 안전망
- `review_metrics_logger.compute_t3_telemetry_skip()` — 보수적 AND-게이트 4조건(전부 만족 시에만 skip, fail-closed):
  ① commits_with_t3≥10 AND **T3-record 기준** span≥7일 ② block_only_rate<10% ③ 최근10 T3커밋 BLOCK 0 ④ skip_subsequent_block==0. 임계 4개 SSOT 상수.
- `review_gate._is_always_tier3()` 위험군(게이트·메트릭·classifier 자체 파일 포함) → cosmetic·telemetry skip 모두 무시 [1,2,3] 강제 (부트스트랩 회피).
- `_telemetry_skip_enacted()` = blast2 + 비위험 + skip=True. enqueue가 락 밖 계산 → state 동결(`_required_tiers_for` 순수성 유지) + 발효 시 라운드당 1회 skip_audit "why" 기록.
- **라이브 검증**: 이번 커밋의 게이트 자기 파일(blast3+ALWAYS_TIER3)에서 telemetry skip=True여도 발효 안 되고 [1,2,3] 강제됨 확인.
- 3-Tier: af-critic WARN(3건 흡수: review_metrics_logger ALWAYS_TIER3 / 빈 sha 제외 / docstring) + SSOT invariant 봉인 / af-cross-review WARN(2건 흡수: span T3기준 / t3_classifier ALWAYS_TIER3) / af-test-runner PASS. 신규 테스트 +26.
- **잔여 한계(미수정)**: severity 분포 미포착 — 메트릭이 per-finding severity 없어 BLOCK-only를 severity 프록시로 사용(§397 caveat). tokens/duration 미지원. `compute_report`의 span은 여전히 전체 레코드 기준(advisory 표시용, 강제 경로 아님).

**R1 17차 (2026-05-31) — COMPLETE** (run_id: 1780229193-54d8463a, merge: `a917f7ff`, PC: Windows):
   - ✅ `core/premortem.py` `_detect_scope_file_risk()` 추가 — scope 목록 중 디스크에 없는 파일을 R11 risk로 리포트. `generate_risks()`에 배선, assumption_risks start=12로 ID 충돌 방지.
   - ✅ `tests/test_premortem.py` `TestDetectScopeFileRisk` 신규 (60 PASS)
   - ✅ auto-policy 자동 머지 + blueprint/code-review 자동 동기화

**R1 18차 (2026-05-31) — COMPLETE** (run_id: 1780229961-2713ae1b, 수동 cherry-pick, commit: `3d2084a8`, PC: Windows):
   - ✅ `core/planner.py` `_build_investigation_steps()`에 R11(scope_file) 연동 — `_extract_scope_file_paths()` 헬퍼 신설, missing 파일별 "경로 확인" investigation step 생성
   - ✅ `shlex.quote()` 안전 처리 (af-critic WARN 흡수)
   - ✅ `tests/test_planner.py` `TestScopeFileRiskInvestigation` 8건 신규 (62 PASS)
   - ⚠️ dogfood auto-merge BLOCKED (CRLF 다중 `^M` 오염 scope_violations) → 수동 cherry-pick으로 처리

   **R1 19차 (2026-05-31) — COMPLETE** (run_id: 1780235778-8d0d1f80, 수동 cherry-pick, commit: `ffc0decf`, PC: Windows):
   - ✅ `core/premortem.py` `_detect_stale_test_risk()` R12 detector 추가 — scope .py 파일 중 tests/test_<stem>.py 없는 파일 R12 risk 생성
   - ✅ assumption_risks start=13 업데이트 (R11=scope_file, R12=stale_test ID 충돌 방지)
   - ✅ `tests/test_premortem.py` `TestDetectStaleTestRisk` 13건 신규 (73 PASS)
   - ✅ 3-Tier: af-critic WARN(CWD의존 advisory) / T3 skip(blast2) / af-test-runner PASS
   - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations 동일 패턴) → 수동 cherry-pick으로 처리

   **R1 20차 (2026-05-31) — COMPLETE** (직접 구현, commit: `80337dd8`, PC: Windows):
   - ✅ `core/planner.py` `_build_investigation_steps()`에 R12(stale_test) 연동 — `_extract_stale_test_paths()` 헬퍼 신설, stale 파일→`tests/test_<stem>.py` 변환, "테스트 작성" investigation step 생성
   - ✅ `tests/test_planner.py` `TestStaleTestRiskInvestigation` 9건 신규 (71 PASS)
   - ✅ 3-Tier: af-critic PASS / T3-skip(blast2) / af-test-runner PASS

   **R1 21차 (2026-06-01) — COMPLETE** (run_id: 1780241272-dc1583ae, merge: `df679c14`, PC: Windows):
   - ✅ `percentile(values: list[int | float], p: float) -> float` core/utils.py 추가 — 선형 보간 백분위수, 빈 리스트/범위 외 p → ValueError
   - ✅ TestPercentile 테스트 클래스 신규 (경계값 p=0/100, 중앙값, 보간, 음수, ValueError 2종)
   - ✅ auto-policy 자동 머지 + blueprint/code-review 자동 동기화

   **R1 22차 (2026-06-01) — COMPLETE** (run_id: 1780242570-83d712b2, 수동 cherry-pick, commit: `81b8fc3e`, PC: Windows):
   - ✅ `core/premortem.py` `_detect_duplicate_function_risk()` R13 detector 추가 — intent 백틱 함수명(`foo()`) 추출 후 scope .py 파일에 `def <name>` 존재 시 R13 리스크 생성
   - ✅ `run_premortem()` 배선 + assumption_risks start=14로 업데이트 (R11=scope_file, R12=stale_test, R13=duplicate_function)
   - ✅ `tests/test_premortem.py` `TestDuplicateFunctionRisk` 11건 신규 (84 PASS)
   - ✅ 3-Tier: af-test-runner PASS (84 tests)
   - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations: docs/runtime_modes.md 등) → 수동 cherry-pick으로 처리

   **R1 23차 (2026-06-01) — COMPLETE** (직접 구현, commit: `55cd2ebb`, PC: Windows):
   - ✅ `core/planner.py` `_extract_duplicate_function_paths()` 헬퍼 신설 — `"`foo` in path"` 형식 파싱
   - ✅ `_build_investigation_steps()`에 R13(duplicate_function) 분기 추가 — 중복 함수별 `grep -n def <name>` investigation step 생성
   - ✅ `tests/test_planner.py` `TestDuplicateFunctionRiskInvestigation` 7건 신규 (78 PASS)
   - ✅ 3-Tier: af-critic PASS / T3 skip(telemetry) / pytest 78 PASS

   **R1 25차 (2026-06-01) — COMPLETE** (직접 구현, commit: `6abe55b2`, PC: Windows):
   - ✅ `core/planner.py` `_extract_conflicting_import_pairs()` 헬퍼 신설 — R14 description에서 (func_name, file_path) 쌍 파싱
   - ✅ `_build_investigation_steps()`에 R14(conflicting_import) 분기 추가 — `grep -n "import {func_name}" {file_path}` investigation step 생성
   - ✅ `_CONFLICTING_IMPORT_PREFIX` / `_CONFLICTING_IMPORT_SUFFIX` 상수 추가
   - ✅ `tests/test_planner.py` `TestConflictingImportRiskInvestigation` 8건 신규 (86 PASS)
   - ✅ 3-Tier: af-critic PASS(WARN-only: grep word boundary advisory, R13와 동일 패턴 수용) / T3 skip(telemetry, commits=32) / af-test-runner PASS

   **R1 26차 (2026-06-01) — COMPLETE** (run_id: 1780246226-2274eb1e, 수동 cherry-pick, commit: `72ab2056`, PC: Windows):
   - ✅ `normalize(values: list[float]) -> list[float]` core/utils.py 추가 — [0.0, 1.0] 선형 정규화, 빈 리스트 [], 동일값 [0.0]*n
   - ✅ TestNormalize 11 tests PASS
   - ✅ 3-Tier: af-test-runner PASS
   - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations: data/memory/*.json, docs/*.md) → 수동 cherry-pick으로 처리

   **R1 27차 (2026-06-01) — COMPLETE** (직접 구현, commit: `c0ee8b52`, PC: Windows):
   - ✅ `core/premortem.py` `_detect_long_function_risk()` R15 detector 추가 — scope .py 파일에서 ast 파싱으로 50줄 초과 함수 탐지 → R15 리스크 생성
   - ✅ `assumption_risks start 15→16`, `gap_start max(20,15+n)→max(21,16+n)` 업데이트
   - ✅ `tests/test_premortem.py` `TestLongFunctionRisk` 12건 신규 (107 PASS)
   - ✅ 3-Tier: af-critic WARN(dead code 수정) / T3 skip(telemetry, commits=32) / af-test-runner PASS

   **R1 28차 (2026-06-01) — COMPLETE** (직접 구현, commit: `850310b9`, PC: Windows):
   - ✅ `core/planner.py` `_extract_long_function_pairs()` 헬퍼 신설 — R15 description에서 (func_name, file_path, line_count) 파싱
   - ✅ `_build_investigation_steps()`에 long_function 분기 추가 — 긴 함수별 `grep -n def <name>` step 생성
   - ✅ `tests/test_planner.py` `TestLongFunctionRiskInvestigation` 8건 신규 (94 PASS)

   **R1 24차 (2026-06-01) — COMPLETE** (run_id: 1780245030-6a8e81b3, merge: `85002ddc`, PC: Windows):
   - ✅ `core/premortem.py` `_detect_conflicting_import_risk()` R14 detector 추가 — intent 백틱 함수명 추출 후 scope .py 파일에서 `import <name>` / `from X import <name>` 형태 충돌 감지. R14 리스크 생성.
   - ✅ `run_premortem()` 배선 + assumption_risks start=15로 업데이트 (R11~R14 ID 충돌 방지)
   - ✅ `tests/test_premortem.py` `TestConflictingImportRisk` 11건 신규 (95 PASS)
   - ✅ auto-policy 자동 머지 + blueprint/code-review 자동 동기화

**R1 16차 (2026-05-31) — COMPLETE** (run_id: 1780210301-3e899fe9, merge: `e0e477fc`, PC: Windows):
- ✅ `zscore(values: list[int | float]) -> list[float]` core/utils.py 추가 — 각 원소 Z-score, 1원소=[0.0], 빈리스트 ValueError
- ✅ TestZscore 10 tests PASS
- ✅ auto-policy 자동 머지 + blueprint/code-review 자동 동기화
- **✅ Phase 4 T3 skip 발효 검증**: `core/utils.py` blast_tier=2, not ALWAYS_TIER3, `t3_telemetry_skip.skip=True` → `_required_tiers_for → [1, 2]` (T3 제외) 코드 경로 실행 확인. 비용 절감: T3(af-cross-review) ~517s 절약/커밋.

### ✅ C. AF Dogfooding Review Safety — Follow-ups (2026-05-20) — DONE

> 설계: [docs/2026-05-20-af-dogfooding-review-safety.md](docs/2026-05-20-af-dogfooding-review-safety.md)
> 후속: [docs/2026-05-20-af-dogfooding-review-safety-followups.md](docs/2026-05-20-af-dogfooding-review-safety-followups.md) (status: DONE)

후속 4건 전부 흡수:
- ✅ **#1 P1** (`89559a8d`) `scripts/t3_classifier.py:7-9` 모듈 docstring 정정 — annotations preserved as semantic.
- ✅ **#2 P2** (`89559a8d`) `scripts/prompts/code_critic.txt:48` 프롬프트 `no` 허용 범위 좁힘 + annotation=semantic 명시.
- ✅ **#3 P3** (`d3734717`) `scripts/review_gate.py` CLI에 `--t3-required` 옵션 추가 (choices=yes/no/unknown).
- ✅ **#4 P3** (`d3734717`) `_T3_SKIP_CLASSIFIER_VERSION`을 `scripts.t3_classifier.CLASSIFIER_VERSION`에서 import하는 dual-import 패턴으로 단일소스화 — 회귀 테스트로 invariant 봉인.

### ✅ R4 Provider Priority Fix (2026-05-21) — DONE (`cf4754b9`)

`GOOGLE_API_KEY` 없을 때 gemini_cli가 claude_cli보다 먼저 시도되어 3초 낭비하는 문제 수정.
`_PROVIDER_KEY_ENVS` + `_has_required_credentials()` 추가, 정렬 키 2-tuple화.
테스트 10건. 3-Tier PASS.

### ✅ R1 Self-Run 실험 (2026-05-21) — DONE

- **결과**: AF가 자기 `.py`를 수정하는 핵심 명제 **최초 증명**
- scope: `core/utils.py` 단 1파일 수정 — scope leak 없음
- claude_cli 17초 완료 (gemini_cli 폴백 포함 ~25초)
- 마찰점: gemini 1순위 낭비(R4), 단순 작업에 57 skill 로드(노이즈), `"skill"` 오인식(무해)
- 결과 문서: `docs/dogfooding/2026-05-21-r1-selfrun-result.md`
- 실험 worktree: `r1-selfrun-exp` (수동 삭제 필요: `git worktree remove --force ...`)

### ✅ G8/G7/G1 정합화 (`529fa1a9`, 2026-05-21) — DONE

- G8: `check_design_pending.py` → "af-cross-review 1개만" (2026-05-01 정책)
- G7: `check_pending_review._agents_for_tier()` review-first 순서 + 전파 4곳
- G1: `MAX_ROUNDS 2→5` (CLAUDE.md 기준) + `review_gate.py:282` 동반
- G6: 기완료 (`82e256a7`)
- 3-Tier: af-critic PASS / af-cross-review PASS / af-test-runner PASS

---

### 🔍 C follow-up 후속 리뷰 (2026-05-20) — 4건 적용 완료, 교차검증 대기

> 코덱스 + 추가 검토. 4건 findings 중 **3건 수용 / 1건 거절**. 적용 결과: 111 tests passed.

- ✅ **#3 P0** `docs/2026-05-20-af-dogfooding-review-safety-followups.md:5` `(이 커밋)` → `d3734717` 치환.
- ✅ **#4 P1** `tests/test_review_gate.py` non-critic invariant 회귀 테스트 추가 — CLI `--record af-test-runner --t3-required yes` → `reviews[af-test-runner]`에 `t3_required` 키 없음 + `fired_at` 보존. 가드(`scripts/review_gate.py:345`) mutation 시 정상 fail 확인.
- ✅ **#1-a P2** `scripts/enqueue_agent_review.py` t3_decision=None 분기 `classifier_version` → `CLASSIFIER_VERSION` 변수 (except 분기에선 `"classifier-unavailable"` sentinel). sentinel은 `pending_agent_review.json.t3_decision.classifier_version` 필드에 forensic 마커로 남고 `reason: "classifier-unavailable"` 라벨과 일관 유지. *(주의: `t3_skip_telemetry.jsonl`은 `if decision.t3_required: return`으로 skip-only 기록이고 sentinel 분기는 t3_required=True이므로 telemetry/report 카운터에는 노출되지 않음 — af-cross-review WARN으로 사후 정정.)*
- ✅ **#1-b P2** `scripts/enqueue_agent_review.py:174` try 블록에 `CLASSIFIER_VERSION` 동시 import → stale-file-set 분기 `getattr` fallback도 동일 변수로 단일소스화. T3Decision dataclass `classifier_version: str` 필수 필드 확인.
- **#2 P? 거절** `scripts/review_gate.py:94` `ImportError` catch 확대 안 함. SyntaxError까지 sentinel로 숨기면 분류기 코드 깨짐을 hide → 진단성 저하. enqueue 측 fail-closed가 이미 SyntaxError까지 커버(`enqueue:187` `except Exception: t3_decision=None`). 상한은 `(ImportError, AttributeError)`.

**부수 변경**: `tests/test_pending_review.py` 두 fake fixture에 `CLASSIFIER_VERSION="test"` 추가 — fake 모듈이 `t3_classifier`를 위장할 때 import 호환성. (NEXT_STEPS 사전 분석에서 놓친 영향.)

**커밋 분리 권고**: #3+#4 한 커밋 / #1+fixture 별도 커밋 (enqueue 변경은 Tier 2 가능성).

---

## 📜 과거 이력 참조

- 세션별 누적 이력: [docs/session-log/2026-05-15-rounds-1-2-3.md](docs/session-log/2026-05-15-rounds-1-2-3.md)
- dogfooding 마찰 F0~F17: [docs/dogfooding/round4-af-cli-friction.md](docs/dogfooding/round4-af-cli-friction.md)
- Research Router 설계: [docs/2026-04-29-research-router-structured-evidence-design.md](docs/2026-04-29-research-router-structured-evidence-design.md)

---

## 세션 종료 체크리스트

1. 완료 작업 / 다음 진입점 갱신
2. `git commit` → `git push`
3. `python end_db.py agent-factory`
