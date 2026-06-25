---
name: project_dogfood_false_success_spin
description: "dogfood full-route가 stopped_max_cycles로 침묵사한 진짜 원인 = 가짜 성공(ok:true가 작업 완료가 아니라 'CLI 응답함'을 측정). S1+S2+S3 전부 구현 완료(2026-06-20). S2=가짜성공가드(agent_runner, 커밋 539bfe62). 다음=우선순위 3·5 별도 설계(baseline 동결됨: docs/2026-06-20-priority-3-5-baseline-capture.md)."
metadata: 
  node_type: memory
  type: project
  originSessionId: 1d18681b-c37c-430f-a944-30aabd9e966b
---

**계기**: Q-S6 QA 파이프라인 dogfood 실증 run(`1781884669-d94896b6`/`-a7502e9b`, 2026-06-20). task="core/completion_contract.py에 GoalContract.goal_count() 추가". Tier-3 파일이라 full route. **phase=blocked, last_failure=stopped_max_cycles**. goal_count는 worktree에 끝내 미생성.

## 진짜 인과 사슬 (전부 run 아티팩트 증거 있음)

```
[Bug 0] codex_cli 셸이 Windows에서 완전히 깨짐 (환경, 방아쇠)
   증거: 두 build 에이전트 transcript 모두 "batch file arguments are invalid 오류로
        [dir/pwd/pytest 등 모든 명령] 실패". 파일쓰기(apply_patch)는 됨, 명령실행은 전부 실패.
        ↓
[Bug 1] build 결과 = ok:true  ★핵심 소프트웨어 버그★
   증거: result.json ok:true / 에이전트는 "수행하지 못했습니다"라고 자기보고.
   증거: core/agent_runner.py:1226-1236 — `if cli_result.get("ok"): result={"ok":True,...}`.
        cli_result.ok = "codex.CMD가 텍스트 반환함"이지 "작업 완료"가 아님. 파일변경/자기보고
        무시. 에이전트가 "막혔다"고 말해도 그 텍스트가 응답이라 성공 집계.
        ↓
[Bug 2] 산출물 검증 없음
   증거: module_1 build = 아무것도 안 씀. module_2 build = tests/test_goal_contract_goal_count.py만
        쓰고 구현은 안 씀. core/completion_contract.py 변경 목록에 없음 → goal_count 영영 부재.
        둘 다 ok:true.
        ↓
[Bug 3] verify 영구실패 + fail-fast 없음
   증거: goal_count 없음 → 테스트 실패 → task_id "module_1_verify_3"(재시도 누적).
        보드 board_is_complete() 영영 False → orchestration loop(dynamic_orchestrator.py:1100)이
        "완료"도 "할일없음"(line 1151 break)도 아닌 상태로 빈 사이클 grind → max_cycles.
   증거: events.jsonl step 이벤트 18개(≈9 실행) vs 100+ 사이클 = 무진전 spin.
        ↓
[Bug 4] 과분해 (부차적)
   증거: 1-메서드를 module_1/module_2 2덩어리 × scope/build/code_review/cross_validate/verify
        5단계 + docs/architecture·planning/*·agents/*.yaml·docs/plans·research·work-items·reviews 산더미.
        Floor 2(Tier-3 → design+review+cross_review 강제)가 단계 수 부풀림.
```

## 가장 중요한 정정 — 앞선 표면 진단은 빗나감
세션 내내 논의한 **Tier-3 분류 / Floor 2 / 리뷰 중복**은 실재하나 **이 run 死因이 아님**. Tier-3를 "고쳤어도" build 가짜성공+verify실패+spin은 동일하게 발생. Tier-3는 태스크 수만 부풀린 **조연**. 주연 = Bug 0(방아쇠) + Bug 1(환경실패를 침묵 미완성으로 둔갑).

핵심 한 줄: **에이전트가 "못 했다"고 말하는데 시스템이 "성공"으로 받는 게 모든 침묵 실패의 뿌리.**

## 부수 사실 (red herring 제거)
- "No GOOGLE_API_KEY" 로그는 orchestrator **진입 前** research bootstrap에서 1회. orchestrator events 내 provider 에러 0건. **gemini 미설정은 死因 아님.** build를 실제로 돌린 provider는 codex_cli.
- dogfood 외부 `_run_review_phase`(dogfood.py:1937)는 코드리뷰 아님 — verify_result.passed/has_failures만 보는 pass/block 게이트. 주석(dogfood.py:1646 "dogfood runs its own 3-Tier REVIEW phase")은 **stale/거짓**.
- dogfood 커밋은 `AF_SKIP_REVIEW_GATE=1`(dogfood.py:1076,1671)로 프리커밋 리뷰게이트 **차단** → dogfood run의 유일한 실제 코드리뷰는 DEVELOP 내부 orchestrator 팀롤(qa_engineer_code_reviewer/cross_validator)뿐.

## 과분해(Bug 4) 4개 층 분해 — 각 층 무죄/유죄 판정
```
[층1 brief LLM]  goal 단수 → deliverables 2개(구현 + pytest 테스트). 증거: project_brief.json.   ✅ 정상(테스트 분리는 좋은 설계)
[층2 role계획]   deliverable 2개 → 모듈 2개(module_1=구현, module_2=테스트). 1:1 매핑.            ✅ 정상
   ※ 모듈에 스킬 필드 없음, 역할 1개(qa_engineer)·스킬 1개가 두 모듈 소유 → 모듈분해는 스킬 아닌 deliverable이 결정. 스킬은 역할 수만 결정(여기선 1개=적정)
[층3 단계템플릿] 모듈마다 scope/build/verify 고정 깖.                                              ❌ 과함(1-메서드에 scope 불필요)
[층4 Floor2]     모듈마다 code_review+cross_validate 주입.                                          ❌ 과함(모듈별 중복리뷰)
```
**핵심: 분해(모듈 나누기)는 멀쩡. 문제는 나뉜 단위마다 붙는 단계·리뷰의 무게.** "과분해"란 이름 자체가 부정확했음.

**뿌리 = 층3·4 + full 루트 단일 기어**: `bootstrap_roles.py:398 plan()`이 task_input+brief 다 받아 **규모를 알면서도**, 프롬프트가 "project planning director" 정체성 + "모듈 0 금지(line465)" + "qa_engineer 필수+verify 필수(line473)"로 **최소 분해를 의무화**. 출구 없음. right_sized_router는 light(분해0)↔full(멀티모듈 프로젝트) **이분법**이고 full이 규모 무관 단일 기어라, Tier-3 사소변경이 Floor2로 light서 떨어지면 곧장 풀 프로젝트 템플릿行.

## 작은 Tier-3용 올바른 실행 흐름 (합의된 설계 방향)
```
build(구현+테스트)
  → [존재가드] ~0비용: 파일변경됐나/import되나   ← Bug-1 일회 차단
  → test ──FAIL→ fix (싸게 반복)
  → (초록일 때만) code_review ──BLOCK→ fix
  → cross_review ──BLOCK→ fix    ← 2회차부턴 스코프 재리뷰(diff만)
  → complete = 단일 코드버전이 전 게이트를 추가수정 없이 연속 통과
```
원칙 4: **싼 게이트가 비싼 게이트를 가린다**(test 초록일 때만 cross_review 토큰 소비) + **스코프 재리뷰**(2회차 diff만, 전체 재독 X) + **하드 루프 캡**(MAX_ROUNDS류) + **수렴 정의 명문화**.
※ 정정: "verify 먼저" 단순 순서트릭은 부분철회 — 리뷰 후 수정이 앞선 test를 무효화하므로 순서 하나로 못 풂. test는 싸서 N번 OK, cross_review를 적게·좁게 재실행하는 게 진짜 레버.

## 수정 우선순위
1. **Bug 1 가짜 성공 탐지** (다음 진입점): 에이전트 자기보고 "못 함" OR 파일변경 0 OR 기대 산출물 부재 → ok:false. 6분 침묵사 → 즉시 명확한 실패. Windows 무관·메타재귀 아님·순수 correctness·최고 레버리지. 단 dynamic_orchestrator/agent_runner는 Tier-3라 설계 1장 후 진행.
2. **Bug 3 무진전 fail-fast**: "N 사이클 보드 진전 0 → BLOCK". Bug 1 누락분 안전망. provider fail-fast도 이 특수케이스.
3. **작은 Tier-3 기어**(위 실행흐름): full에 "작은 full" 추가. 층3·4 무게 제거 + 단일기어 분해.
4. (별도) Bug 0 codex Windows 셸 — `batch file arguments are invalid` 시그니처 감지.
5. (큰 별도) Bug 4 뿌리(bootstrap_roles 프롬프트 규모 조건부화) — right-sizing 본질.

## Tier-3 판단 관련 (보류 결론, 별개 트랙)
- Tier-3 판정 유지(fail-closed 옳음). LLM 단독 위험도 강등 금지. 정밀화는 AST proof-carrying(증명되는 안전만 강등)으로 — 설계자가 "Phase 1"로 미뤄둠(blast_radius.py 주석 "Phase 0 — Proof-Carrying Review 도입 전").
- Floor 2 review/cross_review 주입 억제는 `merge_mode∈{never,manual}`일 때만(auto_policy는 내부 리뷰가 유일 게이트). `_light_allowed` INV-5와 동형.

## 수정 설계 완료 (2026-06-20, Opus, af-cross-review PASS/BLOCK0)
설계문서 `docs/2026-06-20-dogfood-false-success-spin-fix-design.md`. 범위=correctness 3슬라이스(disjoint 파일·병렬 구현 가능). 우선순위 3·5(작은 Tier-3 기어 + bootstrap 과분해 뿌리)는 baseline churn BLOCK루프 회피 위해 **별도 설계로 분리**(§6 진입점만).
- **S1 (cli.py)**: `_SHELL_FAILURE_MARKERS=("batch file arguments are invalid",)` 신설 → `_classify_cli_issue`가 `"shell_error"` 반환 → `cli.py:930` 제외튜플에 추가 → codex ok-승격 차단. 핵심사실 검증됨: 비공백 issue는 전부 제외튜플에 있어 잔여 false-success는 `returncode!=0 + issue=="" + text非공백` 한 경우뿐.
- **S2 (agent_runner.py:1226)**: 보수적 가드 — `ok==True AND returncode!=0 AND 파일변경0`만 강등(`*_false_success_no_output`, cli_failures 적재→`:1259` 폴백). 자기보고 텍스트/blanket-zero는 하드게이트 미채택(read태스크 false-fail 위험). `_workspace_mutation_signature`(파일수,최대mtime; .git/node_modules/__pycache__/.af-dogfood 제외) 신규.
- **S3 (dynamic_orchestrator.py)**: `_hard_no_progress_cycles=env(AGENT_HARD_NO_PROGRESS,20)` + 루프내 hard-stop(`cycles_since_completion>=임계 AND (all_infra OR retry_exhausted)`→`_blocked_no_progress=True; break`) + `:1213` 상태결정에 `blocked_no_progress` 분기 선두 삽입. 기존 stall감지(:1124 로깅전용)·infra판정(:338)·`_last_completion_cycle` 재사용.
- cross-review advisory(Low) 2건: S3 `retry_exhausted`는 infra실패가 dispatch 스킵돼 카운터 미증가→공허 가능하나 `all_infra`가 커버(구현시 주석); `_blocked_no_progress` 플래그명 명료화.
- 구현 순서: S1·S3 먼저(단순), S2 뒤. 3슬라이스 disjoint→병렬 PR 가능. 각 Tier-3=3-Tier 리뷰.

## 구현 완료 (2026-06-20)
- **S1+S3 완료** (Sonnet, 커밋 `32f77a60`). 3-Tier PASS.
- **S2 완료** (Opus, 커밋 `539bfe62`). 설계 대비 **af-cross-review BLOCK 2건 흡수 후 강화**:
  - **F1**: 시그니처를 `(파일수, 최대mtime)` → `(파일수, st_mtime_ns 총합)`. max는 미래 mtime 형제 파일이 더 오래된 파일 수정을 가려 false-negative(INV-S2b 위반). sum+정수(ns)라 부동소수 오차 없음·항상 감지. `.venv`/`venv` 제외 추가.
  - **F2**: `ws_sig_before`를 루프 밖 1회 → **provider별 실행 직전 스냅샷**(provider1 부분쓰기가 provider2 가짜성공 가림 방지). + **bounded-workspace gate**(`target_workspace!=PROJECT_ROOT`): workspace 미전달=전체레포 walk 2.85초 비용 회피, dogfood worktree는 bounded라 정상 작동·원 버그 재현됨.
  - `produced_changes`를 result dict에 첨부하려던 설계(§3.2 (3))는 **소비처 없어 제거**(speculative 코드 배제, S3 미구현). 필요 시 실 consumer와 함께 추가.
  - 테스트 13건. 3-Tier: af-critic WARN / af-cross-review BLOCK(R1)→PASS(R2 codex 실증) / af-test-runner PASS(61).
- **학습**: mtime 시그니처는 max 아닌 sum. 워크스페이스 변경 감지 가드는 multi-provider면 provider별 baseline 필수, 대형 워크스페이스(repo-root)는 비용으로 skip.

## ▶ 다음 = 우선순위 3·5 별도 설계
S1~S3 correctness 슬라이스 전부 닫힘. baseline 실코드 동결: `docs/2026-06-20-priority-3-5-baseline-capture.md` (§6.1 right_sized_router `is_light():55-70`/`LIGHT_STAGES:33`/`_FULL_STAGES:104`/Floor2 `_apply_safety_floors:205-227`, §6.2 bootstrap_roles `plan():398`/director프롬프트:400/모듈0금지:465/`_ensure_qa_role:318-396`/규모입력 부재). 두 설계 **각각 전용 dated 문서 분리**(합치면 baseline churn → cross-review BLOCK 진동, 메모리 `cross_review_stale_baseline_repeat`).

연관: [[project_qa_pipeline_intake]] [[project_right_sized_execution]] [[feedback_test_mock_vs_defect]] [[project_model_routing_facts]] [[feedback_model_per_phase]] [[feedback_cross_review_stale_baseline_repeat]] [[feedback_analysis_doc_baseline_must_be_real_code]]
