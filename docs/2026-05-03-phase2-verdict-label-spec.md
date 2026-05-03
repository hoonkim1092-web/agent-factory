# Phase 2: 판정 라벨 명시화 설계

작성일: 2026-05-03  
대상 브랜치: `2026-04-14-build-diet`  
선행 완료: Phase 1a (`a8025d25` — af-cross-review.md Step 1+2+3 프롬프트 개선)

---

## §1 배경

CLAUDE.md는 다음 3개 정책에서 verdict 라벨을 직접 의존한다.

| 정책 | 의존하는 라벨 |
|------|-------------|
| BLOCK 정책: Critical/High ACCEPT ≥ 1 → commit 차단 | `block` |
| WARN-only no-fire: 직전 라운드 BLOCK 없이 완료 → 자동 재발화 안 함 | `warn` (≠ block) |
| max_rounds=2 캡: 같은 큐 최대 2라운드 | round_count (간접) |

세 정책이 "BLOCK이냐 아니냐"에만 의존하면 충분할 것 같지만,  
**WARN 라벨이 발화되지 않으면 WARN-only no-fire 정책이 동작하지 않는다.**

---

## §2 현황 분석 (실측)

### §2.1 af-critic.md (Tier 2)

출력 라인 형식:
```
Verdict: BLOCK | WARN | PASS
```

BLOCK 기준 (`af-critic.md:19-25`):
- 데이터 손실/무결성 파괴, silent failure, 보안 취약점, 깨진 public API, crash 유발

WARN 기준:
- 위에 해당하지 않는 잠재적 리스크/품질/스타일 전부

→ **Tier 2 라벨 BLOCK/WARN/PASS 완비. 변경 불필요.**

### §2.2 af-cross-review.md Step 5 (Tier 3)

출력 라인 형식 (현재):
```
## Tier 3 판정: BLOCK
```
또는
```
## Tier 3 판정: PASS
```

판정 테이블 (현재):

| 출처 | 조건 | 최종 판정 |
|------|------|-----------|
| High/Critical + verified | — | ACCEPT |
| High/Critical + [보강] | 코드 근거 충분 | ACCEPT★ |
| High/Critical + [보강] | 코드 근거 불충분 | REJECT |
| High/Critical + [철회] | — | REJECTED |
| Medium/Low (unchallenged) | — | ACCEPT (advisory) |
| BONUS 항목 | — | advisory only |

BLOCK 조건: "ACCEPT 또는 ACCEPT★ 항목 중 Critical/High가 1개 이상"

**갭 1**: Medium/Low ACCEPT (advisory)가 있을 때 → `PASS` 출력 중 (실제로는 `WARN`이어야 함)  
**갭 2**: `[HOLD]` 라벨이 finding에는 쓰이지만 최종 verdict 처리 규칙 없음  
**갭 3**: WARN 라벨을 한 번도 발화하지 않음 → WARN-only no-fire 정책이 Tier 3에서 작동 불가

### §2.3 review_gate.py 파서 (실측)

`scripts/review_gate.py:25-31`:
```python
_VERDICT_RE = re.compile(
    r"(?:verdict|판정)\s*[:\-]\s*(block|warn|pass|fail)",
    re.IGNORECASE | re.MULTILINE,
)
_VERDICT_HEADER_RE = re.compile(
    r"^#{1,4}\s+(BLOCK|WARN|PASS|FAIL)\b",
    re.IGNORECASE | re.MULTILINE,
)
```

`is_gate_blocked()` 차단 조건 (`review_gate.py:196-199`):
```python
if r.get("verdict") in ("block", "fail"):
    return True, f"verdict-block:{agent}"
```

→ `warn` 은 파싱되고 기록되지만 gate를 차단하지 않는다.  
→ **review_gate.py는 이미 WARN을 올바르게 처리. 변경 불필요.**

### §2.4 실제 발화 패턴 (docs/reviews/ 30건 분석)

| 에이전트 | BLOCK | WARN | PASS |
|---------|-------|------|------|
| af-critic (T2) | 다수 | 다수 | 다수 |
| af-cross-review (T3) | 다수 | **0건** | 다수 |

Tier 3이 WARN을 단 한 번도 발화하지 않았음 = 갭 3 확인.

---

## §3 문제 진단

### §3.1 WARN 라벨 미발화 (Gap 3)

현재 af-cross-review Step 5:
- ACCEPT/ACCEPT★ Critical/High ≥ 1 → BLOCK
- 나머지 전부 → PASS

**결과**: Medium/Low Advisory 항목이 10개여도 PASS. WARN-only no-fire 정책이 Tier 3에서 의미 없음.  
**기대**: Medium+ 발견이 있으면 WARN을 발화해 사용자에게 "advisory 있음" 신호를 줘야 한다.

### §3.2 [HOLD] 처리 미정의 (Gap 2)

`af-cross-review.md:351` "보류는 성실한 판정이다. 불확실하면 HOLD가 올바른 답이다."

[HOLD]는 finding-level 라벨(`[HOLD] [Medium]`, `[HOLD] [Low]`)로 쓰이지만,  
이 항목이 BLOCK/WARN/PASS 중 어느 라벨에 매핑되는지 명시가 없다.

실측 샘플:
- `docs/reviews/2026-05-01-233947-...`: `[HOLD] [Medium]` — 최종 verdict는 BLOCK (다른 High 있어서)
- `docs/reviews/2026-04-30-081944-...`: `[HOLD] [Medium]` — 최종 verdict는 WARN (af-critic)
- 모두 Critical HOLD 없음 — Critical HOLD 케이스 실측 없음

### §3.3 ACCEPT 라벨 중의성 (Gap 4 — 기존 항목)

Step 5 테이블에 `[ACCEPT]` 라벨이 두 가지 의미로 쓰인다:
- `[ACCEPT]` Critical/High verified → BLOCK 유발
- `[ACCEPT]` advisory Medium/Low → No-BLOCK

출력 형식에서 둘이 같은 이름 → 파서가 의미를 혼동할 수 없으므로 실질적 버그는 없지만,  
설계 문서와 에이전트 지시문에서 혼란을 유발. → 라벨 분리.

---

## §4 설계 결정

### §4.1 verdict 라벨 계층 확정

```
BLOCK > WARN > PASS
```

| 라벨 | gate 동작 | 의미 |
|------|----------|------|
| `block` | 차단 | 수정 필수 결함 확인 |
| `warn` | 통과 | advisory 발견 있음, 사용자 결정 |
| `pass` | 통과 | 발견 없음 |
| `fail` | 차단 | test-gap FAIL (T1 전용) |
| `hold` | 미지원 | finding-level 전용, final verdict 아님 |

**결정**: `hold`는 final verdict 라벨로 사용하지 않는다.  
[HOLD] finding은 아래 §4.3의 severity에 따라 BLOCK/WARN/PASS 중 하나에 기여한다.

### §4.2 af-cross-review Step 5 verdict 매핑 테이블 (신규)

| finding 결과 | 조건 | final verdict 기여 |
|-------------|------|-------------------|
| `[ACCEPT]` / `[ACCEPT★]` Critical | — | → **BLOCK** |
| `[ACCEPT]` / `[ACCEPT★]` High | — | → **BLOCK** |
| `[HOLD]` Critical | 불확실 — 코드 근거 불충분 | → **WARN** (BLOCK 승격 금지) |
| `[HOLD]` High | 불확실 — 코드 근거 불충분 | → **WARN** |
| `[ACCEPT]` advisory Medium | — | → **WARN** |
| `[ACCEPT]` advisory Low | — | → WARN (§4.4에서 집계) |
| `[REJECTED]` / `[HOLD]` Low | — | → PASS 기여 (무시) |
| BONUS 항목 | advisory only | → WARN 기여 (count 증가) |

**집계 규칙 (우선순위 내림차순)**:
1. BLOCK 기여 항목 ≥ 1 → 최종 verdict = **BLOCK**
2. WARN 기여 항목 ≥ 1 (BLOCK 없음) → 최종 verdict = **WARN**
3. 모두 PASS 기여 / 발견 없음 → 최종 verdict = **PASS**

### §4.3 [HOLD] 처리 규칙 (신규)

- **HOLD = "근거 불충분으로 판정 보류"**
- HOLD를 BLOCK으로 승격하지 않는다. "확신이 없으면 commit을 막지 않는다."
- HOLD Critical/High → WARN (사용자에게 "확인 필요" 신호)
- HOLD Medium/Low → WARN (동일)
- HOLD가 유일한 finding이면 → WARN 발화 (기존 PASS 발화 오류 수정)

**근거**: BLOCK은 "명확한 증거" 요건(af-critic.md:19)과 동일한 기준. 불확실한 HOLD는 이 기준 미달.

### §4.4 Medium 임계 정책

- **Medium은 BLOCK 임계 없음.** Medium 10개여도 WARN.
- **WARN-only no-fire** 정책 하에서 WARN는 자동 재발화를 막는다. → Medium 폭탄으로 인한 무한루프 없음.
- 이는 기존 af-critic 정책(`잠재적 리스크/품질 = WARN`)과 일관.

### §4.5 단독 [ACCEPT] Critical → BLOCK 유지

"단독 [ACCEPT]" = Challenge 없이 Claude가 직접 코드 확인한 Critical.

→ **BLOCK 유지**.  
근거: Claude가 파일을 직접 읽고 Critical 결함을 확인한 것은 충분한 evidence. Codex 확인 없음이 곧 false positive를 의미하지 않는다.

---

## §5 변경 파일

### §5.1 af-cross-review.md Step 5 (변경)

**변경 내용**:

1. 판정 테이블에 `[HOLD]` 행 추가 (§4.3)
2. `[ACCEPT]` advisory → `[ACCEPT-ADV]` 로 라벨 분리 (§3.3 중의성 해소)
3. verdict 집계 규칙 3단계 명시 (§4.2)
4. 출력 형식에 WARN 케이스 추가

**신규 판정 테이블**:

| finding 라벨 | 심각도 | 최종 verdict 기여 |
|------------|--------|----------------|
| `[ACCEPT]` `[ACCEPT★]` | Critical | → BLOCK |
| `[ACCEPT]` `[ACCEPT★]` | High | → BLOCK |
| `[HOLD]` | Critical / High | → WARN |
| `[HOLD]` | Medium / Low | → WARN |
| `[ACCEPT-ADV]` | Medium | → WARN |
| `[ACCEPT-ADV]` | Low | → WARN |
| `[REJECTED]` | any | → PASS 기여 |
| BONUS 항목 | Critical / High | → WARN |
| BONUS 항목 | Medium / Low | → WARN |

**집계**:
```
BLOCK 기여 ≥ 1 → "## Tier 3 판정: BLOCK"
WARN 기여 ≥ 1 (BLOCK 없음) → "## Tier 3 판정: WARN"
PASS 기여만 (BLOCK/WARN 없음) → "## Tier 3 판정: PASS"
```

**출력 형식 추가**:
```
## 교차 검증 결과 (참여: codex_cli — 4-Round Deliberation)
...

### 수용 항목 적용 여부
Critical/High ACCEPT/ACCEPT★ 항목은 즉시 수정이 필요합니다.
HOLD/Advisory 항목은 사용자 판단에 따라 수정하세요.

## Tier 3 판정: WARN
```
(`WARN` 시 적용 사유를 한 줄 추가: e.g., "HOLD High 1건, Advisory Medium 2건 있음")

**라벨 분리 (`[ACCEPT]` → `[ACCEPT-ADV]`)**:

Step 5 출력 형식에서:
- `#### N. [ACCEPT] 제목 (verified — Challenge 생략)` → 그대로 (Critical/High verified)
- `#### N. [ACCEPT] 제목 (advisory — Medium/Low)` → `[ACCEPT-ADV]` 로 변경

파서 영향: `review_gate.py`는 verdict 라인만 파싱하므로 finding-level 라벨 변경 무영향.

### §5.2 af-critic.md (변경 없음)

이미 BLOCK/WARN/PASS 완비.

### §5.3 review_gate.py (변경 없음)

`warn` 인식 및 통과 처리 이미 구현됨 (`review_gate.py:196-199`).

---

## §6 비목표 (Scope OUT)

| 항목 | 이유 |
|------|------|
| HOLD final verdict 지원 | §4.1 결정: finding-level 전용 |
| Medium N개 이상 → BLOCK 자동 승격 | §4.4 결정: Medium은 BLOCK 불가 |
| af-critic HOLD 처리 변경 | af-critic은 자체 BLOCK/WARN/PASS 판단, HOLD 사용 안 함 |
| review_gate.py 파서 변경 | 이미 WARN 처리 완비 |
| WARN → gate 차단 | 정책 변경 아님 |

---

## §7 검증 계획

### §7.1 단위 검증 (af-cross-review.md 변경 후)

수동 시나리오 테스트:

| 시나리오 | 기대 verdict |
|----------|-------------|
| ACCEPT★ High 1건만 있음 | BLOCK |
| HOLD High 1건만 있음 (ACCEPT High 없음) | WARN |
| ACCEPT-ADV Medium 3건만 있음 | WARN |
| 전부 REJECTED | PASS |
| 발견 없음 ("No BLOCK-level findings") | PASS |
| ACCEPT Critical + HOLD High | BLOCK (BLOCK 기여 우선) |

### §7.2 파서 호환성 확인

`review_gate.py:_VERDICT_RE` 패턴 `(verdict|판정)\s*[:\-]\s*(block|warn|pass|fail)` 으로 다음이 파싱됨:
- `## Tier 3 판정: WARN` → 패턴 미일치 (한국어 헤더 `##` 형식)
- `_VERDICT_HEADER_RE: ^#{1,4}\s+(WARN)\b` → **일치** ✓

단, `## Tier 3 판정: WARN` 형식은 `_VERDICT_HEADER_RE`에 의해 `WARN`이 캡처되어야 한다.  
실제 확인: `^#{1,4}\s+(BLOCK|WARN|PASS|FAIL)\b`는 `## Tier 3 판정: WARN`에서 매칭 실패 —  
`##` 다음에 바로 `WARN`이 오지 않고 `Tier 3 판정:` 텍스트가 사이에 있기 때문.

→ `_VERDICT_RE`: `"판정"\s*[:\-]\s*(warn)` 패턴이 필요. 확인:  
`(?:verdict|판정)\s*[:\-]\s*(block|warn|pass|fail)` — `판정: WARN`에 매칭 ✓  
`## Tier 3 판정: WARN` → `판정: WARN` 부분이 내장 → `_VERDICT_RE` **매칭 ✓**

→ 파서 변경 불필요 확정.

### §7.3 WARN-only no-fire 동작 확인

시나리오: T3 verdict = warn → `record_review_done("af-cross-review", tier=3, verdict="warn")` 기록  
→ `is_gate_blocked()`: warn은 `("block", "fail")`에 없음 → PASS  
→ WARN-only no-fire: `last_round_summary.has_block = False` → 재발화 없음 ✓

---

## §8 구현 순서

1. 이 설계문서 → af-cross-review만 교차검증 (AF_SKIP_PROVIDER=codex, codex usage limit)
2. PASS 시 `.claude/agents/af-cross-review.md` Step 5 업데이트
3. af-cross-review 자체에 대한 af-test-runner (설정 파일 변경이므로 Tier 1)
4. 커밋

---

## §9 미결 사항 (다음 세션)

| 항목 | 내용 |
|------|------|
| WARN 발화 후 운영 관찰 | Phase 1a 1주 운영 데이터 수집 후 WARN 비율 측정 |
| Medium → BLOCK 임계 재검토 | WARN 비율이 너무 높으면 Medium을 PASS로 내리는 것 검토 |
| BONUS Critical/High WARN 적정성 | BONUS는 "변경 무관" 항목 — WARN이 과도한지 운영 후 판단 |
