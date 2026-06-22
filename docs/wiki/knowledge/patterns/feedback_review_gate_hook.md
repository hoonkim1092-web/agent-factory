---
name: Review-Gate Hook 동작 방식과 우회 방법
description: AF_SKIP_REVIEW_GATE=1 인라인 env var가 PreToolUse hook에서 무시되는 이유 + 올바른 우회법
type: feedback
originSessionId: a6fd8482-d129-4d32-acd8-aa4a6d431b18
---
PreToolUse hook은 Claude Code가 별도 Python subprocess로 실행한다. 따라서 Bash 명령어 안에 인라인으로 쓴 `AF_SKIP_REVIEW_GATE=1 git commit ...`은 **hook subprocess의 `os.environ`에 전달되지 않는다**.

2026-04-20 수정: `scripts/hook_runner.py`의 `_pre_bash_review_gate()`가 명령어 문자열에서 `AF_SKIP_REVIEW_GATE=1`을 정규식으로 파싱해 우회를 감지하도록 수정됨 (커밋 `1f3fb884`). 이후로는 인라인 env var 방식이 정상 동작한다.

**Why:** 이전에는 `AF_SKIP_REVIEW_GATE=1 git commit ...` 커맨드를 써도 hook이 계속 BLOCK하는 문제가 있었고, 이것이 무한 루프처럼 보였다.

**How to apply:**
- `AF_SKIP_REVIEW_GATE=1 git commit ...` — 인라인으로 사용 가능 (수정 후)
- hook 동작 이상 시 `python3 scripts/review_gate.py --debug` 로 진단
- Agent 툴(af-test-runner 등)이 hook에 의해 막힐 경우 → hook이 Agent 툴을 가로채는 것이 아니라, 게이트 상태 파일의 stale-review 때문임. 파일 수정 후에는 3-tier 리뷰를 다시 돌려야 함.
