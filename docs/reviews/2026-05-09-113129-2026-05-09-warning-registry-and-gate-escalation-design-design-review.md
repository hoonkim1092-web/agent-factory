# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 11:31
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

1 Critical (RunEvent baseline factually wrong) + multiple High contradictions (rename rollback, `_global` regen, phase fallback semantics) make implementation unsafe. Two reviewers independently caught the RunEvent error, and Cross found a fatal lock-path bug Critic missed. Resolve all ACCEPT findings before P1 implementation.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] RunEvent 인프라 부재 주장은 거짓 (§8.3 / Acceptance #27)
- **Critic**: `core/events/run_event.py`(5,940B)가 `RunEvent`/`RunEventType`/`get_default_store` 정의, `core/approval_gate.py:29`가 이미 사용 중. grep 패턴 `core/*.py`가 서브디렉토리 비재귀라 false-negative.
- **Cross**: `RunEvent` at `core/events/run_event.py:50`, `ApprovalGate` emits at `core/approval_gate.py:24`. 결론(P1 미발행)은 유효할 수 있으나 근거가 거짓.
- **Judgment**: 두 리뷰어가 동일 증거(파일 경로+라인)로 동시 지적. 근거 없는 결정은 P4에서 wiring 시 혼동 유발.
- **Action Required**: §8.3 본문을 "RunEvent 인프라는 baseline에 존재(`core/approval_gate.py:24`); P1 record 호출처 일부에서 `run_id` 미수신으로 일관 발화 어려움 → P1은 jsonl-only, P4에서 `run_id` 가용 경로에 `WARNING_RECORDED` 추가"로 정정. Acceptance #27을 "warning-specific event 미발행" 검증으로 교체.

#### 2. [ACCEPT] [High] §8.1과 §4.4 v5 폐기 명세 충돌
- **Critic**: §8.1 line 666의 "10건마다 lazy 트리거"가 §4.4 v5 line 317의 "v3/v4 명세는 폐기, read-on-demand 단일화"와 정면 충돌.
- **Cross**: 미플래그
- **Judgment**: Critic 단독이지만 line 인용으로 명확. 구현자가 §8.1을 보면 record() 내부 카운터+flush를 넣어 v5와 정반대로 감.
- **Action Required**: §8.1을 "`record()`는 jsonl append만; `_summary.json`은 `summarize()` 호출 시 read-on-demand"로 교체.

#### 3. [ACCEPT] [High] §7.3에 폐기된 ApprovalGate rename이 잔존
- **Critic**: 미플래그
- **Cross**: §6.3은 v6에서 rename 폐기를 명시했지만, §7.3 line 685는 여전히 `workspace`→`doc_root` rename을 요구. baseline `core/approval_gate.py:78`은 `(self, workspace, slug)`이고 `tests/test_t3_7_run_event_integration.py:96`이 `workspace=` 키워드 사용.
- **Judgment**: Cross 단독이지만 코드+테스트 인용 강력. 따라가면 v6가 회피하려던 TypeError 재도입.
- **Action Required**: §7.3 / §10 #18을 "`workspace` 유지, keyword-only `runtime_workspace` 추가, split-mode 호출처만 `runtime_workspace=...` 추가, keyword 호환 테스트 유지"로 수정.

#### 4. [ACCEPT] [High] Lock 경로에 `.lock` 이중 첨부
- **Critic**: 미플래그
- **Cross**: 설계 line 331-332가 `_summary.json.lock`을 `locked_file()`에 전달. `core/file_lock.py:49,53`이 내부에서 `.lock`을 다시 append → `_summary.json.lock.lock` 생성, 문서화된 lock 키와 불일치.
- **Judgment**: Cross 단독이지만 baseline 코드 인용 명확, 첫 실행에서 디버깅 혼선 + 테스트 어긋남 보장.
- **Action Required**: `with locked_file(str(summary_path), timeout=5)`, `with locked_file(str(rule_jsonl_path), timeout=5)`로 정정. 결과 `.lock` 파일은 구현 산출물이지 입력이 아님을 명시.

#### 5. [ACCEPT] [High] `_global/` 제거 vs Acceptance #14 모순
- **Critic**: 미플래그
- **Cross**: §4.1/§7.3(line 275-277, 700)은 `_global/`을 P1 scope에서 제거하지만, §10 #14(line 834)는 repair가 `_global` 재생성 검증 요구.
- **Judgment**: Cross 단독, 두 acceptance가 정면 충돌하므로 명확.
- **Action Required**: #14를 "P1에서는 `_summary.json`만 삭제/재생성"으로 수정. P4용 `_global` repair acceptance를 별도 추가.

#### 6. [ACCEPT] [High] §3.1 row 2 — `detect_owner_drift` 새 본문 미명시
- **Critic**: baseline `core/project_task_board.py:227-248`이 첫 mismatch에서 `return True` early-exit. 시그니처를 `list[tuple]`로 바꾸려면 함수 본문도 누적 루프로 리팩토링해야 하는데 row 2는 호출처만 보여줌. 구현자가 `return [(tid, exp, act)]` 한 건만 감싸면 acceptance #16(list[tuple] 반환)은 통과하나 `count=len(mismatches)`가 항상 1.
- **Cross**: 미플래그
- **Judgment**: Critic 단독, baseline 코드 인용 강력. acceptance #16에 누적 검증 케이스 부재 시 silent regression.
- **Action Required**: §3.1 row 2에 새 함수 본문 코드블록(loop 누적 + `return mismatches`) 명시. acceptance #16에 "module이 N개 owner-drift task를 가질 때 반환 길이 == N" 케이스 추가.

#### 7. [ACCEPT] [High] §2.2a unknown→build fallback이 P2 BLOCK과 충돌
- **Critic**: LLM이 비표준 phase(`compile`/`buld` 등)를 반환하면 silent하게 `build`로 매핑 → §5.1 `e2e_command_missing`이 `count_per_run_min:1`로 즉시 BLOCK. unknown은 "LLM 출력 결함" 신호이지 BLOCK 신호가 아님.
- **Cross**: 미플래그
- **Judgment**: Critic 단독이지만 §5.1과 §2.2a의 상호작용을 정확히 분석. 안티패턴 명확.
- **Action Required**: unknown은 `scope`로 fallback(BLOCK-exempt) + 별도 `unknown_phase_observed` rule로 기록. 또는 boundary validation에서 reject.

#### 8. [ACCEPT] [Medium] fsync 명세 불일치
- **Critic**: 미플래그
- **Cross**: 설계 line 717은 "jsonl append < 5ms (fsync 포함)"이지만, 차용한 `core/work_item_telemetry.py:55` 패턴은 `mkstemp + os.replace`만 하고 `flush()`/`os.fsync()` 없음.
- **Judgment**: Cross 단독, 코드 인용 명확. 둘 중 하나로 결정 필요.
- **Action Required**: "fsync included" 제거하고 atomic replace만 명세화 OR `fh.flush(); os.fsync(fh.fileno())` + dir fsync 명시 후 latency 목표 조정.

#### 9. [ACCEPT] [Medium] `block_when: never`가 dict 스키마와 타입 충돌
- **Critic**: 다른 rule들은 dict(`{count_per_run_min: 5}`)인데 `plan_verifier_warn`만 string `"never"`. evaluator가 `block_when.get(...)` 사용 시 AttributeError.
- **Cross**: 미플래그
- **Judgment**: Critic 단독, 스키마 분석 명확.
- **Action Required**: `activate_at: never`만 두고 `block_when` 생략 또는 `{}` 빈 dict로 통일. evaluator는 `if rule.get("activate_at") == "never": return inactive` 단일 게이트.

#### 10. [ACCEPT] [Medium] `_index.json` 스키마 미명세
- **Critic**: P1 PR이 `_index.json` 초기 커밋하지만 JSON 스키마 부재 — 후속 P5/P6 추가 시 형식 충돌 위험.
- **Cross**: P1이 commit을 요구하지만 shape/ownership/validation 미정의.
- **Judgment**: 양 리뷰어 동시 지적, 명확.
- **Action Required**: 스키마 추가 — `{"schema_version": 1, "rules": {"<rule_id>": {"owner": "...", "introduced_in": "P1", "description": "..."}}}`. registry는 unknown rule_id 허용하되 summary/CLI는 `_index.json` 등록분만 라벨링.

#### 11. [HOLD] [Medium] N=1 baseline 임계값 일반화
- **Critic**: minesweeper 1개 실측 결과로 `count_per_run_min: 1` 활성 시, work_item_generator LLM 결함이 보편적이면 P2 활성 즉시 모든 신규 work-item BLOCK.
- **Cross**: 미플래그
- **Judgment**: Critic 단독. 정책 판단 사안 — "P2도 N≥3 measurement window" vs "P2는 즉시 활성"은 작성자 의도 확인 필요.
- **Question for Author**: P2 활성 전 work_item_generator의 e2e_command 출력 능력을 별도 PR로 검증할 계획인지, 또는 `count_per_run_min`을 보수적 값(예: 5)로 시작할지?

#### 12. [ACCEPT] [Medium] _decision.md multi-workspace 가시성 + [Low] repeat_count override 의미 모호
- **Critic**: (#6) `target_path` 모드에서 _decision.md는 레포 안, doc_root에는 절대경로 link만 — 사용자 PR review 시 cross-repo 이동 비용. (#8) override된 record를 repeat_count에 포함하는지 미명세.
- **Cross**: 미플래그
- **Judgment**: 둘 다 Critic 단독이지만 명세 명확화 필요. 합쳐서 ACCEPT.
- **Action Required**: §6.3에 (a) _decision.md 미러링 또는 (b) approval-gate.md `## Review Notes`에 BLOCK rule 목록+임계+해소법 inline embed 중 택일 명시. §2.2에 "`repeat_count`는 false_positive_override=true 포함 prior record 개수, override 적용은 evaluate() 단계에서 처리" 한 문장 추가.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | RunEvent 부재 주장 거짓 (§8.3) | Critical | ACCEPT | Both |
| 2 | §8.1 vs §4.4 v5 폐기 충돌 | High | ACCEPT | Critic |
| 3 | §7.3 ApprovalGate rename 잔존 | High | ACCEPT | Cross |
| 4 | Lock 경로 `.lock` 이중 첨부 | High | ACCEPT | Cross |
| 5 | `_global/` 제거 vs #14 모순 | High | ACCEPT | Cross |
| 6 | `detect_owner_drift` 본문 미명시 | High | ACCEPT | Critic |
| 7 | unknown→build fallback이 BLOCK 유발 | High | ACCEPT | Critic |
| 8 | fsync 명세 불일치 | Medium | ACCEPT | Cross |
| 9 | `block_when: never` 타입 충돌 | Medium | ACCEPT | Critic |
| 10 | `_index.json` 스키마 미명세 | Medium | ACCEPT | Both |
| 11 | N=1 baseline 임계값 일반화 위험 | Medium | HOLD | Critic |
| 12 | _decision.md 가시성 + override 의미 | Medium | ACCEPT | Critic |

### Recommendations (구현 진입 전 처리)

- **§8.3 / Acceptance #27 정정**: RunEvent 인프라 존재를 인정하고 P1 미발행 사유를 "일부 호출처 `run_id` 미수신"으로 재서술. (Critical)
- **§8.1 v5 정합화**: "10건마다 lazy" 문구 삭제, `summarize()` read-on-demand로 단일화.
- **§7.3 / §10 #18 ApprovalGate rename 롤백**: `workspace` 유지, `runtime_workspace` keyword-only 추가만 명시.
- **Lock 경로 정정**: `_summary.json` / rule jsonl 자체 경로를 `locked_file()`에 전달.
- **#14 repair acceptance 분리**: P1은 `_summary.json`만, `_global` repair는 P4 acceptance로 이전.
- **§3.1 row 2 함수 본문 코드블록 추가** + acceptance #16에 누적 길이 검증 케이스.
- **§2.2a unknown phase 처리 변경**: `scope` fallback 또는 reject + `unknown_phase_observed` rule.
- **fsync 정책 결정**: atomic-replace-only로 단순화 OR fsync 명시 + latency 목표 재산정.
- **§5.1 `block_when` 타입 통일**: `plan_verifier_warn`을 `activate_at: never` + `block_when` 생략으로 변경.
- **`_index.json` 스키마 명세 추가**.
- **§6.3 _decision.md 가시성 결정 + §2.2 override semantics 한 문장 추가**.
- **HOLD 항목(#11)**: 작성자에게 P2 활성 전 measurement window 또는 `count_per_run_min` 시작값 정책 확인 필요.