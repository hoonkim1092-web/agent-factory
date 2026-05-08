# Product Designer Scope 설계 검토서

## 목적

`task_id=designer_module_7_scope_1`의 scope 단계에서 Product Designer의 구현 경계,
인터페이스 계약, 구현 순서를 고정한다.

## 설계 의도

- CLI 지뢰찾기 게임의 정보 구조, 화면 흐름, 사용자 인터페이스 텍스트를 명세로 고정한다.
- 코드 구현 없이 **명세 문서**만 산출한다. Frontend Dev가 이 명세를 참조하여 실제 Python 코드를 작성한다.
- 기능 요구사항(feature-spec.md)과 구현 명세(implementation-design.md) 사이의 간극을 메우는 역할에 집중한다.

## 영향 범위

### 포함

| 항목 | 설명 |
|------|------|
| 보드 렌더링 포맷 | 8×8 격자의 ASCII 레이아웃, 행/열 레이블 형식 |
| 셀 기호 사전 | 미공개(`?`), 깃발(`F`), 숫자(`1`~`8`), 빈 셀(`.`), 지뢰(`*`) 확정 |
| 화면 흐름 명세 | 게임 상태(시작·진행·승리·패배) 전이별 출력 순서와 구분 방식 |
| 사용자 대면 메시지 문자열 | 승리/패배/오류/안내 메시지 원문 (한국어) |
| 입력 프롬프트 포맷 | 매 턴 표시되는 입력 안내 문자열 |

### 제외

- Python 코드 구현 (Frontend Dev 담당)
- 게임 로직 및 상태 전이 규칙 (Game Logic Dev 담당)
- 단위 테스트 작성 (QA Engineer 담당)
- 서버/데이터/외부 연동 레이어 (Backend Dev 담당)
- GUI, 웹, curses 등 비CLI 인터페이스

## 인터페이스 계약

### 입력 (소비 문서)

| 문서 | 참조 항목 |
|------|-----------|
| `feature-spec.md` | FR-08(보드 렌더링), FR-09(입력 파싱), EX-01~EX-06(오류 처리), User Scenarios |
| `implementation-design.md` | Interface Impact, State And Data Model |

### 출력 (산출 문서)

| 산출물 | 위치 | 소비자 |
|--------|------|--------|
| UI/UX 명세서 | `docs/designer/ui-spec.md` | Frontend Dev |

### 계약 규칙

- `ui-spec.md`에 정의된 셀 기호, 메시지 문자열, 보드 포맷은 Frontend Dev가 그대로 구현한다.
- `ui-spec.md` 변경 시 Frontend Dev에게 즉시 통보하고 `change_history.md`에 기록한다.
- 메시지 문자열은 반드시 한국어로 작성한다 (OS: `ko-KR`).

## 의존성

### 선행 의존성

- `feature-spec.md` 완료 (FR-08, FR-09, User Scenarios 확정) — 이미 완료됨
- `implementation-design.md` 완료 (Interface Impact, State And Data Model 확정) — 이미 완료됨

### 후행 의존성

- Frontend Dev(`frontend_dev_module_1_build_2`)는 `ui-spec.md`를 참조하여 `minesweeper.py`의 출력 로직을 구현한다.
- QA Engineer는 `ui-spec.md`의 메시지 문자열을 기준으로 수락 기준을 검증한다.

## 산출물

| 번호 | 산출물 | 설명 |
|------|--------|------|
| 1 | 본 문서 (`docs/plans/2026-05-08-designer-scope.md`) | 범위/의존성/인터페이스/순서 정의 |
| 2 | `docs/designer/ui-spec.md` | 보드 포맷·셀 기호·메시지 문자열·화면 흐름 명세 |
| 3 | `docs/architecture.md` 갱신 | Designer 인터페이스 섹션 반영 |
| 4 | `docs/change_history.md` 이력 추가 | 설계 변경 기록 |

## 구현 순서 고정

1. **화면 흐름 정의** — 게임 시작·턴 반복·승리·패배 각 상태에서 터미널에 출력되는 내용 순서 확정
2. **보드 렌더링 포맷 명세** — 행/열 레이블 형식, 격자 구분 문자, 들여쓰기 규칙 확정
3. **셀 기호 사전 확정** — feature-spec.md FR-08 기준, 5가지 상태 기호 최종 확인
4. **메시지 문자열 목록 작성** — 승리/패배/오류/안내/프롬프트 전체 목록 작성 (한국어)
5. **입력 프롬프트 포맷 확정** — 매 턴 표시되는 안내 문자열 최종 확정

## 대안

### 대안 A: 설계 문서 없이 feature-spec.md 직접 사용

feature-spec.md의 FR-08~FR-09만으로 Frontend Dev가 자율 구현한다.

기각 이유: 메시지 문자열, 화면 흐름 구분자, 보드 들여쓰기 등 세부 사항이
feature-spec에 명시되지 않아 구현체마다 결과가 달라질 수 있다. 측정 기준 통일을 위해
별도 명세 문서가 필요하다.

### 대안 B(채택): 별도 ui-spec.md 명세 작성

설계 의도대로 Product Designer가 `ui-spec.md`를 작성하고 Frontend Dev가 이를 소비한다.

채택 이유:
- 메시지 문자열 일관성 보장 (수락 기준 AC-06, AC-07, AC-08과 직접 연결)
- 화면 흐름 구분 방식 명문화 → Frontend Dev 구현 판단 불확실성 제거
- QA Engineer가 독립적으로 기준을 검증할 수 있는 단일 문서 제공

## 교차검증 요청 상태

- 현재 실행 환경에 `send_mailbox_message` 도구가 노출되지 않아 자동 요청 전송은 보류 상태다.
- 도구가 제공되면 `review_request` 타입으로 즉시 교차검증을 요청한다.
