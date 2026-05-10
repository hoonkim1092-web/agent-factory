# Design Review: 2026-05-10-p4a-owner-lint-activation-mechanics-design

> Source: docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md
> Date: 2026-05-10 21:13
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

두 리뷰어가 독립적으로 **observation mode 분기 위치 결함**을 동일하게 지적함 (High). 즉시 BLOCK 발화는 없으나(P4 rule에 현재 override/exempt 미적용), **P4b enforce toggle 전까지 반드시 해소되어야 하는 설계 시맨틱 결함**. 그 외 다수의 Medium/Low가 누적됨. 구현 진입 전 §5.3 분기 위치 + §8 테스트 정합 + §2.1 변경 파일 목록 정정 필요.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [High] Observation mode 분기가 false_positive_override·exempt_when 앞 — operator override/exempt 무력화
- **Critic** (#1, #2): mode 분기를 override/exempt 앞에 두면 (a) 운영자가 `warning-override`로 표시한 record까지 observation threshold 평가 포함 → P4b 입력 데이터 오염, (b) exempt_when 가진 rule(향후 e2e_command_missing observation toggle 등)이 exempt 정책 silently 무력화. `core/escalation_evaluator.py:122-149` 실측 검증.
- **Cross** (#2): 동일 결함 — observation rule은 override/exempt 통과 전 threshold 평가됨. §5.5 표의 `false_positive_override / exempt_phase` warn reason이 observation rule에서 도달 불가능.
- **Judgment**: 두 리뷰어가 독립 지적 + 코드 라인 (`escalation_evaluator.py:122,128`) 직접 인용 + observation 시맨틱의 근본 문제 → 강한 ACCEPT.
- **Action Required**:
  - §5.3 분기 순서를 `rule_not_active → inactive_phase → false_positive_override → exempt_when → mode 분기 → block_when 평가`로 변경 (`block_when` 매칭 시 mode==observation이면 block=False severity=block_candidate).
  - §10 시맨틱 결정 #2 정정.
  - §0/§3.2에 observation 시맨틱 정의 1문장 추가: *"observation = BLOCK 효력만 차단, 나머지 게이트(override/exempt)는 enforce와 동일 평가"*.
  - §8 테스트에 "observation + override → reason=false_positive_override", "observation + exempt phase → reason=exempt_phase" 케이스 추가.

#### 2. [ACCEPT] [Medium] Error-path 테스트와 minimal fallback "P2" 시맨틱 충돌
- **Critic** (#3): `_write_minimal_block_decision`의 "P2" floor가 정상 경로 P4 마커와 한 워크스페이스에 혼재 — 운영자 진단 혼란.
- **Cross** (#1): §8.2 테스트 8 (`_build_summary` 강제 예외 → `_decision.json["escalation_phase"]=="P4"`)는 §10 #6 (minimal fallback P2 유지) 시맨틱과 직접 충돌. `_build_summary` 실패는 `_write_minimal_block_decision()` 경로로 진입 (`warning_registry.py:181 → 283` 검증).
- **Judgment**: Cross가 더 구체적(테스트-스펙 직접 모순). Critic의 "P2/P4 혼재"는 동일 결함의 운영자 가시성 측면.
- **Action Required**: 둘 중 택일 —
  - (a) §8.2 테스트 8을 `compute_run_decision()` 또는 `write_decision_report()` 강제 예외로 변경 (P2 fallback 그대로),
  - (b) §10 #6 철회 + `_write_minimal_block_decision`에 `current_phase` kwarg 추가하고 caller가 yaml 로드 성공 시 P4 전달, yaml 로드 자체 실패만 P2 fallback. **권장: (b)** — 정상 yaml 환경에서 marker 일관성 보장.

#### 3. [ACCEPT] [Medium] `read_current_phase` policy shape validation + dead `"never"` 가드
- **Critic** (#4): `_PHASE_ORDER_ESCALATION`에 `"never"` 키 부재(`escalation_evaluator.py:17` 검증) — `cp not in ("never",)` dead code. 또 module-private 상수 외부 직접 검사는 약한 결합.
- **Cross** (#3): top-level이 dict 아닌 경우(list/string)나 `rules`가 list 아닌 경우 `policy.get(...)` AttributeError로 fail-closed. `load_policy()`는 `safe_load()` 결과 raw 반환 (`escalation_evaluator.py:65,81` 검증).
- **Judgment**: 같은 함수의 다른 결함이라 한 항목으로 병합. 둘 다 코드 라인 기반.
- **Action Required**:
  - `evaluator`에 `is_valid_phase(name: str) -> bool` 공개 헬퍼 추가, `read_current_phase`는 이 헬퍼 사용. `"never"` 가드 제거.
  - `read_current_phase` 또는 `load_policy()` 계약에 "top-level non-dict는 RuntimeError raise (fail-closed config error), `current_phase` missing/invalid만 P2 fallback" 명시 + 테스트 추가.

#### 4. [ACCEPT] [Medium] §8.1 Test #5 — `read_current_phase` 정상 path 회귀 가드 부재
- **Critic** (#5): fallback case (`{}` / invalid)만 검증. `{"current_phase": "P3"}` → "P3" 같은 정상 path 회귀 가드 없음. 누군가 모든 입력을 P2로 강등하는 변경을 가해도 통과 — P4a→P4b mode toggle 시 yaml 변경 무력화 silent regression.
- **Cross**: 미언급.
- **Judgment**: Critic 단독이지만 증거 명확 (테스트 명세 직접 인용). silent regression 시나리오 구체적.
- **Action Required**: 테스트 5를 두 케이스로 분리 — `test_read_current_phase_returns_valid_phase_value` (P1~P6 각각) + `test_read_current_phase_fallback_p2_when_missing_or_invalid` (현 case).

#### 5. [ACCEPT] [Medium] yaml `mode` ↔ `_index.json` `mode` 동기화 책임 미정의
- **Critic** (#6): §3.1 "yaml이 escalation 단일 진실원" 주장과 §11 "_index.json mode 동기" 충돌. P4b가 yaml만 enforce로 바꾸고 _index.json 잊으면 불일치. 동기 책임자/검증 방법 미정의.
- **Cross**: 미언급.
- **Judgment**: Critic 단독이나 §3.1 vs §11 문서 내부 모순을 정확히 지적. 단일 진실원 주장의 정합성 문제.
- **Action Required**: 둘 중 택일 — (a) `_index.json.mode`를 yaml에서 derive된 read-only mirror로 강등 + summarize 시 매번 yaml mode로 덮어쓰기 명시 (권장), (b) §10에 시맨틱 결정 추가 — "yaml mode 변경 PR은 _index.json도 같은 커밋, pre-commit hook 검증".

#### 6. [ACCEPT] [Medium] Block-candidate 가시성 — summarize 자동 트리거 미정의
- **Cross** (#4): P4 producer callsites는 record만 호출하고 summarize 미호출. owner drift는 pipeline run 후 기록 — "다음 FSA tick"이 어떤 호출인지 구현자가 확정 어려움. `project_pipeline.py:769,1455` (record only) vs `work_item_generator.py:1173` (auto summarize) 검증.
- **Critic**: 미언급 ("Missing from Design"의 "P4a 첫 실행 timeline" 항목에 부분 중복).
- **Judgment**: Cross가 구체적 callsite 인용. 사용자 가시성(`_decision.md`)이 P4a 핵심 산출인데 발화 시점 불명확.
- **Action Required**: §2.1에 추가 — owner/evidence record 직후 best-effort `summarize(project_slug=...)` 호출 (최소안), 또는 §0에 "가시화는 다음 WIG 실행 / `af warning-summary` 수동 호출까지 지연" 명시 (사용자 기대치 조정).

#### 7. [ACCEPT] [Low] `af.spec` 버전 bump 항목 비실행 가능
- **Cross** (#5): 현재 `af.spec`에 버전 문자열 없음 (`af.spec:23` 검증) — §2.1의 "`af.spec` 버전 bump"는 구현자가 무엇을 바꿔야 할지 알 수 없음.
- **Critic**: 미언급.
- **Judgment**: 코드 직접 인용 — 명백.
- **Action Required**: §2.1에서 `af.spec`를 "변경 없음, `config/` datas 기존 포함 확인"으로 정정.

#### 8. [ACCEPT] [Low] install-af.ps1 occurrence 카운트 오기 (8 → 7)
- **Cross** (#6): 실제 `1.2.26` 발생은 7곳 — "8곳" 체크리스트 실패 유발.
- **Critic**: 미언급.
- **Judgment**: 사실 검증 명확.
- **Action Required**: §2.1 line 83에서 "8곳"을 "모든 `1.2.26` occurrence"로 변경, 사후 검증을 `rg -n '1\.2\.26' install-af.ps1 version.py`로 통일.

#### 9. [ACCEPT] [Low] §3.2 `mode: "off"` 도입 — YAGNI
- **Critic** (#7): P4a에서 사용하지 않는 값 추가 — Simplicity First 위반. 필요 시 yaml 1줄+검증 set 1단어로 즉시 도입 가능.
- **Cross**: 미언급.
- **Judgment**: CLAUDE.md Karpathy Rule 2 직접 적용. 정당성 약함("예약어"는 yaml에선 충돌 없음).
- **Action Required**: §3.2 결정 B에서 `"off"` 제거. P4a는 `mode: enforce | observation`만 도입. `"off"`는 P4b 잡신호 발견 시 같은 PR에서 도입.

#### 10. [ACCEPT] [Low] §6 흐름도에 override/exempt 분기 누락
- **Critic** (#8): 흐름도 line 354에 evaluate 내부 분기(override/exempt) 미표시 — #1 결함의 한 원인.
- **Cross**: 미언급 (#2에서 동일 영역 다른 측면).
- **Judgment**: #1 fix와 동시 반영 자연스러움.
- **Action Required**: §6 ASCII tree에 `rule_not_active? → inactive_phase? → false_positive_override? → exempt_phase? → mode? → block_when match? → severity` 명시.

---

### REJECTED

#### R1. [REJECT] `config/escalation_policy.yaml` packaging needs new af.spec entry
- **Source**: Cross (#7, self-rejected)
- **Original Finding**: frozen build에서 새 YAML 필드 누락 우려 — `af.spec` datas 변경 필요해 보임.
- **Rejection Reason**: `af.spec`이 이미 `config` 디렉터리 전체 패키징 (`af.spec:27` 검증). `load_policy()`는 `BASE_DIR/config/escalation_policy.yaml` 경로 사용 — 기존 entry로 자동 포함됨.

### HOLD

#### H1. [HOLD] [Low] Logging expectations for observation rollout
- **Cross** (#8): `_decision.md` 가시성은 다뤄지나 runtime log 미정의. 운영자가 decision 파일 안 보면 phase/mode 전환 silent.
- **Critic**: 미언급.
- **Judgment**: 양 옵션(log 추가 vs "파일 산출물만") 모두 합리적 — 작성자 의도 필요.
- **Question for Author**: `WarningRegistry.summarize()`에 phase/mode + block_candidate count 1줄 INFO 로그를 추가할지, 아니면 §0에 "observability is `_decision.json/.md` only; no runtime log added"를 명시할지?

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | observation mode 분기가 override/exempt 앞 | High | ACCEPT | Both |
| 2 | minimal fallback "P2" vs 테스트 시맨틱 충돌 | Medium | ACCEPT | Both |
| 3 | read_current_phase shape validation + dead 가드 | Medium | ACCEPT | Both |
| 4 | Test #5 정상 path 회귀 가드 부재 | Medium | ACCEPT | Critic |
| 5 | yaml mode ↔ _index.json mode 동기화 미정의 | Medium | ACCEPT | Critic |
| 6 | block-candidate summarize 자동 트리거 미정의 | Medium | ACCEPT | Cross |
| 7 | af.spec 버전 bump 비실행 가능 | Low | ACCEPT | Cross |
| 8 | install-af.ps1 occurrence count 8→7 | Low | ACCEPT | Cross |
| 9 | mode "off" YAGNI | Low | ACCEPT | Critic |
| 10 | §6 흐름도 override/exempt 분기 누락 | Low | ACCEPT | Critic |
| R1 | af.spec config datas 추가 필요 | Low | REJECT | Cross |
| H1 | observation rollout logging 정책 | Low | HOLD | Cross |

---

### Recommendations

구현 진입 전 다음을 설계문서에 반영:

1. **§5.3 분기 순서 재설계** (Finding #1) — `false_positive_override → exempt_when → mode 분기 → block_when` 순서. §10 시맨틱 결정 #2 동시 정정. §6 흐름도 분기 명시 (#10).
2. **§0 또는 §3.2에 observation 시맨틱 정의 추가** — *"observation = BLOCK 효력만 차단, override/exempt는 enforce와 동일 평가"*.
3. **§10 #6 철회 또는 §8.2 테스트 8 변경** (Finding #2) — `_write_minimal_block_decision`에 `current_phase` kwarg 추가 권장.
4. **§2.1 변경 파일 목록 정정** (#7, #8) — `af.spec` 제거(또는 datas 확인만), install 카운트를 "모든 occurrence"로 변경.
5. **§8 테스트 보강** (#1, #3, #4) — observation+override / observation+exempt 2 케이스, malformed policy shape, `read_current_phase` 정상 path 매트릭스 추가.
6. **§3.1 vs §11 정합 정정** (#5) — yaml mode가 단일 진실원이면 _index.json mode를 read-only mirror로 명시.
7. **§2.1에 summarize 발화 명시** (#6) — record-after-summarize 또는 가시화 지연 정책 택일.
8. **§3.2에서 `mode: "off"` 제거** (#9).
9. **H1 결정 후 §0 또는 §10에 logging 정책 1줄 명시**.

위 9개 적용 후 재리뷰 1회 권장. **개별 수정은 작지만 #1은 P4b 입력 데이터 정합성에 직결되므로 우회 불가.**