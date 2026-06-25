---
name: P4a ship 완료 / P4b 대기
description: Warning Registry P4a 완료 (v1.2.27, commit d61b1d68). current_phase yaml 단일 진실원 + rule-level mode 필드. P4b = threshold 결정 + mode enforce toggle (측정 데이터 축적 후).
type: project
originSessionId: 53f26c43-762b-4024-ba66-5682e5d2fc9d
---
P1+P2+P3+P4a 완료. v1.2.27 (main `d61b1d68`, 2026-05-10).

**P4a 구현 내용:**
- `core/escalation_evaluator.py` — `_PolicyRule.mode` 필드 + `read_current_phase()` + `evaluate()` mode 분기 (off/observation/enforce)
- `core/escalation_decision_report.py` — `write_error_decision` `current_phase` kwarg
- `core/warning_registry.py` — single-load 패턴, `escalation_phase` 동적화
- `config/escalation_policy.yaml` — v1, `current_phase: "P4"`, P4 rule 전부 `mode: observation`
- 테스트 12케이스 신규 + 기존 59 = 71 PASS
- 3-tier 게이트 WARN-only 통과

**Why:** P4a = "기계장치만 ship, BLOCK 0건 보장". 측정 데이터 0건 상태에서 임계 결정 불가 → P4를 P4a/P4b로 분리.

**Advisory WARN (수정 의무 없음):**
- `read_current_phase()` list 타입 yaml 입력 시 TypeError → fail-closed (배포 yaml 정상, P4b 진입 시 `isinstance(cp, str)` 타입 가드 1줄 추가 권장)
- 설계문서 §10 #2 stale 문구 (코드는 정확)

**How to apply (다음 세션 — P4b):**
1. P3 measurement 데이터(`af warning-stats --rule owner_role_mismatch`) 충분히 수집 후 진입
2. `config/escalation_policy.yaml`: owner_role_mismatch + evidence_quality_warn `mode: "observation" → "enforce"` toggle + repeat_count_min/count_per_run_min 측정 기반 값으로 갱신
3. `runtime/warnings/_index.json`: evidence_quality_warn `mode` 필드 동기 (P4a에서 yaml만, _index.json은 P4b)

## 관련
- [[code/symbols]]

