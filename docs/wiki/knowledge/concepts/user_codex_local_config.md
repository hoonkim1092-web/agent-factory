---
name: user-codex-local-config
description: .codex/config.toml은 사용자가 Codex CLI 퍼미션 우회용으로 둔 로컬 설정 — untracked 유지 의도적.
metadata: 
  node_type: memory
  type: user
  originSessionId: b6ab161b-9947-460c-bc48-002a6383485c
---

`.codex/config.toml` (워크스페이스 루트) 은 사용자가 Codex CLI 퍼미션 prompt를 통과시키기 위해 둔 **로컬 전용** 설정 파일이다. **의도적 untracked** — 커밋·staging 금지.

**How to apply:**
- 세션 시작 시 `?? .codex/config.toml` 가 보여도 hygiene 위반·dogfood 산출물로 판정하지 말 것.
- 사용자가 명시적으로 "이 파일 커밋해"라고 지시하기 전엔 `git add`/`git stage` 대상에서 자동 제외.
- 관련: [[feedback-commit-staging-hygiene]] (dogfood 산출물 staging 금지 원칙과는 별개 — 본 파일은 user-local config).
