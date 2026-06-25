---
name: project_af_gate_efficiency_debate
description: "AF 풀 파이프라인 vs Opus 직접 — 토큰/시간 효율 논의. 잠정결론 동결, 다음 세션 계속."
metadata: 
  node_type: memory
  type: project
  originSessionId: 6fe92d3f-2d85-4d55-b6a6-4f89866b490a
---

**진행 중 논의 (2026-06-11 시작, 다음 세션 계속). 사용자 질문: "AF로 작업하는 게 Opus 직접보다 토큰·시간이 너무 많이 든다는 느낌. 동조 말고 논리적으로 판단."**

## 실측 (이번 세션 `af project symbols` 작업 — 12줄 CLI 디스패치)
- 실제 구현(Sonnet 직접): 12줄 + 테스트 1파일, 분 단위.
- 교차검증: af-critic 32,668토큰/103초 + **af-cross-review 77,632토큰/1,934초(32분)** + af-test-runner 26,223토큰/68초 = **합 ~136,500토큰 / ~37분**.
- 산출물: advisory 1건(is_dir), **BLOCK 0**. → 12줄에 교차검증이 토큰 대부분·시간 90%+.
- **사용자 느낌은 데이터상 정확.** (동조 아님, 측정값)

## 진단 (확정)
- 차이의 100% = **교차검증 게이트 오버헤드**. 코드 생성 속도는 Opus 직접과 동일 — AF가 느린 게 아니라 게이트가 무거움.
- 근본: **Tier 분류 과보수.** `agent_launcher.py`가 subprocess 포함이라 자동 Tier3 → 12줄에도 풀 3-Tier. 위험 실체와 무관하게 파일 속성만으로 최고등급.
- dogfood full은 더 심각: `geometric_mean` trivial 함수에 designer/qa_engineer 과분해 + 215+ 사이클 비수렴(기존 메모리 [[project_dogfood_isolation_leak]] 인근 기록). 효율 경쟁에서 명백히 패배.
- 단일 vendor(claude_cli만) 환경에선 af-cross-review 가치 구조적으로 낮음([[project_model_routing_facts]] single-vendor=외부검증 없음).

## 잠정 결론 (다음 세션 재검토 대상)
- **"AF vs Opus 직접" 이분법이 틀린 프레임.** 진짜 레버 = 게이트 강도.
- 일상 단순 코딩(CLI/유틸/문서) → **Opus 직접 + 표적 검증(필요시 af-test-runner만).** cross-review·dogfood 생략. **이건 타협 아니라 옳은 판단.**
- core 정책·보안·subprocess·격리 로직 → 풀 3-Tier 정당(메모리에 BLOCK이 실제 결함 잡은 사례 다수).
- 자율 실행 목적 대형 작업 → dogfood full. 단 가치는 "효율"이 아니라 "사람 개입 없이 돈다".

## 미해결 (다음 세션 논의 항목)
1. Tier 분류 과보수 교정 — subprocess=자동Tier3 룰을 "변경 라인의 실제 위험"으로 좁힐지.
2. cross-review 생략 기준 공식화 — trivial 판정 신호(라인수/변경범위/right_sized_router light?).
3. 단일 vendor에서 cross-review 정책 — 외부 0이면 SKIP 정책 이미 있음, 더 적극 생략?
4. **메타-재귀 경고**: 이 판단을 또 AF 기능으로 구현하면 함정. **운영 규칙으로 먼저 손 적용 → 효과 확인 후 코드화.** (메모리 반복 패턴 [[project_dev_workflow_paradigm_shift]])

---

## ★ 2026-06-11 후속 조사 — cross-review 32분의 진짜 원인 규명 (팩트 동결)

사용자 방향: "cross-review가 LLM Wiki/옵시디언 참고해 찾으면 되잖아? + 수정 내용만이 아니라 side-effect까지 봐야 하잖아?" → 깊은 분석 요구. **코드로 검증한 팩트 4개:**

- **팩트 1**: `docs/generated/llm_wiki/symbols.md`(8255줄)는 **정의 목록만**(파일별 class/function), **호출 edge 없음**. → side-effect(파급)는 symbols.md 조회로 못 얻음. (사용자 "LLM Wiki가 찾아준다"는 절반만 맞음 — 보정)
- **팩트 2**: `scripts/blast_radius.py`는 이름과 달리 파급 계산기 아님 — 파일경로→Tier1/2/3 **분류기**일 뿐. AF엔 진짜 call graph 없음(GitNexus 검토 "graphify 死"와 일치).
- **팩트 3**: side-effect는 **이미 수집됨** — `core/review_bundle.py:252 _find_direct_callers`("Grep core/+scripts/ for calls to changed_symbols") + `hook_runner.py:164`가 enqueue 직후 `build_review_bundle.py` 호출 → `.af_review_queue/review_bundle.md`(callers 포함) **이미 생성**.
- **팩트 4 (진짜 병목·단선)**: `af-cross-review.md` Step 2a Codex 프롬프트(176~217줄)가 **그 번들을 안 씀**. 대신 raw 7302줄 `code-review.md`(198줄) + "호출자/피호출자를 *직접 읽어라*"(206줄). 번들 정책(459줄)은 **Claude 오케스트레이터 본인** Read만 통제 — 외부 Codex 프롬프트엔 미반영. → **side-effect를 grep해 번들에 담아놓고 외부엔 "직접 탐색해"라고 중복 지시 = 32분 자율탐색의 정체.**

**side-effect 커버리지 한계(동조 안 함)**: `_find_direct_callers`는 max3/심볼·core+scripts만·**1-hop만**·`{sym}(` 텍스트 grep → 동적 디스패치/문자열 호출/설정 주도/transitive 놓침. "번들에 callers 포함"해도 깊은 side-effect 일부 손실 = 진짜 trade-off("얼마나 깊이"는 정책 결정).

## 합의된 4단계 계획 — STEP 1·2 완료 (2026-06-12 Opus), STEP 4 다음
- **✅ STEP 1 (진단, 코드0) 완료**: `scripts/hook_runner.py:165`가 모든 `.py` 편집 시 `build_review_bundle.py` 호출 → `review_bundle.md` **항상 생성**(현재도 존재, §5 Direct Callers 포함). 32분 정체 = 번들 미생성 아니라 Step 2a가 *안 써서*(단선). 팩트 4 확정(무시, not missing).
- **✅ STEP 2 (본체) 완료**: `.claude/agents/af-cross-review.md` 3개 편집(지시문 텍스트만, core 코드 0, 되돌리기 쉬움). ① Step1 `REVIEW_DOC`→청킹 index(`docs/generated/llm_wiki/code_review/index.md`, 없으면 raw fallback) + `review_bundle.md`를 `/tmp/af-review-bundle.txt`로 준비(stale/absent fallback) ② Step2a 프롬프트에 `[Review Bundle]` 섹션(§5 Direct Callers 임베드) + 지시1="청킹 index 관련 섹션만" + 지시4="호출자는 번들 §5에 이미 있음, risk 가설 있을 때만 추가 Read" ③ python `BUNDLE_PLACEHOLDER` 치환 1줄. 스모크 PASS(잔여 placeholder 0). `.md`만→review-gate 자동통과(self-review 모순 회피). ⚠️ self-mod라 auto classifier가 막음 → 사용자가 권한모드 전환 후 적용.
- **STEP 3 (정책, 선택·안급함)**: `_find_direct_callers` 1-hop/max3 한계 넓힐지 = "안전 vs 빠름" 다이얼. STEP4 결과 보고 사용자 결정.
- **△ STEP 4 (controlled 측정 강행 — 사용자 지시 2026-06-12) 1차 완료, 단 불완전**: `root_mean_square` leaf util(12줄, Tier2) 커밋 후 af-cross-review 직접 호출(gemini auth_expired는 `AF_SKIP_PROVIDER=gemini_cli`로 우회). **결과: 34분→10.8분(3.2× 빠름), 77k→63k토큰(-18%). 메커니즘 전부 PASS**(청킹 index 사용·번들 임베드·§5 섹션 포함·Codex가 §5 근거로 호출자 자율탐색 안 함·extension log 0·Claude 6파일 read). **그러나 깨끗한 A/B 아님(overclaim 금지)**: ① Tier 불일치(baseline Tier3 vs Tier2) ② **핵심 benefit 미측정** — `root_mean_square`는 신규 leaf라 callers 0 + **commit-first 탓에 번들 §2 Git Diff 비고 changed_symbols=0 → §5 애초에 비어있었음**. side-effect 커버리지 가치(=§5 callers 임베드로 자율탐색 제거)는 **callers 있는 함수를 pre-commit 게이트(번들 staged 생성)로** 재측정해야 진짜 입증. ③ 남은 ~11분은 codex 자체 리뷰패스+deliberation(번들로 제거 안 됨). **방향성 확인→STEP2 유지 정당, 헤드라인 "분 단위"·side-effect benefit은 미입증.** advisory 1: blueprint_updater가 신규 공개심볼 §3.12 자동반영 못 함(WARN). 측정 vehicle 커밋 `83dd4662`(RMS).
- **▶ STEP 4-rerun (다음, 선택)**: callers 있는 함수 변경을 **pre-commit 게이트로** 측정(번들 §5 채워진 상태) → side-effect 자율탐색 제거 효과 진짜 검증. 자연 발화 run으로 대체 가능.
- **✅ RMS 정식 3-Tier 완주 (2026-06-12 Opus)**: 측정 vehicle `83dd4662`가 `AF_SKIP_REVIEW_GATE=1`로 cross-review WARN+테스트만 받았던 잔여 2-tier 실행 — **af-critic PASS**(발견 0) + **af-test-runner PASS**(RMS 6 + 전체 272, gap PASS). 코드 변경 0.
- **✅ blueprint_updater advisory 완료 + STEP4 2차 측정 (2026-06-12 Opus, `a32c382d`)**: 미결 #2(§3.12 신규심볼 누락) 수정 = positional 캡 제거 + 신규 `_changed_public_symbols`(change-relative: `+def`/`+class` + `@@` 헌크컨텍스트 enclosing). "전체 반영"(advisory 문자대로)은 utils.py 54함수 bloat라 기각, change-relative가 정답. 부수 발견·수정: `_git`의 cp949 기본 디코딩이 비-cp949 문자에서 `stdout=None`(전 호출자 잠재결함) → utf-8 고정. 3-Tier PASS(critic WARN→헌크컨텍스트로 해소). **이 cross-review가 STEP4-rerun vehicle 겸용(callers 有)**: ~15.3분/80k/Codex CLI fallback 단일라운드/PASS. **그러나 번들 또 stale** → "git 직접 실험으로 대체" → **§5 side-effect benefit 2회 연속 미입증**(staged 직접 호출이라 pre-commit 번들 재생성 안 됨). **결론: STEP2 방향 유효, 헤드라인 benefit은 자연 pre-commit 발화 run에서만 측정 가능.** 미결 3건 전부 소진 → 다음=product-value work-item.

- **△ STEP4 3차 측정 — §5 채워진 조건 첫 성립, 단 codex 또 비활성 (2026-06-12 Opus, `b150cda6`)**: WI-B STEP2-b(build_llm_wiki 외부 확장) 커밋의 자연 3-Tier가 vehicle. **`build_review_bundle.py .`를 staged 변경 기준으로 먼저 돌려 §5 채움 → `callers=7/7`(RMS 1차·blueprint 2차에서 둘 다 비어있던 그 섹션이 처음 채워짐).** af-cross-review **6.8분 / 78.2k** = 32분 baseline 대비 **4.7× 빠름**, extension log 0(번들 §5를 1차 근거로 사용, 14개 항목 직접검증 후 호출자 자율탐색 안 함). **그러나 또 깨끗한 A/B 아님**: `mcp__codex__codex`가 **이 세션에서 비활성**(provider_detect는 codex_cli available 보고했으나 MCP 도구 미등록) → cross-review가 Claude 단독(single-vendor)로 폴백 → **6.8분 단축에 "외부 codex deliberation 부재"가 혼입**. §5 채워짐의 순효과와 분리 불가. **헤드라인 benefit은 여전히 [codex MCP 활성 + §5 채워짐] 동시 조건이 필요**(3회 측정 모두 한 변수씩 어긋남: RMS=§5빈+codex有 / blueprint=§5빈(stale)+codex有 / 이번=§5채움+codex無). **STEP2 방향성은 3회 모두 유효 재확인**(번들 §5 채우면 Claude/Codex가 자율탐색 안 함). 측정 운영 팁: staged 직접 호출 전 `build_review_bundle.py .` 수동 실행하면 §5 채워진 번들 확보 가능(pre-commit 자연 발화 없이도).

- **✅ ②번 갭(provider available ≠ MCP 연결) 진단+처방 완료 (2026-06-12 Opus, `7570cdf6`)**: STEP4 3차에서 codex가 또 비활성이던 근본 원인 규명. **결함(grep 확정)**: `core/provider_detect.py:65` codex probe = `["login","status"]` = **CLI 인증 레벨만 검증** → fan_out 포함. 하지만 실제 리뷰는 `mcp__codex__codex`(세션 MCP) 필요. 둘의 일치를 보장하는 코드/지시 없음 → `af-cross-review.md` 케이스 분기(1b rate-limited/2 빈fan_out/2c gemini-only)에 **"codex는 fan_out에 있는데 MCP만 미연결" 케이스 누락** → MCP 미연결 세션에서 cross-review가 즉흥 single-vendor 폴백. **처방(현실화)**: codex CLI는 `codex exec`/`codex review` non-interactive 지원(`codex --help` 확인) → MCP 없어도 CLI로 외부검증 가능. `af-cross-review.md`에 ① Step2 도입부 경고 블록 + ② `2b-fallback`(codex exec) 추가 — MCP 미연결 시 Claude 단독 대신 `codex exec`로 외부검증 유지, verdict 라벨 `[codex-cli, no-mcp]`(single-vendor 아님). **provider_detect(별도 프로세스)는 세션 MCP 상태를 알 수 없어 코드 레벨 해결 불가 → .md 지시문 레벨이 정답**(core 코드 0, STEP2와 동급). self-mod라 auto classifier가 막음 → 사용자 권한 허용 후 적용. **효과: 깨끗한 A/B의 ② 스위치(codex 활성)를 CLI 경로로 보장** — 다음 측정부터 MCP 미연결이어도 codex 외부검증 받음(단 codex CLI exec 실호출은 다음 자연 발화 때 검증 대기).

- **✅ STEP4 4차 측정 — [§5 채워짐 + codex 활성] 동시조건 첫 성립 (2026-06-22 Opus, output-isolation O-S2 vehicle)**: `agent_launcher.py`(caller-rich Tier3) 변경을 staged → `build_review_bundle.py .`로 **§5 Direct Callers=7/7 채움** + codex_cli AVAILABLE(login OK). 이전 3회는 매번 한 변수 어긋남(1차 §5빈+codex有 / 2차 §5stale+codex有 / 3차 §5채움+codex無). **이번이 둘 다 성립한 첫 측정.** 결과: af-cross-review **81.9k토큰 / 10.1분 / WARN(BLOCK0)**, **Extension Log 비어있음**(§5 7/7을 1차 근거로 사용, 자율 재탐색 0). codex는 **CLI fallback(no-MCP)**으로 외부검증 유지(single-vendor 아님 — `7570cdf6` 2b-fallback 메커니즘 작동 실증). 실질 finding 1건 산출(--out/--workspace 메시지 불일치, 내가 수정) = rubber-stamp 아님. **깨끗하게 입증된 것**: §5 채우면 외부검증자가 자율탐색 안 함(Extension Log 0) = STEP2 메커니즘. **여전히 미측정(overclaim 금지)**: 32분→10분은 [§5 fill benefit] + [codex CLI 단일라운드 vs codex MCP 다라운드 deliberation] 혼입 — codex MCP는 Windows shell 버그("batch file arguments are invalid", dogfood Bug0)로 이 환경에서 못 돎. 순수 §5 fill의 시간효과를 codex MCP와 분리하려면 MCP 정상 환경 필요. **STEP2 방향성 4회 연속 유효 재확인.**

관련: [[feedback_reverse_sycophancy_balance]] [[feedback_review_verdict_vs_bug_substance]] [[project_right_sized_execution]] [[project_gitnexus_adoption_review]] [[project_provider_instruction_parity]] [[project_model_routing_facts]]
