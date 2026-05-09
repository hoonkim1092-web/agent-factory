# frontend_dev_module_3 Code Review

## 메타데이터
- task_id: `frontend_dev_module_3_code_review`
- reviewer_role: frontend_dev_code_reviewer
- reviewed_at: 2026-04-18
- phase: code_review
- 대상 산출물:
  - `web/js/components/CardList.js`
  - `web/styles/cards.css`
  - `web/index.html` (link 1줄 추가)
  - `docs/architecture.md`, `docs/change_history.md` (계약 갱신)
- 참고 문서: `docs/modules/frontend_dev_module_3_scope.md`, `docs/modules/frontend_dev_module_3_scope_review.md`

## 판정
- `WARN` — 구현은 scope 계약을 충실히 반영하고 XSS·경계값·접근성 측면에서 치명적 결함이 없다. 다만 HTML 구조 유효성과 키보드 토글 이중 처리 부분은 후속 모듈(4/5) 확장을 위해 기록해 둔다.

## 검토 항목별 결과

### 1. 보안 취약점 (OWASP Top 10)
- `ACCEPT`: 모든 사용자/서버 값은 `textContent` 또는 숫자 연산을 거쳐 DOM에 주입된다. `innerHTML` 은 빈 문자열 초기화(`el.innerHTML = ""`)에만 사용하며 외부 입력을 주입하지 않는다.
  - 근거: `web/js/components/CardList.js:22`, `web/js/components/CardList.js:121`, `web/js/components/CardList.js:152`, `web/js/components/CardList.js:209`, `web/js/components/CardList.js:235`
- `ACCEPT`: `setAttribute` 로 주입되는 값은 고정 문자열 또는 `Number.toFixed()`, 숫자 연산 결과로만 구성되어 속성 주입(attribute injection) 여지가 없다.
  - 근거: `web/js/components/CardList.js:60-62`, `web/js/components/CardList.js:175-180`
- `ACCEPT`: `style.setProperty("--h", String(v / max))`, `style.width = \`${Math.round(safe * 100)}%\`` 는 모두 `Number.isFinite` 필터와 `clamp01`을 거친 수치로, CSS 인젝션 위험이 없다.
  - 근거: `web/js/components/CardList.js:184`, `web/js/components/CardList.js:234`
- 결론: XSS/HTML 인젝션/CSS 인젝션 관점에서 현재 경로는 모두 안전하다.

### 2. 버그 및 엣지 케이스
- `ACCEPT`: `renderCardList` 진입 방어(`el instanceof HTMLElement`, `Array.isArray(combos)`)가 scope §7과 일치한다.
  - 근거: `web/js/components/CardList.js:21-32`
- `ACCEPT`: `combos` 가 빈 배열이면 `empty-hint` 문구를 유지해 smoke 테스트 계약과 호환된다.
  - 근거: `web/js/components/CardList.js:26-32`, `tests/frontend/test_smoke_render.py:58-60`
- `ACCEPT`: `renderBalls` 는 비숫자/NaN/Infinity 를 `Number.isFinite` 로 제거하고 방어적 오름차순 정렬을 수행한다.
  - 근거: `web/js/components/CardList.js:114-116`
- `ACCEPT`: `formatScore` / `clamp01` 이 범위 밖 값을 `"--"` 또는 0/1 로 클램프해 렌더를 깨뜨리지 않는다.
  - 근거: `web/js/components/CardList.js:161-198`
- `ACCEPT`: `renderSections` 가 길이 <5 는 0 으로 패딩, >5 는 `slice(0, 5)` 로 절삭, 음수·비숫자는 0 치환해 scope §5 R3 방어 전략과 일치한다.
  - 근거: `web/js/components/CardList.js:224-237`
- `WARN` (LOW): `renderBalls` 는 길이 6 을 강제하지 않는다. 백엔드 계약(`numbers.length === 6`)이 깨질 경우 5개 또는 7개 공을 그대로 렌더한다. 이는 scope §리스크 R3(“카드 1개 실패가 전체 리스트를 무너뜨리지 않게”) 정책과 일치하지만, 길이 이상이 QA 단계에서 곧바로 드러나도록 `length !== 6` 시 `unknown` 마커를 남기거나 개발자 콘솔 경고를 남기는 것이 후속 모듈에서 고려 가능하다.
  - 근거: `web/js/components/CardList.js:109-126`, `docs/modules/frontend_dev_module_3_scope.md:22-24`, `docs/modules/frontend_dev_module_3_scope.md:184-186`
- `WARN` (LOW): Enter/Space 토글이 `<button>` 의 네이티브 활성화와 **중복**될 여지가 있다. 현재는 `event.preventDefault()` 로 네이티브 click 합성을 차단해 실질적 이중 토글은 발생하지 않지만, 보조기술/IME 합성 중 일부 조합에서 `key` 값이 `"Spacebar"` 로 들어오는 레거시 브라우저(구 Edge, IE)에서는 네이티브만 동작한다. 요구하는 지원 범위(모던 모바일 웹) 내에서는 문제 없음.
  - 근거: `web/js/components/CardList.js:80-86`, `docs/modules/frontend_dev_module_3_scope.md:36-40`

### 3. 설계 품질
- `ACCEPT`: 단일 책임 — `renderBalls/formatScore/renderGauge/renderRatioBadge/renderSections` 가 각 시각 요소를 독립적으로 담당하고, `buildCombo` 가 조립만 맡는다.
  - 근거: `web/js/components/CardList.js:53-240`
- `ACCEPT`: 공개 API(`renderCardList(el, combos) => void`) 시그니처가 `frontend_dev_module_2` 계약과 일치한다.
  - 근거: `web/js/components/CardList.js:20`, `web/js/app.js:7`, `web/js/app.js:129`, `docs/modules/frontend_dev_module_2_scope.md:86-95`
- `ACCEPT`: 의존성 방향이 외부(app → CardList) 단방향이며, `state.store` 에 접근하지 않고 지역 DOM 상태(`aria-expanded`, `hidden`)만 사용한다. scope §4 상호작용 정책과 일치.
  - 근거: `web/js/components/CardList.js:96-101`, `docs/modules/frontend_dev_module_3_scope.md:122-130`
- `ACCEPT`: BEM 계열 클래스가 scope §2 DOM 구조와 일치하며 `qa_engineer_module_7` smoke 필수 셀렉터/슬롯과 충돌하지 않는다.
  - 근거: `docs/modules/frontend_dev_module_3_scope.md:75-112`, `tests/frontend/test_smoke_render.py:36-40`
- `WARN` (LOW, **HTML 유효성**): `<button>` 이 `<span>` → `<ul>`/`<ol>` 을 자식으로 포함하는 구조는 HTML5 명세상 “button 의 content model 은 phrasing content 이며 interactive content 를 자손으로 가질 수 없다” 와 충돌한다(`<ul>`/`<ol>` 은 flow content). 브라우저는 관대하게 렌더하고 실제 접근성·동작에는 영향이 없으나, 미래에 lint(axe, html-validate, eslint-plugin-jsx-a11y) 를 도입하면 경고가 발생할 수 있다. scope 에서 이미 이 구조를 확정·교차검증했으므로 `BLOCK` 은 아니며, `frontend_dev_module_4/5` 에서 구조를 재검토할 여지를 남긴다.
  - 근거: `web/js/components/CardList.js:57-89`, `docs/modules/frontend_dev_module_3_scope.md:75-112`

### 4. 에러 처리
- `ACCEPT`: scope §리스크 R3 에 따라 `try/catch` 없이 **입력 검증 분기**로 카드 1개 실패가 전체 리스트를 무너뜨리지 않도록 방어한다(숫자 필터/슬라이스/클램프).
  - 근거: `web/js/components/CardList.js:109-240`, `docs/modules/frontend_dev_module_3_scope.md:184-186`
- `ACCEPT`: `combo?.numbers` 등 옵셔널 체이닝으로 `combo` 가 `null/undefined` 인 비정상 입력에서도 예외 없이 렌더한다.
  - 근거: `web/js/components/CardList.js:67-76`

### 5. 성능
- `ACCEPT`: 렌더 복잡도가 O(N) (조합 수 × 6 공 + 5 섹션)으로 상수 시간. `draws=500` 시나리오에서도 카드 수(기본 5개)는 고정이므로 무관.
- `ACCEPT`: 재렌더 시 `el.innerHTML = ""` 로 기존 DOM 제거 → 기존 이벤트 리스너는 GC 대상이 되어 누수 없음.
  - 근거: `web/js/components/CardList.js:22-44`
- `ACCEPT`: `cards.css` 는 transition 에 `prefers-reduced-motion: reduce` 훅을 제공해 저성능/모션 감소 환경에서 GPU 부하를 제거한다.
  - 근거: `web/styles/cards.css:220-230`

### 6. 문서/계약 정합성
- `ACCEPT`: `docs/architecture.md` §프론트엔드 셸 공개 API 요약 > `renderCardList` 항목이 실제 시각화 설명으로 갱신됨.
  - 근거: `docs/architecture.md:19-20`, `docs/architecture.md:72`
- `ACCEPT`: `docs/change_history.md` 에 2026-04-18 build 항목(요약/이유/영향 파일/후속 작업)이 추가됐다.
  - 근거: `docs/change_history.md:20-23`
- `ACCEPT`: `web/index.html` 의 `base → layout → cards` 링크 순서가 scope §3 과 일치하며 smoke 테스트의 필수 링크(`./styles/base.css`, `./styles/layout.css`) 존재성을 유지한다.
  - 근거: `web/index.html:15-17`, `tests/frontend/test_smoke_render.py:32-34`

## 이슈 요약
1. (WARN/LOW) HTML 유효성 — `<button>` 자손에 `<ul>`/`<ol>` 이 포함됨. 브라우저는 허용하나 lint 도입 시 경고 가능. scope 합의 사항이므로 BLOCK 아님.
2. (WARN/LOW) Enter/Space 중복 처리 — 네이티브 활성화 + 수동 keydown. 현재는 `preventDefault` 로 안전하나 레거시 브라우저에서 분기 필요. 지원 범위 내에서는 문제 없음.
3. (INFO) `renderBalls` 길이 6 미강제 — R3 “부분 실패 허용” 정책과 일치. 후속 모듈에서 개발자 콘솔 경고를 고려해 볼 수 있음.

## 결론
- 보안·버그·에러 처리·성능은 PASS 수준이다.
- 설계/HTML 유효성 영역에서 LOW 수준 경고 2건이 있으나 모두 scope 교차검증을 통과한 합의 범위 안이며 회귀 위험은 없다.
- verify 단계(`frontend_dev_module_3_verify_3`)에서 iPhone SE(375)/Pixel(412) 뷰포트 수동 렌더와 `prefers-reduced-motion` 동작을 확인하면 BLOCK 없이 진행 가능하다.

## JSON 판정
```json
{
  "verdict": "WARN",
  "issues": [
    {
      "severity": "low",
      "category": "design",
      "title": "button 자손에 ul/ol 포함 — HTML5 content model 위반",
      "location": "web/js/components/CardList.js:57-89",
      "impact": "lint/axe 도입 시 경고. 실제 동작/접근성 영향 없음.",
      "recommendation": "후속 모듈에서 button → div[role=button] + aria-* 구조 또는 카드 바깥으로 펼침 제어 이관 검토."
    },
    {
      "severity": "low",
      "category": "bug",
      "title": "Enter/Space keydown 중복 처리",
      "location": "web/js/components/CardList.js:80-86",
      "impact": "모던 브라우저에서는 preventDefault로 안전. 레거시 브라우저 분기 시 예외 가능.",
      "recommendation": "지원 범위가 모던 모바일이므로 현 상태 유지. 문서에 의도 주석 유지."
    },
    {
      "severity": "info",
      "category": "edge-case",
      "title": "renderBalls 가 길이 6 미강제",
      "location": "web/js/components/CardList.js:109-126",
      "impact": "R3 부분 실패 허용 정책과 일치.",
      "recommendation": "QA 계약 위반 조기 탐지를 위해 length !== 6 일 때 개발자 콘솔 warn 남기는 것 검토."
    }
  ],
  "summary": "CardList.js / cards.css / index.html 변경은 scope 계약과 일치하고 XSS·경계값·접근성·성능 측면에서 치명적 결함이 없다. button 자손에 ul/ol 을 둔 구조는 HTML 유효성 경고 여지가 있으나 scope 합의 사항이므로 WARN으로 기록하고 진행 권고."
}
```
