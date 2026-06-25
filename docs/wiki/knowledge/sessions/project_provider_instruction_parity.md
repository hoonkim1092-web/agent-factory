---
name: project_provider_instruction_parity
description: "다음 세션 진입점 2건(2026-06-11 준비). WI-A=멀티 프로바이더 지침 SSOT 정합성(CLAUDE/AGENTS/GEMINI.md 전부 다름, Codex/Gemini는 실무규칙 0 전달). WI-B=LLM Wiki 청킹본 우선(7302→28줄 260배 절감, 보라는 지침만 누락)+외부 프로젝트 AST 인덱스. 둘 다 메타-재귀 아님."
metadata: 
  node_type: memory
  type: project
  originSessionId: ab8be669-b848-475b-b4ec-2e884013db33
---

2026-06-11 세션(Opus). 사용자가 "Codex/다른 프로바이더로 작업하면 CLAUDE.md 지침이 안 먹히지 않나? AGENTS.md 깡통인데 맞나?"를 제기 → grep 검증으로 진짜 harness 결함 확정. **재논쟁 금지 — 좌표는 grep 확정.**

## ✅ WI-A 구현 완료 (2026-06-11 Sonnet, `158aeaf4`)

- 설계문서: `docs/2026-06-11-provider-instruction-ssot-design.md`.
- 구현: `INSTRUCTIONS.md` 신규(공통 SSOT) + `scripts/sync_provider_instructions.py` 신규(marker-injection) + `generate_agents_md.py` `render_roster()` 추가·`main()` sync 위임 + `.githooks/pre-commit` sync 트리거(commit 차단 포함).
- INV-1~8 27 테스트 PASS. 3-Tier: af-critic PASS / af-cross-review PASS(BLOCK 0) / af-test-runner PASS(3145).
- Codex/Gemini 실무규칙 전달 채널 복원 완료.
- **WI-B STEP1** (청킹본 우선 read 지침)은 INSTRUCTIONS.md에 한 줄 추가로 흡수 가능 — 별도 작은 PR.

## WI-A: 멀티 프로바이더 지침 SSOT 정합성 (선행)

**문제 (grep 확정):** 세 지침 파일이 내용·카테고리 전부 다르다.
- `CLAUDE.md`(198줄) = 실무 규칙 (타입 SSOT, 하드코딩 금지, 리뷰 게이트, 커밋 규칙, Blueprint 동기화, Karpathy 원칙)
- `GEMINI.md`(149줄) = 정체성/철학 헌법 (페르소나, 엔진 역할분담, planning-first)
- `AGENTS.md`(25줄) = 에이전트 명단 테이블 (`generate_agents_md.py`가 `agents/*.yaml` 스캔해 자동생성, **지침 아님**)
→ Claude 외 프로바이더(Codex=AGENTS.md, Gemini=GEMINI.md)는 **실무 규칙 0 전달**.

**핵심 모순:** `scripts/session_bridge.py:13` `NOISE_PREFIXES`에 `"# AGENTS.md instructions"`가 있다 = AF는 **Codex가 AGENTS.md를 작업지침으로 읽는다는 걸 코드로 안다.** 그런데 `scripts/generate_agents_md.py:296` `output_path.write_text(...)`가 AGENTS.md를 **에이전트 명단으로 덮어씀** → 지침 채널을 카탈로그가 점유.

**방향:** 공통 규칙 SSOT(1곳 정의) + 프로바이더별 래퍼(CLAUDE/AGENTS/GEMINI)를 generate 패턴으로 합성 → sync 자동 유지(LLM Wiki 청킹 재생성과 같은 패턴). 근거 = [[feedback_pipeline_deploy_parity]] 배포 동등성.

**설계 전 합의할 결정 3개:**
1. 공통 SSOT 위치 — 새 파일(예: `INSTRUCTIONS.md`) vs CLAUDE.md를 원본으로 두고 나머지 생성
2. AGENTS.md 에이전트 명단을 어디로 이전 (별도 섹션 vs 별도 파일 vs AGENTS.md 내 공통+명단 2섹션)
3. 완전 동일 vs "공통 규칙 공유 + 프로바이더 전용(Claude=Skill/hook, Gemini=정체성) 분리"

**작업 방식:** 아키텍처 변경 → 설계문서 + af-cross-review 필수 ([[feedback_design_review_mandatory]]). 구현 전 결정 3개 사용자 합의.

## WI-B: LLM Wiki 청킹본 우선 + 외부 프로젝트 AST 인덱스

사용자 의도 = "Master_Blueprint/code-review를 청킹해 넣은 건 재탐색 토큰·시간 절감용". **grep으로 직관 옳음 확정.**

**STEP 1 (WI-A 공통 SSOT에 흡수):** 분석 시작 시 `docs/generated/llm_wiki/blueprint/N-*.md` 청킹 섹션만 read(원본 통째 금지) + `symbols.md`는 grep(통째 read 금지, 8204줄). 근거 = code-review **7302줄 → 청킹 섹션 28줄(260배)**. 청킹 인프라는 완성, **소비 지침만 누락**(CLAUDE.md가 원본 Master_Blueprint.md를 가리킴). ⚠️ Claude 전용 파일에 넣으면 또 단일 프로바이더 — **WI-A 공통 SSOT에 넣어야** 3 프로바이더 공유.

**STEP 2 (별도 기능·설계 필요):** 외부 프로젝트(AF 부착)용 AST 인덱스. `build_llm_wiki.py:31-33`은 `Master_Blueprint.md`/`code-review.md`/`NEXT_STEPS.md` **하드코딩 = AF 전용**(외부엔 없음 → architecture/review mirror 깨짐). 범용은 `scripts/codebase_symbols.py`(임의 디렉터리 AST)뿐. `af` 명령으로 외부 프로젝트 symbols 인덱스 생성 + AF 분석경로 참조. **ROI 최고** — 외부 프로젝트는 기존 정리 0이라 AST 인덱스가 유일 지도. 토대: `af project inspect`가 이미 외부 llm_wiki 존재여부 체크(`af_project_inspect.py:133-138`).
- **✅ STEP 2 (symbols만) 완료 (2026-06-11 Sonnet, `a6f53fdc`)**: `af project symbols <path>` — codebase_symbols.build() 재사용.
- **✅ STEP 2-b (외부 full-wiki) 완료 (2026-06-12 Opus, `b150cda6`)**: `build_llm_wiki`를 source-presence-aware로 — AF 문서 3종 `_read_optional`(부재→의존 페이지 skip) + `_build_codebase_tree(symbols)` AST 디렉터리/모듈 navigation 섹션을 `_build_architecture`에 항상 추가(AF=Blueprint 테이블+AST, 외부=AST만; 페이지 수 14 불변·회귀 0) + `_build_index`/`_build_source_refs` 적응형 + symbols 1회 수집 공유. CLI `af project wiki <path> [--out DIR]` + af.spec hiddenimports. 테스트 9 신규(56 PASS). 3-Tier: af-critic PASS / af-cross-review WARN[single-vendor](BLOCK 0, Advisory Medium 1=`--out` 기본값 외부 docs/ 오염, 자동수정 의무 없음) / af-test-runner PASS. **WI-B 전부 소진.** 잔여 선택: `--out` 기본값 덜 침습 경로(WARN). **다음 = product-value work-item 신규 선정.**

**STEP 3 (보류):** dogfood ContextPack 주입 — 과거 "메타-재귀 함정으로 기각"(NEXT_STEPS L9). STEP1/2 효과 확인 후 재평가.

**세 주체 공통 분모 = AST 심볼 인덱스(symbols.md). ROI 순서 ③외부 > ①Claude세션 > ②dogfood.** (기존 정리 없을수록 인덱스 가치 큼.)

**Why:** AF는 멀티 프로바이더 하네스를 표방하나 지침은 Claude 전용. 청킹 인프라는 만들었으나 소비 미연결. 둘 다 "만들었지만 연결 안 함" = [[project_model_routing_facts]] WI-2/4와 같은 패턴(정책 있음, 실행 보장 약함).

**How to apply:** 다음 세션 NEXT_STEPS 상단 진입점 + 이 메모리 먼저. WI-A 결정 3개 사용자 합의 후 설계 Opus. 관련: [[feedback_pipeline_deploy_parity]] [[feedback_design_review_mandatory]] [[project_af_codebase_wiki_direction]] [[feedback_no_hardcode_single_type_source]]

## 관련
- [[code/symbols]]

