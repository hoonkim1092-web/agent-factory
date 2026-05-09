# Code Review: hook_runner

> Source: scripts/hook_runner.py
> Date: 2026-04-17 22:43
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

WARN = 4 Medium findings. No Critical issues; the one-line fix is correct in isolation, but it surfaces a pattern of incomplete fixes across neighboring code.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] 나머지 4개 builtin의 returncode 여전히 0 하드코딩
- **Critic**: `_post_edit_enqueue`, `_post_edit_code_review`, `_post_edit_blueprint`, `_post_edit_design_review` 4곳이 `_log_hook_event(..., 0)` 하드코딩 상태. `subprocess.run()` 결과를 변수에 받지 않아 수정도 불가
- **Cross**: "not flagged" (capture_output 관점에서 동일 함수를 다룸 → 아래 #2)
- **Judgment**: 이번 diff는 `_post_edit_py_compile` 1곳만 수정했으나, 동일 패턴이 4곳에 남아 있다. 반쪽짜리 수정.
- **Action Required**: 각 함수에서 `r = subprocess.run(...)` 으로 결과 수신 후 `_log_hook_event(..., r.returncode)` 전달

#### 2. [ACCEPT] [Medium] `capture_output=True`가 자식 프로세스 진단 출력을 무음 폐기
- **Critic**: "not flagged"
- **Cross**: `capture_output=True` 추가 후 `r.stdout`/`r.stderr`를 읽거나 포워딩하지 않음. `blueprint_updater.py:393`, `code_review_updater.py:269`, `design_review_trigger.py:77` 등이 stderr/stdout에 에러·상태를 출력하는데 모두 사라짐
- **Judgment**: 실패가 silent no-op이 되므로 디버그 불가. 코드 증거 명확.
- **Action Required**: `capture_output=True` 제거하거나, `r.returncode != 0` 시 `r.stderr` 를 `sys.stderr` 로 포워딩

#### 3. [ACCEPT] [Medium] PostToolUse 경로에서 `--no-llm` 미전달
- **Critic**: "not flagged"
- **Cross**: `code_review_updater.py:5-7,260-261` 및 `blueprint_updater.py:375-376` 모두 PostToolUse fast-path로 `--no-llm` 사용을 문서화. 현재 hook_runner는 해당 플래그 미전달
- **Judgment**: 근거 파일·라인 인용이 구체적이고 설정 파일(`.claude/settings.local.json:144-152`)까지 일치. 매 Write/Edit마다 LLM 호출 가능성.
- **Action Required**: `_post_edit_code_review`, `_post_edit_blueprint` subprocess 호출에 `"--no-llm"` 인자 추가

#### 4. [ACCEPT] [Medium] `_extract_file_path()` 가 hook 스택의 나머지 경로 키를 무시
- **Critic**: "not flagged"
- **Cross**: `lsp_check.py:138-144`, `design_review_hook.py:44-50`는 `path`/`file_path`/`filename`/`filepath`/`target` 5종을 지원하지만 신규 파서는 `tool_input.file_path`만 처리. 키 불일치 시 로그 없이 조기 반환
- **Judgment**: 아키텍처 문서(`docs/2026-04-17-...md:344`)도 stdin schema drift를 위험 요소로 명시. 증거 충분.
- **Action Required**: 기존 extractor 패턴(`path`, `filename`, `filepath`, `target` 폴백) 재사용, 빈 값이면 `no_file_path` reason 포함해 로그

#### 5. [HOLD] [Info] 로그 포맷에서 `|` 포함 시 파싱 깨짐
- **Critic**: `_log_hook_event`의 파이프 구분자 포맷에서 `error=str(exc)` 경로에 `|` 포함 시 컬럼 오분리
- **Cross**: "not flagged"
- **Judgment**: 이번 diff와 직접 연관 없고 기존 잠재 버그. 로그 파서 존재 여부가 불확실.
- **Question for Author**: `_log_hook_event` 출력을 소비하는 파서가 있는가? 있다면 즉시 ACCEPT로 격상.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 나머지 4개 builtin returncode 하드코딩 | Medium | ACCEPT | Critic |
| 2 | capture_output=True가 진단 출력 폐기 | Medium | ACCEPT | Cross |
| 3 | PostToolUse에 --no-llm 미전달 | Medium | ACCEPT | Cross |
| 4 | _extract_file_path 키 범위 부족 | Medium | ACCEPT | Cross |
| 5 | 로그 pipe 구분자 파싱 취약 | Info | HOLD | Critic |

---

### Recommendations

1. **즉시**: 4개 builtin 함수에 `r = subprocess.run(...)` 결과 수신 추가 → `_log_hook_event(..., r.returncode)`
2. **즉시**: `capture_output=True` 제거하거나 `r.returncode != 0` 조건으로 stderr 포워딩
3. **다음 커밋**: `_post_edit_code_review` / `_post_edit_blueprint`에 `"--no-llm"` 플래그 추가
4. **다음 커밋**: `_extract_file_path()` 에 `path`/`filename`/`filepath`/`target` 폴백 추가, 미발견 시 reason 포함 로그
5. **보류**: 로그 파서 유무 확인 후 `|` 이스케이프 여부 결정