---
name: project_cli_cp949_robustness_fix
description: "✅ 완료(f2229782, 2026-06-21). cli.py _run_command에 errors='replace' 추가 — cp949 UnicodeDecodeError 방어. 3-Tier PASS. gemini는 인증 필요(환경, 별도)."
metadata: 
  node_type: memory
  type: project
  originSessionId: 8df098b4-4c58-4360-932e-d9d5dada394a
---

**버그**: `core/providers/cli.py:291-301`의 CLI 실행 공통 헬퍼 `runner()` 호출이 `encoding="utf-8"`만 쓰고 **`errors=`가 없음**. 같은 파일 git 호출들(L620/622/635/644)은 `encoding="utf-8", errors="replace"` 사용 — **chat 실행 경로만 빠짐**.

**증상**: provider가 cp949 바이트(Windows 콘솔 인코딩) 출력 시 subprocess stdout utf-8 strict 디코딩이 `UnicodeDecodeError: 0xb8 position 0` → `_readerthread` 죽음 → CLI failed → control-plane이면 fallback(full). 2026-06-21 멀티프로바이더 실측에서 gemini_cli가 **인증 안 된 상태**라 한글 에러를 cp949로 출력 → 이 버그로 즉시 죽음(4/4 fallback). 인증 에러를 graceful하게 분류해야 할 자리에서 터진 것.

**fix (다음 세션 A, Sonnet)**: `errors="replace"` 추가. **절차**: ① 재현테스트 먼저 — cp949 바이트 내는 가짜 프로세스(`python -c "import sys; sys.stdout.buffer.write(b'\xb8...')"` 류)로 현재 죽음 재현 → fix 후 graceful. ② 3-Tier(critic→cross→test-runner, core Tier3). ③ Blueprint §11/§12.

**맥락 — 2026-06-21 멀티프로바이더 라우팅 실측 (`AF_CONTROL_PLANE_PROVIDERS` 강제)**:
- **claude_cli / codex_cli = 검증 완료**: 둘 다 단순(0.72~0.82) / 복잡(0.35) 분리. 라우팅 분류 메커니즘은 멀티프로바이더에서 정상.
- **gemini_cli = 인증 안 됨**(사용자 확인, 환경 문제). 분류 능력 검증은 인증 후 별도. A는 gemini 살리기가 아니라 **provider 무관 cp949 graceful 처리** robustness 보강.

**과장 정정 이력**: 최초 "gemini 라우팅 전체 마비"로 진단했으나 1차 원인은 인증(환경), 2차가 인코딩(코드). A는 robustness 보강 수준(긴급도 중).

관련: [[project_router_research_decoupling]] [[project_model_routing_facts]] [[feedback_crlf_normalization_separate_commit]]

## 관련
- [[code/symbols]]

