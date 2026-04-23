# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-04-21 00:12
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Two reviewers surfaced 7 distinct findings (1 rejected). No Critical issues, but 3 High-severity findings require documented mitigations before merge.

---

### Aggregated Findings (7 total, 1 rejected)

#### 1. [ACCEPT] [High] `deliverables` 타입 미검증 — non-list 시 문자 단위 순회
- **Critic**: `for _deliv in (_mod.get("deliverables") or [])` — LLM이 str 반환 시 각 문자가 패턴으로 등록되어 ledger 오염
- **Cross**: not flagged directly, but finding 3 (fallback dedup) relies on same loop being correct
- **Judgment**: Python의 `str or []` 는 비어있지 않은 문자열이면 str 자체를 반환하므로 iteration은 문자 단위. 실제 LLM 응답이 string deliverable을 반환하는 엣지케이스는 충분히 현실적.
- **Action Required**:
  ```python
  _delivs = _mod.get("deliverables")
  if not isinstance(_delivs, list):
      _delivs = []
  for _deliv in _delivs:
  ```

#### 2. [ACCEPT] [High] Partial run이 모든 모듈/deliverable에 failure를 기록
- **Critic**: not flagged
- **Cross**: `_succeeded = status == "completed"` — `partial`/`stopped_max_cycles`/`crashed` 시 모든 패턴에 failure 기록. `dynamic_orchestrator.py:1011-1014`에서 단일 subtask 실패 시 `partial` 세팅됨.
- **Judgment**: 강한 증거. `project_task_board.py:543-563`에 모듈별 status가 있음에도 project-wide `_succeeded` 단일 플래그로 모든 기록을 덮어씀. 장기적으로 role selection을 빠르게 편향시킴.
- **Action Required**: 모듈별 board status를 읽어 개별 성공/실패 판정하거나, non-completed 런에서는 positive signal만 기록.

#### 3. [ACCEPT] [High] Ledger가 planned owner를 학습 (실행 owner 아님)
- **Critic**: not flagged
- **Cross**: `prepared.role_plan["modules"][*]["owner_role"]`은 승인 후 `implementation-tasks.md` 편집으로 변경될 수 있으나 refresh 없음. `work_item_parser.py:239-242`가 task owner_role을 재작성함.
- **Judgment**: 강한 증거 — `sync_board_from_work_items()` 호출 이후에도 `prepared.role_plan`은 stale 상태. 학습 데이터가 실제 실행 owner와 달라질 수 있음.
- **Action Required**: synced board 또는 reloaded final board에서 owner를 읽어 기록.

#### 4. [ACCEPT] [Medium] `lookup_best_role` 매칭-등록 패턴 불일치
- **Critic**: 긴 deliverable 문장 등록 시 짧은 쿼리로 miss 발생 가능. `dp in lowered` vs `any(tok in lowered...)`의 비대칭.
- **Cross**: not flagged
- **Judgment**: `strategy_ledger.py:202`의 매칭 로직과 등록 단위가 맞지 않으면 B2-4 fix의 효과가 반감됨. Critic의 분석이 코드 증거와 일치.
- **Action Required**: 등록 패턴을 토큰 단위로 짧게 유지하거나, 매칭 로직을 등록 방식에 맞게 조정.

#### 5. [ACCEPT] [Medium] Fallback deliverable 반복으로 sample threshold 조기 충족
- **Critic**: not flagged
- **Cross**: `project_task_board.py:444`에서 missing deliverable을 project-level fallback으로 채움 → 동일 패턴이 여러 모듈에서 반복 → 단일 프로젝트로 3 sample 충족 (`strategy_ledger.py:203-208`)
- **Judgment**: 강한 증거. 단일 런으로 학습이 고정될 수 있음.
- **Action Required**: 프로젝트 런 단위로 `(pattern, owner_role)` 중복 제거 후 기록.

#### 6. [ACCEPT] [Low] `_patterns` 중복 검사 O(n²)
- **Critic**: `list`의 `not in`이 O(n) → deliverables가 많으면 이중 루프로 O(n²)
- **Cross**: not flagged
- **Judgment**: 현재 데이터 규모에서 실질적 영향은 미미하나 `set` 교체로 비용 없이 해결 가능.
- **Action Required**: `_patterns_seen: set[str]` 추가하여 dedup, `_patterns: list[str]`는 순서 유지용으로 병행.

#### 7. [ACCEPT] [Low] Strategy-ledger 피드백 루프 테스트 커버리지 없음
- **Critic**: not flagged
- **Cross**: `tests/test_project_pipeline.py:84-235`가 ledger 내용 또는 후속 `_pick_owner_role()` 동작을 검증하지 않음.
- **Judgment**: 위 findings 1-5의 regression이 현재 테스트로는 감지 불가.
- **Action Required**: ledger 내용 + 후속 planning pass를 검증하는 integration test 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `deliverables` 타입 미검증 | High | ACCEPT | Critic |
| 2 | Partial run → 전체 failure 기록 | High | ACCEPT | Cross |
| 3 | Planned owner 학습 (stale) | High | ACCEPT | Cross |
| 4 | lookup 매칭-등록 불일치 | Medium | ACCEPT | Critic |
| 5 | Fallback deliverable threshold 조기 충족 | Medium | ACCEPT | Cross |
| 6 | `_patterns` dedup O(n²) | Low | ACCEPT | Critic |
| 7 | Ledger 피드백 루프 테스트 없음 | Low | ACCEPT | Cross |

---

### Recommendations

- **즉시 수정 (merge 전)**: Finding 1 (`isinstance` 가드) — 코드 1줄, 위험 확실
- **단기 수정**: Finding 2 (모듈별 status 기반 success/failure 분리) + Finding 3 (synced board에서 owner 읽기)
- **중기**: Finding 4 (패턴 등록 단위 정책 결정) + Finding 5 (run-level dedup)
- **백로그**: Finding 6 (set 교체) + Finding 7 (integration test)