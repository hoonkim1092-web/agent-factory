# frontend_dev_module_4 Cross Validation

## 메타데이터
- task_id: `frontend_dev_module_4_cross_validate`
- validator_role: `frontend_dev_cross_validator`
- validated_at: 2026-04-18
- phase: `cross_validate`
- 대상 산출물:
  - `web/js/components/ParamPanel.js`
  - `web/styles/sliders.css`
  - `web/index.html`
  - `web/js/app.js`
  - `web/js/state.js`
  - `web/js/api.js`
  - `tests/frontend/test_param_panel_contract.py`
  - `tests/frontend/test_smoke_render.py`
  - `docs/modules/frontend_dev_module_4_scope.md`
  - `docs/architecture.md`
  - `docs/change_history.md`

## 검증 결과
- 판정: `WARN`

## 교차검증 요약
- 모듈 간 공개 계약은 대체로 일치한다. `renderParamPanel(el, store)` 시그니처는 유지되고, `state.js`의 `params` 부분 병합 계약을 전제로 `params.n`/`params.draws`만 갱신하며 `params.offline`을 보존한다.
- 설계 문서와 구현의 핵심 범위도 정렬된다. 슬라이더 범위(`n=1..10`, `draws=100..500`), `loading` 시 비활성화, `sliders.css` 분리, `index.html` 링크 순서는 scope 및 architecture와 일치한다.
- 다만 전체 정합성 관점에서는 수명주기 정리 누락과 실행 기반 테스트 부재가 남아 있어, 재마운트·반복 실행·향후 통합 단계에서 회귀를 충분히 막지 못한다.

## 검토 항목별 결과

### 1. 모듈 간 인터페이스 일관성
- `PASS`: `web/js/app.js`는 기존대로 `renderParamPanel(paramPanelRoot, store)`를 호출하고, `web/js/components/ParamPanel.js`는 `void` 반환 계약을 유지한다.
- `PASS`: `web/js/state.js`의 `setState()`는 `params`를 한 단계 더 얕게 병합하므로, 슬라이더가 `{ params: { [spec.name]: value } }`만 보내도 `offline` 값이 보존된다.
- `WARN`: `ParamPanel`은 내부에서 `store.subscribe(syncFromState)`를 등록하지만 해제 경로를 외부에 노출하지 않는다. 반면 상위 `mountApp().unmount()`는 자신의 store 구독만 정리한다. 결과적으로 컴포넌트 수명주기 계약은 상위 모듈과 완전히 맞물리지 않는다.

### 2. 설계 문서와 구현의 괴리
- `PASS`: `docs/modules/frontend_dev_module_4_scope.md`와 `docs/architecture.md`에 적힌 슬라이더 범위, `aria-valuetext`, `output`, `loading` 비활성화 정책은 구현과 일치한다.
- `PASS`: `web/index.html`은 `base → layout → cards → sliders` 순서로 스타일을 로드한다.
- `PASS`: build 단계에서 요구된 문서 갱신(`docs/architecture.md`, `docs/change_history.md`)도 반영되어 있다.

### 3. 테스트 커버리지 갭
- `WARN`: `tests/frontend/test_param_panel_contract.py`는 문자열 매칭 위주라 실제 DOM 구조, 슬라이더 속성, `store.setState()` 호출, 외부 상태 변경 반영, `loading` 전환 시 disabled 토글을 실행으로 검증하지 않는다.
- `WARN`: `tests/frontend/test_smoke_render.py`도 `ParamPanel`의 동작 경계를 직접 검증하지 않는다. 따라서 scope에서 강조한 "1회 마운트 + 속성 갱신", "외부 상태 클램프", "드래그 중 DOM 재생성 금지"는 회귀 방어망이 없다.

### 4. 의존성 그래프 정합성
- `PASS`: 상류 의존성인 `state.js`, `app.js`, `api.js`와의 데이터 경계는 충돌 없이 이어진다. 특히 `api.js`는 `params.offline`을 별도로 읽고, `ParamPanel`은 그 키를 건드리지 않아 module_5와의 분리 계약이 유지된다.
- `PASS`: 백엔드 파라미터 경계(`n=1..10`, `draws=100..500`)와 UI 제약이 일치한다.
- `WARN`: 상위 앱(`web/js/app.js`)의 submit 버튼 이벤트도 `unmount()`에서 제거되지 않는다. `ParamPanel`의 미정리 구독과 결합되면 재마운트 환경에서 중복 동작 위험이 커진다.

### 5. 문서 업데이트 누락
- `PASS`: 현재 작업 범위에서 요구된 설계 문서 반영은 누락되지 않았다.
- `PASS`: 이번 교차검증 결과는 본 문서로 별도 기록했다.

## 이슈
1. `medium` / `interface-lifecycle`
   - 위치: `web/js/components/ParamPanel.js:80-85`, `web/js/app.js:49-56`
   - 내용: `ParamPanel`의 store 구독과 상위 `submitButton` 이벤트가 정리되지 않아 컴포넌트 수명주기 계약이 닫혀 있지 않다.
   - 영향: 동일 루트 재마운트, 테스트 반복, 향후 부분 초기화/HMR에서 죽은 DOM 참조, 중복 요청, 누수 위험이 생긴다.
2. `medium` / `test-gap`
   - 위치: `tests/frontend/test_param_panel_contract.py:7-24`, `tests/frontend/test_smoke_render.py:45-59`
   - 내용: 테스트가 문자열/정적 자산 존재성 중심이라 실제 슬라이더 상호작용과 상태 동기화 회귀를 막지 못한다.
   - 영향: 리팩터링 내성은 낮고, 중요한 런타임 버그는 놓칠 수 있다.

## 실행 검증
- `pytest tests/frontend -q` 실행 결과: `5 passed`

## JSON 판정
```json
{"verdict":"WARN","issues":[{"severity":"medium","category":"interface-lifecycle","title":"ParamPanel 구독과 상위 submit 이벤트가 언마운트 시 정리되지 않음","location":"web/js/components/ParamPanel.js:80-85, web/js/app.js:49-56","impact":"재마운트·반복 테스트·향후 부분 초기화 환경에서 죽은 DOM 참조와 중복 요청이 누적될 수 있다.","recommendation":"컴포넌트 cleanup을 상위가 수거할 수 있게 하거나, mountApp이 모든 리스너와 구독 해제를 통합 관리하도록 정리한다."},{"severity":"medium","category":"test-gap","title":"슬라이더 계약 테스트가 실행 기반이 아니라 문자열 매칭 위주임","location":"tests/frontend/test_param_panel_contract.py:7-24, tests/frontend/test_smoke_render.py:45-59","impact":"DOM/이벤트/store 동기화 회귀를 충분히 검출하지 못한다.","recommendation":"DOM 생성 결과, input/change 이벤트, 외부 store 갱신, loading disabled 토글을 직접 검증하는 실행 기반 테스트를 추가한다."}],"summary":"frontend_dev_module_4는 범위 문서와 핵심 구현 계약이 대체로 일치하고 프론트 테스트 5건도 통과한다. 그러나 ParamPanel과 상위 앱의 수명주기 정리가 닫혀 있지 않고, 테스트가 런타임 상호작용을 충분히 덮지 못해 전체 정합성 판정은 WARN이다."}
```
