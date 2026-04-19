---
qa_exempt_forbidden_tokens: true
reason: "금지 토큰(`(edit required)` 등)을 리터럴로 인용해야 하는 메타 설계 문서"
---

# 야간 무인 완주 파이프라인 — Phase -1 ~ 4 설계 (v3)

- 작성일: 2026-04-18
- 상태: Draft v3 (v2 Critic ACCEPT WITH CHANGES + Doc-QA PASS 조건부 반영)
- 관련 이슈: 로또 프로젝트(`lotto_predictor_v2`, `lotto_mobile_web`) 실패 분석
- 관련 블루프린트 섹션: §3.2 DynamicOrchestrator, §4 자가진화 루프, §7 안전장치

## 0. 배경

### 0.1 사용자 최우선 요구 (제약 조건)

> **"자기 전에 작업을 지시하고 아침에 일어났을 때 완료가 되어있거나 진행 중이어야 한다. 중간에 멈추면 안 된다."**

이는 파이프라인의 불변식이다. 어떤 품질 개선도 이 제약을 만족시키지 못하면 의미가 없다.

### 0.2 v1 BLOCK 판정 요약

v1(초안)은 교차검증에서 **REJECT**됐다. 치명 결함 5건:

1. **프로세스 생존 메커니즘 부재** — Claude CLI 세션 10~30분 타임아웃, macOS sleep 시 SIGSTOP. 단일 `asyncio.run` 프로세스로 12시간 연속 실행이 구조적으로 불가.
2. **CHECKPOINT_ONLY cycle 카운터 충돌** — `while cycle < max_cycles` 루프에서 `continue`만으로는 cycle 증가를 막지 못해 결국 종료.
3. **`run_budget.py` USD↔토큰 미연결** — 실코드는 토큰 기반, v1은 USD 기반. 환산 테이블 없음.
4. **재설계 후 Level 카운터 리셋** — 새 task_id 생성 시 `_max_task_retries` 초기화 → 무한 재설계 루프 위험.
5. **Blueprint §3.2 드리프트** — `_stall_threshold` Blueprint(`5`) vs 실코드(`15`), `max_cycles` 하드코딩(`30`) vs 실코드 동적(`max(30, pending*4)`).

### 0.3 v2의 핵심 전환 — **"연속 프로세스"에서 "idempotent tick"으로**

**v1 암묵 전제**: 하나의 긴 프로세스가 모든 상태를 메모리에 갖고 12시간 살아있어야 한다.

**v2 새 모델**: launchd가 15분마다 짧은 tick 프로세스를 기동. 각 tick은:
1. 파일(state_board, checkpoint, budget)에서 상태 복원
2. 할 일 N개 수행 (태스크 디스패치 / LLM 개입 / watchdog 에스컬레이션)
3. 상태를 파일에 기록
4. 종료

이 전환이 **Q1/Q2/Claude CLI 타임아웃/macOS sleep을 구조적으로 동시 해결**한다.

---

## 1. 목표와 비목표

### 1.1 목표

| 코드 | 내용 | 측정 방법 |
|------|-----|---------|
| G1 | 12시간 방치 시 "아침에 완료 또는 진행중" 상태 보장 | 실제 야간 rehearsal (가속이 아닌 real wall clock) |
| G2 | 모든 실패는 retry/pivot/redesign/degrade/checkpoint 중 하나로 수렴 | 합성 실패 주입 테스트 (tick 단위 시뮬) |
| G3 | 외부 의존 3-티어 fallback(live→cache→seed) 준수 | 네트워크 차단 + 캐시 비움 시 seed 응답 |
| G4 | `status=completed` 는 파일 존재 + 금지 토큰 0 + e2e exit 0 충족 시에만 | approval-gate 자동 차단 로그 |
| G5 | `.af/nightly_summary.md` 매 tick 갱신, 파일만 읽고 상태 재구성 가능 | mtime ≤ tick 주기 + 2분 여유 |
| G6 | 동일 실수(심볼 발명, frontend_dev 오배정 등) 3번째 프로젝트에서 재발 금지 | golden project 회귀 |

### 1.2 비목표

- 품질 완벽성 (아침에 버그 0): 보장 안 함. "멈추지 않음"만.
- 인간 감독 완전 제거: 프로덕션 배포·외부 publish는 여전히 HITL.
- UI 자동화(Playwright 등): 별도 Phase 5+.
- 기존 deployed 빌드(af zip) 바이너리 호환성 유지: 필요 시 파괴적 변경 허용.
- Linux/Windows 대응: macOS 전용 (launchd 기반). 향후 OS 추상 레이어 분리 가능성만 열어둠.

### 1.3 범위 경계

- **IN**: `core/dynamic_orchestrator.py`, `core/work_item_generator.py`, `core/project_task_board.py`, `core/approval_gate.py`, `core/fsa_loop.py`, `core/ise_*.py`, `core/memory_system/`, `core/run_budget.py`, `scripts/nightly_*`, `install-af.ps1`(+ launchd 등가), 템플릿, policy.yaml, hooks, Master_Blueprint §3.2/§4/§7/§12.
- **OUT**: provider/LLM 엔진 핵심, 빌드 시스템(`af.spec`), 스킬 시스템 핵심, Linux/Windows 이식.

---

## 2. 핵심 불변식 (Invariants) — v2 재정의

tick 아키텍처에 맞춰 불변식을 재정의. 주체가 "연속 프로세스"가 아니라 "tick의 집합(schedule)"이다.

- **I1. Schedule Continuity**: launchd/등가 스케줄러에 **다음 tick이 반드시 큐잉되어 있다**. 어떤 단일 tick이 종료되어도 다음 tick이 자동 기동된다. 스케줄러 자체가 비활성화되면 I1 파괴 — 이는 사용자 명시 `nightly-stop` 외엔 발생 안 한다.
- **I2. Failure → Next-Action**: tick 내부 실패·tick 자체 크래시 어느 경우든 다음 tick이 상태 파일을 읽고 이어간다. 영구 실패 태스크는 degrade 태스크 생성 또는 lineage 상한 도달 시 skip.
- **I3. External Dependency 3-tier**: 외부 의존은 (live → cache → seed) 계층 강제. 3차까지 실패 시 degrade task (품질 하향하고 계속).
- **I4. Completion = Verified Artifact**: `status=completed` 는 파일 존재 + 금지 토큰 0 + e2e exit 0 + verification verdict ≠ BLOCK 충족 시에만 플래그됨.
- **I5. Reconstructable State**: `.af/nightly_summary.md`, `.af/board_state.json`, `.af/lineage_ledger.json` 세 파일만으로 지금 어디까지 왔고 무엇이 걸려 있는지 재구성 가능.

---

## 3. tick 아키텍처 — v2의 심장

### 3.1 구조

```
┌────────────── macOS launchd (또는 env daemon) ──────────────┐
│  com.af.nightly.tick plist                                   │
│  StartInterval: 900s (15분)                                  │
│  KeepAlive: SuccessfulExit=false                            │
└───────────────────────┬─────────────────────────────────────┘
                        │ exec
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ af nightly tick   (CLI 진입점, scripts/nightly_tick.py)      │
│                                                              │
│  1. acquire flock(.af/nightly.lock)  # 동시 실행 방지        │
│  2. state = load_state()   # board_state + lineage + budget  │
│  3. action = decide(state) # 이번 tick 할 일 1~N개          │
│  4. execute(action)        # 태스크 디스패치 or watchdog     │
│  5. save_state(state)      # atomic write                    │
│  6. update_summary()       # .af/nightly_summary.md          │
│  7. release lock + exit                                      │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 tick 당 지속시간 상한

- Soft: 10분 (tick 주기 15분 중 여유 5분)
- Hard: 14분 (다음 tick과 겹침 방지)
- Hard 초과 시 현재 작업 중단 신호(SIGTERM) → 상태 저장 → 종료. 다음 tick이 이어감.

### 3.3 WatchdogState (cycle 카운터 대체)

v1의 cycle은 tick 사이에 리셋되므로 의미가 없다. 대신 **lineage·stall 을 파일에 영구 기록**:

```json
// .af/watchdog_state.json
{
  "last_progress_tick_id": "2026-04-18T02:30Z",
  "consecutive_no_progress_ticks": 3,
  "watchdog_level": "STALL_1",
  "lineage_counters": {
    "lineage:abc123": { "level": 2, "attempts": 4 }
  },
  "checkpoint_only_since": null
}
```

`consecutive_no_progress_ticks` ≥ 4 → STALL_2, ≥ 8 → STALL_3, ≥ 16 → CHECKPOINT_ONLY. Tick은 어차피 종료되므로 "cycle 동결" 문제 자체가 없다 (Q2 해결).

### 3.4 Idempotency 보장

모든 tick 액션은 "이미 처리됨" 감지 후 skip:

- 태스크 수행 전 `task.status in {in_progress, completed}` 체크
- 파일 쓰기는 `tempfile.mkstemp + os.replace` atomic
- 외부 API 호출은 멱등 키(`request_id`) 부착
- 동일 lineage 재진입 시 `lineage_counters.attempts` 증분만

### 3.5 실패 격리

- tick 내부 파이썬 예외는 tick **종료만** 시킨다. launchd가 다음 tick 기동.
- 실패 스택트레이스는 `.system_generated/logs/tick_<id>.err` 로 보존.
- 연속 5 tick 실패 시 watchdog 이 `.af/alert.flag` 파일 생성 (Q1 선결: 사용자 알림 채널).

### 3.6 다중 파일 상태 원자성 (v3 보강 — Critic Acceptance #3)

tick 종료 시점의 상태는 5개 파일(`board_state`, `watchdog_state`, `budget_state`, `lineage_ledger`, `nightly_summary`)에 걸쳐 있다. 단일 `tempfile + os.replace` 만으로는 파일 간 일관성 보장 안 됨 (SIGTERM이 중간 파일에서 발생 시 부분 기록).

**채택 방안: 단일 `state_snapshot.json` + 파생 렌더링**

```
.af/state_snapshot.json         # 모든 상태의 single source of truth (atomic write)
.af/board_state.json            # snapshot에서 파생 (view, 읽기 전용)
.af/watchdog_state.json         # snapshot에서 파생
.af/budget_state.json           # snapshot에서 파생
.af/lineage_ledger.json         # snapshot에서 파생
.af/nightly_summary.md          # snapshot에서 렌더링
```

**쓰기 프로토콜**:
1. 메모리에서 state 구성
2. `state_snapshot.json` 에 atomic write (`tempfile.mkstemp + os.replace`)
3. (선택) 파생 파일 4종은 fsck 이후 rebuild — tick 시작 시 `state_snapshot.json` 이 유일한 복원 소스. 파생 파일은 사람/외부 도구 관찰용.

이로써 SIGTERM으로 쓰기가 중단되어도 `state_snapshot.json` 은 이전 유효 상태를 유지 (os.replace 는 atomic).

### 3.7 Dispatcher 상태 persist (v3 보강 — Critic Acceptance #1)

기존 `DynamicOrchestrator`의 인스턴스 필드 중 tick 간 유지되어야 하는 것:

| 필드 | 파일 | 비고 |
|------|------|------|
| `state_board` | `state_snapshot.board` | 기존 board 파일 활용 |
| `active_assignments` | `state_snapshot.active_assignments` | `{role: {subtask_id, started_at, tick_id, result_path}}` |
| `_task_retry_count` | `state_snapshot.task_retry_count` | `{retry_key: count}` |
| `_last_completion_cycle` | 제거 | cycle 개념 폐기 → `last_progress_tick_id` 로 대체 |
| `_stall_threshold` | 제거 | `consecutive_no_progress_ticks` 파일 기반 |
| `max_cycles` | 제거 | wall clock / budget tokens 로 대체 |

**재기동 시 복원 로직** (`scripts/nightly_tick.py` 진입부):

```python
snapshot = load_snapshot(".af/state_snapshot.json")
orch = DynamicOrchestrator(mr=..., restore_from=snapshot)
# active_assignments 중 tick_id가 이전 tick 이고 result_path 미존재 → 재디스패치 대상
# task_retry_count 는 그대로 복원
```

`DynamicOrchestrator` 에 `restore_from(snapshot)` 클래스 메서드 신규. 기존 `__init__` 은 `restore_from=None` 기본값으로 뒷호환.

**"어댑션 경계"**: tick 내부 short-lived 상태(`result_future`, async task 핸들 등)는 persist 안 함. 해당 tick에서 완료하거나 timeout 시 `active_assignments` 엔트리만 남기고 다음 tick이 결과 회수.

### 3.8 launchd plist 설정 (v3 보강 — Critic Acceptance #2)

기본 `StartInterval=900` 만으로는 macOS 장시간 sleep 시 최대 `sleep 지속 + 15분` 공백 발생. 이를 최소화하기 위해 **이중 스케줄**:

```xml
<!-- ~/Library/LaunchAgents/com.af.nightly.tick.plist -->
<plist version="1.0">
<dict>
  <key>Label</key><string>com.af.nightly.tick</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>/Users/hoon/workTree/agent-factory/scripts/nightly_tick.py</string>
  </array>
  <key>StartInterval</key><integer>900</integer>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Minute</key><integer>0</integer></dict>
    <dict><key>Minute</key><integer>15</integer></dict>
    <dict><key>Minute</key><integer>30</integer></dict>
    <dict><key>Minute</key><integer>45</integer></dict>
  </array>
  <key>KeepAlive</key>
  <dict><key>SuccessfulExit</key><false/></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/Users/hoon/workTree/agent-factory/.system_generated/logs/nightly_tick.out</string>
  <key>StandardErrorPath</key><string>/Users/hoon/workTree/agent-factory/.system_generated/logs/nightly_tick.err</string>
</dict>
</plist>
```

- `StartInterval=900`: 마지막 실행 완료 후 900초 경과 시 기동.
- `StartCalendarInterval` 4개 엔트리: 매시 00/15/30/45분 **절대 시각**에 기동. sleep 후 wake 시 가장 가까운 절대 시각에 즉시 기동됨 (macOS 기본 동작).
- flock이 중복 기동 방지하므로 두 스케줄이 동시에 trigger 돼도 안전.

**sleep 대응 한계**:
- macOS 전원 끄기, Safe Sleep(하이버네이트) 중에는 기동 불가. wake 직후 `StartCalendarInterval`이 가장 가까운 slot에서 기동.
- 4시간 sleep이어도 wake 즉시 다음 15분 경계에 tick 시작 → 공백 최대 15분.
- 전력 설정(`caffeinate`) 은 사용자 선택이며 본 설계는 강제하지 않음. 대신 `nightly-start` 실행 시 "야간 Mac 전원 연결 + sleep 설정 확인" 안내 출력.

---

## 4. Phase 설계

### Phase -1 — Blueprint 드리프트 동기화 (0.5일, 선행)

**목적**: 정확한 baseline 확보. 후속 Phase가 드리프트한 문서를 신뢰하고 설계하면 구현 중 재협상 발생.

**스코프 (IN)**:
- `Master_Blueprint.md` §3.2 동기화 (3개 지점 모두):
  - L200 (블록다이어그램 `max_cycles=50` 표기): `max(30, pending*4)` 로
  - L294: `_max_task_retries = 3` 확인 (일치)
  - L296: `_stall_threshold = 15` (env `AGENT_STALL_THRESHOLD`로 가변)
  - L297: `max_cycles` 하드코딩 제거 → `compute_max_cycles()` 동적 수식 명시
  - L1067: `max_cycles 소진 50 사이클` → 동일 동적 수식 반영
  - L337: `max_cycles=30` 분기 서술 → 동적 수식 반영
- §4 Flow B ISE 루프 실 배선 현황 정확 기술:
  - `fsa_loop.py`가 `ise_analyzer/redesigner/stall_detector` 이미 흡수
  - `dynamic_orchestrator`는 `fsa_loop`를 호출하지 않음 (배선 누락)
  - `ISELoop` 클래스는 dead — Phase 3에서 결정(삭제 or 복귀)
- §7 `ApprovalGate` 상태 필드 확인·기술 (`execution_open` 기준, `approved`는 별칭 여부 확정)
- §12 변경이력에 "2026-04-18 v2 설계 반영을 위한 드리프트 동기화" 1건 추가

**스코프 (OUT)**: 코드 수정 0. 문서만.

**변경 파일**: `Master_Blueprint.md`

**성공 기준**:
- `_stall_threshold`, `max_cycles`, `_max_task_retries` 값이 문서 ↔ 실코드 1:1 일치 (grep 증명).
- §4 Flow B 서술과 실 import 그래프 일치.

**의존성**: 없음.

**기간**: 0.5일.

---

### Phase 0 — launchd tick 아키텍처 + 파일 기반 상태 (2일)

**목적**: I1/I5 달성. 야간 무인의 **인프라 베이스** 구축.

**스코프 (IN)**:
- **launchd plist**: `install-af.ps1`(macOS 보조 스크립트)에 plist 설치·로드 단계.
  - `~/Library/LaunchAgents/com.af.nightly.tick.plist`
  - `StartInterval=900`, `KeepAlive.SuccessfulExit=false`, `StandardOutPath/StandardErrorPath` 지정.
- **tick CLI 엔트리**: `scripts/nightly_tick.py` (신규). `af nightly tick` 서브커맨드.
- **flock 기반 동시 실행 방지**: `.af/nightly.lock` `fcntl.LOCK_EX | LOCK_NB`.
- **파일 기반 상태 스토어**:
  - `.af/board_state.json` (기존 활용)
  - `.af/watchdog_state.json` (신규): lineage, stall, checkpoint_only
  - `.af/budget_state.json` (신규): 토큰 누적, tick 카운트
  - `.af/nightly_summary.md` (신규): 사람이 읽는 요약
  - `.af/alert.flag` (신규): 연속 실패 시 알림 마커
- **tick dispatcher**: state 읽고 action 결정, `dynamic_orchestrator._dispatch_from_board` 재사용 (연속 루프가 아닌 "이번 tick에 할 일 N개" 추출 모드).
- **Graceful interrupt**: tick hard limit(14분) 도달 시 SIGTERM → state flush → exit.
- **`nightly-start` / `nightly-stop` CLI**: 스케줄 on/off 제어.

**스코프 (OUT)**:
- ISE 배선 (Phase 3).
- 문서 품질 개선 (Phase 1).
- e2e 계약 강제 (Phase 2).
- 에피소드 학습 (Phase 4).

**변경 파일**:

| 파일 | 변경 |
|------|------|
| `scripts/nightly_tick.py` (신규) | tick CLI + dispatcher |
| `scripts/nightly_summary.py` (신규) | summary 렌더러 |
| `scripts/install_launchd.sh` (신규) | plist 설치·로드 |
| `~/Library/LaunchAgents/com.af.nightly.tick.plist` (설치 산출물) | — |
| `core/dynamic_orchestrator.py` | "tick 모드" 추출 (`_dispatch_from_board` 호출을 단일 사이클로 분리) |
| `core/run_budget.py` | 파일 persist + tick 간 상태 유지 |
| `core/watchdog.py` (신규) | WatchdogState 관리 (cycle 없는 모델) |
| `policy.yaml` | `nightly_autonomy.{enabled, tick_interval_sec, soft_deadline_sec, hard_deadline_sec, max_tokens_per_night, alert_after_consec_fail}` |
| `af` CLI | `nightly-start/stop/status/tick` 서브커맨드 |

**TickDispatcher 의사코드**:

```python
def tick_once():
    with flock(".af/nightly.lock", LOCK_EX | LOCK_NB) as got:
        if not got:
            return  # 이전 tick 진행 중, 이번은 skip
        state = load_state()
        if state.nightly_autonomy_enabled is False:
            return  # 사용자가 stop
        if state.budget.tokens_remaining <= 0:
            enter_checkpoint_only(state)
            save_and_exit(state)
            return

        actions = dispatcher.next_actions(state, max_actions=5)
        if not actions:
            watchdog_tick_no_progress(state)  # STALL_1/2/3 에스컬레이션
        else:
            for a in actions:
                if deadline_exceeded(): break
                execute_action(a, state)

        render_summary(state)
        save_state(state)  # atomic
```

**공개 API**:

```bash
af nightly-start          # plist 로드, enabled=true
af nightly-stop           # plist 언로드, enabled=false
af nightly-status         # tick 이력, watchdog 레벨, budget 요약
af nightly tick           # 수동 1회 tick (launchd 호출과 동일)
```

**CLI 진입점 구체화**: `run_factory_cli.py::main()`의 argparse `subparsers` 블록에 다음 4개 `add_parser` 추가:

```python
# run_factory_cli.py 내 subparser 블록에 추가
sp_nightly_start = subparsers.add_parser("nightly-start", help="야간 무인 모드 활성화")
sp_nightly_stop  = subparsers.add_parser("nightly-stop",  help="야간 무인 모드 비활성화")
sp_nightly_status = subparsers.add_parser("nightly-status", help="야간 상태 조회")
sp_nightly_tick  = subparsers.add_parser("nightly-tick",  help="수동 1회 tick")
# 각각 dispatch → scripts/nightly_{start,stop,status,tick}.py 또는 core/nightly/*.py 모듈 호출
```

**기존 파일 마이그레이션**: 최초 `nightly-start` 실행 시 `.af/` 하위 기존 상태 파일(`board_state.json` 등)이 snapshot 스키마와 호환되지 않으면:
1. 기존 파일을 `.af/legacy_<ts>/` 로 이동 (백업)
2. 새 `state_snapshot.json` 을 빈 상태로 초기화
3. `nightly-status` 에 "migrated from legacy" 1회 경고

**성공 기준**:
- GA: `af nightly-start` 후 15분 간격으로 launchd 로그에 tick 기동 확인 (2~3 tick rehearsal).
- GB: 의도적으로 tick 1회 `exit(1)` → 다음 tick 정상 기동 + 상태 복구 확인.
- GC: `.af/nightly_summary.md` mtime 최신 tick 후 2분 이내.
- GD: 동일 시점에 두 tick 동시 기동 시도 → 후행이 flock skip 로그 남기고 즉시 종료.
- GE: `pmset sleepnow` (macOS sleep 주입) 후 wake → 다음 tick 주기에 자동 기동.

**위험 & 완화**:
- R1 *launchd plist 설치 실패 (macOS 버전 편차)*: `launchctl bootstrap` / `launchctl load -w` 이중 경로 + 실패 시 친절한 에러.
- R2 *flock 누수 (tick 프로세스 kill 시)*: `fcntl.flock(LOCK_EX|LOCK_NB)` 단독 사용. 커널이 프로세스 종료 시 자동 해제 — PID 파일 기반 부가 검증 불필요. PID 파일은 `nightly-status` 표시용으로만 사용 (역할 분리).
- R3 *budget 파일 corruption*: atomic write + backup 1회.
- R4 *사용자 혼동 (언제 실행 중인지 모름)*: `nightly-status` 가 선명하게 "다음 tick 예정 시각" 표시.
- R5 *Linux/Windows 이식성*: Phase 0에서는 macOS만. OS 추상은 Phase 5+.

**의존성**: Phase -1.

**롤백**: `af nightly-stop` + plist 제거.

**기간**: 2일.

---

### Phase 1 — 외부 의존 3-티어 + 문서 품질 최소 (2일)

**목적**: I3/G3 달성 + `(edit required)` 토큰 제거로 야간 결과물 품질 하한선 확보.

**스코프 (IN)**:
- `core/work_item_generator.py`: 생성 직후 금지 토큰 스캔, 발견 시 LLM 보강 루프 (최대 2회).
- 문서별 입력 계약 분리: plan ← outcomes/metrics, spec ← user_stories/io_contracts, design ← components/flows.
- 외부 API 3-티어 계약 표준 `docs/patterns/2026-04-18-external-api-3tier.md` 신규.
- `projects/lotto_predictor_v2/seed_draws.json` (100회차 실데이터) 커밋.
- `projects/lotto_mobile_web/server/services/recommendation.py`: seed 경로 추가.
- `DhLotteryClient` 3-티어 fallback 리팩토링.

**스코프 (OUT)**:
- 역할 오배정 완전 개선 (→ Phase 4, memory).
- DAG 자동 추론 (→ Phase 4).

**변경 파일**:

| 파일 | 변경 |
|------|------|
| `core/work_item_generator.py` | placeholder 스캔·보강 + 입력 키 계약 |
| `core/document_policy.py` | 금지 토큰 리스트 + 스캐너 제외 메커니즘: 문서 frontmatter `qa_exempt_forbidden_tokens: true` 플래그 시 스캔 skip. 본 설계 문서 등 "금지 토큰을 리터럴로 인용해야 하는 메타 문서"는 이 플래그 명시. |
| `projects/lotto_predictor_v2/seed_draws.json` (신규) | 100회차 실데이터 |
| `projects/lotto_predictor_v2/src/lotto_predictor/backend/http_client.py` | 3-티어 fallback |
| `projects/lotto_mobile_web/server/services/recommendation.py` | seed 경로 |
| `docs/patterns/2026-04-18-external-api-3tier.md` (신규) | 표준 |
| `scripts/refresh_lotto_seed.py` (신규) | 월 1회 갱신 |

**성공 기준**:
- GF: 새 AF 프로젝트 생성 시 모든 `.md`에 `(edit required)` 0건.
- GG: 동행복권 API 전면 차단 + 캐시 비움 시 seed로 200 응답 (`source=seed` 로깅).
- GH: plan / spec / design 의 Goals 섹션 Jaccard 유사도 ≤ 0.4. **토큰화 규칙 고정**: `text.lower()` → 비알파벳/숫자 문자 공백 치환 (`re.sub(r"[^a-z0-9가-힣]+", " ", s)`) → 공백 분리 → 빈 토큰 제거 → stopword 없음. 구현 참조: `scripts/measure_goal_overlap.py` (Phase 1 산출물).

**위험 & 완화**:
- R6 *seed 라이선스*: 출처 명시 (`동행복권 공공 발표 결과`). README에 고지.
- R7 *보강 루프 무한*: 2회 cap, 그 뒤는 `status=needs_human_review` 태그.
- R8 *seed 노후화*: 월 1회 refresh 스크립트 + `age_days` 메타 기록.

**의존성**: Phase -1, Phase 0 (보강 루프 실패 시 다음 tick이 이어받아야).

**롤백**: env `AF_PLACEHOLDER_REFINE=0`.

**기간**: 2일.

---

### Phase 2 — approval-gate ← verification + e2e 계약 (3일)

**목적**: I4/G4 달성 — 가짜 PASS 제거.

**스코프 (IN)**:
- `core/approval_gate.py`: 동일 work-item `verification-report.md` verdict 강제 입력.
  - verdict == BLOCK → `execution_open=false`.
- task 스키마에 `e2e_command: string` 필수 필드.
- verify handoff 템플릿에 e2e 실행 결과(exit code + stdout 요약) 섹션 필수.
- `scripts/verify_handoff_checker.py` (신규): pre-commit + tick 완료 검증용.
- 기존 work-item migration 스크립트.

**스코프 (OUT)**:
- 브라우저 UI 자동화 (별도).
- ISE 연동 (Phase 3).

**변경 파일**:

| 파일 | 변경 |
|------|------|
| `core/approval_gate.py` | verification verdict 입력 |
| `core/work_item_generator.py` | task 스키마 `e2e_command` |
| `templates/verify-handoff.md.tpl` | e2e 결과 섹션 |
| `scripts/verify_handoff_checker.py` (신규) | pre-commit/CI gate |
| `.githooks/pre-commit` | checker 호출 |
| `core/document_policy.py` | completion_criteria 추가 |

**Completion Criteria (v2 개정)**:

```yaml
task_complete_criteria:
  artifact_files_exist: true
  forbidden_tokens_absent:
    - "(edit required)"
    - "(auto-generate needed)"
    - "TODO: "
  e2e_command_exit_code: 0
  verification_report_verdict: { not: "BLOCK" }
  # critic_minimum_score 는 근거 확보 전까지 제외 — Phase 4에서 분포 측정 후 도입
```

**성공 기준**:
- GI: verify BLOCK 주입 시 `execution_open=false` 자동.
- GJ: `e2e_command` 없는 task 생성 거부.
- GK: 기존 work-items 마이그레이션 후 모두 e2e 필드 보유 (수동 보강 태그 허용).

**위험 & 완화**:
- R9 *기존 프로젝트 호환*: migration 스크립트 `scripts/migrate_workitem_e2e.py` — 빈 값은 `exit 1` + `needs_backfill` 태그.
- R10 *e2e 느린 경우*: tick hard limit 14분 내 완료 못 하면 tick 종료 + 다음 tick에 retry, `e2e_timeout_sec=180` 기본값.

**의존성**: Phase -1, Phase 0, Phase 1.

**롤백**: env `AF_VERIFY_E2E_STRICT=0` (경고만).

**기간**: 3일.

---

### Phase 3 — ISE 배선 + lineage 기반 Level 누적 (1주)

**목적**: I2 심화 — 정적 재시도에서 동적 재설계로.

**스코프 (IN)**:
- `dynamic_orchestrator._execute_agent_task` 실패 경로가 `FSALoop.run_mission` 위임.
- `lineage_id` 신규 필드: task 생성 시 부모 task의 lineage 상속.
- `.af/lineage_ledger.json`: lineage별 Level 누적 `{lineage: {level, attempts, history}}`.
- Level 매핑:
  - Level 1 retry (기존)
  - Level 2 pivot (스코프 축소)
  - Level 3 redesign (태스크 재작성 — 새 task_id, 기존 lineage 상속)
  - Level 4 skill evolve (최소 — 도구 힌트 추가)
  - Level 5 decompose (태스크 쪼갬)
- Lineage 상한: Level 5 누적 `attempts>=20` 도달 시 Phase 0 watchdog의 degrade 경로로 위임 (R11).
- `core/ise_loop.py` 는 Phase -1 정밀 기술 결과에 따라 **삭제 또는 FSALoop 얇은 래퍼로 축소**.
- **`core/ise_strategy_ledger.py` 통폐합 결정**: Phase 4 `core/memory_system/strategy_ledger.py` 와 네이밍 충돌. Phase 3 종료 시 둘 중 하나:
  - (a) `ise_strategy_ledger.py` 를 `memory_system/strategy_ledger.py` 로 흡수 (권장 — ISE 결과가 결국 memory에 저장되므로 자연스러움)
  - (b) ISE 런타임 전략과 memory 학습 원장을 명확 분리 (각자 유지)
  - 결정은 Phase 3 종료 PR에서, 기본값 (a).

**스코프 (OUT)**:
- Level 4 완전 스킬 진화 (별도 skill 시스템 리팩토링 필요).
- Level 재설계 결과 memory 저장 (→ Phase 4).

**변경 파일**:

| 파일 | 변경 |
|------|------|
| `core/dynamic_orchestrator.py` | `_execute_agent_task` 실패 → FSALoop 위임 |
| `core/fsa_loop.py` | `run_mission(task_context=..., lineage_id=...)` |
| `core/ise_analyzer.py` | 실패 → Level 매핑 |
| `core/ise_redesigner.py` | Level 3 구현 |
| `core/lineage_ledger.py` (신규) | ledger read/write atomic |
| `core/project_task_board.py` | task.lineage_id 필드 추가 |
| `core/watchdog.py` | lineage 누적 상한 감지 |
| `Master_Blueprint.md` §4 | 실 배선 반영 |

**Lineage 카운터 설계 (Critic Q4 해결)**:

```python
@dataclass
class LineageEntry:
    lineage_id: str
    level: int           # 1~5
    attempts: int        # 모든 level 포함 누적
    history: list[dict]  # [{"ts": ..., "level": ..., "outcome": ...}, ...]

def on_task_failure(task, failure):
    lid = task.lineage_id
    entry = ledger.load(lid)
    entry.attempts += 1
    new_level = analyze(failure, entry.level)
    entry.level = new_level
    if entry.attempts >= 20 or entry.level > 5:
        watchdog.degrade(task)  # lineage 상한
    else:
        fsa_loop.run_mission(task, lineage_id=lid, level=new_level)
    ledger.save(lid, entry)
```

**성공 기준**:
- GL: 인위적 logic 실패 주입 시 Level 1→2→3 로그 확인.
- GM: Level 5 도달 시 원 task가 2개 이상 하위 task로 분해되고 `lineage_id` 상속.
- GN: `attempts=20` 도달 시 degrade 경로 자동 진입.

**위험 & 완화**:
- R11 *무한 재설계*: lineage_id + `attempts>=20` 하드캡. history에 모든 level 기록되어 검증 가능.
- R12 *ISE 도입 성능 저하*: 실패 시에만 활성화, 성공 경로는 오버헤드 0.
- R13 *블루프린트 §4 드리프트 재발*: Phase 3 종료 시 §4 업데이트를 PR 체크리스트에 포함.

**의존성**: Phase -1, 0, 1, 2.

**롤백**: env `AF_ISE_ENABLED=0` → 기존 retry 경로만.

**기간**: 1주.

---

### Phase 4 — 에피소드 Memory + 재사용 (1주)

**목적**: G6 달성 — 동일 실수 반복 방지.

**스코프 (IN)**:
- `memory_system/episode_matcher.py` 기능 확장: 새 brief → 유사 과거 에피소드 top-k.
- `memory_system/strategy_ledger.py` (신규): 성공 DAG/역할 배정·실패 패턴 영구 기록.
- `core/work_item_generator.py`: 에피소드 힌트 주입 섹션.
- `core/project_task_board.py:_pick_owner_role`: ledger 우선, 키워드 폴백 후순위.
- 시드 에피소드 3종 기록 (심볼 발명 / CLI→frontend_dev 폴백 / stub-only tests pass).
- **야간 자동 저장 조건 강화 (Critic 지적 반영)**:
  - 조건 A (본 운영): Phase 2 verify e2e PASS 비율 14일 rolling window에서 80% 이상.
  - **조건 B (초기 14일 bootstrap)**: 운영 14일 미만이면 "N건 중 M건 PASS, N≥20 and M/N≥0.8" 으로 대체 (표본 수 기반).
  - 둘 다 미충족이면 "후보" 태그로 보류, 사용자 ACK 시에만 승격.

**`memory/episodes/` 디렉토리 위치 결정 (v3 보강)**:

| 후보 | 장점 | 단점 |
|------|------|------|
| (A) 루트 `memory/episodes/` | 프로젝트 산출물/런타임 상태와 명확 분리 | 레포 루트에 새 디렉토리 추가 |
| (B) `core/memory_system/episodes/` | 기존 패키지 일관성 | 코드와 데이터 혼재 |
| (C) `.af/episodes/` | 런타임 상태와 일관 (`.af/state_snapshot.json` 등) | 사용자가 커밋/공유 대상 여부 혼동 |

**선택: (A) 루트 `memory/`** — 이유:
- 에피소드는 **학습 자산**이므로 커밋·버전관리 대상 (사용자·팀 공유 가능). (C)는 런타임 상태로 보여 `.gitignore` 되기 쉬움.
- `core/` 는 코드 전용. 데이터 파일 배치는 기존 관례 없음.
- 향후 팀 공유 시 `memory/` 루트가 자연스러운 제품화 단위.

**스코프 (OUT)**:
- LLM 파인튜닝.
- 팀 공유 메모리.

**변경 파일**:

| 파일 | 변경 |
|------|------|
| `core/memory_system/episode_matcher.py` | 유사도 top-k 확장 |
| `core/memory_system/strategy_ledger.py` (신규) | DAG/역할 원장 |
| `core/work_item_generator.py` | 에피소드 섹션 주입 |
| `core/project_task_board.py` | `_pick_owner_role` ledger 조회 |
| `memory/episodes/2026-04-18-wrong-symbol-invention.md` (신규) | 시드 |
| `memory/episodes/2026-04-18-cli-frontend-dev-fallback.md` (신규) | 시드 |
| `memory/episodes/2026-04-18-stub-only-tests-pass.md` (신규) | 시드 |
| `memory/episodes/` 디렉토리 (신규) | — |

**성공 기준**:
- GO: 3번째 로또 프로젝트 (golden brief) 에서 CLI deliverable이 `backend_dev` 또는 `general_dev`.
- GP: 심볼 발명 시도 시 작업 전 경고 주입 로그.
- GQ: `episode_matcher.query()` 응답 500ms 이내.
- GR: Phase 2 PASS 비율이 14일 rolling window에서 80% 미만인 경우 자동 저장 0건 (보류만). 초기 14일은 bootstrap 조건(N≥20, M/N≥0.8) 적용.

**위험 & 완화**:
- R14 *잘못된 기억 학습*: PASS 비율 게이트 + 저장 후 14일 probation (재조회 금지).
- R15 *메모리 폭발*: 1000건 상한 + LRU + relevance pruning.
- R16 *프라이버시*: brief redaction (이메일/URL 자동 마스킹).

**의존성**: Phase -1 ~ 3.

**롤백**: env `AF_MEMORY_REPLAY=0`.

**기간**: 1주.

---

## 5. Phase 의존성 DAG

```
Phase -1 ──> Phase 0 ──> Phase 1 ──> Phase 2 ──> Phase 3 ──> Phase 4
```

- Phase -1: Blueprint 동기화 선행. 코드 수정 없음.
- Phase 0: 인프라 (launchd tick, 상태 persist). 모든 후속의 베이스.
- Phase 1 → Phase 2: Phase 2가 `work_item_generator` 의 task 스키마에 `e2e_command` 필드를 추가하는데, Phase 1에서 동일 파일의 placeholder 보강 로직이 먼저 안정화되어야 merge 충돌 최소.
- Phase 3: Phase 2 e2e 계약 위에서 실패 감지.
- Phase 4: Phase 3의 lineage·redesign 결과를 memory 재료로 사용.

## 6. 회귀 검증 전략

### 6.1 합성 tick 시뮬레이션 (Phase 0)

**목적**: 실제 launchd 배선·야간 rehearsal 이전에 파이프라인이 48회 tick 동안 크래시 없이 돌고 상태가 올바르게 전이되는지 합성 환경에서 검증. 야간에 조용히 터지는 사고를 방지하기 위한 최후의 안전망.

#### 6.1.1 파일 구조

```
tests/e2e/
├── __init__.py
├── conftest.py              # 공통 픽스처 (임시 workspace, env 격리)
└── tick_simulator.py        # 핵심 시뮬레이터 + pytest 테스트
```

#### 6.1.2 가속 메커니즘

실제 launchd는 15분 간격으로 별도 프로세스를 spawn하지만, 테스트에서는 `launchd 배제 + 순차 호출`로 가속:

- **루프 구조**: `for i in range(48): tick_once(workspace=tmp_workspace)` — `scripts/nightly_tick.py:tick_once()` 직접 호출.
- **"시간" 주입**: 실제 대기 없음. `make_tick_id()`가 `datetime.now()`에 의존하므로 `monkeypatch.setattr("core.nightly_state.make_tick_id", lambda: f"tick_{i:02d}")`로 주입.
- **deadline 단축**: `SOFT_DEADLINE_SEC`/`HARD_DEADLINE_SEC`를 `monkeypatch.setattr("scripts.nightly_tick.HARD_DEADLINE_SEC", 2)` 로 2초로 축소.
- **기대 실시간**: tick당 ~6초 × 48 = **5분 이내** 1회 시뮬레이션 완주 (설계 상한).

#### 6.1.3 모킹 대상

| 대상 | 모킹 이유 | 방식 |
|------|-----------|------|
| `agent.run` / `agent_chat_cli.run()` | LLM API 실호출 방지 + 결정론적 실패 주입 | `monkeypatch.setattr` → `AgentExecutionResult(ok=False, reason="simulated_fail", output="")` |
| `DynamicOrchestrator._execute_agent_task` | 배선 전체 bypass 옵션 | `AF_SIMULATION_MODE=1` env 변수 체크 |
| `core.lottery_client.ThreeTierLotteryClient` | 외부 API 실호출 방지 | 3-티어 fixture: live=fail, cache=fail, seed=OK |
| `~/Library/LaunchAgents/*` 설치 | 테스트가 OS에 영향 주지 않도록 | `install_launchd.sh`는 **절대 호출하지 않음** (루프에서 `tick_once`를 직접 호출) |
| `ANTHROPIC_API_KEY` | 실 API 호출 원천 차단 | `monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)` |

#### 6.1.4 픽스처 (conftest.py)

```python
@pytest.fixture
def sim_workspace(tmp_path, monkeypatch):
    """임시 workspace + env 격리."""
    ws = tmp_path / "af_sim"
    (ws / ".af").mkdir(parents=True)
    (ws / ".system_generated" / "logs").mkdir(parents=True)

    # env 격리
    monkeypatch.setenv("AF_SIMULATION_MODE", "1")
    monkeypatch.setenv("AF_ISE_ENABLED", "1")
    monkeypatch.setenv("AF_MEMORY_REPLAY", "0")   # 시드 에피소드 간섭 방지
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    # 초기 brief 주입 (최소 task 1건)
    (ws / ".af" / "nightly_brief.md").write_text(
        "# brief\n- task: simulated_task_1\n", encoding="utf-8"
    )
    return ws

@pytest.fixture
def fail_agent(monkeypatch):
    """모든 agent.run 호출을 artificial fail로 고정."""
    from core.dynamic_orchestrator import DynamicOrchestrator

    async def _fake_execute(self, role, subtask, *args, **kwargs):
        return {"ok": False, "reason": "simulated_fail", "output": "", "artifacts": []}

    monkeypatch.setattr(
        DynamicOrchestrator, "_execute_agent_task", _fake_execute
    )
```

#### 6.1.5 판정 기준 (5가지)

| # | 조건 | 측정 방식 |
|---|------|-----------|
| GE-1 | tick이 정확히 48회 기동 | 루프 카운트 == 48 |
| GE-2 | 어느 tick도 예외를 상위로 전파하지 않음 | `tick_once()` 반환 exit code ∈ {0, 1} (내부 catch) |
| GE-3 | 각 tick 후 `.af/nightly_summary.md` mtime 갱신 | `summary_path(ws).stat().st_mtime` 단조증가 |
| GE-4 | 종료 시점 `state.status != "stopped_broken"` | `load_state(ws).status` 확인 |
| GE-5 | 연속 실패 5회 초과 시 `.af/alert.flag` 생성 | `alert_flag_path(ws).exists()` == True |

#### 6.1.6 테스트 골격 (Sonnet 구현 참고)

```python
# tests/e2e/tick_simulator.py
import pytest
from pathlib import Path
from scripts.nightly_tick import tick_once
from core.nightly_state import load_state, summary_path, alert_flag_path

TICK_COUNT = 48  # 12h / 15min


@pytest.mark.e2e
def test_48_ticks_no_crash(sim_workspace, fail_agent, monkeypatch):
    """GE-1 ~ GE-5 통합 검증."""
    monkeypatch.setattr("scripts.nightly_tick.HARD_DEADLINE_SEC", 2)
    prev_mtime = 0.0

    for i in range(TICK_COUNT):
        monkeypatch.setattr(
            "core.nightly_state.make_tick_id",
            lambda i=i: f"sim_tick_{i:02d}",
        )
        exit_code = tick_once(workspace=sim_workspace)
        assert exit_code in (0, 1), f"tick {i} unexpected exit {exit_code}"  # GE-2

        mtime = summary_path(sim_workspace).stat().st_mtime
        assert mtime >= prev_mtime, f"tick {i} summary mtime regressed"  # GE-3
        prev_mtime = mtime

    state = load_state(sim_workspace)
    assert state.status != "stopped_broken"  # GE-4
    assert alert_flag_path(sim_workspace).exists()  # GE-5 (48회 연속 실패 → 5회 초과)
```

#### 6.1.7 실행 방법

```bash
# 로컬 단일 실행
pytest tests/e2e/tick_simulator.py -m e2e -v

# CI (느리므로 별도 stage)
pytest tests/e2e/ -m e2e --timeout=600
```

- `pytest.ini` 에 `markers = e2e: 느린 e2e (기본 skip)` 추가.
- 기본 `pytest` 실행 시 skip, `-m e2e` 명시 또는 `AF_RUN_E2E=1` env로만 활성화.

#### 6.1.8 범위 외 (이 시뮬레이터가 검증하지 않는 것)

- 실제 launchd `StartInterval` 타이밍 정확성 → §6.3 `pmset sleepnow` 테스트에서 커버.
- 실제 LLM 호출 품질·비용 → §6.2 실 야간 rehearsal에서 커버.
- macOS sleep/wake 복구 → §6.3에서 커버.
- Golden Project 완주 → §6.4에서 커버.

### 6.2 실 야간 Rehearsal (Phase 0 완료 후 매주)

매 금요일 밤 23:00 start → 토요일 11:00 stop. 빈 brief 또는 lotto golden brief.
- 성공 기준: 48회 tick 실행 + 종료 시 `status != stopped_broken`.

### 6.3 macOS sleep 주입 (Phase 0)

`pmset sleepnow` 후 15분 대기 → wake → 다음 tick 기동 확인 (GE).

### 6.4 Golden Project 회귀 (Phase 4 종료 시)

3번째 로또 프로젝트 생성 → 12시간 무인 완주 → `.md` `(edit required)` 0건, e2e PASS, CLI deliverable 역할 배정 올바름.

---

## 7. 롤백·Feature Flag

```yaml
nightly_autonomy:
  enabled: true
  tick_interval_sec: 900
  soft_deadline_sec: 600
  hard_deadline_sec: 840
  max_tokens_per_night: 2_000_000   # Q3 토큰 기반
  usd_cost_hint: true                # 로그에 참고값 표시 (환산 테이블 없음, 추정)
  alert_after_consec_fail: 5
  placeholder_refine: true           # Phase 1
  verify_e2e_strict: true            # Phase 2
  ise_enabled: true                  # Phase 3
  memory_replay: true                # Phase 4
  memory_auto_save_min_pass_rate: 0.8  # Phase 4
```

개별 flag off 시 이전 동작 복귀. CI는 최소 두 조합(전부 on / Phase 0만 on) 검증.

## 8. 일정 요약

| Phase | 기간 | 누적 | 야간 지시 가능 시점 |
|-------|------|------|-----------------|
| -1 | 0.5일 | 0.5일 | ❌ (인프라 없음) |
| 0 | 2일 | 2.5일 | ✅ 최소 (품질 없음) |
| 1 | 2일 | 4.5일 | ✅ 품질 하한선 |
| 2 | 3일 | 7.5일 | ✅ 완료 검증 포함 |
| 3 | 7일 | 14.5일 | ✅ 실패 자동 재설계 |
| 4 | 7일 | 21.5일 | ✅ 학습 재사용 |

## 9. Blueprint 갱신 계획

- §0: `core/watchdog.py`, `core/lineage_ledger.py`, `core/memory_system/strategy_ledger.py`, `scripts/nightly_*`, `scripts/install_launchd.sh` 추가.
- §3.2: tick 모드 추출, `break`/`continue` 의미 변경 기술.
- §3.8.3 RunBudget: 파일 persist + tick 간 상태 유지.
- §4: FSA ↔ ISE 실 배선 (Phase 3).
- §7: approval-gate ← verification (Phase 2).
- §9: `nightly_autonomy.*` 설정 키.
- §10 Blast Radius: 신규 `scripts/nightly_*` 의존 엣지.
- §12: Phase별 완료 엔트리.

## 10. 오픈 질문 (남은 것만)

### 10.1 agent-factory 레벨 (프레임워크 정책)

- Q6: 알림 채널 `.af/alert.flag` 외 추가(예: macOS notification, Slack)?
- Q8: Level 4 skill evolve 최소 구현 범위 (Phase 3에 포함 최소? 전면 Phase 5로?).
- Q9: `max_tokens_per_night` 기본값 200만 토큰이 적절한가?

### 10.2 프로젝트별 결정 사항 (agent-factory 범위 외)

- ~~Q7: seed 데이터 갱신 주기 — 월 1회 vs 분기 1회.~~
  - **재분류 사유 (2026-04-19)**: seed 갱신 주기는 프로젝트 도메인(로또=주 1회, 주식=분 단위, 정적 참조 자료=연 1회 등)에 따라 완전히 달라지므로 agent-factory 레벨에서 결정할 수 없다.
  - agent-factory 책임 범위: 각 프로젝트가 자기 주기를 설정할 수 있는 메커니즘 제공(예: 프로젝트 config의 `seed_refresh_interval_days` 필드 + Phase 1 3-티어 패턴 표준). 실제 값은 각 프로젝트가 정한다.

## 11. v1 → v2 → v3 변경 요약

### 11.1 v1 → v2 (Critic REJECT → ACCEPT WITH CHANGES)

| 항목 | v1 | v2 |
|------|----|----|
| 프로세스 모델 | 단일 연속 asyncio | 15분 tick 독립 프로세스 |
| 불변식 I1 | "메인 루프 break 금지" | "스케줄 다음 tick 항상 큐잉" |
| 불변식 I5 | "nightly_summary 기록" | "3 파일만으로 상태 재구성 가능" |
| Q1 프로세스 생존 | 미해결 | launchd + KeepAlive |
| Q2 cycle 카운터 | CHECKPOINT_ONLY + continue (미완) | tick 간 cycle 리셋 → 자연 해결 |
| Q3 비용 단위 | `max_cost_usd` | `max_tokens_per_night` + USD hint 로그 |
| Q4 Level 누적 | 미명시 | `lineage_id` + `.af/lineage_ledger.json` |
| Q5 Blueprint 동기화 | Phase 0 포함 | Phase -1 선행 분리 |
| Claude CLI 타임아웃 | 미해결 | tick이 매번 새 세션 → 구조적 해결 |
| macOS sleep | 미해결 | launchd wake trigger 자동 |
| R9 무한 재설계 | 언급만 | `attempts>=20` 하드캡 + ledger 추적 |
| Phase 4 자동 저장 | 회귀 PASS만 | PASS rate ≥ 80% 게이트 추가 |
| GF 중복률 메트릭 | 레벤슈타인 (모호) | Jaccard on token set (명확) |
| Phase 0 일정 | 1일 (비현실) | 2일 (현실) |

### 11.2 v2 → v3 (Critic Acceptance 전제 3건 + Doc-QA 우선순위 1-3 반영)

| 항목 | v2 | v3 |
|------|----|----|
| 다중 파일 원자성 | 미명시 | §3.6: 단일 `state_snapshot.json` single-source-of-truth + 파생 파일 |
| `active_assignments`/`_task_retry_count` persist | 미명시 | §3.7: snapshot 내 필드 + `restore_from()` 클래스 메서드 |
| launchd sleep 공백 | `StartInterval` 만 | §3.8: `StartInterval` + `StartCalendarInterval` 4개 엔트리 (15분 절대 시각 기반) |
| Blueprint 드리프트 지점 | 추상 (하드코딩 제거) | Phase -1: L200/L294/L296/L297/L337/L1067 6지점 명시 |
| CLI 엔트리 위치 | 추상 (`af` 서브커맨드) | Phase 0: `run_factory_cli.py` subparser 블록 구체 코드 |
| `memory/episodes/` 위치 | 루트 선택만 | Phase 4: A/B/C 비교표 + 선택 근거 |
| `ise_strategy_ledger.py` 통폐합 | 미언급 | Phase 3: (a) 흡수 vs (b) 분리 결정점 명시, 기본값 (a) |
| flock + PID 역할 | 중복 감지 | R2: `fcntl.flock` 전담, PID 파일은 status 표시용 |
| Jaccard 토큰화 | 규칙 미정 | GH: 소문자 + 비알파벳 치환 + 공백 분리 구체 |
| Phase 4 rolling window 초기 14일 | fallback 미정 | 조건 B (표본 N≥20, M/N≥0.8) 추가 |
| 금지 토큰 스캐너 제외 | 개념만 | frontmatter `qa_exempt_forbidden_tokens: true` 메커니즘 |
| DAG 엣지 | 1/2 병렬 | 1→2 순차 (work_item_generator 동일 파일 merge 충돌 최소화) |
| GR 측정 기간 | 불명확 | "14일 rolling window" 명시 + bootstrap 조건 |
| 기존 `.af/*` migration | 미명시 | Phase 0: 최초 nightly-start 시 `.af/legacy_<ts>/` 백업 후 초기화 |

## 12. 성공 판정 최종 체크리스트

- [ ] lotto golden project로 실제 12시간 야간 rehearsal 1회 성공 (가속 아님)
- [ ] 48회 tick 전부 기동, 종료 시점 `status != stopped_broken`
- [ ] `.af/nightly_summary.md`, `.af/board_state.json`, `.af/lineage_ledger.json` 로 상태 재구성 가능
- [ ] macOS sleep → wake 시나리오에서도 정상 재개
- [ ] Claude CLI 세션 타임아웃 시 다음 tick이 이어받음 (로그 증빙)
- [ ] 새 `.md` 산출물 전부 `(edit required)` 0건
- [ ] verification BLOCK → execution_open false 자동
- [ ] lineage attempts>=20 → degrade 자동
- [ ] CLI deliverable이 `frontend_dev`에 폴백되지 않음 (memory ledger 조회 후)
- [ ] Phase 2 PASS rate < 80% 기간에는 memory 자동 저장 0건
