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
| `GAME_OVER` | 게임 종료 | 한 명만 남거나 강제 종료 |

---

## 2. 상태 전이 테이블

| # | from_state | event | to_state | 조건 |
|---|---|---|---|---|
| T01 | `WAITING` | `PLAYER_JOIN` | `WAITING` | 착석 인원 < 2 |
| T02 | `WAITING` | `PLAYER_JOIN` | `SETUP` | 착석 인원 ≥ 2 |
| T03 | `WAITING` | `PLAYER_LEAVE` | `WAITING` | — |
| T04 | `SETUP` | `SETUP_COMPLETE` | `PREFLOP` | 블라인드 징수 완료 & 카드 배분 완료 |
| T05 | `PREFLOP` | `BET_ROUND_COMPLETE` | `FLOP` | 액션 완료 & 2명 이상 잔존 |
| T06 | `PREFLOP` | `ONE_PLAYER_REMAINS` | `POT_DISTRIBUTION` | 나머지 전원 폴드 |
| T07 | `FLOP` | `BET_ROUND_COMPLETE` | `TURN` | 액션 완료 & 2명 이상 잔존 |
| T08 | `FLOP` | `ONE_PLAYER_REMAINS` | `POT_DISTRIBUTION` | 나머지 전원 폴드 |
| T09 | `TURN` | `BET_ROUND_COMPLETE` | `RIVER` | 액션 완료 & 2명 이상 잔존 |
| T10 | `TURN` | `ONE_PLAYER_REMAINS` | `POT_DISTRIBUTION` | 나머지 전원 폴드 |
| T11 | `RIVER` | `BET_ROUND_COMPLETE` | `SHOWDOWN` | 액션 완료 & 2명 이상 잔존 |
| T12 | `RIVER` | `ONE_PLAYER_REMAINS` | `POT_DISTRIBUTION` | 나머지 전원 폴드 |
| T13 | `SHOWDOWN` | `HANDS_EVALUATED` | `POT_DISTRIBUTION` | 모든 핸드 평가 완료 |
| T14 | `POT_DISTRIBUTION` | `DISTRIBUTION_COMPLETE` | `SETUP` | 생존 플레이어 ≥ 2 |
| T15 | `POT_DISTRIBUTION` | `DISTRIBUTION_COMPLETE` | `GAME_OVER` | 생존 플레이어 = 1 |
| T16 | `GAME_OVER` | `REMATCH_REQUESTED` | `WAITING` | 호스트 재시작 요청 |
| T17 | 모든 상태 | `HOST_FORCE_END` | `GAME_OVER` | 호스트 강제 종료 |
| T18 | 모든 상태 | `ALL_PLAYERS_LEFT` | `GAME_OVER` | 접속자 0명 |
| T19 | `PREFLOP`·`FLOP`·`TURN`·`RIVER` | `PLAYER_TIMEOUT` | 동일 상태 유지 | 해당 플레이어 자동 폴드 처리 후 베팅 계속 |
| T20 | `PREFLOP`·`FLOP`·`TURN`·`RIVER` | `ALL_IN_ALL_PLAYERS` | `SHOWDOWN` | 베팅 가능 플레이어 0명 (모두 올인) |

---

## 3. 상태별 진입·퇴장 액션

### WAITING

```
진입(entry):
  - 로비 화면 활성화 브로드캐스트
  - 좌석 슬롯 초기화 (0–7)
  - 딜러 버튼 위치 미정 상태로 설정

퇴장(exit):
  - 준비 완료 플레이어 목록 스냅샷 생성
  - 좌석 변경 잠금
```

### SETUP

```
진입(entry):
  - 딜러 버튼 다음 좌석으로 이동 (첫 핸드: 무작위)
  - Small Blind 플레이어 칩에서 50 차감 → 팟 적립
  - Big Blind 플레이어 칩에서 100 차감 → 팟 적립
  - 덱 52장 셔플 (Fisher-Yates)
  - 각 플레이어 홀 카드 2장 서버 메모리 할당 (미공개)
  - 액션 순서 포인터 = Big Blind 다음 좌석으로 초기화
  - 현재 베팅 = 100 (big blind), 최소 레이즈 델타 = 100

퇴장(exit):
  - SETUP_COMPLETE 이벤트 발행
  - 각 플레이어에게 본인 홀 카드만 암호화 전송 (deal_private 메시지)
```

### PREFLOP

```
진입(entry):
  - 베팅 라운드 상태 초기화
  - 액션 타이머 시작 (기본 30초)
  - 현재 액션 플레이어에게 action_request 메시지 전송
  - 클라이언트에 stage=PREFLOP 브로드캐스트

퇴장(exit):
  - 이번 라운드 베팅 총액 팟에 통합
  - 플레이어별 라운드 베팅액 초기화
  - 커뮤니티 카드 공개 준비 (플롭 3장 서버에서 선택)
```

### FLOP

```
진입(entry):
  - 커뮤니티 카드 3장 공개 브로드캐스트 (board_update 메시지)
  - 베팅 라운드 상태 초기화
  - 액션 포인터 = 딜러 버튼 다음 생존 플레이어
  - 현재 베팅 = 0, 최소 레이즈 델타 = Big Blind(100)
  - 액션 타이머 재시작

퇴장(exit):
  - 이번 라운드 베팅 총액 팟에 통합
  - 플레이어별 라운드 베팅액 초기화
```

### TURN

```
진입(entry):
  - 커뮤니티 카드 4번째 장 공개 브로드캐스트
  - 베팅 라운드 상태 초기화
  - 액션 포인터 = 딜러 버튼 다음 생존 플레이어
  - 현재 베팅 = 0, 최소 레이즈 델타 = Big Blind(100)
  - 액션 타이머 재시작

퇴장(exit):
  - 이번 라운드 베팅 총액 팟에 통합
  - 플레이어별 라운드 베팅액 초기화
```

### RIVER

```
진입(entry):
  - 커뮤니티 카드 5번째 장 공개 브로드캐스트
  - 베팅 라운드 상태 초기화
  - 액션 포인터 = 딜러 버튼 다음 생존 플레이어
  - 현재 베팅 = 0, 최소 레이즈 델타 = Big Blind(100)
  - 액션 타이머 재시작

퇴장(exit):
  - 이번 라운드 베팅 총액 팟에 통합
  - 플레이어별 라운드 베팅액 초기화
```

### SHOWDOWN

```
진입(entry):
  - 모든 생존 플레이어 홀 카드 전체 공개 브로드캐스트 (reveal_hands 메시지)
  - 7장(홀 2 + 커뮤니티 5) 핸드 평가 알고리즘 실행
  - 핸드 랭킹 순서 계산 (동점 처리 포함)

퇴장(exit):
  - 승자 목록 및 핸드 랭킹 결과 서버 메모리 확정
  - HANDS_EVALUATED 이벤트 발행
```

### POT_DISTRIBUTION

```
진입(entry):
  - 메인팟·사이드팟 분리 계산 (올인 플레이어 기여액 기준)
  - 각 팟별 자격 있는 플레이어 그룹 결정
  - 팟 금액 → 승자 칩 증가 처리
  - 분배 결과 브로드캐스트 (pot_result 메시지)
  - 폴드한 플레이어 홀 카드 공개 여부: 폴드 시 비공개 유지

퇴장(exit):
  - 전체 플레이어 칩 잔액 갱신 브로드캐스트
  - 칩 0인 플레이어 상태 → BUSTED 전환
  - DISTRIBUTION_COMPLETE 이벤트 발행
```

### GAME_OVER

```
진입(entry):
  - 최종 순위 및 칩 잔액 브로드캐스트
  - 게임 결과 서버 로그 기록
  - 모든 타이머 정지
  - WebSocket 세션 유지 (로비 복귀 대기)

퇴장(exit):
  - 게임 상태 전체 초기화
  - 좌석·칩·카드 상태 리셋
```

---

## 4. 플레이어 레벨 서브 상태

### 서브 상태 목록

| 서브 상태 | 설명 | 베팅 가능 | 카드 보유 |
|---|---|---|---|
| `ACTIVE` | 현재 핸드에 참여 중 | O | O |
| `FOLDED` | 이번 핸드에서 폴드 완료 | X | X (반납) |
| `ALL_IN` | 칩 전부 베팅, 추가 액션 없음 | X | O |
| `SITTING_OUT` | 일시 자리 비움 (핸드 스킵) | X | X |
| `BUSTED` | 칩 소진, 게임 탈락 | X | X |
| `WAITING_BB` | 중간 착석, Big Blind 대기 중 | X | X |

### 플레이어 서브 상태 전이 테이블

| # | from_sub | event | to_sub | 조건 |
|---|---|---|---|---|
| P01 | `SITTING_OUT` | `PLAYER_READY` | `ACTIVE` | 다음 핸드 시작 전 준비 완료 |
| P02 | `WAITING_BB` | `BB_PAID` | `ACTIVE` | Big Blind 선납 완료 |
| P03 | `ACTIVE` | `PLAYER_FOLD` | `FOLDED` | 베팅 라운드 중 폴드 선택 |
| P04 | `ACTIVE` | `PLAYER_ALL_IN` | `ALL_IN` | 보유 칩 전부 베팅 |
| P05 | `ACTIVE` | `PLAYER_TIMEOUT` | `FOLDED` | 30초 내 액션 미입력 → 자동 폴드 |
| P06 | `ACTIVE` | `HAND_ENDS` | `ACTIVE` | 다음 핸드 준비 (칩 > 0) |
| P07 | `ALL_IN` | `HAND_ENDS` | `ACTIVE` | 다음 핸드 준비 (칩 > 0) |
| P08 | `FOLDED` | `HAND_ENDS` | `ACTIVE` | 다음 핸드 준비 (칩 > 0) |
| P09 | `ACTIVE`·`ALL_IN`·`FOLDED` | `CHIP_DEPLETED` | `BUSTED` | 핸드 종료 후 칩 = 0 |
| P10 | `ACTIVE` | `PLAYER_SIT_OUT` | `SITTING_OUT` | 플레이어 자발적 자리 비움 |
| P11 | `BUSTED` | `REBUY` | `WAITING_BB` | 리바이 정책 활성화 시 (옵션) |

---

## 5. 베팅 라운드 내부 흐름

```
베팅 라운드 시작
  └─ 현재 액션 플레이어 결정 (액션 포인터)
       ├─ 플레이어 ACTIVE 아님 → 다음 좌석으로 포인터 이동
       └─ 플레이어 ACTIVE
            ├─ action_request 전송 (가능 액션 목록 포함)
            ├─ 타이머 30초 카운트다운
            └─ 플레이어 응답 수신
                 ├─ FOLD   → 서브 상태 FOLDED, 다음 포인터
                 ├─ CHECK  → (현재 베팅=0일 때만 허용), 다음 포인터
                 ├─ CALL   → 현재 베팅액만큼 차감, 다음 포인터
                 ├─ RAISE  → 최소 레이즈 델타 검증 후 베팅 갱신, 포인터 리셋
                 └─ ALL_IN → 서브 상태 ALL_IN, 사이드팟 마커 기록

베팅 라운드 종료 조건:
  - 모든 ACTIVE 플레이어의 라운드 베팅액이 동일
  - ACTIVE 플레이어 1명만 남음
  - ACTIVE 플레이어 0명 (전원 ALL_IN)
```

---

## 6. 사이드팟 계산 규칙

```
올인 발생 시:
  1. 올인 플레이어의 기여 상한(cap) = 해당 플레이어의 총 투입액
  2. 메인팟 = 모든 플레이어 × cap 금액
  3. cap 초과분은 사이드팟 #1로 분리
  4. 추가 올인 발생 시 사이드팟 #N 누적 생성
  5. 각 팟에 자격 있는 플레이어 = 해당 팟에 기여한 플레이어만

분배 순서:
  1. 메인팟 → 자격 플레이어 중 최강 핸드 수령
  2. 사이드팟 #1 → 자격 플레이어 중 최강 핸드 수령
  3. 사이드팟 #N 순서대로 반복
  4. 동일 핸드 강도 시 팟을 균등 분할 (홀수 칩은 딜러 버튼 기준 좌측 우선)
```

---

## 7. WebSocket 메시지 이벤트 타입 (서버 → 클라이언트)

| 메시지 타입 | 발신 시점 | 페이로드 핵심 필드 |
|---|---|---|
| `game_state_update` | 모든 상태 전이 시 | `state`, `players[]`, `pot` |
| `deal_private` | SETUP 퇴장 | `hole_cards[2]` (수신자 본인만) |
| `board_update` | FLOP·TURN·RIVER 진입 | `community_cards[]` |
| `action_request` | 베팅 라운드 중 해당 플레이어 차례 | `player_id`, `valid_actions[]`, `call_amount`, `min_raise` |
| `action_broadcast` | 플레이어 액션 완료 | `player_id`, `action`, `amount` |
| `reveal_hands` | SHOWDOWN 진입 | `players[]{id, hole_cards, hand_rank}` |
| `pot_result` | POT_DISTRIBUTION 진입 | `main_pot`, `side_pots[]`, `winners[]` |
| `player_status` | 서브 상태 변경 시 | `player_id`, `sub_state` |
| `timer_update` | 매초 | `player_id`, `remaining_seconds` |
| `error` | 규칙 위반 액션 수신 시 | `code`, `message` |

---

## 8. 초기 설정값 요약

| 항목 | 값 |
|---|---|
| 최대 착석 인원 | 8명 |
| 초기 칩 | 10,000 |
| Small Blind | 50 |
| Big Blind | 100 |
| 베팅 구조 | No-Limit |
| 최소 레이즈 | 직전 레이즈 금액 이상 |
| 액션 타이머 | 30초 (타임아웃 시 자동 폴드) |
| 블라인드 레벨업 | 비활성 (캐시게임 기준, 토너먼트 모드 시 별도 설정) |
| 리바이 허용 | 옵션 (기본 비활성) |
| 덱 | 표준 52장, 조커 없음 |