---
name: Canonical 상태는 분산하지 않는다
description: runtime state(board 등)를 역할별 파일로 분산하는 제안 금지. canonical 유지 + projection 추가 방식만 허용.
type: feedback
---

runtime state를 역할별 파일로 분산하는 구조를 제안하지 말 것. canonical 유지 + role-local projection 추가가 올바른 방향.

**Why:** project_board_state.json은 단순 문서가 아니라 런타임 제어면. locked_file() 원자성, cross-role 의존성 해소, 스케줄링/완료 판정/stall 복구가 이 단일 파일 기준으로 동작함. 역할별로 쪼개면 이 모든 로직을 다시 써야 함. 또한 별도 dependency_graph.json 같은 이중 source of truth도 drift 위험으로 금지.

**How to apply:** 문서 구조 개선 제안 시 항상 "canonical은 유지, projection은 파생 뷰"를 기본 원칙으로. work-item은 에이전트 단위가 아니라 모듈/슬라이스 단위로 재편.
