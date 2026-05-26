# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-26 17:43
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

근거: 두 리뷰어 모두 동의한 Critical 결함(`_is_crlf_only_diff` untracked 오판)이 dogfood 산출물 누락을 일으키는 정확성 결함이므로 머지 차단.

### T3 Advisory

t3_required: yes (Critic 단독 명시, Cross 동의 함의 — 머지 게이트/정책 경로 변경)

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [Critical] `_is_crlf_only_diff`가 untracked 신규 파일을 "CRLF-only"로 오판
- **Critic**: `git diff -- <untracked>` → rc=0/empty stdout이므로 untracked 전부가 crlf_only로 분류되어 `real_dirty`에서 제거. dogfood 산출물(plan artifact 포함)이 staging/commit에서 누락되고 `merge_status="no_changes"`로 사일런트 무결과.
- **Cross**: 동일 결함. `git diff --ignore-cr-at-eol -- new.py` empty stdout을 워크트리에서 직접 검증.
- **Judgment**: **양 리뷰 합의**. `core/dogfood.py:590-601`에서 `all_dirty = diff + untracked` 합친 뒤 helper를 일괄 적용하는 구조상 자명한 false positive. 정확성 결함 + 머지 게이트 silently bypass.
- **Action Required**:
  ```python
  untracked_set = {f for f in untracked.stdout.splitlines() if f}
  tracked_dirty = [f for f in all_dirty if f not in untracked_set]
  crlf_only = {f for f in tracked_dirty if _is_crlf_only_diff(f, wt)}
  real_dirty = [f for f in all_dirty if f not in crlf_only]
  ```
  Regression test: untracked allowed artifact가 `changed_files`에 포함되는지 확인.

#### 2. [ACCEPT] [High] `committed_changed`가 FINALIZE 신규 커밋에만 채워져 사전 커밋이 게이트 우회
- **Critic**: `committed_changed`가 plan_allowlist 대비 미검증 → `scope_violations`에 포함 안 됨. `MergePolicy()` 디폴트에서 `allowed_paths` 빈 경우 무방비.
- **Cross**: IMPLEMENT 단계에서 이미 HEAD가 전진한 경우 `head == pre_finalize_head`라 `committed_changed=[]`, `merge_status="no_changes"`. denied/allowed_paths 체크가 빈 리스트로 통과.
- **Judgment**: **양 리뷰가 같은 결함을 다른 각도에서 지적**. Cross의 근거 더 강함 — `_run_implement_phase()`가 `_pre_sha..HEAD` 디프를 명시적으로 처리(L1020-1026)하므로 IMPLEMENT-commit 시나리오는 spec상 지원. FINALIZE에서 이를 무시하는 게 결함.
- **Action Required**:
  - `committed_changed`를 `state.base_ref` 존재 + `HEAD != base_ref` 조건으로 채우기
  - `committed_changed`를 `plan_allowlist` 대비 검사하여 `scope_violations`에 합산
  - 머지 readiness 판정도 `HEAD != base_ref` 또는 committed diff non-empty 기준
  - 테스트: `pre_finalize_head`가 이미 `base_ref` 앞선 상태에서 finalize가 commit 파일 리스트를 보고

#### 3. [ACCEPT] [Medium] `dogfood_commit == base_ref` 가드가 새 커밋 보장으로 불충분
- **Critic**: `pre_finalize_head ≠ base_ref`이지만 FINALIZE에서 추가 커밋이 없는 경우 `dogfood_commit_created=False`인데 가드 통과.
- **Cross**: 별도 항목 아님 — Finding 2와 같은 사안의 다른 표현.
- **Judgment**: Finding 2 해결책과 일체로 처리. `dogfood_commit_created` 필드를 `DogfoodState`에 보존하거나 가드 조건을 `report.dogfood_commit_created`로 통합.
- **Action Required**: Finding 2 수정 시 `_check_merge_policy`의 `require_dogfood_commit` 게이트도 `dogfood_commit_created` 또는 `HEAD != base_ref` 기준으로 재작성.

#### 4. [ACCEPT] [Medium] `merge_report.json`의 `changed_files` 의미 변경 — downstream silent breakage
- **Critic**: `interactive_chat.py:255`가 `changed_files`를 사용자에게 표시. 의미가 "stage_files" → "base 이후 누적 커밋 변경"으로 바뀌어 무관 reformat 커밋 파일이 UI에 노출.
- **Cross**: 직접 flag는 아님. 다만 Finding 2 evidence에서 `merge_dogfood_branch()`가 `merge_report["changed_files"]`를 denied/allowed-path 체크에 사용한다고 언급 — 의미 변경 영향 받음.
- **Judgment**: Critic 단독, 그러나 evidence 강함 (`interactive_chat.py:255` 호출처 명시). Downstream 호환성 결함.
- **Action Required**: `committed_changed`는 별도 키로 노출하고 `changed_files`는 기존 의미(`stage_files`) 유지, 또는 downstream consumer 일괄 갱신.

#### 5. [HOLD] [High] 파일당 subprocess 1회 — Windows finalize 지연
- **Critic**: N개 파일 = N개 `git diff` 프로세스. Windows에서 50ms~150ms × N, 대규모 dirty 시 finalize 블로킹.
- **Cross**: 미flag.
- **Judgment**: 실제 결함이지만 Finding 1의 권장 픽스(untracked 분리)와 결합해 **단일 호출 batch**로 일괄 해소 가능. 픽스가 정확성+성능 둘 다 잡으므로 Action으로 통합.
- **Action Required**:
  ```python
  r = _git(["diff", "--ignore-cr-at-eol", "--name-only", "--"] + tracked_dirty, cwd=wt, check=False)
  real_modified = set(r.stdout.splitlines())
  crlf_only = set(tracked_dirty) - real_modified
  ```
  Helper 자체 제거 가능.

#### 6. [HOLD] [Low] `--ignore-cr-at-eol`이 BOM/trailing-newline 등 EOL 인접 노이즈 miss
- **Critic**: docstring이 좁은 범위 명시했으니 의도라면 보존하되 테스트 케이스(LF→CRLF, CRLF+공백, CRLF+BOM) 추가 필요.
- **Cross**: 미flag.
- **Judgment**: Critic 단독, 문서/테스트 권고 수준. 차단 사유는 아님. 픽스 후 테스트 보강 시 함께 처리.
- **Action Required**: `tests/test_dogfood_*.py`에 EOL 변형 케이스 보강 (Finding 1 regression test와 묶어서).

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | untracked 파일이 CRLF-only로 오판 | Critical | ACCEPT | Both |
| 2 | committed_changed가 사전 커밋 우회 | High | ACCEPT | Both |
| 3 | dogfood_commit==base_ref 가드 불충분 | Medium | ACCEPT | Critic (Cross 함의) |
| 4 | changed_files 의미 silent shift | Medium | ACCEPT | Critic |
| 5 | per-file subprocess Windows 지연 | High | HOLD→#1과 통합 | Critic |
| 6 | EOL 인접 노이즈 미검출 | Low | HOLD | Critic |

### Recommendations

1. **Finding 1+5 통합 픽스**: `_is_crlf_only_diff` helper 제거하고 `git diff --ignore-cr-at-eol --name-only -- <tracked_dirty 일괄>` 단일 호출로 교체. untracked는 helper 대상에서 제외.
2. **Finding 2+3 통합 픽스**: `committed_changed`를 `HEAD != base_ref` 조건으로 채우고 `plan_allowlist` 대비 scope 검사. `_check_merge_policy`의 dogfood_commit 가드는 `report.dogfood_commit_created` 참조로 변경.
3. **Finding 4**: `merge_report.json`에 `stage_files`(기존 의미)와 `committed_changed`를 분리 노출. `interactive_chat.py:255`도 어느 키를 표시할지 명시.
4. **회귀 테스트**:
   - untracked 신규 파일이 `changed_files`에 포함되는 케이스
   - IMPLEMENT 단계에서 HEAD가 이미 전진한 상태에서 finalize가 commit 파일 리스트 보고하는 케이스
   - EOL 변형(LF→CRLF / CRLF+공백 / CRLF+BOM) 케이스
5. **T3 필수**: 머지 게이트/정책 변경이므로 픽스 후 af-cross-review 재실행.