---
name: 산출물 양식 vs 깊이 진단 구분
description: 사용자가 "시뮬레이션/분석/아키텍처 해줘" 같은 동사를 써도 메타 명령일 수 있음. 양식 분기 처방으로 뛰기 전 동일 build prompt 결과를 먼저 비교할 것.
type: feedback
originSessionId: 0cab285b-626b-434f-9311-64134441d5e4
---
## Rule

품질 격차 진단 시 "사용자가 양식 X를 원했다"고 결론짓기 전에, **사용자가 실제로 build 결과만 본 적이 있는지** 확인할 것. 동일 build prompt 빌드본 결과와 비교해서 격차가 같은 수준이면 진단축은 양식이 아니라 **깊이·근거**.

**Why**: 2026-05-04 AF vs Manus 포커 시나리오 격차 분석에서, 사용자가 "시뮬레이션 해서 알려줘"라 입력 → 내가 "사용자가 시뮬레이션 양식을 원함" → "intent-routed 산출 양식 분기"를 본질 해결책으로 진단. 실제로는 사용자가 "AF 정상 작동 테스트" 메타 명령을 한 것이고, 빌드 배포본에 build prompt 직접 입력 시에도 동일 4-doc 보일러플레이트 산출 → 양식 분기 무관, 격차의 본체는 evidence depth + 도메인 명세 강제 부재. 진단축이 빗나가서 1-2주짜리 처방을 잘못 권고할 뻔함.

**How to apply**:
- 외부 에이전트(Manus, Cursor 등) 산출물과 AF 비교 시 입력 단순화: 같은 build prompt를 두 곳에 넣고 결과 비교
- 사용자가 "시뮬레이션/분석/아키텍처/런북" 같은 동사를 써서 격차를 호소하면, 첫 질문: "build prompt 직접 입력 시에도 같은 격차였나요?"
- 격차가 같으면 → 깊이·근거 진단축 (evidence/coverage/spec)
- 격차가 다르면 → 양식 분기 진단축 (intent routing)
- 진단을 명확히 분리해야 처방이 surgical해짐
- 관련 문서: `docs/2026-05-04-poker-scenario-af-vs-manus-gap-analysis.md` §7.1 (양식 분기 ④ 폐기 사유)
