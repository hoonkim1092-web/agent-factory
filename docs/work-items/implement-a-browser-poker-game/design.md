# Implementation Design

## Metadata

- work_item: implement-a-browser-poker-game
- spec_type: feature
- source_spec: spec.md (2026-05-09)
- status: draft
- last_updated: 2026-05-14

---

## 설계 요약

브라우저 기반 텍사스 홀덤(Texas Hold'em) 포커 게임을 Vanilla JS로 구현한다. 게임 로직(`game rules`)과 렌더링(`game ui`)을 엄격히 분리하여 각 모듈이 독립적으로 테스트 가능하도록 설계한다. 상태 전이는 단방향 흐름(game rules → game ui)을 따르며, UI는 game rules 모듈의 반환값만을 기반으로 DOM을 갱신한다.

---

## 수정 대상 모듈

| 모듈 | 파일 | 역할 |
|------|------|------|
| game ui | `game/index.html`, `game/js/ui.js`, `game/css/style.css` | 카드 렌더링, 베팅 컨트롤, 게임 보드 레이아웃, DOM 갱신 |
| game rules | `game/js/poker-rules.js` | 덱 관리, 핸드 평가, 상태 전이, AI 액션, 팟 계산 |
| test checklist | `game/tests/test-checklist.md` | 15개 이상 항목의 통합 검증 체크리스트 |

---

## 데이터 흐름

```
사용자 액션 (클릭)
    │
    ▼
[game ui] → dispatchAction(action, amount?)
    │
    ▼
[game rules] applyAction(action, amount)
    │  ├─ 상태 전이 (Pre-Flop → Flop → Turn → River → Showdown)
    │  ├─ AI 액션 자동 처리 (콜/체크 우선, 10% 폴드)
    │  └─ 반환: GameState 객체
    │
    ▼
[game ui] renderState(gameState)
    │  ├─ 카드 DOM 갱신
    │  ├─ 팟·칩 수치 갱신 (200ms 이내)
    │  └─ 버튼 활성화/비활성화
```

---

## 인터페이스 영향

### game rules 공개 API

```javascript
// 초기화
const game = createGame({ startingChips: 1000, bigBlind: 20 });

// 플레이어 액션 처리
const newState = game.applyAction({ action: 'bet' | 'call' | 'fold' | 'check' | 'raise', amount?: number });

// 핸드 평가 (FR-2.2 ~ FR-2.4 이행)
// 입력: 7장 카드 배열 ['Ah','Kh','Qh','Jh','Th','2d','3s']
// 출력: { rank: number, name: string, cards: Card[] }
//        rank: 0(High Card) ~ 9(Royal Flush) 숫자 오름차순
const result = evaluateHand(cards);

// 두 핸드 비교 — 키커·동점 처리 포함
// 반환: 1(hand1 승), -1(hand2 승), 0(Split Pot)
const cmp = compareHands(hand1, hand2);
```

### 핸드 랭킹 번호 체계 (spec.md FR-2.3과 동일)

| rank (number) | name (string) |
|---------------|---------------|
| 0 | high_card |
| 1 | one_pair |
| 2 | two_pair |
| 3 | three_of_a_kind |
| 4 | straight |
| 5 | flush |
| 6 | full_house |
| 7 | four_of_a_kind |
| 8 | straight_flush |
| 9 | royal_flush |

### GameState 객체 구조 (spec.md Inputs and Outputs와 동일)

```javascript
{
  phase: 'pre-flop' | 'flop' | 'turn' | 'river' | 'showdown' | 'end',
  players: [
    { id, chips, hand: Card[], bet, folded, isAllIn }
  ],
  communityCards: Card[],   // Flop 3장, Turn +1장, River +1장
  pot: number,
  sidePots: [{ amount, eligiblePlayers }],
  currentPlayer: number,
  winner: null | number | 'split',
  isAllIn: boolean
}
```

---

## 상태 및 데이터 모델

### Card 타입

```javascript
// 문자열 표기: 랭크(A,2~9,T,J,Q,K) + 수트(h,d,c,s)
// 예: 'Ah' = Ace of Hearts, 'Td' = Ten of Diamonds
```

### 상태 전이 규칙 (FR-2.5 이행)

| 전이 트리거 | 전이 방향 |
|-------------|----------|
| 양측 베팅 금액 동일 + 액션 완료 | 현재 단계 → 다음 단계 |
| 한쪽 Fold | 즉시 → Showdown |
| 올인 발생 | 남은 베팅 단계 스킵 → 커뮤니티 카드 모두 공개 → Showdown |

### AI 전략 (FR-2.8 이행)

- 보유 칩 충분 시: 90% 확률 Call 또는 Check, 10% 확률 Fold
- Bet/Raise 없음
- 별도 ML 모델 사용 없음

---

## 호환성 고려사항

- **브라우저**: Chromium 기반 최신 브라우저 (NFR-3)
- **Node.js 실행**: `poker-rules.js`는 DOM API 참조 없이 Node.js에서도 실행 가능해야 함 (NFR-2, FR-2.6)
- **외부 의존성 없음**: `<script>` 태그 단독 로드 가능한 vanilla JS (NFR-1)

---

## 마이그레이션 필요 여부

신규 구현. 마이그레이션 대상 기존 코드 없음.

---

## 리스크

| 리스크 | 영향 | 완화 방법 |
|--------|------|----------|
| rule evaluation bug — 핸드 비교 엣지케이스(동점, 키커, 사이드 팟) 오평가 | 승자 결정 오류 | 10종 핸드 랭킹 전부 + 동점/키커/올인 케이스를 test checklist에 명시적으로 포함 |
| 상태 전이 경쟁 조건 (연속 클릭) | 게임 상태 불일치 | 액션 처리 중 버튼 비활성화 (FR-1.2) |

---

## 대안 비교

| 방안 | 선택 여부 | 이유 |
|------|----------|------|
| Vanilla JS (채택) | ✅ | tech_stack 제약 준수 (NFR-1), 외부 의존성 없음 |
| React/Vue | ❌ | tech_stack 제약 위반 |
| 이벤트 버스 패턴 | ✅ | game ui ↔ game rules 결합도 최소화, 모듈 격리 유지 |
| 직접 DOM 참조 (game rules 내부) | ❌ | NFR-2·FR-2.6 위반 — Node.js 실행 불가 |

---

## 테스트 전략

test checklist (`game/tests/test-checklist.md`) 기반 수동+자동 혼합 검증:

| 카테고리 | 항목 수 | 검증 방법 |
|----------|---------|----------|
| 핸드 랭킹 평가 (10종 전부) | ≥ 10 | `node -e` 스크립트로 각 핸드 rank 반환값 확인 |
| 키커·동점(Split Pot) 처리 | ≥ 3 | `compareHands` 직접 호출 결과 비교 |
| 상태 전이 시나리오 | ≥ 5 | 각 전이 트리거별 `gameState.phase` 값 확인 |
| UI 렌더링 | ≥ 3 | 브라우저에서 DOM 요소·버튼 상태 시각 확인 |
| 엣지 케이스 (올인·사이드 팟·Fold) | ≥ 3 | `gameState.sidePots` 배열·버튼 `disabled` 확인 |

전체 항목 수 ≥ 15 (QA Engineer scope task 수용 기준 이행).
