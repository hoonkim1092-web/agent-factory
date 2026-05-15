# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-15 KST** — Round 4b 산출물 stale 부분 정정 (handoff doc 운영 복구).

---

## 🔥 현재 진행 중 — F12 scope 조사 + dogfooding 보강

**브랜치**: `af-on-af/round1-hook-fix` (origin 동기화됨). Round 4b까지 commit/push 완료. P5/P4.5a/P4.5x/Round4b는 모두 **이미 커밋됨** — pending 작업 없음.

### 최근 commit (origin 반영됨)
| Hash | 의도 |
|------|------|
| `66f80fb0` | Round 4b — AF self-run NEXT_STEPS 분리 SUCCEEDED (execution-path 성공, 산출물 stale은 후수정) |
| `f62c52e2` | P4.5x — F3/F8 fix (agent_launcher argparse + context_schema sentinel cleanup) |
| `a4cb42e9` | Round 4 — AF self-run failure 기록 (F3+F8 차단) |
| `06a58d5c` | P4.5a — agent default model 명시 + escalation 정책 |

### 즉시 다음 작업
1. **F12 scope 조사** (30분 timebox, 80줄 cap, per-path S/M/L 표) — `docs/dogfooding/round4-af-cli-friction.md` 내부 새 섹션.
2. **friction log 보강** — F13 cost / F14 nondeterministic leak / F10 root 메모 / `prompt_mission_template` missing import 기록.
3. **분류 결과에 따라 분기**: 전부 S면 F12 fix 후보 제안, M/L 포함되면 issue/ADR로 이월 + P4.5b로.
4. (이번 turn 외) P4.5b — runtime model selection. 단 기존 `[Model Routing]`(provider routing)과 책임 경계 5분 grep 선행.

### 진입 명령
```bash
cd D:\hoonProJect\worktrees\agent-factory
git pull
python start_db.py agent-factory
git status   # baseline dirty 38건은 start_db sync 결과, touch 금지
```

---

## 📜 과거 이력

세션별 누적 이력은 [docs/session-log/2026-05-15-rounds-1-2-3.md](docs/session-log/2026-05-15-rounds-1-2-3.md) 참고.

- Round 1·2·3 dogfooding 종료 (2026-05-14~05-15)
- P5 DomainVerdict 매트릭스 완료 (2026-05-15)
- P4.5a model routing defaults (2026-05-15)
- Phase A/B/C, ADR M1~M5, P1~P4, Question Router Stage 0, Work-Item 병렬화 v3.1, Phase 2 verdict-label spec, Research Router v1.4.1, AST/LSP 분석 — 전부 위 session-log 파일로 이동.

---

## 세션 종료 체크리스트

1. 완료 작업 / 다음 진입점 갱신
2. `git commit` → `git push`
3. `python end_db.py agent-factory`
