---
name: dogfooding-hygiene-sprint
description: "dogfooding hygiene sprint — P0-A/B·P1-C 완료, P1-D·P2-E/F 잔여. P1-C-rv는 optional-id work-item으로 분리"
metadata:
  node_type: memory
  type: project
  originSessionId: 3a317cce-6081-4506-8c63-9bf90c73fb7d
---

2026-05-18 코덱스 분석 + 팩트 검증로 도출한 dogfooding hygiene sprint. 2026-05-19 P0-A/P0-B 완료.

## ✅ 완료 (2026-05-19)

- **P0-A — 런타임 산출물 untrack** (`2dff149a`). 사용자 결정으로 메모리 원안(agent_factory 29개)보다 확대: `projects/*/runs/`(274) + `projects/*/dashboard.json`(21) + `projects/*/skill-lock.yaml`(22) = **317개 `git rm --cached`** (파일 디스크 보존). `.gitignore` per-project `runs/` 5줄 → `projects/*/runs/` 일반화 + dashboard/skill-lock 패턴. `core/projects/`는 제외(패키지 seed). `projects/agent_factory/` config 6개(architect/logicdev/context_schema/policies/settings/workflow.yaml)는 **내용 변경 없는 CRLF-only 노이즈** — seed로 판정해 추적 유지, 미스테이징(별도 renormalize 이슈, 본 sprint 범위 밖).
- **P0-B — review_metrics_logger BLOCK 해소** (`21f6a827` + Blueprint `e4c8038c`). 4 finding 수정: (1) guidance 게이팅 `t3_rate`→`t3_block_only_commits` 기반 `block_only_rate`, (2) `_load_skip_audit_records()` 신규 — `subsequent_block=True` 시 guidance 억제, (3) 7일 span 게이트 추가, (4) 충분-샘플 테스트 단일커밋 T2+T3 그룹핑. 3-Tier: af-critic PASS / af-cross-review WARN(BLOCK 0) / af-test-runner PASS. 테스트 40 PASS.
- **P1-C — verification_focus 전달 갭 해소** (`bcc4c223`). B-2가 verify 태스크 `acceptance`에 주입한 `verification_focus`가 LLM dispatch(`dynamic_orchestrator._lilith_decide_next`→`board_prompt_digest`) 경로에 미도달하던 배포 동등성 위반. `board_prompt_digest()`에 `task_id`/`phase`/bounded `acceptance`(`max_acceptance_chars=240`) 렌더링 + `_lilith_decide_next` 프롬프트에 보드 task_id echo 지시. rule-based dispatch(`next_board_tasks()`)는 기존부터 task_id 채워 무관. 테스트 3건 신규. 3-Tier: af-critic PASS / af-cross-review WARN(BLOCK 0) / af-test-runner PASS. af-cross-review advisory(프롬프트 `"else empty"` 모호) 반영 → 게이트 stale은 reviewer-dictated 편집 timestamp false-positive라 `AF_SKIP_REVIEW_GATE=1` 우회. **실제 LLM run(claude_cli ×2)으로 end-to-end 검증** — LLM이 `task_id` echo → `_resolve_task_meta` → `specialize`까지 `검증 초점:` 도달 확인.
- **P1-C 후속 finding #2·#3** (`c0c7c0b7`). #2: `write_task_execution_plan()`이 태스크 행을 `role_plan`이 아닌 `board["tasks"]`에서 `module_id` 그룹핑해 렌더 → `docs/task_execution_plan.md`에 주입 `검증 초점:` 반영. #3: `build_project_board()` `verification_focus` 주입에 `MAX_VERIFICATION_FOCUS_ITEMS=8`·`MAX_VERIFICATION_FOCUS_ITEM_CHARS=200` cap. 테스트 3건 신규. 3-Tier: af-critic PASS / af-cross-review WARN(BLOCK 0) / af-test-runner PASS(75). 게이트 `all-tiers-passed` 정상 통과(우회 없음).

## ⚠️ 잔여 / 미커밋

- **cli_hook_bridge 미커밋** — `.claude/settings.json`의 `cli_hook_bridge` 훅 5개 제거 (settings.local.json 2중 발화 해소). 아직 커밋 안 됨. `.py` 아님 → 게이트 무관. A·B 세션 범위 밖이라 보류.
- **P0-B advisory N-1 (미반영)** — `review_metrics_logger.py` `span_days`가 `records[0]`/`records[-1]` 파일순서 의존. 동시 쓰기 시 음수 span 가능하나 실패 모드는 보수적(guidance 억제=안전). af-cross-review가 `min`/`max` 권고. WARN-only라 미수정, 후속 권고로만 기록.
- **CRLF 노이즈** — `projects/agent_factory/` config 6개가 `.gitattributes eol=lf` vs 작업트리 CRLF로 영구 modified 표시. 별도 renormalize 작업 필요(`git add --renormalize`).

## 다음 작업 (의존성순)

**P1**
- **D. AF self-run 체크리스트 고정** — round4 friction 기반. A 완료 후 의미.

**P2**
- **E. B-3 step 4** manifest projection — `skill_manifest`에 `capability_gap/confidence/rationale` 보존. 소비처 0개 → 포렌식 기록 수준. [[project_research_router_b3_pending]]
- **F. 루프 정합** — `.codex/hooks.json` cli_hook_bridge 2중 등록(codex용), `MAX_ROUNDS` 코드(check_pending_review.py=2) vs CLAUDE.md(5) 불일치.

**P1-C 잔여 (별도 처리)**
- **P1-C-rv → optional-id 정규화 work-item** — P1-C(`bcc4c223`)의 bypass된 변경을 사용자 지적으로 재검증하다 `safe_id("")="skill"` 다중모듈 계약 버그 발견. P1-C-rv 시도(`_lilith_decide_next` 화이트리스트 + `_resolve_task_meta` 가드)는 cross-review BLOCK + whack-a-mole이라 **철수**. WIP는 `git stash` `stash@{0}: P1C-rv-safe_id-wip`에 pathspec 한정으로 보존(3파일만). 정식 설계는 [[optional-id-normalization]] 참조 — Tier 3, `safe_optional_id()` 헬퍼 접근.
- **개행 정규화 [Medium, WARN-only]** — `verification_focus` 항목 내부 `\n`이 `_clean_text()`로 미제거 → `task_execution_plan.md` markdown 구조 깰 수 있음. `build_project_board()` 주입 루프에 `" ".join(item.split())` 1줄로 해소. optional-id work-item과 함께 묶어 처리 가능.

## 참고

P0-B 해소로 `compute_report()` 출력은 이제 신뢰 가능. 단 **A Phase 4(스마트 라우팅)는 여전히 1주 실측 데이터 수집 후** 진입 — 데이터 부족 게이트는 코드가 아니라 수집 기간 문제. [[project_dev_workflow_paradigm_shift]]

## 관련
- [[code/symbols]]

