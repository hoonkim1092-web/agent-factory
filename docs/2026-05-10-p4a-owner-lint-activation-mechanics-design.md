# P4a — owner_role_mismatch 활성화 메커니즘 설계 (임계 TBD, P4b 인계)

- 작성일: 2026-05-10
- 모델: Opus 4.7 (1M)
- 의존: `docs/2026-05-09-warning-registry-and-gate-escalation-design.md` (P1) / `docs/2026-05-09-p2-e2e-command-block-activation-design.md` (P2) / `docs/2026-05-10-p3-owner-lint-measurement-design.md` (P3 v4)
- 브랜치: `main` (또는 P4a 전용 후속 브랜치)
- 상태: v2 — cross-review 1라운드 (2026-05-10 21:09) BLOCK 1 + WARN 6 흡수
- 이력:
  - v1 (2026-05-10) — 초안
  - v2 (2026-05-10) — cross-review BLOCK 1 + 결정 강제 1 + WARN 4 흡수:
    1. (F4 BLOCK) §0.1/§2.1의 `reason="observation_mode"` → `reason="observation_threshold_met|observation_below_threshold"` 표현 통일 (§5.5/§5.3-B와 일관)
    2. (F5 WARN, 결정 강제) mode 분기 위치를 `false_positive_override` **직후**로 변경 (옵션 (a) 채택). override한 record는 mode 무관 warn 유지 — P4b candidate count 데이터 오염 방지. exempt_when도 observation 경로에서 적용.
    3. (F2/F3 WARN) §3.2/§3.4 마지막에 "_index.json evidence_quality mode 동기는 P4b 책임" 1줄 추가
    4. (F7 WARN) §8.1에 11번째 케이스 추가 — P4 phase 환경에서 e2e_command_missing enforce가 BLOCK 발화하는 회귀 가드
    5. (F9 WARN) §5.4 표현 보완 — "compute_run_decision **함수 자체** 시그니처/내부 변경 0. 단 caller(`warning_registry.summarize`)는 §7 #3, #5 변경 필수"
    6. (F12 WARN) §10 #1을 single-load 패턴 강조로 강화 — `policy = load_policy()` 한 번 호출 후 같은 객체 사용
    7. (F11 REJECT) Codex F11 (§5.4 "compute 0줄" BLOCK) 오독 — §5.4는 compute 함수 자체 0이라는 의미, _PolicyRule/evaluate 변경은 §5.1/§5.3에 별도 명세. F9 표현 보완으로 혼동 차단.

---

## §0 Goal — 한 줄 정의

> **P4a = "P4로 들어가는 기계장치 설계"**. owner_role_mismatch / evidence_quality_warn 의 **임계값(threshold)은 결정하지 않는다** — 측정 데이터 0건 상태에서 임계 확정은 P3 measurement window 후 **P4b**의 책임. P4a는 (1) `current_phase` 진입 메커니즘, (2) rule-level `mode` 필드(observation/enforce) 도입, (3) escalation_phase 마커 동적화, (4) rollback 4단을 결정·구현한다.

### 0.1 P3 vs P4a vs P4b 경계 (사용자 가시 변화)

| 항목 | P3 (완료, v1.2.26) | **P4a (본 설계)** | P4b (이연) |
|------|-------------------|-------------------|------------|
| `current_phase` 단일 진실원 | `core/warning_registry.py:216` 하드코딩 `"P2"` | ✅ **`config/escalation_policy.yaml` `current_phase` 필드** — 하드코딩 제거, yaml→evaluator 전파 | (변경 없음) |
| `current_phase` 운영 값 | (계속 `"P2"`) | ✅ **`current_phase: "P4"`로 전환** | (그대로 P4) |
| P4 rule 평가 진입 | `inactive_phase` (block=False) | ✅ **evaluate 진입** — 단, mode 분기로 BLOCK 미발생 | (그대로 진입) |
| `mode` 필드 (yaml) | 없음 | ✅ **rule별 `mode: observation \| enforce`** 도입. P4 rule 둘 다 `observation` 시작 | `mode: enforce` toggle |
| BLOCK 발화 가능성 | 0% (phase 미달) | **0% 보장** (mode=observation로 차단) | owner_role_mismatch 임계 도달 시 BLOCK |
| `repeat_count_min` / `count_per_run_min` 값 | yaml placeholder (`3` / `5`) | (변경 없음, 의미 없음 — observation에선 미사용) | ✅ **P3 measurement 데이터로 결정 후 lock** |
| `escalation_phase` 마커 | summary/decision 모두 `"P2"` 하드코딩 | ✅ **runtime current_phase 동기 (`"P4"`)** | (그대로) |
| approval_gate phase 호환 | P2 (`_PHASE_ORDER_EC`까지 P6) | ✅ P4 통과 검증 (회귀 테스트) | (그대로) |
| `WarningRegistry.load_global()` stub | `NotImplementedError` | (그대로 — owner_role BLOCK엔 불필요) | 별도 phase에서 평가 |
| rollback 수단 | `AF_SKIP_ESCALATION=1` 1단 | ✅ **4단** — env / current_phase / mode / never | (그대로 4단) |

> **P4a 첫 실행 동작**: 사용자가 P4a 빌드 설치 → `summarize()`가 yaml에서 `current_phase: "P4"` 로드 → P4 rule(`owner_role_mismatch`, `evidence_quality_warn`)이 evaluate 진입 → mode=observation으로 분기 → 임계 도달 시 `block=False severity="block_candidate" reason="observation_threshold_met"` / 미달 시 `block=False severity="warn" reason="observation_below_threshold"` decision 산출 → `_decision.md`에 "block_candidate (관측 중)" 또는 "warn (임계 미달)" 보고 → **빌드 차단 0건**, 사용자에게 가시화만 발생. P4b가 mode를 `enforce`로 toggle해야 실제 BLOCK 시작.

---

## §1 문제 — 왜 "yaml 한 줄"이 아닌가

### 1.1 baseline grep 사실 (실측, 2026-05-10)

| 파일:줄 | 사실 |
|---------|------|
| `core/warning_registry.py:215-217` | `compute_run_decision(summary, load_policy(), current_phase="P2")` — **하드코딩**. yaml/env/version 어디서도 안 옴 |
| `core/warning_registry.py:191-192` | `summary["escalation_phase"] = "P2"` — **하드코딩** |
| `core/escalation_decision_report.py:41` | `write_error_decision` payload `"escalation_phase": "P2"` — **하드코딩** |
| `core/escalation_decision_report.py:97` | `_write_decision_json` payload `"escalation_phase": decision.activate_phase` — 동적 (정상 경로) |
| `core/approval_gate.py:226` | `_PHASE_ORDER_EC = {"P1": 1, ..., "P6": 6}` — P4 이미 등록 |
| `core/approval_gate.py:227-238` | decision_phase > expected_phase → `decision_phase_mismatch` fail-closed. P4a에서 expected/decision 둘 다 P4여야 통과 |
| `core/escalation_evaluator.py:88-91` | `_is_phase_active(rule_phase, current)`: `rule_num >= 1 and rule_num <= cur_num`. current=P4면 P1/P2/P3/P4 rule 전부 활성 진입 |
| `core/escalation_evaluator.py:138-152` | `block_when` 매칭: `phase_match and count_match and repeat_match` → `block=True severity="block"`. **mode 분기 없음** |
| `core/escalation_evaluator.py:25` | `EscalationDecision.severity` docstring: `"warn" \| "block_candidate" \| "block"` — `block_candidate` 명목 슬롯만 존재, **현재 아무도 발화 안 함** (= P4a에서 처음 사용) |
| `config/escalation_policy.yaml:1-30` | `version: 0`. `current_phase` / `mode` 필드 없음 |
| `runtime/warnings/_index.json:11-16` | `owner_role_mismatch.activate_at: "P4"`, `measure_at: "P3"`, `mode: "observation"` — **여기엔 이미 mode 있음** (P3에서 도입). yaml과 분리됨 |
| `runtime/warnings/` jsonl | **0건** — owner_role_mismatch 측정 데이터 부재 (2026-05-10 검증) |

### 1.2 결과: 4개의 결정점이 묶여야 함

P4 진입 = `current_phase="P4"` 1줄 변경처럼 보이지만, 측정 데이터 0건 상태에서 그대로 토글하면 다음 부수효과 발생:

1. **owner_role_mismatch + evidence_quality_warn 둘 다 BLOCK 활성** — yaml `block_when` placeholder (`3` / `5`)가 비검증 임계로 enforce됨. P4b가 데이터 보고 결정해야 할 값을 **데이터 없이 enforce**.
2. **`escalation_phase` 마커 P2 잔존** — approval_gate가 `decision_phase_mismatch` (decision=P4 > expected=P2) fail-closed 발화. 회귀.
3. **rollback 1단(env)만 존재** — 잘못 활성된 rule 하나만 끄려 해도 `AF_SKIP_ESCALATION=1`이 e2e_command_missing(P2 enforce)도 같이 무력화.
4. **사용자 가시성 부재** — observation 단계라는 사실이 `_decision.md`에 안 보임. P4b 임계 결정에 필요한 "block-candidate 분포"를 사람이 추적 못함.

→ **이 4개를 한 PR로 묶는다**. 코드 변경은 작지만 **결정**이 핵심.

---

## §2 Scope (사용자 합의 — 2026-05-10)

### 2.1 포함 (한 PR)

1. **`config/escalation_policy.yaml`** — top-level `current_phase: "P4"` 필드 신설. P4 rule(`owner_role_mismatch`, `evidence_quality_warn`)에 `mode: "observation"` 필드 추가. e2e_command_missing(P2)는 `mode: "enforce"` 명시.
2. **`core/escalation_evaluator.py`**
   - `_PolicyRule`에 `mode: str = "enforce"` 필드 추가 (yaml 부재 시 enforce 기본 — 기존 동작 보존)
   - `load_policy()` 반환 dict에 `current_phase` top-level 키 보존
   - `evaluate()`에 mode 분기: `mode == "off"` → `reason="mode_off"` 즉시 반환 / `mode == "observation"` → exempt_when 검사 후 threshold 평가, 도달 시 `block=False severity="block_candidate" reason="observation_threshold_met"`, 미달 시 `block=False severity="warn" reason="observation_below_threshold"`. 분기 위치는 `false_positive_override` **직후** (override한 record는 mode 무관 warn 유지 — F5 결정)
   - 새 헬퍼 `read_current_phase(policy: dict) -> str`: yaml top-level `current_phase` 반환, 부재 시 `"P2"` fallback (호환)
3. **`core/warning_registry.py:215-217`**
   - `current_phase = read_current_phase(load_policy())` 동적 로드
   - `summary["escalation_phase"] = current_phase` 동적 (line 192)
4. **`core/escalation_decision_report.py:41`**
   - `write_error_decision`도 `current_phase` 인자 받아 동적 마커 작성 (caller가 yaml 로드 실패 시 fallback `"P2"` 전달)
5. **`Master_Blueprint.md`** §3.8 Warning Registry & Stats 갱신 + §12 변경 이력
6. **테스트** — §8 12 케이스 (v2: F5/F7 추가로 8 → 12)
7. **`version.py` / `install-af.ps1` / `af.spec`** 버전 bump (1.2.26 → **1.2.27**). install-af.ps1 8곳 일괄.

### 2.2 제외 (P4b 이상)

- `owner_role_mismatch.repeat_count_min` 최종값 결정 (P4b — `af warning-stats` 실측 후)
- `evidence_quality_warn.count_per_run_min` 최종값 결정 (P4b — 동일)
- `mode: observation → enforce` toggle (P4b)
- `WarningRegistry.load_global()` stub 해제 (별도 phase, owner_role BLOCK엔 불필요)
- `affected_phase_in` 기반 owner_role exempt 정책 (P4b 측정 결과 보고 결정)
- record-level override (현 _overrides.json은 rule-level — 입도 변경은 별도 설계)

### 2.3 명시적 비목표

- **P4a는 BLOCK을 발화하지 않는다.** 모든 P4 rule이 observation. mode toggle 전엔 빌드 동작 0 변화.
- **P4a는 새 측정 인프라를 추가하지 않는다.** P3에서 ship된 `af warning-stats`/`warning-export`로 충분. P4b는 그 출력만 보면 됨.

---

## §3 핵심 결정 — 옵션 비교 + 채택

### 3.1 결정 A: `current_phase` 단일 진실원 위치

| 옵션 | 설명 | 장점 | 단점 |
|------|------|------|------|
| A1 | hardcode 1줄 변경 (`warning_registry.py:216` `"P2"` → `"P4"`) | 가장 단순 | rollback = 코드 수정 + 재빌드. 운영자 권한 부재 |
| A2 | 환경 변수 `AF_ESCALATION_PHASE=P4` | 빌드 무관, 즉시 토글 | 단일 진실원 부재 (CI/local/사용자 PC 별로 분기). 부재 시 fallback도 결정 필요. yaml의 `activate_at`과 의미 중복 |
| A3 | `version.py` 모듈 상수 `ESCALATION_PHASE = "P4"` | 빌드 시 lock | rollback = rebuild |
| **A4 (채택)** | **`config/escalation_policy.yaml` top-level `current_phase: "P4"`** | yaml이 이미 escalation 단일 진실원 (`activate_at`/`block_when` 모두 여기). `load_policy()` 한 번에 모든 escalation state 결정. rollback = yaml 1줄 revert + 다음 summarize() 호출 시 즉시 반영 | 첫 도입 시 schema migration 필요 (default fallback `"P2"`로 하위 호환) |

**근거**: yaml이 이미 escalation 정책의 단일 진실원이고, 여기에 `current_phase`를 두면 `load_policy()` 한 번 호출로 모든 평가 입력이 결정된다. env는 일회성 우회용으로 보존(`AF_SKIP_ESCALATION`).

**fallback 정책**: yaml에 `current_phase` 키 부재 시 `"P2"` (현 하드코딩 값) — 기존 P2 빌드와 100% 호환. 미설정 워크스페이스가 의도치 않게 P4로 점프하는 회귀 차단.

### 3.2 결정 B: rule-level `mode` 필드 도입

P4a 본질은 **"phase는 P4지만 BLOCK은 안 한다"**. 이를 표현할 메커니즘 옵션:

| 옵션 | 설명 | 장점 | 단점 |
|------|------|------|------|
| B1 | yaml `block_when`을 도달 불가능한 큰 값으로 (`repeat_count_min: 999999`) | 코드 변경 0 | 의도 불명. 회의록 없이 보면 placeholder처럼 보임. 임계 결정 후 값 변경할 때 "원래 999999였음"이 노이즈로 남음 |
| B2 | yaml에 `enabled: false` rule-level flag | 단순 | "비활성"과 "관측 중"의 구분 없음. block_candidate 보고 못 함 |
| **B3 (채택)** | **`mode: "observation" \| "enforce" \| "off"` 필드** (default = `"enforce"`로 하위 호환) | (1) `_index.json`이 이미 같은 단어 사용 — schema 일관성. (2) observation 의도가 yaml에 그대로 표현됨. (3) evaluate가 `block_candidate` severity 발화 — 사용자에게 "곧 BLOCK 됨" 가시화. (4) toggle 1줄 (P4b가 `observation → enforce`만 바꾸면 enforce 시작) | rule schema에 1 필드 추가 |
| B4 | `evaluate()` 호출자에 mode 인자 | 정책이 yaml 떠남 | 단일 진실원 깨짐 |

**채택 근거**: B3는 `runtime/warnings/_index.json` (P3 v4에서 이미 도입한 `owner_role_mismatch.mode: "observation"`)과 같은 단어를 yaml에 미러링. **owner_role mode는 두 파일에서 동일하게 읽힘**. P4b가 단일 yaml 키 toggle만으로 enforce 시작.

> **`_index.json` 동기 시간 갭 (F2/F3)**: 현재 `runtime/warnings/_index.json` line 18-21의 `evidence_quality_warn`은 mode 필드 없음 (P3 v4에서 owner_role만 도입). P4a는 yaml v1에서 evidence_quality에도 `mode: observation` 추가하지만 `_index.json` 동기는 **P4b 책임으로 미룸** (§11). 두 파일 의미 동기는 P4b mode toggle PR에서 한 번에 처리 — 표면 불일치는 의도된 2단계 schema sync.

**default = `"enforce"`** 근거: 기존 yaml (P2까지) 어떤 rule도 `mode` 키를 갖지 않음. fallback이 enforce여야 e2e_command_missing(P2)이 자동으로 enforce 유지. observation은 명시적 opt-in.

**`"off"` 모드**: P4a에서 도입은 하지만 어떤 rule도 사용 안 함. `mode: never`(activate_at: never와 의미 중복) 회피용 reserved word. P4b 이후 임시 비활성 필요 시 사용 (e.g., 데이터 오염 발견 시 yaml 1줄로 stop).

### 3.3 결정 C: `escalation_phase` 마커 동적화

현재 `summary["escalation_phase"] = "P2"` (warning_registry.py:192) / `write_error_decision` payload `"P2"` (escalation_decision_report.py:41) 하드코딩. P4 전환 후 그대로 두면 approval_gate `decision_phase_mismatch` fail-closed 회귀.

**채택**: 두 곳 모두 `current_phase`(yaml에서 로드)로 치환. `write_error_decision`은 caller(`warning_registry.summarize`의 except 블록)에서 `current_phase` 인자 전달. yaml 자체 로드 실패 시 `"P2"` fallback 명시 — fail-closed 보존.

**approval_gate 변경 없음**: `_PHASE_ORDER_EC`에 P4 이미 등록(line 226). expected_phase = `summary["escalation_phase"]`, decision_phase = `_decision.json["escalation_phase"]` 둘 다 yaml current_phase에서 와야 하므로 동기화는 자동.

### 3.4 결정 D: 부수활성 rule 처리 (evidence_quality_warn)

current_phase=P4 전환 시 evidence_quality_warn(activate_at=P4)도 evaluate 진입. 그 임계 `count_per_run_min: 5`도 measurement 데이터 0건 상태에서 결정된 placeholder.

**채택**: **evidence_quality_warn도 `mode: "observation"`으로 시작**. P4a 범위에 같이 포함. owner_role_mismatch와 동일 절차 (P4b가 측정 데이터 보고 enforce toggle).

→ P4a 진입 시 P4 rule **전부** observation. BLOCK 0건 보장.

> **`_index.json` 동기는 P4b**: 위 §3.2 노트와 동일 — P4a는 yaml만 갱신, `runtime/warnings/_index.json`의 evidence_quality_warn `mode` 필드 추가는 P4b mode toggle PR에서 일괄 처리 (§11).

### 3.5 결정 E: rollback 4단 절차

| 수단 | 트리거 | 효과 | 회복 시간 |
|------|--------|------|-----------|
| 1. 환경변수 | `AF_SKIP_ESCALATION=1` | 모든 escalation 우회 (decision 읽기 자체 skip) | 즉시 |
| 2. yaml `current_phase` 강등 | `current_phase: "P3"` (또는 `"P2"`) | P4 rule 전부 inactive_phase로 하강. 평가 자체 안 함 | 다음 summarize() (즉시) |
| 3. yaml rule mode | `mode: "off"` | 특정 rule만 즉시 무력화 (다른 rule 영향 없음) | 다음 summarize() (즉시) |
| 4. yaml `activate_at: never` | rule 영구 비활성 | rule 자체가 평가 진입 안 함 | 다음 summarize() (즉시) |

**입도**: 1번 = 워크스페이스 전체 (긴급), 2번 = phase 전체 (회귀 발견), 3번 = rule 단위 (잡신호 격리), 4번 = 영구 (deprecation).

**P4b가 enforce toggle 후 잡신호 폭증 발견 시 권장 경로**: 3번(`mode: observation` 복귀) → 측정 재개 → 임계 재조정.

---

## §4 yaml schema 변경 (v0 → v1, in-place)

```yaml
# escalation_policy.yaml — v1 (P4a)
# 변경: top-level `current_phase` 신설, rule별 `mode` 옵션 필드.
# 호환: current_phase 부재 → "P2" fallback / mode 부재 → "enforce" fallback.
version: 1                  # ← bump
current_phase: "P4"         # ← 신설: P4a 진입 (BLOCK은 mode로 차단)

rules:
  - rule_id: e2e_command_missing
    activate_at: P2
    mode: "enforce"         # ← 명시 (default와 동일하지만 명시적 의도 표현)
    block_when:
      affected_phase_in: [build, integrate, code_review, cross_validate, verify]
      count_per_run_min: 1
    exempt_when:
      affected_phase_in: [scope]
    rationale: "build 이후 단계에서는 e2e 검증 명령이 필수. P2부터 enforce."

  - rule_id: owner_role_mismatch
    activate_at: P4
    mode: "observation"     # ← P4a: 평가 진입하되 BLOCK 미발생
    block_when:
      repeat_count_min: 3   # placeholder — P4b가 P3 measurement 데이터로 확정
    rationale: "P3 measurement 후 임계 결정 (P4b). P4a는 observation으로 block-candidate 분포 가시화만."

  - rule_id: evidence_quality_warn
    activate_at: P4
    mode: "observation"     # ← P4a: 동일
    block_when:
      count_per_run_min: 5  # placeholder — P4b가 결정
    rationale: "근거 부족 누적 임계. P4b가 측정 후 결정."

  - rule_id: plan_verifier_warn
    activate_at: never
    rationale: "plan_verifier score는 refine 루프로 보정 가능 — escalation 보류"
```

**migration 안전성**:
- `version: 0 → 1` bump는 reader가 검증하지 않음 (현 `load_policy()` 무조건 yaml.safe_load) — 회귀 없음
- 기존 v0 yaml을 가진 환경 (커스텀 fork 등)에서 P4a 코드 실행 시: `current_phase` 부재 → `"P2"` fallback / `mode` 부재 → `"enforce"` fallback → **기존 P2 동작 100% 보존**

---

## §5 evaluator 코드 변경 명세

### 5.1 `_PolicyRule` 필드 추가

```python
@dataclass
class _PolicyRule:
    rule_id: str
    activate_at: str = "never"
    mode: str = "enforce"           # ← 신설. 허용: "enforce" | "observation" | "off"
    block_when: dict | None = None
    exempt_when: dict | None = None
    rationale: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "_PolicyRule":
        bw = d.get("block_when")
        if bw is not None and not isinstance(bw, dict):
            raise ValueError(...)
        mode = d.get("mode", "enforce")
        if mode not in ("enforce", "observation", "off"):
            raise ValueError(
                f"mode must be enforce|observation|off, got {mode!r}"
            )
        return cls(
            rule_id=d["rule_id"],
            activate_at=d.get("activate_at", "never"),
            mode=mode,
            block_when=bw,
            exempt_when=d.get("exempt_when"),
            rationale=d.get("rationale", ""),
        )
```

### 5.2 `read_current_phase()` 신헬퍼

```python
def read_current_phase(policy: dict) -> str:
    """yaml top-level current_phase 반환. 부재/잘못된 값 → "P2" fallback (호환)."""
    cp = policy.get("current_phase")
    if cp in _PHASE_ORDER_ESCALATION and cp not in ("never",):
        return cp
    return "P2"
```

**fallback 근거**: 잘못된 값(예: `"foo"`)도 `"P2"` 강등. fail-safe — phase 폭주(P9 등) 차단.

### 5.3 `evaluate()` mode 분기 — 위치 결정

mode 분기를 **어디에 끼우느냐**가 핵심:

| 옵션 | 위치 | 결과 |
|------|------|------|
| 5.3-A | `rule_not_active` 직후, `inactive_phase` 직전 | activate_at: never 면 mode 무관 rule_not_active. 그 외 phase 미달도 inactive_phase 유지 |
| 5.3-B (초안 v1) | `inactive_phase` 통과 직후, `false_positive_override` 직전 | **결함 발견 (cross-review F5)**: override한 record도 mode 무관 block_candidate로 보고 → P4b candidate count 데이터 오염 |
| **5.3-C (채택, v2)** | **`false_positive_override` 통과 직후, `exempt_when` 검사 앞단** | override한 record는 mode 무관 warn 유지 (override semantics 보존). exempt_when은 observation 경로에서도 적용 (P4b가 owner_role에 affected_phase exempt 추가할 가능성 있음 — 일관) |
| 5.3-D | `block_when` 매칭 후 `block=True` 직전에 mode==observation 시 block→False 전환 | exempt/threshold 로직과 섞임. severity = "block" → "block_candidate" 강제 변환 — 의미가 모호 |

**채택 근거 (v2 갱신)**:
- override는 "이 rule이 이 워크스페이스에서 false-positive임"을 사용자가 명시적으로 선언한 것. mode와 직교하는 결정 — observation에서 override 무시하면 P4b가 `_decision.json` candidate 분포로 임계 결정할 때 false-positive까지 합산되어 임계가 인위적으로 높게 보임 (Cross-review F5).
- exempt_when을 observation 경로에서도 적용해야 enforce 전환 시 동일한 면제 정책이 적용됨 — toggle 1줄로 enforce 시작 가능.

```python
def evaluate(record, *, policy=None, current_phase="P2") -> EscalationDecision:
    if policy is None:
        policy = load_policy()
    rule = _find_rule(policy, record.rule_id)

    if rule is None or rule.activate_at == "never":
        return EscalationDecision(
            block=False, severity="warn", reason="rule_not_active", ...
        )

    if not _is_phase_active(rule.activate_at, current=current_phase):
        return EscalationDecision(
            block=False, severity="warn", reason="inactive_phase", ...
        )

    if record.false_positive_override:
        return EscalationDecision(
            block=False, severity="warn", reason="false_positive_override", ...
        )

    # ---- P4a 신규: mode 분기 (override 직후, exempt/threshold 앞단) ----
    if rule.mode == "off":
        return EscalationDecision(
            block=False, severity="warn", reason="mode_off",
            rule_id=record.rule_id, activate_at=rule.activate_at,
        )
    if rule.mode == "observation":
        # exempt_when 먼저 (enforce 경로와 일관)
        if rule.exempt_when:
            ex_phases = rule.exempt_when.get("affected_phase_in") or []
            if record.affected_phase in ex_phases:
                return EscalationDecision(
                    block=False, severity="warn",
                    reason=f"observation_exempt_phase:{record.affected_phase}",
                    rule_id=record.rule_id, activate_at=rule.activate_at,
                )
        # threshold 평가하여 candidate 분포 가시화 (선택적 — P4b가 _decision.json에서 즉시 추적 가능)
        bw = rule.block_when or {}
        cond_phase = bw.get("affected_phase_in")
        cond_count = bw.get("count_per_run_min", 1)
        cond_repeat = bw.get("repeat_count_min", 0)
        phase_match = (cond_phase is None) or (record.affected_phase in cond_phase)
        count_match = record.count >= cond_count
        repeat_match = record.repeat_count >= cond_repeat
        if phase_match and count_match and repeat_match:
            return EscalationDecision(
                block=False, severity="block_candidate",
                reason="observation_threshold_met",
                rule_id=record.rule_id, activate_at=rule.activate_at,
            )
        return EscalationDecision(
            block=False, severity="warn",
            reason="observation_below_threshold",
            rule_id=record.rule_id, activate_at=rule.activate_at,
        )
    # ---- 이하 enforce 경로 (기존 동작) ----

    # ... exempt_when ...
    # ... block_when ...
```

**왜 observation에서도 threshold 평가하나 (v2 표현 보완)**: P4b 임계 결정의 1차 데이터는 `af warning-stats` 의 `by_per_record_count` 분포 (P3 §3.3) — `core/warning_stats.py:227-330`에서 jsonl 직접 스캔. `_decision.json` candidate 분포는 **선택적 가시화 (필수 아님)**. 그러나 observation에서도 threshold 평가하면 사용자가 `_decision.md`만 봐도 "어느 slug가 임계 도달했는지" 즉시 추적 가능 — P4b enforce toggle 전 사용자 신호로 가치 있음. observation = "본다", off = "안 본다".

### 5.4 `compute_run_decision` 변경 (cross-review F9/F11 명확화)

`compute_run_decision` **함수 자체**의 시그니처/내부 로직 변경 0줄. observation severity → blocking 카운터에서 제외는 이미 `if d.block: blocking.append(...)` 로직이 block=False면 자동 제외 (line 196).

**다만 다음 변경은 caller/dependency 측에서 필수 — §5.4 변경 0이 caller 변경 0이라는 뜻 아님**:
- `_PolicyRule.mode` 필드 추가 (§5.1)
- `evaluate()` mode 분기 (§5.3)
- `warning_registry.summarize()` 호출자 변경 (§7 #3): `current_phase = read_current_phase(policy)` 동적 로드
- `write_error_decision` caller 변경 (§7 #5): `current_phase=` kwarg 전달

→ §5.4의 "변경 0"은 `compute_run_decision` 함수 본문에 대한 진술. 의존하는 함수와 caller는 별도 명세를 따른다.

### 5.5 `EscalationDecision.severity` 활성 슬롯 갱신

기존 docstring `"warn" | "block_candidate" | "block"`은 명목만. P4a 후 실제 발화:

| severity | 발화 reason | block | 의미 |
|----------|-------------|-------|------|
| `"warn"` | rule_not_active / inactive_phase / mode_off / false_positive_override / exempt_phase / below_threshold / observation_below_threshold | False | 평가 결과 무해 |
| `"block_candidate"` | **observation_threshold_met** (P4a 신설) | False | 관측 중, enforce 전환 시 BLOCK 예정 |
| `"block"` | threshold_met | True | enforce 발화 |

---

## §6 decision path 회귀 — 흐름도

```
project_pipeline._record_ledger_outcomes (line 1331)
  └─ detect_owner_drift (project_task_board.py:227)
        └─ WarningRegistry.record(rule_id="owner_role_mismatch", ...)
             └─ jsonl append (runtime/warnings/<slug>/owner_role_mismatch.jsonl)

project_pipeline (next FSA tick)
  └─ WarningRegistry.summarize()
        ├─ policy = load_policy()                                            ← single-load (F12)
        ├─ current_phase = read_current_phase(policy)                        ← P4a 변경
        ├─ _build_summary → by_rule[owner_role_mismatch] = {count, repeat_count_max, by_phase, ...}
        ├─ summary["escalation_phase"] = current_phase                       ← P4a 변경 (같은 객체)
        ├─ _summary.json atomic write
        └─ compute_run_decision(summary, policy, current_phase=current_phase)  ← 같은 policy/phase
              └─ for each rule in by_rule:
                    └─ evaluate(virtual_record, policy=policy, current_phase=current_phase)
                          ├─ false_positive_override 우선                    ← override semantics 보존 (F5)
                          └─ mode="observation" → block_candidate / warn      ← P4a 신경로
              └─ RunDecision(block=False, blocking_rules=[], rule_decisions=[...])
              └─ write_decision_report → _decision.json/.md (escalation_phase=P4)

project_pipeline (apply_edits 호출 시, line 1277)
  └─ approval_gate.read_block_decision()
        ├─ AF_SKIP_ESCALATION=1 → (False, None)                              ← rollback 1단
        ├─ summary.escalation_phase=P4, decision.escalation_phase=P4 → 통과   ← P4a 회귀 검증 대상
        └─ d["block"] == False → (False, d) → 빌드 진행
```

**회귀 항목**:
1. P4 진입 후 `escalation_phase` 마커 양쪽 P4 동기 (`decision_phase_mismatch` 미발화)
2. observation rule이 BLOCK 발화 안 함 (read_block_decision 결과 (False, _))
3. enforce rule (e2e_command_missing) 동작 무변화 — 회귀 차단

---

## §7 변경 파일 목록 (의존성 순)

| # | 파일 | 변경 | 의존 |
|---|------|------|------|
| 1 | `core/escalation_evaluator.py` | `_PolicyRule.mode` 필드 + `read_current_phase()` 헬퍼 + `evaluate()` mode 분기 (~30줄 추가) | (없음) |
| 2 | `tests/test_escalation_evaluator_p4a.py` | 신규 5 케이스 (§8.1) — observation/off/enforce + read_current_phase fallback | #1 |
| 3 | `core/warning_registry.py:215-217, 192` | `current_phase = read_current_phase(load_policy())` 동적 로드 + `summary["escalation_phase"] = current_phase`. import 추가. | #1 |
| 4 | `core/escalation_decision_report.py:28-50` | `write_error_decision`에 `current_phase: str = "P2"` kwarg 추가 + payload `escalation_phase` 동적화 | #1 |
| 5 | `core/warning_registry.py:226-236` | `write_error_decision` 호출 2곳에 `current_phase=current_phase` kwarg 전달 (yaml load 실패 시 fallback "P2") | #3, #4 |
| 6 | `tests/test_warning_registry_p4a.py` | 신규 3 케이스 (§8.2) — escalation_phase=P4 마커 / decision_report 일관성 / yaml 부재 시 P2 fallback | #3, #5 |
| 7 | `config/escalation_policy.yaml` | `version: 0 → 1`, `current_phase: "P4"` 신설, e2e/owner_role/evidence_quality에 `mode` 명시 | #1~#6 (코드 준비 후 yaml flip) |
| 8 | `tests/test_escalation_policy_yaml_p4a.py` | 신규 2 케이스 (§8.3) — yaml schema 검증 / migration 호환 | #7 |
| 9 | `af.spec` + `version.py` + `install-af.ps1` | version `1.2.27`. install-af.ps1 8곳 일괄 (`grep -c '1\.2\.26' install-af.ps1` = 0 사후 검증) | (마지막) |
| 10 | `Master_Blueprint.md` | §3.8 Warning Registry & Stats 갱신 (current_phase 단일 진실원, mode 필드, severity 활성 슬롯) + §12 변경 이력 | 모든 코드 변경 후 |

**총 신규 코드 ~90줄 (v2: exempt_when 처리 추가), 신규 테스트 12 케이스, yaml 4 줄.**

---

## §8 테스트 케이스

### 8.1 `tests/test_escalation_evaluator_p4a.py` (7 케이스 — v2: F5/F7 추가)

1. `test_evaluate_observation_below_threshold_returns_warn` — mode=observation, repeat_count=1 < repeat_count_min=3 → `block=False severity="warn" reason="observation_below_threshold"`
2. `test_evaluate_observation_threshold_met_returns_block_candidate` — mode=observation, repeat_count=5 ≥ 3 → `block=False severity="block_candidate" reason="observation_threshold_met"`
3. `test_evaluate_off_mode_skips_threshold` — mode=off, repeat_count=999 → `block=False severity="warn" reason="mode_off"` (threshold 평가 없음)
4. `test_evaluate_enforce_mode_default_when_field_missing` — `mode` 키 부재 yaml → `_PolicyRule.mode == "enforce"`, threshold 도달 시 `block=True` (P2 호환)
5. `test_read_current_phase_fallback_p2_when_missing_or_invalid` — `{}` / `{"current_phase": "P9"}` / `{"current_phase": "never"}` → 모두 `"P2"` 반환
6. `test_observation_respects_false_positive_override` (F5 회귀) — mode=observation, `false_positive_override=True`, repeat_count=999 → `block=False severity="warn" reason="false_positive_override"` (mode 분기 진입 없음 — override가 우선)
7. `test_e2e_command_missing_blocks_under_p4_current_phase` (F7 회귀) — yaml v1 `current_phase: "P4"` + e2e_command_missing(`activate_at: P2 mode: enforce`) + record(`affected_phase: "build" count: 1`) → `block=True severity="block" reason="threshold_met"`. **P4 phase 전환이 P2 enforce를 깨지 않음을 보장하는 핵심 가드**.

### 8.2 `tests/test_warning_registry_p4a.py` (3 케이스)

6. `test_summarize_writes_escalation_phase_from_yaml` — yaml `current_phase: "P4"` → `_summary.json["escalation_phase"] == "P4"` + `_decision.json["escalation_phase"] == "P4"`
7. `test_summarize_falls_back_to_p2_when_yaml_missing_phase` — `{"version": 1, "rules": []}` (current_phase 부재) → 양쪽 `"P2"`
8. `test_write_error_decision_uses_dynamic_phase` — yaml `current_phase: "P4"` 로 로드 후 `_build_summary`에서 강제 예외 → `_decision.json["escalation_phase"] == "P4"` (error path도 동적)

### 8.3 `tests/test_escalation_policy_yaml_p4a.py` (2 케이스)

9. `test_yaml_v1_loads_current_phase_and_modes` — 실제 `config/escalation_policy.yaml` 파일 로드 → `current_phase == "P4"`, owner_role/evidence_quality `mode == "observation"`, e2e_command_missing `mode == "enforce"`
10. `test_yaml_invalid_mode_raises` — `mode: "garbage"` rule → `_PolicyRule.from_dict` `ValueError` raise (validator 작동)

### 8.4 회귀 (기존 테스트 통과 확인)

- `tests/test_decision_report.py` — block decision 작성 path. mode 미설정 fixture는 enforce default로 동작해야 함
- `tests/test_warning_registry_*.py` (P2 ledger 회귀) — e2e_command_missing 여전히 enforce
- `tests/test_approval_gate*.py` — `_PHASE_ORDER_EC` 4 통과, `decision_phase_mismatch` 미발화

### 8.5 frozen 빌드 smoke

- `python build_exe.py` → `dist/af-1.2.27.zip` 생성
- 임시 워크스페이스에서 `dist/af-1.2.27/af warning-stats --workspace . --rule owner_role_mismatch` 실행 → `escalation_phase: "P4"` 마커 확인 (또는 `_decision.md` block: false / blocking_rules: 없음)
- host OS 기준 1개만 (P3 §8.4 패턴 follow)

---

## §9 baseline grep 의무 (구현 진입 시 1차 검증)

| 파일:줄 | 검증 사실 | 검증 방법 |
|---------|-----------|-----------|
| `core/warning_registry.py:215-217` | `current_phase="P2"` 하드코딩 1곳 | `grep -n 'current_phase="P2"' core/warning_registry.py` = 1줄 |
| `core/warning_registry.py:192` | `summary["escalation_phase"] = "P2"` 하드코딩 1곳 | `grep -n '"escalation_phase"\] = "P2"' core/warning_registry.py` = 1줄 |
| `core/warning_registry.py:283` | `_write_minimal_block_decision` payload `"escalation_phase": "P2"` — **별도 처리 필요** (warning_registry 자체에서 fallback 작성, yaml 의존 안 함) | `grep -n '"escalation_phase": "P2"' core/warning_registry.py` = 1줄 |
| `core/escalation_decision_report.py:41` | `write_error_decision` payload `"escalation_phase": "P2"` 1곳 | `grep -n '"escalation_phase": "P2"' core/escalation_decision_report.py` = 1줄 |
| `core/escalation_decision_report.py:97` | `_write_decision_json` payload `"escalation_phase": decision.activate_phase` (이미 동적) | grep으로 확인, 변경 없음 |
| `core/approval_gate.py:226` | `_PHASE_ORDER_EC` P4 등록 | `grep -n '"P4": 4' core/approval_gate.py` ≥ 1줄 |
| `core/escalation_evaluator.py:25` | `severity` docstring `"block_candidate"` 명목 슬롯 존재 | grep 확인 |
| `config/escalation_policy.yaml:1-30` | `current_phase` / `mode` 키 부재 (변경 전) | `grep -E '^current_phase\|mode:' config/escalation_policy.yaml` = 0줄 |
| `runtime/warnings/_index.json:11-16` | `owner_role_mismatch.mode == "observation"` 이미 존재 | jq로 확인 |
| `runtime/warnings/` jsonl | 측정 데이터 0건 (P4b 전제) | `find runtime/warnings -name '*.jsonl'` = 0줄 |
| `core/warning_registry.py:240-242 load_global()` | `NotImplementedError` 유지 — **import 금지, 호출 금지** | grep 확인 |

**`_write_minimal_block_decision` 처리 결정**: 이 헬퍼는 `write_error_decision` import 자체가 실패한 극단 케이스용. yaml 로드도 신뢰 못하는 상태 → `"P2"` fallback 그대로 유지(가장 안전한 floor). approval_gate가 `decision_phase_num <= expected_phase_num` 순방향 호환이므로 `expected=P4 + decision=P2`는 통과 (line 231 `decision_phase_num > expected_phase_num` 만 fail).

---

## §10 핵심 시맨틱 결정 (구현자가 임의로 변경 금지)

1. **`current_phase`는 yaml 단일 진실원**. env/code hardcode 금지. `read_current_phase()` 한 함수만이 진입점. **호출자(`warning_registry.summarize`)는 `policy = load_policy()` 한 번 호출 후 `current_phase = read_current_phase(policy)` + `compute_run_decision(summary, policy, current_phase=current_phase)` 를 같은 policy 객체로 전달** — split read 금지 (cross-review F12). yaml 변경은 사용자 수동 수정이라 race 위험은 없으나 명시적 single-load 패턴이 의도 보존.
2. **mode 분기는 phase 활성 직후, false_positive_override 앞단**. 순서 변경 금지 (의미 달라짐).
3. **observation은 threshold도 평가**. block_candidate severity 발화 — P4b 데이터 가시화에 필수.
4. **mode default = "enforce"**. yaml 부재 시 enforce. 기존 P2 동작 100% 보존.
5. **`current_phase` fallback = "P2"**. yaml 부재/invalid 시 P2. P4 폭주 차단.
6. **`_write_minimal_block_decision` (`warning_registry.py:283`)는 "P2" 하드코딩 유지**. yaml 로드 실패 + write_error_decision import 실패 더블 fail 케이스의 floor — `expected_phase_num >= decision_phase_num` 순방향 호환에 의존.
7. **mode 값 검증**: `"enforce"|"observation"|"off"` 외 raise. yaml 오타 즉시 노출.
8. **`activate_at: never` rule은 mode 무관 rule_not_active**. observation으로 우회 못 함 — never가 강함.
9. **P4a는 BLOCK 발화 0건 보장**. yaml에 `enforce` 모드의 P4 rule이 들어 있으면 안 됨 (테스트 9가 회귀 가드).
10. **버전 bump 1.2.26 → 1.2.27**. install-af.ps1 8곳, af.spec hiddenimports 변경 없음(신규 모듈 0).

---

## §11 P4b 인계 사항 (출력 → 입력)

P4a 산출물:
- `_decision.json`/`_decision.md`에 `block_candidate` severity가 발화되기 시작
- `af warning-stats --rule owner_role_mismatch` 의 `distribution.by_per_record_count` (P3 §3.3) 가 충분히 수집됨

P4b 결정 입력:
| 데이터 | 출처 | 결정 |
|--------|------|------|
| `owner_role_mismatch` `repeat_count` 분포 (워크스페이스 전체) | `af warning-stats` | `repeat_count_min` 임계 후보 (예: p95) |
| `_decision.json` rule_decisions 중 `severity=="block_candidate"` 빈도 | `runtime/warnings/<slug>/_decision.json` 집계 | 임계 도달 빌드 비율. 너무 높으면 임계 상향 |
| `_overrides.json` (false-positive 누적) | `runtime/warnings/<slug>/_overrides.json` | 임계 무관 오탐 — affected_phase exempt 정책 후보 |
| `evidence_quality_warn` 분포 | `af warning-stats --rule evidence_quality_warn` | `count_per_run_min` 결정 |

P4b PR 변경 (예상):
- `config/escalation_policy.yaml` — owner_role_mismatch / evidence_quality_warn `mode: "observation" → "enforce"` toggle
- yaml `repeat_count_min` / `count_per_run_min` 측정 기반 값으로 갱신
- `runtime/warnings/_index.json` — `owner_role_mismatch.mode: "observation" → "enforce"` 동기 + **`evidence_quality_warn`에 `mode` 필드 신규 추가** (P4a에서 yaml만 갱신, _index.json은 P4b 일괄 처리 — F2/F3 시간 갭 해소)
- 관측 기간 명시 회의록 (P4b 별도 doc)

P4b가 mode toggle만으로 enforce 시작 가능 — **P4a가 이미 모든 기계장치를 깔아 둠**.

---

## §12 변경 이력

- v1 (2026-05-10) — 초안. 4 결정점(current_phase 단일 진실원 / rule mode / escalation_phase 동적화 / rollback 4단). P4b 분리 명시.
