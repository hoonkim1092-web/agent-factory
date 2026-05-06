# Design Review: 2026-05-03-phase2-verdict-label-spec

> Source: docs/2026-05-03-phase2-verdict-label-spec.md
> Date: 2026-05-03 20:37
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

---

## Final Design Review

### Verdict: WARN

> **Cross Review 상태**: 프로바이더 오류로 출력 없음 (OpenAI Codex 연결 실패). Critic Review 단독 집계. Aggregation Rule 2 적용 — Critic 증거가 문서 내 명시된 텍스트에 직접 근거하므로 ACCEPT 처리.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] §4.2 테이블이 `[HOLD] Low → PASS`로 규정해 §4.3/§5.1과 충돌

- **Critic**: §4.2 `[REJECTED] / [HOLD] Low → PASS 기여(무시)` vs §4.3 `HOLD Medium/Low → WARN` vs §5.1 테이블 `[HOLD] Medium/Low → WARN`. 세 섹션이 같은 문서에 공존하며 구현자가 규범 섹션을 판단할 수 없음.
- **Cross**: (프로바이더 오류로 미평가)
- **Judgment**: 문서 내 §4.2:166과 §4.3:179, §5.1 테이블 217행이 직접 모순됨. 단순 조회로 확인 가능한 내부 불일치이므로 강한 증거로 ACCEPT.
- **Action Required**: §4.2의 `[REJECTED] / [HOLD] Low` 묶음 행을 두 행으로 분리:
  - `[REJECTED] | any | → PASS 기여`
  - `[HOLD] Low | — | → WARN (§4.3 참조)`

---

#### 2. [ACCEPT] [Medium] §7.3 no-fire 검증이 실제 억제 코드 경로를 참조하지 않음

- **Critic**: §7.3은 `is_gate_blocked()` 기준으로 no-fire를 논증하지만, 실제 재발화 억제는 `check_pending_review.py:126`의 `not last_summary.get("has_block", True)` 조건이 담당. 두 코드 경로가 다름에도 §7에서 교차 확인 없음.
- **Cross**: (미평가)
- **Judgment**: Critic이 구체적 파일명과 라인 번호를 제시. `review_gate.py:196`의 `is_gate_blocked()`와 `check_pending_review.py:126` 중 어느 쪽이 no-fire를 실제로 막는지 §7.3에 명시되지 않아 검증 불완전.
- **Action Required**: §7.3에 단계 추가 — "`check_pending_review.py:126`이 `last_round_summary.has_block`을 읽어 재발화를 억제함을 확인; `is_gate_blocked()`는 commit 시점 체크로 별도 경로임을 명기."

---

#### 3. [ACCEPT] [Medium] WARN 출력에서 사유 줄 위치 미확정

- **Critic**: §5.1에서 WARN 시 사유를 "한 줄 추가"하라고만 되어 있어, `## Tier 3 판정: WARN — 사유` (같은 줄) 인지 다음 줄인지 불명확. `_VERDICT_RE`는 현재 형식에서 정상이지만 프롬프트 외 프로바이더나 향후 파서가 다르게 해석할 수 있음.
- **Cross**: (미평가)
- **Judgment**: §7.2 파서 분석이 상세하지만 WARN + 사유 케이스의 완전 샘플이 없다. 형식 고정이 없으면 구현 편차 발생 가능.
- **Action Required**: §5.1에 완전 WARN 출력 샘플 추가. 권장 형식: `## Tier 3 판정: WARN` 다음 줄에 `> WARN 사유: HOLD High 1건, Advisory Medium 2건 있음` 형태로 고정.

---

#### 4. [ACCEPT] [Low] §4.2 테이블에 `[REJECTED]` Medium/High 행 누락

- **Critic**: §4.2 테이블에 `[REJECTED]` 의 임의 severity에 대한 기여(`→ PASS`)가 없음. §5.1에는 있어 구현 영향은 없으나 §4.2 설계 결정 테이블 완결성이 깨짐.
- **Cross**: (미평가)
- **Judgment**: Finding 1 수정 시 동시에 처리 가능한 사소한 보완. 구현 영향 없으므로 Low 유지.
- **Action Required**: Finding 1 수정 시 `[REJECTED] | any | → PASS 기여` 행을 §4.2에 함께 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §4.2 `[HOLD] Low → PASS` vs §4.3/§5.1 `→ WARN` 충돌 | High | ACCEPT | Critic |
| 2 | §7.3 no-fire 검증이 `check_pending_review.py` 경로 누락 | Medium | ACCEPT | Critic |
| 3 | WARN 출력 사유 줄 위치 미확정 | Medium | ACCEPT | Critic |
| 4 | §4.2 테이블 `[REJECTED]` any 행 누락 | Low | ACCEPT | Critic |

---

### Recommendations

구현 진입 전 설계문서에서 아래 3건을 수정한다.

1. **§4.2 테이블 수정** (Finding 1+4 동시 처리): `[REJECTED] / [HOLD] Low` 묶음 행을 `[REJECTED] any → PASS`, `[HOLD] Low → WARN (§4.3 참조)` 두 행으로 분리하고 `[REJECTED] any` 행을 추가.

2. **§7.3 검증 단계 보완** (Finding 2): `check_pending_review.py:126`이 `has_block` 필드를 읽어 재발화를 억제함을 명시. `is_gate_blocked()`가 commit 게이트 전용임을 구분해 기술.

3. **§5.1 WARN 출력 형식 고정** (Finding 3): 사유를 헤더 다음 줄에 블록쿼트(`>`) 형식으로 고정하는 완전 샘플 추가.

> **Cross Review 부재 영향**: 모든 findings가 Critic 단독 출처이므로 신뢰도가 양방향 교차검증 대비 낮다. 단, findings 1·2·4는 문서 텍스트·코드 라인 직접 참조로 충분히 입증됨. Finding 3은 미래 호환성 우려로 판단 여지 있음 — 구현자가 파서 영향 없다고 판단하면 스킵 가능.