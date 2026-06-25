---
name: 개발방식 전환 결정 (2026-05-14)
description: AF 메타-재귀 함정 진단, 외부 도구 도입 거절, worktree 병렬+dogfooding+hook-bug-fix 채택, specialist 6명 거절 — 다음 세션 진입점
type: project
originSessionId: 585c206a-cc80-48bd-9c12-d7864c90994a
---
**결정 일자**: 2026-05-14 (Sonnet 4.6)
**상태**: 채택만 됨, 실행 X. 다음 세션 진입점.

## 진단
사용자 "AF 개발 느리고 토큰 소모 큼" → 외부 도구(Harness/Hermes/Oh My OpenAgent) 도입 ROI 음수.
**AF 메타-재귀 함정**: AF는 "에이전트가 에이전트 만드는 시스템"인데 정작 자기 자신은 사람 1명+Claude Code 1세션이 손으로 만듦 → governance(Phase A/B/C, ADR, 3-tier) 무한 증가 → 손 개발 더 느려짐.

## 채택 (우선순위 순)
1. **Hook 부산물이 review-gate 깨는 버그 fix** — 가장 시급. `docs/reviews/2026-*-code-review.md`를 hook이 commit 도중 자동 생성 → review-gate가 "new-files-added"로 잘못 BLOCK → 사용자가 `AF_SKIP_REVIEW_GATE=1` 매번 강제 → 안전장치 무효화.
2. **Worktree 병렬** (`skills/git_worktrees/` 흡수 완료) — 2~3개 worktree 동시 진행. wt-fast-cleanup + wt-dogfood.
3. **AF dogfooding** — `project_pipeline.py`로 AF 자신 dry-run. 실패/마찰 지점 기록만.
4. **af-critic HIGH+ → cross-review 자동 승격** — Codex 제안 중 유일하게 새로운 알맹이.

## 거절
- **6명 specialist team** (Core/Hook/Skill/Memory/QA/Docs Engineer) — 최근 10 커밋 중 5~6개가 cross-cutting (`053efbe0` 7파일, `4851c305`/`a6c08d56`/`f69ff076` 각 4도메인). hand-off 비용 > 효과.
- **외부 도구 본격 도입** — 동일 모델 호출이라 토큰 절약 X. AF governance 우회로 안전성 잃음.

## 팩트 근거 (Codex 제안의 80%가 이미 AF에 있음)
- `scripts/blast_radius.py`: Tier 1/2/3 자동 분류 (subprocess/shell/hook/.codex 자동 Tier 3)
- CLAUDE.md L126-127: Tier 1=af-test-runner만, Tier 2~3=3-tier review-first
- WARN-only no-fire (L131), max_rounds=5 (L129), AF_SKIP_REVIEW_GATE (L132)

**Why**: 사용자가 "동조하지 말고 근거 팩트 기반 의견" 요청 → Codex의 specialist+full-review 제안을 데이터(커밋 cross-cutting 비율)로 반박. 외부 의견에 동조 X, 가짜 흠 X (역방향 sycophancy 메모리 적용).

**How to apply**: 다음 세션 시작 시 NEXT_STEPS.md §"개발방식 전환 결정" 먼저 읽을 것. Hook 버그 fix 먼저 → worktree 셋업 → dogfooding 순. specialist team 제안 다시 나오면 이 메모리의 cross-cutting 데이터로 반박.

---

## Round 1 시작 (2026-05-14, Opus 4.7 세션)

### 채택된 dogfooding 설계 (Codex 협의 결과)
- **변수 0개 baseline**: worktree X, specialist X, fast/default/full mode X, DoD 강화 X
- **측정은 정성 1개**: `docs/dogfooding/round1-friction.md` 실시간 append (4분류: review-gate / doc-sync / context / expertise)
- **시간 측정 X**: 1회 작업 비교는 통계적 noise
- **Round 2 자동 진행 X**: Round 1 마찰 분류 결과에 따라 진행 여부 결정
- **Master_Blueprint.md 갱신**: 평소 100% 패턴이라 baseline 포함 (변수 X). code-review.md는 회귀 패턴 있을 때만 (29% 조건부).

### Round 1 종료 기준 (3개 다 만족)
1. hook fix 코드 동작
2. 후속 N회 commit에서 review-gate false positive 0
3. friction.md를 4분류로 분류 완료

### 진단 수정 (중요)
- 초기 가정: "review-gate가 docs/reviews/*.md를 new-files-added로 잘못 감지"
- 실제: `scripts/review_gate.py` line 191이 `.py`만 필터링 → `.md`는 BLOCK 직접 원인 아님
- 진짜 원인 후보: `check_design_pending.py` / `check_pending_review.py` / `.githooks/pre-commit` / `hook_runner.py`
- **다음 세션 첫 작업**: 위 4 후보 grep으로 BLOCK 출력 코드 찾기

### 브랜치
`af-on-af/round1-hook-fix` (main에서 분기, 첫 commit 전)

### 마찰 메타 발견 (Round 1 시작 전부터)
- LLM이 `rm` 호출 시 권한 차단 → 사용자 `!` 직접 실행 필요 (작업 흐름 끊김)
- `.codex/agents/` 858줄이 git history 없음 (단순 cleanup 시 영구 소실 위험) — staging으로 보존

---

## Round 1+2 종료 (2026-05-15)

### Round 1 fix (commit `04ddc207`)
`.githooks/post-commit`에 `review_gate.py --clear --files <committed>` 호출 추가. **확정 원인**: `_post_commit_clear` 함수는 존재했으나 `.claude/settings.json` PostToolUse `Bash` matcher 미등록으로 호출 경로 없음 → 큐 영구 누적. shell hook 보완으로 시스템 wide 커버.

### Round 2 fix (commit `f1bafcf0`)
`clear_committed_files`에 stale-reset 분기 추가 — `last_round_summary.has_block is False` AND `int(round_count or 0) > 0` AND `round_started_at is None` 3중 가드. forensic 로깅(size·sample·round) + 회귀 테스트 5건. 47 tests PASS.

### dogfooding 정량 데이터 (첫 표본)
- **af-cross-review 1회 비용**: 477s + 77k tokens (4-Round Codex deliberation)
- **가치**: Codex 본인이 PASS → WARN 자기 수정 (비양보 challenge로 4건 advisory 발견 → 전부 surgical 흡수)
- **selection bias**: Round 1+2 마찰 100% review-gate 도메인 (첫 두 라운드 작업 자체가 hook fix였음)

### 발견된 후속 작업 (Round 3 후보)
- **정책-코드 갭**: CLAUDE.md L131 "WARN-only no-fire"가 `review_gate.py:214` `round_count < 2` 조건과 충돌 → round_count=1에서 WARN 흡수 surgical edit이 stale-review BLOCK 유발 → `AF_SKIP_REVIEW_GATE=1` 강제. fix 후보: `last_round_summary.has_block=False` 분기 추가.
- **selection bias 해소**: Round 3는 비-hook 도메인 (skill 흡수·feature 구현·문서 작성) 마찰 측정 필요.

### 브랜치 상태
`af-on-af/round1-hook-fix` (5 commits ahead of origin/main), origin push 완료. main 머지 결정 보류 (사용자 직접 결정).

## 관련
- [[code/symbols]]

