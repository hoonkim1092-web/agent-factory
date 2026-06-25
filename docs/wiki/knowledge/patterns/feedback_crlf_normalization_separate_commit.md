---
name: feedback-crlf-normalization-separate-commit
description: CRLF→LF 같은 대량 정규화 커밋은 기능 커밋과 절대 섞지 말고 단독 chore 커밋으로 분리한다.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0f077b88-91db-4871-8d2e-ea318fb8021c
---

CRLF→LF (또는 EOL/whitespace/format 일괄 정규화) 같은 대량 변경은 단독 `chore:` 커밋으로 분리한다. 기능 커밋과 절대 섞지 않는다.

**Why:** 2026-05-27 R1 11차에서 `c9138f07` 가 64파일 CRLF 정규화로 분리됐는데, 그 자체는 잘했지만 만약 기능 커밋과 섞였다면 리뷰 노이즈가 폭증하고 diff에서 실제 로직 변경을 찾기 어려워졌을 것. Mac→Windows pull 부산물처럼 환경 차이로 발생하는 정규화는 빈번하게 재발한다.

**How to apply:**
- 기능 작업 중 EOL/whitespace 대량 변경이 stage 에 보이면, 즉시 `git restore --staged` 로 빼고 별도 `chore: CRLF→LF 정규화` 커밋으로 처리.
- 한 커밋 안에서 `git diff --stat` 가 수십 파일인데 실제 로직 변경은 1-2 파일이면 정규화가 섞인 신호.
- `.gitattributes` 의 `* text=auto eol=lf` 가 있으면 OS 차이로 인한 일회성 부산물일 가능성 높음 — 단독 커밋 후 push.

**다중 CR(blob 오염) 진단 — 2026-06-02 추가:**
- 증상: 파일이 `git status` 상시 modified인데 diff는 내용 동일(EOL만). `--ignore-cr-at-eol` diff가 0이 아닌데도 내용 변경은 없음.
- 근본: blob 자체에 줄당 CR이 **여러 개**(`\r\r...\r\n`, 실측 9개) 박혀 커밋됨 + `.gitattributes eol=lf`가 영구 renormalize 요구. dogfood worktree(autocrlf=true)가 저장 사이클마다 CR을 누적시켜 발생. 과거 R18/19/22/26 수동 cherry-pick 통증의 진짜 뿌리.
- **`git restore`로는 못 고침**: working tree가 이미 (오염된) blob과 동일 → 폐기할 변경이 없음. "커밋 없이 폐기" 모델 자체가 불가.
- **`git add --renormalize`도 불충분**: eol=lf clean 필터는 줄당 CR을 **1개만** 제거(`\r\n`→`\n`). 9개면 8개 잔존.
- **올바른 처방**: `sed -i 's/\r//g' <files>` 로 **전체 CR 제거** 후 `git add` + 단독 chore 커밋. 검증 2종 필수 — ① staged CR 잔존 0 (`git show :file | tr -cd '\r' | wc -c`) ② 내용 불변 (`diff <(git show HEAD:file|tr -d '\r') <(git show :file|tr -d '\r')` = 0).
- **진단 순서**: 의심 시 strip-all-CR 비교부터 — `diff <(git show HEAD:f|tr -d '\r') <(tr -d '\r' <f)` 가 0이면 순수 EOL 오염(폐기/정규화 안전), >0이면 진짜 내용 변경(restore 시 작업 손실 위험). `--ignore-cr-at-eol`만 믿지 말 것(단일 CR만 무시).
- 관련: [[feedback_dogfood_pc_handoff]] (worktree autocrlf 오염), [[feedback_commit_staging_hygiene]].

**근본 원인 = sync 코드의 read/write 비대칭 (2026-06-03 FIX `b0bbbb48`):**
- 진짜 발생원은 `scripts/project_context_sync.py` `write_text`(`Path.write_text` text mode)와 `scripts/sync_claude_memory.py` `_write_atomic`(`os.fdopen "w"`). **text mode write가 Windows에서 `\n`→`\r\n` 자동 변환**. read는 binary(변환X)/write는 text(변환O) 비대칭 → `start_db`/`end_db` round-trip마다 CR 누적(`\r\n`→`\r\r\n`→...). git을 우회해 디스크에 쓰므로 `.gitattributes eol=lf`가 못 막음.
- **이전 청소(sed CR 제거)는 증상 치료였음** — 발생원을 안 고쳐서 매 세션 재발. "전에 고쳤는데 왜 또?" = 청소만 하고 생성 코드를 안 막았기 때문.
- **fix**: 양쪽에 `_normalize_newlines(text) = re.sub(r"\r+\n","\n",text).replace("\r","\n")` 적용. write는 `write_bytes`/`newline=""`로 OS 변환 차단 + content 정규화. read/push는 `read_bytes` 기반 정규화(universal-newline read가 다중CR `\r\r\n`을 `\n\n`으로 오변환하는 함정 회피 — 단순 `.replace("\r\n","\n").replace("\r","\n")`도 다중CR을 `\n\n`으로 폭증시키니 **반드시 `\r+\n` 먼저 붕괴**). `core.autocrlf=false` 설정. 회귀 테스트 8건(round-trip 안정성 포함).
- **교훈**: CRLF가 "자꾸" 재발하면 청소 전에 **파일을 누가 쓰는지**(git 우회 Python write?)부터 grep. text mode write + binary read 비대칭이 전형 패턴.

**Edit/Write 도구가 확장자 없는 파일을 CRLF로 churn (2026-06-03):**
- Windows에서 Claude의 Edit/Write 도구로 파일을 고치면 **CRLF로 기록**됨. `.gitattributes`에 매칭 eol 규칙이 있는 파일(`*.md`/`*.sh` 등)은 git이 add 시 renormalize해 무해하지만, **확장자 없는 파일은 무방비**: `.githooks/pre-commit`(7줄만 고쳤는데 numstat 97-/106+ 전체 churn), `.gitattributes` 자신(41-/43+)이 실제로 당함. shebang `#!/bin/sh\r`의 trailing CR은 Unix/Mac에서 `bad interpreter` 유발.
- **진단**: 작은 편집인데 `git diff --numstat`가 대량 -/+면 churn. `git ls-files --eol <f>`로 `i/lf w/crlf attr/`(빈 attr) 확인.
- **처방**: `sed -i 's/\r$//' <f>` → numstat이 순수 추가(N/0)로 줄면 OK → unpushed면 `git commit --amend`. 재발 방지는 해당 glob에 `text eol=lf` 추가(이번에 `.githooks/* text eol=lf` 등록 `be9b8be4`). ⚠️ `.gitattributes` 자신은 아직 self-rule 없음 — 편집 시 또 churn 가능, sed 후 amend 필요.
- 관련: [[feedback_commit_staging_hygiene]].

## 관련
- [[code/symbols]]

