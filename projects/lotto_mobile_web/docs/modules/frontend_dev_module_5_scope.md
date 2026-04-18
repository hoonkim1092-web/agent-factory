# 오프라인 캐시 폴백 모듈 — 범위와 인터페이스 정의

## 메타데이터
- task_id: `frontend_dev_module_5_scope_1`
- module_id: `frontend_dev_module_5`
- owner_role: frontend_dev
- phase: scope
- last_updated: 2026-04-18
- status: draft
- 문서 언어: 한국어 (OS: `ko-KR`)

## 목적
모바일 웹 로또 추천 서비스에서 네트워크 실패 또는 서버 데이터 불가용 상황이 발생해도 사용자가 마지막 성공 추천 결과를 다시 확인할 수 있도록 **오프라인 캐시 폴백 모듈**의 범위와 공개 인터페이스를 고정한다.
본 문서는 `frontend_dev_module_2`가 자리표시자로 노출한 `renderOfflineBanner(el, status)` 를 실제 오프라인 안내 배너로 치환하고, `web/js/app.js` 와 `localStorage` 간 캐시 폴백 경계를 정의하는 단일 모듈(`frontend_dev_module_5`)만 대상으로 하며, 카드 시각화(`module_3`)와 파라미터 슬라이더(`module_4`) 구현은 포함하지 않는다.

## 범위 (In Scope)
1. 마지막 성공 응답 캐시 저장
   - `GET /api/recommend` 성공 응답을 `localStorage` 에 단일 레코드로 저장
   - 저장 대상은 사용자 재표시에 필요한 최소 필드(`generated_at`, `source`, `status`, `draws_used`, `latest_draw_no`, `latest_draw_date`, `combos`, `params`, `cached_at`)로 제한
   - 저장 시점은 온라인 요청 성공 직후 1회로 고정
2. 네트워크 실패 시 캐시 폴백
   - `api.fetchRecommendation()` 이 `OfflineError` 를 throw 하면 `app.js` 가 캐시를 읽어 결과가 유효하면 `state.result` 에 주입
   - 캐시가 유효하면 `state.status = 'offline'`, `lastError` 는 사용자 안내용 문구로 갱신
   - 캐시가 없거나 손상되었거나 TTL이 만료되면 폴백하지 않고 기존 오류 상태로 남긴다
3. stale 데이터 표기
   - 배너는 `status === 'offline'` 또는 응답 `result.source ∈ {'cache','offline'}` 인 경우 stale 데이터임을 명시
   - 배너 문구는 "현재 네트워크가 불안정해 마지막 저장 결과를 보여주는 중"으로 통일하고, 부가 메타로 `cached_at`, `latest_draw_no`, `latest_draw_date` 를 노출한다
4. 캐시 무결성 방어
   - `localStorage` 접근 실패(사파리 private mode, quota, JSON parse error)는 조용히 무시하고 앱 주 흐름을 깨지 않는다
   - `combos` 배열, `params.n`, `params.draws` 등 최소 형상이 어긋난 캐시는 무효로 본다
5. 공개 API 유지 + 내부 DOM 치환
   - `web/js/components/OfflineBanner.js` 의 공개 export `renderOfflineBanner(el, status)` 시그니처는 유지
   - 배너의 상세 메시지/타임스탬프/회차 메타는 `el.dataset.*` 또는 모듈 내부 조회 가능한 DOM 계약으로 주입
6. 구현 순서와 의존성 고정
   - 캐시 키, TTL, 저장 payload, 상태 전이, 영향 파일, 테스트 포인트를 문서로 먼저 확정해 build 단계 재해석을 막는다

## 범위 밖 (Out of Scope)
- 서비스 워커, Cache Storage API, PWA 설치 프롬프트
- 여러 버전 캐시 보관, 사용자별 히스토리 브라우징, 비교 보기
- 추천 결과가 아닌 정적 자산/HTML/CSS/JS 캐싱
- `params.offline` 토글 UI 자체의 신규 추가 여부 결정
- 백엔드 `source/status` 계약 수정
- 카드/슬라이더 컴포넌트 내부 구현 변경

## 인터페이스 정의

### 1) 공개 API (유지)
| 파일 | export | 시그니처 | 변경점 |
|------|--------|----------|--------|
| `web/js/components/OfflineBanner.js` | `renderOfflineBanner` | `(el: HTMLElement, status: Status) => void` | 시그니처 동일, 내부 구현만 실제 배너로 치환 |

- `Status` 는 `web/js/state.js` 의 상태 값(`idle | loading | success | error | offline`)을 그대로 사용한다.
- 반환값은 `void` 이며, side-effect 로 `el` 내부를 갱신한다.
- 캐시 읽기/쓰기 함수는 새 공개 export 로 노출하지 않고 `app.js` 내부 헬퍼 또는 `api.js` 보조 함수로만 유지한다.

### 2) 캐시 레코드 계약
```json
{
  "version": 1,
  "cached_at": "2026-04-18T19:40:00Z",
  "params": {
    "n": 5,
    "draws": 500,
    "offline": false
  },
  "result": {
    "generated_at": "2026-04-18T19:39:58Z",
    "source": "api",
    "status": "success",
    "draws_used": 500,
    "latest_draw_no": 1162,
    "latest_draw_date": "2026-04-18",
    "combos": [
      {
        "numbers": [3, 11, 17, 22, 34, 41],
        "score": 0.87,
        "odd_even_ratio": "3:3",
        "section_distribution": [1, 2, 1, 2, 0]
      }
    ]
  }
}
```
- `localStorage` 키: `lotto:last-success-recommendation`
- TTL: `cached_at` 기준 24시간
- 폴백 허용 조건
  - JSON parse 성공
  - `version === 1`
  - `cached_at` 이 ISO 문자열이며 현재 시각 대비 24시간 이내
  - `result.combos` 가 길이 1 이상 배열
  - `params.n`, `params.draws` 가 숫자

### 3) 상태 전이 계약
```text
loading --(api success)--> success + cache write
loading --(OfflineError + valid cache)--> offline + cached result hydrate
loading --(OfflineError + no/invalid/expired cache)--> offline
loading --(ApiError 4xx)--> error
```
- `offline` 상태에서 `result` 가 존재하면 카드 리스트는 그대로 렌더하고, 배너가 stale 표시를 담당한다.
- `offline` 상태에서 `result` 가 없으면 배너는 "저장된 추천 결과가 없어 오프라인으로는 보여줄 수 없음" 문구만 노출한다.

### 4) DOM 구조
```html
<section class="offline-banner" data-visible="false" hidden>
  <p class="offline-banner__message">현재 네트워크가 불안정해 마지막 저장 결과를 보여주는 중입니다.</p>
  <dl class="offline-banner__meta">
    <div>
      <dt>저장 시각</dt>
      <dd>2026-04-18 19:40</dd>
    </div>
    <div>
      <dt>기준 회차</dt>
      <dd>1162회 / 2026-04-18</dd>
    </div>
  </dl>
</section>
```
- `hidden` 과 `data-visible` 로 표시 여부를 동기화한다.
- `status !== 'offline'` 이고 `result.source ∉ {'cache','offline'}` 면 숨김 처리한다.
- 배너 렌더러는 `HTMLElement` 가 아니면 no-op 로 반환한다.

### 5) 기존 모듈과의 결합
| 결합 지점 | 기존 | 본 모듈 변경 |
|-----------|------|--------------|
| `web/js/app.js` | `OfflineError` 발생 시 `status='offline'` 전이만 수행 | 캐시 읽기/쓰기와 배너 메타 주입을 추가 |
| `web/js/api.js` | `fetchRecommendation`, `OfflineError`, `ApiError` | 네트워크 오류 승격 계약 유지, 필요 시 캐시 헬퍼 보조 함수 추가 가능 |
| `web/js/state.js` | `params`, `result`, `status`, `lastError` | 상태 스키마 변경 없음 |
| `web/js/components/OfflineBanner.js` | hidden 스텁 | 실제 배너 렌더링으로 치환 |
| `web/js/components/CardList.js` | 결과 렌더링 | 변경 없음, `result` 재사용 |
| `tests/frontend/` | 정적 셸 smoke 중심 | build/verify 에서 오프라인 폴백 계약 테스트 추가 |

## 의존성
- 상류(upstream, 이 모듈이 소비)
  - `frontend_dev_module_2` 산출물: `app.js`, `state.js`, `api.js`, `OfflineBanner.js` 자리표시자
  - `backend_dev_module_1` handoff: `source=cache|offline` 둘 다 stale 로 수용해야 한다는 권고
  - 브라우저 저장소: `window.localStorage`
- 하류(downstream)
  - `qa_engineer_module_7` 및 후속 프론트 테스트가 오프라인 배너/캐시 계약을 검증
  - 사용자 UX는 `CardList` 가 캐시된 `result.combos` 를 그대로 재사용한다는 전제에 의존
- 횡단(cross-cutting)
  - `docs/architecture.md` 데이터 흐름의 `OfflineError → OfflineBanner + 캐시 폴백` 설명을 본 문서 기준으로 갱신

## 산출물 (Deliverables)
- `docs/modules/frontend_dev_module_5_scope.md` — 본 범위 문서
- `docs/plans/2026-04-18-offline-cache-fallback.md` — build 전 설계 의도/영향 범위/대안 문서
- `docs/architecture.md`, `docs/change_history.md` — 설계 변경 반영
- build 단계 예정 산출물
  - `web/js/components/OfflineBanner.js`
  - `web/js/app.js`
  - 필요 시 `web/js/api.js`
  - `tests/frontend/` 관련 계약 테스트

## 구현 순서 (고정)
1. 캐시 키와 payload shape 를 상수로 고정한다(`lotto:last-success-recommendation`, `version=1`, `cached_at`, `params`, `result`).
2. `web/js/app.js` 에 저장 헬퍼와 복구 헬퍼를 추가한다.
   - 성공 응답 시 캐시 저장
   - `OfflineError` 시 캐시 읽기
   - TTL/형상 검증 실패 시 무시
3. `offline` 상태 전이를 명시적으로 분기한다.
   - 유효 캐시가 있으면 `result` hydrate + 배너 메타 주입
   - 유효 캐시가 없으면 `result` 유지/초기화 정책을 명시하고 배너는 오류 안내만 노출
4. `web/js/components/OfflineBanner.js` 를 실제 렌더러로 치환한다.
   - `status`, `dataset.cachedAt`, `dataset.latestDrawNo`, `dataset.latestDrawDate`, `dataset.source` 를 읽어 표시
   - `source=cache|offline` 둘 다 stale 배너를 보이게 처리
5. 회귀 테스트를 추가한다.
   - 성공 응답 저장
   - `OfflineError` + 유효 캐시 복구
   - 만료 캐시/손상 캐시 무시
   - `source=cache|offline` 배너 표시
6. `docs/architecture.md` 와 `docs/change_history.md` 를 build 결과 기준으로 갱신한다.
7. verify 단계에서 브라우저 수동 점검과 저장소 초기화/재시도 시나리오를 확인한다.

## 수용 기준 (이 문서 단위)
- 오프라인 캐시 폴백 모듈의 범위/비범위/인터페이스/의존성/산출물/구현 순서가 문서화돼 있다.
- `renderOfflineBanner(el, status)` 공개 API 유지가 명시된다.
- 캐시 키, payload shape, TTL, stale 표시 조건이 고정돼 build 담당자가 재해석 없이 구현할 수 있다.
- `source=cache|offline` 드리프트를 흡수하는 방어적 UI 계약이 문서화돼 있다.
- 영향 파일과 비침범 파일이 구분돼 있다.

## 리스크와 완화
- (R1) 백엔드 `source/status` 계약 드리프트가 지속됨 → `cache|offline` 둘 다 stale 로 수용하는 방어적 UI 계약을 먼저 고정한다.
- (R2) 손상된 `localStorage` 데이터가 앱을 깨뜨릴 수 있음 → parse/shape 검증 실패 시 조용히 무시한다.
- (R3) 24시간 이상 지난 추천 결과가 오래된 정보로 오인될 수 있음 → TTL 24시간을 넘기면 폴백하지 않고 안내 문구만 노출한다.
- (R4) `localStorage` 가 불가한 환경에서 예외가 터질 수 있음 → `try/catch` 로 감싸고 저장 실패를 비치명(non-fatal)으로 처리한다.
- (R5) `offline` 상태에서 카드와 배너가 서로 다른 메타를 가리킬 수 있음 → 배너 메타는 캐시 hydrate 직후 같은 `result` 소스에서 파생한다.

## 참고
- `docs/modules/frontend_dev_module_2_scope.md` — `renderOfflineBanner(el, status)` 자리표시자 계약
- `docs/modules/backend_dev_module_1_handoff.md` — `source=cache|offline` 드리프트와 프론트 방어 요구
- `docs/architecture.md` — 프론트 데이터 흐름과 상태 전이
- `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/feature-spec.md` — 오프라인 사용자 시나리오
