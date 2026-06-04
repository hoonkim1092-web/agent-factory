# Agent Factory — Claude Code 지시사항

<!-- KARPATHY-PRINCIPLES-START (실험 2026-05-04 ~ 2026-05-11, 제거 시 이 마커 사이 전부 삭제) -->
## LLM 행동 원칙 (Karpathy)

> 출처: [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)
> **트레이드오프**: 속도보다 신중함을 택한다. trivial한 작업에는 판단해서 적용.

### 1. Think Before Coding — 가정하지 말고, 혼란을 숨기지 말고, 트레이드오프를 드러내라

구현 전에:
- 가정을 명시한다. 불확실하면 묻는다.
- 해석이 여럿이면 모두 제시한다. 조용히 고르지 않는다.
- 더 단순한 방법이 있으면 말한다. 정당하면 반박한다.
- 모르겠으면 멈추고 무엇이 혼란스러운지 명시하고 묻는다.

### 2. Simplicity First — 문제를 푸는 최소 코드. 추측성 코드 금지.

- 요청하지 않은 기능 추가 금지.
- 일회성 코드에 추상화 금지.
- 요청하지 않은 "유연성/설정 가능성" 금지.
- 일어날 수 없는 시나리오의 에러 처리 금지.
- 200줄을 50줄로 줄일 수 있으면 다시 써라.

자문: "시니어 엔지니어가 이걸 보면 과설계라고 할까?" YES면 단순화.

### 3. Surgical Changes — 꼭 필요한 곳만 만져라. 자기 흔적만 정리해라.

기존 코드를 편집할 때:
- 인접한 코드/주석/포맷을 "개선"하지 않는다.
- 깨지지 않은 것을 리팩토링하지 않는다.
- 기존 스타일을 유지한다 — 본인 취향과 달라도.
- 무관한 죽은 코드를 발견하면 언급만 한다 — 삭제 X.

본인 변경으로 고아가 된 것만 제거:
- 본인이 미사용으로 만든 import/변수/함수만 제거.
- 기존부터 죽어있던 코드는 요청 없이 제거 X.

검증: 변경된 모든 줄이 사용자 요청에 직접 추적되어야 한다.

### 4. Goal-Driven Execution — 성공 기준 정의. 검증될 때까지 반복.

작업을 검증 가능한 목표로 변환:
- "검증 추가" → "잘못된 입력 테스트 작성 후 통과시키기"
- "버그 수정" → "버그 재현 테스트 작성 후 통과시키기"
- "X 리팩토링" → "전후 테스트 통과 보장"

다단계 작업은 간단한 계획 제시:
```
1. [단계] → 검증: [체크]
2. [단계] → 검증: [체크]
```

강한 성공 기준은 독립 반복을 가능하게 한다. "그냥 동작하게 해" 같은 약한 기준은 매번 명확화가 필요하다.

**효과 측정**: 불필요한 변경 감소, 과설계로 인한 재작성 감소, 구현 후가 아닌 구현 전 명확화 질문 증가.
<!-- KARPATHY-PRINCIPLES-END -->

---

## 필수 규칙

### 파이프라인 배포 동등성 규칙 (2026-05-13 추가)
- **파이프라인 관련 기능은 배포 사용자 환경과 개발 환경에서 동일하게 동작해야 한다.**
- 구현 완료 기준: API/함수 레이어가 아니라 **production 호출 경로** (`project_pipeline.py`, `agent_launcher.py` 등) 까지 end-to-end로 파라미터가 흘러들어가는지 반드시 확인
- 테스트 픽스처만 통과하는 구현은 미완료 — 테스트가 직접 파라미터를 주입하는 방식이라면 production caller도 동일하게 주입하는지 추가로 grep 확인
- 확인 방법: `grep -rn "함수명\|클래스명"` 으로 production caller를 찾고, 새 파라미터가 전달되는지 검증
- 예외: 사용자가 **명시적으로** "개발 환경 전용" 또는 "추후 연결"을 지시한 경우에만 미연결 허용

### 세션 연속성 규칙 (2026-04-23 추가)
- **세션 시작 시**: `NEXT_STEPS.md`를 먼저 읽어 현재 진행 중인 작업과 우선순위를 파악한다
- **작업 완료 또는 세션 종료 전**: `NEXT_STEPS.md` 상태 업데이트 → `git commit` → `git push` → `python end_db.py agent-factory` (메모리 Supabase 동기화)
- **다른 PC에서 재개 시**: `git pull` → `python start_db.py agent-factory` (Supabase → 로컬 메모리 pull)
- Claude Code 메모리(`memory/`)는 PC별 로컬 저장 — `sync_claude_memory.py`가 Supabase `claude_memory` 테이블을 통해 동기화
- Supabase 미설정 시 `start_db`/`end_db` 실패하지 않고 경고만 출력하고 진행

### Dogfood Run PC 핸드오프 규칙 (2026-05-27 추가)
- **dogfood run의 worktree·state·dogfood_commit은 `~/.af-dogfood/<run_id>/`에 PC-로컬 저장** — git/Supabase 동기화 대상 아님. PC 이동 시 그 PC를 떠나면 회수 불가.
- **세션 종료 전 진행 중인 dogfood run은 둘 중 하나로 처리 의무**:
  1. **머지까지 완료**: `python agent_launcher.py dogfood merge <run_id>` → `git push` (권장)
  2. **명시 보류**: NEXT_STEPS.md에 `보류 dogfood run: <run_id>`, `발생 PC: $(hostname)`, `worktree 경로: ~/.af-dogfood/<run_id>/worktree` 3줄 기록. 다른 PC 재개 시 회수 불가는 사용자가 사전 인지.
- 미완료 머지 + PC 식별자 기록 누락 = 해당 라운드 산출물 회수 불가능 (Windows R1 11차 `1779867851-3611529e`가 그 사례).

### Master_Blueprint.md 참조 의무
- **코드 수정 전**: `Master_Blueprint.md`의 해당 §섹션을 먼저 읽어 의존성과 영향 범위를 파악한다
- **코드 수정 후**: 변경된 파일에 해당하는 섹션(§0~§11)과 §12 변경 이력을 **같은 커밋**에서 업데이트한다
- 전체 코드를 다시 읽지 않는다. Blueprint가 최신이면 Blueprint만으로 판단한다

### Blueprint 업데이트 트리거
| 이벤트 | 업데이트 대상 |
|--------|-------------|
| 새 `.py` 파일 생성 | §0 빠른 참조 테이블 |
| 클래스·메서드 변경 | §3 해당 서브시스템 + `last_updated` |
| 새 버그 수정 | §11 에러 코드 해설, §12 이력 |
| 배포(버전 bump) | §8 빌드, §12 이력 |
| 의존성 변경 | §10 Blast Radius 테이블 |

### 버전 및 빌드
- 버전 파일: `version.py` (`__version__`)
- 설치 스크립트: `install-af.ps1` (버전 문자열 3곳 동시 수정)
- 빌드: `python build_exe.py` → `dist/af-{version}.zip`
- 새 `core/*.py` 파일은 `af.spec` `hiddenimports`에 반드시 추가

### 문서 파일명 규칙
- **code-review.md**: 날짜 없음 (살아있는 단일 문서, in-place 갱신)
- **기타 모든 문서**: 파일명에 날짜 포함 필수 — `YYYY-MM-DD-제목.md`
  - 예: `2026-04-03-cross-cli-skill-discovery.md`
  - Feature 문서, 버그픽스 문서, 설계 문서, 플랜 등 전부 해당

### ADR 명명 규칙 (M2, 2026-05-13 추가)
- **저장 위치**: `docs/decisions/`
- **파일명**: `ADR-YYYYMMDD-HHMMSS-<slug>.md` (초 단위 — 야간 파이프라인 동시 생성 충돌 방지)
  - 예: `ADR-20260513-225000-domain-gate-verdict-parser.md`
- **Git workflow**: feature 브랜치에서 직접 commit. 별도 PR 불필요. ADR은 결정 기록이므로 동일 작업 커밋에 포함.
- **Status 필드**: `Draft` → `Accepted` → `Superseded` / `Resolved` 순서로 갱신

### 스킬 흡수 귀속 정책 (M4, 2026-05-13 추가)
- **외부 소스 흡수 시**: SKILL.md 파일 상단 프론트매터에 `inspired_by:` 메타 필드 추가
  - 형식: `inspired_by: <출처-패키지>/<스킬-ID>` (예: `superpowers/brainstorming`)
  - MIT 라이선스 기반 흡수 시 본 메타로 attribution 의무 이행
- **AF 자체 스킬**: `inspired_by:` 필드 없음 (생략)

### 교차검증 자동 실행
- UserPromptSubmit hook이 `[af-review-pending]` 메시지를 출력하면, **메시지의 `실행 에이전트:` 라인에 명시된 에이전트만** 실행한다 (Phase 0 — Tier 1은 af-test-runner 1개, Tier 2~3은 3-tier 순서)
  - 에이전트 이름 뒤에 `[model=X]` 접미사가 있으면 Agent tool의 `model:` 파라미터에 해당 값을 전달한다 (P4.5b 사전강제: 이전 라운드 escalation 적용)
- UserPromptSubmit hook이 `[af-design-review-pending]` 메시지를 출력하면, **반드시** af-cross-review **1개만** 실행한다 (설계문서 큐 자동 발화, scripts/check_design_pending.py)
- **단일 설계문서** (docs/YYYY-MM-DD-*.md) 작성 후에는 **af-cross-review만** 실행한다 (2026-05-01 변경: af-critic은 설계문서에서 소스 중복 탐색 비용만 발생, 효과 없음)
- **Work-item 문서 세트** (docs/work-items/<slug>/ 4개 문서) 작성·수정 후에는 af-doc-qa + af-cross-review **2개를 병렬 실행**한다
- 교차검증 결과에서 **BLOCK 판정 시에만** 발견 사항을 수정한다. **WARN은 advisory** — 자동 수정 의무 없음 (Phase 0 정책, 2026-04-30: 무한루프 방지)
- **Tier 3(af-cross-review)는 가용 외부 CLI 프로바이더 전부에 병렬 fan-out한다.** 외부 프로바이더 0개면 자동 SKIP(통과 간주), 1개 이상 인증 만료가 있으면 BLOCK + 재인증 안내. (`core/provider_detect.py` Step 0 감지)

### Review-Gate 규칙 (Phase 0 갱신 2026-05-13)
- `.py` 파일 수정 후 `git commit` 전 필수 tier 완주:
  - **Tier 1 파일** (docs/, README, 단순 설정): af-test-runner만
  - **Tier 2~3 파일** (core/, scripts/, 일반 코드): **af-critic → af-cross-review → af-test-runner** 순서 (review-first pattern)
  - 분류는 `scripts/blast_radius.py`가 결정 (`subprocess`, `shell=True`, hook launcher 등은 자동 Tier 3)
- **max_rounds=5 캡** (코드 수정) — 같은 큐는 최대 5라운드까지만 자동 발화. 이후엔 사용자가 수동 결정 (재리뷰 vs 우회)
- **설계문서는 사용자 안내** — BLOCK 반복 시 무조건 사용자에게 안내 (자동 고정 금지, 의사결정 필요)
- **WARN-only no-fire** — 직전 라운드가 BLOCK 없이 완료됐다면 (전부 WARN/PASS) 재편집해도 자동 재발화 안 함
- **게이트 우회** (긴급·부트스트랩 시): `AF_SKIP_REVIEW_GATE=1 git commit ...` (hook_events.log에 기록)
- `.py` 없는 커밋(문서·설정만)은 게이트 자동 통과
- 진단: `python3 scripts/review_gate.py --debug`

### Agent Model Routing — Defaults + Escalation Triggers (P4.5a, 2026-05-15 추가)

**Default model** (agent frontmatter `model:` 필드 기준):

| Agent | Default | 역할 |
|-------|---------|------|
| af-test-runner | haiku | Tier 1 QA executor (Bash + 테스트 실행) |
| af-critic | sonnet | Tier 2 코드 비평 (버그 검출) |
| af-cross-review | sonnet | Tier 3 orchestrator (Codex 호출) |
| af-doc-qa | sonnet | 문서 정합성 검증 |

**Escalation triggers** (spawn 시점에 `model:` override로 강제):

| Default | Escalate to | Trigger 조건 |
|---------|-------------|-------------|
| af-test-runner (haiku) | sonnet | test_failure / flaky_or_timeout / import_path_issue / subprocess_or_os_branching / packaging_or_frozen_build |
| af-critic (sonnet) | opus | core_policy_change / approval_gate_change / security_or_destructive_action / cross_platform_subprocess |
| af-doc-qa (sonnet) | haiku (down) | 단순 doc-lint 전용 (link/section/checklist) |
| af-cross-review | (no escalation) | orchestrator 역할 — Sonnet 충분 |

**현재 상태 (P4.5a)**: 정적 default만 frontmatter에 적용됨. **Runtime escalation 강제는 P4.5b에서 구현** (`select_model()` 헬퍼 + review_gate/hook 연결 + 테스트). 그 전까지 escalation은 spawn 주체가 `model:` 매개변수로 명시 override해야 함.

**근거 ADR**: `docs/decisions/ADR-20260515-114000-agent-model-routing-defaults-escalation.md`

### 커밋 규칙
- 코드 수정 + Blueprint 업데이트는 같은 커밋
- 빌드 zip은 **GitHub Release로 배포**: `gh release create af-fsa_v{version} dist/af-{version}.zip --notes ...` (2026-04-14 정책 변경: LFS 미구성 환경에서 ~91MB zip이 GitHub 100MB 한계로 push 실패한 사례 이후. `dist/*.zip`은 `.gitignore` 처리)
- 태그 형식: `af-fsa_v{version}`

## Hook 설치 (레포 클론 후 1회)

```bash
git config core.hooksPath .githooks
```

이후 `core/*.py` 등 변경 커밋 시 `Master_Blueprint.md` 미스테이지 → 자동 차단.

## 프로젝트 개요
- **위치**: `C:\Project\agent-factory`
- **퍼블릭 레포**: `origin` = `https://github.com/hoonkim1092-web/af-fsa.git`
- **소스 레포**: `agent-factory` remote = `https://github.com/hoonkim1092-web/agent-factory.git`
- **현재 브랜치**: `2026-04-01-super-harness`
- **아키텍처 문서**: `Master_Blueprint.md` (845줄, 12섹션)
