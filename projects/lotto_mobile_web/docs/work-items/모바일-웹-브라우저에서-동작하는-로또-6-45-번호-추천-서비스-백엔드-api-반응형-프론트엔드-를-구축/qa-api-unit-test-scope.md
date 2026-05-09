# API 단위 테스트 스위트 범위 정의

## 메타데이터
- task_id: `qa_engineer_module_6_scope_1`
- owner_role: `qa_engineer`
- status: `defined`
- last_updated: `2026-04-18T01:26:22`

## 목표
- 백엔드 API 계약이 깨졌는지 빠르게 검출하는 pytest 기반 API 단위 테스트 스위트의 범위를 고정한다.
- 구현 단계에서 추가 논의 없이 테스트 파일 구조, fixture 경계, 검증 책임을 바로 적용할 수 있게 인터페이스를 명시한다.

## 범위
### 포함
- `GET /api/recommend` 엔드포인트의 성공 응답 계약 검증
- `n`, `draws`, `offline` 질의 파라미터의 입력 검증과 오류 응답 검증
- 응답 JSON의 필수 필드와 최소 구조 검증
- FastAPI 앱을 프로세스 외부 네트워크 없이 호출하는 테스트 인터페이스 정의
- 테스트용 예측 엔진 대체 지점과 fixture 책임 정의

### 제외
- 실제 브라우저 렌더링 검증
- 오프라인 캐시 저장소 자체의 영속성 검증
- 외부 네트워크, 실데이터 수집, E2E 흐름 검증
- 성능 벤치마크, 부하 테스트, 시각 회귀 테스트

## 테스트 대상 인터페이스
### 런타임 인터페이스
- 대상 API: `GET /api/recommend`
- 요청 파라미터:
  - `n`: 정수, 허용 범위 `1..10`
  - `draws`: 정수, 허용 범위 `100..500`
  - `offline`: 불리언, 선택값
- 기대 응답 필드:
  - `generated_at`
  - `source`
  - `draws_used`
  - `combos`
- `combos[*]` 기대 필드:
  - `numbers`
  - `score`
  - `odd_even_ratio`
  - `section_distribution`

### 테스트 코드 인터페이스
- 테스트 루트: `tests/api/`
- 대표 파일:
  - `tests/api/test_recommend_endpoint.py`
  - `tests/api/conftest.py`
- 공용 fixture:
  - `app_client`: FastAPI 앱을 감싼 `TestClient`
  - `predictor_stub`: 예측 결과를 결정론적으로 돌려주는 대체 객체 또는 monkeypatch
  - `valid_query`: 정상 기본 질의값 묶음
- 실행 명령:
  - `pytest tests/api`
  - `pytest tests/api/test_recommend_endpoint.py -k recommend`

## 테스트 케이스 범위
### 성공 케이스
- 기본 요청으로 `200 OK`와 JSON 본문을 반환한다.
- `n` 값에 맞는 조합 개수만 반환한다.
- 각 조합의 `numbers`가 6개 정수 목록으로 직렬화된다.
- `source`와 `draws_used`가 요청/실행 결과와 일관된다.

### 입력 검증 케이스
- `n < 1` 이면 `422`를 반환한다.
- `n > 10` 이면 `422`를 반환한다.
- `draws < 100` 이면 `422`를 반환한다.
- `draws > 500` 이면 `422`를 반환한다.
- 정수가 아닌 `n`, `draws` 입력은 `422`를 반환한다.
- 불리언으로 해석할 수 없는 `offline` 입력은 `422`를 반환한다.

### 오류 처리 케이스
- 내부 예측 의존성이 예외를 던질 때 API가 비정상 크래시 대신 합의된 오류 응답을 반환하는지 검증한다.
- 빈 조합 목록이나 구조 불일치가 발생하면 테스트가 계약 위반으로 실패하도록 한다.

## 의존성
- 선행 모듈:
  - `backend_dev_module_1_scope_1`: 엔드포인트 계약과 파라미터 범위 확정
  - `backend_dev_module_1_build_2`: FastAPI 앱과 `GET /api/recommend` 구현
- 라이브러리:
  - `pytest`
  - `fastapi`
  - `httpx` 또는 FastAPI `TestClient`
- 테스트 더블:
  - 예측 엔진 import 경로를 가로채거나 주입할 수 있는 monkeypatch 지점

## 산출물
- `tests/api/test_recommend_endpoint.py`: 엔드포인트 계약 테스트
- `tests/api/conftest.py`: 공용 fixture와 stub 정의
- 필요 시 `pytest.ini` 또는 기존 테스트 설정 파일: 테스트 경로/마커 보강

## 구현 순서
1. 백엔드 구현에서 고정한 `GET /api/recommend` 요청/응답 스키마를 QA 기준 입력으로 동결한다.
2. `tests/api/conftest.py`에 `app_client`, `predictor_stub`, `valid_query` fixture를 만든다.
3. 성공 응답 계약 테스트부터 작성해 기본 응답 스키마를 고정한다.
4. `n`, `draws`, `offline` 입력 검증 케이스를 경계값 중심으로 추가한다.
5. 내부 의존성 예외를 주입해 오류 처리 케이스를 추가한다.
6. `pytest tests/api` 기준으로 스위트 진입점을 검증하고 다음 verify 단계로 넘긴다.

## 완료 기준
- API 단위 테스트 스위트의 포함/제외 범위가 문서에 명시된다.
- 테스트 대상 엔드포인트, fixture, 실행 명령이 명시된다.
- 선행 의존성과 예상 산출물이 문서에 명시된다.
- 구현 단계에서 적용할 순서가 번호 목록으로 고정된다.
