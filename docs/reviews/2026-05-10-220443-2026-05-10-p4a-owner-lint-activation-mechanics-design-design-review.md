# Design Review: 2026-05-10-p4a-owner-lint-activation-mechanics-design

> Source: docs/2026-05-10-p4a-owner-lint-activation-mechanics-design.md
> Date: 2026-05-10 22:04
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Critic #1은 Critical (v2 이력에서 "흡수했다"고 선언한 cross-review BLOCK이 §5.3 본문에 실제로 반영되지 않음 — 구현자가 §5.3 코드대로 짜면 동일 BLOCK으로 회귀). 추가로 High 6건(코드 참조 강함). 진행 불가.

### Aggregated Findings (14 total)

#### 1. [ACCEPT] [Critical] v2 이력 #2가 §5.3 본문에 미반영 — cross-review BLOCK 미해소
- **Critic**: v2 헤더 line 12는 "mode 분기를 false_positive_override **직후**로 변경, exempt_when도 observation에 적용"이라 선언했으나, §5.3-B(line 273)·§5.3 코드(lines 294-328)·§10 #2(line 459) 전부 **앞단** 배치 + observation 경로에 exempt 분기 부재
- **Cross**: 직접 동일 항목 미플래그 (단 #2/#3에서 동일 영역의 의미·fail-closed 위험을 별개로 지적)
- **Judgment**: §5.3 코드와 §10 #2 다이어그램이 v2 이력과 정면 충돌. 어느 진실원도 신뢰 불가. 구현자가 §5.3 코드를 따르면 cross-review가 동형 BLOCK으로 회귀.
- **Action Required**: 결단 — (a) v2 이력대로 §5.3 코드/표/§10 #2를 모두 "false_positive_override + exempt_when 통과 후" 배치로 정정, 또는 (b) v2 이력 #2를 retract하고 "앞단 배치 유지 + P4b candidate count 데이터 오염 가능성 수용"을 명시. 동시에 Critic #9(아래) 결정도 같이 처리.

#### 2. [ACCEPT] [High] §0.1 표가 v2 #1 "reason 표현 통일" 주장과 불일치
- **Critic**: §0.1 line 40 `reason="observation_mode"`가 §5.3/§5.5/v2 #1의 `observation_threshold_met|observation_below_threshold`와 어긋남
- **Cross**: 미플래그
- **Judgment**: 운영자가 `_decision.md`에서 `observation_mode` grep → 0건. 가시 불일치, 디버깅 시간 낭비.
- **Action Required**: line 40을 `reason="observation_below_threshold"`로 정정.

#### 3. [ACCEPT] [High] §7 #4 — `write_error_decision`의 `activate_phase` 필드/MD 마커 누락
- **Critic**: `escalation_decision_report.py:43,57` `activate_phase: "P2"` 하드코딩 + md 라인. §7 #4는 `escalation_phase`만 다룸
- **Cross**: 미플래그
- **Judgment**: 두 phase 필드(`escalation_phase`/`activate_phase`) 공존, 같이 동적화 안 하면 `_decision.md`에 split brain.
- **Action Required**: §7 #4에 "payload `activate_phase` + md line 57 `activate_phase` 마커도 동적화" 명시. 또는 `activate_phase` deprecation 결정 추가.

#### 4. [ACCEPT] [High] 정책 shape 오류 fail-closed 미보장 (Critic #4 + Cross #3 병합)
- **Critic**: `read_current_phase`가 yaml `current_phase: ["P4"]`/`4` 같은 비-string에 TypeError → fail-open
- **Cross**: 더 넓게 — top-level mapping/`rules` list 검증도 부재. `summarize()` 현 fail-closed 블록 바깥에서 raise되면 `write_error_decision` 호출 불가능
- **Judgment**: 두 리뷰 모두 같은 구조 결함을 다른 입구에서 지목. 강한 evidence.
- **Action Required**: (a) `read_current_phase`에 `isinstance(cp, str)` 가드, (b) `load_policy()`가 top-level mapping/`rules` list 검증 후 `PolicyError` raise, (c) `summarize()`에서 `current_phase = "P2"`를 policy load **전**에 초기화하여 실패 시에도 `write_error_decision(..., current_phase=current_phase)` 항상 호출 가능. §7/§5.2/§8 테스트 fixture에 list/int/malformed rules 케이스 추가.

#### 5. [ACCEPT] [High] `_PolicyRule.from_dict` mode 오타 → 슬러그 전체 BLOCK
- **Critic**: `mode: enfroce` 1글자 오타 → ValueError → except → `write_error_decision` → BLOCK. §3.5 rollback 표 부재
- **Cross**: 미플래그
- **Judgment**: P4b가 mode toggle 중 오타 1건에 슬러그 빌드 마비. 위험 vs 가시성 trade-off 결정 누락.
- **Action Required**: §3.5 5번째 rollback 행 추가 ("yaml 검증 실패 → AF_SKIP_ESCALATION=1 / yaml revert / dist/af warning repair") + 의도가 fail-closed인지 fail-safe(invalid → enforce fallback + log.warning)인지 명시.

#### 6. [ACCEPT] [High] P4 record 작성 후 `summarize()` 트리거 부재
- **Cross**: `project_pipeline.py:769-777`(evidence_quality_warn), `:1455-1467`(owner_role_mismatch) 모두 record 작성 후 `summarize()` 호출 안 함. P4a 가시성 가정 깨짐
- **Critic**: 미플래그
- **Judgment**: 강한 코드 evidence(file:line). P4a 핵심 가치(observation 데이터 가시화)가 트리거 부재로 무력화.
- **Action Required**: §6 flowchart/§7에 record 작성 직후 `summarize()` 호출 wiring 명시 또는 "P4a 가시성은 별도 CLI/manual summarize 필요"로 spec 변경. §8 테스트에 owner_role_mismatch/evidence_quality_warn record → `_decision.json` 갱신 assertion 추가.

#### 7. [ACCEPT] [High] `repeat_count_min`이 record dedup으로 영원히 도달 불가
- **Cross**: `warning_registry.py:110-124,145-146`에서 동일 payload는 같은 record_id → 중복 skip. 안정적 owner 드리프트는 `repeat_count_max`가 1에서 멈춤
- **Critic**: 미플래그
- **Judgment**: P4b가 measurement 후 임계 결정한다 가정인데 측정 메트릭 자체가 의미 변형됨. 강한 evidence.
- **Action Required**: 의미 결정 후 §3에 추가 — (a) `count_per_run_min`로 distinct mismatches 카운트, (b) record identity에 run/session 시간 포함, 또는 (c) `repeat_count_min`을 "distinct payload variants only"로 문서화. "same drift twice" 회귀 테스트 추가.

#### 8. [ACCEPT] [Medium] §10 #1 (single-load) vs §2.1 #3·§6 (double-load) 모순
- **Critic**: §6 flowchart는 `load_policy()` 두 번 호출, §10 #1은 single-load 강조. race condition 시 두 read 사이 yaml swap → split decision
- **Cross**: 미플래그 (단 #3에서 load 위치 spec 명시 권고와 같은 방향)
- **Judgment**: 문서 자체가 모순. 운영자 rollback 중 split 위험 실재.
- **Action Required**: §2.1 #3, §6 flowchart, §7 #3을 single-load로 통일 — `policy_obj = load_policy(); current_phase = read_current_phase(policy_obj); compute_run_decision(summary, policy_obj, current_phase=current_phase)`.

#### 9. [ACCEPT] [Medium] §8.5 frozen smoke test가 `af warning-stats`로 `_decision.md` 검증 불가
- **Critic**: warning-stats는 jsonl 집계만, `_decision.md` 트리거 아님. 빈 워크스페이스 read-only
- **Cross**: 미플래그 (단 #1과 같은 영역의 변형)
- **Judgment**: smoke 절차 자체가 검증 가치 0. Cross #1과 함께 P4a 가시성 wiring 부재 신호.
- **Action Required**: `af pipeline run --workspace .` 또는 신규 `af warning summarize --slug <test>` CLI 추가 spec. 없으면 §8.5 smoke를 unit fixture로 위임 명시.

#### 10. [ACCEPT] [Medium] 테스트 케이스 #6 의존성 모호 — 프로덕션 yaml vs monkeypatch
- **Critic**: 케이스 6은 yaml `current_phase: "P4"` 기대, §7 #7(yaml flip)은 #6 이후 단계. 의존 그래프 깨짐
- **Cross**: 미플래그
- **Judgment**: CI에서 #7 전에 #6 실행 시 실패. spec에 fixture 명시 필요.
- **Action Required**: §8.2 케이스 6 본문에 "fixture로 `_POLICY_PATH`를 `tmp_path/escalation_policy.yaml` monkeypatch" 명시, 또는 §7 #7 yaml flip을 #6 앞으로 이동.

#### 11. [ACCEPT] [Medium] §5.4 0줄 주장과 `compute_run_decision`의 `any_override` 슬러그 OR 집계 충돌
- **Critic**: `false_positive_override`가 슬러그 전체 OR 집계 → mode 분기를 override 뒤로 두면 한 record override가 모든 phase virtual_record를 warn으로 빨아들임 → P4b 임계용 분포 0건
- **Cross**: 미플래그 (단 본 finding은 #1 결정과 직결)
- **Judgment**: v2 #2 자기 목표("override 데이터 오염 방지")와 §5.4 "변경 0줄" 주장이 동시에 성립 불가. Critic #1 결정과 함께 처리 필수.
- **Action Required**: 둘 중 — (a) §5.4에 "any_override 집계를 phase별 분리"로 변경 추가, (b) virtual record 생성 시 `false_positive_override=False` + observation 분기에서만 별도 override marker. §5.4 "0줄" 주장 수정 동반.

#### 12. [ACCEPT] [Low] §9 baseline grep 표 row 442 표현 모호
- **Critic**: "별도 처리 필요"가 변경/유지 양방향 해석 가능. line 452에서야 분명
- **Action Required**: 표 셀을 "변경 없음 — line 452 §10 #6 참조" 또는 "유지: P2 floor"로 정정.

#### 13. [ACCEPT] [Low] §3.5 rollback "4단" 명명 — 4번은 기존 메커니즘
- **Critic**: `activate_at: never`는 yaml line 28 `plan_verifier_warn`에서 이미 사용 중인 escape hatch. 4단 신설처럼 표기는 변경 범위 부풀림
- **Action Required**: §3.5 첫 줄에 "P4a는 2번/3번을 신설, 1번/4번은 기존 메커니즘 유지·문서화" 추가.

#### 14. [HOLD] [Medium] `evidence_quality_warn` slug 소유권 vs gate slug 일치 미정
- **Cross**: record 시 `_ev_slug = safe_id(task_input)[:40]` 사용 vs approval gate decision은 work-item slug 경로 read. 다르면 evidence warn은 gate decision에 영원히 비가시
- **Critic**: 미플래그
- **Judgment**: Cross #1 wiring 결정과 묶여 있어 단독 판정 어려움. evidence는 강하지만 의도가 "workspace 통계 전용"일 가능성 배제 못함.
- **Question for Author**: `task_input`이 work-item slug과 동일 보장되는가? 아니면 `evidence_quality_warn`은 P4a에서 통계 전용이고 gate decision 노출은 P4b 작업인가?

#### 15. [REJECT] [Low] `load_policy()`가 top-level `current_phase` strip 가능성
- **Source**: Cross #5
- **Original Finding**: 마이그레이션 중 `{"rules": ...}`만 반환할 위험
- **Rejection Reason**: Cross 본인이 self-reject — 현 `load_policy()`는 `yaml.safe_load()` 결과를 필터 없이 반환. 보존은 자연스럽게 됨. 진짜 위험은 검증/배치이며 그건 #4(ACCEPT)가 커버.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | v2 이력 #2 §5.3 본문 미반영 | Critical | ACCEPT | Critic |
| 2 | §0.1 reason 명칭 불일치 | High | ACCEPT | Critic |
| 3 | write_error_decision activate_phase 미동적화 | High | ACCEPT | Critic |
| 4 | 정책 shape 오류 fail-closed 미보장 | High | ACCEPT | Both |
| 5 | _PolicyRule mode 오타 → 슬러그 BLOCK | High | ACCEPT | Critic |
| 6 | P4 record 후 summarize() 트리거 부재 | High | ACCEPT | Cross |
| 7 | repeat_count_min dedup 도달 불가 | High | ACCEPT | Cross |
| 8 | single-load vs double-load 모순 | Medium | ACCEPT | Critic |
| 9 | §8.5 smoke가 _decision.md 검증 불가 | Medium | ACCEPT | Critic |
| 10 | 테스트 #6 yaml 의존 모호 | Medium | ACCEPT | Critic |
| 11 | §5.4 0줄 vs any_override 집계 충돌 | Medium | ACCEPT | Critic |
| 12 | §9 baseline grep row 442 모호 | Low | ACCEPT | Critic |
| 13 | §3.5 rollback "4단" 명명 | Low | ACCEPT | Critic |
| 14 | evidence_quality_warn slug 일치 | Medium | HOLD | Cross |
| 15 | load_policy current_phase strip | Low | REJECT | Cross |

### Recommendations

구현 진입 전 다음 순서로 처리:

1. **결단 1건 먼저 (#1 + #11 동반)** — v2 이력 #2 옵션 (a) 채택 vs retract. 결정 후 §5.3 코드/§5.3-B/§10 #2 + §5.4 "any_override" 집계 처리 + §5.4 0줄 주장을 모두 같은 방향으로 정합화. 이 결정이 P4b candidate 데이터 품질의 근본.
2. **fail-closed 정합화 (#4 + #5)** — `read_current_phase` 가드 + `load_policy()` shape 검증 + `summarize()` 내 `current_phase` 사전 초기화. §3.5에 yaml 오타 rollback 행 추가.
3. **wiring 보강 (#6 + #9)** — owner_role_mismatch/evidence_quality_warn record 직후 `summarize()` 호출 명시. §8.5 smoke 명령을 검증 가능 경로로 변경.
4. **dedup semantics 결정 (#7)** — `repeat_count_min` 카운트 의미 확정 + 회귀 테스트.
5. **표기 정합 (#2, #3, #8, #10, #12, #13)** — 문서 정정 일괄.
6. **HOLD #14 응답** — evidence_quality_warn slug 소유권 결정 후 §3.2 또는 §6에 명시.
7. v2 → **v3 리비전 + cross-review 재발화** 후 코드 진입.