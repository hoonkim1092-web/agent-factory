---
name: ApprovalGate auto-approve BLOCK 5건 흡수 완료 (2026-05-11 v2)
description: commit 603dd702 auto-approve opt-in의 cross-review BLOCK 6건 중 Must-fix+idempotency 5건 흡수 완료. #6(write_text atomic)은 HOLD. Codex cross-review v2 검증은 5/13+ 보류.
type: project
originSessionId: 5e1c20a6-2b6a-4eb6-8c2e-e70e5adf2fe4
---
## 결과 (v2 commit 흡수 완료)

cross-review artifact: `docs/reviews/2026-05-11-184118-approval_gate-code-review.md`

| # | Severity | 흡수 방식 | 위치 |
|---|----------|-----------|------|
| #1 | Critical | auto 분기 직전 `status=="verification_blocked"` + `read_block_decision()` blocked 시 `return False`. user 명시 승인은 영향 없음 (auto 한정) | `core/approval_gate.py:approve()` 가드 |
| #2 | High | `_sanitize_reason()` 모듈헬퍼 — `re.sub(r"[\r\n#]+", " ")` + 120자 절단, approver+audit line 양쪽 | `core/approval_gate.py:25` |
| #3 | High | `_auto_approve_env_active(slug)` — `AF_AUTO_APPROVE_SLUGS` 콤마/공백 화이트리스트 필수, `*`/`all` 단독만 전역 | `core/approval_gate.py:35` |
| #4 | Medium | 멱등성 가드 — `is_auto + status=="approved" + "[auto-approve]" in notes` 즉시 `return True` | `approve()` 본문 |
| #5 | Medium | `from core.file_io import _env_flag` 통일 (1/true/yes/on/y) | import 라인 |
| #6 | Medium | **HOLD** — write_text non-atomic은 별도 PR (범위 외) | 미수정 |

## 검증

- `tests/test_approval_gate_auto_approve.py`: **24/24 PASS** (기존 12 + 신규 12)
- `tests/test_approval_gate_block_decision.py`: **6/6 PASS** (호환성)
- `tests/test_approval_gate_runtime_workspace.py`: **4/4 PASS** (호환성)
- `python -m py_compile` 통과
- 3-tier 교차검증: **SKIP** (사용자 한도 도달, 사용자 명시 결정)

## 호환성 보장 포인트

- 일반 사용자 명시 승인 (`auto=False`)은 `verification_blocked` 덮어쓰기 가능 — 기존 동작 유지
- 안전 가드는 **auto 한정** (auto=True 또는 env 모드)
- env 모드는 화이트리스트 필수 — 기존 `AF_AUTO_APPROVE=1`만 켠 설정은 자동 비활성 (breaking change지만 H3 회귀 차단)

## 후속 (5/13+)

- Codex cross-review 재시도 → v3 검증 (재인증 후)
- #6 (write_text atomic) 별도 PR — 영향 범위 넓음
- BLOCK 0건 PASS 후 안정화 단계

**Why:** Critical BLOCK + High 2건은 보안/안전성 직결이라 Codex 재시도 대기 무의미. v2로 즉시 흡수 결정 (사용자 선택). Codex 재시도는 신뢰성 확보용 future verification.

**How to apply:**
- 다른 PC에서 `auto=True` / `AF_AUTO_APPROVE=1` 사용 시 새 화이트리스트 요구사항 인지 — `AF_AUTO_APPROVE_SLUGS=slug1,slug2` 또는 `AF_AUTO_APPROVE_SLUGS=*` 필요
- verification_blocked 상태에서 강제 승인 필요 시 `auto=False` + 사용자 명시 호출만 가능
- 5/13 01:00 KST 이후 Codex cross-review 재실행 → BLOCK 0건 확인 후 자율 모드 단계 다음 옵션 검토
