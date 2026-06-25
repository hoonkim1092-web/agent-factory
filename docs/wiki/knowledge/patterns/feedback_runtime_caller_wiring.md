---
name: 런타임 호출자 run_id 연결 필수
description: 새 kwarg(run_id 등)를 추가할 때 실제 실행 경로의 호출자까지 연결하지 않으면 기능이 no-op이 됨
type: feedback
originSessionId: e2a681a3-9b63-4d59-919e-9d20ba0435d2
---
새 optional kwarg(특히 run_id, project_id)를 인터페이스에 추가할 때, 단위 테스트만으로는 실제 실행 경로에서 값이 전달되는지 검증할 수 없다.

**Why:** T3-7에서 ApprovalGate.approve(run_id=) 와 set_run_budget(run_id=)를 추가했으나, af-cross-review가 work_item_generator.py, project_pipeline.py, agent_launcher.py 등 실제 호출자가 run_id를 전달하지 않아 이벤트가 no-op임을 발견. 14건 테스트가 전부 직접 kwarg 전달하는 happy path였음.

**How to apply:** 새 kwarg 추가 시 반드시 grep으로 모든 호출자를 확인하고, 값이 있는 상위 컨텍스트(PreparedProject.run_id 등)에서 전파가 이뤄지는지 체크한다. af-cross-review가 "런타임 연결 누락" 패턴을 잘 잡으므로 Tier 3 완료 후 ACCEPT 항목은 즉시 수정한다.

## 관련
- [[code/symbols]]

