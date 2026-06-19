# 멀티 프로바이더 sandbox on/off 토글 — `af sandbox` 명령 설계

**날짜**: 2026-06-19
**상태**: Draft
**작성자**: Claude Opus 4.8
**계기**: Windows native에서 sandbox 미지원 → 명령/hook 실행마다 `CreateProcessWithLogonW failed: 1326/1909` → 빈 검은 콘솔 창 수십 개. 사용자 요청: "샌드박스를 온오프 명령으로 멀티프로바이더에 할 수 있도록".

---

## §1 배경 및 동기

### §1.1 증상
Windows 11 native에서 Claude Code 사용 시 명령·hook 실행마다 검은 콘솔 창이 뜨고 사라지지 않으며 내용이 안 보인다. 원인: **sandbox 격리 메커니즘이 Windows native에서 미지원**(공식 문서: macOS/Linux/WSL2만 지원)인데도 시도되어 `CreateProcessWithLogonW`(다른 사용자로 프로세스 생성)가 실패하며 빈 창만 양산.

### §1.2 sandbox 출처는 **두 갈래** (grep/read 확정)

| 출처 | 위치 | 영향 |
|---|---|---|
| **(a) Claude Code 세션 sandbox** | `~/.claude/settings.json` (`sandbox.enabled` / `permissions.defaultMode: "auto"`가 안전명령 자동 격리) | 인터랙티브 세션의 bash·hook 실행 → 매 프롬프트·턴종료·편집마다 콘솔 창 |
| **(b) AF→provider subprocess sandbox 플래그** | `core/providers/cli.py` `_CLI_SPECS` | af-cross-review·dogfood가 codex/gemini를 subprocess로 띄울 때 |

**(b) 세부 (확정)**:
- `codex_cli` (`cli.py:97`): `default_command=("codex", "--ask-for-approval", "never", "--sandbox", "workspace-write", "exec", "--skip-git-repo-check")` — `--sandbox workspace-write` 하드코딩
- `gemini_cli` (`cli.py:93`): `headless_edit_flags=("--sandbox", "--approval-mode", "yolo")` — `--sandbox` 하드코딩
- `claude_cli` (`cli.py:78`): `headless_edit_flags=("--permission-mode", "bypassPermissions")` — sandbox 플래그 없음(세션 settings가 담당)

### §1.3 목표
**한 명령(`af sandbox on|off|status`)으로 3개 프로바이더의 sandbox를 일괄 제어**한다. 단일 SSOT가 (a)+(b)를 모두 반영해 멀티프로바이더 parity를 보장.

---

## §2 현재 코드 진단 (grep/read 확정)

- `core/providers/cli.py:47-64` `CliProviderSpec` (frozen dataclass) + `:66-109` `_CLI_SPECS` 상수.
- `:143-148` `get_cli_provider_spec()` — provider_id → spec.
- `:155-` `_resolve_base_command(spec)` — `command_env` override(`AGENT_CODEX_CLI_COMMAND` 등) 처리 후 base command 리스트 반환. **여기가 명령 빌드 단일 통로.**
- Claude Code sandbox: `~/.claude/settings.json`에 sandbox 블록 부재(기본 off)이나 `permissions.defaultMode: "auto"`가 안전명령을 격리 실행 시도. schema: `sandbox.enabled`/`allowUnsandboxedCommands`/`failIfUnavailable`.
- `~/.codex/.sandbox/` 디렉터리 실재 = codex sandbox 활성 중.

---

## §3 설계

### §3.1 SSOT — `core/sandbox_config.py` (신규, 순수 로직)

```python
# core/sandbox_config.py
import json, os, platform
from pathlib import Path

_ENV_OVERRIDE = "AF_SANDBOX"                 # "0"/"off"/"false" → off, "1"/"on"/"true" → on
_CONFIG_PATH = Path.home() / ".af" / "sandbox.json"   # {"enabled": bool}

def sandbox_enabled() -> bool:
    """sandbox 활성 여부 SSOT.
    우선순위: env AF_SANDBOX > ~/.af/sandbox.json > 플랫폼 기본(Windows=False, 그 외=True).
    """
    env = os.getenv(_ENV_OVERRIDE, "").strip().lower()
    if env in ("0", "off", "false", "no"):
        return False
    if env in ("1", "on", "true", "yes"):
        return True
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "enabled" in data:
            return bool(data["enabled"])
    except Exception:
        pass
    return platform.system() != "Windows"      # Windows native 기본 off (미지원)

def set_sandbox_enabled(enabled: bool) -> None:
    """~/.af/sandbox.json에 write-through (env override는 건드리지 않음)."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps({"enabled": bool(enabled)}, ensure_ascii=False), encoding="utf-8")
```

> 플랫폼 기본 off(Windows)는 INV-S1: 설정·env 부재 시에도 Windows에서 콘솔 창이 안 뜨게 하는 안전 기본값.

### §3.2 provider 명령에서 sandbox 플래그 제거 — `cli.py`

> **2026-06-19 BLOCK #F1·F2 반영 (cross-review, grep 재확인)**: ① 초안은 훅을 `_resolve_base_command`(`:155`) 직후에 두려 했으나, **gemini의 `--sandbox`는 거기 없다** — `build_cli_command:682` `cmd.extend(spec.headless_edit_flags)`에서 *나중에* 추가된다(codex의 `--sandbox`만 `_resolve_base_command`가 반환하는 `default_command`에 있음). 따라서 훅은 **`build_cli_command`의 최종 `return cmd`(`:702`) 직전 = 완성된 argv 전체**에 1회 적용해야 두 프로바이더를 모두 잡는다. ② gemini는 `:678-682`에서 `allow_file_edit`와 무관하게 `--sandbox --approval-mode yolo`를 항상 유지하는데, 주석(`:680`)이 "hang 방지"라 명시 → **`--approval-mode yolo`는 절대 제거 금지**(hang 회귀 방지, INV-S7).

**배선 지점**: `build_cli_command`(`:670-702`)의 `return cmd` 직전에 `cmd = _apply_sandbox_mode(spec.provider_id, cmd)` 1줄 삽입. `_resolve_base_command` + 모든 `extend`(model/headless/workspace/fixed/output/prompt) 이후라 **완성 argv**가 입력된다.

```python
def _apply_sandbox_mode(provider_id: str, parts: list[str]) -> list[str]:
    """sandbox off면 provider별 sandbox 격리 플래그를 무력화. 완성 argv 후처리. (cli.py)"""
    from core.sandbox_config import sandbox_enabled
    if sandbox_enabled():
        return parts                       # on → 기존 그대로 (회귀 0, INV-S4)
    pid = (provider_id or "").lower()
    if pid == "codex_cli":
        # --sandbox <mode> → --sandbox danger-full-access (codex 격리 해제 모드)
        return _swap_flag_value(parts, "--sandbox", "danger-full-access")
    if pid == "gemini_cli":
        # 부울 플래그 --sandbox만 제거. --approval-mode yolo 는 보존(hang 방지, INV-S7).
        return [p for p in parts if p != "--sandbox"]
    return parts                           # claude_cli 등: 변경 없음(세션 settings가 담당)
```
- `codex`: `--sandbox workspace-write` → `--sandbox danger-full-access`. ⚠️ **구현 전 검증(gate)**: codex `--sandbox` 허용값(`read-only`/`workspace-write`/`danger-full-access`)이 설치본에서 유효한지 `codex --help` 1회 확인. 무효면 **`--sandbox`와 그 값 토큰 쌍 제거**로 폴백(codex 기본 모드 사용 — 폴백 시 codex는 인자 없는 기본 sandbox로 동작, danger 강제 아님).
- `gemini`: `--sandbox` 토큰만 필터. `--approval-mode yolo`는 남는다(INV-S7). ⚠️ **구현 전 검증(gate)**: gemini를 headless로 `--approval-mode yolo`만(=`--sandbox` 제거) 1회 실행해 **hang 미발생 확인**. hang 발생 시 → gemini는 토글 대상에서 제외(`--sandbox` 유지)하고 status에 "gemini: sandbox 토글 미지원(hang)" 표기. (gemini sandbox는 컨테이너 기반이라 codex/claude의 OS 격리와 메커니즘이 달라, Windows 콘솔 창의 주 원인이 아님 — 검증 실패 시 제외해도 사용자 증상 해결엔 영향 없음.)
- 후처리는 **완성 argv 리스트** 1곳(`build_cli_command` 최종)에만 적용 → codex(default_command 유래)·gemini(headless_edit_flags 유래)·`command_env` override 전부 동일하게 커버.

### §3.3 Claude Code 세션 sandbox — `af sandbox`가 settings 기록

`af sandbox off`는 `~/.claude/settings.json`(존재 시 프로젝트 `.claude/settings.json`도)에 다음을 merge(기존 키 보존):
```json
"sandbox": { "enabled": false, "allowUnsandboxedCommands": true, "failIfUnavailable": false }
```
`af sandbox on`은 `sandbox.enabled: true`(나머지 키 유지) 또는 sandbox 블록 제거(기본 복원).

> **auto-mode 차단 회피**: 이 settings 편집을 **사용자가 `af sandbox off`를 실행**해 수행하므로 Claude Code auto-mode classifier의 self-modification 차단 대상이 아님(사용자 행위). AF 코드가 직접 Edit하지 않음.
> **재시작 필요**: Claude Code settings는 **재시작 후 적용** — 명령 출력에 명시.

### §3.4 CLI — `af sandbox <on|off|status>` (agent_launcher.py dispatch)

```
af sandbox status   # 프로바이더별 현재 sandbox 상태 출력 (SSOT + claude settings + cli.py 반영값)
af sandbox off      # SSOT write(enabled=false) + claude settings merge + codex/gemini 플래그 무력화 활성. 재시작 안내.
af sandbox on       # 반대.
```
- `status`는 read-only(파일 수정 0). `on`/`off`는 SSOT + claude settings write.
- `af.spec` `hiddenimports`에 `core.sandbox_config` 추가.

---

## §4 불변식 + 테스트

| ID | 내용 | 테스트 |
|---|---|---|
| INV-S1 | env·config 부재 시 Windows=off, 그 외=on (안전 기본값) | `test_sandbox_default_windows_off`, `test_default_posix_on` |
| INV-S2 | 우선순위 env > config > 플랫폼 기본 | `test_sandbox_precedence` |
| INV-S3 | off면 codex argv에 `--sandbox workspace-write` 부재(danger-full-access 또는 제거), gemini argv에 `--sandbox` 부재 | `test_codex_sandbox_off_argv`, `test_gemini_sandbox_off_argv` |
| INV-S4 | on이면 기존 argv 그대로(회귀 0) | `test_sandbox_on_argv_unchanged` |
| INV-S5 (배포 동등성) | `_apply_sandbox_mode`가 **`build_cli_command`의 최종 `return cmd`(`:702`) 직전**에 배선 — 완성 argv에 적용(codex+gemini+override 전부 커버), 픽스처 전용 아님 | `test_build_cli_command_applies_sandbox_mode`, `test_gemini_sandbox_stripped_via_build_cli_command` |
| INV-S6 | `af sandbox off`가 `~/.af/sandbox.json` + claude settings(`sandbox.enabled:false`) 둘 다 기록, 기존 settings 키 보존 | `test_af_sandbox_off_writes_both`, `test_claude_settings_merge_preserves` |
| INV-S7 (hang 회귀 방지) | sandbox off여도 gemini argv의 `--approval-mode yolo`는 **절대 제거되지 않음**(`cli.py:680` hang 방지 불변식 유지). gemini는 `--sandbox`만 필터 | `test_gemini_yolo_preserved_when_sandbox_off` |

---

## §5 위험 / 트레이드오프

| 위험 | 대응 |
|---|---|
| codex `danger-full-access` = 격리 해제(보안 약화) | Windows native엔 sandbox가 어차피 미작동 → 실질 손실 적음. `af sandbox on`으로 즉시 복구. 비-Windows 기본은 on 유지(영향 없음) |
| codex `--sandbox` 허용값이 설치본마다 다를 수 있음 | 구현 전 `codex --help` 검증, 무효 시 플래그 쌍 제거 폴백(§3.2) |
| claude settings 편집이 다른 세션 설정과 충돌 | merge-only(기존 키 보존), `on`은 복원. 사용자 실행이므로 auto-mode 비차단 |
| AF 내부 sandbox 개념(skill_evolution)과 혼동 | 본 설계는 **provider CLI sandbox**만. skill_evolution sandbox는 무관(별개 모듈) |

---

## §6 비목표 / 의도적 제외

- WSL2 전환 자동화: 범위 밖(문서 안내만). 본 설계는 native Windows에서 창을 없애는 최소 경로.
- Claude Code auto-mode 자체 토글: `defaultMode` 변경은 권한 프롬프트 UX에 광범위 영향 → 별도 결정. 본 설계는 sandbox만.
- design-review watcher가 편집마다 codex를 띄우는 빈도 자체: 별개 이슈(NEXT_STEPS item A). 단 `af sandbox off`로 그 codex 창은 사라짐.

---

## §7 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-06-19 | Draft (Opus 4.8). grep/read 확정 좌표: `cli.py:97`(codex --sandbox workspace-write), `:93`(gemini --sandbox), `:155`(_resolve_base_command), `~/.claude/settings.json`(claude 세션 sandbox). 2-갈래 sandbox(세션 + provider subprocess)를 단일 SSOT(`core/sandbox_config.py`)로 제어하는 `af sandbox on/off/status` 설계. |
| 2026-06-19 | af-cross-review **BLOCK 2건 반영 (Opus, grep 재확인)**: **F1** 훅 위치를 `_resolve_base_command` 직후 → **`build_cli_command` 최종 `return cmd`(`:702`) 직전**으로 정정(gemini `--sandbox`는 `:682` headless_edit_flags extend에서 추가되므로 완성 argv 후처리만이 codex+gemini 모두 캡처). **F2** gemini는 `:680` hang 방지 불변식이 있어 `--approval-mode yolo` 제거 금지 → `--sandbox`만 필터 + INV-S7 신설 + 구현 전 gemini headless no-hang 검증 gate(실패 시 gemini 토글 제외). INV-S5 좌표 갱신. |
