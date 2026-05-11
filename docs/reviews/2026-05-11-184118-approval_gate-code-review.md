# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-11 18:41
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

**Note**: Cross Review failed to execute (provider error — Codex stdin prompt was truncated before producing any findings). Aggregation falls back to the Critic Review only, with diff-evidence used to confirm each finding rather than treating single-source findings as automatic HOLD.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [Critical] Auto-approve bypasses `verification_blocked` status
- **Critic**: `approve(auto=True)`가 현재 status 확인 없이 `status="approved"`로 덮어써, `apply_verification_verdict()`가 잠근 system BLOCK을 silent하게 우회.
- **Cross**: not flagged (provider error).
- **Judgment**: Diff 확인 — `if not os.path.exists(self.gate_path): return False` 외에 status/block 가드가 전혀 없음. `apply_verification_verdict()`의 verification_blocked 잠금이 무력화됨이 명백. docstring에 위험을 명시했으면서도 가드 미구현 — 자율 모드의 1번 결함. **Critical로 격상** (system-issued BLOCK silent 우회 = security/safety bypass).
- **Action Required**: auto 분기 진입 직전 가드 추가:
  ```python
  if is_auto:
      if _clean(current.get("status")) == "verification_blocked":
          return False
      blocked, _ = self.read_block_decision()
      if blocked:
          return False
  ```

#### 2. [ACCEPT] [High] `auto_reason` injection으로 메타데이터 변조 가능
- **Critic**: `auto_reason`은 `.strip()`만 호출되고 줄바꿈/마크다운 prefix sanitization 없음. `_parse()`가 라인 단위로 `- key: value` 매칭 → 위조된 키 주입 가능.
- **Cross**: not flagged (provider error).
- **Judgment**: Diff 확인 — `auto_reason.strip()`만 적용되고 `\n`, `- `, `##` 제거 없음. `_parse()`의 정규식 `r"-\s+(\w+):\s*(.*)"`가 멀티라인을 받으면 위조 메타데이터를 줍는 것이 확실. 현재 내부 호출자만 있지만 CLI/env 노출 시 즉시 활성 취약점. C4 sanitization 회귀 카테고리와 동일.
- **Action Required**: 한 줄 강제 + 위험 문자 제거 헬퍼 추가, approver 필드와 audit line 양쪽 적용:
  ```python
  def _sanitize_reason(raw: str) -> str:
      return re.sub(r"[\r\n#]+", " ", raw).strip()[:120]
  ```

#### 3. [ACCEPT] [High] `AF_AUTO_APPROVE` 전역 적용 — work-item 격리 없음
- **Critic**: env var가 프로세스 전역 → dynamic_orchestrator 5-concurrent / 다중 work-item 환경에서 한 trivial 작업을 위해 켠 플래그가 critical 작업까지 우회시킴.
- **Cross**: not flagged (provider error).
- **Judgment**: Diff에서 `os.environ.get("AF_AUTO_APPROVE") == "1"`는 ApprovalGate 인스턴스/slug와 무관하게 truthy. 동시 처리 시나리오가 실재(Master_Blueprint §2.5)하므로 격리 부재가 실효적 결함. Manus-방향 자율 모드가 의미를 가지려면 정책 매칭 필수.
- **Action Required**: 화이트리스트(`AF_AUTO_APPROVE_SLUGS=...`) 또는 policy.yaml의 work_kind risk 분류 참조. 최소한 slug 단위 opt-in.

#### 4. [ACCEPT] [Medium] review_notes audit line 무한 누적 — 멱등성 가드 부재
- **Critic**: `apply_verification_verdict()`(L347-354)는 동일 마커 중복 가드 존재. `approve(auto=True)`는 동일 보호 부재 → 재호출 시 `[auto-approve]` 라인 N개 누적.
- **Cross**: not flagged (provider error).
- **Judgment**: Diff 확인 — `review_notes = (audit_line + "\n" + review_notes).strip()`는 무조건 prepend. 같은 회귀 패턴이 이미 한 번 잡혔는데 동일 보호가 한 곳에만 적용된 형태로 회귀 위험 명백.
- **Action Required**: idempotency 가드:
  ```python
  if is_auto and "[auto-approve]" in review_notes and _clean(current.get("status")) == "approved":
      return True
  ```

#### 5. [ACCEPT] [Medium] `AF_AUTO_APPROVE` 값 비교가 프로젝트 컨벤션과 불일치
- **Critic**: `_env_flag()`(core/file_io.py:22-26)는 `1/true/yes/on/y` 모두 truthy. 다른 AF env flag들도 그 컨벤션 따름. `=="1"`만 받는 strict 비교는 디버깅 함정.
- **Cross**: not flagged (provider error).
- **Judgment**: Diff 확인 — 명백한 컨벤션 위반. 기존 헬퍼 미사용은 명백한 oversight.
- **Action Required**: `from core.file_io import _env_flag` 후 `_env_flag("AF_AUTO_APPROVE")`로 통일. 관련 테스트 갱신.

#### 6. [HOLD] [Medium] `write_text()` non-atomic — diff 범위 외
- **Critic**: code-review.md C2/H5a/M10 동일 카테고리. auto-approve가 빈번 호출 시나리오 → 크래시 손상 위험 증가. 이번 diff에서 새 경로 도입은 없으나 자율 모드 도입과 함께 격상 권장.
- **Cross**: not flagged (provider error).
- **Judgment**: Diff 범위 외 이슈. 이번 변경이 새 결함을 도입한 것은 아니지만 노출 빈도를 키우는 것은 사실. 정책상 별도 PR이 합리적이며 이 변경의 BLOCK 사유로 보기는 어렵다.
- **Question for Author**: write_text atomic 격상을 이 PR에 포함할지, 별도 작업으로 분리할지 결정 필요.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | verification_blocked silent 우회 | Critical | ACCEPT | Critic + diff |
| 2 | auto_reason injection | High | ACCEPT | Critic + diff |
| 3 | AF_AUTO_APPROVE 전역 격리 부재 | High | ACCEPT | Critic + diff |
| 4 | review_notes 멱등성 없음 | Medium | ACCEPT | Critic + diff |
| 5 | env flag 컨벤션 불일치 | Medium | ACCEPT | Critic + diff |
| 6 | write_text non-atomic | Medium | HOLD | Critic only (out-of-scope) |

---

### Recommendations

**Must-fix before merge (BLOCK 해제 조건)**:
1. Finding #1: auto 분기 진입 직전 `verification_blocked` + `read_block_decision()` 가드 추가. **이 한 가지가 빠지면 merge 금지.**
2. Finding #2: `_sanitize_reason()` 헬퍼로 `auto_reason` 줄바꿈/마크다운 제거, approver와 audit line 양쪽 적용.
3. Finding #3: 최소한 slug 화이트리스트(`AF_AUTO_APPROVE_SLUGS`) 도입. 정책 매칭은 후속 PR 가능하나, 전역-only 상태로는 merge 불가.

**같이 처리 권장 (별도 commit이지만 같은 PR 내)**:
4. Finding #4: idempotency 가드 추가 — 회귀 차단 비용 매우 낮음.
5. Finding #5: `_env_flag()`로 통일 + 관련 테스트(`test_env_value_other_than_1_does_not_activate`) 컨벤션 맞춰 수정.

**별도 PR**:
6. Finding #6: `write_text` atomic 격상은 영향 범위가 넓어 별도 PR로 분리.

**프로세스 노트**:
- Cross Review(Codex) provider error로 단일 소스 판정. 사용자가 시간 여유 있으면 Codex 재인증 후 `af-cross-review` 재실행 권장. 단, Critic Review의 6개 findings 모두 diff에서 직접 검증 가능했으므로 BLOCK 판정 자체에는 영향 없음.