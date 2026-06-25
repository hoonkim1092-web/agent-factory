---
name: project_windows_sandbox_console_and_toggle
description: "af sandbox on|off|status 구현 완료(53dc15ce). Windows 검은 콘솔창 근본원인(sandbox 미지원) + 2-갈래 토글 SSOT."
metadata: 
  node_type: memory
  type: project
  originSessionId: 3ac412ee-6b56-4ed4-8900-502eff27832b
---

Windows native에서 명령/hook 실행마다 **검은 콘솔 창이 수십 개 뜨고 안 사라지며 내용도 안 보이는** 증상의 근본원인 = **sandbox 미지원**. Claude Code/codex sandbox는 macOS/Linux/WSL2만 지원(native Windows 미지원, 공식문서)인데도 시도되어 `CreateProcessWithLogonW failed: 1326/1909`(로그온 실패)로 빈 창만 양산. 모든 docs/reviews의 "windows sandbox: CreateProcessWithLogonW failed"가 이것 — 즉 그 BLOCK/HOLD 리뷰들은 코드 결함이 아니라 **인프라 실패**.

**2-갈래 sandbox 출처 (grep/read 확정)**:
- (a) Claude Code 세션 sandbox: `~/.claude/settings.json`에 sandbox 블록 부재이나 `permissions.defaultMode: "auto"`가 안전명령을 격리 실행 시도 → 매 프롬프트/턴종료/편집(hook)마다 창. 임시회피=settings에 `"sandbox":{"enabled":false,"allowUnsandboxedCommands":true,"failIfUnavailable":false}` 추가+재시작. **단 Claude Code auto-mode classifier가 AF의 직접 settings 편집을 self-modification으로 차단** → 사용자가 직접 편집해야 함.
- (b) AF→provider subprocess: `core/providers/cli.py` `_CLI_SPECS` — codex(`:97` `--sandbox workspace-write` in default_command), gemini(`:93` `--sandbox` in headless_edit_flags). claude_cli엔 sandbox 플래그 없음. 최종 argv 조립=`build_cli_command`(`:670-702`), 유일 return=`:702`. gemini는 `:680` 주석대로 `--sandbox --approval-mode yolo` hang 방지 불변식.

**구현 완료 (2026-06-19, Sonnet, 커밋 `53dc15ce`)**:
- `core/sandbox_config.py` 신규: `sandbox_enabled()` SSOT, `set_sandbox_enabled()`
- `core/providers/cli.py`: `_apply_sandbox_mode` + `_swap_flag_value` + `build_cli_command` 배선
- `scripts/af_sandbox.py` 신규: on/off/status dispatch + claude settings merge
- `agent_launcher.py`/`af.py`/`af.spec`: sandbox 서브커맨드 등록
- 테스트 16케이스 INV-S1~S7 PASS. 3-Tier: af-critic PASS / af-cross-review WARN(BLOCK 0) / af-test-runner PASS(57)

**사용법**: `af sandbox off` 실행 → Claude Code 재시작 → Windows 검은 콘솔 창 해소.
advisory 3건(INV-S6 서술, on 시 stale key, AGENT_CODEX_CLI_COMMAND override 엣지)은 WARN-only.

**Why**: 이 세션 내내 사용자를 괴롭힌 실제 환경 버그. 구현 완료.
**How to apply**: 완료. 사용자에게 `af sandbox off` + 재시작 안내. [[feedback_workflow_agent_review_gate_gap]]

## 관련
- [[code/symbols]]

