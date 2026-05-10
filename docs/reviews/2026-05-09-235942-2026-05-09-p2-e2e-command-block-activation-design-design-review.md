# Design Review: 2026-05-09-p2-e2e-command-block-activation-design

> Source: docs/2026-05-09-p2-e2e-command-block-activation-design.md
> Date: 2026-05-09 23:59
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

두 리뷰를 집계합니다.

---

## Final Design Review

### Verdict: BLOCK

BLOCK — Critical 2건이 구현을 시작하기 전에 반드시 해소되어야 합니다.

> **주의**: Critic이 BLOCK으로 분류한 10건 중 **2건은 False Positive**입니다 (§7.4, §8.6). 해당 스펙은 v4 문서에 이미 존재하며, Critic이 이전 버전을 기준으로 판단한 것으로 보입니다. 아래 REJECT 섹션에 근거를 명시합니다.

---

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] `_task_template` — `{task_id}` NameError

- **Critic**: `§7.3.1` 표가 `f"# TODO: e2e command for {task_id} (build)"` 를 Python f-string으로 명시. `_task_template(owner, module_id, phase, ...)` 스코프에 `task_id`는 없음. `task_id`는 `_normalize_tasks` (line 481) 사후 계산. v4 10건 변경 중 시그니처 추가 없음. Acceptance #21은 `startswith("# TODO:")` 만 검사 → NameError 검출 불가.
- **Cross**: 미플래그 (런타임 동작 중심 리뷰).
- **Judgment**: ACCEPT. `core/project_task_board.py:337-389` 스코프에 `task_id`가 없다는 Critic의 코드 추적은 정확하다. §7.3.2에서 같은 위치가 `<task_id>` (꺽쇠 표기)를 사용하는 것과 달리 §7.3.1은 `{task_id}` (f-string 표기)를 사용 — 표기 불일치 자체가 모호성의 증거.
- **Action Required**: 두 옵션 중 하나를 §7.3.1에 명시하라. (a) f-string 포기 → `"# TODO: e2e command (build)"` (task_id 참조 없음), (b) `_task_template` 시그니처에 `task_id` 파라미터 추가 + 모든 호출부 목록 명시. Acceptance #21도 선택에 맞게 갱신.

---

#### 2. [ACCEPT] [Critical] `EscalationDecision` — `affected_phase`/`count` 필드 부재

- **Critic**: `EscalationDecision` P1 stub 필드는 `block/severity/reason/rule_id/activate_at` 5개. 그러나 §5.2 `_decision.json.rule_decisions` 예시는 `"affected_phase": "build", "count": 14`를 포함. `compute_run_decision`이 `evaluate(virtual)` 반환값을 `rule_decisions`에 append할 때 이 정보가 소실됨.
- **Cross**: ACCEPT. `EscalationDecision`에 해당 필드 없음을 `core/escalation_evaluator.py:17` 직접 확인. 구현자가 필드 출처를 추측해야 하는 설계 gap.
- **Judgment**: ACCEPT (양 reviewer 일치, 고확신). §4.3 의사코드에서 `virtual = WarningRecord(affected_phase=phase, count=count, ...)` → `d = evaluate(virtual)` → `rule_decisions.append(d)`. `d`에 `affected_phase`/`count`가 없으므로 §5.2 schema를 충족하지 못함.
- **Action Required**: 다음 중 하나를 §4 또는 §5에 명시하라. (a) `EscalationDecision`에 `affected_phase: str`, `count: int` 추가, (b) `compute_run_decision`이 `EscalationDecision`을 dict로 확장해 `rule_decisions`를 구성하는 알고리즘 명시, (c) `RuleDecisionEntry` 별도 dataclass 정의.

---

#### 3. [ACCEPT] [High] `load_policy()` 실패 시 fail-open 위험

- **Critic**: `§4.4a`에 `_load_policy()` → `load_policy()` rename 명시. 그러나 policy 파일 부재/parse error 시 동작 미정의. silently `{}` 반환 시: `_find_rule({}, rule_id)` → `None` → `EscalationDecision(block=False)` — fail-open. `summarize()`의 try/except는 exception이 raise될 때만 작동.
- **Cross**: 직접 미플래그. Cross #7 (override 범위) 간접 연관.
- **Judgment**: ACCEPT (단일 reviewer, 증거 강함). fail-closed 3중 방어선을 설계한 문서가 gate의 첫 번째 단계인 `load_policy()` 계약을 빈칸으로 둔 것은 구조적 모순이다.
- **Action Required**: §4.4a에 계약을 명시하라: "`load_policy()`는 policy 파일 부재/parse error 시 반드시 exception을 raise한다. 빈 dict 반환 금지." 이 계약이 있어야 §5.4의 try/except fail-closed 로직이 완전히 작동한다.

---

#### 4. [ACCEPT] [High] append-only JSONL — `e2e_command` 수정 후 재실행이 블록을 해소하지 못함

- **Critic**: 미플래그.
- **Cross**: ACCEPT. `WarningRegistry.record()`가 JSONL append/dedup (`warning_registry.py:127`). `_build_summary()`가 `*.jsonl` 전체를 resolved 시맨틱 없이 스캔 (`warning_registry.py:228`). `e2e_command`를 채워도 기존 record는 잔존 → `_build_summary`가 여전히 missing count를 반환 → 블록 해소 안 됨.
- **Judgment**: ACCEPT (단일 reviewer, 코드 직접 확인). §0.1의 해소 option (a) "각 task의 `e2e_command` 필드를 실제 명령으로 채운 후 재실행"은 실제로 BLOCK을 해소하지 못한다. 사용자는 반드시 (b) override 또는 (c) policy 비활성을 사용해야 한다.
- **Action Required**: §0.1 / §5.3 `_decision.md` 해소 방법에서 option (a)를 수정하거나 제거하라. 또는 `_build_summary()`가 현재 board 상태와 기존 JSONL records를 reconcile하는 알고리즘(예: 재실행 시 missing 기록을 resolved로 supersede)을 설계에 명시하라. 현 설계대로 구현하면 사용자 안내가 틀리다.

---

#### 5. [ACCEPT] [High] `execute()` 블록 체크 순서 — user edit sync 전에 실행됨

- **Critic**: 미플래그.
- **Cross**: ACCEPT. 현재 `project_pipeline.py:1268`에서 approval 체크, `project_pipeline.py:1279`에서 work-item 편집 sync. P2 블록 체크가 approval 체크 직후에 추가되므로 사용자가 work-item 문서에서 `e2e_command`를 수정해도 sync 전에 차단됨. 또한 `parse_implementation_tasks()`가 현재 `e2e_command` 필드를 파싱하지 않음 (`core/work_item_parser.py:153`).
- **Judgment**: ACCEPT (단일 reviewer, 라인 번호 직접 확인). Finding #4와 연계: 설령 sync 순서를 바꿔도 JSONL append-only 문제(#4)로 인해 새 summary가 blocking하지 않으려면 resolver 로직이 별도로 필요하다. 두 문제 모두 "user edits → unblock" 경로에서 동시에 드러난다.
- **Action Required**: §6.2에 다음 중 하나를 명시하라. (a) `execute()` 내 user edit sync를 `read_block_decision()` 전으로 이동하는 경우 `parse_implementation_tasks()` + `sync_board_from_work_items()`의 `e2e_command` 처리 범위도 P2 scope에 포함 여부 결정, (b) "edit → unblock"은 full `prepare()` 재실행이 필요하다는 사용자 안내 명시. 현재 설계는 어느 쪽도 선택하지 않았다.

---

#### 6. [ACCEPT] [Medium] `compute_run_decision`의 `policy` 파라미터 — dead parameter / 이중 load

- **Critic**: `compute_run_decision(summary, policy)` 로 외부에서 policy 전달받지만, 내부 `evaluate(virtual)` 호출이 `_load_policy()`를 재호출 → `policy` 파라미터 미사용. by_phase M개 순회 시 YAML M+1회 read.
- **Cross**: ACCEPT. `core/escalation_evaluator.py:50, 62`에서 현재 `evaluate(record)`에 policy 파라미터 없음 직접 확인. policy fixture inject로 테스트 신뢰성 저하.
- **Judgment**: ACCEPT (양 reviewer 일치). §4.3 의사코드가 `compute_run_decision(summary, policy, ...)` 로 policy를 받으면서 안으로 `evaluate(virtual)` (policy 없음)을 호출하는 구조는 dead code와 성능 낭비를 동시에 만든다.
- **Action Required**: §4.2 `evaluate()` 시그니처를 `evaluate(record: WarningRecord, policy: dict) -> EscalationDecision`으로 변경하거나, `compute_run_decision`에서 `policy` 파라미터를 제거하고 내부 단일 `_load_policy()` 호출로 통일. 두 옵션 중 채택된 것을 §4.1/§4.2/§4.3에 일관 반영.

---

#### 7. [ACCEPT] [Medium] ISO timestamp string 비교 — timezone offset 혼재 시 stale 오판

- **Critic**: `§6.1`: `decision_summary_ts < summary_last` 문자열 비교. `"2026-05-09T07:00:00Z"` < `"2026-05-09T16:00:00+09:00"` 는 string 비교 상 True이지만 동일 시각. §5.2 예시 timestamp는 `+09:00` 포맷이고 `_write_minimal_block_decision`의 `now_iso()` 반환 포맷 미정의.
- **Cross**: 미플래그.
- **Judgment**: ACCEPT (단일 reviewer, 기술적으로 정확). fail-closed 설계에서 stale detection이 오작동하면 false-positive BLOCK이 발생한다. timestamp 포맷이 단일 시스템 내에서도 혼재할 수 있다.
- **Action Required**: 두 옵션 중 하나를 §5.2 또는 §6.1에 명시하라. (a) `now_iso()`는 항상 UTC (`Z` suffix) 반환 고정, 모든 timestamp는 UTC로 저장, (b) 비교 로직을 `datetime.fromisoformat()` 기반으로 변경. 어느 쪽이든 §12 grep table에 `now_iso()` 포맷 계약 추가.

---

#### 8. [ACCEPT] [Medium] `inject_review_tasks` — 경고 스캔 우회

- **Critic**: 미플래그.
- **Cross**: ACCEPT. `inject_review_tasks`가 `# TODO:` e2e_command를 가진 review task를 execution 중에 동적으로 생성(`dynamic_orchestrator.py:231`). 그러나 `e2e_command_missing` record 경로는 prepare 시점의 `generate_work_items()` (`work_item_generator.py:1048`)에만 있음. 동적 주입 task는 스캔되지 않음.
- **Judgment**: ACCEPT (단일 reviewer, 코드 직접 확인). §7.3.2가 `inject_review_tasks`에 `# TODO:` marker 추가를 명시하면서 그 task들이 warning scan을 우회한다는 것을 설계가 인지하지 못하고 있다.
- **Action Required**: §7.3.2 또는 §3.1 데이터 흐름에 다음 중 하나를 명시하라. (a) `inject_review_tasks()` 내부에서 즉시 `WarningRegistry.record()` + `summarize()` 호출, (b) orchestrator pre-dispatch gate에서 신규 주입 task의 `e2e_command` 검사, (c) injected tasks의 `# TODO:` marker는 policy scope에서 의도적으로 exempt — 그 근거 명시.

---

#### 9. [HOLD] [Medium] Override scope — rule 전체 영구 비활성 위험

- **Cross**: HOLD. `any_override=True` 시 해당 rule의 모든 record가 false-positive 처리. 이후 새로 추가되는 task의 `e2e_command_missing`도 동일하게 override됨. P2 영구 bypass 의도인지, 새 경고 후 재활성화가 필요한지 불명확.
- **Critic**: 미플래그.
- **Judgment**: HOLD. P2 설계 의도가 "한 번 override하면 이 slug에서 영구 비활성"을 의도한다면 §8.4에 명시가 필요하다. 그렇지 않다면 override 만료/재활성 조건을 정의해야 한다. 현재 §8.4는 "P4에서 record_id별, phase별 확장"만 언급 — P2 범위 내 override 유효 조건이 빠져 있다.
- **Question for Author**: P2에서 override는 slug-rule 쌍에 대해 영구적으로 작동하는가? 새로운 `e2e_command_missing` record가 이후에 추가될 때도 같은 override가 적용되는가?

---

#### 10. [REJECT] [Low] §7.4 backfill parser 스펙 미정의

- **Source**: Critic
- **Original Finding**: "§7.4 본문에는 함수 시그니처와 'best-effort, 파싱 실패 시 silent skip' 2줄만 있다. 정규식 패턴 미정의, task_id 매칭 알고리즘 미정의, conflict 처리 미정의."
- **Rejection Reason**: 원문 §7.4 (lines 700–723)에 다음이 모두 존재한다. 정규식: `r"(?:^[-*]\s+task_id:\s*(T-\d+).*?^[-*]\s+e2e_command:\s+(.+?)$|...)"` with `re.MULTILINE | re.DOTALL`. task_id 매칭: "e2e_command 라인 직전의 `task_id: T-NNN` 라인 탐색 (최대 5줄 위로)". conflict: "추출값이 `# TODO` 로 시작하면 기존 마커 그대로". 정량 acceptance: "≥7개 정확히 파싱". Critic이 구버전 §7.4를 기준으로 판단한 False Positive.

---

#### 11. [REJECT] [Low] §8.6 override write lock spec 미정의

- **Source**: Critic
- **Original Finding**: "§8.6 본문은 함수 시그니처 5줄과 `_build_summary` 호출 1줄뿐이다."
- **Rejection Reason**: 원문 §8.6 (lines 820–861)에 `upsert_override` 전체 pseudocode가 있으며, `locked_file(lock_path, timeout=10)`, `tempfile.mkstemp`, `os.replace`, `os.unlink` 패턴이 명시되어 있다. v4가 실제로 해당 spec을 추가했으며 Critic의 분석 대상이 v3 이전 버전이었던 것으로 판단. False Positive.

---

#### 12. [REJECT] [Low] `config/escalation_policy.yaml` frozen-build 번들 누락

- **Source**: Cross
- **Original Finding**: PyInstaller 빌드에서 policy YAML이 번들되지 않을 수 있음.
- **Rejection Reason**: Cross reviewer가 직접 확인: `af.spec:27`에 `('config', 'config')` datas 항목이 이미 존재. v4 change item 6도 이를 확인. False Positive.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_task_template` `{task_id}` NameError | Critical | ACCEPT | Critic |
| 2 | `EscalationDecision` `affected_phase`/`count` 필드 부재 | Critical | ACCEPT | Both |
| 3 | `load_policy()` fail-open 위험 | High | ACCEPT | Critic |
| 4 | append-only JSONL — edit 후 재실행이 블록 해소 안 됨 | High | ACCEPT | Cross |
| 5 | `execute()` 블록 체크 순서 — user edit sync 전 실행 | High | ACCEPT | Cross |
| 6 | `policy` 파라미터 dead code / 이중 load | Medium | ACCEPT | Both |
| 7 | ISO timestamp string 비교 timezone 오판 | Medium | ACCEPT | Critic |
| 8 | `inject_review_tasks` 경고 스캔 우회 | Medium | ACCEPT | Cross |
| 9 | Override scope — rule 전체 영구 비활성 의도 불명 | Medium | HOLD | Cross |
| 10 | §7.4 backfill parser 스펙 미정의 | Low | REJECT | Critic |
| 11 | §8.6 write lock spec 미정의 | Low | REJECT | Critic |
| 12 | policy YAML frozen-build 번들 누락 | Low | REJECT | Cross |

---

### Recommendations

구현 전 v5에서 반드시 해소할 항목:

1. **[Critical #1]** `§7.3.1` 테이블의 `{task_id}` 표기를 수정하라. `"# TODO: e2e command (build)"` (파라미터 없음) 또는 `_task_template` 시그니처 확장 중 하나를 명시적으로 채택.

2. **[Critical #2]** `EscalationDecision` 필드 목록을 §4.1에 완전히 나열하고, `rule_decisions` 직렬화 시 `affected_phase`/`count` 가 어디서 오는지 알고리즘을 §4.3에 추가.

3. **[High #3]** `load_policy()` 계약: "파일 부재/parse error 시 exception raise, 빈 dict 반환 금지"를 §4.4a에 한 줄 추가.

4. **[High #4 + #5]** "user edits e2e_command → rerun → unblock" 경로를 재설계하거나, §0.1 option (a)를 사용자 안내에서 제거. 현재 설명대로 구현하면 사용자 경험이 broken이다.

5. **[Medium #6]** `evaluate()` 시그니처를 정하고 §4.2 / §4.3에 일관 반영. policy 이중 load 제거.

6. **[Medium #7]** `now_iso()` 포맷 계약(UTC 고정 또는 `fromisoformat()` 비교)을 §5.2 또는 §6.1에 명시.

7. **[Medium #8]** `inject_review_tasks` 에서 생성된 task의 경고 스캔 경로를 §7.3.2 또는 §3.1에 명시.

8. **[Hold #9]** override 유효 범위(영구 vs 조건부)를 §8.4에 명시한 후 HOLD 해소.