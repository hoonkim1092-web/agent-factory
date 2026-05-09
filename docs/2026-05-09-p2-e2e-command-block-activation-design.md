# P2 — e2e_command_missing BLOCK 활성화 설계

- 작성일: 2026-05-09
- 모델: Opus 4.7 (1M)
- 의존: `docs/2026-05-09-warning-registry-and-gate-escalation-design.md` (v6, P1)
- 브랜치: `2026-05-07-memory-gitignore-cleanup` (또는 P2 전용 후속 브랜치)
- 상태: v4.1 (v4 cross-review WARN advisory 1건 흡수 — §7.4 backfill regex를 splitlines() 기반으로 교정)
- 이력:
  - v1 (2026-05-09 KST 16:30) — 초안
  - v2 (2026-05-09 KST 17:30) — Tier 3 BLOCK 5건 수용
  - v3.1 (2026-05-09 KST 19:00) — v3 WARN advisory 3건 흡수: §12 `_is_e2e_missing` predicate 변경 / `repeat_count_max` 명시 / `escalation_decision_report` import 제약
  - v4 (2026-05-10) — v3.1 cross-review BLOCK 10건 수용:
    1) §3.1/§5.4 — summarize() 트리거 위치를 `work_item_generator.py` 명시 (initialize() 내부가 아님)
    2) §7.3.3 — LLM prompt 타겟을 fallback line 556 → 실 prompt lines 787-800으로 교정
    3) §8.5 — `_STAGE1_DISPATCH`/`_STAGE1_USAGE` 이미 반영됨 (false positive 확인)
    4) §5.4/§8.5/§9 — body drift 검증 완료 (v3 변경 전부 반영됨)
    5) §0.1/§1 — `# TODO:` 첫 실행 차단 정책 명시 (모순 해소, Policy B 채택)
    6) §10 — af.spec datas 이미 `config/` 전체 번들 확인 + hiddenimports 신규 2개 추가
    7) §6.1 — phase 순방향 호환 규칙 추가 (P2→P3 업그레이드 시 기존 decision 유효)
    8) §8.6 — override 쓰기 락 spec 추가 (`locked_file` + atomic replace)
    9) §7.4 — backfill parser 계약 명시 (regex / task_id / conflict / 정량 acceptance)
    10) §11.2 — `AF_SKIP_ESCALATION=1` 이미 반영됨 (body drift false positive 확인)
  - v3 (2026-05-09 KST 18:30) — v2 BLOCK 2건 + advisory 5건 수용:
    1) §5.4 fail-closed import를 try 안으로 이동 (import 실패도 fail-closed)
    2) §8.5 dispatch dict 변수명을 baseline `_STAGE1_DISPATCH`/`_STAGE1_USAGE`로 정정
    3) §3.2 / §12 표의 `_task_template` 변경 phase 표기 통일 (build/verify는 `# TODO:`, scope는 필드 부재)
    4) §11.2 rollback atomicity — 락 + 순서 + emergency env var
    5) §6.1 / §10 — `import json` PR file list에 명시
    6) §9.6 #20 hermetic 명시 (LLM stub + jsonl seed)
    7) §9 제목 "23 케이스" → "25 케이스" 정정

---

## §0 Goal — 한 줄 정의

> P1이 깐 데이터/스키마 위에서 **`e2e_command_missing` 단일 rule을 phase-aware BLOCK으로 활성**한다. baseline 코드의 빈 `e2e_command` 결측을 **실측해보고**, BLOCK 활성에 의해 첫 실행이 즉시 막히지 않도록 **소스 fix 동시 PR**.

### 0.1 P1 vs P2 경계 (사용자 가시 변화)

| 항목 | P1 (완료) | P2 (본 설계) |
|------|-----------|-------------|
| `WarningRecord` jsonl 누적 | ✅ | (그대로) |
| `_summary.json` 재계산 | ✅ | (그대로) |
| `escalation_evaluator.evaluate()` body | stub (모두 `block=False`) | **policy 매칭 실 구현** |
| `_decision.md` 자동 생성 | path만 렌더 | **본문 작성 + `_decision.json` sidecar** |
| BLOCK 강제 (pipeline halt) | 없음 | **`execute()` 진입 차단** |
| `_task_template` `e2e_command` 채움 | 빈값 | **phase별 `# TODO:` 마커 추가 (BLOCK 트리거 — 의도된 동작)** |
| 사용자 우회 경로 | 없음 | **`af warning-override ...` CLI 1개** |

> **P2 첫 실행 동작**: `_task_template`이 생성한 `# TODO:` 마커는 `_is_e2e_missing()` 에 의해 missing으로 인식되어 `e2e_command_missing` record 발생 → `execute()` BLOCK. 사용자는 (a) 각 task의 `e2e_command` 필드를 실제 명령으로 채운 후 재실행, (b) `af warning-override`로 false-positive 처리, (c) policy 비활성(`activate_at: never`) 중 하나로 해소한다. **"첫 빌드를 즉시 통과"는 P2의 설계 목표가 아니다.** 빌드 통과 전 의도적인 검증 gate를 강제하는 것이 P2의 목적.

---

## §1 문제 — 왜 P2가 "yaml 한 줄"이 아닌가

### 1.1 baseline grep 사실 (실측)

| 파일:줄 | 사실 |
|---------|------|
| `core/project_task_board.py:337-389` `_task_template()` | tasks 생성 시 `e2e_command` 필드 자체를 만들지 않음 (phase/title/instruction/acceptance만) |
| `core/project_task_board.py:497` `_normalize_tasks()` | `raw.get("e2e_command") or ""` — `_task_template` 결과를 normalize 시 항상 `""` |
| `core/escalation_evaluator.py:62-70` `evaluate()` | P1 stub. 항상 `EscalationDecision(block=False, severity="warn", reason="inactive_phase")` 반환 |
| `core/escalation_evaluator.py` production 호출처 | grep 결과 0건 (파일 자체 외) |
| `core/approval_gate.py:351-353` | `_decision.md` path만 line으로 렌더, 실제 작성 코드 없음 |
| `config/escalation_policy.yaml:6-13` | `e2e_command_missing.activate_at: P2` + `block_when.affected_phase_in: [build, integrate, code_review, cross_validate, verify]` + `count_per_run_min: 1` |

### 1.2 결과: yaml만 활성하면 모든 프로젝트 BLOCK

`_task_template`이 build/verify phase에서 `e2e_command=""`인 task를 생성 → `work_item_generator.py:1048-1086`이 `e2e_command_missing` record 생성 → policy `count_per_run_min: 1` → **BLOCK**.

→ P2는 BLOCK 활성과 **소스 fix를 한 PR**로 묶지 않으면 "사용자가 처음 P2 빌드를 받자마자 본인 프로젝트가 막히는" 첫인상을 주게 됨.

---

## §2 Scope (사용자 합의 — 2026-05-09)

### 2.1 포함 (한 PR)

1. `escalation_evaluator.evaluate()` 본체 — policy 매칭, phase-aware 분기
2. `_decision.md` writer + `_decision.json` sidecar — `summarize()` 호출 시 동기 생성
3. `ApprovalGate` BLOCK 강제 — `is_execution_open()` 또는 별도 `check_block_decision()`
4. `project_pipeline.execute()` 진입 차단 — `is_execution_open() and not block_decision.block` 보장
5. `_task_template` e2e_command 생성 — phase별 placeholder + LLM tasks-prompt 강화
6. `warning-override` CLI — marker 파일 작성 / 후속 record는 `false_positive_override=true`로 평가 제외

### 2.2 제외 (P3+ 또는 별 PR)

- `owner_role_mismatch` BLOCK 활성 (P4)
- `evidence_quality_warn` BLOCK 활성 (P4)
- 글로벌 누적 통계 (`load_global`) (P4)
- doc_consistency_meter (P5)

---

## §3 Architecture

### 3.1 데이터 흐름 (P2 추가분 굵게)

```
  work_item_generator
    └─→ _task_template / LLM tasks         ← (소스 fix: e2e_command 채움)
    └─→ WarningRegistry.record(e2e_command_missing, ...)   [P1]
    └─→ WarningRegistry(workspace).summarize(project_slug=slug)  ★P2 ← [record loop 직후, gate.initialize() 직전]
          └─→ compute_run_decision(summary, policy)        ★P2
          └─→ write_decision_report(decision, slug_dir)    ★P2
                ├─→ _decision.md  (사용자 노출)
                └─→ _decision.json (machine parse)
    └─→ ApprovalGate(doc_root, slug, runtime_workspace=ws)
          └─→ initialize()
              └─→ _render() 에 gate_decision_report: 절대경로  [P1]

  project_pipeline.execute()
    └─→ gate.is_execution_open()                            [P1]
    └─→ gate.read_block_decision()                         ★P2
          └─→ if blocked: return ok=False, reason="escalation_block", ...
```

> **wiring 위치 확정**: `summarize()` 는 `work_item_generator.py` 안에서 `record()` 루프(line ~1086) 직후, `gate = ApprovalGate(...)` 생성(line ~1087) 직전에 호출한다. `ApprovalGate.initialize()` 자체는 `WarningRegistry` import 없음 — P1 동작 그대로 유지. `initialize()`가 내부에서 summarize를 호출하는 구조는 **채택하지 않는다** (책임 분리: gate는 reader, summarize/decision 작성은 generator 책임).

### 3.2 모듈별 변경

| 파일 | 변경 | LOC 추정 |
|------|------|---------|
| `core/escalation_evaluator.py` | stub → 실 구현. `evaluate(record)` + 신규 `compute_run_decision(summary, policy)` + `load_policy()` public 노출 | +130 |
| `core/escalation_decision_report.py` (신규) | `write_decision_report(decision, slug_dir, *, summary_last_updated)` + `write_error_decision(...)` — md + json 동시 작성, `decision_schema_version` + `generated_from_summary_last_updated` 포함. **leaf writer**: `core.warning_registry` module-level import 금지 (RunDecision-like dataclass + slug_dir + summary_last_updated 파라미터만 받아 작성). `core.escalation_evaluator` 의 `RunDecision`/`EscalationDecision` 만 import 허용 | +95 |
| `core/approval_gate.py` | `read_block_decision()` 추가 (fail-closed, stale/escalation_phase 검증). top-level `import json` 추가 (현재 imports = `hashlib/os/re`만, `json` 없음). `_render()` 변경 없음 | +52 |
| `core/project_pipeline.py:1268-` | `execute()` 진입 시 block 체크 추가 | +20 |
| `core/project_task_board.py:337-389` `_task_template` | build/verify phase task에 `e2e_command="# TODO: ..."` 마커 추가. scope phase는 필드 부재 (정책 exempt) | +18 |
| `core/project_task_board.py:1025-1130` `inject_review_tasks` | code_review/cross_validate 태스크에 `e2e_command="# TODO: ..."` 마커 추가 | +6 |
| `core/work_item_generator.py:556` | tasks LLM prompt에 "e2e_command 채워라" 강제. **`# TODO:` 마커 명시 강제** | +8 |
| `core/work_item_generator.py:1048-1086` | missing 검사 보강 — 빈문자열 OR `# TODO:` 시작 모두 missing으로 카운트 | +6 |
| `core/work_item_generator.py` | `_backfill_e2e_from_tasks_md` 신규 + 호출 | +30 |
| `core/warning_registry.py` | `summarize()` 끝 decision 트리거 (try/except 시 fail-closed: `block=true, reason="evaluator_error"` 강제 작성). `_build_summary` 가 **`any_override` + `repeat_count_max` 두 필드 추가**. `_summary.json`에 `escalation_phase` 마커 도입 | +50 |
| `core/warning_overrides.py` (신규) | overrides_path / load / upsert / remove / is_overridden | +50 |
| `run_factory_cli.py` | `warning-override` 서브커맨드 — `_run_warning_override_subcommand` + dispatch dict + help string (기존 패턴 일치) | +70 |
| `config/escalation_policy.yaml` | 변경 없음 (P1 그대로) | 0 |
| `tests/test_escalation_evaluator.py` (신규) | evaluate / compute_run_decision / load_policy 케이스 | +200 |
| `tests/test_decision_report.py` (신규) | md/json writer + stale 검출 | +90 |
| `tests/test_pipeline_block_enforcement.py` (신규) | execute() 차단 (fake gate mock + 통합 smoke 분리) | +80 |
| `tests/test_warning_override_cli.py` (신규) | CLI 동작 + dispatch dict wiring | +60 |
| `tests/test_task_template_e2e_command.py` (신규) | _task_template 회귀 (scope/build/verify) | +30 |
| `tests/test_inject_review_tasks_e2e_command.py` (신규) | inject_review_tasks 회귀 (code_review/cross_validate) | +30 |
| `tests/test_summary_schema_repeat_count.py` (신규) | _build_summary 산출 schema (count/first_ts/last_ts/severity/by_phase + **repeat_count_max + any_override**) | +40 |
| `Master_Blueprint.md` | §3 evaluator/decision/overrides 섹션 + §12 이력 | +35 |

총: ≈ 950 LOC 가산. 순수 production 코드 ≈ 415 LOC.

---

## §4 escalation_evaluator 본체 설계

### 4.1 시그니처 (P1 stub과 호환)

```python
# 기존 (P1)
def evaluate(record: WarningRecord) -> EscalationDecision: ...

# P2 추가
def compute_run_decision(
    summary: dict, policy: dict, *, current_phase: str = "P2"
) -> RunDecision: ...

@dataclass
class RunDecision:
    block: bool
    blocking_rules: list[str]              # ["e2e_command_missing"]
    rule_decisions: list[EscalationDecision]
    reason: str                            # "no_active_rules" | "all_below_threshold" | "blocked_by:<rule>"
    activate_phase: str                    # "P2"
    summary_snapshot: dict                 # _summary.json 그대로 임베드 (디버깅용)
```

`evaluate(record)`는 단일 record 평가 (P4 글로벌 분석 진입점). `compute_run_decision`은 슬러그의 summary 전체로 run-level 결정.

### 4.2 evaluate(record) 의사코드

```python
def evaluate(record: WarningRecord) -> EscalationDecision:
    policy = _load_policy()
    rule = _find_rule(policy, record.rule_id)
    if rule is None or rule.activate_at == "never":
        return EscalationDecision(block=False, severity="warn",
                                  reason="rule_not_active", rule_id=record.rule_id,
                                  activate_at=rule.activate_at if rule else "")

    # P2 단계 — activate_at: P2만 평가 (P3는 측정만, P4는 그 이상)
    if not _is_phase_active(rule.activate_at, current="P2"):
        return EscalationDecision(block=False, severity="warn",
                                  reason="inactive_phase", rule_id=record.rule_id,
                                  activate_at=rule.activate_at)

    if record.false_positive_override:
        return EscalationDecision(block=False, severity="warn",
                                  reason="false_positive_override",
                                  rule_id=record.rule_id, activate_at=rule.activate_at)

    # exempt 우선 — 매칭되면 즉시 면제
    if rule.exempt_when:
        ex_phases = rule.exempt_when.get("affected_phase_in") or []
        if record.affected_phase in ex_phases:
            return EscalationDecision(block=False, severity="warn",
                                      reason=f"exempt_phase:{record.affected_phase}",
                                      rule_id=record.rule_id, activate_at=rule.activate_at)

    # block_when 매칭
    bw = rule.block_when or {}
    cond_phase = bw.get("affected_phase_in")
    cond_count = bw.get("count_per_run_min", 1)
    cond_repeat = bw.get("repeat_count_min", 0)

    phase_match = (cond_phase is None) or (record.affected_phase in cond_phase)
    count_match = record.count >= cond_count
    repeat_match = record.repeat_count >= cond_repeat

    if phase_match and count_match and repeat_match:
        return EscalationDecision(block=True, severity="block",
                                  reason="threshold_met", rule_id=record.rule_id,
                                  activate_at=rule.activate_at)

    return EscalationDecision(block=False, severity="warn",
                              reason="below_threshold", rule_id=record.rule_id,
                              activate_at=rule.activate_at)
```

### 4.3 compute_run_decision 의사코드

```python
def compute_run_decision(summary: dict, policy: dict, *, current_phase="P2") -> RunDecision:
    by_rule = summary.get("by_rule") or {}
    rule_decisions: list[EscalationDecision] = []
    blocking: list[str] = []

    for rule_id, info in by_rule.items():
        rule = _find_rule(policy, rule_id)
        if rule is None:
            continue
        # by_phase 분포로 phase별 가상 record를 만들어 evaluate에 위임
        # (record-level 로직 재사용 → 분기 단일화)
        for phase, count in (info.get("by_phase") or {}).items():
            virtual = WarningRecord(
                rule_id=rule_id, severity=info.get("severity", "warn"),
                affected_phase=phase, count=count,
                repeat_count=info.get("repeat_count_max", 1),
                false_positive_override=info.get("any_override", False),
                project_slug=summary["project_slug"], ts=info.get("last_ts", ""),
                rationale="(aggregated)", affected_ids=[],
                source_path="(aggregated)", extra={},
                schema_version=1, record_id="(aggregated)",
                baseline_delta=0.0,
            )
            d = evaluate(virtual)
            rule_decisions.append(d)
            if d.block:
                blocking.append(rule_id)

    if blocking:
        reason = f"blocked_by:{','.join(sorted(set(blocking)))}"
        return RunDecision(block=True, blocking_rules=sorted(set(blocking)),
                           rule_decisions=rule_decisions, reason=reason,
                           activate_phase=current_phase, summary_snapshot=summary)
    return RunDecision(block=False, blocking_rules=[],
                       rule_decisions=rule_decisions,
                       reason="no_active_blocks_in_run",
                       activate_phase=current_phase, summary_snapshot=summary)
```

### 4.4 false_positive_override 처리 (run-level)

`info.get("any_override")`는 그 rule의 record 중 **하나라도** override 되었으면 True. 운영상 override는 "이 슬러그의 이 rule은 통째로 false positive" 의미이므로 단일 토큰 충분. 세분화(record_id별 override)는 P4.

→ 따라서 `_summary.json` 산출에 `any_override: bool` 필드 추가 필요. **`_build_summary` 마이너 변경**.

### 4.4a `load_policy()` public 노출

기존 `_load_policy()` private 함수를 `load_policy()` public 으로 rename. private API에 호출처가 생기지 않도록 P2 진입 시 정리. `core.warning_registry.summarize()` 가 `from core.escalation_evaluator import load_policy, compute_run_decision` 를 명시적으로 import.

### 4.4b virtual record 패턴의 P4 분리 노트 (advisory)

`compute_run_decision`이 evaluate(virtual_record)를 호출하는 분기 단일화 패턴은 P2 정책 매칭에는 안전(필요 필드 = `rule_id`/`affected_phase`/`count`/`repeat_count`/`false_positive_override`만). 그러나 P4에서 record-level 글로벌 분석이 도입되면 dummy 필드(`record_id="(aggregated)"` 등)가 오염원이 될 수 있다.

→ **P4 진입 시점**에 `evaluate_record(record)` / `evaluate_aggregate(rule_id, phase, count, repeat_count, override)` 두 함수로 분리하거나, aggregate 전용 dataclass 도입. 본 P2 PR scope 외.

### 4.5 `_is_phase_active(rule.activate_at, current="P2")`

```python
_PHASE_ORDER_ESCALATION = {"never": -1, "P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "P6": 6}

def _is_phase_active(rule_phase: str, current: str) -> bool:
    return (
        _PHASE_ORDER_ESCALATION.get(rule_phase, -1) >= 1
        and _PHASE_ORDER_ESCALATION.get(rule_phase, -1) <= _PHASE_ORDER_ESCALATION.get(current, 0)
    )
```

`current_phase`는 P2 PR에선 상수 `"P2"`. 향후 P3/P4 진입 시 환경변수 또는 build 메타에서 읽도록 확장 (P3 설계에서 결정).

---

## §5 Decision Report — md + json

### 5.1 파일 위치

```
<runtime_workspace>/runtime/warnings/<slug>/
  ├── _summary.json               (P1)
  ├── _summary.json.lock          (P1)
  ├── _decision.md                ★P2 — 사용자 노출
  ├── _decision.json              ★P2 — pipeline read
  └── <rule_id>.jsonl             (P1)
```

### 5.2 `_decision.json` schema

```json
{
  "decision_schema_version": 1,
  "project_slug": "minesweeper-smoke-v2-01",
  "last_updated": "2026-05-09T16:00:00+09:00",
  "generated_from_summary_last_updated": "2026-05-09T16:00:00+09:00",
  "escalation_phase": "P2",
  "block": true,
  "activate_phase": "P2",
  "blocking_rules": ["e2e_command_missing"],
  "reason": "blocked_by:e2e_command_missing",
  "rule_decisions": [
    {
      "rule_id": "e2e_command_missing",
      "block": true,
      "severity": "block",
      "reason": "threshold_met",
      "activate_at": "P2",
      "affected_phase": "build",
      "count": 14
    },
    {
      "rule_id": "e2e_command_missing",
      "block": false,
      "severity": "warn",
      "reason": "exempt_phase:scope",
      "activate_at": "P2",
      "affected_phase": "scope",
      "count": 3
    }
  ],
  "summary_snapshot": { /* _summary.json 그대로 */ }
}
```

**stale 검출 키**:
- `decision_schema_version` — schema 진화 시 bump (P4가 record-level scope 추가하면 v2)
- `generated_from_summary_last_updated` — `_summary.json.last_updated` 와 비교. 더 오래된 decision이면 stale → fail-closed
- `escalation_phase` — decision이 어느 phase 정책으로 평가됐는지. 호출자가 기대 phase와 다르면 fail-closed

### 5.3 `_decision.md` 포맷 (사용자 노출)

```markdown
# Escalation Decision — minesweeper-smoke-v2-01

- last_updated: 2026-05-09T16:00:00+09:00
- activate_phase: P2
- block: true
- blocking_rules: e2e_command_missing
- reason: blocked_by:e2e_command_missing

## 차단 근거

### e2e_command_missing
- block_when: affected_phase_in=[build,integrate,code_review,cross_validate,verify], count_per_run_min=1
- 매칭 phase: build (14건), verify (4건)
- exempt phase: scope (3건)

**해소 방법** (택 1):
1. 각 task의 `e2e_command` 필드를 채운 후 work-item 문서 재생성
2. `af warning-override --workspace . --slug minesweeper-smoke-v2-01 --rule e2e_command_missing --reason "<이유>"` 로 false-positive 표시
3. `config/escalation_policy.yaml` 에서 `e2e_command_missing.activate_at` 을 `never` 로 변경 (전역 비활성, 권장하지 않음)

## 평가된 모든 규칙
| rule_id | block | severity | reason |
|---------|-------|----------|--------|
| e2e_command_missing | true | block | threshold_met |
| owner_role_mismatch | false | warn | inactive_phase |
| evidence_quality_warn | false | warn | inactive_phase |

## 부록: summary 스냅샷
(_summary.json 본문 임베드)
```

`_decision.md` 는 **summarize() 호출마다 덮어씀**. 누적 로그 아님 (=v6 §6.3 정합).

### 5.4 trigger — 언제 작성하나

`WarningRegistry.summarize()` 끝에서 decision report를 자동 작성. 호출처:

**①  `work_item_generator.py` — record loop 직후, gate.initialize() 직전**

```python
# work_item_generator.py  (P2 추가, record loop 바로 아래)
# P2: summarize → decision report 작성 (fail-closed)
try:
    _WR(workspace=workspace).summarize(project_slug=slug)
except Exception as _sum_exc:
    _LOGGER.warning("warning_registry summarize failed: %s", _sum_exc)

gate = ApprovalGate(doc_root, slug, runtime_workspace=workspace)
gate.initialize(work_item_id, run_id=run_id)
```

`WarningRegistry` 임포트는 이미 record loop에서 `_WR`로 바인딩됨 (P1 그대로).

**② `run_factory_cli.py warning-summary` / `warning-repair`** CLI도 같은 경로.

`ApprovalGate.initialize()` 는 `WarningRegistry` import **없음** — P1 동작 유지, 독립 단위 테스트 그대로.

→ **`WarningRegistry.summarize()` 수정**: 끝에서 `compute_run_decision` + `write_decision_report` 호출. `_summary.json` 락 안에서 함께 실행 (atomic 보장). **fail-closed**: 평가 실패 시 `block=true, reason="evaluator_error"` decision을 강제 작성 (silent skip 금지). **import 자체도 try 블록 안**에 두어 ImportError(circular / missing module / frozen build hiddenimports 누락) 케이스에서도 fail-closed 보장.

```python
def summarize(self, *, project_slug: str) -> dict:
    ...
    with locked_file(summary_lock_path, timeout=10):
        summary = _build_summary(project_slug, slug_dir)
        # _summary.json 에 escalation_phase 마커 포함
        summary["escalation_phase"] = "P2"
        # ... atomic write _summary.json ...

        # P2: decision report (fail-closed — import 실패도 차단 처리)
        try:
            from core.escalation_evaluator import (
                compute_run_decision, load_policy,
            )
            from core.escalation_decision_report import (
                write_decision_report, write_error_decision,
            )
            decision = compute_run_decision(
                summary, load_policy(), current_phase="P2"
            )
            write_decision_report(
                decision, slug_dir,
                summary_last_updated=summary["last_updated"],
            )
        except Exception as exc:
            _LOGGER.error("decision evaluator failure — fail-closed: %s", exc)
            # write_error_decision도 같은 신규 모듈에 있으므로 import 실패면 호출 불가.
            # 그래서 본 함수는 "JSON dict를 직접 작성하는 fallback" 까지 가진다.
            try:
                from core.escalation_decision_report import write_error_decision
                write_error_decision(
                    slug_dir, project_slug=project_slug,
                    summary_last_updated=summary["last_updated"],
                    error_repr=repr(exc),
                )
            except Exception:
                # 마지막 fallback — 최소 키만 직접 dump
                _write_minimal_block_decision(
                    slug_dir, project_slug=project_slug,
                    summary_last_updated=summary["last_updated"],
                    error_repr=repr(exc),
                )
            # Note: _summary.json 자체는 성공적으로 작성됨. decision만 error 상태.

    return summary


def _write_minimal_block_decision(slug_dir, *, project_slug, summary_last_updated, error_repr):
    """write_error_decision import도 실패한 극단 케이스용 최소 _decision.json."""
    payload = {
        "decision_schema_version": 1,
        "project_slug": project_slug,
        "last_updated": now_iso(),
        "generated_from_summary_last_updated": summary_last_updated,
        "escalation_phase": "P2",
        "block": True,
        "blocking_rules": [],
        "reason": "evaluator_import_error",
        "error": error_repr,
    }
    path = os.path.join(slug_dir, "_decision.json")
    fd, tmp = tempfile.mkstemp(dir=slug_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
```

`write_error_decision`는 `block=true, reason="evaluator_error", blocking_rules=[]`인 `_decision.json`+`_decision.md`를 강제 작성. pipeline.execute()는 이를 보고 BLOCK 처리.

→ **순환 import 주의**: `warning_registry.py`는 `escalation_evaluator`/`escalation_decision_report`를 함수 내부에서 import. evaluator는 warning_registry의 `WarningRecord`만 module-level import (이미 P1).

---

## §6 ApprovalGate / Pipeline 강제 wiring

### 6.1 ApprovalGate.read_block_decision() — fail-closed

**시멘틱**:
- `_summary.json` 부재 → P1 호환 (fail-open: `(False, None)`)
- `_summary.json` 존재 + `escalation_phase` 마커 있음 → P2 환경. `_decision.json` 누락/stale/parse error 시 **fail-closed**: `(True, {"block": True, "reason": "decision_missing_or_stale", ...})`
- `_decision.json` 정상 → 그 값 그대로

```python
def read_block_decision(self) -> tuple[bool, dict | None]:
    # emergency env switch — rollback 시 사용 (P1 호환 동등 동작)
    if os.environ.get("AF_SKIP_ESCALATION") == "1":
        return False, None

    warnings_dir = os.path.join(
        self.runtime_workspace, "runtime", "warnings", self.slug
    )
    summary_path = os.path.join(warnings_dir, "_summary.json")
    decision_path = os.path.join(warnings_dir, "_decision.json")

    # P1 호환: summary 자체가 없으면 escalation 환경 아님 → fail-open
    if not os.path.isfile(summary_path):
        return False, None
    try:
        with open(summary_path, encoding="utf-8") as fh:
            summary = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return False, None

    expected_phase = summary.get("escalation_phase")
    summary_last = summary.get("last_updated", "")

    # 마커 없는 summary → P1 산출. fail-open
    if not expected_phase:
        return False, None

    # 여기부터는 P2+ 환경 → fail-closed 분기
    if not os.path.isfile(decision_path):
        return True, {
            "block": True,
            "reason": "decision_missing",
            "blocking_rules": [],
            "expected_phase": expected_phase,
        }
    try:
        with open(decision_path, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return True, {
            "block": True,
            "reason": "decision_parse_error",
            "blocking_rules": [],
            "expected_phase": expected_phase,
        }

    # phase 검증 — 순방향 호환 (old decision은 새 phase에서도 유효)
    _PHASE_ORDER_EC = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "P6": 6}
    decision_phase = d.get("escalation_phase", "")
    decision_phase_num = _PHASE_ORDER_EC.get(decision_phase, 0)
    expected_phase_num = _PHASE_ORDER_EC.get(expected_phase, 0)
    # decision이 현재 phase보다 낮은 버전으로 평가됨 → old policy 기준이지만 순방향 허용
    # (policy 조건이 강화되면 stale 재계산이 필요하나, P2→P3 upgrade 시 즉시 차단은 과도)
    # decision이 expected_phase보다 미래 phase로 평가됨 → 이상 상태 → fail-closed
    if decision_phase_num > expected_phase_num:
        return True, {
            "block": True,
            "reason": "decision_phase_mismatch",
            "blocking_rules": [],
            "expected_phase": expected_phase,
            "actual_phase": decision_phase,
        }
    # decision_phase_num <= expected_phase_num → 순방향 호환, 그대로 사용

    # stale (decision이 더 오래된 summary 기준)
    decision_summary_ts = d.get("generated_from_summary_last_updated", "")
    if decision_summary_ts and summary_last and decision_summary_ts < summary_last:
        return True, {
            "block": True,
            "reason": "decision_stale",
            "blocking_rules": [],
            "summary_last": summary_last,
            "decision_summary_ts": decision_summary_ts,
        }

    return bool(d.get("block")), d
```

`is_execution_open()` 자체는 **변경하지 않는다** (rename 안전, P1 회귀 방지).

### 6.2 project_pipeline.execute() 진입 차단

```python
# 기존
if not gate.is_execution_open():
    return {"ok": False, "reason": "approval_required", ...}

# P2 추가 — execution_open 체크 직후
blocked, decision = gate.read_block_decision()
if blocked:
    return {
        "ok": False,
        "reason": "escalation_block",
        "blocking_rules": decision.get("blocking_rules", []),
        "decision_report": os.path.join(
            prepared.workspace, "runtime", "warnings",
            prepared.work_item_slug, "_decision.md"
        ),
        "message": "escalation 차단. _decision.md 를 확인하고 e2e_command 보강 또는 warning-override 후 재실행하세요.",
    }
```

**왜 `is_execution_open` 안에 합치지 않나**: is_execution_open은 "사용자 승인 마크" 시멘틱. block decision은 "정책 평가 결과" 시멘틱. 분리 → reason 메시지 정확, 두 차단의 해소 방법이 다름 (전자: 승인 마크, 후자: e2e 보강 / override).

---

## §7 e2e_command 생성 — 책임 함수별 분리

### 7.1 phase별 책임 함수 (baseline grep 사실)

`core/project_task_board.py:337-389` `_task_template`은 phase 6개 중 **3개만** 직접 생성한다 (직접 코드 확인). 나머지 phase는 별도 경로:

| phase | 생성 함수 | 호출 경로 |
|-------|----------|----------|
| `scope` | `_task_template` | 항상 (모든 module) |
| `build` | `_task_template` | 항상 (slices 있으면 N개, 없으면 1개) |
| `verify` | `_task_template` | 항상 |
| `integrate` | LLM tasks-generator | `_generate_implementation_tasks` 결과에 포함 시에만 (선택적) |
| `code_review` | `inject_review_tasks` (`core/project_task_board.py:1025-1130`) | build phase task 완료 후 동적 주입 |
| `cross_validate` | `inject_review_tasks` | build 완료 + CLI provider ≥ 2개일 때만 동적 주입 |

따라서 P2 e2e_command 생성 작업은 **두 함수 + LLM prompt + missing 검사** 4지점에 분산.

### 7.2 미인식 결정 — `# TODO:` 마커는 missing으로 카운트

placeholder의 핵심 모순: BLOCK 회피하면 의식 강제 의미 없음, BLOCK 트리거하면 첫 P2 빌드가 막힘. 해소:

> **`# TODO:` 로 시작하는 e2e_command는 빈값과 동등하게 missing으로 인식한다.**

- `core/work_item_generator.py:1050-1054` 의 missing 검사를 `_clean(t.get("e2e_command") or "")` 단일 검사 → `_is_e2e_missing(...)` 헬퍼로 교체:
  ```python
  def _is_e2e_missing(value: str) -> bool:
      v = _clean(value or "")
      if not v:
          return True
      return v.startswith("# TODO") or v.startswith("#TODO")
  ```
- 이렇게 하면 `# TODO:` 마커는 user-readable + grep 가능 + BLOCK 트리거 모두 만족.
- 사용자는 `_decision.md` 안내에 따라 (a) `# TODO:` 자리에 실제 명령 채우기, (b) override, (c) policy 비활성 중 선택.

### 7.3 함수별 e2e_command 생성 (책임별 분리)

#### 7.3.1 `_task_template` (`core/project_task_board.py:337-389`)
| phase | e2e_command 값 | 비고 |
|-------|-------------|------|
| `scope` | (필드 추가하지 않음) | exempt |
| `build` | `f"# TODO: e2e command for {task_id} (build)"` | LLM 또는 사용자 채움 대상 |
| `verify` | `f"# TODO: e2e command for {task_id} (verify)"` | 동일 |

> 비-Python 프로젝트 호환을 위해 `pytest` 같은 도구-특정 명령은 placeholder에 두지 않는다. `# TODO` 마커는 도구-중립.

#### 7.3.2 `inject_review_tasks` (`core/project_task_board.py:1025-1130`)
- code_review/cross_validate task에 `e2e_command="# TODO: e2e command for <task_id> (<phase>)"` 1줄 추가.
- 두 위치: line 1055-1067 cr_task dict, line 1089-1102 cv_task dict.

#### 7.3.3 LLM tasks-prompt 강화 (`core/work_item_generator.py:787-800`)

> **baseline 확인**: line 556 은 `_fallback_impl_tasks()` 함수 내부의 static template이며 LLM에 전달되지 않음. 실제 LLM 프롬프트는 `_generate_implementation_tasks()` 함수 내 `prompt` 문자열 (line 773-800). P2 변경 대상은 line 787 (`## Task List` 포맷 설명) + line 792 (`Rules:` 블록).

```python
# 기존 (line 787)
"(각 태스크: - [ ] 태스크 제목 / task_id: T-001 / owner_role / phase / depends_on / "
"acceptance / artifacts / estimated_complexity / implementation_hint)\n\n"

# P2 변경 — e2e_command 필드 명시 추가
"(각 태스크: - [ ] 태스크 제목 / task_id: T-001 / owner_role / phase / depends_on / "
"acceptance / e2e_command / artifacts / estimated_complexity / implementation_hint)\n\n"
```

```python
# P2 변경 — Rules 블록에 e2e_command 규칙 추가 (line 798 직후)
"- 모든 태스크에 e2e_command 포함: 실제 검증 명령어 (예: `pytest -k T-001 -q`, "
"`bash scripts/smoke.sh`, `node tests/e2e/auth.test.js`). "
"작성 불가 시 `# TODO: <설명>` 으로 명시 (BLOCK 트리거 — 의도된 동작)\n"
```

fallback path (`_fallback_impl_tasks` line 556)는 LLM 실패 시 호출되는 static template. 해당 함수의 `Definition Of Done` 섹션에도 동일하게 e2e_command 가이드 문구 추가 (fallback 산출물도 동일 기준).

#### 7.3.4 missing 검사 보강 (`core/work_item_generator.py:1050-1054`)
- `_is_e2e_missing` 헬퍼 도입 (§7.2)
- 호출처 수정:
  ```python
  missing_e2e = [
      _clean(t.get("task_id") or t.get("id") or "?")
      for t in tasks_list
      if _is_e2e_missing(t.get("e2e_command"))
  ]
  ```
- `_phase_groups` 분기 (line 1063-1071)도 동일하게 `_is_e2e_missing` 사용.

### 7.4 round-trip 보강 — LLM 결과를 task_board로 반영

현재 `_generate_implementation_tasks` (line 758~)은 `implementation-tasks.md` 문서만 생성. task_board의 e2e_command는 별도 source-of-truth.

**P2 변경**: tasks LLM 결과 마크다운을 파싱해 e2e_command를 추출하고 task_board에 backfill. 신규 헬퍼:

```python
# work_item_generator.py
def _backfill_e2e_from_tasks_md(tasks_content: str, task_board: dict) -> dict:
    """implementation-tasks.md의 'e2e_command:' 라인을 추출해 task_board에 반영.
    
    파서 계약:
    - e2e_command 라인 패턴: `^[-*]\\s+e2e_command:\\s+(.+)$` (re.MULTILINE)
    - task_id 매칭: 해당 e2e_command 라인 **직전 최대 5줄**에서 `task_id: T-NNN` 탐색
      → splitlines() 기반 line-window 접근 (regex .*?+DOTALL은 줄 수 제한 불가)
    - 같은 task_id가 여러 번 등장하면 **첫 번째** 매칭만 사용 (중복 무시)
    - task_id 매칭 실패 → 해당 항목 silent skip
    - 추출값이 `# TODO` 로 시작하면 → 기존 마커 그대로 (덮어쓰지 않음)
    - 파싱 전체 실패(예외) → 기존 task_board 반환 (silent skip)
    """
    import re
    _E2E_RE = re.compile(r'^[-*]\s+e2e_command:\s+(.+)$')
    _TID_RE = re.compile(r'^[-*]\s+task_id:\s*(T-\d+)')
    lines = tasks_content.splitlines()
    result = {}  # task_id → e2e_command
    for i, line in enumerate(lines):
        m = _E2E_RE.match(line.strip())
        if not m:
            continue
        e2e_val = m.group(1).strip()
        if e2e_val.startswith("# TODO"):
            continue  # 기존 마커 → 덮어쓰지 않음
        # 직전 최대 5줄에서 task_id 탐색
        task_id = None
        for j in range(max(0, i - 5), i):
            tm = _TID_RE.match(lines[j].strip())
            if tm:
                task_id = tm.group(1)
        if task_id and task_id not in result:
            result[task_id] = e2e_val  # 첫 번째 매칭만 사용
    # task_board tasks에 반영
    ...
```

호출 위치: `tasks_content = tasks_result.content` 직후, `write_initial_record` 직전.

**정량 acceptance**: `tests/test_work_item_generator_backfill.py` — mock markdown 8개 (정상 매칭, task_id 없음, TODO 마커, 중복 task_id, 예외, 필드 없음, 순서 역전, 다중 phase) 중 **≥7개 정확히 파싱** (pass 기준).

→ **scope 보호**: round-trip은 **best-effort**. 파싱 실패 시 silent skip → 기존 동작 유지. 정확한 매칭이 안 되면 `e2e_command_missing` record가 그대로 발생 → BLOCK 또는 override 흐름.

---

## §8 warning-override CLI

### 8.1 사용법

```bash
af warning-override \
  --workspace . \
  --slug minesweeper-smoke-v2-01 \
  --rule e2e_command_missing \
  --reason "프로토타입 단계 — e2e 보강 후속 PR에서 처리"
```

### 8.2 동작

1. `<workspace>/runtime/warnings/<slug>/_overrides.json` 에 entry append:
```json
{
  "schema_version": 1,
  "overrides": [
    {
      "rule_id": "e2e_command_missing",
      "reason": "프로토타입 단계 — e2e 보강 후속 PR에서 처리",
      "ts": "2026-05-09T16:30:00+09:00",
      "scope": "rule"
    }
  ]
}
```
2. `WarningRegistry.summarize()` 가 `_overrides.json`을 읽어, 해당 `rule_id`의 모든 record를 `false_positive_override=true`로 처리 (record 자체는 수정하지 않고, summary 산출 시 `any_override: true` 필드만 세팅).
3. `compute_run_decision` 의 `evaluate(virtual)` 가 override를 보고 `block=False, reason="false_positive_override"` 반환.

### 8.3 record 비파괴

기존 jsonl record는 **수정하지 않는다**. override는 별도 파일. `_overrides.json` 삭제하면 즉시 BLOCK 복귀. v6 §3.3의 "record는 append-only" 정책 유지.

### 8.4 scope 단순화 (P2)

현재는 `scope: "rule"` (rule 전체 override) 만 지원. P4에서 `scope: "record"` (record_id 별), `scope: "phase"` (phase 별) 확장.

### 8.5 CLI subcommand wiring — dispatch dict 패턴 일치

기존 `warning-summary`/`warning-repair`는 `run_factory_cli.py:403` 의 **`_STAGE1_DISPATCH`** dict + `:447` 의 **`_STAGE1_USAGE`** dict 패턴을 사용 (baseline 직접 확인 — 변수명 정확히 이대로). `warning-override`도 같은 두 dict에 등록:

```python
def _run_warning_override_subcommand(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="af warning-override")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--rule", required=True)
    parser.add_argument("--reason", default="")
    parser.add_argument("--remove", action="store_true",
                        help="override 제거 (재차단)")
    args = parser.parse_args(argv)

    from core.warning_overrides import upsert_override, remove_override
    if args.remove:
        remove_override(args.workspace, args.slug, args.rule)
        print(f"[warning-override] removed slug={args.slug} rule={args.rule}")
    else:
        if not args.reason.strip():
            parser.error("--reason 은 override 추가 시 필수")
        upsert_override(args.workspace, args.slug, args.rule, args.reason)
        print(f"[warning-override] added slug={args.slug} rule={args.rule}")

    # summary 재계산 → decision report 갱신
    from core.warning_registry import WarningRegistry
    WarningRegistry(workspace=args.workspace).summarize(project_slug=args.slug)
    return 0
```

dispatch dict 등록 (`run_factory_cli.py:403` `_STAGE1_DISPATCH`):
```python
_STAGE1_DISPATCH: dict[str, "callable[[list[str]], None]"] = {
    ...
    "warning-summary":  _run_warning_summary_subcommand,
    "warning-repair":   _run_warning_repair_subcommand,
    "warning-override": _run_warning_override_subcommand,   # ★ P2
    ...
}
```

help string (`run_factory_cli.py:447` `_STAGE1_USAGE`):
```python
_STAGE1_USAGE = {
    ...
    "warning-summary": "usage: af warning-summary --workspace PATH --slug SLUG    # WARN 요약 출력",
    "warning-repair":  "usage: af warning-repair --workspace PATH --slug SLUG    # _summary.json 재생성",
    "warning-override": "usage: af warning-override --workspace PATH --slug SLUG --rule RULE --reason TEXT [--remove]   # ★ P2 false-positive override",
}
```

### 8.6 신규 모듈 `core/warning_overrides.py`

```python
def overrides_path(workspace: str, slug: str) -> str: ...
def load_overrides(workspace: str, slug: str) -> dict: ...

def upsert_override(workspace: str, slug: str, rule_id: str, reason: str) -> None:
    """override 추가 또는 갱신 — locked_file + atomic replace."""
    path = overrides_path(workspace, slug)
    lock_path = path + ".lock"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked_file(lock_path, timeout=10):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            data = {"schema_version": 1, "overrides": []}
        # 동일 rule_id 중복 제거 후 upsert
        data["overrides"] = [e for e in data.get("overrides", []) if e.get("rule_id") != rule_id]
        data["overrides"].append({
            "rule_id": rule_id, "reason": reason,
            "ts": now_iso(), "scope": "rule",
        })
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception:
            try: os.unlink(tmp)
            except OSError: pass
            raise

def remove_override(workspace: str, slug: str, rule_id: str) -> None:
    """override 제거 — locked_file + atomic replace."""
    # upsert 와 동일 lock 패턴. entries 필터링 후 atomic write.
    ...

def is_overridden(overrides: dict, rule_id: str) -> bool: ...
```

`_build_summary` 가 `load_overrides()` 로 읽고 `any_override` 필드 세팅. **락은 `locked_file(overrides_path + ".lock")`** — `_summary.json.lock`과는 별개 락 (deadlock 없음: 두 락을 동시에 잡는 경로 없음).

---

## §9 Acceptance — 28 케이스

### 9.1 evaluator (6)
1. `evaluate(record with rule_id="never_rule")` → `block=False, reason="rule_not_active"`
2. `evaluate(record with activate_at="P4")` → `block=False, reason="inactive_phase"` (current=P2)
3. `evaluate(e2e_command_missing record, phase="scope")` → `block=False, reason="exempt_phase:scope"`
4. `evaluate(e2e_command_missing record, phase="build", count=1)` → `block=True, reason="threshold_met"`
5. `evaluate(e2e_command_missing record, phase="build", count=0)` → `block=False, reason="below_threshold"`
6. `evaluate(record with false_positive_override=True)` → `block=False, reason="false_positive_override"`

### 9.2 compute_run_decision + load_policy (3)
7. summary에 active rule 0개 → `RunDecision(block=False, blocking_rules=[])`
8. summary에 build phase 14건 + scope 3건 → `block=True, blocking_rules=["e2e_command_missing"]`, rule_decisions에 build/scope 두 분기 모두 존재
9. summary `any_override=true` → `block=False, reason="no_active_blocks_in_run"`

### 9.3 _build_summary schema 회귀 (1)
10. `_build_summary` 산출 dict 의 entry 필드 = `{count, first_ts, last_ts, severity, by_phase, repeat_count_max, any_override}`. **`repeat_count_max` + `any_override` 누락 회귀 차단**

### 9.4 decision report writer (3)
11. `write_decision_report(decision, slug_dir, summary_last_updated="...")` → `_decision.md` + `_decision.json` atomic 작성
12. `_decision.json`에 `decision_schema_version=1` + `generated_from_summary_last_updated` + `escalation_phase` 3개 키 모두 존재
13. `write_error_decision(...)` → `_decision.json.block=true, reason="evaluator_error"` 강제 작성

### 9.5 ApprovalGate.read_block_decision (5)
14. `_summary.json` 부재 → `(False, None)` (P1 호환)
15. `_summary.json` 존재 + `escalation_phase` 마커 없음 → `(False, None)` (P1 산출)
16. `_summary.json.escalation_phase="P2"` + `_decision.json` 부재 → `(True, {"reason": "decision_missing"})` (fail-closed)
17. `_decision.json.escalation_phase` 가 summary와 다름 → `(True, {"reason": "decision_phase_mismatch"})` (fail-closed)
18. `_decision.json.generated_from_summary_last_updated` 가 summary.last_updated보다 오래됨 → `(True, {"reason": "decision_stale"})` (fail-closed)

### 9.6 pipeline.execute (2)
19. (단위/mock) prepared.gate() 가 `read_block_decision=(True, {"blocking_rules": ["e2e_command_missing"]})` 반환 → execute() 가 `{"ok": False, "reason": "escalation_block", "blocking_rules": [...], "decision_report": ...}` 반환
20. (통합 smoke — **hermetic**) LLM provider 호출은 stub (record 직접 jsonl seed). `tmp_path` workspace에 `runtime/warnings/<slug>/e2e_command_missing.jsonl` 1줄 작성 → `WarningRegistry.summarize()` 호출 → ApprovalGate.read_block_decision() → pipeline.execute() (work_item_generator 우회 또는 fake `prepared` 객체) 가 escalation_block 반환. CI provider 키 불필요

### 9.7 _task_template / inject_review_tasks 회귀 (3)
21. `_task_template("alice", "auth", "summary")` 의 `build` phase task → `e2e_command.startswith("# TODO:")` (build/verify 동일)
22. `_task_template` 의 `scope` phase task → `e2e_command` 필드 부재 (또는 빈문자열)
23. `inject_review_tasks` 가 build 완료 시 주입한 code_review/cross_validate task → `e2e_command.startswith("# TODO:")`

### 9.8 missing 검사 보강 (1)
※ 9.6 통합 smoke와 결합 — `_is_e2e_missing("# TODO: ...") == True` 단위 1건 + record 생성 시 `# TODO:` 도 missing으로 카운트되는지 검증.

### 9.9 warning-override CLI (2)
24. `af warning-override --rule e2e_command_missing --reason "..."` → `_overrides.json` 생성, summary `any_override=true`, decision `block=False`
25. `af warning-override --remove --rule e2e_command_missing` → override 제거, summary `any_override=false`, decision `block=True` 복귀

### 9.10 summarize() trigger wiring (1)
26. `work_item_generator.generate_work_items(...)` 호출 시 — record loop 이후 `_summary.json`과 `_decision.json` 파일이 `runtime/warnings/<slug>/` 에 생성됨. LLM provider 없이 hermetic 테스트 (직접 jsonl seed + fake gate + tmp_path workspace).

### 9.11 phase forward-compat (1)
27. `read_block_decision()` — `_decision.json.escalation_phase="P2"`, `_summary.json.escalation_phase="P3"` → decision_phase_num(2) ≤ expected_phase_num(3) → `(bool(d["block"]), d)` 반환 (fail-closed 아님).

### 9.12 frozen build smoke (1)
28. `dist/af/af.exe warning-summary --workspace=. --slug=test` 실행 → ImportError 없이 정상 종료. CI 단위: PyInstaller build 결과물 존재 시 실행 (없으면 SKIP marker).

---

## §10 PR file list (체크리스트)

- [ ] `core/escalation_evaluator.py` — body 재작성 + `load_policy()` public + `compute_run_decision` + `RunDecision` (+130)
- [ ] `core/escalation_decision_report.py` — 신규: `write_decision_report` + `write_error_decision` (md+json, decision_schema_version, generated_from_summary_last_updated, escalation_phase) (+95)
- [ ] `core/warning_overrides.py` — 신규: load/upsert/remove/is_overridden (+50)
- [ ] `core/warning_registry.py` —
  - `summarize()` 끝에서 decision 트리거, **try/except → fail-closed (`write_error_decision`)**
  - `_summary.json`에 `escalation_phase: "P2"` 마커 도입
  - `_build_summary` 가 **`any_override` + `repeat_count_max` 두 필드 추가**
  - (+50)
- [ ] `core/approval_gate.py` —
  - top-level `import json` 추가 (현재 imports = `hashlib`, `os`, `re`, `Any` — `json` 부재. `read_block_decision`이 `json.load` + `json.JSONDecodeError` 사용)
  - `read_block_decision()` fail-closed 분기 (decision_missing / parse_error / phase_mismatch / stale)
  - (+52)
- [ ] `core/project_pipeline.py:1268-` — execute() block 체크 추가 (+20)
- [ ] `core/project_task_board.py:337-389` `_task_template` — scope(필드 추가 안함) / build / verify task에 `# TODO:` 마커 추가 (+18)
- [ ] `core/project_task_board.py:1025-1130` `inject_review_tasks` — code_review / cross_validate task에 `# TODO:` 마커 추가 (+6)
- [ ] `core/work_item_generator.py:787-800` — LLM prompt 강화 (Task List 포맷에 `e2e_command` 필드 추가 + Rules 블록 규칙 추가) (+10)
- [ ] `core/work_item_generator.py:511-558` `_fallback_impl_tasks` — Definition Of Done 섹션에 e2e_command 가이드 추가 (+2)
- [ ] `core/work_item_generator.py:1050-1086` — `_is_e2e_missing` 헬퍼 도입 + missing 검사 / phase_groups 분기 모두 헬퍼 사용 (+6)
- [ ] `core/work_item_generator.py:1085-1087` — record loop 직후 `summarize()` 호출 추가 (try/except 포함) (+8)
- [ ] `core/work_item_generator.py` — `_backfill_e2e_from_tasks_md` 신규 + tasks 생성 직후 호출 (+35)
- [ ] `run_factory_cli.py` — `_run_warning_override_subcommand` + `_STAGE1_DISPATCH`/`_STAGE1_USAGE` 등록 (+70)
- [ ] `runtime/warnings/_index.json` — 메타 메모만 (activate_at 값 자체는 P1에 이미 P2)
- [ ] `af.spec` hiddenimports — `core.escalation_decision_report`, `core.warning_overrides` 추가 (line 33-)
- [ ] `af.spec` datas — `('config', 'config')` 이미 있음 (P1). `escalation_policy.yaml` 번들 확인용 smoke 테스트(§9 #28)만 추가
- [ ] `version.py`/`install-af.ps1` — P2 PR에서 patch 버전 bump (1.2.25 → 1.2.26 또는 구현 완료 시 결정)
- [ ] `tests/test_escalation_evaluator.py` — 9 케이스
- [ ] `tests/test_decision_report.py` — 3 케이스 (writer + stale 키 + error_decision)
- [ ] `tests/test_pipeline_block_enforcement.py` — 2 케이스 (단위 mock + 통합 smoke 분리)
- [ ] `tests/test_approval_gate_block_decision.py` — 6 케이스 (fail-open 2 + fail-closed 3 + phase forward-compat 1)
- [ ] `tests/test_warning_override_cli.py` — 2 케이스 (add/remove + dispatch wiring)
- [ ] `tests/test_task_template_e2e_command.py` — 2 케이스 (_task_template 회귀)
- [ ] `tests/test_inject_review_tasks_e2e_command.py` — 1 케이스 (inject_review_tasks 회귀)
- [ ] `tests/test_summary_schema_repeat_count.py` — 1 케이스 (`_build_summary` schema 회귀: count/first_ts/last_ts/severity/by_phase/**repeat_count_max**/**any_override**)
- [ ] `tests/test_work_item_generator_backfill.py` — 1 케이스 (backfill parser ≥7/8 mock markdowns)
- [ ] `tests/test_wig_summarize_wiring.py` — 1 케이스 (§9 #26: generate_work_items → _summary.json + _decision.json 생성 확인)
- [ ] `Master_Blueprint.md` §3 escalation_evaluator/decision_report/warning_overrides 섹션 + §12 변경 이력 (v1.2.25 또는 다음 버전)
- [ ] `NEXT_STEPS.md` 갱신

---

## §11 Risk & Rollback

### 11.1 위험

| 위험 | 영향 | 완화 |
|------|------|------|
| `summarize()` 끝 decision 호출이 예외 → silent skip | BLOCK 무력화 | **fail-closed**: try/except에서 `write_error_decision()` 강제 호출 → `_decision.json.block=true, reason="evaluator_error"` 작성 |
| `_decision.json` 부재 시 pipeline 통과 | BLOCK 무력화 | **`escalation_phase` 마커**: summary에 마커 있으면 fail-closed (decision 누락 = 차단), 없으면 P1 호환 fail-open |
| `_task_template` 의 `# TODO` 마커 → BLOCK | 첫 P2 실행이 항상 차단됨 | **의도된 동작** (§0.1 명시). `_decision.md` 안내 + `warning-override` 우회 경로 제공 |
| `# TODO` 마커가 BLOCK을 회피해 의식 강제 무력화 | 사용자가 무관심하게 통과 | `_is_e2e_missing` 이 `# TODO` 도 missing으로 카운트 → BLOCK 트리거 유지 |
| `_overrides.json` 손상 → JSONDecodeError | summarize 실패 | try/except → silent fallback to `{"overrides": []}` + warning |
| round-trip parser가 `# TODO:` 잘못 파싱 | task_board 오염 | parser는 conservative — `^[-*]\s+e2e_command:\s+(.+)$` 정확 매칭. 매칭 실패 시 기존값 유지 |
| stale `_decision.json` → 오래된 결정으로 silently 차단/통과 | 잘못된 BLOCK 또는 false-pass | `generated_from_summary_last_updated` < `summary.last_updated` 인 경우 fail-closed |
| P2→P3 업그레이드 시 기존 `_decision.json` (`escalation_phase: P2`) → 일제 BLOCK | 전 프로젝트 동시 차단 | **순방향 호환**: `decision_phase_num ≤ expected_phase_num` 이면 기존 decision 그대로 사용 (§6.1). 새 phase에서 summarize() 재호출 시 decision이 자연스럽게 갱신됨. |
| `_overrides.json` write race (CLI + summarize 동시) | 파일 손상 | `locked_file(overrides_path + ".lock")` — read-modify-write + `os.replace` (§8.6) |

### 11.2 Rollback (개별)

- **decision wiring 문제 시 (atomic 절차 — 반드시 이 순서)**:
  1. **emergency switch 우선**: `AF_SKIP_ESCALATION=1` 환경변수로 `read_block_decision`이 즉시 `(False, None)` 반환하도록 우회 (단발 사고 시 가장 빠름). 영구 rollback이 필요할 때만 아래 단계로.
  2. `summarize()` 의 decision 호출 블록 주석 처리
  3. **락 획득 후 한 트랜잭션으로**:
     - `core/file_lock.locked_file(<workspace>/runtime/warnings/<slug>/_summary.json.lock)` 안에서:
       - summary read → `escalation_phase` 키 제거 → `tempfile.mkstemp + os.replace` 로 atomic write (P1 패턴 차용)
       - 그 다음 `_decision.json` 삭제 (또는 `block: false, reason: "rolled_back"` 로 덮어쓰기)
       - 락 해제
     - 이렇게 하면 다른 프로세스가 마커 vs decision 부재 사이의 spurious BLOCK 윈도우에 들어가지 않음
  4. **검증**: `af warning-summary --workspace . --slug <slug>` 실행 후 `_decision.json` 미생성 + `read_block_decision` 가 `(False, None)` 반환하는지 단위 확인
- **`_task_template` 회귀 시**: e2e_command 추가 라인 (build/verify 각 1줄) revert + `inject_review_tasks` 의 cr_task/cv_task dict의 e2e_command 라인 revert
- **`_is_e2e_missing` 헬퍼 회귀 시**: `core/work_item_generator.py:1050-1054` 의 검사 로직을 P1 형태(`if not _clean(...)`)로 revert
- **`warning-override` CLI 버그**: dispatch dict 의 `"warning-override":` 항목 + `_run_warning_override_subcommand` 함수 + help string 1줄 revert
- **fail-closed 마커 회귀 시**: summary의 `escalation_phase` 추가 1줄 revert + read_block_decision 의 P1 호환 분기는 그대로 동작
- **emergency env var**: `AF_SKIP_ESCALATION=1` — `read_block_decision()` 진입 즉시 `(False, None)` 반환 (P1 호환 동등). 단발 incident 시 사용. CLAUDE.md 의 `AF_SKIP_REVIEW_GATE` 패턴 차용 (hook subprocess 격리 이슈는 동일하게 inline env 권장)

---

## §12 baseline grep table (구현 진입 시 1차 검증)

| 파일:줄 | 역할 | P2 변경 |
|---------|------|---------|
| `core/project_task_board.py:17` `_PHASE_ORDER` | phase enum 6개 | (참조만) |
| `core/project_task_board.py:337-389` `_task_template` | scope/build/verify task 생성 (3 phase만) | **build/verify** phase에 `e2e_command="# TODO: ..."` 마커 추가. scope는 필드 부재 (정책 exempt) |
| `core/project_task_board.py:1025-1130` `inject_review_tasks` | build 완료 시 code_review/cross_validate 동적 주입 | 두 task dict에 `e2e_command="# TODO: ..."` 마커 추가 (line 1055-1067 cr_task, line 1089-1102 cv_task) |
| `core/project_task_board.py:497` `_normalize_tasks` | e2e_command normalize | (변경 없음) |
| `core/work_item_generator.py:787-800` LLM prompt | `_generate_implementation_tasks()` tasks 포맷 + Rules 블록 | **e2e_command 필드 추가 + 규칙 추가** (line 556은 `_fallback_impl_tasks` 내부 — 별도 추가) |
| `core/work_item_generator.py:1037-1046` | tasks 생성 후 텔레메트리 | round-trip backfill 호출 위치 |
| `core/work_item_generator.py:1048-1086` | e2e_command_missing record | record 호출 인자(`affected_ids`/`source_path` 등) 그대로 / **missing predicate `_clean(...) or ""`를 `_is_e2e_missing(...)` 헬퍼로 교체** (line 1053 검사 + line 1063-1071 `_phase_groups` 분기 모두) |
| `core/warning_registry.py:166-188` `summarize` | _summary 작성 | 끝에서 decision 작성 호출 (trigger는 work_item_generator에서 호출, summarize 자체가 decision report 작성) |
| `core/warning_registry.py:220-272` `_build_summary` | rule 집계 (현재 entry = `count/first_ts/last_ts/severity/by_phase`) | **`any_override` + `repeat_count_max` 두 필드 추가** (P4 `repeat_count_min` 정책 발화 사전 준비) |
| `core/escalation_evaluator.py:62-70` `evaluate` | stub | body 재작성 |
| `core/approval_gate.py:13-21` imports | `hashlib/os/re/Any` 만 (json 부재) | **top-level `import json` 추가** |
| `core/approval_gate.py:351-353` decision_report line | path 렌더 | (변경 없음) |
| `core/approval_gate.py` `is_execution_open` | 승인 체크 | (변경 없음) — 별도 read_block_decision 추가 |
| `run_factory_cli.py:403` `_STAGE1_DISPATCH` | subcommand → handler dict | `"warning-override": _run_warning_override_subcommand` 추가 |
| `run_factory_cli.py:447` `_STAGE1_USAGE` | subcommand → help string dict | `"warning-override": "..."` 추가 |
| `core/project_pipeline.py:1268-1275` execute() 진입 | 승인 체크 | 직후 block 체크 추가 |
| `run_factory_cli.py` warning subcommands | summary/repair | override 추가 |
| `tests/e2e` | (확인 필요) | 회귀 영향 |
| `af.spec` hiddenimports | frozen build 모듈 | 신규 2개 등록 |

---

## §13 후속 (P3 이후)

- **P3** (P2 데이터 측정): doc_consistency_drift record 도입, 글로벌 통계 활성, false_positive 수집·분석
- **P4** (escalation v1):
  - owner_role_mismatch / evidence_quality_warn BLOCK 활성 (`repeat_count_min: 3` 정책 발화 — `repeat_count_max` 필드를 P2에서 미리 산출해 P4에서 정책 매칭에 사용)
  - override를 record/phase 단위로 확장 (`scope: "record"` / `scope: "phase"`) → `_overrides.json.schema_version=2`
  - `evaluate(record)` / `evaluate_aggregate(rule_id, phase, count, repeat_count, override)` 분리 (P2 §4.4b advisory 적용)
- **P5**: doc_consistency_meter 신설
- **P6**: 글로벌 ledger / 멀티-PC sync 정책

---

## §14 Open questions (v2 — cross-review 후 정리됨)

| # | 질문 | 처리 |
|---|------|------|
| 1 | `summarize()` 끝의 decision 작성을 락 안에서 해도 되나? | **확정**: 락 안 OK. yaml load는 락 안에서 1회 (작업 기간 짧음). 큰 부담은 아님. |
| 2 | `_task_template` build placeholder를 `pytest -k` 로 가정하는 게 적절한가? | **변경**: `# TODO:` 마커로 변경 (§7.2). BLOCK 트리거 유지 + 도구 중립. |
| 3 | `_overrides.json`의 schema versioning | P4에서 `schema_version: 2` 로 자연 진화. v1 entry는 `scope: "rule"` 으로 implicit. |
| 4 | virtual record 패턴이 P3/P4 글로벌 분석과 정합? | **P2는 안전, P4 진입 시 dataclass 분리** (§4.4b advisory). |
| 5 | `current_phase="P2"`를 어디서 source 할지 | P2 PR에선 상수. P3 진입 시 env var (`AF_ESCALATION_PHASE`) 또는 `version.py` 메타에서 읽도록 결정. |
| 6 | acceptance #19/#20 (pipeline.execute) — mock vs 통합 분리 | **분리됨**: 9.6 #19 단위 mock, #20 통합 smoke. |
| 7 | fail-open vs fail-closed 정책 | **fail-closed**: `escalation_phase` 마커 + stale 검출 키. P1 호환은 마커 부재로만 분기 (§6.1) |

---

## §15 변경 이력

- **v4.1 (2026-05-10)** — v4 cross-review WARN advisory 1건 흡수
  - §7.4 backfill regex — `re.DOTALL + .*?` 대신 `splitlines()` + 5-line window 접근으로 교체. "최대 5줄" 계약을 pseudo-code에서 정확히 구현
- **v4 (2026-05-10)** — v3.1 cross-review BLOCK 10건 수용
  - §0.1 — "첫 실행 미차단" 모순 해소: Policy B 채택. `# TODO:` BLOCK은 의도된 동작으로 명시
  - §3.1 — summarize() 트리거 위치를 `work_item_generator.py` (record loop 직후) 로 명시. `ApprovalGate.initialize()`는 변경 없음
  - §5.4 — 트리거 코드 스니펫 추가 (work_item_generator에서 summarize 호출)
  - §6.1 — phase 순방향 호환 규칙 추가 (`decision_phase_num ≤ expected_phase_num` → pass)
  - §7.3.3 — LLM prompt 타겟 교정: fallback line 556 → 실 prompt lines 787-800 + fallback 추가 분리
  - §7.4 — backfill parser 계약 명시: regex / task_id 탐색 / 중복 처리 / 정량 acceptance (≥7/8)
  - §8.6 — `locked_file(overrides_path + ".lock")` + atomic replace spec 추가
  - §9 — 케이스 25 → 28 (summarize wiring #26, phase forward-compat #27, frozen smoke #28)
  - §10 — work_item_generator 변경 라인 교정 + summarize 호출 추가 + af.spec datas 이미 있음 확인 + version bump 항목 추가 + 테스트 파일 2개 추가
  - §11.1 — phase 업그레이드 위험 + override race 위험 추가
  - §12 — work_item_generator:556 → 787-800 교정 + summarize trigger 주석 추가
- **v3 (2026-05-09 KST 18:30)** — v2 cross-review BLOCK 2건 + advisory 5건 + bonus 1건 수용
  - §0 이력 갱신
  - §3.2 — `_task_template` 변경 phase를 "build/verify는 `# TODO:`, scope는 필드 부재"로 통일. `core/approval_gate.py` 행에 `import json` 추가 명시
  - §5.4 — fail-closed import를 `try` 블록 안으로 이동. `_write_minimal_block_decision` 최종 fallback 추가 (escalation_decision_report 자체가 import 실패해도 `_decision.json` 작성)
  - §6.1 — `AF_SKIP_ESCALATION=1` emergency env 분기 추가 (rollback 시 사용)
  - §8.5 — dispatch dict 변수명을 baseline `_STAGE1_DISPATCH` (`run_factory_cli.py:403`) / `_STAGE1_USAGE` (line 447)로 정정
  - §9 — 제목 "23 케이스" → "25 케이스" 정정. #20 hermetic 명시 (LLM stub + jsonl seed + tmp_path workspace)
  - §10 — `core/approval_gate.py` 행에 `import json` 추가 명시
  - §11.2 — emergency env switch 우선 + 락 안 atomic 절차 + 검증 단계 추가
  - §12 — baseline grep table 의 `_task_template` 변경 표기 통일. `inject_review_tasks` / `approval_gate.py imports` / `_STAGE1_DISPATCH` / `_STAGE1_USAGE` 행 추가
- **v2 (2026-05-09 KST 17:30)** — Tier 3 cross-review BLOCK 5건 + advisory 4건 수용
  - §0 이력 섹션 신설
  - §3.2 모듈 표: `_task_template` LOC 재산정, `inject_review_tasks` 행 추가, `_build_summary` repeat_count_max 명시
  - §4.4a `load_policy()` public 신설
  - §4.4b virtual record 패턴 P4 분리 advisory 추가
  - §5.2 `_decision.json` schema에 `decision_schema_version` / `generated_from_summary_last_updated` / `escalation_phase` 3 키 추가
  - §5.4 fail-closed (try/except → write_error_decision) + escalation_phase 마커
  - §6.1 read_block_decision fail-closed 분기 (decision_missing / parse_error / phase_mismatch / stale)
  - §7 두 표로 분리: `_task_template` (scope/build/verify) + `inject_review_tasks` (code_review/cross_validate). placeholder를 `# TODO:` 마커로. `_is_e2e_missing` 헬퍼 도입
  - §8.5 dispatch dict 패턴 일치
  - §9 acceptance 18 → 25 케이스 (schema 회귀, fail-closed 5분기, 단위/통합 분리, inject_review_tasks 회귀 추가)
  - §10 PR file list — `repeat_count_max`, `inject_review_tasks` 별행, fail-closed 명시
  - §11.1 위험 표 — fail-closed 정책 명시
  - §11.2 rollback — stale `_decision.json` 처리 + escalation_phase 마커 처리 추가
  - §13 P4 dataclass 분리 + repeat_count_max 사용 명시
- **v1 (2026-05-09 KST 16:30)** — 초안

---

**상태**: v4.1 — Tier 3 cross-review **WARN (BLOCK 0건, Advisory Medium 1건 흡수)**. P2 단일 PR 구현 진입 가능. Sonnet으로 모델 전환 후 §10 PR file list 순서대로 작업 (CLAUDE.md "단계별 모델 선호" — 코드 구현은 Sonnet).
