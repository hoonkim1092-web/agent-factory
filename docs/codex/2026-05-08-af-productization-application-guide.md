치# AF 제품화 적용 가이드 (Manus 비교 분석 반영)

작성일: 2026-05-08  
대상: Agent Factory 개발환경 + 사용자 실행 흐름  
기준: 문서 품질이 아니라 **제품화 가능성(Productization Readiness)**

---

## 1단계. 판단 기준을 고정한다 (Productization Scorecard)

문서를 잘 썼는지보다, 실제 구현·검증·운영으로 이어지는지를 아래 5축으로 평가한다.

1. Config 일관성: 전역 설정값 충돌 0건
2. Protocol 완결성: 필수 이벤트 계약 100% 정의
3. Owner 정확성: 모듈-역할 매핑 오류 0건
4. 검증 가능성: 실행 가능한 acceptance/test 비율
5. Gate 통과율: `review_pending -> execution_open` 전환율

핵심 판단:
- Manus: 시나리오/설명 강점
- Agent Factory: 공정/분해/자동화 강점
- 제품화 기준 우위: Agent Factory (단, 계약/검증 레이어 보강 필수)

---

## 2단계. 우선순위 1 - Global Game Config를 단일 소스로 고정

### 왜 먼저 해야 하나
`starting_stack`, `SB/BB`, `timeout` 충돌은 룰, 테스트, 밸런스를 동시에 깨뜨린다.

### 개발환경 적용
1. `global_game_config.json` (또는 YAML) 1개를 SSOT로 선언
2. Feature Plan/Spec/Design/Tasks 생성 시 이 파일만 참조
3. 파이프라인에 config drift check 추가 (불일치 시 gate fail)

### 사용자 사용 흐름 적용
1. 사용자 입력 초기에 게임 기본값 확정
2. 이후 문서 생성 단계에서 설정값 직접 편집 금지
3. 값 변경 시 관련 산출물 일괄 재생성

### 완료 기준
- 문서 간 설정값 불일치 0건

---

## 3단계. 우선순위 2 - Event Protocol을 “문서”가 아닌 “계약”으로 전환

### 왜 중요한가
서버 권위형 게임에서 이벤트 프로토콜은 서버-클라이언트 실행 계약서다.  
없으면 구현/검증/운영 모두 불가능해진다.

### 개발환경 적용
1. `event-protocol.md` + JSON Schema 동시 생성
2. 방향 분리: `client -> server`, `server -> client`
3. 서버/클라 검증 코드가 스키마를 참조하도록 강제
4. 필수 이벤트 누락 시 approval gate fail

### 사용자 사용 흐름 적용
1. AF가 프로토콜 초안 제시
2. 사용자 승인 후에만 설계/작업 문서 생성 진행

### 최소 필수 이벤트
- CLIENT -> SERVER: `join_room`, `create_room`, `start_game`, `player_action`, `reconnect`, `leave_room`
- SERVER -> CLIENT: `room_state`, `game_started`, `private_hole_cards`, `public_state_update`, `action_required`, `action_rejected`, `street_revealed`, `showdown_result`, `pot_distributed`, `player_disconnected`, `error`

### 완료 기준
- 필수 이벤트 100% + payload schema 검증 통과

---

## 4단계. 우선순위 3 - 역할(owner) 자동 보정 규칙 도입

### 왜 필요한가
룰 엔진/서버가 Frontend Dev로 배정되면 작업 신뢰도와 병렬 실행 효율이 떨어진다.

### 개발환경 적용
1. `module_type -> owner` 강제 매핑 테이블 적용
2. 보드 생성 후 `owner lint` 실행
3. 위반 시 자동 재배정 + 로그 남김

### 권장 강제 매핑
- Rule Engine -> Game Logic Dev
- Realtime Server/WebSocket -> Backend Dev
- UI/화면/입력 -> Frontend Dev
- 테스트/회귀/품질게이트 -> QA Engineer

### 사용자 사용 흐름 적용
- 사용자 커스텀 배정 허용하되, 핵심 모듈은 보호 규칙 유지

### 완료 기준
- 핵심 모듈 owner 오배정 0건

---

## 5단계. 우선순위 4 - Acceptance Criteria를 테스트 문장으로 강제

### 왜 필요한가
“구현된다”는 검증이 불가능하다.  
“입력/행동/기대결과” 형식이어야 자동 테스트가 가능하다.

### 개발환경 적용
1. acceptance 문장 린터 추가 (함수/조건/기대결과 포함 강제)
2. acceptance 기반 테스트 스켈레톤 자동 생성
3. 테스트 없는 태스크는 gate fail

### 좋은 기준 예시
- `evaluate_hand(cards7)`가 모든 족보를 판정한다.
- `A-2-3-4-5`를 5-high 스트레이트로 처리한다.
- One Pair 동률 시 kicker 3장을 순서대로 비교한다.
- 3인 올인 시 기여금 기준 side pot이 생성된다.
- 턴 타임아웃 초과 시 서버가 `AUTO_FOLD`를 발행한다.

### 완료 기준
- 모든 구현 태스크에 최소 1개 실행 가능한 테스트 존재

---

## 6단계. 우선순위 5 - Manus식 시뮬레이션 문서를 흡수

### 목적
AF의 공정 강점을 유지하면서, Manus의 설명력을 보강한다.

### 적용 방식
`simulation.md`를 `state-machine` + `event-protocol`에서 자동 파생 생성한다.

### 산출물 권장 세트
1. `project-brief.json`
2. `rules-spec.md`
3. `server-architecture.md`
4. `client-view.md`
5. `event-protocol.md`
6. `state-machine.md`
7. `implementation-design.md`
8. `implementation-tasks.md`
9. `approval-gate.md`
10. `simulation.md` (설명력 보강)

### 완료 기준
- 시나리오 문서와 프로토콜/상태머신 간 충돌 0건

---

## 7단계. 실행 로드맵 (권장)

1주차: Config SSOT + drift check  
2주차: Event schema + protocol gate  
3주차: Owner lint + acceptance-to-test 생성기  
4주차: simulation.md 자동 생성 + 대시보드 지표화

---

## 8단계. 최종 판단

Agent Factory가 Manus보다 제품화 방향성은 우위다.  
다만 승패를 가르는 조건은 문서 개수가 아니라 다음 4가지다.

1. 설정값 단일화 (SSOT)
2. 이벤트 계약 완결성 (Protocol)
3. 역할 배정 정확성 (Owner Lint)
4. 테스트 가능한 acceptance 강제

즉, AF는 “문서 생성기”가 아니라 “계약-검증-승인 시스템”으로 이동해야 한다.
