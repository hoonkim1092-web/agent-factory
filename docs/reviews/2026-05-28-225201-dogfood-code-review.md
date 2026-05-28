# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-28 22:52
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Critical finding confirmed by both reviewers: `DEFAULT_DENIED_PATHS`가 `auto_policy` 실행 경로에서 완전히 우회됨. 머지 전 필수 수정.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Critical] `_run_merge_phase`가 `DEFAULT_DENIED_PATHS`를 우회

- **Critic**: `MergePolicy(mode="auto_policy")`를 명시 전달하므로 `policy is None` 분기를 건너뜀 → `denied_paths=[]`로 머지 실행
- **Cross**: 동일 경로 확인. `run_all()` → `run_phase()` → `_run_merge_phase()` 체인은 `merge_dogfood_branch(policy=None)` 경로를 절대로 통과하지 않음
- **Judgment**: 두 리뷰어가 독립적으로 동일 코드 경로(`core/dogfood.py:1375-1377`)를 추적하여 동일 결론 도달. `DEFAULT_DENIED_PATHS`(`skills/registry.yaml`, `.af_runtime/`)는 리팩토링 전 dataclass 기본값에 있었으나 이제 `policy is None` 분기에만 주입됨. `auto_policy` 모드가 정상 운영 경로이므로 이 버그는 매 dogfood run에 발동됨. `NEXT_STEPS.md #7`에 이미 등록된 알려진 결함이 이번 변경으로 악화됨.
- **Action Required**:
  ```python
  # core/dogfood.py:1377
  # Before:
  merge_dogfood_branch(state, MergePolicy(mode="auto_policy"))
  # After:
  merge_dogfood_branch(state, MergePolicy(mode="auto_policy", denied_paths=list(DEFAULT_DENIED_PATHS)))
  ```
  회귀 테스트 추가: `auto_policy`로 `skills/registry.yaml` 수정 시 차단되는지 검증.

---

#### 2. [ACCEPT] [High] `finalize_dogfood_result`에서 untracked 파일이 CRLF-only로 오탐 제거

- **Critic**: `git diff --ignore-cr-at-eol -- <untracked>` 는 untracked 파일에 대해 returncode=0, stdout 비어있음 → `_is_crlf_only_diff()`가 항상 `True` 반환 → `real_dirty`에서 untracked 전부 제외
- **Cross**: 동일 확인. `_dirty_files(include_untracked=True)`의 `??` 항목이 `finalize_dogfood_result` L744-745에서 CRLF 필터를 통과하며 드롭됨. 실제 Git 동작으로 확인됨.
- **Judgment**: 두 리뷰어가 동일 메커니즘을 독립 추적. untracked 파일에 `git diff`는 의미없으므로 CRLF 필터 적용 자체가 잘못됨. dogfood 산출물 중 신규 파일이 커밋에서 누락될 수 있는 실질적 데이터 손실 경로.
- **Action Required**: `_dirty_files`가 status 종류(`??` vs `M`, `A` 등)를 함께 반환하도록 수정하거나, `_is_crlf_only_diff` 내에서 untracked 파일을 조기 `False` 반환:
  ```python
  # Option A (minimal): finalize_dogfood_result L744-745
  tracked = [f for f in all_dirty if _get_git_status(f, wt) != "??"]
  untracked = [f for f in all_dirty if f not in set(tracked)]
  real_dirty = [f for f in tracked if not _is_crlf_only_diff(f, wt)] + untracked
  ```
  untracked 신규 파일이 커밋에 포함되는지 검증하는 통합 테스트 추가.

---

#### 3. [ACCEPT] [High] Windows Git `--ignore-cr-at-eol` 폴백 제거로 인한 회귀

- **Critic**: 삭제된 주석이 명시적으로 Windows git 호환성을 위한 `-b` 폴백이었음을 기록. 이 프로젝트는 Windows 11 실행, `c9138f07` (64파일 CRLF 사건) 전례 있음.
- **Cross**: 미플래그
- **Judgment**: Cross가 플래그하지 않았으나 증거가 강함 — (a) 삭제된 주석이 명시적으로 이유를 기록했고, (b) 이 저장소에서 CRLF 이슈가 반복 발생한 실제 이력이 있으며, (c) 폴백 제거는 `prepare_isolated_worktree`와 `_check_merge_policy`를 CRLF-only 파일에 대해 불필요하게 차단할 수 있음. Windows 플랫폼 전용이므로 우선순위는 찾기 1번보다 낮지만 이 프로젝트에서는 High.
- **Action Required**:
  ```python
  def _is_crlf_only_diff(filepath: str, cwd: str) -> bool:
      r = _git(["diff", "--ignore-cr-at-eol", "--", filepath], cwd=cwd, check=False)
      if r.returncode == 0 and not r.stdout.strip():
          return True
      # Windows git fallback
      r2 = _git(["diff", "-b", "--", filepath], cwd=cwd, check=False)
      return r2.returncode == 0 and not r2.stdout.strip()
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_run_merge_phase` DEFAULT_DENIED_PATHS 우회 | Critical | ACCEPT | Both |
| 2 | untracked 파일 CRLF-only 오탐 제거 | High | ACCEPT | Both |
| 3 | Windows Git `--ignore-cr-at-eol` 폴백 제거 | High | ACCEPT | Critic |

**참고 (비-산출물)**: Cross reviewer가 `include_untracked=False` 미필터링을 초기 플래그했다가 직접 REJECT함 — production 코드는 `--untracked-files=no`를 올바르게 전달하며, 문제는 테스트 스텁이 해당 플래그를 무시하는 것. 프로덕션 버그 아님, 테스트 스텁 수정 대상.

---

### Recommendations

1. **[필수, 즉시]** `_run_merge_phase` L1377: `MergePolicy(mode="auto_policy", denied_paths=list(DEFAULT_DENIED_PATHS))`로 교체
2. **[필수, 즉시]** `finalize_dogfood_result` L744-745: untracked 파일을 CRLF 필터에서 분리
3. **[필수, Windows]** `_is_crlf_only_diff`: `-b` 폴백 복원
4. **[테스트]** `auto_policy`로 `skills/registry.yaml` 수정 시 차단되는 회귀 테스트 추가
5. **[테스트]** 신규 untracked 파일이 dogfood 커밋에 포함되는지 검증하는 통합 테스트 추가
6. **[테스트 스텁]** `test_dirty_files_includes_untracked`: `"--untracked-files=no" in args` 분기 추가