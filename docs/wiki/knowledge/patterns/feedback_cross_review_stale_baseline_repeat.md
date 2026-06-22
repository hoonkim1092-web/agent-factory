---
name: cross-review가 stale baseline false positive를 반복 보고하는 패턴
description: 단일 세션 spec churn(v3→v7 5라운드) 중 v6/v7 cross-review가 §11 row 부재를 잘못 BLOCK 보고 — 매번 grep으로 즉시 반증 가능. 동일 patternが 2회 연속 발생.
type: feedback
originSessionId: 175cc2d5-8c89-425b-acfc-12214e1ddae5
---
**규칙**: spec churn 라운드(v3→v4→v5...)가 4회를 넘어가면 cross-review가 stale baseline false positive를 반복 보고하기 시작한다. Critical/High BLOCK 주장이라도 grep으로 1차 반증 가능한지 먼저 확인 — 반증되면 dismiss with evidence trail (§11 row freeze + §10 F-row로 cross-review prompt 보강 의무).

**Why (실측 사례)**: 2026-05-03 Phase 2 verdict-label spec v3→v7 churn cycle:
- v6 cross-review: §11 v5→v6 row "부재" Critical → 실제는 line 832-840에 5-row 실재 (false positive)
- v7 cross-review: §11 v6→v7 row "부재" Critical → 실제는 line 845에 row 실재 (false positive 동형 재발)
- 두 라운드 모두 critic이 "v5 BLOCK pattern이 v6/v7에서 동형 재발"이라 단정했으나 실측 grep으로 즉시 반증
- §10 F11 (Phase 3 후보)로 등록: "cross-review subagent prompt에 grep baseline 검증 의무 1줄 추가"

**How to apply**:
- spec churn 4라운드 이상에서 cross-review BLOCK 보고가 들어오면 **각 항목에 대해 `grep` 또는 `Read`로 baseline을 직접 검증** (단순 LLM 단정 신뢰 금지)
- 실측 반증되는 항목은 dismiss with evidence trail (§11 audit row에 line number + 반증 grep 결과 명시)
- valid 항목만 다음 버전에 정정. false positive를 그대로 정정하면 churn cycle이 spec 정확성을 오히려 손상시킴
- max_rounds=2 캡 정신 — CLAUDE.md "WARN은 advisory" 정책상 사용자가 명시 결정으로 churn 진행할 때만 라운드 추가. 자동 진행 금지
- 최종 라운드 종결 결정은 사용자 명시 호출로 "세션 종료" 또는 "코드 적용 진입"으로 break
