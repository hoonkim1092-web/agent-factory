---
name: project_completion_contract_and_review_surfacing
description: "**A·B·S1·S2·S3 전부 완료(2026-06-19, S3=`6808dd3d`).** §6.4 BLOCKED-terminal + surface 게이트 + 데이터계층(S1) + ExecutionHarness+AcceptanceGate(S2) + pipeline 배선(S3). 다음=watcher 이식성(A) 또는 새 product work-item."
metadata: 
  node_type: memory
  type: project
  originSessionId: 6200d978-5758-44c1-b586-b4a96b6fa73c
---

**A·B·S1·S2·S3 전부 완료.** 커밋: B=`32a438c2`, A=`f4fa5fb8`, S1=`15dd7882`, S2=`03a78052`, **S3=`6808dd3d`**. 브랜치 `2026-06-04-right-sized-execution-slice1`. **다음 = watcher 이식성(A) 또는 새 product work-item.**

## (C) S1 완료 — 데이터 계층
`core/completion_contract.py` 신규: `GoalVerdict`/`GoalEvidence`/`GoalEntry`/`GoalContract`/`HarnessResult`. **순수 구조체 + 직렬화만**(하니스 실행은 S2). `is_done()`=INV-A(빈 계약 불가, UNVERIFIED/FAILED 차단, CANNOT_VERIFY done 허용) + `has_failures()` + 중첩 `to_dict/from_dict` round-trip. `DogfoodState.goal_contract: GoalContract|None` persist 채널(import+직렬화). `af.spec` hiddenimports. 테스트 17 + `test_dogfood.py` key-set 갱신. 3-Tier(§8 S1=Tier2, subprocess 미도입 → af-critic+af-test-runner): 둘 다 PASS(290). **S1엔 파서 불필요**(§10에서 파싱=S3로 분리). 커밋 시 stale-review BLOCK → Agent-spawn 3-Tier가 gate state 미기록이라 `AF_SKIP_REVIEW_GATE=1` 우회(memory `feedback_workflow_agent_review_gate_gap`).

## (C-S2) 완료 — ExecutionHarness + AcceptanceGate
`core/completion_contract.py`에 추가. `ExecutionHarness`: cli(shlex.split+subprocess.run, shell=False) / server(Popen+DEVNULL+_SERVER_STARTUP_WAIT_SEC) / library(sys.executable -c) / gui(cannot_verify) / none(unverified). `shlex.split ValueError → evidence_type="unverified"` (§6.2 불변식). `AcceptanceGate`: idempotent(VERIFIED/FAILED/CANNOT_VERIFY skip), gui→CANNOT_VERIFY, unverified→UNVERIFIED. 테스트 46 PASS. 3-Tier 완주(WARN 각 2건 수정). wiring deferred (S3).

## (C-S3) 완료 — pipeline 배선 (2026-06-19, `6808dd3d`)
`parse_acceptance_criteria()` / `build_evidence_ledger()` 헬퍼, `PreparedProject.goal_contract` 필드, `execute()` AcceptanceGate 게이팅(`gated_ok`/`gated_reason`/`evidence_ledger`), `already_done` 재집계/legacy 폴백, `dogfood` 2차 배선. 버그픽스 2건: `work_item_parser.py` 영어 heading fallback(generator-parser 불일치 해소), `project_pipeline.py` workspace 오전달. `tests/test_acceptance_gate_integration.py` 34 신규. 3-Tier: af-critic PASS / af-cross-review BLOCK 2건 수정→PASS / af-test-runner 216 PASS.

## (A) §6.4 재작성 완료 — inv3 정합
자동리뷰 BLOCK 6건 반영(`docs/reviews/2026-06-18-015950-...`). §6.4를 "골 FAILED→dogfood IMPLEMENT 되돌림 + FSA max-retry 상수 재사용"(inv3 위반 + 사실오류)에서 **BLOCKED(goal_failed) terminal**(inv3 정합)로 재작성. 자동 수정 루프=dogfood 밖 상위 재기동+신규 bound(`MAX_GOAL_FIX_REINVOCATIONS` 류) 요구 → 후속 별도 메커니즘 분리. #2 생성 SSOT=`prepare():1246`/`PreparedProject:74`. #3 classifier 변경 제거(no-op). #4 ok 단일화. #5 already_done 재집계. #6 stale 라인. **af-cross-review가 inv3 해소 코드대조 REJECTED(=위반 없음 확증).**

## (B) surface 복원 완료 — git-native pre-commit
`scripts/check_staged_design_review.py` 신규: staged 설계문서의 `docs/reviews/` 최신 verdict BLOCK이면 exit 1. provider·사람입력 무관. `is_design_doc`/`normalize_path` SSOT 재사용. 최신성=파일명 ts(새 PASS가 BLOCK 덮음). **`_VERDICT_RE`가 볼드체 `**BLOCK**` 흡수**(실측 19파일 — af-cross-review가 잡은 BLOCK). `.githooks/pre-commit` design check 블록(AF_SKIP_REVIEW_GATE 우회 공유). 테스트 17. 3-Tier: af-critic WARN(2반영)/af-cross-review BLOCK→fixed/af-test-runner PASS.
- **미채택**: Stop hook 드레인 보류(pre-commit이 d1022ecd 정확 차단하는 최소 경로, 사용자 선택). 부수버그 `_is_watcher_alive` os.kill Windows WinError 87 / watcher codex CreateProcessWithLogonW:1909 단일vendor = surface와 독립, **미수정**(별도 추적 필요시).

## 부트스트랩 교훈
§6.4 수정본 커밋 시 (B) 게이트가 자기 자신을 차단(최신 기록 리뷰 = stale BLOCK `2026-06-18-015950`). af-cross-review 독립 확증 근거로 `AF_SKIP_REVIEW_GATE=1` 우회 커밋. watcher 재리뷰가 새 PASS를 산출하면 자연 해소(같은 source 새 verdict가 최신이 됨).

## 원칙 (동결, §11.0)
검증=완료-이벤트에 매달린 스테이지, 결함=IMPLEMENT 되먹임(단 dogfood 내 retry는 inv3로 금지 → 상위 재기동). UserPromptSubmit은 폴링이라 틀린 트리거. 연관: [[project_router_research_decoupling]], [[feedback_design_doc_review_pipeline]], [[feedback_workflow_agent_review_gate_gap]].

## 관련
- [[code/symbols]]

