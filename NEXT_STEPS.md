# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-15 KST** — F10 완료 + E2E smoke 통과 + main 머지 완료. 다음 진입점 = **F6 tempdir cleanup**.

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

## 🔥 다음 진입점 — F6 tempdir cleanup

**브랜치**: `main` (af-on-af/round1-hook-fix → main ff-merge 완료, 2026-05-15)

### 완료된 것들 (이번 세션)
- ✅ **F10** git-context 주입 — `_collect_git_context()` + 3개 provider `[Git State]` 섹션
- ✅ **E2E smoke** — claude_cli 실제 실행 → `BRANCH=af-on-af/round1-hook-fix COMMIT=056096b` 정확 출력
- ✅ **main 머지** — ff-only `056096be`, Round 1~4 전체 포함

### F6 — tempdir cleanup (Size S)

**문제**: `af_self_run_*` 임시 디렉터리가 self-run마다 생성되지만 정리되지 않아 누적.

**Fix 방향**: 생성 시 `atexit.register(shutil.rmtree, tmpdir, ignore_errors=True)` 등록.

**진입 전 확인**:
```bash
ls /tmp/af_self_run_* 2>/dev/null | wc -l   # 누적 개수
grep -rn "af_self_run\|mkdtemp\|TemporaryDirectory" core/ | grep -v ".pyc"
```

### 나머지 backlog (우선순위 순)
- **P4.5b** Agent Model Selection — runtime model 선택. 진입 전 `[Model Routing]`(provider routing)과 책임 경계 grep + rename 권장
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
