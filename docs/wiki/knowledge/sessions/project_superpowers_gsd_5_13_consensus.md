---
name: project-superpowers-gsd-5-13-consensus
description: 5/13 Superpowers/GSD 흡수 워크플로우에 대한 cross-vendor 합의 완료 (4/4 동의). Step A-1 진입 전 결정 2건 대기 중.
metadata: 
  node_type: memory
  type: project
  originSessionId: 6d52b453-3738-4b27-ac90-0d1572699fb1
---

`docs/codex/2026-05-13-superpowers-gsd-quality-workflow-analysis.md`에 대한 Claude + Codex 독립 file:line 검증 합의 완료 (2026-05-13).

**Why**: Superpowers 11개 스킬을 그대로 import하지 말고 AF-native SKILL/template/gate로 패턴만 흡수하기 위함. 5/11 Domain Gate 설계(BLOCK 11건)와 5/13 분석문서(BLOCK 10건)의 후속.

**합의된 4개 결정**:
1. Step 1-2 순서 역전 — 5/11 Critical 2건(work_kind 식별자 + ApprovalGate work_kind 미수신)이 5/13 v2 정정보다 *코드 블로커*로 우선
2. Step 7 분리 — PlanChecker+Verifier+UAT는 Phase A 범위 밖, 별도 Phase B 트랙
3. TDD 강제는 verification-report contract + approval-gate verdict로 (새 gate 신설 회피)
4. PlanChecker 신설 금지 — RubricCompiler/CriticSkillRouter 확장 우선, 얇은 façade만 허용

**Codex 직접 read로 추가 발견** (2026-05-13):
- `docs/work-items/_template/verification-report.md:31-33`에 verdict 필드 이미 존재
- `core/approval_gate.py:385-413`에 `verification_blocked`, `execution_open=False` 로직 이미 구현
- `core/work_item_generator.py:552-557`에 DoD가 `e2e_command` + verdict 요구
- → Step A-4 "verification-report contract 고정"은 신규 schema 작성이 아니라 *기존 코드/템플릿 schema 명문화 + missing field 보강*

**How to apply**:
- Phase A 진입 전 사용자 결정 2건 필요:
  (a) `architecture-change` work_kind를 신설할 것인가, 폐기할 것인가? (5/11 review #1)
  (b) intake.py에서 work_kind를 metadata에 기록하는 시점은? (work-item 생성 시 vs 승급 시)
- 권장 ApprovalGate ↔ work_kind 연결 방식: **옵션 3** (intake.py metadata 기록 → ApprovalGate read). 생성자 인자 추가는 호출부 회귀 위험
- Phase A 작업 순서: Step A-1(work_kind 정정) → A-2(5/13 v2) → A-3(domain-review.md) → A-4(verification schema 명문화) → A-5(systematic_debugging SKILL.md) → A-6(TDD/worktree gate 연결)
- Phase B는 Step A 완료 + 회귀 안정화 후 별도 design doc 작성 후 진입
- 관련: [[project-auto-approve-block-followup]] — ApprovalGate 흡수 5건은 5/11 v2 별도 트랙

## 관련
- [[code/symbols]]

