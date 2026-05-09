# API 단위 테스트 스위트 검증 및 handoff

## 메타데이터
- task_id: `qa_engineer_module_6_verify_3`
- owner_role: `qa_engineer`
- phase: `verify`
- 작성 시각: `2026-04-18T17:25:00+09:00`

## 검증 결과
- 결과: 통과
- 실행 명령:
  - `pytest tests/api/test_recommend_endpoint.py -q`
  - `pytest tests/api -q`
- 실행 요약:
  - `10 passed, 7 warnings` (`tests/api/test_recommend_endpoint.py -q`)
  - `10 passed, 7 warnings` (`tests/api -q`)
- 확인한 범위:
  - `GET /api/recommend` 성공 응답의 기본 계약(`generated_at`, `source`, `draws_used`, `combos`) 검증
  - `combos[*]` 구조(`numbers`, `score`, `odd_even_ratio`, `section_distribution`) 검증
  - `n`, `draws`, `offline` 질의 파라미터 경계값/형식 오류에 대한 `422` 검증
  - 요청한 `n` 값과 응답 조합 개수 일치 여부 검증
  - `offline=true` 요청 시 `source=offline` 응답 검증

## 확인한 구현 포인트
- `tests/api/conftest.py`는 `QA_API_APP_TARGET` 또는 기본 후보 경로(`app.main:app`, `main:app`, `src.main:app`, `backend.main:app`, `backend.app:app`)에서 앱을 탐색한다.
- 예측기 대체는 `QA_API_PREDICTOR_TARGET` 또는 `QA_API_PREDICTOR_DEPENDENCY` 환경 변수로 주입 가능하다.
- 테스트 클라이언트는 외부 네트워크 없이 ASGI in-process 호출만 사용한다.

## 잔여 리스크
- `starlette._exception_handler`에서 `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning 이 7건 발생한다. 현재 테스트 실패는 아니지만, Starlette/FastAPI 상위 버전 추적 시 경고가 오류로 승격될 수 있다.
- 현재 스위트는 계약과 입력 검증 중심이다. 내부 예측 의존성이 예외를 던질 때 `500` 또는 합의된 오류 스키마를 반환하는지에 대한 케이스는 이번 실행 범위에서 확인되지 않았다.
- `QA_API_APP_TARGET`, `QA_API_PREDICTOR_TARGET`, `QA_API_PREDICTOR_DEPENDENCY` 환경 변수 이름이 바뀌면 fixture 탐색이 바로 깨질 수 있다. CI 또는 후속 리팩터링에서 동일 이름 유지가 필요하다.

## 다음 작업자 handoff
- 우선순위 1: 백엔드 또는 QA 후속 작업자는 `422` deprecation warning 원인을 정리하고, status 상수 또는 예외 처리 경로가 새 Starlette 상수명과 호환되는지 확인한다.
- 우선순위 2: API 오류 처리 회귀를 막으려면 예측기 예외 주입 케이스를 추가해 `{error:{code,message,details}}` 스키마와 `500`/`503` 분기를 명시적으로 검증한다.
- 우선순위 3: CI에서 사용할 경우 기본 실행 명령은 `pytest tests/api -q`로 고정하고, 앱/의존성 경로를 바꾸는 리팩터링에서는 `tests/api/conftest.py` fixture 계약을 먼저 갱신한다.
- 참고 파일:
  - `tests/api/test_recommend_endpoint.py`
  - `tests/api/conftest.py`
  - `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/qa-api-unit-test-scope.md`
