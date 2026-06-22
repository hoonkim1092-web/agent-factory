---
name: commit-staging-hygiene
description: 코드/문서 커밋 시 변경에 속한 파일만 명시 스테이징. dogfooding 산출물 섞지 말 것.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 705cfc7b-7b4a-474a-b57e-1c63a4c99694
---

코드/문서 변경을 커밋할 때는 그 변경에 직접 속한 파일만 이름으로 명시 스테이징한다. `git add -A` / `git add .` 금지.

**Why:** AF는 자기 자신에 파이프라인을 돌리는 dogfooding 때문에 워킹트리에 산출물 파일이 끊임없이 재생성된다 — `projects/agent_factory/**` (agents/runs/dashboard/settings 등), `skills/dp/*`, untracked `docs/reviews/*`, `runs/**`의 `chat_trace.json`/`state.json`. 이게 코드 커밋에 섞이면 히스토리가 오염되고, 사용자가 과거에 반복적으로 겪은 문제다.

**How to apply:** `git add <파일명 나열>`로만 스테이징. 커밋 후 `git show --stat HEAD`로 의도한 파일(+ pre-commit hook이 자동 갱신·스테이징하는 `docs/code_review/code-review.md`)만 들어갔는지 확인. `git status --short`에 dogfooding 산출물이 uncommitted로 남아 있는 게 정상.
