---
name: feedback-tier3-no-sycophancy
description: "Tier 3(af-cross-review) 비양보 원칙 — 동조 금지+깊이 분석+팩트 기반. multi-provider 공통(claude/codex/gemini/이후 추가). 사용자 입력 없이 항상 강제. 2026-05-14 합의."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3e766f20-8a0f-4d51-806b-84639ea9e38b
---

# Tier 3 비양보 원칙 — 영구 강제 (multi-provider)

Tier 3 교차검증(af-cross-review) 모든 라운드에서 다음 원칙을 사용자가 프롬프트로 매번 입력하지 않아도 항상 적용한다:

**"동조하지 말고 깊게 분석하라. 고민해서 논리적으로, 근거를 팩트로 이슈를 제기하라."**

## Why
사용자가 매번 프롬프트에 직접 박는 것은 비효율이고 누락 위험이 크다. 본 원칙은 cross-review가 "어떤 외부 AI가 말했으니까 OK", "관용적 AI 패턴이라 OK" 식의 표면 동조로 흐르는 것을 방지하기 위해 만들어졌다. 2026-05-14 사용자 합의로 영구 강제됨. **AF는 멀티 프로바이더(`claude_cli`/`codex_cli`/`gemini_cli` + 향후 추가) 구조이므로 본 원칙은 특정 vendor 전용이 아니라 fan_out 전체에 공통 적용**된다 — 2026-05-14 후속 보강.

## How to apply
1. **에이전트 정의에 박혀 있음** — `.claude/agents/af-cross-review.md` 상단 "⚠️ 비양보 원칙" 섹션(provider-agnostic) + Step 2a 공용 리뷰 프롬프트 `[비양보 원칙 — 무조건 적용 / 모든 외부 리뷰어 공통]` 블록.
2. **공용 프롬프트 단일 출처 유지** — Step 2a `/tmp/af-review-prompt.txt` 하나로 모든 fan_out 프로바이더가 같은 프롬프트를 받는다. provider별 별도 프롬프트를 만들면 원칙이 누락되므로 금지.
3. **신규 프로바이더 추가 시** — Step 2의 신규 분기를 추가하더라도 공용 프롬프트 파일을 재사용해야 한다. 새 분기에서 자체 프롬프트를 작성하지 마라.
4. **provider 권위 평등** — codex_cli 발언이 gemini_cli보다, 또는 그 반대가 자동으로 더 무겁지 않다. 라운드별 코드 근거 강도만이 판정 가중치를 결정한다.
5. **새 세션에서도 자동 적용** — 에이전트 호출 시 위 정의가 로드되므로 별도 프롬프트 추가 불필요.
6. **사용자에게 절대 되묻지 마라** — "동조 금지 원칙 적용할까요?"는 금지. 무조건 적용.
7. **Tier 2(af-critic)에는 별도 합의 없음** — 본 원칙은 Tier 3 한정. critic 확장이 필요하면 사용자에게 별도 확인.
8. **수정 시 사용자 승인 필요** — 본 원칙을 약화/삭제하는 변경은 사용자의 명시적 지시가 있을 때만.

## 검증 방법
- `grep "비양보 원칙" .claude/agents/af-cross-review.md` → 2회 hit (Claude 오케스트레이터 섹션 + 공용 리뷰 프롬프트 블록).
- 두 위치 모두 특정 provider명("Codex 전용", "Gemini 한정")으로 좁혀져 있지 않은지 확인 — multi-provider 톤 유지가 본 합의의 핵심.
- Tier 3 응답에서 verdict 산출 시 "근거 없는 동의" 라벨이 들어가면 위반.
