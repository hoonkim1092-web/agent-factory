---
name: Phase A Step 1 ISE 배선 복구 완료
description: Phase A Step 1 ISE 배선 복구 작업 결과 — 브랜치, 커밋, 다음 단계
type: project
originSessionId: 2b270772-7bb2-4890-944d-e8806db15143
---
## Phase A Step 1 완료 (2026-04-22)

**브랜치**: `2026-04-14-build-diet`
**커밋**: `6b53412c` (feat: ISE 배선 복구), `32da8b8e` (chore: 런타임 파생 파일 일괄)
**Push**: 완료 (origin/2026-04-14-build-diet)

**Why:** Phase A 우선순위 1번인 ISE 배선이 끊어진 상태(dead code)였고, 
Review-Gate BLOCK 7건 + af-critic BLOCK 2건 + af-cross-review BLOCK 1건 총 10건 해소 후 커밋.

**How to apply:** 다음 세션에서 Phase A Step 2 (COMPACT) 작업 시 이 커밋을 기준으로 시작.

## 완료 항목 요약

- agent_launcher.py: ISELoop 연결 + `--mode ise` CLI routing
- core/dynamic_orchestrator.py: `_should_decompose()` 신규 + 오케스트레이션 루프 연결 + 모든 실패 경로에 `failure_category` 필드
- core/ise_strategy_ledger.py: SHA256 32자 확장 + 레거시 해시 경고
- core/project_pipeline.py: ise 모드 AF_ISE_ENABLED 강제 활성화
- core/skill_procurer.py: auto_approve ise 포함
- af.spec: ISE 5모듈 hiddenimports
- tests/test_ise_integration.py: 7개 신규 테스트 (전부 PASS)

## 테스트 결과

- 787P/17F(pre-existing)/3S — 회귀 0건
- ISE integration: 7/7 PASS

## Phase A 다음 작업 (Step 2: COMPACT)

1. `agent_runner.py:915` `result["text"]` 키 수정 → RunBudget.record() 실제 작동
2. `fsa_loop.py:149`/`dynamic_orchestrator.py:896` CWM cross-cycle reset
3. `policy.yaml`에 `phase_gate_enabled`, `compaction_thresholds` 추가
4. `SkillPackBootstrapper.check_installed()` 구현
5. `memory_system/decay.py` DEFAULT_TTL_DAYS 30 → 15
6. `run_budget.py` 태스크당 기본 한도 200K 상향

## Phase A 우선순위 정책 (Q2 확정)

ISE → COMPACT → EVOLUTION → MEMORY

## 관련
- [[code/symbols]]

