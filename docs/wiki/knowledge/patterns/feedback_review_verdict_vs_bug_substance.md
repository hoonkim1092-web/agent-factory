---
name: review-verdict-vs-bug-substance
description: "리뷰 게이트 라벨(WARN/advisory)과 버그 실체를 분리해 보고할 것. advisory를 \"버그 아님\"으로 제시 금지."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 124cbd22-f07f-4d7c-a8be-4ee052c84f21
---

크로스리뷰/리뷰 결과를 보고할 때 게이트 정책 라벨(WARN·advisory·"수정 의무 없음")을 버그 존재 여부와 섞지 말 것. advisory는 "게이트가 자동수정을 강제하지 않는다"는 뜻이지 "버그가 아니다"가 아니다. 실제 결함이 발견됐으면 라벨과 무관하게 "버그를 찾았다"를 먼저 명확히 단언하고, 게이트 의무(수정 강제 여부)는 그 다음에 별도로 안내한다.

**Why:** B-2 리뷰에서 af-cross-review가 `_clean_list` 문자열 char-decomposition이라는 진짜 버그를 Finding 1으로 보고했는데, "WARN이라 반드시 고칠 건 없다"고 요약해 버그 실체가 가려짐. 사용자가 "수정해야 하는 게 있지?", "버그 발견하지 않았나?"로 두 번 되물어 바로잡음.
**How to apply:** 리뷰 결과 요약 시 (1) 버그/결함 실재 여부를 먼저 단언 → (2) 심각도·게이트 의무는 그 다음. "advisory = 무시 가능"으로 읽히는 표현 회피. 관련: [[feedback_code_review_workflow_v2]]
