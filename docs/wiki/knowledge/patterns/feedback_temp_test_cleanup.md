---
name: 임시/스크래치 테스트 정리 정책
description: 일회성 테스트 파일은 사용 종료 후 삭제 또는 tests/_tmp/ 이동, git 동기화 차단
type: feedback
originSessionId: 9027e693-3036-4b9e-a3f7-20643cf194f0
---
검증·실험 목적의 일회성 테스트 파일은 사용이 끝나면 삭제하거나 git에서 추적되지 않도록 처리한다.

**Why**: 사용 끝난 임시 테스트가 `tests/`에 untracked로 남으면 매 세션 git status를 오염시키고, 무심코 커밋되면 CI에서 의도 불명 실패를 만든다. 다른 PC와의 git pull 동기화 정합성을 떨어뜨린다.

**How to apply**:
- 회귀 방지가 목적이고 production 코드와 함께 유지보수할 테스트 → 정상 커밋 (`tests/test_*.py`)
- 일회성 reproducer / TDD draft / 실험 검증 → 다음 중 하나:
  1. 사용 후 삭제
  2. `tests/_tmp/` 또는 `tests/_tmp_probe/` 이동 (`.gitignore`에 이미 등록됨)
- "test가 끝났다" 판단 기준: 사용자가 명시적으로 정리 지시하거나, 동일 기능에 대한 정식 테스트가 다른 위치에 안정적으로 존재할 때
- 4개 untracked 테스트 파일이 어느 브랜치에도 커밋된 적 없으면 (git log --all 0건) 일회성 가능성 높음 — 사용자에게 처리 방향 확인
