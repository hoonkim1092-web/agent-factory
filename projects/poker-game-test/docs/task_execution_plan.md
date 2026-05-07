# Task Execution Plan

## Overview
- project_goal: WSOP 텍사스 홀덤 공식 룰 기반의 최대 8인 실시간 네트워크 포커 게임을 WebSocket 서버-클라이언트 분리 구조로 구현한다.
- execution_strategy: parallel
- role_count: 4
- module_count: 9
- task_count: 27

## Evidence
- Local reference: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json -> { "original_request": "목표 : 8인 네트워크 플레이 포커게임 만들기\n\n최근 공신력 있는 세계 포커게임을 기반으로 규칙을 만들고, 초기 자산, 배팅룰, 배팅 금액 룰을 적용해\n게임 로직 판단은 서버에서 하고, 클라이언트는 뷰어 역할만 한다,\n클라이언트는 html5 개발하고, 앱웹 방식으로 모바일 피시 태블릿에서 작동하도록 개발한다.", "goal": "텍사스 홀덤 기반 8인 실시간 네트워크 포커 게임을 서버-클라이언트 분리 구조로...
- Local reference: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json -> constraints": [ "게임 판정(핸드 비교, 팟 계산, 턴 진행) 전부 서버 전담 — 클라이언트는 UI 입력 전송과 상태 렌더링만 수행", "클라이언트는 순수 HTML5/CSS3/Vanilla JS — 별도 앱 설치 없이 모바일·PC·태블릿 브라우저에서 동작", "최대 8명 동시 플레이, 최소 2명 이상 시 게임 시작 가능", "텍사스 홀덤 공식 룰 적용 — WSOP 표준 베팅 구조(프리플랍/플랍/턴/리버)", "초기 칩 고정 지급, 블라인드·베팅...
- Local reference: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json -> "플레이어: 칩 소진 → 서버: 해당 플레이어 게임 아웃, 사이드팟 계산 적용" ], "non_goals": [ "실제 현금 베팅 또는 결제 시스템 — 가상 칩만 사용", "AI 봇 플레이어 구현", "채팅 기능", "토너먼트·리그 구조 (단일 캐시 게임만)", "세븐카드 스터드·오마하 등 다른 포커 변형 게임", "계정 영구 저장·로그인 시스템 (세션 내 닉네임만)", "모바일 네이티브 앱 빌드 (웹앱만)" ], "architecture_style": "...
- Web reference: 포커 룰, 규칙, 용어정리 : 네이버 블로그 -> ​ ​ > 세븐카드 스터드 > > Seven-card stud poker 세븐카드 스터드 포커 ​ 각각의 플레이어가 7장의 카드를 받으며, 받은 카드들 중 4장을 공개하는 포커 게임이다. 이것이 대한민국에 수입되어 변형된 버전이 '세븐 포커'이다. 텍사스 홀덤이 유행하기 전에 세계에게 가장 널리 유행하던 포커 게임이었으며, 대한민국에서는 무늬별 서
- Web reference: HWAIN 이용안내 FAQ | 자주 묻는 질문 -> 트,라이브홀덤규칙,온라인홀덤게임룰,블랙잭게임,블랙잭게임룰,블랙잭게임공짜,블랙잭게임다운로드,블랙잭게임방법,블랙잭게임하는법,라이브홀덤,플레이홀덤,인터넷라이브홀덤,텍사스홀덤규칙,홀덤포커,홀덤룰,우리카지노,다이사이,무료충전바둑이게임,바카라,온라인바둑이,바카라필승전략,룰렛,룰렛게임,바카라카지노,카지노바카라규칙,바카라카지노전략,카지노바카라확률,바카라카지노게임,카지노바
- Web reference: [PDF] 2022년 11월 8일, 화요일 -> • 카드게임방. 현재 32개 카운티에 있는 84개 카드게임방에서 특정 카드 게임(예: 포커)을 제공할 수 있습니다. 카드게임방은 주 및 지방 정부에 수수료와 세금을 지불합니다. 예를 들어, 카드게임방은 규제 비용으로 일반적으로 매년 (연간) 약 $2,400만을 주 정부에 지불합니다. 또한, 카드게임방은 해당 카드게임방이 있는 도시에 매년 약 $1억을 지불합

## Stage Order
1. 범위와 계약 정의
   objective: 기능 경계를 모듈 단위로 나누고 역할별 인터페이스를 고정한다.
   exit_criteria: 모든 작업이 owner_role과 depends_on을 가진다., 핵심 산출물이 모듈별로 정리된다.
2. 기능 슬라이스 구현
   objective: 독립 배포 가능한 작은 기능 단위로 구현을 진행한다.
   exit_criteria: 각 모듈이 최소 1개의 구현 작업을 가진다., 기능 슬라이스가 파일/산출물 기준으로 분리된다.
3. 통합과 핸드오프
   objective: 역할 간 의존성을 정리하고 결과를 다음 작업자가 이어받을 수 있게 만든다.
   exit_criteria: 의존 작업이 정리되고 handoff 기준이 명시된다., 검증 전에 필요한 연결 작업이 완료된다.
4. 검증과 마감
   objective: 기능 동작, 회귀 리스크, 남은 이슈를 명시적으로 검증한다.
   exit_criteria: 검증 작업이 존재한다., 잔여 리스크와 후속 작업이 기록된다.

## Module Breakdown By Role
### 텍사스 홀덤 룰 엔진
- owner_role: Frontend Dev
- objective: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)을(를) 구현한다.
- feature_slices: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)을(를) 구현한다.
- deliverables: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 텍사스 홀덤 룰 엔진 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 텍사스 홀덤 룰 엔진 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 텍사스 홀덤 룰 엔진의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 텍사스 홀덤 룰 엔진 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 8인 실시간 게임 서버
- owner_role: Frontend Dev
- objective: 8인 실시간 게임 서버 (WebSocket 기반)을(를) 구현한다.
- feature_slices: 8인 실시간 게임 서버 (WebSocket 기반)을(를) 구현한다.
- deliverables: 8인 실시간 게임 서버 (WebSocket 기반)
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 8인 실시간 게임 서버 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 8인 실시간 게임 서버 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 8인 실시간 게임 서버 (WebSocket 기반)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 8인 실시간 게임 서버의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 8인 실시간 게임 서버 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 반응형 HTML5 게임 클라이언트
- owner_role: Frontend Dev
- objective: 반응형 HTML5 게임 클라이언트 (모바일·PC·태블릿)을(를) 구현한다.
- feature_slices: 반응형 HTML5 게임 클라이언트 (모바일·PC·태블릿)을(를) 구현한다.
- deliverables: 반응형 HTML5 게임 클라이언트 (모바일·PC·태블릿)
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 반응형 HTML5 게임 클라이언트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 반응형 HTML5 게임 클라이언트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 반응형 HTML5 게임 클라이언트 (모바일·PC·태블릿)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 반응형 HTML5 게임 클라이언트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 반응형 HTML5 게임 클라이언트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 방 생성·입장·대기 로비 UI
- owner_role: Frontend Dev
- objective: 방 생성·입장·대기 로비 UI을(를) 구현한다.
- feature_slices: 방 생성·입장·대기 로비 UI을(를) 구현한다.
- deliverables: 방 생성·입장·대기 로비 UI
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 방 생성·입장·대기 로비 UI 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 방 생성·입장·대기 로비 UI 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 방 생성·입장·대기 로비 UI을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 방 생성·입장·대기 로비 UI의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 방 생성·입장·대기 로비 UI 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 게임 진행 화면
- owner_role: Frontend Dev
- objective: 게임 진행 화면 (커뮤니티카드·홀카드·베팅 액션 표시)을(를) 구현한다.
- feature_slices: 게임 진행 화면 (커뮤니티카드·홀카드·베팅 액션 표시)을(를) 구현한다.
- deliverables: 게임 진행 화면 (커뮤니티카드·홀카드·베팅 액션 표시)
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 게임 진행 화면 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 게임 진행 화면 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 게임 진행 화면 (커뮤니티카드·홀카드·베팅 액션 표시)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 게임 진행 화면의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 게임 진행 화면 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 베팅 액션 UI
- owner_role: Frontend Dev
- objective: 베팅 액션 UI (콜·레이즈·폴드·체크·올인)을(를) 구현한다.
- feature_slices: 베팅 액션 UI (콜·레이즈·폴드·체크·올인)을(를) 구현한다.
- deliverables: 베팅 액션 UI (콜·레이즈·폴드·체크·올인)
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 베팅 액션 UI 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 베팅 액션 UI 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 베팅 액션 UI (콜·레이즈·폴드·체크·올인)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 베팅 액션 UI의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 베팅 액션 UI 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### Backend Dev 구현
- owner_role: Backend Dev
- objective: 서버, 데이터, 외부 연동 레이어를 구현한다.
- feature_slices: 서버, 데이터, 외부 연동 레이어를 구현한다.
- deliverables: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)
- depends_on: -
- tasks:
  - [scope] Backend Dev: Backend Dev 구현 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: Backend Dev 구현 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: 서버, 데이터, 외부 연동 레이어를 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: Backend Dev 구현의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: Backend Dev 구현 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### Game Logic Dev 구현
- owner_role: Game Logic Dev
- objective: 핵심 규칙과 상태 전이를 구현한다.
- feature_slices: 핵심 규칙과 상태 전이를 구현한다.
- deliverables: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)
- depends_on: -
- tasks:
  - [scope] Game Logic Dev: Game Logic Dev 구현 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: Game Logic Dev 구현 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Game Logic Dev: 핵심 규칙과 상태 전이를 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: Game Logic Dev 구현의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Game Logic Dev: Game Logic Dev 구현 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### QA Engineer 검증
- owner_role: QA Engineer
- objective: 핵심 플로우와 회귀 시나리오를 검증한다.
- feature_slices: 핵심 플로우와 회귀 시나리오를 검증한다.
- deliverables: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)
- depends_on: -
- tasks:
  - [scope] QA Engineer: QA Engineer 검증 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: QA Engineer 검증 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: 핵심 플로우와 회귀 시나리오를 검증한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: QA Engineer 검증의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: QA Engineer 검증 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

## Execution Rules
- Each task should finish as a small, independent slice of work.
- Resolve dependencies using `depends_on` before parallelizing the next step.
- Define scope and file boundaries before implementation begins.
- Keep verification work as separate tasks instead of burying it inside build tasks.

## Handoff Rules
- Agents should communicate using task_id-scoped handoff, blocker, decision_request, decision_response, review_request, review_result, and result messages.
- Include relevant file paths and acceptance criteria in each handoff or review request.
- Every blocker should state what is blocked, why, and what decision or input is required.
- Each receiving agent should check the inbox and acknowledge required messages before starting work.
