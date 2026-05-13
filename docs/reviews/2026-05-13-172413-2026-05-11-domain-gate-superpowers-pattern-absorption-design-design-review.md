# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:24
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

**중요 주석**: Cross Review는 provider error로 실패 (출력에 Codex 실행 배너만 남고 본 리뷰 본문 없음). 따라서 본 판정은 **Critic 단일 소스**이며, 각 항목은 Critic의 코드/문서 라인 인용 강도에 근거해 채택했다. Cross-review 재실행 후 본 판정을 보강하는 것을 권장한다.

근거: High급 4건 (그 중 #1~#3은 코드 라인 인용으로 검증된 구현 모순, #4는 문서 자체 자가 모순) → BLOCK.

### Aggregated Findings (11 total)

#### 1. [ACCEPT] [High] `blast_radius == "system_wide"` 단독 트리거가 실제로는 거의 발화하지 않음
- **Critic**: `change_impact.py:58-60, 200-209, 211-243` — `system_wide` 판정은 `affected_files ≥ 10` 또는 `core/` prefix 매칭에만 의존. `affected_files`는 자연어 task_input 휴리스틱 추출이라 실제 시스템급 요구도 `module`/`isolated`로 떨어진다.
- **Cross**: not flagged (provider error)
- **Judgment**: 코드 라인 인용이 정확하고, 설계 의도와 트리거 분포 간의 갭이 실증적으로 확인됨. 핵심 트리거 경로가 사실상 죽어 있다.
- **Action Required**: §3.3에 (a) `approval-gate.md ## Metadata`의 `- blast_radius: system_wide` 수동 override 또는 `--blast-radius` CLI 플래그 trigger 경로 추가, (b) §10.2 단계 전환 진입 조건으로 `data/skill-usage.jsonl` 또는 `run_ledger.jsonl` 기반 직전 30일 `system_wide` 분포 실측 N건/X건 명시.

#### 2. [ACCEPT] [High] `work_kind == "new_project"`이 도메인 게이트를 영구히 우회
- **Critic**: `intake.py:110` — `needs_impact = work_kind in ("maintenance", "bugfix", "refactor", "feature_update")`. `new_project`은 change_impact 산출 자체가 스킵 → `blast_radius = ""` → `system_wide` 매칭 불가. green-field 도메인 도입이 사각지대.
- **Cross**: not flagged
- **Judgment**: 코드 인용이 명확하고, §3.3 "잡히는 케이스" 표가 5종 중 4종만 다룬 누락이 실제 존재.
- **Action Required**: `require_domain_review()`에 `work_kind == "new_project"` OR 분기 추가, 또는 `intake.py:110` 정책에서 `new_project`도 change_impact 강제 호출 — 둘 중 하나를 Phase A 산출물에 명시 포함.

#### 3. [ACCEPT] [High] `ControlPlaneIntake.normalize()` 추가 호출이 `run_id` 이중 발급/RunLedger 이중 open을 유발
- **Critic**: `intake.py:92` `normalize()`가 자체적으로 `run-{ts}-{uuid4}` 발급 + `intake.py:126-134`에서 RunLedger open. `prepare_documents()` 시점엔 이미 `PreparedBrief.run_id`(`project_pipeline.py:49`)가 발급된 상태. 본 설계는 어느 run_id가 정본인지 결정 안 함.
- **Cross**: not flagged
- **Judgment**: 강한 증거. 그대로 구현하면 한 prepare 흐름에 RunLedger run 2건 open → 비용/메트릭 카운팅 깨짐 + downstream(`agent_launcher.py:438`) 모호.
- **Action Required**: §3.2에 (i) `normalize(run_id=prepared_brief.run_id, ...)` 키워드 강제 전달, 또는 (ii) `normalize()` 내부 RunLedger open 옵션화(`open_ledger: bool = True`)하고 prepare 경로에선 False — 본 설계가 결정자.

#### 4. [ACCEPT] [High] §10.3 vs §12 Q4 자체 모순 (dead code 처분)
- **Critic**: §6.1/§7.3/§10.3은 옵션 A(즉시 제거) 채택, §12 Q4는 잠정답 옵션 B(DEPRECATED 주석). 같은 문서 내 결정 충돌.
- **Cross**: not flagged
- **Judgment**: 문서 내 자가 모순으로 시각 검증 가능. 머지 시 dead code 처분이 절반만 진행되거나 정반대 결과 위험.
- **Action Required**: §12 Q4를 "**옵션 A 채택 (§6.1/§7.3/§10.3 참조). 결정 종료.**"로 갱신하거나 Open Questions에서 제거.

#### 5. [ACCEPT] [Medium] domain-review.md verdict 체크박스/1줄 마커 이원화 — drift 방지책 없음
- **Critic**: 사람이 보는 `- [ ] PASS|NEEDS_ADR|BLOCK` 체크박스와 게이트가 파싱하는 `- verdict: PASS` 1줄 공존. 둘이 어긋나도 검출 없음.
- **Cross**: not flagged
- **Judgment**: §3.4 템플릿 구조에서 직접 확인 가능. 사람-기계 라벨 충돌 risk가 실재.
- **Action Required**: 체크박스 제거하고 `- verdict: <value>` 1줄만 유지, 또는 `_read_domain_review_verdict()`에 체크박스-verdict 일치 검증 추가 + `last_block_reason="verdict_checkbox_mismatch"`.

#### 6. [ACCEPT] [Medium] `_DOMAIN_REVIEW_FILE`을 `_DOC_FILES`에서 분리하면 승인 후 verdict 변조 감지 불가
- **Critic**: `_DOC_FILES`는 `compute_snapshots()` / `check_validity()`(`approval_gate.py:357, 366, 381`) 묶임. 분리 시 도메인 verdict가 승인 스냅샷 미포함 → `BLOCK → PASS` 변조해도 `is_execution_open()` 통과(`approval_gate.py:242-257`). 의도/사고 불명확.
- **Cross**: not flagged
- **Judgment**: 강한 증거. 회귀 차단 의도는 좋으나 사후 변조 자유화는 게이트 가치 약화. 설계 명시 필요.
- **Action Required**: §3.2에 정책 1문장 명시 — "approve() 시점 1회 검사만, 승인 후 변조 무시" 또는 별도 `_DOMAIN_SNAPSHOT` 키로 변조 감지만 활성화.

#### 7. [ACCEPT] [Medium] `last_block_reason` 인스턴스 상태 리셋 시점 미정 — stale 사유 누출
- **Critic**: 1회 실패 후 같은 ApprovalGate 인스턴스로 2회 호출 시 stale 값 잔존. `agent_launcher.py:437-441` 분기가 stale 값 참조 위험. thread-safe 가드 없음.
- **Cross**: not flagged
- **Judgment**: 상태 관리 결함 명확.
- **Action Required**: `approve()` 진입 시 `self.last_block_reason = ""` 강제 리셋을 §3.2 명세에 추가.

#### 8. [ACCEPT] [Medium] `AF_SKIP_DOMAIN_REVIEW` bypass 로그 채널 정의 누락
- **Critic**: 현 approval_gate는 `_emit_approval_event()` → RunEvent store 사용. `.af_runtime/hook_events.log`는 `scripts/review_gate.py`/`core/hooks/*` 별개 채널. bypass를 그 경로로 쓰려면 신규 helper 필요한데 §3.2/§3.3 어디에도 LOC/구현 명시 없음.
- **Cross**: not flagged
- **Judgment**: 구현 경로 모호로 Phase A 산정 LOC 비현실.
- **Action Required**: bypass 이벤트를 `_emit_approval_event(event_type="approval_bypassed", ...)`로 RunEvent에 통일 기록하거나, `.af_runtime/hook_events.log` 쓰기 헬퍼를 §3.2 변경 LOC에 명시 추가.

#### 9. [ACCEPT] [Medium] Phase B 매트릭스 결과 → §5.1 갱신 절차 부재
- **Critic**: §5.1이 3개 흡수 후보를 사전 고정. §4.4가 사전 추정인데, Phase B 실측이 어긋날 경우 §5.1/§7.5 갱신 → 재리뷰 분기 게이트 부재.
- **Cross**: not flagged
- **Judgment**: 추정 단계가 사후 추인이 될 위험. 거버넌스 게이트로 명시 필요.
- **Action Required**: §4.5 검증 기준에 "#5: Phase B 실측이 §4.4 사전 추정과 ±3 이상 어긋난 차원 1개 이상 발생 시 §5.1/§7.5 갱신 + cross-review 1회 재발화 (Tier 3)" 추가.

#### 10. [ACCEPT] [Medium] `workspace` vs `target_workspace` 혼선
- **Critic**: `intake.py:69-87`의 `normalize(workspace=...)`는 issue_context/continuity_snapshot/RunLedger 모두에 전파(`intake.py:99-134`). `target_workspace`를 넘기면 외부 프로젝트 디렉토리에 ledger 기록 → 멀티 PC + 외부 target_path 환경 파편화. 5/13 3차 정정 본문이 부작용 분석 없음.
- **Cross**: not flagged
- **Judgment**: 코드 인용 강도 높음. ledger 분기로 cross-PC 동기화 사고 위험.
- **Action Required**: `normalize(task_input=..., workspace=<af_workspace>, route=..., board=..., target_path=<target_workspace_or_None>)`로 시그니처 분리, 또는 §3.2에 "ledger/issue tracker는 AF workspace, change_impact 파일 매칭만 target_workspace" 분기 규칙 명시.

#### 11. [ACCEPT] [Low] §10.2 단계 3 빈도 트리거 "5%" 분모 미정의
- **Critic**: 분모(전체 prepare/approve/30일 윈도우?) 명시 없음.
- **Cross**: not flagged
- **Judgment**: 측정 기반 거버넌스의 단위 정의 누락.
- **Action Required**: "최근 30일 `approve()` 호출 N건 중 `last_block_reason != ""` 비율 ≥ 5%"처럼 분자/분모/윈도우 명시.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `blast_radius=="system_wide"` 트리거 사실상 무발화 | High | ACCEPT | Critic |
| 2 | `new_project` work_kind 영구 우회 | High | ACCEPT | Critic |
| 3 | `normalize()` 추가 호출의 run_id/Ledger 이중화 | High | ACCEPT | Critic |
| 4 | §10.3 vs §12 Q4 dead code 처분 자가 모순 | High | ACCEPT | Critic |
| 5 | verdict 체크박스/1줄 마커 drift | Medium | ACCEPT | Critic |
| 6 | `_DOMAIN_REVIEW_FILE` 분리 후 변조 감지 누락 | Medium | ACCEPT | Critic |
| 7 | `last_block_reason` stale 누출 | Medium | ACCEPT | Critic |
| 8 | bypass 로그 채널 정의 누락 | Medium | ACCEPT | Critic |
| 9 | Phase B 실측 → §5.1 갱신 절차 부재 | Medium | ACCEPT | Critic |
| 10 | `workspace` vs `target_workspace` 혼선 | Medium | ACCEPT | Critic |
| 11 | §10.2 "5%" 분모 미정의 | Low | ACCEPT | Critic |

### Missing from Design (Critic 별도 지적, 참조용)

- Phase A 검증 #7 마이그레이션 시뮬레이션 자동화 방식
- `approve()` False 분기별 user-facing guidance 텍스트
- Phase A 검증 #5 production 검증 fixture 형식 (`requires_domain_review=True` 강제 방법)
- `change_impact._compute_blast_radius()` 휴리스틱의 false positive/negative 분석
- §3.5 #3 더미 work-item 위치/정리 규칙

### Recommendations

구현 진입 전 다음을 §본문에 반영해 재리뷰 1회 발화:

1. **§3.3 트리거 확장**: `blast_radius` 수동 override + `new_project` 명시 분기 추가 (#1, #2)
2. **§3.2 run_id/Ledger 정본화**: `normalize()` 호출 시 기존 `run_id` 강제 또는 `open_ledger=False` 분기 결정 (#3)
3. **§12 Q4 정정**: 옵션 A로 확정 갱신 또는 Open Questions 제거 (#4)
4. **§3.4 verdict 단일화**: 체크박스 제거 또는 일치 검증 추가 (#5)
5. **§3.2 정책 1문장**: 도메인 verdict 변조 감지 정책 명시 (#6)
6. **§3.2 명세 보강**: `approve()` 진입 시 `last_block_reason` 리셋 강제 (#7)
7. **§3.2/§3.3 bypass 로그 채널**: RunEvent 통일 또는 helper LOC 명시 (#8)
8. **§4.5 거버넌스 게이트**: Phase B 실측 vs §4.4 추정 분기 룰 (#9)
9. **§3.2 시그니처 분리**: AF workspace vs target_workspace 분리 명시 (#10)
10. **§10.2 측정 단위**: 분자/분모/윈도우 정의 (#11)
11. **Cross-review 재실행**: provider error로 cross 시각 누락. 본 BLOCK 해소 PR 직전 af-cross-review 1회 재발화로 단일 시각 편향 보강.
12. **Missing-from-design 5건 처리**: 핵심 운영 절차(특히 user-facing guidance + 휴리스틱 분석)는 본문에 흡수.