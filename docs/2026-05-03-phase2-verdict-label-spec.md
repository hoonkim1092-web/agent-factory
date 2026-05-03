# Phase 2: 판정 라벨 명시화 설계 (재설계 v5)

작성일: 2026-05-03 (v5 — v4 Critic 8건 정정, Critical 1건(§5.4 v3 BLOCK 재도입) + High 4건 + Medium 3건 BLOCK 해제)
대상 브랜치: `2026-04-14-build-diet`
선행 완료: Phase 1a (`a8025d25` — af-cross-review.md Step 1+2+3 프롬프트 개선)
선행 검토:
  - v2 (`f8be0794`)에 대한 Critic Review — 8건 (Cross-review provider error로 미수행)
  - v3 (`d9cc3304`)에 대한 Critic Review (`docs/reviews/2026-05-03-224512-...`) — Critic 단독 BLOCK 8건 + Missing 권장 4건
  - v4 (`2174812c`)에 대한 Final Design Review (`docs/reviews/2026-05-03-231445-...`) — Critic 단독 8건 ACCEPT [Critical 1 + High 4 + Medium 3] (Cross-review provider error)
  - **v5 cross-review 재실행 권장** (codex usage limit 회복: 2026-05-05 15:37 KST) — 단, 사용자 결정에 따라 Claude 단독 검증으로 진행 가능

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

→ Phase 2는 **labeling 정확화**가 본질이다(§4.6). 단, **labeling 변화가 메트릭/파서를 통과해 효과를 검증할 수 있어야 substantive하다** — 이를 위해 v3은 코드 변경 3건(`review_metrics_logger.py`, `hook_runner.py`, `review_gate.py`)을 Phase 2 차단 의존성으로 격상했고, v4는 운영 메트릭 sink 결손(G11)을 추가로 식별해 `check_pending_review.py`까지 4건의 .py 변경으로 확장했으며, **v5는 v4 §5.4의 `_log_hook_event` 시그니처 모순(v3 BLOCK 재도입)과 sink 폭발을 정정**한다 — 코드 4건 + 테스트 2건 + agent md 1건 = **7파일 단일 commit** (§5.3/§5.4/§5.5/§5.6 + tests 2 + af-cross-review.md, §8.2).

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

**경로 1** — verdict 추출 (`hook_runner.py:_post_agent_record`, line 316-346):
```python
m = _VERDICT_RE.search(content)        # (?:verdict|판정)\s*[:\-]\s*(block|warn|pass|fail)
if m:  verdict = m.group(1).lower()
else:
    hm = _VERDICT_HEADER_RE.search(content)   # ^#{1,4}\s+(BLOCK|WARN|PASS|FAIL)\b
    verdict = hm.group(1).lower() if hm else "pass"   # ← silent fallback (G4)
```

→ 두 패턴 모두 `block|warn|pass|fail` 4종 인식. 단 **둘 다 매칭 실패 시 silent "pass" fallback** (line 344). LLM이 `Tier 3: WARN` 같이 콜론·헤더 형식이 어긋나면 PASS로 기록되어 Phase 2 효과가 침묵 무력화됨 (§3 G4).

**경로 1.5** — `_VERDICT_RE`는 `re.MULTILINE | re.IGNORECASE`로 `re.search()` 첫 매칭 반환. af-cross-review가 본문에 prior round 인용("이전 라운드 판정: BLOCK")을 포함하면 본문이 verdict로 캡처될 수 있음 (§3 G7).

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

→ **경로 3+4가 실제 WARN-only no-fire 동작 위치**. v1 §7.3은 경로 2(`is_gate_blocked()`)를 인용해 잘못된 경로로 검증했다. v2/v3에서 경로 3+4로 재작성한다(§7.3).

### §2.4 review_metrics_logger.py (실측 — v3 신규 분석)

`scripts/review_metrics_logger.py:31-34`:
```python
_FINDING_RE = re.compile(
    r'\[(?:ACCEPT[★*]?|WARN|BLOCK|REJECTED)\]',
    re.IGNORECASE,
)
```

→ 본 정규식은 v2가 도입한 `[ACCEPT-ADV]`를 매칭하지 못한다. `parse_findings_count()`가 0으로 무너지면 `compute_report()`의 finding-rate 메트릭이 모두 손상되고 §9.1 운영 검증(WARN 비율 측정)이 self-defeat됨.

**테스트 영향**: `tests/test_review_metrics_logger.py:34-57`은 기존 4-라벨만 가정 → `[ACCEPT-ADV]` 도입 즉시 회귀.

### §2.5 실제 발화 패턴 (`docs/reviews/` 30건)

| 에이전트 | BLOCK | WARN | PASS |
|---------|-------|------|------|
| af-critic (T2) | 다수 | 다수 | 다수 |
| af-cross-review (T3) | 다수 | **0건** | 다수 |

T3가 WARN을 단 한 번도 발화하지 않았음 = 갭 확인.

---

## §3 문제 진단

| ID | 갭 | 위치 | 영향 | v4 처리 |
|----|-----|------|------|--------|
| G1 | T3가 WARN을 발화하지 않음 | af-cross-review.md Step 5 매핑 | advisory 신호 손실 | §5.1 |
| G2 | `[ACCEPT]` 라벨이 BLOCK용/Advisory용 두 의미로 중첩 | af-cross-review.md:283/302 | LLM/리뷰어 혼동 | §5.1 |
| G3 | `[HOLD]` finding 입구 조건 미정의 | Step 3/4 어디에도 진입 조건 없음 | dead label | **Phase 3로 완전 이관 — v3에서 정의도 빼기** (§5.1 / §6) |
| G4 | parser silent fallback ("pass") | hook_runner.py:344 | 형식 위반 시 조용히 PASS | **detection-only 해소** (`_log_hook_event("verdict_fallback")`, §5.5) — gate-level 차단은 Phase 3 이관 (v4 정정: v3의 "fail-safe" 표현 강등 — §4.6) |
| G5 | v1/v2 `§4.2/§4.3/§5.1` 다중 테이블 | (v1·v2 문서) | 구현 혼란 | v2 §4.3 단일 정규 테이블로 정리 완료 |
| G6 | v1 §7.3이 잘못된 코드 경로(`is_gate_blocked()`) 인용 | (v1 문서) | no-fire 보장 불완전 | v2 §7.3 정정 완료 |
| G7 | `_VERDICT_RE.search()` collision — 본문에 prior round 판정 인용 시 캡처 가능 | review_gate.py:25-28 | LLM 자기 통제 100% 의존 | **Phase 2 차단 — verdict fence 도입** (§5.1 변경 8) + **두 정규식 last-position 결합 알고리즘 명시** (§5.3, v4 정정) |
| G8 | `_FINDING_RE` 회귀 — `[ACCEPT-ADV]` 미매칭 | review_metrics_logger.py:31-34 | findings_count=0, §9.1 운영 검증 self-defeat | **정규식 확장** (§5.6) |
| G9 | severity 누락 매핑 결정 불가 | §4.3 (매핑 입력) | LLM이 severity 잊을 시 silent miscategorization | **§4.3 fail-safe default + [REJECTED] verdict-neutral 우선 단서** (§4.3 / §7.1 시나리오 11, v4 정정) |
| G10 | BONUS finding의 출력 헤더 라벨 미정의 | §5.1 (출력 형식) | 검증 시나리오 입력 명세 불완전 | **§5.1 변경 6에 BONUS 헤더 규칙 + REJECTED severity 생략 허용 명시** (v4 정정) |
| **G11 (v4 신규)** | **§9.2 롤백 트리거 #1 측정 방법 미정의 — `verdict_fallback`과 no-fire 오작동은 직접 인과 관계 없음** | check_pending_review.py:126-138 | 롤백 트리거 falsifiable 불가, §9.1 운영 검증 self-defeat | **§5.4 신규 — `_log_hook_event("warn_only_suppressed")` 1줄 추가** (§5.4 / §9.2 트리거 #1 재정의) |
| **G12 (v4 신규)** | **`_SCOPE_CREEP_RE` 전역 검색 vs §5.1 변경 5 fence-내부 한정 정책 충돌** | review_metrics_logger.py:_SCOPE_CREEP_RE | 메트릭 손상 또는 정책 모호 | **§5.6에 정책 명시 — scope-creep는 verdict 라벨이 아니므로 fence 외부 검색 유지** (단순성) |

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

`hold`는 **final verdict 라벨로 사용하지 않는다**. v3에서 finding-level에서도 사용하지 않는다 (G3 Phase 3 완전 이관).

### §4.2 finding-level 라벨 (af-cross-review 전용 — v3)

| finding 라벨 | 의미 | 입구 조건 |
|-------------|------|----------|
| `[ACCEPT]` | Critical/High 지적이 verified (Claude가 코드 직접 확인) | Step 3에서 Challenge 생략한 항목 |
| `[ACCEPT★]` | Critical/High 지적이 challenge 후 Codex `[보강]` + Claude 재확인 | Step 4 Defense 통과 |
| `[ACCEPT-ADV]` | Medium/Low (advisory) | Step 3에서 도전 대상 외 모두 |
| `[REJECTED]` | Codex `[철회]` 또는 Claude challenge 결과 false positive | Step 3/4에서 무효 확정 |
| `[BONUS]` | 변경 무관 advisory (Codex Round 1에서 분류) | Codex Round 1 BONUS 분류 |

**v3 변경 (G2 해소)**: `[ACCEPT]` 분리 = `[ACCEPT]` (Critical/High verified) + `[ACCEPT-ADV]` (Medium/Low advisory).
**v3 변경 (G3 Phase 3 이관)**: `[HOLD]` 라벨은 v3 finding 라벨에서도 빠진다. Phase 3 deliberation 알고리즘 변경 시 재도입.
**v3 변경 (G10 해소)**: `[BONUS]`를 finding 라벨로 승격. Step 5 출력 헤더 형식 = `#### N. [BONUS] [Severity] 제목`.

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
| `[REJECTED]` | any (severity **생략 허용**) | (verdict-neutral — 무시 — fail-safe보다 우선) |
| `[BONUS]` | any | **WARN** |
| **(severity 누락 — fail-safe default, `[REJECTED]` 외 라벨 한정)** | (지정 안 됨) | **BLOCK** |
| (발견 없음) | — | **PASS** |

**§4.3 변경 (G9 해소)**: severity bracket이 누락된 finding은 BLOCK 안전 default로 처리한다. Critical/High 가능성이 있는 항목을 silent miscategorization로 잃지 않기 위함. LLM 출력 정확성에 의존하지 않는 fail-safe.

**§4.3 v4 정정 (Critic #2)**: `[REJECTED]` finding은 verdict-neutral이 fail-safe BLOCK보다 **우선**한다. 즉 `#### 1. [REJECTED] 제목` (severity 누락)은 어느 카운트에도 들어가지 않는다. 입구 조건은 §5.1 변경 6에서 "REJECTED는 severity 생략 허용, 그 외 5종 라벨(`[ACCEPT]`/`[ACCEPT★]`/`[ACCEPT-ADV]`/`[BONUS]`)은 severity 의무"로 명시한다. 이는 Codex가 false positive로 인정한 항목 때문에 BLOCK이 발생하는 의도-반전을 차단한다.

### §4.4 집계 규칙 (우선순위 내림차순)

```
0. [REJECTED] finding은 어느 카운트에도 들어가지 않는다 (verdict-neutral, severity 무관).
1. BLOCK 기여 finding ≥ 1   → 최종 verdict = BLOCK
2. (BLOCK 없음) WARN 기여 finding ≥ 1   → 최종 verdict = WARN
3. (BLOCK·WARN 둘 다 없음)   → 최종 verdict = PASS
```

severity 누락 finding은 (§4.3 단서대로 `[REJECTED]`가 아닌 한) §4.3 fail-safe로 BLOCK 1건이 카운트된다.

### §4.5 [HOLD] 처리 정책 (v3 — Phase 3 완전 이관)

v2까지는 finding-level `[HOLD]` forward-looking 정의를 두었으나, **prompt drift 위험**(G3) 때문에 v3은 정의도 제거한다.

- **af-cross-review.md Step 5 / 출력 형식 / 매핑 테이블 어디에도 HOLD를 명시하지 않는다.**
- Phase 2 운영 중 HOLD 라벨이 출력되면 = LLM이 자의적으로 발화한 것 = 형식 위반.
- Phase 3에서 deliberation 알고리즘 변경과 함께 HOLD 입구 조건·매핑·파서 호환성을 동시 정의해 재도입한다.
- **enforcement**: af-cross-review.md Step 5에 "HOLD 라벨 사용 금지 (Phase 2 범위)" 명시. (Critic #4 권장 (a) 채택.)

### §4.6 Phase 2의 substantive 변화 = labeling + 파이프라인 정합

**핵심 사실**: 경로 3(`has_block`)와 경로 4(`no-fire`)는 PASS와 WARN을 동등 처리한다. 따라서 Phase 2는:

- ✅ verdict 라인의 **글자**가 바뀐다 (PASS → WARN, advisory가 있을 때).
- ✅ `state.reviews[T3].verdict`의 **값**이 바뀐다 (PASS → WARN).
- ✅ **v3 추가** — `_FINDING_RE`가 새 라벨을 인식해 메트릭이 정상 계측된다.
- ✅ **v3 추가** — `_VERDICT_RE` collision이 fence + last-position 결합으로 차단된다 (§5.3, v4 정정).
- ✅ **v3 추가** — verdict 파서 silent fallback이 hook 이벤트로 **가시화**된다 (detection-only — gate-level 차단은 Phase 3, v4 정정).
- ✅ **v4 추가** — WARN-only no-fire suppression 발화가 별도 sink(`warn_only_suppressed`)로 가시화되어 §9.2 트리거가 falsifiable해진다 (§5.4).
- ❌ gate 차단 빈도는 바뀌지 않는다 (둘 다 차단 안 함).
- ❌ no-fire 발화 빈도는 바뀌지 않는다 (둘 다 has_block=False).
- ❌ verdict 파서 형식 위반 → gate-level fail-safe 차단은 Phase 2 비목표 (§6 O5와 정합 — Phase 3에서 알고리즘과 함께 도입).

→ **Phase 2는 정책 변화가 아닌 labeling+측정 정확화다.** 운영 risk가 매우 낮음 (코드 변경은 모두 추가 진단/방어 — 기존 정상 경로 비파괴). G4·G11는 **detection fail-safe** (사후 가시화)이며 gate-level fail-safe는 아니다.

### §4.7 [ACCEPT] Critical 단독 → BLOCK 유지

"단독 [ACCEPT]" = Codex 도전 없이 Claude가 직접 코드 확인한 Critical/High.

**유지 결정**: BLOCK. Claude의 직접 코드 확인은 충분한 evidence. Codex 부재가 곧 false positive를 의미하지 않는다.

### §4.8 Medium 임계 정책

Medium은 BLOCK 임계 없음. Medium 10건이어도 WARN. (af-critic 정책과 일관: 잠재적 리스크/품질 = WARN)

WARN-only no-fire가 Medium 폭탄으로 인한 무한루프를 차단한다 (§4.6 + 경로 4).

---

## §5 변경 파일

### §5.1 `.claude/agents/af-cross-review.md` Step 5 (변경)

§4.3 테이블 + §4.4 집계 규칙을 Step 5에 적용한다. 본 v3 문서가 정규 출처이므로 af-cross-review.md는 **요약 + 본 문서 링크**만 둔다 (G5 재발 방지).

**적용 변경 내역 (v3)**:

1. **판정 테이블 교체**: 현재 6행 테이블(`af-cross-review.md:259-266`)을 §4.3 10행 테이블로 대체.
2. **집계 규칙 추가**: §4.4 우선순위 3단계를 명시.
3. **finding 라벨 분리**: `[ACCEPT]` advisory → `[ACCEPT-ADV]` 로 라벨명 변경. 출력 예시 #### 4 항목(`af-cross-review.md:302`)을 갱신.
4. **출력 형식 WARN 케이스 추가**: 현재 BLOCK/PASS 2-case → WARN 예시 추가:
   ```
   <!-- final-verdict-start -->
   ## Tier 3 판정: WARN
   사유: Advisory Medium 2건, Low 1건 — 사용자 검토 권장
   <!-- final-verdict-end -->
   ```
5. **scope-creep / INCOMPLETE 마커 호환성 명시**: 현재 verdict 라인에 붙는 `[scope-creep]` `[INCOMPLETE]` 마커는 WARN/BLOCK/PASS 어느 라벨에도 부착 가능하다는 불변 명시. (단, fence 내부 한정 — §5.1 변경 8.)
6. **finding 헤더 형식 의무화**: `#### N. [라벨] [Severity] 제목`.
   - 라벨: `[ACCEPT]` / `[ACCEPT★]` / `[ACCEPT-ADV]` / `[REJECTED]` / `[BONUS]` 5종 (G10 해소 — `[BONUS]` finding 라벨 승격).
   - Severity: `[Critical]` / `[High]` / `[Medium]` / `[Low]` 4종.
   - **Severity 의무 라벨**: `[ACCEPT]` / `[ACCEPT★]` / `[ACCEPT-ADV]` / `[BONUS]` 4종 (BONUS 포함).
   - **Severity 생략 허용 라벨**: `[REJECTED]` 1종 (verdict-neutral이므로 severity 정보 가치 없음 — v4 정정).
   - **severity 누락 시 (의무 라벨에서)**: §4.3 fail-safe로 BLOCK 처리됨 — Step 5 출력 형식에 "severity 누락은 BLOCK으로 안전 처리됨 (`[REJECTED]` 제외)" 명시 (G9 해소).
7. **(v3 삭제)** ~~HOLD 라벨 finding-level 정의~~ — §4.5에 따라 Phase 3로 완전 이관. Step 5에 "HOLD 라벨 사용 금지 (Phase 2 범위)" 1줄 추가.
8. **(v3 신규) verdict fence 도입**: 최종 판정은 반드시 fence 내부에 위치한다.
   ```
   <!-- final-verdict-start -->
   ## Tier 3 판정: BLOCK
   사유: <한 줄>
   <!-- final-verdict-end -->
   ```
   본문 어디에서도 fence를 재사용할 수 없다 (Step 5 prompt에서 명시). G7 collision 차단 + §5.3 파서가 fence 내부만 인식 (§5.3 변경).

### §5.2 `af-critic.md` (변경 없음)

이미 BLOCK/WARN/PASS 직접 출력. Critic은 자체 판단으로 라벨 결정 — finding-level taxonomy 없음.

### §5.3 `scripts/review_gate.py` (변경) — v3 추가, v4 정정

**v3 변경 사유 (G7 해소)**: `_VERDICT_RE.search()` 첫 매칭 정책이 본문 인용을 잘못 캡처하는 collision 위험이 있음.

**v4 정정 (Critic #1, #6, Missing 1·4)**: 두 정규식의 결합 알고리즘과 wrapper 호출자가 v3에서 모호했음. last-position 결합 + 단일 호출자(=`hook_runner.py`) 명시.

**구체 변경**:
- `_extract_verdict_from_content(content: str) -> str | None` 신규 함수 (`scripts/review_gate.py`에 정의).
  - **1순위 — fence 내부**: 첫 번째 `<!-- final-verdict-start -->`부터 첫 번째 `<!-- final-verdict-end -->`까지의 부분 문자열만 추출 (다중/중첩 fence 발견 시 첫 쌍만 인식 — Missing #4 해소). 추출된 부분 문자열에 대해 `_VERDICT_RE.findall()` + `_VERDICT_HEADER_RE.finditer()` 모두 실행 → **두 패턴의 모든 매칭을 (start_position, group(1).lower()) 튜플로 합쳐 last-position 선택** (단일 패스, ambiguity 0).
  - **2순위 — fence 부재 폴백**: 전체 content에 대해 동일 알고리즘 수행 — `_VERDICT_RE.finditer()` + `_VERDICT_HEADER_RE.finditer()` 매칭을 (start_position, lowered_label) 튜플로 합쳐 **start_position이 가장 큰 것** 1건 선택. **두 패턴은 정의상 disjoint(콜론 폼 `verdict:|판정:` vs 헤더 폼 `^#{1,4}\s+...`)이므로 동일 start position 매칭은 발생하지 않는다** (Python `re.MULTILINE`에서 헤더 폼은 줄 시작에서만 매칭, 콜론 폼은 키워드 다음 콜론 매칭 — 시작 위치 충돌 불가능). 만약 미래 정규식 변경으로 동일 start 매칭이 발생하면 의사 코드의 stable sort 동작에 따라 후 삽입된 `_VERDICT_HEADER_RE`가 `matches[-1]`로 선택된다. v5는 이 동작을 정규로 채택한다 (v4 prose의 "`_VERDICT_RE` 우선" 표현은 의사 코드와 모순이었으므로 삭제 — Critic #2). 본문 인용은 보통 위쪽에 있고 verdict 라인은 마지막에 있으므로 last-position이 정상 verdict를 선택한다.
  - **3순위 — 매칭 0건**: `None` 반환 (caller가 fallback 정책 결정 — §5.5 참조).
  - 호환성: af-critic.md, af-test-runner.md는 fence 미사용 → 폴백 경로로 정상 동작.
- **단일 호출자**: `_extract_verdict_from_content()`는 `scripts/hook_runner.py:_post_agent_record`에서만 호출한다 (현재 `hook_runner.py:339-344`의 verdict 파싱 블록을 wrapper 호출로 교체). `is_gate_blocked()` / `record_review_done()` / `_compute_round_summary()`는 본문 파싱을 하지 않으며 — 이미 `record_review_done()`이 verdict 인자를 caller로부터 받는 구조 — wrapper와 무관함을 v4에서 명확히 한다 (Critic #6 해소).
- **`record_review_done()` 인자 신뢰 관계** (Missing #1 해소): wrapper 신설은 `record_review_done()`의 verdict 인자 의미를 변경하지 않는다. 즉 caller(`hook_runner.py`)가 wrapper로 추출한 verdict를 그대로 인자로 전달; `record_review_done()`은 이 인자를 그대로 신뢰해 `state["reviews"][agent]["verdict"]`에 기록한다. fence/non-fence 출처 추적은 wrapper 호출 시점의 `_log_hook_event("verdict_fallback", ...)` (§5.5)로만 이뤄진다.
- 기존 동작 보존: `_VERDICT_RE`/`_VERDICT_HEADER_RE` 패턴 자체는 무변경.

**의사 코드** (v4 알고리즘 명세):

```python
# scripts/review_gate.py
_VERDICT_FENCE_RE = re.compile(
    r"<!--\s*final-verdict-start\s*-->(.*?)<!--\s*final-verdict-end\s*-->",
    re.DOTALL | re.IGNORECASE,
)

def _extract_verdict_from_content(content: str) -> str | None:
    fence = _VERDICT_FENCE_RE.search(content)
    target = fence.group(1) if fence else content   # 1순위 vs 2순위 분기
    matches: list[tuple[int, str]] = []
    for m in _VERDICT_RE.finditer(target):
        matches.append((m.start(), m.group(1).lower()))
    for hm in _VERDICT_HEADER_RE.finditer(target):
        matches.append((hm.start(), hm.group(1).lower()))
    if not matches:
        return None
    matches.sort(key=lambda t: t[0])     # 위치 오름차순
    return matches[-1][1]                # last-position
```

**테스트 추가 의무** (§7.2):
- C1 fence 내부 매칭 케이스
- C2 본문 인용 + fence 외부 verdict 라인 → fence 내부만 캡처
- C3 fence 부재 + `_VERDICT_RE`(본문 인용 BLOCK) + `_VERDICT_HEADER_RE`(마지막 라인 PASS 헤더) 두 정규식이 다른 위치에서 동시 매칭 → last-position인 PASS 헤더 선택 (v4 정정 — 두 정규식 동시 매칭 케이스 명시)
- C4 fence 부재 + 단일 `Verdict: BLOCK` (af-critic 형식) → block (호환성)
- C5 fence 부재 + verdict 라인 0개 → `None` → caller가 silent fallback("pass") + `_log_hook_event("verdict_fallback")` (§5.5 G4)
- **C6 (v4 신규)** 다중/중첩 fence — 본문에 fence 2쌍이 있을 때 첫 쌍 내부만 인식, 둘째 쌍은 무시 (Missing #4 해소)

### §5.4 `scripts/check_pending_review.py` (변경) — v4 신규, v5 정정 (Critic #1·#4·#5)

**v3 입장**: "변경 없음. WARN-only no-fire가 `last_summary.has_block`만 본다. WARN/PASS 둘 다 has_block=False → 동일 동작."

**v4 변경 사유 (G11)**: §9.2 롤백 트리거 #1("WARN-only no-fire가 의도와 달리 작동")은 v3 시점에서 falsifiable하지 않다. `verdict_fallback` 이벤트(§5.5)와 no-fire 오작동은 직접 인과 관계가 없으며, `check_pending_review.py:126-138`의 no-fire 분기에는 telemetry sink가 부재 — 발화 빈도를 측정할 수 없다.

**v5 정정 (Critic #1 / Critical / v3 BLOCK 재도입 해제)**:
- v4 코드는 `_log_hook_event(workspace, "warn_only_suppressed", {dict})` 3-arg 호출이었으나 `hook_runner.py:100` 실제 시그니처는 `(builtin: str, file: str, exit_code: int, error: str = "")` 4-arg. 즉 `dict`가 `exit_code` 자리에 들어가 `f"|{exit_code}|"` 포맷에 `repr(dict)` 직렬화 — 측정값 손실. v5는 4-arg + JSON 페이로드(`error=`)로 통일한다.

**v5 정정 (Critic #4 / High / import 전략)**:
- v4는 "import하거나 inline 재정의"로 결정 보류. v5는 **`from scripts.hook_runner import _log_hook_event` import 결정** + 다음 보장:
  - **workspace path 일관성**: `_log_hook_event`는 `_project_root()`를 `__file__` 기반으로 결정한다(`hook_runner.py:105`). `scripts/hook_runner.py`와 `scripts/check_pending_review.py`는 동일 디렉토리에 있어 `_project_root()`가 동일 root를 반환 → 동일 `.af_review_queue/hook_events.log` 파일에 append. workspace 분기 위험 없음.
  - **import 비용**: Python import cache로 첫 1회만 fully load. UserPromptSubmit hot-path에서 N번째 hook은 cache hit (`sys.modules`).
  - **private prefix `_`**: cross-script reuse는 본 레포에 선행 사례(`scripts/hook_runner.py:338` `_VERDICT_RE`/`_VERDICT_HEADER_RE`를 review_gate에서 import)가 있어 conventional.
  - **fallback**: import 실패 시 `try/except: pass` — sink 결손은 Phase 2 비목표(detection-only).

**v5 정정 (Critic #5 / High / sink 폭발 차단)**:
- v4는 hook event 기록을 `if not data.get("warn_only_notified_at"):` 분기 **밖**에 두어 매 UserPromptSubmit마다 N:1 폭발 (§9.2 트리거 #1 "1:1 정합" 의도와 반대). v5는 **1회-알림 분기 내부로 이동** — WARN 라운드당 정확히 1건 sink 기록.

**구체 변경** (`check_pending_review.py:126-138`):

```python
# 변경 전 (현재 상태)
if round_count >= 1 and last_summary and not last_summary.get("has_block", True):
    if not data.get("warn_only_notified_at"):
        print("[af-review-suppressed] 직전 라운드가 WARN/PASS만 포함 — 재발화 보류.")
        print("[af-review-suppressed] commit이 막힌다면: AF_SKIP_REVIEW_GATE=1 ...")
        data["warn_only_notified_at"] = time.time()
        _atomic_write(marker, data)
    return

# 변경 후 (v5)
if round_count >= 1 and last_summary and not last_summary.get("has_block", True):
    if not data.get("warn_only_notified_at"):
        # G11: WARN 라운드당 정확히 1건 — 1회-알림과 동일 분기에서 시계열 sink 기록
        try:
            from scripts.hook_runner import _log_hook_event
            _log_hook_event(
                "warn_only_suppressed",  # builtin
                str(round_count),         # file (round_count 표기)
                0,                        # exit_code
                error=json.dumps({        # error 자리에 JSON 페이로드
                    "agents_present": list((last_summary.get("verdicts") or {}).keys()),
                }),
            )
        except Exception:
            pass  # sink 결손은 Phase 2 비목표 (detection-only)
        print("[af-review-suppressed] 직전 라운드가 WARN/PASS만 포함 — 재발화 보류.")
        print("[af-review-suppressed] commit이 막힌다면: AF_SKIP_REVIEW_GATE=1 ...")
        data["warn_only_notified_at"] = time.time()
        _atomic_write(marker, data)
    return
```

**`_log_hook_event` 시그니처 (정규)** — v4에서 모호했던 부분을 v5에서 단일화:
- 정의: `hook_runner.py:100` `def _log_hook_event(builtin: str, file: str, exit_code: int, error: str = "") -> None`
- 호출 약속: 모든 caller (§5.4 / §5.5)는 4-arg 형식 사용. JSON-직렬화 가능 페이로드는 `error=json.dumps({...})`로 전달.
- §5.4·§5.5 정합: 두 caller 모두 동일 시그니처 사용 — 문서 내부 일관성 보장.

**호환성**: 기존 1회-알림은 그대로 유지. 추가된 1줄은 silent (`hook_events.log` append만). 정상 흐름 비파괴.

**§9.2 트리거 #1 재정의 (단순화 — Critic #5)**: "WARN 라운드당 정확히 1건의 `warn_only_suppressed` 이벤트가 기록된다." → 측정: `grep -c "warn_only_suppressed" .af_review_queue/hook_events.log` vs WARN verdict 발생 라운드 수. 정상 작동 시 1:1 정합 (이전 v4 0.8x~1.2x 범위 정의는 N:1 폭발 가정 하에서였음 — v5 단순화).

**테스트 갱신 의무 (Critic #4 — workspace path 단위 테스트)**: `tests/test_check_pending_review.py` (또는 hook_runner 통합 테스트)에:
- WARN-only suppression 분기 진입 시 `warn_only_suppressed` 이벤트가 정확히 1회 기록 (1회-알림과 같은 분기 내 발화 검증)
- 동일 round_count 재진입 시 추가 sink 발화 없음 (`warn_only_notified_at` 멱등성)
- import한 `_log_hook_event`가 `scripts/.af_review_queue/hook_events.log` 동일 파일에 append하는지 (workspace path 일관성)

**v5 코드 변경 파일 수**: v3 6개 → v4 7개 → **v5 7개 유지** (`check_pending_review.py` 변경 내역만 정정, 파일 수 불변).

### §5.5 `scripts/hook_runner.py` (변경) — v3 추가, v4 정정

**v3 변경 사유 (G4)**: silent "pass" fallback이 Phase 2 효과(verdict 라인 글자 변경)를 LLM 출력 형식 표류 시 침묵 무력화.

**v4 정정 (Critic #3 + #6)**:
- **detection-only 강등**: v3은 본 변경을 "G4 해소 + Phase 2 차단 의존성"으로 격상했으나 **gate-level 차단은 여전히 Phase 3로 이관**한다. fallback 시 `verdict="pass"`가 그대로 `record_review_done()`/`has_block=False`로 전파되므로, gate 결정 자체는 형식 위반 LLM 출력 시 silent PASS 그대로다. 본 변경은 사후 가시화(detection fail-safe)일 뿐 현재 라운드 gate를 차단하지 않는다. §6 O5("WARN → gate 차단" 비목표)와도 정합 — 진짜 gate-level fail-safe(WARN/sentinel 강등)는 §6 O5와 모순되므로 Phase 3 영역.
- **wrapper 호출 (Critic #6)**: v3 변경 코드는 `_VERDICT_HEADER_RE.search()`를 직접 호출했으나 — wrapper(§5.3)와 비정합. v4는 wrapper 단일 호출자(§5.3) 약속에 따라 wrapper로 일원화한다.

**구체 변경** (`hook_runner.py:337-346`):

```python
# 변경 전 (현재 상태)
try:
    from scripts.review_gate import _VERDICT_RE, _VERDICT_HEADER_RE
    m = _VERDICT_RE.search(content)
    if m:
        verdict = m.group(1).lower()
    else:
        hm = _VERDICT_HEADER_RE.search(content)
        verdict = hm.group(1).lower() if hm else "pass"
except Exception:
    verdict = "pass"

# 변경 후 (v4)
try:
    from scripts.review_gate import _extract_verdict_from_content
    extracted = _extract_verdict_from_content(content)
    if extracted is not None:
        verdict = extracted
    else:
        verdict = "pass"
        _log_hook_event(
            "verdict_fallback",
            subagent_type,
            0,
            error=f"no-verdict-line:{content[:200]!r}",
        )
except Exception as exc:
    verdict = "pass"
    _log_hook_event("verdict_fallback", subagent_type, 1, error=str(exc))
```

(`_log_hook_event` 호출은 `scripts/hook_runner.py:100` 정의된 helper 시그니처에 맞춤 — `(builtin, file, exit_code, error="")` 4-arg. v4 line 64 인용은 오류 — line 64는 `_find_venv_python()`의 `return sys.executable`로 무관 [Critic #3 v5 정정]. §5.4 caller도 동일 4-arg 형식 — §5.4 호환성 보장.)

**호환성**: 정상 verdict 출력 케이스는 동작 무변경. fallback이 발화되는 시점에만 1줄 로그 추가. **gate 동작은 v3과 동등** (silent "pass" 그대로 전파 — gate-level 차단은 Phase 3).

**§4.6 / §6 정합**: 본 변경은 detection fail-safe (사후 가시화). gate-level fail-safe(verdict="warn"/sentinel 강등 + `is_gate_blocked` 분기)는 §6 O5와 모순되므로 Phase 3로 이관 (§10 F2와 연결).

### §5.6 `scripts/review_metrics_logger.py` (변경) — v3 신규

**v3 변경 사유 (G8 해소)**: `_FINDING_RE`가 v2 신설 `[ACCEPT-ADV]`를 매칭 못 함 → §9.1 운영 검증이 self-defeat.

**구체 변경** (`review_metrics_logger.py:31-34`):
```python
# 변경 전
_FINDING_RE = re.compile(
    r'\[(?:ACCEPT[★*]?|WARN|BLOCK|REJECTED)\]',
    re.IGNORECASE,
)

# 변경 후
_FINDING_RE = re.compile(
    r'\[(?:ACCEPT(?:[★*]|-ADV)?|WARN|BLOCK|REJECTED|BONUS)\]',
    re.IGNORECASE,
)
```

**v3 정규식 결정 사항**:
- `ACCEPT(?:[★*]|-ADV)?` — `[ACCEPT]`, `[ACCEPT★]`, `[ACCEPT*]`, `[ACCEPT-ADV]` 4가지 매칭.
- `BONUS` 추가 — §5.1 변경 6 BONUS finding 라벨 승격에 정합.
- `HOLD` 미포함 — §4.5 결정에 따라 Phase 3 이관, Phase 2에서 발화 금지. (forward-looking spec도 두지 않음 — Critic #4의 prompt drift 우려 제거.)

**v4 정정 (Critic #7 / G12) — `_SCOPE_CREEP_RE` 검색 범위 정책**:

§5.1 변경 5는 `[scope-creep]` / `[INCOMPLETE]` 마커가 fence 내부 verdict 라인에 부착됨을 명시한다. 그러나 `review_metrics_logger.py`의 `_SCOPE_CREEP_RE`는 전체 content를 검색한다 — 두 정책이 충돌하면 메트릭이 손상되거나 정책 모호성이 발생한다.

**결정**: scope-creep는 verdict 라벨이 아니므로 `_SCOPE_CREEP_RE` 검색 범위는 **fence 외부 검색을 유지**한다 (단순성 우선). 마커는 본문 어디에 있어도 메트릭에 카운트한다. 이는 verdict 파서(§5.3 fence 한정)와 메트릭 파서의 책임 분리:
- verdict 파서: fence 내부만 (verdict label collision 차단)
- 메트릭 파서: 전체 content (정량 신호 보존)

**스펙 명시**: `review_metrics_logger.py` 모듈 docstring 또는 `_SCOPE_CREEP_RE` 위 1줄 주석에 "scope-creep 마커는 verdict 라벨이 아니므로 fence 외부도 검색 유지 (Phase 2 v4 §5.6)" 명시.

**호환성**: 기존 메트릭 동작 100% 유지 (검색 범위 변경 없음). v4 정정은 정책 명시만이며 코드 동작은 변경 없음.

**테스트 갱신 의무** (`tests/test_review_metrics_logger.py`):
- 신규 케이스: `[ACCEPT-ADV]` Medium 3건 → `findings_count = 3`
- 신규 케이스: `[BONUS]` Critical 2건 → `findings_count = 2`
- 신규 케이스: 혼합 (`[ACCEPT★]`, `[ACCEPT-ADV]`, `[REJECTED]`, `[BONUS]`) → 모두 카운트
- 회귀 보호: 기존 `[ACCEPT]` / `[WARN]` / `[BLOCK]` / `[REJECTED]` 4종 매칭 유지

---

## §6 비목표 (Scope OUT)

| ID | 항목 | 이유 |
|----|------|------|
| O1 | `hold` final verdict 라벨 도입 | §4.1 결정: finding-level 전용도 제거 (G3 Phase 3 이관) |
| O2 | Medium N건 → BLOCK 자동 승격 | §4.8 결정 |
| O3 | af-critic HOLD 처리 변경 | af-critic은 자체 BLOCK/WARN/PASS 판단 |
| O4 | `_VERDICT_RE` 패턴 자체 변경 | §5.3에서 호출 wrapper만 도입, 패턴 무변경 |
| O5 | WARN → gate 차단 | 정책 변경 아님 (§4.6) |
| **G3** | **[HOLD] finding 입구 조건 정의 + 라벨 자체** | **Phase 3 완전 이관**: deliberation 알고리즘 변경과 동시 도입. v3에서 Step 5 prompt에 "HOLD 사용 금지" 명시. |
| **G4** | **parser silent fallback gate-level 차단 (verdict="warn"/sentinel 강등 + `is_gate_blocked` 분기)** | **Phase 3 이관** — §6 O5("WARN → gate 차단")와 모순되므로 algorithm change와 함께 도입. v4는 detection-only 가시화만 (§5.5). |

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
| 6 | `[BONUS]` Critical 2건 (PRIMARY 0건) | WARN | §4.3 BONUS 행. 헤더 형식 = `#### 1. [BONUS] [Critical] ...` (§5.1 변경 6) |
| 7 | (v3 삭제) ~~`[HOLD]`~~ | ~~WARN~~ | §4.5 Phase 3 이관, Phase 2 발화 금지 |
| 8 | `[ACCEPT★]` High 1건 + `[REJECTED]` Critical 1건 | BLOCK | REJECTED 무시, ACCEPT★ High → BLOCK |
| **9 (v3 신규)** | **severity 누락 finding 1건 (예: `#### 1. [ACCEPT-ADV] 제목`)** | **BLOCK** | **§4.3 fail-safe default (G9)** |
| **10 (v3 신규)** | **`[BONUS]` Medium 1건 + `[ACCEPT-ADV]` Low 2건** | **WARN** | BLOCK 없음, WARN ≥ 1 |
| **11 (v4 신규)** | **`[REJECTED]` severity 누락 1건 (예: `#### 1. [REJECTED] 제목`) + 그 외 finding 0건** | **PASS** | §4.3 단서 — REJECTED는 severity 생략 허용 + verdict-neutral fail-safe 우선. fail-safe BLOCK 트리거 안 함 (Critic #2 / G9 보강) |
| **12 (v4 신규)** | **`[REJECTED]` severity 누락 1건 + `[ACCEPT★]` High 1건** | **BLOCK** | REJECTED는 verdict-neutral, ACCEPT★ High → BLOCK |
| **13 (v4 신규)** | **의무 라벨 severity 누락 + `[REJECTED]` severity 누락 동시 (예: `#### 1. [ACCEPT-ADV] 제목` + `#### 2. [REJECTED] 제목`)** | **BLOCK** | ACCEPT-ADV severity 누락 → fail-safe BLOCK 1건 (§4.3). REJECTED는 verdict-neutral 무시 |

### §7.2 파서 호환성 검증 (v3 — fence + collision 회귀)

verdict 라인 형식: `## Tier 3 판정: WARN [scope-creep]` (fence 내부)

`_VERDICT_RE` 매칭:
- 패턴: `(?:verdict|판정)\s*[:\-]\s*(block|warn|pass|fail)`
- 입력의 `판정: WARN` 부분이 group 1에 `warn` 캡처 → 매칭 ✓
- 후행 `[scope-creep]`은 무시 → ✓

`_VERDICT_HEADER_RE` 매칭 (fallback):
- 패턴: `^#{1,4}\s+(BLOCK|WARN|PASS|FAIL)\b`
- `## Tier 3 판정: WARN`은 `##` 다음에 `Tier`가 와서 미매칭
- 그러나 `_VERDICT_RE`가 먼저 매칭하므로 fallback 불필요 → ✓

→ **패턴 변경 불필요 확정. 단 §5.3 wrapper 신설**.

**v3/v4 collision 회귀 케이스 (§5.3 신규 단위 테스트)**:

| # | 입력 | 기대 |
|---|------|------|
| C1 | fence 내부 단일 `## Tier 3 판정: WARN` | verdict=warn |
| C2 | 본문에 "이전 라운드 판정: BLOCK" + fence 내부 `## Tier 3 판정: PASS` | verdict=pass (fence 내부만 인식, G7 해소) |
| **C3 (v4 정정)** | **fence 부재 + 본문 위쪽에 `_VERDICT_RE` 매칭(예: "verdict: BLOCK" 인용) + 본문 아래쪽에 `_VERDICT_HEADER_RE` 매칭(예: `## PASS`)** | **verdict=pass — 두 정규식 매칭 위치를 합쳐 last-position(아래쪽 헤더) 선택 (Critic #1)** |
| **C3b (v4 신규)** | **fence 부재 + 위쪽 `_VERDICT_HEADER_RE` 매칭(`## BLOCK`) + 아래쪽 `_VERDICT_RE` 매칭(`판정: PASS`)** | **verdict=pass — 패턴 종류와 무관, 위치만 비교 (대칭성)** |
| C4 | fence 부재 + 단일 `Verdict: BLOCK` (af-critic 형식) | verdict=block (호환성) |
| C5 | fence 부재 + verdict 라인 0개 | `_extract_verdict_from_content() → None` → caller가 silent fallback("pass") + `_log_hook_event("verdict_fallback")` (§5.5 G4 — detection-only) |
| **C6 (v4 신규)** | **본문에 fence 2쌍 (다중/중첩) — 첫 쌍 내부 `## PASS` + 둘째 쌍 내부 `## BLOCK`** | **verdict=pass — 첫 쌍만 인식, 둘째 쌍은 무시 (Missing #4)** |

### §7.3 WARN-only no-fire 동작 검증 (실제 코드 경로 기반)

**시나리오**: T3가 advisory만 발견 → verdict=warn 발화 → 다음 사용자 편집 시 자동 재발화 안 됨.

**경로 추적**:

1. **T3 에이전트가 출력**: fence 내부 `## Tier 3 판정: WARN`
2. **`hook_runner.py:339`** `_extract_verdict_from_content(content)` (§5.3 wrapper) → fence 내부에서 `_VERDICT_RE` 매칭 → `verdict = "warn"`
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

→ **WARN-only no-fire 정상 동작 확정**.

### §7.4 commit gate 동작 검증

**시나리오**: T3 verdict=warn → `git commit` 시도.

1. pre-commit hook → **`review_gate.py:198`**: `r.get("verdict") in ("block","fail")` — warn은 미해당 → 통과 ✓
2. 다른 tier도 모두 non-block이라면 `is_gate_blocked()` → False → commit 통과 ✓

→ **WARN은 commit을 차단하지 않는다** (정책 의도와 일치).

### §7.5 BLOCK 시나리오 회귀 + round 전환 검증 (v3 보강)

기존 BLOCK 동작과 round 전환 시 has_block 갱신 보장.

| # | 시나리오 | 기대 |
|---|---------|------|
| R1 | T3 verdict=block, T1/T2 pass | gate BLOCK (`review_gate.py:198`) |
| R2 | T3 verdict=block | next-round 재발화 ✓ (`has_block=True`이므로 no-fire 트리거 안 함) |
| **R3 (v3 신규)** | **R1 WARN 종결 → 사용자 편집 → R2 자동 발화 안 됨** | `has_block=False` 누적 → no-fire (§7.3 경로 6) |
| **R4 (v3 신규)** | **R1 BLOCK → 사용자 코드 수정 → R2 WARN** | R2 시작 시 `has_block=True`이므로 자동 재발화 ✓ → R2 결과로 `has_block=False` 갱신 → R3 no-fire |
| **R5 (v3 신규)** | **max_rounds=2 도달 후 WARN** | `round_count >= 2` 캡으로 추가 자동 발화 없음 (`check_pending_review.py:110`) — 사용자 수동 결정 단계로 전환 |
| **R6 (v3 신규)** | **Mixed: T1=pass, T2=block, T3=warn** | T2 block 1건만으로 `has_block=True` → next-round 재발화 ✓ (T3가 warn이어도 영향 없음 — §4.4 우선순위 1은 has_block.value 기준) |

→ **§4.6 "labeling만 바뀌고 no-fire 동일" 주장이 round 전환 케이스에서도 유지됨을 확인**.

### §7.6 메트릭 정합 검증 (v3 신규 — G8 / v5 정정 — Critic #8 false-positive 회귀)

**True-positive 시나리오**: af-cross-review 출력에 `[ACCEPT-ADV]` Medium 3건, `[BONUS]` Low 1건 포함.

1. `review_metrics_logger.parse_findings_count(content)` → `_FINDING_RE.findall(content)` → 4건 매칭 (`[ACCEPT-ADV]` 3 + `[BONUS]` 1)
2. `compute_report()` → `findings_per_review = 4` → §9.1 WARN 비율 산출 정상 ✓

**기존 회귀 보호 (v3)**:

3. af-critic의 `Verdict: PASS` (대문자, 라벨 미사용) → `parse_findings_count → 0` (변경 없음).
4. af-cross-review의 `[REJECTED]` × 5 → `findings_count = 5` (verdict-neutral이지만 finding 발견량은 카운트 — 기존 정책 유지).

**False-positive 회귀 (v5 신규 — Critic #8 / G8 보강)**:

신규 라벨 2종(`[ACCEPT-ADV]`, `[BONUS]`) 도입으로 noise surface가 50% 증가했음에도 v4 §7.6은 true-positive만 다뤘다. v5는 false-positive 회귀 2건을 추가:

5. **markdown 코드 fence 내부 false-positive**: 본문에
   ````markdown
   여기는 정책 설명 블록입니다.
   ```
   예시: 라벨 [ACCEPT-ADV] Medium은 advisory를 의미합니다.
   ```
   ````
   `_FINDING_RE`는 fence 내부도 검색 → `findings_count = 1`.
   **정책 (v5 명시)**: 모두 카운트 (현 정책 유지). 이유:
   - fence 내부/외부 분리 비용이 _FINDING_RE의 단순 grep 정책을 깨트림
   - `_SCOPE_CREEP_RE`(§5.6)와 동일 정책 (fence 외부 검색 유지) — 일관성
   - false positive는 1주 운영 시 빈도 측정 → §10 F4 트리거 (Medium 임계 재검토)와 함께 재평가

6. **prose 인용 false-positive**: 본문에 `"라벨 [BONUS]를 새로 도입한다는 의미로..."` 같은 prose 인용이 있을 때 → `findings_count = 1`.
   **정책 (v5 명시)**: 모두 카운트 (현 정책 유지). 이유 동일 (단순성 우선). 운영 메트릭으로 1주 후 재평가.

→ **v5 §9.2 트리거 #4 보강**: "false-positive 매칭 빈도 ≥ 5건/주 + 수동 grep 결과 비교 시 ≥ 30% noise" → §10 F4와 함께 fence 내부 한정 정책 재검토. 단, Phase 2는 단순성 우선이므로 회귀 자체로 BLOCK 트리거 안 함.

---

## §8 구현 순서 (v5 — Critic 8건 BLOCK 해제 후)

### 8.1 검증 사전 단계

1. **본 v5 문서에 대해 af-cross-review만 교차검증** 실행 (단일 설계문서 정책).
   - codex usage limit 회복(**2026-05-05 15:37 KST 이후**) 후 fan-out 권장. 사용자 결정에 따라 Claude 단독 검증으로 v4 BLOCK 해소 확인 가능(본 v5는 Claude 단독 검증 수용 결정으로 진행).
   - v5 PASS/WARN 후에만 §8.2 코드 적용 일괄 commit 진입.

### 8.2 코드 적용 일괄 commit — 부트스트랩 순서

v5 코드 변경 7개 파일은 **단일 commit + 3-tier 전체 + `blast_radius.py` 사전 출력 첨부** 전략으로 적용한다.

**자기모순 회피 — staged 코드와 reviewer 동시 활성화 (v5 정정 — Critic #6)**:
- `scripts/review_gate.py`, `scripts/hook_runner.py`, `scripts/check_pending_review.py`는 자동 Tier 3 (subprocess/shell=True/hook launcher) — `scripts/blast_radius.py` 분류기준.
- **단일 commit의 staged 코드는 hook 발화 직전에 disk에 존재한다** — reviewer(claude code subagent) prompt와 parser(Python script) 모두 v5 형식이 동시 활성화. v4 prose의 "본 commit 검증 라운드는 이전 fence 없는 형식으로 실행됨" 단정은 잘못이었다 (Critic #6 ACCEPT).
- 단, **agent definition cache** 영향 가능성: claude code가 `.claude/agents/af-cross-review.md`를 첫 호출 시 disk에서 read하지만, 같은 세션 내 prior 호출 캐시가 잔존할 수 있다. 이 경우 첫 호출에 한해 v3 prompt로 실행되어 fence 미사용 출력이 나올 수 있음. parser는 §5.3 2순위(fence 부재 폴백)로 정상 동작 — last-position 추출 → C5(verdict 0건) 케이스만 silent fallback. 즉 **chicken-and-egg는 grace period로 해소** (운영 리스크 최소).
- 검증 시점 cross-review 출력은 v4/v5 형식 또는 fence 없는 free-form 둘 다 정상 처리. Spec drift는 다음 commit cycle에서 catch됨 (운영 메트릭 `verdict_fallback` 빈도로 확인).

**대안 — 2-commit 분리 전략 (보류)**: af-cross-review.md를 먼저 commit (Tier 1 — 단순 에이전트 설정) → 새 fence로 다음 라운드 cross-review가 출력 → scripts/*.py 적용 commit. 그러나 첫 commit과 둘째 commit 사이에 prompt와 parser가 비정합 상태(파서 v3, prompt v5)가 되며, 단일 commit 전략은 폴백 경로로 동등 안전성 확보 → **단일 commit 전략 채택**.

**적용 파일 (7개)**:

| # | 파일 | 변경 위치 | spec 참조 | Tier (blast_radius) |
|---|------|----------|----------|---------------------|
| 1 | `.claude/agents/af-cross-review.md` Step 5 | 6개 변경 (§5.1 변경 1~8) | §5.1 | Tier 1 (agent config) |
| 2 | `scripts/review_gate.py` | `_extract_verdict_from_content` 신규 | §5.3 | Tier 3 |
| 3 | `scripts/hook_runner.py` | wrapper 호출 + verdict_fallback log | §5.5 | Tier 3 |
| 4 | `scripts/check_pending_review.py` | warn_only_suppressed log | §5.4 | Tier 3 |
| 5 | `scripts/review_metrics_logger.py` | `_FINDING_RE` 확장 + scope-creep 주석 | §5.6 | Tier 2~3 |
| 6 | `tests/test_review_metrics_logger.py` | finding 라벨 케이스 추가 | §5.6 | Tier 1~2 |
| 7 | `tests/test_review_gate.py` | C1~C6 collision 케이스 | §7.2 | Tier 1~2 |

**검증 게이트**: 단일 commit이 Tier 3 trigger 시 af-test-runner → af-critic → af-cross-review 3-tier 전체 발화. 같은 commit message에 `blast_radius.py --json --files <list>` 사전 출력을 첨부하여 분류 근거를 검증 가능하게 한다.

### 8.3 Frozen Build Sanity (Critic #8 HOLD)

**약한 evidence**: v4 spec 변경은 hooks가 frozen 컨텍스트(`dist/af/af.exe`)에서 호출되는 경로의 동작을 직접 검증하지 않음. 특히 `_log_hook_event`가 새 키(`verdict_fallback`, `warn_only_suppressed`)를 쓸 때 workspace 경로 해석이 source build와 동일한지 미확인.

**Mac 단계에서는 검증 불가 → Windows PC 빌드 단계로 이관**:
- Windows PC에서 `python build_exe.py` → `dist/af-{version}.zip` 생성 후 `dist/af/af.exe`가 hook subprocess로 호출되는 경로 1회 sanity 호출:
  - `hook_runner.py`가 frozen mode에서 `_log_hook_event` 신규 이벤트 키 2종(`verdict_fallback`, `warn_only_suppressed`)을 정상 append하는지 확인.
  - `.af_review_queue/hook_events.log` 파일 권한·경로가 source build와 동일한지 확인.
- 비검증 시 install-af.ps1 배포 buyer에서 hook이 silent fail할 수 있음 (low probability, low severity).

### 8.4 단위 시나리오 회귀 (다음 .py 변경 사이클에서 자연스럽게 검증)

- 단위 시나리오(§7.1) **13건** (v3 10건 + v4 신규 11/12/13)
- collision 회귀(§7.2) **7건** (v3 5건 + v4 신규 C3b·C6)
- round 전환(§7.5) 6건
- 메트릭(§7.6) 4건
- WARN-only suppression(§5.4 신규) 1건 = 31건 회귀

### 8.5 CLAUDE.md 정책 변경 여부

CLAUDE.md 정책 변경 없음 (parser·gate 동작 binary 결과 불변). 단, hook_events.log 신규 키 2종(`verdict_fallback`, `warn_only_suppressed`)을 운영 메트릭 항목으로 §9.1에 등재 (CLAUDE.md 본문에는 미반영, 다음 §10 F2 결정 시 등재 검토).

---

## §9 운영 / 롤백 계획

### §9.1 운영 모니터링 (1주 baseline)

- **메트릭**: `review_metrics_logger.compute_report()` 에서 T3 verdict 분포 측정. (§5.6 정규식 확장 선행 필수.)
- **기대**: PASS 비율 ↓ (현재 100% 중 일부가 WARN으로 이동), WARN 비율 ↑.
- **운영 sink** (`hook_events.log`):
  - `verdict_fallback` 이벤트 — fence/패턴 0매칭 시점 1줄 (§5.5).
  - `warn_only_suppressed` 이벤트 — WARN/PASS 라운드 후 다음 사용자 prompt에서 no-fire 분기 진입 시점 1줄 (§5.4 신규).
- **우려 지표**:
  - WARN 비율 > 80% → advisory 노이즈 과다 가능성 (Medium 임계 재검토 트리거 — §10 F4).
  - `verdict_fallback` 이벤트 ≥ 1건/주 → LLM 출력 형식 표류 (§10 F2 후속).
  - severity 누락 BLOCK fail-safe 발화 ≥ 1건/주 → Step 5 프롬프트 가이드 강화 검토.
  - **(v4 신규)** `warn_only_suppressed` 빈도와 WARN verdict 발화 빈도가 0.8x~1.2x 범위 밖 → no-fire 정합성 의심 트리거 (G11).

### §9.2 롤백 트리거 (v4 정정 — 트리거 #1 measurable 재정의)

다음 중 하나라도 발생하면 §5.1/§5.3/§5.4/§5.5/§5.6 변경 revert:

- **(v4 정정)** WARN-only no-fire가 의도와 달리 작동:
  - **측정 방법**: 1주 baseline에서 `grep -c "warn_only_suppressed" .af_review_queue/hook_events.log` 빈도 vs `compute_report()` T3 WARN verdict 빈도 비교. WARN 라운드 종결 후 다음 사용자 prompt에서 정확히 1회 suppression 기대 → 두 빈도가 0.8x~1.2x 범위.
  - 범위 밖 + ≥ 1건/주 → §5.4 변경 revert + check_pending_review.py:126 분기 재검토.
- WARN 메시지가 사용자에게 BLOCK으로 오인 (UX 피드백).
- parser collision 발견 (fence 외부에서 verdict 라인 외 텍스트가 캡처되는 사례) — `verdict_fallback` 이벤트 빈도 ≥ 5건/주 + 발생 케이스 grep 후 false positive 확인.
- `_FINDING_RE` 확장으로 인한 false positive 매칭 (예: 코드 인용 안의 `[ACCEPT-ADV]` 캡처) — `compute_report()` finding count vs 수동 grep 결과 비교.

### §9.3 롤백 절차

```bash
git revert <commit-hash-of-v5-implementation>
# 7개 파일 단일 commit (§8.2) — 단일 revert로 복구 가능
```

**roll-back safe property** (v5 통일): §5.2(`af-critic.md`)는 무변경. v5에서도 §5.4가 변경 대상(`warn_only_suppressed` log 1줄, 4-arg 정정), 변경된 모든 파일은 추가 진단/방어 (fence-aware wrapper, last-position 결합, fallback log, suppression log, 정규식 확장) → revert 시 v3 동작으로 복귀(데이터 손상 없음). v5 → v3 → v2 단계 revert도 가능.

### §9.4 사전 검증 명령

v3 commit 전 로컬에서 다음 체크:

```bash
# §5.6 정규식 검증
python -c "
import re
p = re.compile(r'\[(?:ACCEPT(?:[★*]|-ADV)?|WARN|BLOCK|REJECTED|BONUS)\]', re.IGNORECASE)
samples = ['[ACCEPT]','[ACCEPT★]','[ACCEPT*]','[ACCEPT-ADV]','[WARN]','[BLOCK]','[REJECTED]','[BONUS]','[HOLD]']
for s in samples:
    print(s, '→', bool(p.match(s)))
"
# 기대: HOLD만 False, 나머지 True

# §7.2 collision 회귀
pytest tests/test_review_gate.py -v -k "collision or fence"

# §7.6 메트릭 정합
pytest tests/test_review_metrics_logger.py -v
```

---

## §10 미결 사항 (다음 세션 / Phase 3+)

| ID | 항목 | 우선순위 | 이관처 |
|----|------|--------|------|
| F1 | [HOLD] finding 입구 조건 정의 + 라벨 재도입 (G3) | High | Phase 3 (deliberation 알고리즘) |
| F2 | `verdict_fallback` 이벤트 발화 시 권장 처리 (자동 재실행? 사용자 알림?) | Medium | §9.1 1주 운영 후 |
| F3 | WARN 비율 baseline 측정 (1주 운영 후) | Medium | Phase 2 검증 후 |
| F4 | Medium → BLOCK 임계 재검토 | Low | WARN 비율 > 80% 시 트리거 |
| F5 | BONUS Critical/High WARN 적정성 | Low | 운영 데이터 기반 판단 |
| F6 | finding 라벨에 `[ACCEPT★]` 별표 표기의 자동화 가능성 | Low | LLM 재현성 측정 후 |
| **F7 (v3 신규)** | **과거 review의 라벨 일괄 재라벨링 (선택)** | Low | `docs/reviews/` 30건 grep 일관성. **본 시점 기준 그대로 유지가 default — §11 명시.** |
| **F8 (v4 신규 — Missing #2)** | **`AF_GATE_ALLOW_VERDICT_BLOCK` 환경 변수 + fence 외부 잔존 인용 처리** | Medium | Phase 3 — gate-level fail-safe 도입과 함께. 사용자가 fence 외부 인용을 의도적으로 사용하는 케이스(예: 문서 내부에 verdict 사례 표기)에서 BLOCK 우회 옵션 필요 시. |
| **F9 (v4 신규 — Missing #3)** | **마이그레이션 윈도우 — v2 라벨 PR과 v3/v4 라벨 PR 공존 시 `compute_report()` 일관성** | Medium | v3/v4 정규식이 v2 라벨(`[ACCEPT]`/`[ACCEPT★]`/`[WARN]`/`[BLOCK]`/`[REJECTED]`)을 포함하므로 호환됨. 다만 1주 운영 후 "신/구 라벨 혼합 review" 빈도 측정 → 0건이면 본 항목 closed. ≥ 1건이면 신규 라벨로 일괄 재라벨링 검토 (F7과 연계). |

---

## §11 v2 → v3 → v4 → v5 변경 요약 (감사 추적용)

### v2 → v3

| 항목 | v2 (`f8be0794`) | v3 (`d9cc3304`) |
|------|----------------|-------------|
| 매핑 테이블 | §4.3 단일 정규 테이블 | + severity 누락 fail-safe 행 추가 (G9) |
| HOLD 처리 | finding-level forward-looking 정의 + Phase 3 입구 조건 이관 | **finding-level 정의 자체 제거** (G3 prompt drift 회피) |
| `[BONUS]` | 라벨 prefix 아님 — Codex Round 1 분류 | **finding 라벨로 승격** — 헤더 = `#### N. [BONUS] [Severity] 제목` (G10) |
| Severity 누락 처리 | 미정의 | **BLOCK fail-safe default** (§4.3 / §7.1 시나리오 9, G9) |
| `_VERDICT_RE` collision (G7) | 미인식 | **fence 도입** + `_extract_verdict_from_content()` wrapper (§5.1 변경 8 / §5.3) |
| Silent verdict fallback (G4) | Phase 후속 이관 (§10 F2) | **Phase 2 차단 의존성으로 격상** — `_log_hook_event("verdict_fallback")` (§5.5) |
| `_FINDING_RE` 회귀 (G8) | 미인식 — §9.1 self-defeat | **정규식 확장 + 테스트** (§5.6) |
| Round 전환 회귀 시나리오 | §7.5 단일 라운드만 | **R3~R6 4건 추가** (§7.5) |
| 라벨 마이그레이션 가이드 | 미언급 | **§11에 "기존 review 시점 기준 유지" 1줄 + §10 F7 신설** |
| 코드 변경 범위 | design-only (af-cross-review.md만) | **scripts/*.py 3건 + tests/*.py 2건 추가** (`scripts/*.py` 3건 + `tests/*.py` 2건 + agent md 1건 = 6파일, v5 정정 후 재집계는 7파일 — Critic #7) |

### v3 → v4 (Critic 8건 + Missing 4건 전수 반영)

| 항목 | v3 (`d9cc3304`) | v4 (본 문서) | Critic 출처 |
|------|----------------|-------------|------------|
| §5.3 last-match 결합 알고리즘 | 미명세 — 두 정규식의 last-match 결합 정책 모호 | **last-position 결합 명시** — 두 패턴 매칭을 (start_position, label) 튜플로 합쳐 last-position 1건 선택 (단일 패스) + 의사 코드 첨부 | High #1 |
| §4.3 [REJECTED] vs severity fail-safe 충돌 | 충돌 — REJECTED severity 누락이 BLOCK으로 카운트 (의도-반전) | **[REJECTED] verdict-neutral 우선 단서** + §5.1 변경 6 "REJECTED severity 생략 허용" 명시 + §7.1 시나리오 11/12/13 추가 | High #2 |
| §5.5 G4 fallback 강도 | "Phase 2 차단 의존성" 격상 (과장) | **detection-only 강등** — gate-level 차단은 Phase 3 (§6 G4 행) — `verdict="pass"` 그대로 전파, hook event만 추가 | High #3 |
| §5.4 변경 여부 | "변경 없음" — 측정 sink 부재로 §9.2 트리거 #1 falsifiable 불가 | **`_log_hook_event("warn_only_suppressed")` 1줄 추가** (G11 신규) → §9.2 트리거 #1 measurable 재정의 | Medium #4 |
| §8 부트스트랩 순서 | "af-test-runner만" + "Tier 2~3 발화 가능" 자기모순 | **단일 commit + 3-tier 전체 + blast_radius 사전 출력** 전략 + chicken-and-egg 명시 | Medium #5 |
| §5.3/§5.5 wrapper 호출자 | "is_gate_blocked/record_review_done 등 통합" — 실제는 hook_runner.py만 호출 | **wrapper 단일 호출자(=hook_runner.py) 명시** + record_review_done은 본문 파싱 무관 명시 | Medium #6 |
| §5.6 SCOPE_CREEP_RE 정책 | §5.1 변경 5 fence 한정 vs `_SCOPE_CREEP_RE` 전역 검색 충돌 (G12 신규) | **fence 외부 검색 유지** 명시 (단순성) — 코드 동작 무변경, 정책 명시만 | Low #7 |
| §8 frozen build sanity | 미언급 | **Windows PC 빌드 단계로 이관** — frozen `dist/af/af.exe`로 hook 1회 sanity 호출 의무 (Mac 검증 불가) | HOLD #8 |
| §5.3 record_review_done 인자 | 인자 신뢰 관계 미명시 | **wrapper와 무관 — caller가 추출한 verdict를 그대로 신뢰** 명시 | Missing #1 |
| §10 F8 (AF_GATE_ALLOW_VERDICT_BLOCK) | 미정의 | **§10 F8로 등록 (Phase 3 후보)** | Missing #2 |
| §10 F9 (마이그레이션 윈도우) | 미언급 | **§10 F9로 등록** + v3/v4 정규식이 v2 라벨 호환임을 명시 | Missing #3 |
| §5.3 다중/중첩 fence | 미명시 | **첫 쌍만 인식, 둘째 쌍 무시** + §7.2 C6 케이스 추가 | Missing #4 |
| 코드 변경 파일 수 | 6개 | **7개** (`check_pending_review.py` 추가 — §5.4) | Medium #4 효과 |
| `_VERDICT_FENCE_RE` 정의 | 미명시 | **scripts/review_gate.py에 정규식 명시** + DOTALL flag로 multiline fence 본문 캡처 | High #1 부산물 |
| §4.6 fail-safe 표현 | "fail-safe" (gate-level 함의) | **"detection fail-safe"로 강등** — §6 O5와 정합 | High #3 부산물 |

### v4 → v5 (Critic 8건 BLOCK 해제 + line 인용 무결성)

| 항목 | v4 (`2174812c`) | v5 (본 문서) | Critic 출처 |
|------|----------------|-------------|------------|
| §5.4 `_log_hook_event` 시그니처 | **3-arg 호출 (v3 BLOCK 재도입)** — `(workspace, "warn_only_suppressed", {dict})` → dict가 exit_code 자리, repr 직렬화 | **4-arg + JSON 직렬화** — `("warn_only_suppressed", str(round_count), 0, error=json.dumps({...}))` | Critical #1 |
| §5.4 helper 시그니처 설명 | "(workspace, event_name, payload)" 잘못 기술 | **`(builtin, file, exit_code, error="")` 4-arg로 §5.5와 통일** + line 100 정의 인용 | Critical #1 |
| §5.3 prose vs 의사 코드 충돌 | "충돌 시 `_VERDICT_RE` 우선" prose vs stable sort 동작(matches[-1]는 둘째 = `_VERDICT_HEADER_RE`) | **두 정규식 disjoint 단언** + stable sort 동작 정규로 채택 (prose "VERDICT_RE 우선" 삭제) | High #2 |
| §5.5 line 인용 | "line 64 helper" — 실제 line 64는 `_find_venv_python()` `return sys.executable` (무관) | **`hook_runner.py:100` 정정** + line 64 인용은 오류였음 명시 | High #3 |
| §5.4 import 전략 | "import하거나 inline 재정의" — 미결정 | **`from scripts.hook_runner import _log_hook_event` import 결정** + workspace path 일관성·import 비용·private prefix 단언 + try/except fallback | High #4 |
| §5.4 sink 폭발 | hook event 기록을 1회-알림 분기 **밖** — 매 UserPromptSubmit마다 N:1 폭발 | **1회-알림 분기 안으로 이동** — WARN 라운드당 정확히 1건 sink + §9.2 트리거 #1 1:1 정합 단순화 | High #5 |
| §8.2 단일-commit 자기모순 | "본 commit 검증 라운드는 이전 fence 없는 형식으로 실행됨" 단정 | **staged 코드와 reviewer 동시 활성화 명시** + agent definition cache grace period로 chicken-and-egg 해소 prose 정확화 | Medium #6 |
| §11 history table 미갱신 | scripts 3건 + tests 2건 (v3 기준) 잔존 / §9.3 "6개 파일" / §8.2 표 7개 — 3·6·7 충돌 | **§11 v3 row 정정 (6→7파일 명기) + §9.3 "7개 파일" + §8.2 표 7개로 통일** | Medium #7 |
| §7.6 false-positive 회귀 | true-positive 4 시나리오만 — 신규 라벨 noise surface 50% 증가했으나 회귀 부재 | **false-positive 시나리오 5/6 추가** (markdown fence 내부 [ACCEPT-ADV] / prose 인용 [BONUS]) + 정책 명시 (현 정책: 모두 카운트, §10 F4 트리거) | Medium #8 |
| line 인용 무결성 audit | 미언급 | **§11 audit 1행 추가** — v3→v4에서 line 100 → line 64 잘못 인용 재발 패턴 메타 가드 | Critic #3 권장 #4 |
| 코드 변경 파일 수 | 7개 (정합) | **7개 유지** — `check_pending_review.py` 변경 내역만 정정 | Critic #7 부산물 |
