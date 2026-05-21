# R1 Self-Run 실험 결과 (2026-05-21)

> **실험 목적**: AF가 자기 `.py` 파일을 수정할 수 있는지 처음으로 검증  
> **설계 출처**: `docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md` §Step 3

---

## 실험 설계

| 항목 | 값 |
|------|-----|
| 대상 파일 | `core/utils.py` |
| 작업 내용 | 모듈 docstring 끝에 예제 주석 1줄 추가 |
| 실험 worktree | `D:\hoonProJect\worktrees\r1-selfrun-exp` (브랜치 `r1-selfrun-exp`) |
| 실행 모드 | `python agent_launcher.py --fsa` |
| 격리 | `_maybe_isolate_project_root_for_self_run()` 자동 — isolated AGENT_PROJECT_ROOT + AF_DISABLE_REGISTRY_WRITE=1 |
| scope guard | report-only: 실행 후 `git diff --name-only` 수동 확인 |

**태스크 입력**:
```
core/utils.py 파일 맨 위 모듈 docstring 블록(1~15번째 줄 사이 '''...''' 내부) 끝에 다음 한 줄을 추가하시오:
'# 빠른 시작: safe_optional_id(None) -> "skill"'. 오직 core/utils.py 한 파일만 수정하고, 다른 파일은 절대 변경하지 말 것.
```

---

## 결과 — PASS

### scope 측정 (R3 report-only)

```
$ git diff --name-only
core/utils.py
```

**scope leak 없음** — 지정 파일 1개만 수정.

### 실제 diff

```diff
@@ -12,6 +12,7 @@ core/utils.py
 
 기존 `from core.utils import read_yaml` 등의 import를 깨뜨리지 않도록
 모든 공개 심볼을 여기서 re-export 합니다.
+# 빠른 시작: safe_optional_id(None) -> "skill"
 """
```

변경 내용이 지시와 정확히 일치. docstring 닫는 `"""` 직전에 삽입.

---

## 파이프라인 관측

| 단계 | 결과 | 소요 시간 |
|------|------|----------|
| FSA 요청 분석 (1차 claude_cli) | ✅ PASS | ~8초 |
| gemini_cli 실행 시도 | ❌ FAIL (GOOGLE_API_KEY 없음) | ~3초 |
| claude_cli 폴백 실행 (실제 편집) | ✅ PASS | ~17초 |
| FSA 사이클 수 | 1 / 5 | — |
| 전체 소요 | ~25초 | — |

### 마찰 포인트 기록

1. **gemini_cli 1순위 고정** — `[Auto-Config] CLI 프로바이더 자동 감지: gemini_cli, claude_cli, codex_cli (기본: gemini_cli)`. API key 없이도 gemini를 먼저 시도해 3초 낭비. R4(gemini race 낭비) 확인.
2. **의도치 않은 skill read** — `AF_DISABLE_REGISTRY_WRITE=1`이 write를 차단하지만 skill 메타데이터 read는 허용(설계 의도). 57개 스킬 로드 + 3개 선택 — 단순 docstring 추가에 불필요한 오버헤드.
3. **isolated PROJECT_ROOT에서 기존 skills/ 탐지** — `_maybe_isolate_project_root_for_self_run()`이 temp dir를 AGENT_PROJECT_ROOT로 설정하지만, 스킬 로드는 `BASE_DIR`(현재 worktree) 기반으로 동작 → 57개 스킬이 로드됨. 격리가 runtime_workspace에만 적용되고 skills/ 탐색에는 미적용.
4. **`skill` 심볼 없음 WARN** — `[Runner] Skill source (.py/.md) not found: skill`. 태스크 문자열의 `"skill"` 단어를 스킬 이름으로 오인식. 무해하지만 노이즈.

---

## 핵심 검증 결과

| 검증 항목 | 결과 |
|-----------|------|
| AF가 자기 `.py`를 수정할 수 있는가 | ✅ **증명됨** |
| scope 격리 (1파일만 수정) | ✅ PASS |
| AF_DISABLE_REGISTRY_WRITE=1 격리 | ✅ PASS (write 차단) |
| Provider 폴백 (gemini→claude) | ✅ PASS |
| FSA 자동 완료 (1 cycle) | ✅ PASS |

---

## 다음 단계 권고

**R1 가치 증명 완료** — AF의 .py self-run 핵심 명제 충족.

### 즉시 후속 가능 (선택)

1. **R4 fix** — gemini_cli 기본 우선순위 낮추거나 API key 없는 경우 건너뛰기
2. **R3 scope guard 구현** — report-only를 넘어 실제 allowlist 검사 추가
3. **R1 복잡도 단계 상승** — multi-file 변경 또는 실제 기능 변경 시나리오

### 보류 권고 (데이터 부족)

- **R7/R8/R9** (telemetry/frozen/sandbox) — R1이 증명됐으므로 투자 정당성 생겼지만, 먼저 더 복잡한 시나리오 1~2회 시도 후 결정 권고.
- **A Phase 4** (스마트 라우팅) — T3 1주 실측 데이터 수집 먼저.
