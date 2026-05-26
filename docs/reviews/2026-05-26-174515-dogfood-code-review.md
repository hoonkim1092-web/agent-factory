# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-26 17:45
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

at least 2 Critical/High accepts on merge-gate semantics. Cross-review even ran pytest and reproduced test failures.

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [Critical] Untracked files silently dropped as "CRLF-only" → never committed
- **Critic**: `all_dirty`는 tracked diff + untracked를 합쳐 만든 뒤 `_is_crlf_only_diff()`를 돌리는데, untracked 파일에 `git diff -- <path>`는 항상 빈 stdout/rc=0을 리턴 → 모든 신규 파일이 `crlf_only`로 분류 → `stage_files`에서 누락 → `dogfood_commit_created=False` → merge "no_changes".
- **Cross**: 동일 결론. `python -m pytest tests/test_dogfood_isolation.py -q`가 현재 2개 실패한다고 보고 (재현 증거).
- **Judgment**: 둘 다 ACCEPT, 코드 590-602에서 직접 확인됨. 회귀 명확.
- **Action Required**: tracked-modified와 untracked를 분리. CRLF 필터는 tracked에만 적용:
  ```python
  tracked_mod = [f for f in diff.stdout.splitlines() if f]
  untracked_new = [f for f in untracked.stdout.splitlines() if f]
  crlf_only = {f for f in tracked_mod if _is_crlf_only_diff(f, wt)}
  real_dirty = [f for f in tracked_mod if f not in crlf_only] + untracked_new
  ```
  + untracked allowlisted artifact 회귀 테스트 추가.

#### 2. [ACCEPT] [High] AI-pre-commit + 잘못된 SHA 동치 게이트 → scope/denied 검사 우회
- **Critic**: `_check_merge_policy`가 보고서의 `dogfood_commit_created`를 안 쓰고 `state.dogfood_commit == state.base_ref` 동치 검사로 대체. `base_ref`가 빈 문자열이면 통과; 이전 세션 stale 커밋(HEAD≠base_ref인데 이번 finalize는 새 커밋 안 만든 경우)에도 통과.
- **Cross**: `committed_changed`가 `dogfood_commit_created=True`일 때만 계산됨. AI executor가 IMPLEMENT에서 자체 커밋하면 `head==pre_finalize_head` → `dogfood_commit_created=False` → `changed_files=[]` → denied_paths/allowed_paths 검사가 빈 리스트에 대해 무력화(701-713 라인).
- **Judgment**: 같은 게이트 결함을 양면에서 본 것. 둘 다 ACCEPT. 657-660, 697-713 코드로 확인됨.
- **Action Required**:
  1. `committed_changed` 계산을 `dogfood_commit_created` 무관하게 `state.base_ref`만 있으면 항상 `git diff --name-only {base_ref}..HEAD`로 산출.
  2. 정책 게이트는 보고서의 `dogfood_commit_created` 플래그를 사용 (SHA 동치는 보조 가드).

#### 3. [ACCEPT] [High] `scope_violations` silent log → hard BLOCK으로 정책 격상 (ADR/테스트 부재)
- **Critic**: 종전 주석은 "logged only; enforcement in later phase", 본 PR이 한 발에 BLOCK으로 격상(681-683). `tests/test_dogfood_isolation.py:286`만 필드 존재 확인, 정책 행동 변화 테스트 없음. ADR/Master_Blueprint 기록도 없음. 운영 회귀 위험.
- **Cross**: not flagged (행동 결함이 아닌 정책 거버넌스 문제라 패턴 미스).
- **Judgment**: 코드는 정확하나 거버넌스 갭이 분명. CLAUDE.md "Review-Gate 규칙" 변경 시 ADR 필수.
- **Action Required**: (a) `MergePolicy.strict_scope: bool = False` opt-in 또는 (b) ADR + §12 이력 + 정책 차단 테스트 케이스 추가.

#### 4. [ACCEPT] [Medium] `_write_json` non-atomic — `merge_report.json` 종속성 강화로 위험 증가
- **Critic**: finalize 직후 `merge_dogfood_branch`가 보고서를 재로드해 정책 입력으로 사용. partial JSON이 남으면 `except Exception: pass` (line 766 근처)에서 조용히 흡수 → `scope_violations=[]`로 BLOCK 우회. 알려진 C2/M10 패턴.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. 본 PR이 의존성을 강화했으므로 같이 잡는 것이 맞음.
- **Action Required**: `tempfile + os.replace`로 교체.

#### 5. [ACCEPT] [Medium] `_is_crlf_only_diff` 파일당 git subprocess fork — O(n) 성능
- **Critic**: 수십~수백 파일 × Windows git fork ~수십 ms = 1~2초+. 단일 호출(`git diff --ignore-cr-at-eol --name-only HEAD`)로 CRLF-only 집합 산출 가능.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. 성능 + 통합과 동시 해결 가능 (Finding 1 패치와 함께 1회 호출로 묶기).
- **Action Required**: `git diff --name-only HEAD` ∖ `git diff --ignore-cr-at-eol --name-only HEAD` = CRLF-only 집합.

#### 6. [HOLD] [Medium] `state.task` 개행/제어문자가 commit -m 본문 오염
- **Critic**: subprocess 리스트라 injection은 없지만, LLM 출력 LF가 commit 본문 분리로 해석. 72자 슬라이싱이 멀티바이트 한글 경계에서 깨질 수도.
- **Cross**: not flagged.
- **Judgment**: HOLD — 실제 부작용은 commit 메시지 미관 문제(트레일러로 자동 해석되는 경우는 있음). 본 PR 회귀가 아닌 기존 코드. 별도 PR로 처리 권장.
- **Question for Author**: `state.task`가 single-line으로 보장되는 contract가 있는가? 없다면 별도 sanitization PR로 분리.

#### Cross #3 (REJECT, 기록만)
- `_check_merge_policy()` 시그니처 변경 — 신규 인자가 optional이라 기존 호출자 깨지지 않음. Cross 본인이 REJECT 처리.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Untracked files → CRLF-only false positive | Critical | ACCEPT | Both |
| 2 | AI pre-commit + SHA 동치 게이트 우회 | High | ACCEPT | Both |
| 3 | scope_violations silent → BLOCK 정책 격상 (ADR 부재) | High | ACCEPT | Critic |
| 4 | `_write_json` non-atomic + 의존성 강화 | Medium | ACCEPT | Critic |
| 5 | `_is_crlf_only_diff` O(n) fork | Medium | ACCEPT | Critic |
| 6 | commit -m 본문 제어문자 오염 | Medium | HOLD | Critic |

### Recommendations

1. **즉시 수정 (BLOCK 해제 조건)**: Finding 1, 2, 3.
   - 1: tracked/untracked 분리 + 회귀 테스트.
   - 2: `committed_changed`를 `dogfood_commit_created` 무관 산출 + 게이트가 `dogfood_commit_created` 플래그 사용.
   - 3: ADR(`docs/decisions/ADR-YYYYMMDD-HHMMSS-dogfood-scope-violation-block.md`) + `tests/test_dogfood_isolation.py`에 scope_violations BLOCK 케이스 + §12 이력.
2. **같은 PR 동봉 권장**: Finding 4 (atomic write), Finding 5 (퍼포먼스 — 어차피 Finding 1 수정과 같은 함수 영역).
3. **별도 PR**: Finding 6 (task 정규화).
4. **T3 권고**: Critic이 t3_required=yes — 게이트 정책/subprocess 분기 변경이므로 af-cross-review fan-out 완주 후 진행.