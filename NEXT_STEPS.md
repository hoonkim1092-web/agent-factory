# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-15 KST** — P4.5b Agent Model Selection runtime 완료. 다음 진입점 = **backlog (F15 또는 cross-review WARN)**.

---

## 🏠 Mac PC 재개 절차

```bash
cd <repo>/agent-factory     # 본 repo (main 브랜치)
git pull
python start_db.py agent-factory   # Supabase → 로컬 메모리 pull
git status -sb
```

그 다음 이 파일 "🔥 다음 진입점" 섹션부터 읽으면 됨.

---

## 🔥 다음 진입점 — backlog

**브랜치**: `main`

### 완료된 것들 (이번 세션)
- ✅ **F10** git-context 주입 — `_collect_git_context()` + 3개 provider `[Git State]` 섹션
- ✅ **E2E smoke** — claude_cli 실제 실행 → `BRANCH=af-on-af/round1-hook-fix COMMIT=056096b` 정확 출력
- ✅ **main 머지** — ff-only `056096be`, Round 1~4 전체 포함
- ✅ **F6** tempdir cleanup — `atexit.register(shutil.rmtree, isolated, True)` in `_maybe_isolate_project_root_for_self_run()`. Codex PASS.
- ✅ **P4.5b** Agent Model Selection runtime — `select_model()` + `_detect_escalation_triggers()` + `check_model_escalation.py` hook + 65 tests PASS. 3-tier PASS (WARN-only)

### 나머지 backlog (우선순위 순)
- **F15** workspace↔internal-state 분리 — provider_cwd 별도 param (M, 옵션 D)
- **cross-review WARN #2/#3** — registry_manager pre-existing 결함
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
