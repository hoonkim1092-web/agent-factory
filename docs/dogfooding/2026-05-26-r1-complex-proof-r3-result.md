# R1 3차 복합 증명 결과 (2026-05-26)

> **실험 목적**: P6 AI executor 연결 후 end-to-end AI 코딩 검증  
> **선행 실험**: `docs/dogfooding/2026-05-25-r1-complex-proof-result.md` (2차)

---

## 실험 설계

| 항목 | 값 |
|------|-----|
| 태스크 | `core/utils.py`에 `clamp(value, min_val, max_val)` 추가 + `tests/test_clamp_utils.py` 신규 |
| 실행 커맨드 | `python agent_launcher.py dogfood run <task> --non-interactive --merge never` |
| 실험 run_id | `1779725735-c6a2a2cf` |

---

## 결과 — P6 AI executor 부분 성공, BLOCKED(VERIFY 실패)

| 검증 항목 | 결과 |
|-----------|------|
| AI executor (P6) 호출 | ✅ claude_cli 4회 실행 |
| `core/utils.py` clamp 추가 | ✅ AI가 실제로 함수 작성 (worktree에 unstaged) |
| `tests/test_clamp_utils.py` 생성 | ❌ 미생성 |
| scope 격리 | ⚠️ docs/*.md 수정 (scope leak) |
| VERIFY 통과 | ❌ BLOCKED — verification_requirements=[] |
| pipeline COMPLETE | ❌ BLOCKED (max 3 attempts) |

---

## 핵심 발견

### ✅ P6 AI executor 동작 확인

worktree `core/utils.py`에 `clamp()` 함수가 실제로 추가됨:
```python
def clamp(value: int | float, min_val: int | float, max_val: int | float) -> int | float:
    """value를 [min_val, max_val] 범위로 제한한다. min_val > max_val이면 ValueError."""
    if min_val > max_val:
        raise ValueError(f"잘못된 범위: min_val({min_val}) > max_val({max_val})")
    ...
```

단, clamp가 두 번 추가됨 (중복). AI task description이 불충분.

---

## 발견된 버그 3개 (이번 세션 수정 완료)

### F-SCOPE-CLARIFICATION (spec_compiler.py) — **수정 완료**

- **현상**: spec.scope = `["경계값 + 타입(int/float) + 잘못된 범위 전체"]` — 파일 경로 아닌 서술문
- **원인**: `_scope_from_clarification_log()`의 `_PATH_RE` (단순 `/` 검사)가 `(int/float)` 안의 `/`를 경로 구분자로 인식
- **수정**: `_PATH_TOKEN_RE` (known-extension 토큰 추출)으로 교체 + `//` URL 필터 추가
- **커밋**: `ad9ed9ac`

### F-VERIFY-EMPTY (planner.py) — **수정 완료**

- **현상**: `verification_requirements: []` → F-PHASE-COMPLETE 가드 → 항상 VERIFY 실패 → BLOCKED
- **원인**: spec.success_criteria=[], premortem 리스크에 verification command 없음
- **수정**: `build_plan()` fallback — scope 파일 경로에서 `_test_file_for()` 파생 → pytest 명령 자동 생성
- **커밋**: `ad9ed9ac`

### P5 fix (dogfood.py) — **수정 완료**

- **현상**: `test_implement_uses_worktree_cwd` 테스트 실패 (NotADirectoryError)
- **원인**: SHA 캡처 시 cwd 미존재 예외 미처리
- **수정**: `OSError/FileNotFoundError` guard 추가
- **커밋**: `ad9ed9ac`

---

## 부수 발견 — cross-platform 인코딩 이슈

실험 실행 시 CP949 콘솔에서 다수 인코딩 오류 발생 → 같은 세션에서 수정:

| 파일 | 수정 |
|------|------|
| `core/providers/cli.py` | 이모지 → ASCII (🚀→`start`, ✅→`done`, ❌→`failed`) |
| `core/dogfood.py` | `_default_command_runner` + `_git()` UTF-8 env |
| `agent_launcher.py` | `_configure_cli_text_streams()` + `_utf8_subprocess_env()` |
| `core/provider_detect.py` | subprocess encoding=utf-8 |

---

## 파이프라인 단계별 관측

| 단계 | 결과 | 비고 |
|------|------|------|
| INTERVIEW | ✅ | clarification 4라운드 (claude_cli 1번 16s) |
| RESEARCH_BRIEF | ✅ | 내용 생성됨 |
| RESEARCH | ✅ | — |
| SPEC | ⚠️ | scope: 서술문 (F-SCOPE-CLARIFICATION) |
| PREMORTEM | ✅ | — |
| PLAN | ⚠️ | steps: 1개, verification_requirements: [] |
| ISOLATE | ✅ | worktree 격리 성공 |
| IMPLEMENT (P6) | ✅ | AI executor 호출, core/utils.py 수정됨 |
| VERIFY | ❌ | F-VERIFY-EMPTY: commands=[] → guard fail |
| REVIEW | ❌ | retry×2 → block |
| BLOCKED | — | — |

---

## 다음 실험 (R1 4차) 예상 결과

수정 후 예상 흐름:
1. `_scope_from_clarification_log` → `core/utils.py`, `tests/test_clamp_utils.py` 올바른 경로 추출
2. `build_plan()` fallback → `verification_requirements: ["python -m pytest tests/test_utils.py -v"]`
3. IMPLEMENT: AI가 clamp 구현 + 테스트 파일 생성
4. VERIFY: pytest 실행 → PASS → COMPLETE

---

## R1 복합 증명 누적 판정

| 실험 | 달성 |
|------|------|
| 1차 (2026-05-21) | PASS — 1파일 단순 docstring |
| 2차 (2026-05-25) | FAIL — plan 공백, scope leak |
| 3차 (2026-05-26) | PARTIAL — P6 AI executor 동작 확인 ✅, VERIFY 미통과 |
| **4차** | **목표: end-to-end COMPLETE** |
