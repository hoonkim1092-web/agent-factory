# Design Review: 2026-05-03-phase2-verdict-label-spec

> Source: docs/2026-05-03-phase2-verdict-label-spec.md
> Date: 2026-05-03 22:45
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

3건의 High 결함이 Critic에서 발견되었고, 모두 코드/문서 인용 근거가 강함. Cross-review는 provider error로 미수행 — 별도 재실행 권고(아래 Recommendations).

> **주의**: Cross Review가 provider error로 누락됨. 따라서 본 판정은 Critic 단독에 의존한다. CLAUDE.md "교차검증 자동 실행"에 따라 단일 설계문서는 af-cross-review만 필수이므로, **Phase 2 commit 전 af-cross-review 재실행이 필수**다(이전 v2 검토에서도 동일 누락이 있었음 — §8 선행 검토 노트).

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [High] §5.3 last-match 폴백 패턴 우선순위 미정의 — G7 회귀 가능
- **Critic**: 두 정규식(`_VERDICT_RE`/`_VERDICT_HEADER_RE`)의 last-match 결합 알고리즘 미명세. 본문 BLOCK 인용 + 마지막 줄 PASS 헤더 충돌 시 §7.2 C3가 PASS로 풀린다고 단정하지만 보장 불가.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. `hook_runner.py:339-344` 순차 우선순위 코드와 v3 §5.3 last-match 정책의 결합 알고리즘이 실제로 명시되지 않음. v3이 막으려는 G7과 동형의 모호성을 폴백 경로에서 재생산한다는 지적이 정확.
- **Action Required**: §5.3에 "두 정규식의 모든 매칭을 위치 기준으로 합쳐 last-position 선택" 또는 "`_VERDICT_RE` last-match 우선, 미매칭 시 `_VERDICT_HEADER_RE` last-match" 둘 중 하나 확정. §7.2 C3에 두 정규식 매칭 위치 동시 표기 케이스 추가.

#### 2. [ACCEPT] [High] §4.3 severity-missing fail-safe와 `[REJECTED]` verdict-neutral 충돌
- **Critic**: severity 누락 → BLOCK fail-safe 룰과 `[REJECTED]` verdict-neutral 룰이 동시 채택되면, severity 없는 정상 REJECTED 항목이 BLOCK으로 카운트됨. Codex가 false positive로 인정한 항목 때문에 BLOCK 발생 — 의도와 정반대.
- **Cross**: not flagged
- **Judgment**: ACCEPT. §4.4 우선순위 1 적용 시 명백한 모순. 현행 출력 예시(`af-cross-review.md:296`)에 REJECTED 항목 severity 의무가 없는 것도 확인됨.
- **Action Required**: §4.3 fail-safe 행에 단서 추가 — "`[REJECTED]` 라벨 finding은 verdict-neutral 우선; severity 누락이어도 BLOCK 카운트하지 않는다." §5.1 변경 6에 "REJECTED는 severity 생략 허용, 그 외 5종 라벨은 severity 의무" 명시. §7.1에 회귀 케이스 추가.

#### 3. [ACCEPT] [High] §5.5 silent fallback "G4 해소" 주장 불완전 — gate에 여전히 silent pass 흐름
- **Critic**: fallback 시 `verdict="pass"`가 `record_review_done()`/`has_block=False`로 전파되어, **gate 결정 자체는 형식 위반 LLM 출력 시 여전히 silent PASS**. 로그는 사후 감사용일 뿐 현재 라운드 gate를 fail-safe로 보호하지 않음. "G4 해소"는 과장.
- **Cross**: not flagged
- **Judgment**: ACCEPT. §6 비목표 O5("WARN → gate 차단")와 §5.5 의도 사이의 모순 정확히 짚음. 운영적으로 monitoring 사이에 일어난 commit은 이미 통과 상태.
- **Action Required**: 택일 명시. (a) fallback 시 `verdict="warn"` 또는 sentinel(`"unparseable"`)로 강등 + `is_gate_blocked` 분기 추가 (진짜 fail-safe), 또는 (b) §5.5/§6에 "G4는 detection-only 해소, gate-level 차단은 Phase 3로 이관" 명시.

#### 4. [ACCEPT] [Medium] §9.2 롤백 트리거 #1 측정 방법 미정의
- **Critic**: `verdict_fallback` 이벤트와 no-fire 오작동은 직접 인과 관계 없음. "재발화 빈도 측정"의 metric/jsonl/스크립트 불명. `check_pending_review.py:126`의 no-fire 분기에 telemetry sink 미존재.
- **Cross**: not flagged
- **Judgment**: ACCEPT. falsifiable rollback trigger를 주장했으나 measurement source가 없는 것이 사실.
- **Action Required**: §5.4를 "변경 없음" 대신 `check_pending_review.py:128`에 `_log_hook_event("warn_only_suppressed", {...})` 1줄 추가로 변경. §9.2 트리거 #1을 "warn_only_suppressed 빈도 vs WARN verdict 빈도"로 정의.

#### 5. [ACCEPT] [Medium] §8 구현 순서 — Tier 분류와 실행 에이전트 셋 자기모순
- **Critic**: 같은 step에서 "af-test-runner만"과 "scripts/*.py는 Tier 2~3 발화"를 동시 선언. `scripts/review_gate.py`/`hook_runner.py`는 자동 Tier 3.
- **Cross**: not flagged
- **Judgment**: ACCEPT. CLAUDE.md "Review-Gate 규칙"의 Tier 분류와 직접 충돌. 6개 파일 일괄 commit 시 3-tier 전체 실행 필수.
- **Action Required**: §8 step 3을 2-commit 전략 또는 "단일 commit + 3-tier 전체 + blast_radius 사전 출력 첨부"로 명시. 새 라벨 시스템 적용 후 다음 라운드부터 검증 가능한 부트스트랩 순서도 명시.

#### 6. [ACCEPT] [Medium] §5.3/§5.5 통합 계약 — wrapper 호출자 미명시
- **Critic**: §5.3 wrapper는 `review_gate.py`에 신설되지만 실제 verdict 파싱은 `hook_runner.py:339-344`에서 일어남. §5.5 변경 코드는 여전히 `_VERDICT_HEADER_RE`를 직접 호출. `record_review_done()`은 본문 파싱 안 함 — wrapper와 무관.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 코드 사실 검증으로 wrapper 통합 지점이 비어 있음을 정확히 짚음.
- **Action Required**: §5.3에 wrapper 단일 호출자(=`hook_runner.py`) 명시. §5.5 변경 코드를 "wrapper 호출 + None일 때만 fallback log + verdict='pass'"로 다시 작성. `record_review_done()`/`is_gate_blocked()`가 wrapper와 무관함을 정정.

#### 7. [ACCEPT] [Low] §5.1 변경 5 fence-내부 한정 vs `_SCOPE_CREEP_RE` 전역 검색 — 메트릭 손상
- **Critic**: `_SCOPE_CREEP_RE`는 전체 content 검색. fence 내부 한정 정책 도입 시 메트릭 손상 또는 정책 모호성 발생.
- **Cross**: not flagged
- **Judgment**: ACCEPT. §5.6이 `_FINDING_RE`만 다루고 `_SCOPE_CREEP_RE`는 누락된 사실 확인 가능.
- **Action Required**: §5.6에 1줄 추가 — "scope-creep는 verdict 라벨이 아니므로 fence 외부 검색 유지" 또는 "fence 내부 한정으로 변경 — 메트릭도 fence 추출 후 검색" 둘 중 하나 명시.

#### 8. [HOLD] [Low] frozen build 영향 미검토
- **Critic**: hooks가 frozen 컨텍스트에서 호출되는 경로 확인 없음. `_log_hook_event`가 새 키(`verdict_fallback`)를 쓸 때 workspace 경로 해석이 source build와 동일한지 미확인.
- **Cross**: not flagged
- **Judgment**: HOLD. scripts/*.py 변경에 대한 frozen build 영향은 일반적으로 외부 인터프리터로 호출되므로 영향이 작을 가능성 — 단정적 결함이라기보다 sanity 확인 사안. "안전하다고 단정할 수 없다"는 표현 자체가 약한 evidence.
- **Question for Author**: hooks 호출이 frozen `dist/af/af.exe`에서 source build와 동일 경로 해석을 사용하는지 확인했는가? 1회 sanity 빌드/실행 결과가 §8에 첨부되면 RESOLVE.

### Missing from Design (Critic 별도 지적 — 4건 추가 검토 권장)

- `record_review_done()` 인자 신뢰 관계 명시 (변경 5번과 연결)
- `AF_GATE_ALLOW_VERDICT_BLOCK` 우회 환경 변수 + fence 외부 잔존 인용 처리
- 마이그레이션 윈도우: v2 라벨 PR과 v3 라벨 PR 공존 시 `compute_report()` 일관성
- 다중/중첩 fence 케이스 wrapper 동작 정의 (LLM이 prompt 어겼을 때)

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §5.3 last-match 패턴 우선순위 미정의 | High | ACCEPT | Critic |
| 2 | §4.3 fail-safe vs `[REJECTED]` 충돌 | High | ACCEPT | Critic |
| 3 | §5.5 G4 "해소" 주장 — gate에 silent pass 잔존 | High | ACCEPT | Critic |
| 4 | §9.2 롤백 트리거 측정 방법 미정의 | Medium | ACCEPT | Critic |
| 5 | §8 Tier 분류 자기모순 | Medium | ACCEPT | Critic |
| 6 | §5.3/§5.5 wrapper 호출자 미명시 | Medium | ACCEPT | Critic |
| 7 | `_SCOPE_CREEP_RE` 전역 검색 잔존 | Low | ACCEPT | Critic |
| 8 | frozen build sanity 미검토 | Low | HOLD | Critic |

### Recommendations

- **즉시 수정 (BLOCK 해제 조건)**: Findings 1, 2, 3 — High 3건 모두 §4.3/§5.3/§5.5에 명시적 단서 추가 필요. 특히 #3은 "G4 해소" 표현을 "detection-only 해소" 또는 실제 gate 차단으로 강등.
- **v4 commit 전 보강**: Findings 4~7 — Medium/Low 4건. §5.4 telemetry 추가, §8 Tier 분류 정합화, §5.3 wrapper 호출자 명시, §5.6 SCOPE_CREEP_RE 정책.
- **af-cross-review 재실행 필수**: provider error로 Tier 3 검증이 누락됨. v2 검토에서도 동일 누락이 있었으므로, v4 작성 후 cross-review 재실행을 §8에 명시적으로 못박을 것 (CLAUDE.md "교차검증 자동 실행" 정책).
- **v4 작성 시 Missing 4건도 반영 검토**: 단정 결함은 아니지만 spec 완결성 향상에 기여.