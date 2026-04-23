# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-04-21 01:01
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Critical 없음. High 4건, Medium 2건. BLOCK 없으나 merge 전 High 항목 수정 권고.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] INFRA 실패가 모든 역할의 fail_count를 오염시킴

- **Critic**: `_succeeded = status == "completed"` 단일 플래그가 `_batch` 전체에 적용 — 인프라 크래시 1회로 수십 개 `(pattern, owner)` 쌍의 fail_count 누적
- **Cross**: not flagged (이전 교차검증 Finding 1 ACCEPT와 동일 이슈)
- **Judgment**: diff에서 `_succeeded` 계산 로직 변경 없음. `stopped_max_cycles`, `partial`, `crashed`는 역할 배정 실패가 아님에도 학습 데이터에 반영된다. 이전 리뷰 ACCEPT 후 미수정.
- **Action Required**: INFRA 실패 시 `record_role_batch` 호출 skip:
  ```python
  if not _succeeded and FailureClassifier.is_infra(status):
      pass
  else:
      _ledger.record_role_batch(_batch)
  ```

#### 2. [ACCEPT] [High] `deliverables` 항목이 dict일 경우 AttributeError 크래시

- **Critic**: `list(_mod.get("deliverables") or [])` 순회 시 항목이 dict이면 `_raw.strip()`에서 AttributeError
- **Cross**: not flagged
- **Judgment**: diff line `+                for _raw in [str(_mod.get("name") or "")] + list(_mod.get("deliverables") or []):` — `name`은 `str()` 캐스팅하지만 deliverables 항목은 그대로 순회. YAML에서 dict 항목은 흔함.
- **Action Required**: `[str(d) for d in (_mod.get("deliverables") or [])]`로 교체

#### 3. [ACCEPT] [High] 승인된 deliverable 편집이 ledger에 반영되지 않음

- **Critic**: not flagged
- **Cross**: `execute()`가 `prepared.role_plan["modules"]`에서 기록하지만, 사용자 승인 시 편집하는 `feature-plan.md`·`implementation-design.md`는 재로드되지 않음
- **Judgment**: `agent_launcher.py:343-347`이 사용자에게 해당 파일 편집을 안내하고, `work_item_parser.py:180-212`는 `implementation-tasks.md`·`feature-spec.md`만 재파싱함. 학습 데이터가 초안 기준으로 기록되는 구조적 결함.
- **Action Required**: `record_role_batch()` 호출 전 승인된 work-item 문서에서 training input 갱신, 또는 실제 실행에서 소비하는 파일로 승인 범위 제한

#### 4. [ACCEPT] [High] approval-time owner_role 편집으로 undispatchable 태스크 + false `completed`

- **Critic**: not flagged
- **Cross**: `implementation-tasks.md` 편집으로 원본 `role_plan["roles"]`에 없는 owner_role 도입 가능 → `_materialize_roles()`가 해당 role을 프로비저닝하지 않아 태스크 영구 미배정, 오케스트레이터가 `completed`로 종료
- **Judgment**: `work_item_parser.py:239-242` → `core/project_pipeline.py:946-953` → `_materialize_roles():476-566` → `core/project_task_board.py:658-661` → `dynamic_orchestrator.py:1011-1014` 경로가 코드로 추적됨. 실패 없이 완료 처리되므로 탐지 불가.
- **Action Required**: board sync 후 모든 태스크 `owner_role`을 materialized role set에 대해 검증, 미등록 role 발견 시 fast-fail

#### 5. [ACCEPT] [Medium] `_seen` 범위가 모듈 단위 — cross-module 중복 `_batch` 삽입

- **Critic**: `_seen`이 `for _mod` 루프 내부에서 초기화되어 모듈 간 중복 제거 안 됨
- **Cross**: not flagged
- **Judgment**: diff에서 `_seen: set[str] = set()`이 모듈 루프 안에 위치함 확인. 동일 deliverable 텍스트를 가진 모듈이 여럿이면 `(pattern, owner)` 중복 삽입 → 임계치 조기 달성.
- **Action Required**: `_seen: set[tuple[str, str]] = set()`을 모듈 루프 밖으로 이동, key를 `(_dp, _owner)`로 변경

#### 6. [ACCEPT] [Medium] 배치 실패 로그에서 컨텍스트 소실

- **Critic**: 기존 `logger.warning("strategy ledger 기록 실패 [%s]: %s", _pattern, _exc)` → `"배치 기록 실패: %s"` 로 변경되면서 영향 항목 수·owner_role 정보 소실
- **Cross**: not flagged
- **Judgment**: diff에서 직접 확인. 운영 디버깅 영향.
- **Action Required**: `logger.warning("strategy ledger 배치 기록 실패 (entries=%d, first=%s): %s", len(_batch), _batch[0] if _batch else None, _exc)`

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | INFRA 실패 → fail_count 오염 | High | ACCEPT | Critic |
| 2 | deliverables dict → AttributeError | High | ACCEPT | Critic |
| 3 | 승인 편집이 ledger에 미반영 | High | ACCEPT | Cross |
| 4 | undispatchable task + false completed | High | ACCEPT | Cross |
| 5 | `_seen` cross-module 중복 미제거 | Medium | ACCEPT | Critic |
| 6 | 배치 실패 로그 컨텍스트 소실 | Medium | ACCEPT | Critic |

---

### Recommendations

- **즉시 수정 (merge 전)**: Finding 2 (AttributeError) — 1줄 fix, 런타임 크래시 방지
- **즉시 수정 (merge 전)**: Finding 1 (INFRA 오염) — `FailureClassifier.is_infra()` 조건 추가
- **즉시 수정 (merge 전)**: Finding 5 (`_seen` 범위) — `_seen` 선언을 루프 밖으로 이동
- **단기 수정**: Finding 3·4 (approval-time 문서 불일치) — 구조적 설계 이슈, 별도 이슈 트래킹 필요
- **단기 수정**: Finding 6 (로그 컨텍스트) — 1줄 fix