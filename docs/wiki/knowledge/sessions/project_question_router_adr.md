---
name: project-question-router-adr
description: Question Router Stage 0 — P1 구현 완료 (2026-05-14). ADR Accepted. 5개 신규 모듈 + approve_gate 시그니처 변경 + work_item_generator Stage 0 삽입. 다음: P2 Brainstorming YAML + P4 GoalClarification YAML + P5 DomainVerdict 매트릭스.
metadata: 
  node_type: memory
  type: project
  originSessionId: 562c2c4a-b971-4e1d-86c5-cc059c138053
---

# Question Router Stage 0 v4 (2026-05-14)

**Why**: AF 파이프라인이 brainstorming을 템플릿만 복사하고 실행 안 함. work_kind 분류가 Stage 흐름에 반영 안 됨. "자율 vs 사용자 질문" 이분법 — 중간 지대 없음.

**How to apply**: 새 세션 재개 시 본 메모리 먼저 읽기. 현재 상태 = v4 freeze, 라운드 3 design review hook 자동 발화 대기. BLOCK 0건 → ADR Accepted → P1 구현. BLOCK 1건+ → 사용자 결정 (3-round cap).

## 합의 결과 (Opus 4.7 + Sonnet 4.6 + Codex 다라운드)

### 핵심 결정

Stage 0 도입. Question Router를 핵심 abstraction으로. 시나리오 분기:
- `new_project` → Goal Clarification QR → project-goal.md
- `maintenance/bugfix/feature_update/refactor` → Light Context Scan → context-scan.md
- 양쪽 → Brainstorming QR → domain-review.md + DomainVerdict
- → approval_gate 정책 매트릭스 → Stage 1~3 (기존, 무손상)

### 3개 enum 단일 원천 (절대 양보 X)

- `QuestionRoute` ∈ {PASS, LLM_DELEGATE, HITL, BLOCK}
- `DomainVerdict` ∈ {PASS, NEEDS_ADR, BLOCK}
- `BlockCause` ∈ {MISSING_REQUIRED_INPUT, DESIGN_CONFLICT, HIGH_RISK, POLICY_VIOLATION, SAFETY}

### 18개 비양보 항목

ADR 파일에 전부 명시: `docs/decisions/ADR-20260514-133054-question-router-stage0.md`

핵심:
- ① 3개 enum 분리 + ② 로그 타입명도 분리
- ③ 기존 Stage 1~3/af-runner/af-test-runner 무손상
- ④ HITL batch (즉시 pause 금지)
- ⑤ Router(분류) vs Gate(결정) SRP — Router side effect 금지
- ⑭ routing policy metadata 4개만: required/fallback/default_route/block_category_if_missing (risk/failure_policy/escalation_policy 금지)
- ⑮ schema_version 필수
- ⑰ schema_hash SHA-256 필수 (drift 1차 판정)
- ⑱ question.id immutable (rename 금지, id+output_field 페어 immutable)

## 완료된 산출물 (v4)

- `docs/decisions/ADR-20260514-133054-question-router-stage0.md` (304줄) — v2 정정 (blast_radius 4-token)
- `docs/2026-05-14-question-router-detailed-design.md` (1272줄, v4) — Codex 라운드 1~5 BLOCK 전부 흡수 + §18 changelog

## v3 → v4 흡수 항목 (Codex 라운드 5 합의)

| # | 항목 | v4 해결 |
|---|------|---------|
| 1 | gate.initialize() 시그니처 변경 명시 | §8.3에 before/after 코드 + status/execution_open 파라미터 backward-compatible 추가 |
| 2 | paused_hitl 시 approval-gate.md 생성 시점 모순 | A안 채택 — paused 분기에서 gate.initialize(paused mode) 1회 호출 (§3.1, §9.1) |
| 3 | "unknown work_kind" 명명 부정확 | "empty/non-enum compatibility guard"로 정확 명명 + 보호 대상 3가지 (§3.2) |
| 4 | §7 추측성 필드 (platform/existing_tests/research_scope) | platform 제거, existing_tests/research_scope는 Stage 1 only + `_exec_stage1():908` 변경 지점 명시 |
| 5 | §14 P5 migration table 약화 | test action table + 신규 test 7건 명시 |
| 6 | Cross-YAML id 격리 미정의 (silent corruption 위험) | A안 + ledger provenance — StageRouter 시작 시 모든 active YAML 로드 + cross-yaml uniqueness hard fail (§5.2.1) |
| 7 | resume 시 어느 set 출처 추적 불가 | AssumptionLedgerEntry/PausedHitlArtifact/DomainReviewArtifact에 question_set_id provenance 필드 추가 |

§15 OQ5: Composite QuestionRef 마이그레이션 trigger 명시 (active set ≥3 + 정당한 id 재사용 use case + breaking change 비용 허용).

## 변경 history

- **v1**: ADR Draft 초안 (Codex BLOCK 9건)
- **v2**: 9건 흡수 (blast_radius 4-token, schema_hash 자기참조 제거 등)
- **v3**: Codex 재설계 (Scope 한정 + sentinel + atomic write)
- **v4**: 라운드 5 합의 7건 흡수 (현 freeze 상태)

## 구현 현황 (2026-05-14)

### P1 완료 ✅
- `core/control/verdicts.py`, `stage_artifacts.py`, `question_router.py`, `context_scanner.py`, `stage_router.py` 신규
- `core/approval_gate.py:initialize()` status/execution_open 파라미터 추가 (backward-compatible)
- `core/work_item_generator.py` Stage 0 삽입 (_copy_extra_templates() 직후)
- `tests/test_stage0_question_router.py` 33개 신규 + 기존 25 회귀 없음

### 다음 단계
- **P4**: `core/control/questions/goal_clarification.yaml` — GoalClarification QR YAML
- **P2**: `core/control/questions/brainstorming.yaml` — Brainstorming QR YAML
- **P5**: ApprovalGate DomainVerdict 매트릭스 적용 (NEEDS_ADR × 4 blast_radius 테스트 7건)
- **P6a**: RunLedger assumption/paused_hitl/schema_drift 이벤트 추가

## 참조

- ADR: `docs/decisions/ADR-20260514-133054-question-router-stage0.md`
- 영향 코드: `core/work_item_generator.py:1072,1094,1397`, `core/control/work_kind.py:9`, `core/approval_gate.py`
- 관련 정책: CLAUDE.md §ADR 명명, §교차검증, §스킬흡수귀속정책
- 흡수 출처: superpowers/brainstorming (inspired_by)
- Open Questions: TOTAL_BUDGET 확장(600s→750~800s), BlockCause 4 vs 5개 통합, schema_hash normalized vs raw

## 양보 가능 3가지

- BlockCause 5개 → 4개로 시작 가능 (policy_violation + safety 통합)
- Question schema versioning migration tooling은 P6b 이후
- Assumption confidence 등급은 MVP 동급
