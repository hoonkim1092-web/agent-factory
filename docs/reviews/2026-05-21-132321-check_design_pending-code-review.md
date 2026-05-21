# Code Review: check_design_pending

> Source: scripts/check_design_pending.py
> Date: 2026-05-21 13:23
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: PASS

변경 범위는 docstring 1줄 + `print()` 안내 문자열 1줄로, CLAUDE.md `2026-05-01 정책`(단일 설계문서 → af-cross-review 1개만)에 hook 출력을 사후 정렬한 surgical fix. 큐 로직(`_load_fired`/`_save_fired` atomic write, debounce, 필터)·실행 분기·subprocess·파일 I/O 어느 것도 손대지 않았고, 두 리뷰어 모두 Critical/High 결함 0건. 잔존 지적은 모두 Low/advisory.

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] 변경된 hook 출력 계약에 대한 회귀 테스트 부재
- **Critic**: not flagged
- **Cross**: `.claude/settings.json:79`가 hook 경로로 이 스크립트를 호출하고 `CLAUDE.md:118`이 "정확히 af-cross-review 1개"를 요구하나, `tests/*check_design_pending*` 또는 `[af-design-review-pending]` 어서션 없음 (rg 확인)
- **Judgment**: 두 번째 리뷰어만 지적했으나 증거가 강하다. 실제 emit 경로(`main()` → stdout)가 테스트되지 않으면 향후 메시지 회귀(예: 누군가 다시 "af-critic + af-cross-review"로 되돌리는 경우) 탐지 불가. 이미 G/R 격차로 식별됐던 정책-구현 표류가 ~20일 지속된 전례가 있음(`docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md:120-121`).
- **Action Required**: `tests/test_check_design_pending.py` 신설 — `.af_review_queue/pending/design/*.json`에 오래된 `timestamp` 픽스처를 두고 `main()` 호출, stdout이 `af-cross-review`를 포함하고 `af-critic + af-cross-review`는 포함하지 않음을 어서트. (이번 PR 또는 즉시 후속 PR)

#### 2. [HOLD] [Low] CLAUDE.md "1개만" 어휘와 hook 메시지 표현 불일치 (다중 인스턴스 오해 여지)
- **Critic**: `"af-cross-review 에이전트를 실행해주세요"`는 "**1개만**" 강조가 빠져, Tier 3가 외부 프로바이더 fan-out하는 점과 결합되면 운영자가 "여러 af-cross-review 인스턴스"로 오해할 수 있음
- **Cross**: not flagged
- **Judgment**: 단일 리뷰어 지적이고 동작 차이는 없으나, 어휘 정렬은 1-line 변경으로 가능. 다만 finding #1 테스트 작성 시 어서트 문자열을 어떻게 잡을지와 묶인 문제라 함께 결정하는 게 합리적.
- **Question for Author**: 메시지를 `"af-cross-review **1개만** 실행해주세요"`로 정렬할지, 아니면 현재 문구 유지하고 finding #1 테스트만 추가할지?

#### 3. [ACCEPT] [Low] 불필요한 f-string 접두사 (변경된 라인의 자기 흔적)
- **Critic**: 변경 후 L153에 `{}` placeholder가 없는데도 `f"..."` 잔존 (위 L152 모방). CLAUDE.md "Surgical Changes"상 본인이 새로 작성한 라인이므로 정리 가능
- **Cross**: not flagged
- **Judgment**: 동작 차이 0, 순수 cosmetic. ACCEPT하되 별건으로 처리해도 무방한 trivial 정리.
- **Action Required**: `print(f"...")` → `print("...")` (옵션, finding #2와 함께 처리 권장)

#### 4. [REJECT 유지] hardcoded path 중복 & watcher 미정렬
- **Critic**: 다른 설계 문서들에 옛 "2-agent 병렬" 표현 잔존 — **본 PR 범위 밖, 수정 불필요**로 명시 (Info)
- **Cross**: (a) `.af_review_queue/pending/design` 하드코딩 — REJECT (현재 `core/design_review_utils.py:82-84`와 일치, hook은 의도적 lightweight), (b) `design_review_watcher.py:260`이 여전히 critic+cross 실행 — REJECT (다른 실행 경로, 본 변경은 manual UserPromptSubmit 안내만 정렬)
- **Judgment**: 두 리뷰어 모두 본 PR 범위 밖이라 결론. 동의.
- **Action Required**: 없음. (별도 work-item으로 분리 — Critic이 가리킨 `docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md:120-121` G/R 격차 추적으로 충분)

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | hook 출력 회귀 테스트 부재 | Medium | ACCEPT | Cross |
| 2 | "1개만" 어휘 정렬 | Low | HOLD | Critic |
| 3 | 불필요한 f-string 접두사 | Low | ACCEPT | Critic |
| 4 | hardcoded path / watcher 미정렬 | — | REJECT | Both (out-of-scope) |

### Recommendations

- **즉시 (이번 PR 또는 즉시 후속)**: `tests/test_check_design_pending.py` 추가 — `[af-design-review-pending]` stdout 어서트로 메시지 회귀 차단 (finding #1).
- **함께 결정**: finding #2 어휘 정렬 여부를 결정한 뒤 테스트의 정확한 어서트 문자열을 그것에 맞춰 작성. 정렬하기로 하면 finding #3 `f"..."` → `"..."` 정리도 같은 1줄 편집에 포함.
- **별도 work-item**: 옛 설계 문서의 "2-agent" 표현과 `design_review_watcher.py` 동작 정합성은 본 PR과 분리 — 이미 `docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md` G/R 격차로 추적 중.
- **현 상태로 머지 가능**: 두 리뷰어 모두 PASS / 신규 결함 0건. 정책-구현 표류를 정확히 봉합한 surgical 변경.