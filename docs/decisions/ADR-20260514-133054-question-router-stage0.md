---
id: ADR-20260514-133054-question-router-stage0
title: Question Router 기반 Stage 0 도입
status: Draft
date: 2026-05-14
authors: hoonkim (Opus 4.7) + codex (cross-vendor consensus)
related: M2 (ADR 명명 규칙), Phase A Domain Gate, [[project_saas_strategy_position]]
---

# ADR-20260514-133054 — Question Router 기반 Stage 0 도입

## 1. Context (배경)

### 1.1 현재 파이프라인의 결함

`core/work_item_generator.py:1072` `generate_work_items()` 는 work_kind/blast_radius 분류 결과를 **소비하지 않고** Stage 1~3을 단일 경로로 흐른다:

```
generate_work_items()
  ├── _copy_extra_templates()   ← domain-review.md "템플릿만" 복사
  ├── Stage 1 plan (90s)        ← 곧바로 deep research
  ├── Stage 2 spec+design (400s)
  └── Stage 3 tasks (110s)
```

문제 3가지:

1. **brainstorming 미실행** — `domain-review.md`는 템플릿만 복사되고 실제 Socratic 질문은 사람이 나중에 채워야 함. Stage 1이 이미 plan을 만든 뒤에 brainstorming → 환상에 가까운 도메인 검증.
2. **시나리오 미분기** — `new_project` vs `maintenance/bugfix/feature_update/refactor` 가 동일 Stage 흐름을 탐. 새 프로젝트엔 context scan 대상이 없고, 기존 프로젝트엔 goal clarification이 불필요.
3. **자율성 vs 게이트 이분법** — 모든 질문을 사용자에게 묻거나(자율성 0), 모두 LLM에 맡기거나(게이트 0). 중간 지대 없음.

### 1.2 합의 형성 과정

Sonnet 4.6 + Opus 4.7 + Codex 다라운드 deliberation. 사용자 통찰 → Codex 4개 수정점 → 본 ADR 작성 시점까지 **18개 비양보 항목** + **3개 양보 가능** + **모서리 3개** 합의 도달.

---

## 2. Decision (결정)

**Stage 0 를 도입한다. Stage 0의 핵심 abstraction은 Question Router 다.**

### 2.1 시나리오 분기 (work_kind 기반)

```
IntentGate → WorkKindClassifier → Stage Router
                                       │
              ┌────────────────────────┴────────────────────────┐
              ↓                                                 ↓
       work_kind = new_project                  work_kind ∈ {maintenance,
              │                                  bugfix, feature_update, refactor}
              ↓                                                 ↓
       Goal Clarification QR                      Light Context Scan (정적)
       → project-goal.md                           → context-scan.md
              │                                                 │
              └────────────────────────┬────────────────────────┘
                                       ↓
                          Brainstorming QR (공용)
                          → domain-review.md + DomainVerdict
                                       ↓
                          approval_gate (정책 적용)
                                       ↓
                        Stage 1 → Stage 2 → Stage 3 (기존, 무손상)
                                       ↓
                              af-runner → af-test-runner → Report
```

### 2.2 핵심 어휘 (3개 enum, 단일 원천)

```python
# core/control/verdicts.py (신규)

class QuestionRoute(Enum):
    """Question Router가 각 질문에 매기는 처리 방식."""
    PASS = "pass"
    LLM_DELEGATE = "llm_delegate"
    HITL = "hitl"
    BLOCK = "block"

class DomainVerdict(Enum):
    """domain-review.md가 작업 진행 가능성에 매기는 verdict."""
    PASS = "pass"
    NEEDS_ADR = "needs_adr"
    BLOCK = "block"

class BlockCause(Enum):
    """BLOCK 발생 시 원인 (Router/Gate 공유 단일 원천)."""
    MISSING_REQUIRED_INPUT = "missing_required_input"
    DESIGN_CONFLICT = "design_conflict"
    HIGH_RISK = "high_risk"
    POLICY_VIOLATION = "policy_violation"
    SAFETY = "safety"
```

### 2.3 정책 매트릭스 — approval_gate가 단일 경로로 실행

**비고 (v1→v2 정정 2026-05-14)**: blast_radius 유효 토큰은 `isolated|module|cross_module|system_wide` 4개(`core/control/change_impact.py:35,223-243`). `local`/`system`은 invalid token이며 `tests/test_approval_gate_domain_review.py:5-6`이 거부. `security`/`data`는 blast_radius axis가 아니라 BlockCause/risk_level axis. 본 매트릭스는 정정된 4-token 기준.

| DomainVerdict | BlastRadius | 동작 |
|--------------|-------------|------|
| PASS | * | 즉시 진행 |
| NEEDS_ADR | isolated, module | ADR 생성 + WARN + 진행 |
| NEEDS_ADR | cross_module, system_wide | ADR 생성 + pause (사용자 검토 대기) |
| BLOCK (cause=MISSING_REQUIRED_INPUT) | * | HITL clarification batch |
| BLOCK (cause=DESIGN_CONFLICT) | * | ADR 생성 + 검토 대기 |
| BLOCK (cause=HIGH_RISK) | * | ADR 생성 + 검토 대기 |
| BLOCK (cause=POLICY_VIOLATION) | * | abort + 사용자 보고 |
| BLOCK (cause=SAFETY) | * | abort + 사용자 보고 |

**기존 계약 영향**: `tests/test_approval_gate_domain_gate.py:6` 헤더 `F5: blast_radius != system_wide → domain gate skipped` 계약이 본 매트릭스 도입으로 변경된다. **확장이 아닌 semantics 변경**. 상세 설계문서 §7.2에서 migration test plan 명시.

### 2.4 LLM_DELEGATE 실패 fallback 정책

```python
def handle_llm_delegate_failure(question, work_item):
    if question.required and not question.fallback:
        promote_to_hitl(question, reason="llm_delegate_failed")
    elif not question.required and question.fallback:
        use_fallback(question.fallback)
        ledger.append_assumption(...)
    elif not question.required and not question.fallback:
        skip_with_warning(question)
    elif question.required and question.fallback:
        # v2 정정: blast_radius 유효 토큰 4개 (isolated|module|cross_module|system_wide).
        # cross_module + system_wide 이 "high blast" 임계값.
        if work_item.blast_radius in ("cross_module", "system_wide"):
            promote_to_hitl(question)
        else:
            use_fallback(question.fallback)
```

### 2.5 18개 비양보 항목

| # | 항목 |
|---|------|
| ① | QuestionRoute ≠ DomainVerdict ≠ BlockCause 3개 enum 분리 |
| ② | enum + 로그/아티팩트 타입명 분리 (`{"question_route":"pass","domain_verdict":"needs_adr"}`) |
| ③ | 기존 Stage 1~3 / af-runner / af-test-runner 무손상 |
| ④ | HITL batch (즉시 pause 금지, 야간 자율성 보장) |
| ⑤ | Router(분류) vs Gate(결정) SRP — Router는 stop/pause/ADR side effect 금지 |
| ⑥ | LLM 반환 BlockCause는 schema enum allowed value로 검증 |
| ⑦ | YAML 외부화 + schema validation hard fail (pipeline 진입 전 차단) |
| ⑧ | Assumption ledger MVP 기록 의무 (감사 가능성) |
| ⑨ | NEEDS_ADR ≠ PASS, BlastRadius 분기 정책 (위 §2.3 매트릭스, v2: 4-token taxonomy 사용) |
| ⑩ | BlockCause enum 단일 원천 (YAML/LLM/Python code 공유) |
| ⑪ | LLM_DELEGATE 실패 fallback은 required + fallback 메타 기반 (위 §2.4) |
| ⑫ | `paused_hitl` 은 incomplete 상태 — 야간 파이프라인 성공 카운트 금지 |
| ⑬ | HITL 무응답 → `paused_hitl` 마킹 + `report_required=true` (다음 세션 resume) |
| ⑭ | **Question-level routing policy metadata** 는 4개만: `required`, `fallback`, `default_route`, `block_category_if_missing`. risk/failure_policy/escalation_policy 금지 |
| ⑮ | `schema_version` 필드 필수 (YAML + artifact 양쪽) |
| ⑯ | schema drift 시 WARN + ledger 기록 + 사용자 선택, **자동 migration 금지** |
| ⑰ | `schema_hash` (SHA-256 of raw YAML bytes) 필수, **drift 1차 판정 기준** |
| ⑱ | `question.id` immutable — rename 금지 (deprecated 마킹만), `id+output_field` 페어 immutable |

### 2.6 양보 가능 3가지

- BlockCause 5개 → 4개로 시작 가능 (policy_violation/safety 초기 통합 OK)
- Question Schema versioning 거창한 migration은 P6b로 미룸 (단, version + hash 필드 자체는 MVP 필수)
- Assumption confidence 등급화 (MVP 동급)

### 2.7 모서리 3개 (운영 정책)

- **모서리 ⑤**: LLM_DELEGATE 호출 실패 시 question.required + fallback + blast_radius 조합에 따라 HITL 승격 / fallback 사용 / skip
- **모서리 ⑥**: HITL 무응답 → `paused_hitl` 상태 마킹, run_ledger에 `{"event":"paused_hitl","questions":[...]}` append, 다음 사용자 세션 진입 시 resume
- **모서리 ⑦**: schema drift (version 또는 hash 다름) → WARN + ledger + 사용자 선택. paused_hitl resume 중 drift 감지 시 "schema가 바뀌었습니다. 재시작하시겠습니까?" HITL question 신규 생성

---

## 3. Rationale (근거)

### 3.1 Question Router를 핵심 abstraction으로 둔 이유

"전체 자동화 vs 전체 사용자" 이분법은 현실의 결정 다양성을 표현 못 함. `deployment_target` 같은 LLM 추론 가능 질문과 `data_deletion_policy` 같은 사용자 판단 필수 질문이 같은 폼에 있어도 다른 처리가 필요. Router는 이 다양성을 4-verdict로 표현.

### 3.2 용어 분리(QuestionRoute ≠ DomainVerdict ≠ BlockCause)의 절대성

`PASS` 가 두 의미로 쓰이면 로그/디버깅에서 매번 추론 필요. enum 분리만으론 부족하고 **로그 필드명도 분리**해야 함 (Codex #1, 본 ADR ②). abstraction 경계선이 곧 운영 가독성.

### 3.3 schema_hash 도입 이유

`schema_version: 1` 만으론 사람의 bump 누락을 못 잡음. SHA-256 hash가 raw bytes 변경을 100% 감지. 비용 ~30분, 효과는 silent corruption 차단.

### 3.4 question.id immutability

paused_hitl artifact는 `id`를 응답 병합 키로 사용. id rename 또는 output_field 변경 시 silent data corruption 발생 가능. ADR 정책으로 차단.

### 3.5 routing policy metadata를 4개로 제한한 이유

Codex가 제안한 `failure_policy` / `escalation_policy` / `fallback_allowed` / `require_hitl_when` 4개 메타는 모두 `required` / `fallback` / `default_route` / `block_category_if_missing` 4개로 표현 가능 (Codex 자신의 예시 2개로 검증). 신규 메타는 redundant + schema 폭발 + 정책 충돌 위험. Karpathy Simplicity First.

---

## 4. Consequences (영향)

### 4.1 신규 컴포넌트 (6개)

| 컴포넌트 | 위치 (예정) |
|---------|------------|
| Stage Router | `core/control/stage_router.py` |
| Stage Artifact Contract | `core/control/stage_artifacts.py` |
| Question Router | `core/control/question_router.py` |
| Light Context Scanner | `core/control/context_scanner.py` |
| Goal Clarification YAML | `core/control/questions/goal_clarification.yaml` |
| Brainstorming YAML | `core/control/questions/brainstorming.yaml` |
| Verdicts enum | `core/control/verdicts.py` |
| (artifact 4종 schema) | `domain-review.md`, `context-scan.md`, `project-goal.md`, `assumptions.md` |

### 4.2 기존 컴포넌트 변경

| 파일 | 변경 |
|------|------|
| `core/work_item_generator.py:1094` | `_copy_extra_templates()` 호출 직후 Stage Router 진입점 추가. Stage 1~3 호출 시그니처 무변경. |
| `core/approval_gate.py` | DomainVerdict + BlastRadius 매트릭스 적용 (Phase A의 domain-review verdict 소비 로직 확장) |
| `core/control/run_ledger.py` | assumption event + paused_hitl event 추가 |

### 4.3 회귀 보호

- Stage 1~3 + af-runner + af-test-runner 호출 시그니처 무변경
- work_kind 산출 안 되는 레거시 경로는 Stage Router fallback (기존 Stage 1~3 직행)
- E2E 5경로 PASS 의무: new_project / maintenance / HITL batch / BLOCK×3원인 / fallback

### 4.4 예산 영향

- TOTAL_BUDGET 600s → 750~800s 확장 권장 (Stage 0 추가분)
- Light Context Scan: LLM 0회 호출 (정적 분석)
- Goal Clarification QR: 1회 LLM batch (질문 라우팅)
- Brainstorming QR: 1~2회 LLM batch (라우팅 + verdict)

### 4.5 위험

- HITL batch 무응답 시 paused_hitl 상태가 영원히 남을 가능성 → garbage collection 정책은 P6b 이후
- LLM_DELEGATE assumption이 잘못된 가정 누적 시 downstream 회귀 → ledger 검토는 P6a 필수
- YAML schema 외부화 → 비개발자 편집 가능성, validation hard fail로 차단

---

## 5. Implementation Plan (P0~P7)

```
P0  본 ADR + cross-review                                    [현재]
    ↓
P1  Stage Router (work_kind → Stage 시퀀스)
    ↓
P1.5 Stage Artifact Contract (4종 dataclass)
    ↓
P1.6 Question Router Contract (YAML schema + 4 verdict)
    ↓
   ┌──────────┬──────────┐
   ↓          ↓          (병렬 가능)
P3 Light    P4 Goal
Context     Clarification QR
Scan
   │          │
   └──────────┴──────────┐
                          ↓
                         P2 Brainstorming QR
                          ↓
                         P5 approval_gate 정책 연결
                          ↓
                         P6a Assumption Ledger 최소
                          ↓
                         P7 E2E 테스트 (5경로)

[선택, MVP 이후]
P6b CLI 시각화 (af assumptions)
```

각 단계의 상세 산출물/검증 기준은 후속 **상세 설계문서** (`docs/2026-05-14-question-router-detailed-design.md`)에서 정의한다. 본 ADR은 정책과 결정에 한정.

---

## 6. Open Questions

본 ADR 작성 시점에 미해결로 남기는 항목 (양보 가능 § 2.6 외):

- **OQ1**: Stage 0 추가로 TOTAL_BUDGET 확장 시 야간 자율 파이프라인 cron 주기 조정 필요? → 상세 설계문서에서 결정
- **OQ2**: BlockCause 5개 → 4개 통합 결정 (`policy_violation` + `safety`) → 상세 설계문서에서 결정
- **OQ3**: schema_hash 계산 시 normalized YAML (정렬/주석 제거) vs raw bytes → 현재 결정: raw bytes (Codex 합의). 후속 false positive 빈도 측정 후 재검토.

---

## 7. References

- 합의 history: 2026-05-14 다라운드 deliberation (Opus 4.7 + Sonnet 4.6 + Codex)
- 선행 결정: ADR M1~M5 (Phase A Domain Gate)
- 정책 참조: `CLAUDE.md` §ADR 명명 규칙, §스킬흡수귀속정책, §교차검증 자동 실행
- 흡수 출처: superpowers/brainstorming (MIT, inspired_by)
- 영향 코드:
  - `core/work_item_generator.py:1072` `generate_work_items()`
  - `core/work_item_generator.py:1397` `_copy_extra_templates()`
  - `core/control/work_kind.py:9` `_WORK_KIND_PRIORITY`
  - `core/approval_gate.py` Domain Gate verdict 소비

---

## 8. Status & Next Step

- **Status**: Draft (v2 in progress, 2026-05-14)
- **v1→v2 정정 사항**:
  - §2.3 매트릭스: blast_radius 토큰 `local|...|security|data` → `isolated|module|cross_module|system_wide` 정정
  - §2.4 fallback 정책: "high blast" 기준 = `cross_module|system_wide` (security/data 제거)
  - §2.5 ⑨: 4-token taxonomy 사용 명시
  - 그 외 7건 (schema_hash 자기참조, paused_hitl 반환 계약, Router SRP, resume 진입점, ApprovalGate semantics migration, LLMCaller 어댑터, af.spec hiddenimports, atomic write)은 상세 설계문서 v2에서 처리
- **다음 단계**: 설계문서 v2 freeze → af-cross-review 재발화
- **Cross-review 통과 후**: Status → Accepted, P1 구현 진입
