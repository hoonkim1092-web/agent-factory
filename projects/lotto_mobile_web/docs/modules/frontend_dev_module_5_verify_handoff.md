# Frontend Module 5 — 오프라인 캐시 폴백 Verify Handoff

- 모듈: `frontend_dev_module_5` (오프라인 캐시 폴백)
- 완료일: 2026-04-18
- 상태: PASS (조건부 — 수동 스모크 권장 항목 2건)

## 1. 검증 범위

build 단계에서 구현된 오프라인 캐시 폴백 모듈(`web/js/app.js`, `web/js/components/OfflineBanner.js`, `web/styles/layout.css`)의 계약 준수 여부와 테스트 회귀성을 확인한다.

## 2. 수행한 검증

### 2.1 자동 테스트
```bash
cd projects/lotto_mobile_web
python -m pytest tests/frontend -q
```

**결과**: 7 passed (0.27s)

테스트 파일별 결과:
- `test_smoke_render.py` (4) — 셸 구조, 자산, export 계약
- `test_offline_cache_contract.py` (2) — 캐시 저장·복구·배너 소스 수용
- `test_param_panel_contract.py` (1) — 파라미터 패널 계약

### 2.2 JavaScript 구문 검증
```bash
node --check web/js/app.js
node --check web/js/components/OfflineBanner.js
```
**결과**: OK (구문 오류 없음)

### 2.3 계약 검증 체크리스트

| 항목 | 결과 | 근거 |
|---|---|---|
| 성공 응답 `localStorage` 저장 | ✅ | `test_offline_cache_persists_and_restores_last_success` |
| 24시간 TTL 검증 | ✅ | `app.js` `isCacheValid()` — `Date.now() - savedAt > 24*60*60*1000` |
| 캐시 형상 검증 (version=1, params/result 최소 shape) | ✅ | `app.js` `parseCache()` |
| `OfflineError` 시 stale 복구 | ✅ | `app.js` `handleOfflineFallback()` |
| 캐시 손상/만료 시 `result=null` 정리 | ✅ | `app.js` 무효 캐시 정리 경로 |
| `source=cache` / `source=offline` 배너 표시 | ✅ | `test_offline_banner_contract_accepts_cache_and_offline_sources` |
| `renderOfflineBanner(el, status)` 시그니처 유지 | ✅ | module_2 셸 계약 보존 |
| stale 메시지 + 저장 시각 + 기준 회차 메타 렌더 | ✅ | `OfflineBanner.js` 렌더 확장 |

## 3. 공개 API 요약

```javascript
// app.js — 캐시 핵심 API (non-exported, 내부 사용)
const CACHE_KEY = "lotto:last-success-recommendation";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const CACHE_VERSION = 1;

function saveLastSuccess(params, result) { /* localStorage.setItem */ }
function readCachedSuccess() { /* localStorage.getItem + validation */ }
function handleOfflineFallback(error, store) { /* OfflineError → stale hydrate */ }

// components/OfflineBanner.js — 공개 API (module_2 계약)
export function renderOfflineBanner(el, status) {
  // status.source in {"cache", "offline"} 둘 다 stale로 표시
  // savedAt, referenceDrawNo 메타를 사람이 읽을 수 있는 형태로 렌더
}
```

## 4. 실행·동작 흐름

1. 사용자가 **추천받기** 탭 → `fetchRecommendation(params)` 호출
2. 성공 시:
   - `state.result = response`
   - `saveLastSuccess(params, result)` → `localStorage` 갱신
   - `data-status="success"` 유지
3. 네트워크 실패 (`OfflineError` 발생) 시:
   - `readCachedSuccess()` 시도
   - 유효한 캐시 존재: `state.status = "offline"`, `state.result = cached.result` (stale)
     - `OfflineBanner`가 "저장 시각 X, 기준 회차 Y" stale 안내 표시
   - 캐시 없음/손상/만료: `state.result = null`, 오프라인 오류 안내만
4. 사용자가 다시 시도 → 온라인 복구 시 캐시 재갱신 + stale 배너 해제

## 5. 알려진 제한 / 미해결 이슈

| # | 항목 | 심각도 | 비고 |
|---|---|---|---|
| 1 | iPhone Safari / Chrome Android 실기기 수동 스모크 미수행 | LOW | 정적 셸 계약으로 커버되나 터치 타깃·스크롤 동작은 실기기 확인 필요 |
| 2 | 구형 Safari `AbortController` 미존재 환경 fallback 미구현 | LOW | `api.js` 타임아웃 로직이 `AbortController` 의존. iOS 11 이하는 영향 가능 |
| 3 | `localStorage` 기능 비활성 환경 (프라이빗 모드 일부) | LOW | 저장 실패 시 silent skip → 오프라인 캐시만 동작 안 함, 온라인 플로우는 정상 |
| 4 | 캐시 크기 상한 없음 | LOW | 단일 레코드 1건만 저장하므로 현실적 한도 초과 불가 |
| 5 | TTL 경계 근처 race condition | VERY LOW | 24시간 경계에서 저장 중 TTL 확인 순서에 따른 일시 stale — 실제 영향 없음 |

## 6. 프론트엔드·QA 후속 작업자 체크리스트

- [ ] Chrome DevTools "Network > Offline" 토글 수동 테스트 (브라우저 1회)
- [ ] iPhone SE / Pixel 5 실기기 수동 렌더 확인
- [ ] `localStorage` 비활성 프라이빗 모드에서 플로우 확인
- [ ] TTL 24시간 경계 테스트 (시스템 시계 변경 또는 mock)

## 7. 관련 파일

- `web/js/app.js:1` — 캐시 저장/복구 로직
- `web/js/components/OfflineBanner.js:1` — stale 배너 렌더
- `web/styles/layout.css:1` — 배너 스타일
- `tests/frontend/test_offline_cache_contract.py:1` — 2종 계약 테스트
- `docs/architecture.md` — 2026-04-18T20:15:00 갱신 반영
- `docs/change_history.md` — 구현 이력 기록
