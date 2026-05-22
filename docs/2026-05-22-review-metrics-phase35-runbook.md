# Phase 3.5 Review Metrics Runbook

> 목적: `review_metrics_logger` 운영 절차 + Phase 4 진입 판정 기준 참조 문서.  
> 구현 커밋: `f75e01b4` (Phase 3.5 측정 인프라 수술적 수정)

---

## 1. 구조 개요

```
.af_review_queue/
  review_metrics.jsonl   # 에이전트 완료 이벤트마다 1행 기록
  skip_audit.jsonl       # Tier 3 skip 후 BLOCK 발견 사례
```

**데이터 생산**: `scripts/hook_runner.py` → `append_metric()` 자동 호출 (에이전트 완료 시).  
별도 실행 불필요 — 리뷰 파이프라인 정상 동작 시 자동 축적.

---

## 2. report 실행

```bash
# 기본 (현재 git repo workspace 자동 감지)
python scripts/review_metrics_report.py

# workspace 명시
python scripts/review_metrics_report.py /path/to/workspace

# raw JSONL 덤프
python scripts/review_metrics_report.py --raw

# 또는 logger 직접
python scripts/review_metrics_logger.py
```

---

## 3. report 출력 판독

```
=== Review Metrics Report (Phase 3.5) ===
기간: 2026-05-22 ~ 2026-05-29
총 레코드: 42 (T3: 18 / 커밋: 14)

── T3-only 기여도 ──
  전체 findings: T1=8  T2=15  T3=12
  T3 finding share (단순 비율, T3 고유값 ≠): 34.3%
  [Phase 4 primary] T3 BLOCK-only 커밋: 4 / 14
  skip audit: 총 2건 (이후 BLOCK 발견: 0건)
  → T3 고유 가치 큼 — skip 보수적 유지 권고
  T3 평균 extension log: 2.3건

── 에이전트별 verdict 분포 ──
  af-critic: block:2  pass:10  warn:2  (총 14)
  af-cross-review: pass:12  warn:6  (총 18)
  af-test-runner: pass:14  (총 14)

── 미지원 필드 ──
  tokens/tool_calls: 미지원 (API 통합 필요)
```

### 핵심 지표

| 필드 | 의미 |
|------|------|
| `T3 finding share` | T3 findings / 전체 findings. **참고용** — T3 고유값(T1/T2와 중복 없는 것)이 아님에 주의 |
| `[Phase 4 primary] T3 BLOCK-only 커밋` | T3만 BLOCK이고 T1/T2는 BLOCK이 아닌 커밋 수. **Phase 4 판단의 1차 지표** |
| `skip 후 BLOCK 발견` | Tier 3 skip 후 이후 라운드/PR에서 BLOCK 발견된 건수. 1건이라도 있으면 Phase 4 진입 금지 |

---

## 4. Phase 4 진입 판정 기준

### 게이트 조건 (모두 충족 필요)

| 조건 | 기준 | 비고 |
|------|------|------|
| 최소 커밋 수 | T3 동반 커밋 ≥ 10개 | 샘플 부족 시 `⚠️ 데이터 부족` 출력 |
| 최소 기간 | ≥ 7일 | 단기 집중 작업 편향 방지 |
| skip-후-BLOCK | 0건 | 1건이라도 있으면 `⚠️ Phase 4 판단 불가` 출력 |

### routing 방향 결정 (게이트 통과 후)

**1차 지표**: `T3 BLOCK-only 커밋 / T3 동반 커밋 비율`

| 비율 | 권고 |
|------|------|
| > 30% | T3 고유 가치 큼 — skip 보수적 유지 |
| 10 ~ 30% | 중간 — 위험군 외 선택적 skip 검토 가능 |
| < 10% | T3 대체로 중복 — 공격적 skip 가능 (Phase 4 진입 검토) |

> `T3 finding share`는 보조 지표. T1/T2가 같은 issue를 이미 잡아도 T3 share가 높게 나올 수 있으므로 단독 판단 금지.

---

## 5. skip_audit.jsonl 기록 시점

현재 `append_skip_audit()` API는 구현됨 (`review_metrics_logger.py:182`).  
**호출 시점은 Phase 4 구현 시 추가 예정** — Tier 3 skip routing 로직(`check_pending_review.py` 또는 `review_gate.py`)에서 skip 이벤트 발생 시 호출.

지금은 skip_audit.jsonl이 비어 있으므로 `skip audit: 총 0건` 출력이 정상.

---

## 6. Phase 4 진입 체크리스트

```
□ python scripts/review_metrics_report.py 실행
□ "데이터 부족" 경고 없음 (커밋 ≥10, 기간 ≥7일)
□ "skip 후 BLOCK 발견" = 0건
□ T3 BLOCK-only 비율 확인 → routing 방향 결정
□ T3 finding의 Critical/High severity 비율 별도 수동 검토
  (전체 비율 < 10%여도 Critical이 있으면 skip 금지)
□ Phase 4 구현 진입 (smart routing + Tier 3 조건부 발화)
```

---

## 참고

- 설계 계획: `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md §Phase 3.5`
- 구현: `scripts/review_metrics_logger.py`, `scripts/review_metrics_report.py`
- hook 연결: `scripts/hook_runner.py` (append_metric 호출부)
