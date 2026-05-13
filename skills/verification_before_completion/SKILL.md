---
id: verification_before_completion
name: Verification Before Completion
version: 0.1.0
inspired_by: superpowers/verification-before-completion
description: Iron Law — 검증 완료 전 완료 선언 금지. 12개 합리화 패턴을 차단하고 실제 완료 기준을 강제한다.
when_to_use: 작업이 "거의 다 됐다"고 느껴질 때. 완료를 선언하기 직전. PR 제출 전. 테스트를 건너뛰고 싶을 때.
when_NOT_to_use: 작업 초기 탐색·설계 단계.
when_to_use_keywords:
  - 완료
  - 검증
  - 확인
  - done
  - complete
  - PR
  - 제출
  - 배포
  - 마무리
  - finished
category: quality
skill_type: knowledge
auto_invocable: true
user_invocable: true
planner_invocable: true
tags:
  - verification
  - quality
  - iron-law
  - completion
---

# Verification Before Completion 가이드

## Iron Law

> **검증을 완료하기 전에는 절대 작업이 완료됐다고 선언하지 않는다.**

완료 선언은 다음 두 조건을 모두 충족해야 한다:

1. **기능 완료**: 요청된 기능이 실제로 동작한다 (테스트 또는 직접 확인).
2. **회귀 없음**: 기존 테스트 전부 PASS.

---

## 완료 기준 체크리스트

작업 종류별 완료 기준:

**코드 수정**
- [ ] 변경된 기능을 직접 실행해서 확인
- [ ] 관련 단위 테스트 PASS
- [ ] `pytest` 전체 실행 — 회귀 없음
- [ ] `core/*.py` 수정 시 Blueprint §해당섹션 + §12 이력 업데이트

**버그 수정**
- [ ] 버그 재현 테스트 작성 후 PASS
- [ ] `pytest` 전체 실행 — 회귀 없음

**문서·설계**
- [ ] 내용이 현재 코드 상태와 일치 (grep으로 확인)
- [ ] 교차 참조 링크 유효

---

## 12개 합리화 패턴 (차단 목록)

완료 선언 전 아래 생각이 든다면 멈추고 실제로 확인한다:

1. "테스트는 나중에 추가하면 되니까" → **지금 추가한다.**
2. "이 경우는 발생하지 않을 테니까" → **발생 조건을 명시하고 검증한다.**
3. "기존 테스트가 커버하겠지" → **`pytest -k 관련_키워드`로 확인한다.**
4. "간단한 변경이니까 테스트 불필요" → **간단할수록 테스트가 빠르다. 지금 쓴다.**
5. "이미 수동으로 확인했으니까" → **자동 테스트로 보완한다.**
6. "리뷰어가 잡겠지" → **리뷰어의 역할은 설계 검토, 내 검증 대체가 아니다.**
7. "CI가 돌 테니까" → **로컬에서 먼저 PASS 확인 후 푸시한다.**
8. "타임 프레셔가 있으니까" → **회귀 버그 수정 비용이 더 크다.**
9. "이전에도 이렇게 했으니까" → **과거의 나쁜 습관은 전례가 아니다.**
10. "이 모듈은 잘 안 바뀌니까" → **변경하지 않는다면 수정할 이유도 없었다.**
11. "타입 체커가 통과했으니까" → **타입 정확성 ≠ 기능 정확성.**
12. "PR 설명에 TODO로 남겼으니까" → **TODO는 완료 대체가 아니다.**

---

## 검증 명령어 모음

```bash
# 전체 테스트
pytest

# 특정 파일 관련 테스트만
pytest tests/ -k "파일명_키워드"

# 실패 시 즉시 중단 + 상세 출력
pytest -x -v

# 커버리지 확인
pytest --cov=core --cov-report=term-missing
```
