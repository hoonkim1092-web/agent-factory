# External API 3-Tier Fallback 표준

- 작성일: 2026-04-18
- 상태: 확정
- 관련 불변식: I3 (External Dependency 3-tier)

## 개요

외부 API에 의존하는 모든 AF 프로젝트는 아래 3-티어 fallback을 강제한다.
야간 무인 파이프라인에서 네트워크 차단, API 다운, rate-limit 등으로 인한 정지를 방지하기 위함이다.

```
Tier 1 live   →  Tier 2 cache  →  Tier 3 seed
(실시간 API)     (로컬 DB/파일)    (정적 번들 JSON)
```

## 계층별 책임

| 계층 | 소스 | 조건 | 로깅 |
|------|------|------|------|
| Tier 1 live | 외부 HTTP API | 기본 경로 | `source=live` (DEBUG) |
| Tier 2 cache | SQLite / 파일 캐시 | live 실패 시 | `source=cache` (INFO) |
| Tier 3 seed | `seed_draws.json` 등 번들 | cache도 없을 때 | `source=seed` (INFO) |

## 구현 계약

1. **live 실패** → WARNING 로그 + Tier 2 시도. 예외를 외부로 전파하지 않는다.
2. **cache 실패** → WARNING 로그 + Tier 3 시도.
3. **Tier 3 데이터로 응답 시** 응답 dict에 `"source": "seed"`, `"status": "degraded-success"` 포함.
4. **3-티어 모두 실패** → `DataUnavailableError` 발생. 야간 파이프라인은 이 예외를 degrade task로 처리.

## Seed 파일 관리

- 경로: `projects/<project>/seed_draws.json` (프로젝트 루트 기준)
- 스키마: `{"_meta": {...}, "draws": [{"drw_no": N, "drw_date": "YYYY-MM-DD", "numbers": [...], "bonus_no": N}]}`
- 갱신: `scripts/refresh_lotto_seed.py` 월 1회 실행 (또는 수동)
- `_meta.age_days`: 마지막 갱신 후 경과일. 90일 초과 시 WARNING.

## 구현 예시 — Python

```python
class ThreeTierClient:
    def fetch(self, key):
        try:
            return self._live.fetch(key)        # Tier 1
        except Exception as exc:
            logger.warning("Tier1 실패: %s", exc)

        cached = self._cache.get(key)           # Tier 2
        if cached is not None:
            return cached

        seed = self._seed.get(key)              # Tier 3
        if seed is not None:
            logger.info("source=seed key=%s", key)
            return seed

        raise DataUnavailableError(f"3-티어 모두 실패: {key}")
```

## 참조 구현

- `projects/lotto_predictor_v2/src/lotto_predictor/backend/http_client.py` — `ThreeTierLotteryClient`
- `projects/lotto_mobile_web/server/services/recommendation.py` — `RecommendationService._load_seed()`
