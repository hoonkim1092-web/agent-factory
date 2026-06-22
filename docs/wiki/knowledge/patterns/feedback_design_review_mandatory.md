---
name: 설계 시 교차검증 필수
description: 코드 변경뿐 아니라 설계 단계에서도 반드시 af-critic + af-cross-review 교차검증을 실행해야 함. 설계문서 작성 여부와 무관.
type: feedback
originSessionId: 9bec23b4-54e8-405d-8fc1-bae170472146
---
설계가 포함된 변경(동작 변경, 아키텍처 변경)을 할 때는 구현 전에 반드시 교차검증을 실행한다.

**Why:** 이번 세션에서 CLI provider 안정성 개선(Codex returncode 처리, stall 임계값, 조기 종료 버그, hook import 우회) 4건의 설계 변경을 교차검증 없이 구현했다가, 나중에 critic이 BLOCK(importlib 우회 미작동)을 발견했음. 설계 단계에서 검증했으면 잘못된 구현을 피할 수 있었음.

**How to apply:**
- 버그 수정이 아닌 동작/아키텍처 변경 시 → 구현 전에 af-critic + af-cross-review 실행
- 설계문서(.md) 작성 시 → af-doc-qa + af-critic 실행
- AF 에이전트 세션에서도 동일 규칙 적용 필요
