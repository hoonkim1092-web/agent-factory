---
name: hook-codereview-amend-loop
description: "[RESOLVED 2026-05-18 f5d5461d] post-commit amend 루프 근본 fix 완료 — post-commit이 더 이상 커밋을 amend하지 않음."
metadata:
  node_type: memory
  type: project
  originSessionId: b27dc00e-5351-44b1-b9eb-87e643d82be5
---

**[RESOLVED — 2026-05-18, 커밋 `f5d5461d`]**

이전 증상: `code_review_updater`/`blueprint_updater` hook이 post-commit에서 `code-review.md`·`Master_Blueprint.md`를 수정한 뒤 `git commit --amend` → 같은 논리 커밋의 해시가 비결정적으로 1~N회 바뀜 (race + LLM 지연 의존).

근본 fix: post-commit의 amend 블록 전체 제거. tracked 문서 갱신은 pre-commit deterministic `--no-llm` updater 한 곳으로 단일화. `post_edit_blueprint`/`post_edit_code_review` hook도 제거(편집 중 working tree 오염 해소). post-commit은 이제 review-gate 큐 클리어만 수행.

**How to apply:** 이 버그는 해소됨 — 커밋·push 후 로컬/origin이 diverge하면 그건 다른 원인이므로 별도 진단. 상세는 `git show f5d5461d`.
