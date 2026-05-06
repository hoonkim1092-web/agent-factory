# Design Review: 2026-05-03-phase2-verdict-label-spec

> Source: docs/2026-05-03-phase2-verdict-label-spec.md
> Date: 2026-05-03 23:14
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

> Cross-review가 provider 오류(codex)로 미실행되어 단일 reviewer 근거에만 의존하지만, Critic의 8건 모두 코드/문서 라인 인용으로 검증 가능한 강한 증거를 제시했고 그중 1건은 v3 BLOCK 결함의 자리만 옮긴 재도입(Critical)이다. Cross-review 재실행 필요는 별도 절차 사항.

### Aggregated Findings (8 total — Cross-review 미실행으로 모두 Critic 단독)

#### 1. [ACCEPT] [Critical] §5.4가 v3 BLOCK #1을 재도입 — `_log_hook_event` 시그니처 모순
- **Critic**: §5.4 line 357-360 코드는 `_log_hook_event(workspace, "warn_only_suppressed", {dict})` 3-arg 호출이지만 `hook_runner.py:100` 실제 시그니처는 `(builtin, file, exit_code: int, error="")` 4-arg. dict가 `exit_code` 자리에 들어가 `f"|{exit_code}|"` 포맷에 `repr()` 직렬화돼 측정값 손실. §5.4 line 369는 helper 시그니처를 "(workspace, event_name, payload)"로 잘못 기술, §5.5 line 421은 정확히 4-arg로 기술 — 동일 문서 내부 모순.
- **Cross**: 미실행(provider error)
- **Judgment**: 코드 라인·시그니처 직접 인용으로 강한 증거. `repr(dict)`이 `|`-구분 sink에 들어가는 동작은 Python 기본 동작으로 즉시 검증 가능. v3 BLOCK이 §5.5는 정정됐으나 §5.4에서 동일 결함이 자리만 옮긴 채 잔존.
- **Action Required**: §5.4 호출을 §5.5와 동일한 4-arg 형식으로 통일하고 페이로드는 `error=json.dumps({...})`로 직렬화. 동시에 §5.4 line 369 helper 시그니처 설명을 §5.5 line 421과 일치시킴.

#### 2. [ACCEPT] [High] §5.3 prose vs pseudocode 정면 모순 — 동일 위치 충돌 시 우선 패턴이 반대
- **Critic**: §5.3 line 296 ("충돌 시 `_VERDICT_RE` 우선")과 line 312-323 의사 코드의 stable sort 동작이 정반대. `matches.sort(key=lambda t: t[0])`는 stable이므로 동일 `start`에서 삽입 순서 유지 → `matches[-1]`은 `_VERDICT_HEADER_RE` 선택.
- **Cross**: 미실행
- **Judgment**: Python `list.sort()` stable property로 즉시 검증 가능. 두 정규식이 disjoint하므로 실제 충돌은 없지만 spec 자체의 모순은 향후 정규식 변경 시 위험.
- **Action Required**: tiebreaker 문장 삭제 + 두 패턴이 disjoint함을 단언하거나, sort key에 우선순위 명시 (예: `(start, 0 if from_verdict_re else 1)`).

#### 3. [ACCEPT] [High] §5.5의 wrong-line 코드 참조 — "line 64 helper" → 실제 line 100
- **Critic**: §5.5 line 421이 helper를 "line 64"로 인용하나 실제 정의는 `hook_runner.py:100`. line 64는 `_find_venv_python()`의 `return sys.executable` — 완전 무관. v3 Critic이 정확히 line 100을 인용했음에도 v4가 새 잘못된 참조 도입.
- **Cross**: 미실행
- **Judgment**: grep 가능한 직접 사실. v3→v4 정정 사이클에서 동일 함수 위치를 두 번 잘못 인용.
- **Action Required**: §5.5 line 421을 "`hook_runner.py:100` 정의된 helper"로 정정. §11 audit table에 "line 인용 무결성" 1행 추가.

#### 4. [ACCEPT] [High] §5.4의 `_log_hook_event` import 전략 미지정 + 부작용 미평가
- **Critic**: §5.4 line 369 "import하거나 inline 재정의" — 결정 미완료. `from scripts.hook_runner import _log_hook_event`는 (a) `_` private 함수 cross-reach, (b) hook_runner 전체 모듈 매 hook 진입마다 로드, (c) `_project_root()`가 `__file__` 기반이라 hook_runner 위치 기준으로 잘못된 경로 가능.
- **Cross**: 미실행
- **Judgment**: hot-path hook의 import 비용·workspace path 결정은 spec 단계 결정 사항.
- **Action Required**: inline 재정의 선택 + `workspace` 인자를 명시적으로 받도록 정의 + §7에 workspace path 단위 테스트 1건 추가.

#### 5. [ACCEPT] [High] §5.4 sink 폭발 — 매 UserPromptSubmit마다 1줄 append, 1회-알림과 분리됨
- **Critic**: WARN-only suppression 분기는 매 UserPromptSubmit마다 진입. v4 §5.4는 hook event 기록을 1회-알림(`warn_only_notified_at`) 분기 **밖**에 두어 N:1 폭발. §9.2 트리거 #1이 "1:1 정합"으로 정의되면 falsifiable 회복 의도와 반대.
- **Cross**: 미실행
- **Judgment**: `check_pending_review.py:126-138` 현재 동작과 §5.4 변경 위치를 같이 읽으면 자명한 sink 폭발.
- **Action Required**: hook event 기록을 `if not data.get("warn_only_notified_at"):` 분기 **내부**로 이동. §9.2 트리거 #1을 "WARN 라운드당 정확히 1건"으로 단순화.

#### 6. [ACCEPT] [Medium] §8.2 단일-commit 부트스트랩 자기 모순
- **Critic**: §8.2 line 606-607이 "본 commit 검증 라운드는 이전 fence 없는 형식으로 cross-review가 실행됨"이라고 단언하나, hook 발화 시점에 staged 코드는 이미 disk에 있어 reviewer/parser 모두 v4 형식 활성화. 단정의 근거 모호.
- **Cross**: 미실행
- **Judgment**: hook 발화 모델과 staging 시점을 정확히 구분하면 단정이 단순하지 않음.
- **Action Required**: §8.2를 "reviewer/parser 동시 활성화. agent 디스크 캐시로 이전 prompt 인용 시 1회 한해 fence 부재 폴백(C5) 발화 가능"으로 정확화하거나 2-commit 분리 + 비정합 명시.

#### 7. [ACCEPT] [Medium] §11 history table 코드 변경 범위 row v4 미갱신
- **Critic**: §11 line 729는 "scripts/*.py 3건 + tests/*.py 2건"로 v3 기준. §8.2 line 614-621 표는 "7개"로 갱신. §9.3 line 673은 "6개 파일 단일 commit 권장" — 동일 문서 내 3·6·7 세 숫자가 충돌.
- **Cross**: 미실행
- **Judgment**: 직접 grep 가능한 텍스트 비정합.
- **Action Required**: §11 row를 "scripts/*.py 4건 + tests/*.py 2건 + agent md 1건"으로 갱신. §9.3 "6개"를 "7개"로 정정.

#### 8. [ACCEPT] [Medium] §7.6 메트릭 회귀 케이스가 §5.6 정규식 false-positive를 검증 안 함
- **Critic**: §9.2 트리거 #4가 "코드 인용/prose 안의 `[ACCEPT-ADV]` `[BONUS]` false positive"를 명시했으나 §7.6 4 시나리오는 모두 true positive만. v4가 신규 라벨 2종을 도입해 noise surface가 50% 증가했음에도 회귀 case 부재.
- **Cross**: 미실행
- **Judgment**: §9.2와 §7.6 사이의 명백한 검증 갭.
- **Action Required**: §7.6에 markdown fence 내부 `[ACCEPT-ADV]` 1건 + prose 인용 `[BONUS]` 1건 추가. 정책(허용/제외) 명시.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §5.4 `_log_hook_event` 시그니처 모순 (v3 BLOCK 재도입) | Critical | ACCEPT | Critic only (강증거) |
| 2 | §5.3 prose vs pseudocode 우선 패턴 반대 | High | ACCEPT | Critic only (강증거) |
| 3 | §5.5 line 64 → line 100 wrong reference | High | ACCEPT | Critic only (강증거) |
| 4 | §5.4 import 전략 미지정 + 부작용 미평가 | High | ACCEPT | Critic only (강증거) |
| 5 | §5.4 sink 폭발 (1회-알림 분기 외부) | High | ACCEPT | Critic only (강증거) |
| 6 | §8.2 단일-commit 자기 모순 | Medium | ACCEPT | Critic only (강증거) |
| 7 | §11 history table 코드 범위 v4 미갱신 (3·6·7 충돌) | Medium | ACCEPT | Critic only (강증거) |
| 8 | §7.6 false-positive 회귀 미검증 | Medium | ACCEPT | Critic only (강증거) |

### Recommendations

1. **즉시 차단 해제 작업 (Critical/High 5건)**: Findings #1~#5를 v5에서 일괄 정정. 특히 #1은 §5.4 호출을 §5.5와 4-arg 형식으로 통일하고 §5.4 line 369 helper 시그니처 설명을 정정해야 동일 문서 내 함수 시그니처 단일화 달성.
2. **Medium 3건 일괄 정정**: §8.2 prose 정확화, §11 audit table v4 갱신 + §9.3 "6개" → "7개" 통일, §7.6 false-positive 회귀 시나리오 2건 추가.
3. **Cross-review 재실행 필수**: codex provider error로 v4 cross-review 미수행. CLAUDE.md 정책상 단일 설계문서 큐는 af-cross-review 1개 실행이 필수. v5 작성 후 재발화 + 재집계 필요. (codex usage limit 회복 시점은 원문 §0에 2026-05-05 15:37 KST로 기재)
4. **§11에 "line 인용 무결성" audit 1행 추가**: v3→v4에서 같은 함수 위치를 두 번 다른 라인으로 인용한 패턴 재발 방지 메타 가드.
5. **Phase 2 commit 시점 차단**: 본 BLOCK 해제 + cross-review PASS/WARN 두 조건 모두 충족 전까지 §8 단일 commit 진입 금지.