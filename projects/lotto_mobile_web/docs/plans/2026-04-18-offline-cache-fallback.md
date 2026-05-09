# 오프라인 캐시 폴백 모듈 build 설계

## 메타데이터
- task_id: `frontend_dev_module_5_scope_1`
- module_id: `frontend_dev_module_5`
- owner_role: frontend_dev
- phase: scope
- last_updated: 2026-04-18

## 설계 의도
- `renderOfflineBanner(el, status)` 공개 API는 유지하고, `module_5`는 여기에 오프라인 안내 배너와 캐시 폴백 상태를 주입하는 역할만 맡는다.
- 캐시 폴백 책임은 UI와 저장소로 분리한다. `OfflineBanner.js` 는 렌더링과 상태 문구만 담당하고, `api.js` 가 던지는 `OfflineError` 이후의 캐시 읽기/쓰기 오케스트레이션은 `app.js` 에서 수행한다.
- 백엔드 `source/status` 계약 드리프트(`api|cache|offline`, `success|degraded-success`)가 해소되기 전까지 프론트는 `cache` 와 `offline` 둘 다 stale 데이터로 취급하는 방어적 인터페이스를 사용한다.

## 영향 범위
- 수정 대상
  - `docs/modules/frontend_dev_module_5_scope.md`
  - `docs/plans/2026-04-18-offline-cache-fallback.md`
  - `docs/architecture.md`
  - `docs/change_history.md`
- build 단계 수정 예정
  - `web/js/components/OfflineBanner.js`
  - `web/js/app.js`
  - `web/js/api.js`
  - `tests/frontend/`
- 비침범
  - `web/js/components/ParamPanel.js`
  - `web/js/components/CardList.js`
  - `web/styles/cards.css`
  - `web/styles/sliders.css`

## 구현 슬라이스
1. 캐시 데이터 계약 고정
   - `localStorage` 키, 저장 payload shape, TTL 판정 규칙, stale 판단 문구를 문서로 먼저 확정한다.
2. 앱 오케스트레이션 경계 고정
   - `app.js` 는 성공 응답 저장, `OfflineError` 시 캐시 복구, 상태 전이(`offline`)를 담당한다.
3. 배너 공개 API 유지
   - `renderOfflineBanner(el, status)` 시그니처는 유지하고, 실제 메시지/메타는 `app.js` 가 `data-*` 속성 또는 내부 DOM 계약으로 주입한다.
4. 회귀 검증 포인트 고정
   - 캐시 미존재/TTL 만료/`source=cache|offline` 표시/손상된 JSON 무시를 테스트 축으로 정의한다.

## 대안 검토
- 대안 1: `OfflineBanner.js` 에 캐시 읽기/쓰기와 네트워크 오류 처리까지 모두 몰아넣기
  - 기각. 렌더러가 저장소/상태 전이까지 가져가면 `app.js` 의 단일 상태 흐름이 깨지고 테스트 지점이 분산된다.
- 대안 2: `sessionStorage` 사용
  - 기각. 새 탭/새 세션에서 폴백이 사라져 "마지막 성공 응답 재사용" 요구를 충족하지 못한다.
- 대안 3: 서비스 워커/Cache Storage 도입
  - 기각. 현재 범위는 정적 SPA + `localStorage` 수준의 마지막 성공 응답 폴백이며, PWA/서비스 워커는 명시적으로 범위 밖이다.

## 검토 요청 상태
- 메일박스 프로토콜상 `send_mailbox_message(review_request)` 가 요구되지만, 현재 세션 도구에는 `read_mailbox`/`send_mailbox_message`/`ack_mailbox_message` 가 제공되지 않는다.
- 따라서 본 설계 문서를 리뷰 요청 근거로 먼저 남기고, 실제 교차검증 메시지 전송은 해당 도구가 제공되는 후속 실행 환경에서 수행해야 한다.
