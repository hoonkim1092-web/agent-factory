# Design Review: 2026-05-09-p2-e2e-command-block-activation-design

> Source: docs/2026-05-09-p2-e2e-command-block-activation-design.md
> Date: 2026-05-09 23:45
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

3개 Critical 동급(High+, 구현 시 즉시 깨짐) + 4개 High + 3개 Medium 미해결. 특히 Cross #1(`task_id` 미정의), Cross #2(`EscalationDecision` 필드 부족), Cross #3(`_load_policy` fail-open) 셋은 첫 구현 라운드에서 즉각 BUG로 드러나는 사항이며, Critic #2/#3(timezone+race)는 fail-closed 정책 자체를 무력화한다. v3.1의 "Tier 3 PASS" 자체 진단은 무효.

---

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] `_task_template` 의 f-string `{task_id}` 가 미정의 변수
- **Critic**: not flagged
- **Cross**: "`_task_template()` creates raw task dicts before normalized task IDs exist. `task_id` is computed later in `_normalize_tasks()`."
- **Judgment**: 직접 확인. `core/project_task_board.py:337-389` `_task_template`는 `phase/title/instruction/acceptance` 4개 키만 만들고 `id`는 부재. `task_id`는 line 481 `_normalize_tasks` 에서 `safe_id(raw.get("id") or f"{module['id']}_{phase}_{index}")` 로 사후 계산. §7.3.1 의 `f"# TODO: e2e command for {task_id} (build)"` 는 `_task_template` 스코프에서 `NameError`로 즉사한다. acceptance #21 도 mock 없이는 통과 불가.
- **Action Required**: §7.3.1 placeholder 를 `task_id` 미참조 문자열 (예: `"# TODO: e2e command for this task (build)"`) 로 변경하거나, 채움 시점을 `_normalize_tasks` 직후로 이동. §3.2 LOC 표 / §12 baseline grep 표 / acceptance #21 함께 정정.

#### 2. [ACCEPT] [Critical] `EscalationDecision` dataclass 가 직렬화 필드 부족
- **Critic**: "P1 시그니처가 다르면 §8.5 CLI 코드를 baseline에 맞춰 수정" (Finding 5 의 일부 — WarningRegistry 시그니처 별건이지만 동일 패턴)
- **Cross**: "Existing dataclass only has `block/severity/reason/rule_id/activate_at`. Design requires serialized fields `affected_phase` and `count`, but does not specify whether to extend ... wrap ... or enrich during report writing."
- **Judgment**: `core/escalation_evaluator.py:17-23` 직접 확인 — 5개 필드뿐. 그러나 §5.2 `_decision.json` 의 `rule_decisions[]` 항목은 `affected_phase` + `count` 도 요구. 어떻게 흘러가는지 (dataclass 확장 vs DTO 신설 vs writer가 보강) 설계가 결정하지 않음. 구현자가 임의 결정 시 §10/§12 변경 LOC 와 acceptance #11/#12 가 즉시 어긋남.
- **Action Required**: §3.2 / §4.1 에 `EscalationDecision` 확장 필드(`affected_phase: str = ""`, `count: int = 0`)를 명시하거나, `RuleDecisionReport` DTO 신설 + `compute_run_decision` 이 그 DTO 리스트를 반환하도록 시그니처 통일. acceptance #12 에 두 신규 필드 검증 1줄 추가.

#### 3. [ACCEPT] [Critical] `load_policy()` fail-open 이 fail-closed 정책을 정면 위배
- **Critic**: not flagged
- **Cross**: "Today malformed YAML, missing PyYAML, or unreadable policy returns an empty ruleset, which would produce no active blocks instead of an evaluator error."
- **Judgment**: `core/escalation_evaluator.py:50-59` 직접 확인 — `except Exception: return {"version": 0, "rules": []}`. yaml 파싱 실패/PyYAML 부재/권한 문제 시 빈 룰셋 → `compute_run_decision` 의 `for rule_id in by_rule` 루프가 매칭 룰 0개 → `block=False, reason="no_active_blocks_in_run"` → **policy 손상 시 BLOCK 자동 무력화**. §5.4 가 약속한 "evaluator_error" 분기로 진입하지 않는다.
- **Action Required**: §4.4a `load_policy()` public 노출 시 strict 모드 기본값으로 변경 (`PolicyLoadError` raise). §5.4 `summarize()` 의 try/except가 이를 받아 `write_error_decision(reason="policy_load_error")` 로 fail-closed. acceptance #7~#9 에 정책 손상 케이스 1건 추가.

#### 4. [ACCEPT] [High] ISO 8601 stale 검출이 timezone 차이에서 깨짐 (사전식 비교)
- **Critic**: "`if decision_summary_ts and summary_last and decision_summary_ts < summary_last: ... reason='decision_stale'` ... 문자열 사전식 비교는 같은 timezone offset에서만 시간 순서를 보존"
- **Cross**: not flagged
- **Judgment**: §5.2 예시 `+09:00` + §6.1 line 528 의 lexical `<`. 동일 시각이라도 KST↔UTC 표기 차이로 stale false-positive → spurious BLOCK 폭주 가능. 멀티-PC 동기화(§13 P6) 진입 시 곧바로 깨진다.
- **Action Required**: `_decision.json` / `_summary.json` `last_updated` 를 UTC로 정규화하는 `now_iso()` 헬퍼 정의를 §3.2 변경 LOC 에 명시. §6.1 비교를 `datetime.fromisoformat().astimezone(UTC)` 로 파싱 후 비교하거나, `!=` 동치 비교(decision은 정확히 그 summary 의 ts 를 인용해야 valid)로 강화. acceptance #18 에 timezone 차이 케이스 추가.

#### 5. [ACCEPT] [High] reader/writer race — fail-closed 가 spurious BLOCK 윈도우 생성
- **Critic**: "작성자는 `_summary.json.lock` 안에서 summary→decision 순서로 두 파일을 atomic write하지만, reader는 락을 획득하지 않는다"
- **Cross**: not flagged
- **Judgment**: §5.4 writer는 `locked_file(summary_lock_path, timeout=10)` 안에서 summary→decision 순서 작성. §6.1 `read_block_decision()` 은 락 없이 `open(summary_path)` + `open(decision_path)`. summary write 직후 decision write 직전 인터럽트 시 reader가 새 summary + 구 decision → `decision_stale` BLOCK. §11.2 rollback 절차가 락 안에서 atomic 처리를 강조하면서 read 경로만 동일 보호 없는 것은 정합 실패.
- **Action Required**: §6.1 `read_block_decision()` 에 shared-lock 또는 short-timeout exclusive lock 추가, 또는 `generated_from_summary_last_updated == _summary.last_updated` 동치 비교(`<` 가 아닌 `!=` 면 stale)로 시멘틱 강화. acceptance에 "summary write 직후 decision write 전 read" 시나리오 1건 추가.

#### 6. [ACCEPT] [High] `current_phase` 매개변수화가 evaluate 본체에서 깨짐 (single change point 약속 위반)
- **Critic**: "`_is_phase_active` 시그니처는 매개변수화되어 있지만 호출부 `evaluate(record)`가 `\"P2\"` 를 hardcode 한다. `compute_run_decision(..., current_phase=\"P2\")` 는 `current_phase` 를 받지만 그 값을 evaluate에 전파하지 않는다"
- **Cross**: not flagged
- **Judgment**: §4.2 line 172 `_is_phase_active(rule.activate_at, current="P2")` hardcode + §4.3 `evaluate(virtual)` 호출에서 `current_phase` 미전파 + §5.4 `summary["escalation_phase"] = "P2"` hardcode = **3 site change**. §14 #5 가 "P3 진입 시 결정"이라 미루지만, 미루는 만큼 P3 PR 비용 증가. P2 PR 자체에서 helper 한 줄로 정리 가능한 사항.
- **Action Required**: `evaluate(record, *, current_phase: str = "P2")` 로 시그니처 통일 + `compute_run_decision` 이 evaluate에 전파. `summarize()` 도 `_resolve_current_phase()` 헬퍼 1회 호출 → 마커/evaluator/decision 모두 동일 값 사용. §14 #5 "P3 결정" 제거.

#### 7. [ACCEPT] [High] `_decision.md` 가 모든 정책 룰 표시를 약속하지만 `compute_run_decision` 은 record 있는 룰만 본다
- **Critic**: not flagged
- **Cross**: "`compute_run_decision()` pseudocode iterates `summary['by_rule']`. Rules with no records, including inactive policy rules, will never appear in `rule_decisions`, so the markdown table cannot be produced as shown."
- **Judgment**: §5.3 예시 표가 `owner_role_mismatch | inactive_phase`, `evidence_quality_warn | inactive_phase` 행을 보여주지만, §4.3 의사코드는 `for rule_id, info in by_rule.items()` 만 순회. record 0건인 정책 룰은 `rule_decisions` 에 부재 → 예시 표를 만들 수 없음.
- **Action Required**: 둘 중 택일 — (a) `compute_run_decision` 가 `policy["rules"]` 전체를 순회해 record 부재 룰은 `reason="no_records"`/`inactive_phase` 로 명시 추가, 또는 (b) §5.3 표를 "record 있는 rule 만" 으로 좁히고 예시·acceptance 를 그에 맞춰 정정. (a) 를 추천 — 사용자가 "이 룰이 측정되긴 했나?" 를 진단할 수 있어 운영 가치 큼.

#### 8. [ACCEPT] [Medium] `warning-override --slug` path traversal 검증 부재
- **Critic**: not flagged
- **Cross**: "The new CLI writes `_overrides.json` under a slug-derived path, but the design does not say whether `slug` rejects path separators or `..`. ... this new command adds a write surface."
- **Judgment**: §8.1 사용 예시는 `--slug minesweeper-smoke-v2-01` 정상 케이스만. P1 `WarningRegistry` 가 read 경로에서 slug 를 그대로 join 했지만 write 진입점이 신설되므로 보호 신설 시점.
- **Action Required**: `core.warning_overrides.upsert_override()` 진입에서 `validate_warning_slug(slug)` 호출 (또는 `safe_id` 재사용) — 정규화 후 변경되거나 `runtime/warnings` 밖으로 escape 시 reject. acceptance #24 에 `--slug "../../etc"` 거부 케이스 추가.

#### 9. [ACCEPT] [Medium] `_is_e2e_missing` predicate 가 LLM 출력 변형을 못 잡음
- **Critic**: "LLM 산출물은 흔히 `# todo`, `// TODO`, `TODO:`, 한국어 `# TODO 채우기` 등 다양하다. 마커가 미스매치되면 LLM이 `# todo: ...` 로 답변할 때 missing 으로 카운트되지 않아 BLOCK 회피"
- **Cross**: not flagged
- **Judgment**: §7.2 `v.startswith("# TODO") or v.startswith("#TODO")` 만으로는 lowercase / 다른 주석 문법 변형을 놓침. `_clean()` 의 정확한 동작이 baseline 표에 인용되지 않아 lstrip/lowercase 여부 불명확. "의식 강제" 효과가 LLM 변덕에 좌우.
- **Action Required**: `v.lstrip().lower().startswith(("# todo", "#todo", "// todo", "todo:"))` 정도로 확장 + `_clean` lowercase/lstrip 동작을 §7.2 에 명시. acceptance #21~#23 에 lowercase/`//` 변형 1~2건 추가.

#### 10. [ACCEPT] [Medium] `_overrides.json` 손상 silent fallback + 동시성 보호 부재
- **Critic**: "silent fallback 은 corrupted 파일을 빈 overrides 로 가정 → 원래 적용된 override 들이 모두 무력화 → BLOCK 자동 복귀"
- **Cross**: not flagged
- **Judgment**: §11.1 위험 표 자체에 "JSONDecodeError → silent fallback to `{overrides: []}` + warning" 명시. 손상 시 사용자 어제의 override 가 묵시적으로 사라지고 BLOCK 복귀 → "어제 override 했는데 오늘 또 BLOCK" 디버그 단서가 warning 로그 1줄. 동시성 락도 명시 안 됨.
- **Action Required**: `_overrides.json` 도 `_overrides.json.lock` 으로 보호. 손상 시 fail-closed (`block=true, reason="overrides_corrupt"`) + `_overrides.json.bak` 백업 안내. §11.1 위험 표에 "override 데이터 묵시적 손실" 행 추가. (Cross #3 와 같이 묶어 처리하면 정합성 ↑.)

#### 11. [ACCEPT] [Medium] P1 → P2 첫 실행 시 기존 슬러그 silent BLOCK
- **Critic**: "기존 P1 슬러그가 P2 빌드를 처음 받으면 다음 `summarize()` 호출에서 마커가 처음 기록 → 그 직후 `read_block_decision()` 은 fail-closed 분기에 진입 ... 진행 중인 슬러그의 task_board 는 여전히 `e2e_command=\"\"` (P1 기간 생성)"
- **Cross**: not flagged
- **Judgment**: §1.2 가 "yaml만 활성하면 모든 프로젝트 BLOCK" 회피를 위해 e2e 보강을 같이 묶지만, 보강은 **새 work-item 부터** 적용. P1 시기 생성 슬러그는 보강 PR 의 효과를 못 받음 → 첫 P2 실행에서 무조건 BLOCK.
- **Action Required**: §11 또는 신규 §11.3 에 "기존 슬러그 처리" 명시 — 첫 P2 `_decision.md` 에 "P1 시기 생성 슬러그입니다. e2e_command 가 비어있으면 채우거나 `--reason \"P1 legacy\"` 로 override" 안내 문구 고정. acceptance에 "기존 슬러그 첫 P2 실행" 케이스 1건 추가.

#### 12. [REJECT] [Critical→Low] `core.escalation_evaluator` af.spec hiddenimports 누락
- **Critic**: "evaluator 가 P1 hiddenimports에 부재하다면, 첫 P2 frozen 빌드에서 `summarize()` 의 evaluator import 가 ImportError"
- **Cross**: not flagged
- **Source/Judgment**: 직접 확인 — `af.spec:39-40` 에 `'core.escalation_evaluator'`, `'core.warning_registry'` 둘 다 이미 등록. 따라서 frozen 빌드 ImportError 위험은 신규 2개 (`escalation_decision_report`, `warning_overrides`) 에 한정되며 §10 가 이미 그것을 명시. 기각.
- **Rejection Reason**: 잘못된 baseline 가정 — 실제 `af.spec` 에 evaluator 가 P1 등록되어 있음. 다만 critic 의 후속 제안인 "frozen 빌드 산출물(`dist/af/af.exe`) 기준 import smoke 1회" 는 §9 acceptance 에 추가하면 도움 됨 — **부분 권장 (Medium)** 으로 흡수.

#### 13. [REJECT] [High→없음] `WarningRegistry(workspace=...).summarize(project_slug=...)` 시그니처 미검증
- **Critic**: "P1 `WarningRegistry` 의 생성자가 `workspace=` 단일 키워드로 인스턴스화 가능한지 본 문서는 grep 으로 입증하지 않는다"
- **Cross**: not flagged
- **Source/Judgment**: 직접 확인 — `core/warning_registry.py:68` `def __init__(self, workspace: str) -> None:` (단일 positional). `WarningRegistry(workspace=args.workspace)` 는 keyword 호출 가능. `summarize(self, *, project_slug: str)` (line 166) 도 keyword-only 와 일치. §8.5 호출이 baseline 과 정합.
- **Rejection Reason**: 시그니처 충돌 없음. 다만 critic 의 권장(§12 baseline grep 표에 시그니처 1줄 인용) 은 advisory 로 수용 권장 — Cross #2 와 함께 처리하면 정합.

#### 14. [REJECT] [Medium→Low] virtual record 의 per-phase count vs 전역 repeat_count 혼용
- **Critic**: "`count` 은 phase 단위, `repeat_count` 은 rule 전체 max. ... P4 가 `owner_role_mismatch.repeat_count_min: 3` 같은 정책을 추가하는 순간 — phase A에서 1번, phase B에서 3번 발생한 케이스가 — phase A의 virtual record 에서 (count=1, repeat_count=3) 으로 false-block"
- **Cross**: not flagged
- **Source/Judgment**: §4.4b advisory 가 이미 P4 dataclass 분리를 명시. P2 정책(`e2e_command_missing`)은 `repeat_count_min` 미설정이라 본 PR 에서 false-block 위험 없음. critic 의 "P2 PR에서 미리 분리" 제안은 합리적이지만 advisory — 본 PR 의 BLOCK 사유는 아님.
- **Rejection Reason**: 본 PR scope 내 작동 영향 없음. P4 진입 시 처리하는 §4.4b advisory 로 충분. **§4.4b 에 "분리 시 P4 PR 도입 비용" 1줄만 보강** (advisory 흡수).

#### 15. [REJECT] [Medium→none] `_task_template` +18 LOC 추정의 근거 불명
- **Critic**: "두 phase 에 dict 키 1개씩 추가 = 2 LOC + 헬퍼 1~2줄이면 충분. +18 LOC 는 다른 변경이 묵시적으로 들어있다는 신호"
- **Cross**: not flagged
- **Source/Judgment**: LOC 추정의 정확성은 PR 리뷰 시점에 다시 점검되는 사항이며 설계 BLOCK 사유는 아님. 다만 critic 의 "코드 diff 예시 인용" 제안은 surgical-changes 정합성 확보에 유용.
- **Rejection Reason**: 본 PR scope 내 위험 없음. 구현 시 LOC 가 +6 으로 줄면 §3.2/§12 표 정정만으로 처리 가능.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | `_task_template` 의 `task_id` 미정의 f-string | Critical | ACCEPT | Cross |
| 2 | `EscalationDecision` 직렬화 필드 누락 | Critical | ACCEPT | Cross |
| 3 | `_load_policy` fail-open 이 fail-closed 위배 | Critical | ACCEPT | Cross |
| 4 | ISO 8601 lexical 비교 timezone 깨짐 | High | ACCEPT | Critic |
| 5 | reader/writer race spurious BLOCK | High | ACCEPT | Critic |
| 6 | `current_phase` hardcode 다중 지점 | High | ACCEPT | Critic |
| 7 | `_decision.md` 전 룰 표 vs by_rule 한정 | High | ACCEPT | Cross |
| 8 | `warning-override --slug` path validation | Medium | ACCEPT | Cross |
| 9 | `_is_e2e_missing` predicate 변형 누락 | Medium | ACCEPT | Critic |
| 10 | `_overrides.json` 손상 silent fallback | Medium | ACCEPT | Critic |
| 11 | P1→P2 기존 슬러그 첫 실행 BLOCK | Medium | ACCEPT | Critic |
| 12 | `escalation_evaluator` hiddenimports | Critical | REJECT | Critic |
| 13 | `WarningRegistry` 시그니처 미검증 | High | REJECT | Critic |
| 14 | virtual record per-phase count 혼용 | Medium | REJECT | Critic |
| 15 | `_task_template` +18 LOC 근거 불명 | Medium | REJECT | Critic |

---

### Recommendations

구현 진입 차단. v3.2 로 다음 순서대로 정정:

1. **#1 우선** — `_task_template` placeholder 를 `task_id` 미참조 문자열로 변경 (§7.3.1, §3.2 LOC, §12 grep 표, acceptance #21 동시 정정).
2. **#2 우선** — `EscalationDecision` 확장 또는 `RuleDecisionReport` DTO 신설 결정. §3.2 / §4.1 / §10 / acceptance #12 동시 갱신.
3. **#3 우선** — `load_policy()` strict 모드 (PolicyLoadError raise) + §5.4 try/except 가 `write_error_decision(reason="policy_load_error")` 로 흡수. acceptance #7~#9 케이스 추가.
4. **#4** — `now_iso()` UTC 강제 헬퍼를 §3.2 에 추가 정의 + §6.1 비교 의사코드를 `datetime.fromisoformat().astimezone(UTC)` 로 정정 또는 `!=` 동치 비교로 강화.
5. **#5** — §6.1 `read_block_decision()` 에 short-timeout shared/exclusive lock 추가 또는 동치 비교로 race 윈도우 제거. acceptance #18 에 race 케이스 추가.
6. **#6** — `evaluate(record, *, current_phase)` 시그니처 통일 + `_resolve_current_phase()` 헬퍼 1회 호출. §14 #5 의 "P3 결정" 제거.
7. **#7** — `compute_run_decision` 가 `policy["rules"]` 전체 순회하도록 변경 (record 없으면 `reason="no_records"`). §5.3 예시 표 유지 가능.
8. **#8~#11** — 보조 정정 (slug validation, predicate 확장, overrides 락+fail-closed, P1→P2 안내 문구).
9. 정정 후 **af-cross-review 1라운드 재실행** (Critic 재실행 불필요 — 본 회차의 12개 finding 이 코드/설계 인용 강도 충분). PASS 판정 후 §15 v3.2 이력 추가하고 PR 진입.