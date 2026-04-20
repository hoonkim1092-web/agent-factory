# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-04-19 08:34
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

BLOCK 기준(Critical) 없음. Medium 3건 — 머지 가능하나 아래 조치 권고.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] 싱크 후 `.todo.md` / 태스크 실행 계획이 stale 상태로 남음
- **Critic**: not flagged
- **Cross**: "execute()는 board만 갱신하고 `.todo.md`와 `task_execution_plan.md`는 prepare() 시점 값 그대로 유지. DynamicOrchestrator가 stale `.todo.md`를 주입할 수 있음."
- **Judgment**: `core/project_pipeline.py:726-729`에서 prepare 시 한 번 생성, `core/dynamic_orchestrator.py:337-369`에서 그대로 소비. 보드는 업데이트되지만 orchestrator가 읽는 tactical 문서는 갱신되지 않아 작업 불일치 위험이 실재함.
- **Action Required**: `write_project_board()` 호출(L933) 직후 `write_project_todo(workspace, board_todo_items(updated_board), board=updated_board)` 및 `write_task_execution_plan(...)` 재생성 추가.

#### 2. [ACCEPT] [Medium] `target_path` 플로우 회귀 테스트 부재
- **Critic**: not flagged
- **Cross**: "`tests/test_project_pipeline.py`는 `workspace == doc_root` 케이스만 검증. `target_path` 설정 시의 prepare→approve→execute 경로는 무커버."
- **Judgment**: 이번 버그(`workspace` 대신 `doc_root` 사용)가 테스트로 잡히지 않았으므로 동일 영역의 회귀를 방지하려면 테스트가 필수.
- **Action Required**: `target_path`가 절대 경로인 케이스를 커버하는 회귀 테스트 추가. `target_path/docs/work-items/<slug>/implementation-tasks.md` 편집 → gate approve → execute → `workspace/project_board_state.json` 반영 확인.

#### 3. [ACCEPT] [Medium] `doc_root` 읽기 / `workspace` 쓰기 비대칭 — 문서화 부재
- **Critic**: "sync는 `doc_root`에서 읽고 board는 `workspace`에 기록 — `doc_root != workspace`면 경로 분산. 의도된 설계라면 명시 필요."
- **Cross**: "board는 workspace-scoped 제어 아티팩트이므로 이동 불필요. 비대칭 자체는 올바름." (REJECT)
- **Judgment**: 두 리뷰어가 결론(비대칭 유지)에 동의하나 Critic은 미래 혼란을 우려. Cross의 근거(`load_project_board`·`DynamicOrchestrator`가 모두 `workspace` 기준)가 명확하므로 비대칭은 정당하다. 단, 코드 주석 없이 향후 유지보수자가 같은 혼란을 반복할 위험은 실재함.
- **Action Required**: `PreparedProject` dataclass 주석(L58-59) 또는 `execute_prepared` 내 해당 블록에 한 줄 주석 추가 — "board(workspace 기준)와 work-item 문서(doc_root 기준)는 의도적으로 분리된 경로."

#### 4. [HOLD] [Medium] Non-atomic `write_project_board` 쓰기 (M10)
- **Critic**: "C2는 수정됐으나 `write_project_board`의 `open(path,'w')` 직접 쓰기는 잔존. `doc_root` 경로가 활성화돼 실질 노출 증가."
- **Cross**: not flagged
- **Judgment**: 기존 M10 이슈(`code-review.md §3.3`)의 인스턴스. 이번 패치가 새로 도입한 문제는 아니나 실제 파일 경로가 활성화돼 노출이 커진 건 사실. M10 해결 작업과 묶어 처리할지 즉시 수정할지 저자 판단 필요.
- **Question for Author**: M10 해결 타임라인이 정해져 있는가? 단기 내 처리 예정이면 이번 PR에서 제외, 아니면 `write_project_board`만 선제 수정.

#### 5. [ACCEPT] [Low] `_effective_doc_root()` 캡슐화 경계 위반
- **Critic**: "`execute_prepared`가 `PreparedProject` 내부 메서드를 직접 호출. 언더스코어 접두사는 내부 전용을 의미."
- **Cross**: not flagged
- **Judgment**: `_` 접두사 관례 위반. 현재 `gate()`(L68)에서도 동일하게 호출되므로 일관성은 있으나 API 계약이 불명확함. 리팩터링 트리거가 될 수 있는 저위험 smell.
- **Action Required**: `_effective_doc_root` → `effective_doc_root`로 공개 메서드 승격(또는 `@property doc_root`로 노출).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 싱크 후 `.todo.md` stale | Medium | ACCEPT | Cross |
| 2 | `target_path` 회귀 테스트 부재 | Medium | ACCEPT | Cross |
| 3 | doc_root/workspace 비대칭 문서화 부재 | Medium | ACCEPT | Both |
| 4 | Non-atomic board 쓰기 (M10) | Medium | HOLD | Critic |
| 5 | `_effective_doc_root` 캡슐화 위반 | Low | ACCEPT | Critic |

---

### Recommendations

- **즉시**: `execute_prepared` 내 `write_project_board()` 호출 후 `.todo.md` + `task_execution_plan.md` 재생성 추가 (finding 1)
- **즉시**: `target_path` 분기 회귀 테스트 추가 (finding 2)
- **즉시**: doc_root/workspace 비대칭 의도를 코드 주석 1줄로 명시 (finding 3)
- **즉시**: `_effective_doc_root` → public 메서드로 승격 (finding 5)
- **M10 이슈 트래킹**: `write_project_board` atomic 쓰기 미결 — M10 해결 범위에 포함 확인 필요 (finding 4)