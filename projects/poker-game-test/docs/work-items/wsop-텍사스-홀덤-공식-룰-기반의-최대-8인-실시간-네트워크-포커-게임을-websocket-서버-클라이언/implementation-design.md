# Implementation Design

## Metadata

- work_item: wsop-텍사스-홀덤-공식-룰-기반의-최대-8인-실시간-네트워크-포커-게임을-websocket-서버-클라이언
- spec_type: feature
- source_spec: feature-spec.md
- status: draft
- last_updated: 2026-05-08T00:12:16

## Design Summary

WSOP 텍사스 홀덤 공식 룰 기반의 최대 8인 실시간 네트워크 포커 게임을 WebSocket 서버-클라이언트 분리 구조로 구현한다.

아키텍처: web_app

기술 스택: Python 3.11, websockets 12.x (asyncio 기반 WebSocket 서버), asyncio (게임 루프·턴 타임아웃 관리), HTML5 / CSS3 / Vanilla JavaScript ES2022, CSS Grid + Flexbox (반응형 레이아웃), JSON (클라이언트-서버 메시지 프로토콜)

실행 전략: parallel

## Planned Modules

### 텍사스 홀덤 룰 엔진
- owner: frontend_dev
- objective: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)을(를) 구현한다.
- deliverables: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)
- feature_slices: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)을(를) 구현한다.

### 8인 실시간 게임 서버
- owner: frontend_dev
- objective: 8인 실시간 게임 서버 (WebSocket 기반)을(를) 구현한다.
- deliverables: 8인 실시간 게임 서버 (WebSocket 기반)
- feature_slices: 8인 실시간 게임 서버 (WebSocket 기반)을(를) 구현한다.

### 반응형 HTML5 게임 클라이언트
- owner: frontend_dev
- objective: 반응형 HTML5 게임 클라이언트 (모바일·PC·태블릿)을(를) 구현한다.
- deliverables: 반응형 HTML5 게임 클라이언트 (모바일·PC·태블릿)
- feature_slices: 반응형 HTML5 게임 클라이언트 (모바일·PC·태블릿)을(를) 구현한다.

### 방 생성·입장·대기 로비 UI
- owner: frontend_dev
- objective: 방 생성·입장·대기 로비 UI을(를) 구현한다.
- deliverables: 방 생성·입장·대기 로비 UI
- feature_slices: 방 생성·입장·대기 로비 UI을(를) 구현한다.

### 게임 진행 화면
- owner: frontend_dev
- objective: 게임 진행 화면 (커뮤니티카드·홀카드·베팅 액션 표시)을(를) 구현한다.
- deliverables: 게임 진행 화면 (커뮤니티카드·홀카드·베팅 액션 표시)
- feature_slices: 게임 진행 화면 (커뮤니티카드·홀카드·베팅 액션 표시)을(를) 구현한다.

### 베팅 액션 UI
- owner: frontend_dev
- objective: 베팅 액션 UI (콜·레이즈·폴드·체크·올인)을(를) 구현한다.
- deliverables: 베팅 액션 UI (콜·레이즈·폴드·체크·올인)
- feature_slices: 베팅 액션 UI (콜·레이즈·폴드·체크·올인)을(를) 구현한다.

### Backend Dev 구현
- owner: backend_dev
- objective: 서버, 데이터, 외부 연동 레이어를 구현한다.
- deliverables: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)
- feature_slices: 서버, 데이터, 외부 연동 레이어를 구현한다.

### Game Logic Dev 구현
- owner: game_logic_dev
- objective: 핵심 규칙과 상태 전이를 구현한다.
- deliverables: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)
- feature_slices: 핵심 규칙과 상태 전이를 구현한다.

### QA Engineer 검증
- owner: qa_engineer
- objective: 핵심 플로우와 회귀 시나리오를 검증한다.
- deliverables: 텍사스 홀덤 룰 엔진 (핸드 평가·팟·사이드팟 계산·턴 진행)
- feature_slices: 핵심 플로우와 회귀 시나리오를 검증한다.


## Data Flow

- (시작) → **텍사스 홀덤 룰 엔진**
- (시작) → **8인 실시간 게임 서버**
- (시작) → **반응형 HTML5 게임 클라이언트**
- (시작) → **방 생성·입장·대기 로비 UI**
- (시작) → **게임 진행 화면**
- (시작) → **베팅 액션 UI**
- (시작) → **Backend Dev 구현**
- (시작) → **Game Logic Dev 구현**
- (시작) → **QA Engineer 검증**

## Event Sequence / Phase Flow

## 게임 상태 머신 명세 — 8인 네트워크 텍사스 홀덤

### 개요

- **기반 규칙**: WSOP 공식 텍사스 홀덤 토너먼트·캐시게임 혼합 규칙 (2024 WSOP Official Rules)
- **최대 인원**: 8명 (좌석 0–7)
- **초기 자산**: 플레이어당 칩 10,000 (캐시게임 기준 바이인)
- **블라인드**: Small Blind = 50, Big Blind = 100
- **베팅 단위**: No-Limit (최소 레이즈 = 직전 레이즈 금액 이상, 최대 = 보유 칩 전부)
- **아키텍처**: 서버 = 게임 로직 단독 실행 / 클라이언트 = 상태 수신 후 렌더링 전담

---

## 1. 게임 레벨 상태 목록

| 상태 ID | 한글 명칭 | 설명 |
|---|---|---|
| `WAITING` | 대기 | 플레이어 2명 이상 착석 대기. 게임 미시작. |
| `SETUP` | 핸드 준비 | 딜러 버튼 이동, 블라인드 징수, 덱 셔플 |
| `PREFLOP` | 프리플롭 | 홀 카드 2장 배분 후 첫 번째 베팅 라운드 |
| `FLOP` | 플롭 | 커뮤니티 카드 3장 공개 후 두 번째 베팅 라운드 |
| `TURN` | 턴 | 커뮤니티 카드 4번째 공개 후 세 번째 베팅 라운드 |
| `RIVER` | 리버 | 커뮤니티 카드 5번째 공개 후 네 번째 베팅 라운드 |
| `SHOWDOWN` | 쇼다운 | 핸드 공개 및 승자 결정 |
| `POT_DISTRIBUTION` | 팟 분배 | 팟·사이드팟 계산 및 칩 지급 |
| `GAME_OVER` | 게임 종료 | 한 명만 남거나

## Interface Impact

- (edit required)

## State And Data Model

- **GameRoom** (memory): room_id, players, deck, community_cards, pot, side_pots, current_phase, dealer_index, active_player_index, min_raise, big_blind, small_blind
- **Player** (memory): player_id, nickname, chips, hole_cards, current_bet, is_folded, is_all_in, is_connected
- **SidePot** (memory): amount, eligible_player_ids
- **GameAction** (memory): player_id, action_type, amount, timestamp

## Compatibility Considerations

- (edit required)

## Migration Requirement

- none

## Risks

- WebSocket 연결 단절 시 게임 상태 복구 로직 부재 → 플레이어 탈락 처리 정책 사전 확정 필요
- 8인 동시 베팅 타임아웃 미처리 → 턴 자동 폴드 로직 필수
- 사이드팟 다중 계산 버그 → 올인 플레이어 조합별 단위 테스트 필요
- 모바일 터치 UI에서 레이즈 금액 입력 UX 미흡 가능성
- 핸드 평가기 엣지케이스(동률·키커) 오판정 리스크
- 클라이언트는 순수 HTML5/CSS3/Vanilla JS — 별도 앱 설치 없이 모바일·PC·태블릿 브라우저에서 동작

## Alternatives Considered

- (edit required)

## Design Evidence

- Local reference: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json -> { "original_request": "목표 : 8인 네트워크 플레이 포커게임 만들기\n\n최근 공신력 있는 세계 포커게임을 기반으로 규칙을 만들고, 초기 자산, 배팅룰, 배팅 금액 룰을 적용해\n게임 로직 판단은 서버에서 하고, 클라이언트는 뷰어 역할만 한다,\n클라이언트는 html5 개발하고, 앱웹 방식으로 모바일 피시 태블릿에서 작동하도록 개발한다.", "goal": "텍사스 홀덤 기반 8인 실시간 네트워크 포커 게임을 서버-클라이언트 분리 구조로...
- Local reference: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json -> constraints": [ "게임 판정(핸드 비교, 팟 계산, 턴 진행) 전부 서버 전담 — 클라이언트는 UI 입력 전송과 상태 렌더링만 수행", "클라이언트는 순수 HTML5/CSS3/Vanilla JS — 별도 앱 설치 없이 모바일·PC·태블릿 브라우저에서 동작", "최대 8명 동시 플레이, 최소 2명 이상 시 게임 시작 가능", "텍사스 홀덤 공식 룰 적용 — WSOP 표준 베팅 구조(프리플랍/플랍/턴/리버)", "초기 칩 고정 지급, 블라인드·베팅...
- Local reference: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json -> "플레이어: 칩 소진 → 서버: 해당 플레이어 게임 아웃, 사이드팟 계산 적용" ], "non_goals": [ "실제 현금 베팅 또는 결제 시스템 — 가상 칩만 사용", "AI 봇 플레이어 구현", "채팅 기능", "토너먼트·리그 구조 (단일 캐시 게임만)", "세븐카드 스터드·오마하 등 다른 포커 변형 게임", "계정 영구 저장·로그인 시스템 (세션 내 닉네임만)", "모바일 네이티브 앱 빌드 (웹앱만)" ], "architecture_style": "...
- Web reference: 포커 룰, 규칙, 용어정리 : 네이버 블로그 -> ​ ​ > 세븐카드 스터드 > > Seven-card stud poker 세븐카드 스터드 포커 ​ 각각의 플레이어가 7장의 카드를 받으며, 받은 카드들 중 4장을 공개하는 포커 게임이다. 이것이 대한민국에 수입되어 변형된 버전이 '세븐 포커'이다. 텍사스 홀덤이 유행하기 전에 세계에게 가장 널리 유행하던 포커 게임이었으며, 대한민국에서는 무늬별 서
- Web reference: HWAIN 이용안내 FAQ | 자주 묻는 질문 -> 트,라이브홀덤규칙,온라인홀덤게임룰,블랙잭게임,블랙잭게임룰,블랙잭게임공짜,블랙잭게임다운로드,블랙잭게임방법,블랙잭게임하는법,라이브홀덤,플레이홀덤,인터넷라이브홀덤,텍사스홀덤규칙,홀덤포커,홀덤룰,우리카지노,다이사이,무료충전바둑이게임,바카라,온라인바둑이,바카라필승전략,룰렛,룰렛게임,바카라카지노,카지노바카라규칙,바카라카지노전략,카지노바카라확률,바카라카지노게임,카지노바
- Web reference: [PDF] 2022년 11월 8일, 화요일 -> • 카드게임방. 현재 32개 카운티에 있는 84개 카드게임방에서 특정 카드 게임(예: 포커)을 제공할 수 있습니다. 카드게임방은 주 및 지방 정부에 수수료와 세금을 지불합니다. 예를 들어, 카드게임방은 규제 비용으로 일반적으로 매년 (연간) 약 $2,400만을 주 정부에 지불합니다. 또한, 카드게임방은 해당 카드게임방이 있는 도시에 매년 약 $1억을 지불합

## References

- Local: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json | { "original_request": "목표 : 8인 네트워크 플레이 포커게임 만들기\n\n최근 공신력 있는 세계 포커게임을 기반으로 규칙을 만들고, 초기 자산, 배팅룰, 배팅 금액 룰을 적용해\n게임 로직 판단은 서버에서 하고, 클라이언트는 뷰어 역할만 한다,\n클라이언트는 html5 개발하고, 앱웹 방식으로 모...
- Local: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json | constraints": [ "게임 판정(핸드 비교, 팟 계산, 턴 진행) 전부 서버 전담 — 클라이언트는 UI 입력 전송과 상태 렌더링만 수행", "클라이언트는 순수 HTML5/CSS3/Vanilla JS — 별도 앱 설치 없이 모바일·PC·태블릿 브라우저에서 동작", "최대 8명 동시 플레이, 최소 2명 이상 시...
- Local: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json | "플레이어: 칩 소진 → 서버: 해당 플레이어 게임 아웃, 사이드팟 계산 적용" ], "non_goals": [ "실제 현금 베팅 또는 결제 시스템 — 가상 칩만 사용", "AI 봇 플레이어 구현", "채팅 기능", "토너먼트·리그 구조 (단일 캐시 게임만)", "세븐카드 스터드·오마하 등 다른 포커 변형 게임",...
- Local: projects/poker-game-test/docs/research/텍사스-홀덤-기반-8인-실시간-네트워크-포커-게임을-서버-클라이언트-분리-구조로-구현한다-project-brief.json | me_rule_engine_designer", "websocket_protocol_architect" ], "deliverables": [ "텍사스 홀덤 룰 엔진 (핸드 평가·팟 계산·턴 진행)", "8인 실시간 게임 서버 (WebSocket 기반)", "반응형 HTML5 게임 클라이언트 (모바일·PC·태블릿)",...
- Web: 포커 룰, 규칙, 용어정리 : 네이버 블로그 | ​ ​ > 세븐카드 스터드 > > Seven-card stud poker 세븐카드 스터드 포커 ​ 각각의 플레이어가 7장의 카드를 받으며, 받은 카드들 중 4장을 공개하는 포커 게임이다. 이것이 대한민국에 수입되어 변형된 버전이 '세븐 포커'이다. 텍사스 홀덤이 유행하기 전에 세계에게 가장 널리 유행하던 포커 게임이...
- Web: HWAIN 이용안내 FAQ | 자주 묻는 질문 | 트,라이브홀덤규칙,온라인홀덤게임룰,블랙잭게임,블랙잭게임룰,블랙잭게임공짜,블랙잭게임다운로드,블랙잭게임방법,블랙잭게임하는법,라이브홀덤,플레이홀덤,인터넷라이브홀덤,텍사스홀덤규칙,홀덤포커,홀덤룰,우리카지노,다이사이,무료충전바둑이게임,바카라,온라인바둑이,바카라필승전략,룰렛,룰렛게임,바카라카지노,카지노바카라규칙,바카라카지노전략...
- Web: [PDF] 2022년 11월 8일, 화요일 | • 카드게임방. 현재 32개 카운티에 있는 84개 카드게임방에서 특정 카드 게임(예: 포커)을 제공할 수 있습니다. 카드게임방은 주 및 지방 정부에 수수료와 세금을 지불합니다. 예를 들어, 카드게임방은 규제 비용으로 일반적으로 매년 (연간) 약 $2,400만을 주 정부에 지불합니다. 또한, 카드게임방은 해당 카드게임...
- Web: 침착맨 (r2521 판) - 나무위키 | ### 3.2. 트위치 전속계약 후(/edit/%EC%B9%A8%EC%B0%A9%EB%A7%A8?section=13) #### 3.2.1. 2015년(/edit/%EC%B9%A8%EC%B0%A9%EB%A7%A8?section=14) [...] #### 3.2.2. 2016년(/edit/%EC%B9%A8%EC%B0%A...

## Test Strategy

- Unit tests per module
- Integration tests for cross-module flows
