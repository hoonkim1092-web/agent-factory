# frontend_dev_module_4 Code Review

## 메타데이터
- task_id: `frontend_dev_module_4_code_review`
- reviewer_role: frontend_dev_code_reviewer
- reviewed_at: 2026-04-18
- phase: code_review
- 대상 산출물:
  - `web/js/components/ParamPanel.js`
  - `web/styles/sliders.css`
  - `web/index.html`
  - `tests/frontend/test_param_panel_contract.py`
- 참고 문서:
  - `docs/modules/frontend_dev_module_4_scope.md`
  - `docs/plans/2026-04-18-parameter-slider-control.md`
  - `docs/architecture.md`

## 판정
- `WARN` — 슬라이더 구현은 보안·입력 경계·접근성 측면에서 대체로 안전하고 scope 계약도 잘 지킨다. 다만 재마운트/언마운트 경로에서 정리되지 않는 구독과 이벤트가 남고, 회귀 테스트가 문자열 매칭 위주라 구조적 회귀를 충분히 막지 못한다.

## 검토 항목별 결과

### 1. 보안 취약점
- `ACCEPT`: 사용자 입력은 `Number(target.value)` 후 `clampToStep()`을 거쳐 숫자로만 스토어에 반영된다. DOM 반영도 `value`, `textContent`, `aria-valuetext`만 사용해 XSS/속성 인젝션 여지가 없다.
  - 근거: `web/js/components/ParamPanel.js:43-50`, `web/js/components/ParamPanel.js:63-77`
- `ACCEPT`: `el.innerHTML = ""`는 외부 입력 주입이 아닌 초기화 용도에 한정되어 있다.
  - 근거: `web/js/components/ParamPanel.js:93-108`

### 2. 버그 및 엣지 케이스
- `WARN` (MEDIUM): `renderParamPanel()`가 `store.subscribe(syncFromState)`의 반환값을 버리고 끝난다. `mountApp().unmount()`도 이 구독을 정리하지 않으므로 동일 루트 재마운트, 테스트 반복, 향후 HMR/부분 재초기화에서 죽은 DOM 참조를 붙든 구독이 누적된다.
  - 근거: `web/js/components/ParamPanel.js:82-85`, `web/js/app.js:41-60`
- `WARN` (MEDIUM): `mountApp()`는 `submitButton.addEventListener("click", ...)`를 등록하지만 `unmount()`에서 제거하지 않는다. 현재 앱이 1회 부트스트랩만 가정하면 숨겨지지만, 테스트나 재마운트 환경에서는 중복 요청이 발생할 수 있다.
  - 근거: `web/js/app.js:51-60`
- `ACCEPT`: 외부 상태가 범위를 벗어나도 `clampToStep()`가 `n`, `draws`를 안전 범위로 정렬해 UI가 깨지지 않는다.
  - 근거: `web/js/components/ParamPanel.js:63-65`, `web/js/components/ParamPanel.js:153-158`

### 3. 설계 품질
- `ACCEPT`: `SLIDERS` 메타데이터로 범위/라벨/단위를 한곳에 모아 DOM 생성과 상태 동기화가 같은 계약을 공유한다. 하드코딩 분산보다 유지보수성이 좋다.
  - 근거: `web/js/components/ParamPanel.js:10-14`, `web/js/components/ParamPanel.js:36-40`, `web/js/components/ParamPanel.js:59-65`
- `WARN` (LOW): 공개 API가 `void`만 반환해 정리 책임을 외부에서 가질 수 없다. 현재 설계는 “1회 마운트” 전제에 강하게 묶여 있고, 컴포넌트 수명주기 제어가 필요한 환경으로 확장될 때 인터페이스가 바로 한계에 닿는다.
  - 근거: `web/js/components/ParamPanel.js:26-85`

### 4. 에러 처리
- `ACCEPT`: 잘못된 요소/스토어 입력에 대해 조기 반환하고, 숫자가 아닌 값은 `clampToStep()`와 `Number.isFinite()`로 방어한다.
  - 근거: `web/js/components/ParamPanel.js:27-30`, `web/js/components/ParamPanel.js:48-49`, `web/js/components/ParamPanel.js:153-158`
- `ACCEPT`: 폼 submit은 `preventDefault()`로 막아 의도치 않은 페이지 이동을 차단한다.
  - 근거: `web/js/components/ParamPanel.js:100-101`

### 5. 성능
- `ACCEPT`: 상태 동기화는 슬라이더 2개에 대해 값 비교 후 필요한 속성만 갱신해 드래그 중 재생성 비용을 피한다.
  - 근거: `web/js/components/ParamPanel.js:66-77`
- `WARN` (LOW): `handleInput()`마다 `SLIDERS.find(...)` 선형 탐색을 수행한다. 현재 2개 슬라이더라 영향은 무시 가능하지만, 메타데이터 기반 설계를 유지할 거면 이름→spec 맵이 더 일관된 구조다.
  - 근거: `web/js/components/ParamPanel.js:43-47`

### 6. 테스트 품질
- `WARN` (MEDIUM): `test_param_panel_contract.py`는 구현 문자열 존재 여부만 단언한다. 함수 추출, 상수 이동, 작은 리팩터링만으로도 동작은 같지만 테스트가 깨지고, 반대로 실제 DOM/구독 정리 버그는 놓친다.
  - 근거: `tests/frontend/test_param_panel_contract.py:11-24`

## 이슈 요약
1. `web/js/components/ParamPanel.js:82-85`, `web/js/app.js:41-60`
   - 카테고리: bug/design
   - 심각도: medium
   - 내용: 슬라이더 구독과 submit 버튼 이벤트가 언마운트에서 정리되지 않는다.
   - 영향: 재마운트 시 메모리 누수, 중복 렌더, 중복 요청 위험.
   - 권고: `renderParamPanel()`이 cleanup 함수를 반환하거나 `mountApp()`가 등록한 모든 정리 함수를 통합 관리하도록 변경.
2. `tests/frontend/test_param_panel_contract.py:11-24`
   - 카테고리: test/design
   - 심각도: medium
   - 내용: 문자열 매칭 기반 계약 테스트라 구조적 회귀는 놓치고 리팩터링 내성은 낮다.
   - 영향: 실제 품질 대비 테스트 신뢰도가 낮다.
   - 권고: DOM 생성 결과, 슬라이더 속성, store 호출, loading 시 disabled 동작을 실행 기반 테스트로 전환.
3. `web/js/components/ParamPanel.js:43-47`
   - 카테고리: performance/design
   - 심각도: low
   - 내용: 이벤트마다 `SLIDERS.find()` 선형 탐색.
   - 영향: 현재는 미미하나 메타데이터 확장 시 불필요한 반복.
   - 권고: `const sliderByName = new Map(...)` 형태로 고정 조회 사용 검토.

## 결론
- 치명적인 보안 문제나 즉시 수정이 필요한 경계값 버그는 없다.
- 다만 수명주기 정리 누락과 테스트 취약성은 실제 프로젝트 확장 단계에서 문제를 만들 가능성이 있어 `WARN`으로 기록한다.

## JSON 판정
```json
{
  "verdict": "WARN",
  "issues": [
    {
      "severity": "medium",
      "category": "bug",
      "title": "슬라이더 store 구독과 submit 버튼 이벤트가 언마운트 시 정리되지 않음",
      "location": "web/js/components/ParamPanel.js:82-85, web/js/app.js:41-60",
      "impact": "재마운트·테스트 반복·향후 HMR 환경에서 죽은 DOM 참조와 중복 요청이 누적될 수 있다.",
      "recommendation": "renderParamPanel이 cleanup 함수를 반환하거나 mountApp이 클릭 리스너와 구독 해제를 함께 관리하도록 수정한다."
    },
    {
      "severity": "medium",
      "category": "test",
      "title": "계약 테스트가 구현 문자열 매칭에 과도하게 의존함",
      "location": "tests/frontend/test_param_panel_contract.py:11-24",
      "impact": "사소한 리팩터링에 취약하고 실제 동작 회귀는 놓칠 수 있다.",
      "recommendation": "DOM/이벤트/store 상호작용을 직접 검증하는 실행 기반 테스트로 보강한다."
    },
    {
      "severity": "low",
      "category": "performance",
      "title": "입력 이벤트마다 slider spec을 선형 탐색함",
      "location": "web/js/components/ParamPanel.js:43-47",
      "impact": "현재 비용은 작지만 구조적으로 불필요한 반복이다.",
      "recommendation": "이름 기준 lookup map을 만들어 고정 시간 조회로 단순화한다."
    }
  ],
  "summary": "frontend_dev_module_4의 슬라이더 구현은 보안과 입력 경계 처리 측면에서 안전하며 scope 계약도 잘 지킨다. 다만 renderParamPanel과 mountApp이 구독/이벤트 정리를 노출하지 않아 재마운트 시 누수와 중복 동작 위험이 있고, 계약 테스트는 문자열 매칭 중심이라 회귀 검출력이 제한적이므로 WARN으로 판단한다."
}
```
