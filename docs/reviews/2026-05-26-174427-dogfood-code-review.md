# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-26 17:44
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

근거: 두 리뷰어가 동일하게 ACCEPT한 Critical 1건(#1 untracked 무음 누락)과 High 1건(#2 AI self-commit 누락) 존재. Cross가 pytest로 실측 검증(`tests/test_dogfood_isolation.py` 2건 FAIL)까지 첨부.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Critical] `_is_crlf_only_diff`가 untracked 파일을 전부 CRLF-only로 오판 → 신규 파일 무음 누락
- **Critic**: "git diff -- <untracked> = exit0 + empty stdout이라 모든 untracked가 crlf_only에 들어가 real_dirty에서 제거됨"
- **Cross**: "동일 결함, 임시 repo에서 실측 검증. tests/test_dogfood_isolation.py 2건 FAIL이 본 결함과 일치"
- **Judgment**: 두 리뷰어가 독립적으로 동일 결함 ACCEPT, Cross가 실제 pytest FAIL로 재현까지 입증. `core/dogfood.py:601` `all_dirty`는 `diff.stdout + untracked.stdout` 합집합(line 588-591)이고 `_is_crlf_only_diff`는 `git diff -- <path>`로 워킹트리 vs 인덱스만 비교 — untracked는 인덱스에 없으므로 항상 empty. dogfood 한 라운드의 신규 산출물이 통째로 사라지는 무음 실패.
- **Action Required**: tracked/untracked를 분리하여 CRLF 필터를 tracked에만 적용:
  ```python
  tracked_dirty = set(diff.stdout.strip().splitlines())
  untracked_dirty = set(untracked.stdout.strip().splitlines())
  crlf_only = {f for f in tracked_dirty if _is_crlf_only_diff(f, wt)}
  real_dirty = [f for f in (tracked_dirty | untracked_dirty) if f and f not in crlf_only]
  ```

#### 2. [ACCEPT] [High] `committed_changed`가 `dogfood_commit_created` 게이트로 막혀 AI self-commit 시나리오 누락
- **Critic**: "docstring은 'AI-commit advances를 견딘다'인데 정작 `dogfood_commit_created`로 게이트하면 AI가 EXECUTE에서 self-commit한 경우 dirty=∅ → 새 commit 안 만들고 → committed_changed=[] → merge_status=no_changes"
- **Cross**: "동일. `_run_implement_phase()`는 `core/dogfood.py:982`에서 AI-committed 파일을 별도 추적하는데, FINALIZE는 그걸 잃어버림. 결과적으로 `_check_merge_policy()`가 changed_files=[]로 호출되어 denied_path/allowed_path 검사가 전부 우회됨"
- **Judgment**: 두 리뷰어가 ACCEPT + 자기참조 docstring과 모순. Cross가 보안적 함의(denied_path 우회)까지 식별.
- **Action Required**:
  ```python
  committed_changed = []
  if state.base_ref and head != state.base_ref:
      _committed = _git(["diff", "--name-only", f"{state.base_ref}..HEAD"], cwd=wt, check=False)
      committed_changed = [f for f in _committed.stdout.splitlines() if f]
  ```
  + `merge_status` 판정도 `committed_changed ∪ real_dirty` 기준으로 통일.

#### 3. [ACCEPT] [High] `_check_merge_policy`가 `dogfood_commit_created`를 직접 사용하지 않음
- **Critic**: "state에 `dogfood_commit_created`가 없고 report에만 저장(line 654). 정책은 `dogfood_commit == base_ref` 동등성만 보는데, finalize 전 AI가 base_ref와 다른 SHA로 advance만 시킨 채 finalize SKIP되면 false-positive 통과"
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 코드 증거 명확. `core/dogfood.py:697-701`이 `state.dogfood_commit == state.base_ref`로만 게이트하므로, finalize가 호출되지 않은 부분실행/crash recovery 경로에서 신호가 약함. 단, #2 수정이 들어가면 finalize는 항상 committed_changed를 채우므로 영향이 부분 완화됨 — 따라서 ACCEPT하되 우선순위는 #2 다음.
- **Action Required**: `DogfoodState`에 `dogfood_commit_created: bool = False` 필드 추가, finalize에서 set, `_check_merge_policy`에서 해당 플래그 함께 검사.

#### 4. [HOLD] [Medium] scope_violations hard BLOCK — 우회 토글 부재
- **Critic**: "기존 주석 `# logged only`에서 enforcement로 승격하면서 `MergePolicy`에 `allow_scope_violations` 토글 추가 없음. 신규 docs/runs/로그가 plan_allowlist에 빠지면 무조건 BLOCK"
- **Cross**: not flagged
- **Judgment**: 정책 변경 자체는 의도된 방향. 단, opt-out 부재가 운영 사고로 이어질지는 실제 plan_allowlist 누락 빈도에 의존 — 현 단계에선 정책 의도 명시(`enforce_scope: bool = True`) 정도가 합당하나 사용자 판단 필요.
- **Question for Author**: scope_violations enforcement에 토글(`MergePolicy.enforce_scope`)을 추가할지, 아니면 plan_allowlist 누락은 항상 reviewer 개입 사항으로 hard BLOCK 유지할지?

#### 5. [ACCEPT] [Medium] `_is_crlf_only_diff` O(N) subprocess fork
- **Critic**: "파일당 git diff 1회. Windows에서 dirty 수십~수백 개 시 hot path 부하. `git diff --ignore-cr-at-eol --name-only HEAD` 1회 결과와 일반 `git diff --name-only HEAD` 차집합으로 2회 subprocess로 축소 가능"
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 증거 명확하고 #1 수정과 함께 적용하면 자연스러움. dogfood는 자주 호출되는 경로.
- **Action Required**: #1 수정 시 함께 적용:
  ```python
  ignore_crlf = set(_git(["diff", "--ignore-cr-at-eol", "--name-only", "HEAD"], cwd=wt).stdout.splitlines())
  crlf_only = tracked_dirty - ignore_crlf
  ```

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | CRLF 필터가 untracked 무음 누락 | Critical | ACCEPT | Both |
| 2 | committed_changed가 AI self-commit 누락 | High | ACCEPT | Both |
| 3 | _check_merge_policy가 commit_created 미사용 | High | ACCEPT | Critic |
| 4 | scope_violations hard BLOCK 우회 부재 | Medium | HOLD | Critic |
| 5 | _is_crlf_only_diff O(N) subprocess | Medium | ACCEPT | Critic |

### Recommendations
- **차단 수정 순서**: #1 → #2 → #5(같이) → #3 → #4(사용자 결정 후).
- **회귀 테스트 추가 의무**:
  - untracked 신규 파일이 finalize로 stage/commit되는지 (`tests/test_dogfood_isolation.py` 기존 2건 FAIL 회복 + 신규 케이스).
  - AI가 EXECUTE 단계에서 self-commit한 시나리오에서 `committed_changed`와 `merge_status="ready"` 보장.
  - denied_path가 AI self-commit 경로에서도 enforce되는지.
- **Cross의 REJECT 1건** (`_check_merge_policy` 시그니처 변경)은 기본값 None으로 호환 유지 — 그대로 REJECT 수용.
- **T3 advisory**: 두 리뷰 모두 `t3_required: yes` 합치. merge gate·subprocess·policy enforcement 영역이라 수정본은 af-cross-review 재돌입 필수.