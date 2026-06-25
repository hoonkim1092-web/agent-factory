---
name: project_knowledge_library_design
description: "자가진화 지식 도서관 — git vault + Obsidian + 증류. STAGE 0·1·2·R·3·4 전부 완료(2026-06-25). 다음=신규 product work-item 또는 STAGE 5(NEXT_STEPS 다이어트)."
metadata: 
  node_type: memory
  type: project
  originSessionId: cb9199f8-8f7d-42d5-ae25-b35b93d031d2
---

**자가진화 지식 도서관** 설계 (2026-06-23, Opus). 설계문서: `docs/2026-06-23-knowledge-library-evolution-design.md`.

**계기**: 사용자가 Karpathy "제2의 뇌/LLM Wiki" 판매자료를 가져와 "내/팀 지식 도서관 + Obsidian 시각화 + 자가진화" 원함. 대화로 좁혀 동결한 결정(재론 금지):

- **D1 단일사용자·다중PC** (팀 아님 — "팀"은 본인이 PC 옮겨다녀서 한 오해. multi-writer 머지/로그인/권한엔진 비범위)
- **D2 저장소=git** (새 DB/SaaS 금지). 지식 vault를 git에 두면 코드와 같은 히스토리 → PC간 드리프트 소멸 + commit핀 공짜. (Supabase memory는 빠른 scratch로 유지, 승격만 단방향)
- **D3 raw 트랜스크립트 미동기화** (189MB·평문·노이즈, git large-file 정책 위반). 증류본+포인터만. raw는 어차피 맥락통로에 없음(안 읽힘)
- **D4 식별·접근제어=seam만** (enforcement 코드 금지). author frontmatter + restricted/ 폴더. 팀 전환시 git/GitHub이 공짜 제공
- **D5 NEXT_STEPS 다이어트, 퇴역 아님** (정밀참조 commit/line/INV는 손실압축 불가)
- **D6 provider-neutral** (control_plane_llm SSOT)

**핵심 통찰**: PC전환 드리프트(STALE vs SKEW)·맥락단절·멍청한 증류(session_bridge 260자 truncate)가 다 "지식과 코드가 따로 동기화돼서". git vault가 이걸 구조적으로 해소.

**STAGE (메타프롬프트 형식, §5)**: 0=vault통합(보이게,docs/wiki/{code,knowledge}) → 1=노트스키마+seam → 2=증류기(truncate→LLM) → 3=staleness점검기(af knowledge doctor) → 4=auto-link → 5=NEXT_STEPS다이어트. MVP=0~2.

**substrate 70% 이미 존재**: llm_wiki 41파일(wikilink,Obsidian호환), memory/ 112파일, session_bridge 멀티프로바이더, resume_brief, Supabase sync. 순신규=LLM증류+staleness+vault통합.

**af-cross-review R1 BLOCK 흡수 완료** (single-vendor, codex MCP 미연결):
- F1(High): §2.4 "Stop hook 이미 배선" 자기모순 → 정정. **증류 발화점=`session_adapter.py:690` SessionEnd/PreCompact(run_bridge 기존), Stop 아님**. STAGE2는 기존 경로 교체.
- F2: §2.2 global_user_key 귀속오류 → sync는 project_id 키, global_user_key는 session_bridge:415 필드
- F3: originating_pc 포인터 필드 미존재(session_bridge details엔 session_file/line만) → STAGE2가 socket.gethostname() 추가

**INV-K7 주의**: `build_llm_wiki.py:590,601`이 out_dir stale unlink → knowledge/는 out_dir 밖 형제폴더(docs/wiki/knowledge, code는 docs/wiki/code).

**메타-재귀 경계**: product 표면(af project wiki 이미 출하)이나 빌드시 과게이트 절제. 작은 STAGE 표적검증, core/만 풀3-Tier.

**STAGE 0 완료** (2026-06-23, Sonnet, `2108d34a`): vault 통합 `docs/wiki/{code,knowledge}` + build_knowledge_wiki.py.

**STAGE 1 완료** (2026-06-23, Opus): `core/knowledge/note.py` 신규 — `KnowledgeNote`(타입 SSOT) + `to_md`/`from_md` round-trip(json.dumps frontmatter=콜론·따옴표 안전, JSON⊂YAML) + `new_note()`/`make_id()` 자동스탬프. id `{type}/{machine}-{micro시각}-{rand6}-{slug}.md`(마이크로초+rand 무충돌 INV-K11, Windows 금지문자 회피, 한글 slug 보존, `:` 회피). scope(D12)·visibility(D11) seam — enforcement 0건(INV-K6). 테스트 17건 PASS. af.spec+Blueprint §0/§12. 3-Tier: critic BLOCK=오탐(partition 첫콜론만 분리, 테스트로 반증)/cross-review PASS BLOCK0(single-vendor)/test-runner PASS. **미커밋(사용자 명시 요청 대기)**.

**STAGE 2 S2-1+S2-2 완료** (2026-06-23, Opus, 커밋 `4f4560ed`): `core/knowledge/distill.py` 신규 — `mask_secrets`(sk-/sk-proj-/sk-ant-/ghp_/AKIA/Bearer/PEM/라벨=값·JSON→[REDACTED], 정밀참조 보존, 입력·출력·title 마스킹) → `extract_precise_refs`(commit숫자요구/file:line경로prefix/INV명 verbatim·중복제거, INV-K5 LLM paraphrase 방어) → `control_plane_llm.generate_json` 증류(INV-K4, DI) → 포인터{originating_pc,session_file,line}. LLM 실패해도 노트 생성. `session_bridge.py` details에 originating_pc(F3). `note.py` `_git` stdin=DEVNULL(hook WinError6 방어→created_commit 캡처). tests 17. 3-Tier: critic BLOCK2(secret누출 sk-proj-/JSON라벨, 수정)/cross BLOCK High1(test raw subprocess WinError6→_git stdin=DEVNULL 근본수정)+adv/runner PASS. 전부 single-vendor(codex rate-limit 6-25). 보류 advisory: 싱글턴 런타임교체(DI회피)·.gitignore무확장 ref미추출.

**STAGE 2 S2-3 배선 완료** (2026-06-23, Opus, 커밋 `68cd91c2`): `session_bridge.run_bridge` 반환에 `events` 추가(이중 cursor 회피, main() stdout엔 pop). `session_adapter._distill_to_vault(events, repo_root, provider_id)` best-effort 헬퍼(전구간 try/except+지연import)가 **두 발화점**에서 호출. **핵심 판단 2건(동결 문구 보정)**: ①두 발화점 필수 — codex는 `cli_hook_bridge --provider`(claude/gemini만)에 없어 `:691`(hook) 미도달, codex 유일 경로=`:583`(`finalize_cli_session`). :690만 배선하면 codex 영영 증류 안 됨 → INV-K4 parity 위해 `:583`+`:691` 둘 다. ②vault=`repo_root`/docs/wiki/knowledge (NEXT_STEPS 초안 "workspace"를 repo_root로 보정 — workspace는 임의 사용자 프로젝트일 수 있음, INV-K1 git-tracked repo·INV-K3 created_commit 정합). tests: test_distill_wiring 8 + test_session_bridge +2(41 PASS). 3-Tier: critic PASS(발견0)/cross WARN[single-vendor] BLOCK0(adv 2 보류:gethostname중복·LLM첫latency)/runner PASS. **★성공기준(§9) 실측 미수행** — 실제 세션 종료가 vault에 노트 쌓은 뒤 `docs/wiki/knowledge/session/`에서 commit·결함번호 보존율 확인.

**STAGE 3 완료** (2026-06-25, Sonnet, 커밋 `6a1c1322`): `scripts/af_knowledge_doctor.py` 신규 — STALE/SKEW staleness 점검기. created_commit 로컬 미보유→SKEW / 있음+file:line 변동→STALE. advisory-only(리포트만, 자동 삭제/수정 금지). `Finding`, `check_note()`, `run_doctor()`, `main()`. `--vault`/`--repo`/`--json` 지원. `agent_launcher.py`+`run_factory_cli.py` doctor dispatch 등록. af.spec hiddenimport. tests 23건 PASS. 3-Tier: critic WARN2 BLOCK0 / cross-review WARN3(F1 startswith:·F2 Path(__file__) 반영) BLOCK0 / test-runner 77 PASS. **다음=신규 product work-item 발굴 또는 codex cross-vendor 재검증(rate-limit 2026-06-25 06:41 KST 이후)**.

**순서 판단 동결** (2026-06-24, Opus — 설명·설계검토 세션, 코드 0변경): "NEXT_STEPS ↔ 대화 증류 연결해야 하나?" 팩트 검증 결론. 연결은 설계상 이미 존재(§9#2=`증류본이 손작성 NEXT_STEPS 정밀참조 보존`, STAGE 5 승격, INV-K8). 그러나 §9#2 한 번도 미측정 + 증류 노트는 retrieval 없어 현재 **고아 아카이브**(써놓고 안 읽힘, NEXT_STEPS만 세션시작 읽힘). **실행순서 = ①S2-3 실측(증류 vs NEXT_STEPS 보존율=연결가부의 답) → ②통과시 STAGE R 검색방향(read-only·advisory, 원장 안 망침) → ③자동생성(NEXT_STEPS auto-draft)은 마지막(미검증 lossy 원장오염 위험)**. 측정 없이 연결 금지. cf. ①번 LLM Wiki(code/)는 커밋마다 재생성=거울이라 낡지 않음 / ②번 knowledge/는 증류·생성이라 STAGE 3 doctor 필요. INV-K7로 두 폴더 물리분리(build_llm_wiki는 code/만 write).

**S2-3 §9 precision 실측 PASS** (2026-06-24, Opus, 커밋 `66aa7377`): vault 첫 증류 노트(`DESKTOP-JPHA09P-...ise-자가수정-brain`, created_commit 68cd91c2) 정밀참조 전수 git/grep 감사. **commit 20/20 실존·file:line 13/13 정확·INV-1/5 정합·정밀참조 채널(INV-K5 deterministic) 100% precision, 조작 0건** → NEXT_STEPS에 흘러들 채널의 (a)조작 실패모드 닫힘. **D5 lossy/precise 분리 실증**: 유일 결함은 LLM 산문 본문의 fuzzy 참조 1건(`2026-06-11-020117-…design-review.md` 말줄임표 truncation, 실재X — 정밀참조 원장 무관). §9 3분할: precision ✅ / recall(raw 누락) ⏸집PC raw 필요 / 멀티프로바이더 동일산출 ⏸cross-provider 실행 / secret 마스킹 ✅. **판정=precision PASS → STAGE R(read-only·advisory) 진입 정당**(read-only라 recall 미측정이 원장오염 위험 안 키움). recall·멀티프로바이더는 ③자동생성(lossy write) 진입 전에만 닫으면 됨.

**위키 빌더 크로스-PC 비결정성 버그 해소** (2026-06-24, Opus, Fix B, 커밋 `1c0201a3`): NEXT_STEPS 진단이 **거꾸로였음** — 이 PC(HOON-KIM)가 "심볼 누락"한 게 아니라 집 PC가 symbols.md를 dogfood 잡파일로 오염. 근본원인=`collect_symbols`(scripts/codebase_symbols.py)가 rglob로 작업트리 전체(git untracked 포함) 스캔 → 집 PC `artifacts/af-dogfood-*/` untracked .py 4,656개가 박혀 60,847줄. **Fix B**: `_git_tracked_candidates` 신규 — git repo면 `git ls-files`로 추적 파일만(비-git·추적0건은 rglob 폴백) → 산출이 커밋된 소스의 결정적 함수=PC무관. dogfood 잡파일은 untracked-but-not-ignored라 제외목록/.gitignore 못 잡아 추적-only가 유일 근본해법. symbols.md 60,847→8,838줄(789 추적모듈). 3-Tier: critic PASS/test-runner PASS(119)/cross 보류(codex rate-limit). **이제 wiki-trigger 파일 커밋 시 `--no-verify` 불필요**(hook 위키 재생성 안전). 부수: hook이 HOON-KIM 증류 노트도 자동 stage→증류 파이프라인 멀티PC 발화 입증.

**STAGE R 상세 설계 + cross-review 완료** (2026-06-25, Opus): `docs/2026-06-25-stage-r-retrieval-design.md` 신규(부모 §13.2 D13 상세화). **MVP = `af knowledge search` 명령어-only**(세션시작 자동주입 연기, 사용자 확정). **핵심 결정(동결)**: ①결정론 전용 — 임베딩(`document_index.py`/Gemini) 미배선·연기 seam만(멀티OS·멀티프로바이더·크로스PC 재현성, symbols.md 비결정 버그 교훈). ②2모드 — `--query`(키워드) + `--files`/`--diff`(변경파일↔노트 정밀참조 exact-match, S2-3 100% precision 계승=1급 신호). ③관용 frontmatter 파싱(신규KnowledgeNote/레거시memory/무-frontmatter 3종, 파싱실패해도 본문 인덱싱=recall 우선 INV-R3). ④read-only·advisory(write 0, INV-R4 grep강제)·bounded(`--limit` 8). ⑤캐시없음 매호출 full-scan(117파일 규모). **재사용 SSOT**: `distill.extract_precise_refs(text)`(:80) 정규식 / `note._git`. **구현대상**: `core/knowledge/retrieve.py`(load_notes/score_notes/format_results)+`agent_launcher`(`_KNOWN_SUBCOMMANDS:31`에 `"knowledge"` 추가 필수)+`run_factory_cli`(_STAGE1_DISPATCH)+af.spec+tests. INV-R1~R5. **af-cross-review WARN[single-vendor] BLOCK0**(codex usage-limit·gemini만료→Claude단독): 5건 전부 grep 사실확인 후 반영(session/ 4→5·총117 / 시그니처 (events)→(text) / _KNOWN_SUBCOMMANDS 명시=격리오실행 방지 F3 / §9#2 합성fixture전제 / §10 레거시노트 file-mode recall0 위험·완화). **다음=Sonnet 구현**(feedback_model_per_phase). codex cross-vendor 재검증은 usage-limit 해제 후.

**부수**(2026-06-25): Ponytail 플러그인 이 PC 설치 — `claude plugin marketplace add https://github.com/DietrichGebert/ponytail`(**HTTPS 필수** — `owner/repo` 짧은형식은 SSH clone 시도→known_hosts에 github.com 키 없어 host key verification 실패) → `install ponytail@ponytail` v4.8.3 enabled. `.claude/settings.json` enabledPlugins는 이미 git pull로 수신됨(다음 세션부터 로드).

**STAGE 4 완료** (2026-06-25, Sonnet, 커밋 `4852a753`): `scripts/af_knowledge_link.py` 신규 — knowledge↔code 자동 wikilink. `_load_symbol_files`(symbols.md 파일명 집합·basename 역인덱스) + `_extract_py_refs`(**full path 우선·basename fallback**, 역인덱스 오탐 방지 F1 반영) + `compute_links`(symbols 연결+session 노트 파일 공유 cross-link) + `_update_note`(frontmatter links: append+본문 ## 관련 삽입, idempotent, frontmatter 제외 본문만 스캔). --dry-run(기본)/--apply. agent_launcher+run_factory_cli dispatch. af.spec hiddenimport. tests 20건 PASS. vault 84개 노트 적용(session 13개 cross-link). af-critic W3/W4/W1·af-cross-review F1(basename 우선 → false cross-link) 반영. **다음=신규 product work-item 또는 codex cross-vendor 재검증(rate-limit 해제 후)**.

관련: [[feedback_analysis_doc_baseline_must_be_real_code]] [[project_af_gate_efficiency_debate]] [[feedback_design_review_mandatory]] [[feedback_review_verdict_vs_bug_substance]] [[feedback_model_per_phase]]
