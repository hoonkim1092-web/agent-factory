# 조합 카드 시각화 컴포넌트 검증 및 handoff

## 메타데이터
- task_id: `frontend_dev_module_3_verify_3`
- module_id: `frontend_dev_module_3`
- owner_role: `frontend_dev`
- phase: `verify`
- 작성 시각: `2026-04-18T19:10:00+09:00`
- 문서 언어: 한국어 (OS: `ko-KR`)

## 검증 결과 요약
- 판정: **통과(PASS), 후속 확인 항목 있음**
- 근거:
  - `renderCardList(el, combos)` 공개 API 시그니처가 module_2 계약과 동일하게 유지된다.
  - 조합 카드 구현이 scope 문서의 핵심 범위(번호 공, 점수 텍스트/게이지, 홀짝 배지, 구간 분포, 접힘/펼침, 빈 상태 방어)를 모두 반영한다.
  - 자동화 확인 결과 `pytest tests/frontend -q` 실행 시 `5 passed in 0.03s` 로 회귀가 없었다.
  - 선행 코드리뷰/교차검증에서 치명적 결함은 없고, 잔여 사항은 LOW 또는 INFO 수준으로 정리돼 있다.

## 실행한 검증 작업
- 구현 대조:
  - `web/js/components/CardList.js`
  - `web/styles/cards.css`
  - `web/index.html`
  - `docs/modules/frontend_dev_module_3_scope.md`
  - `docs/code_review/frontend_dev_module_3_code_review.md`
  - `docs/code_review/frontend_dev_module_3_cross_validation.md`
- 확인 항목:
  - `CardList.js` 가 카드 리스트를 `<button class="combo-card">` 기반 토글 UI로 렌더하는지 확인
  - 번호 공 색상 버킷(`b1`~`b5`)과 점수/분포 방어 로직이 scope 정의와 일치하는지 확인
  - `cards.css` 가 카드 전용 스타일만 추가하고 기존 `base.css`/`layout.css` 를 침범하지 않는지 확인
  - `index.html` 의 CSS 링크 순서가 `base → layout → cards` 인지 확인
  - 프런트 smoke 회귀 테스트 통과 여부 확인

## 검증 상세
- 구현 정합:
  - `renderCardList` 는 `HTMLElement`/배열 여부를 먼저 검사하고, 빈 배열이면 `"추천 결과가 없습니다."` 문구를 유지한다.
  - 카드 본문은 번호 공 목록, 점수 텍스트, 점수 게이지, 홀짝 비율 배지, 5칸 분포 히스토그램으로 구성돼 scope와 일치한다.
  - 점수는 `formatScore()` 와 `clamp01()` 로 방어되고, 분포는 길이 5 기준 패딩/절삭으로 렌더 안정성을 확보한다.
- 접근성/상호작용:
  - 카드 토글은 `aria-expanded`, `aria-controls`, `aria-labelledby`, `hidden` 으로 상태를 동기화한다.
  - 클릭과 `Enter`/`Space` 키로 상세 영역을 열고 닫는다.
  - `prefers-reduced-motion: reduce` 대응이 `cards.css` 에 포함돼 있다.
- 회귀 확인:
  - 명령: `pytest tests/frontend -q`
  - 결과: `5 passed in 0.03s`
  - 해석: 현재 프런트 smoke 계약 범위에서는 파일, 엔트리, 셸 구조, export 계약 회귀가 없다.

## 잔여 리스크
- (LOW) HTML 유효성 경고 가능성:
  - 현재 구조는 `<button>` 내부에 `<ul>`/`<ol>` 을 포함한다.
  - 브라우저 동작에는 문제가 없지만, 이후 HTML lint/axe 규칙을 강화하면 경고가 발생할 수 있다.
- (LOW) 키보드 토글 처리 중복 여지:
  - `keydown` 에서 `Enter`/`Space` 를 직접 처리한다.
  - 모던 브라우저 기준 `preventDefault()` 로 안전하지만, 향후 입력 이벤트 정책을 바꾸면 재확인이 필요하다.
- (INFO) 수동 뷰포트 검증 미수행:
  - iPhone SE(375), Pixel(412) 실 브라우저에서 가로 스크롤/터치 감도/접힘 UI를 직접 확인하지는 못했다.
  - 현재 판정은 코드/문서/자동화 테스트 기준이다.
- (INFO) 카드 내부 상호작용 자동화 부족:
  - 펼침/접힘 토글, 색상 버킷 경계값, score 클램프, distribution 이상값은 전용 테스트가 아직 없다.

## 다음 작업자 handoff
- 우선순위 1:
  - 수동 브라우저 점검을 수행한다.
  - 최소 확인 항목은 iPhone SE(375)와 Pixel(412) 뷰포트에서 가로 스크롤 부재, 카드 터치 타깃, 펼침/접힘 동작, `prefers-reduced-motion` 반영 여부다.
- 우선순위 2:
  - 카드 상호작용 전용 테스트를 추가할지 결정한다.
  - 특히 `aria-expanded` 토글, `combo-card__ball--b1~b5` 경계값, `score` 클램프, `section_distribution` 패딩/절삭이 후보이다.
- 우선순위 3:
  - 향후 접근성/lint 규칙을 도입하면 카드 루트 구조를 재검토한다.
  - 필요하면 토글 제어를 카드 외부로 분리하거나 `div[role="button"]` 대안을 검토한다.
- 우선순위 4:
  - `frontend_dev_module_5` 가 오프라인/캐시 경로를 붙일 때도 `renderCardList` 공개 API는 그대로 유지한다.
  - 이 컴포넌트는 store/network 상태를 직접 참조하지 않으므로, 데이터 주입 방식만 맞추면 재사용 가능하다.

## 참고 파일
- `web/js/components/CardList.js`
- `web/styles/cards.css`
- `web/index.html`
- `docs/modules/frontend_dev_module_3_scope.md`
- `docs/code_review/frontend_dev_module_3_code_review.md`
- `docs/code_review/frontend_dev_module_3_cross_validation.md`
- `tests/frontend/test_smoke_render.py`
