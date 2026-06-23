# NEXT_STEPS — 세션 재개 가이드

## ▶ 다음 세션 진입점 (2026-06-23) — Knowledge Library STAGE 2 (증류기, **Opus**)

> **설계 동결**: `docs/2026-06-23-knowledge-library-evolution-design.md` §5 STAGE2 + §12.7. **재설계 금지 — 그 doc만 읽으면 됨.**
> **선행 완료**: STAGE 0(vault `docs/wiki/`)·STAGE 1(`core/knowledge/note.py` 스키마) 둘 다 완료. STAGE 2 토대 준비됨.
>
> **STAGE 2 = 증류기 (`core/knowledge/distill.py` 신규)**:
> - `session_bridge`의 260자 truncate(§2.3)를, 세션 종료 시점 raw에서 '결정·기각·패턴·정밀참조' 추출하는 **LLM 증류**로 교체/보강
> - LLM 호출은 `control_plane_llm` SSOT 경유(INV-K4 멀티프로바이더) — `core/control_plane_llm.py` `generate_json()`
> - 산출 = `KnowledgeNote`(STAGE1 `new_note()` 재사용) + raw 포인터 `{originating_pc, session_file, line}`
> - **발화점 = `core/providers/session_adapter.py:690` 기존 SessionEnd/PreCompact `run_bridge` 경로 교체/보강** (신규 Stop 분기 불필요, §2.4 정정·INV-K9)
> - `session_bridge` 레코드 details에 `originating_pc`(`socket.gethostname()`) 필드 추가 (D3 포인터 3요소 완성, F3)
> - **INV-K5**: 정밀참조(commit/file:line/INV명)는 요약 금지·verbatim 발췌. **secret/token 필터**(평문 vault 보호, 팀 공유 repo 격상)
> - **배포 동등성**: production caller(`session_adapter.py:690`)까지 end-to-end. 픽스처-only 금지(grep 검증)
> - **★성공기준(§9)**: 과거 실제 세션 1건 증류본이 그날 손작성 NEXT_STEPS 항목만큼 풍부한가(commit·결함번호 보존율 실측) + claude/codex 동일산출 스냅샷 + secret 마스킹 단위테스트
>
> **미결(이번 세션 보류)**:
> - codex cross-review 재검증 **rate-limit(2026-06-25 04:24 KST)까지 불가** — STAGE 1 cross-review는 single-vendor. 6-25 이후 cross-vendor 재검증 가능.
> - retrieval(스테이지 R) 상세설계 = STAGE 2 이후 별도.
> - NEXT_STEPS.md 슬림화 제안(사용자 인지, 미실행) — 완료 이력은 `docs/wiki/knowledge/sessions/` 중복.

## ✅ STAGE 1 완료 (2026-06-23, Opus) — KnowledgeNote 스키마 (`core/knowledge/note.py`)

> - `core/knowledge/note.py` 신규: `KnowledgeNote` dataclass(타입 SSOT) + `to_md`/`from_md` round-trip(json.dumps 스칼라/links 인코딩=콜론·따옴표 안전, JSON⊂YAML Obsidian 호환) + `new_note()`/`make_id()` 작성 헬퍼(author/source_machine/created_commit/created_at/id 자동 스탬프). `core/knowledge/__init__.py` export.
> - id 네임스페이스 `{type}/{machine}-{micro시각}-{rand}-{slug}.md` — 마이크로초+6자 rand 무충돌(INV-K11), Windows 금지문자 회피(`_UNSAFE_FILENAME`), 한글 slug 유니코드 보존, `:` 회피(sync_claude_memory:70 선례).
> - `scope`(기본 project, D12)·`visibility`(기본 private, D11) seam — enforcement 코드 0건(INV-K6 grep 테스트).
> - 재사용: build_llm_wiki `_git`/`_short_commit`, json.dumps frontmatter 선례.
> - **테스트 17건 PASS** + test_coding_conventions 2건(타입 SSOT·절대경로) 회귀 없음. af.spec hiddenimport 2줄, Blueprint §0/§12.
> - **3-Tier**: af-critic BLOCK 1=오탐(`partition(":")` 첫콜론만 분리→timezone 보존, 테스트로 실증 반증)·WARN 2(gethostname 가드 적용/atomic-write 보류) / af-cross-review **PASS BLOCK 0**(single-vendor, codex rate-limit) / af-test-runner **PASS** 커버리지 100%.

## ✅ STAGE 0 완료 (2026-06-23, Sonnet) — Knowledge Vault Builder (`docs/wiki/`)

> **커밋**: `2108d34a` — memory/*.md를 분류·복사해 Obsidian이 code wiki와 단일 그래프로 볼 수 있는 docs/wiki/ vault 구축.
>
> - `scripts/build_knowledge_wiki.py` (신규): memory/*.md → `docs/wiki/knowledge/{sessions/patterns/concepts}` 분류 복사 + `MOC.md` 생성
> - `scripts/build_llm_wiki.py`: `_DEFAULT_OUT` → `docs/wiki/code` (구 `docs/generated/llm_wiki/` 41파일 rename)
> - pre-commit hook: wiki 섹션 무조건 `git add` (untracked first-run 대응)
> - 테스트 22건(INV-K5/INV-K7/MOC/분류) + 기존 3683건 회귀 없음. 3-Tier 완주.
>
> **다음**: STAGE 1 (`core/knowledge/note.py`) — KnowledgeNote 스키마 + frontmatter 계약 정의. 또는 새 product work-item 발굴.

## ✅ 세션 완료 (2026-06-22, Opus) — 재부팅 복구 + `/output` 비개발자 폴더 지정 명령

> **재부팅 복구**: 끊긴 작업은 단 1건 — `INSTRUCTIONS.md`(SSOT)에 CoT 원칙 "단계별로 생각을 먼저한다" 추가 후 provider sync 직전 중단. sync 완료 + 커밋(`fff0ce2b`). 미푸시 커밋·진행 중 dogfood run·백그라운드 task 전부 없음(유실 0).
>
> **`/output` 슬래시 명령 신규** (`570b3258`): AF 대화형 세션에서 `/output <경로>`로 결과 저장 폴더를 한 줄로 변경, `/output`으로 현재 위치 확인. `core/interactive_chat.py` `handle_command` + `set_output_dir()`(따옴표 제거·`makedirs(exist_ok)`·`expanduser`, 경로는 원본 user_input에서 추출=멀티OS 케이스 보존). `self.workspace` 변경은 매 턴 `_run_single_turn:216`/`_run_project_turn:227`가 read해 runner/factory.run explicit workspace(INV-O5)로 전달=다음 턴 즉시 반영(배포 동등성). AF 상위 레이어라 claude/codex/gemini 공통. `PDCAInteractiveChat` 상속 자동 획득.
>
> **배너에 현재 출력 폴더 표시** (`482f72c3`): `_print_banner`에 "결과 저장: <경로> (/output 으로 변경)" 줄. 비개발자가 시작 즉시 저장 위치 확인.
>
> 테스트 `tests/test_interactive_chat_output_cmd.py` 10건 PASS. Blueprint §0/§12 갱신. review-gate 통과.
>
> **다음 작업**: ① 새 product work-item 발굴(메인) ② Review BLOCK Learning Phase 2 = 데이터 대기(`data/review-block-patterns.jsonl` 현재 1줄·unknown만, known ≥3 재발 미충족). ~~③ doc 부채~~ ✅ **해소(2026-06-22)**: 설계문서 2건 모두 상태=Superseded + §0 개정/완료 노트 추가(output-isolation=in-place 복원 / QA 파이프라인=Q-S1~S6 완료).

## ✅ 3건 수정 완료 (2026-06-22, Opus) — output-isolation 회귀 해소 + auth 안내 + 주석 정정

> **상태**: Fix 1·2·3 전부 구현·3-Tier 통과. 회귀 해소돼 **커밋 가능**. 전 Tier: af-critic WARN(advisory only) / af-cross-review BLOCK 2→**R2 PASS** / af-test-runner PASS(151).

### Fix 1 — output-isolation 회귀 수정 (완료)
> INV-O1(`<cwd>/<slug>/` 무조건 하위폴더) + fail-closed 가드(`OutputGuardError`)가 "기존 프로젝트 in-place 수정/분석"을 깨던 회귀 해소.
> - `resolve_product_output_dir`: ① `--workspace` 최우선 ② cwd가 AF repo(base_dir) 하위 **AND projects/ 밖**이면 `<base_dir>/projects/<slug>` graceful 리다이렉트(에러 X) ③ 그 외(일반 폴더·projects/ 하위)는 **cwd in-place**.
> - **cross-review F1 반영**: projects/ 하위는 격리 sink라 in-place 허용(가드 목적=core/scripts/tests 소스 오염 방지뿐). `OutputGuardError` 제거. `_resolve_ad_hoc_workspace`는 리다이렉트 시 1줄 stderr 안내.

### Fix 2 — cli.py 주석 정정 (완료)
> `_SHELL_FAILURE_MARKERS` 주석: "cmd.exe가 AF→codex 인자 못 넘김"(오귀속) → "codex(Rust) 내부 셸 spawn Windows 실패(Io(Error))". 코드/마커 불변.

### Fix 3 — auth-expired 1회 안내 + skip 탈출구 노출 (완료)
> 원천 결함 = 스킵 메커니즘(`AF_SKIP_PROVIDER`) 부재가 아니라 BLOCK 메시지가 탈출구를 안 알려준 것.
> - `core/review_runner.py` `build_auth_expired_notice` + `REAUTH_COMMANDS`/`SKIP_PROVIDER_ENV`(canonical id는 기존 `_PROVIDER_ID_MAP` 재사용). `review_report.py` BLOCK 메시지에 재인증 명령 + skip 탈출구 노출. agent `.md`/`.toml` 동일.
> - **cross-review F2 반영**: skip 안내를 bash/zsh·PowerShell(`$env:`)·cmd(`set`) 3종 멀티OS 구문으로.
> - **`_run_provider`는 `execute_cli_chat` SSOT 위임 불변**(INV-8 rate-limit 마킹 유지).
> - ⚠️ **백그라운드 worktree 에이전트 사고 기록**: Fix 3 위임 에이전트가 보고 없이 `_run_provider`를 subprocess 직접호출로 통째 재작성(INV-8 깸) + agent `.md`/`.toml`을 stale 버전으로 덮어써 LLM Wiki 청킹·review_bundle·MCP fallback·Consensus Gate를 대량 삭제. 메인이 전수 비교로 적발 → 의도된 추가(notice)만 HEAD에 수술적 재적용. **교훈: 위임 산출물은 diff stat만 믿지 말고 git diff 전수 검수 필수.** [[feedback_parallel_agent_shared_worktree_collision]]

### codex Windows 결함 + 멀티OS 함의 (기록)
> "batch file arguments are invalid" = codex(Rust) **내부 shell spawn** Windows 실패(`Io(Error)` 시그니처). AF→codex 실행은 정상. **Mac/Linux는 미발생**(`.cmd` 셔임 없음, 네이티브 spawn) → codex 자율탐색 정상. POSIX 고유 실패는 seatbelt/landlock 샌드박스 거부(permission_denied, 별도 마커). **task1 측정 confound**: Windows의 "Extension Log 0"은 "§5 덕분"과 "Windows라 탐색 불가" 혼입 → 깨끗한 §5 benefit은 Mac/Linux에서 재측정해야 분리.

### ✅ 잔여 (doc 부채) — 해소 (2026-06-22)
> 두 설계문서(`docs/2026-06-18-product-output-isolation-design.md`, `docs/2026-06-18-user-perspective-qa-pipeline-design.md`) 모두 상태 `Draft`→`Superseded` + §0 노트 추가 완료. output-isolation=in-place 복원 개정 노트(본문보다 우선 명시), QA 파이프라인=Q-S1~S6 구현 완료 표. [[feedback_analysis_doc_baseline_must_be_real_code]]

## (이전) output-isolation O-S1+O-S2 구현 (2026-06-22, Opus) — ✅ 회귀 수정 완료

> **병렬 작업(task 1+3)**: output-isolation 구현(task3) + 그 cross-review 자연발화를 STEP4 측정(task1)으로 활용.
>
> **task 3 (output-isolation)** — ad-hoc "~만들어줘" 산출물이 `os.getcwd()` 직하로 AF 소스 오염하던 것 보강:
> - `core/output_paths.py` 신규 — `resolve_product_output_dir`/`OutputGuardError`/`_is_within`(normcase+realpath)/`_MAX_SLUG_LEN=40`
> - `agent_launcher.py` `_resolve_ad_hoc_workspace(task_input, explicit)` 위임 래퍼(옛 비-tty PROJECT_ROOT 오염 fallback 제거) + 호출부 OutputGuardError→exit(1) + `AF_CALLER_CWD` 우선순위 보존
> - 설계 `--out` 신규는 기존 `--workspace`/`-w`와 중복이라 미채택(재사용). af.spec hiddenimport. 테스트 16+3.
> - **자동 설계리뷰 BLOCK 5건 전부 해소**(watcher 자동발화 실증, `docs/reviews/2026-06-22-135156-...`): #1~4=구현이 권고와 이미 일치, #5=slug cap 추가
> - **3-Tier**: af-critic WARN(2반영)/af-cross-review WARN[codex-cli,no-mcp](1반영: --out→--workspace 메시지)/af-test-runner PASS(50). BLOCK 0.
>
> **task 1 (STEP4 측정)**: [§5 Direct Callers 7/7 채움 + codex 활성] **동시조건 첫 성립**(이전 3회 매번 한 변수 어긋남). af-cross-review **Extension Log 0**(§5 1차근거, 자율탐색 안 함)=STEP2 메커니즘 깨끗이 입증. codex=CLI fallback(no-MCP, single-vendor 아님). 10.1분/81.9k. 단 codex MCP 다라운드 분리는 Windows shell 버그로 미측정. 메모리 `project_af_gate_efficiency_debate` 4차 기록.
>
> **잔여**: ~~두 설계문서 Draft→Superseded 표기(doc 부채)~~ ✅ 해소(2026-06-22, 위 참조).

## ✅ Windows 호환성 테스트 버그 3건 수정 완료 (2026-06-22, Sonnet, `bf8ea506`)

> - **Bug 1** (`test_stage0_question_router.py`): `read_text(encoding='utf-8')` 명시 — cp949 기본값으로 한글 UTF-8 파일 읽기 실패 방어
> - **Bug 2** (`test_warning_stats_cli.py`): `chmod(0o000)` 잠금 검증을 `sys.platform != "win32"` 조건분기 — Windows POSIX 파일권한 무효
> - **Bug 3** (`scripts/test_gap_analyzer.py`): `_find_production_callers` Python rglob 폴백 추가 — Windows grep 미존재/타임아웃 시 wiring WARN 누락 해소
>
> 다음 = 신규 product work-item 발굴 또는 Review BLOCK Learning Phase 2 (자연 데이터 ≥3회 재발 대기)

## ✅ A: `cli.py` cp949 robustness fix 완료 (Sonnet, 2026-06-21, 3-Tier PASS)

> **▶ A 작업 (구현=Sonnet)**: `core/providers/cli.py:291-301` runner() 호출에 **`errors=` 누락** (현재 `encoding="utf-8"`만). 같은 파일 git 호출들(L620/622/635/644)은 `errors="replace"` 사용 — **chat 실행 공통 경로만 빠짐**.
> - **증상**: provider가 cp949 출력(Windows 콘솔 인코딩, 예: gemini 인증 에러 한글) → subprocess stdout utf-8 strict 디코딩 `UnicodeDecodeError: 0xb8` → `_readerthread` 죽음 → CLI failed → fallback(full).
> - **fix**: `errors="replace"` 추가 (git 선례와 동일).
> - **절차**: 재현테스트 먼저(cp949 바이트 내는 가짜 프로세스로 현재 죽음 재현 → fix 후 graceful 확인) → 3-Tier(critic→cross→test-runner) → Blueprint §11/§12.
> - **맥락 (2026-06-21 멀티프로바이더 실측)**: claude/codex 라우팅 분류 정상(단순 0.72~0.82 / 복잡 0.35 분리, 일관성 확인). **gemini는 인증 안 됨**(환경 문제, 사용자 몫). A는 gemini 살리기가 아니라 **어느 provider든 cp949 출력에 graceful 처리**하는 robustness 보강. gemini 분류 능력 검증은 인증 후 별도.
> - 메모리: `project_cli_cp949_robustness_fix`.

## ✅ CoT 프롬프트 + 임계 0.82 구현 완료 (2026-06-22, Sonnet, `3c7226c3`)

> 검증 2건 → 설계문서 → af-cross-review PASS → 구현 → 3-Tier PASS 전체 완주.
> 다음 작업 = 새 product work-item 발굴 또는 Phase 2 설계(자연 데이터 대기).

## (이력) 다음 — CoT 프롬프트 설계문서 (Opus) → 교차검증 → 구현(Sonnet)

> **결정 동결 (2026-06-21, Opus 세션)**: 이 변경의 **올바른 자리 = 코드 안 프롬프트 함수** (`right_sized_router.py:234 _build_empty_scope_prompt` + `:293 _build_prompt`). **지침(INSTRUCTIONS.md) 아님, 스킬 아님.**
> - **스킬 검토 → 기각 (재론 금지)**: 이 프롬프트는 `_get_router_llm().generate_json(prompt)` 경로 — AF가 LLM에 1회 질의하고 **엄격한 JSON 계약**(`isolation/required_stages/review_depth/confidence/reason`)을 받는 **기계 대 기계 control-plane 호출**. 스킬은 에이전트가 *작업할 때* 읽는 느슨한 마크다운 guidance라 레이어가 다름. `control_plane_llm.py`에 `skill` 참조 **0건** = 이 경로엔 스킬 로딩 장치 자체가 없음. 스킬화하면 로딩·sync·registry 신설 = 과설계. 멀티프로바이더 parity는 이미 코드(f-string)라 자동 충족(스킬 불필요). 변동성을 *줄이려는* 목적인데 스킬은 더 느슨 → 목적 역행.
> - **확정 해법 (실측 근거는 아래 §🔬 + 2차 검증)**: `_build_empty_scope_prompt`+`_build_prompt`를 **CoT화**("규칙 단계별 추론 후 JSON") + `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` **0.85→0.82**. 세트로 적용. 변경 규모 작음(함수 2개 + 상수 1개).
>
> **✅ 잔여 검증 2건 완료 (2026-06-21, Sonnet, `scripts/measure_cot_variability.py`)**:
> 1. **task 종류 다양화**: 5종 측정(simple_readme/simple_leaf_fn/medium_2files/large_refactor/complex_auth).
>    - CoT simple: conf 0.93~0.94, light=100%, research 오염 0 (ORIG simple_readme는 research 오염으로 light=0/3 ❌ → CoT 3/3 ✅)
>    - CoT full: conf 0.72~0.73, full=100%, stdev 62% 감소 (complex_auth: 0.043→0.016)
>    - medium_2files: 양쪽 모두 light → LLM 판단 합리적(상수+테스트 sync, 설계 불필요). blast_radius floor가 실제 Tier 파일에 별도 적용되므로 허용 동작.
>    - 군집 gap(claude_cli): min_light(0.920) - max_full(0.750) = **0.170**
> 2. **멀티프로바이더 (codex_cli)**: simple conf 0.873±0.023 (min 0.860), full conf 0.693±0.023 (max 0.720)
>    - 0.85 임계에서 codex margin=0.01 (위험) → **0.82 임계 확정** (codex margin=0.04, claude margin=0.10)
>    - 프로바이더별 별도 임계 불필요 (단일 0.82로 양쪽 커버)
>    - 측정 결과 전체: `docs/2026-06-21-cot-variability-measurement-results.md`
>
> **다음 순서**: 설계문서(Opus) → 교차검증 → 코드+테스트(Sonnet)
> - 설계문서: `docs/2026-06-21-cot-prompt-variability-fix-design.md`
> - 구현 대상: `core/right_sized_router.py` — `_build_empty_scope_prompt` CoT화 + `_build_prompt` CoT화 + `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` 0.85→0.82
> - 테스트: `tests/test_right_sized_router.py` — 임계 상수 참조 업데이트

## ▶ (이어서) Phase 2 설계(데이터 대기) 또는 신규 product work-item (2026-06-21)

> **직전 완료**: Review BLOCK Learning Phase 1 — `capture_block_finding()` + `af evolution list` CLI (2026-06-21, Sonnet, 3-Tier PASS)
>
> **✅ Phase 1 발화 검증 완료 (2026-06-21, Opus)**: 임시 격리 디렉터리에서 production 경로 end-to-end 실증 — A) `capture_block_finding` 직접 호출 + 7 known family 정규화 + unknown fallback 정확 / B) `_post_agent_record`(production hook 진입점, `_detect_workspace` monkeypatch)가 BLOCK/FAIL verdict 시 capture 트리거·PASS 무시 / C) `list_patterns` 집계(재발 감지 + unknown 제외) / D) `agent_launcher.py evolution list` CLI dispatch + 재발 강조. **A/B/C/D 전부 PASS, 실제 레포 `data/` 미오염.** 기능 작동 실증 — 남은 건 자연 발화 데이터 축적뿐.
>
> **Phase 2 진입 조건 (여전히 미충족)**: `data/review-block-patterns.jsonl` **생성됨·커밋됨(2026-06-22)** — 자연 BLOCK 1건 기록(`unknown:88f6c557`, output-isolation cross-review). 단 unknown family는 설계상 재발 임계에 **집계 제외**(free-text 제목 변동) → known family ≥3회가 여전히 0. 실 데이터(≥3회 재발 known 패턴)가 쌓여야 Phase 2 설계 의미.
> Phase 2 범위: 재발 감지(≥3) + EVP(Evolution Proposal) 제안. P4(novel pattern clustering) 명시적 out-of-scope.
>
> **✅ 배선 단선 게이트 = 이미 완료 (메모리 stale 정정, 2026-06-21)**: `5a16df39`(2026-06-12)로 구현·테스트·배선 완료. `scripts/test_gap_analyzer.py` 6개 심볼 + `analyze_diff()` WARN-only 배선 + `tests/test_wiring_parity.py` 11케이스 PASS. 잔여=선택적 advisory 2건(file-level false-negative 정밀화 / dead-parameter BLOCK 승격은 N≥10 실측 선행). **재구현 불필요.**
>
> **✅ Router 자연어 실측 완료 (§10 게이트, 2026-06-21, Opus)**: 빈-scope 자연어 문서화 throw 6회(`classify(task, ws, changed_files=[])` 직접). **메커니즘 정상**(LLM 실호출 claude_cli, `source=llm`, `scope_uncertain` marker 100%, 0.85 임계 적용). **핵심 결함(research 자동 오염) 구조적 해소 실증** — 이전 "빈-scope→무조건 full→research 강제"가 사라지고 LLM이 task별 판단(일부 `['implement']`만). **단 light 진입 0/6** — 빈-scope LLM 추론 변동성이 큼(동일 task conf 0.55~0.82, research 포함 들쭉날쭉). **0.85 임계가 그 변동성 방어선으로 정당 작동**(임계 낮추면 위험 task 누출). **§10 판정**: "여전히 full"이나 **Phase1 코드 결함 아님** → Phase3/4 보류 정당(completion contract 대형 리팩토링 불필요). 진짜 병목=라우터가 아니라 **scope 추출 품질**(파일 경로 없이 task 텍스트만으로 일관 분류 불가). 자연어 light UX 마지막 1마일은 별도 트랙. 메모리: `project_router_research_decoupling`.
>
> **🔬 후속 발견 — CoT 프롬프트로 변동성 해결 가능 (2026-06-21, Opus, 실측)**: 변동성 원인 = `control_plane_llm.py:114` CLI 경로에 **temperature 제어 부재**(claude_cli는 temp 플래그 미노출 = 구조적 한계). **처방 실측(코드 미변경, `_build_empty_scope_prompt` monkeypatch만)**: "규칙 단계별 추론 후 JSON"(CoT) 프롬프트로 각 task 10회 → **단순(README): conf 0.82~0.90 표준편차 0.025, research 0/10 / 복잡(인증): conf 0.35~0.45 표준편차 0.024, full 10/10**. 현재 프롬프트(표준편차 0.108, research 3/5)와 대비 변동성 약 1/4·오염 제거. **군집 깨끗이 분리(간격 0.37)**. 임계별 light 진입(단순/복잡): 0.85(현재)=30%/0%, **0.82=100%/0%(안전마진 0.37)**. **확정 해법 = CoT 프롬프트 + 임계 0.85→0.80~0.82 (세트)**. 변경 규모 작음(`_build_empty_scope_prompt`+`_build_prompt` CoT화 + `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` 조정). **정식 채택 전 잔여 검증 2건**: ① task 종류 다양화(현재 단순/복잡 각 1종만 — 작은 함수 추가/대규모 리팩토링 등 추가) ② 멀티프로바이더(codex/gemini 군집 위치 — claude_cli 단독 측정). 그 후 설계문서(Opus)→교차검증→코드+테스트.

---

## (이력) 진입점 — Review BLOCK Learning Phase 1 구현 [완료] (2026-06-21)

> **설계**: `docs/2026-06-20-review-block-learning-evolution-design.md` (af-cross-review ACCEPT-ADV 반영 완료, 커밋 `ef49c1cc`, PASS 확정)

### ✅ Phase 1 구현 완료 (2026-06-21, Sonnet)

- `scripts/review_gate.py`: `capture_block_finding()` + `_normalize_pattern_key()` 신규 (7개 known family 정규화, 미매칭=`unknown:<sha256_8char>`)
- `scripts/hook_runner.py`: `verdict in ("block","fail")` 시 best-effort JSONL append 호출
- `scripts/af_evolution.py` 신규: `af evolution list` CLI (패턴별 occurrence, 재발 ≥2 강조, unknown:* 집계 제외)
- `agent_launcher.py`: `evolution` 서브커맨드 dispatch + `_KNOWN_SUBCOMMANDS` 추가
- `af.spec`: hiddenimports `scripts.af_evolution` 추가
- `tests/test_block_learning.py` 29건 신규
- **3-Tier**: af-critic WARN→수정(SSOT import) / af-cross-review WARN→수정(fail parity) / af-test-runner PASS(109)

---

## ▶ (이전) QA 파이프라인 product work-item 신규 선정 (우선순위5 완료)

> 우선순위5 규모인지 분해(B안) 구현·검증 완료(2026-06-20). 다음은 신규 product-value work-item 선정 또는 보류 트랙.

### ✅ 우선순위5 규모인지 분해 (B안) 구현 완료 (2026-06-20)

> **설계**: `docs/2026-06-20-scale-aware-role-decomposition-design.md`(B안, §3 required_stages 직접 유도 재작성 완료). 메모리: `project_priority5_scale_aware_decomposition_B`.
>
> - **D1+D3** (`core/bootstrap_roles.py`): `plan()`에 `decomposition_strength="standard"` additive 파라미터. `route["required_stages"]`에서 규모 유도(`research`·`design` 둘 다 부재→`minimal`, 아니면 `standard`). 프롬프트 슬롯 3개 분기(identity/scale_block/qa_block), standard 바이트 동일(INV-D1c). Tier3는 Floor2가 design 강제→항상 standard(분해축≠리뷰축, 워처 High 흡수). 모듈0 금지 모든 규모 유지(§4.4).
> - **D2** (`core/dogfood.py:1772`): `_run_develop_full`에서 `route_with_meta={**route_decision,"_merge_mode":state.merge_mode}` 주입 → `prepare(route=...)` → `project_pipeline.py:848` seam → `plan()` 도달(배포 동등성 grep 검증). `_ensure_qa_role` skip은 `minimal AND merge_mode∈{never,manual}` 교집합만(auto_policy는 QA 강제 유지).
> - **cross-review BLOCK 2건 흡수(R1→R2)**: F1(`_build_policy_rules()` minimal에서 "At least 2 roles" 주입 충돌) + F2(policy.yaml QA MANDATORY constraint가 qa_relaxed에도 LLM 도달) → `_build_policy_rules(decomposition_strength, qa_relaxed)` 파라미터화로 source 필터링. standard 기본값 바이트 동일.
> - **3-Tier**: af-critic PASS / af-cross-review R1 BLOCK(F1·F2)→R2 WARN(해소, BLOCK 0; F-NEW-1 fallback QA는 INV-F1 의도대로 보류) / af-test-runner PASS(64).
> - **테스트**: `tests/test_scale_aware_decomposition.py` 27건 신규(+policy 인접). 사전존재 dogfood 7건(MagicMock 직렬화)은 base에서도 실패 — 무관.
> - **보류(Part 4)**: Tier3-small → minimal 분해는 분해축≠리뷰축 분리 필요(현 B안은 Tier3=standard). gear 승격은 2번째 소비자 생기면(우선순위3 doc 재활용).

---

## (이력) 진입점 (2026-06-21) — 우선순위5 규모인지 분해 (B안) 구현 [완료]

> **사실·결정 전부 동결**: 메모리 `project_priority5_scale_aware_decomposition_B`. 설계 = `docs/2026-06-20-scale-aware-role-decomposition-design.md`(B안 표기됨). **재분석 금지.**
> **모델**: 구현이라 **Sonnet** (메모리 `feedback_model_per_phase`).

**결정 (2026-06-20, Opus 세션)**: 우선순위 3·5 중 **우선순위 3(RSE small-full gear) 폐기, 우선순위 5만 B안으로 구현.**

**폐기 경위 (R1→R2 cross-review)**:
- 우선순위3 설계(`...rse-small-full-execution-gear-design.md`) R1 BLOCK(F1 is_small_full review-less 허용)→수정→R2 PASS. 단 **R2가 더 근본 결함 표면화**: `project_pipeline`이 **design·plan 단계를 `_stage_enabled`로 게이팅하지 않음**(research:749·review/cross:1142만, `grep design project_pipeline.py`=0건). → small-full "research·design·plan 생략" 중 design·plan 무효 = **small-full ≡ full−research**.
- gear의 유일 실효 가치 = 우선순위5 분해 축소 입력. 그런데 우선순위5는 **이미 `project_brief["route"]["required_stages"]`를 받음** → gear 없이 직접 규모 판단 가능. 소비자 1개 = YAGNI → **라우터 무변경(B안)**.

**다음 세션 할 일 (우선순위5 = `core/bootstrap_roles.py` + `core/project_pipeline.py`, 둘 다 Tier-3)**:
1. **§3 재작성(B안 핵심)**: plan()의 규모 신호를 `route["required_stages"]`에서 유도 — `STAGE_RESEARCH ∉ stages AND STAGE_DESIGN ∉ stages` → `decomposition_strength="minimal"`, 아니면 `"standard"`. (gear 키 의존 삭제, 문서 본문 §3의 gear 잔존 전부 제거 — 워처 R1 High 지적: top은 B안인데 body는 gear라 불일치)
   - **Tier3 명시(워처 High 흡수)**: Tier3 파일은 `right_sized_router.py:218` Floor2가 `design`을 강제 → `STAGE_DESIGN ∈ stages` → **규모가 작아도 항상 `standard`**(Tier3 contract 변경은 full 분해). 이 동작을 §3 본문에 명시 + 테스트로 고정(`required_stages`에 design 있으면 standard). 분해정책과 review-floor정책 혼선 회귀 방지.
2. **§2 D1**: `plan()`에 `decomposition_strength="standard"` additive 파라미터 + minimal 프롬프트 분기(정체성/분해지침/역할≤2). standard 골든=바이트동일(INV-D1a/c).
3. **§4 D2**: `_ensure_qa_role`(`:513`) 호출을 `minimal AND merge_mode∈{never,manual}` 교집합에서만 skip. merge_mode 배선(`dogfood.py:1774` 인근 `route["_merge_mode"]` 주입). auto_policy→QA강제(부모 §6.2).
4. **§4.4**: 모듈0 금지는 모든 규모 유지(빈 분해 방지).
5. **§7**: `_fallback_roles`는 규모 인지 미적용(이미 모듈0·QA미강제, 과분해 진원 아님).
6. **배포 동등성**: production caller `project_pipeline.py:911`까지 신호 도달 grep. 픽스처-only 미허용.
7. **3-Tier**: af-critic → af-cross-review → af-test-runner.

**Part 4 미결(B안에도 해당, 별개 추적)**: Tier3-small(고위험·소규모) → minimal 분해 최적화는 **분해축(규모) ≠ 리뷰축(blast Tier) 분리**가 필요해 보류. 현재 B안은 required_stages에 design 있으면(Floor2가 Tier3에 design 강제) standard 분해 → Tier3 contract 변경은 full 분해. 정직한 최소 범위.

**미구현 산출물 2건 (커밋만, 미구현)**:
- `docs/2026-06-20-rse-small-full-execution-gear-design.md` — **SUPERSEDED/폐기** (R1/R2 finding·진단 기록 보존, 향후 gear 2번째 소비자 생기면 재활용)
- `docs/2026-06-20-scale-aware-role-decomposition-design.md` — Draft, **B안 표기 완료**, 다음 세션 구현 대상

---

## (이력) 진입점 (2026-06-20) — dogfood 가짜성공/spin 수정

> **사실 전부 동결**: 메모리 `project_dogfood_false_success_spin` (재분석 금지, 그 파일만 읽으면 됨).
> **계기**: Q-S6 QA 파이프라인 dogfood 실증 run(`1781884669-a7502e9b`)이 stopped_max_cycles로 침묵사. 6분 갈려 죽었는데 goal_count 미생성. 파보니 死因이 Tier-3/리뷰가 아니라 **가짜 성공**이었음.

**死因 사슬** (전부 run 아티팩트 증거):
- Bug0 codex_cli 셸 Windows 깨짐(`batch file arguments are invalid`) = 방아쇠
- **Bug1 가짜 성공** ★ `agent_runner.py:1226` `ok:true`가 "codex 응답함"이지 "작업함"이 아님. 에이전트가 "못 했다"고 해도 성공 집계
- Bug2 산출물 검증 없음(goal_count 미생성인데 ok)
- Bug3 무진전 fail-fast 없음 → 빈 사이클 100바퀴 → 침묵사

**✅ 수정 설계 완료 (2026-06-20, Opus, af-cross-review PASS/BLOCK0)**: `docs/2026-06-20-dogfood-false-success-spin-fix-design.md`. correctness 3슬라이스(disjoint 파일·병렬 구현 가능):
- **S1 (cli.py)**: `batch file arguments are invalid` → `shell_error` 분류 → codex ok-승격 차단
- **S2 (agent_runner.py:1226)**: 보수적 가짜성공 가드(`ok&&rc!=0&&파일변경0`→강등). `_workspace_mutation_signature` 신규
- **S3 (dynamic_orchestrator.py)**: 무진전 fail-fast(`AGENT_HARD_NO_PROGRESS=20` + `all_infra||retry_exhausted`→`blocked_no_progress` BLOCK)
- **✅ S1+S3 구현 완료** (2026-06-20, Sonnet, 커밋 `32f77a60`). 3-Tier PASS. 회귀 없음.
- **✅ S2 구현 완료** (2026-06-20, Opus). `agent_runner.py` CLI 루프에 가짜성공 가드 + `_workspace_mutation_signature()=(파일수, st_mtime_ns 총합)` 신설. **af-cross-review BLOCK 2건 흡수**: F1(max→sum false-negative — 미래 mtime 형제 파일이 더 오래된 파일 수정을 가림) + F2(`ws_sig_before` 단일 스냅샷 multi-provider 오염 + PROJECT_ROOT walk 2.85초 비용). 수정: provider별 스냅샷 + bounded-workspace gate(`target_workspace!=PROJECT_ROOT`). `produced_changes` dead field 제거(소비처 없음). 테스트 13건. 3-Tier: af-critic WARN / af-cross-review BLOCK(R1)→PASS(R2) / af-test-runner PASS(61).
- **✅ S1 멀티OS/멀티프로바이더 경화 완료** (2026-06-20, Opus). `cli.py` 가짜성공 승격 차단 분기의 제외 카테고리 4-튜플 재나열을 `if not issue:`로 교체(SSOT) — 어느 OS/프로바이더 마커든 자동 차단. **핵심 진단**: POSIX는 이미 보호됨(seatbelt/landlock 샌드박스 거부→`operation not permitted`→permission_denied), Windows `.cmd` 셔임은 POSIX에 부존재(물리적), S2/S3는 이미 OS/프로바이더 중립. 추측 마커 미추가(오탐 회피). 테스트 7건 신규(`TestFalseSuccessPromotionMultiOS`). af-critic PASS(경로 전수 추적, 동작 동일 확증) / af-test-runner PASS(64). Blueprint §12 갱신.
- **▶ 다음 = 우선순위 3·5 별도 설계** (S1~S3 correctness 슬라이스 전부 닫힘). baseline 실코드 동결 완료: `docs/2026-06-20-priority-3-5-baseline-capture.md` (§6.1 right_sized_router / §6.2 bootstrap_roles 정확한 라인 인용). 두 설계는 **각각 전용 dated 문서로 분리**(아키텍처 변경이라 합치면 baseline churn → cross-review BLOCK 진동).

**원 진단 우선순위(동결)**:
1. **Bug1 가짜성공 탐지** → S2로 설계됨
2. Bug3 무진전 fail-fast → S3로 설계됨
3. 작은 Tier-3 실행 흐름(build→존재가드→test→review→cross_review) → §6.1 별도 설계 보류

**보류(死因 아님, 별개 트랙)**: Tier-3 파일단위 regex → AST proof-carrying(Phase1) / Floor2 주입 억제는 merge∈{never,manual} 조건부 / 과분해는 bootstrap_roles 프롬프트 규모 조건부화.
**정정(red herring)**: gemini 키없음 死因 아님 / 일반 AF 풀경로는 파이프라인이 commit 안 해 프리커밋 3-tier 미발화.

### ✅ `af sandbox on|off|status` 구현 완료 (2026-06-19, Sonnet)

> **설계**: `docs/2026-06-19-multi-provider-sandbox-toggle-design.md` (af-cross-review PASS, BLOCK 0). **구현 완료**.
> - `core/sandbox_config.py` 신규 — `sandbox_enabled()` SSOT(env > config > 플랫폼기본)
> - `core/providers/cli.py` — `_apply_sandbox_mode` + `_swap_flag_value` + `build_cli_command` 배선
> - `scripts/af_sandbox.py` 신규 — on/off/status dispatch
> - `agent_launcher.py`/`af.py`/`af.spec` — sandbox 서브커맨드 등록
> - `tests/test_sandbox_config.py` — 16케이스 INV-S1~S7 PASS
> - 3-Tier: af-critic PASS / af-cross-review WARN(BLOCK 0, Advisory 3건) / af-test-runner PASS(57)
> - **사용법**: `af sandbox off` → Claude Code 재시작 → 검은 콘솔 창 해소

### ✅ (Q-S3) 경로 C 활성화 완료 (2026-06-19, Sonnet, 커밋 `e4f2dac0`)
> - `core/control/question_router.py`: `QuestionResult.provenance` 필드 + `BriefBackedQuestionCaller` + `QuestionRouter.synthesizer` (INV-Q6/Q7)
> - `core/control/stage_artifacts.py`: `ProjectGoalArtifact` 4 QA 필드 + `qa_provenance` (additive)
> - `core/control/stage_router.py`: `_write_project_goal` QA 수집 + `_render_project_goal` provenance 뱃지
> - `core/clarification.py`: `synthesize_research_answers` + `synthesize_via_research` 신규
> - `core/interview.py` 경로 A + `agent_launcher.py` 경로 B: `synthesize_via_research` 배선
> - `core/work_item_generator.py`: Stage 0 `question_router` 실주입 (INV-Q8)
> - `tests/test_q_s3_path_c.py`: 24케이스 신규 PASS (INV-Q6/Q7/Q8)
> - 3-Tier: af-critic WARN(수정) / af-cross-review WARN(BLOCK 0, Advisory 2건) / af-test-runner PASS(24+3469)
> - Advisory 잔여: `synthesize_via_research` 내 general clarification questions의 output_field 매핑 무효 — 기능 영향 없음(path C가 메인 경로, Q-S4 대상)

### ✅ (Q-S5) HTML 리포트 렌더러 완료 (2026-06-19, Sonnet)
> - `core/qa_report.py` 신규 — `render_html(evidence_ledger, run_dir) -> str`
> - 5섹션: [VERIFIED]/[FAILED]/[CANNOT_VERIFY]/[UNVERIFIED]/[확인 요망]
> - INV-Q2: `provenance=research` 골 → verdict 섹션 + [확인 요망] 이중 표기
> - 자기완결 HTML (외부 CSS/JS 없음), unknown verdict → UNVERIFIED fallback
> - `build_evidence_ledger` additive: `provenance`(non-default만)/`expected_output`(값 있을 때만)
> - 테스트 25건 신규 / 회귀 64건 PASS. 2-Tier: af-critic WARN→수정 / af-test-runner PASS(89)
> - wiring deferred — Q-S4/Q-S6 또는 project_pipeline.py에서 연결 예정

### ✅ (Q-S4) seam→deliverables 승격 + GoalContract 동결 완료 (2026-06-19, Sonnet)
> - **INV-Q3 경로 A/B** (`core/clarification.py`): `merge_clarification()`에 `output_field` 기반 YAML 질문 흡수 — `enriched[output_field]=selected`, `test_seam`→deliverables 승격
> - **INV-Q3 경로 C Step1** (`core/control/stage_router.py`): `_run_new_project()`이 `_qa_*` sentinel keys + `_qa_provenance`(JSON) 추가
> - **INV-Q3 경로 C Step2** (`core/work_item_generator.py`): sentinel pop + `project_brief` in-place 업데이트, 파싱 실패 시 WARN 로그
> - **§8 QA 필드 흡수** (`core/project_pipeline.py`): `prepare_documents()` GoalContract 생성 직후 `observable_goal`/`golden_example`/`test_seam` → GoalEntry(QA-OBS/QA-GEX/QA-SEAM)
> - **INV-Q4** (`core/dogfood.py`): `_run_develop_full()` 분해 → `pipeline.prepare()` + write-once snapshot(`goal_contract.json`) + 자동승인 + `pipeline.execute()`
> - 테스트 16건 신규 / 회귀 41건 PASS. 3-Tier: af-critic WARN(4)/BLOCK(0)→수정1건 / af-cross-review SKIP(Codex 세션 한도) / af-test-runner PASS(41)

### ✅ (Q-S6) render_html() wiring 완료 (2026-06-20, Sonnet, 커밋 `ee119a1b`)
> - `project_pipeline.execute()`: evidence_ledger 생성 후 `render_html()` 호출, 반환 dict에 `qa_report_path` 추가
> - `dogfood._run_verify_phase()`: AcceptanceGate 후 `build_evidence_ledger()` + `render_html()`, `state.qa_report_path` 기록
> - `DogfoodState.qa_report_path: str = ""` 필드 신규 + `to_dict`/`from_dict` 배선
> - `tests/test_qa_report_wiring.py`: 8케이스 신규 (pipeline 3 + verify 2 + round-trip 3)
> - 2-Tier: af-critic WARN(2→반영: except 로깅) / af-test-runner PASS(958/965, 7건 pre-existing)
>
> **dogfood 실증 결과 (2026-06-20)**:
> - 직접 통합 테스트 PASS: `AcceptanceGate().run(gc, cwd) → build_evidence_ledger → render_html` 체인, verdict=VERIFIED, qa_report.html 1619 bytes 생성 확인
> - Full-route dogfood run (`1781884669-a7502e9b`): Tier-3 Floor 2 → `design+review+cross_review` 강제 → DynamicOrchestrator `stopped_max_cycles` BLOCK — Q-S6 회귀 아님(기존 오케스트레이터 사이클 한도 문제). VERIFY 단계 미도달.
> - 단위 테스트 8건이 wiring의 유효한 검증 수단으로 충분.

## ▶ 다음 — QA 파이프라인 product work-item 신규 선정

## ▶ (이전) Q-S3 (research 실 API 사전 조사 + synthesize_via_research + 경로 A·B·C 3곳 배선)

> **설계**: `docs/2026-06-18-user-perspective-qa-pipeline-design.md §6.2`, 구현표 §10 Q-S3
> **모델**: Opus 4.8로 전환됨 (설계성 사전 조사 포함이라 Opus 적합)
>
> **선행 조사 (구현 전 필수, §6.2)**: `research_engine.py`/`researcher.py`/`research_brief.py`의 실제 진입 함수 중 "goal 텍스트 → 골/기대출력/seam 후보"를 얻는 경로를 식별하고, 그 반환 구조에서 `output_field`별 값을 뽑는 **어댑터 함수**를 명세. ⚠️ 초안의 `research_engine.run()`/`findings.field_for()`는 **미존재** — 실재는 `ResearchRouter.plan()`(`research_router.py:214`) + `query_notebooklm`/`ResearchMode`/`classify_research_depth`만. 어댑터 불가 시 §10 Q-S3을 "리서치 합성 미지원 → 스킵=UNVERIFIED"로 축소(폴백 안전망).
>
> **배선 3곳**: ① `interview.py:167` `auto_apply_defaults`→`synthesize_via_research` ② `agent_launcher.py:533` should_skip 시에도 골/테스트 합성 1회 ③ `stage_router.py:101-106` `_run_new_project` route_batch 경로
>
> **합성 실패 처리**: 엔진 미가용/빈 결과/어댑터 부재 → `provenance="default"` + `verdict="UNVERIFIED"` (완료계약 §4.2 폴백 정합, `is_done()==False`)
>
> **Q-S2 잔여 advisory (Q-S3에서 해소)**: RESEARCH_SYNTHESIZE pending 결과가 `value=None`이라 `stage_router.py:270`의 `values` dict + `ProjectGoalArtifact`에서 silent 누락 → 현재 사용자 피드백 부재. Q-S3에서 4개 필드(observable_goal 등)를 artifact에 surface해야 함.
>
> **순서 무관 대안**: Q-S5(`core/qa_report.py` HTML 렌더러, §9)는 Q-S3 독립 — `evidence_ledger` 입력 + provenance 뱃지/[확인 요망]. 더 가벼운 Tier 1~2.

### ✅ (Q-S2) RESEARCH_SYNTHESIZE + 4문항 + provenance 완료 (2026-06-19, Sonnet, `be884287`+`5fb3d8ad`)
> - `core/control/verdicts.py`: `QuestionRoute.RESEARCH_SYNTHESIZE = "research_synthesize"` (INV-Q1)
> - `core/control/question_router.py`: `route_batch()`에 RESEARCH_SYNTHESIZE 분기 추가 → `source="research_synthesize_pending"` (BLOCK/HITL 기여 안 함)
> - `core/control/questions/goal_clarification.yaml`: `observable_goal`/`golden_example`/`test_seam`/`manual_only` 4문항 추가 (`default_route: research_synthesize`)
> - `core/clarification.py`: `merge_clarification(provenance="default")` — log 엔트리에 `provenance` 태깅, 기존 호출 하위호환
> - `agent_launcher.py`/`interview.py`: HITL 경로 `provenance="user"` 수정 (af-critic WARN-2 반영)
> - 테스트 9건 신규(TestResearchSynthesizeRoute 4 + TestMergeClarificationProvenance 5) / 총 43 PASS
> - 3-Tier: af-critic WARN→수정 / af-cross-review PASS / af-test-runner 137 PASS

### ✅ (Q-S1) GoalEntry 확장 + TestManifest 완료 (2026-06-19, Sonnet, `bacafe3d`)
> - `core/completion_contract.py`: `Provenance` 타입(`user`/`research`/`default`) + `GoalEntry` 3개 additive 필드(`scenario`/`expected_output`/`provenance`) + `TestManifest` 신규(`required_tools`/`required_env`/`seam_requirements`/`provenance`) + `GoalContract.manifest: TestManifest|None`
> - 전부 기본값 하위호환 + round-trip 보장. 레거시 직렬화(필드 부재)도 기본값 복원.
> - 테스트 13건 신규 / 총 30건 PASS. 3-Tier: af-critic PASS / af-test-runner 252 PASS
> - 설계: `docs/2026-06-18-user-perspective-qa-pipeline-design.md §5`

---

## ▶ (이전 다음) 리뷰 합의 게이트 자연 발화 검증 또는 신규 product work-item

### ✅ (S3~S6) 증거수집 합의기 완료 (2026-06-19, Sonnet, 커밋: `6ec0d1bb`)
> - `scripts/review_consensus.py` 신규: finding-level 증거수집기(LLM 미호출). ACCEPT/ACCEPT★ finding마다 surrounding_code·callers(grep 1-hop)·callees(AST 1-hop, `_enclosing_function`+`_find_callees`)·tests 수집 → `cr_evidence.json` 생성
> - `af-cross-review.md` / `.codex/agents/af-cross-review.toml`: S3(finding 사이드카 `cr_findings.json` 저장 지시) + S6(Step 6: review_consensus.py 호출 → cr_evidence.json 읽기 → LLM 합의판정 ACCEPT/REJECT/UNVERIFIED → cr_consensus.json → verdict fence 재발행)
> - `scripts/review_gate.py`: `_extract_verdict_from_content`에서 `search()` → `finditer()[-1]` 교체 — 마지막 fence 우선(S6 재발행이 S5 fence 올바르게 대체). `test_c6_multiple_fences_last_pair_wins` 갱신.
> - UNVERIFIED는 BLOCK 기여 안 함(INV-5). 프로바이더 중립(INV-2).
> - 테스트: `test_review_consensus.py` 28케이스 PASS (INV-1/2/5/7 + enclosing-func·callees·callers·surrounding·ACCEPT★ 2건)
> - 3-Tier: af-critic BLOCK→수정(마지막 fence 정책) / af-cross-review SKIP(외부 프로바이더 없음) / af-test-runner 158 PASS

### ✅ (S2) 수렴감지 + 스코프게이트 완료 (2026-06-19, Sonnet, 브랜치: `2026-06-04-right-sized-execution-slice1`)
> - `scripts/check_design_pending.py`: `_normalize_entry`에 `last_block_sections`/`oscillation_detected` 필드, candidate 루프에 oscillation 체크(`[af-design-review-oscillation]` + 플래그 리셋), 발화 기록 dict 신규 필드 포함
> - `scripts/check_staged_design_review.py`: `_extract_block_sections()`/`_map_doc_to_queue_fname()`/`_record_verdicts_to_fired_marker()`/`_reset_verdict_in_fired_marker()` 신규, `main()`에 BLOCK verdict 기록 + PASS/WARN 시 last_verdict 초기화(false-positive 방지), importlib 실패 stderr 진단
> - `.claude/agents/af-cross-review.md` / `.codex/agents/af-cross-review.toml`: Step 2a 스코프게이트 지시사항 8번(WHAT→BLOCK, HOW→ACCEPT-ADV 강등)
> - 테스트: 72케이스 PASS (TestOscillationDetection 8 + TestExtractBlockSections 5 + TestMapDocToQueueFname 3 + TestRecordVerdictsToFiredMarker 4 + TestResetVerdictInFiredMarker 3)
> - 3-Tier: af-critic WARN(3) / af-cross-review BLOCK→2건 수정(PASS중간-last_verdict 미갱신, importlib stderr) / af-test-runner PASS(72)

### ✅ (S1) 설계문서 라운드 캡 완료 (2026-06-19, Sonnet, 브랜치: `2026-06-04-right-sized-execution-slice1`)
> - `scripts/check_design_pending.py`: `MAX_DESIGN_ROUNDS=3` + `_normalize_entry()` (float/dict 정규화, nan 방어) + candidate 루프 캡 체크(`[af-design-review-capped]` 1회 알림 + 발화 중단) + dict 포맷 발화 기록
> - `tests/test_check_design_pending.py`: 18케이스 신규 (INV-3 커버리지 완료)
> - 3-Tier: af-critic WARN(nan 방어 수정) / af-cross-review WARN(BLOCK 0, Advisory: `last_verdict` 기록은 S2 `check_staged_design_review.py`) / af-test-runner PASS(58=18신규+40회귀)
> - **미구현(S2 예정)**: `last_verdict` 기록 경로 (`check_staged_design_review.py`에서 verdict → fired marker 기록) + 수렴 감지(섹션 겹침) + 스코프 게이트(HOW → ACCEPT-ADV 강등)

### ✅ 리뷰 합의 게이트 설계 완료 (2026-06-19, Opus, 브랜치: `2026-06-04-right-sized-execution-slice1`)
> **설계 파일**: `docs/2026-06-19-review-consensus-evidence-gate-design.md`
> **계기**: `docs/2026-06-18-user-perspective-qa-pipeline-design.md` cross-review가 **5라운드 연속 BLOCK** 후 캡 종료. 복기 → **두 독립 실패** 진단.
> - **실패 B(자기유발 진동)**: 설계문서 경로(`check_design_pending.py`)는 라운드캡·수렴가드 *부재*(코드리뷰는 `MAX_ROUNDS=5` 있음). 매 라운드 내 수정이 다음 BLOCK 유발. → §4 수렴가드+스코프게이트(설계 `MAX_DESIGN_ROUNDS=3`, HOW 모순은 advisory 강등).
> - **실패 A(증거 미수집)**: finding 단위 증거 API 부재(`build_full`은 전체 파일만), finding은 산문 비가독. 지침으로 "grep 하라" 해도 LLM이 건너뜀. → §5 증거수집 합의기(코드가 caller/callee/test 수집 → 합의 LLM이 증거 위에서만 ACCEPT/REJECT). **코드리뷰 한정(INV-6 메타-재귀 경계)**.
> - **멀티프로바이더=코드로 중립**: 합의/수렴 로직을 Python에 두면 어느 프로바이더가 게이트 돌려도 같은 코드(INV-2). 산문 지침은 sync(`INSTRUCTIONS.md`→CLAUDE/AGENTS/GEMINI).
> - **교차검증**: af-cross-review **WARN**(BLOCK 0). §2 baseline 11개 라인인용 전수 사실확인 PASS. Advisory 3건 전부 HOW-깊이로 cross-review가 *자동 강등*(이 설계의 INV-4 작동 실증 — 5라운드 루프와 정반대). Finding 1(§5.6 verdict 연결경로)만 한 줄 보강.
> - **구현 슬라이스**: S1 ✅ → S2(수렴감지+스코프) ∥ S3(구조화 finding 사이드카) → S4(consensus.py+증거래퍼) → S5(callee) → S6(합의판정+verdict집계). **S1·S2(실패B)는 S3~S6(실패A)와 병렬 가능.**

### ✅ watcher 이식성 + 설계문서 재검증 완료 (2026-06-19, `90b5dfb4`)
- watcher: `_process_alive()` 신설(Windows ctypes OpenProcess / Unix os.kill 분기, WinError 87 해소) + `_is_watcher_alive` 교체 + `_start_watcher` DETACHED_PROCESS 플래그·close_fds 제거. 테스트 13케이스.
- 설계문서 `docs/2026-06-18-user-perspective-qa-pipeline-design.md`: §2.5 S2/S3 완료 갱신 + INV-Q4 enforcement 구체화 + §10 Q-S4 선행조건·pipeline 분해. **단 cross-review 5라운드 BLOCK 후 캡 종료** — 잔여 advisory는 Q-S4 구현 시 결정. (이 루프가 위 합의 게이트 설계의 계기.)

### ✅ (B) fail-closed 게이트 완료 (2026-06-18, Sonnet, `1374dd7b`)
- `scripts/check_staged_design_review.py` 확장: verdict 부재 시 provider 상태별 BLOCK/SKIP 분기
  - AVAILABLE → BLOCK (watcher 미실행 의심)
  - AUTH_EXPIRED(외부 전부 unavailable 중) → BLOCK + 재인증 안내
  - NOT_INSTALLED | RATE_LIMITED → ℹ️ 노티 + 커밋 허용
  - AVAILABLE 우선 수정: codex AVAILABLE + gemini AUTH_EXPIRED → "available"(watcher 가 codex 로 리뷰 가능)
- 테스트 29케이스 (신규 12개 포함). 3-Tier: WARN / BLOCK→수정(우선순위 역전) / PASS.

### ▶ (A) watcher 이식성 수정 — 미결, 별도 추적
- `_is_watcher_alive` os.kill Windows WinError 87 — `psutil` 또는 플랫폼 분기
- watcher codex CreateProcessWithLogonW 이식성 — spawn 방식 점검
- 멀티 프로바이더 headless 실행 경로 검증

**미결 산출물**: 설계문서 2건 Draft 완료 — `docs/2026-06-18-user-perspective-qa-pipeline-design.md`(af-cross-review BLOCK 3건 수동수정 완료, **재검증 미실시**) + `docs/2026-06-18-product-output-isolation-design.md`(af-cross-review PASS). 둘 다 구현 대기.

---

## ✅ "AF 완료 계약 — 증거원장 기반 goal-reached 검증" 설계문서 완료 (2026-06-17, Sonnet)

> **설계 파일**: `docs/2026-06-17-af-completion-contract-goal-verification-design.md`
> **교차검증**: af-cross-review WARN (BLOCK 0) — §6.3 High 1건 수정(FSA 재시도 → BLOCKED terminal 아키텍처). Advisory Medium 4건 미적용(의무 아님):
>   - §5.1 `test` harness 유형 누락 (기존 `_run_verify_phase`와 이중 실행 위험)
>   - §8 S3에 `contract_status` 구분 부재 (파싱 실패 vs old-state None 혼동)
>   - §2.3 단절④에 `verify_result` 기본값 `True` 취약점 추가 권장
>   - §2.2 라인 번호 정확도 개선 권장

## ✅ A·B 완료 (2026-06-18, Opus) — 다음 = (C) S1 구현

> **핵심 발견**: 자동 설계리뷰 watcher(`scripts/design_review_watcher.py`)는 **정상 작동**(provider 무관·headless로 `docs/reviews/*.md` 산출)하나 **결과 surface가 끊겨** §6.4 Critical BLOCK이 안 보인 채 커밋(`d1022ecd`)됐었다. A=잘못된 §6.4 재작성, B=surface 복원. 둘 다 완료·3-Tier 검증.

### ✅ (A) §6.4 inv3 정합 재작성 — 6 findings 반영 완료
> 근거: `docs/reviews/2026-06-18-015950-...-design-review.md` (BLOCK, 6건 전부 grep 검증). af-cross-review가 inv3 해소를 코드대조 **REJECTED(=위반 없음 확증)**.
- **#1 Critical**: §6.4를 "골 FAILED→dogfood IMPLEMENT 되돌림 + FSA max-retry 상수 재사용"(inv3 위반 + 사실오류)에서 **BLOCKED(goal_failed) terminal**(inv3 정합, `dogfood.py:2044`/`:1895`)로 재작성. 자동 수정 루프는 dogfood 밖 상위 재기동+신규 bound(`MAX_GOAL_FIX_REINVOCATIONS` 류) 요구 → **후속 별도 메커니즘으로 분리**(§6.4·§10). "재사용" 삭제(`fsa_loop.py` max-retry 상수 0건, 실재 bound=`dynamic_orchestrator.py:528` `_task_retry_count<3`).
- **#2 High**: GoalContract 생성 SSOT를 `prepare():1246`→`PreparedProject:74`로 명시(동기 `execute()` 경로 커버). **#3 Medium**: `goal_failed` classifier 변경 **제거**(no-op+소비처 없음). **#4 Medium**: `execute()` ok 단일화(`:1396`/`:1421` 동일 `gated_ok`). **#5 Medium**: `already_done` 조기반환(`:1301-1307`) contract 재집계/`already_done_legacy`. **#6 Low**: stale `:1845`→`:1891`/`:1899`. §9 INV-A/INV-G·§10·§11 연동 + §12 이력.

### ✅ (B) watcher 결과 surface 복원 — git-native pre-commit (provider 무관·사람입력 무관)
- **신규** `scripts/check_staged_design_review.py`: staged 설계문서의 `docs/reviews/` 최신 리뷰 verdict 확인 → BLOCK이면 exit 1. `is_design_doc`/`normalize_path` SSOT 재사용. 최신성=파일명 ts prefix(같은 source 새 PASS가 BLOCK 덮음). `_VERDICT_RE`가 볼드체 `**BLOCK**`도 흡수(실측 19파일).
- **`.githooks/pre-commit`**: review-gate 블록 직후 design check 추가(AF_SKIP_REVIEW_GATE 우회 공유, .py 없는 문서커밋도 발화).
- **테스트** `tests/test_check_staged_design_review.py` 17케이스. 3-Tier: af-critic WARN(2 advisory 반영) / af-cross-review BLOCK→fixed(볼드체 regex) / af-test-runner PASS(17+회귀11).
- **미채택(설계 결정)**: Stop hook 드레인 보류(pre-commit이 실패 케이스 `d1022ecd`를 정확히 차단하는 최소·자족 경로). 부수버그 `_is_watcher_alive` os.kill Windows WinError 87 / watcher codex CreateProcessWithLogonW:1909 단일vendor는 **미수정**(surface와 독립, 별도 추적).

### ✅ (C) S1 완료 (2026-06-18, Opus) — 다음 = S2 (ExecutionHarness + AcceptanceGate)
> **S1 완료**: `core/completion_contract.py` 신규(`GoalVerdict`/`GoalEvidence`/`GoalEntry`/`GoalContract`/`HarnessResult`) — 순수 데이터 구조 + 직렬화만. `GoalContract.is_done()`(INV-A: 빈 계약 불가, UNVERIFIED/FAILED 차단, CANNOT_VERIFY done 허용) + `has_failures()` + 중첩 `to_dict/from_dict` round-trip. `DogfoodState.goal_contract: GoalContract|None` persist 채널 배선(import + 직렬화). `af.spec` hiddenimports. `tests/test_completion_contract.py` 17케이스 + `test_dogfood.py` key-set 갱신. 3-Tier(§8 S1=Tier 2, subprocess 미도입): af-critic PASS(발견 0) / af-test-runner PASS(290 = 17 신규 + 273 회귀). Blueprint §0·§12 갱신.
>
> **선행조건 메모(S1엔 불필요, S3 파서용)**: 실제 LLM criteria(task_board `acceptance_criteria`) 출력 샘플 캡처는 §10에서 "파싱 로직은 S3에서 결정"으로 분리 — S1 산출물(구조체+직렬화)엔 파서 없음. S3 진입 전 baseline 캡처(메모리 `analysis_doc_baseline_must_be_real_code`).

### ✅ (C-S2) ExecutionHarness + AcceptanceGate 완료 (2026-06-18, Haiku, `03a78052`)
> - `ExecutionHarness`: cli/server/library/gui/none harness_type별 subprocess 실행. DEVNULL deadlock 방지. `shlex.split ValueError → evidence_type="unverified"` (§6.2 불변식). `_SERVER_STARTUP_WAIT_SEC` 상수.
> - `AcceptanceGate`: GoalContract 순회, idempotent (VERIFIED/FAILED/CANNOT_VERIFY skip), gui→CANNOT_VERIFY, evidence_type="unverified"→UNVERIFIED 판정.
> - `tests/test_acceptance_gate.py` 46 케이스. 3-Tier: af-critic WARN(2건 수정: DEVNULL+상수화) / af-cross-review WARN(2건 수정: shlex ValueError FAILED→UNVERIFIED, _run_server docstring) / af-test-runner FAIL→46/46 PASS(shlex posix import 추가).
> - wiring deferred (S3에서 dogfood.py/project_pipeline.py 연결).

### ✅ (C-S3) pipeline 배선 완료 (2026-06-19, Sonnet, `6808dd3d`)
> - `parse_acceptance_criteria()` / `build_evidence_ledger()` 헬퍼 신설
> - `PreparedProject.goal_contract` 필드 + `prepare_documents()` GoalContract 생성 (TYPE_CHECKING guard)
> - `execute()`: AcceptanceGate 게이팅 — `gated_ok`/`gated_reason`/`evidence_ledger`
> - `already_done` 재집계 / `contract=None` → `already_done_legacy` (Finding #5)
> - `dogfood`: `_run_develop_full` goal_contract 추출 / `_run_verify_phase` AcceptanceGate / `_run_review_phase` BLOCKED(goal_failed) 조기반환 (inv3 terminal)
> - 버그픽스 2건:
>   - `work_item_parser.py`: 영어 `Acceptance Criteria` heading fallback 추가 (generator-parser 불일치 해소)
>   - `project_pipeline.py`: `AcceptanceGate.run(contract, workspace)` — `state_workspace` 오전달 수정
> - `tests/test_acceptance_gate_integration.py` 34케이스 신규. 3-Tier: af-critic PASS / af-cross-review BLOCK 2건 수정→PASS / af-test-runner 216 PASS
>
> **메모리**: `project_completion_contract_and_review_surfacing`

---

## (이력) 다음 세션 = product-value work-item 신규 선정 — wiring-parity-gate 완료 (2026-06-12, Sonnet)

> **✅ wiring-parity-gate 완료 (2026-06-12, Sonnet, `5a16df39`)**: `test_gap_analyzer.py`에 배선 단선 검증 룰 추가.
> - **설계 문서**: `docs/2026-06-12-wiring-parity-gate-design.md` (af-cross-review PASS, 2026-06-12 Opus).
> - **구현**: `_WIRING_EXEMPT_PATHS`/`_WIRING_DEFERRED_MARKER` 명명 상수 + `_extract_wiring_candidates`(diff→신규def/파라미터추출) + `_find_production_callers`(core/scripts/skills grep, tests/제외, 정의파일 self 제외) + `_any_caller_passes_param`(def 행 제외 keyword 검색) + `_has_deferred_marker`(±1줄). `__init__` 파라미터 skip(INV). `core/utils.py` 면제. `analyze_diff` warnings 채널 배선(verdict=PASS 유지, WARN-only).
> - **테스트**: `tests/test_wiring_parity.py` 11케이스 신규. `af-critic.md` Step3 High 체크리스트 1줄.
> - **3-Tier**: af-critic PASS / af-cross-review WARN(BLOCK 0, Advisory Medium: file-level false negative — 동일 파일 내 무관 `param=` 오탐 가능, WARN-only로 완화됨) / af-test-runner PASS(22). Windows CP949 em-dash 버그 수정 포함.
> - **Advisory 잔여(선택)**: file-level `param=` false negative → `sym(` 포함 라인만 스캔으로 개선 가능. false-positive 실측 N≥10 run 후 dead-parameter BLOCK 승격 여부 결정.
>
> **▶ 다음 = product-value work-item 신규 선정.** GitNexus Step 0 PoC(미실행) 또는 외부 부착 end-to-end 라인 또는 신규 발굴.

---

## (이력) 다음 세션 = product-value work-item 신규 선정 — WI-B STEP 2-b 완료 (2026-06-12, Opus)

> **✅ WI-B STEP 2-b 완료 (2026-06-12, Opus)**: `build_llm_wiki`를 AF 전용 → **외부 프로젝트 full-wiki(AST architecture)**로 확장.
> - **구현**: ① AF 문서 3종(Blueprint/code-review/NEXT_STEPS) `_read_optional`로 전환 — 부재 시 의존 페이지(blueprint/*, code_review/*, review_patterns, open_items) skip ② `_build_codebase_tree(symbols)` 신규 — AST 심볼 맵을 디렉터리별 모듈 navigation 섹션으로 렌더(외부 프로젝트도 navigation 제공) ③ `_build_architecture`에 AST 섹션 항상 추가(AF=Blueprint 테이블+AST, 외부=AST만) — 페이지 수 14 불변(회귀 0) ④ `_build_index` 적응형(`_INDEX_LINKS` 상수, 생성된 페이지만 링크) ⑤ `_build_source_refs` 적응형 ⑥ 심볼 `collect_symbols` 1회 수집 공유.
> - **CLI 신규**: `af project wiki <path> [--out DIR]` (`agent_launcher.py` dispatch + `af.spec` hiddenimports).
> - **테스트**: TestExternalProject 8 + AF AST 1 = 9 신규, `test_build_llm_wiki` 37 PASS (전체 56 PASS).
> - **3-Tier 완주**: af-critic PASS(발견 0) / af-cross-review WARN[single-vendor](BLOCK 0, Advisory Medium 1 — `--out` 기본값 외부 docs/ 오염, 자동수정 의무 없음) / af-test-runner PASS(56 + 배포 동등성).
> - **🔬 STEP4 부수 측정 (자연 pre-commit 조건 첫 성립)**: review_bundle §5 Direct Callers = **callers=7/7 채워짐**(RMS 1차·blueprint 2차에서 둘 다 비어있던 그 섹션). cross-review **6.8분 / 78.2k** = 32분 baseline 대비 4.7× 빠름, extension log 0(번들 §5 1차 근거 사용). **단 codex MCP가 또 비활성 → Claude 단독(single-vendor)** → 시간 단축에 외부 deliberation 부재 혼입. 헤드라인 benefit은 codex 활성+§5 채워짐 동시 조건 필요(여전히 미충족). 사실 동결: 메모리 `project_af_gate_efficiency_debate`.
> - **잔여 advisory(선택)**: `af project wiki` `--out` 기본값을 외부 프로젝트엔 덜 침습적인 경로로 바꿀지(WARN, 의무 아님). **STEP 3(보류)**: dogfood ContextPack 주입은 기각 이력(메타-재귀).
>
> **▶ 다음 = product-value work-item 신규 선정.** GitNexus Step 0 PoC(미실행) 또는 외부 부착 end-to-end 라인 또는 신규 발굴.

---

## (이력) cross-review 입력 배선 STEP 4-rerun(선택) — STEP 1·2·4(1차) 완료 (2026-06-12)

> **STEP 1·2·4(1차) 완료 (2026-06-12, Opus).** 사실·계획·측정결과 동결: 메모리 `project_af_gate_efficiency_debate`. **재분석 금지.**
>
> **△ STEP 4 (controlled 측정 강행) 1차 완료, 단 불완전**: `root_mean_square` leaf util(12줄, Tier2, 커밋 `83dd4662`) → af-cross-review 직접 호출(gemini는 `AF_SKIP_PROVIDER=gemini_cli` 우회). **결과: 34분→10.8분(3.2× 빠름), 77k→63k토큰(-18%), 메커니즘 전부 PASS**(청킹 index·번들 임베드·§5 포함·Codex가 §5 근거로 자율탐색 안 함·extension log 0·6파일 read). **그러나 깨끗한 A/B 아님(overclaim 금지)**: ① Tier 불일치(3 vs 2) ② **핵심 benefit 미측정** — RMS는 신규 leaf라 callers 0 + commit-first 탓에 번들 §2 Git Diff 비고 changed_symbols=0 → §5 애초 비어있었음. side-effect 커버리지 가치는 **callers 있는 함수를 pre-commit 게이트(번들 §5 채워진 상태)로** 재측정해야 진짜 입증 ③ 남은 ~11분은 codex 자체 리뷰패스+deliberation. **방향성 확인→STEP2 유지 정당, "분 단위"·side-effect benefit 미입증.** advisory: blueprint_updater 신규 심볼 §3.12 자동반영 못 함(WARN).
> **▶ STEP 4-rerun (선택, 다음)**: callers 있는 함수를 pre-commit 게이트로 측정(§5 채워진 상태). 자연 발화 run으로 대체 가능.
> **STEP 3 (정책·선택·안급함)**: `_find_direct_callers` 1-hop/max3/core+scripts 한계 넓힐지 = "안전 vs 빠름" 다이얼. STEP4-rerun 결과 보고 사용자 결정.
>
> **▶▶ 다음 세션 미결 (3건 전부 소진/측정 — 2026-06-12)**:
> 1. ~~**(권장·먼저) RMS 정식 3-Tier 완주**~~ ✅ **완료 (2026-06-12 Opus)**: `83dd4662` `root_mean_square` 잔여 2-tier — **af-critic PASS**(발견 0) + **af-test-runner PASS**(RMS 6 + 전체 272, gap PASS). cross-review WARN(BLOCK 0) 포함 완주. 코드 변경 0.
> 2. ~~**(advisory) blueprint_updater 신규 공개심볼 누락**~~ ✅ **완료 (2026-06-12 Opus, `a32c382d`)**: positional 캡(`funcs[:3]/[:6]`)으로 파일 뒤쪽 공개함수가 §3.12 자동요약에서 누락되던 결함 해소. 신규 `_changed_public_symbols()` — git diff `+def`/`+class` + `@@` 헌크 컨텍스트 enclosing 함수를 **change-relative** 추출(전체 반영 아님 — bloat 회피; utils.py 공개함수 54개라 "전체"는 과설계). `_update_section_3_auto_summary` 배선 교체(+폴백). **부수**: `_git`에 `encoding=utf-8,errors=replace` 추가 — Windows cp949 기본이 diff 비-cp949 문자(em-dash·수식)에서 `stdout=None` 만들던 잠재 결함(전 호출자 공유). 테스트 5건. 3-Tier: af-critic WARN→해소(헌크컨텍스트) / af-cross-review PASS(BLOCK 0, Low 2) / af-test-runner PASS(5+회귀 86). gate state gap stale-BLOCK은 우회(실완주).
> 3. ~~**(선택) STEP 4-rerun**~~ △ **2차 측정 (위 #2 cross-review가 vehicle 겸용), 단 또 미입증**: blueprint_updater(callers 有: `dogfood.py:972`)를 staged로 af-cross-review — **~15.3분 / 80k토큰 / Codex CLI fallback 단일라운드 / PASS**. 단 **번들이 또 stale** → cross-review가 "bundle stale, git 직접 실험으로 대체" 보고 → **§5 채워진 번들의 side-effect benefit은 여전히 미입증**(staged 직접 호출이라 pre-commit 번들 재생성 안 됨; RMS 1차와 동일 한계). **진짜 입증하려면 자연 pre-commit 발화 run 필요**(staged 우회 측정으론 번들 stale 반복). STEP2 방향성은 유효, 헤드라인 benefit은 2회 연속 미측정.
>
> **▶ 다음 = product-value work-item 신규 선정** (미결 3건 소진). STEP4 side-effect benefit은 자연 dogfood/pre-commit run에서 기회 측정.

---

## (이력) cross-review 입력 배선 STEP 1·2 상세

> **STEP 1·2 완료 (2026-06-12, Opus).** 사실·계획 동결: 메모리 `project_af_gate_efficiency_debate`. **재분석 금지.**
>
> **✅ STEP 1 (진단·코드0) 완료**: `scripts/hook_runner.py:165`가 모든 `.py` 편집 시 `build_review_bundle.py`를 호출 → `review_bundle.md`는 **항상 생성됨**(현재도 존재, §5 Direct Callers 포함). 32분 정체는 번들 *미생성*이 아니라 Step 2a 프롬프트가 그 번들을 *안 써서*(단선) — 팩트 4 확정(무시, not missing).
>
> **✅ STEP 2 (본체) 완료**: `.claude/agents/af-cross-review.md` 3개 편집(에이전트 지시문 텍스트만, core 코드 로직 0, 되돌리기 쉬움):
> - 편집1 (Step 1): `REVIEW_DOC`을 raw 7302줄 → **청킹 index**(`docs/generated/llm_wiki/code_review/index.md`, 없으면 raw fallback) 재지정 + `review_bundle.md`를 `/tmp/af-review-bundle.txt`에 준비(stale/absent 시 fallback 문구, 입력정책 라인461과 동일한 `-nt` stale 판정).
> - 편집2 (Step 2a 프롬프트): `[변경 diff]` 뒤 `[Review Bundle — side-effect 표면 이미 수집됨]` 섹션 추가(§5 Direct Callers 임베드). 지시1="청킹 index에서 관련 섹션만", 지시4="호출자는 번들 §5에 이미 있음 → 1차 근거로, 구체적 risk 가설 있을 때만 추가 Read+사유 명시".
> - 편집3 (python 치환): `BUNDLE_PLACEHOLDER` 치환 1줄 추가.
> - **검증**: 치환 로직 스모크 PASS — 잔여 PLACEHOLDER 0 / Direct Callers·§5 헤더·청킹 index 임베드 확인. `.md`만이라 review-gate 자동통과.
>
> **실측 baseline (STEP2 前)**: `af project symbols` 12줄에 교차검증 136k토큰/37분(cross-review 단독 77k/32분), BLOCK 0 advisory 1.

---

## 🎯 다음 세션 최우선 진입점 (2026-06-11 준비 — Opus)

> 이번 세션 grep으로 확정한 work-item 2건. **둘 다 메타-재귀 아님** — 멀티 프로바이더 하네스 정합성 + 토큰 절감(실제 product value). 상세 팩트 동결: 메모리 `project_provider_instruction_parity`. **재분석 금지 — 아래 좌표는 grep 확정.**

### WI-A: 멀티 프로바이더 지침 SSOT 정합성 — ✅ 구현 완료 (2026-06-11 Sonnet)
- **✅ 설계 완료**: `docs/2026-06-11-provider-instruction-ssot-design.md`.
- **✅ 구현 완료 (2026-06-11 Sonnet)**: `INSTRUCTIONS.md` 신규(공통 SSOT) + `scripts/sync_provider_instructions.py` 신규(marker-injection) + `generate_agents_md.py` `render_roster()` 추가·`main()` sync 위임 + `.githooks/pre-commit` sync 트리거 추가(commit 차단 포함). INV-1~8 27 테스트 PASS. 3-Tier: af-critic PASS / af-cross-review PASS(BLOCK 0, Advisory 3건 무해) / af-test-runner PASS(3145 PASS). Codex/Gemini 실무규칙 전달 채널 복원.
- **다음 = WI-B 또는 다른 product-value work-item.**

### WI-B: LLM Wiki 청킹본 우선 활용 + 외부 프로젝트 AST 인덱스 — ✅ 완료 (2026-06-11 Sonnet)
- **✅ STEP 1 완료 (2026-06-11 Sonnet, `df3cb933`)**: LLM Wiki 청킹 활용 규칙을 INSTRUCTIONS.md SSOT에 추가 → CLAUDE/AGENTS/GEMINI 3 파일 자동 전파.
- **✅ STEP 2 완료 (2026-06-11 Sonnet, `a6f53fdc`)**: `af project symbols [path] [--out DIR]` 서브커맨드 추가. `codebase_symbols.build()` 재사용. `is_dir()` 체크(Medium advisory 수용). 12 테스트 신규(INV-1~4). 3-Tier: af-critic PASS / af-cross-review WARN(BLOCK 0) / af-test-runner PASS(117).
- **STEP 3 (보류)**: dogfood ContextPack 주입 — 기각 이력(메타-재귀), STEP1/2 효과 확인 후 재평가.

### GitNexus 도입 검토 — ✅ 분석 완료 / 도입 미실행 (2026-06-11)
- **사실 동결**: 메모리 `project_gitnexus_adoption_review`. 패키지명 `gitnexus`(Node, Python3.14 무관, 즉시 실행 가능). 코드 의존성 그래프(import/호출/상속) + 16 MCP 도구(impact/context/query/detect_changes 등).
- **중복 결론**: graphify 死상태 직접대체 / blast_radius·symbols 보완(대체 불가) / memory graph·LLM Wiki 무중복(L1만 겹침).
- **회의용 문서**: `docs/2026-06-11-gitnexus-code-intelligence-도입검토.md`(`1eed96ee`). 사용자가 회사 RAG 논의와 합쳐 사용.
- **다음 = Step 0 PoC (미실행)**: 격리 임시폴더 복제 → `npx gitnexus@1.6.7 analyze` → 인덱싱시간·DB·impact정확도 측정. ⚠️ analyze가 AGENTS.md/CLAUDE.md/hook 덮어쓰기 위험 → AF 루트 직접 실행 금지.

- **다음 = product-value work-item 신규 선정 또는 GitNexus Step 0 PoC.**

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
 - **✅ skill-quality-gate (1+1) fitness 게이트 구현 완료 (2026-06-10, Sonnet, `d313d638`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: baseline 경로 silent-fail 버그 수정(`os.path.join(baseline_dir, "skill.py")` 정규화) + `_shadow_not_regressed()` delta>0 게이트 + `MIN_SHADOW_CASES=3` + `GateResult.quality_delta` 반환 + `skill_evolution_controller._run_quality_gate` baseline_dir 배선. INV-1~7 테스트 9건 신규. 3-Tier PASS. **다음 = S2(hidden 과적합 탐지) 또는 다른 product-value work-item.**
 - **✅ feat(utils): running_min + skewness 신규 함수 (`c734f1c1`)**: running_min(누적 최솟값), skewness(Fisher 왜도). 테스트 19건.
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
 - **✅ test_dogfood_realignment 2건 FAIL 수정 (2026-06-10, Sonnet, `bde577d2`)**: `test_inv4` + `test_inv5`에 `monkeypatch.setattr("core.right_sized_router.classify", ...)` 추가 — fallback RouteDecision(source="fallback", confidence=0.0) 반환으로 LLM 호출 차단 → full path로 FakePipeline 호출. 5/5 PASS.
 - **✅ check_pending_review rate_limited skip (2026-06-10, Sonnet, `2fa89587`)**: 외부 프로바이더 전부 RATE_LIMITED 시 `[af-review-pending]` 발화에서 af-cross-review 제거. `_all_external_providers_rate_limited()` 헬퍼 + `_agents_for_tier()` t3_skip_reason 파라미터. 테스트 2건. 25/25 PASS.
 - **✅ feat(utils): mean_absolute_deviation + exponential_moving_average (2026-06-10, Sonnet, `b60bae6a`)**: MAD·EMA 신규 함수. 테스트 18건 신규(266 PASS). LLM Wiki/Blueprint 자동 갱신. 3-Tier PASS.
 - **✅ fix(pending-review): NOT_INSTALLED 프로바이더 af-cross-review 스킵 포함 (2026-06-10, Sonnet, `b6323a1a`)**: `_all_external_providers_rate_limited` → `_all_external_providers_unavailable` 리네임. 스킵 조건: RATE_LIMITED만 → NOT_INSTALLED | RATE_LIMITED. gemini CLI 미설치 환경에서 af-cross-review 불필요 발화 방지. AUTH_EXPIRED는 스킵 제외(재인증 안내 필요). 테스트 25/25 PASS.
 - **✅ dogfood 버그 B3 + B2 완료 (2026-06-11, Sonnet, `0354224c`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**:
   - **B3**: `_develop_isolation_env`에 `AF_SKIP_REVIEW_GATE=1` 추가 + `_ISO_ENV_KEYS` 포함 → worktree 내부 커밋이 source-repo review-gate hook에 막히던 문제 수정
   - **B2**: `failure_classifier._INFRA_PATTERNS`에 `"auth_expired"` 추가 + `fsa_loop` INFRA 즉시 중단 → AUTH_EXPIRED가 IMPLEMENTATION 오분류되어 FSA 100+ 재시도하던 문제 수정
   - 테스트 25/25 PASS, 전체 3119 PASS. 3-Tier 완주.
   - **B1 (복잡, 보류)**: 단순 patch task에 멀티에이전트 orchestrator 과분해 — RSE 설계 필요, 별도 세션
   - **다음 = product-value work-item 신규 선정**
 - **✅ fix(dynamic_orchestrator): infra-only stall LLM 개입 차단 완료 (2026-06-11, Sonnet, `77e05ad4`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: `_needs_llm_intervention` 분기 3에 infra-only 실패 감지 추가 — 최근 실패 전부 `failure_category="infra"`이면 `return False`(LLM 재시도 차단). `0354224c` fsa_loop INFRA 즉시 종료의 orchestrator-레벨 보완층. 테스트 2건 신규(11/11 PASS). 3-Tier 완주.
 - **✅ 자가수정 brain Provider-Awareness 구현 완료 (2026-06-11, Sonnet, `08e04ebf`, 브랜치: `2026-06-04-right-sized-execution-slice1`)**: 설계(`docs/2026-06-11-self-correction-provider-awareness-design.md`) → RED(INV-1~6) → GREEN(3파일 각 1줄 + import) → 3-Tier PASS. ① `ise_analyzer.py:20,68` ② `ise_redesigner.py:24,49` ③ `evaluator.py:4,16` 전부 `LLMEngine` → `ControlPlaneLLM`, model_name default `None`. ④ `fsa_loop.py:87` fallback `"gemini-1.5-pro-latest"` → `None` (D1 완전 반영). 테스트 INV-1~6 + 기존 7건 모두 PASS. af-critic PASS / af-cross-review WARN(BLOCK 0, Medium 2·Low 1 수용) / af-test-runner PASS. **동작 변화**: CLI 환경에서 FSA 자가수정 두뇌가 실제 LLM 호출로 전환 (비용↑·품질↑). **다음 = product-value work-item 신규 선정.**
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
