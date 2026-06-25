---
name: feedback-dogfood-pc-handoff
description: PC 이동 시 dogfood run 핸드오프 규칙 — 세션 종료 전 머지 완료 또는 NEXT_STEPS에 PC 식별자 기록 의무.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4e59af23-fda9-4e57-92cd-f6dc84d25bd5
---

PC를 이동하면서 작업할 때 dogfood run을 세션 종료 전에 머지까지 완료하거나, 그러지 못하면 NEXT_STEPS.md에 PC 식별자와 worktree 경로를 명시 기록한다.

**Why:** `dogfood merge <run_id>` 명령은 `~/.af-dogfood/<run_id>/`의 PC-로컬 worktree·`dogfood_state.json`·`merge_report.json`·`dogfood_commit` 해시에 의존한다. 이 디렉토리는 홈 디렉토리 아래에 있고 git/Supabase 동기화 대상이 아니므로 다른 PC에서 회수 불가능하다. 2026-05-27에 Windows PC에서 시작한 R1 11차(`1779867851-3611529e`)가 머지되지 않은 채 Mac으로 자리를 옮긴 사례 — `product()` + `plan_step_count()` + 10건 테스트가 갇혔다. 검증 결론(NEXT_STEPS 본문)과 advisory fix(`9259e2c9`)는 이미 origin에 올라와 있어 결과적으로 회수 가치는 낮았지만, 만약 그 라운드에서 production 코드를 작성했다면 손실이 컸을 것.

**How to apply:**
- dogfood run 시작 시 `hostname` 출력해 현재 PC 식별
- 세션 종료 전 진행 중 dogfood run이 있으면 둘 중 하나:
  1. `python agent_launcher.py dogfood merge <run_id>` + `git push`로 완료 (권장)
  2. NEXT_STEPS.md에 다음 3줄 기록:
     ```
     보류 dogfood run: <run_id>
     발생 PC: <hostname>
     worktree 경로: ~/.af-dogfood/<run_id>/worktree
     ```
- 다른 PC에서 세션 재개 시 NEXT_STEPS.md의 PC 식별자와 현재 hostname 비교. 불일치면 그 라운드 회수 불가 — 새 라운드 시작 또는 해당 PC로 복귀
- 룰 영구화: CLAUDE.md "Dogfood Run PC 핸드오프 규칙" (2026-05-27 추가) 참조

관련: [[project_session_2026_04_16_summary]], [[feedback_no_main_merge_suggestion]]
