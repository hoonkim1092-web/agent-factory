# Design Review: 2026-05-10-p4a-owner-lint-activation-mechanics-design

> Source: docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md
> Date: 2026-05-10 21:06
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

여러 High/Medium 결함이 있으나 P4a 본질(BLOCK 발화 0건 + observation 데이터 신뢰성)을 직접 깨지는 않음. 단 #1, #2, #3, #4는 구현 진입 전 반드시 설계 보강 필요.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [High] `mode=observation` 분기 위치가 `false_positive_override` 앞 — 오버라이드된 record가 block_candidate에 오염
- **Critic**: §5.3 채택안 코드의 mode 분기가 false_positive_override보다 위. 운영자가 명시적으로 false-positive 표시한 record가 임계 평가에 포함되어 block_candidate 보고됨. P4b 임계 결정 데이터 자체가 훼손.
- **Cross**: `any_override`가 모든 virtual record에 전달되는데 observation이 먼저 return하면 overridden noisy rule도 block_candidate로 노출. `warning-override`가 P4a 동안 무력화됨. 증거: `core/warning_registry.py:310`, `core/escalation_evaluator.py:122,183`.
- **Judgment**: 양쪽 동의 + 코드 인용 정확. 데이터 오염 + 운영자 신뢰 동시 훼손.
- **Action Required**: §5에 분기 순서 명시 — `rule_not_active → inactive_phase → false_positive_override → mode 분기 → exempt_when → block_when`. §10 시맨틱 결정에 "false_positive_override는 mode 무관 즉시 warn — 데이터 오염 차단" 추가. §8에 "overridden record는 observation에서 block_candidate 발화 안 함" assertion.

#### 2. [ACCEPT] [High] `write_error_decision`의 markdown 본문도 `"P2"` 하드코딩 별도 존재 — 변경 범위 누락
- **Critic**: §7 표 #4 변경 범위가 `core/escalation_decision_report.py:28-50`에 그치면 line 57 `"- activate_phase: P2"` 잔존. evaluator 오류 시 `_decision.json`은 P4, `_decision.md`는 P2로 보고서 자체가 모순.
- **Cross**: not flagged (오히려 Cross #6에서 minimal writer는 무방하다 판단 — 다른 위치)
- **Judgment**: grep 검증 완료(`escalation_decision_report.py:57`). approval_gate가 json만 읽으니 차단 회귀는 아니지만 사용자 보고서 정합성/감사 추적 깨짐.
- **Action Required**: §7 #4 범위를 `escalation_decision_report.py:28-68`로 확장. line 43·57 둘 다 `current_phase` kwarg로 치환. §9 baseline grep에 `grep -n 'activate_phase: P2' core/escalation_decision_report.py = 2줄` 추가.

#### 3. [ACCEPT] [High] `_decision.md` block_candidate 사용자 가시화 약속 미구현
- **Critic**: §0.1이 약속한 "`_decision.md`에 block_candidate (관측 중) 보고"가 §5 코드 변경 범위 밖. `_write_decision_md`의 "차단 근거" 섹션은 `if decision.block` 분기 안이라 observation 모드에서 통째 누락. 평가된 모든 규칙 표 한 줄로만 노출.
- **Cross**: 동일 — `core/escalation_decision_report.py:129,177` 인용. severity/reason 원시값만 렌더링되며 "관측 중" 라벨 없음.
- **Judgment**: 양쪽 동일 결함 동일 코드 인용. §0.1 약속과 §5 사이 간극이 명백.
- **Action Required**: §5에 `_write_decision_md` 변경 추가 — `decision.rule_decisions` 중 `severity == "block_candidate"`이면 별도 "## 관측 중 (Observation)" 섹션 출력, "현재 BLOCK 미발화. enforce 전환 시 차단 예정" 안내 + yaml `mode` 노출. §8 테스트에 `_decision.md` 본문 assertion 추가.

#### 4. [ACCEPT] [High] `rule_decisions` 스키마가 P4b가 사용해야 할 컨텍스트(affected_phase / count / repeat_count / threshold)를 보존하지 않음
- **Critic**: "Missing from Design"에 동일 지적 — `_decision.json` rule_decisions schema(`{rule_id, block, severity, reason, activate_at}`)에 phase 미포함. P4b가 affected_phase 별 데이터 분리 결정 불가.
- **Cross**: `core/escalation_decision_report.py:81` JSON 직렬화에서 누락. `core/escalation_evaluator.py:175`엔 데이터 있으나 `EscalationDecision`이 carry 못함. P4a가 약속한 "rule_decisions만 봐도 임계 도달 추적 가능"이 무효.
- **Judgment**: 양쪽 동의 + 코드 인용 정확. P4b 인계 데이터 자체가 빈약 → P4a 가치 훼손.
- **Action Required**: `EscalationDecision`에 optional `affected_phase`, `count`, `repeat_count`, `threshold`, `mode` 추가하고 직렬화. §8에 `_decision.json.rule_decisions[]`이 observation_threshold_met 재구성에 충분한지 assertion.

#### 5. [ACCEPT] [Medium] `summarize()` 내 `load_policy()` 2회 호출 — phase drift 위험
- **Critic**: §6 흐름도 line 349, 351에서 yaml file I/O 중복. 동시성 + 빈번한 summarize 시 disk I/O 중복.
- **Cross**: 더 강하게 — yaml이 두 호출 사이에 변경되면 `_summary.json.escalation_phase`와 `_decision.json.escalation_phase`가 갈라져 fail-closed 발화 가능. `core/approval_gate.py:225` 인용.
- **Judgment**: Cross의 phase drift 시나리오가 더 무거움 (성능 아닌 정합성). 두 평가 합치면 Medium.
- **Action Required**: §5.4 또는 §6에 명시 — `policy = load_policy(); current_phase = read_current_phase(policy); summary["escalation_phase"] = current_phase; decision = compute_run_decision(summary, policy, current_phase=current_phase)`. 단일 호출 보장 테스트 추가(monkeypatch로 2회 호출 시 fail).

#### 6. [ACCEPT] [Medium] `core/warning_registry.py` import 추가 시 순환 import 위험
- **Critic**: not flagged
- **Cross**: `escalation_evaluator.py:13`이 이미 `WarningRecord`를 import. `read_current_phase`/`load_policy`/`compute_run_decision`을 module-level로 추가하면 cycle. 현재는 `summarize()` 내 lazy import (`warning_registry.py:207`).
- **Judgment**: 코드 인용 정확. §7 "import 추가" 표현이 모호 → 구현자가 module-level import할 위험 실재.
- **Action Required**: §7에 명시 — "`read_current_phase`, `load_policy`, `compute_run_decision`은 `summarize()` 내 lazy import 유지. module-level 이동 금지(순환 import)".

#### 7. [ACCEPT] [Medium] `_index.json` mode와 yaml mode의 이중 진실원 — 동기화 강제 부재
- **Critic**: P4b가 yaml만 toggle하고 `_index.json`을 잊으면 두 파일 의미 분기. 외부 운영자가 `_index.json`만 보고 오판 가능.
- **Cross**: not flagged
- **Judgment**: §3.2 채택 근거가 "두 파일이 같은 단어 = 인지 부담 0"인데 동기화 메커니즘이 없으면 그 전제가 무너짐. 증거 강함(grep 결과 `_index.json.mode`는 코드 consumer 0).
- **Action Required**: 옵션 (a) `_index.json.mode`를 P4a에서 제거(단일 진실원=yaml) 권장, 또는 (b) `tests/test_warning_index_integrity.py`로 yaml current_phase rule들의 mode == _index.json mode assert. Master_Blueprint §3.7에 "yaml이 진실원, _index.json은 사람용 메타" 명시.

#### 8. [ACCEPT] [Medium] §3.5 rollback 옵션 1번의 부수효과 미언급
- **Critic**: `AF_SKIP_ESCALATION=1`은 fail-open 전체 BLOCK 우회 → P2 enforce(e2e_command_missing)도 무력화. §1.2에선 지적했으나 §3.5 표에선 평등한 옵션처럼 묘사.
- **Cross**: not flagged
- **Judgment**: `core/approval_gate.py:181-183` 동작 일치 확인. 운영 가이드 누락.
- **Action Required**: §3.5 표에 "옵션 1 사용 시 P2 enforce rule도 함께 우회됨 — 긴급용. P4 rule만 끄려면 옵션 3(`mode: off`) 권장" 추가.

#### 9. [HOLD] [Medium] frozen 빌드의 yaml rollback 경로가 실제 dist 레이아웃과 일치하는지 미검증
- **Critic**: §8.5 line 421 — `af warning-stats --rule owner_role_mismatch` 출력에 `escalation_phase` 마커 포함 baseline 미검증.
- **Cross**: 더 근본 — frozen 모드에선 `BASE_DIR = dirname(sys.executable)`. PyInstaller datas가 `_internal/config/`로 갈 수도 있어 "yaml edit → 다음 summarize 즉시 반영"이 설치 사용자에게 거짓일 수 있음.
- **Judgment**: 두 지적 모두 frozen 빌드 검증 부족이지만 실제 `dist/af` 레이아웃 확인 필요. Critic은 출력 schema, Cross는 yaml 경로 — 둘 다 frozen 검증 보강이 필요하나 실제 빌드 결과 없이 결정 불가.
- **Question for Author**: `python build_exe.py` 후 `dist/af/` 트리에서 `config/escalation_policy.yaml` 위치는? `core.escalation_evaluator._POLICY_PATH`가 frozen 모드에서 resolve되는 실제 경로는? — §8.5 smoke를 그 경로 출력 + yaml 1줄 revert + 재실행으로 e2e 확장.

#### 10. [ACCEPT] [Low] §8 테스트 케이스에 evidence_quality_warn observation 검증 부재
- **Critic**: §3.4가 evidence_quality_warn도 observation 시작이라 명시했으나 §8.1~§8.3 10 케이스 모두 owner_role_mismatch 중심. P4 진입 시 두 rule 모두 BLOCK 0건이 §10 #9 핵심.
- **Cross**: not flagged
- **Judgment**: 단순 누락. 비용 작음.
- **Action Required**: §8.1에 `test_evidence_quality_warn_observation_does_not_block` 추가. §8.3 #9에서 두 rule 모두 mode=observation 동시 assertion.

### Rejected

#### R1. [REJECT] [Low] `_write_minimal_block_decision`이 `"P2"` 하드코딩 유지
- **Source**: Cross (Initial concern, self-rejected)
- **Original Finding**: P4 current phase와 불일치로 보임.
- **Rejection Reason**: Critic도 §1.1 Positive Observations에서 동일 결정 검증. `core/approval_gate.py:225`에서 `decision_phase_num <= expected_phase_num`이면 통과 → P2 비상 decision은 P4 summary와 호환. minimal writer 격리 의도 정당. (Cross가 직접 reject)

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | mode 분기가 false_positive_override 앞 | High | ACCEPT | Both |
| 2 | write_error_decision md본문 P2 잔존 | High | ACCEPT | Critic |
| 3 | _decision.md block_candidate 가시화 미구현 | High | ACCEPT | Both |
| 4 | rule_decisions 스키마 P4b 데이터 부족 | High | ACCEPT | Both |
| 5 | load_policy() 2회 호출 → phase drift | Medium | ACCEPT | Both |
| 6 | warning_registry import 순환 위험 | Medium | ACCEPT | Cross |
| 7 | _index.json/yaml mode 이중 진실원 | Medium | ACCEPT | Critic |
| 8 | §3.5 rollback 옵션1 부수효과 누락 | Medium | ACCEPT | Critic |
| 9 | frozen 빌드 yaml 경로/출력 미검증 | Medium | HOLD | Both |
| 10 | evidence_quality_warn observation 테스트 누락 | Low | ACCEPT | Critic |
| R1 | minimal writer P2 잔존 | Low | REJECT | Cross |

### Recommendations

구현 진입 전 다음을 설계 문서에 반영:

1. **§5 evaluator 분기 순서 명시** — `false_positive_override`가 `mode 분기` 앞에 오도록 코드 골격 수정 (Finding #1).
2. **§7 변경 파일 범위 확장** — `escalation_decision_report.py:28-68`로 늘리고 line 43·57 둘 다 `current_phase` 치환 (Finding #2).
3. **§5에 `_write_decision_md` 변경 추가** — observation 섹션 출력 사양 명시 + 테스트 (Finding #3).
4. **`EscalationDecision` 스키마 확장** — `affected_phase / count / repeat_count / threshold / mode` 직렬화 (Finding #4).
5. **§5.4·§6 의사코드** — `policy = load_policy()` 단 한 번 호출하고 두 곳에 전달 (Finding #5).
6. **§7 import 절** — lazy import 유지 명시 (Finding #6).
7. **§3.2 또는 §3.7** — `_index.json.mode` 제거 또는 동기화 테스트 추가 + Master_Blueprint 단일 진실원 명시 (Finding #7).
8. **§3.5 표 운영 가이드** — 옵션 1 우회 범위 경고 + 옵션 3 권장 (Finding #8).
9. **§8 테스트 보강** — evidence_quality_warn observation 케이스 + `_decision.md` 본문 assertion + load_policy 단일 호출 검증 (Findings #3, #5, #10).
10. **frozen 빌드 사실 확인 후 §8.5 재작성** — `dist/af` 실제 레이아웃 + `_POLICY_PATH` 출력 + yaml revert e2e (Finding #9).

위 10개 반영 후 재리뷰 1라운드만 더 돌려도 PASS 가능 — BLOCK 항목 없음, 핵심 결정(Decision A/B/C/D)은 모두 유효.