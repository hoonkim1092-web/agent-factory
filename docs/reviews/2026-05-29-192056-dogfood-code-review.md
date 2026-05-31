# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-29 19:20
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

5개 허용(ACCEPT) + 0개 보류(HOLD). Critical 없음. Medium/High 2개 포함으로 WARN.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Auto-merge 경로에서 plan-derived `allowed_paths` 우회
- **Critic**: not flagged
- **Cross**: "`_run_merge_phase()`가 `MergePolicy`를 직접 생성해 `allowed_paths`가 비어있다. `run_all(..., merge_mode='auto_policy')` 경로에서 plan allowlist builder가 실행되지 않아 IMPLEMENT 단계 커밋이 scope_violations 검사를 통과할 수 있다."
- **Judgment**: Cross만 flagged했지만 증거가 강함. `core/dogfood.py:998-1018` plan-based allowlist 빌더는 `policy is None`일 때만 실행되고, `_run_merge_phase()`는 `policy is None`이 아닌 새 `MergePolicy`를 직접 전달한다. `_check_merge_policy()`의 `allowed_paths` 검사는 비어있으면 pass-through. 이 경로는 실제 운영 병합 시 scope 경계를 무력화할 수 있음.
- **Action Required**: `build_merge_policy(state, mode)` 공용 헬퍼를 추출하거나 `_run_merge_phase()` 내에서 `state.merge_mode = merge_mode` 세팅 후 `merge_dogfood_branch(state)`를 호출해 manual/auto 경로가 동일한 plan-derived policy를 사용하게 수정.

---

#### 2. [ACCEPT] [Medium] `merge_mode` 임의 문자열 허용 — fallthrough로 auto 동작
- **Critic**: not flagged
- **Cross**: "`run_all()`이 `merge_mode: str`을 받아 `'never'`/`'manual'` 외 임의 값이 auto merge 브랜치로 fall-through. CLI는 제약하지만 직접 호출자·테스트는 `'foo'`나 `'manual '`을 전달할 수 있다."
- **Judgment**: Cross만 flagged, 증거 명확. `DogfoodState.merge_mode`에 저장 후 `_run_merge_phase()`로 전달되는 흐름 확인. 입력 경계 검증 부재.
- **Action Required**: `create_run()` 또는 `run_all()` 진입부에서 `merge_mode in {"auto_policy", "manual", "never"}` 검증 추가. `MergePolicy.__post_init__()`에도 동일 enum 검증.

---

#### 3. [ACCEPT] [Medium] `read_phase_trace` — `UnicodeDecodeError` / `OSError` 미처리
- **Critic**: "`read_text()`가 던지는 `UnicodeDecodeError`(partial UTF-8 write 후 파일 절단)와 `OSError`(권한/락)를 catch하지 않는다. `_append_phase_trace`의 non-atomic write 후 파일 절단 시 `json.JSONDecodeError`가 아닌 `UnicodeDecodeError`가 발생해 silent drop 의도가 무력화된다."
- **Cross**: not flagged
- **Judgment**: Critic만 flagged. `_append_phase_trace`의 non-atomic write + `read_phase_trace`의 읽기 방어 불일치는 기존 C2/H5a 패턴과 동일 계열. `read_text()` 예외가 함수 밖으로 전파되면 "corrupt lines silently dropped" 계약 위반. 증거 충분.
- **Action Required**:
  ```python
  try:
      text = path.read_text(encoding="utf-8", errors="replace")
  except OSError:
      return []
  ```
  또는 `errors="replace"` 단독 적용.

---

#### 4. [ACCEPT] [Medium] `_handle_blocked_worktree` — `"cleanup_failed"` 상태가 두 케이스 혼용
- **Critic**: "worktree가 애초에 생성되지 않은 경우(`wt_was_present=False`)에도 branch가 존재하면 `'cleanup_failed'`로 설정된다. 실제 실패와 의도적 건너뜀이 동일 레이블을 공유해 장기 디버깅 시 false alarm 가능성."
- **Cross**: cleanup policy가 올바르게 배선되었음을 확인(finding 3 REJECT)했지만, 상태 레이블 모호성 자체는 검토하지 않음 — 서로 다른 sub-issue.
- **Judgment**: Critic finding 3과 Cross finding 3 REJECT는 다른 계층(배선 여부 vs 상태 값 의미론)을 다룬다. Cross REJECT는 배선 정상을 확인했을 뿐, 상태 레이블 모호성을 반박하지 않음. Critic 주장 유효.
- **Action Required**: `wt_was_present=False`이고 branch가 잔존하는 경로에 `"branch_preserved"` 또는 `last_failure` 필드에 reason 기록. 최소 수정: `state.cleanup_skip_reason = "wt_never_created"` 보조 필드 추가.

---

#### 5. [ACCEPT] [Low] `_dirty_files` docstring — 예외 계약 미반영
- **Critic**: "계약이 '빈 리스트 반환'에서 `GitWorktreeError` 던지기로 바뀌었지만 docstring이 갱신되지 않았다. 현 호출부 5개는 모두 try/except로 보호되어 있어 즉각적 크래시는 없다."
- **Cross**: not flagged
- **Judgment**: 런타임 위험 낮음. 단, 계약 변경이 문서에 반영되지 않으면 다음 caller가 예외를 누락할 위험은 실재. Low로 수용.
- **Action Required**: `_dirty_files` docstring에 `Raises: GitWorktreeError if git status exits non-zero` 한 줄 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Auto-merge `allowed_paths` 우회 | High | ACCEPT | Cross |
| 2 | `merge_mode` 임의 문자열 fallthrough | Medium | ACCEPT | Cross |
| 3 | `read_phase_trace` OSError/UnicodeDecodeError 미처리 | Medium | ACCEPT | Critic |
| 4 | `cleanup_failed` 상태 레이블 모호성 | Medium | ACCEPT | Critic |
| 5 | `_dirty_files` docstring 예외 계약 누락 | Low | ACCEPT | Critic |

---

### Recommendations

- **즉시 수정 (merge 전)**: Finding 1 — `allowed_paths` 우회는 scope 경계 무력화 가능성이 있어 High로 분류. `build_merge_policy()` 공용 헬퍼로 두 경로 통일.
- **함께 처리**: Finding 2 — `merge_mode` enum 검증을 `create_run()` / `__post_init__` 두 곳에 추가. Finding 1과 같은 파일·같은 PR.
- **방어 코드 보완**: Finding 3 — `read_phase_trace()` `OSError` 캐치 + `errors="replace"` 추가. 기존 C2 패턴 재현 예방.
- **상태 명세 명확화**: Finding 4 — `wt_was_present=False` 분기 명시. `"cleanup_failed"` 재사용 제거.
- **문서 1줄**: Finding 5 — docstring `Raises` 항목 추가. 코드 변경 없음.