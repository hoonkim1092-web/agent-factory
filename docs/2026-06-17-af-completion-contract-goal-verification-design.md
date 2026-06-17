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
# dogfood.py:1899 (_run_review_phase, def 위치 :1891)
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

### §4.2 GoalContract 생성 시점 — SSOT는 `prepare()` (모든 진입점 커버)

> **2026-06-18 정정 (High — 생성 SSOT가 동기 경로를 못 막음)**: 초안은 생성을 "PLAN 단계 + DogfoodState 직렬화"로만 기술했다. 그러나 동기 dogfood(`drive_meeting_stt.py:68`)는 `project_pipeline.execute()`를 직접 호출 — dogfood phase·DogfoodState를 **경유하지 않는다**. DogfoodState에서만 contract를 만들면 동기 경로는 contract가 영구 `None` → §6.3 1차 게이트가 그 경로에서 **절대 발화 안 함**. 따라서 생성 SSOT를 모든 진입점이 거치는 `prepare()`로 옮긴다.

**생성 SSOT = `project_pipeline.prepare()` (`:1246`)**:
파이프라인의 **PLAN/prepare 단계**에서 task_board의 `acceptance_criteria`(planner가 생성, `project_pipeline.py:342`·`:520`에서 이미 다뤄지는 필드)를 파싱해 GoalContract를 초기화한다.

- criteria 각 항목 → `GoalEntry(goal_id, description, harness_type)`
- `harness_type`은 LLM이 키워드(CLI/server/GUI/library)를 명시하면 파싱, 없으면 `"none"`
- 초기 verdict는 전부 `"UNVERIFIED"`
- 생성된 GoalContract를 **`PreparedProject`(`project_pipeline.py:74`)에 적재** → `execute()`가 run 컨텍스트에서 읽는다(§6.3 1차 배선). 이로써 동기·dogfood 양 경로 모두 동일 SSOT에서 contract를 받는다.

**`DogfoodState` 직렬화는 부가 persist(생성 아님)**: dogfood 경로는 resume/cross-PC handoff를 위해 `DogfoodState.goal_contract`로도 직렬화하지만(§8 S1), 이는 prepare가 만든 contract를 **persist**하는 보조 채널일 뿐 생성 지점이 아니다. 생성 SSOT는 prepare 하나.

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

`execute()`에는 `ok` 판정이 **두 곳**에 있다 — `:1396`(`append_dashboard_run(... "ok": status=="completed")` 텔레메트리)과 `:1421`(반환값). **둘 중 하나만 게이팅하면 텔레메트리 거짓**(대시보드 `ok=true`, 반환 `ok=false`). 따라서 gated `ok`를 **`:1390 append_dashboard_run` 호출 이전에 한 번 계산**해 두 지점이 같은 값을 쓴다(Finding #4).

```
project_pipeline.execute()
    # ── ① 게이트 계산 (append_dashboard_run :1390 이전) ──
    contract = prepared.goal_contract  (run 컨텍스트, 없으면 None)
    if contract is not None:
        AcceptanceGate.run(contract, workspace)   # idempotent 가드(§6.3 이중배선 주의)
        gated_ok = (status == "completed") and contract.is_done()
        reason   = "" if gated_ok else ("goal_failed" if contract.has_failures() else "goal_unverified")
    else:
        gated_ok = (status == "completed")   # INV-D 폴백 (§8 S3에서 조건 제한)
        reason   = ""
    evidence_ledger = contract → §7 포맷 (contract None이면 빈 ledger 명시)

    # ── ② 대시보드(:1396) ──  "ok": gated_ok  ← status=="completed" 대신 gated_ok
    # ── ③ 반환(:1421) ──      "ok": gated_ok, "reason": reason, "evidence_ledger": ...
```

GoalContract를 `execute()`에서 접근하려면 **run 컨텍스트에 실어야 한다** — 생성 SSOT는 `prepare()`이고(§4.2), 그 산출물 `PreparedProject.goal_contract`(`project_pipeline.py:74` 신규 필드)를 `execute()`가 읽는다. `DogfoodState.goal_contract`는 dogfood 경로의 부가 persist 채널일 뿐(신규 파라미터 최소화: 기존 `prepared` 객체 채널 우선).

**조기 반환 경로도 게이트 적용 (Finding #5 — `:1301-1307` `already_done`)**:
`execute():1301` `_cp.next_step_cursor == "done"` 인 resume/cached run은 `:1307` `{"ok": True, "reason": "already_done"}`로 **`:1421` 게이트 도달 전 조기 반환**한다. 게이트 도입 *전*에 done으로 표시된 run을 resume하면 증거 없이 `ok=True`가 새어나가 INV-A를 위반한다. 처리:
- `prepared.goal_contract`가 있으면 조기 반환 직전 `contract.is_done()`을 **재집계**(이미 채워진 verdict만 읽음, 하니스 재실행 없음 — idempotent)해 `gated_ok`로 반환한다. contract가 없으면(전환기 done run) `reason="already_done_legacy"`로 명시 반환하고 **INV-A 예외임을 ledger에 정직히 기록**(증거 부재 표기).
- 이 분기는 §8 S3에서 명시. INV-A 문구(§9)에 "게이트 도입 이전 done-표시 resume run은 evidence 부재로 `already_done_legacy` 명시"라는 한정 예외를 추가한다.

**2차 배선 (보강, dogfood 경로 한정) — `dogfood._run_verify_phase()`**:
pytest 실행 → `VerifyResult.passed` + `AcceptanceGate.run(state.goal_contract, workspace)`. `contract.has_failures()` 시에는 **`block_run()` → `DogfoodPhase.BLOCKED`(reason="goal_failed") terminal**로 닫는다(§6.4). 이는 현재 코드의 BLOCKED-terminal 동작을 **그대로 따른다**(inv3 정합) — 골 실패를 dogfood 레벨에서 IMPLEMENT로 되돌리는 retry는 `dogfood.py:2044`(`inv3: no retry in Option 2`)·`:1895` docstring이 명시 금지하므로 하지 않는다. 자동 수정 루프는 dogfood 밖 별도 메커니즘이며 §6.4에서 범위 분리한다.

> **이중 배선 주의**: 1차(execute)와 2차(verify_phase)가 같은 contract에 대해 AcceptanceGate를 두 번 실행하지 않도록, dogfood 경로는 `_run_verify_phase`에서 실행하고 `execute()`는 이미 채워진 verdict를 **재실행 없이 집계만** 한다(idempotent: 이미 VERIFIED/FAILED인 골은 재실행 skip). §8 S3에서 idempotent 가드 명시.

### §6.4 골 실패 처리 — BLOCKED(goal_failed) terminal (Phase 3 본체) + 수정 루프는 별도 메커니즘으로 분리

> **2026-06-18 재작성 (Critical — 초안 §6.4가 코드 inv3를 정면 위반 + 사실오류)**: 직전 초안은 "골 FAILED → dogfood가 IMPLEMENT로 되돌림 → FSA 기존 max-retry 상수 재사용"으로 수정 루프를 본체 승격했다. 자동 설계리뷰(`docs/reviews/2026-06-18-015950-...`)가 이를 **Critical BLOCK**으로 판정했고 grep으로 전건 확인됐다:
> - **inv3 위반**: dogfood 레벨에서 골 실패를 IMPLEMENT로 되돌리는 retry는 `dogfood.py:2044`(`advance_phase(state)  # → FINALIZE (inv3: no retry in Option 2)`)와 `:1895` docstring("a dogfood-level retry is redundant and its reset destroys FSALoop learning")이 **의도적으로 제거·금지**한 동작이다. 초안은 코드가 막아둔 바로 그 경로를 되살렸다.
> - **사실오류**: "FSA 기존 max-retry 상수 재사용"은 거짓 — `fsa_loop.py`에 재사용할 max-retry 상수가 **0건**이다(grep 확인). 실재하는 bound는 `dynamic_orchestrator.py:528` `self._task_retry_count.get(retry_key, 0) < 3` 으로, **task 단위·VERIFY 도달 *전*** 재시도다. 즉 FSA/orchestrator의 "자기수정 소유권"은 **task-level orchestrator retry(implement 전)**이지 **post-verify 골 실패 피드백이 아니다**. 둘은 다른 단계의 다른 메커니즘이다.

**결정 (inv3 정합 우선)**: 골 FAILED는 **`BLOCKED`(reason="goal_failed") terminal로 종료**한다. dogfood 레벨 retry는 도입하지 않는다(inv3 보존). 자동 수정 루프(find→fix)는 가치가 있지만 **dogfood 안의 phase 되돌림으로 구현할 수 없다** — dogfood 밖 **상위 재호출 메커니즘**(파이프라인을 새 run으로 재기동) + **신규 bound**가 필요하며, 그 메커니즘은 본 설계 범위 밖의 후속 작업으로 분리한다. "재사용"은 삭제한다.

**Phase 3 본체 (이 설계가 구현) — 검출 + 정직한 종료**:
```
AcceptanceGate → goal FAILED
   │
   ├─ contract.has_failures() == True
   │
   ├─ block_run() → DogfoodPhase.BLOCKED(reason="goal_failed")   ← 현재 코드 동작 그대로 (inv3 정합)
   │     (CANNOT_VERIFY는 실패 아님 — is_done()이 done 허용, BLOCKED 아님)
   │
   └─ evidence_ledger에 [FAILED] 섹션 + 골별 증거(command/exit_code/누락 키워드) 기록
         → 사용자/상위 오케스트레이터가 개입 판단.
```
이것은 detector가 아니라 **증거 첨부된 정직한 종료**다 — 패턴 A/B의 "거짓 ok=True"를 차단하는 것이 Phase 3의 핵심 가치이며, 그 자체로 end-to-end의 검증 절반을 닫는다.

**수정 루프 (별도 메커니즘, 본 설계 범위 밖 — 후속)**:
골 FAILED를 자동으로 고치려면 다음이 **새로** 필요하다(기존 것 재사용 불가):
1. **상위 재기동 메커니즘**: BLOCKED(goal_failed) run을 받아 같은 work-item을 **새 dogfood run으로 재기동**하는 외부 오케스트레이션(dogfood phase 되돌림 아님 → inv3 비위반). 진입점·상태 인계·증거 전달 계약 미정.
2. **신규 bound**: 그 재기동 횟수를 제한하는 **신규 상수**(예: `MAX_GOAL_FIX_REINVOCATIONS`). FSA `_task_retry_count<3`(task-level, VERIFY 전)과는 **다른 단계의 다른 카운터**이므로 재사용하지 않는다. exhausted 시 `goal_failed_exhausted`로 종료 + evidence 보존.
3. **CANNOT_VERIFY 제외**: 환경 한계 골은 재기동해도 못 고치므로 루프 대상 아님(§9 INV-G).

이 3요소는 신규 메커니즘·신규 계약·신규 bound를 요구하므로 별도 설계로 분리한다. **본 문서 §8 S3는 BLOCKED(goal_failed) terminal까지만 구현**한다.

**불변식 (§9 INV-G)**: `verdict="CANNOT_VERIFY"`는 실패가 아니므로 BLOCKED를 유발하지 않는다(is_done()이 done 허용). `verdict="FAILED"`만 BLOCKED(goal_failed)로 종료한다. (자동 수정 루프가 후속으로 도입되면 그 메커니즘의 신규 bound가 FAILED 재기동을 제한하고, CANNOT_VERIFY는 그때도 루프 제외다.)

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

`FAILED`가 있으면 `[FAILED]` 섹션 추가 후 BLOCKED(reason="goal_failed") 처리(§6.4 — dogfood 레벨 재시도 없음, inv3 정합).

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

- **생성 SSOT (필수, Finding #2)**: `core/project_pipeline.py` `prepare():1246` — task_board `acceptance_criteria`(`:342`·`:520`) 파싱 → `GoalContract` 생성 → `PreparedProject.goal_contract`(`:74` 신규 필드)에 적재. 동기 `execute()` 직접 호출 경로(`drive_meeting_stt.py:68`)도 `prepared`를 거치므로 이 SSOT로 커버된다.
- **1차 배선 (필수, ok SSOT)**: `core/project_pipeline.py` `execute()` — gated `ok`를 **`append_dashboard_run`(`:1390`) 호출 이전에 한 번 계산**해 `:1396`(대시보드)·`:1421`(반환) **두 지점이 동일 `gated_ok` 사용**(Finding #4). `gated_ok = (status=="completed") and contract.is_done()`, `contract is None`이면 `status=="completed"` 폴백(INV-D). `evidence_ledger` 추가. contract는 `prepared.goal_contract`에서 읽음(신규 시그니처 0개).
- **조기 반환 게이트 (필수, Finding #5)**: `execute():1301-1307` `next_step_cursor=="done"` → `already_done` 조기 반환 경로도 `prepared.goal_contract` 있으면 `contract.is_done()` **재집계 후 `gated_ok` 반환**(하니스 재실행 없음). contract 없으면 `reason="already_done_legacy"` + ledger에 증거부재 명시(INV-A 한정 예외, §9).
- **2차 배선 (dogfood 보강)**: `core/dogfood.py` `_run_verify_phase()` — AcceptanceGate 호출. `execute()`는 이미 채워진 verdict를 **재실행 없이 집계**(idempotent 가드: 골이 이미 VERIFIED/FAILED/CANNOT_VERIFY면 `ExecutionHarness.run` skip).
- **하위 호환 폴백 경계 (Low 방어보강 — production 미도달, 전환기 한정)**: `goal_contract=None`이면 기존 `verify.passed` 폴백. 이론상 `verify_result.get("passed", True)`의 기본값 `True`(`core/dogfood.py:1899`)와 결합하면 "contract 없음 + verify 빈 dict → 무음 pass"가 INV-B를 위반할 수 있다. **단 production 도달 경로는 아니다**: `_run_review_phase`는 항상 `context={"verify_result": ...}`로 호출되고(`core/dogfood.py:2038`) `_run_verify_phase`가 `passed`를 항상 채운다 — 빈 `context={}`는 단위 테스트 전용. 그럼에도 전환기 방어로 폴백 진입을 다음으로 **제한**한다(cheap):
  - `goal_contract=None`은 **점진 도입 전환기에만** 허용되는 상태로 정의. S3 배선 완료 후에는 planner가 criteria를 못 뽑아도 **전부 `UNVERIFIED`인 비어있지 않은 contract**를 만든다(§4.2 파서 폴백) → `goal_contract`는 사실상 None이 되지 않는다.
  - 전환기 폴백 시에도 `verify_result`가 **빈 dict이면 pass 금지** — 폴백 경로는 `passed = verify_result.get("passed", True)`가 아니라 `verify_result`에 `passed` 키가 **실제로 존재**할 때만 그 값을 쓰고, 부재 시 `ok=False, reason="goal_unverified"`로 떨어뜨린다(INV-B). 기존 테스트 `test_run_review_missing_verify_result_assumes_passed`는 이 정책 변경에 맞춰 갱신 필요(고정된 pass 가정 해제).
- **골 실패 → BLOCKED terminal (§6.4 — 본 설계 범위, inv3 정합)**:
  - `core/dogfood.py`: `contract.has_failures()` → `block_run()` → `DogfoodPhase.BLOCKED`(reason="goal_failed"). **현재 코드의 BLOCKED-terminal 동작 그대로 — dogfood 레벨 IMPLEMENT 되돌림(retry) 추가하지 않음**(`:2044`/`:1895` inv3). `CANNOT_VERIFY`는 실패 아님 → BLOCKED 유발 안 함(INV-G).
  - evidence_ledger [FAILED] 섹션에 골별 증거 보존.
  - **`failure_classifier.py` 변경 없음 (Finding #3 — no-op 제거)**: 초안은 `goal_failed`→IMPLEMENTATION 클래스를 추가하려 했으나, `classify_failure:48`이 `_INFRA_PATTERNS` 미매칭 시 **이미 IMPLEMENTATION을 기본 반환**하므로 추가는 no-op이고, 완료 경로에서 그 분류를 읽어 재시도 라우팅하는 **소비처도 없다**(`control_plane_llm.py:135`·`fsa_loop.py:247`은 INFRA 중단 전용). 따라서 classifier는 건드리지 않는다.
  - **자동 수정 루프(find→fix)는 본 설계 범위 밖**(§6.4) — dogfood 밖 상위 재기동 메커니즘 + 신규 bound(`MAX_GOAL_FIX_REINVOCATIONS` 류)를 요구하는 후속 별도 설계. "FSA max-retry 상수 재사용"은 사실오류였으므로 삭제.
- 테스트: `tests/test_acceptance_gate_integration.py` — ① VERIFIED 골 → ok=True ② FAILED 골 → ok=False + BLOCKED(goal_failed) ③ **`execute()` 직접 호출 경로(dogfood 미경유)에서도 contract 차단 적용** ④ contract=None + verify 빈 dict → ok=False(무음 pass 금지, INV-B) ⑤ **CANNOT_VERIFY → BLOCKED 아님, is_done() done 허용 (INV-G)** ⑥ **`execute()` ok가 `:1396` 대시보드·`:1421` 반환에서 동일 `gated_ok` (Finding #4)** ⑦ **`already_done` 조기 반환에서 contract 재집계 / contract 없으면 `already_done_legacy` (Finding #5)**
- **3-Tier 필수**: `dogfood.py`/`project_pipeline.py` = Tier 3 → 풀 3-Tier (`failure_classifier.py`/`fsa_loop.py`는 변경 없음 → 대상 아님)

---

## §9 불변식 + 테스트 요구사항

| 불변식 ID | 내용 | 테스트 |
|----------|------|-------|
| INV-A | `GoalContract.is_done()==False`이면 pipeline `ok=True` 금지 — **gated `ok`를 `append_dashboard_run`(`:1390`) 이전 1회 계산, `:1396`·`:1421` 동일값**, dogfood 미경유 직접 호출 경로 포함. **한정 예외**: 게이트 도입 *이전* done-표시 resume run(`:1307` 조기 반환)은 contract 부재 시 evidence 없이 `already_done_legacy` 명시 반환(ledger에 증거부재 표기) | `test_ok_blocked_when_goal_unverified`, `test_execute_direct_path_gated`, `test_dashboard_and_return_ok_match`, `test_already_done_reaggregates_or_legacy` |
| INV-B | `commands_run=[]`이고 `passed=True`면 verdict=`UNVERIFIED` (추측 통과 금지) | `test_no_evidence_means_unverified` |
| INV-C | `harness_type="gui"` → verdict=`CANNOT_VERIFY` (FAILED 아님) | `test_gui_harness_cannot_verify` |
| INV-D | `goal_contract=None` 폴백은 전환기 한정 + **`verify_result`에 `passed` 키가 실제 존재할 때만** 그 값 사용. 빈 dict → `ok=False`(무음 pass 금지, INV-B와 정합) | `test_null_contract_empty_verify_blocks` |
| INV-E | evidence_ledger는 항상 `goals/cannot_verify/unverified` 3-section 포함 | `test_ledger_three_sections_always_present` |
| INV-F | `harness_type="none"`(미해결) 골 → verdict=`UNVERIFIED` (file-exists 자동 통과 금지, §5.1 정정) → `is_done()==False` | `test_none_harness_stays_unverified` |
| INV-G | `verdict="CANNOT_VERIFY"`는 실패 아님 → BLOCKED 유발 안 함(`is_done()` done 허용). `verdict="FAILED"`만 `BLOCKED(reason="goal_failed")` terminal로 종료 — **dogfood 레벨 IMPLEMENT 되돌림 retry 없음**(`dogfood.py:2044`/`:1895` inv3 정합). 자동 수정 루프는 본 설계 범위 밖(§6.4, 후속 별도 메커니즘+신규 bound) | `test_cannot_verify_not_blocked`, `test_failed_blocks_terminal_no_retry` |

---

## §10 미결 / 의도적 제외 항목

| 항목 | 결정 | 이유 |
|------|------|------|
| GUI offscreen 하니스 | 미구현 (S4 보류) | Qt offscreen plugin 설치 의존성, 복잡도 ↑ |
| Oracle(정답 검증) | 미구현 | 의미적 골은 자동화 불가 — `CANNOT_VERIFY` 처리로 충분 |
| GoalContract LLM 추출 정확도 | 별도 조율 필요 | planner criteria 품질은 이 설계 범위 밖 |
| CI 장치 프로비저닝 | 별도 인프라 작업 | 환경 구멍은 `CANNOT_VERIFY` 명시로 대응, CI 셋업은 별도 |
| `completion_criteria` 파싱 로직 | S1 구현 시 결정 | LLM criteria 포맷이 확정되면 파서 설계 |
| goal_failed 자동 수정 루프 (find→fix) | **별도 메커니즘으로 분리 — 후속 설계** (2026-06-18 재정정) | 본 설계는 BLOCKED(goal_failed) terminal까지 구현(§6.4). dogfood phase 되돌림 retry는 inv3 위반(`dogfood.py:2044`/`:1895`) → 자동 수정은 dogfood 밖 **상위 재기동 메커니즘 + 신규 bound**(`MAX_GOAL_FIX_REINVOCATIONS` 류, FSA `_task_retry_count<3` 재사용 불가)를 요구하므로 분리 |

---

## §11 연결 지점

### §11.0 하나의 축 — "검증은 완료 이벤트에 매달린 스테이지, 결함은 IMPLEMENT로 되먹임" (2026-06-18)

이 설계는 독립 기능이 아니라 **세 설계가 공유하는 한 원칙**의 출구 절반이다:

| 설계 | 역할 | 같은 원칙의 어느 면 |
|------|------|-------------------|
| router decoupling (2026-06-07) **Phase 2** | post-implement **Tier3 코드리뷰 floor** (observe-first) | 리뷰 = implement 완료 시 도는 **스테이지** (자율 경로 `_inject_review_tasks`) |
| **이 문서 Phase 3** | AcceptanceGate **골 증거 검증** + 실패 시 BLOCKED(goal_failed) terminal | 골테스트 = implement 완료 시 도는 **스테이지** |
| §6.4 수정 루프 (후속·별도) | 골 FAILED → **상위 재기동**(dogfood 밖, 신규 bound) | 결함 되먹임 — 단 dogfood phase 되돌림은 inv3 위반이라 **별도 메커니즘으로 분리**(본 설계 범위 밖) |

**핵심 함의 — UserPromptSubmit 자동발화는 이 모델과 충돌**:
- 3-Tier 리뷰 자동발화를 `UserPromptSubmit`(사람 키 입력 = 폴링)에 매달면, "implement 완료" 이벤트와 디커플됨. 올바른 트리거는 **완료 이벤트**(자율=파이프라인 스테이지, 인터랙티브=커밋/어시스턴트 완료 판단)다.
- 실제로 `UserPromptSubmit` 훅 제거 시 **단절④의 `AF_SKIP_REVIEW_GATE=1` 우회가 상시 강제**된다 — 즉 자동발화 폴링을 떼면 이 설계가 닫으려는 바로 그 구멍이 더 벌어진다. **결론**: 넛지 복원이 아니라 검증을 완료-이벤트 스테이지로 모델링(§6.4 루프 포함)하는 것이 정답.

### §11.1 `docs/2026-06-07-router-scope-research-decoupling-design.md` §1.3 "출구 단절 4곳"
- 단절 ①②③④ 모두 이 설계의 GoalContract + AcceptanceGate가 해소 대상
- **단절④ = `_run_review_phase`(def `:1891`, `verify_result.get("passed", True)` `:1899`) + finalize `AF_SKIP_REVIEW_GATE=1` 우회** = §11.0의 UserPromptSubmit 제거가 벌린 그 구멍. §6.4 BLOCKED(goal_failed) terminal + ok=True SSOT 배선(§6.3)이 정공법 해소(거짓 ok=True 차단). 자동 수정 되먹임은 후속 별도 메커니즘.
- Phase 3 (Completion Contract) = 이 문서가 그 설계

### §11.2 `core/dogfood.py` BLOCKED terminal — `fsa_loop.py`/`failure_classifier.py`는 **변경 없음** (§6.4 정정)
- 본 설계가 구현하는 골 실패 처리는 `dogfood.block_run()` → `DogfoodPhase.BLOCKED(reason="goal_failed")` terminal까지다. **`fsa_loop.py`·`failure_classifier.py`는 이 설계로 수정하지 않는다**:
  - `failure_classifier`: `goal_failed`→IMPLEMENTATION 추가는 no-op(`classify_failure:48` 이미 기본 IMPLEMENTATION) + 소비처 없음(`fsa_loop.py:247`은 INFRA 중단 전용) → 변경 제거(Finding #3).
  - `fsa_loop`: 재사용할 max-retry 상수 **0건**(grep) — "기존 상수 재사용"은 사실오류였음. 실재 bound는 `dynamic_orchestrator.py:528` `_task_retry_count<3`(task-level, VERIFY *전*)으로 골 실패 피드백과 무관.
- 자동 수정 루프(`ok=False, reason="goal_failed"` 수신 → 재기동)는 dogfood 밖 **상위 재기동 메커니즘 + 신규 bound**를 요구하는 후속 별도 설계(§6.4·§10). 본 문서 범위 밖.

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
| 2026-06-18 | **자동 설계리뷰 watcher BLOCK 6건 반영 (Opus)** — surface 단절로 `d1022ecd`에 잘못 push된 §6.4를 inv3 정합·사실기반으로 재작성. 출처: `docs/reviews/2026-06-18-015950-...-design-review.md`(전건 grep 재확인). ① **#1 Critical** §6.4 — "골 FAILED→dogfood가 IMPLEMENT 되돌림+FSA max-retry 상수 재사용"이 inv3 위반(`dogfood.py:2044`/`:1895`) + 사실오류(`fsa_loop.py` max-retry 상수 0건; 실재 bound는 `dynamic_orchestrator.py:528` `_task_retry_count<3` task-level·VERIFY 전). → **골 FAILED=BLOCKED(goal_failed) terminal**(inv3 정합), 자동 수정 루프는 dogfood 밖 상위 재기동+신규 bound 요구하는 **후속 별도 메커니즘으로 분리**. "재사용" 삭제. ② **#2 High** GoalContract 생성 SSOT를 `prepare():1246`→`PreparedProject:74`로 이동(동기 `execute()` 경로 커버). ③ **#3 Medium** `failure_classifier goal_failed` 추가는 no-op(`classify_failure:48` 기본 IMPLEMENTATION)+소비처 없음 → **변경 제거**. ④ **#4 Medium** `execute()` ok 2곳(`:1396` 대시보드/`:1421` 반환) → gated `ok`를 `append_dashboard_run`(`:1390`) 이전 1회 계산해 동일값. ⑤ **#5 Medium** resume 조기반환(`:1307` already_done)이 게이트 우회 → contract 재집계 또는 `already_done_legacy` 명시(INV-A 한정 예외). ⑥ **#6 Low** stale 라인 `:1845`→`:1891`/`:1899`. §9 INV-A/INV-G·§10·§11.0/§11.1/§11.2 연동 갱신. (메타: watcher cross-review가 `CreateProcessWithLogonW:1909`로 미생산 → 단일 vendor(Critic) 증거, 단 전건 파일:라인 grep 인용으로 ACCEPT) |
| 2026-06-18 | af-cross-review 발견 검증 후 4건 수용·1건 severity 하향 (Opus). **전건 동조 아님 — 각 건 grep 직접 반증 후 판정**: ① **High (수용)** §6.3/§8 S3 — AcceptanceGate를 ok=True SSOT(`project_pipeline.execute:1421`)에 1차 배선(동기 dogfood `drive_meeting_stt.py:68`이 execute 직접 호출 → dogfood verify 미경유 갭 해소). idempotent 이중배선 가드. (1차 코드대조 리뷰가 놓친 진짜 아키텍처 갭) ② **Low로 하향 (cross-review는 High로 보고)** §8 S3/INV-D — `goal_contract=None`+`verify` 빈 dict → 무음 pass 시나리오는 **production 미도달**: `_run_review_phase`는 항상 `context={"verify_result": ...}`로 호출되고(`core/dogfood.py:2038`) `_run_verify_phase`가 `passed`를 항상 채운다. 빈 `context={}` 호출자는 `tests/test_dogfood.py`뿐(production caller 0). cross-review가 테스트 픽스처(`test_..._assumes_passed`)를 결함 실체로 격상한 케이스(메모리 `feedback_test_mock_vs_defect`). **수정은 유지**(폴백을 `passed` 키 실존 시로 제한 = cheap 전환기 방어)하되 severity는 Low 방어보강. ③ **Adv 수용** §8 S2 `_run_file_exists` 잔존 제거(자체 편집 미완성) ④ **Adv 수용** §8 S1 직렬화 명세 추가 ⑤ **Adv 수용** §3 INV-A `GoalContract.verdict`→`is_done()` 오표기 정정. **수용 거부 1건** (BONUS: `work_item_generator.py:1318` source_path stale = 기존 코드 annotation 오류, 본 설계 무관 — 미수정). 따라서 실제 BLOCK 기여는 High#1 1건. |
