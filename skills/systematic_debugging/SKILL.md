---
id: systematic_debugging
name: Systematic Debugging
version: 0.1.0
inspired_by: superpowers/systematic-debugging
description: 4단계 디버깅 프레임워크 — 근본원인 파악 → 패턴 분석 → 가설 수립 → 구현. AF 코드베이스에 버그·이상 동작이 발생했을 때 체계적으로 진단하는 가이드.
when_to_use: 버그 재현, 예상치 못한 동작, 테스트 실패, 런타임 오류 등 원인 불명의 문제에 직면했을 때.
when_NOT_to_use: 원인이 이미 명확한 단순 오타·설정 오류. 새 기능 설계 단계(brainstorming 사용).
when_to_use_keywords:
  - 버그
  - 오류
  - 디버깅
  - debug
  - error
  - traceback
  - 원인불명
  - 재현
  - 이상동작
  - 테스트실패
  - 회귀
  - regression
category: debugging
skill_type: knowledge
auto_invocable: true
user_invocable: true
planner_invocable: true
tags:
  - debugging
  - root-cause
  - systematic
---

# Systematic Debugging 가이드

## Phase 1 — 근본원인 파악 (Root Cause Identification)

**목표**: 증상이 아니라 원인을 찾는다.

1. **증상 문서화** — 오류 메시지, 스택 트레이스, 재현 조건을 그대로 기록한다. 요약·해석 없이.
2. **재현 스크립트 작성** — 버그를 최소 코드로 재현한다. 재현 불가면 환경 차이를 추적한다.
3. **변경 이력 확인** — `git log --oneline -20` 후 버그 발생 시점과 커밋을 대조한다.
4. **경계 확인** — 입력값·반환값·상태 변화를 각 함수 경계에서 확인한다 (print/assert/breakpoint).

> **금지**: "아마 X 때문일 것"으로 즉시 수정 진입. Phase 1 완료 전 코드 변경 금지.

---

## Phase 2 — 패턴 분석 (Pattern Analysis)

**목표**: 이 버그가 일회성인지, 시스템적 패턴인지 판단한다.

1. **유사 사례 검색** — `grep -rn "동일_에러_키워드" .` 로 동일 패턴이 다른 위치에도 있는지 확인한다.
2. **호출 스택 역추적** — 오류 지점에서 위쪽으로 역방향 탐색. 외부 입력이 어느 경계에서 오염되었는지 찾는다.
3. **인접 테스트 확인** — 관련 테스트가 있는가? 있다면 언제부터 실패했는가? (`git bisect` 활용).
4. **타입·계약 검토** — 타입 힌트, 전제조건(precondition), 사후조건(postcondition)이 실제 동작과 일치하는지.

---

## Phase 3 — 가설 수립 (Hypothesis Formation)

**목표**: 검증 가능한 가설을 1–3개 작성한다.

```
가설 1: [구체적 원인] — 검증 방법: [확인 단계]
가설 2: [구체적 원인] — 검증 방법: [확인 단계]
가설 3: [구체적 원인] — 검증 방법: [확인 단계]
```

**우선순위 기준**:
- 재현 빈도가 높은 경로
- 최근 변경된 코드 근처 (`git log -p` 비교)
- 테스트 커버리지가 낮은 영역

> **금지**: 가설 없이 "일단 수정해보자" 진입. 각 가설은 반증 가능해야 한다.

---

## Phase 4 — 구현 (Implementation)

**목표**: 가설을 검증하고, 수정하고, 회귀를 방지한다.

1. **가설 검증 먼저** — 가설 1부터 순서대로 검증. 반증되면 다음 가설로.
2. **최소 수정** — 확인된 원인만 수정한다. 인접 코드 "개선" 금지 (CLAUDE.md §Surgical Changes).
3. **재현 테스트 추가** — 버그를 재현하는 테스트를 먼저 작성 후 수정 (TDD).
4. **전체 테스트 실행** — 수정 후 `pytest` 전체 실행. 회귀가 없는지 확인.
5. **완료 선언** — 버그 재현 테스트가 PASS이고 기존 테스트 전부 PASS일 때만 완료.

---

## 체크리스트

작업 완료 전 확인:

- [ ] P1: 버그 재현 스크립트 작성 완료
- [ ] P1: `git log`로 변경 이력 확인
- [ ] P2: 동일 패턴 grep 완료
- [ ] P2: 호출 스택 역추적 완료
- [ ] P3: 검증 가능한 가설 1개 이상 작성
- [ ] P4: 가설 검증 후 수정
- [ ] P4: 재현 테스트 추가 + PASS
- [ ] P4: 전체 `pytest` PASS
