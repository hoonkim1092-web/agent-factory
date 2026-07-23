# Agent Factory — Claude Code 지시사항

<!-- AF-COMMON-START (generated from INSTRUCTIONS.md — DO NOT EDIT between markers) -->
<!-- 이 파일이 공통 실무 규칙의 SSOT입니다. 편집 후 scripts/sync_provider_instructions.py 또는 pre-commit이 CLAUDE/AGENTS/GEMINI에 전파합니다. -->

# 공통 코딩 지침

> 단순성 우선, 수술적 변경, 목표 기반 검증 원칙은 [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)에서 영감을 받았다.

## 1. 구현 전 판단

- 구현 전에 요청 범위, 필요한 가정, 성공 기준을 확인한다.
- 결과나 부작용이 의미 있게 달라지는 모호성이 있으면 사용자에게 질문한다.
- 저위험이고 쉽게 되돌릴 수 있는 사소한 모호성은 가장 단순한 해석을 명시하고 진행한다.
- 중요한 해석이 여러 개라면 선택지와 트레이드오프를 짧게 제시한다.
- 더 단순한 방법이 있으면 알리고, 과도하거나 위험한 요구에는 근거를 들어 이의를 제기한다.
- 내부 추론을 장황하게 출력하지 말고 가정, 결정, 검증 계획만 필요한 만큼 제시한다.

## 2. 단순성 우선

- 요청을 충족하는 최소한의 코드를 작성한다.
- 요청하지 않은 기능, 추측성 확장성, 설정 가능성, 추상화를 추가하지 않는다.
- 일회성 구현을 위해 불필요한 프레임워크나 계층을 만들지 않는다.
- 같은 명확성, 안정성, 테스트 가능성을 유지하면서 더 단순하게 구현할 수 있다면 단순한 방식을 선택한다.
- 외부 입력, 파일 I/O, 네트워크, subprocess, 데이터 손실 경계의 현실적인 실패는 처리하되 추측성 방어 코드는 추가하지 않는다.

## 3. 수술적 변경

- 사용자 요청에 필요한 부분만 수정한다.
- 기존 코드 스타일과 구조를 존중한다.
- 관련 없는 리팩터링, 포맷 변경, 이름 변경, 주석 수정, 죽은 코드 삭제를 하지 않는다.
- 이번 변경으로 새롭게 미사용 상태가 된 import, 변수, 함수만 정리한다.
- 기존부터 존재하던 별도 문제는 임의로 수정하지 말고 필요하면 보고한다.
- 변경된 모든 줄은 사용자 요청 또는 그 검증에 직접 연결되어야 한다.

## 4. 목표 기반 실행과 검증

- 작업을 검증 가능한 성공 기준으로 변환한다.
- 다단계 작업은 다음 형식의 짧은 계획을 사용한다.

  1. `[작업]` → 검증: `[방법]`
  2. `[작업]` → 검증: `[방법]`

- 재현 가능한 버그는 가능하면 실패하는 회귀 테스트를 먼저 작성한다.
- 자동 테스트 작성이 비현실적이면 최소 재현 명령, 로그 또는 수동 검증 절차를 먼저 확립한다.
- 변경 후 관련 테스트, 타입 검사, 린트, 빌드 또는 실제 실행을 수행한다.
- 테스트 픽스처나 단위 함수만 확인하지 말고 실제 사용자가 거치는 호출 경로까지 연결되었는지 확인한다.
- 검증하지 못한 결과를 성공으로 보고하지 않는다.
- 외부 요인으로 검증할 수 없다면 차단 요인과 미검증 범위를 명시한다.

## 5. 타입 SSOT

- dataclass, TypedDict, Protocol 등 공유 타입은 하나의 원천 파일에서만 선언한다.
- 동일한 타입을 다른 파일에 복사하거나 재선언하지 않고 원천 파일에서 import한다.
- 기존 중복 타입을 발견해도 현재 요청과 무관하면 임의로 정리하지 않는다.
- 프로젝트에 기존 예외 목록이나 호환성 정책이 있다면 이를 따르며, 새 예외는 사용자 승인 없이 추가하지 않는다.

## 6. 경로 이식성

- 사용자나 머신에 종속된 절대경로를 코드에 하드코딩하지 않는다.
- 프로젝트 루트, 현재 파일 위치, 환경변수, 설정값 또는 함수 파라미터로 경로를 구성한다.
- 경로 결합에는 해당 언어의 표준 경로 API를 사용한다.
- 테스트 데이터의 의도적인 플랫폼별 경로 문자열은 실제 파일 접근 코드와 구분한다.

## 7. 멀티 OS

- 공통 기능은 Windows, macOS, Linux에서 동일한 사용자 결과를 제공하는 것을 기본 목표로 한다.
- 셸, 경로 구분자, 인코딩, 권한, 시그널 등 OS별 동작을 무조건 같다고 가정하지 않는다.
- OS 고유 기능은 명시적인 어댑터 또는 capability detection 뒤에 격리한다.
- 특정 OS에서 지원할 수 없는 기능은 명확한 오류나 대체 경로를 제공한다.
- 변경과 관련된 플랫폼별 테스트가 있다면 실행하고, 실행하지 못한 플랫폼은 명시한다.

## 8. 멀티 프로바이더와 모델

- 핵심 동작 계약과 성공 기준은 특정 LLM 프로바이더나 모델에 종속시키지 않는다.
- Claude, Codex, Gemini 등 모델별 출력 형식과 capability 차이는 어댑터 계층에서 처리한다.
- 특정 모델의 비공개 프롬프트 형식, 도구 이름 또는 응답 습관에 핵심 로직을 의존시키지 않는다.
- 필요한 capability가 없는 모델에서는 조용히 잘못 동작하지 말고 명확한 제한이나 대체 경로를 제공한다.

## 9. Git과 외부 반영

- 사용자가 요청하지 않은 commit, push, release, 배포를 자동으로 수행하지 않는다.
- commit이나 원격 반영이 작업 범위에 포함되었는지 확인한다.
- 다른 사람이 만든 기존 변경을 임의로 되돌리거나 commit에 섞지 않는다.
- commit 전 diff와 검증 결과를 확인한다.
- 프로젝트별 review gate, 문서 동기화, 브랜치 및 release 정책은 해당 프로젝트의 로컬 지침을 따른다.

## 10. 프로젝트별 규칙과의 관계

- 이 문서는 모든 프로젝트에 적용되는 공통 원칙만 정의한다.
- 빌드 명령, 테스트 경로, 브랜치, 문서 구조, 배포 절차, 저장소 경로 등 프로젝트 고유 정보는 각 프로젝트의 로컬 지침에 둔다.
- 공통 규칙과 프로젝트 규칙이 충돌하면 사용자 요청과 더 구체적인 프로젝트 규칙을 우선한다.
- 단, 안전, 보안, 데이터 손실 위험이 있으면 실행 전에 사용자에게 확인한다.
<!-- AF-COMMON-END -->

### 교차검증 자동 실행
- UserPromptSubmit hook이 `[af-review-pending]` 메시지를 출력하면, **메시지의 `실행 에이전트:` 라인에 명시된 에이전트만** 실행한다 (Phase 0 — Tier 1은 af-test-runner 1개, Tier 2~3은 3-tier 순서)
  - 에이전트 이름 뒤에 `[model=X]` 접미사가 있으면 Agent tool의 `model:` 파라미터에 해당 값을 전달한다 (P4.5b 사전강제: 이전 라운드 escalation 적용)
- UserPromptSubmit hook이 `[af-design-review-pending]` 메시지를 출력하면, **반드시** af-cross-review **1개만** 실행한다 (설계문서 큐 자동 발화, scripts/check_design_pending.py)
- **단일 설계문서** (docs/YYYY-MM-DD-*.md) 작성 후에는 **af-cross-review만** 실행한다 (2026-05-01 변경: af-critic은 설계문서에서 소스 중복 탐색 비용만 발생, 효과 없음)
- **Work-item 문서 세트** (docs/work-items/<slug>/ 4개 문서) 작성·수정 후에는 af-doc-qa + af-cross-review **2개를 병렬 실행**한다
- 교차검증 결과에서 **BLOCK 판정 시에만** 발견 사항을 수정한다. **WARN은 advisory** — 자동 수정 의무 없음 (Phase 0 정책, 2026-04-30: 무한루프 방지)
- **Tier 3(af-cross-review)는 가용 외부 CLI 프로바이더 전부에 병렬 fan-out한다.** 외부 프로바이더 0개면 자동 SKIP(통과 간주), 1개 이상 인증 만료가 있으면 BLOCK + 재인증 안내. (`core/provider_detect.py` Step 0 감지)

### Review-Gate 에이전트 순서 (Claude Code 전용)
- **Tier 2~3 파일**: **af-critic → af-cross-review → af-test-runner** 순서 (review-first pattern)
- **설계문서는 사용자 안내** — BLOCK 반복 시 무조건 사용자에게 안내 (자동 고정 금지, 의사결정 필요)
- **WARN-only no-fire** — 직전 라운드가 BLOCK 없이 완료됐다면 (전부 WARN/PASS) 재편집해도 자동 재발화 안 함

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

## Hook 설치 (레포 클론 후 1회)

```bash
git config core.hooksPath .githooks
```

이후 `core/*.py` 등 변경 커밋 시 `Master_Blueprint.md` 미스테이지 → 자동 차단.
