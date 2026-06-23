---
name: project_knowledge_library_design
description: "자가진화 지식 도서관(Knowledge Library) 설계 — git vault + Obsidian + 증류, 단일사용자·다중PC. R1 BLOCK 흡수 완료"
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

**다음**: R2 재검증(원하면) 또는 STAGE 0 구현(Sonnet) 진입. 관련: [[feedback_analysis_doc_baseline_must_be_real_code]] [[project_af_gate_efficiency_debate]] [[feedback_design_review_mandatory]]
