---
name: 테스트 mock과 실제 결함 구분
description: 의도적 mock(_DummyLLM 등 빈 응답 stub)을 "구조적 결함"으로 표현하지 말 것. 결함은 production 코드/assertion 정합성에 있음.
type: feedback
originSessionId: f70bd926-d96e-4d95-8760-12ae1b26f28f
---
테스트의 mock 객체(예: `_DummyLLM.generate_json` returning `{"next_tasks": []}`)는 **의도된 시뮬레이션 입력**이지 결함이 아니다. 실패 원인을 mock 자체로 돌리는 표현을 피한다.

**Why:** 2026-04-25 세션에서 `tests/test_orchestrator_manifest.py`의 pre-existing 실패를 "_DummyLLM 구조적 결함"으로 표현했을 때 사용자가 "근데 이거 말그대로 더미 아니야?"라고 반박. 진짜 원인은 둘 중 하나임:
1. **테스트 버그**: production 코드가 변경되어 더 일찍 return → assertion이 stale
2. **production 회귀**: 원래 자주 만들어지던 산출물(예: `dynamic_log.txt`)이 어느 리팩토링에서 조건이 좁아짐

mock의 의도와 production 흐름을 분리해서 진단해야 한다.

**How to apply:**
- 테스트 실패를 분석할 때 "mock이 X를 반환해서 실패함"이라고 끝내지 말고, "mock 입력 → production 흐름의 어느 분기 → assertion 미충족"의 3단계로 분해
- mock 자체를 "결함/구조적 문제"로 호명하기 전에, `git blame`/`git log --follow`로 production 코드 변경 이력과 테스트 작성 시점의 의도를 비교
- 특히 빈 컬렉션 반환(`[]`, `{}`)은 거의 항상 "아무 일도 안 일어나는 케이스"를 검증하기 위한 의도적 입력

## 관련
- [[code/symbols]]

