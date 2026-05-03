# Phase 2: 판정 라벨 명시화 설계 (재설계 v2)

작성일: 2026-05-03 (v2 — Cross-review WARN 피드백 반영 + deep-think 재구조화)
대상 브랜치: `2026-04-14-build-diet`
선행 완료: Phase 1a (`a8025d25` — af-cross-review.md Step 1+2+3 프롬프트 개선)
선행 검토: 본 문서 v1에 대한 Final Design Review (`5c77af16` 참조) — Critic 발견 4건

---

## §1 배경

CLAUDE.md는 다음 3개 정책에서 verdict 라벨을 직접 의존한다.

| 정책 | 의존 라벨 | 실제 코드 경로 |
|------|----------|--------------|
| BLOCK gate (commit 차단) | `block`, `fail` | `review_gate.py:198` |
| WARN-only no-fire (다음 라운드 자동 발화 억제) | `warn` (≠ block/fail) | `check_pending_review.py:126` |
| max_rounds=2 캡 | round_count (간접) | `check_pending_review.py:110` |

세 정책은 모두 **"BLOCK이냐 아니냐"의 이진 분기**다. 그런데 Phase 1a에서 발견된 갭은:

> **af-cross-review (Tier 3)는 `WARN` 라벨을 한 번도 발화한 적이 없다** (실측: `docs/reviews/` 30건 중 0건).
> 즉, T3는 PASS-only이며, advisory finding의 존재를 사용자에게 신호하지 않는다.

기능적으로는 PASS = WARN (둘 다 has_block = False). 그러나 UX/감사 관점에서는 다음 차이가 있다:

- **사용자 신호**: PASS = "리뷰가 깨끗함" vs WARN = "advisory 발견 있음, 검토 권장"
- **감사 추적**: 잡음 많은 리뷰와 깨끗한 리뷰가 메트릭에서 구분됨
- **미래 정책 hook**: "WARN 3라운드 연속 → BLOCK 승격" 같은 정책의 토대

→ Phase 2는 **labeling 정확화**가 본질이다. 기능적 변화가 아니다(§4.6 명시).

---

## §2 현황 분석 (실측)

### §2.1 af-critic.md (Tier 2)

출력 형식: `Verdict: BLOCK | WARN | PASS`

BLOCK 기준 (`af-critic.md:19-25`): 데이터 손실/무결성 파괴, silent failure, 보안 취약점, 깨진 public API, crash.
WARN 기준: 잠재적 리스크/품질/스타일 전부.

→ **변경 불필요. BLOCK/WARN/PASS 3-라벨 완비.**

### §2.2 af-cross-review.md Step 5 (Tier 3) — 현재

판정 테이블 (`af-cross-review.md:259-266`):

| 출처 | 조건 | 최종 판정 |
|------|------|-----------|
| High/Critical + verified | — | ACCEPT |
| High/Critical + Codex `[보강]` | 코드 근거 충분 | ACCEPT★ |
| High/Critical + Codex `[보강]` | 코드 근거 불충분 | REJECT |
| High/Critical + Codex `[철회]` | — | REJECTED |
| Medium/Low (unchallenged) | — | ACCEPT (advisory) |
| BONUS 항목 | — | advisory only |

BLOCK 조건 (`af-cross-review.md:268`): "ACCEPT 또는 ACCEPT★ 항목 중 Critical/High가 1개 이상"

verdict 라인 (`af-cross-review.md:310-312`): `## Tier 3 판정: BLOCK` 또는 `PASS`. (PASS 외 다른 라벨 없음)

`[HOLD]` 라벨은 원칙으로만 언급(`:351` "보류는 성실한 판정이다") — **템플릿/Step 어디에도 HOLD finding 입구 조건이 정의돼 있지 않다**. 즉 현재 HOLD는 dead label.

### §2.3 verdict 파서 (실측)

**경로 1** — verdict 추출 (`hook_runner.py:_post_agent_record`, line 316):
```python
m = _VERDICT_RE.search(content)        # (?:verdict|판정)\s*[:\-]\s*(block|warn|pass|fail)
if m:  verdict = m.group(1).lower()
else:
    hm = _VERDICT_HEADER_RE.search(content)   # ^#{1,4}\s+(BLOCK|WARN|PASS|FAIL)\b
    verdict = hm.group(1).lower() if hm else "pass"   # ← silent fallback
```

→ 두 패턴 모두 `block|warn|pass|fail` 4종 인식. 단 **둘 다 매칭 실패 시 silent "pass" fallback** (line 344).

**경로 2** — gate 차단 (`review_gate.py:198`):
```python
if r.get("verdict") in ("block", "fail"):  return True, f"verdict-block:{agent}"
```

**경로 3** — 라운드 요약 (`review_gate.py:260`):
```python
has_block = any(v in ("block", "fail") for v in verdicts.values())
state["last_round_summary"]["has_block"] = has_block
```

**경로 4** — no-fire 억제 (`check_pending_review.py:126`):
```python
if round_count >= 1 and last_summary and not last_summary.get("has_block", True):
    return  # 재발화 안 함
```

→ **경로 3+4가 실제 WARN-only no-fire 동작 위치**. v1 §7.3은 경로 2(`is_gate_blocked()`)를 인용해 **잘못된 경로로 검증**했다. v2에서 경로 3+4로 재작성한다(§7.3).

### §2.4 실제 발화 패턴 (`docs/reviews/` 30건)

| 에이전트 | BLOCK | WARN | PASS |
|---------|-------|------|------|
| af-critic (T2) | 다수 | 다수 | 다수 |
| af-cross-review (T3) | 다수 | **0건** | 다수 |

T3가 WARN을 단 한 번도 발화하지 않았음 = 갭 확인.

---

## §3 문제 진단

| ID | 갭 | 위치 | 영향 |
|----|-----|------|------|
| G1 | T3가 WARN을 발화하지 않음 | af-cross-review.md Step 5 매핑 | advisory 신호 손실, WARN-only 정책 의미 없음 |
| G2 | `[ACCEPT]` 라벨이 BLOCK용/Advisory용 두 의미로 중첩 | af-cross-review.md:283/302 (예시) | LLM/리뷰어 혼동, 리뷰 품질 저하 |
| G3 | `[HOLD]` finding 입구 조건 미정의 | Step 3/4 어디에도 진입 조건 없음 | dead label — 원칙 위반 시에도 사용 안 함 |
| G4 | parser silent fallback ("pass") | hook_runner.py:344 | 형식 위반 시 조용히 PASS 기록, 디버깅 어려움 |
| G5 | v1 설계의 §4.2/§4.3/§5.1 3개 테이블 모순 | (v1 문서 자체) | 구현자 판단 혼란 — 본 v2의 1차 동기 |
| G6 | v1 §7.3이 잘못된 코드 경로(`is_gate_blocked()`) 검증 | (v1 문서 자체) | no-fire 보장 불완전 — 본 v2에서 정정 |

---

## §4 설계 결정 (정규)

### §4.1 verdict 라벨 계층 (final verdict 전용)

```
BLOCK > WARN > PASS
```

| 라벨 | gate 동작 | has_block | 의미 |
|------|----------|-----------|------|
| `block` | 차단 | True | 수정 필수 결함 확인 |
| `fail` | 차단 | True | test-gap FAIL (T1 전용) |
| `warn` | 통과 | False | advisory 발견 있음, 사용자 결정 |
| `pass` | 통과 | False | 발견 없음 / 모두 REJECTED |

`hold`는 **final verdict 라벨로 사용하지 않는다**. finding-level에서만 쓰이며, 아래 §4.3 매핑에 따라 BLOCK/WARN/PASS 중 하나에 기여한다.

### §4.2 finding-level 라벨 (af-cross-review 전용)

| finding 라벨 | 의미 | 입구 조건 |
|-------------|------|----------|
| `[ACCEPT]` | Critical/High 지적이 verified (Claude가 코드 직접 확인) | Step 3에서 Challenge 생략한 항목 |
| `[ACCEPT★]` | Critical/High 지적이 challenge 후 Codex `[보강]` + Claude 재확인 | Step 4 Defense 통과 |
| `[ACCEPT-ADV]` | Medium/Low (advisory) | Step 3에서 도전 대상 외 모두 |
| `[REJECTED]` | Codex `[철회]` 또는 Claude challenge 결과 false positive | Step 3/4에서 무효 확정 |
| `[HOLD]` | 근거 불충분 — 판정 보류 | (Phase 2 비목표 — §6 G3 참조) |
| `BONUS` (라벨 prefix 아님) | 변경 무관, advisory only | Codex Round 1에서 `[BONUS]` 분류 |

**라벨 분리(G2 해소)**: 현재 `[ACCEPT]`가 두 의미로 쓰이는 것을 `[ACCEPT]` (Critical/High verified) + `[ACCEPT-ADV]` (Medium/Low advisory)로 분리한다.

### §4.3 단일 정규 매핑 테이블 (THE source of truth)

> 본 테이블이 verdict 매핑의 **유일한 정규 출처**다. 다른 섹션·문서·코드는 이 테이블을 참조하되 재기술하지 않는다 (G5 재발 방지).

| finding 라벨 | severity | final verdict 기여 |
|------------|---------|----------------|
| `[ACCEPT]` / `[ACCEPT★]` | Critical | **BLOCK** |
| `[ACCEPT]` / `[ACCEPT★]` | High | **BLOCK** |
| `[ACCEPT]` / `[ACCEPT★]` | Medium / Low | (해당 없음 — Medium/Low은 challenge 대상 아님) |
| `[ACCEPT-ADV]` | Critical / High | (해당 없음 — Critical/High은 ACCEPT/ACCEPT★ 경로) |
| `[ACCEPT-ADV]` | Medium | **WARN** |
| `[ACCEPT-ADV]` | Low | **WARN** |
| `[REJECTED]` | any | (verdict에 영향 없음 — 무시) |
| `[HOLD]` | Critical / High | **WARN** (Phase 2에서는 미발화. 정의만 둠) |
| `[HOLD]` | Medium / Low | **WARN** (동일 — 미발화) |
| `BONUS` | any | **WARN** |
| (발견 없음) | — | **PASS** |

### §4.4 집계 규칙 (우선순위 내림차순)

```
1. BLOCK 기여 finding ≥ 1   → 최종 verdict = BLOCK
2. (BLOCK 없음) WARN 기여 finding ≥ 1   → 최종 verdict = WARN
3. (BLOCK·WARN 둘 다 없음)   → 최종 verdict = PASS
```

REJECTED는 어느 카운트에도 들어가지 않는다 (verdict-neutral).

### §4.5 [HOLD] 처리 정책

- **HOLD = "근거 불충분으로 판정 보류"**. BLOCK으로 승격하지 않는다 (af-critic.md:19 "명확한 증거" 요건과 정합).
- HOLD severity 무관하게 → WARN 기여 (사용자에게 "확인 필요" 신호).
- **Phase 2 범위 제한**: HOLD finding의 *입구 조건*(언제 HOLD를 발화할지)은 Phase 2 비목표(§6 G3). 매핑만 정의한다.
- 결과: Phase 2 시점에 HOLD finding은 0건 발화 → §4.3의 HOLD 행은 forward-looking spec.

### §4.6 Phase 2의 substantive 변화 = labeling only

**핵심 사실**: 경로 3(`has_block`)와 경로 4(`no-fire`)는 PASS와 WARN을 동등 처리한다. 따라서 Phase 2는:

- ✅ verdict 라인의 **글자**가 바뀐다 (PASS → WARN, advisory가 있을 때).
- ✅ `state.reviews[T3].verdict`의 **값**이 바뀐다 (PASS → WARN).
- ❌ gate 차단 빈도는 바뀌지 않는다 (둘 다 차단 안 함).
- ❌ no-fire 발화 빈도는 바뀌지 않는다 (둘 다 has_block=False).

→ **Phase 2는 정책 변화가 아닌 labeling 정확화다.** 운영 risk가 매우 낮음.

### §4.7 [ACCEPT] Critical 단독 → BLOCK 유지

"단독 [ACCEPT]" = Codex 도전 없이 Claude가 직접 코드 확인한 Critical/High.

**유지 결정**: BLOCK. Claude의 직접 코드 확인은 충분한 evidence. Codex 부재가 곧 false positive를 의미하지 않는다.

### §4.8 Medium 임계 정책

Medium은 BLOCK 임계 없음. Medium 10건이어도 WARN. (af-critic 정책과 일관: 잠재적 리스크/품질 = WARN)

WARN-only no-fire가 Medium 폭탄으로 인한 무한루프를 차단한다 (§4.6 + 경로 4).

---

## §5 변경 파일

### §5.1 `.claude/agents/af-cross-review.md` Step 5 (변경)

§4.3 테이블 + §4.4 집계 규칙을 Step 5에 적용한다. 본 v2 문서가 정규 출처이므로 af-cross-review.md는 **요약 + 본 문서 링크**만 둔다 (G5 재발 방지).

**적용 변경 내역**:

1. **판정 테이블 교체**: 현재 6행 테이블(`af-cross-review.md:259-266`)을 §4.3 11행 테이블로 대체.
2. **집계 규칙 추가**: §4.4 우선순위 3단계를 명시.
3. **finding 라벨 분리**: `[ACCEPT]` advisory → `[ACCEPT-ADV]` 로 라벨명 변경. 출력 예시 #### 4 항목(`af-cross-review.md:302`)을 갱신.
4. **출력 형식 WARN 케이스 추가**: 현재는 BLOCK/PASS 2-case 예시만 있음. WARN 예시 추가:
   ```
   ## Tier 3 판정: WARN
   (사유 한 줄: 예 "Advisory Medium 2건, Low 1건 — 사용자 검토 권장")
   ```
5. **scope-creep / INCOMPLETE 마커 호환성 명시**: 현재 verdict 라인에 붙는 `[scope-creep]` `[INCOMPLETE]` 마커는 WARN/BLOCK/PASS 어느 라벨에도 부착 가능하다는 불변 명시.
6. **finding 헤더에 severity 명기 의무화**: 현재 `#### N. [ACCEPT★] 제목` → `#### N. [ACCEPT★] [High] 제목`. 매핑 결정에 severity가 필요하므로 출력에 명시.
7. **HOLD 라벨 finding-level 정의 추가** (Phase 2에서 미발화이지만 forward-looking):
   - 어떤 라벨로 출력하는지 (`[HOLD]`)
   - severity 표기 의무 (`[HOLD] [High]` 형식)
   - verdict 매핑 (§4.3 인용)

### §5.2 `af-critic.md` (변경 없음)

이미 BLOCK/WARN/PASS 직접 출력. Critic은 자체 판단으로 라벨 결정 — finding-level taxonomy 없음.

### §5.3 `scripts/review_gate.py` (변경 없음)

`_VERDICT_RE`가 `warn`을 이미 인식. `is_gate_blocked()`가 warn을 통과 처리(`block|fail`만 차단). `record_review_done()`가 `has_block`을 정확히 계산 (block/fail만).

### §5.4 `scripts/check_pending_review.py` (변경 없음)

WARN-only no-fire가 `last_summary.has_block`만 본다. WARN/PASS 둘 다 has_block=False → 동일 동작.

### §5.5 `scripts/hook_runner.py` (변경 없음 — 단, G4 후속 검토)

verdict 파서 silent fallback("pass" 기본값, line 344)은 Phase 2 범위 외. 단, **§9 후속 항목**으로 등록: "verdict 라인 누락 시 fail-safe 정책" 검토 필요.

---

## §6 비목표 (Scope OUT)

| ID | 항목 | 이유 |
|----|------|------|
| O1 | `hold` final verdict 라벨 도입 | §4.1 결정: finding-level 전용 |
| O2 | Medium N건 → BLOCK 자동 승격 | §4.8 결정: Medium은 BLOCK 불가 |
| O3 | af-critic HOLD 처리 변경 | af-critic은 자체 BLOCK/WARN/PASS 판단, HOLD 사용 안 함 |
| O4 | review_gate.py 파서 변경 | 이미 WARN 처리 완비 (§2.3 경로 1) |
| O5 | WARN → gate 차단 | 정책 변경 아님 (§4.6) |
| **G3** | **[HOLD] finding 입구 조건 정의** | **Phase 3 이관**: Step 3/4에서 어떤 상황에 HOLD를 발화할지는 deliberation 알고리즘 변경이며 Phase 2 verdict-spec 범위 외 |
| **G4** | **parser silent fallback("pass") 강화** | **Phase 후속 이관 (§9)**: verdict 라인 누락 시 fail-safe(예: error 기록 + WARN 기본값) — 별도 분석 필요 |

---

## §7 검증 계획

### §7.1 단위 시나리오 (af-cross-review.md 변경 후 수동 테스트)

| # | finding 입력 | 기대 verdict | 근거 |
|---|------------|------------|------|
| 1 | `[ACCEPT★]` High 1건 | BLOCK | §4.3 BLOCK 행 + §4.4 우선순위 1 |
| 2 | `[ACCEPT-ADV]` Medium 3건 | WARN | §4.3 WARN 행 + §4.4 우선순위 2 |
| 3 | `[ACCEPT]` Critical 1건 + `[ACCEPT-ADV]` Medium 5건 | BLOCK | BLOCK 우선 (§4.4) |
| 4 | `[REJECTED]` × N | PASS | §4.3 verdict-neutral |
| 5 | 발견 없음 | PASS | §4.3 (발견 없음) 행 |
| 6 | BONUS Critical 2건 (PRIMARY 0건) | WARN | §4.3 BONUS 행 |
| 7 | `[HOLD]` High 1건 (Phase 2 미발화이지만 spec 검증) | WARN | §4.3 HOLD 행 (forward-looking) |
| 8 | `[ACCEPT★]` High 1건 + `[REJECTED]` Critical 1건 | BLOCK | REJECTED 무시, ACCEPT★ High → BLOCK |

### §7.2 파서 호환성 검증

verdict 라인 형식: `## Tier 3 판정: WARN [scope-creep]`

`_VERDICT_RE` 매칭:
- 패턴: `(?:verdict|판정)\s*[:\-]\s*(block|warn|pass|fail)`
- 입력의 `판정: WARN` 부분이 group 1에 `warn` 캡처 → 매칭 ✓
- 후행 `[scope-creep]`은 무시 → ✓

`_VERDICT_HEADER_RE` 매칭 (fallback):
- 패턴: `^#{1,4}\s+(BLOCK|WARN|PASS|FAIL)\b`
- 입력에서 `## Tier 3 판정: WARN`은 `##` 다음에 `Tier`가 와서 미매칭
- 그러나 `_VERDICT_RE`가 먼저 매칭하므로 fallback 불필요 → ✓

→ **파서 변경 불필요 확정**.

**파서 collision 우려**: `_VERDICT_RE.search()`는 첫 매칭을 반환. af-cross-review 출력에 verdict 라인이 1개만 있어야 한다 (이전 라운드 인용에서 "Verdict: BLOCK" 같은 텍스트가 본문에 등장하면 잘못 캡처될 수 있음). § 5.1 변경 6 (severity 명기)에서도 finding 헤더가 `Verdict:` 형식이 아니므로 충돌 없음. **불변 추가**: af-cross-review.md 출력에는 `Verdict:` 또는 `판정:` 콜론 형식이 최종 라인 1회만 등장해야 한다 (Step 5 출력 형식 주석에 명시).

### §7.3 WARN-only no-fire 동작 검증 (실제 코드 경로 기반)

**시나리오**: T3가 advisory만 발견 → verdict=warn 발화 → 다음 사용자 편집 시 자동 재발화 안 됨.

**경로 추적**:

1. **T3 에이전트가 출력**: `## Tier 3 판정: WARN`
2. **`hook_runner.py:339`** `_VERDICT_RE.search(content)` → group(1)="warn" → `verdict = "warn"`
3. **`hook_runner.py:354`** `record_review_done(workspace, "af-cross-review", 3, "warn")`
4. **`review_gate.py:241`** `state["reviews"]["af-cross-review"]["verdict"] = "warn"`
5. 라운드 종결 시 (모든 required tier 완료):
   **`review_gate.py:260`** `has_block = any(v in ("block","fail") for v in verdicts.values())`
   - T1=pass, T2=warn (advisory), T3=warn → `has_block = False`
   **`review_gate.py:262`** `state["last_round_summary"]["has_block"] = False`
6. **다음 사용자 편집 → UserPromptSubmit hook → `check_pending_review.py:126`**:
   ```python
   if round_count >= 1 and last_summary and not last_summary.get("has_block", True):
       return  # 재발화 안 함
   ```
   - `round_count=1`, `last_summary.has_block=False` → 조건 충족 → **return → 자동 재발화 없음** ✓

→ **WARN-only no-fire 정상 동작 확정**. v1 §7.3에서 잘못 인용했던 `is_gate_blocked()`(경로 2)는 commit 시점 gate이며 no-fire 경로가 아니다(G6 정정).

### §7.4 commit gate 동작 검증

**시나리오**: T3 verdict=warn → `git commit` 시도.

1. pre-commit hook → **`review_gate.py:198`**: `r.get("verdict") in ("block","fail")` — warn은 미해당 → 통과 ✓
2. 다른 tier도 모두 non-block이라면 `is_gate_blocked()` → False → commit 통과 ✓

→ **WARN은 commit을 차단하지 않는다** (정책 의도와 일치).

### §7.5 BLOCK 시나리오 회귀 검증

기존 BLOCK 동작이 깨지지 않는지 확인.

| 시나리오 | 기대 |
|---------|------|
| T3 verdict=block, T1/T2 pass | gate BLOCK (`review_gate.py:198`) |
| T3 verdict=block | next-round 재발화 ✓ (`has_block=True`이므로 no-fire 트리거 안 함) |

---

## §8 구현 순서

1. 본 v2 문서에 대해 **af-cross-review만 교차검증** 실행 (단일 설계문서 정책).
2. 검증 PASS 확인 후, `.claude/agents/af-cross-review.md` Step 5에 §5.1 변경 1~7 적용.
3. af-cross-review.md 변경에 대해 **af-test-runner만** 재실행 (Tier 1: 에이전트 설정 파일).
4. 단위 시나리오(§7.1) 8건 수동 회귀 (다음 .py 변경 사이클에서 자연스럽게 검증).
5. 커밋. CLAUDE.md 정책 변경 없음 (parser·gate 동작 불변).

---

## §9 운영 / 롤백 계획

### §9.1 운영 모니터링 (1주 baseline)

- **메트릭**: `data/skill-usage.jsonl` (또는 `review_metrics_logger`) 에서 T3 verdict 분포 측정.
- **기대**: PASS 비율 ↓ (현재 100% 중 일부가 WARN으로 이동), WARN 비율 ↑.
- **우려 지표**: WARN 비율 > 80% → advisory 노이즈 과다 가능성 (Medium 임계 재검토 트리거 — §10 추적).

### §9.2 롤백 트리거

다음 중 하나라도 발생하면 §5.1 변경 revert:

- WARN-only no-fire가 의도와 달리 작동 (재발화 빈도 측정으로 확인).
- WARN 메시지가 사용자에게 BLOCK으로 오인 (UX 피드백).
- parser collision 발견 (verdict 라인 외 텍스트가 캡처되는 사례).

### §9.3 롤백 절차

```bash
git revert <commit-hash-of-af-cross-review-md-change>
# CLAUDE.md, scripts/는 무변경이므로 단일 revert로 완료
```

**roll-back safe property**: §5.2~§5.4가 무변경이므로 .md 파일 1개만 revert하면 된다.

---

## §10 미결 사항 (다음 세션 / Phase 3+)

| ID | 항목 | 우선순위 | 이관처 |
|----|------|--------|------|
| F1 | [HOLD] finding 입구 조건 정의 (G3) | High | Phase 3 (deliberation 알고리즘) |
| F2 | parser silent "pass" fallback 강화 (G4) | Medium | 후속 분석 — error 기록 + 기본값 정책 |
| F3 | WARN 비율 baseline 측정 (1주 운영 후) | Medium | Phase 2 검증 후 |
| F4 | Medium → BLOCK 임계 재검토 | Low | WARN 비율 > 80% 시 트리거 |
| F5 | BONUS Critical/High WARN 적정성 | Low | 운영 데이터 기반 판단 |
| F6 | finding 라벨에 `[ACCEPT★]` 별표 표기의 자동화 가능성 | Low | LLM 재현성 측정 후 |

---

## §11 v1 → v2 변경 요약 (감사 추적용)

| 항목 | v1 (`5c77af16`) | v2 (본 문서) |
|------|----------------|-------------|
| 매핑 테이블 | §4.2 / §4.3 / §5.1 — 3곳 분산 + HOLD Low 모순 | §4.3 단일 정규 테이블 |
| no-fire 경로 검증 | §7.3에서 `is_gate_blocked()` 인용 (잘못된 경로) | §7.3에서 `check_pending_review.py:126` + `review_gate.py:260` 경로 추적 |
| HOLD 정책 | 입구 조건 미정 + 매핑만 모순 | 매핑 정의 + 입구 조건 명시적 Phase 3 이관 |
| parser fallback | 미언급 | G4 식별 + §9 후속 등록 |
| Phase 2의 substance | "WARN 라벨 도입" (정책 변화처럼 기술) | "labeling only — 기능 불변" 명시 (§4.6) |
| 롤백 계획 | 없음 | §9에 명시 |
| 출력 형식 명세 | severity 명기 누락, scope-creep 호환성 미언급 | §5.1 변경 5~7에 명시 |
| 정규 출처 명확화 | 다중 테이블로 모호 | "§4.3가 THE source of truth" 선언 |
