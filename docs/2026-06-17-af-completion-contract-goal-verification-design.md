# AF 완료 계약 — 증거원장 기반 goal-reached 검증 설계

**날짜**: 2026-06-17  
**상태**: Draft  
**작성자**: Claude Sonnet 4.6  
**연관 설계**: `docs/2026-06-07-router-scope-research-decoupling-design.md` §출구 단절 (Phase 3)

---

## §1 배경 및 동기

### §1.1 meeting_stt_app dogfood에서 확인된 3가지 구조적 실패

AF 파이프라인으로 `projects/meeting_stt_app` (PySide6 + faster-whisper + WASAPI loopback)을 개발하면서 다음 패턴이 반복 관측됐다.

**패턴 A — 생성≠완료 (Generation ≠ Done)**  
파이프라인이 `ok=True`를 반환했으나 실제 e2e 명령(예: `python meeting_stt.py --loopback`) 실행 결과 검증이 없었다. "구현 파일이 생성됨"이 "골에 도달함"으로 오인됐다.

**패턴 B — 실행 안 된 테스트 = 거짓 확신**  
믹서 정렬 회귀 테스트가 생성됐지만 아무도 돌리지 않았다. 테스트 파일 존재 자체가 "검증 완료"로 취급됐고, 그 테스트가 실제로는 FAIL이었다.

**패턴 C — 골 검증 3구멍**  
| 구멍 | 설명 |
|------|------|
| 실행 구멍 | 산출물 유형별 실행 하니스 없음 — 누가 어떻게 실행하는지 계약 없음 |
| 정답 구멍 | oracle 없음 — "올바른 출력"이 무엇인지 명세 없음 |
| 환경 구멍 | CI에 장치(WASAPI 사운드카드, 디스플레이 등) 없음 — 환경 의존 실행 불가 |

### §1.2 핵심 진단

> **사용자 핵심 통찰**: "결국 골에 도달했는지를 검증하는 부분이 부족한 게 문제다"

현재 pipeline의 완료 계약은 **"task가 모두 completed 상태"**로 닫히고, **"goal이 evidence로 충족됐는가"**로 닫히지 않는다.

---

## §2 현재 코드 진단

### §2.1 ok=True 판정 경로

```
project_pipeline.py:1421
    "ok": status == "completed"
        ↑
    status = run_board["current_status"]  (line 1379)
        ↑
    dynamic_orchestrator.py:1218
    self.state_board["current_status"] = "completed"
        ↑ 조건: _todo_fully_completed() → board의 task 카운트만 확인
```

**결론**: `ok=True`는 orchestrator board의 task 카운트가 완료됐을 때만 성립. 산출물 실행·골 충족 여부는 검사하지 않는다.

### §2.2 테스트 검증 경로

```python
# dogfood.py:1845 (_run_review_phase)
passed = verify_result.get("passed", True)
```

`VerifyResult.passed`(bool)만 확인한다. "테스트가 생성됐는가" vs "테스트를 실행해서 green이 나왔는가"를 구분하지 않는다.

### §2.3 단절 4곳 (2026-06-07 설계문서 §1.3 사실 확인)

| # | 위치 | 현재 동작 | 결함 |
|---|------|---------|------|
| ① | `completion_criteria` | 저장만 됨 | gate-reader 0건 — 소비처 없음 |
| ② | `VerifyResult` | passed/commands_run/failures | criteria 필드 없음 |
| ③ | `board_is_complete` | task 카운트만 | acceptance_criteria는 프롬프트 텍스트, 게이트 아님 |
| ④ | `_run_review_phase` | verify.passed만 본다 | criteria 충족 검사 0, `AF_SKIP_REVIEW_GATE=1` 우회 |

### §2.4 `e2e_command_missing` 게이트 현황

이 이름의 게이트는 코드베이스에 존재하지 않는다 (grep 확인). "e2e 커맨드가 없다"는 조건은 LLM이 태스크 내부에서 생성하는 텍스트 조각일 뿐이며, 파이프라인 게이트로 강제되지 않는다.

---

## §3 설계 원칙

이 설계가 지켜야 할 불변식 3개:

**INV-A (증거 없으면 완료 없음)**  
`GoalContract.verdict == "VERIFIED"` 없이는 pipeline `ok=True` 금지. 증거 첨부 없는 완료 선언은 `ok=False, reason="goal_unverified"`.

**INV-B (거짓 확신 금지)**  
테스트가 실행됐는지 알 수 없는 경우 `verdict = "UNVERIFIED"` 명시. "알 수 없음"을 "통과"로 간주 금지.

**INV-C (환경 불가 = 미검증 명시, 실패 아님)**  
장치/디스플레이/네트워크 의존 골은 자동 검증 불가. `verdict = "CANNOT_VERIFY"` 기록 후 DONE 허용. DONE = 자동 검증 가능한 골 전부 VERIFIED + 불가능한 골 전부 CANNOT_VERIFY 명시.

---

## §4 GoalContract 스펙

### §4.1 데이터 구조

```python
# core/completion_contract.py  (신규 파일)

from dataclasses import dataclass, field
from typing import Literal

GoalVerdict = Literal["VERIFIED", "FAILED", "CANNOT_VERIFY", "UNVERIFIED"]

@dataclass
class GoalEvidence:
    evidence_type: str          # "exit_code" | "stdout_contains" | "file_exists" | "manual"
    evidence_value: str         # 실제 캡처된 값 또는 설명
    command_run: str = ""       # 실행한 명령 (있을 경우)

@dataclass
class GoalEntry:
    goal_id: str                # 예: "G-1"
    description: str            # 사람이 읽는 골 설명
    harness_type: str           # "cli" | "server" | "gui" | "library" | "none"
    evidence: GoalEvidence | None = None
    verdict: GoalVerdict = "UNVERIFIED"
    cannot_verify_reason: str = ""   # CANNOT_VERIFY일 때 이유

@dataclass
class GoalContract:
    task_id: str
    goals: list[GoalEntry] = field(default_factory=list)

    def is_done(self) -> bool:
        """INV-A: 모든 골이 VERIFIED 또는 CANNOT_VERIFY여야 done."""
        for g in self.goals:
            if g.verdict in ("UNVERIFIED", "FAILED"):
                return False
        return bool(self.goals)

    def has_failures(self) -> bool:
        return any(g.verdict == "FAILED" for g in self.goals)
```

### §4.2 GoalContract 생성 시점

파이프라인의 **PLAN 단계** 종료 시, planner가 생성하는 `completion_criteria` 텍스트를 파싱해 GoalContract를 초기화한다.

- LLM이 생성한 criteria 각 항목 → `GoalEntry(goal_id, description, harness_type)`
- `harness_type`은 LLM이 키워드(CLI/server/GUI/library)를 명시하면 파싱, 없으면 `"none"`
- 초기 verdict는 전부 `"UNVERIFIED"`

GoalContract는 `DogfoodState`에 직렬화해 persist한다.

---

## §5 ExecutionHarness 카탈로그

실행 하니스는 **산출물 유형별 최소 집합**으로 유지한다. 복잡한 프레임워크 도입 금지.

### §5.1 하니스 종류

| harness_type | 실행 방법 | 성공 증거 | 환경 한계 |
|-------------|---------|---------|---------|
| `cli` | `subprocess.run([cmd, *args], timeout=30)` | exit_code==0 + stdout 키워드 포함 | 없음 (범용) |
| `server` | subprocess 기동 후 `requests.get(url, timeout=10)` | HTTP 200 + 응답 키워드 | 포트 충돌 가능 |
| `gui` | N/A (현재 미구현) | — | 디스플레이 필요 → CANNOT_VERIFY |
| `library` | `python -c "import <mod>; <assertion>"` | 예외 없음 + stdout 키워드 | 없음 (범용) |
| `none` | 실행 없음 | 파일 존재 + 크기 > 0 | — |

### §5.2 HarnessRunner 인터페이스

```python
# core/completion_contract.py (계속)

@dataclass
class HarnessResult:
    ok: bool
    evidence_type: str
    evidence_value: str
    command_run: str

class ExecutionHarness:
    """유형별 하니스 실행기. 각 run()은 timeout 내 결과를 반환한다."""

    def run(
        self,
        goal: GoalEntry,
        workspace: str,
        timeout: int = 30,
    ) -> HarnessResult:
        if goal.harness_type == "cli":
            return self._run_cli(goal, workspace, timeout)
        if goal.harness_type == "server":
            return self._run_server(goal, workspace, timeout)
        if goal.harness_type == "gui":
            return HarnessResult(
                ok=False,
                evidence_type="cannot_verify",
                evidence_value="GUI harness requires display — mark CANNOT_VERIFY",
                command_run="",
            )
        if goal.harness_type == "library":
            return self._run_library(goal, workspace, timeout)
        # "none" or unknown
        return self._run_file_exists(goal, workspace)
```

`_run_cli`, `_run_server`, `_run_library`, `_run_file_exists` 구현은 §8 구현 단계에서 상세 기술.

---

## §6 AcceptanceGate

### §6.1 역할

VERIFY 단계에서 GoalContract의 각 GoalEntry에 대해 하니스를 실행해 verdict를 채운다. 현재 `_run_review_phase`의 `verify.passed` 단순 체크를 대체/보강한다.

### §6.2 게이트 로직

```
AcceptanceGate.run(contract, workspace):
    for each goal in contract.goals:
        if goal.harness_type == "gui":
            goal.verdict = "CANNOT_VERIFY"
            goal.cannot_verify_reason = "display required"
            continue

        result = ExecutionHarness().run(goal, workspace)

        if result.ok:
            goal.evidence = GoalEvidence(
                evidence_type=result.evidence_type,
                evidence_value=result.evidence_value,
                command_run=result.command_run,
            )
            goal.verdict = "VERIFIED"
        else:
            goal.verdict = "FAILED"
            goal.evidence = GoalEvidence(...)

    return contract
```

### §6.3 pipeline 통합 위치

```
dogfood._run_verify_phase()
    현재: pytest 실행 → VerifyResult.passed
    변경: pytest 실행 → VerifyResult.passed
          + AcceptanceGate.run(state.goal_contract, workspace)
          → contract.is_done() → ok=True 조건으로 승격
```

`contract.has_failures()` 시 REVIEW phase는 `decision="block"` 반환 → `block_run()` 호출 → `DogfoodPhase.BLOCKED`(terminal) 종료. Option 2 아키텍처에서 REVIEW block은 FSA 재시도가 아니라 **run 종료**다 (`core/dogfood.py` — `block_run()`: `state.phase = BLOCKED`, `while not state.is_terminal():` 즉시 탈출). 골 실패 후 재시도가 필요하다면 BLOCKED 원인을 "goal_failed"로 분류해 상위 FSA 또는 사용자 개입으로 새 run을 시작하는 경로를 **별도로 설계**해야 한다.

---

## §7 EvidenceLedger — 증거 원장 출력

### §7.1 출력 포맷

pipeline 최종 출력(`project_pipeline.execute()` 반환값)에 `evidence_ledger` 섹션 추가:

```json
{
  "ok": true,
  "run_id": "...",
  "evidence_ledger": {
    "task_id": "T-123",
    "summary": "3 goals: 2 VERIFIED, 0 FAILED, 1 CANNOT_VERIFY",
    "goals": [
      {
        "goal_id": "G-1",
        "description": "CLI로 실행 시 exit code 0 반환",
        "verdict": "VERIFIED",
        "evidence_type": "exit_code",
        "evidence_value": "0",
        "command_run": "python meeting_stt.py --help"
      },
      {
        "goal_id": "G-2",
        "description": "WASAPI loopback 오디오 캡처",
        "verdict": "CANNOT_VERIFY",
        "cannot_verify_reason": "WASAPI requires audio hardware"
      }
    ],
    "unverified": [],
    "cannot_verify": ["G-2"]
  }
}
```

### §7.2 3-section 구조

파이프라인 로그 및 dogfood 최종 보고에는 항상 아래 3-section 포맷으로 출력:

```
=== 골 / 증거 원장 ===

[VERIFIED]
  G-1  CLI exit code 0  →  command: "python meeting_stt.py --help", exit_code=0

[CANNOT_VERIFY]
  G-2  WASAPI loopback  →  이유: WASAPI requires audio hardware (환경 한계)

[UNVERIFIED]
  (없음)
```

`FAILED`가 있으면 `[FAILED]` 섹션 추가 후 FSA 재시도 또는 BLOCKED 처리.

---

## §8 구현 단계

### S1 — GoalContract 구조체 + EvidenceLedger (코드 없는 기반)

- `core/completion_contract.py` 신규: `GoalVerdict`, `GoalEvidence`, `GoalEntry`, `GoalContract`, `HarnessResult`
- `core/dogfood.py`: `DogfoodState.goal_contract: GoalContract | None = None` 필드 추가 + 직렬화
- 테스트: `tests/test_completion_contract.py` — dataclass 계약 + `is_done()` + `has_failures()` 불변식
- **3-Tier 필요**: `completion_contract.py`는 Tier 2 (`core/`), af-critic + af-test-runner

### S2 — ExecutionHarness + AcceptanceGate

- `core/completion_contract.py`: `ExecutionHarness.run()` + `_run_cli`, `_run_server`, `_run_library`, `_run_file_exists`
- `core/completion_contract.py`: `AcceptanceGate.run(contract, workspace)`
- 테스트: mock workspace + 실제 `subprocess.run` stub으로 cli/library/cannot_verify 케이스
- **주의**: `subprocess.run` 사용 → `blast_radius` Tier 3 가능 → af-critic + af-cross-review

### S3 — Pipeline 통합

- `core/dogfood.py` `_run_verify_phase()`: AcceptanceGate 호출 + `ok=True` 조건 교체
- `core/project_pipeline.py` `execute()`: `evidence_ledger` 추가
- 하위 호환: `goal_contract=None`이면 기존 경로(`verify.passed`)로 폴백 — 점진 도입
- 테스트: `tests/test_acceptance_gate_integration.py` — VERIFIED 골 → ok=True, FAILED 골 → ok=False 검증
- **3-Tier 필수**: `dogfood.py`/`project_pipeline.py` = Tier 3 → 풀 3-Tier

---

## §9 불변식 + 테스트 요구사항

| 불변식 ID | 내용 | 테스트 |
|----------|------|-------|
| INV-A | `GoalContract.is_done()==False`이면 pipeline `ok=True` 금지 | `test_ok_blocked_when_goal_unverified` |
| INV-B | `commands_run=[]`이고 `passed=True`면 verdict=`UNVERIFIED` (추측 통과 금지) | `test_no_evidence_means_unverified` |
| INV-C | `harness_type="gui"` → verdict=`CANNOT_VERIFY` (FAILED 아님) | `test_gui_harness_cannot_verify` |
| INV-D | `goal_contract=None`이면 기존 `verify.passed` 폴백 (하위호환) | `test_null_contract_fallback` |
| INV-E | evidence_ledger는 항상 `goals/cannot_verify/unverified` 3-section 포함 | `test_ledger_three_sections_always_present` |

---

## §10 미결 / 의도적 제외 항목

| 항목 | 결정 | 이유 |
|------|------|------|
| GUI offscreen 하니스 | 미구현 (S4 보류) | Qt offscreen plugin 설치 의존성, 복잡도 ↑ |
| Oracle(정답 검증) | 미구현 | 의미적 골은 자동화 불가 — `CANNOT_VERIFY` 처리로 충분 |
| GoalContract LLM 추출 정확도 | 별도 조율 필요 | planner criteria 품질은 이 설계 범위 밖 |
| CI 장치 프로비저닝 | 별도 인프라 작업 | 환경 구멍은 `CANNOT_VERIFY` 명시로 대응, CI 셋업은 별도 |
| `completion_criteria` 파싱 로직 | S1 구현 시 결정 | LLM criteria 포맷이 확정되면 파서 설계 |

---

## §11 연결 지점

**`docs/2026-06-07-router-scope-research-decoupling-design.md` §1.3 "출구 단절 4곳"**:
- 단절 ①②③④ 모두 이 설계의 GoalContract + AcceptanceGate가 해소 대상
- Phase 3 (Completion Contract) = 이 문서가 그 설계

**`core/fsa_loop.py`**:
- FSA 재시도 루프는 `ok=False, reason="goal_failed"`를 수신하면 IMPLEMENT 단계로 되돌아가야 함
- `failure_classifier`에 `"goal_failed"` 패턴 추가 필요 (S3 구현 시)

**`core/premortem.py`**:
- premortem이 "실행 하니스 없음" 위험을 R-series 패턴으로 탐지하면 AcceptanceGate 강제 발화 연동 가능
- 별도 detector 추가 여부는 S3 완료 후 평가

---

## §12 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-06-17 | Draft 작성 (Sonnet 4.6) — meeting_stt_app dogfood 3가지 실패 패턴 기반 |
| 2026-06-17 | §6.3 High 수정 — FSA 재시도 → BLOCKED terminal 아키텍처 사실 반영 (af-cross-review WARN) |
