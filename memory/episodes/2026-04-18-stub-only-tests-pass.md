---
episode_id: 2026-04-18-stub-only-tests-pass
outcome: failure_then_success
project_id: lotto_predictor_v2
date: 2026-04-18
tags: [stub-test, false-positive, approval-gate, e2e]
---

# 에피소드: stub-only 테스트가 PASS — 실제 기능은 미구현

## 상황

lotto_predictor_v2 QA 단계에서 모든 unit test가 PASS 됐지만
실제 e2e 실행 시 `ModuleNotFoundError: No module named 'lotto'` 발생.

## 실패 원인

- qa_engineer가 테스트를 전부 mock/stub으로만 작성
- 실제 `lotto` 패키지가 설치되지 않았지만 import가 mock으로 우회됨
- approval-gate가 e2e_command 없는 태스크를 `needs_backfill`로 표시했지만
  orchestrator가 계속 진행함

## 해결 방법

- Phase 2 approval-gate에서 e2e_command 필수화
- `python -m lotto --help` exit 0 조건 추가
- 실제 패키지 설치 후 통합 테스트 재실행 성공

## Hints

- stub-only 테스트는 실제 기능 존재를 보장하지 않는다 — e2e_command 필수
- e2e_command가 `needs_backfill`인 태스크는 PASS 처리 불가
- 테스트 작성 시 최소 1개의 실제 실행 경로(비mock)를 포함해야 한다
- approval-gate `status=completed` = 파일 존재 + 금지토큰 0 + e2e exit 0 모두 충족

## 결과

e2e 검증 추가 후 Level 2 pivot으로 성공. lineage_id: lotto_predictor_v2::qa::unit_tests
