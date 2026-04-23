# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-04-20 01:00
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Critical race condition exists in `record_review_done`. Must fix before merge.

---

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [Critical] `record_review_done` — 파일 락 없는 Read-Modify-Write 경쟁 조건
- **Critic**: "3개 에이전트 병렬 실행 시 각자 초기 state를 읽고 자신의 tier만 쓰면 마지막 writer가 다른 tier 결과를 삭제 → 영구 BLOCK"
- **Cross**: "#2에서 병렬 완료가 gate를 통과하는 별개 문제 확인 (sequential contract 미집행), #3에서 연관 상태 변이 문제 추가 확인"
- **Judgment**: CLAUDE.md가 af-test-runner + af-critic + af-cross-review를 명시적으로 병렬 실행하도록 지시하므로, 이 경쟁 조건은 설계상 반드시 발현된다. `_save_state`의 atomic write(`os.replace`)는 올바르지만 read→modify→write 전체 구간이 비원자적이다. `clear_committed_files`도 동일 위험.
- **Action Required**: `_load_state` + `_save_state` 호출 쌍 전체를 `filelock.FileLock(_PENDING_FILE + ".lock")` 컨텍스트로 감싸기. `clear_committed_files`에도 동일 락 적용.

#### 2. [ACCEPT] [High] `af-test-runner` FAIL이 gate를 막지 않음
- **Critic**: not flagged
- **Cross**: "`is_gate_blocked()`는 `verdict == 'block'`만 확인. CLI는 `--verdict fail`을 허용하고, hook_runner는 `fail`을 기록하지만 gate는 PASS 반환. 실제 재현 확인."
- **Judgment**: `scripts/review_gate.py:125`의 조건이 `"block"` 단일 값만 확인한다. `scripts/hook_runner.py:312-318`이 `"fail"`을 emit하고 설계문서 `docs/2026-04-19-review-gate-enforcement.md:154`가 tier-1 실패 시 blocking을 요구한다. 증거가 명확하다.
- **Action Required**: `is_gate_blocked()`에서 `af-test-runner`의 verdict가 `"fail"`이면 `(True, "tier1-failed")`를 반환하도록 수정. 실패 경로 단위 테스트 추가.

#### 3. [ACCEPT] [High] Sequential tier contract 미집행 — 병렬 완료가 gate 통과
- **Critic**: not flagged
- **Cross**: "코드 주석은 '1→2→3 순서 확인'이라 하지만, 구현은 3개 agent key 존재 여부만 확인. tier 번호·완료 순서·predecessor 성공 여부 불검증. 역순 완료로 재현."
- **Judgment**: `scripts/review_gate.py:105-109`가 key 존재만 검사함을 직접 확인 가능. CLAUDE.md가 병렬 실행을 지시하므로 sequential 계약을 코드로 강제하지 않으면 의도된 tier 순서는 결코 보장되지 않는다. 설계 문서와 실제 실행 방식 간 모순이 명확하다.
- **Action Required**: (a) CLAUDE.md/실행 방식을 순차 실행으로 바꾸거나 (b) gate 내에서 `reviews[agent]["tier"]` 값과 `completed_at` 단조 증가를 검증하는 것 중 하나 선택. 설계 문서와 동기화 필수.

#### 4. [ACCEPT] [High] `_load_state` silent fallback — 손상 파일이 gate를 무력화
- **Critic**: "모든 예외가 `None` 반환 → `no-queue` (PASS) 판정. 디스크 오류·JSON 손상 시 gate 무력화."
- **Cross**: "동일 문제 독립 확인. 잘못된 JSON 입력 시 경고 경로가 실행되지 않음을 재현."
- **Judgment**: 양쪽 모두 독립적으로 확인. `scripts/review_gate.py:39-48`의 `except Exception: return None` 패턴이 code-review.md §3.2 H3 "silent fallback" 재현 사례이다. Fail-open 정책 자체는 문서화되어 있으나, 손상 상태와 빈 queue를 구분하는 경로가 없어 경고조차 출력되지 않는다.
- **Action Required**: `except json.JSONDecodeError`를 별도 처리하여 stderr 경고 출력 후 fail-open. `OSError` 등 I/O 오류는 sentinel 값(예: `_CORRUPTED`) 반환 후 `is_gate_blocked`에서 `(True, "corrupted-queue")`로 fail-closed 처리 고려. invalid-JSON 단위 테스트 추가.

#### 5. [ACCEPT] [High] 파일 스냅샷 시점 오류 — 에이전트 실행 중 편집이 허위 커버리지로 기록
- **Critic**: not flagged
- **Cross**: "`hook_runner.py:323`이 에이전트 완료 시점의 현재 queue를 읽어 `--record`로 전달. 에이전트 실행 중 신규 편집이 queue에 추가되면 해당 파일을 '실제로 검토한 것처럼' 기록."
- **Judgment**: `scripts/enqueue_agent_review.py:83-86`이 `files`와 `updated_at`를 즉시 변경하고, gate는 `completed_at`과 `files_snapshot`으로 커버리지를 판단한다. 실행 중 편집이 허위 커버됨은 코드 흐름으로 명확히 추적 가능하다.
- **Action Required**: 각 에이전트 실행 *시작* 시점에 `state["files"]` 스냅샷을 캡처하여 `--record`로 전달. "에이전트 실행 중 신규 파일 편집" 회귀 테스트 추가.

#### 6. [ACCEPT] [Medium] 우회 경로 — `scripts/*.py` 편집이 review queue에 진입하지 않음
- **Critic**: not flagged
- **Cross**: "`.githooks/pre-commit`에 `review_gate.py --check` 없음. `enqueue_agent_review.py`가 `scripts/`를 감시 대상에서 제외하여 게이트 자체를 수정해도 검토가 생략됨."
- **Judgment**: `scripts/enqueue_agent_review.py:25-37`의 감시 경로 목록에 `scripts/` 없음을 확인. gate 핵심 파일인 `scripts/review_gate.py`와 `scripts/hook_runner.py`가 감시에서 빠지는 것은 보안 관점에서 의미 있는 공백이다.
- **Action Required**: `enqueue_agent_review.py` 감시 경로에 최소한 `scripts/review_gate.py`, `scripts/hook_runner.py` 추가. `.githooks/pre-commit`에 `review_gate.py --check` fast path 삽입.

#### 7. [ACCEPT] [Medium] `clear_committed_files` — C1 복합 위험
- **Critic**: "reviews 초기화 전 files+reviews 모두 비어있는지 확인 필요. C1(락 부재)과 복합 위험."
- **Cross**: "finding #7에서 기각 (단독으로는 버그 아님). 단, C1 락 미적용 상태에서 복합 위험은 유효."
- **Judgment**: C1(락)이 해결되면 대부분 완화된다. 그러나 `state["files"] == []` 조건만으로 `reviews`를 초기화하는 L175 로직이 동시 기록 중인 에이전트 결과를 삭제할 수 있는 구조적 문제는 락 적용 후에도 잔존한다.
- **Action Required**: C1 락 적용 후, `reviews` 초기화 조건을 `files`가 빈 경우 **and** `reviews`의 모든 tier가 완료 상태일 때로 강화 검토.

#### 8. [HOLD] [Medium] `--files` 쉼표 구분자 — 경로에 쉼표 포함 시 파싱 오류
- **Critic**: "`nargs='*'` 또는 NUL 구분자로 변경 권고."
- **Cross**: not flagged
- **Judgment**: 실제 OS 수준에서 파일 경로에 쉼표가 포함되는 경우는 드물다. 현재 호출자(git hook)가 공백 구분 방식을 사용하는지 확인 필요.
- **Question for Author**: `.githooks/pre-commit`이 `--files`에 전달하는 파일 목록 구분자가 `,`인지 공백인지 확인 후, 실제 위험이 있으면 `nargs='*'` 방식으로 전환.

---

### [REJECT] stale 체크 `min()` — Critic 판정 기각

- **Critic**: "`min()` → `max()`로 교체 필요" (High)
- **Cross**: "설계 문서가 'any tier completed before latest edit → stale'을 요구하므로 `min()`이 정확한 구현. 테스트 12/12 통과."
- **Judgment**: 설계 의미론이 "모든 tier가 최신 편집 이후에 완료되어야 함"이면, `min(completed_at) < updated_at`이 올바른 조건이다. Cross 기각이 코드 증거(`tests/test_review_gate.py:141-151`)와 설계 문서(`docs/2026-04-19-review-gate-enforcement.md:150`)에 의해 지지된다. **Critic 판정 기각.**

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | record_review_done 락 부재 Race Condition | Critical | ACCEPT | Both |
| 2 | af-test-runner FAIL이 gate 미차단 | High | ACCEPT | Cross |
| 3 | Sequential tier contract 미집행 | High | ACCEPT | Cross |
| 4 | _load_state silent fallback | High | ACCEPT | Both |
| 5 | 파일 스냅샷 시점 오류 | High | ACCEPT | Cross |
| 6 | scripts/ 감시 우회 경로 | Medium | ACCEPT | Cross |
| 7 | clear_committed_files 복합 위험 (C1 의존) | Medium | ACCEPT | Critic |
| 8 | --files 쉼표 구분자 | Medium | HOLD | Critic |
| — | stale 체크 min() 오류 | High | **REJECT** | Critic only |

---

### Recommendations

1. **[즉시 필수]** `filelock.FileLock` 또는 `fcntl.flock`으로 `record_review_done`과 `clear_committed_files` 전체를 원자적 구간으로 보호 (Finding 1, 7 동시 해결)
2. **[즉시 필수]** `is_gate_blocked()`에서 `af-test-runner`의 `"fail"` verdict를 blocking 조건으로 추가 (Finding 2)
3. **[설계 결정 필요]** CLAUDE.md 병렬 실행 지시 vs. 설계 문서의 sequential tier 계약 모순 해소 — 실행 방식을 sequential로 바꾸거나 gate 코드가 tier 순서를 검증하도록 수정 (Finding 3)
4. **[버그 수정]** `_load_state`에서 `json.JSONDecodeError`와 `OSError`를 구분 처리, 손상 파일은 경고+fail-open, 설계 변경 시 fail-closed 고려 (Finding 4)
5. **[버그 수정]** 에이전트 실행 시작 시점 파일 목록을 스냅샷으로 캡처하여 `--record`로 전달 (Finding 5)
6. **[배선 작업]** `enqueue_agent_review.py` 감시 경로에 `scripts/review_gate.py`, `scripts/hook_runner.py` 추가; `.githooks/pre-commit`에 `review_gate.py --check` 삽입 (Finding 6)
7. **[테스트 추가]** af-test-runner fail 경로, invalid JSON, 에이전트 실행 중 신규 파일 편집 시나리오 각각 단위 테스트 작성