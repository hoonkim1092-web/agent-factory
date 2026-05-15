# ADR: Agent Model Routing — Defaults + Escalation Policy (P4.5a)

- **Status**: Accepted
- **Date**: 2026-05-15
- **Phase**: P4.5a (P4.5b runtime enforcement deferred)
- **Branch**: `af-on-af/round1-hook-fix`

## Context

AF dogfooding Round 3 (2026-05-15) friction 분석에서 모델 사용 패턴의 비효율과 비결정성이 드러남:

1. **비용 비효율**: `af-test-runner`는 거의 Bash + 단순 테스트 실행이지만 Sonnet을 사용 중 → Tier 1 QA에 과한 모델.
2. **비결정성**: `af-cross-review`, `af-doc-qa`는 frontmatter에 `model:` 없이 parent inherit → 호출 시점에 어떤 모델이었는지 기록 불가.
3. **수동 라우팅 한계**: `feedback_model_per_phase.md` 정책("설계 Opus / 구현 Sonnet")이 `/model` 수동 안내에만 의존 → 자동화 부재.

요구: 비용 절감 + 재현성(어떤 모델이 어떤 판단을 했는지 기록 가능) + escalation contract.

## Decision

**2단계 분리 채택**:
- **P4.5a (이 ADR)**: 정적 default + 정책 문서. 코드 변경 없음.
- **P4.5b (다음)**: Runtime escalation 강제 (`select_model()` 헬퍼 + review_gate/hook 연결).

### Default Model (frontmatter)

| Agent | Default | 변경 | 근거 |
|-------|---------|------|------|
| af-test-runner | **haiku** | sonnet → haiku | Bash + 단순 테스트 실행 중심. Debug analyst 역할은 escalation으로 처리. |
| af-critic | sonnet | (유지) | 버그 검출 + 회귀 위험 판단 — reasoning 품질 중요, false negative 비쌈. |
| af-cross-review | **sonnet** | (inherit) → 명시 | Orchestrator 역할 (Codex가 heavy lift) → Sonnet 충분. 재현성 위해 명시. |
| af-doc-qa | **sonnet** | (inherit) → 명시 | 정책-코드 정합성 / Blueprint 일관성 같은 의미론적 검증 — haiku 부족. |

### Escalation Policy

| Agent | Escalate to | Trigger |
|-------|-------------|---------|
| af-test-runner | sonnet | `test_failure`, `flaky_or_timeout`, `import_path_issue`, `subprocess_or_os_branching`, `packaging_or_frozen_build` |
| af-critic | opus | `core_policy_change`, `approval_gate_change`, `security_or_destructive_action`, `cross_platform_subprocess` |
| af-doc-qa | haiku (↓) | 단순 doc-lint 전용 (link/section/checklist 확인) |
| af-cross-review | — | 없음 (orchestrator라 escalation 불필요) |

### 비채택 안

- **Agent 파일 중복 생성** (`af-test-runner-deep.md` 등): Claude Code Agent tool이 spawn 시점 `model:` override 지원 → 중복 불필요. 비채택.
- **P4.5a+P4.5b 동시 진행**: review_gate.py 실행 경로 변경은 dogfooding 브랜치 안정성 흔듦. 검증 포인트 분리를 위해 단계 분할 채택.

## Consequences

**Positive**:
- af-test-runner 비용 ↓ (Haiku token cost <<< Sonnet)
- 재현성 ↑ — 4개 agent 모두 명시적 default model
- Escalation contract 명문화 → 향후 P4.5b 강제 로직의 acceptance criteria 선명함

**Negative / Risks**:
- **Frontmatter defaults are NOT enforced** — Spawn 주체가 escalation 조건 감지 후 `model:` 명시 override해야 함. P4.5b 전까지 manual.
- **드리프트 위험**: 이 ADR의 default와 실제 frontmatter 불일치 가능. 완화책: `af-cross-review` 또는 별도 cross-check 스크립트.
- af-test-runner에서 의도된 escalation을 누락하면 false negative 위험 (예: 복잡한 테스트 실패를 haiku가 얕게 분석).

## Implementation

이번 commit 변경 파일:
- `.claude/agents/af-test-runner.md` — `model: sonnet` → `model: haiku`
- `.claude/agents/af-cross-review.md` — `model: sonnet` 신규 추가
- `.claude/agents/af-doc-qa.md` — `model: sonnet` 신규 추가
- `CLAUDE.md` — 새 섹션 "Agent Model Routing — Defaults + Escalation Triggers"
- `docs/decisions/ADR-20260515-114000-agent-model-routing-defaults-escalation.md` (본 파일)

af-critic은 이미 `model: sonnet`이라 변경 없음.

## Next: P4.5b (Runtime Enforcement)

P4.5b에서 다룰 항목 (별도 ADR 또는 작업 단위):

1. `select_model(agent_name, triggers: List[str]) -> str` 헬퍼 — escalation 매트릭스 코드화
2. Agent spawn 지점 식별 — 현재 어디서 subagent를 호출하는지 grep
3. review_gate.py / hook에 escalation 조건 감지 로직
4. Routing log (어떤 호출이 어떤 모델로 escalate됐는지)
5. 회귀 테스트 — escalation trigger별 unit test

## References

- Memory: `feedback_model_per_phase.md` (Phase-based model preference)
- Memory: `project_dev_workflow_paradigm_shift.md` (Round 1/2/3 dogfooding 컨텍스트)
- Dogfooding: `docs/dogfooding/round3-skill-absorption.md` (Round 3 친화 분석)
- CLAUDE.md L131: "WARN-only no-fire" (related review-gate policy)
