# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-11 01:35
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Cross Review provider errored (Codex CLI session init only, no findings produced). All aggregated findings derive from Critic Review alone. Per aggregation rule #2: single-reviewer findings are ACCEPT when evidence is strong — all four findings have clear diff evidence.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] `_refine_document`의 `timeout_sec`가 실제 LLM 호출에 전달되지 않음

- **Critic**: "`_refine_document(content, feedback, project_brief, timeout_sec=iter_timeout)` 호출 시 `iter_timeout` 계산은 존재하지만 `ControlPlaneLLM.generate(prompt)` 시그니처는 `prompt` 하나만 받아 값이 완전히 무시됨 — dead parameter 패턴"
- **Cross**: provider error로 미평가
- **Judgment**: diff에서 `_refine_document` 시그니처에 `timeout_sec: int = 120`이 추가됐고 (`+    timeout_sec: int = 120`), 호출부에서 `timeout_sec=iter_timeout`을 전달하지만, 함수 내부 `llm.generate(prompt)` 호출은 변경 없음. `iter_timeout` 계산 블록 전체가 효력 없는 dead code. 증거가 명확하므로 ACCEPT.
- **Action Required**: `ControlPlaneLLM.generate(prompt, timeout_sec=120)` 시그니처에 파라미터 추가 후 내부에서 `concurrent.futures` thread + `future.result(timeout=timeout_sec)`으로 래핑, **또는** `_refine_document` 내부에서 직접 thread timeout 강제 적용.

---

#### 2. [ACCEPT] [Medium] `time.sleep(_GRACE_SEC)` 무조건 실행 — Stage 2 정상 완료 시에도 5초 고정 손실

- **Critic**: "Stage 2 futures 정상 완료(`timeout_fallback=False`) 시에도 sleep이 실행됨. Stage 2 over-budget 상황에서는 총 실행 시간이 `TOTAL_BUDGET + 5`초로 늘어남"
- **Cross**: 미평가
- **Judgment**: diff에 `time.sleep(_GRACE_SEC)` 추가가 조건 없이 삽입됨. `DocGenerationResult.timeout_fallback` 필드가 이미 존재하므로 조건부 sleep이 가능. ACCEPT.
- **Action Required**:
  ```python
  if spec_result.timeout_fallback or design_result.timeout_fallback:
      time.sleep(_GRACE_SEC)
  ```

---

#### 3. [ACCEPT] [Medium] `_build_episode_hints_section`이 Stage 1 예산 내부로 이동, deadline 미적용

- **Critic**: "원래 `t_total_start` 이전에 호출되어 Stage 예산 밖이었으나, `_exec_stage1` 내부로 이동 후 `deadline_1` 안에서 실행됨. 함수 내부는 `deadline` 파라미터 없이 비동기 에피소드 매칭 실행 — 느린 경우 Stage 1 carry-over 잠식"
- **Cross**: 미평가
- **Judgment**: diff에서 `-    episode_hints_section = _build_episode_hints_section(project_brief, workspace)` 라인이 `t_total_start` 이전에서 제거되고, `_exec_stage1` 내부에 `+    hints_section = _build_episode_hints_section(project_brief, workspace)` 추가됨. deadline 전파 없이 이동. ACCEPT.
- **Action Required**: `generate_work_items`에서 `t_total_start` 이전으로 pre-fetch 복원, **또는** `_build_episode_hints_section`에 `deadline` 파라미터 추가 후 thread timeout 래핑 적용.

---

#### 4. [ACCEPT] [Low] `_extract_section_outline` mismatch 시 `return ""` — 부분 outline 전체 폐기

- **Critic**: "11개 섹션 등 부분 mismatch 시 `return ""`로 tasks generator에 spec 구조가 전혀 전달되지 않음. 부분 outline이 없는 것보다 낫다"
- **Cross**: 미평가
- **Judgment**: diff에 `+        return ""` 추가. `_generate_and_refine`이 `prev_spec_outline`을 falsy 체크로 제외하는 로직과 결합 시 부분 spec 정보가 완전 손실됨. ACCEPT.
- **Action Required**: `section_idx == 0`일 때만 `return ""`하고, 그 외는 mismatch 경고 후 수집된 부분 outline 반환.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `timeout_sec` dead parameter in `_refine_document` | High | ACCEPT | Critic |
| 2 | Unconditional `time.sleep(_GRACE_SEC)` in Stage 2→3 transition | Medium | ACCEPT | Critic |
| 3 | `_build_episode_hints_section` moved inside Stage 1 without deadline | Medium | ACCEPT | Critic |
| 4 | `_extract_section_outline` returns `""` on partial mismatch | Low | ACCEPT | Critic |

---

### Recommendations

- **필수 (BLOCK 해소)**: Finding 1 — `ControlPlaneLLM.generate`에 `timeout_sec` 파라미터 추가 또는 `_refine_document` 내부 thread-with-timeout 래핑. 현재 deadline-aware `iter_timeout` 계산 전체가 무효.
- **권장 수정**: Finding 2 — `spec_result.timeout_fallback or design_result.timeout_fallback` 조건 추가로 정상 완료 경로의 5초 고정 손실 제거.
- **권장 수정**: Finding 3 — `_build_episode_hints_section` pre-fetch를 `t_total_start` 이전으로 복원, 또는 deadline 전파 적용.
- **선택적 수정**: Finding 4 — `section_idx == 0` 조건으로 return "" 범위 제한.
- **Cross Review 재실행 고려**: 이번 라운드 Cross Review가 provider error로 공백. Finding 1 수정 후 재검증 시 Cross Review 정상 실행 확인 권장.