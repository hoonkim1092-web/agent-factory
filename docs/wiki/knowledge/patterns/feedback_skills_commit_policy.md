---
name: skills/ 폴더 커밋·푸시 정책
description: skills/ 변경 사항은 hook 자동 갱신본까지 모두 커밋·푸시 대상
type: feedback
originSessionId: 9027e693-3036-4b9e-a3f7-20643cf194f0
---
skills/ 폴더(`skills/registry.yaml`, `skills/<name>/meta.yaml`, `skills/<name>/skill-spec.yaml`, `skills/<name>/evals.yml`, `skills/new_skill/skill-eval-report.json`, `skills/new_skill/skill-promotion.json` 등)는 변경이 감지되면 즉시 커밋·푸시한다.

**Why**: skills/ 파일들은 FSA 스킬 진화 파이프라인의 상태 + 정의를 담고 있어 PC 간 동기화 끊김 = 평가 히스토리 손실. hook이 자동으로 수정만 하고 커밋은 안 하는 경우가 있어 명시적으로 커밋해야 함.

**How to apply**:
- core/*.py 커밋 직후 `git status -s skills/`에 변경이 보이면 같은 세션에서 별도 `chore(skills): ...` 커밋으로 처리
- 다른 chore 묶음(docs+skills 등)에 함께 포함해도 무방
- data/skill-usage.jsonl, skill-eval-report.json도 동일 정책 (skills 평가 데이터)
