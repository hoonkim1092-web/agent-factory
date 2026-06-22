---
name: 코덱스 다라운드 의견 교환은 codex-reply 사용
description: 코덱스와 합의/deliberation 시 stateless codex 대신 codex-reply로 thread를 이어가야 함. 배포 빌드(af-cross-review 등)에도 동일 적용.
type: feedback
originSessionId: 0298a7dc-abb2-441c-909b-48c280653b83
---
다라운드 의견 교환·합의·deliberation을 코덱스와 진행할 때는 `mcp__codex__codex-reply`(또는 동등한 thread 연속 도구)를 사용해 같은 threadId로 이어간다. `mcp__codex__codex`(새 thread)를 라운드마다 재호출하지 않는다.

**Why:** `mcp__codex__codex`는 stateless라 매번 새 인스턴스가 생성되고, 라운드 N의 코덱스는 라운드 N-1 결과를 모른다. Claude가 paraphrase로 채워주는 컨텍스트는 ① 부정확하게 요약될 위험 ② 반론을 강하게 프레이밍해 라운드 N의 답을 편향시킬 위험이 있다. `codex-reply`로 thread를 이어가면 코덱스 측에 자기가 직전에 한 말이 그대로 누적되어 진짜 deliberate에 가까워진다.

**How to apply:**
- 1라운드 quick check, 단발 리뷰: `mcp__codex__codex` OK
- 2라운드 이상 의견 교환·합의 시도: 1라운드는 `codex`로 thread 시작 → 이후 모두 `codex-reply`로 동일 threadId 유지
- **배포 빌드에서도 동일** — `.claude/agents/af-cross-review.md` 등 deliberation/Step 4 합의 단계에서 코덱스 호출이 있다면 thread 연속 패턴 사용. 미적용 시 점검·수정 대상.
- 정확한 인용: 1라운드 결과를 paraphrase 말고 원문 그대로 thread context에 남게 한다.

**기준일:** 2026-04-30. 라운드 1·2를 모두 `codex` 새 thread로 호출했다가 사용자에게 "그건 진짜 합의가 아니다"라고 지적받음.
