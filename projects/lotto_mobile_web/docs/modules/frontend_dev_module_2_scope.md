# 모바일 반응형 추천 웹 UI — 범위와 인터페이스 정의

## 메타데이터
- task_id: `frontend_dev_module_2_scope_1`
- module_id: `frontend_dev_module_2`
- owner_role: frontend_dev
- phase: scope
- last_updated: 2026-04-18
- status: draft
- 문서 언어: 한국어 (OS: `ko-KR`)

## 목적
모바일 웹 브라우저(주 타깃: iOS Safari 15+, Android Chrome 110+)에서 동작하는 로또 6/45 번호 추천 서비스의 프론트엔드 셸(shell) 레이어를 정의한다.
본 문서는 `frontend_dev_module_2` 단 하나의 모듈 — "모바일 반응형 추천 웹 UI" — 만을 대상으로 하며, 하위 모듈(`frontend_dev_module_3` 조합 카드, `frontend_dev_module_4` 슬라이더, `frontend_dev_module_5` 오프라인 폴백)은 본 모듈이 정의한 인터페이스를 통해 합쳐진다.

## 범위 (In Scope)
1. 모바일-퍼스트 레이아웃 셸
   - `web/index.html` 하나의 SPA 엔트리 페이지 제공 (viewport, 메타 태그, preconnect)
   - 상단 헤더(제목/세션 상태), 본문(파라미터 영역 + 추천 결과 영역), 하단 CTA(추천받기 버튼) 영역의 3단 수직 레이아웃
   - 360–430 CSS px 폭 범위에서 가로 스크롤 없이 배치, 768 px 이상에서는 2열 fallback
2. 전역 스타일
   - `web/styles/base.css`: reset, typography, spacing scale, 컬러 토큰(CSS variables)
   - 터치 대상 최소 44×44 CSS px (WCAG 2.1 / Apple HIG 준수)
   - `prefers-color-scheme`에 따른 다크 모드 대응 (1단계 구현은 light 고정, 다크는 CSS 토큰 훅만 마련)
3. 애플리케이션 부트스트랩 및 상태 관리
   - `web/js/app.js`: 앱 진입점, 초기 상태 조립, 루트 컴포넌트 마운트
   - `web/js/state.js`: plain 객체 기반 단일 스토어(subscribe/publish 패턴, Redux 미도입)
   - 상태 스키마: `{ params: RecommendationRequest, result: RecommendationResponse | null, status: 'idle'|'loading'|'success'|'error'|'offline', lastError: string | null }`
4. API 연동 레이어
   - `web/js/api.js`: `fetchRecommendation(params)` 하나의 공용 함수 노출
   - 네트워크 오류 시 `OfflineError`를 throw, 폴백 결정은 상위(`state.js`)가 책임
   - 백엔드 계약은 `backend_dev_module_1`이 정의하는 `GET /api/recommend` 를 그대로 소비
5. 모듈 경계와 확장 슬롯
   - 카드 렌더링 슬롯: `web/js/components/CardList.js` 자리표시자(placeholder) 노출
   - 파라미터 슬라이더 슬롯: `web/js/components/ParamPanel.js` 자리표시자 노출
   - 오프라인 배너 슬롯: `web/js/components/OfflineBanner.js` 자리표시자 노출
   - 자리표시자는 본 모듈에서 빈 구현을 두고, 세부 구현은 각 하위 모듈(`module_3/4/5`)에서 치환한다.

## 범위 밖 (Out of Scope)
- 백엔드 `GET /api/recommend` 엔드포인트 구현 (→ `backend_dev_module_1`)
- 각 조합 카드의 점수·홀짝 비율·구간 분포 시각화 세부 디자인 (→ `frontend_dev_module_3`)
- `n`, `draws` 슬라이더의 구체적인 인터랙션 로직과 접근성 처리 (→ `frontend_dev_module_4`)
- `localStorage` 캐시 키 설계, TTL, stale-while-revalidate 정책 (→ `frontend_dev_module_5`)
- PWA 매니페스트, 서비스 워커, 설치 프롬프트
- 로그인, 결제, 추첨 실시간 중계 (feature-spec §Out Of Scope 참조)

## 인터페이스 정의

### 1) 파일 및 디렉터리 레이아웃
```
web/
├── index.html                     # SPA 엔트리
├── styles/
│   ├── base.css                   # reset + 토큰
│   └── layout.css                 # 3단 수직 레이아웃
└── js/
    ├── app.js                     # 부트스트랩
    ├── state.js                   # 단일 스토어
    ├── api.js                     # fetchRecommendation
    └── components/
        ├── CardList.js            # (placeholder, module_3 치환)
        ├── ParamPanel.js          # (placeholder, module_4 치환)
        └── OfflineBanner.js       # (placeholder, module_5 치환)
```

### 2) 백엔드 계약 (소비자 측 요약)
- `GET /api/recommend?n={1-10}&draws={100-500}&offline={true|false}`
- 응답 스키마 (feature-spec.md §Inputs and Outputs 기준):
  ```json
  {
    "generated_at": "2026-04-18T01:30:00Z",
    "source": "live | offline",
    "draws_used": 500,
    "combos": [
      {
        "numbers": [3, 11, 17, 22, 34, 41],
        "score": 0.87,
        "odd_even_ratio": "3:3",
        "section_distribution": [1, 2, 1, 2, 0]
      }
    ]
  }
  ```
- 에러: 4xx → 파라미터 오류 배너 노출, 5xx/네트워크 실패 → `OfflineError` 승격

### 3) 컴포넌트 공개 API (JS 모듈 단위)
| 모듈 | export | 시그니처 | 비고 |
|------|--------|----------|------|
| `state.js` | `createStore(initial)` | `(init) => { getState, setState, subscribe }` | module_3/4/5 공통 소비 |
| `state.js` | `initialState` | object | 상태 스키마의 기본값 |
| `api.js` | `fetchRecommendation` | `(params) => Promise<RecommendationResponse>` | 네트워크 실패 시 `OfflineError` throw |
| `api.js` | `OfflineError` | class | module_5가 이 타입을 감지해 폴백 |
| `components/CardList.js` | `renderCardList(el, combos)` | `(HTMLElement, RecommendationCombo[]) => void` | 본 모듈은 빈 구현, module_3가 치환 |
| `components/ParamPanel.js` | `renderParamPanel(el, store)` | `(HTMLElement, Store) => void` | 본 모듈은 정적 레이블만, module_4가 슬라이더 추가 |
| `components/OfflineBanner.js` | `renderOfflineBanner(el, status)` | `(HTMLElement, Status) => void` | 본 모듈은 hidden 스텁, module_5가 로직 추가 |

### 4) 상태 전이
```
idle ──(submit)──> loading ──(ok)──> success
                        │
                        ├──(4xx)──> error
                        └──(net err)──> offline   # module_5가 캐시 주입
```

## 의존성
- 상류(upstream, 이 모듈이 소비): `backend_dev_module_1` 의 `GET /api/recommend` 계약. 구현 완료 전에도 본 모듈은 계약 기반으로 독립 진행 가능 (mock 응답으로 검증).
- 하류(downstream, 이 모듈이 제공): `frontend_dev_module_3`(카드), `frontend_dev_module_4`(슬라이더), `frontend_dev_module_5`(오프라인)에 공개 API와 DOM 슬롯 제공.
- 횡단(cross-cutting): `qa_engineer_module_7`(프론트엔드 smoke 테스트)은 본 모듈이 노출한 `web/index.html`과 컴포넌트 export를 대상으로 검증.

## 산출물 (Deliverables)
- `web/index.html` — 모바일 반응형 셸 페이지
- `web/styles/base.css`, `web/styles/layout.css` — 기본 스타일/레이아웃
- `web/js/app.js`, `web/js/state.js`, `web/js/api.js` — 핵심 스크립트 3종
- `web/js/components/CardList.js`, `ParamPanel.js`, `OfflineBanner.js` — 자리표시자 컴포넌트
- `docs/modules/frontend_dev_module_2_scope.md` — 본 범위 문서
- `docs/architecture.md`, `docs/change_history.md` — 문서 계약 갱신

## 구현 순서 (고정)
1. 파일/디렉터리 골격 생성 (`web/` 하위 트리와 빈 파일들)
2. `web/index.html` 셸 마크업 + viewport/메타 태그
3. `web/styles/base.css` 토큰 + reset
4. `web/styles/layout.css` 3단 레이아웃 + 브레이크포인트
5. `web/js/state.js` createStore + initialState
6. `web/js/api.js` fetchRecommendation + OfflineError
7. `web/js/components/*.js` 빈 export 스텁 3종
8. `web/js/app.js` 부트스트랩(마운트 + 이벤트 와이어링)
9. 수동 렌더 확인: 로컬 `python -m http.server`로 iPhone SE/Pixel 뷰포트에서 레이아웃 깨짐 없는지 점검
10. `build` 단계로 handoff — `frontend_dev_module_2_build_2`에서 이 순서대로 구현

## 수용 기준 (이 문서 단위)
- 모듈의 범위/비범위/인터페이스/의존성/산출물/구현 순서가 모두 문서화되어 있다.
- `frontend_dev_module_3/4/5`가 본 문서가 정의한 공개 API에 의존해서 구현을 시작할 수 있다.
- `backend_dev_module_1`의 `GET /api/recommend` 응답 스키마와 본 문서의 계약이 일치한다.

## 리스크와 완화
- (R1) 백엔드 계약 변동 → `api.js`와 `state.js` 상태 스키마의 단일 수정 지점으로 blast radius 제한.
- (R2) 자리표시자 컴포넌트 서명이 하위 모듈 구현과 어긋남 → 본 문서의 "컴포넌트 공개 API" 표를 단일 소스로 고정하고, 하위 모듈 scope 문서에서 역참조.
- (R3) 360 px 이하 구형 단말 레이아웃 깨짐 → `layout.css`에서 `clamp()` 기반 타이포/간격 사용.

## 참고
- `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/feature-spec.md` (I/O 스키마)
- `docs/work-items/.../implementation-design.md` (기술 스택, 리스크)
- `docs/work-items/.../implementation-tasks.md` (task 체계, depends_on)
