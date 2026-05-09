# 파라미터 슬라이더 컨트롤 — 범위와 인터페이스 정의

## 메타데이터
- task_id: `frontend_dev_module_4_scope_1`
- module_id: `frontend_dev_module_4`
- owner_role: frontend_dev
- phase: scope
- last_updated: 2026-04-18
- status: draft
- 문서 언어: 한국어 (OS: `ko-KR`)

## 목적
모바일 웹 로또 추천 서비스에서 사용자가 추천 파라미터(`n`: 추천 조합 수, `draws`: 분석 회차)를 직관적으로 조정할 수 있도록 **파라미터 슬라이더 컨트롤**의 범위와 공개 인터페이스를 고정한다.
본 문서는 `frontend_dev_module_2`가 자리표시자로 노출한 `renderParamPanel(el, store)` 를 실제 슬라이더 UI로 치환하는 단일 모듈(`frontend_dev_module_4`)만 대상으로 하며, 카드 시각화(`module_3`)나 오프라인 폴백(`module_5`) 로직은 포함하지 않는다.

## 범위 (In Scope)
1. 파라미터 패널 렌더러 치환
   - `web/js/components/ParamPanel.js` 의 `renderParamPanel(el, store)` 공개 API 를 실제 슬라이더 구현으로 교체
   - 기존 호출자(`web/js/app.js`)와의 계약(시그니처, 인자 순서, 반환 없음)을 그대로 유지
   - 본 모듈은 `store.setState({ params: { ... } })` 를 통해 `params.n`, `params.draws` 두 키만 갱신한다(`params.offline` 은 건드리지 않음).
2. `n` (추천 조합 수) 슬라이더
   - 백엔드 검증 범위와 동일하게 `min=1`, `max=10`, `step=1`, 초기값 `state.params.n`(기본 5)
   - 단위 표기: `N개` (예: `5개`)
   - 값 변경 시 `store.setState({ params: { n } })` 호출
3. `draws` (분석 회차) 슬라이더
   - 백엔드 검증 범위와 동일하게 `min=100`, `max=500`, `step=50`, 초기값 `state.params.draws`(기본 500)
   - 단위 표기: `N회` (예: `500회`)
   - 값 변경 시 `store.setState({ params: { draws } })` 호출
4. 접근성 / 모바일 인터랙션
   - 각 슬라이더는 표준 `<input type="range">` 로 구현하여 OS/브라우저 내장 접근성(스크린리더, 키보드 ←→/Home/End/PageUp/PageDown)을 그대로 활용
   - 각 슬라이더에 `<label for>` + `<output for>` 결합으로 레이블·현재값을 명시
   - 슬라이더 트랙/썸은 모바일 터치 타깃 ≥ 44×44 CSS px 보장(썸 자체가 44 미만일 경우 `touch-action: manipulation` + 패딩 영역 확장)
   - `:focus-visible` 토큰 적용으로 키보드 포커스 링 유지
   - `aria-valuetext` 로 단위 포함 값(`5개`, `500회`)을 안내(스크린리더 사용자가 단위를 인지할 수 있게)
5. 스토어 동기화
   - 사용자 → 슬라이더: `input` 이벤트(드래그 중 실시간) 와 `change` 이벤트(놓을 때) 모두 동일 핸들러로 `store.setState` 호출 — 같은 값이면 스토어가 자체적으로 no-op
   - 스토어 → 슬라이더: `store.subscribe(render)` 로 외부 갱신(예: 다른 모듈이 `params.n` 을 강제 변경)을 슬라이더/표시값에 역반영
   - 동일 값에 대한 재렌더 시 입력 포커스/드래그 상태가 끊기지 않도록 **DOM 재생성 대신 속성 갱신**으로 동기화한다(컴포넌트 1회만 마운트).
6. 빈 상태 / 이상 입력 처리
   - `el` 이 `HTMLElement` 가 아니거나 `store` 가 `getState`/`setState` 를 노출하지 않으면 no-op 로 안전 반환
   - 외부에서 들어온 값이 범위/스텝을 벗어나면 클램프 후 스토어와 슬라이더 양쪽을 정렬한다(슬라이더는 자체 클램프, 표시값은 보정값을 그대로 노출)
7. 스타일 자산
   - 신규 파일 `web/styles/sliders.css` 를 추가해 슬라이더 전용 스타일을 격리(`base.css`·`layout.css`·`cards.css` 는 건드리지 않음)
   - `web/index.html` `<head>` 에 `sliders.css` 링크 1줄 추가(레이아웃 순서: `base → layout → cards → sliders`) — `qa_engineer_module_7` smoke 계약과 호환

## 범위 밖 (Out of Scope)
- `params.offline` 토글 UI(→ `frontend_dev_module_5` 의 `OfflineBanner` 영역에서 모드 안내 통합)
- `n=1..10` / `draws=100..500` 외의 범위 확장(백엔드 계약 변경 필요 — `backend_dev_module_1` 영역)
- 슬라이더 값에 따른 자동 추천 호출(현재 흐름은 사용자가 "추천받기" 버튼을 명시적으로 누르는 모델 — `app.js` `submitRecommendation` 트리거 그대로)
- 디바운스/throttle 정책의 정밀 측정·튜닝(기본 동작은 매 변경마다 setState, 스토어 자체 shallowEqual 가드에 의존)
- 카드 시각화(`module_3`), 오프라인 캐시(`module_5`)
- Lighthouse 점수 측정, 픽셀 회귀 테스트, 외부 슬라이더 라이브러리 도입(프레임워크 미도입 원칙 유지)

## 인터페이스 정의

### 1) 공개 API (유지)
| 파일 | export | 시그니처 | 변경점 |
|------|--------|----------|--------|
| `web/js/components/ParamPanel.js` | `renderParamPanel` | `(el: HTMLElement, store: Store) => void` | 시그니처 동일, 내부 구현만 슬라이더로 치환 |

- `Store` 형은 `web/js/state.js` 의 `createStore` 반환 객체 — `getState`, `setState`, `subscribe` 3종 메서드를 사용한다.
- 반환: `void`(side-effect 로 `el` 내부 교체). 기존 호출자(`app.js`)는 수정하지 않는다.

### 2) DOM 구조 (BEM 계열 클래스)
```
<form class="param-panel" novalidate>
  <fieldset class="param-panel__group" data-param="n">
    <label class="param-panel__label" for="param-n">추천 조합 수</label>
    <div class="param-panel__row">
      <input
        class="param-panel__slider"
        type="range"
        id="param-n"
        name="n"
        min="1" max="10" step="1"
        value="5"
        aria-valuetext="5개"
      />
      <output class="param-panel__value" for="param-n">5개</output>
    </div>
  </fieldset>

  <fieldset class="param-panel__group" data-param="draws">
    <label class="param-panel__label" for="param-draws">분석 회차</label>
    <div class="param-panel__row">
      <input
        class="param-panel__slider"
        type="range"
        id="param-draws"
        name="draws"
        min="100" max="500" step="50"
        value="500"
        aria-valuetext="500회"
      />
      <output class="param-panel__value" for="param-draws">500회</output>
    </div>
  </fieldset>
</form>
```
- 클래스 이름은 smoke 테스트가 결합하지 않도록 **필수 export 존재**만 강제하고, 상세 선택자는 내부 구현으로 본다.
- `<form>` 은 제출 시맨틱 표현용이며 `novalidate` 로 브라우저 기본 검증을 끈다(스토어가 단일 진실원).

### 3) 스타일 자산
- 신규: `web/styles/sliders.css`
  - 토큰(`--color-*`, `--space-*`, `--radius-*`, `--touch-target-min`)은 `base.css` 를 재사용
  - `<input type="range">` 의 트랙/썸을 `-webkit-slider-runnable-track`, `-webkit-slider-thumb`, `-moz-range-track`, `-moz-range-thumb` 로 모바일 사파리/크롬/파이어폭스 모두에서 일관되게 스타일링
  - 썸 크기 ≥ 28 px, 터치 영역 패딩으로 시각적 영역과 별도로 44×44 hit area 확보
  - `prefers-reduced-motion: reduce` 조건에서 트랜지션 제거
  - 다크 훅은 `--ball-*` 와 동일 패턴(`--slider-track-dark`, `--slider-thumb-dark`)으로 별도 변수만 준비
- 셸 변경: `web/index.html` 의 `<head>` 에 `<link rel="stylesheet" href="./styles/sliders.css" />` 추가(순서: `base → layout → cards → sliders`)

### 4) 상호작용·상태
- 컴포넌트는 `el` 에 폼을 1회만 마운트하고, 이후 스토어 변경에 따라 슬라이더의 `value`/`aria-valuetext` 와 `<output>` 텍스트만 갱신한다(드래그 중 DOM 재생성 금지).
- 사용자 → 스토어: `input` 이벤트에서 `Number(target.value)` 를 `store.setState({ params: { n } })` 또는 `{ params: { draws } }` 로 부분 패치. `state.js` 의 `setState` 가 `params` 를 한 단계 더 얕게 병합하므로 다른 키는 보존된다.
- 스토어 → DOM: `store.subscribe(applyState)` 에서 현재 `state.params.n`/`state.params.draws` 가 슬라이더 `value` 와 다를 때만 갱신(루프 방지).
- 비활성화: `state.status === 'loading'` 이면 두 슬라이더의 `disabled` 를 `true` 로 토글한다(현재 `app.js` 가 추천 버튼을 비활성화하는 정책과 일치). 비활성 상태에서도 마지막 값은 표시 유지.

### 5) 접근성 계약
- 각 슬라이더: `<label for>` 결합 + `<output for>` 결합으로 스크린리더가 "추천 조합 수, 슬라이더, 5개" 형태로 안내
- `aria-valuetext` 로 단위 포함 값을 명시(시각 사용자에게는 `<output>`, 스크린리더에는 `aria-valuetext`)
- 키보드: 표준 `<input type="range">` 의 ←/→/↑/↓(±step), Home/End(min/max), PageUp/PageDown(±10·step) 을 그대로 사용
- 포커스 링: `base.css` `:focus-visible` 토큰 재사용
- 색상 대비: 트랙 vs 채움(progress) 대비 AA(≥3:1), 텍스트(레이블/값) ≥ 4.5:1 유지

### 6) 기존 모듈과의 결합
| 결합 지점 | 기존 | 본 모듈 변경 |
|-----------|------|--------------|
| `web/js/app.js` | `renderParamPanel(paramPanelRoot, store)` 호출 | 변경 없음 |
| `web/js/components/ParamPanel.js` | `dl/dt/dd` 정적 라벨 자리표시자 | 두 슬라이더 + `<output>` 폼으로 치환 |
| `web/js/state.js` | `params: { n: 5, draws: 500, offline: false }` | 변경 없음(부분 패치만 사용) |
| `web/index.html` | `base.css`, `layout.css`, `cards.css` 링크 | `sliders.css` 링크 1줄 추가 |
| `web/styles/sliders.css` | — | 신규 추가 |
| `web/js/api.js` | `fetchRecommendation(params)` 가 `params.n`/`params.draws` 소비 | 변경 없음(스토어 값이 그대로 흐름) |
| `tests/frontend/test_smoke_render.py` | 파일/Export/셸 계약 검사 | 통과 유지(신규 CSS 파일은 smoke 필수 항목이 아님) |

## 의존성
- 상류(upstream, 이 모듈이 소비)
  - `frontend_dev_module_2` 산출물: `web/index.html`, `web/js/app.js`, `web/js/components/ParamPanel.js` 자리표시자, `web/js/state.js` 의 `createStore`/`initialState`/부분 패치 계약
  - `backend_dev_module_1` 의 파라미터 검증 범위(`n=1..10`, `draws=100..500`) — 슬라이더 min/max/step의 단일 진실원
- 하류(downstream)
  - `qa_engineer_module_7` smoke 테스트는 본 모듈 이후에도 통과해야 한다(필수 파일/Export 계약은 그대로 유지)
  - `frontend_dev_module_5` 오프라인 폴백은 `state.params.offline` 을 자체적으로 다루며, 본 슬라이더가 `params.offline` 키를 건드리지 않는다는 약속에 의존한다.
- 횡단(cross-cutting)
  - `docs/architecture.md` 의 "프론트엔드 셸 공개 API 요약 > `renderParamPanel`" 항목이 build 단계에서 실제 슬라이더 설명으로 갱신되어야 함

## 산출물 (Deliverables)
- `docs/modules/frontend_dev_module_4_scope.md` — 본 범위 문서
- `web/js/components/ParamPanel.js` — build 단계에서 실제 슬라이더 구현으로 치환
- `web/styles/sliders.css` — build 단계에서 신규 추가
- `web/index.html` — build 단계에서 `sliders.css` 링크 1줄 추가
- `docs/architecture.md`, `docs/change_history.md` — 본 scope 작업과 build 작업에서 각각 갱신(설계 변경 반영)

## 구현 순서 (고정)
1. 본 scope 문서를 근거로 `web/styles/sliders.css` 의 토큰·클래스 골격을 생성한다(트랙·썸 크로스브라우저 스타일, 44×44 터치 영역, focus-visible, reduced-motion 가드).
2. `web/index.html` 의 `<head>` 에 `sliders.css` 링크를 추가한다(순서: `base → layout → cards → sliders`).
3. `web/js/components/ParamPanel.js` 내부를 치환한다:
   1. 입력 방어(`el`·`store` 타입) 분기
   2. 한 번만 폼/슬라이더 DOM을 빌드하는 `build(el)` 헬퍼
   3. 스토어 → DOM 동기화 헬퍼(`syncFromState(state)`): 슬라이더 `value`/`aria-valuetext`/`<output>` 텍스트/`disabled` 갱신, 동일 값일 때 no-op
   4. DOM → 스토어 핸들러(`onSliderInput(event)`): `event.target.name` 으로 분기해 `setState({ params: { [name]: number } })` 호출
   5. `store.subscribe(syncFromState)` 등록 + 초기 1회 `syncFromState(store.getState())` 호출
4. 회귀 확인: `pytest tests/frontend -q` — 필수 셸 계약/Export 통과 재확인.
5. 수동 시각·인터랙션 점검: `python -m http.server` 로 iPhone SE(375)/Pixel(412) 뷰포트에서
   - 두 슬라이더 모두 가로 스크롤 없이 패널 폭에 맞고
   - 터치 드래그·키보드 화살표·Home/End 동작이 즉시 `<output>` 과 `data-status` 흐름에 반영되는지
   - "추천받기" 클릭 직후 `loading` 상태에서 슬라이더가 비활성되는지 확인.
6. `docs/architecture.md` 의 "프론트엔드 셸 공개 API 요약 > `renderParamPanel`" 항목을 실제 슬라이더 설명으로 갱신하고, `docs/change_history.md` 에 build 항목을 추가한다(이 갱신 자체는 build 태스크에서 수행).
7. verify 단계로 handoff(`frontend_dev_module_4_verify_3`).

## 수용 기준 (이 문서 단위)
- 파라미터 슬라이더 컨트롤의 범위/비범위/인터페이스/의존성/산출물/구현 순서가 문서화돼 있다.
- 공개 API(`renderParamPanel` 시그니처)가 `frontend_dev_module_2` 계약과 일치한다.
- 슬라이더 min/max/step 이 `backend_dev_module_1` 의 검증 범위(`n=1..10`, `draws=100..500`)와 1:1 정렬돼 있다.
- 영향 파일(`ParamPanel.js`, `sliders.css`, `index.html`)과 비침범 파일(`state.js`, `api.js`, `app.js`, `base.css`, `layout.css`, `cards.css`, `CardList.js`, `OfflineBanner.js`)이 명시된다.
- build 단계 담당자가 재해석 없이 §구현 순서 1–7 을 그대로 실행할 수 있다.
- QA smoke 테스트(`qa_engineer_module_7`)가 placeholder/실제 구현 양쪽에서 통과하는 계약이 유지된다.

## 리스크와 완화
- (R1) `<input type="range">` 의 트랙/썸 스타일이 iOS Safari 와 Android Chrome 에서 어긋남 → `sliders.css` 에서 벤더 프리픽스(`-webkit-`/`-moz-`) 양쪽을 모두 정의하고, 썸 반경·hit area 를 토큰으로 단일화한다.
- (R2) `input` 이벤트 폭주로 `setState` → `subscribe` 루프가 발생할 가능성 → `state.js` 의 `shallowEqual` 가드가 동일 값을 컷오프하고, `syncFromState` 가 슬라이더 현재 `value` 와 비교 후에만 DOM 을 건드려 양방향 루프를 차단한다.
- (R3) 사용자가 드래그 중인데 외부 갱신(예: `module_5` 가 강제 값 변경)으로 DOM 재생성이 일어나면 드래그가 끊김 → 본 모듈은 1회 마운트 + 속성 갱신 정책을 명시해 회귀를 차단한다.
- (R4) 신규 CSS 링크 추가로 smoke 테스트가 깨질 가능성 → `qa_engineer_module_7_scope.md` §검증 대상은 `base.css`·`layout.css` 존재성만 강제하므로 회귀 없음을 확인.
- (R5) 슬라이더만 변경 후 새로고침 시 값이 초기화되어 사용자가 혼란 → 본 모듈 범위에서는 `localStorage` 영속화를 도입하지 않고(R5 수용) `module_5` 의 캐시 정책에서 후속 검토한다.

## 참고
- `docs/modules/frontend_dev_module_2_scope.md` — 자리표시자 계약 표 §3
- `docs/modules/frontend_dev_module_3_scope.md` — 동일한 "신규 CSS 격리 + index.html 링크 1줄 추가" 패턴 선례
- `docs/architecture.md` — "프론트엔드 셸 공개 API 요약" 및 데이터 흐름
- `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/feature-spec.md` — 사용자 시나리오 §"조합 개수·분석 회차 슬라이더 조정 후 추천받기"
- `docs/modules/qa_engineer_module_7_scope.md` — 본 모듈 변경 후에도 통과해야 할 smoke 계약
- `docs/plans/2026-04-18-backend-api-scope.md` — `n=1..10`, `draws=100..500` 검증 범위 출처
