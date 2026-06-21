---
generated_at: 2026-06-22T04:25:55+09:00
source_commit: f6aef5f4
sources:
  - "docs/code_review/code-review.md"
---

# 2.3 Provider 레이어

> Source: `docs/code_review/code-review.md:79`
> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]

````markdown
### 2.3 Provider 레이어

| 파일 | 줄 | 역할 |
|------|-----|------|
| `providers/registry.py` | 253 | CLI_PROVIDER_IDS: claude_cli, gemini_cli, codex_cli. configure_providers(), detect_installed_cli_providers() (60s 캐시) |
| `providers/cli.py` | 764 | CliChatRequest/execute_cli_chat. 실제 CLI subprocess 호출 |
| `providers/session_adapter.py` | 642 | provider별 세션 설정. codex=wrapper_bridge (L110), frozen 빌드에서 hook 건너뜀 (L434) |
| `providers/__init__.py` | 17 | re-export |

**문제점:**
- `session_adapter.py:110`: codex_cli는 `mode="wrapper_bridge"`, `hook_events=()` → native hook 불가, AF EventBus 필요
- `session_adapter.py:434-436`: frozen 빌드에서 claude_cli hook 등록 스킵 → AF-owned checkpoint가 대안
- `registry.py`: `configure_providers()` 있지만 daemon에서 auto_configure 우회 경로 미구현
````
