# Design Review: 2026-06-02-dogfood-pipeline-realignment

> Source: docs/2026-06-02-dogfood-pipeline-realignment.md
> Date: 2026-06-04 17:03
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `develop_changed_paths` 기반 allowlist는 scope 게이트를 무력화한다
   - Section: "`develop_changed_paths 기반 allowlist + 빈 allowlist=fail-closed`", "`fake가 allowlist 밖 파일 변경 → MERGE BLOCK`"
   - Issue: `develop_changed_paths`는 DEVELOP 이후 실제 변경된 파일 목록이다. 이를 allowlist로 사용하면 pipeline이 임의로 변경한 파일도 자동 승인된다. 현재 `core/dogfood.py:1151`의 `build_merge_policy()`도 `state.develop_changed_paths`를 그대로 `allowed_paths`로 사용한다. 따라서 T2의 “allowlist 밖 파일 변경 차단” 시나리오는 독립적인 기대 scope가 없어 성립하지 않는다.
   - Suggestion: `expected_allowed_paths`와 `observed_changed_paths`를 분리하라. Allowlist는 DEVELOP 전에 task/spec/사용자 정책으로 확정하고, DEVELOP 후 실제 변경과 비교해야 한다.

2. [Critical] §5 환경변수 배선은 스킬 쓰기 격리를 보장하지 않는다
   - Section: "`AGENT_PROJECT_ROOT = worktree`", "`AF_DISABLE_REGISTRY_WRITE = 1`", "`스킬·레지스트리 쓰기=전역 차단`", "`#5b ... 구현 중 확정`"
   - Issue: `AgentFactory`와 관련 모듈은 DEVELOP 전에 이미 import된다. `core/config_paths.py`의 `PROJECT_ROOT`, `PROJECT_SKILLS_DIR`, `SKILLS_DIR`와 `core/skill_procurer.py`의 `AGENT_PROJECT_ROOT`, `FORGE_DIR`는 import 시점에 고정된다. DEVELOP에서 `os.environ["AGENT_PROJECT_ROOT"]`를 바꿔도 갱신되지 않는다. 더구나 `core/builder.py:322`는 `AF_DISABLE_REGISTRY_WRITE`를 확인하지 않고 고정된 글로벌 `SKILLS_DIR`에 직접 `.py`를 쓴다. #5b는 “조건부 검증”이 아니라 이미 확인 가능한 차단 결함이다.
   - Suggestion: Dogfood DEVELOP를 별도 프로세스로 실행하고, 프로세스 시작 전에 격리 env를 설정하라. 추가로 `SandboxedBuilder.build_skill()` 자체에 write-disable 또는 명시적 `workspace/skill_root` 계약을 추가하라.

3. [Critical] Worktree는 파일시스템 안전 컨테이너가 아니다
   - Section: "`dogfood = 자기수정 안전 컨테이너`", "`쓰기탈출 차단`", "`VERIFY ... 실효 명령을 실제 실행`"
   - Issue: Worktree는 Git 변경을 분리할 뿐 외부 경로 쓰기를 막지 않는다. Pipeline 에이전트와 VERIFY 명령은 source workspace, 사용자 홈, 글로벌 skills 또는 임의 절대경로를 수정할 수 있다. `core/dogfood.py:351`의 `_default_command_runner()`는 Unix에서 `shell=True`, Windows에서 생성된 문자열을 PowerShell로 실행한다. Merge 게이트는 worktree 밖에서 이미 발생한 쓰기를 탐지하거나 rollback할 수 없다.
   - Suggestion: “안전 컨테이너” 요구를 유지하려면 DEVELOP/VERIFY를 제한된 subprocess 또는 OS sandbox에서 실행하라. 최소한 검증 명령 allowlist, 절대경로 및 shell metacharacter 차단, 보호 경로 변경 전후 검사와 복구 정책이 필요하다.

4. [High] 프로세스 전역 env 변경은 동시 실행에서 격리를 깨뜨린다
   - Section: "`dogfood DEVELOP 진입 시 직접 설정(try/finally 복원)`"
   - Issue: `os.environ`은 프로세스 전역이다. 두 dogfood run 또는 일반 project run과 dogfood run이 겹치면 한 실행이 다른 실행의 `AGENT_PROJECT_ROOT`, `AF_SELF_RUN`, `AF_DISABLE_REGISTRY_WRITE`를 관측하거나 복원값을 덮어쓸 수 있다. `ProjectPipeline.execute()`는 `DynamicOrchestrator(max_concurrent=5)`를 사용하므로 DEVELOP 내부에서도 여러 실행 경로가 이 전역 상태를 공유한다. try/finally는 동시성 문제를 해결하지 않는다.
   - Suggestion: 격리 env는 subprocess별로 전달하라. 단일 프로세스를 유지한다면 dogfood 실행 전체를 전역 lock으로 직렬화해야 하지만 기능과 처리량이 크게 제한된다.

5. [High] ProjectPipeline과 dogfood VERIFY 사이의 결과 계약이 정의되지 않았다
   - Section: "`DEVELOP = ProjectPipeline.run(...)`", "`dogfood VERIFY가 ... 실효 명령을 실제 실행`"
   - Issue: `core/project_pipeline.py:1397`의 `ProjectPipeline.execute()` 결과에는 `changed_files`나 `verification_requirements`가 없다. Dogfood VERIFY에 전달할 명령, 기대 변경 범위, disposable pipeline artifact의 소유권이 정의되지 않았다. 현재 호출 흐름은 `agent_launcher.py → dogfood.run_all() → ProjectPipeline.run() → prepare()/execute() → DynamicOrchestrator.run_project()`이며, 이 중 dogfood 검증 계약을 생성하는 계층이 없다.
   - Suggestion: DEVELOP 결과 스키마를 명시하라: `observed_changed_paths`, `expected_allowed_paths`, `verification_commands`, `pipeline_artifacts`, `status`, `run_id`. Pipeline 결과 자체를 신뢰하지 않는다면 dogfood가 task board와 git diff를 독립적으로 읽어 생성하는 규칙도 정의해야 한다.

6. [High] 제거되는 phase의 persisted state 및 CLI 호환 계획이 없다
   - Section: "`제거: INTERVIEW / RESEARCH_BRIEF / RESEARCH / SPEC / PREMORTEM / PLAN / IMPLEMENT`"
   - Issue: 기존 `dogfood_state.json`은 제거 대상 phase 값을 저장할 수 있다. `DogfoodState.from_dict()`는 `DogfoodPhase(data["phase"])`로 직접 역직렬화하므로 enum 제거 시 `dogfood status`와 재개가 실패한다. 또한 `agent_launcher.py`에는 `dogfood interview`와 `--from-file` 경로가 남아 있어 INTERVIEW 제거 결정과 충돌한다.
   - Suggestion: state schema version과 phase migration 표를 추가하라. 기존 phase 상태는 `DEVELOP`, `BLOCKED` 또는 읽기 전용 legacy 상태 중 어디로 변환할지 명시하고 CLI 제거·유지 정책도 확정해야 한다.

7. [Medium] 사전 안전 검사를 사후 REVIEW로 대체한다는 근거가 불충분하다
   - Section: "`PREMORTEM/Triad 제거 ... .githooks + REVIEW af-critic이 이미 커버`"
   - Issue: PREMORTEM은 편집 전 차단이고 REVIEW는 편집 후 판정이므로 동등하지 않다. 외부 쓰기나 비용 소진은 사후 REVIEW로 복구할 수 없다. 또한 FINALIZE 커밋 경로는 `AF_SKIP_REVIEW_GATE=1`을 사용할 수 있어 `.githooks`를 안전 근거로 삼기 어렵다.
   - Suggestion: 최소한 scope, 외부 쓰기, 위험 명령, 예상 비용을 검사하는 결정적 pre-DEVELOP gate는 유지하라.

8. [Medium] Frozen build 검증 범위가 빠져 있다
   - Section: "`구현 단계 ... dogfood: run_all에 pipeline 주입`"
   - Issue: `af.spec`에는 현재 `core.dogfood`, `core.project_pipeline`, `core.right_sized_router`가 포함되어 있지만 새 adapter/helper 모듈 추가 시 hiddenimports 갱신이 필요하다. Frozen 환경에서는 `SKILLS_DIR`가 `af.exe` 인접 경로가 되어 builder 누출이 권한 오류 또는 설치 디렉터리 오염으로 이어질 수 있다.
   - Suggestion: `dist/af/af.exe dogfood run` smoke test와 글로벌 skills 불변 검사를 Definition of Done에 추가하라.

### Missing from Design
- DEVELOP 전 확정되는 독립적인 merge allowlist
- `ProjectPipeline.run()`과 dogfood 사이의 명시적 결과 스키마
- Worktree 밖 쓰기 탐지·차단·rollback 전략
- 동시 dogfood/project 실행 정책
- 기존 `dogfood_state.json` phase migration
- 외부 서비스 및 provider 부분 실패 시 복구 정책
- Frozen build dogfood 실행 및 글로벌 skills 불변 테스트
- VERIFY 명령의 Windows/Unix 안전 실행 정책

### Positive Observations
- `agent_launcher.py`의 `AgentFactory.project_pipeline`을 주입 지점으로 식별한 것은 실제 호출 구조와 일치한다.
- Empty allowlist와 placeholder VERIFY를 fail-closed로 만들려는 방향은 타당하다. 다만 독립 allowlist와 실행 격리가 추가되어야 안전 불변식이 성립한다.