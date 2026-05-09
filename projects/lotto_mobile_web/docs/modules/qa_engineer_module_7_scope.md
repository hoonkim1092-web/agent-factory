# 프론트엔드 렌더링 smoke 테스트 — 범위와 인터페이스 정의

## 메타데이터
- task_id: `qa_engineer_module_7_scope_1`
- module_id: `qa_engineer_module_7`
- owner_role: qa_engineer
- phase: scope
- last_updated: 2026-04-18
- status: draft
- 문서 언어: 한국어 (OS: `ko-KR`)

## 목적
모바일 웹 로또 추천 서비스의 프론트엔드 셸이 최소 렌더링 계약을 깨지 않는지 빠르게 검출하는 smoke 테스트 범위를 정의한다.
본 문서는 시각적 회귀 전수검사나 상호작용 세부 검증이 아니라, `web/index.html` 진입점과 기본 컴포넌트 export 가 build 단계 이후에도 안정적으로 존재하는지 확인하는 QA 경계를 고정한다.

## 범위 (In Scope)
1. 정적 엔트리 렌더 확인
   - `web/index.html` 파일 존재
   - 필수 메타 태그 존재: `viewport`, 문서 제목, 루트 마운트 노드
   - `base.css`, `layout.css`, `app.js` 연결 여부 확인
2. 기본 DOM 셸 구조 확인
   - 헤더, 파라미터 영역, 결과 영역, CTA 영역의 최소 DOM 슬롯 존재
   - 초기 렌더 시 치명적 예외 없이 빈 상태 또는 기본 상태가 표시됨
3. JS 모듈 공개 API 확인
   - `web/js/state.js`: `createStore`, `initialState`
   - `web/js/api.js`: `fetchRecommendation`, `OfflineError`
   - `web/js/components/CardList.js`, `ParamPanel.js`, `OfflineBanner.js`: 지정 export 존재
4. 최소 상호작용 smoke 확인
   - 추천 실행 트리거 버튼 또는 submit 이벤트가 DOM에 연결됨
   - API 호출은 실제 네트워크 대신 stub 으로 대체 가능해야 함
   - 성공/오류 중 하나의 대표 상태 전이가 렌더 계층에서 처리됨
5. 모바일 기준 레이아웃 smoke 확인
   - 360px 폭 기준에서 가로 스크롤이 발생하지 않음
   - 주요 인터랙티브 요소가 viewport 내부에 표시됨

## 범위 밖 (Out of Scope)
- 픽셀 단위 시각 회귀 비교
- 브라우저별 세부 스타일 완전 일치 검증
- `frontend_dev_module_3` 카드 내부 시각화 세부 내용 검증
- `frontend_dev_module_4` 슬라이더 접근성/키보드 조작 세부 검증
- `frontend_dev_module_5` 캐시 TTL, stale 정책 검증
- 실제 백엔드 서버와의 end-to-end 통합 검증
- Lighthouse 점수, 성능 측정, SEO 측정

## 인터페이스 정의

### 1) 테스트 파일 레이아웃
```text
tests/frontend/
├── test_smoke_render.py          # 프론트엔드 렌더 smoke 엔트리
├── conftest.py                   # HTML/모듈 로더, stub fixture
└── fixtures/
    └── recommendation_success.json
```

### 2) 테스트 실행 인터페이스
- 기본 실행 명령: `pytest tests/frontend/test_smoke_render.py`
- 전체 QA 실행에 포함될 명령: `pytest`
- 테스트 러너: Python `pytest`
- 브라우저 자동화 도구는 scope 단계에서 도입하지 않는다.
- build 단계에서는 정적 HTML 파싱 + JS 모듈 계약 확인 중심으로 구현한다.

### 3) fixture 및 helper 계약
| 항목 | 형식 | 설명 |
|------|------|------|
| `frontend_root` | pytest fixture | `web/` 정적 산출물 루트 경로 제공 |
| `index_html` | pytest fixture | `web/index.html` 내용을 로드 |
| `recommendation_stub` | fixture JSON | `RecommendationResponse` 성공 샘플 |
| `module_exports(name)` | helper | JS 파일 텍스트에서 공개 export 존재 여부 확인 |
| `render_contract` | 상수 dict | 필수 셀렉터/자산 목록 단일 정의 |

### 4) 검증 대상 계약
| 대상 | 검증 포인트 | 실패 의미 |
|------|-------------|-----------|
| `web/index.html` | 루트 노드, 자산 링크, 기본 영역 슬롯 | 셸 진입점 손상 |
| `web/styles/base.css` | 파일 존재 | 기본 스타일 자산 누락 |
| `web/styles/layout.css` | 파일 존재 | 레이아웃 자산 누락 |
| `web/js/app.js` | 파일 존재 및 엔트리 연결 | 부트스트랩 손상 |
| `web/js/state.js` | `createStore`, `initialState` export | 상태 계약 파손 |
| `web/js/api.js` | `fetchRecommendation`, `OfflineError` export | API 어댑터 계약 파손 |
| `web/js/components/*.js` | 컴포넌트 export 존재 | 하위 모듈 결합점 파손 |

### 5) smoke 테스트 케이스 묶음
1. 산출물 존재성
   - `web/` 하위 핵심 파일 7종 존재
2. HTML 셸 계약
   - 루트 마운트 노드와 주요 영역 셀렉터 존재
   - CSS/JS 자산 링크가 문서에 선언됨
3. JS 모듈 계약
   - 필수 export 이름이 각 파일에 선언됨
4. 대표 렌더 상태
   - 초기 상태 렌더를 위한 플레이스홀더 또는 빈 상태 노드 존재
   - 오류 또는 오프라인 상태 배너 슬롯 존재
5. 모바일 최소 제약
   - `viewport` 메타가 설정됨
   - 레이아웃 컨테이너가 모바일 우선 클래스/속성을 가짐

## 의존성
- 상류(upstream):
  - `frontend_dev_module_2_scope_1` 문서가 정의한 `web/` 구조와 공개 API
  - `frontend_dev_module_2_build_2` 산출물 구현
  - 선택 의존: `frontend_dev_module_3/4/5`가 실제 구현을 넣더라도, smoke 테스트는 placeholder 단계와 호환되어야 함
- 횡단(cross-cutting):
  - `docs/architecture.md`의 프론트엔드 셸 구조와 QA 범위 설명
  - `docs/work-items/.../feature-spec.md`의 "pytest 실행 시 프론트 smoke 테스트 통과" 요구
- 하류(downstream):
  - `qa_engineer_module_7_build_2`가 본 문서의 테스트 파일 구조와 검증 포인트를 그대로 구현
  - `qa_engineer_module_7_verify_3`가 본 문서를 기준으로 실행 결과와 잔여 리스크를 점검

## 산출물 (Deliverables)
- `docs/modules/qa_engineer_module_7_scope.md` — 본 범위 문서
- `tests/frontend/test_smoke_render.py` — build 단계 구현 대상
- `tests/frontend/conftest.py` — build 단계 fixture 구현 대상
- `tests/frontend/fixtures/recommendation_success.json` — build 단계 샘플 응답
- `docs/architecture.md`, `docs/change_history.md` — 계약 문서 갱신

## 구현 순서 (고정)
1. `frontend_dev_module_2_scope.md` 기준으로 smoke 대상 파일/공개 API 목록 확정
2. `tests/frontend/` 디렉터리 및 fixture 자산 구조 생성
3. 핵심 파일 존재성 테스트 구현
4. `index.html` 메타 태그/DOM 슬롯 계약 테스트 구현
5. JS 모듈 export 계약 테스트 구현
6. stub 응답 fixture 추가 및 대표 상태 smoke 테스트 구현
7. `pytest tests/frontend/test_smoke_render.py` 단독 실행 기준 안정화
8. 전체 `pytest` 실행에 포함되도록 회귀 확인
9. verify 단계로 handoff

## 수용 기준 (이 문서 단위)
- 프론트엔드 렌더링 smoke 테스트의 검증 대상, 비대상, 실행 인터페이스가 문서화되어 있다.
- 상류 의존성(`frontend_dev_module_2`)과 build 단계 산출물이 명시되어 있다.
- build 담당자가 재해석 없이 테스트 파일 구조와 구현 순서를 그대로 사용할 수 있다.

## 리스크와 완화
- (R1) 브라우저 런타임 없이 JS 모듈 시맨틱 검증이 제한됨 → scope 단계에서는 export 존재성 계약으로 제한하고, 실제 DOM 실행은 verify 단계 잔여 리스크로 명시한다.
- (R2) 프론트엔드 셸 마크업이 build 단계에서 바뀌면 테스트가 과도하게 깨질 수 있음 → 필수 슬롯만 검증하고 세부 클래스명 결합은 최소화한다.
- (R3) 하위 모듈 구현 전 placeholder 상태와 실제 구현 상태가 다를 수 있음 → placeholder와 실제 구현 모두 통과하는 존재성 중심 assertions 로 고정한다.

## 참고
- `docs/modules/frontend_dev_module_2_scope.md`
- `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/feature-spec.md`
- `docs/work-items/모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축/implementation-tasks.md`
