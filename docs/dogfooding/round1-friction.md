# Round 1 Dogfooding — 마찰 메모

> **목적**: AF로 AF 개발 (hook 버그 fix)을 진행하면서 답답한 지점·우회·재작업을 **실시간 append**.
> 회고는 `round1-completion.md`에서.
>
> **기록 형식**: `[YYYY-MM-DD HH:MM] [분류] 한 줄 설명`
> **분류 4개**:
> - `review-gate` — review-gate / hook BLOCK·우회
> - `doc-sync` — 코드와 문서 동시 편집·동기화 어려움
> - `context` — 토큰/컨텍스트 부족, 재읽기
> - `expertise` — 전문성 부족·재학습

---

## 마찰 로그

- [2026-05-14 22:05] [review-gate] `docs/2026-05-14-dev-workflow-paradigm-shift.md` 생성 직후 design-review hook이 자동 발화 → `docs/reviews/2026-05-14-220501-...-design-review.md` 부산물 생성. **Round 1 fix 대상 버그 실시간 재현.** 사용자가 직전 세션에서 같은 증상 보고했고, 이번 세션 브랜치 분기 직후 동일 패턴 재현.
- [2026-05-14 22:05] [review-gate] 이전 세션 hook 부산물 4개가 untracked로 남아있음 (`.codex/agents/`, `docs/reviews/2026-05-14-0724*`, `docs/reviews/2026-05-14-0727*`, `docs/work-items/implement-a-browser-poker-game/`). `rm` 권한이 계속 거부됨 → 사용자가 수동 삭제 안내 받고도 미실행 → 작업 시작 전 cleanup 비용 발생.
- [2026-05-14 22:22] [review-gate] LLM이 `rm` 호출 3회 모두 권한 거부 (세션 설정상 차단). 사용자가 `!` prefix로 직접 실행해야 함 → 작업 흐름 끊김. **Round 1 fix와 별개로 `rm` 권한 정책도 dogfooding 마찰 항목**.
- [2026-05-14 22:28] [review-gate] **진단 발견**: 사용자가 보고한 "new-files-added BLOCK"은 `scripts/review_gate.py` line 191이 `.py` 파일만 필터링하므로 `docs/reviews/*.md` 부산물이 직접 원인 아님. 진짜 원인은 다른 hook (`scripts/check_design_pending.py` 등)일 가능성. **Round 1 fix 시작 전 정확한 원인 추적 필요** — paradigm-shift.md 본문의 "review-gate가 new-files-added로 잘못 감지" 가정은 부정확.
- [2026-05-14 22:37] [review-gate] **🎯 진짜 BLOCK 원인 실시간 확정**: 이번 첫 commit (`.py` 0개, 문서만)에서 BLOCK 발생. 원인은 `.af_review_queue/pending_agent_review.json`에 이전 세션 stale `.py` 3개 (`core/utils.py`, `core/hooks/skill_self_evolution.py`, `scripts/project_context_sync.py`) 남아있음. **진짜 패턴**: (1) 이전 세션이 .py 수정 → 큐 enqueue (2) commit 성공해도 큐 정리 안 됨 (post-commit clear 미작동) (3) 다음 세션이 .py 없는 commit 시도 → stale 큐 .py가 검사 대상으로 잡힘 → BLOCK. **Fix 방향**: post-commit clear hook wiring 또는 review_gate.py에서 staged files와 큐 files 교집합만 검사하도록 수정. paradigm-shift.md의 "hook 부산물 잘못 감지" 가정은 **완전 부정확** — Round 1 다음 세션에서 docs/2026-05-14-dev-workflow-paradigm-shift.md §"채택 1" 갱신 필요.
- [2026-05-14 23:50] [review-gate] **확정 원인 — 호출 경로 누락**: `hook_runner.py:496-514`에 `_post_commit_clear` 함수는 존재하지만 호출 경로가 없음. `.claude/settings.json` PostToolUse hook은 `Write|Edit`·`Agent`만 등록 — `Bash` matcher 누락. `.githooks/post-commit` shell hook은 Blueprint/code-review만 처리, 큐 클리어 안 함. 결과: 큐 영구 누적.
- [2026-05-14 23:54] [review-gate] **Fix 적용 + 검증 완료**: `.githooks/post-commit`에 `review_gate.py --clear --files <committed>` 호출 추가 (commit `04ddc207`). 후속 commit 1회에서 `[gate-cleared] committed=1 remaining=0` 로그 확인. 큐 자동 클리어 동작. **시스템 wide** — Claude Code Bash + 사용자 터미널 직접 commit 모두 커버.
- [2026-05-14 23:54] [review-gate] **남은 edge case** (Round 2 후보): 새 commit의 `committed_set`에 포함되지 않는 stale 큐 항목은 여전히 남는다. 예: 큐에 .py A가 남아있는 상태에서 .py B만 commit하면 A는 큐에 영구 잔존. 다음 .py 작업 시 stale review 충돌 가능. **해소안**: `last_round_summary.has_block=false` AND `round_count>0` → `clear_committed_files`가 큐 통째 reset 옵션 추가. Round 2 결정.

---

## 4분류 카운트 (Round 1 종료 시점 분류)

| 분류 | 건수 | 비중 |
|------|-----:|-----:|
| `review-gate` | 7 | 100% |
| `doc-sync` | 0 | 0% |
| `context` | 0 | 0% |
| `expertise` | 0 | 0% |

**해석**: Round 1 마찰은 **100% review-gate 도메인**. dogfooding의 첫 작업 자체가 hook 버그 fix였으므로 편향 있음 (selection bias). 다른 도메인 마찰을 보려면 Round 2에서 비-hook 작업 (예: skill 흡수, 문서 작성) 진행 필요.

**Round 1 종료 조건 (3개 만족):**
1. ✅ hook fix 코드 동작 — `.githooks/post-commit` review_gate --clear 호출, commit `04ddc207` 검증
2. ✅ 후속 commit에서 false positive 0 — `04ddc207` commit pre-commit gate PASS (`no-py-files`)
3. ✅ friction.md 4분류 완료 — 위 표
