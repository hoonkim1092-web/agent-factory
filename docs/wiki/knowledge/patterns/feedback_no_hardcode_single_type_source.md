---
name: feedback_no_hardcode_single_type_source
description: "구현 시 하드코딩 금지(매직 스트링/넘버→명명 상수) + 타입/상수 SSOT 1곳, 여러 곳 재선언·재정의 금지."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f3cffffb-c8a3-486c-9dc0-016ccff07b4c
---

구현할 때 두 제약을 **강제**한다 (사용자 지시 2026-06-05):

1. **하드코딩 금지** — 매직 스트링/넘버를 코드에 분산하지 않는다. 정책값·어휘·파일명·임계값은 명명된 상수(SSOT)에 두고 참조한다. 호출처마다 "이 경우만 예외" 분기를 박지 않고 공통 helper/policy로 경유.
2. **타입/상수 단일 선언** — 같은 타입(dataclass/Enum)·상수·어휘를 여러 모듈에서 재선언하거나 재정의하지 않는다. SSOT가 있는 모듈에서 import해 **소비만** 한다. 새 stage/mode 이름 같은 어휘를 소비처에서 임의 도입 금지.

**Why:** 매직 스트링 분산은 오타·표류(drift) 버그를 부르고, 타입 중복 선언은 한 곳만 고치면 다른 곳이 어긋나는 silent 불일치를 만든다. NEXT_STEPS dogfood hardening의 "하드코딩 금지 원칙"을 전 구현으로 확장한 것.

**How to apply:**
- 구현 전 SSOT 위치를 먼저 찾는다(grep). 예: stage 어휘=`core/right_sized_router.STAGE_VOCAB`, isolation=`ISOLATION_LEVELS`.
- 새 게이트/분기에서 stage·mode 이름을 쓸 때 SSOT 어휘 멤버임을 보장(테스트로 검증). 오타/신규 어휘 도입 차단.
- "강제"는 주석 권고가 아니라 **테스트로 못박는다**(Karpathy goal-driven): SSOT 멤버십 assert, 중복 선언 탐지.
- 슬라이스2 적용: `docs/2026-06-05-af-right-sized-execution-slice2-design.md` §6.1 구현 제약 + stage-name SSOT 테스트.

관련: [[project_right_sized_execution]], [[feedback_post_edit_checklist]].
