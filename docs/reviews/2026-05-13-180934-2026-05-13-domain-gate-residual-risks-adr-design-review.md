# Design Review: 2026-05-13-domain-gate-residual-risks-adr

> Source: docs/2026-05-13-domain-gate-residual-risks-adr.md
> Date: 2026-05-13 18:09
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

Cross Review가 provider error로 실패하여 Critic Review 단독 판정. Critical 2건 + 8건 High/Medium 모두 ADR 본문에서 직접 검증 가능한 사실 오류·논리 모순이므로 BLOCK 유지. F1, F2 분할, F5 Decision 모순만 정정하면 PASS로 다운그레이드 가능.

---

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] F1이 거짓 잔여 — design doc은 이미 `"local"`을 사용하지 않음
- **Critic**: ADR이 인용한 `§3.3 line 152/181 "local"`은 grep 미실측. 152행은 `→ RequestRouter.route()`, 181행은 공백. "local"은 195/266행 부정형 회귀 차단 문장에만 존재.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: ADR 본인이 인용한 메모리 룰 `feedback_design_doc_grep_before_write`를 위반. "5번째 회귀"라는 카운트가 사실과 다름. ADR line 13의 "회귀 누적 5회" 표현 및 Residual Findings F1 모두 grep 실측과 불일치.
- **Action Required**: F1을 "이미 정정됨 — Phase A 구현 시 grep 회귀 테스트만 추가"로 다운그레이드 + 라인 번호(`§3.3 line 152/181`) 및 "5번째 회귀" 카운트 제거.

#### 2. [ACCEPT] [Critical] Decision과 F5의 모순 — Phase A 진입 허가 vs Phase A 정당화 부재
- **Critic**: ADR line 25 "Phase A 진입 가능"과 F5 (line 44) "Phase A 단독 정당화 근거 부재, 결정 시점=Phase A 진입 결정"이 직접 충돌.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: 문서 자체에서 확인 가능한 논리 모순. F5가 High로 미결인데 Decision이 무조건부 진입 허가를 내리면 F5는 무의미한 finding.
- **Action Required**: Decision을 "Phase A 진입 가능 — 단 F5 결정이 PR 0번으로 선행 필수"로 한정, 또는 F5를 Critical로 승격 후 Decision을 조건부로 명시.

#### 3. [ACCEPT] [High] F2 verification 범위 부족 — `_parse()`/스키마/호출자 미언급
- **Critic**: F2(line 36)는 `_render()` 시그니처만 다룸. `_parse()` round-trip, `## Metadata` 스키마 확장(design doc line 169-170), 기존 마크다운 마이그레이션, 정확한 호출자 매트릭스 누락.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: F2 grounding 자체(`core/approval_gate.py:496-550`)는 정확하지만 범위가 좁음. 시그니처 확장은 _parse + 스키마 + 호출자 4파트로 전파됨.
- **Action Required**: F2를 F2a(`_render` 시그니처)/F2b(`_parse` round-trip)/F2c(`## Metadata` 스키마+마이그레이션)/F2d(호출자 enumerate) 4개로 분리. G1에 `test_approval_gate_runtime_workspace.py`, `test_approval_gate_block_decision.py` 추가.

#### 4. [ACCEPT] [High] G4 카운트 오류 — 기존 게이트 테스트는 7개가 아닌 8개
- **Critic**: `approval_gate` 참조 grep 결과 8개 파일(auto_approve, block_decision, runtime_workspace, pipeline_block_enforcement, critic_skill_router, t3_7_run_event_integration, skill_procurer_reuse_gate, skill_procurer_external_fallback). ADR line 63은 "7개".
- **Cross**: 검증 불가 (provider error)
- **Judgment**: ADR이 카운트조차 grep 안 한 명백한 사실 오류. 회귀 매트릭스 신뢰도 하락.
- **Action Required**: "기존 7개 게이트 테스트" → 정확한 파일명 8개 enumerate.

#### 5. [ACCEPT] [High] F3에서 `_DOMAIN_REVIEW_FILE`을 기존 식별자처럼 인용
- **Critic**: `core/approval_gate.py`에 `_DOMAIN_REVIEW_FILE` grep 0건. 신설 상수인데 ADR이 "격리로 verdict 위조"라고 단정 = 격리 정책을 이미 결정했다고 전제.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: 옵션 (a)/(b) 미정 상태에서 격리가 사라질 가능성. F1과 동일한 패턴 — grep 누락.
- **Action Required**: F3를 "신설 `_DOMAIN_REVIEW_FILE` 상수 격리 정책 미정 (grep 0건 확인됨)"으로 재작성 + design doc에서 "격리 결정" 위치 line 인용.

#### 6. [ACCEPT] [Medium] F4가 design doc 결정 위반 — "1줄 의무" 이미 확정
- **Critic**: design doc line 228 "machine-readable 1줄 의무, 체크박스는 보조"는 결정사항. `missing_verdict`는 false-positive가 아닌 정상 동작. F4 옵션 (b)/(c)는 design 결정을 뒤집는 셈.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: F4의 진짜 risk는 검토자 UX(체크박스만 채울 가능성)이지 파서 옵션 아님.
- **Action Required**: F4 재문구화 — 옵션 (b)/(c) 제거, (a)(체크박스 제거) + (d)(template prompt 추가)만 유지.

#### 7. [ACCEPT] [Medium] Source Design 동결 시점 모호
- **Critic**: `git status: M docs/2026-05-11-...` — 워킹트리 M 상태. ADR line 5가 워킹트리 동결인지 HEAD 동결인지 불명. 사후 추가 수정 시 동결 무효화.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: 4차 freeze ADR이 freeze 대상의 정확한 sha를 못 가리키면 freeze 자체가 약함.
- **Action Required**: ADR 헤더에 `Source Design Commit: <git sha>` 또는 design doc을 별도 commit으로 먼저 freeze.

#### 8. [ACCEPT] [Medium] F7 미결정 옵션 — ADR의 역할 위배
- **Critic**: ADR은 결정 기록 문서. F3/F4/F5/F7 모두 옵션 나열만 있고 결정 미실시면 RFC.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: ADR + Residual finding 혼합 구조에서 미결정 옵션은 별도 섹션 분리 필요.
- **Action Required**: "Decisions Required Before Phase A" 섹션 신설 + F3/F4/F5/F7 책임자·deadline 지정.

#### 9. [ACCEPT] [Medium] F8 검증 불가 — design doc §4.3/§4.4 인용 부재
- **Critic**: "B=6은 보류여야 하는데 선택적 표기"가 어떤 행을 가리키는지 ADR만으로 알 수 없음 → silent rework 위험.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: 미래 작업자에게 재해석 부담을 남김.
- **Action Required**: F8에 `§4.3 line X / §4.4 line Y` 직접 인용 추가.

#### 10. [ACCEPT] [Medium] 후속 책임 1번이 F1/F2 즉시 처리 지시 — F1 거짓이면 효과 0
- **Critic**: F1의 grep 회귀 시나리오는 design doc line 266에 이미 존재. ADR 추가 가치 없음.
- **Cross**: 검증 불가 (provider error)
- **Judgment**: Finding #1의 직접 귀결. F1 정정 시 자동 해소.
- **Action Required**: "F1: design doc line 266 회귀 시나리오를 `tests/test_approval_gate_identifier_regression.py`로 코드화"로 구체화.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | F1 거짓 잔여 (라인 번호·카운트 오류) | Critical | ACCEPT | Critic |
| 2 | Decision과 F5 논리 모순 | Critical | ACCEPT | Critic |
| 3 | F2 _parse/스키마/호출자 누락 | High | ACCEPT | Critic |
| 4 | G4 테스트 카운트 7→8 정정 | High | ACCEPT | Critic |
| 5 | F3 `_DOMAIN_REVIEW_FILE` grep 0건 미명시 | High | ACCEPT | Critic |
| 6 | F4 design doc "1줄 의무" 결정 위반 | Medium | ACCEPT | Critic |
| 7 | Source Design commit sha 부재 | Medium | ACCEPT | Critic |
| 8 | F7 미결정 옵션 (ADR 역할 위배) | Medium | ACCEPT | Critic |
| 9 | F8 §4.3/§4.4 인용 부재 | Medium | ACCEPT | Critic |
| 10 | 후속 책임 #1이 F1에 의존 | Medium | ACCEPT | Critic |

---

### Recommendations

**Phase A 진입 전 필수 정정 (Critical 2건)**:
1. F1 → "이미 정정됨" 다운그레이드 + 라인 번호·5번째 회귀 카운트 제거 (ADR line 13, F1 row)
2. F5 모순 해소 — Decision을 조건부로 한정하거나 F5를 Critical로 승격

**구조 정정 (High 3건)**:
3. F2를 F2a~F2d 4개로 분리 + G1에 누락 테스트 2건 추가
4. G4 "7개" → 8개 파일명 enumerate
5. F3 `_DOMAIN_REVIEW_FILE` grep 0건 사실 명시

**문서 품질 (Medium 5건)**:
6. F4 옵션 (b)/(c) 제거, design doc line 228 인용
7. ADR 헤더에 `Source Design Commit: <sha>` 추가
8. "Decisions Required Before Phase A" 섹션 신설
9. F8에 design doc 직접 인용 추가
10. 후속 책임 #1을 design doc line 266 회귀 시나리오 코드화로 구체화

**Cross Review 재실행**: codex provider 17:25 stdin-read error로 외부 vendor 검증 부재 — 위 정정 후 cross-review 재실행 권장 (3-round cap 카운트 별도, provider 장애 라운드는 cap에 미포함).