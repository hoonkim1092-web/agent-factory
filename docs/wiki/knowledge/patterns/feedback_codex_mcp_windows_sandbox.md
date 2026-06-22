---
name: feedback-codex-mcp-windows-sandbox
description: Windows에서 codex MCP를 사용하려면 sandbox_mode=danger-full-access + approval_policy=untrusted 조합이 필수. 다중 PC 환경에선 레포 루트 `.mcp.json`(portable) 방식이 정답.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6d52b453-3738-4b27-ac90-0d1572699fb1
---

Windows에서 codex MCP의 read-only / workspace-write 모드는 작동 불가. 등록 args에는 `sandbox_mode="danger-full-access"` + `approval_policy="untrusted"`를 함께 설정해야 한다.

**Why**: codex는 read-only/workspace-write 모드에서 Windows `CreateProcessWithLogonW` API로 별도 user credential 격리를 시도하는데, secondary logon에서 `error 1326 (ERROR_LOGON_FAILURE)`이 떨어져 PowerShell/cmd/bash/sh 모든 셸 launch가 차단된다. 결과적으로 codex가 file read를 위한 `Get-Content` 등도 실행하지 못해 cross-vendor 검증이 무력화됨 (2026-05-13 실측).

**How to apply** (우선순위 순):

1. **레포 루트 `.mcp.json` (권장, portable)** — 2026-05-13 채택:
   ```json
   {
     "mcpServers": {
       "codex": {
         "type": "stdio",
         "command": "codex",
         "args": ["mcp-server", "-c", "sandbox_mode=\"danger-full-access\"", "-c", "approval_policy=\"untrusted\""],
         "env": {}
       }
     }
   }
   ```
   - 절대경로 0개. `.claude.json` projects 키 의존 없음.
   - 다른 PC에서 `git pull` 후 Claude Code 재시작 → trust 다이얼로그 1회 승인 → 즉시 작동.
   - worktree에서도 동일 작동 (project key path mismatch 문제 회피).

2. **`.claude.json` projects.<absolute-path>.mcpServers.codex.args** — 단일 PC/단일 경로 환경:
   - `-c sandbox_mode="danger-full-access"` + `-c approval_policy="untrusted"` 두 줄 추가
   - **함정**: worktree(`worktrees/agent-factory`)와 메인 레포(`agent-factory`) 경로가 다르면 양쪽 모두 등록 필요. 다른 PC도 별도 등록.

3. **인라인 override (일회성)**:
   - mcp__codex__codex 호출 시 `sandbox="danger-full-access"` + `approval-policy="untrusted"` 인자 전달.

**보안 모델**:
- `danger-full-access`는 *OS 격리를 끄는* 것일 뿐 write 권한과 무관. write/delete 차단은 `approval_policy=untrusted`가 담당 (모든 셸 명령 사용자 승인 요청).
- read는 자동, write/delete는 매번 승인 → prompt injection으로도 임의 변경 불가.

관련: [[feedback-codex-reply-for-deliberation]] — codex 다라운드 의견 교환은 codex-reply로 thread 유지
