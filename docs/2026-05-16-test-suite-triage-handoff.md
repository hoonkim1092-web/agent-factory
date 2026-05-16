# 2026-05-16 — 테스트 수트 분류(triage) 핸드오프

> **목적**: /clear 후 이 문서만 읽고 작업을 그대로 재개한다. 워킹트리에 미커밋 변경 9개가 있는 상태에서 작성됨.

---

## 1. 발단

이전 세션에서 AF CLI dogfooding을 시도 → CLI가 registry write 단계에서 막힘 → dogfooding을 중단하고 **수동 테스트 수리(manual rescue)** 로 전환. registry 관련 수정은 커밋 `d77e5766` ("fix(tests): stale mock + AF_DISABLE_REGISTRY_WRITE gate in 3 test files")로 완료. 그 이후 추가로 테스트 3개를 더 손대면서 scope가 넓어진 상태.

---

## 2. 현재 워킹트리 (미커밋 9개)

| 파일 | 성격 | 처리 |
|------|------|------|
| `tests/test_skill_retrieval_engine.py` | 테스트 수정 (정당) | **커밋 대상** |
| `tests/test_sync_wrappers.py` | 테스트 수정 (정당) | **커밋 대상** |
| `tests/test_text_integrity.py` | 테스트 수정 (정당) | **커밋 대상** |
| `Master_Blueprint.md` | hook이 §12에 자동 생성한 무의미 entry 4줄 | **커밋 제외** |
| `data/skill-usage.jsonl` | 런타임 append-only 이벤트 로그 | **커밋 제외** |
| `docs/code_review/code-review.md` | hook 자동 append ("Review skipped") | **커밋 제외** |
| `skill-eval-report.json` | `written_at` timestamp만 변경 | **커밋 제외** |
| `skills/new_skill/skill-eval-report.json` | 동일 | **커밋 제외** |
| `skills/new_skill/skill-promotion.json` | `feedback_total_events` +3 | **커밋 제외** |

---

## 3. 확정 타임라인 (git 검증 완료)

```
8e1a8acf  "feat: next-gen skill lifecycle pipeline"
          → skill_retrieval_engine.py + test_skill_retrieval_engine.py 동시 생성
          → 이 시점 엔진엔 enhance 모드 없음 (ranked_reuse / shadow_reuse / forge 3개뿐)

294ce411  "release: codex-5.4 — next-gen features"  (2026-03-23)
          → 엔진에 enhance 모드 + enhance_confidence=0.70 + CapabilityGap dataclass 추가
          → ❌ test_skill_retrieval_engine.py 갱신 누락

(이후 ~8주)  test 2건 RED 방치 — 강제 게이트 부재로 아무도 모름
```

검증 방법: `git stash` 후 HEAD 테스트 실행 → `test_..._medium_confidence_candidate`,
`test_..._reranks_..._feedback_history` **2건 실제 FAIL 확인**. 2026-03-23 이후 줄곧 red.

**판정**: `294ce411`의 `enhance` 모드는 `CapabilityGap` dataclass / `_analyze_capability_gap()` /
`threshold_enhance` 필드까지 동반한 **설계된 기능** — 사고로 끼어든 변경이 아님.
→ 워킹트리의 테스트 수정은 "regression 추종"이 아니라 **누락된 테스트 갱신을 따라잡는 정당한 수정**.

---

## 4. 3개 테스트 — 최종 판정 (전부 정당)

| 파일 | 수정 방식 | 근거 |
|------|----------|------|
| `test_skill_retrieval_engine` test 1 | 입력 `top_score` 70→65 | 70은 이제 enhance 밴드[0.70,0.85). 테스트 이름이 "medium/shadow_reuse"이므로 입력을 65로 내려 **의도 보존**. 출력만 바꿨으면 이름이 거짓이 됨. |
| `test_skill_retrieval_engine` test 2 | 출력 `shadow_reuse`→`enhance` | 이 테스트 본질은 reranking 검증. `candidate_skill_id`/`used_historical_signal`/`ranked_candidates[0]`/`base_score==82` 4개 핵심 단언은 그대로 통과. mode는 부수 단언. score=82는 정당하게 enhance. |
| `test_sync_wrappers` | `@pytest.mark.skipif(sys.platform != "win32")` | `.cmd` 래퍼는 Windows 전용. macOS엔 파일 자체가 없음. |
| `test_text_integrity` | subprocess에 `PYTHONPATH` env 주입 | 자식 프로세스가 repo 모듈을 못 찾던 격리 문제. |

검증: 수정 후 `pytest tests/test_skill_retrieval_engine.py tests/test_sync_wrappers.py
tests/test_text_integrity.py` → **10 passed, 2 skipped**.

---

## 5. 진짜 발견 (분류 작업보다 중요)

> **테스트 2건이 2026-03-23부터 ~8주간 red 방치 → 테스트 수트가 CI/pre-commit에서
> 강제 실행되지 않고 있다.** d77e5766(3개) + 워킹트리(3개) = 최소 6개 테스트 파일이 부패해 있었음.

dogfooding의 실제 산출물 = "테스트를 고쳐라"가 아니라 **"강제 게이트 부재 + 런타임
산출물의 git 오염"**. dogfooding 진단은 이미 끝났으므로 재실행해도 같은 벽 — 새 정보 없음.

부수 발견: `enhance` 밴드와 `_analyze_capability_gap()` gap 서브로직(`gap_ratio` 분기)은
**전용 테스트가 전무**. `294ce411`부터의 pre-existing 테스트 갭.

---

## 6. 다음 세션 실행 계획

### Step 1 — 커밋 분리 (즉시)
테스트 3개만 stage, 산출물 6개 제외. **3개를 한 커밋으로** (전부 "썩은 테스트 수트 복구" 동일 범주 — 분리하면 churn).

```bash
git add tests/test_skill_retrieval_engine.py tests/test_sync_wrappers.py tests/test_text_integrity.py
git commit -m "fix(tests): catch up skill_retrieval test to 294ce411 enhance mode + platform/env guards"
```
- `.py` 없는 산출물 6개는 커밋 안 함 → 게이트는 `.py` 테스트 수정만 보므로 Tier 분류 확인 필요
  (`scripts/review_gate.py --debug`). 테스트 파일만이면 Tier 1(af-test-runner).

### Step 2 — 산출물 git 오염 차단 (backlog)
`data/skill-usage.jsonl`, `skill-eval-report.json`, `skills/new_skill/*.json`을 `.gitignore`에
추가할지 결정. 단 `skills/new_skill/`이 의도된 산출 스킬이면 `*-report.json`/`*-promotion.json`만
선별 제외. 결정 전 `git log --oneline -- skill-eval-report.json`로 과거에 커밋돼 왔는지 확인.

### Step 3 — Master_Blueprint §12 hook 잡음 (backlog)
hook이 비-코드 편집에도 §12에 "chore: edit: tests/... — Master_Blueprint.md, skill-usage.jsonl..."
같은 무의미 entry를 자동 생성 중. hook 로직 점검 대상. (메모리 `feedback_blueprint_section3_manual` 참고)

### Step 4 — dogfooding 재시작은 보류
CLI 자체 blocker(registry write 등)가 풀리기 전엔 재실행 = 토큰 낭비. 진단 완료 상태.

---

## 7. 한 줄 요약

테스트 3개 수정은 전부 정당(검증 완료) → 한 커밋. 산출물 6개는 커밋 제외.
진짜 문제는 "테스트 수트 강제 게이트 부재 + 런타임 산출물 git 오염" 2건 — 이게 다음 우선순위.
