# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-28 23:07
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

2개의 High 결함이 확인됨. 머지 전 수정 필수.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] `MergePolicy.denied_paths` 기본값 `[]` — 안전 기본값 제거

- **Critic**: "`denied_paths=[]`로 변경되어 `.af_runtime/`, `runtime/`, `skills/registry.yaml` 차단이 무력화. 테스트 9곳 + 외부 직접 호출자 모두 영향."
- **Cross**: "Explicit `MergePolicy(...)` 생성자를 사용하는 모든 호출자가 DEFAULT_DENIED_PATHS를 직접 전달하지 않는 한 denied path 계약을 우회. `_run_merge_phase()`는 패치됐지만 테스트 직접 호출 경로는 미보호."
- **Judgment**: 양쪽 동의. `merge_dogfood_branch(state, MergePolicy(mode="auto_policy"))` 형태의 호출은 `denied_paths`를 명시하지 않으면 빈 리스트로 동작함. Cross가 `_run_merge_phase()` L1375 패치는 확인했지만, L405·L480·L752·L780·L1079 등 테스트 호출 경로는 여전히 무보호.
- **Action Required**: `MergePolicy` 기본 팩토리를 복구:
  ```python
  denied_paths: list[str] = field(default_factory=lambda: list(DEFAULT_DENIED_PATHS))
  ```

---

#### 2. [ACCEPT] [High] `_is_crlf_only_diff` — Windows `-b` fallback 제거로 CRLF 오감지 회귀

- **Critic**: "삭제된 원본 주석이 명시했던 'Windows git에서 `--ignore-cr-at-eol`이 CRLF를 억제 못 하는' 케이스를 위한 `-b` fallback이 사라짐. Windows 11 환경에서 CRLF-only 파일을 dirty로 오분류 → `GitWorktreeError`로 dogfood run 전체 차단 가능."
- **Cross**: "미언급."
- **Judgment**: Critic 단독 플래그이나 증거 충분. (1) 이 프로젝트는 Windows 11에서 실행됨(환경 컨텍스트). (2) 원본 코드 주석이 해당 Windows git 엣지케이스를 명시적으로 언급하고 있었음. (3) CRLF 정규화 이슈가 최근 커밋(`d6f6ae39`)에서도 발생한 이력 있음. fallback 제거 근거가 diff에 없다.
- **Action Required**: `-b` fallback 복구 또는 해당 Windows git 버전에서 `--ignore-cr-at-eol`이 충분하다는 테스트/검증 증거 추가:
  ```python
  r = _git(["diff", "--ignore-cr-at-eol", "--", filepath], cwd=cwd, check=False)
  if r.returncode == 0 and not r.stdout.strip():
      return True
  r2 = _git(["diff", "-b", "--", filepath], cwd=cwd, check=False)
  return r2.returncode == 0 and not r2.stdout.strip()
  ```

---

#### 3. [ACCEPT] [Medium] `_dirty_files` — `check=False` + returncode 미검사, git 오류 시 fails-open

- **Critic**: "`_git(..., check=False)` 호출 후 returncode 미검사. git 실패 시 빈 stdout → `[]` 반환 → 호출자(`prepare_isolated_worktree`, `_check_merge_policy`)가 clean으로 간주하고 진행."
- **Cross**: "`_dirty_files()` is a safety gate at L648 and L839. Fails open when returncode != 0. Should fail closed."
- **Judgment**: 양쪽 동의. `prepare_isolated_worktree`(L648)와 `_check_merge_policy`(L839) 모두 이 함수를 보안 게이트로 사용. `[]` 반환이 "clean" 의미를 가지므로 git 오류가 조용히 게이트 우회로 변환됨.
- **Action Required**:
  ```python
  result = _git(["status", "--porcelain"] + ut_flag, cwd=workspace, check=False)
  if result.returncode != 0:
      raise GitWorktreeError(f"git status failed in {workspace}: {result.stderr.strip()}")
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `MergePolicy.denied_paths` 기본값 `[]` | High | ACCEPT | Both |
| 2 | `_is_crlf_only_diff` `-b` fallback 제거 | High | ACCEPT | Critic |
| 3 | `_dirty_files` fails-open on git error | Medium | ACCEPT | Both |

Cross REJECT 항목 2건(Finding 3: `_run_merge_phase` 패치 확인됨 / Finding 4: untracked 제외는 의도된 동작)은 집계에서 제외.

---

### Recommendations

1. **Finding 1 먼저 수정**: `MergePolicy` 기본 팩토리 복구 — 모든 기존 호출자가 즉시 안전 기본값을 되찾음.
2. **Finding 2**: `-b` fallback 복구 또는 "현재 Windows git 버전에서 `--ignore-cr-at-eol` 단독으로 충분하다"는 테스트를 `tests/test_dogfood_isolation.py`에 추가.
3. **Finding 3**: `_dirty_files`에 returncode 검사 추가 — `GitWorktreeError`로 명시적 실패. 이 패턴은 M10(조용한 실패)과 동일 계열이므로 다음 리뷰에서도 반복 감시 필요.
4. Finding 3까지 수정 후 af-test-runner 재실행 권장 (`tests/test_dogfood_isolation.py` 전체 — dirty-check 경로 회귀 확인).