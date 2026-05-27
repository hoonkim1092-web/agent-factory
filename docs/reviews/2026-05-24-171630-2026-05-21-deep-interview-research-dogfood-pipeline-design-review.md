# Design Review: 2026-05-21-deep-interview-research-dogfood-pipeline

> Source: docs/2026-05-21-deep-interview-research-dogfood-pipeline.md
> Date: 2026-05-24 17:16
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

**근거**: Critical 수준 미결 사항 2건 — Triad 호출 경로 전무, 파이프라인 Interview I/O 계약 파손. 해소 전 구현 진입 불가.

---

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] Interview I/O 계약 파손 + Intake artifact 스키마 불일치

- **Critic**: `run_interview()`는 `input_fn`/`print_fn` 주입 필요. `run_all()`이 주입 경로를 제공 안 함. non-TTY에서 pipeline이 `{"goal": task}` 기본값으로 fallback해 §4 "same artifact shape" 보장 불가.
- **Cross**: `core/interview.py:155`에서 `project_brief` 래퍼를 반환하나, `core/dogfood.py:281`은 top-level `intent` 또는 `goal`을 요구 — `--from-file` 경로가 즉시 실패함.
- **Judgment**: 두 reviewer가 동일 계층의 다른 단면을 발견. Critic은 I/O 주입 누락, Cross는 스키마 불일치. 둘 다 pipeline을 non-functional 상태로 만드는 Critical 결함.
- **Action Required**: (a) `run_all()`에 `interview_fn: Callable | None` 파라미터 추가 명세; (b) `normalize_intake_artifact(payload) -> IntakeArtifact` 정규화 함수 계약을 §3/§4에 명시하고, `interview`, `dogfood --from-file`, `_run_interview_phase` 세 곳에서 동일 함수 사용.

---

#### 2. [ACCEPT] [Critical] Triad 에이전트 호출 경로 전무

- **Critic**: §8은 Planner/Fact-Based Critic/Architect 역할을 상세 정의하나 호출 방법이 한 줄도 없음. `core/architect_agent.py` 파일 미존재. `build_plan()`은 Triad 오케스트레이션이 아닌 결정론적 함수.
- **Cross**: §8.8 Architect Agent 컨텍스트 요구사항(전체 Blueprint + 전체 ADR + active diff)이 실제 컨텍스트 한도를 초과할 수 있다는 우려 제기 (HOLD).
- **Judgment**: Critic 근거가 강함 — 파일 비존재 + 호출 경로 전무는 구현 불가 상태. Cross의 컨텍스트 우려는 별도 HOLD로 처리.
- **Action Required**: §8에 "Triad는 `dynamic_orchestrator.py` 3-agent parallel board로 구현" 또는 "순차 `executor.py` 호출" 중 하나를 결정해 명시. `core/architect_agent.py` 최소 stub 인터페이스(입출력 타입만)를 §18 체크리스트에 포함.

---

#### 3. [ACCEPT] [High] Research 실행 주체 미정의

- **Critic**: §6이 "brief로 제약된 research"를 요구하지만 무엇이 연구를 실행하는지 없음. `core/researcher.py`(894줄) 언급 없음. `_run_research_phase`는 현재 `return context` stub.
- **Cross**: `core/dogfood.py:303`이 research brief를 그대로 반환. `core/spec_compiler.py`가 기대하는 `local_refs`, `web_refs` 등 키 부재.
- **Judgment**: 양쪽 모두 동일 gap 확인. 기존 `core/researcher.py`가 있음에도 설계에서 무시됨.
- **Action Required**: §6 또는 §18에 `ResearchExecutor` 계약 명시: 입력 `ResearchBrief + workspace + budget`, 출력 `{local_refs, web_refs, llm_prior, references, errors, skipped_questions}`. `core/researcher.py` 재사용 여부 결정.

---

#### 4. [ACCEPT] [High] Retry loop에서 plan 재생성 경로 없음

- **Critic**: `retry_run()`(dogfood.py:269)은 `state.phase = IMPLEMENT`, `state.attempts += 1`만 수행. 동일 plan.json 재실행. `build_plan()` 입력(`CompiledSpec + PremortomResult`)이 retry 시 변경되지 않아 동일 plan 재생성. §12 "revise plan" 요건 구현 불가.
- **Cross**: 미발견.
- **Judgment**: Critic 단독이나 코드 인용이 구체적 (`dogfood.py:269`, `build_plan()` 시그니처). §12 요건과 실제 구현 간 직접 모순.
- **Action Required**: `retry_run()` 시 `last_failure`를 `PremortomResult.risks`에 추가 후 `build_plan()` 재호출하거나, PLAN phase로 rewind하는 경로를 state machine에 명시. §12 flowchart에 이 분기 추가.

---

#### 5. [ACCEPT] [High] Review tier 순서가 기존 review_gate와 충돌

- **Critic**: §11이 `af-test-runner → af-critic → af-cross-review`를 정의하나, 기존 CLAUDE.md/`check_pending_review.py`는 `af-critic → af-cross-review → af-test-runner`. `_run_review_phase`(dogfood.py:423)는 review tier를 실제로 호출하지 않음. 이중 발화 위험.
- **Cross**: `scripts/check_pending_review.py:57`이 `"af-critic → af-cross-review → af-test-runner"` 반환 — 문서와 코드 불일치 확인.
- **Judgment**: 양쪽 동일 모순 확인. 순서 변경이라면 마이그레이션 범위(scripts, prompts, tests, Blueprint)를 정의해야 함.
- **Action Required**: 의도적 순서 변경인지 오타인지 결정. 변경이라면 §11에 마이그레이션 태스크 목록 명시. 이중 발화 방지 정책(dogfood pipeline의 review가 pre-commit gate와 어떻게 공존하는지) §11에 추가.

---

#### 6. [ACCEPT] [Medium] Worktree 격리 상태 모델 불완전

- **Critic**: `DogfoodState`에 `worktree_path` 없음. Resume 시 worktree 경로 복원 불가. worktree 생성 phase 미정의.
- **Cross**: `core/dogfood.py:81`에 `main_workspace`, `worktree_path`, `branch`, `dirty_policy` 필드 전무. `core/dogfood.py:211`에서 runtime이 동일 workspace의 `.af_runtime`으로 default.
- **Judgment**: 양쪽 동일 gap. Cross가 더 구체적인 필드 목록 제시.
- **Action Required**: `DogfoodState`에 `source_workspace`, `worktree_workspace`, `runtime_workspace`, `branch_name`, `base_ref`, `dirty_policy`, `finalization_mode` 추가를 §13에 명시. IMPLEMENT phase 직전 worktree 생성 타이밍을 §14에 명확화.

---

#### 7. [ACCEPT] [Medium] CLI 소유권 불일치

- **Critic**: `run_factory_cli.py`의 `_STAGE1_COMMANDS`에 `"dogfood"` 키 없음. 사용자가 실제로 호출할 방법 없음.
- **Cross**: `run_factory_cli.py:621`은 `"interview"`만 등록. `agent_launcher.py:903`에 `dogfood run/interview/status`가 별도 존재.
- **Judgment**: 양쪽 동일 이슈. Cross가 두 파일 간 이중 구현 사실을 추가로 발견.
- **Action Required**: §16/§18에 "canonical CLI 진입점은 `run_factory_cli.py`" 또는 "`agent_launcher.py`" 중 하나를 명시. MVP 커맨드를 기존 구현된 이름에 매핑하는 테이블 추가. argparse 스펙(`--from-file`, `--deep-skip` 등) §16에 포함.

---

#### 8. [ACCEPT] [Medium] `dogfood run` vs `dogfood complete` phase 경계 불명확

- **Critic**: `run`과 `complete`의 terminal condition이 동일(COMPLETE/BLOCKED)하면 중복, 다르면 경계 미명시.
- **Cross**: `start/review/resume` 커맨드 누락 언급 (finding #1에서 부분 언급).
- **Judgment**: Critic 단독이지만 설계 문서에서 직접 확인 가능한 모호성. 구현자가 독립적으로 해석해 불일치 발생 위험.
- **Action Required**: §16에 각 커맨드가 실행하는 phase 범위와 종료 조건을 테이블로 명시. `run`이 어느 phase에서 사용자 개입을 기다리는지 명확화.

---

#### 9. [ACCEPT] [Medium] Verification 커맨드 Windows 비호환 + shell=True 위험

- **Critic**: §14 `D:/tmp/af-dogfood-<run_id>` 경로가 Windows에서 `%TEMP%` 대신 Unix `/tmp` 사용.
- **Cross**: `core/premortem.py:91`이 `grep` 사용. `core/dogfood.py:167`이 `shell=True`로 LLM 생성 커맨드 실행 — Windows/PowerShell에서 취약.
- **Judgment**: Critic은 경로, Cross는 shell coupling을 각각 발견. 모두 동일 플랫폼 이식성 범주.
- **Action Required**: §7 Premortem 예시의 `grep` 커맨드를 구조화된 형태로 교체. §14 worktree 경로를 `$env:TEMP` 기반으로 수정. §18에 verification step 형식을 `{argv: [...], cwd, timeout, kind}`로 명세.

---

#### 10. [ACCEPT] [Low] §21 "Known details deferred"가 배포 동등성 규칙과 충돌

- **Critic**: retry budget 기본값이 `MAX_VERIFY_ATTEMPTS = 3`으로 코드에 이미 하드코딩됨. §21이 이를 "implementation spec, not blocker"로 처리하면 문서-코드 불일치.
- **Cross**: 미발견.
- **Judgment**: CLAUDE.md 프로젝트 규칙에 직접 위반 가능성. Low지만 명시적 결정 필요.
- **Action Required**: §21에서 retry budget 기본값과 state JSON 필수 필드를 확정하거나, "별도 lower-level spec 먼저 작성" 조건을 명시.

---

#### 11. [HOLD] [Low] Architect Agent 컨텍스트 한도 초과 가능성

- **Critic**: 미발견.
- **Cross**: 전체 Blueprint + 전체 ADR + active diff를 매 synthesis마다 주입하면 컨텍스트 초과 가능. fallback 동작 미정의.
- **Judgment**: 실제 컨텍스트 크기와 증가 속도를 모르면 판단 불가. 현재 Blueprint 845줄, ADR 수 확인 필요.
- **Question for Author**: Architect Agent에 주입할 최대 컨텍스트 예상 크기는? 초과 시 section-indexed retrieval fallback을 허용하는가?

---

#### 12. [REJECT] [Low] af.spec hidden imports 누락

- **Source**: Cross
- **Original Finding**: 새 모듈이 af.spec에 없을 수 있음.
- **Rejection Reason**: Cross 자신이 `af.spec:97` 확인을 통해 기존 파이프라인 모듈(`core.interview`, `core.research_brief`, `core.spec_compiler`, `core.premortem`, `core.planner`, `core.dogfood`)이 모두 등록되어 있음을 확인. 실제 문제 없음.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Interview I/O 계약 파손 + 스키마 불일치 | Critical | ACCEPT | Both |
| 2 | Triad 에이전트 호출 경로 전무 | Critical | ACCEPT | Both |
| 3 | Research 실행 주체 미정의 | High | ACCEPT | Both |
| 4 | Retry loop plan 재생성 경로 없음 | High | ACCEPT | Critic |
| 5 | Review tier 순서 review_gate 충돌 | High | ACCEPT | Both |
| 6 | Worktree 격리 상태 모델 불완전 | Medium | ACCEPT | Both |
| 7 | CLI 소유권 불일치 | Medium | ACCEPT | Both |
| 8 | `dogfood run` vs `complete` 경계 불명확 | Medium | ACCEPT | Critic |
| 9 | Verification 커맨드 Windows 비호환 | Medium | ACCEPT | Both |
| 10 | §21 deferred details 배포 동등성 위반 | Low | ACCEPT | Critic |
| 11 | Architect Agent 컨텍스트 한도 | Low | HOLD | Cross |
| 12 | af.spec hidden imports 누락 | Low | REJECT | Cross |

---

### Recommendations

구현 진입 전 설계 문서에서 해소해야 할 항목:

1. **[즉시 필수]** `normalize_intake_artifact()` 함수 계약을 §3/§4에 추가. `run_all()` 시그니처에 `interview_fn: Callable | None` 파라미터 명세.
2. **[즉시 필수]** §8에 Triad 호출 메커니즘 결정 — `dynamic_orchestrator.py` parallel board vs 순차 `executor.py`. `core/architect_agent.py` stub 인터페이스 정의.
3. **[구현 전 필수]** §6/§18에 `ResearchExecutor` 계약 추가. `core/researcher.py` 재사용 결정.
4. **[구현 전 필수]** §12 retry flowchart에 plan rewind 경로 추가.
5. **[구현 전 필수]** §11 review tier 순서를 기존 review_gate와 일치시키거나, 의도적 변경 시 마이그레이션 태스크 목록 명시.
6. **[설계 보완]** §13 `DogfoodState` 스키마에 `worktree_path`, `branch_name`, `dirty_policy` 필드 추가.
7. **[설계 보완]** §16에 canonical CLI 진입점 및 커맨드-phase 매핑 테이블 추가.
8. **[플랫폼 수정]** §7 grep 예시 → 구조화 형태, §14 `/tmp` → `$env:TEMP` 경로 수정.