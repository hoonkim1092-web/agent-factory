# P4a 설계문서 교차 검증 — Cross-Provider Fan-out

- 일시: 2026-05-10
- 대상 문서: docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md (487줄, v1)
- 외부 프로바이더: codex-cli 0.130.0 (gpt-5.5) — gemini 미가용
- 진행: codex 1개 호출 (480s), Claude Opus 4.7 1차 grep 반증 동시 수행
- 출력 파일: 본 문서 (raw codex 응답 + Claude 판정)

---

## §1 Codex 원문 응답 (raw)

[INFO] 1 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:40](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:40) — baseline 인용은 코드와 일치. `rg 'current_phase="P2"' core/warning_registry.py` → [core/warning_registry.py:216](/Users/hoon/workTree/agent-factory/core/warning_registry.py:216), `summary["escalation_phase"] = "P2"` → [core/warning_registry.py:192](/Users/hoon/workTree/agent-factory/core/warning_registry.py:192), minimal payload `"P2"` → [core/warning_registry.py:283](/Users/hoon/workTree/agent-factory/core/warning_registry.py:283), `write_error_decision` payload `"P2"` → [core/escalation_decision_report.py:41](/Users/hoon/workTree/agent-factory/core/escalation_decision_report.py:41).

[WARN] 1 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:50](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:50) — `_index.json:11-16` 인용은 `owner_role_mismatch`만 정확. [runtime/warnings/_index.json:18](/Users/hoon/workTree/agent-factory/runtime/warnings/_index.json:18)의 `evidence_quality_warn`에는 `mode`/`measure_at`이 없음. §3.2의 “_index.json이 이미 같은 단어 사용” 근거를 P4 rule 전체로 일반화하면 불일치.

[WARN] 2 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:127](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:127) — §3.2 채택 근거가 “두 파일을 보면 같은 의미”라고 하지만 실제는 yaml에 `evidence_quality_warn.mode: observation`을 추가하는 순간 `_index.json`과 의미 동기 불일치가 생김. [runtime/warnings/_index.json:18](/Users/hoon/workTree/agent-factory/runtime/warnings/_index.json:18)에는 mode 없음.

[INFO] 2 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:110](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:110) — §3.1 `current_phase`를 yaml top-level로 두는 결정은 현재 구조와 맞음. 정책은 이미 [config/escalation_policy.yaml:4](/Users/hoon/workTree/agent-factory/config/escalation_policy.yaml:4) `version/rules` 아래 `activate_at/block_when`을 갖고, evaluator는 policy dict를 받아 [core/escalation_evaluator.py:160](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:160) `compute_run_decision(..., current_phase="P2")`로 평가함.

[WARN] 3 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:74](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:74) — 문서 내부 모순. §2는 `mode == observation/off`면 `reason="observation_mode"`로 “즉시 반환”이라고 쓰지만, §5.3-B/의사코드는 threshold를 평가해 `observation_threshold_met` 또는 `observation_below_threshold`를 반환한다고 함([docs:290](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:290), [docs:302](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:302)). §0.1 첫 실행 설명의 `reason="observation_mode"`도 같은 불일치([docs:30](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:30)).

[WARN] 3 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:263](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:263) — mode 분기 위치 “inactive_phase 직후, false_positive_override 직전”은 기존 코드 위치상 삽입 가능함: inactive는 [core/escalation_evaluator.py:116](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:116), false-positive는 [core/escalation_evaluator.py:122](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:122). 다만 이 순서는 `false_positive_override`가 observation candidate를 억제하지 못하게 만든다. summary의 `any_override`는 [core/warning_registry.py:355](/Users/hoon/workTree/agent-factory/core/warning_registry.py:355)에서 들어가고 virtual record로 [core/escalation_evaluator.py:183](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:183)에 전달되므로, override semantics를 유지하려면 mode 분기는 false-positive 뒤여야 한다.

[WARN] 3 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:320](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:320) — “threshold 평가가 P4b 데이터 가시화에 필수”는 과장. P3 통계는 `warning_stats`가 jsonl을 직접 스캔하며 [core/warning_stats.py:141](/Users/hoon/workTree/agent-factory/core/warning_stats.py:141), `count/repeat_count/by_phase` 분포는 decision 없이도 계산됨. threshold 평가는 `_decision.json`에서 candidate 빈도를 보려는 추가 가시화에는 유용하지만 P4b 임계 결정 자체의 필수 데이터 경로는 아님.

[WARN] 4 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:414](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:414) — §8.4 회귀 테스트 명세는 P2 enforce 보존을 “기존 테스트 통과”에 의존함. 현재 P2 핵심은 [core/escalation_evaluator.py:196](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:196)의 `if d.block`와 [config/escalation_policy.yaml:6](/Users/hoon/workTree/agent-factory/config/escalation_policy.yaml:6)의 `e2e_command_missing activate_at: P2`. P4a 전용 회귀로 “v1 yaml + current_phase=P4 + e2e mode=enforce + build count=1 => block=True” 케이스가 명시되어 있지 않아 충분하지 않음.

[INFO] 4 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:453](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:453) — `_write_minimal_block_decision`의 `"P2"` 유지 논리는 approval gate 코드상 통과한다. gate는 [core/approval_gate.py:231](/Users/hoon/workTree/agent-factory/core/approval_gate.py:231)에서 `decision_phase_num > expected_phase_num`만 mismatch로 막고, 낮은 decision phase는 [core/approval_gate.py:239](/Users/hoon/workTree/agent-factory/core/approval_gate.py:239)에서 순방향 호환으로 둠. 기존 테스트도 P2 decision + P3 summary 통과를 검증함([tests/test_approval_gate_block_decision.py:117](/Users/hoon/workTree/agent-factory/tests/test_approval_gate_block_decision.py:117)).

[WARN] 5 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:205](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:205) — v0 yaml fallback으로 P2 동작 보존은 설계상 맞지만, “100%”는 `write_error_decision` 동적 phase 전달 경로까지 구현되어야 성립. 현재 호출부는 [core/warning_registry.py:226](/Users/hoon/workTree/agent-factory/core/warning_registry.py:226)에서 `current_phase` 인자를 전달하지 않고, writer도 [core/escalation_decision_report.py:34](/Users/hoon/workTree/agent-factory/core/escalation_decision_report.py:34)에 인자가 없음. 설계에는 포함되어 있으나 §5.4 “compute만 0줄”과 함께 호출부 변경 누락 위험이 큼.

[BLOCK] 6 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:145](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:145) — self-contradiction 확인. `evidence_quality_warn도 mode: observation`으로 시작한다고 하지만 `_index.json`에는 [runtime/warnings/_index.json:18](/Users/hoon/workTree/agent-factory/runtime/warnings/_index.json:18)-[20](/Users/hoon/workTree/agent-factory/runtime/warnings/_index.json:20) `rule_id/activate_at/source`만 있음. §11은 P4b에서 `_index.json mode` 동기도 요구함([docs:478](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:478)). P4a에서 yaml만 mode 추가하면 두 정책 표면이 즉시 불일치한다.

[BLOCK] 7 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:324](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:324) — §5.4 “compute_run_decision 변경 0”은 부정확. `compute_run_decision` 시그니처는 그대로여도, observation threshold 결과를 `rule_decisions`에 남기려면 `evaluate()`가 mode를 읽어야 하고 `_PolicyRule.from_dict`가 mode를 보존해야 함. 현재 `_PolicyRule`에는 mode 필드가 없고([core/escalation_evaluator.py:41](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:41)), `from_dict`도 mode를 버림([core/escalation_evaluator.py:56](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:56)).

[BLOCK] 7 — [docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:378](/Users/hoon/workTree/agent-factory/docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md:378) — `current_phase` 전달 명세가 호출 site 단위로 아직 불완전함. 현재 `warning_registry.summarize()`는 policy를 두 번 읽는 형태로 설계 변경될 가능성이 있고, 현 코드는 [core/warning_registry.py:215](/Users/hoon/workTree/agent-factory/core/warning_registry.py:215)-[217](/Users/hoon/workTree/agent-factory/core/warning_registry.py:217)에서 `load_policy()` 결과와 `current_phase="P2"`를 직접 넘김. P4a 구현 명세는 반드시 `policy = load_policy(); current_phase = read_current_phase(policy); compute_run_decision(summary, policy, current_phase=current_phase)` 단일 policy 객체 흐름을 못박아야 함. 그렇지 않으면 summary phase와 decision phase가 서로 다른 policy read에서 올 수 있음.

verdict: BLOCK
---

## §2 Claude 1차 grep 반증 결과 (independent)

| 검증 좌표 | 설계문서 인용 | Claude grep 실제값 | 판정 |
|-----------|---------------|---------------------|------|
| `core/warning_registry.py` `current_phase="P2"` | line 215-217 | **line 216** (단 1줄) | ✅ 일치 |
| `core/warning_registry.py` `escalation_phase = "P2"` | line 192 | **line 192** | ✅ 일치 |
| `core/warning_registry.py` minimal payload `"P2"` | line 283 | **line 283** | ✅ 일치 |
| `core/escalation_decision_report.py` write_error payload `"P2"` | line 41 | **line 41** | ✅ 일치 |
| `core/approval_gate.py` `_PHASE_ORDER_EC` P4 등록 | line 226 | **line 226** | ✅ 일치 |
| `core/escalation_evaluator.py` `block_candidate` docstring | line 25 | **line 25** | ✅ 일치 |
| `runtime/warnings/_index.json` owner_role mode | line 11-16 | line 14 (`mode: "observation"`) | ✅ 일치 |
| `runtime/warnings/_index.json` evidence_quality_warn | (언급 없음) | line 18-21 (**mode 필드 없음**) | ⚠ 자기모순 가능 |
| `runtime/warnings/*.jsonl` 측정 데이터 | 0건 | `find … -name '*.jsonl' \| wc -l` = **0** | ✅ 일치 |
| `config/escalation_policy.yaml` current_phase/mode | 부재 | grep 매칭 0건 | ✅ 일치 |
| install-af.ps1 `1.2.26` 카운트 | "8곳" | `grep -c '1\.2\.26'` = **8** | ✅ 일치 |

**Claude 1차 결론**: 설계문서의 baseline file:line 인용은 **모두 정확**. self-contradiction 후보는 §3.4 evidence_quality_warn 결정과 _index.json mode 부재 간 불일치 1건.

---

## §3 Finding별 Claude 최종 판정


### Finding 1 — [INFO] Baseline 정합 (Codex)

- **Codex 원문**: "baseline 인용은 코드와 일치. ... line 216, 192, 283, 41 모두 확인"
- **Claude 판정**: **ACCEPT**
- **근거**: Claude도 동일 grep 수행 (§2 표). 7개 좌표 전부 일치. 추가 issue 없음.
- **조치**: 없음. baseline은 정확함.

---

### Finding 2 — [WARN] _index.json evidence_quality_warn mode 누락 (Codex W1)

- **Codex 원문**: "`_index.json:11-16` 인용은 owner_role_mismatch만 정확. line 18의 evidence_quality_warn에는 mode/measure_at이 없음. §3.2의 '_index.json이 이미 같은 단어 사용' 근거를 P4 rule 전체로 일반화하면 불일치."
- **Claude 판정**: **ACCEPT**
- **근거**: `runtime/warnings/_index.json` line 18-21 확인 결과 `evidence_quality_warn`은 `rule_id/activate_at/source` 3필드만 있음. owner_role_mismatch (line 11-15)에는 `measure_at`/`mode` 필드 존재. P3에서 owner_role만 mode 필드를 받았고 evidence_quality는 P4a 범위로 미뤄진 것. 설계 §3.2 채택 근거가 "_index.json이 이미 같은 단어 사용"이라고 하면서 P4 rule 둘 다(§3.4)에 mode 부여하면 evidence_quality 한쪽은 yaml-only가 됨.
- **조치**: 설계 §3.2 채택 근거를 "_index.json owner_role mode와 동일 어휘를 P4 rule 전체로 통일" 표현으로 보완하거나, P4a에서 _index.json evidence_quality에도 mode 필드 동시 추가 결정 명시.

---

### Finding 3 — [WARN] §3.2 / _index.json 의미 동기 불일치 (Codex W2)

- **Codex 원문**: "§3.2가 '두 파일을 보면 같은 의미'라고 하지만 yaml에 evidence_quality_warn.mode: observation 추가 시 _index.json과 의미 동기 불일치"
- **Claude 판정**: **ACCEPT**
- **근거**: Finding 2와 동일 코드 사실. 설계 §11(P4b 인계)는 "P4b가 _index.json mode 동기"를 명시했으므로 P4a 범위에서는 의도적으로 yaml만 갱신하고 _index.json은 P4b로 미루는 그림이지만, §3.2 채택 근거 표현이 이 시간 갭을 모호하게 만듦. 자기모순보다는 표현 보완 사안.
- **조치**: §3.2 마지막 문단에 "_index.json evidence_quality mode 필드 동기는 P4b에서 처리 (P4a는 yaml v1만 갱신)" 명시 1줄 추가 권장.

---

### Finding 4 — [WARN] §0.1 / §2의 `reason="observation_mode"` vs §5.3-B `observation_threshold_met`/`observation_below_threshold` 모순 (Codex W3-a)

- **Codex 원문**: "§2는 mode==observation/off면 `reason='observation_mode'`로 즉시 반환, 그러나 §5.3-B/의사코드는 threshold 평가해 `observation_threshold_met`/`observation_below_threshold` 반환. §0.1 첫 실행 설명도 같은 불일치."
- **Claude 판정**: **ACCEPT (BLOCK 후보)**
- **근거**: 직접 확인:
  - 설계문서 line 30 (§0.1): `reason="observation_mode"`
  - 설계문서 line 74 (§2.1): `block=False severity="block_candidate" reason="observation_mode" 즉시 반환`
  - 설계문서 line 287 (§5.3-B): `reason="mode_off"` (off 모드)
  - 설계문서 line 302 (§5.3-B): `reason="observation_threshold_met"`
  - 설계문서 line 307 (§5.3-B): `reason="observation_below_threshold"`
  - 설계문서 line 332-334 (§5.5): warn에 `observation_below_threshold`, block_candidate에 `observation_threshold_met` 등록 — §5.3-B와 일관, §0.1/§2와 모순
- 명백한 자기모순. §5.5/§5.3-B가 최종 결정으로 보이고, §0.1/§2의 "observation_mode" 표현이 이전 버전 잔재.
- **조치**: §0.1 표 line 30 + §2.1 line 74의 `reason="observation_mode"` 표현을 `reason="observation_threshold_met|observation_below_threshold"` (또는 추상적으로 "mode 분기 reason")로 정정 필요. **BLOCK 등급 가치 있음** — 구현자가 §0.1/§2만 보고 reason="observation_mode" 하드코딩하면 §5.5 severity 표와 불일치하는 산출물 생성.

---

### Finding 5 — [WARN] mode 분기 위치가 false_positive_override를 우회 (Codex W3-b)

- **Codex 원문**: "이 순서는 false_positive_override가 observation candidate를 억제하지 못하게 만든다. summary의 any_override는 warning_registry.py:355에서 들어가고 virtual record로 escalation_evaluator.py:183에 전달되므로, override semantics를 유지하려면 mode 분기는 false-positive 뒤여야 한다."
- **Claude 판정**: **ACCEPT**
- **근거**: 코드 직접 확인:
  - `core/warning_registry.py:355` `"any_override": rid in overridden_rules` ✓
  - `core/escalation_evaluator.py:183` `false_positive_override=bool(info.get("any_override", False))` ✓
  - 현재 `evaluate()` 순서: inactive_phase(116) → false_positive_override(122) → exempt → block_when
  - 설계 §5.3-B는 mode 분기를 (122) 직전에 끼우자고 명시 → false_positive_override가 후순위로 밀려서 **override한 record도 observation에선 block_candidate로 보고됨**
  - P4b가 _decision.json에서 candidate 빈도 보고 임계 결정할 때 **override된 false-positive까지 candidate count에 포함되어 임계가 인위적으로 높게 보일 수 있음** — 데이터 오염 위험
- **조치**: §5.3-B 위치 결정을 재검토. 옵션:
  - (a) mode 분기를 `false_positive_override` **직후**로 이동 (override한 record는 mode 무관 warn 유지)
  - (b) §10에 "observation은 override를 무시한다"를 명시적 결정으로 못박고 P4b가 override 분리 집계
- 설계자가 어느 시맨틱을 택할지 결정 필요. **현 설계는 결정 없음 = 결함**.

---

### Finding 6 — [WARN] "threshold 평가가 P4b 데이터 가시화에 필수"는 과장 (Codex W3-c)

- **Codex 원문**: "P3 통계는 warning_stats가 jsonl을 직접 스캔하며 (warning_stats.py:141), count/repeat_count/by_phase 분포는 decision 없이도 계산됨. threshold 평가는 _decision.json에서 candidate 빈도를 보려는 추가 가시화에는 유용하지만 P4b 임계 결정 자체의 필수 데이터 경로는 아님."
- **Claude 판정**: **ACCEPT**
- **근거**: `core/warning_stats.py:227-330` 확인. jsonl 직접 스캔으로 `by_per_record_count`/`repeat_count_max` 분포 생성. P4b가 임계 결정에 쓰는 1차 데이터는 이 jsonl 스캔 결과지 _decision.json rule_decisions가 아님. 설계 §5.3-B 마지막 단락 ("왜 observation에서도 threshold 평가하나")의 표현이 과장됨 — "필수"가 아니라 "추가 교차 검증용".
- **조치**: §5.3-B 마지막 단락 표현 완화 ("필수" → "선택적 가시화"). 결정 자체는 유지 가능 — observation에서 threshold 평가하는 것이 P4b가 _decision.json만 봐도 즉시 candidate 분포 추적 가능한 부가가치 있음. 다만 "필수"라는 정당화는 부정확.

---

### Finding 7 — [WARN] P4a 전용 회귀 테스트 명시 부족 (Codex W4)

- **Codex 원문**: "§8.4 회귀 테스트 명세는 P2 enforce 보존을 '기존 테스트 통과'에 의존함. P4a 전용 회귀로 'v1 yaml + current_phase=P4 + e2e mode=enforce + build count=1 => block=True' 케이스가 명시되어 있지 않아 충분하지 않음."
- **Claude 판정**: **ACCEPT**
- **근거**: 설계 §8.1~§8.3은 P4a 신규 기능(observation/off/yaml fallback) 위주. §8.4는 "기존 테스트 통과"만 명시. **P2 rule이 P4 phase 환경에서도 enforce 동작하는 통합 테스트는 없음**. 회귀 차단 수단으로는 부족 — 누군가 mode 분기를 잘못 짜서 enforce도 우회시켰을 때 §8.1-8.3 테스트는 통과하고 §8.4 기존 테스트도 (yaml flip 안 하면) 통과할 수 있음.
- **조치**: §8.1에 11번째 케이스 추가:
  - `test_e2e_command_missing_blocks_under_p4_current_phase` — yaml `current_phase: "P4"` + e2e_command_missing `mode: "enforce"` + record(build phase, count=1) → `block=True severity="block" reason="threshold_met"`
- 이 1 케이스가 enforce 회귀 가드. **WARN 수준으로 충분**, BLOCK은 아님 (구현 시 추가 가능).

---

### Finding 8 — [INFO] _write_minimal_block_decision "P2" 유지 결정 안전 (Codex INFO 4)

- **Codex 원문**: "approval gate는 line 231에서 decision_phase_num > expected_phase_num만 mismatch로 막고, 낮은 decision phase는 line 239에서 순방향 호환. tests/test_approval_gate_block_decision.py:117에서도 P2 decision + P3 summary 통과 검증."
- **Claude 판정**: **ACCEPT**
- **근거**: `core/approval_gate.py:231` `if decision_phase_num > expected_phase_num` 확인. P4 워크스페이스(expected=P4)에서 minimal payload(decision=P2) 작성되어도 `2 > 4 = False`이므로 phase mismatch 발화 안 함. 다만 그 다음 라인 252의 `bool(d.get("block"))` 체크에서 minimal decision의 `block: True`가 그대로 fail-closed로 작동 — 의도와 일치.
- **조치**: 없음. §10 #6 결정은 정확함.

---

### Finding 9 — [WARN] write_error_decision current_phase 인자 누락 (Codex W5)

- **Codex 원문**: "v0 yaml fallback으로 P2 동작 보존은 설계상 맞지만 '100%'는 write_error_decision 동적 phase 전달 경로까지 구현되어야 성립. 현재 호출부는 warning_registry.py:226에서 current_phase 인자를 전달하지 않고, writer도 escalation_decision_report.py:34에 인자가 없음. 설계에 포함되어 있으나 §5.4 'compute만 0줄'과 함께 호출부 변경 누락 위험이 큼."
- **Claude 판정**: **ACCEPT**
- **근거**: 코드 직접 확인:
  - `core/warning_registry.py:226-230` `write_error_decision(slug_dir, project_slug=..., summary_last_updated=..., error_repr=...)` — current_phase 인자 없음
  - `core/escalation_decision_report.py:28-35` `write_error_decision(slug_dir, *, project_slug, summary_last_updated, error_repr)` — current_phase 시그니처 없음
  - 설계 §7 #4/#5는 이 변경을 명시하지만, §2.1 "포함" 목록의 표현 ("write_error_decision도 current_phase 인자 받아 동적 마커 작성")이 caller 변경(§7 #5)을 별도 항목으로 강조하지 않으면 구현자가 빠뜨릴 위험. §5.4 "compute_run_decision 변경 0줄"이 caller 변경 0이라는 인상을 강화.
- **조치**: §5.4 제목/표현을 명확히. "compute_run_decision 시그니처 변경 0줄, 단 호출자(warning_registry.summarize)는 변경 필요 — §7 #3, #5 참조" 1줄 추가 권장.

---

### Finding 10 — [BLOCK] §3.4 evidence_quality_warn observation 결정 vs _index.json 자기모순 (Codex BLOCK 6)

- **Codex 원문**: "self-contradiction 확인. evidence_quality_warn도 mode: observation으로 시작한다고 하지만 _index.json line 18-20에는 rule_id/activate_at/source만 있음. §11은 P4b에서 _index.json mode 동기도 요구. P4a에서 yaml만 mode 추가하면 두 정책 표면이 즉시 불일치."
- **Claude 판정**: **HOLD** (Codex는 BLOCK이지만 Claude는 보류)
- **근거**: 
  - 사실 자체는 일치 — Finding 2/3과 동일 grep
  - 그러나 설계 §11 명시적으로 "_index.json mode 동기는 P4b 책임" — 의도된 시간 갭. 자기모순이라기보다는 **2단계 schema sync 전략**.
  - 다만 §0.1 표/§3.4의 표현이 이 시간 갭을 명시하지 않음 — 독자가 P4a 범위로 _index.json 동기까지 기대할 수 있음.
- 시맨틱 결함 = NO (의도된 분리). 표현 불명확 = YES (보완 권장).
- **조치**: BLOCK으로 강등하지 말고 §3.4 마지막에 "_index.json mode 필드는 P4b에서 동기 (§11)"  1줄 추가하면 모순 해소. **WARN 등급 충분**.

---

### Finding 11 — [BLOCK] §5.4 "compute_run_decision 변경 0" 부정확 (Codex BLOCK 7-a)

- **Codex 원문**: "compute_run_decision 시그니처는 그대로여도, observation threshold 결과를 rule_decisions에 남기려면 evaluate()가 mode를 읽어야 하고 _PolicyRule.from_dict가 mode를 보존해야 함. 현재 _PolicyRule에는 mode 필드가 없고(escalation_evaluator.py:41), from_dict도 mode를 버림(line 56)."
- **Claude 판정**: **REJECT**
- **근거**: Codex가 §5.4의 의도를 잘못 읽었음. §5.4 본문은 "compute_run_decision은 current_phase 인자만 받으므로 시그니처 무변경. 단, observation severity → blocking 카운터에서 제외 (이미 if d.block: blocking.append(...) 로직이 block=False면 자동 제외 → **변경 0**)"라고 명시. 즉 §5.4는 `compute_run_decision` **함수 자체의** 변경이 0이라는 뜻이지, 의존하는 `_PolicyRule`/`evaluate()` 변경이 0이란 뜻 아님. `_PolicyRule.mode` 추가는 §5.1에서, `evaluate()` mode 분기는 §5.3에서 별도로 명세됨.
- 단, Codex의 지적이 §5.4 표현이 헷갈림을 유발했다는 신호이므로 — 표현 보완은 가치 있음 (Finding 9와 통합). BLOCK은 잘못된 판정.

---

### Finding 12 — [BLOCK] current_phase 단일 policy 객체 흐름 미명시 (Codex BLOCK 7-b)

- **Codex 원문**: "current_phase 전달 명세가 호출 site 단위로 아직 불완전. P4a 구현 명세는 반드시 `policy = load_policy(); current_phase = read_current_phase(policy); compute_run_decision(summary, policy, current_phase=current_phase)` 단일 policy 객체 흐름을 못박아야 함. 그렇지 않으면 summary phase와 decision phase가 서로 다른 policy read에서 올 수 있음."
- **Claude 판정**: **ACCEPT**
- **근거**: 현 설계 §7 #3 표현 "`current_phase = read_current_phase(load_policy())` 동적 로드 + `summary["escalation_phase"] = current_phase`"는 한 번 로드 의도이지만 명확하지 않음. 별도로 §6 흐름도 line 349/351에서도 `read_current_phase(load_policy())` 와 `compute_run_decision(summary, policy, current_phase=...)`이 두 줄로 분리되어 있어 구현자가 `load_policy()` 두 번 호출하는 코드를 짤 가능성 있음. 동일 yaml 파일이지만 atomic write 도중 race condition은 없을 것 (yaml 변경은 사용자 수동 수정). 그러나 **명시적 single-load 패턴 못박기**는 의미 있음.
- **조치**: §10 #1을 다음으로 강화:
  > 1. **`current_phase`는 yaml 단일 진실원**. env/code hardcode 금지. `read_current_phase()` 한 함수만이 진입점. **호출자는 `policy = load_policy()` 한 번 호출 후 `current_phase`/`compute_run_decision` 모두 같은 policy 객체 사용** — split read 금지.
- BLOCK 등급은 과함 (race condition 위험은 yaml 사용자 수동 수정이라 현실적 문제 아님). **WARN 등급으로 reclassify**.

---

## §4 최종 Verdict 종합

| 검증 항목 | Codex Severity | Claude 판정 | 근거 |
|-----------|----------------|-------------|------|
| 1. Baseline 정합 | INFO | ACCEPT | 7 좌표 전부 grep 일치 |
| 2. 결정 정합 (§3.1~§3.5) | INFO+WARN | ACCEPT (보완 권장) | yaml 단일 진실원 결정 OK, §3.2 표현 보완 필요 |
| 3. 시맨틱 정합 (§5.3-B) | WARN×3 | **3건 ACCEPT** | reason 모순(F4) + override 우회(F5) + "필수" 과장(F6) |
| 4. 회귀 차단 | WARN+INFO | ACCEPT (F7), ACCEPT (F8 안전성) | P2 enforce 통합 테스트 누락, minimal payload 안전 |
| 5. Schema migration | WARN | ACCEPT (F9) | write_error_decision caller 변경 위험 |
| 6. Self-contradiction | BLOCK | **HOLD (WARN으로 강등)** | §11 의도된 시간 갭, 표현 보완으로 해소 |
| 7. 누락된 결정점 | BLOCK×2 | F11 REJECT, F12 ACCEPT (WARN 강등) | F11은 §5.4 의도 오독, F12는 single-load 명시 권장 |

**최종 Verdict**: **WARN (advisory)** — Phase 0 정책상 BLOCK 자동 수정 의무는 없으나, 다음 항목 중 적어도 **F4 (reason 모순)** 와 **F5 (override 우회)** 는 구현 진입 전 명시적 결정 필요:

### BLOCK 1건 (구현 전 결정 강제)
- **F4** [§5.5 vs §0.1/§2.1 reason 표현 모순] — 구현자 혼동 유발 가능성 큼. §0.1/§2.1 표현 정정 1줄 수정으로 해소.

### WARN 6건 (advisory, 설계자 판단)
- **F2/F3** [evidence_quality_warn _index.json mode 동기 명시 부재] — §3.4/§3.2에 P4b 분리 명시 1줄 추가
- **F5** [observation 모드에서 false_positive_override 시맨틱 결정] — §5.3-B 위치 재검토 또는 §10에 "observation은 override 무시" 명시
- **F6** [§5.3-B "필수" 표현 완화]
- **F7** [§8.1에 P4 환경 e2e enforce 회귀 1 케이스 추가]
- **F9** [§5.4/§7 #5 caller 변경 강조]
- **F12** [§10 #1에 single-load 패턴 명시]

### 통과 (정책상 PASS)
- **F1** [Baseline 7 좌표] — 정확
- **F8** [_write_minimal_block_decision P2 유지] — 안전 확인됨

### Codex 오판 (REJECT)
- **F11** [§5.4 "compute 0줄" BLOCK] — Codex가 §5.4 본문을 잘못 해석. 실제 §5.4는 compute_run_decision 함수 자체 변경 0의 의미.

---

## §5 권장 다음 액션

1. **즉시 (구현 진입 전)**: 설계문서 v1 → v2 보완
   - F4 (reason 표현 통일): §0.1 line 30 + §2.1 line 74 정정
   - F5 (override semantics 결정): §5.3-B 또는 §10에 명시
2. **권장 (v2 보완 동시)**: F2/F3/F6/F7/F9/F12 표현 보완 — 5분 미만
3. **선택**: P4b 인계서에 _index.json evidence_quality mode 동기 1줄 추가 (§11)

