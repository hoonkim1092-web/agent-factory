# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-15 KST** — F16 완료 후 Mac PC 인계 준비. 다음 진입점 = F10.

---

## 🏠 Mac PC 재개 절차

```bash
cd <repo>/agent-factory     # worktree 또는 본 repo
git pull
python start_db.py agent-factory   # Supabase → 로컬 메모리 pull
git status -sb              # baseline dirty projects/agent_factory/* 는 sync 산출물 — touch 금지
```

그 다음 이 파일 "🔥 다음 진입점 — F10" 섹션부터 읽으면 됨.

---

## 🔥 다음 진입점 — F10 git-awareness fix (scope 조사 완료, 구현 대기)

**브랜치**: `af-on-af/round1-hook-fix`. origin sync 상태는 `git status -sb`로 확인 (이 파일에 sync 여부 기재 금지 — F10 메타 함정).

### F10 문제
AF self-run이 provider에 넘기는 prompt에 git context가 없어, 생성 문서(NEXT_STEPS 등 handoff doc)가 git reality와 어긋남 (Round 4b 사례).

### F10 scope 조사 결과 (이번 세션 완료 — 재조사 불필요)
- **Prompt 중앙 함수**: `core/providers/cli.py:548 _compose_prompt(request, spec, system_prompt)` — 3개 provider(gemini/claude/codex_cli) 모두 통과
- **현재 주입**: `[Workspace]` / `[System Prompt]` / `[Task]` — git context 없음
- **Fix size**: **S** (M 추정에서 다운). 1 파일 ~30-50줄 + 3-5 tests

### F10 fix 옵션 (사용자 미결정 — Mac에서 결정)
| 옵션 | 내용 | Size |
|------|------|:--:|
| **A (권장)** | `_compose_prompt`에 `[Git State]` 섹션 자동 주입 (HEAD hash + log -5 + status -sb). 비-git workspace graceful fallback | S |
| B | 옵트인 flag `AF_INJECT_GIT_CONTEXT=1` | S+ |
| C | `get_git_state` tool 등록 | M |

옵션 A 주입 형식 제안:
```
[Git State]
HEAD: <short hash> on <branch>
Recent commits:
  <hash> <subject> ...
Working tree: <git status -sb>
```

### 최근 commit (이번 세션, origin 반영)
| Hash | 의도 |
|------|------|
| `6f95c4fa` | F16 — test registry isolation (conftest AF_DISABLE_REGISTRY_WRITE + abc fixture cleanup) |
| `b2d35578` | F17 — split user workspace from runtime state |
| `b3fe6bb8` | empty-argv NameError — lazy import prompt_mission_template |
| `8ad6ea4b` | Round 4d FAIL 기록 + F17 신규 |
| `75adb845`/`78e6a4be` | F12 architectural isolation + hardening |
| `f62c52e2` | P4.5x — F3/F8 fix |
| `06a58d5c` | P4.5a — agent default model + escalation 정책 |

### 그 외 backlog (우선순위 순)
- **F6** tempdir cleanup — `af_self_run_*` 누적, atexit hook (S)
- **P4.5b** Agent Model Selection — runtime model 선택. 진입 전 기존 `[Model Routing]`(provider routing)과 책임 경계 grep + rename 권장
- **F15** workspace↔internal-state 분리 — provider_cwd 별도 param (M, 옵션 D)
- **cross-review WARN #2/#3** — registry_manager pre-existing 결함
- **AF main 머지 결정** — `af-on-af/round1-hook-fix` → main (사용자 직접 결정)
- 전체 `pytest` fastapi 미설치 환경 이슈 (별개)

---

## 📜 과거 이력

세션별 누적 이력은 [docs/session-log/2026-05-15-rounds-1-2-3.md](docs/session-log/2026-05-15-rounds-1-2-3.md), dogfooding 마찰 F0~F17은 [docs/dogfooding/round4-af-cli-friction.md](docs/dogfooding/round4-af-cli-friction.md) 참고.

- Round 1~4e dogfooding (2026-05-14~05-15)
- P5 DomainVerdict / P4.5a model routing / P4.5x F3·F8 / F12 isolation+hardening / F16 test isolation / F17 workspace split — 모두 완료
- Phase A/B/C, ADR M1~M5, P1~P4, Question Router Stage 0 등 — session-log 파일 참조

---

## 세션 종료 체크리스트

1. 완료 작업 / 다음 진입점 갱신
2. `git commit` → `git push`
3. `python end_db.py agent-factory`
