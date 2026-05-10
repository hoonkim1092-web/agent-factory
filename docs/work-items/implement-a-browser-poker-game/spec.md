# Feature Spec

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | implement-a-browser-poker-game |
| source_plan | Feature Plan — 2026-05-09 |
| status | pending |
| last_updated | 2026-05-09 |

---

## Feature Overview

브라우저에서 동작하는 싱글 플레이어 포커 게임을 Vanilla JS로 구현한다. 게임 상태는 모듈 단위(`game ui`, `game rules`)로 분리되어 각 모듈이 독립적으로 배포·검증 가능하도록 설계한다. 텍사스 홀덤 규칙을 기본 변형으로 채택하며, 모든 게임 상태는 메모리 내에서 관리된다. AI 상대는 규칙 기반 단순 전략(콜·체크 우선, 랜덤 폴드)으로 동작하며 별도 ML 모델을 사용하지 않는다.

---

## User Scenarios

### 시나리오 1 — 게임 시작 및 카드 딜

사용자가 브라우저에서 게임을 열면 덱이 셔플되고, 스몰 블라인드·빅 블라인드가 자동 공제된 후 플레이어와 AI 상대에게 각 2장의 홀 카드가 배분된다. 사용자는 자신의 핸드를 화면에서 확인할 수 있으며, AI의 카드는 뒷면으로 표시된다.

### 시나리오 2 — 베팅 라운드 진행

플레이어는 각 베팅 라운드에서 Check, Bet, Call, Raise, Fold 중 하나를 선택한다. 선택에 따라 게임 상태가 다음 단계로 전이된다. Bet/Raise 입력 시 베팅 금액은 최솟값(빅 블라인드 이상) 및 최댓값(보유 칩)으로 제한된다.

### 시나리오 3 — 커뮤니티 카드 공개

Flop, Turn, River 단계에서 커뮤니티 카드가 순차적으로 공개된다. 각 단계 진입 전에 해당 라운드의 AI 베팅 액션이 먼저 처리된다. UI는 각 단계에서 화면을 자동 갱신한다.

### 시나리오 4 — 쇼다운 및 승자 결정

베팅 라운드 종료 후 쇼다운이 발생하면, 룰 엔진이 각 플레이어의 핸드를 평가하고 승자를 결정한다. 동점이면 팟을 균등 분배하고 "Split Pot"을 표시한다. 결과가 화면에 명확히 표시된다.

### 시나리오 5 — 새 게임 시작

게임 종료 후 플레이어는 새 게임을 시작할 수 있다. 이전 게임 상태는 완전히 초기화된다.

### 시나리오 6 — 블라인드 수집 및 Pre-Flop 진입

게임 시작 시 딜러 버튼을 기준으로 스몰 블라인드(SB = bigBlind / 2)와 빅 블라인드(BB)가 자동 공제되어 팟에 합산된다. 블라인드 공제 후 Pre-Flop 베팅 라운드가 시작되며, 플레이어에게 현재 팟 크기와 콜 금액이 표시된다.

---

## Functional Requirements

### FR-1: game ui 모듈

| ID | 요구사항 |
|----|----------|
| FR-1.1 | 52장 덱을 화면에 렌더링하고, 플레이어 핸드와 커뮤니티 카드를 구분하여 표시한다. AI 상대의 홀 카드는 쇼다운 전까지 뒷면으로 표시한다. |
| FR-1.2 | 베팅 액션 버튼(Check, Bet, Call, Raise, Fold)을 현재 게임 상태에 따라 활성화/비활성화한다. |
| FR-1.3 | Flop, Turn, River 각 단계의 커뮤니티 카드를 순차적으로 공개한다. |
| FR-1.4 | 쇼다운 결과(승자, 핸드 랭킹, AI 홀 카드 공개)를 화면에 표시한다. |
| FR-1.5 | 새 게임 시작 버튼을 제공하며, 클릭 시 게임 상태를 완전 초기화한다. |
| FR-1.6 | 현재 팟 크기와 각 플레이어의 잔여 칩을 실시간으로 표시한다. 베팅 액션 후 200ms 이내에 수치가 갱신된다. |
| FR-1.7 | Bet/Raise 입력 시 금액 입력 필드를 표시하며, 입력값이 최솟값(빅 블라인드) 미만이거나 보유 칩 초과인 경우 즉시 오류 메시지를 표시한다. |

### FR-2: game rules 모듈

| ID | 요구사항 |
|----|----------|
| FR-2.1 | 표준 52장 덱에서 카드를 셔플하고 배분하는 함수를 제공한다. |
| FR-2.2 | 홀 카드 2장 + 커뮤니티 카드 5장 총 7장에서 C(7,5)=21가지 조합 전부를 평가하여 최선의 5장 조합으로 핸드 랭킹을 결정한다. |
| FR-2.3 | 핸드 랭킹 우선순위: Royal Flush > Straight Flush > Four of a Kind > Full House > Flush > Straight > Three of a Kind > Two Pair > One Pair > High Card. |
| FR-2.4 | 동점 시 Kicker 규칙으로 승자를 결정한다. Kicker까지 동일하면 Split Pot을 반환한다. |
| FR-2.5 | 게임 상태 전이(Pre-Flop → Flop → Turn → River → Showdown → End)를 관리하는 상태 머신을 포함한다. 전이 트리거: (a) 양측 베팅 금액이 동일해지고 액션이 완료되면 다음 단계로 진입, (b) 한쪽이 Fold하면 즉시 Showdown으로 전이, (c) 올인 발생 시 남은 베팅 단계를 건너뛰고 커뮤니티 카드를 모두 공개한 뒤 Showdown 진입. |
| FR-2.6 | game rules 모듈은 UI 코드에 의존하지 않고 독립 실행 가능해야 한다. DOM API(`document`, `window`, `HTMLElement` 등)를 직접 참조하지 않는다. |
| FR-2.7 | 팟 계산, 블라인드 설정(SB = bigBlind / 2, BB = bigBlind), 올인 처리 로직을 포함한다. 올인 시 초과 금액은 사이드 팟으로 분리한다. |
| FR-2.8 | AI 상대는 규칙 기반 단순 전략으로 동작한다: 보유 칩이 충분하면 항상 Call 또는 Check, 10% 확률로 Fold. Bet/Raise는 하지 않는다. AI 전략 로직은 game rules 모듈 내부에 포함하며 별도 ML 모델을 사용하지 않는다. |

### FR-3: test checklist 모듈

| ID | 요구사항 |
|----|----------|
| FR-3.1 | 핵심 게임플레이 경로(딜 → 블라인드 수집 → 베팅 → 쇼다운)를 항목으로 포함하는 체크리스트를 작성한다. |
| FR-3.2 | 각 핸드 랭킹(10종)에 대한 평가 정확성 검증 항목을 포함한다. |
| FR-3.3 | 상태 전이 시나리오별 예상 동작(전이 트리거, 진입 단계, 사이드 이펙트)을 명시한다. |
| FR-3.4 | 승자 결정 엣지 케이스(동점/Split Pot, 올인, 사이드 팟)를 항목으로 포함한다. |
| FR-3.5 | AI 행동 검증 항목(콜/체크 우선, 10% 폴드 확률 범위)을 포함한다. |

---

## Non-Functional Requirements

| ID | 요구사항 |
|----|----------|
| NFR-1 | **기술 스택 제한** — 구현에 Vanilla JS만 사용한다. React, Vue, jQuery 등 외부 프레임워크 사용 금지. |
| NFR-2 | **모듈 격리** — game rules 모듈은 DOM API에 의존하지 않으며 Node.js 환경에서도 실행 가능해야 한다. |
| NFR-3 | **브라우저 호환성** — Chromium 기반 최신 브라우저에서 동작해야 한다. |
| NFR-4 | **상태 무결성** — 유효하지 않은 액션(예: 칩 부족 시 Raise, Fold 후 재액션)은 게임 상태를 변경하지 않는다. |
| NFR-5 | **응답성** — 사용자 액션(버튼 클릭)부터 DOM 갱신 완료까지 200ms 이내에 반영된다. `performance.now()`로 측정한 경과 시간이 기준. |
| NFR-6 | **메모리 관리** — 게임 상태는 메모리 내에서만 관리하며 영속 스토리지(localStorage 등)를 사용하지 않는다. |

---

## Inputs and Outputs

### game ui 모듈

| 방향 | 항목 | 설명 |
|------|------|------|
| 입력 | 게임 상태 객체 | game rules 모듈이 반환하는 현재 게임 상태 |
| 입력 | 사용자 액션 이벤트 | 버튼 클릭(Check, Bet, Call, Raise, Fold, New Game) |
| 입력 | 베팅 금액 | Bet/Raise 시 숫자 입력값. `bigBlind` 이상, 보유 칩 이하 |
| 출력 | DOM 갱신 | 카드 렌더링, 팟 표시, 버튼 상태, 결과 화면 |
| 출력 | 액션 디스패치 | 사용자 선택을 game rules 모듈에 전달 |

### game rules 모듈

| 방향 | 항목 | 설명 |
|------|------|------|
| 입력 | 초기화 파라미터 | `{ startingChips: number, bigBlind: number }` |
| 입력 | 플레이어 액션 | `{ action: 'bet' \| 'call' \| 'fold' \| 'check' \| 'raise', amount?: number }` — amount는 bet/raise 시 필수. `bigBlind` 이상, 보유 칩 이하 |
| 출력 | 게임 상태 객체 | `{ phase, players, communityCards, pot, sidePots, currentPlayer, winner, isAllIn }` |
| 출력 | 핸드 평가 결과 | `{ rank: number, name: string, cards: Card[] }` — rank 0(High Card)~9(Royal Flush) |

### test checklist

| 방향 | 항목 | 설명 |
|------|------|------|
| 입력 | game ui 및 game rules의 scope 단계 완료 결과 | 기능 경계와 인터페이스 계약 |
| 출력 | 체크리스트 문서 | 항목별 검증 방법, 예상 결과, 엣지 케이스 포함 |

---

## Exceptions and Failure Scenarios

| ID | 시나리오 | 예상 동작 |
|----|----------|----------|
| E-1 | 플레이어가 보유 칩보다 큰 금액으로 Bet 시도 | 액션을 거부하고 UI에 오류 메시지 표시. 게임 상태 변경 없음. |
| E-2 | Fold 후 해당 플레이어가 액션을 시도 | fold된 플레이어는 액션 불가. 버튼 비활성화. |
| E-3 | 덱 카드 부족 (이론상 발생 불가) | 방어 코드로 콘솔에 에러를 기록하고 새 게임 시작을 안내. |
| E-4 | 동점 쇼다운 (두 플레이어 핸드가 완전 동일) | 팟을 균등 분배하고 "Split Pot" 결과를 화면에 표시. |
| E-5 | 올인 후 사이드 팟 생성 | 메인 팟과 사이드 팟을 `sidePots` 배열로 별도 계산하여 각 승자에게 지급. 화면에 메인 팟·사이드 팟 금액을 분리 표시. |
| E-6 | 브라우저 새로고침 | 게임 상태 초기화. 영속 스토리지 미사용으로 이전 상태 복원 불가 — 이는 의도된 동작. |
| E-7 | Bet/Raise 금액이 bigBlind 미만 | 액션을 거부하고 "최소 베팅은 빅블라인드(N)입니다" 오류 메시지 표시. 게임 상태 변경 없음. |

---

## Existing Behavior To Preserve

현재 구현이 없는 신규 기능이므로 보존해야 할 기존 동작은 없다. 단, `docs/architecture.md` §Modules에 정의된 모듈 분리 원칙을 위반하지 않는다.

---

## Acceptance Criteria

| ID | 기준 | 검증 방법 |
|----|------|----------|
| AC-1 | game ui 모듈이 브라우저에서 카드를 렌더링하고 베팅 버튼을 표시한다. | 브라우저에서 `index.html` 열기 → 카드 및 버튼 시각 확인 |
| AC-2 | game rules 모듈이 DOM 없이 독립 실행 가능하다. | Node.js에서 `node game_rules.js` 실행 → 에러 없이 종료. `grep -r "document\." game_rules.js`로 DOM 참조 부재 확인 |
| AC-3 | 10종 핸드 랭킹(Royal Flush ~ High Card)이 모두 올바르게 평가된다. | 각 핸드에 대해 `evaluateHand()` 호출 → 예상 rank(0~9) 반환 확인 |
| AC-4 | 게임 상태가 Pre-Flop → Flop → Turn → River → Showdown 순서로 전이된다. | 베팅 완료 시마다 `gameState.phase` 값 검증 |
| AC-5 | 동점 시 팟이 균등 분배된다. | 동일 핸드 시나리오 실행 → `pot` 분배 결과 및 "Split Pot" UI 텍스트 확인 |
| AC-6 | Fold 후 해당 플레이어의 액션 버튼이 비활성화된다. | Fold 버튼 클릭 후 액션 버튼 `disabled` 속성 확인 |
| AC-7 | 새 게임 시작 버튼 클릭 시 모든 게임 상태가 초기값으로 리셋된다. | 게임 진행 중 New Game 클릭 → 초기 화면 렌더링 및 `gameState.phase === 'pre-flop'` 확인 |
| AC-8 | test checklist가 딜, 블라인드 수집, 베팅, 쇼다운 네 경로를 모두 포함한다. | 체크리스트 문서 항목 수동 검토 |
| AC-9 | 각 모듈의 verify 단계 완료 후 handoff 메모(잔여 리스크, 후속 작업)가 남겨진다. | 각 모듈 verify 태스크 산출물에 handoff 메모 존재 확인 |
| AC-10 | 칩 부족 시 Bet/Raise 액션이 거부되고 게임 상태가 변경되지 않는다. | 잔여 칩 0인 상태에서 Bet 시도 → `gameState` 불변 확인 |
| AC-11 | 사용자 액션 후 DOM 갱신이 200ms 이내에 완료된다. | `performance.now()`로 버튼 클릭부터 팟·칩 수치 DOM 반영까지 경과 시간 측정 → 200ms 미만 |
| AC-12 | 팟 크기와 각 플레이어 잔여 칩이 베팅 액션 후 즉시 갱신된다. | Bet/Call 액션 후 화면의 팟 수치와 `gameState.pot` 값 일치 확인 |
| AC-13 | 올인 시 사이드 팟이 별도 계산되고 화면에 분리 표시된다. | 올인 시나리오 실행 → `gameState.sidePots` 배열 비어있지 않음 + UI에 메인/사이드 팟 금액 분리 렌더링 확인 |
| AC-14 | AI 상대가 규칙 기반 전략(콜/체크 우선)으로 자동 액션을 수행한다. | AI 턴 시 콘솔 또는 상태 로그에서 액션이 'call' 또는 'check'임을 50회 반복 실행 중 최소 85% 이상 확인 |
| AC-15 | Bet/Raise 금액이 bigBlind 미만이면 거부되고 오류 메시지가 표시된다. | bigBlind=20 설정 후 amount=10으로 Bet 시도 → 게임 상태 불변 + 오류 메시지 DOM 렌더링 확인 |

---

## Evidence

### 로컬 참고

| 경로 | 섹션 | 핵심 내용 | 관련성 |
|------|------|-----------|--------|
| `docs/architecture.md` | `# Modules` | 게임 상태는 모듈 단위로 분리된다 | 0.90 |

### 웹 참고

| 제목 | 핵심 내용 | 관련성 |
|------|-----------|--------|
| Poker rules | 상태 전이와 승자 평가를 검증한다 | 0.80 |

### 노트북 요약

> 격리된 게임 룰 모듈과 명시적 검증 체크포인트를 선호한다.

---

## References

- `docs/architecture.md` §Modules — 모듈 분리 설계 원칙
- Poker rules (web reference) — 표준 텍사스 홀덤 상태 전이 및 핸드 평가 명세
- Feature Plan (2026-05-09) — 역할 배정, 실행 전략, 리스크 분석

---

## Out Of Scope

- 멀티플레이어 실시간 네트워크 대전
- 서버 사이드 로직 및 백엔드 API
- React, Vue 등 외부 JS 프레임워크 사용
- 실제 머니 결제 또는 도박 기능
- 모바일 앱 배포
- localStorage 또는 외부 DB를 이용한 게임 상태 영속화
- CI/CD 파이프라인 구성
- 디자인 시스템 또는 공식 스타일 가이드 수립
- Omaha, Seven-Card Stud 등 텍사스 홀덤 이외 포커 변형
- ML/AI 모델 기반 고급 AI 상대
