# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-26 17:54
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

가장 심각한 발견은 Critic #1(Blueprint-staged 미스테이지로 인한 silent crash) 및 Cross #1(IMPLEMENT 실패 무시)이다. 둘 다 dogfood run 전체 무결성을 위협하지만, 변경 diff 자체(_git extra_env 추가)는 작고 격리되어 있어 BLOCK까지는 아니다. 단, 본 PR의 의도(FINALIZE 게이트 우회)가 실제로 실패 경로에서 동작하지 못한다는 점에서 후속 fix가 필요하다.

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] Blueprint-staged check가 dogfood FINALIZE에서 그대로 실패
- **Critic**: `AF_SKIP_REVIEW_GATE=1`은 review-gate만 우회, pre-commit:67-79의 "Master_Blueprint.md 미스테이지 → exit 1" 검사는 살아남음. `core/*.py` 수정 시 `check=True`로 `CalledProcessError` 폭사.
- **Cross**: not flagged
- **Judgment**: 근거 강함. `.githooks/pre-commit` 구조와 `_git(check=True)` 기본값 결합 시 본 PR의 의도(자동 commit)가 정확히 실패하는 경로. 현재 브랜치 자체가 `core/dogfood.py`를 수정 중이므로 즉시 재현된다.
- **Action Required**: (a) `stage_files`가 `CODE_CHANGED`와 교집합이면 Blueprint도 함께 staging, 또는 (b) dogfood 전용 통합 우회 키(`AF_DOGFOOD_COMMIT=1`)를 hook이 인식하게 단일화, 또는 (c) 최소 `check=False`로 두고 `merge_report["finalize_error"]`에 사유 기록.

#### 2. [ACCEPT] [High] IMPLEMENT 실패가 `executed`가 비어있지 않으면 무시됨
- **Critic**: not flagged
- **Cross**: `run_all()`이 `ok=False` AND `executed` 비어있을 때만 차단. `_run_implement_phase()`가 `failures`를 기록해도 VERIFY/REVIEW/FINALIZE/MERGE가 진행됨.
- **Judgment**: Cross가 코드 라인(`core/dogfood.py:1023-1030, 1279`)을 명시했고 evidence가 분명. 본 PR 범위 밖이지만 dogfood pipeline 무결성 직결.
- **Action Required**: `run_all()`에서 `not impl_result.get("ok")` 자체를 차단/재시도 시그널로. 부분 성공 처리하려면 REVIEW로 라우팅.

#### 3. [ACCEPT] [Medium] auto_policy merge가 plan 기반 `allowed_paths`를 드롭
- **Critic**: not flagged
- **Cross**: `_run_merge_phase()`가 `MergePolicy(mode="auto_policy")`로 직접 전달, `merge_dogfood_branch()`의 default-policy 빌더(plan_path → allowed_paths) 우회. 수동 경로와 게이트가 달라짐.
- **Judgment**: Cross의 라인 인용(`core/dogfood.py:736-750`, `agent_launcher.py:1102`) 검증됨. 본 PR 범위 밖이나 보안/안전 게이트 일관성 이슈.
- **Action Required**: `state.merge_mode = "auto_policy"` 세팅 후 `merge_dogfood_branch(state)` 호출, 또는 공유 `build_merge_policy(state, mode)` 추출.

#### 4. [ACCEPT] [Medium] 감사 추적 단서 빈약 — dogfood 자동 우회와 사용자 인라인 우회 구분 불가
- **Critic**: `_log_event(workspace, "[gate-skipped-env]")` 한 줄로는 호출 컨텍스트 부재. dogfood 자동 우회 vs 사용자 의식적 우회 forensic 구분 불가.
- **Cross**: not flagged
- **Judgment**: CLAUDE.md의 "긴급·부트스트랩 시" 인라인 우회 정책 전제와 본 PR의 "모든 dogfood commit 자동 우회"가 충돌. Critic 근거 타당.
- **Action Required**: `extra_env`에 `AF_GATE_SKIP_REASON="dogfood_finalize"` 보조 키 추가 → `scripts/review_gate.py`의 `_log_event`가 사유 포함하여 기록. 또는 dogfood ledger에 별도 영구 저장.

#### 5. [ACCEPT] [Medium] `merge_mode` 공개 API가 임의 문자열 허용 → silent auto-merge
- **Critic**: not flagged
- **Cross**: `run_all(..., merge_mode="auto_policy")`가 `"never"`/`"manual"` 외 전부 auto-policy로 fallback. CLI는 검증하지만 직접 호출자는 `"never "` 같은 오타로 자동 머지 가능.
- **Judgment**: 라인 인용(`core/dogfood.py:1131, 1152-1161`) 정확. 머지는 비가역 작업이므로 입력 검증은 정당.
- **Action Required**: `create_run()`과 `run_all()` 공유 normalizer/validator. `auto_policy|manual|never` 외 `ValueError`.

#### 6. [ACCEPT] [Low] `verify_handoff_checker` 우회는 별도 — 향후 verification-report.md staging 시 재발
- **Critic**: pre-commit:83-95의 `AF_PRE_COMMIT_VERIFY` 게이트는 별도 키. dogfood가 verification report를 produce하게 되면 동일 silent failure 패턴 재현.
- **Cross**: not flagged
- **Judgment**: 현재 흐름에선 트리거 안 됨, 그러나 Critic #1과 묶어서 통합 우회 키(`AF_DOGFOOD_COMMIT=1`)로 해결하면 한 번에 정리됨.
- **Action Required**: Finding #1의 (b) 옵션 채택 시 함께 해결.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Blueprint-staged 우회 미적용 → FINALIZE silent crash | High | ACCEPT | Critic |
| 2 | IMPLEMENT 실패 무시(executed 비어있을 때만 차단) | High | ACCEPT | Cross |
| 3 | auto_policy merge가 allowed_paths 드롭 | Medium | ACCEPT | Cross |
| 4 | 감사 추적 단서 부족 | Medium | ACCEPT | Critic |
| 5 | merge_mode 임의 문자열 허용 | Medium | ACCEPT | Cross |
| 6 | verify_handoff 별도 게이트 잔존 | Low | ACCEPT | Critic |

(Critic의 #4 API simplicity, #5 `check=True` 폭사는 #1과 동근원으로 흡수. Cross의 #4는 REJECT 유지.)

### Recommendations

1. **즉시 fix (본 PR 후속)**:
   - Finding #1: dogfood commit에 `AF_DOGFOOD_COMMIT=1` 통합 키 도입 → hook에서 review-gate + Blueprint-stage + verify_handoff 세 검사 모두 우회. 또는 `_git` commit 호출만 `check=False` + `merge_report["finalize_error"]` 기록.
   - Finding #4: `extra_env`에 `AF_GATE_SKIP_REASON="dogfood_finalize"` 추가 + `review_gate.py:_log_event` 사유 포함.
2. **본 PR 범위 밖, 별도 work-item**:
   - Finding #2: `run_all()` IMPLEMENT 실패 차단 강화
   - Finding #3: `_run_merge_phase()` allowed_paths 빌더 공유
   - Finding #5: `merge_mode` 입력 검증
3. **T3 advisory 처리**: Critic이 t3_required=yes 표기. 자동 commit + 게이트 우회 조합이므로 외부 프로바이더 fan-out된 cross-review 결과(현 라운드)를 근거로 진행. WARN이므로 자동 fix 의무는 없으나 Finding #1·#4는 본 PR 의도와 직결되어 후속 fix 강력 권고.