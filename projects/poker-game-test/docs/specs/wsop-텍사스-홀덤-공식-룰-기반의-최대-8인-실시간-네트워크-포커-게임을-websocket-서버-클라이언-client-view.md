## 개요

8인 멀티플레이어 텍사스 홀덤 포커 게임의 클라이언트 뷰 명세서.  
기준 규칙: **WSOP (World Series of Poker) No-Limit Texas Hold'em 표준 규칙 2024**.  
게임 로직 판정은 서버 전담, 클라이언트는 서버가 전송한 플레이어별 뷰만 렌더링한다.

---

## 기본 게임 설정

| 항목 | 값 | 비고 |
|------|-----|------|
| 최대 플레이어 수 | 8인 | |
| 시작 칩 | 10,000 | 단위: 칩(chip) |
| 스몰 블라인드 | 50 | 딜러 기준 +1 포지션 |
| 빅 블라인드 | 100 | 딜러 기준 +2 포지션 |
| 베팅 구조 | No-Limit | 최소 레이즈 = 직전 레이즈 금액 이상 |
| 올인 허용 | 예 | 사이드팟 자동 생성 |
| 커뮤니티 카드 | 플랍(3) + 턴(1) + 리버(1) | 총 5장 |

---

## 베팅 규칙 (WSOP No-Limit 기준)

### 베팅 행동 정의

| 행동 | 조건 | 최소 금액 |
|------|------|-----------|
| `CHECK` | 현재 라운드 베팅액 = 0 또는 콜 금액 이미 납부 | 0 |
| `CALL` | 상대 베팅 존재 | 현재 최고 베팅액 - 내 납부액 |
| `BET` | 현재 라운드 오픈 베팅 없음 | 빅 블라인드(100) 이상 |
| `RAISE` | 상대 베팅 또는 레이즈 존재 | 직전 레이즈 증분 이상 |
| `FOLD` | 언제나 가능 | - |
| `ALL-IN` | 보유 칩 전액 | 보유 칩 전액 |

### 레이즈 크기 규칙

```
최소 레이즈 = 직전 레이즈 증분(delta)
예) 빅블라인드 100 → 첫 레이즈 최소 200 (delta=100)
    200 레이즈 후 → 다음 레이즈 최소 300 (delta=100 유지)
    200 레이즈 후 500 레이즈 → delta=300, 다음 최소 800
```

### 올인 & 사이드팟 규칙

- 플레이어가 콜 금액보다 적은 칩으로 올인 시 → 사이드팟 분리
- 쇼다운 시 각 플레이어는 자신이 기여한 팟에만 경쟁
- 팟 계산은 서버 전담, 클라이언트는 표시만 담당

---

## 정보 비대칭 모델 (Information Asymmetry Model)

포커의 핵심은 정보 비대칭이다. 각 플레이어가 볼 수 있는 정보와 숨겨진 정보를 명확히 분리한다.

### 정보 가시성 매트릭스

| 정보 항목 | 본인 | 다른 플레이어 | 관전자 | 쇼다운 후 |
|-----------|------|---------------|--------|-----------|
| 본인 홀 카드 (2장) | **공개** | 숨김 | 숨김 | 공개 |
| 상대 홀 카드 (2장) | 숨김 | 숨김 | 숨김 | **공개** |
| 플랍 (커뮤니티 3장) | 공개 | 공개 | 공개 | 공개 |
| 턴 (커뮤니티 1장) | 공개 | 공개 | 공개 | 공개 |
| 리버 (커뮤니티 1장) | 공개 | 공개 | 공개 | 공개 |
| 메인 팟 금액 | 공개 | 공개 | 공개 | 공개 |
| 사이드팟 금액 | 공개 | 공개 | 공개 | 공개 |
| 현재 베팅액 (각 플레이어) | 공개 | 공개 | 공개 | 공개 |
| 각 플레이어 보유 칩 | 공개 | 공개 | 공개 | 공개 |
| 폴드 여부 | 공개 | 공개 | 공개 | 공개 |
| 핸드 랭킹 (최종 결과) | 숨김 | 숨김 | 숨김 | **공개** |

---

## 본인 홀 카드 (Own Hand)

- 서버는 딜링 시 `player_id`를 키로 각 플레이어에게 **개별 메시지**로만 홀 카드를 전송한다.
- 클라이언트는 `my_hole_cards` 필드만 수신하며, 이 필드는 본인 세션에만 존재한다.
- 카드 2장은 게임 중 항상 클라이언트 화면에 표시된다 (쇼다운 전까지 본인만 가시).
- 쇼다운(showdown) 이벤트 수신 전까지 서버는 상대의 홀 카드를 절대 전송하지 않는다.

```json
// 서버 → 클라이언트 (플레이어 본인 전용 메시지)
{
  "type": "DEAL_HOLE_CARDS",
  "player_id": "p1",
  "my_hole_cards": ["Ah", "Kd"]
}
```

---

## 상대 홀 카드 (Other Players' Hole Cards)

- 게임 진행 중 상대 홀 카드는 **절대 클라이언트에 전송되지 않는다**.
- 클라이언트는 상대 카드 자리에 **카드 뒷면 이미지**만 렌더링한다.
- 쇼다운 이벤트(`SHOWDOWN`) 발생 시 서버가 **공개 의무가 있는 플레이어의 카드만** 전송한다.
  - 폴드한 플레이어의 카드는 쇼다운 후에도 공개하지 않는 것이 WSOP 기준 원칙 (머크 권리 보호).

```json
// 서버 → 전체 (쇼다운 이벤트)
{
  "type": "SHOWDOWN",
  "revealed_hands": [
    { "player_id": "p2", "hole_cards": ["Qs", "Jc"], "hand_rank": "STRAIGHT" },
    { "player_id": "p5", "hole_cards": ["2h", "7d"], "hand_rank": "HIGH_CARD" }
  ],
  "winner_id": "p2"
}
```

---

## 커뮤니티 카드 (Community Cards)

- 플랍, 턴, 리버는 **모든 클라이언트에 동시에 브로드캐스트**된다.
- 각 스트리트 공개 시 서버는 단계별 이벤트를 순서대로 전송한다.

```json
// 플랍
{ "type": "DEAL_FLOP", "community_cards": ["5c", "9h", "Kd"] }

// 턴
{ "type": "DEAL_TURN", "community_cards": ["5c", "9h", "Kd", "2s"] }

// 리버
{ "type": "DEAL_RIVER", "community_cards": ["5c", "9h", "Kd", "2s", "Jh"] }
```

- 클라이언트는 `community_cards` 배열을 누적 렌더링한다 (덮어쓰기 아닌 append).
- 커뮤니티 카드 공개 전 빈 슬롯은 카드 뒷면으로 표시한다.

---

## 팟 금액 및 베팅 금액 (Pot & Bet Amounts)

팟과 베팅 정보는 게임 페어니스를 위해 **모든 플레이어에게 동일하게 공개**된다.

### 팟 구조

```json
{
  "type": "POT_UPDATE",
  "main_pot": 1500,
  "side_pots": [
    { "pot_id": "sp1", "amount": 600, "eligible_players": ["p3", "p5", "p7"] }
  ],
  "total_pot": 2100
}
```

### 베팅 현황

```json
{
  "type": "BET_UPDATE",
  "player_bets": [
    { "player_id": "p1", "bet": 200, "total_chips": 9800, "status": "ACTIVE" },
    { "player_id": "p2", "bet": 400, "total_chips": 8600, "status": "ACTIVE" },
    { "player_id": "p3", "bet": 0,   "total_chips": 0,    "status": "ALL_IN" },
    { "player_id": "p4", "bet": 0,   "total_chips": 7200, "status": "FOLDED" }
  ],
  "current_max_bet": 400,
  "minimum_raise": 400
}
```

- `total_chips`: 현재 베팅 금액을 제외한 남은 칩 (표시용)
- `status`: `ACTIVE` | `FOLDED` | `ALL_IN` | `WAITING`

---

## 구현 계약: 서버 → 클라이언트 뷰 전송 규칙 (Implementation Contract)

### 핵심 원칙

> **서버는 절대 글로벌 게임 상태를 클라이언트에 전송하지 않는다.**  
> 서버는 각 플레이어의 `session_id`와 `player_id`를 기반으로 **개인화된 뷰(player-specific view)**만 전송한다.

### 전송 격리 규칙

| 규칙 | 설명 |
|------|------|
| **홀 카드 격리** | `DEAL_HOLE_CARDS`는 단일 WebSocket 연결(unicast)로만 전송. 브로드캐스트 금지. |
| **글로벌 상태 금지** | 서버는 모든 플레이어의 홀 카드를 포함한 `game_state` 객체를 클라이언트에 직접 전송하지 않는다. |
| **클라이언트 검증 금지** | 핸드 평가, 팟 계산, 위너 결정은 서버만 수행. 클라이언트는 결과를 표시할 뿐 자체 계산하지 않는다. |
| **순서 보장** | 이벤트는 서버가 정한 순서대로만 클라이언트에 도달 보장 (WebSocket ordered delivery). |
| **클라이언트 조작 방어** | 클라이언트가 다른 플레이어의 카드를 요청하는 메시지를 보내도 서버는 응답하지 않는다 (403 무응답). |

### WebSocket 메시지 분류

| 전송 방식 | 이벤트 타입 | 수신자 |
|-----------|-------------|--------|
| Unicast (1:1) | `DEAL_HOLE_CARDS` | 해당 플레이어만 |
| Broadcast (1:N) | `DEAL_FLOP`, `DEAL_TURN`, `DEAL_RIVER` | 테이블 전체 |
| Broadcast (1:N) | `POT_UPDATE`, `BET_UPDATE` | 테이블 전체 |
| Broadcast (1:N) | `PLAYER_ACTION`, `TURN_CHANGE` | 테이블 전체 |
| Broadcast (1:N) | `SHOWDOWN`, `ROUND_END` | 테이블 전체 |
| Unicast (1:1) | `YOUR_TURN` (액션 요청) | 해당 플레이어만 |

### 서버 뷰 생성 로직 (의사코드)

```python
def build_player_view(game_state: GameState, requesting_player_id: str) -> PlayerView:
    view = PlayerView()

    # 커뮤니티 카드 - 전체 공개
    view.community_cards = game_state.community_cards

    # 팟/베팅 - 전체 공개
    view.main_pot = game_state.main_pot
    view.side_pots = game_state.side_pots
    view.player_bets = game_state.player_bets  # 금액만, 카드 없음

    # 홀 카드 - 본인만 공개, 나머지는 HIDDEN
    for player in game_state.players:
        if player.id == requesting_player_id:
            view.players[player.id].hole_cards = player.hole_cards  # 실제 카드
        else:
            view.players[player.id].hole_cards = ["HIDDEN", "HIDDEN"]  # 뒷면

    return view
```

---

## 클라이언트 렌더링 계약

클라이언트는 서버로부터 수신한 뷰 데이터만으로 UI를 구성하며, 어떠한 추론이나 상태 보완도 금지된다.

| 상태 | 렌더링 |
|------|--------|
| `hole_cards = ["Ah", "Kd"]` (본인) | 카드 앞면 표시 |
| `hole_cards = ["HIDDEN", "HIDDEN"]` (상대) | 카드 뒷면 이미지 2장 |
| `status = "FOLDED"` | 카드 뒤집기 애니메이션 + 어둡게 처리 |
| `status = "ALL_IN"` | ALL-IN 뱃지 표시 |
| 쇼다운 `revealed_hands` 수신 | 해당 플레이어 카드 앞면 플립 애니메이션 |
| 커뮤니티 카드 미공개 슬롯 | 카드 뒷면 (placeholder) |

---

## 보안 고려사항

- 서버는 WebSocket 연결마다 `session_token`을 검증하여 `player_id` 위조를 방지한다.
- 모든 게임 상태는 서버 메모리에만 존재하며, 클라이언트는 자신의 뷰 스냅샷만 보유한다.
- 클라이언트 DevTools에서 WebSocket 메시지를 감청해도 본인의 카드 정보 외에는 추출 불가능한 구조를 유지한다.
- 쇼다운 결과의 핸드 랭킹 계산은 서버가 수행하고 결과(`hand_rank` 문자열)만 전송한다.