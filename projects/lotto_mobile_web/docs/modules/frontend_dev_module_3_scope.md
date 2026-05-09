# 조합 카드 시각화 컴포넌트 — 범위와 인터페이스 정의

## 메타데이터
- task_id: `frontend_dev_module_3_scope_1`
- module_id: `frontend_dev_module_3`
- owner_role: frontend_dev
- phase: scope
- last_updated: 2026-04-18
- status: draft
- 문서 언어: 한국어 (OS: `ko-KR`)

## 목적
모바일 웹 로또 추천 서비스에서 추천 조합(조합 번호 + 점수 + 홀짝 비율 + 구간 분포)을 한 화면에 시각적으로 인지할 수 있도록 렌더링하는 **조합 카드 시각화 컴포넌트**의 범위와 공개 인터페이스를 고정한다.
본 문서는 `frontend_dev_module_2`가 자리표시자로 노출한 `renderCardList(el, combos)` 를 실제 카드 UI로 치환하는 단일 모듈(`frontend_dev_module_3`)만 대상으로 하며, 슬라이더(`module_4`)나 오프라인 폴백(`module_5`) 로직은 포함하지 않는다.

## 범위 (In Scope)
1. 카드 리스트 렌더러 치환
   - `web/js/components/CardList.js` 의 `renderCardList(el, combos)` 공개 API 를 실제 구현으로 교체
   - 기존 호출자(`web/js/app.js`)와의 계약(시그니처, 인자 순서, 반환 없음)을 그대로 유지
2. 조합 번호 시각화
   - 6개 번호를 **번호 공(ball)** 형태로 수평 배열
   - 번호 범위별 색상 구분(1–10 노랑, 11–20 파랑, 21–30 빨강, 31–40 회색, 41–45 초록 — 한국 로또 표준 색상 관례)
   - 오름차순 정렬 표시(서버 응답이 정렬돼 있어도 방어적으로 한 번 더 정렬)
   - 번호 공은 최소 32 CSS px, 터치 타깃 전체 컨테이너(요약 행)는 44×44 이상
3. 점수(score) 시각화
   - 소수 두 자리 고정 표시(예: `0.87`)
   - 0.0–1.0 범위를 시각적 게이지(수평 막대 또는 원형 진행도) 1종으로 제공
   - 범위 밖 값은 클램프 후 `--` 텍스트로 표기
4. 홀짝 비율(odd_even_ratio) 시각화
   - `"3:3"` 형태의 문자열을 그대로 배지(badge)로 표기
   - 잘못된 형식이면 원문을 그대로 보여주되 배지 클래스만 적용
5. 구간 분포(section_distribution) 시각화
   - 길이 5 배열을 5칸 미니 히스토그램(높이·불투명도 매핑) 또는 5개 도트로 표기
   - 합계가 6을 초과/미달이어도 렌더는 깨지지 않게 방어
6. 카드 상호작용
   - 각 카드는 `<button>` 기반 토글로 동작: 기본은 **접힘(요약)**, 탭/클릭·Enter·Space 시 **펼침(상세)**
     - 요약: 번호 공 + 간단 score 수치
     - 상세: score 게이지 + 홀짝 비율 배지 + 구간 분포 히스토그램
   - `aria-expanded`, `aria-controls`, `aria-labelledby` 를 설정해 스크린리더가 전개 상태를 인지
   - 키보드 포커스 링 유지(기본 `:focus-visible` 토큰)
7. 빈 상태 / 이상 데이터 처리
   - `combos` 가 비어 있으면 `empty-hint` 문구(“추천 결과가 없습니다.”) 유지 — 기존 자리표시자 계약과 동일
   - `combos` 가 배열이 아니거나 `el` 이 `HTMLElement` 가 아니면 no-op 로 안전 반환
8. 스타일 자산
   - 새 파일 `web/styles/cards.css` 를 추가해 카드 전용 스타일을 격리(기존 `base.css`·`layout.css` 는 건드리지 않음)
   - `web/index.html` 에 `cards.css` 링크 한 줄 추가(셸 변경점 1건) — qa_engineer_module_7 smoke 테스트와 호환

## 범위 밖 (Out of Scope)
- `ParamPanel.js` 슬라이더 인터랙션 구현(→ `frontend_dev_module_4`)
- `OfflineBanner.js` 및 `localStorage` 캐시 정책(→ `frontend_dev_module_5`)
- 실제 애니메이션 라이브러리 도입(프레임워크 미도입 원칙 유지)
- 카드 즐겨찾기·공유·복사 기능(현재 feature-spec 범위 밖)
- 서버 측 응답 스키마 변경(백엔드 계약은 그대로 소비)
- `draws=500` 지연 시의 로딩 스켈레톤 UX 정책(아키텍처 §열린 질문으로 유지)
- Lighthouse 점수 측정, 픽셀 회귀 테스트

## 인터페이스 정의

### 1) 공개 API(유지)
| 파일 | export | 시그니처 | 변경점 |
|------|--------|----------|--------|
| `web/js/components/CardList.js` | `renderCardList` | `(el: HTMLElement, combos: RecommendationCombo[]) => void` | 시그니처 동일, 내부 구현만 치환 |

- `RecommendationCombo`(아키텍처 §프론트엔드 셸 공개 API 요약과 동일):
  ```ts
  {
    numbers: number[];           // 길이 6, 1..45
    score: number;               // 0..1
    odd_even_ratio: string;      // "3:3" 등
    section_distribution: number[]; // 길이 5
  }
  ```
- 반환: `void`(side-effect 로 `el` 내부 교체). 기존 호출자(`app.js`)는 수정하지 않는다.

### 2) DOM 구조(카드 단위, BEM 계열 클래스)
```
<ol class="card-list">
  <li class="card-list__item">
    <button
      class="combo-card"
      type="button"
      aria-expanded="false"
      aria-controls="combo-card-detail-{idx}"
      aria-labelledby="combo-card-summary-{idx}"
    >
      <span id="combo-card-summary-{idx}" class="combo-card__summary">
        <ul class="combo-card__balls" aria-label="추천 번호">
          <li class="combo-card__ball combo-card__ball--b1">3</li>
          ...6개
        </ul>
        <span class="combo-card__score-text">점수 0.87</span>
      </span>
      <span
        id="combo-card-detail-{idx}"
        class="combo-card__detail"
        hidden
      >
        <div class="combo-card__score-gauge" role="meter"
             aria-valuemin="0" aria-valuemax="1" aria-valuenow="0.87">
          <span class="combo-card__score-fill" style="width: 87%;"></span>
        </div>
        <span class="combo-card__ratio" aria-label="홀짝 비율">3:3</span>
        <ol class="combo-card__sections" aria-label="구간 분포">
          <li class="combo-card__section" style="--h: 1;">1</li>
          ...5개
        </ol>
      </span>
    </button>
  </li>
  ...
</ol>
```
- 클래스 이름은 smoke 테스트가 결합하지 않도록 **필수 슬롯 존재**만 강제하고, 상세 선택자는 내부 구현으로 본다.

### 3) 스타일 자산
- 신규: `web/styles/cards.css`
  - 토큰(`--color-*`, `--space-*`, `--radius-*`, `--touch-target-min`)은 `base.css` 를 재사용
  - 번호 공 색상: `--ball-b1..b5` 변수로 정의해 `prefers-color-scheme: dark` 훅 확장 여지 남김
  - 펼침/접힘 전이는 `prefers-reduced-motion: reduce` 조건에서 제거
- 셸 변경: `web/index.html` 의 `<head>` 에 `<link rel="stylesheet" href="./styles/cards.css" />` 추가(레이아웃 순서: `base → layout → cards`)

### 4) 상호작용·상태
- 카드 상태는 DOM 내부(`aria-expanded`, `hidden`)로만 관리하고 `state.store` 는 건드리지 않는다(카드 UX 는 지역 상태).
- 재렌더 시(`store.subscribe` → `applyStateToDom` → `renderCardList`) **매번 DOM 재생성**이 기본 동작이며, 사용자의 펼침 상태는 재렌더 경계에서 초기화되는 것을 수용한다(리스트 스크롤·펼침 보존은 후속 과제).
- 접근성
  - 각 카드: `<button>` 한 개로 포커싱·활성화 통합, `aria-expanded` 가 상태를 설명
  - 번호 공: `<ul>` 랩핑 + `aria-label="추천 번호"` 제공
  - 구간 분포: `<ol>` 랩핑 + `aria-label="구간 분포"` 제공
  - 점수 게이지: `role="meter"`, `aria-valuemin/max/now`

### 5) 기존 모듈과의 결합
| 결합 지점 | 기존 | 본 모듈 변경 |
|-----------|------|--------------|
| `web/js/app.js` | `renderCardList(cardListRoot, combos)` 호출 | 변경 없음 |
| `web/js/components/CardList.js` | 번호만 `·` 로 출력하는 자리표시자 | 실제 카드 시각화로 치환 |
| `web/index.html` | `base.css`, `layout.css` 링크 | `cards.css` 링크 1줄 추가 |
| `web/styles/cards.css` | — | 신규 추가 |
| `web/js/state.js` | `{params, result, status, lastError}` | 변경 없음 |
| `web/js/api.js` | — | 변경 없음 |
| `tests/frontend/test_smoke_render.py` | 파일/Export/셸 계약 검사 | 통과 유지(신규 CSS 파일은 smoke 필수 항목이 아님) |

## 의존성
- 상류(upstream, 이 모듈이 소비)
  - `frontend_dev_module_2` 산출물: `web/index.html`, `web/js/app.js`, `web/js/components/CardList.js` 자리표시자, `web/js/state.js` 의 `result.combos` 계약
  - `backend_dev_module_1` 의 `RecommendationCombo` 스키마(아키텍처 §데이터 흐름)
- 하류(downstream)
  - `qa_engineer_module_7` smoke 테스트는 본 모듈 이후에도 통과해야 한다(필수 파일/Export 계약은 그대로 유지)
  - `frontend_dev_module_5` 오프라인 폴백은 `source === 'offline' | 'cache'` 상태에서 본 카드 렌더를 그대로 재사용한다
- 횡단(cross-cutting)
  - `docs/architecture.md` 의 “프론트엔드 셸 공개 API 요약”에서 `renderCardList` 설명이 실제 시각화로 갱신되어야 함(build 단계에서 반영)

## 산출물 (Deliverables)
- `docs/modules/frontend_dev_module_3_scope.md` — 본 범위 문서
- `web/js/components/CardList.js` — build 단계에서 실제 시각화로 치환
- `web/styles/cards.css` — build 단계에서 신규 추가
- `web/index.html` — build 단계에서 `cards.css` 링크 1줄 추가
- `docs/architecture.md`, `docs/change_history.md` — 본 scope 작업에서 계약 문서 갱신(설계 변경 반영)

## 구현 순서 (고정)
1. 본 scope 문서를 근거로 `web/styles/cards.css` 토큰·클래스 골격을 생성한다(번호 공 5단계 색상, 카드 컨테이너, 게이지, 히스토그램).
2. `web/index.html` 에 `cards.css` 링크를 추가한다(순서: base → layout → cards).
3. `web/js/components/CardList.js` 내부를 치환한다:
   1. 입력 방어(`el`·`combos` 타입/빈 배열) 분기
   2. 번호 공 렌더 헬퍼(`renderBalls(numbers)`)
   3. 점수 표시 헬퍼(`formatScore(score)` + `renderGauge(score)`)
   4. 홀짝 비율 배지 헬퍼
   5. 구간 분포 히스토그램 헬퍼
   6. 카드 전체를 `<button aria-expanded>` 로 조립
   7. 클릭·Enter·Space 로 `aria-expanded` 토글, 상세 블록 `hidden` 동기화
4. 수동 시각 점검: `python -m http.server` 로 iPhone SE(375)·Pixel(412) 뷰포트에서 가로 스크롤 없음/탭 동작 확인.
5. 회귀 확인: `pytest tests/frontend/test_smoke_render.py` — 필수 셸 계약/Export 통과를 재확인한다.
6. `docs/architecture.md` 의 “프론트엔드 셸 공개 API 요약 > `renderCardList`” 항목을 실제 시각화 설명으로 갱신하고, `docs/change_history.md` 에 build 항목을 추가한다(이 갱신 자체는 build 태스크에서 수행).
7. verify 단계로 handoff(`frontend_dev_module_3_verify_3`).

## 수용 기준 (이 문서 단위)
- 조합 카드 시각화 컴포넌트의 범위/비범위/인터페이스/의존성/산출물/구현 순서가 문서화돼 있다.
- 공개 API(`renderCardList` 시그니처)가 `frontend_dev_module_2` 계약과 일치한다.
- 영향 파일(`CardList.js`, `cards.css`, `index.html`)과 비침범 파일(`state.js`, `api.js`, `app.js`, `base.css`, `layout.css`)이 명시된다.
- build 단계 담당자가 재해석 없이 §구현 순서 1–7 을 그대로 실행할 수 있다.
- QA smoke 테스트(`qa_engineer_module_7`)가 placeholder/실제 구현 양쪽에서 통과하는 계약이 유지된다.

## 리스크와 완화
- (R1) 펼침/접힘 상태가 스토어 재렌더 시 초기화됨 → 지역 DOM 상태로 설계됐음을 본 문서에 명시하고, 필요 시 후속 모듈에서 `state.params.expandedCardIndex` 형태로 승격한다.
- (R2) 번호 공 색상 팔레트가 접근성(대비) 기준을 벗어날 가능성 → `cards.css` 에서 AA 대비(텍스트 ≥ 4.5:1) 값으로 고정하고, 다크 훅을 `--ball-*-dark` 로 별도 준비한다.
- (R3) 스토어 응답이 스키마를 어길 경우 렌더 폭파 → 카드 단위로 `try/catch` 없이 **입력 검증 분기**만 두고, 필드 누락 시 해당 섹션만 자리표시로 렌더한다(카드 1개 실패가 전체 리스트를 무너뜨리지 않게).
- (R4) 신규 CSS 링크 추가로 smoke 테스트가 깨질 가능성 → `qa_engineer_module_7_scope.md` §검증 대상은 `base.css`·`layout.css` 존재성만 강제하므로 회귀 없음을 확인.

## 참고
- `docs/modules/frontend_dev_module_2_scope.md` — 자리표시자 계약 표 §3
- `docs/architecture.md` — “프론트엔드 셸 공개 API 요약” 및 데이터 흐름
- `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/feature-spec.md` — 사용자 시나리오 §“카드 탭 → 상세 영역 표시”
- `docs/modules/qa_engineer_module_7_scope.md` — 본 모듈 변경 후에도 통과해야 할 smoke 계약
