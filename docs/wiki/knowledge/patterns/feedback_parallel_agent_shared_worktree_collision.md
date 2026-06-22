---
name: feedback_parallel_agent_shared_worktree_collision
description: 같은 work-item을 백그라운드 워크플로와 메인 세션이 격리 없이 동시 작업하면 working tree·staging이 충돌·흡수된다
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c788b521-2158-4aa2-adaf-e09a058699aa
---

2026-06-01 dogfood investigation_outputs(`_build_ai_task`) 작업에서 발생: 세션 재개 후 메인 루프가 리뷰·수정을 진행하는 동안, 별개의 백그라운드 워크플로(재개된 `wy9jtjbf9` 계열)가 **같은 working tree**에서 동일 기능을 격리 없이 병렬 구현하다 먼저 커밋(`b5a5578a`, `AF_SKIP_REVIEW_GATE` 우회).

증상:
- 내 staged 파일이 백그라운드 에이전트의 `git commit`에 흡수됨 (staging은 프로세스 공유 자원)
- 내 working-tree 편집(`_INVESTIGATION_MAX_ENTRIES`/`[-N:]`)이 그쪽 버전(`_INVESTIGATION_MAX_ITEMS`/`[:N]`)으로 일부 덮어써짐 — 단 내 `capped_output` append-time 절삭 + 테스트 함수명은 살아남아 blend 커밋됨
- 테스트가 간헐적으로 "11 failed" → 병렬 에이전트가 real-git 테스트 도중 파일/git 조작한 경쟁 흔적이었음 (재현 불가)

**Why:** git working tree와 index는 PC-전역 단일 자원. 두 에이전트가 같은 디렉터리에서 동시에 Edit/`git add`/`git commit`하면 서로의 상태를 비결정적으로 덮어쓴다. 이게 CLAUDE.md worktree-isolation 규칙([[feedback_dogfood_pc_handoff]])이 막으려는 바로 그 상황.

**How to apply:** ① 백그라운드 워크플로/에이전트에 구현(파일 편집+커밋) 작업을 위임할 땐 `isolation: "worktree"`로 격리하거나, 메인 세션은 그 work-item을 동시에 만지지 말 것. ② 세션 재개 시 "진행 중 백그라운드 작업"이 있으면 먼저 그 완료/커밋 여부를 확인하고, 같은 파일을 손대기 전 그 산출물부터 회수할 것. ③ 동일 기능을 양쪽이 만졌다면 commit 전 `git log --oneline`으로 예상외 커밋 유무를 확인. 관련: [[feedback_commit_staging_hygiene]]
