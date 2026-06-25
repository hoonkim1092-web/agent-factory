---
name: project_right_sized_execution
description: "AF Right-Sized Execution 슬라이스1·2 + WI-1/WI-2/WI-3 + af doctor 완료. 다음=WI-4 또는 다른 product-value work-item."
metadata: 
  node_type: memory
  type: project
  originSessionId: 4fad39fd-7139-4ae4-8a19-d25003669e93
---

**상태(2026-06-05): 슬라이스1·2 전체 완료. WI-1/WI-2/WI-3 + af doctor 완료.**

**Why:** RSE 슬라이스1 → WI-1/WI-3 → af doctor → WI-2 → RSE 슬라이스2 순서로 진행.

**How to apply:** 다음 세션은 WI-4(review_runner→execute_cli_chat 통합) 또는 다른 product-value work-item. NEXT_STEPS.md 상단 확인.

---

## 완료 기록

- **슬라이스1** (`f208b632`, `098a9bd5`): `core/right_sized_router.py` 신규 + dogfood `_run_develop_phase` 라우터화 + 안전마감. 3-Tier PASS.
- **WI-1** (`9f4bb071`): `agent_runner.py` provider_id 보존. 3-Tier PASS.
- **WI-3** (`7a1a6061`): P4.5b model escalation 사전강제 + claude tier 매핑. 3-Tier PASS.
- **af doctor** (`e4c6dc5f`): `scripts/af_doctor.py` — 7개 진단 항목. 3-Tier WARN/PASS/PASS(26).
- **WI-2** (`7aa0be67`): review_provider runtime enforcement. 3-Tier PASS/BLOCK→fixed/PASS(72).
- **슬라이스2** (`d29f298d`): `_stage_enabled` helper + STAGE_* SSOT 상수 + research/doc-review 조건부 skip 게이트 + dogfood route 배선. 신규 19케이스 PASS, 3-Tier PASS/PASS/PASS(193).

## 다음 (2026-06-05 기준)

**WI-4** — review_runner → execute_cli_chat 통합.

관련: [[project_dogfood_isolation_leak]], [[feedback_crlf_normalization_separate_commit]], [[project_model_routing_facts]].
