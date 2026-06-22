---
name: project_af_codebase_wiki_direction
description: "AF 정체성(범용 에이전틱+외부 대규모 프로젝트 부착) + LLM Wiki를 코드베이스→Obsidian knowledge view로 재포지셔닝. 실행결정 수렴: 경로(i) light bounded-slice 체인으로 codebase wiki 구현. 첫 throw=symbols.md dogfood run. light/full 경로 사실·CLI 확정. 다음 진입점."
metadata:
  node_type: memory
  type: project
  originSessionId: 539eaac5-0302-4de2-afe4-d53c890ab804
---

2026-06-07 세션. STT 앱 요청을 계기로 AF 정체성·아키텍처를 코드로 진단하고 다음 방향을 확정.

## 정체성 (사용자 확정)
AF = Manus류 **범용 에이전틱 시스템** + **기존 대규모 프로젝트에 붙어 분석/유지보수/기능추가 자동화**. Claude/Codex CLI를 백엔드 LLM으로 위임하는 오케스트레이터. 상세: [[project_saas_strategy_position]].

## 아키텍처 진단 (코드 grep 사실, 2026-06-07)
**골격은 실재 (외부 부착 지향 설계 맞음):**
- workspace 분리 실재: `project_pipeline.py:708-709` `target_workspace`(대상 코드베이스)/`state_workspace`(AF 데이터). prepare/execute 전체가 target 기준.
- `ControlPlaneIntake`(work_kind 분류+ChangeImpactProfiler) 실배선 `project_pipeline.py:728`.
- `StageRouter` new_project/maintenance 분기 실배선 `work_item_generator.py:1170`. `_run_maintenance`는 실로직(LightContextScanner 코드 스캔), stub 아님.
- work_kind 5종: new_project/maintenance/bugfix/feature_update/refactor (`core/control/intake.py`).

**갭 3건:**
1. **`core/control/maintenance_pipeline.py`(378줄) MaintenancePipeline = 死코드** — `grep "MaintenancePipeline("` 0건. `__init__.py` export만. stage_router는 자체 _run_maintenance 사용. → 두 maintenance 구현 중 하나가 죽어있음.
2. **외부 대규모 프로젝트 실전 검증 0** — 모든 dogfood가 self(core/utils.py). 골격은 있으나 외부 end-to-end 미실증.
3. **외부 프로젝트 지정 사용자 진입 경로 모호** — `run_factory_cli.py:201` workspace 기본값이 AF 내부 projects/ 하위. 외부 임의 경로로 prepare/execute 거는 매끄러운 UX 미노출/미검증.

## LLM Wiki 재포지셔닝 목표 (확정)
**목표: 하나의 "코드베이스→Obsidian knowledge wiki" 기능을 AF self(개발자도구)+사용자 프로젝트(제품기능)에 동시 적용.**
- 현재 `scripts/build_llm_wiki.py` = `Master_Blueprint.md` 등 **AF 수기 문서 하드코딩 파싱**. 외부 재사용 0%. "코드 분석"이 아니라 "문서 재포맷".
- `core/ast_engine.py` = ast-grep search/replace 패턴 도구(`search_dir` 외부 가능). architecture/의존성 **추출기는 아님**. 토대는 되나 부족.
- **설계 핵심**: 공통 입력을 **소스코드 AST 분석**(Python `ast` 표준)으로. self/외부 동일 경로 + AF는 Blueprint 문서 보강. → import graph/모듈·클래스·함수/의존성 추출 → Obsidian wiki 렌더.
- **전략적 의미**: 코드 read-only라 "외부 부착 실증"의 **가장 안전한 첫 케이스** + 제품 기능. 진단 갭2(외부 검증)를 무해하게 연다.
- **메타-재귀 아님**: "self냐"가 기준이 아니라 "제품 기능이냐 vs 내부 배관이냐"가 기준. 코드→view는 사용자가 받는 제품 기능. AF 자신(502 .py)에 적용 = dogfood. (단 NEXT_STEPS의 ContextPack agent_runner 자동주입은 내부배관=함정으로 기각 이력 — Obsidian은 사람용 보너스 뷰어, 본질 아님.)

## 실행 결정 수렴 (2026-06-07 후속 세션 — 이게 다음 진입점)
**결정: LLM Wiki + Obsidian(=codebase knowledge wiki)을 경로 (i)로 간다 — light-routable bounded slice 체인.**

확정 사실(코드 grep, 재논쟁 금지):
- dogfood DEVELOP 라우팅: `dogfood.py:1788` `if route.is_light() and scope → _run_develop_light` else `_run_develop_full`.
- **light**(`dogfood.py:1739`) = compile_spec→premortem→build_plan→implement **직선 1회, 루프 없음 → 무조건 수렴.** orchestrator/Lilith/terminal_per_agent 없음. `weighted_mean` 등 leaf 성공이 전부 이 경로(NEXT_STEPS:10 is_light=True).
- **full**(`dogfood.py:1722`→pipeline.run→`DynamicOrchestrator(terminal_per_agent=True)` `project_pipeline.py:1369`) = Lilith `while cycle<max_cycles` 루프(`dyn_orch:1097`). 종료조건 실재(1148-1150 empty-board break/1210 stopped_max_cycles/1169 max_retries skip)지만 **완료 acceptance gate 없음** — Lilith(LLM)가 빈 board를 계속 재충전(`dyn_orch:1141`)해 열린 task는 미수렴. stall은 로그만(`dyn_orch:1123`). **이 레포에서 full이 복잡 feature 완성시킨 적 0.**
- 두 경로 격리 동일(`_develop_isolation_env`, 1725/1761). 차이는 실행모양뿐.
- 라우팅은 비결정 LLM 호출(`right_sized_router.classify`→generate_json) — 제출 시점에 경로 통제 불가.

판단 근거: wiki는 deterministic(parse→render)이라 동적 re-planning 거의 불필요 → light로 충분. (iii)"iterative light/매니저 완료게이트"는 north-star지만 **wiki는 그걸 검증할 잘못된 타깃**(surprise 없음). (iii)는 진짜 필요한 task가 끌어낼 때만 착수 = 추측성 인프라 회피.

**첫 행동(클리어 후 바로):**
- 첫 throw: `python agent_launcher.py dogfood run "디렉터리의 Python 파일을 read-only AST로 분석해서 각 모듈의 클래스/함수를 정리한 symbols.md를 생성. 원본 수정 금지, 테스트 포함." --merge never`
- (CLI 확정: `dogfood run <task> [--workspace] [--run-id] [--merge auto-policy|manual|never] [--non-interactive] [--allow-partial-impl]`. merge never=worktree throwaway 안전망. TTY 없으면 --non-interactive 필요할 수 있음.)
- 관찰: route_decision의 is_light/source. light 수렴 → 다음 슬라이스 체인(modules.md→imports.md→CLI). full로 빠지거나 미수렴 → "이 task엔 (iii) 필요" 데이터로 기록 후 (iii) 착수 판정.
- 슬라이스 경계를 사람이 정하는 건 손-코딩 아님(정상 dogfood). 

보류(이번 trajectory에서 명시 제외): maintenance_pipeline 死코드 정리 / ContextPack agent_runner 자동주입(내부배관 기각 이력) / Obsidian vault 6폴더 export(기존 docs/generated/llm_wiki/가 이미 vault) / full 경로 완료게이트 수정(B, 지금 안 함).

**Why:** STT 앱 논의에서 "Claude가 마감하면 AF 불필요"라는 정당한 반박 → AF는 항상 Claude/Codex 위임 오케스트레이터라는 정정 → 정체성·아키텍처 코드 재확인 → LLM Wiki 외부화가 정체성·외부부착·제품가치 교집합으로 수렴.
**How to apply:** 다음 세션 진입 시 이 메모리 먼저. 추측 말고 위 라인좌표 grep 재확인(死코드/배선은 stale 가능). 설계는 Opus, 구현 Sonnet([[feedback_model_per_phase]]).

## 첫 throw 결과 (2026-06-07 후속, run_id 1780809012-1a879d16, merge never)
**관측: light 아님 — `source=fallback`, `confidence=0.0`, `reason="no changed_files: scope required for routing"` → full 7-stage(research/design/plan/implement/test/review/cross_review).**

**근본 원인(grep 확정, 추측 아님):** `dogfood.py:1784` `_intended_scope(task)` → `spec_compiler._scope_from_intent`(line 101)는 토큰이 **확장자 AND 경로 구분자 둘 다** 있어야 scope로 인정(`_PATH_RE.search(m)`). task의 `symbols.md`는 확장자만 있고 `/` 없음 → scope=[] → `classify(changed_files=[])` → fallback → full. (대조: `core/utils.py` 명시한 leaf-함수 task들은 scope 확보 → llm → light였음. NEXT_STEPS:11.)
- **검증**: `_scope_from_intent("...symbols.md...")=[]` vs `_scope_from_intent("scripts/codebase_symbols.py ...")=['scripts/codebase_symbols.py']` 직접 확인.

**= 메모리 가설("full로 빠지면 (iii) 필요") 정정**: full 빠짐은 task 복잡도가 아니라 **greenfield(새 파일을 디렉터리 없이 지목) → deterministic scope 추출 precondition 미충족**. wiki 슬라이스는 전부 새 파일 생성이라 **경로 한정 phrasing(`scripts/xxx.py`)이 light 라우팅의 전제** — 코드 수정 아닌 phrasing 규율.

**full 경로 실측(부수 확인):** 실제 코드 생성됨(`core/symbols_md_generator.py`+`module_symbol_extractor.py`+`recursive_ast_analyzer.py`+`game_logic_cli.py`+테스트 4) BUT Lilith가 deterministic parse→render를 `game_logic_dev`/`qa_engineer` 멀티에이전트로 과분해 + work-items/research/reviews/plans 수십 문서 sprawl + AF 자체 docs 수정(worktree 격리=source 안전) + 191 cycle 후 **blocked**(verify_result는 null로 미영속 — 경미 불일치). **= 메모리 "full이 복잡 feature 완성한 적 0 / acceptance gate 없음" 재확인.**

**다음**: 경로 한정 재-throw(run_id bk9hliht3, `scripts/codebase_symbols.py`) light 수렴 여부 → 수렴 시 슬라이스 체인 계속(단 phrasing에 경로 명시 규율) / 미수렴 시 (iii) 판정.

## 부수 완료 (2026-06-07)
- `af project inspect` 외부 프로젝트 정확도 fix 3건 (`865fef9c`): doctor cwd 누수(_DOCTOR_CWD_GIT_CHECKS 제외)/하위 디렉터리 test 감지(_find_nested_test_file)/entrypoint test 제외 + pyproject pytest섹션만 indicator. 외부 3개(codex_parent_test/stock-analyzer/afb) 실측으로 발견. 테스트 47→76. 3-Tier PASS/WARN(BLOCK0)/PASS. + _recommend_next_steps 테스트 9건.

관련: [[project_right_sized_execution]] [[project_saas_strategy_position]] [[feedback_design_review_mandatory]] [[feedback_grep_before_rejecting_crossreview]]
