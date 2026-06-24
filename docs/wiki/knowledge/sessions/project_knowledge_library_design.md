---
name: project_knowledge_library_design
description: "자가진화 지식 도서관 — git vault + Obsidian + 증류. STAGE 0·1·2(S2 전체) 완료. 다음 순서 동결: ①S2-3 실측 →②STAGE R(검색) →③자동생성. 또는 STAGE 3/product"
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

**다음 = STAGE 3** (`af knowledge doctor` 크로스OS staleness 점검기, 설계 §5 STAGE3): 노트 named file:line/심볼/커밋이 코드에 실존하나 검증. created_commit이 git 히스토리에 있나? 없음→SKEW(미pull, 오보차단)/있음→git diff로 file:line 변동→STALE. 순수Python(fcntl/flock/launchd 금지), advisory만. 산출=`scripts/af_knowledge_doctor.py`+`af knowledge doctor` dispatch+af.spec. 의존=STAGE1 created_commit. **대안**: product work-item 우선이면 STAGE3 보류 가능(자가진화 인프라). codex cross-vendor 재검증은 6-25 이후.

**순서 판단 동결** (2026-06-24, Opus — 설명·설계검토 세션, 코드 0변경): "NEXT_STEPS ↔ 대화 증류 연결해야 하나?" 팩트 검증 결론. 연결은 설계상 이미 존재(§9#2=`증류본이 손작성 NEXT_STEPS 정밀참조 보존`, STAGE 5 승격, INV-K8). 그러나 §9#2 한 번도 미측정 + 증류 노트는 retrieval 없어 현재 **고아 아카이브**(써놓고 안 읽힘, NEXT_STEPS만 세션시작 읽힘). **실행순서 = ①S2-3 실측(증류 vs NEXT_STEPS 보존율=연결가부의 답) → ②통과시 STAGE R 검색방향(read-only·advisory, 원장 안 망침) → ③자동생성(NEXT_STEPS auto-draft)은 마지막(미검증 lossy 원장오염 위험)**. 측정 없이 연결 금지. cf. ①번 LLM Wiki(code/)는 커밋마다 재생성=거울이라 낡지 않음 / ②번 knowledge/는 증류·생성이라 STAGE 3 doctor 필요. INV-K7로 두 폴더 물리분리(build_llm_wiki는 code/만 write).

관련: [[feedback_analysis_doc_baseline_must_be_real_code]] [[project_af_gate_efficiency_debate]] [[feedback_design_review_mandatory]] [[feedback_review_verdict_vs_bug_substance]]
