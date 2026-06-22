---
name: feedback-af-repo-scope-policy
description: "AF 레포 범위 정책 — AF 자체 개발만 agent-factory에, 외부 산출물은 별도 레포로"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e79b63cc-3764-4d7d-8133-a6e0816353b0
---

AF 레포(agent-factory)는 AF 자체 기능 구현/버그수정/리팩토링 전용이다.
AF를 플랫폼으로 사용해 만든 외부 산출물은 처음부터 별도 레포로 분리한다.

**Why:** `projects/meeting_stt_app`을 AF 레포에 커밋했다가 별도 분리 작업이 필요했던 사례(2026-06-17).
AF 레포에 외부 산출물이 섞이면 관심사 혼재, 릴리즈 사이클 얽힘, clone 비용 증가.

**How to apply:**
- AF `core/`, `scripts/`, `tests/` 변경 → agent-factory 레포
- AF dogfood(AF가 AF를 개선하는 루프) → agent-factory 레포 (projects/ 임시 작업공간)
- "~~ 만들어줘" 외부 앱/서비스 → 별도 레포(GitHub private/public), AF 레포에 커밋하지 말 것
- 외부 대규모 프로젝트에 AF 붙여 작업 → 해당 프로젝트 레포에서 작업
- `.gitignore`에 `projects/<외부산출물>/` 추가로 임시 작업 잔재 제외

**적용 사례:** `meeting_stt_app` → `hoonkim1092-web/meeting-stt-app` (private) 분리 완료 (2026-06-17)
