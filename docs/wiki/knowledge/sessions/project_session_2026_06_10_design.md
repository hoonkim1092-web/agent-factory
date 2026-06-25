---
name: project_session_2026_06_10_design
description: 2026-06-10 세션 — 자가진화 fitness 게이트 설계 + provider rate-limit 스킵 설계+구현 완료. 다음=fitness 게이트 구현 또는 다른 work-item.
metadata: 
  node_type: memory
  type: project
  originSessionId: 4099ec60-d119-4b84-9c4a-72611a523941
---

2026-06-10 세션 산출물.

**설계 2건** 작성·커밋·푸시 완료 (`f99f0235`, 브랜치 `2026-06-04-right-sized-execution-slice1`). 외부 교차검증은 codex usage limit(6/11 10:31 KST 해소)으로 생략(single-vendor).

**✅ provider rate-limit 스킵 구현 완료** (`29df9555`, 2026-06-10, Sonnet)
- S1+S2+S3 전부 구현. `ProviderState.RATE_LIMITED` / `mark_rate_limited()` / `detect_rate_limit_signal()` / `_apply_rate_limit_override()` / `review_runner._run_provider` ok=True 위장 경로 포함 배선 / `af-cross-review.md` 케이스 1b+Step 2b.
- 3-Tier: af-critic WARN-2(advisory) / af-cross-review BLOCK-2→fixed(use_cache=False 경로 + ok=True 위장 경로) / af-test-runner PASS(53+1). INV-1~9b 14건 신규.
- **다음 = 자가진화 fitness 게이트 구현(S1 먼저) 또는 skewness 신규 함수 커밋(utils.py에 이미 있음).**

**설계 1 — 자가진화 fitness 게이트** (`docs/2026-06-10-skill-evolution-fitness-gate-design.md`)
- 문제: 스킬 진화 검증이 "안 망가지면 통과"(contract pass_rate만). `shadow_eval.delta`(baseline A/B 비교)는 계산되나 게이트 미사용. Controller가 baseline 미전달.
- 해법: (1+1) hill climbing — 제안 1개 → 골든셋 전후 비교 → delta>0일 때만 publish. C1(Controller→Gate baseline 배선), C2(shadow delta 게이트+quality_delta 반환), C3(MIN_SHADOW_CASES 소표본 가드).
- cross-review 1라운드 BLOCK 반영 완료: baseline **디렉터리→파일 경로 정규화** 누락(silent fail) 수정 + INV-6에 total_cases>0 assert.
- 슬라이스: S1(shadow delta 배선) / S2(hidden 과적합 탐지) / S3(실패→케이스 축적) / S4(프롬프트 스킬 LLM-as-judge). 한계: 케이스 0개 스킬엔 압력 없음, 프롬프트 스킬 채점기 부재.

**설계 2 — provider rate-limit 스킵** (`docs/2026-06-10-provider-rate-limit-aware-skip-design.md`)
- 문제: codex usage limit이어도 provider_detect는 login만 봐 AVAILABLE 보고 → 반복 헛호출(매회 cross-review 에이전트 ~65k 토큰). limit 사전감지 불가(사후만).
- 해법(사용자 선택 A=SSOT): provider_detect에 `RATE_LIMITED` 상태 + `rate_limited_until` 필드 + `mark_rate_limited()` + detect override + CLI `--mark-rate-limited`/JSON `rate_limited`. 1회 부딪힘→캐시 학습→만료 전 스킵+노티. 자동 복구.
- 슬라이스: S1(provider_detect SSOT) / S2(detect_rate_limit_signal+review_runner 배선) / S3(af-cross-review.md 노티+MCP mark).

**다음 진입점**: `/model sonnet`으로 구현. **rate-limit S1 먼저 권장**(즉효+이후 모든 cross-review 살림). 각 슬라이스 core/ → test-first + af-critic + af-test-runner (af-cross-review는 codex limit 시 SKIP). 관련 [[project_model_routing_facts]] [[feedback_design_review_mandatory]].

**미정리 항목**: LLM Wiki 52개 파일이 **staged 미커밋** 상태로 남음(이전 세션 Codex 작업, 마지막 커밋 4ca329f1 이후, +2639/-233). NEXT_STEPS.md도 그 일부로 staged. 사용자가 "이번 세션만 커밋" 지시 → 설계문서 2개만 분리 커밋(AF_SKIP_REVIEW_GATE=1, index에 이전 .py 남아 게이트 발동했으나 이번 커밋은 .md만). LLM Wiki 덩어리는 커밋 or 폐기 결정 대기. 관련 [[project_af_codebase_wiki_direction]].

## 관련
- [[code/symbols]]

