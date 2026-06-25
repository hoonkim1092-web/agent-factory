---
name: Phase A Step 2 COMPACT 완료 상태
description: Phase A Step 2 COMPACT 구현 완료 현황 (2026-04-22)
type: project
originSessionId: 4471b27b-477c-4cfb-9149-9090719255cc
---
Phase A Step 2 COMPACT 연동 활성화 완료 (2026-04-22).

**Why:** RunBudget 토큰 예산이 agent_runner에서 항상 빈 문자열을 기록해 추적이 불작동했고, FSA 루프에 예산 체크가 없었으며, PlanVerifier에 Phase Gate 메서드가 없었음.

**완료된 6개 항목:**
1. `core/agent_runner.py:_flush_trace()` — `result["text"]` 빈 문자열 버그 수정 → transcript assistant 엔트리 합산으로 RunBudget.record() 실제 연결
2. `core/fsa_loop.py` — 각 FSA 사이클 시작 시 RunBudget.is_exhausted() 조기 탈출 체크 추가
3. `policy.yaml` — phase_gate(enabled: false) + context_window 섹션 추가 (placeholder, 코드와 아직 미연결 명시)
4. `core/plan_verifier.py` — PlanVerifyResult.redirect 필드 추가, PlanVerifier.gate() Phase Gate 메서드 신설, PhaseGateResult 별칭
5. `core/skill_pack_bootstrapper.py` — 신규: shutil.which 기반 claude-code/codex/gemini CLI 감지 (설치 없음)
6. `tests/test_compact_step2.py` — 18개 테스트 (autouse RunBudget fixture 포함), 18/18 PASS

**주의사항:**
- linter가 plan_verifier.py, fsa_loop.py, agent_runner.py를 자동으로 되돌리는 현상 발생 → 세션 내에서 재적용 필요했음
- policy.yaml의 context_window.default=8000 (skill_context_config.py 기준), 128000이 아님

**How to apply:** 다음 Phase A Step 3(EVOLUTION) 시작 전 RunBudget이 실제로 작동하는지 확인. dynamic_orchestrator와 fsa_loop 양쪽에 is_exhausted() 체크 완료.

## 관련
- [[code/symbols]]

