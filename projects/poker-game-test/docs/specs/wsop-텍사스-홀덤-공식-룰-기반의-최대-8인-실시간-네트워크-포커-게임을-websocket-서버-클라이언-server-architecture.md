# 8인 멀티플레이어 포커 게임 — 서버 아키텍처 명세서

**버전**: 1.0.0
**기준 규칙**: World Series of Poker (WSOP) / Poker Tournament Directors Association (TDA) 2023 규칙
**기술 스택**: Python 3.11 · websockets 12.x · asyncio · HTML5/Vanilla JS ES2022

---

## 1. 서버 책임 (Server Responsibilities)

서버는 게임의 유일한 진실 공급원(Single Source of Truth)이다. 클라이언트는 서버가 브로드캐스트한 뷰 전용 스냅샷만 렌더링한다.

### 1.1 권한 있는 게임 상태 관리

서버가 단독으로 소유하고 변경하는 상태:

| 상태 항목 | 설명 |
|---|---|
| `deck` | 셔플된 52장 덱 (클라이언트에 절대 노출 안 함) |
| `hole_cards[player_id]` | 각 플레이어의 홀 카드 (본인 외 마스킹) |
| `community_cards` | 플롭/턴/리버 공개 카드 |
| `pot` | 메인 팟 + 사이드팟 배열 |
| `player_stacks` | 각 플레이어 칩 잔액 |
| `betting_state` | 현재 베팅 라운드, 최고 베팅액, 액션 순서 |
| `rng_seed` | 서버 내부 RNG 시드 (외부 노출 금지) |

### 1.2 모든 플레이어 액션 검증

서버가 클라이언트 요청을 수신하면 다음 순서로 검증한다:

```
수신 → 세션 인증 → 액션 플레이어 확인 → 턴 타이밍 확인
     → 베팅 금액 범위 검증 → 게임 상태 적합성 검증
     → 적용 또는 오류 응답
```

검증 실패 시 `{"type": "ERROR", "code": "...", "message": "..."}` 를 해당 클라이언트에만 전송하며, 게임 상태는 변경되지 않는다.

---

## 2. 룸/세션 관리 (Room & Session Management)

### 2.1 룸 구조

```
PokerServer
└── RoomManager
    └── Room (1개 테이블 = 1개 asyncio Task)
        ├── room_id: str (UUID)
        ├── players: dict[player_id → PlayerSession]
        ├── spectators: set[WebSocket]  (관전자, 공개 정보만 수신)
        ├── state: GameState
        └── config: RoomConfig
```

### 2.2 RoomConfig (WSOP/TDA 기반 기본값)

```python
@dataclass
class RoomConfig:
    max_players: int = 8          # 최대 8인
    min_players: int = 2
    starting_stack: int = 10_000  # 초기 칩 10,000
    small_blind: int = 50
    big_blind: int = 100
    ante: int = 0                 # 토너먼트 모드 시 설정
    turn_timeout_sec: int = 30    # 턴 타임아웃
    reconnect_grace_sec: int = 60 # 재접속 유예 시간
    min_raise: str = "big_blind"  # 최소 레이즈 = 직전 레이즈 크기
```

### 2.3 베팅 규칙 (TDA Rule 43 기반)

- **최소 레이즈**: 직전 레이즈 증분 이상 (첫 베팅은 빅블라인드 이상)
- **올인 룰**: 올인 금액이 최소 레이즈 미만이면 재레이즈 권리 불발생
- **팟 리밋/노리밋**: 기본값은 No-Limit Hold'em
- **콜 금액**: 현재 최고 베팅액 − 플레이어의 이번 스트리트 투입액

### 2.4 최대 플레이어 및 좌석 관리

```
좌석 번호: 0~7 (고정 8석)
상태: EMPTY | WAITING | SITTING_OUT | ACTIVE | ALL_IN | FOLDED
```

- 게임 중 입장: 다음 핸드 시작 전까지 `WAITING` 상태 대기
- 게임 중 퇴장 요청: 현재 핸드 종료 후 좌석 반환
- 강제 퇴장(연결 끊김 + 유예 초과): `FOLDED` 처리 후 좌석 반환

### 2.5 재접속 처리 (Reconnection Handling)

```
연결 끊김 감지 (websocket.closed)
    │
    ▼
PlayerSession.status = DISCONNECTED
    │
    ├─ 유예 60초 이내 재접속 ─→ 동일 player_id WebSocket 교체
    │                              → full_state_snapshot 전송
    │                              → status = ACTIVE 복원
    │
    └─ 60초 초과 ──────────────→ 해당 턴은 auto_fold 처리
                                  → 핸드 종료 후 좌석 반환
```

재접속 플레이어에게 전송하는 `FULL_STATE_SNAPSHOT`:
- 현재 커뮤니티 카드
- 본인 홀 카드
- 팟 크기
- 각 플레이어 스택/베팅액 (홀 카드 마스킹 유지)
- 현재 액션 순서 및 유효 액션 목록

---

## 3. 핵심 게임 루프 (Core Game Loop)

### 3.1 핸드 생명주기 (Hand Lifecycle)

```
[대기] WAITING_FOR_PLAYERS
    │  인원 ≥ 2명 확인
    ▼
[준비] HAND_STARTING
    │  딜러 버튼 이동, 블라인드 포스트, 덱 셔플
    ▼
[홀카드 딜] DEALING_HOLE_CARDS
    │  플레이어별 개인 전송 (hole_cards 서버만 보관)
    ▼
[프리플롭 베팅] BETTING_PREFLOP
    │
    ▼
[플롭 딜] DEALING_FLOP  (커뮤니티 3장)
    │
    ▼
[플롭 베팅] BETTING_FLOP
    │
    ▼
[턴 딜] DEALING_TURN
    │
    ▼
[턴 베팅] BETTING_TURN
    │
    ▼
[리버 딜] DEALING_RIVER
    │
    ▼
[리버 베팅] BETTING_RIVER
    │
    ▼
[쇼다운] SHOWDOWN  (핸드 평가 → 승자 결정)
    │
    ▼
[팟 분배] DISTRIBUTING_POT
    │
    ▼
[결과 브로드캐스트] HAND_RESULT
    │
    └─→ [대기]로 복귀 (탈락 플레이어 처리 후)
```

### 3.2 베팅 라운드 이벤트 루프

```python
async def run_betting_round(room: Room) -> None:
    """
    베팅 라운드 단일 진행 루프.
    모든 액션 플레이어가 동일 베팅액에 도달하거나 폴드할 때까지 반복.
    """
    while room.state.has_action_remaining():
        player = room.state.current_actor()
        valid_actions = room.state.compute_valid_actions(player)

        # 액션 요청 브로드캐스트 (해당 플레이어에게 유효 액션 포함)
        await room.broadcast(ActionRequestEvent(player.id, valid_actions))

        try:
            action = await asyncio.wait_for(
                player.action_queue.get(),
                timeout=room.config.turn_timeout_sec
            )
            room.state.apply_action(player.id, action)  # 검증+적용
        except asyncio.TimeoutError:
            room.state.apply_action(player.id, AutoFoldAction())

        await room.broadcast(ActionResultEvent(room.state.snapshot()))
```

### 3.3 상태 변이 (State Mutation) 원칙

- 모든 상태 변이는 `GameState.apply_action()` 단일 진입점을 통해서만 수행
- 변이 전 `validate_action()` 선행 — 검증 실패 시 `InvalidActionError` 발생, 상태 불변
- 변이는 동기 처리 (asyncio 이벤트 루프 내 단일 태스크 → 경쟁 조건 없음)

### 3.4 브로드캐스트 전략

```
게임 이벤트 발생
    │
    ├─ 공개 정보 → 전체 브로드캐스트 (WebSocket fan-out)
    │              예: 커뮤니티 카드, 베팅 액션, 팟 크기
    │
    └─ 비공개 정보 → 해당 플레이어에게만 단독 전송
                     예: 홀 카드, 패배 시 홀 카드 비공개 처리
```

---

## 4. 서버 권한 이벤트 목록 (Server-Authoritative Events)

### 4.1 서버 → 클라이언트 이벤트

| 이벤트 타입 | 트리거 | 페이로드 |
|---|---|---|
| `HAND_STARTED` | 새 핸드 시작 | `dealer_seat`, `small_blind_seat`, `big_blind_seat`, `ante` |
| `HOLE_CARDS_DEALT` | 홀카드 딜 완료 | `cards: [Card, Card]` (본인만), 타인은 `["??", "??"]` |
| `ACTION_REQUESTED` | 플레이어 턴 | `player_id`, `valid_actions`, `timeout_at` |
| `ACTION_APPLIED` | 액션 처리 완료 | `player_id`, `action_type`, `amount`, `pot_total` |
| `COMMUNITY_CARDS_DEALT` | 플롭/턴/리버 공개 | `street`, `cards: [Card, ...]` |
| `SHOWDOWN` | 쇼다운 | `hands: [{player_id, cards, hand_rank}]` |
| `POT_AWARDED` | 팟 분배 | `winners: [{player_id, amount, hand_rank}]`, `side_pots` |
| `PLAYER_JOINED` | 플레이어 입장 | `player_id`, `seat`, `stack` |
| `PLAYER_LEFT` | 플레이어 퇴장 | `player_id`, `reason` |
| `PLAYER_RECONNECTED` | 재접속 | `player_id` |
| `FULL_STATE_SNAPSHOT` | 재접속 복원용 | 전체 공개 상태 |
| `ERROR` | 유효하지 않은 액션 | `code`, `message` |

### 4.2 클라이언트 → 서버 요청 이벤트

| 이벤트 타입 | 설명 | 서버 검증 항목 |
|---|---|---|
| `FOLD` | 폴드 | 액션 플레이어 여부, 게임 진행 중 여부 |
| `CHECK` | 체크 | 현재 베팅액 = 본인 투입액 조건 |
| `CALL` | 콜 | 콜 가능 금액 ≤ 스택 |
| `RAISE` | 레이즈 | `amount ≥ min_raise`, `amount ≤ stack` (올인 허용) |
| `ALL_IN` | 올인 | 스택 전액 투입 |
| `JOIN_ROOM` | 룸 입장 | 빈 좌석 존재, 인증 토큰 유효 |
| `LEAVE_ROOM` | 룸 퇴장 | 핸드 종료 후 처리 큐 등록 |
| `SIT_OUT` | 시팅 아웃 | 다음 핸드부터 적용 |

### 4.3 핸드 평가 서버 처리 순서 (Showdown)

```
1. 생존 플레이어 홀 카드 공개
2. 각 플레이어 7장(홀 2 + 커뮤니티 5)에서 최고 5장 조합 선택
3. 핸드 랭킹 평가 (서버 내 hand_evaluator.py)
4. 사이드팟별 적격 플레이어 결정 (올인 금액 기준)
5. 팟 분배 — 동점 시 균등 분할 (홀수 칩은 딜러 좌측 플레이어 우선)
6. SHOWDOWN + POT_AWARDED 이벤트 브로드캐스트
```

**핸드 랭킹 순위** (높음 → 낮음):
로열 플러시 → 스트레이트 플러시 → 포카드 → 풀하우스 → 플러시 → 스트레이트 → 트리플 → 투페어 → 원페어 → 하이카드

---

## 5. 치팅 방지 (Cheat Prevention)

### 5.1 클라이언트가 정규 상태를 절대 보유하지 않는 이유

```
[잘못된 구조 — 금지]           [올바른 구조 — 채택]
Client ──→ 게임 로직 적용       Client ──→ 렌더링 전용 뷰
Client ──→ 카드 계산            Server ──→ 모든 게임 로직
Client ──→ 승패 판정            Server ──→ 카드 소유 및 공개 통제
```

클라이언트가 게임 로직을 보유하면 메모리 조작, 패킷 변조, 시간 조작 등으로 클라이언트 상태를 위조할 수 있다. 서버만이 유일한 진실 공급원이면 클라이언트 조작의 결과는 서버 검증 단계에서 거부된다.

### 5.2 적용된 치팅 방지 메커니즘

| 위협 | 방어 메커니즘 |
|---|---|
| 홀 카드 스니핑 | 타인 홀 카드를 서버가 전송하지 않음. 쇼다운 전까지 `["??","??"]` 마스킹 |
| 패킷 위조 (유효하지 않은 액션) | 서버에서 `validate_action()` — 실패 시 무시+ERROR 반환 |
| 턴 외 액션 | `current_actor()` 불일치 시 즉시 거부 |
| 베팅 금액 조작 | `min_raise ≤ amount ≤ stack` 서버 검증 |
| 덱 예측 | RNG 시드 서버 내부 보관, 클라이언트 미노출 |
| 리플레이 공격 | 각 액션에 단조 증가 `action_seq` 포함, 중복 seq 거부 |
| 타임아웃 조작 | 타임아웃은 서버 asyncio `wait_for`가 관리, 클라이언트 시간 신뢰 안 함 |
| 멀티 계정 공모 | 룸당 동일 IP 제한 (선택 적용), 핸드 히스토리 서버 기록 |

### 5.3 서버-클라이언트 신뢰 경계

```
┌──────────────────────────────────────────────────────┐
│                      SERVER (신뢰 영역)                │
│  덱·홀카드·RNG·게임로직·팟계산·핸드평가·검증          │
└──────────────────────────┬───────────────────────────┘
                           │ JSON over WebSocket (TLS)
                           │ 공개 상태 스냅샷만 하향 전송
┌──────────────────────────▼───────────────────────────┐
│                    CLIENT (비신뢰 영역)                 │
│  렌더링·애니메이션·사운드·UX 입력 수집                  │
│  게임 로직 없음 — 서버 메시지를 그대로 표시             │
└──────────────────────────────────────────────────────┘
```

클라이언트가 수신하는 모든 데이터는 **이미 필터링된 공개 정보**이며, 클라이언트 코드에 게임 판단 로직이 존재해서는 안 된다. 클라이언트의 역할은 "서버가 말한 것을 보여주는 것"이다.

---

## 6. 초기 자산 및 블라인드 구조

### 6.1 초기 칩 설정

| 항목 | 기본값 | 비고 |
|---|---|---|
| 초기 스택 | 10,000 칩 | 캐시 게임 기준 |
| 스몰 블라인드 | 50 | 빅 블라인드의 50% |
| 빅 블라인드 | 100 | 최소 베팅 단위 |
| 앤티 | 0 | 토너먼트 모드 시 활성화 |
| 최소 바이인 | 4,000 (40BB) | 입장 최소 칩 |
| 최대 바이인 | 10,000 (100BB) | 초기 스택과 동일 |

### 6.2 베팅 금액 규칙 (No-Limit Hold'em)

- **체크**: 추가 베팅 없이 턴 넘기기 (현재 베팅액 = 0일 때만 가능)
- **콜**: 현재 최고 베팅액 전액 매칭 (스택 부족 시 올인 처리)
- **레이즈 최솟값**: 직전 레이즈 증분 (최초 레이즈는 BB 이상)
- **레이즈 최댓값**: 스택 전액 (올인)
- **올인**: 스택이 콜 금액보다 적을 때 자동 올인 처리, 사이드팟 생성

---

## 부록: WebSocket 메시지 프로토콜 개요

```json
// 클라이언트 → 서버: 레이즈 액션 예시
{
  "type": "RAISE",
  "room_id": "uuid-...",
  "player_id": "uuid-...",
  "action_seq": 42,
  "amount": 300
}

// 서버 → 전체 브로드캐스트: 액션 적용 결과
{
  "type": "ACTION_APPLIED",
  "player_id": "uuid-...",
  "action_type": "RAISE",
  "amount": 300,
  "pot_total": 750,
  "player_stack": 9700,
  "current_bet": 300
}

// 서버 → 본인 전용: 홀 카드 딜
{
  "type": "HOLE_CARDS_DEALT",
  "cards": ["Ah", "Kd"]
}
```

모든 메시지는 UTF-8 JSON, TLS 필수 (프로덕션 환경 wss://). `action_seq`는 단조 증가 정수로 리플레이 공격 방지에 사용된다.