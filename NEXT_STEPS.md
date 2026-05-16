# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-16 KST** — 테스트 수트 분류 완료 + `ae786417` 커밋. 다음 진입점 = **CI pytest stub 수정 (backlog #1)**.

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

## 🔥 다음 진입점 — CI pytest stub 수정

**브랜치**: `main`

> 테스트 수트 분류 완료 (`ae786417`). 다음 우선순위는 CI/테스트 인프라 수정 2건.

### Backlog #1 (다음 세션 첫 액션): CI pytest stub → 실제 테스트 게이트

`.github/workflows/ci.yml`이 pytest를 설치만 하고 실행하지 않음 ("Run Schema Tests" 스텝은 schema import 1줄짜리 stub). 2개 수정 필요:

**수정 A** — `pytest.ini`에 한 줄 추가:
```ini
pythonpath = .
```
(bare `pytest`도 `ModuleNotFoundError: core` 없이 동작하게 — pytest 7.0+ `pythonpath` ini 옵션)

**수정 B** — `ci.yml:43-46` schema stub → 실제 pytest 스텝:
```yaml
- name: Run Tests
  run: |
    python -m pytest -m "not slow and not e2e" -q
```
(`-m "not slow and not e2e"` 필수 — 5개 slow/e2e 마커 테스트가 외부 바이너리 호출)

**주의**: 켜기 전에 `python -m pytest -m "not slow and not e2e" -q` 전체 수트를 로컬에서 1회 돌려 베이스라인 확인 필수. 처음 CI가 빨개지면 회귀 아니라 게이트가 드디어 작동하는 것.

### Backlog #2: 런타임 산출물 git 오염
`data/skill-usage.jsonl`, `skill-eval-report.json`, `skills/new_skill/*.json` — 매 세션 dirty.
`git log --oneline -- skill-eval-report.json`으로 과거 커밋 여부 확인 후 `.gitignore` 선별 추가.

### 완료된 것들 (이번 세션)
- ✅ **F10** git-context 주입 — `_collect_git_context()` + 3개 provider `[Git State]` 섹션
- ✅ **E2E smoke** — claude_cli 실제 실행 → `BRANCH=af-on-af/round1-hook-fix COMMIT=056096b` 정확 출력
- ✅ **main 머지** — ff-only `056096be`, Round 1~4 전체 포함
- ✅ **F6** tempdir cleanup — `atexit.register(shutil.rmtree, isolated, True)` in `_maybe_isolate_project_root_for_self_run()`. Codex PASS.
- ✅ **P4.5b** Agent Model Selection runtime — `select_model()` + `_detect_escalation_triggers()` + `check_model_escalation.py` hook + 65 tests PASS. 3-tier PASS (WARN-only)
  - 🟢 **첫 실동작 확인**: UserPromptSubmit hook이 `packaging_or_frozen_build` 트리거 감지 → `af-test-runner: model='sonnet'` 권장 출력 성공
- ✅ **테스트 수트 분류** (`ae786417`): test_skill_retrieval(294ce411 계약 추종) + test_sync_wrappers(Windows skip) + test_text_integrity(PYTHONPATH 주입). 부수 발견: CI stub + bare pytest 깨짐(pytest.ini pythonpath 미설정)

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
