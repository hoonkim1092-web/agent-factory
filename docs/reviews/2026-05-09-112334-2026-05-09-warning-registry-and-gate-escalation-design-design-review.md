# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 11:23
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

근거: ApprovalGate rename(call site 5건 중 3건 누락 + keyword 인자 테스트 1건)이 두 리뷰어 모두에서 Critical/ACCEPT로 일치 보고됨. 머지 즉시 `TypeError`/테스트 회귀 발생 보장.

---

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] ApprovalGate `workspace` → `doc_root` rename이 call site 5곳을 모두 커버하지 못함
- **Critic**: 누락 3곳 — `tests/test_t3_7_run_event_integration.py:96` (keyword `workspace=`, rename 시 `TypeError` 즉시 발생), `core/control/maintenance_pipeline.py:310`, `scripts/verify_handoff_checker.py:104`. §7.3 PR scope는 2곳만 명시.
- **Cross**: `rg "ApprovalGate\("` 결과 5곳 (maintenance_pipeline + project_pipeline + work_item_generator + verify_handoff_checker + tests). 동일 누락 확인.
- **Judgment**: 두 리뷰어가 같은 evidence(grep)로 동일 결론. acceptance #6 (test PASS) 충족 불가.
- **Action Required**: §7.3 PR scope를 "호출처 5곳 + keyword 인자 테스트 1건"으로 정정. `workspace=` deprecation alias를 추가하거나, `tests/test_t3_7_run_event_integration.py:96`을 `doc_root=`로 동시 갱신. `maintenance_pipeline.py`/`verify_handoff_checker.py` 시멘틱 정합 명시.

#### 2. [ACCEPT] [High] `record_id` idempotency가 underspecified — 정상 이벤트 silent drop 또는 retry dedup 실패
- **Critic**: `ts` 해상도 미정 → 같은 초 동시 dispatch 시 false-positive idempotency. `repeat_count` 누적이 record_id dedup 후 수행되면 §5.1 `repeat_count_min: 3` 임계 영구 미달.
- **Cross**: `ts=now_iso()`를 idempotency key에 포함하면 retry 시 새 record_id 생성 → dedup 자체 작동 안 함. caller가 `ts`/`record_id`를 어떻게 재사용하는지 미정의.
- **Judgment**: 두 리뷰어가 정반대 시나리오(false-positive vs no-dedup)를 모두 가능하다고 지적 → idempotency 정의 자체가 모순.
- **Action Required**: `record()`가 `ts`/`record_id`를 자체 생성. duplicate detection은 `ts` 제외 stable hash로 정의, 또는 retry caller가 명시 record_id 전달하도록 강제. "idempotency는 retry 한정, 누적 repeat은 SoT count로 계산" 분리 정책을 §4.0a에 명시. acceptance #14 정의역 명확화 + 동일 payload 2회 호출 → SoT 1라인 테스트 추가.

#### 3. [ACCEPT] [High] `_summary.json` 동시성/원자성이 모두 약함
- **Critic**: `core/file_lock.locked_file()`은 path별 독립 lock (`core/file_lock.py:53`). 서로 다른 `<rule>.jsonl` lock으로 진입한 두 record가 `_summary.json` read-modify-write를 인터리브 → last-writer-wins 손실.
- **Cross**: lock이 있어도 process crash 시 truncated JSON 발생. `core/work_item_telemetry.py:43-70`은 이미 `mkstemp + os.replace` 패턴 사용. code-review M10에 non-atomic write 부채 등재.
- **Judgment**: Critic은 race(직렬화 부재), Cross는 durability(atomic write 부재) — 같은 파일에 대한 보완 finding. 둘 다 evidence 강함.
- **Action Required**: `_summary.json`/`_index.json` 갱신은 (a) 별도 단일 lock(`<warnings_root>/<slug>/_summary.json.lock`)으로 직렬화 + (b) `core/work_item_telemetry.py`의 mkstemp + `os.replace` 패턴으로 atomic write. §4.4 "동일 lock으로 직렬화" 문구 정정.

#### 4. [ACCEPT] [Medium] `_decision.md` 링크가 P1에서 dead link 가능
- **Critic**: §6.3 "decision_report_link가 있으면 한 줄 추가" — 조건이 모호. `initialize()` 시점은 record 0건, `apply_verification_verdict()`는 검증 후. 양쪽 자동 주입 시 dead link.
- **Cross**: P1 stub evaluator는 active decision 없음. `WarningRegistry` API에 `render_decision_report`/placeholder 생성 메서드 미정의 → P4까지 missing file.
- **Judgment**: 양쪽 모두 "P1에서 링크는 추가하는데 대상 파일은 언제 생기나"를 지적. evidence 일치.
- **Action Required**: 옵션 A — `summarize()`가 P1에서 minimal `_decision.md`("no active decisions")를 lazy 생성. 옵션 B — `warnings count > 0` 또는 `_summary.json` 존재 시에만 라인 추가. §6.3에 의사코드 1줄 명시 + acceptance에 "링크 대상 파일 존재" 검증 추가.

#### 5. [ACCEPT] [Medium] §10 acceptance #5 / #2가 본문 계약과 불일치
- **Source**: Cross #2, #3
- **#5**: §3.1 row 2와 §10 #16은 `list[tuple[str, str, str]]` (task_id, expected_owner, actual_owner). §10 #5만 2-tuple로 남아 있음.
- **#2**: §10 #2가 `--workspace` 누락. §8.3/§10 #13은 `--workspace` 누락 시 argparse 실패 요구 → 구현자가 #2 충족 위해 fallback 만들면 #13 위반.
- **Judgment**: Cross 단독 finding이지만 design 자체 본문 텍스트 불일치 — evidence 명백.
- **Action Required**: §10 #5 → 3-tuple로 정정 + ordering assertion 명시. CLI 예시/acceptance 전부 `--workspace=<path> --slug=<slug>`로 통일.

#### 6. [ACCEPT] [Medium] §7.3 vs §10 #6 테스트 케이스 수 불일치
- **Source**: Critic #7
- **Critic**: §7.3은 6 케이스로 갱신했으나 §10 #6은 v3 텍스트 "4 케이스" 잔존. v4 변경 이력에 §10 갱신 17건만 명시되고 #6 본문 누락.
- **Cross**: not flagged.
- **Judgment**: design 내부 텍스트 불일치 — 단순 stale text.
- **Action Required**: §10 #6을 v4의 실제 PR scope (warning_registry 6 + migration_callsites 4 + approval_gate_runtime_workspace 3 + warning_registry_cli 2 = 15)로 정정.

#### 7. [ACCEPT] [Medium] `block_when` schema 분기 (string vs mapping) 미정의
- **Source**: Critic #6
- **Critic**: §5.1 `plan_verifier_warn`은 `block_when: never` (string), 다른 rule은 mapping. evaluator parser/validator 미명세 → P2 body 교체 시 union type 처리 책임자 불명.
- **Cross**: not flagged.
- **Judgment**: design은 P1에서 yaml schema를 데이터로 외화한다고 명시했는데 schema 형식 자체가 두 가지. validator 부재는 P2 진입 시 묵시적 버그 표면.
- **Action Required**: 단일 형식으로 통일 — `activate_at: never` 또는 `block_when` 생략으로 비활성 표현. P1에 pydantic/dataclass schema 1개 추가, yaml 로드 시 검증.

#### 8. [ACCEPT] [Medium] §4.5 .gitignore + Multi-PC sync 정책 모순
- **Source**: Critic #4 + #5 (병합)
- **Critic #4**: 5줄 패턴 중 line 2 `!/runtime/warnings/`, line 5 `/runtime/warnings/_global/`은 git semantics 상 no-op. 코멘트 정당화도 사실과 어긋남.
- **Critic #5**: §4.0 row 1은 SoT를 "multi-PC sync 대상 통일"이라 했는데 §4.5는 동일 경로를 gitignore. supabase/git submodule 등 sync 채널 미정의 → minesweeper baseline 측정 PC 이동 시 손실.
- **Cross**: not flagged.
- **Judgment**: 두 finding 모두 §4.5 관련 — 패턴 자체와 sync 정책이 함께 깨짐. evidence 명확.
- **Action Required**: 패턴 3줄로 축약 (`/runtime/warnings/*`, `!/runtime/warnings/.gitkeep`, `!/runtime/warnings/_index.json`). §4.0a 또는 §8.3에 sync 채널 (supabase / 별도 submodule / 명시 미동기화) 결정 명시. 미동기화 채택 시 §4.0 row 1 "multi-PC sync 대상 통일" 문구 삭제.

#### 9. [ACCEPT] [Low] §3.1 row 4 `plan_verifier_warn affected_phase="scope"` 시멘틱 약함
- **Source**: Critic #9
- **Critic**: PlanVerifier는 plan/spec/design/tasks 4문서 통합 검증인데 단일 phase "scope"로 매핑. P2의 `exempt_when affected_phase_in: [scope]`이 plan_verifier_warn에도 적용되면 의도치 않게 면제됨.
- **Cross**: not flagged.
- **Judgment**: phase taxonomy 의미 누수. 정정 비용 작음.
- **Action Required**: `affected_phase=""` 빈값 허용 정책 §3.3에 명시하거나, 신규 phase 값(`planning_set`) 도입은 별도 baseline 확장 PR로 분리 표기.

#### 10. [REJECT] [Low] `core/file_lock.locked_file` 사용은 컨벤션 충돌 아님
- **Source**: Cross #7 (자기-기각)
- **Original Finding**: 새 registry가 별도 locking 컨벤션 도입 우려.
- **Rejection Reason**: `project_task_board.py`/`project_mailbox.py`/`work_item_telemetry.py`/`session_adapter.py` 모두 동일 import. 기존 컨벤션과 일치. (단 #3에서 적용 방식 한계는 별도 finding)

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | ApprovalGate rename — call site 5곳 누락 | Critical | ACCEPT | Both |
| 2 | record_id idempotency 미정의 | High | ACCEPT | Both |
| 3 | `_summary.json` race + non-atomic write | High | ACCEPT | Both (보완) |
| 4 | `_decision.md` dead link 가능 | Medium | ACCEPT | Both |
| 5 | §10 #5 2-tuple, #2 `--workspace` 누락 | Medium | ACCEPT | Cross |
| 6 | §7.3 vs §10 #6 테스트 수 불일치 | Medium | ACCEPT | Critic |
| 7 | `block_when` string vs mapping schema 미정 | Medium | ACCEPT | Critic |
| 8 | .gitignore no-op + multi-PC sync 미정의 | Medium | ACCEPT | Critic |
| 9 | plan_verifier_warn phase="scope" 시멘틱 | Low | ACCEPT | Critic |
| 10 | file_lock 컨벤션 충돌 | Low | REJECT | Cross 자기-기각 |

---

### Recommendations

머지 전 v6에서 다음을 처리:

1. **(Critical)** §6.3/§7.3 — ApprovalGate call site 5곳 + keyword `workspace=` 테스트 모두 명시. deprecation alias 도입 여부 결정.
2. **(High)** §2.1/§4.0a — `record_id` 생성 책임자(callee), `ts` 해상도, retry vs concurrent 분리, `repeat_count`는 SoT count로 계산함을 명시. 동일 payload 2회 호출 PASS 테스트 추가.
3. **(High)** §4.4 — `_summary.json` 단일 lock + mkstemp/`os.replace` 원자 쓰기. "동일 lock으로 직렬화" 거짓 문구 정정.
4. **(Medium)** §6.3 — `_decision.md` lazy 생성 또는 조건부 링크 의사코드 1줄.
5. **(Medium)** §10 acceptance — #5 3-tuple, #2/#13 CLI `--workspace` 일관, #6 테스트 수 (15 케이스)로 정정.
6. **(Medium)** §5.1 + 신규 §5.x — `block_when` schema 단일화 + pydantic 검증.
7. **(Medium)** §4.5 + §4.0a — .gitignore 3줄 축약, sync 채널 명시.
8. **(Low)** §3.3 — phase 빈값 또는 plan-set 매핑 정책 추가.

v6 작성 후 af-cross-review 재발화 1라운드. max_rounds=2 캡 도달 — 이후엔 사용자가 수동 결정.