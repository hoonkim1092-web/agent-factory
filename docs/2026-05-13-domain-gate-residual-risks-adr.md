# ADR: Domain Gate Design — Residual Risks Carried to Implementation

> **Status**: Partially Resolved (Phase A 완료 + M1~M5 결정 완료, 2026-05-13 22:55 KST)
> **Date**: 2026-05-13
> **Source Design**: `docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md`
> **Trigger**: 메모리 룰 `feedback_design_review_rounds_stop_rule` "3라운드 cap + 4차 freeze" 적용
> **Reviews 누적**: 5/11 원안 → 5/13 1차 정정 (16:12 BLOCK) → 5/13 2차 정정 (16:51 BLOCK) → 5/13 3차 정정 (17:25 BLOCK)

---

## Context

도메인 게이트 설계 문서가 4 라운드 cross-review를 거쳤음에도 BLOCK 잔존. 각 라운드는 새 결함을 발견하면서 동시에 일부 정정한 결과의 새 결함을 만드는 패턴(식별자 회귀 누적 5회: `feature` → `feature_update`, `system` → `system_wide`, `local` → `isolated` 2회). cross-review provider도 일부 라운드에서 실행 실패 (codex stdin-read error 17:25).

추가 정정 사이클은 다음 두 가지 위험:
1. **무한 루프 위험**: 매 라운드 신규 결함 발생 (이론상 영원히 fixable)
2. **구현 단계 회피**: 설계 검토가 실제 구현보다 비싸지는 anti-pattern

메모리 룰(`feedback_design_review_rounds_stop_rule`)에 따라 4차 freeze 적용. 잔여 finding은 ADR로 이월하여 구현 단계에서 실측 검증.

---

## Decision

5/11 design doc은 **현 상태로 동결** (이후 정정 금지). Phase A 진입 가능. 단 아래 10개 잔여 finding + 6 design gaps는 본 ADR에서 추적하여 구현 단계에서 검증 책임을 가짐.

---

## Residual Findings (이월 항목)

### Critical 2건 — Phase A 구현 1순위 검증

| # | 내용 | 검증 시점 | 검증 방법 |
|---|---|---|---|
| F1 | `blast_radius` 식별자 5번째 회귀 — design doc §3.3 line 152/181이 `"local"` 사용. 실제 enum은 `{"isolated","module","cross_module","system_wide"}` (`core/control/change_impact.py:16,35,243`) | 코드 작성 직전 (Phase A Step 1) | `core/approval_gate.py`에 `"local"`, `"system"` 토큰 grep 결과 0건 회귀 테스트 |
| F2 | `_render()` 미수정 — `core/approval_gate.py:496-550` `_render()`가 매 호출에서 파일 전체 재기록. design doc은 read만 명시, 시그니처 확장 누락. 사용자 approve 시 work_kind/blast_radius 즉시 wipe | Phase A Step 2 (approval_gate 구현 진입 직후) | `_render(work_kind, blast_radius)` 시그니처 + `approve/apply_verification_verdict/invalidate` 모두 carry. test_approval_gate_metadata_persistence.py 신설 |

### High 3건 — Phase A 진입 전 결정

| # | 내용 | 결정 시점 | 옵션 |
|---|---|---|---|
| F3 | `domain-review.md` drift invalidation 정책 미정 — `_DOMAIN_REVIEW_FILE` 격리로 verdict 위조 시 `check_validity()` 무반응 | Phase A 작업 첫 PR | (a) snapshot 별도 키 `domain_review_version` 추가 / (b) "승인된 domain-review.md immutable, 변경 시 새 slug" |
| F4 | verdict 파서 × 체크박스 UX 충돌 — 검토자가 체크박스만 채우면 `missing_verdict` BLOCK false-positive | Phase A 작업 첫 PR | (a) 체크박스 제거 + 1줄만 / (b) 파서가 체크박스도 인식 / (c) sync 스크립트 |
| F5 | Phase A 단독 정당화 근거 부재 — Phase B 매트릭스 의존 구조. Phase B 흡수가 정당화 안 되면 Phase A 인프라만 부담 | Phase A 진입 결정 | 결정 충돌 실측 N건 또는 PROJECT_CONTEXT rework 사례 제시. 없으면 B→A 순서 재고 |

### Medium 5건 — 구현 중 본문 반영

| # | 내용 | 검증 시점 |
|---|---|---|
| F6 | `last_block_reason` 4분기 미분리 (`missing_domain_review_file` / `missing_verdict` / `multiple_verdicts` / `domain_review_blocked`) | Phase A 구현 시점, test fixture로 검증 |
| F7 | `AF_SKIP_DOMAIN_REVIEW` bypass 정당화 부족. 도메인 충돌은 hotfix와 무관 → silent debt 위험 | Phase A 구현 시점, 옵션 (a) 제거 / (b) ADR stub 자동 생성 + 단계 3 메트릭 |
| F8 | §4.4 TDD 분류 § 4.3 규칙 산술 모순 (B=6은 "보류"여야 하는데 "선택적" 표기) | Phase B 매트릭스 작업 시 정정 |
| F9 | ADR ID 분 단위 collision (야간 파이프라인 동시 생성 가능) | Phase A 구현 시점, `ADR-YYYYMMDD-HHMMSS-<slug>` 또는 `<git-sha6>` suffix |
| F10 | PROJECT_CONTEXT stale 감지 Phase A 포함 여부 미확정 | Phase A 구현 첫 commit 전, 권장: 체크리스트 (0 LOC) |

### Design Gaps 6건 — 구현 PR 체크리스트

| # | Gap | 검증 |
|---|---|---|
| G1 | `_render()` 시그니처 변경이 `tests/test_approval_gate_auto_approve.py` fixture 회귀 | fixture 갱신 commit 포함 |
| G2 | domain-review.md drift × verdict 위조 (F3과 통합) | F3 결정 따름 |
| G3 | `apply_verification_verdict()` × domain-review 상호작용 미명세 (verification=BLOCK + domain=PASS 상태 매트릭스) | Phase A 구현 시 상태 매트릭스 작성 |
| G4 | 기존 7개 게이트 테스트 호환성 (test_pipeline_block_enforcement, test_approval_gate_block_decision 등) | 회귀 매트릭스 + `last_block_reason==""` default 검증 |
| G5 | `af.spec` hiddenimports — `_DOMAIN_REVIEW_FILE` 상수 + frozen 빌드 검증 | Phase A 완료 commit에 `python build_exe.py` 1회 실행 + dist 로딩 회귀 |
| G6 | `core/skill_pack_bootstrapper.py` 제거 시 `af.spec:122` hiddenimports로 ImportError | dead code 제거 commit에 `af.spec` 동시 정정 + frozen 회귀 |

---

## Consequences

### 긍정적

- 무한 정정 루프 차단. Phase A 진입 가능
- 잔여 risk가 본 ADR에 명시 추적되어 silent debt 누적 방지
- 구현 단계의 실측 검증이 design 검토보다 효율적 — 코드 작성하면서 즉시 발견 가능

### 부정적 (수용)

- F1, F2 같은 식별자/구조 결함이 구현 시점에 발견되면 코드 재작성 비용 발생
- F3, F4 같은 정책 미정은 구현자가 자의 선택할 위험 (→ 첫 PR review에서 명시 결정 강제)
- 본 ADR이 구현 PR review의 별도 체크리스트로 동작해야 함 — review reviewer가 ADR을 참조해야 함

### 후속 책임

1. **Phase A Step 1 작업자**: F1 (식별자 grep 회귀 테스트) + F2 (`_render()` 시그니처 확장) 즉시 처리
2. **Phase A 첫 PR**: F3, F4 결정 명시 + G1~G6 체크리스트 통과
3. **본 ADR Status**: Phase A 완료 시 "Superseded by implementation" 또는 "Resolved" 갱신
4. **cross-review provider 진단**: 17:25 codex stdin-read error 별도 추적 (`docs/codex_논의/` 진단). 본 ADR과 독립

---

## M1~M5 결정 기록 (2026-05-13 22:55 KST)

Phase A 구현(commit `ef82acc4`) 완료 후 잔여 Medium 항목 결정:

| # | 항목 | 결정 | 근거 |
|---|------|------|------|
| M1 | verdict 파서 예외 형태 | **return False 유지** (BlockedExecutionError 도입 안 함) | `approve()` 는 False + `last_block_reason` 패턴 일관성 유지. `agent_launcher.py:440`이 이미 이 패턴으로 소비 중 |
| M2 | ADR 번호 부여 규칙 | **`ADR-YYYYMMDD-HHMMSS-<slug>.md`, 저장위치 `docs/decisions/`** | 초 단위로 야간 파이프라인 충돌 방지. CLAUDE.md §ADR명명규칙 추가 |
| M3 | frozen build `docs/decisions/` 경로 | **검증 완료 — 변경 불필요** | `approval_gate.py` 경로는 `workspace` 파라미터 기반 (user project dir). `_MEIPASS` 독립. `docs/decisions/` 생성(`mkdir`) |
| M4 | MIT attribution `inspired_by:` 정책 | **SKILL.md 프론트매터에 `inspired_by: <패키지>/<스킬-ID>` 추가** | Phase B 흡수 시 적용. CLAUDE.md §스킬흡수귀속정책 추가 |
| M5 | Phase B 진입 지표 + 결정자 | **3개 지표 + 사용자 명시 승인** | 아래 §Phase B 진입 기준 참조 |

### Phase B 진입 기준

| 지표 | 기준값 | 측정 방법 |
|------|--------|-----------|
| 지표 1: Phase A domain gate 발동 | ≥ 1건 (실 운영) | `hook_events.log` 또는 approval-gate.md `blast_radius: system_wide` 확인 |
| 지표 2: approval_gate 테스트 지속 PASS | ≥ 29건, 2주 이상 연속 | `pytest tests/test_approval_gate*.py` CI 기록 |
| 지표 3: 사용자 명시적 Phase B 지시 | 필수 (자동 전환 없음) | 구두 또는 NEXT_STEPS.md 지시 |

**결정자**: hoon.kim1092@gmail.com (사용자) 단독 결정. 지표 1~2는 참고 기준이며, 지표 3 없이 자동 전환하지 않는다.

---

## Related

- 설계 문서: `docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md`
- Review 누적:
  - `docs/reviews/2026-05-13-161251-...-design-review.md` (1차 정정 후)
  - `docs/reviews/2026-05-13-165102-...-design-review.md` (2차 정정 후)
  - `docs/reviews/2026-05-13-172527-...-design-review.md` (3차 정정 후, 본 ADR 트리거)
- 메모리 룰: `feedback_design_review_rounds_stop_rule`, `feedback_design_doc_grep_before_write`
- 정책 이력: 2026-05-13 cross-vendor 검토 결과 `.claude/agents/af-design-critic.md` 신설 폐기, 5/1 정책 (af-cross-review만) 유지
