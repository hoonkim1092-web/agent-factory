# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-15 KST** — F10 구현 완료. 다음 진입점 = Tier 자동화 또는 AF main 머지 결정.

---

## 🏠 Mac PC 재개 절차

```bash
cd <repo>/agent-factory     # worktree 또는 본 repo
git pull
python start_db.py agent-factory   # Supabase → 로컬 메모리 pull
git status -sb              # baseline dirty projects/agent_factory/* 는 sync 산출물 — touch 금지
```

그 다음 이 파일 "🔥 다음 진입점" 섹션부터 읽으면 됨.

---

## 🔥 다음 진입점 — post-F10 결정 (AF main 머지 vs 계속 개발)

**브랜치**: `af-on-af/round1-hook-fix`. 

### F10 완료 내역
- ✅ `core/providers/cli.py`: `_collect_git_context()` 헬퍼 추가 (~48줄)
- ✅ `_compose_prompt()`: 3개 provider 분기에 git context 주입
- ✅ `tests/test_cli_providers.py`: 5개 테스트 추가
- ✅ 기존 테스트 회귀 없음 (35 passed, 2 skipped)

### 그 외 backlog (우선순위 순)
- **AF main 머지 결정** — `af-on-af/round1-hook-fix` → main (사용자 직접 결정). 지금 머지할 시점인가?
- **F6** tempdir cleanup — `af_self_run_*` 누적, atexit hook (S)
- **P4.5b** Agent Model Selection — runtime model 선택. 진입 전 기존 `[Model Routing]`(provider routing)과 책임 경계 grep + rename 권장
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
