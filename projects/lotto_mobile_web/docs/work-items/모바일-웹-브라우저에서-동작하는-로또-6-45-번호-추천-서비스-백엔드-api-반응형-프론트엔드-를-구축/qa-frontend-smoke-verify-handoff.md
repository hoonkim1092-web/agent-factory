# 프론트엔드 렌더링 smoke 테스트 검증 및 handoff

## 메타데이터
- task_id: `qa_engineer_module_7_verify_3`
- owner_role: `qa_engineer`
- phase: `verify`
- 작성 시각: `2026-04-18T17:40:00+09:00`

## 검증 결과
- 결과: 경고 포함 통과
- 실행 명령:
  - `pytest tests/frontend/test_smoke_render.py -q`
- 실행 요약:
  - `4 passed in 0.02s`
- 확인한 범위:
  - `web/index.html`, `web/styles/*`, `web/js/*` 핵심 산출물 존재 여부
  - 모바일 셸 계약(`title`, `viewport`, CSS/JS 링크, 필수 DOM 슬롯) 선언 여부
  - `state/api/components` 모듈의 필수 export 존재 여부
  - 프런트엔드 fixture의 기본 추천 응답 구조(`combos`, `numbers`, `odd_even_ratio`, `section_distribution`) 존재 여부

## 판정 근거
- `tests/frontend/test_smoke_render.py`는 정적 엔트리, 자산, export 계약 검증에는 성공했다.
- 그러나 `docs/modules/qa_engineer_module_7_scope.md`가 정의한 수용 범위를 모두 충족했다고 보기는 어렵다.
- 교차검증 결과 `runs/run_1776443752_qa_engineer_cross_validator_af6b65/cross_validation_report.json` 기준 판정은 `WARN`이다.

## 확인한 구현 포인트
- `tests/frontend/conftest.py`의 `render_contract`는 smoke 대상 자산, 필수 셀렉터, 필수 export 이름을 단일 상수로 관리한다.
- `tests/frontend/test_smoke_render.py`는 실제 브라우저 실행 없이 HTML 문자열과 JS 소스 텍스트를 파싱해 계약을 확인한다.
- `tests/frontend/fixtures/recommendation_success.json`는 추천 성공 샘플을 제공하지만, 현재 `source` 값은 `offline`으로 고정되어 있다.

## 잔여 리스크
- scope 문서의 "최소 상호작용 smoke" 수용 기준이 미충족이다. 현재 테스트는 `submit` 이벤트 연결, stub fetcher 주입, `idle/loading/success|error|offline` 상태 전이를 렌더 계층에서 검증하지 않는다.
- scope 문서의 "모바일 기준 레이아웃 smoke" 수용 기준이 미충족이다. 현재는 `viewport` 메타만 확인하며, 360px 기준 가로 스크롤 부재나 주요 인터랙티브 요소의 viewport 내 배치를 보장하지 않는다.
- 프런트엔드 fixture 계약이 상위 문서와 드리프트되어 있다. `tests/frontend/fixtures/recommendation_success.json`는 `source=offline`과 최소 필드만 사용하지만, 아키텍처 문서는 폴백 시 `source=cache`, `status=degraded-success` 및 추가 메타 필드를 기대한다.

## 다음 작업자 handoff
- 우선순위 1: smoke 테스트를 정적 문자열 검사 수준에서 한 단계 올려 `mountApp()` 또는 동등한 엔트리 호출 기준의 대표 상태 전이 검증을 추가한다.
- 우선순위 2: fixture와 프런트 타입/테스트 기대값을 백엔드 계약에 맞춘다. 최소한 `source`, `status`, 폴백 메타 필드는 아키텍처 문서와 동일한 형태로 정렬해야 한다.
- 우선순위 3: 모바일 레이아웃 smoke를 보강한다. 브라우저 자동화 도입 전이라도 모바일 우선 컨테이너 속성, 주요 인터랙티브 요소 배치, 가로 overflow 방지와 연결되는 최소 assertion이 필요하다.
- 참고 파일:
  - `tests/frontend/test_smoke_render.py`
  - `tests/frontend/conftest.py`
  - `tests/frontend/fixtures/recommendation_success.json`
  - `docs/modules/qa_engineer_module_7_scope.md`
  - `runs/run_1776443752_qa_engineer_cross_validator_af6b65/cross_validation_report.json`
