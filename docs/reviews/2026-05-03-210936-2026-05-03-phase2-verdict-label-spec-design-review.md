# Design Review: 2026-05-03-phase2-verdict-label-spec

> Source: docs/2026-05-03-phase2-verdict-label-spec.md
> Date: 2026-05-03 21:09
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

Cross-review failed with provider error (Codex CLI startup output truncated mid-prompt — no findings produced). I'll aggregate from Critic only, having verified each finding against the actual code.

## Final Design Review

### Verdict: BLOCK

크리틱 #1(메트릭 파서 회귀)이 §9.1 운영 검증을 self-defeat 시키는 구조적 결함 — 실제 코드에서 확인됨. Cross-review는 provider error로 산출 실패. Critic 발견 8건만으로도 BLOCK 충분.

> ⚠️ **Cross-review 미수행**: 출력에서 Codex CLI가 stdin을 읽다가 응답 없이 truncate됨 (`(provider error: Reading prompt from stdin...`). 본 판정은 Critic 단독 + 코드 직접 검증 기반. 재실행 권장.

---

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [High] `[ACCEPT-ADV]` 신설이 `review_metrics_logger._FINDING_RE` 회귀
- **Critic**: §5에 `scripts/review_metrics_logger.py` 누락 — `_FINDING_RE = r'\[(?:ACCEPT[★*]?|WARN|BLOCK|REJECTED)\]'`가 ACCEPT-ADV/HOLD 미매칭, findings_count 0으로 무너짐.
- **Cross**: not flagged (provider error).
- **Judgment**: 코드 직접 검증 — `scripts/review_metrics_logger.py:31-34`는 정확히 critic 인용대로다. `tests/test_review_metrics_logger.py:34-57`이 기존 라벨만 가정. `[ACCEPT-ADV]`/`[HOLD]` 도입 즉시 메트릭이 손상되며 §9.1 "WARN 비율 측정"이 동시에 무력화 — Phase 2 효과 측정 수단 상실.
- **Action Required**: §5에 `scripts/review_metrics_logger.py` 변경 + `tests/test_review_metrics_logger.py` 갱신을 등록. 정규식: `\[(?:ACCEPT(?:[★*]|-ADV)?|WARN|BLOCK|REJECTED|HOLD)\]`. Phase 2 범위 외로 분리 시 §9.1 검증 자체가 불가능하므로 Phase 2 차단 의존성으로 격상.

#### 2. [ACCEPT] [High] G4 silent "pass" fallback이 Phase 2 효과를 침묵 무력화
- **Critic**: `hook_runner.py:344` `verdict = hm.group(1).lower() if hm else "pass"` — LLM이 `Tier 3: WARN` 같이 형식 어긋나면 silent PASS. §9.2 "WARN-only no-fire 의도와 다른 동작" 트리거가 실제로 발화되지 않는다. §6에서 G4를 Phase 후속 이관 처리.
- **Cross**: not flagged (provider error).
- **Judgment**: `scripts/hook_runner.py:343-346` 직접 확인 — silent fallback 그대로. Phase 2의 substantive 변화가 정확히 verdict 라인 글자 변경에 의존하는데 LLM 출력 형식 표류를 감지할 메커니즘이 없음. §9.2 롤백 트리거가 falsifiable하지 않게 됨.
- **Action Required**: Phase 2 범위에 최소 1건 추가 — fallback 발생 시 `_log_hook_event("verdict_fallback", ...)` 또는 stderr 1줄 경고. 또는 §10 F2를 **Phase 2 차단 의존성**으로 격상.

#### 3. [ACCEPT] [High] `_VERDICT_RE.search()` collision enforcement 부재
- **Critic**: §7.2 "verdict 라인은 최종 라인 1회만"을 invariant로 추가만 하고 enforcement 없음. `re.search()` 첫 매칭 정책이라 finding 본문에 "이전 라운드 판정: BLOCK" 인용이 있으면 본문이 verdict로 캡처.
- **Cross**: not flagged (provider error).
- **Judgment**: `scripts/review_gate.py:25-28` 직접 확인 — `_VERDICT_RE`는 MULTILINE `re.search()` 첫 매칭. af-cross-review는 본질적으로 prior round를 인용할 수 있는 에이전트 → collision 현실적. LLM 자기 통제 100% 의존은 spec defect.
- **Action Required**: 둘 중 하나 — (a) 파서를 anchored regex 또는 마지막-매칭 우선으로 변경 (Phase 2 범위 확장), (b) Step 5 출력에 verdict fence(`<!-- final-verdict-start --> ... <!-- final-verdict-end -->`) 도입 후 파서가 fence 내부만 매칭. §7.2에 "본문에 `판정: BLOCK` 인용 포함" 회귀 케이스 추가.

#### 4. [ACCEPT] [Medium] `[HOLD]` forward-looking 정의가 prompt drift 유발
- **Critic**: §5.1 변경 7에서 HOLD를 Step 5에 명문화하면서 §6 G3로 입구 조건은 이관 → LLM이 자의적으로 HOLD 발화 → Phase 2 데이터 노이즈 + Finding #1과 결합해 카운트 이중 손실.
- **Cross**: not flagged (provider error).
- **Judgment**: prompt design anti-pattern. "정의됐는데 사용 금지"는 LLM 행동 통제 실패 사례 다수. §4.5의 "Phase 2 시점 HOLD 0건 발화" 가정에 enforcement 없음.
- **Action Required**: (a) §5.1 변경 7 자체를 Phase 3로 이관 (정의도 빼기) — 권장, 또는 (b) Phase 2 prompt에 "HOLD 사용 금지" 명시적 가드 + 파서/검증 단계에서 HOLD 출현 시 fail-fast.

#### 5. [ACCEPT] [Medium] §5.1 변경 6 severity 누락 실패 모드 미정의
- **Critic**: severity bracket 누락 시 매핑 결정 불가. 기본값/검증 미정. 현재 코드에 severity 추출 로직 없음.
- **Cross**: not flagged (provider error).
- **Judgment**: §4.3 매핑 테이블 전체가 severity 의존인데 §7.1 시나리오 8건이 모두 깔끔한 severity 명시 케이스 → 누락 입력 검증 0건. 운영 데이터에서 LLM이 잊으면 silent miscategorization.
- **Action Required**: §4.3에 "severity 누락 → BLOCK 안전 default" 행 추가 + §7.1에 severity 누락 시나리오 1건 추가.

#### 6. [HOLD] [Medium] §7.1 시나리오 6 BONUS 입력 형식 모호
- **Critic**: `[BONUS]`는 라벨 prefix 아닌 Codex Round 1 분류(§4.2). 시나리오 6 "BONUS Critical 2건"이 §5.1 출력 형식의 어떤 라벨로 표기되는지 불명확.
- **Cross**: not flagged (provider error).
- **Judgment**: 현 spec에서 BONUS finding이 §5.1 변경 6의 `#### N. [라벨] [Severity] 제목` 헤더에 어떤 라벨로 출력되는지 정말로 미정의. 실 운영 영향은 작지만 검증 시나리오의 입력 명세 불완전.
- **Question for Author**: Step 5에서 BONUS 항목은 어떤 finding 헤더 라벨로 출력하는가? `[BONUS]`를 finding 라벨로 승격할지, 아니면 별도 섹션에 묶을지 §5.1에 명시 필요.

#### 7. [ACCEPT] [Medium] §7.5 회귀 시나리오 round-간 상호작용 누락
- **Critic**: max_rounds=2 cap, mixed verdict round, Round 1 BLOCK→Round 2 WARN 전환 시 has_block 갱신 등 round 단위 추적 누락. Phase 2의 핵심 보장 "labeling만 바뀌고 no-fire 동일"이 round 전환 케이스에서 검증 안 됨.
- **Cross**: not flagged (provider error).
- **Judgment**: §7.3은 단일 라운드 경로 추적만 제공. Phase 2의 "기능 불변" 주장(§4.6)을 보장하려면 round 전환이 필수.
- **Action Required**: §7.5에 4 케이스 추가 — (i) R1 WARN→R2 사용자 편집 시 no-fire, (ii) R1 BLOCK→수정→R2 WARN, (iii) max_rounds=2 도달 후 WARN, (iv) Mixed (T1 pass, T2 block, T3 warn).

#### 8. [ACCEPT] [Low] `[ACCEPT]` → `[ACCEPT-ADV]` 마이그레이션 가이드 없음
- **Critic**: 기존 `docs/reviews/` 30건이 구 라벨. grep 일관성 + LLM context 혼재.
- **Cross**: not flagged (provider error).
- **Judgment**: 운영 영향 작지만 audit trail 명료성 위해 1줄 명시 가치 있음.
- **Action Required**: §11에 "기존 review의 `[ACCEPT]` advisory는 시점 기준 그대로 유지" 1줄 + §10 F7 "과거 review 일괄 재라벨링(선택)" 등록.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_FINDING_RE` 회귀 (review_metrics_logger.py 누락) | High | ACCEPT | Critic + 코드 검증 |
| 2 | G4 silent fallback이 Phase 2 효과 무력화 | High | ACCEPT | Critic + 코드 검증 |
| 3 | `_VERDICT_RE` collision enforcement 부재 | High | ACCEPT | Critic + 코드 검증 |
| 4 | `[HOLD]` forward-looking 정의의 prompt drift | Medium | ACCEPT | Critic |
| 5 | §5.1 변경 6 severity 누락 실패 모드 미정의 | Medium | ACCEPT | Critic |
| 6 | §7.1 BONUS 시나리오 입력 형식 모호 | Medium | HOLD | Critic |
| 7 | §7.5 회귀 시나리오 빈약 (round 전환 누락) | Medium | ACCEPT | Critic |
| 8 | ACCEPT→ACCEPT-ADV 마이그레이션 가이드 없음 | Low | ACCEPT | Critic |

---

### Recommendations

구현 전 v3 리비전에서 다음 조치 필요:

1. **§5에 `scripts/review_metrics_logger.py` + 테스트 추가** (Finding #1, BLOCK 해소 필수). 정규식: `\[(?:ACCEPT(?:[★*]|-ADV)?|WARN|BLOCK|REJECTED|HOLD)\]`.
2. **G4 fallback 가시화 또는 F2 격상** (Finding #2). `_log_hook_event("verdict_fallback", ...)` 1줄 추가가 최소 비용 해법.
3. **Verdict collision 방지 메커니즘 도입** (Finding #3). Fence 마커(`<!-- final-verdict-start -->`) 또는 last-match 정책 중 택1 + §7.2 회귀 케이스 보강.
4. **HOLD 정의를 Phase 3로 완전 이관** (Finding #4). §5.1 변경 7 삭제 권장.
5. **Severity 누락 안전 default 명시** (Finding #5). §4.3에 행 추가 + §7.1 시나리오 추가.
6. **§7.1 시나리오 6 BONUS 입력 형식 명시** (Finding #6). HOLD 결정 후 §5.1에 BONUS finding 헤더 표기 규칙 명시.
7. **§7.5 round 전환 4 케이스 추가** (Finding #7).
8. **§11에 라벨 마이그레이션 1줄 + §10 F7 등록** (Finding #8).
9. **Cross-review 재실행** (provider error로 미수행) — 본 판정 보강 위해 필요.