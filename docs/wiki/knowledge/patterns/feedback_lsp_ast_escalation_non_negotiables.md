---
name: feedback-lsp-ast-escalation-non-negotiables
description: "oh-my-openagent와의 비교에서 도출된 \"LSP/AST as escalation tools\" 합의안에 대한 5가지 양보 불가 원칙. AF가 코딩 하네스가 아니라 delivery contract layer라는 층위 인식이 핵심."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0ae236d2-7985-470b-a3db-0bc698fa0dd7
---

# LSP/AST escalation 합의안 양보 불가 5건 (2026-05-14)

**Why**: 사용자가 oh-my-openagent와의 비교에서 "AF가 코딩 하네스 관점에서 뒤져 있다 → LSP/AST를 1급 agent tool로 흡수해야 한다"는 합의안을 제시. 깊게 분석해본 결과 합의안 프레임 자체가 AF 아키텍처와 불일치. 표면 동조 거부.

**How to apply**: LSP/AST 도입 논의가 재개될 때 본 메모리 먼저 읽고, 5가지 비양보 항목을 그대로 적용한다. 사용자가 합의안을 약화·삭제 요청하면 명시적 지시 필요 (단순 "진행해"로는 합의안 통과 금지).

## 1. "agent tool" 프레임 거부 (가장 근본)

**근거**: AF는 자체 agent 없음. `core/provider_detect.py`로 외부 CLI(`claude_cli`, `codex_cli`, `gemini_cli`) 감지 후 fan-out. `agent_launcher.py:82 AgentFactory` 클래스는 CLI 런처일 뿐 agent 아님.

**결론**: AF가 LSP/AST를 추가해도 Claude/Codex CLI는 자기 내부 grep을 쓴다 (CLI 내부 결정). "1급 agent tool 노출"은 AF에 무의미. LSP/AST를 추가하려면 **approval_gate 후속 검증 단계**로만.

## 2. 비교 프레임 거부 — AF는 코딩 하네스가 아니다

**근거**: [[project-saas-strategy-position]] — "AI Software Delivery OS (Claude/Codex 대체 아님)". `core/approval_gate.py` 게이트 계약 + `core/work_item_generator.py` Stage 0~3 산출물 계약이 AF의 product surface.

**결론**: oh-my-openagent는 코딩 하네스, AF는 그 위 layer. 같은 평면 경쟁은 곧 패배. AF는 oh-my-openagent를 **하부 provider로 흡수** 가능 (`provider_detect`에 `oh_my_openagent_cli` 추가).

## 3. 신규 trigger 분류 차원 거부

**근거**: AF에 이미 두 가지 분류 taxonomy 존재 — `core/control/work_kind.py:9 ISSUE_KIND_MAP` (5종) + `scripts/blast_radius.py` (4-token). 합의안 trigger 8개(rename/refactor/public API/cross_module/system_wide/import graph/large-scale/symbol references)는 카테고리 혼합.

**결론**: trigger 도입 시 기존 taxonomy 조합만 사용:
```
trigger = (work_kind == "refactor") OR (blast_radius in {cross_module, system_wide})
```
"rename detection", "import graph changes" 등 신규 분류 차원 거부.

## 4. 실증 없는 추측 거부 (Karpathy 1번 원칙)

**근거**: AF의 commit log·NEXT_STEPS·project_session 메모리 어디에도 "grep rename으로 production 문자열 충돌" 사례 0건. [[project-research-system-gaps]] 5개 결함 중 rename/AST 관련 0건.

**결론**: LSP/AST 도입 ADR 작성 권한 = **실측 실패 사례 ≥3건 수집** 이후. CLAUDE.md "일어날 수 없는 시나리오의 에러 처리 금지" + "과설계 금지" 적용.

## 5. 진행 중 ADR 미완료 상태에서 doglegging 거부

**근거**: 현재 Question Router Stage 0 v4 freeze 상태에서 P1+P2+P4 완료, **P5 (DomainVerdict 매트릭스) 미구현**, **P6a (RunLedger 이벤트) 미구현**, Request Harness 후속 설계 미착수.

**결론**: P5 + P6a + Request Harness ADR 완료 전 LSP/AST 논의는 OPEN QUESTION으로만 유지. ADR 슬롯 예약 가능, draft 작성 금지.

## 결합 — 수정된 합의안 (현 메모리 기점)

| 원안 | 수정안 |
|------|--------|
| LSP/AST as agent tool | LSP/AST as approval_gate 후속 검증 단계 |
| 신규 trigger 카테고리 | work_kind + blast_radius 조합만 |
| 즉시 도입 가능 | 실측 실패 ≥3건 수집 후 |
| 도입 시점 자유 | Stage 0 + Request Harness ADR 완료 후 |
| 언어 미정 | Python-only 1차, 다중 언어 별도 ADR |

## 관련

- [[code/symbols]]
- [[project-question-router-adr]] — 진행 중 ADR (Stage 0 v4)
- [[project-saas-strategy-position]] — AF SaaS 포지셔닝
- [[feedback-tier3-no-sycophancy]] — 동조 금지 원칙 (본 분석의 메타 토대)
- [[project-research-system-gaps]] — 실측 결함 카탈로그 (rename/AST 0건 근거)
