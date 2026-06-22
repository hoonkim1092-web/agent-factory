---
name: project_router_research_decoupling
description: "Router scope/research decoupling Phase1+2 완료(`30f891fb`) + §10 자연어 실측 완료(2026-06-21). 결함(research 자동오염) 해소 실증, 단 light 진입 0/6(빈-scope LLM 변동성 큼, 0.85 임계 정당). Phase1 코드 결함 아님 → Phase3/4 보류 정당. 진짜 병목=scope 추출 품질(별도 트랙)."
metadata: 
  node_type: memory
  type: project
  originSessionId: efb31d48-872c-44a9-875a-1534eac05274
---

2026-06-07 세션. 3라운드 deliberation(사용자+Claude)으로 수렴. 클리어 후 이 메모리 먼저 → 바로 설계문서 작성. **재논쟁 금지 — 아래 팩트는 grep 확정.**

## 제품 목표 (사용자 확정)
사용자가 자연어로 "만들어줘/문서화해줘/고쳐줘" 던지면 AF가 ① 불필요한 full/research로 안 새고 적절한 light로 들어가고 ② 완료를 phase success가 아니라 evidence-backed criteria로 닫는다. 입구(routing)+출구(completion) 두 축. OMO ulw-loop 원칙(스마트 입구/evidence 출구)만 흡수, 파이프라인 베끼기 아님.

## 검증된 팩트 (grep 확정, 재논쟁 금지)
- **classify() production 호출처 = `dogfood.py:1785` 단 1곳.** `project_pipeline.py:12`는 STAGE 상수만 import, classify() 호출 안 함. → Phase1 blast radius = dogfood DEVELOP(=self-run) 한정. full 머신(ProjectPipeline/Lilith/board) 무변.
- **빈-scope 단락**: `right_sized_router.py:268-269` `if not files: return _fallback_decision(...)` — LLM(`:283`)보다 앞. `test_right_sized_router.py:179-195` R-FB-NOSCOPE가 "LLM must NOT be called" **계약화**. → 의도적 계약 변경 필요.
- **단절(criteria가 gate 아님) 3곳 확인**: ① `completion_criteria`(`dogfood.py:175`, 채움 `:1413/:1759` from `spec.success_criteria`) gate-reader **0건**(비-쓰기 소비처는 역직렬화 `:264`·planner `:531`뿐) ② `VerifyResult`(`:329`)=passed/commands_run/failures만, criteria 없음 ③ `board_is_complete()`(`project_task_board.py:738`)=`total==completed` 카운트만, acceptance(`:973`)는 프롬프트 텍스트만 ④ `_run_review_phase`(`dogfood.py:1837`)=`verify_result.passed`만. finalize commit은 `AF_SKIP_REVIEW_GATE=1`(`:1052`).
- **wiki 산출물은 Tier2 아님 Tier3**: `classify_with_content('scripts/codebase_symbols.py')=2`. → post-implement Tier3 floor에 **안 걸림**. (`core/dogfood.py`는 content=3 → self-mod risky core는 걸림.) **observe-first 근거는 "wiki run 보호"가 아니라 "floor trip-rate 캘리브레이션".**
- **선례(하드코딩 0 강제 수단)**: named 임계 `_LIGHT_CONFIDENCE_THRESHOLD: float=0.7`(`:35`) / policy 스레딩 `MergePolicy.allow_partial_impl`(`dogfood.py:295`+`__post_init__` 검증 `:306`) / self-run 신호 `AF_SELF_RUN`(`:1625`, set `:1641`) / 경로명 비의존 self-mod `_is_self_modification`(`:163`) / Tier3 floor `:206`. **convention test 강제**: `test_coding_conventions.py` test_no_hardcoded_abspath·test_no_duplicate_type_names = 위반 시 빌드 FAIL.

## 4-Phase 계획 (수렴, 순서 확정)
- **Phase 1 (router decoupling)**: 빈-scope early fallback → scope-uncertainty LLM path. 일반보다 높은 임계(빈-scope 전용). LLM 실패/무효/low-conf→full fallback. scope 있는 routing 무변. = "거의 추가, 단 R-FB-NOSCOPE 계약 1개 의도 변경"(완전 무해 아님).
- **Phase 2 (post-implement Tier3 floor)**: `_run_develop_light()` 후 actual_changed 기준. **observe-first**(phase_trace warning, complete 기존대로) → 승격 후 enforce(block/review 강제). Phase1과 묶여야(1만=unsafe, 2만=UX 안 열림).
- **Phase 3 (completion contract)**: criteria↔evidence↔all-pass gate로 단절 4곳 연결. **게이트 뒤**(단순 연결 아님 — ledger 4개[evolution/ise_strategy/lineage/run]+board+verify+review+approval 화해 = 대형 내부 리팩토링, 메타-재귀 1순위). + **진짜 병목은 criteria 부재 아니라 criteria SOURCE 품질**(non-interactive greenfield는 1줄 task에서 LLM 자동생성 → garbage-in이면 gate도 garbage). 하위호환 기본값(criteria 없으면 legacy) 없으면 기존 run 회귀.
- **Phase 4 (iterative light)**: 게이트 뒤. **끌어내는 task 0**(wiki는 one-shot light가 COMPLETE 실증, run `1780813496`). 메모리 [[project_af_codebase_wiki_direction]]의 "(iii)는 task가 끌어낼 때만" 원칙 그대로. 지금 짓는 건 추측성 인프라.

## 설계문서에 박을 불변식 (Claude가 추가한 2 델타 포함)
1. scope 있는 routing 무변 / scope=[]만 새 경로 / LLM 실패·무효·low-conf→full fallback / 빈-scope light는 route metadata **uncertainty marker**(Final 상수 키).
2. **δA (Claude 추가)**: observe-first에 **명시 승격 기준** 필수 — 없으면 영구 dead-safety. 예: AF_SELF_RUN dogfood K회 관측 + 정당 run false-trip 0 → self-run 한정 enforce flip.
3. **δB (Claude 추가)**: observe 윈도우 동안 빈-scope light ↔ **non-auto_policy 결합** — `merge∈{never,manual}`만 빈-scope light 허용, `auto_policy`는 enforce 전까지 기존 빈-scope→full 유지. 안 그러면 self-run이 Tier3 self-수정을 무검열 auto-merge(review=verify만+finalize=SKIP_GATE)로 source 오염.
4. 하드코딩/abspath 강제: 빈-scope 임계=named 상수(`_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD`) / observe·enforce 모드=MergePolicy 필드+__post_init__ 검증(allow_partial_impl 선례, CLI→policy→runner) / marker=Final / self-run=AF_SELF_RUN env / Tier3=기존 `:206` / 경로=state._cwd()·worktree_workspace만.

## 다음 행동 (현재 상태: Phase 1+2 완료 + §10 실측 완료)
1. ✅ **설계문서 작성 완료** `docs/2026-06-07-router-scope-research-decoupling-design.md` (Opus).
2. ✅ **af-cross-review WARN** (BLOCK 0). 발견 3건 반영.
3. ✅ **Phase 1+2 구현 완료** (Sonnet, `30f891fb`, 2026-06-07). 신규 32 테스트. 3-Tier PASS.
4. ✅ **§10 자연어 실측 완료 (2026-06-21, Opus)**: 빈-scope 문서화 throw 6회(`classify(task, ws, changed_files=[])` 직접 호출, 실제 claude_cli LLM). **결과**: (a) 메커니즘 정상 — `source=llm`, `scope_uncertain` marker 100%, 0.85 임계 적용. (b) **research 자동 오염 구조 결함 해소 실증** — 일부 throw가 `['implement']`만(research 없이). 이전의 "빈-scope→무조건 full→research 강제"가 사라짐. (c) **light 진입 0/6** — 빈-scope LLM 추론 변동성 큼(동일 "scripts README" task가 conf 0.82→0.55→0.62, research 0/1 들쭉날쭉). **0.85 임계가 변동성 방어선으로 정당**(낮추면 위험 task 누출). **§10 판정 = "여전히 full"이나 Phase1 코드 결함 아님** → **Phase3/4 보류 정당**(completion contract 불필요). 진짜 병목 = 라우터 아닌 **scope 추출 품질**(task 텍스트만으로 일관 분류 불가) — 자연어 light UX 마지막 1마일은 별도 트랙. **임계 캘리브레이션/enforce flip은 δA대로 AF_SELF_RUN 관측 데이터 누적 후 결정**(지금 임계 변경은 데이터 없는 추측 = δA 위반).
5. 🔬 **후속 발견 — CoT 프롬프트가 변동성 해결 (2026-06-21, Opus, 실측, 코드 미변경)**: 변동성 근본원인 = `control_plane_llm.py:114` CLI 경로 **temperature 제어 부재**(claude_cli temp 플래그 미노출 = 구조적 한계, CLI론 결정적 분류 불가). **실측**(`_build_empty_scope_prompt` monkeypatch로 "규칙 단계별 추론 후 JSON"=CoT, 각 task 10회): 단순(README) conf 0.82~0.90 **표준편차 0.025** research 0/10 / 복잡(인증) conf 0.35~0.45 **표준편차 0.024** full 10/10. 현재 프롬프트(표준편차 0.108, research 3/5) 대비 변동성 ~1/4 + 오염 제거. **conf 군집 깨끗이 분리(단순0.82↔복잡0.45, 간격 0.37)**. 임계별 light 진입(단순/복잡): 0.85(현재)=30%/0% ← 임계가 단순군집 정중앙 위라 병목 / **0.82=100%/0%(안전마진 0.37)**. **확정 해법 = CoT 프롬프트 + 임계 0.85→0.80~0.82 세트** (CoT만으론 임계 0.85가 막아 절반의 해결). 변경 작음(`_build_empty_scope_prompt`+`_build_prompt` CoT화 + `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` 조정). **정식 채택 전 잔여 검증 2건**: ① task 종류 다양화(현 단순/복잡 각 1종만) ② 멀티프로바이더(codex/gemini 군집 위치, claude_cli 단독 측정 — CLAUDE.md 멀티프로바이더 규칙). 그 후 설계(Opus)→교차검증→코드+테스트. [[feedback_no_hardcode_single_type_source]]

## 구현 동결 (설계 수렴 — 클리어 후 Sonnet 구현 시 재설계 금지)
설계문서 `docs/2026-06-07-router-scope-research-decoupling-design.md`가 SSOT. af-cross-review(WARN, 3건)+외부리뷰(5건) 검토 반영 완료. 핵심 구현 결정 7개:
1. **`RouteDecision.markers: list[str] = field(default_factory=list)`** 신규 필드 + `to_dict()`에 `"markers"` 추가(누락 시 audit↔dispatch 갈림).
2. **`is_light()` marker-aware 단일 SSOT**(외부리뷰#5): `ROUTE_MARKER_SCOPE_UNCERTAIN in markers`면 임계 0.85(`_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD`), 아니면 0.7(`_LIGHT_CONFIDENCE_THRESHOLD`). marker 없으면 scope 경로 완전 무변(INV-1).
3. **`_classify_empty_scope`**: LLM 호출→`_validate_raw`→marker만 부착 반환. 게이트 안 함(is_light()가 판정). LLM 에러/무효만 `_fallback_decision`. low-conf도 marker단 채 반환→is_light()=False→full(audit에 LLM 실판단 보존). floors 생략 안전성=INV-5 의존(docstring 명시).
4. **`classify` 빈-scope 분기**(`right_sized_router.py:268-269`): `_fallback_decision`→`_classify_empty_scope(task, workspace)`.
5. **`_light_allowed(route, scope, state)`**(dogfood dispatch guard `:1788` 교체): `if scope: return True`(INV-1) / 빈-scope는 `ROUTE_MARKER_SCOPE_UNCERTAIN in markers` AND `state.merge_mode in ("never","manual")`(INV-5/δB — auto_policy 빈-scope light는 source 오염 통로라 full 유지).
6. **`MergePolicy.tier3_floor_mode: str = "observe"`** + `__post_init__` 검증(`{"observe","enforce"}`). 소유권 근거=MergePolicy가 이미 lifecycle policy SSOT(require_verify/review_pass, allow_partial_impl 선례). 별도 DevelopSafetyPolicy 기각(과설계). CLI→policy→runner 스레딩(allow_partial_impl 경로).
7. **`_run_develop_light(state, policy)`** 시그니처+1, 말미에 observe 관측: `actual_changed`(+`_changed_files_fallback`) 빈→`observability="no_changes"` / 있으면 `classify_with_content>=3` 필터→`"observed"`+changed_tier3. result dict `base["tier3_floor"]` 키로 기록(`_append_phase_trace` output_data 경유, **`_emit_phase_trace`는 실재 안 함**). observe는 block 안 함(complete 무변). `_run_develop_phase`가 `build_merge_policy`로 policy 생성·전달.

**구현 순서**(§9): RED(§5.3 router 7테스트+§6.5 floor 4테스트) → right_sized_router → dogfood → GREEN → test_coding_conventions → 3-Tier(critic→cross→test-runner) → Blueprint §3+§12 같은 커밋. test-first, 재설계 금지.

**키워드 분류기 금지**(사용자·Claude 합의): express_router 死코드 전례+하드코딩 금지+"인증 시스템"은 위험키워드 없이 복잡/"디렉터리 문서화"는 wiki키워드 없이 deterministic → 양방향 샘. LLM stage 판단+confidence+floor가 정답.

**Why:** dogfood light wiki가 planner shlex 버그 fix 후 COMPLETE 실증(`7a3f44e5`). 그 과정에서 "scope 추출 성공이 research 필요 판단을 오염"(빈scope→full→research) 구조 결함 발견. 자연어 UX는 제품 정체성(외부부착+자연어 진입)의 입구.
**How to apply:** 클리어 후 이 메모리+NEXT_STEPS 먼저. 팩트는 동결됨(재grep 불요, 단 구현 직전 line만 재확인). 설계 Opus, 구현 Sonnet.

관련: [[project_af_codebase_wiki_direction]] [[project_right_sized_execution]] [[feedback_design_review_mandatory]] [[feedback_no_hardcode_single_type_source]] [[feedback_reverse_sycophancy_balance]]
