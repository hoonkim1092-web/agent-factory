# R1 복합 증명 결과 (2026-05-25)

> **실험 목적**: multi-file 변경 시나리오에서 dogfood pipeline end-to-end 검증  
> **선행 실험**: `docs/dogfooding/2026-05-21-r1-selfrun-result.md` (1파일, 단순 docstring)

---

## 실험 설계

| 항목 | 값 |
|------|-----|
| 태스크 | `core/utils.py`에 `clamp()` 함수 추가 + `tests/test_clamp_utils.py` 신규 생성 (2파일) |
| 실행 커맨드 | `python agent_launcher.py dogfood run <task> --non-interactive --merge never` |
| 실험 run_id | `1779695091-53de9311` |
| dogfood_branch | `dogfood/1779695091-53de9311` |
| dogfood_commit | `9b432c61` |

---

## 결과 — 형식적 COMPLETE, 기능적 FAIL

| 검증 항목 | 결과 |
|-----------|------|
| pipeline phase=complete | ✅ 달성 |
| 태스크 완성 (`core/utils.py` clamp 추가) | ❌ FAIL — 파일 미수정 |
| scope 격리 (지정 2파일만 수정) | ❌ FAIL — `syncCompyne/` scope leak |
| plan steps 생성 | ❌ FAIL — `steps: []` (빈 plan) |
| artifacts 내용 생성 | ❌ FAIL — research_brief/spec/plan 모두 빈 구조 |

---

## 실제 worktree 변경 내용

```
dogfood commit 9b432c61에 포함된 변경:
  run_output.txt                       | 134 +++---
  syncCompyne/AGENTS.md                |  96 ++--
  syncCompyne/LOG_COMMANDS.md          |  38 +-
  syncCompyne/PROJECT_LOG.md           | 142 +++---
  syncCompyne/WORKSPACE_CONTEXT.md     | 162 +++----
  syncCompyne/memory_store.py          | 388 ++++++++--------
  syncCompyne/project_log_cli.py       | 282 ++++++------
  syncCompyne/workspace_context_cli.py | 850 +++++++++++++++++------------------
```

`core/utils.py`, `tests/test_clamp_utils.py` — **미수정**.

`run_output.txt` 내용:
```
python factory_manager.py "Japanese Restaurant Master Chef" > run_output.txt
```
AI가 worktree 내 `syncCompyne/` 프로젝트를 발견, 내부 `factory_manager.py`를 실행.

---

## 발견된 구조적 버그 4개

### F-DIRTY (수정 완료)
- **현상**: `planning/interview_brief.json`이 `core/interview.py:26`에서 workspace에 직접 생성 → ISOLATE dirty 검사 실패
- **수정**: `.gitignore`에 추가 (`f896eeb9`)

### F-PLAN-EMPTY
- **현상**: `research_brief`, `spec`, `plan` artifacts 모두 빈 구조(`steps: []`, `scope: []`)
- **원인**: AI 생성 파이프라인(RESEARCH_BRIEF → RESEARCH → SPEC → PREMORTEM → PLAN)이 실질적 내용 없이 통과
- **영향**: IMPLEMENT 단계가 no-op (steps 없음)

### F-SCOPE-LEAK
- **현상**: VERIFY/REVIEW 단계에서 AI가 `syncCompyne/`(다른 프로젝트) 파일 수정
- **원인**: worktree에 여러 프로젝트 디렉토리 존재, scope guard가 방지하지 못함
- **영향**: 의도치 않은 파일 변경이 dogfood commit에 포함됨

### F-PHASE-COMPLETE
- **현상**: 빈 plan + 태스크 미완성에도 `phase=complete` 달성
- **원인**: 완료 기준(`completion_criteria: []`) 공백, VERIFY가 실질적 검증 없이 통과
- **영향**: pipeline COMPLETE가 task COMPLETE를 보장하지 않음

---

## 파이프라인 관측

| 단계 | 결과 | 비고 |
|------|------|------|
| INTERVIEW | ✅ | artifact 생성됨 |
| RESEARCH_BRIEF | ⚠️ | `questions: [], risk_hints: []` 빈 구조 |
| RESEARCH | ⚠️ | 내용 미확인 |
| SPEC | ⚠️ | `scope: [], success_criteria: []` 빈 구조 |
| PREMORTEM | ⚠️ | 내용 미확인 |
| PLAN | ⚠️ | `steps: []` 빈 구조 |
| ISOLATE | ✅ | worktree 격리 성공 |
| IMPLEMENT | ✅ (no-op) | steps 없어서 아무것도 실행 안 함 |
| VERIFY | ❌ scope leak | AI가 syncCompyne/ 수정 |
| REVIEW | 미확인 | — |
| FINALIZE | ✅ | — |
| MERGE | ✅ | merge_mode=never 적용 |
| COMPLETE | ✅ | — |

---

## 다음 단계 권고

이 실험은 pipeline의 구조적 약점을 노출했습니다. 우선순위 순:

1. **F-PLAN-EMPTY 진단**: 왜 AI 생성 단계들이 빈 구조를 반환하는지 확인
   - `core/research_brief.py`, `core/spec_compiler.py`, `core/planner.py` — LLM 호출 경로 grep
   - non-interactive 모드에서 LLM 호출이 실제로 이루어지는지 확인

2. **F-SCOPE-LEAK 완화**: worktree scope guard 강화
   - R3 scope guard (`AF_SCOPE_GUARD_PATHS`)가 VERIFY 단계에서 작동하는지 확인
   - `syncCompyne/`처럼 tracked되지 않아야 할 프로젝트 디렉토리 정리

3. **F-PHASE-COMPLETE 수정**: task 완성도 검증 추가
   - `completion_criteria`가 비면 VERIFY가 실패하도록 가드 추가

---

## R1 복합 증명 판정

**기능적 FAIL** — 형식적 pipeline COMPLETE는 달성했지만 실제 task는 수행되지 않았고 scope leak이 발생했습니다.

단, R1 자기실험(2026-05-21)과 비교:
- R1 실험(단순, 1파일): PASS — 지정 파일만 수정, 내용 정확
- R1 복합(multi-file): FAIL — plan 공백, scope leak

→ **복잡도 상승 시 파이프라인 안정성 저하** 확인. 복합 증명 달성 전 F-PLAN-EMPTY 수정이 선행 필요.
