# 교차검증 강제 게이트 설계 (v2 — tier 순차 파이프라인)

- 날짜: 2026-04-19 (v2 개정 2026-04-19)
- 작성자: Claude Sonnet 4.6 (설계) · Sonnet (구현 예정)
- 관련: `CLAUDE.md` "교차검증 자동 실행", `.af_review_queue/`, `scripts/check_pending_review.py`, `scripts/enqueue_agent_review.py`, `scripts/hook_runner.py`, `scripts/pre_commit_review.py`
- 상태: 설계 v2 (구현 미착수, Critical 2건 실증 선행 필요)

## 개정 이력

| 버전 | 일시 | 내용 |
|------|------|------|
| v1 | 2026-04-19 | 초기 설계. 3개 에이전트 병렬 가정. |
| v2 | 2026-04-19 | af-doc-qa(WARN)·af-critic(BLOCK) 반영. Tier 순차 파이프라인 도입, 판정 규칙 4번 방향 수정, 기존 `pre_commit_review.py` 역할 분리, `docs(blueprint):` 우회 삭제, Critical 2건 실증 프로토콜 Appendix A 추가. |

---

## 1. 문제 정의

### 1.1 현상
- `UserPromptSubmit` 훅이 `[af-review-pending]` 텍스트를 컨텍스트에 주입하면 Claude는 **반드시** 교차검증 에이전트를 실행해야 한다 (CLAUDE.md 규칙).
- 실제로는 Claude가 메시지를 무시하고 다음 작업으로 넘어가는 사례가 최근 세션만 3회 이상 발생.

### 1.2 원인: advisory ≠ enforcement
현재 파이프라인은 **리마인더**다. 훅은 Claude의 컨텍스트에 문자열을 밀어넣을 뿐, 특정 툴(Agent)을 강제 호출시킬 수단이 없다. 메시지 문구 강화·`MIN_BATCH_INTERVAL_SEC` 조정·CLAUDE.md 규칙 강화 — 모두 advisory라 Claude가 무시하면 그만이다.

### 1.3 핵심 전환: advisory → blocking
진짜 강제는 **다음 단계를 물리적으로 차단**하는 것뿐이다. Claude Code의 PreToolUse 훅이 exit 2로 Bash 툴 호출을 차단할 수 있다는 전제 하에(→ **Appendix A 실증 필요**), `git commit` 실행 시점에 리뷰 완료 여부를 판정한다.

---

## 2. 설계 원칙

1. **Blocking이지 advisory가 아니다** — 리뷰 안 했으면 commit 자체를 막는다.
2. **Editing은 자유** — 편집 흐름은 방해하지 않는다. 게이트는 commit 시점에만.
3. **Tier 순차 파이프라인** — 에이전트를 병렬로 돌리지 않고 tier 순서로 실행한다 (§3).
4. **멱등·fail-open** — 게이트 자체 오류는 PASS 처리 (commit을 막는 건 리뷰 미완료일 때만). 우회 수단 명시.
5. **기존 자산 보존** — `pending_agent_review.json` 스키마는 append-only로 확장, `pre_commit_review.py`(기존 severity 게이트)와 역할 분리.

---

## 3. Tier 리뷰 파이프라인 (핵심 신규)

### 3.1 왜 순차인가

병렬 실행은 **토큰·시간 효율**만 잡고 품질은 떨어뜨린다. 실제 발생한 폐해:

- **중복 지적 낭비**: v1 문서 리뷰에서 af-doc-qa와 af-critic이 §4.1 방향 오류·§5.5 우회 취약성을 둘 다 잡음 (토큰 2배, 발견 1배).
- **의존성 무시**: 테스트 fail인 코드를 af-critic이 설계 관점으로 리뷰하는 건 무의미.
- **심화 기회 상실**: 뒤 에이전트가 앞 에이전트의 발견을 확장하거나 fix 반영 후 재검증하지 못함.

### 3.2 Tier 정의 (코드 리뷰)

```
Tier 1. af-test-runner   — 기계적 검증 (테스트 실행)
           ↓ PASS 필수
Tier 2. af-critic        — 로직·보안·일관성 리뷰
           ↓ BLOCK 해소 후 PASS
Tier 3. af-cross-review  — Codex 자율 탐색, 다른 관점으로 사각지대 확인
           ↓ 최종 PASS
```

**규칙:**
- Tier N이 PASS(또는 BLOCK fix 반영)되기 전엔 Tier N+1을 실행하지 않는다.
- Tier 1 FAIL → 테스트 fix → Tier 1 재실행. Tier 1이 녹색이어야 Tier 2 시작.
- Tier 2 BLOCK → 지적된 항목 fix → (선택) Tier 2 재실행 → 통과 후 Tier 3.
- Tier 3은 fix 반영된 **최종 코드 상태**를 본다. 그래서 가장 마지막.

### 3.3 설계문서 리뷰 (별도 트랙, 병렬 OK)
- **af-doc-qa + af-critic 병렬** — 짧은 단일 아티팩트 + 관점 다양성이 핵심. 중복 지적은 신호 강도 확인용으로 감수.
- 코드 tier와 완전 분리. 서로 상태 공유 없음.

### 3.4 게이트 판정과 tier의 관계
`review_gate.py`가 요구하는 "리뷰 완료"는 **Tier 1/2/3 모두 통과** 상태다. 중간 tier만 완료해도 게이트는 BLOCK (§5.1 판정 규칙 참조).

---

## 4. 게이트 위치 결정

| 후보 | 시점 | 장점 | 단점 | 채택 |
|------|------|------|------|------|
| (A) PreToolUse(Edit\|Write) | 편집 시도 | 조기 차단 | 과도함(편집 자체 불가) | ❌ |
| (B) PreToolUse(Bash) `git commit` 매처 | Claude Bash 툴 commit | 편집은 자유, commit만 차단 | Claude 경로만 커버 | ✅ Primary |
| (C) `.githooks/pre-commit` | git 레벨 | 사용자 직접 commit도 커버 | Claude Code는 Bash 툴 통과 전에 차단 못 함 | ✅ 보조 |

**결정: (B) + (C) 병행.** 동일 판정 함수 `review_gate.is_gate_blocked()` 공유 (DRY).

### 4.1 기존 `pre_commit_review.py`와의 역할 분리

**두 게이트는 직교 관계, AND로 묶는다.**

| 게이트 | 파일 | 질문 | 입력 | BLOCK 조건 |
|--------|------|------|------|-----------|
| **A. Review-gate** (신규) | `scripts/review_gate.py` | "3 tier 리뷰가 실행됐는가?" | `.af_review_queue/pending_agent_review.json` | tier 미완료 또는 재편집 |
| **B. Severity-gate** (기존) | `scripts/pre_commit_review.py` | "리뷰 결과에 Critical/High 있는가?" | `docs/reviews/*.md` | severity ≥ 설정 임계 |

**`.githooks/pre-commit` 실행 순서:**
```
1. (기존) Blueprint staged 체크          ← 변경 없음
2. (신규) review_gate.py --check         ← FAST: 리뷰 실행 여부
3. (기존) pre_commit_review.py           ← SLOW: severity 집계
4. (기존) verify-handoff 검증             ← 변경 없음
```

Fast-path를 먼저 돌려 미리뷰 상태면 즉시 차단(severity 파일 파싱 불필요). 모두 PASS여야 commit 성공.

---

## 5. 데이터 스키마

### 5.1 `pending_agent_review.json` 확장

```jsonc
{
  "files": ["core/foo.py", "core/bar.py"],
  "created_at": 1776432651.559,
  "updated_at": 1776604813.668,
  "fired_at": 1776605649.204,

  // ── 신규: tier별 리뷰 완료 기록 ────────────────────
  "reviews": {
    "af-test-runner": {
      "completed_at": 1776606000.0,
      "files_snapshot": ["core/foo.py", "core/bar.py"],
      "tier": 1,
      "result": "pass"        // "pass" | "fail"
    },
    "af-critic": {
      "completed_at": 1776606120.0,
      "files_snapshot": ["core/foo.py", "core/bar.py"],
      "tier": 2,
      "verdict": "pass"       // "pass" | "warn" | "block"
    },
    "af-cross-review": {
      "completed_at": 1776606240.0,
      "files_snapshot": ["core/foo.py", "core/bar.py"],
      "tier": 3,
      "verdict": "pass"
    }
  }
}
```

### 5.2 판정 규칙 (`is_gate_blocked()`)

순서대로 검사, 첫 BLOCK 즉시 반환:

1. `files`가 비었거나 키 자체가 없으면 → **PASS** ("queue-empty")
2. `reviews` 누락 에이전트 있으면 → **BLOCK** (`"missing-tier-<N>: <agent-name>"`)
3. Tier 순서 위반 (tier 1 없이 2만 있음 등) → **BLOCK** (`"tier-order-violation"`)
4. 어느 tier든 `completed_at < updated_at` → **BLOCK** (`"stale-review: edited after"`)
5. **현재 `files`가 `files_snapshot`의 상위집합이 아니면** → **BLOCK** (`"new-files-added"`)
   - 구체: `set(files) - set(files_snapshot) ≠ ∅`이면 신규 파일 추가됨 → BLOCK
   - (v1 문서의 방향 오류 수정: append-only enqueue는 항상 snapshot⊆files → snapshot⊆files 검사는 죽은 규칙이었음)
6. `result == "fail"` (tier 1) 또는 `verdict == "block"` (tier 2/3) → **BLOCK** (`"tier-N-failed"`)
   - 단 Q4 정책에 따라 `AF_GATE_ALLOW_VERDICT_BLOCK=1` 시 PASS (§10 Q4)
7. 전부 통과 → **PASS**

---

## 6. 컴포넌트 설계

### 6.1 `scripts/review_gate.py` (신규, 단일 진실원천)

```python
def is_gate_blocked(workspace: str) -> tuple[bool, str]:
    """BLOCK 여부 + reason. 게이트 자체 오류는 fail-open (PASS + stderr 경고)."""

def record_review_done(
    workspace: str,
    agent: str,                # "af-critic" | "af-cross-review" | "af-test-runner"
    tier: int,                 # 1 | 2 | 3
    verdict: str,              # "pass" | "warn" | "block" | "fail"
    files_snapshot: list[str],
) -> None:
    """reviews[agent] 기록. atomic write."""

def clear_committed_files(workspace: str, committed_files: list[str]) -> None:
    """
    커밋 성공 후 staged 파일만 선택적으로 files/reviews snapshot에서 제거.
    (af-critic v1-H4 반영: 통째 삭제하면 동시 편집한 신규 파일 유실)
    """

# CLI
if __name__ == "__main__":
    # --check         : is_gate_blocked 결과에 따라 exit 0 (PASS) / 1 (BLOCK)
    # --record <agent> --tier N --verdict V --files f1,f2,...
    # --clear --files f1,f2,...   (staged 파일만)
    # --debug                       : 현재 큐 상태 + 판정 출력
```

### 6.2 `scripts/hook_runner.py` 신규 빌트인

| 커맨드 | 트리거 | 동작 | stdin JSON 경로 |
|--------|--------|------|----------------|
| `pre_bash_review_gate` | PreToolUse(Bash) | `command` 파싱 → `git\s+commit\b` 정규식 매칭 → `is_gate_blocked()` → BLOCK 시 exit 2 + stderr. | `payload["tool_input"]["command"]` ✅ Appendix A 실증 완료 (§10 Q5-b). **주**: 서브에이전트(Agent 툴)의 내부 Bash 호출에서도 본 훅이 발동하나(`agent_id`/`agent_type` 필드 포함), git commit 정규식 필터로 게이트 동작에는 영향 없음 (§10 Q5 추가 발견 #2). |
| `post_agent_record` | PostToolUse(Task) | `subagent_type` 추출 → 3종 리스트에 있으면 tier 판정 후 `record_review_done()` 호출 | `payload["tool_input"]["subagent_type"]` ✅ Appendix A 실증 완료 (§10 Q5-c). `tool_name` 필드 값은 "Agent". |
| `post_commit_clear` | PostToolUse(Bash) | `command` 매칭 + 종료 코드 확인 → commit 성공 시 `clear_committed_files()` | staged 파일은 `git diff HEAD~1 --name-only`로 재조회 |

**git commit 매칭 정규식** (합성 명령 대응):
```python
_GIT_COMMIT_RE = re.compile(r"(?:^|[\s;&|])git\s+commit\b(?!\s+--help)")
```
`cd foo && git commit ...`, `git commit; git push` 모두 매칭. `git commit --help`는 제외.

**에이전트 → tier 매핑**:
```python
_AGENT_TIER = {
    "af-test-runner": 1,
    "af-critic":      2,
    "af-cross-review": 3,
}
```

### 6.3 `.claude/settings.local.json` 훅 배선

**운영 참고 (§10 Q5 추가 발견 #3)**: Claude Code는 `settings.local.json`을 세션 중에 파일 변경 감지로 리로드한다. 따라서 게이트 배포·롤백 모두 파일 수정만으로 즉효이며 **세션 재시작이 필요 없다**. 단, shell env(`AF_SKIP_REVIEW_GATE=1`)를 통한 우회는 Claude Code 프로세스 시작 시점의 환경변수가 캡처되므로 env 변경 시에는 재시작 필요 (§11 롤백 #3 참조).

기존 `PostToolUse.Write|Edit` 유지, 아래 3개 엔트리 신규 추가:

```jsonc
"PreToolUse": [
  {
    "matcher": "Bash",
    "hooks": [{
      "type": "command",
      "command": "python3 /Users/hoon/workTree/agent-factory/scripts/hook_runner.py pre_bash_review_gate",
      "timeout": 5
    }]
  }
],
"PostToolUse": [
  // ... 기존 Write|Edit 엔트리 ...
  {
    "matcher": "Task",
    "hooks": [{
      "type": "command",
      "command": "python3 /Users/hoon/workTree/agent-factory/scripts/hook_runner.py post_agent_record",
      "timeout": 3
    }]
  },
  {
    "matcher": "Bash",
    "hooks": [{
      "type": "command",
      "command": "python3 /Users/hoon/workTree/agent-factory/scripts/hook_runner.py post_commit_clear",
      "timeout": 5
    }]
  }
]
```

### 6.4 `.githooks/pre-commit` 보조 게이트

line 25 이후, 기존 `pre_commit_review.py` 블록(line 27~49) **앞에** 삽입:

```sh
# ── 신규: review-gate fast-path ──
if [ "${AF_SKIP_REVIEW_GATE:-0}" != "1" ]; then
    REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
    VENV_PYTHON="${REPO_ROOT}/.venv/bin/python3"
    [ -x "$VENV_PYTHON" ] && GATE_PY="$VENV_PYTHON" || GATE_PY="python3"
    "$GATE_PY" "${REPO_ROOT}/scripts/review_gate.py" --check
    GATE_EXIT=$?
    if [ $GATE_EXIT -ne 0 ]; then
        echo ""
        echo "⛔ [pre-commit] 교차검증 미완료."
        echo "   af-test-runner → af-critic → af-cross-review 순서로 Agent 툴 실행 후 재시도."
        echo "   우회: AF_SKIP_REVIEW_GATE=1 git commit ..."
        echo ""
        exit 1
    fi
fi
```

### 6.5 우회 수단 (단순화)

**v1에서 `docs(blueprint):` prefix 우회 삭제.** 커밋 메시지 문자열은 속이기 너무 쉽고, staged diff가 진실원천.

| 우회 | 조건 | 로그 |
|------|------|------|
| `AF_SKIP_REVIEW_GATE=1` env | 환경변수 명시적 설정 | `.af_review_queue/hook_events.log`에 `[gate-skipped-env]` 기록 → 사후 감사 |
| `.py` 변경 없는 커밋 | `git diff --cached --name-only` 결과에 `.py` 파일 0개 | 로그 없음 (정상 통과) |

**둘 다 review_gate.py 내부에서 판정.** `.githooks/pre-commit`과 `hook_runner.py` 양쪽에서 동일 로직 호출.

---

## 7. 흐름 다이어그램

### 7.1 정상 (tier 3단 순차)
```
[Edit core/foo.py] → PostToolUse(Edit) → enqueue: files=[foo.py]

Claude: [af-review-pending 수신]
  → Agent(subagent_type="af-test-runner")
      → PostToolUse(Task): tier=1 record
  → [Tier 1 PASS 확인 후]
  → Agent(subagent_type="af-critic")
      → PostToolUse(Task): tier=2 record
  → [Tier 2 fix 필요 시 여기서 수정 → 필요시 tier 2 재실행]
  → Agent(subagent_type="af-cross-review")
      → PostToolUse(Task): tier=3 record

Claude: Bash("git commit -m '...'")
  → PreToolUse(Bash) `pre_bash_review_gate`
     → `is_gate_blocked()` → (False, "all-tiers-passed")
     → exit 0 (PASS)
  → git commit 실행 → 성공
  → PostToolUse(Bash) `post_commit_clear`
     → committed .py 파일만 files/reviews 정리
```

### 7.2 위반 (리뷰 건너뜀)
```
[Edit core/foo.py] → enqueue
Claude: Bash("git commit ...")
  → PreToolUse(Bash) `pre_bash_review_gate`
     → is_gate_blocked → (True, "missing-tier-1: af-test-runner")
     → stderr: "⛔ 교차검증 미완료: core/foo.py. Tier 1부터 실행 필요."
     → exit 2 (BLOCK)
  → Bash 툴 실행 거부 → Claude는 Tier 1부터 실행
```

### 7.3 재편집
```
[tier 1/2/3 모두 완료 상태]
Edit core/foo.py → updated_at > 모든 completed_at
Bash("git commit ...") → BLOCK("stale-review: edited after tier-2 completion")
→ tier 2, 3 재실행 필요 (tier 1은 테스트 실행이라 fix 없으면 재실행 무의미 — 단 정책 Q6)
```

### 7.4 Tier 순서 위반
```
[tier 2만 완료, tier 1 건너뜀]
Bash("git commit ...") → BLOCK("tier-order-violation: tier 1 missing")
```

---

## 8. 엣지 케이스

| 케이스 | 동작 |
|--------|------|
| `.af_review_queue/` 없음 | PASS (큐 없음 = 차단 근거 없음) |
| `pending_agent_review.json` 손상 | PASS + stderr 경고 (fail-open) |
| `.py` 변경 없는 commit | PASS (우회 규칙 §6.5) |
| `git commit --amend` | BLOCK (첫 commit과 동일 취급, 의도) |
| 셸 합성 `cd foo && git commit` | 정규식 `_GIT_COMMIT_RE`로 매칭, BLOCK 적용 |
| `git commit --help` | PASS (`(?!\s+--help)` lookahead) |
| **에이전트 실행 중 파일 자동 편집** | 문제: subagent가 Edit 툴로 파일 수정하면 `updated_at`이 갱신되어 자기 리뷰를 무효화. 해결: PostToolUse(Edit)가 **현재 Task 실행 중인지** 환경변수 `AF_IN_AGENT_TASK=1`로 판정하면 enqueue 스킵. Task 훅에서 subagent 시작 시 env 설정, 종료 시 해제. |
| **Background 자동 커밋** (nightly tick 등) | Claude Code 훅은 background 프로세스에 작동 안 함. **(C) `.githooks/pre-commit`만 작동**. background commit이 AF_SKIP_REVIEW_GATE=1로 우회하지 않는 한 pre-commit 게이트에 걸림 — 의도한 동작. |
| 여러 commit 병렬 (동시에 실행 불가 환경) | Claude Code는 Bash 툴을 순차 실행. race 거의 없음. `clear_committed_files`는 staged 파일만 지우므로 동시 Edit enqueue 보존. |
| 큐 파일 없이 `--record` 호출 | 큐 파일 자동 생성, reviews만 있고 files 비어있는 상태 → is_gate_blocked PASS |

---

## 9. 구현 순서 (Sonnet 구현 지침)

**전제 (2026-04-19 완료 ✅): Appendix A의 Critical 2건 실증 검증이 완료되어 §10 Q5에 결과가 기록되었다. exit 2 Bash 차단과 stdin JSON 경로가 기대대로 동작함이 확인되었고, §6.2가 "실증 완료" 상태로 갱신되었다. 구현 착수 가능.**

1. ~~**Appendix A 실증**~~ **[✅ 2026-04-19 완료]** — `.af_runtime/hook_samples.jsonl`에 샘플 보관. Q5 결과 §6.2 반영 완료.
2. **`scripts/review_gate.py` 신규** — `is_gate_blocked`, `record_review_done`, `clear_committed_files` + CLI (`--check`, `--record`, `--clear`, `--debug`)
3. **유닛 테스트 `tests/test_review_gate.py` 10종**:
   - (a) 빈 큐 → PASS
   - (b) tier 1 누락 → BLOCK("missing-tier-1")
   - (c) tier 2 누락 → BLOCK("missing-tier-2")
   - (d) tier 3 누락 → BLOCK("missing-tier-3")
   - (e) 재편집 → BLOCK("stale-review")
   - (f) 신규 파일 추가 → BLOCK("new-files-added")
   - (g) 전부 완료 → PASS
   - (h) verdict=block + AF_GATE_ALLOW_VERDICT_BLOCK unset → BLOCK
   - (i) verdict=block + AF_GATE_ALLOW_VERDICT_BLOCK=1 → PASS
   - (j) `AF_SKIP_REVIEW_GATE=1` → PASS + 로그
4. **`scripts/hook_runner.py` 확장** — `pre_bash_review_gate`, `post_agent_record`, `post_commit_clear`. 기존 `_read_hook_stdin_once`, `_extract_file_path` 패턴 재사용. 모든 신규 빌트인은 실증 확정된 JSON 경로만 사용.
5. **`.claude/settings.local.json` 훅 배선** — §6.3 3개 엔트리 추가.
6. **`.githooks/pre-commit` 보조 게이트** — §6.4 블록 삽입.
7. **통합 테스트**:
   - Claude 경로: 미리뷰 상태에서 `git commit` 시도 → BLOCK 확인 (e2e, 실제 Claude Code에서)
   - 터미널 직접: `AF_SKIP_REVIEW_GATE=1 git commit` 우회 확인
   - `.py` 없는 commit PASS 확인
8. **마이그레이션** — §10 Q7 방식으로 처리 (빈 큐 초기화 권장, 또는 15파일 일괄 tier 완주)
9. **Blueprint 업데이트** — §7/§11에 게이트 동작 기술, §12 feat 엔트리 추가, `CLAUDE.md`에 우회 규칙 명시.
10. **교차검증 사이클 자기 적용** — 구현 완료 후 이 게이트를 통해 구현 자체를 commit (드래프팅: 2번 fix → 3번 tier 완주 → commit)

---

## 10. 미결정 사항 (구현 전 확정)

### Q1. 브랜치 범위
- A) 전 브랜치 / B) feature 브랜치만
- **추천: A**. 머지 전에도 필요.

### Q2. Tier 1 테스트 없는 모듈
- `tests/test_<module>.py` 없는 파일은 af-test-runner가 형식적으로만 PASS 기록.
- **추천**: 대응 테스트 파일 존재 여부로 판정. 없으면 tier 1 자동 PASS 허용.

### Q3. 훅 자체 예외 시
- A) fail-open (PASS + 경고) / B) fail-closed (BLOCK)
- **추천: A**. 훅 버그로 commit 못하는 건 과도함.

### Q4. 리뷰 verdict=BLOCK 처리
- A) 실행했으면 PASS / B) verdict까지 검사해 BLOCK이면 게이트도 BLOCK
- **추천: B (기본), A 우회 가능** — `AF_GATE_ALLOW_VERDICT_BLOCK=1` env로 BLOCK verdict 우회 허용. 기본은 "BLOCK verdict 나왔으면 커밋 불가"가 의미 있는 강제.

### Q5. ⚠️ Critical 2건 실증 결과 (Appendix A 2026-04-19 완료)

- **Q5-a**: PreToolUse(Bash) exit 2가 실제로 Bash 툴 실행을 차단하는가?
  - 기대: 차단됨
  - **실측: 차단 확정 ✅** — `/tmp/af_probe_marker.txt` 마커 파일이 생성되지 않았고, 툴 결과는 `PreToolUse:Bash hook error: [...]: PROBE_BLOCK: ...`만 반환. 후속 Bash 호출도 전부 차단.
- **Q5-b**: PreToolUse(Bash) stdin JSON의 `command` 경로는 `tool_input.command`인가?
  - 기대: 맞음
  - **실측: 일치 ✅** — 캡처된 payload: `{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git status --short | head -5","description":"..."},"session_id":"...","cwd":"...","permission_mode":"acceptEdits","tool_use_id":"..."}`
- **Q5-c**: PostToolUse(Task) stdin JSON의 `subagent_type` 경로는 `tool_input.subagent_type`인가?
  - 기대: 맞음
  - **실측: 일치 ✅** — 캡처된 payload: `{"hook_event_name":"PostToolUse","tool_name":"Agent","tool_input":{"description":"...","prompt":"...","subagent_type":"Explore"},"tool_response":{...}}`

#### Q5 추가 발견 (설계에 반영 필수)

1. **matcher 문자열과 `tool_name` 필드 값이 다름**: `.claude/settings.local.json`의 `PostToolUse.matcher="Task"`로 배선하면 실제 `Agent` 툴 호출 시 훅이 트리거되지만, stdin JSON의 `tool_name` 필드 값은 **"Agent"**. hook_runner 내부에서 tool_name으로 분기할 때 "Agent"를 기대해야 함. §6.2는 JSON 경로만 명시하고 tool_name 검사는 안 하므로 문제 없음 — 다만 구현자가 혼동 시 주의.

2. **서브에이전트(Agent)의 내부 Bash 호출도 PreToolUse(Bash) 발동**: payload에 `agent_id`, `agent_type` 필드 포함. 예: 서브에이전트가 `git commit`을 실행하려 하면 게이트가 동작. 현재 Agent-Factory에서 서브에이전트가 git commit을 호출하는 경로는 없으므로 **수용 가능**. 단, 향후 서브에이전트에게 자동 커밋을 위임할 경우 review_gate.py가 `AF_SKIP_REVIEW_GATE=1`을 서브프로세스 env로 명시 전달하는 로직 필요.

3. **settings.local.json은 세션 중 리로드됨**: Claude Code가 훅 설정을 파일 변경 감지로 리로드. 게이트 배포 시 **세션 재시작 불필요**. 롤백도 파일 수정만으로 즉효.

4. **`permission_mode` 필드 포함**: `"acceptEdits"` 등. 게이트 로직이 안전모드/기본모드 구분하려면 이 필드 활용 가능.

- **미통과 시 대안** (전부 통과했으므로 미적용): ~~Q5-a 차단 불가 → (B) 경로 폐기~~ / ~~Q5-b/c 경로 다름 → 실측 경로로 수정~~

### Q6. Tier 1 재실행 조건
- 재편집이 테스트 코드면 tier 1 재실행 필수. 프로덕션 코드만 변경이면 tier 1 skip 가능?
- **추천: 항상 tier 1 재실행**. 단순함이 이긴다.

### Q7. 마이그레이션 (현재 밀려있는 15파일)
- A) 빈 큐 초기화 후 게이트 ON
- B) 15파일 전부 tier 3단 완주 → reviews 필드 생성 → 게이트 ON
- **추천: A + 별도 트랙으로 B 진행**. 게이트 활성화를 막는 blocker로 15파일을 걸지 않는다. 빈 큐로 시작하고, 코드 버그 fix(Appendix B)는 별도 PR로 리뷰.

---

## 11. 롤백 계획

과도한 오차단 시 1분 내 복구:
1. `.claude/settings.local.json`에서 PreToolUse(Bash) 블록 제거 (1줄)
   - **세션 재시작 불필요** — settings는 파일 변경 감지로 리로드됨 (§10 Q5 추가 발견 #3)
2. `.githooks/pre-commit`에서 review-gate 블록 주석 처리
   - **세션 재시작 불필요** — `.githooks`는 매 commit 시 신선한 프로세스로 재실행됨
3. `AF_SKIP_REVIEW_GATE=1` shell export
   - 현재 터미널 세션만 즉효. Claude Code 세션에는 **재시작 필요** (환경변수는 Claude Code 시작 시 캡처됨)

롤백은 코드 되돌릴 필요 없이 훅 비활성화만으로 충분하도록 설계.

---

## 12. DoD (검증 기준)

- [x] **Appendix A 실증 완료** — Q5-a/b/c 결과 문서화 (2026-04-19 수행, §10 Q5 실측 기록됨)
- [ ] `is_gate_blocked` 10종 유닛 테스트 통과 (§9.3)
- [ ] Claude 경로 e2e — 미리뷰 상태 commit 시도 → BLOCK 확인
- [ ] 3 tier 순차 완료 후 commit → PASS 확인
- [ ] 터미널 직접 commit → `.githooks/pre-commit` 게이트 동일 동작 확인
- [ ] `AF_SKIP_REVIEW_GATE=1` 우회 + 로그 기록 확인
- [ ] `.py` 없는 커밋 자동 PASS 확인
- [ ] 기존 `pre_commit_review.py` severity 게이트와의 AND 동작 회귀 테스트
- [ ] `.af_review_queue/hook_events.log`에 gate BLOCK/SKIP 이벤트 기록 확인
- [ ] 마이그레이션(§10 Q7) 완료 — 15파일 처리 방침 적용
- [ ] `Master_Blueprint.md` §7/§11 동작 기술, §12 feat 엔트리 추가
- [ ] `CLAUDE.md`에 우회 수단 문서화 (AF_SKIP_REVIEW_GATE 명시)

---

## 13. 배포 파이프라인 통합 (agent-factory 배포 대상자에게 동등 적용)

### 13.1 배포 경로 3종과 게이트 적용 여부

| 배포 경로 | 대상 | 게이트 작동 | 조치 필요 |
|-----------|------|-------------|----------|
| (a) `agent-factory` 소스 clone (개발자) | git tracked 파일 전부 포함 | (B) PreToolUse + (C) pre-commit 모두 작동 | `git config core.hooksPath .githooks` 1회 필요 — 설치 스크립트 자동화 |
| (b) `install-af.sh` / `.ps1` 소스 설치 (최종 사용자) | tarball 기반 소스 배포 | 동일 작동 가능 | 설치 스크립트가 `core.hooksPath` 설정 + `.claude/settings.local.json` 배치 |
| (c) PyInstaller frozen exe (`dist/af-*.zip`) | `af.spec` datas만 포함 | **훅 전부 무력** (스크립트 파일이 frozen 내부에 없음) | §13.3 참조 |

### 13.2 소스 배포 (a·b) 통합

**`install-af.sh` / `install-af.ps1` 공통 변경:**
1. 설치 말미에 `git config core.hooksPath .githooks` 자동 실행 (`.git/` 존재 시에만)
2. `.claude/settings.local.json`이 사용자 로컬에 이미 있으면 **덮어쓰지 않고**, 신규 훅 엔트리만 병합 (JSON merge). 없으면 템플릿 복사.
3. 설치 완료 메시지에 "교차검증 게이트 활성화됨" 안내

**`.claude/settings.local.json` 배포 정책:**
- 현재 git tracked → clone 사용자는 그대로 사용
- 사용자별 커스터마이즈(개인 allowed commands 등)와 배포 게이트 훅이 같은 파일에 있음 → **파일 분리 권장**:
  - `.claude/settings.json` (tracked, 공용 훅 배선)
  - `.claude/settings.local.json` (gitignored, 사용자별)
  - Claude Code는 두 파일을 merge하여 로드 (공식 지원 확인 필요)
- 분리 마이그레이션은 **별도 작업**으로 분류. 이번 gate 구현에서는 `settings.local.json`에 훅 추가하고, 분리 리팩터는 §13.5 후속 작업으로.

### 13.3 Frozen exe (c) 대응

Frozen 환경에서는 훅이 무력하므로 **대안 경고 메커니즘** 필요:

- **Option A**: frozen 빌드에서 `review_gate.py`를 `datas`로 포함하지 않고, `run_factory_cli.py`의 `af check-review-gate` 서브커맨드로 대체 노출. 사용자가 수동 확인.
- **Option B**: frozen 빌드에서도 `scripts/`, `.githooks/`를 datas에 포함하고, frozen 실행 시 `sys._MEIPASS/scripts/review_gate.py`를 호출. 단, frozen 환경에서 Claude Code 자체를 쓸 일이 없을 가능성 높음 (frozen은 CLI 전용).
- **추천: Option A**. Frozen exe 사용자는 Claude Code를 쓰지 않는 최종 사용자이므로 게이트의 원래 목적(LLM의 리뷰 우회 방지)과 무관. 대신 `af check-review-gate` CLI로 `.af_review_queue/` 상태를 수동 조회 가능하게만 열어둔다.

**`af.spec` 변경:**
- Option A 채택 시 `hiddenimports`에 `scripts.review_gate` 불필요 (scripts는 정상 Python 호출 경로). 단, `run_factory_cli.py`가 `scripts/review_gate.py`를 dynamic import하면 `datas=[('scripts/review_gate.py', 'scripts')]` 추가 필요.
- 현재 `install_scheduler.py`도 dynamic import라 같은 이슈. 이번 변경에서 함께 datas 추가 권장.

### 13.4 퍼블릭 레포 `af-fsa` 동기화

**메모리 기반 배경**: 개발은 `agent-factory`, 공개 릴리즈는 `af-fsa` 레포.

| 아티팩트 | 반드시 `af-fsa` 동기화 | 방식 |
|---------|---------------------|-----|
| `scripts/review_gate.py` (신규) | ✅ | tarball에 포함 |
| `scripts/hook_runner.py` (확장) | ✅ | 동 |
| `.githooks/pre-commit` (확장) | ✅ | 동 |
| `.claude/settings.local.json` (훅 추가) | 정책 확정 필요 | §13.2 파일 분리 후 `.claude/settings.json`만 배포 |
| `docs/2026-04-19-review-gate-enforcement.md` | 선택 (docs/만 포함 정책이면) | — |
| `install-af.sh`/`.ps1` (훅 자동 설치) | ✅ | 동 |
| `Master_Blueprint.md` | ✅ (§7, §11, §12 업데이트) | 동 |
| `CLAUDE.md` (우회 규칙) | ✅ | 동 |

**태그·배포 절차:**
1. `agent-factory` 브랜치에서 모든 변경 commit (게이트 자체를 dogfooding — tier 3단 완주 후 commit)
2. `version.py` bump: 최소 `1.2.22` (feat 레벨). 게이트 ON은 사용자 동작 변경이므로 minor 고려 가능 (1.3.0). 추천: **1.2.22 (patch)** — 우회 가능한 기능 추가이므로.
3. `install-af.ps1`/`install-af.sh`의 버전 문자열 3곳 동기화
4. `af.spec` hiddenimports·datas 갱신
5. `python build_exe.py` → `dist/af-1.2.22.zip`
6. `gh release create af-fsa_v1.2.22 dist/af-1.2.22.zip --notes ...`
7. `af-fsa` 레포에 동일 파일 push (별도 remote)
8. Blueprint §12 feat 엔트리 추가

### 13.5 후속 작업 (분리된 PR)

- `.claude/settings.json` ↔ `settings.local.json` 분리 리팩터
- frozen exe에서의 `af check-review-gate` CLI 서브커맨드 구현
- `install-af.sh`/`.ps1`에 훅 자동 설치 + upgrade 시 `.claude/settings.json` 안전한 머지 로직

---

## Appendix A. Critical 2건 실증 검증 프로토콜

**✅ 2026-04-19 수행 완료.** 결과는 §10 Q5에 기록됨. exit 2 차단 + stdin JSON 경로 모두 기대대로 동작 확인.

아래 프로토콜은 재검증(예: Claude Code 메이저 업데이트 후) 기준 절차로 보존.

### A.1 stdin JSON 구조 캡처

**임시 probe 스크립트 `.af_runtime/probe_hook.py`:**
```python
#!/usr/bin/env python3
import json, sys, time, pathlib
out = pathlib.Path(".af_runtime/hook_samples.jsonl")
out.parent.mkdir(parents=True, exist_ok=True)
try:
    payload = json.load(sys.stdin)
except Exception as e:
    payload = {"_parse_error": str(e)}
with out.open("a") as f:
    f.write(json.dumps({
        "hook_at": time.time(),
        "argv": sys.argv,
        "payload": payload,
    }) + "\n")
sys.exit(0)   # 절대 차단하지 않음 (실증만)
```

**임시 훅 배선 (`.claude/settings.local.json`에 추가):**
```jsonc
"PreToolUse": [{
  "matcher": "Bash",
  "hooks": [{"type":"command","command":"python3 .af_runtime/probe_hook.py pre_bash","timeout":2}]
}],
"PostToolUse": [{
  "matcher": "Task",
  "hooks": [{"type":"command","command":"python3 .af_runtime/probe_hook.py post_task","timeout":2}]
}]
```

**절차:**
1. Claude Code에서 `Bash("git status")` 실행 → `.af_runtime/hook_samples.jsonl`에 stdin 기록 확인
2. Claude Code에서 `Agent(subagent_type="general-purpose", ...)` 실행 → 샘플 기록
3. 두 샘플의 JSON 경로 확인 (특히 `tool_input.command`, `tool_input.subagent_type`)

### A.2 exit 2 차단 검증

**probe에 exit 2 버전 추가 `.af_runtime/probe_block.py`:**
```python
#!/usr/bin/env python3
import sys
print("⛔ PROBE: 이 Bash 툴 호출은 차단되어야 합니다 (exit 2 테스트).", file=sys.stderr)
sys.exit(2)
```

**임시 배선 (기존 probe와 교체, 일회성):**
```jsonc
"PreToolUse": [{
  "matcher": "Bash",
  "hooks": [{"type":"command","command":"python3 .af_runtime/probe_block.py","timeout":2}]
}]
```

**절차:**
1. Claude Code에서 `Bash("echo probe-block-test")` 실행 시도
2. 두 가지 관찰 중 하나:
   - (A-2a) 툴 실행 자체가 거부되고 stderr 메시지만 표시됨 → **exit 2 차단 확정** → 게이트 설계 가능
   - (A-2b) stderr 표시 후에도 `echo probe-block-test` 실제 실행됨 → **exit 2 차단 불가** → 설계 (B) 경로 폐기, (C) only

**결과 기록 방식:**
`docs/2026-04-19-review-gate-enforcement.md` §10 Q5 섹션에 직접 업데이트.

### A.3 정리
- 실증 완료 후 `.af_runtime/probe_*.py`와 임시 훅 배선 제거
- `.af_runtime/hook_samples.jsonl`은 보관 (스키마 변경 감지용 레퍼런스)

---

## Appendix B. 별도 트랙 — 코드 버그 fix (리뷰 결과 요약)

이 설계 문서의 scope 밖이지만 **게이트 활성화 전에 최소 Critical 해소 필요**.

### B.1 af-critic(15파일) 발견 — 품질 이슈 5건

| # | 파일 | 심각도 | 이슈 | 제안 fix |
|---|------|--------|------|---------|
| B1-1 | `core/lineage_ledger.py` | High | 스레드 Lock 없음 (StrategyLedger는 있음, 일관성 깨짐) | `threading.Lock` 추가, `on_task_*` 진입점 감쌈 |
| B1-2 | `core/project_pipeline.py:164-168` | High | `_save_checkpoint` non-atomic write | 같은 클래스의 `_write_json` 사용 |
| B1-3 | `run_factory_cli.py:203-207, 231-236` | Medium | `importlib.util.spec_from_file_location` None 미방어 | `if _spec is None: ...` 가드 추가 |
| B1-4 | `core/memory_system/episode_matcher.py:225-227` | Medium | stop-word 미제거 → 유사도 과대추정 | 한/영 stop-word set 차집합 |
| B1-5 | `core/approval_gate.py:222-254` | Medium | Markdown 파서가 포맷 드리프트에 취약 | `_render`/`_parse` 공통 `_SECTION_SEPARATOR` 상수화 |

### B.2 af-cross-review(Codex) 발견 — 통합 불변식 위배 8건

**⚠️ #3은 이 설계(review-gate)의 approval-gate 연동을 직접 무력화한다. 게이트 활성화 전 필수 fix.**

| # | 대상 | 심각도 | 이슈 |
|---|------|--------|------|
| B2-1 | `scripts/nightly_tick.py:98-103, 132-133, 161-162` | **Critical** | board 스키마와 mismatch — `mod.get("tasks")`·`task.get("role")` 읽는데 실제는 `board["tasks"]`에 `owner_role`. tick이 항상 빈 결과 → Phase 0 불변식 위배 |
| B2-2 | `core/nightly_state.py:172-175` ↔ `core/lineage_ledger.py:67-81` | **Critical** | `lineage_ledger.json` 동일 파일을 두 서브시스템이 **다른 스키마**로 덮어쓰기 (`{watchdog.lineage_counters}` vs `{entries:[...]}`) → tick 종료 시 history 유실 |
| B2-3 | `scripts/verify_handoff_checker.py:97` | **High** | `_propagate_block_to_gate`가 `work_item_dir.parent.parent` 전달하나 ApprovalGate가 내부적으로 `docs/work-items/slug` 재조합 → 이중 `docs/docs/...` 경로 → **BLOCK 전파 no-op**. **방금 설계한 review-gate의 approval-gate 연계 무력화** |
| B2-4 | `core/project_pipeline.py:931-946`, `core/work_item_parser.py:253-269` | High | `sync_board_from_work_items`가 신규 task를 `module_id=""`로 넣지만, `_materialize_roles`는 `prepared.role_plan`만 참조 → 편집으로 추가된 `owner_role`의 역할 YAML 미설치 |
| B2-5 | `core/memory_system/strategy_ledger.py:158, 174` | High | key에 `owner_role` 누락, `deliverable_pattern.lower()`만 사용 → 두 역할이 같은 pattern에 섞이고 `owner_role`은 최초값 고정 → `_pick_owner_role` 학습 불가 |
| B2-6 | `core/project_pipeline.py:963, 971-981` | Medium | 프로젝트 전역 `status`로 전 모듈에 일괄 fail 기록 → 정상 모듈도 패널티 |
| B2-7 | `core/work_item_generator.py:492, 497` | Medium | `_search_seed_episodes` private 직접 호출 → `EpisodeMatcher.query_similar` facade 미사용 → 런타임 저장 에피소드 dead path |
| B2-8 | `core/project_task_board.py:382-394`, `core/work_item_generator.py:135` | Medium | `_normalize_tasks` 반환 dict에 `e2e_command` 키 자체가 없음 → generator는 항상 `(needs_backfill)` → DoD 미달 |

### B.3 af-test-runner 발견 — 테스트 실패 2건

**총 103 tests 실행, 2 FAIL, 소요 262.87s.**

| # | 테스트 | 대상 | 원인 | 제안 fix |
|---|--------|------|------|---------|
| B3-1 | `tests/test_run_factory_cli.py::test_run_factory_cli_sets_provider_and_projects_root` | `run_factory_cli.py:522-527` | `--provider` 처리에서 `configure_providers()` 성공 시 `os.environ["AGENT_CHAT_PROVIDER"]`를 세트하지 않음 (except 블록에만 있음). 테스트 계약과 불일치. | try 블록 밖으로 `os.environ["AGENT_CHAT_PROVIDER"] = args.provider` 항상 실행 |
| B3-2 | `tests/test_project_pipeline.py::test_project_pipeline_writes_planning_artifacts_and_roles` | `core/project_pipeline.py:1047-1048` | `run()` 경로에서 `approve("auto")` 시 `gate.initialize()` 선행 안 됨. LLM 타임아웃(claude_cli 2분·codex API key invalid) 발생 시 gate_path 부재 → `ok=False`. | `run()` 시작부에 `if not os.path.exists(_gate.gate_path): _gate.initialize(slug)` 방어 또는 `prepare()` 마지막에 `gate.initialize()` 보장 |

**커버리지 없음** (테스트 파일 부재): `core/watchdog.py`, `core/nightly_state.py`, `core/document_policy.py`, `core/lineage_ledger.py`, `core/ise_loop.py` — **별도 테스트 보강 트랙 필요**.

### B.4 처리 순서 권장

1. **B2-1, B2-2, B2-3** (Critical, High) → **review-gate 구현 전**에 해소. 특히 B2-3은 게이트 의미 자체를 깨뜨림.
   - **현재 상태 (2026-04-19)**:
     - [x] B2-3 — 본 커밋에서 수정됨 (`verify_handoff_checker.py`). af-critic의 CWD 독립성 지적 반영하여 `report_path.resolve()` 선행 + `work_item_dir.parent.parent.parent` 방식으로 재수정.
     - [ ] B2-1 — `scripts/nightly_tick.py` 스키마 mismatch, **미해소**. review-gate 본체 구현 착수 전 fix 필요.
     - [ ] B2-2 — `core/nightly_state.py` ↔ `core/lineage_ledger.py` 스키마 충돌, **미해소**. review-gate 본체 구현 착수 전 fix 필요.
2. Review-gate 구현 (이 문서 본체 §9) — B2-1/B2-2 fix 선행 후 착수
3. Gate 통과한 상태에서 나머지 B1·B2 fix를 tier 순차로 리뷰·commit (dogfooding)
