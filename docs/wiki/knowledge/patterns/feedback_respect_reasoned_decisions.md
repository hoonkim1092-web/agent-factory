---
name: respect-reasoned-user-decisions
description: 사용자가 근거를 붙여 내린 결정은 A/B로 재질문하지 말 것. 사실 보정만 제시하고 진행.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2eaf2278-2f8a-4177-bdc3-e47b27b674ce
---

사용자가 결정 + 근거를 함께 제시하면(예: "내 판단은… 근거는… 결론:" 구조), 그 결정을 다시 A/B 선택지로 되묻지 않는다. 결정은 이미 내려진 것으로 취급한다.

**Why:** 사용자가 ISE loop/canonical checkpoint 처리에 대해 근거까지 붙인 판단을 줬는데, 나는 그것을 `AskUserQuestion` "포함/미포함" A/B로 다시 물었다. 사용자가 "내가낸 의견은 생각해봤어?"로 반박 — 결정을 재심한 셈이었다.

**How to apply:**
- 결정에 동의하면 바로 실행한다.
- 전제에 사실 오류를 발견하면 **그 보정 한 가지만** 제시하고(스코프 영향 포함) 진행한다. 결정 전체를 다시 묻지 않는다.
- 근거 있는 결정 = 지시이지 설문이 아니다. `AskUserQuestion`은 사용자가 아직 판단을 안 내린 진짜 분기에만 쓴다.
- 관련: [[feedback_design_review_mandatory]], [[feedback_reverse_sycophancy_balance]]
