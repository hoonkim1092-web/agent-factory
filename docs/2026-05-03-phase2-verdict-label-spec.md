# Phase 2: 판정 라벨 명시화 설계 (재설계 v3)

작성일: 2026-05-03 (v3 — Critic 8건 전수 반영 + 코드 변경 범위 확장)
대상 브랜치: `2026-04-14-build-diet`
선행 완료: Phase 1a (`a8025d25` — af-cross-review.md Step 1+2+3 프롬프트 개선)
선행 검토: 본 문서 v2 (`f8be0794`)에 대한 Final Design Review (`docs/reviews/2026-05-03-210936-2026-05-03-phase2-verdict-label-spec-design-review.md`) — Critic 단독 8건 (Cross-review provider error로 미수행, Phase 2 commit 전 재실행 필수 — §8)

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

→ Phase 2는 **labeling 정확화**가 본질이다(§4.6). 단, **labeling 변화가 메트릭/파서를 통과해 효과를 검증할 수 있어야 substantive하다** — 이를 위해 v3은 코드 변경 3건(`review_metrics_logger.py`, `hook_runner.py`, `review_gate.py`)을 Phase 2 차단 의존성으로 격상한다(§5.3/§5.5/§5.6).

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

| ID | 갭 | 위치 | 영향 | v3 처리 |
|----|-----|------|------|--------|
| G1 | T3가 WARN을 발화하지 않음 | af-cross-review.md Step 5 매핑 | advisory 신호 손실 | §5.1 |
| G2 | `[ACCEPT]` 라벨이 BLOCK용/Advisory용 두 의미로 중첩 | af-cross-review.md:283/302 | LLM/리뷰어 혼동 | §5.1 |
| G3 | `[HOLD]` finding 입구 조건 미정의 | Step 3/4 어디에도 진입 조건 없음 | dead label | **Phase 3로 완전 이관 — v3에서 정의도 빼기** (§5.1 / §6) |
| G4 | parser silent fallback ("pass") | hook_runner.py:344 | 형식 위반 시 조용히 PASS, §9.2 롤백 트리거 falsifiable 무효화 | **Phase 2 차단 의존성으로 격상** — `_log_hook_event("verdict_fallback")` 추가 (§5.5) |
| G5 | v1/v2 `§4.2/§4.3/§5.1` 다중 테이블 | (v1·v2 문서) | 구현 혼란 | v2 §4.3 단일 정규 테이블로 정리 완료 |
| G6 | v1 §7.3이 잘못된 코드 경로(`is_gate_blocked()`) 인용 | (v1 문서) | no-fire 보장 불완전 | v2 §7.3 정정 완료 |
| **G7** | **`_VERDICT_RE.search()` collision — 본문에 prior round 판정 인용 시 캡처 가능** | review_gate.py:25-28 | LLM 자기 통제 100% 의존, spec defect | **Phase 2 차단 — verdict fence 도입** (§5.1 변경 8 / §5.3) |
| **G8** | **`_FINDING_RE` 회귀 — `[ACCEPT-ADV]` 미매칭** | review_metrics_logger.py:31-34 | findings_count=0, §9.1 운영 검증 self-defeat | **Phase 2 차단 — 정규식 확장** (§5.6) |
| **G9** | **severity 누락 매핑 결정 불가** | §4.3 (매핑 입력) | LLM이 severity 잊을 시 silent miscategorization | **§4.3에 fail-safe default 행** (§4.3 / §7.1 시나리오 9) |
| **G10** | **BONUS finding의 출력 헤더 라벨 미정의** | §5.1 (출력 형식) | 검증 시나리오 입력 명세 불완전 | **§5.1 변경 6에 BONUS 헤더 규칙 명시** |

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
| `[REJECTED]` | any | (verdict-neutral — 무시) |
| `[BONUS]` | any | **WARN** |
| **(severity 누락 — fail-safe default)** | (지정 안 됨) | **BLOCK** |
| (발견 없음) | — | **PASS** |

**§4.3 변경 (G9 해소)**: severity bracket이 누락된 finding은 BLOCK 안전 default로 처리한다. Critical/High 가능성이 있는 항목을 silent miscategorization로 잃지 않기 위함. LLM 출력 정확성에 의존하지 않는 fail-safe.

### §4.4 집계 규칙 (우선순위 내림차순)

```
1. BLOCK 기여 finding ≥ 1   → 최종 verdict = BLOCK
2. (BLOCK 없음) WARN 기여 finding ≥ 1   → 최종 verdict = WARN
3. (BLOCK·WARN 둘 다 없음)   → 최종 verdict = PASS
```

REJECTED는 어느 카운트에도 들어가지 않는다 (verdict-neutral).
severity 누락 finding은 §4.3 fail-safe로 BLOCK 1건이 카운트된다.

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
- ✅ **v3 추가** — `_VERDICT_RE` collision이 fence로 차단된다.
- ✅ **v3 추가** — verdict 파서 silent fallback이 hook 이벤트로 가시화된다.
- ❌ gate 차단 빈도는 바뀌지 않는다 (둘 다 차단 안 함).
- ❌ no-fire 발화 빈도는 바뀌지 않는다 (둘 다 has_block=False).

→ **Phase 2는 정책 변화가 아닌 labeling+측정 정확화다.** 운영 risk가 매우 낮음 (코드 변경 3건은 모두 추가 진단/방어 — 기존 정상 경로 비파괴).

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
   - Severity: `[Critical]` / `[High]` / `[Medium]` / `[Low]` 4종 — **BONUS 포함 의무**.
   - **severity 누락 시**: §4.3 fail-safe로 BLOCK 처리됨 — Step 5 출력 형식에 "severity 누락은 BLOCK으로 안전 처리됨" 명시 (G9 해소).
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

### §5.3 `scripts/review_gate.py` (변경) — v3 추가

**v3 변경 사유 (G7 해소)**: `_VERDICT_RE.search()` 첫 매칭 정책이 본문 인용을 잘못 캡처하는 collision 위험이 있음.

**구체 변경**:
- `_extract_verdict_from_content(content: str) -> str | None` 신규 함수.
  - 1순위: fence 내부(`<!-- final-verdict-start -->` ~ `<!-- final-verdict-end -->`)에서만 `_VERDICT_RE`/`_VERDICT_HEADER_RE` 매칭.
  - 2순위(폴백): fence 부재 시 기존 동작 유지 — 단, **last-match 우선** (`re.findall()` 후 마지막 항목)으로 정책 전환. 본문 인용은 보통 위쪽에 있고 verdict 라인은 마지막에 있다.
  - 호환성: af-critic.md, af-test-runner.md는 fence 미사용 → 폴백 경로로 정상 동작.
- `is_gate_blocked()` / `record_review_done()` / `_compute_round_summary()` 등은 `_extract_verdict_from_content()`를 사용하도록 통합.
- 기존 동작 보존: `_VERDICT_RE`/`_VERDICT_HEADER_RE` 패턴 자체는 무변경.

**테스트 추가 의무** (§7.2):
- fence 내부 매칭 케이스
- 본문 인용 + fence 외부 verdict 라인 → fence 내부만 캡처
- fence 부재 + 단일 verdict 라인 → 정상 캡처
- fence 부재 + 본문에 "이전 라운드 판정: BLOCK" + 마지막 라인 verdict=PASS → last-match 정책으로 PASS

### §5.4 `scripts/check_pending_review.py` (변경 없음)

WARN-only no-fire가 `last_summary.has_block`만 본다. WARN/PASS 둘 다 has_block=False → 동일 동작.

### §5.5 `scripts/hook_runner.py` (변경) — v3 추가

**v3 변경 사유 (G4 해소 — Phase 후속 이관 → Phase 2 차단 의존성으로 격상)**: silent "pass" fallback이 Phase 2 효과(verdict 라인 글자 변경)를 LLM 출력 형식 표류 시 침묵 무력화. §9.2 롤백 트리거가 falsifiable하지 않게 됨.

**구체 변경** (`hook_runner.py:343-346`):
```python
# 변경 전
hm = _VERDICT_HEADER_RE.search(content)
verdict = hm.group(1).lower() if hm else "pass"

# 변경 후
hm = _VERDICT_HEADER_RE.search(content)
if hm:
    verdict = hm.group(1).lower()
else:
    verdict = "pass"
    _log_hook_event(workspace, "verdict_fallback", {
        "agent": agent,
        "round": round_count,
        "content_head": content[:200],
    })
```

`_log_hook_event()`는 `hook_events.log`에 append. `review_metrics_logger`가 별도 sink로 fallback 발생률을 집계할 수 있도록 함.

**호환성**: 정상 verdict 출력 케이스는 동작 무변경. fallback이 발화되는 시점에만 1줄 로그 추가.

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
| ~~G4~~ | ~~parser silent fallback 강화~~ | **v3에서 Phase 2 차단 의존성으로 격상** (§5.5) — 이관 취소 |

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

**v3 collision 회귀 케이스 (§5.3 신규 단위 테스트)**:

| # | 입력 | 기대 |
|---|------|------|
| C1 | fence 내부 단일 `## Tier 3 판정: WARN` | verdict=warn |
| C2 | 본문에 "이전 라운드 판정: BLOCK" + fence 내부 `## Tier 3 판정: PASS` | verdict=pass (fence 내부만 인식, G7 해소) |
| C3 | fence 부재 + 본문에 "verdict: BLOCK" 인용 + 마지막 라인 `## Tier 3 판정: PASS` | verdict=pass (last-match 폴백 정책, §5.3) |
| C4 | fence 부재 + 단일 `Verdict: BLOCK` (af-critic 형식) | verdict=block (호환성) |
| C5 | fence 부재 + verdict 라인 0개 | `_extract_verdict_from_content() → None` → caller가 silent fallback("pass") + `_log_hook_event("verdict_fallback")` (§5.5 G4) |

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

### §7.6 메트릭 정합 검증 (v3 신규 — G8)

**시나리오**: af-cross-review 출력에 `[ACCEPT-ADV]` Medium 3건, `[BONUS]` Low 1건 포함.

1. `review_metrics_logger.parse_findings_count(content)` → `_FINDING_RE.findall(content)` → 4건 매칭 (`[ACCEPT-ADV]` 3 + `[BONUS]` 1)
2. `compute_report()` → `findings_per_review = 4` → §9.1 WARN 비율 산출 정상 ✓

기존 회귀 보호:
3. af-critic의 `Verdict: PASS` (대문자, 라벨 미사용) → `parse_findings_count → 0` (변경 없음).
4. af-cross-review의 `[REJECTED]` × 5 → `findings_count = 5` (verdict-neutral이지만 finding 발견량은 카운트 — 기존 정책 유지).

---

## §8 구현 순서

1. 본 v3 문서에 대해 **af-cross-review만 교차검증** 실행 (단일 설계문서 정책).
   - codex usage limit 회복(2026-05-05 15:37 KST 이후) 후 실행. 그 이전에는 v2 BLOCK 미해소(provider error)로 인해 commit 차단.
2. 검증 PASS 확인 후, 코드+에이전트 변경 일괄 적용 (다음 6개 파일):
   - `.claude/agents/af-cross-review.md` Step 5 (§5.1 변경 1~8)
   - `scripts/review_gate.py` (§5.3 wrapper 신설)
   - `scripts/hook_runner.py` (§5.5 verdict fallback 가시화)
   - `scripts/review_metrics_logger.py` (§5.6 정규식 확장)
   - `tests/test_review_metrics_logger.py` (§5.6 신규 케이스)
   - `tests/test_review_gate.py` (또는 신규) — §7.2 collision 회귀 C1~C5
3. `core/*.py` 변경이 없으므로 **af-cross-review.md 변경에 대해 af-test-runner만** 재실행 (Tier 1: 에이전트 설정 파일). 단, `scripts/*.py` 3건 변경 + 테스트는 Tier 2~3 발화 가능 — `scripts/blast_radius.py`로 사전 분류 권장.
4. 단위 시나리오(§7.1) 10건 + collision 회귀(§7.2) 5건 + round 전환(§7.5) 6건 + 메트릭(§7.6) 4건 = 25건 회귀 (다음 .py 변경 사이클에서 자연스럽게 검증).
5. 커밋. CLAUDE.md 정책 변경 없음 (parser·gate 동작 binary 결과 불변).

---

## §9 운영 / 롤백 계획

### §9.1 운영 모니터링 (1주 baseline)

- **메트릭**: `review_metrics_logger.compute_report()` 에서 T3 verdict 분포 측정. (§5.6 정규식 확장 선행 필수.)
- **기대**: PASS 비율 ↓ (현재 100% 중 일부가 WARN으로 이동), WARN 비율 ↑.
- **우려 지표**:
  - WARN 비율 > 80% → advisory 노이즈 과다 가능성 (Medium 임계 재검토 트리거 — §10 F4).
  - `verdict_fallback` 이벤트 ≥ 1건/주 → LLM 출력 형식 표류 (§10 F2 후속).
  - severity 누락 BLOCK fail-safe 발화 ≥ 1건/주 → Step 5 프롬프트 가이드 강화 검토.

### §9.2 롤백 트리거

다음 중 하나라도 발생하면 §5.1/§5.3/§5.5/§5.6 변경 revert:

- WARN-only no-fire가 의도와 달리 작동 (`verdict_fallback` 이벤트 또는 재발화 빈도 측정으로 확인 — falsifiable해짐, G4 해소).
- WARN 메시지가 사용자에게 BLOCK으로 오인 (UX 피드백).
- parser collision 발견 (fence 외부에서 verdict 라인 외 텍스트가 캡처되는 사례).
- `_FINDING_RE` 확장으로 인한 false positive 매칭 (예: 코드 인용 안의 `[ACCEPT-ADV]` 캡처).

### §9.3 롤백 절차

```bash
git revert <commit-hash-of-v3-implementation>
# 6개 파일 단일 commit 권장 — 단일 revert로 복구 가능
```

**roll-back safe property**: §5.2/§5.4가 무변경. 변경된 5개 파일은 모두 추가 진단/방어 (silent fallback gate, fence-aware wrapper, 정규식 확장) → revert 시 v2 동작으로 복귀, 데이터 손상 없음.

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

---

## §11 v2 → v3 변경 요약 (감사 추적용)

| 항목 | v2 (`f8be0794`) | v3 (본 문서) |
|------|----------------|-------------|
| 매핑 테이블 | §4.3 단일 정규 테이블 | + severity 누락 fail-safe 행 추가 (G9) |
| HOLD 처리 | finding-level forward-looking 정의 + Phase 3 입구 조건 이관 | **finding-level 정의 자체 제거** (G3 prompt drift 회피, Critic #4) |
| `[BONUS]` | 라벨 prefix 아님 — Codex Round 1 분류 | **finding 라벨로 승격** — 헤더 = `#### N. [BONUS] [Severity] 제목` (G10) |
| Severity 누락 처리 | 미정의 | **BLOCK fail-safe default** (§4.3 / §7.1 시나리오 9, G9) |
| `_VERDICT_RE` collision (G7) | 미인식 | **fence 도입** + `_extract_verdict_from_content()` wrapper (§5.1 변경 8 / §5.3) |
| Silent verdict fallback (G4) | Phase 후속 이관 (§10 F2) | **Phase 2 차단 의존성으로 격상** — `_log_hook_event("verdict_fallback")` (§5.5) |
| `_FINDING_RE` 회귀 (G8) | 미인식 — §9.1 self-defeat | **정규식 확장 + 테스트** (§5.6) |
| Round 전환 회귀 시나리오 | §7.5 단일 라운드만 | **R3~R6 4건 추가** (§7.5, Critic #7) |
| 라벨 마이그레이션 가이드 | 미언급 | **§11에 "기존 review 시점 기준 유지" 1줄 + §10 F7 신설** (Critic #8) |
| 코드 변경 범위 | design-only (af-cross-review.md만) | **scripts/*.py 3건 + tests/*.py 2건 추가** — §5.3/§5.5/§5.6 |
| Phase 2 substantive | "labeling only — 기능 불변" (§4.6) | **"labeling + 측정/파이프라인 정합"** (§4.6) — 메트릭/파서 fail-safe 포함 |
| 정규 출처 명확화 | "§4.3가 THE source of truth" | (유지) + "§5.6 정규식이 메트릭 정규 출처" |
