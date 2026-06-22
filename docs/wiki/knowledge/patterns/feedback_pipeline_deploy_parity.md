---
name: 파이프라인 배포 동등성 규칙
description: 파이프라인 기능은 production caller까지 end-to-end로 연결해야 완료. 테스트 픽스처만 통과는 미완료.
type: feedback
originSessionId: 9ba41419-7b0d-44f3-ba7f-8f5a3641f82f
---
파이프라인 관련 기능은 배포 사용자 환경과 개발 환경에서 동일하게 동작해야 한다.

**Why:** 이번 세션에서 `approval_gate.py`와 `work_item_generator.py`에 `blast_radius` 파라미터를 추가했으나 production caller인 `project_pipeline.py:963-970`이 해당 파라미터를 전달하지 않아 domain gate가 실제로는 절대 활성화되지 않는 dead code가 됐다. 테스트 픽스처가 직접 파라미터를 주입해 모든 테스트가 PASS였지만 production에서는 작동 안 했음.

**How to apply:**
- 구현 완료 기준 = production 호출 경로(`project_pipeline.py`, `agent_launcher.py` 등)까지 파라미터 흐름 확인
- 새 파라미터/기능 추가 후 `grep -rn "함수명"` 으로 production caller 찾아서 연결 확인
- 테스트 픽스처가 직접 파라미터를 주입하는 패턴이면 특히 주의 — production path에도 동일하게 흘러야 함
- 예외: 사용자가 명시적으로 "개발 환경 전용" 또는 "추후 연결"을 지시한 경우만
