# Dogfood = 자기수정 안전 컨테이너 / Project Pipeline = 개발 엔진 재정렬 (v3)

- 작성일: 2026-06-02
- 상태: v3 — 구현 진입 가능 (다회 deliberation으로 분류·불변식·인프라 재사용 확정)
- 결정 방향: **Option 2 — dogfood가 ISOLATE 직후 일반 `ProjectPipeline.run()`을 worktree 안에서 통째로 실행**
- baseline 문서: `docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md` (R1/R3 — 재분석 금지, 인용)

---

## 0. 목표 (한 문장)

> 일반 파이프라인의 LLM-driven 개발 능력을 dogfood의 자기수정 안전 루프 안에 넣어,
> AF가 자기 코드를 설계→구현→검증→반복→merge까지 스스로 수행하게 한다.

| 컴포넌트 | 책임 |
|----------|------|
| **project pipeline** | 실제 LLM-driven 개발 엔진 (설계·리서치·구현·재시도·학습·스킬진화) |
| **dogfood** | 안전 컨테이너 (worktree 격리 · 독립 검증 · merge 게이트 · 쓰기탈출 차단) |

---

## 1. 경계 원칙 (pipeline 성역화 금지, 단 비틀지도 않음)

판별 테스트: **"이 문제가 dogfood 없이도 버그인가?"**
- **YES** → pipeline/공통층에서 고친다 (단 일반 mode 동작 변경·dogfood 특수분기 주입 금지).
- **NO** → dogfood adapter/wrapper에서 처리한다.

핵심 문장:
> Project pipeline은 개발 엔진으로 그대로 둔다. Dogfood는 그 엔진을 worktree 안에서 실행하고,
> 결과의 검증·allowlist·merge·쓰기탈출 차단만 책임진다. **Pipeline 본체 수정은 dogfood 없이도
> 재현되는 일반 결함에 한하며, 현재 그 후보는 #5b(스킬 빌드 쓰기 누출) 하나뿐이고 실측 확인 후에만 손댄다.**

운영 규칙: "fix" 쪽이라도 **새 코드보다 기존 방어 재사용 우선** (planner `#`필터, `_is_e2e_missing`, F12 가드).

---

## 2. 확정된 코드 팩트 (baseline)

### 2.1 두 경로는 분리돼 있고, pipeline이 더 강한 엔진이다
- `core/dogfood.py`(2212줄)는 pipeline/orchestrator/FSALoop을 **import하지 않음** — 자체 phase 머신(`:81-115`).
- dogfood IMPLEMENT(`:1508`)는 plan step 명령 실행 + AI step마다 `claude_cli` 단발(`_default_ai_executor:435`) — 약한 루프.
- `ProjectPipeline.run()`(`project_pipeline.py:1522`) = `prepare()`(LLM 플래닝+리서치 `:725`) + **자동승인**(`:1547-1551` `_gate.approve(approver="auto")`) + `execute()`(`:1254`) → `DynamicOrchestrator.run_project()`(`:1352`) → 실패 시 **FSALoop 위임**(`dynamic_orchestrator.py:905`).

### 2.2 pipeline은 자가수정·학습·재시도를 이미 내장 (→ dogfood retry 불필요)
- **FSALoop**(`fsa_loop.py`): 한 run 안에서 max_cycles(`:164`, 기본 5) 자가수정 — L1 피드백 재시도(`:189`) / L2 전략피벗 / L3 설계재시작 / **L4 스킬진화**(`_try_evolve_failed_skill:622`, hot reload `:665`) / L5 분해.
- **학습**: 사이클별 git 스냅샷 commit(`:211`), StrategyLedger(`:150`), 메모리 회상(`project_pipeline.py:703-723`).
- → 책임 분리상 **dogfood-level 재시도는 중복**. 게다가 dogfood reset은 FSALoop의 학습/commit을 파괴 → anti-learning.

### 2.3 GitManager·workspace는 격리의 가능 조건
- GitManager는 workspace-scoped(`git_manager.py:13`). DynamicOrchestrator는 `.todo.md`/board를 workspace 상대경로로 다룸(`dynamic_orchestrator.py:150-167`). → worktree를 workspace로 주면 에이전트가 worktree 내부 `core/*.py`를 편집.

### 2.4 dogfood 격리/merge 안전장치는 이미 완성
- `prepare_isolated_worktree`(`:869`), `finalize_dogfood_result`(`:969`), `build_merge_policy`/`merge_dogfood_branch`(`:1140`, `:1177`).

---

## 3. Option 2 — 재정렬된 phase 머신

```
PENDING
 → ISOLATE          (유지: worktree 생성, dogfood 브랜치)
 → DEVELOP   ★신규   (= ProjectPipeline.run(workspace=worktree, runtime_workspace=dogfood_runtime))
 → VERIFY           (유지: dogfood 독립 검증 — pipeline 자기보고 불신)
 → REVIEW           (유지: 3-Tier 교차검증)
 → FINALIZE         (유지: worktree 커밋 → dogfood_commit)
 → MERGE            (유지: merge policy → source merge)
 → COMPLETE
```

**제거**: INTERVIEW / RESEARCH_BRIEF / RESEARCH / SPEC / PREMORTEM / PLAN / IMPLEMENT.
- 흡수처: pipeline의 `prepare()`(리서치·플래닝) + `execute()`(구현·FSA).
- **INTERVIEW 제거 근거**: pipeline이 intake 소유. task 문자열을 `pipeline.run(task_input=task)`로 직접 전달. 사용자 제약은 task_input에 명시 포함. (seed 파라미터 신설 안 함 — pipeline 무변경)
- **orphan 점검 완료**: `state.interview_path`는 제거되는 RESEARCH에서만 읽힘(`:1312`), `state.completion_criteria`는 제거되는 SPEC에서만 채워짐(`:1400`)이고 게이트에서 소비처 없음 → 안전.
- **PREMORTEM/Triad 제거 근거**: dogfood Triad는 反(critic) PASS stub(`triad.py:195`) + 合(architect) rule-based(`architect_agent.py:8`). 잃는 건 Blueprint/ADR 모순 검사인데 `.githooks` + REVIEW af-critic이 이미 커버 → 무이식.

---

## 4. 분류표 — pipeline touch vs dogfood (판별 테스트 적용, 코드 확정)

| 발견 | dogfood 없이도 버그? | pipeline touch | 처리 |
|------|:---:|:---:|------|
| **#1** merge allowlist fail-open (`dogfood.py:1129` `if policy.allowed_paths:` 빈 리스트 skip; `:1149` plan_path 의존) | NO | 0 | dogfood: `develop_changed_paths` 기반 allowlist + **빈 allowlist=fail-closed** |
| **#2** verify placeholder (`project_task_board.py:401` `# TODO`) | NO | **0** | dogfood VERIFY가 기존 `_is_e2e_missing()`(`work_item_generator.py:1070`) **재사용** + 실효 명령 0이면 fail-closed. (일반 pipeline은 raw e2e_command를 shell-exec 안 함 — core grep 확인; planner도 `#` 필터 `planner.py:96`) |
| **#4** INTERVIEW 제거 | NO | 0 | dogfood 설계 선택. research는 `project_pipeline.py:725`에서 그대로 실행 |
| **#5a** registry/workflow write 누출 | NO | 0 | dogfood가 기존 가드 활성 (§5) |
| **#5b** 스킬 빌드 `.py` 디스크 쓰기 누출 | **YES** | **조건부 1** | builder/skill층 — **누출 실측 확인 후에만**. 05-21 P0 항목 |
| board/evidence 위치 (`project_pipeline.py:1324` workspace 기록) | NO (일반 프로젝트엔 정상) | 0 | dogfood FINALIZE cleanup/allowlist에서 제외 |
| retry | NO (FSALoop 소유) | 0 | dogfood 자동 retry 안 함 (§6) |

**결론: pipeline 본체 touch는 최대 1곳(#5b), 그것도 실측 조건부. 나머지 전부 dogfood + 기존 인프라 재사용.**

---

## 5. 격리 배선 — 기존 인프라 재사용 (새 env 변수 신설 금지)

스킬/레지스트리 쓰기 차단 인프라는 **이미 존재**한다 (F12 architectural fix):
- `AF_DISABLE_REGISTRY_WRITE` 가드: `registry_manager.py:51`(_write_registry), `:181`(install), `:387`(register_built), `:403`(workflow). `skill_preflight.py:265`.
- `AF_SELF_RUN`: `core/utils.py:462-463` — 스킬 탐색에서 전역 `SKILLS_DIR` 제외(읽기 격리).
- 전역 레지스트리는 절대경로(`config_paths.py:86 REGISTRY_PATH`, `skill_procurer.py:58 FACTORY_ROOT`) + 프로세스 싱글턴(`skill_registry.py:279`).

**문제**: `_maybe_isolate_project_root_for_self_run`(`agent_launcher.py:130`)이 `:143`에서 `argv[0] in _KNOWN_SUBCOMMANDS`(="project","dogfood" `:31`)면 **skip** → **dogfood는 이 격리를 현재 활성화하지 않음** (05-25 리뷰 기록).

**처방**: dogfood DEVELOP 진입 시 직접 설정(try/finally 복원):
```
AGENT_PROJECT_ROOT = worktree       # 파일 편집은 worktree로 (git 격리 → merge 게이트)
workspace          = worktree
AF_DISABLE_REGISTRY_WRITE = 1       # 전역 registry/workflow 쓰기 차단 (기존 F12)
AF_SELF_RUN        = 1              # 스킬 읽기를 project root로 격리 (기존)
AF_SCOPE_GUARD_PATHS = <allowlist>  # scope 리포트 (기존)
→ ProjectPipeline.run(workspace=worktree, runtime_workspace=dogfood_runtime)
```
경계: **편집=worktree(merge 게이트 검사) / 스킬·레지스트리 쓰기=전역 차단 / 스킬 읽기=worktree 범위.**
**읽기는 전역(=worktree 동일 toolset) 유지** — 읽기까지 막으면 개발 능력 저하.
05-21 리뷰의 "AF_DISABLE_REGISTRY_WRITE는 isolated AGENT_PROJECT_ROOT와 짝일 때만 안전" → worktree=AGENT_PROJECT_ROOT 짝이 이 갭을 닫음.

---

## 6. Retry = 0 (책임 단일화)

- pipeline(FSALoop)이 5레벨 자가수정+학습을 이미 수행(§2.2).
- dogfood 자동 retry는 중복이며, reset이 FSALoop 학습/commit을 파괴 → 금지.
- pipeline 실패 또는 dogfood 독립 VERIFY 실패 = **BLOCK + 보고** (맹목 재실행 금지).
- `retry_run`(`dogfood.py:622` IMPLEMENT 하드코딩)과 `MAX_VERIFY_ATTEMPTS`(`:317`)는 Option 2 경로에서 사용 안 함 (REVIEW의 retry 분기 → BLOCK 매핑).

---

## 7. 불변식 (test-first — 구현보다 먼저 작성, 실패 확인 후 구현)

> 재검증은 LLM 재리뷰가 아니라 실행 가능한 테스트로 고정한다 (codex MCP 브리지 unavailable이라 재리뷰=자기검증; fail-open은 논쟁 대상이 아니라 회귀 테스트 대상).

```
inv1  plan_path/allowlist 없이 변경 파일 발생 → merge fail-closed (빈 allowlist=거부, 전체허용 아님)
inv2  실효 검증 명령이 빈/주석/TODO뿐이면 VERIFY 실패 (_is_e2e_missing 재사용; 단순 len==0 아님)
inv3  dogfood는 project-pipeline mode에서 자동 retry하지 않음 (실패=BLOCK)
inv4  INTERVIEW 제거 후에도 pipeline research/evidence가 실행됨 (project_pipeline.py:725 경로)
inv5  dogfood mode에서 skill/registry/evolution write는 worktree/runtime 안으로만 (읽기는 전역 유지)
```
inv1=merge 안전 구멍, inv5=격리 안전 구멍 — 두 축의 핵심.

---

## 8. 구현 단계 (cross-review 통과 무관, test-first)

```
0. (test-first) inv1~inv5 테스트 작성 → 전부 실패(red) 확인
1. dogfood: run_all에 pipeline 주입 + launcher 배선(self.project_pipeline, agent_launcher.py:262)  → mock 주입 테스트
2. dogfood: DEVELOP phase 신규 (DogfoodPhase + run_phase 디스패치) + §5 env 배선(try/finally)     → DEVELOP가 pipeline.run 호출 + env 설정/복원 테스트 → inv4,inv5 green
3. dogfood: RESEARCH/SPEC/PREMORTEM/PLAN/IMPLEMENT/INTERVIEW 제거 + _PHASE_ORDER 갱신             → phase 순서 테스트
4. dogfood: #1 merge allowlist = develop_changed_paths + 빈=fail-closed (build_merge_policy/finalize) → inv1 green
5. dogfood: VERIFY가 _is_e2e_missing 재사용 + 빈=fail-closed                                       → inv2 green
6. dogfood: retry_run/MAX_VERIFY_ATTEMPTS 비활성 (REVIEW retry→BLOCK)                              → inv3 green
7. (조건부) #5b: 스킬 빌드 .py 쓰기가 self-run 시 전역으로 새는지 grep/실측 → 누출 시 builder 가드     → 누출 재현 테스트
8. Master_Blueprint §3(dogfood)+§12 이력 갱신                                                      → blueprint hook 통과
```

---

## 9. 남은 검증 1건 (구현 중 확정)

- **#5b**: `skill_procurer.py:842 builder.build_skill → code_path`가 `AF_SELF_RUN`+`AGENT_PROJECT_ROOT=worktree`에서 worktree로 가는지 vs 전역 `SKILLS_DIR`로 가는지. 전역이면 일반 self-run 안전 결함(05-21 P0) → builder 층 가드. worktree면 #5b도 0 touch.
- **#2 확정됨**: core에 raw e2e_command를 직접 shell-exec 하는 경로 없음 (grep 결과 생성·판정·게이트뿐) → pipeline touch 0.

---

## 10. 미해소 advisory (구현 시 판단)

- VERIFY 독립성: pipeline이 e2e를 실행하지 않으므로(§9), dogfood VERIFY가 merge 시점에 실효 명령을 **실제 실행**해 통과를 재확인하는 게 독립 검증의 실체. 실효 명령 자체가 없으면 inv2로 fail-closed.
- 공유 RunBudget: pipeline 소진 시 dogfood가 BLOCK(`dogfood.py:1920`) — 의도된 동작.

---

## 11. 실증 테스트 계획 (필수 — mock 통과 ≠ 완료)

**성공 기준은 코드가 아니라 "dogfood worktree 안에서 pipeline이 실제로 개발하고, dogfood가 그 결과를 안전하게 검증·차단·merge함을 증명하는 결과"다.** 10개 증명 항목을 결정성 기준으로 3티어로 분리한다(LLM flakiness와 안전 증명을 분리).

### T1 — 불변식 (결정적, CI 게이트)
§7의 inv1~inv5. fail-closed 회귀 고정.

### T2 — 안전 컨테이너 e2e (★ 결정적, CI 게이트) — **가짜 pipeline 주입**
dogfood의 pipeline 주입 시드(§8 step1) + 기존 `_ai_executor` 주입(`dogfood.py:453-454`)을 이용해 **결과가 고정된 fake pipeline**을 주입한다. LLM 없이 안전 외피 전체를 증명:

| 증명 항목 | 시나리오 | 단언 |
|----------|---------|------|
| 1 worktree 생성 | dogfood run | worktree 존재, dogfood 브랜치 |
| 5 변경파일 수집 | fake가 `core/utils.py` 변경 | `develop_changed_paths`에 기록 |
| 6 verify 실행 | fake가 실 e2e_command 제공 | 명령 실제 실행됨 |
| 7 placeholder 실패 | fake가 `# TODO`/빈 명령 | VERIFY **BLOCK** (inv2) |
| 8 allowlist 차단 | fake가 allowlist 밖 파일 변경 | MERGE **BLOCK** (inv1) |
| **9 쓰기 누출 차단** | **fake가 registry write 시도** | **차단됨 + 전역 registry.yaml/skills/ 불변** (inv5) — ⚠️ 트리거 없는 "불변" 단언은 vacuous, 반드시 쓰기 시도 후 불변 확인 |
| 10 통과만 merge | fake 성공+verify green | source에 merge; fake 실패 | source 미반영 |

### T3 — 개발능력 e2e (비결정적, 수동 acceptance) — **실제 pipeline+LLM**
05-21 gap-analysis **R1**(self-run `.py` 수정 미증명)을 처음으로 증명. 역사상 첫 단계 → 일반 pipeline 결함을 드러낼 수 있음(§1 원칙대로 일반 결함만 fix).

- **성공 시나리오**: `"core/utils.py에 작은 순수 함수 추가 + tests/test_utils_*.py로 검증하라"`
  - 단언(결과 기반, 느슨): worktree에만 변경 / pipeline 산출물(research·role_plan·task_board·work-items) 생성 / 실제 코드 변경 발생 / pytest green / merge_report에 변경파일 기록 / source는 merge 전까지 미반영.
  - ❌ "정확히 이 함수" exact-match 단언 금지 (비결정성 → brittle).
- **실패 시나리오**: `"검증 명령 없이 완료"` 또는 `"허용 안 된 파일 수정"` → dogfood VERIFY/MERGE **BLOCK**.
- 실행: 최소 1회 실제 run 필수. CI 게이트 아님(비용·flaky) — 수동/주기적 acceptance.

### 완료 정의 (Definition of Done)
- T1+T2 green (CI) **AND** T3 성공 시나리오 1회 + 실패 시나리오 1회 실제 관측.
- T3 green = **AF 자기수정 파이프라인의 배관·안전경계 작동의 증거(필요조건)**. 범용성·깊이는 별개 누적 증명 — 단일 e2e를 "AF 범용 에이전트 작동"으로 등치하지 않는다.

### 범위 정밀화 (과대주장 방지)
- 범용 개발 능력은 이미 `project` 모드(`agent_launcher.py`)가 임의 프로젝트에서 수행. dogfood가 추가하는 건 **자기 자신 대상 안전 래퍼**(가장 어려운 특수 케이스). dogfood e2e는 "자기수정 안전"을 증명하지 "범용성"을 증명하지 않는다.
