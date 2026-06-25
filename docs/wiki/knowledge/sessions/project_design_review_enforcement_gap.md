---
name: enforcement_complete
description: PostToolUse watcher 백그라운드 자동발화 — (A)(B) 모두 완료(2026-06-19), 다음=신규 product work-item
metadata: 
  node_type: memory
  type: project
  originSessionId: 45968b00-20ba-40d7-a85a-45dfc3c31f44
---

설계리뷰 자동발화 enforcement 수정 — **완료** (2026-06-22 재확인).

## 구현 완료 (2026-06-19)

**현재 배선 (3단 hook 체인)**:
1. Edit 설계문서 → PostToolUse `post_edit_design_review` → `scripts/design_review_trigger.py` enqueue
2. 백그라운드 `scripts/design_review_watcher.py` → cross-review headless → `docs/reviews/{ts}-design-review.md` verdict
3. git commit → pre-commit `scripts/check_staged_design_review.py` → 최신 verdict BLOCK이면 차단

### (A) ✅ watcher Windows 이식성 완료 (2026-06-19)
- `_process_alive()` 신규 (`core/design_review_utils.py:242-270`)
  - Windows: `ctypes.windll.kernel32.OpenProcess` + `GetExitCodeProcess` (WinError 87 해소)
  - Unix: POSIX `os.kill(pid, 0)` 호환

### (B) ✅ provider-aware fail-closed 게이트 완료 (2026-06-18)
- `check_staged_design_review.py`: verdict 부재 시 provider state별 분기
  - AVAILABLE → BLOCK (watcher 미실행)
  - AUTH_EXPIRED → BLOCK + 재인증 안내
  - NOT_INSTALLED | RATE_LIMITED → ℹ️ 노티 + SKIP
  - 기존 `provider_detect.py` SSOT 재사용

## 다음 단계

**신규 product work-item 발굴** (NEXT_STEPS.md 상단) 또는 Review BLOCK Learning Phase 2 진행.

## 관련
- [[code/symbols]]

