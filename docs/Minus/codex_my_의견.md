AF 문서상 있는 기능과 실제 부족한 부분

문서에는 분명 리서치 관련 모듈이 있어.

core/research_router.py는 project research mode 분류와 complexity gap 탐지를 담당하고, core/researcher.py는 Himari 리서치 에이전트로 로컬+웹+NotebookLM 기반 source pack 조립과 structured evidence normalizer를 담당한다고 되어 있어.

그런데 실제 품질이 Manus처럼 안 나왔다면, 부족한 건 모듈 존재가 아니라 배선 강도야.

즉 이런 차이.

구분	현재 AF 가능성	Manus식 필요 구조
리서치 모듈	있음	있음
리서치 강제 여부	약함	강함
출처 충분성 평가	약함	필수
부족 항목 재수집	약함	자동 반복
도메인 룰 추출	일반 LLM 요약	구조화 evidence
계획 생성 조건	바로 생성 가능	evidence gate 통과 후 생성
결과물	task board 중심	제품 기획서/명세 중심

까칠하게 말하면, 지금 AF는 “리서치할 수도 있는 개발 자동화 엔진”이고, Manus는 “리서치해서 계획부터 예쁘게 뽑는 범용 에이전트”에 가까운 거야.

이번 포커 요청에서 AF가 놓쳤을 가능성이 큰 지점

이 요청은 그냥 게임 만들기가 아니라 룰 검증형 프로젝트야.
그래서 AF가 처음부터 아래 질문을 강제로 던졌어야 해.

1. 기준 게임은 Texas Hold'em인가?
2. No-Limit / Pot-Limit / Fixed-Limit 중 무엇인가?
3. 8인 테이블에서 dealer button, small blind, big blind 이동 규칙은?
4. 초기 칩은 캐시게임 기준인가, 토너먼트 기준인가?
5. blind 증가가 있는가?
6. minimum raise 규칙은?
7. all-in과 side pot 처리는?
8. showdown과 hand ranking 기준은?
9. 서버가 어떤 이벤트를 검증하는가?
10. 클라이언트에 절대 노출하면 안 되는 정보는?

Manus는 이런 걸 “계획 품질”로 뽑아내는 데 강하고, AF는 아마 바로:

- 서버 구축
- 클라이언트 구축
- WebSocket 구현
- 게임 룸 구현
- 포커 로직 구현
- UI 구현

이렇게 작업분해로 빨리 갔을 가능성이 높아.

이러면 결과가 얕아져.
작업 목록은 맞는데, 게임 규칙 명세가 얕은 상태에서 개발 태스크가 만들어지는 것이 문제야.

AF에 필요한 수정 방향

AF가 Manus처럼 나오려면 “리서치 모듈 추가”가 아니라 Planning 앞에 Research Quality Gate를 넣어야 해.

추천 흐름은 이거야.

User Brief
  ↓
Intent Classifier
  ↓
Research Required? = YES
  ↓
Research Plan 생성
  ↓
Source Collection
  ↓
Evidence Matrix 생성
  ↓
Coverage 평가
  ↓
Gap 있으면 재수집
  ↓
Domain Specification 생성
  ↓
Architecture Plan 생성
  ↓
Task Board 생성

지금 AF의 ProjectPipeline.prepare()는 research brief, role plan, task board, work item을 만드는 흐름이지만, 여기에 Evidence Matrix와 Coverage Gate가 들어가야 한다는 뜻이야.

포커게임 케이스 전용으로는 이렇게 강제해야 함

AF가 네 입력을 받으면 바로 task board 만들지 말고, 먼저 이런 중간 산출물을 생성해야 해.

docs/research/poker-rule-sources.md
docs/research/poker-rule-evidence.json
docs/specs/poker-rules-spec.md
docs/specs/betting-state-machine.md
docs/specs/server-authoritative-architecture.md
docs/specs/websocket-event-protocol.md
docs/specs/client-view-model.md

그리고 poker-rules-spec.md가 없으면 구현 task를 만들면 안 돼.

즉 이런 게이트가 필요해.

Implementation task generation is blocked until:
- rule baseline selected
- betting model defined
- side pot policy defined
- server authoritative boundary defined
- WebSocket event contract defined
- responsive client view model defined

이게 없으면 AF는 그냥 “게임 만들어줘”를 일반 개발 태스크로 쪼갠다.
그러면 Manus 같은 고품질 기획은 안 나와. 당연함.

핵심 차이 한 줄

Manus는 “계획을 만들기 위해 리서치”하고,
현재 AF는 “구현하기 위해 작업을 분해”하는 쪽에 더 가깝다.

둘 다 에이전트지만 목적 함수가 달라.

Manus는 사용자에게 먼저 “그럴듯한 전략/계획/조사 결과”를 보여주는 데 최적화되어 있고, AF는 실제 코드 실행·실패 복구·리뷰 게이트 쪽에 더 많은 설계가 들어가 있다. AF 문서만 봐도 DynamicOrchestrator, AgentRunner, FSA/ISE, 스킬 시스템, review gate, PyInstaller, CLI provider 같은 실행 계층이 매우 두껍다.

AF를 Manus처럼 만들려면 붙여야 하는 기능명

나는 이걸 이렇게 넣는 게 맞다고 봐.

1. ResearchFirstPlanner

요구사항에서 리서치 필요성을 먼저 판정.

requires_research = true
domain = "online poker game"
research_depth = "deep"
2. EvidenceMatrix

출처 기반 claim 저장.

{
  "claim": "No-Limit Texas Hold'em uses blinds and four betting rounds",
  "source": "WSOP/PokerStars/etc",
  "confidence": 0.9,
  "applies_to": "game_rule"
}
3. CoverageGate

필수 항목이 비면 계획 생성 차단.

BLOCKED:
- side pot rule missing
- minimum raise rule missing
- blind structure missing
4. RecoverySearchLoop

부족 항목만 재수집.

Missing: side pot
→ Search: "official side pot rules Texas Hold'em"
→ Search: "PokerStars side pot all-in rules"
→ Summarize
→ update evidence
5. SpecBeforeTasks

구현 태스크 전, 도메인 명세 필수 생성.

rules spec → architecture spec → task board
결론

네 테스트 결과는 AF의 한계를 잘 찌른 거야.

AF가 Manus처럼 안 된 이유는 리서치 능력이 아예 없어서가 아니라, 리서치가 “계획 생성의 필수 선행조건”으로 강하게 걸려 있지 않아서야.

현재 AF는:

요구사항 → 작업분해 → 실행

에 강하고,

Manus는:

요구사항 → 자료수집 → 분석 → 계획 → 실행

에 강하게 보인다.

AF가 범용 AI처럼 보이려면 첫 번째 수정은 이거야.

ProjectPipeline.prepare() 앞단에 ResearchFirstPlanner + Evidence/Coverage Gate를 넣어라.

그러면 포커게임 같은 요청에서 AF도 Manus처럼:

1. 공신력 있는 룰 조사
2. 기준 룰 선택
3. 베팅/칩/사이드팟 명세화
4. 서버 권위형 아키텍처 정리
5. HTML5 앱웹 클라이언트 계획
6. 구현 task board 생성

request-intake → project_brief.json 강화
research-plan/source-log/evidence-matrix → research_evidence.json 강화
coverage-report → 새 파일 추가
decision-record → 새 파일 추가
traceability → 새 파일 추가 권장

순서로 나오게 된다.

지금은 엔진은 좋은데, 생각하는 순서가 Manus식이 아니라 개발 오케스트레이터식이야.
이 순서만 바꾸면 결과 품질 확 올라간다. 🚀