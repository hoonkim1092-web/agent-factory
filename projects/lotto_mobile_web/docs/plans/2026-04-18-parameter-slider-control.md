# 파라미터 슬라이더 컨트롤 build 설계

## 메타데이터
- task_id: `frontend_dev_module_4_build_2`
- module_id: `frontend_dev_module_4`
- owner_role: frontend_dev
- phase: build
- last_updated: 2026-04-18

## 설계 의도
- `renderParamPanel(el, store)` 공개 API는 유지하고, 내부 구현만 두 개의 `<input type="range">` 기반 파라미터 슬라이더로 완성한다.
- 슬라이더 범위는 백엔드 계약과 동일하게 `n=1..10`, `draws=100..500`으로 고정한다.
- 드래그 중 포커스가 끊기지 않도록 DOM 재생성 대신 1회 마운트 후 속성만 동기화한다.

## 영향 범위
- 수정 대상
  - `web/js/components/ParamPanel.js`
  - `web/styles/sliders.css`
  - `web/index.html`
  - `tests/frontend/test_param_panel_contract.py`
  - `docs/architecture.md`
  - `docs/change_history.md`
- 비침범
  - `web/js/app.js`
  - `web/js/state.js`
  - `web/js/api.js`
  - `web/js/components/CardList.js`
  - `web/js/components/OfflineBanner.js`

## 구현 슬라이스
1. 셸 자산 정렬
   - `sliders.css` 링크가 `base → layout → cards → sliders` 순서로 로드되는지 유지한다.
2. 슬라이더 DOM 계약
   - `n`, `draws` 각각에 대해 label/input/output 구조를 유지한다.
3. 상태 동기화
   - 사용자 입력은 `store.setState({ params: { [name]: value } })`로 부분 갱신한다.
   - 외부 상태 변화는 `value`, `aria-valuetext`, `output`, `disabled`만 갱신한다.
4. 회귀 검증
   - 프론트 테스트에 슬라이더 계약 검증을 추가한다.

## 대안 검토
- 대안 1: 커스텀 div 기반 슬라이더
  - 기각. 키보드/스크린리더/모바일 브라우저 기본 접근성을 직접 재구현해야 한다.
- 대안 2: 상태 변경마다 `innerHTML` 재생성
  - 기각. 드래그 중 포커스 손실과 불필요한 재렌더 위험이 크다.
- 대안 3: 외부 슬라이더 라이브러리 도입
  - 기각. 현재 셸은 프레임워크 미도입 원칙이며, 범위 대비 의존성 비용이 크다.
