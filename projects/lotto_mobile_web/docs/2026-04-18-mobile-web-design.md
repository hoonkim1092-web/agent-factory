# 모바일 웹 로또 예측기 — 통합 설계 문서

- 작성일: 2026-04-18
- 상태: 완료 (scope/build/verify 3단계 통합)
- 관련 프로젝트: `projects/lotto_mobile_web`
- 재사용 기반: `projects/lotto_predictor_v2/src/lotto`

## 0. 설계 원칙

1. **신규 분석 로직 금지** — `lotto_predictor_v2`의 `analytics.patterns`, `recommender`, `cache.store`를 **import로만 재사용**한다.
2. **모바일 퍼스트** — 360 CSS px 기준, 터치 타깃 ≥ 44×44 px, viewport meta tag 필수.
3. **프레임워크 미도입** — ES2020 Vanilla JS + CSS, 번들러 없이 정적 파일 서빙.
4. **상태 비저장 API** — 백엔드는 FastAPI 단일 프로세스, 세션·DB 없음.
5. **오프라인 복원 가능** — `localStorage` TTL 24시간 캐시, stale 배너로 신선도 명시.

## 1. 아키텍처 개요

```
┌──────────────────────────────────────────────────────────────┐
│ 모바일 브라우저 (iOS Safari / Android Chrome, 360px+)          │
│                                                                │
│  ┌────────┐  ┌────────┐  ┌────────┐   ┌─────────────┐        │
│  │ Card   │  │ Slider │  │ Offline│←──│  app.js     │        │
│  │ List   │  │ Panel  │  │ Banner │   │ (Controller)│        │
│  └────────┘  └────────┘  └────────┘   └──────┬──────┘        │
│                                                │               │
│                                   ┌────────────▼────────┐      │
│                                   │  state.store (Pub)  │      │
│                                   └────────────┬────────┘      │
│                                                │               │
│                                   ┌────────────▼────────┐      │
│                                   │  api.js (fetch)     │      │
│                                   └────────────┬────────┘      │
└───────────────────────────────────────────────┼────────────────┘
                                                │ HTTPS
┌───────────────────────────────────────────────▼──────────────┐
│ FastAPI 백엔드 (server/app.py)                                │
│                                                                │
│  GET /api/health     — 헬스 체크                               │
│  GET /api/recommend  — n, draws, offline 파라미터              │
│  GET /api/draws/latest — 최신 회차 확인                        │
│                                                                │
│              │         │           │                            │
│              ▼         ▼           ▼                            │
│       [services/recommendation.py]                              │
│              │                                                  │
│              ▼                                                  │
│    import projects/lotto_predictor_v2/src/lotto:               │
│     - analytics.patterns.analyze_patterns                      │
│     - recommender.recommend_combinations                       │
│     - cache.store.LottoCacheStore                              │
└────────────────────────────────────────────────────────────────┘
```

## 2. 모듈 분해

### 2.1 Backend (`backend_dev_module_1`)
- **위치**: `server/`
- **파일**: `app.py`, `bootstrap.py`, `dependencies.py`, `errors.py`, `schemas.py`, `services/recommendation.py`, `services/draw_cache.py`
- **공개 엔드포인트**:
  - `GET /api/health` → `{status: "ok"}`
  - `GET /api/recommend?n=1..10&draws=100..500&offline=true|false`
  - `GET /api/draws/latest` → 최신 회차 메타
- **응답 스키마**: `generated_at`, `latest_draw_no`, `latest_draw_date`, `source ∈ {api,cache,offline}`, `status ∈ {success,degraded-success}`, `draws_used`, `combos[]`
- **재사용**: `bootstrap.py`가 `sys.path`에 `projects/lotto_predictor_v2/src`를 주입해 `lotto.*` 모듈을 그대로 import.
- **오류 스키마**: `{error: {code, message, details}}` — `invalid_parameter`(422), `data_unavailable`(503), `internal_error`(500)

### 2.2 Frontend 셸 (`frontend_dev_module_2`)
- **위치**: `web/`
- **파일**: `index.html`, `styles/{base,layout}.css`, `js/{app,state,api}.js`
- **공개 API**:
  ```javascript
  // js/state.js
  export function createStore(initialState) { /* getState, setState, subscribe */ }
  // js/api.js
  export async function fetchRecommendation(params, { signal }) { /* throws OfflineError */ }
  // js/app.js
  export function mountApp(root) { /* bootstrap + bind components */ }
  ```
- **DOM 컨벤션**: `data-status="idle|loading|success|error|offline"`, `data-slot="card-list|param-panel|offline-banner"`, `data-testid=...`

### 2.3 Card List (`frontend_dev_module_3`)
- **파일**: `web/js/components/CardList.js` + `web/styles/cards.css`
- **공개 API**: `export function renderCardList(el, state)` — 셸의 자리표시자 치환
- **시각화**: 6개 번호 공(색상 = 구간), 점수 게이지, 홀짝 비율, 구간 분포 히스토그램, 접기·펼치기

### 2.4 Param Panel (`frontend_dev_module_4`)
- **파일**: `web/js/components/ParamPanel.js` + `web/styles/sliders.css`
- **공개 API**: `export function renderParamPanel(el, store)` — 셸 계약 유지
- **슬라이더**:
  - `n` (조합 개수): 1~10, step 1
  - `draws` (분석 회차): 100~500, step 50
- **정책**: 1회 마운트 후 속성만 갱신 (드래그 끊김 방지), `params.offline` 키는 건드리지 않음, `status="loading"` 중 비활성화.

### 2.5 Offline Banner + Cache (`frontend_dev_module_5`)
- **파일**: `web/js/components/OfflineBanner.js` + `web/js/app.js` 캐시 로직
- **저장 키**: `lotto:last-success-recommendation` (localStorage)
- **TTL**: 24시간, 버전 필드 `version=1`, shape 검증 (`params/result` 최소 필드)
- **정책**:
  - 성공 응답마다 캐시 갱신
  - `OfflineError` 발생 시 유효 캐시 있으면 `status='offline'` + stale 표시
  - 손상/만료 시 `result=null` 정리
  - 배너는 `source=cache`와 `source=offline` 둘 다 stale로 렌더

### 2.6 QA API (`qa_engineer_module_6`)
- **위치**: `tests/api/`
- **테스트**: `TestClient` + stubbed predictor로 엔드포인트 계약 + 입력 검증 + 오류 응답 검증
- **결과**: 10/10 PASS

### 2.7 QA Frontend Smoke (`qa_engineer_module_7`)
- **위치**: `tests/frontend/`
- **테스트**: 정적 HTML 파싱 + 파일 존재성 + JS export 계약 + stub 기반 렌더 상태 계약
- **결과**: 7/7 PASS (4 smoke + 2 offline + 1 param)

## 3. 데이터 흐름

### 3.1 정상 성공 플로우
1. 사용자가 슬라이더로 `n=5, draws=500` 선택 → `ParamPanel`이 `store.setState({params})`
2. **추천받기** 탭 → `app.js`가 `api.fetchRecommendation(params)` 호출
3. FastAPI: `invalid_parameter` 검증 → `services/recommendation.py` → `LottoCacheStore.load_draws()` → `analyze_patterns` → `recommend_combinations` → JSON 응답
4. `store.setState({status:'success', result})` → `CardList` 렌더링 + 캐시 저장

### 3.2 오프라인 폴백 플로우
1. `api.fetchRecommendation` → 네트워크 실패 → `OfflineError` throw
2. `app.js` 캐시 복구 시도
3. **유효 캐시**: `status='offline', result=cached, banner=stale(savedAt, drwNo)`
4. **무효 캐시**: `result=null, banner=오프라인 오류 안내`

### 3.3 백엔드 캐시 폴백 (`offline=true` 또는 API 실패)
- `services/recommendation.py`가 `LottoCacheStore` 전용 경로로 전환
- 응답: `source='cache', status='degraded-success'`

## 4. 제약 사항

| 영역 | 제약 |
|---|---|
| 브라우저 | iOS 12+ Safari / Chrome Android 최신 2버전 / Desktop Chrome/Firefox/Safari 최신 |
| 화면 | 360–430 CSS px 우선, 태블릿/데스크톱도 정상 |
| 네트워크 | 오프라인 TTL 24시간, 단일 캐시 레코드 |
| 파라미터 | `n=1..10`, `draws=100..500`, `offline=boolean` |
| 백엔드 | 상태 비저장, 외부 DB 없음, `lotto_predictor_v2` 분석 모듈 import로만 재사용 |
| 프론트 | 프레임워크 미도입, 번들러 없이 정적 서빙 |

## 5. 테스트 전략

### 5.1 자동 테스트 (17/17 PASS)
- **API** (`tests/api/`): 10건 — 엔드포인트 계약, 입력 검증, 오류 응답
- **Frontend Smoke** (`tests/frontend/`): 7건 — 셸 계약, 캐시 계약, 슬라이더 계약

### 5.2 수동 검증 권장
- iPhone SE / Pixel 5 실기기 렌더
- Chrome DevTools "Network > Offline" 토글
- `localStorage` 프라이빗 모드 동작
- 가로 스크롤 부재 확인 (360px 기준)

## 6. 배포·실행

### 개발 모드
```bash
cd projects/lotto_mobile_web
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
# 스마트폰에서 http://<PC_IP>:8000 접속
```

### 프로덕션
- FastAPI + Uvicorn (또는 Gunicorn + Uvicorn workers)
- Nginx 리버스 프록시로 `web/` 정적 파일 서빙
- HTTPS 필수 (카카오톡 인앱 브라우저 호환)

## 7. 교차검증·리스크

| 카테고리 | 리스크 | 완화 |
|---|---|---|
| 프론트-백 계약 드리프트 | `section_distribution` 타입 (dict vs array) | 테스트 계약 고정 + QA 교차검증으로 잡음 |
| 오프라인 TTL 경계 | 24시간 근처 stale 표시 일관성 | `Date.now()` 비교로 단일 기준 |
| iOS Safari `AbortController` 미존재 | 구형 iOS fallback 없음 | 후속 과제 (LOW) |
| 한글 폰트 렌더 | 시스템 폰트 의존 | `-apple-system, "Noto Sans KR"` fallback |

## 8. 후속 과제

1. **iPhone SE 실기기 스모크 테스트** 1회
2. **Playwright e2e 추가** — 실제 브라우저에서 전체 플로우 검증
3. **WebSocket 실시간 결과 업데이트** (선택적)
4. **PWA 매니페스트** 추가 — 홈 화면 아이콘 설치 지원
5. **서버 캐시 워밍업 스크립트** — 최초 실행 시 500회차 선수집

## 9. 문서·산출물 체크리스트

- [x] `docs/architecture.md` — 살아 있는 아키텍처 기준 문서
- [x] `docs/change_history.md` — 변경 이력
- [x] `docs/modules/*_scope.md` — 모듈별 범위 문서 (6개)
- [x] `docs/modules/*_handoff.md` — Backend module_1, Frontend module_5
- [x] `docs/work-items/*/` — 작업 아이템별 scope/design/tasks
- [x] `docs/2026-04-18-mobile-web-design.md` — **본 문서 (통합 설계)**
