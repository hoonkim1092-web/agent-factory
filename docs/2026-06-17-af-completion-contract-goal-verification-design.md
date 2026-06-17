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

### §2.4 `e2e_command_missing` 게이트 현황 — 기존 게이트와의 관계

> **2026-06-18 정정**: 초안은 "이 게이트는 존재하지 않는다"고 기술했으나 사실 오류였다. `e2e_command_missing`은 실재하는 P4 escalation 게이트다.

**기존 게이트 실재 (grep 확인)**:
- `core/work_item_generator.py:1312` — `WarningRegistry.record(rule_id="e2e_command_missing", severity="warn")`. task에 `e2e_command` 필드가 비면 warn 기록.
- `core/escalation_evaluator.py:3` + `config/escalation_policy.yaml` — 현재 단계(P2)에서 이 warn을 BLOCK으로 승격.
- **이 설계의 동기 dogfood가 실제로 막혔다**: `drive_meeting_stt.py:4-8` — "생성된 work-item task 에 e2e_command 가 없어 P4 escalation block(`e2e_command_missing`)이 걸려 execute() 가 코드 생성 직전 조용히 반환한다" → 작성자가 `upsert_override(..., "e2e_command_missing", ...)`로 우회.

**기존 게이트의 한계 = 이 설계의 존재 이유**:
기존 `e2e_command_missing`은 **presence-check** — task에 `e2e_command` *문자열 필드가 있는지*만 본다. 그 명령을 **실행하지 않고**, 실행 결과(exit code·stdout)를 **증거로 캡처하지 않는다**. 즉 "e2e 커맨드가 적혀 있다"는 통과시키지만 "e2e 커맨드가 실제로 green인가"는 검증하지 못한다 — 패턴 B(실행 안 된 테스트 = 거짓 확신)를 그대로 통과시킨다.

**관계 결정**: AcceptanceGate는 기존 presence-check를 **evidence-check로 승격한다**. 기존 `e2e_command_missing` warn/escalation은 "계약(harness_type)이 비었다"는 *입력 단계 신호*로 보존하고 (제거하지 않음), AcceptanceGate는 그 계약을 *실행해서 증거를 채우는* VERIFY 단계 게이트로 추가된다. 두 게이트는 단계가 다르므로 공존한다 — escalation_policy 수정은 이 설계 범위 밖.

---

## §3 설계 원칙

이 설계가 지켜야 할 불변식 3개:

**INV-A (증거 없으면 완료 없음)**  
`GoalContract.is_done() == True`(모든 골이 VERIFIED 또는 CANNOT_VERIFY) 없이는 pipeline `ok=True` 금지. 증거 첨부 없는 완료 선언은 `ok=False, reason="goal_unverified"`. (`GoalContract`에는 `verdict` 필드가 없다 — 개별 `GoalEntry.verdict`를 `is_done()`이 집계한다.)

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

**파서 폴백 불변식 (INV-A 보호)**: GoalContract 전체의 검증 강도는 이 파싱 품질에 의존한다(§10의 "criteria 품질은 범위 밖"과 연결되는 load-bearing 지점). 파서가 어떤 골에서도 harness_type을 못 뽑아 **모든 골이 `"none"`으로 떨어지는 경우**, 그 계약은 실질 검증 없이 file-exists만으로 DONE이 될 수 있다 — 이는 패턴 A를 재도입한다. 따라서:
- harness_type을 못 뽑은 골은 `verdict="UNVERIFIED"`로 **유지**되고, file-exists로 자동 승격되지 **않는다** (§5.1 `"none"` 항목 참조).
- 결과적으로 그런 골을 가진 계약은 `is_done()==False` → INV-A에 의해 `ok=True` 차단. "키워드 없음 = 검증 불가(UNVERIFIED)"가 "키워드 없음 = 파일만 보고 통과"보다 안전하고 설계 의도에 부합한다.

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
| `none` | 실행 없음 | **증거 불충분 → `verdict="UNVERIFIED"`** (파일 존재만으로 VERIFIED 승격 금지) | — |

> **`none` 의미 정정 (2026-06-18)**: 초안은 `none` → "파일 존재 + 크기 > 0 = 성공"으로 기술했으나, 이는 패턴 A(생성=완료)와 동일하다. harness_type을 못 뽑았다는 것은 "어떻게 검증할지 모른다"는 뜻이므로 자동 통과가 아니라 `UNVERIFIED`(미검증)로 남긴다. 파일 존재가 의미 있는 골이라면 LLM criteria가 `library`(import 검증) 또는 `cli`(실행 검증)로 분류되어야 하며, 그렇지 못한 골은 §4.2 파서 폴백 불변식에 따라 INV-A로 `ok=True`를 차단한다.

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
        # "none" or unknown — 증거 불충분. 자동 통과(file-exists) 금지(§5.1 정정).
        # ok=False + evidence_type="unverified" → AcceptanceGate가 verdict="UNVERIFIED" 부여.
        return HarnessResult(
            ok=False,
            evidence_type="unverified",
            evidence_value="harness_type unresolved — cannot auto-verify",
            command_run="",
        )
```

`_run_cli`, `_run_server`, `_run_library` 구현은 §8 구현 단계에서 상세 기술. (초안의 `_run_file_exists`는 §5.1 정정으로 제거 — file-exists는 검증 증거가 아님.)

**AcceptanceGate verdict 매핑 보강**: `evidence_type=="unverified"`(harness 미해결)는 `FAILED`가 아니라 `UNVERIFIED`로 매핑한다 — §6.2 게이트 로직의 `else` 분기에서 `result.evidence_type`을 구분해 `unverified`→`UNVERIFIED`, 실제 실행 실패→`FAILED`로 나눈다.

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
        elif result.evidence_type == "unverified":
            # harness_type 미해결 → 검증 불가(미실행). FAILED 아님 (§5.1/§5.2 정정).
            goal.verdict = "UNVERIFIED"
            goal.evidence = GoalEvidence(
                evidence_type="unverified",
                evidence_value=result.evidence_value,
                command_run="",
            )
        else:
            # 실제 실행 후 실패(exit code != 0, 키워드 누락 등).
            goal.verdict = "FAILED"
            goal.evidence = GoalEvidence(
                evidence_type=result.evidence_type,
                evidence_value=result.evidence_value,
                command_run=result.command_run,
            )

    return contract
```

> **`UNVERIFIED` vs `FAILED` 구분이 INV-A/INV-B에 직결**: `is_done()`은 둘 다 `False`를 반환하므로(§4.1) 어느 쪽이든 `ok=True`를 차단한다 — 안전성은 동일. 다만 증거원장(§7) 보고에서 "실행했는데 실패(FAILED, 재시도 의미 있음)"와 "검증 방법을 못 정해 미실행(UNVERIFIED, criteria 보강 필요)"은 사용자 조치가 다르므로 분리한다.

### §6.3 pipeline 통합 위치

> **2026-06-18 정정 (High — 통합 지점이 ok=True SSOT를 놓침)**: 초안은 AcceptanceGate를 `dogfood._run_verify_phase()`에만 배선했다. 그러나 `ok=True` 판정의 **SSOT는 `project_pipeline.execute()`(line 1421 `"ok": status == "completed"`)**이며(§2.1이 이미 그렇게 진단), **`project_pipeline.execute()`는 `dogfood._run_verify_phase()`를 경유하지 않는다** (`execute():1275` → `orchestrator.run_project():1373` → ok 판정). 결정적으로 **이 설계의 동기 dogfood(`drive_meeting_stt.py:68`)가 `factory.project_pipeline.execute()`를 직접 호출**한다 — 즉 초안 배선으로는 동기 케이스를 못 막는다. 따라서 게이트는 **ok=True SSOT 지점에 배선**한다.

**1차 배선 (SSOT, 모든 진입점 커버) — `project_pipeline.execute()`**:
```
project_pipeline.execute():1421
    현재: "ok": status == "completed"
    변경: contract = <run의 GoalContract>  (없으면 None)
          if contract is not None:
              AcceptanceGate.run(contract, workspace)
              ok = (status == "completed") and contract.is_done()
              if not ok: reason = "goal_unverified" if not contract.has_failures() else "goal_failed"
          else:
              ok = status == "completed"   # INV-D 폴백 (§8 S3에서 조건 제한)
          + evidence_ledger = contract → §7 포맷 (contract None이면 빈 ledger 명시)
```
GoalContract를 `execute()`에서 접근하려면 **run 컨텍스트에 실어야 한다** — `DogfoodState.goal_contract`(dogfood 경로) 외에, 직접 `execute()` 호출 경로는 `prepared`/run-board를 통해 contract를 전달하는 배선을 §8 S3에서 명시한다(신규 파라미터 최소화: 기존 run 컨텍스트 dict 채널 우선).

**2차 배선 (보강, dogfood 경로 한정) — `dogfood._run_verify_phase()`**:
pytest 실행 → `VerifyResult.passed` + `AcceptanceGate.run(state.goal_contract, workspace)`. `contract.has_failures()` 시의 처리는 §6.4(골 실패 → 수정 루프)로 닫는다 — 현재 코드의 BLOCKED-terminal은 **사실**이고, end-to-end 목표는 그 terminal을 IMPLEMENT 피드백 루프로 바꾸는 것이다.

> **이중 배선 주의**: 1차(execute)와 2차(verify_phase)가 같은 contract에 대해 AcceptanceGate를 두 번 실행하지 않도록, dogfood 경로는 `_run_verify_phase`에서 실행하고 `execute()`는 이미 채워진 verdict를 **재실행 없이 집계만** 한다(idempotent: 이미 VERIFIED/FAILED인 골은 재실행 skip). §8 S3에서 idempotent 가드 명시.

### §6.4 골 실패 → 수정 루프 (end-to-end 닫기) — Phase 3 본체로 승격

> **2026-06-18 승격**: 초안은 골 FAILED → BLOCKED terminal로 멈추고, "goal_failed → IMPLEMENT 재시도"를 §11로 보류했다. 그러나 골 테스트의 핵심 가치는 **버그를 찾는 것이 아니라 찾아서 고치는 것**이다. 멈추기만 하면 detector이지 end-to-end가 아니다. 따라서 이 루프를 본체로 승격한다.

**현재 상태 (사실)**: `AcceptanceGate`가 골 FAILED를 내면 REVIEW phase `decision="block"` → `block_run()` → `DogfoodPhase.BLOCKED`(terminal). `while not state.is_terminal():`가 즉시 탈출하므로 **수정 없이 run이 끝난다**. 버그는 검출되지만 닫히지 않는다.

**목표 모델 — 닫힌 루프**:
```
AcceptanceGate → goal FAILED
   │
   ├─ failure_classifier: "goal_failed" → IMPLEMENTATION 클래스 (infra 아님)
   │     (CANNOT_VERIFY는 분류 제외 — 환경 한계는 고칠 수 없음, 루프 진입 금지)
   │
   ├─ FSA → IMPLEMENT 단계 복귀 → 수정 → AcceptanceGate 재실행
   │     (코드리뷰 BLOCK→수정→재리뷰와 동일한 피드백 구조)
   │
   └─ 경계(무한루프 차단): goal_failed 재시도는 FSA의 기존 max-retry bound 재사용.
         N회 후에도 FAILED면 BLOCKED(reason="goal_failed_exhausted")로 종료 +
         evidence_ledger에 [FAILED] 섹션 + 시도 횟수 기록 → 사용자 개입.
```

**구현 3요소 (S3에서 함께)**:
1. **`failure_classifier`**: `goal_failed` 패턴을 `IMPLEMENTATION` 클래스로 등록(`_INFRA_PATTERNS`에 **넣지 않음** — 고칠 수 있는 결함). `CANNOT_VERIFY`로 끝난 골은 분류 대상 아님.
2. **dogfood 피드백 경로**: 현재 VERIFY/REVIEW → BLOCKED(terminal)을, `goal_failed`일 때만 IMPLEMENT로 되돌리는 분기 추가. **`block_run()`은 `goal_failed_exhausted`·`CANNOT_VERIFY`가 아닌 진짜 종료에만 유지** (Option 2 FSA-소유 원칙과 충돌하지 않게: 루프 소유권은 FSA, dogfood는 분류·라우팅만).
3. **bound**: FSA `max-retry`(기존 상수 재사용) + `CANNOT_VERIFY` 루프 제외 + exhausted 시 evidence 보존. 무한루프(안 고쳐지는 골)와 환경불가 골의 헛도는 재시도를 둘 다 차단.

**불변식 추가 (§9 INV-G)**: `verdict="CANNOT_VERIFY"`는 절대 IMPLEMENT 루프를 유발하지 않는다(환경 한계는 수정 불가). `verdict="FAILED"`만 bound 내에서 루프한다.

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
- **직렬화 명세 (필수)**: `DogfoodState.to_dict()`/`from_dict()`는 수동 변환이다(`core/dogfood.py:197-269`) — 중첩 dataclass를 자동 직렬화하지 않는다. 따라서:
  - `GoalContract.to_dict()` / `GoalContract.from_dict(data)` 메서드를 `completion_contract.py`에 함께 구현(중첩 `GoalEntry`/`GoalEvidence`까지 재귀 변환). `GoalVerdict`는 `Literal[str]`이라 JSON round-trip 가능.
  - `DogfoodState.to_dict()`에 `"goal_contract": self.goal_contract.to_dict() if self.goal_contract else None` 추가.
  - `DogfoodState.from_dict()`에 `goal_contract=GoalContract.from_dict(d) if (d := data.get("goal_contract")) else None` 복원 추가.
  - 테스트: round-trip 불변식(`from_dict(to_dict(x)) == x`).
- `core/dogfood.py`: `DogfoodState.goal_contract: GoalContract | None = None` 필드 추가
- 테스트: `tests/test_completion_contract.py` — dataclass 계약 + `is_done()` + `has_failures()` 불변식 + 직렬화 round-trip
- **3-Tier 필요**: `completion_contract.py`는 Tier 2 (`core/`), af-critic + af-test-runner

### S2 — ExecutionHarness + AcceptanceGate

- `core/completion_contract.py`: `ExecutionHarness.run()` + `_run_cli`, `_run_server`, `_run_library` (※ `_run_file_exists`는 §5.1/§5.2 정정으로 제거 — `none`/unknown은 `UNVERIFIED` 반환, file-exists 자동통과 없음)
- `core/completion_contract.py`: `AcceptanceGate.run(contract, workspace)`
- 테스트: mock workspace + 실제 `subprocess.run` stub으로 cli/library/cannot_verify 케이스
- **주의**: `subprocess.run` 사용 → `blast_radius` Tier 3 가능 → af-critic + af-cross-review

### S3 — Pipeline 통합

- **1차 배선 (필수, SSOT)**: `core/project_pipeline.py` `execute():1421` — `ok = (status=="completed") and contract.is_done()` (§6.3 1차 배선). GoalContract를 run 컨텍스트(`prepared`/run-board dict 채널)로 `execute()`에 전달하는 배선 추가(신규 시그니처 최소화). `evidence_ledger` 추가.
- **2차 배선 (dogfood 보강)**: `core/dogfood.py` `_run_verify_phase()` — AcceptanceGate 호출. `execute()`는 이미 채워진 verdict를 **재실행 없이 집계**(idempotent 가드: 골이 이미 VERIFIED/FAILED/CANNOT_VERIFY면 `ExecutionHarness.run` skip).
- **하위 호환 폴백 경계 (Low 방어보강 — production 미도달, 전환기 한정)**: `goal_contract=None`이면 기존 `verify.passed` 폴백. 이론상 `verify_result.get("passed", True)`의 기본값 `True`(`core/dogfood.py:1899`)와 결합하면 "contract 없음 + verify 빈 dict → 무음 pass"가 INV-B를 위반할 수 있다. **단 production 도달 경로는 아니다**: `_run_review_phase`는 항상 `context={"verify_result": ...}`로 호출되고(`core/dogfood.py:2038`) `_run_verify_phase`가 `passed`를 항상 채운다 — 빈 `context={}`는 단위 테스트 전용. 그럼에도 전환기 방어로 폴백 진입을 다음으로 **제한**한다(cheap):
  - `goal_contract=None`은 **점진 도입 전환기에만** 허용되는 상태로 정의. S3 배선 완료 후에는 planner가 criteria를 못 뽑아도 **전부 `UNVERIFIED`인 비어있지 않은 contract**를 만든다(§4.2 파서 폴백) → `goal_contract`는 사실상 None이 되지 않는다.
  - 전환기 폴백 시에도 `verify_result`가 **빈 dict이면 pass 금지** — 폴백 경로는 `passed = verify_result.get("passed", True)`가 아니라 `verify_result`에 `passed` 키가 **실제로 존재**할 때만 그 값을 쓰고, 부재 시 `ok=False, reason="goal_unverified"`로 떨어뜨린다(INV-B). 기존 테스트 `test_run_review_missing_verify_result_assumes_passed`는 이 정책 변경에 맞춰 갱신 필요(고정된 pass 가정 해제).
- **골 실패 → 수정 루프 (§6.4, end-to-end 닫기)**:
  - `core/failure_classifier.py`: `goal_failed` → IMPLEMENTATION 클래스 추가(`_INFRA_PATTERNS` 아님). `CANNOT_VERIFY`는 분류 제외(INV-G).
  - `core/dogfood.py`: `goal_failed`(exhausted 아님)일 때 VERIFY/REVIEW → IMPLEMENT 되돌림 분기. `block_run()`은 `goal_failed_exhausted`·`CANNOT_VERIFY`가 아닌 종료에만. 루프 소유권은 FSA(`fsa_loop.py`), dogfood는 분류·라우팅만.
  - bound: FSA 기존 max-retry 상수 재사용. exhausted 시 BLOCKED(reason="goal_failed_exhausted") + evidence_ledger [FAILED] 섹션 보존.
- 테스트: `tests/test_acceptance_gate_integration.py` — ① VERIFIED 골 → ok=True ② FAILED 골 → ok=False ③ **`execute()` 직접 호출 경로(dogfood 미경유)에서도 contract 차단 적용** ④ contract=None + verify 빈 dict → ok=False(무음 pass 금지, INV-B) ⑤ **FAILED → IMPLEMENT 루프 (bound 내) / CANNOT_VERIFY → 루프 없음 (INV-G) / exhausted → BLOCKED+evidence**
- **3-Tier 필수**: `dogfood.py`/`project_pipeline.py`/`failure_classifier.py`/`fsa_loop.py` = Tier 3 → 풀 3-Tier

---

## §9 불변식 + 테스트 요구사항

| 불변식 ID | 내용 | 테스트 |
|----------|------|-------|
| INV-A | `GoalContract.is_done()==False`이면 pipeline `ok=True` 금지 — **ok=True SSOT(`project_pipeline.execute:1421`)에 배선**, dogfood 미경유 직접 호출 경로 포함 | `test_ok_blocked_when_goal_unverified`, `test_execute_direct_path_gated` |
| INV-B | `commands_run=[]`이고 `passed=True`면 verdict=`UNVERIFIED` (추측 통과 금지) | `test_no_evidence_means_unverified` |
| INV-C | `harness_type="gui"` → verdict=`CANNOT_VERIFY` (FAILED 아님) | `test_gui_harness_cannot_verify` |
| INV-D | `goal_contract=None` 폴백은 전환기 한정 + **`verify_result`에 `passed` 키가 실제 존재할 때만** 그 값 사용. 빈 dict → `ok=False`(무음 pass 금지, INV-B와 정합) | `test_null_contract_empty_verify_blocks` |
| INV-E | evidence_ledger는 항상 `goals/cannot_verify/unverified` 3-section 포함 | `test_ledger_three_sections_always_present` |
| INV-F | `harness_type="none"`(미해결) 골 → verdict=`UNVERIFIED` (file-exists 자동 통과 금지, §5.1 정정) → `is_done()==False` | `test_none_harness_stays_unverified` |
| INV-G | `verdict="CANNOT_VERIFY"`는 IMPLEMENT 수정 루프를 유발하지 않는다(환경 한계=수정 불가). `verdict="FAILED"`만 FSA max-retry bound 내에서 루프. exhausted 시 BLOCKED(reason="goal_failed_exhausted") (§6.4) | `test_cannot_verify_no_retry`, `test_failed_loops_within_bound`, `test_exhausted_blocks_with_evidence` |

---

## §10 미결 / 의도적 제외 항목

| 항목 | 결정 | 이유 |
|------|------|------|
| GUI offscreen 하니스 | 미구현 (S4 보류) | Qt offscreen plugin 설치 의존성, 복잡도 ↑ |
| Oracle(정답 검증) | 미구현 | 의미적 골은 자동화 불가 — `CANNOT_VERIFY` 처리로 충분 |
| GoalContract LLM 추출 정확도 | 별도 조율 필요 | planner criteria 품질은 이 설계 범위 밖 |
| CI 장치 프로비저닝 | 별도 인프라 작업 | 환경 구멍은 `CANNOT_VERIFY` 명시로 대응, CI 셋업은 별도 |
| `completion_criteria` 파싱 로직 | S1 구현 시 결정 | LLM criteria 포맷이 확정되면 파서 설계 |
| ~~goal_failed → IMPLEMENT 재시도 루프~~ | **§6.4로 승격(2026-06-18)** — 더 이상 보류 아님 | 골 테스트의 핵심 가치는 "찾아 고치기". detector에 그치면 end-to-end 아님 |

---

## §11 연결 지점

### §11.0 하나의 축 — "검증은 완료 이벤트에 매달린 스테이지, 결함은 IMPLEMENT로 되먹임" (2026-06-18)

이 설계는 독립 기능이 아니라 **세 설계가 공유하는 한 원칙**의 출구 절반이다:

| 설계 | 역할 | 같은 원칙의 어느 면 |
|------|------|-------------------|
| router decoupling (2026-06-07) **Phase 2** | post-implement **Tier3 코드리뷰 floor** (observe-first) | 리뷰 = implement 완료 시 도는 **스테이지** (자율 경로 `_inject_review_tasks`) |
| **이 문서 Phase 3** | AcceptanceGate **골 증거 검증** | 골테스트 = implement 완료 시 도는 **스테이지** |
| §6.4 (이번 승격) | 골/리뷰 결함 → IMPLEMENT **수정 루프** | 결함 되먹임 (코드리뷰 BLOCK·골 FAILED 공통 구조) |

**핵심 함의 — UserPromptSubmit 자동발화는 이 모델과 충돌**:
- 3-Tier 리뷰 자동발화를 `UserPromptSubmit`(사람 키 입력 = 폴링)에 매달면, "implement 완료" 이벤트와 디커플됨. 올바른 트리거는 **완료 이벤트**(자율=파이프라인 스테이지, 인터랙티브=커밋/어시스턴트 완료 판단)다.
- 실제로 `UserPromptSubmit` 훅 제거 시 **단절④의 `AF_SKIP_REVIEW_GATE=1` 우회가 상시 강제**된다 — 즉 자동발화 폴링을 떼면 이 설계가 닫으려는 바로 그 구멍이 더 벌어진다. **결론**: 넛지 복원이 아니라 검증을 완료-이벤트 스테이지로 모델링(§6.4 루프 포함)하는 것이 정답.

### §11.1 `docs/2026-06-07-router-scope-research-decoupling-design.md` §1.3 "출구 단절 4곳"
- 단절 ①②③④ 모두 이 설계의 GoalContract + AcceptanceGate가 해소 대상
- **단절④ = `_run_review_phase`(`:1845`) + finalize `AF_SKIP_REVIEW_GATE=1`(`:1052`) 우회** = §11.0의 UserPromptSubmit 제거가 벌린 그 구멍. §6.4 수정 루프 + ok=True SSOT 배선(§6.3)이 정공법 해소.
- Phase 3 (Completion Contract) = 이 문서가 그 설계

### §11.2 `core/fsa_loop.py` + `core/failure_classifier.py` (§6.4 본체)
- FSA 재시도 루프는 `ok=False, reason="goal_failed"`를 수신하면 IMPLEMENT 단계로 되돌아간다 (§6.4 — **보류 아님, Phase 3 본체**)
- `failure_classifier`에 `"goal_failed"`를 **IMPLEMENTATION 클래스**로 추가(`_INFRA_PATTERNS` 아님). `CANNOT_VERIFY`는 분류 제외(INV-G)
- max-retry bound는 FSA 기존 상수 재사용 — exhausted 시 `goal_failed_exhausted` BLOCKED

### §11.3 `core/premortem.py`
- premortem이 "실행 하니스 없음" 위험을 R-series 패턴으로 탐지하면 AcceptanceGate 강제 발화 연동 가능
- 별도 detector 추가 여부는 S3 완료 후 평가

---

## §12 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-06-17 | Draft 작성 (Sonnet 4.6) — meeting_stt_app dogfood 3가지 실패 패턴 기반 |
| 2026-06-17 | §6.3 High 수정 — FSA 재시도 → BLOCKED terminal 아키텍처 사실 반영 (af-cross-review WARN) |
| 2026-06-18 | 코드 대조 리뷰 3건 반영 (Opus): ① §2.4 사실 정정 — `e2e_command_missing` 게이트는 실재(work_item_generator:1312·escalation_evaluator·drive_meeting_stt.py 동기 dogfood가 실제로 막힘). presence-check vs evidence-check 구분 + 공존 관계 명시 ② §4.2/§5.1/§5.2/§6.2 — `harness_type="none"` 기본값을 file-exists 자동통과 → `UNVERIFIED`로 정정(패턴 A 재도입 차단). `UNVERIFIED`/`FAILED` verdict 분기 추가 ③ §9 INV-F 신규 |
| 2026-06-18 | 세 설계 연결 + 골 실패 수정루프 승격 (Opus): ① §11.0 신규 — router decoupling Phase 2(post-implement Tier3 floor) + 이 문서 Phase 3(골 검증) + §6.4(수정 루프)가 "검증=완료-이벤트 스테이지, 결함=IMPLEMENT 되먹임" 한 축. **UserPromptSubmit 자동발화(폴링)는 이 모델과 충돌** — 제거 시 단절④ `AF_SKIP_REVIEW_GATE` 우회 상시 강제(구멍 확대), 정답은 완료-이벤트 스테이지화 ② §6.4 신규 — `goal_failed → IMPLEMENT 수정 루프`를 §11 보류 → Phase 3 본체로 **승격**. failure_classifier(IMPLEMENTATION 클래스)+dogfood 피드백 경로+FSA max-retry bound 3요소. detector→end-to-end ③ §9 INV-G(CANNOT_VERIFY는 루프 금지, FAILED만 bound 내 루프) + §8 S3 루프 구현·테스트 ⑤ §10 goal_failed 루프 항목 "승격"으로 이동 |
| 2026-06-18 | af-cross-review 발견 검증 후 4건 수용·1건 severity 하향 (Opus). **전건 동조 아님 — 각 건 grep 직접 반증 후 판정**: ① **High (수용)** §6.3/§8 S3 — AcceptanceGate를 ok=True SSOT(`project_pipeline.execute:1421`)에 1차 배선(동기 dogfood `drive_meeting_stt.py:68`이 execute 직접 호출 → dogfood verify 미경유 갭 해소). idempotent 이중배선 가드. (1차 코드대조 리뷰가 놓친 진짜 아키텍처 갭) ② **Low로 하향 (cross-review는 High로 보고)** §8 S3/INV-D — `goal_contract=None`+`verify` 빈 dict → 무음 pass 시나리오는 **production 미도달**: `_run_review_phase`는 항상 `context={"verify_result": ...}`로 호출되고(`core/dogfood.py:2038`) `_run_verify_phase`가 `passed`를 항상 채운다. 빈 `context={}` 호출자는 `tests/test_dogfood.py`뿐(production caller 0). cross-review가 테스트 픽스처(`test_..._assumes_passed`)를 결함 실체로 격상한 케이스(메모리 `feedback_test_mock_vs_defect`). **수정은 유지**(폴백을 `passed` 키 실존 시로 제한 = cheap 전환기 방어)하되 severity는 Low 방어보강. ③ **Adv 수용** §8 S2 `_run_file_exists` 잔존 제거(자체 편집 미완성) ④ **Adv 수용** §8 S1 직렬화 명세 추가 ⑤ **Adv 수용** §3 INV-A `GoalContract.verdict`→`is_done()` 오표기 정정. **수용 거부 1건** (BONUS: `work_item_generator.py:1318` source_path stale = 기존 코드 annotation 오류, 본 설계 무관 — 미수정). 따라서 실제 BLOCK 기여는 High#1 1건. |
