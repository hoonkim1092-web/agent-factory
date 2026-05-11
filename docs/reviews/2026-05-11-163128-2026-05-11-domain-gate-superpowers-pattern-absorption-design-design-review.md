# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-11 16:31
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

Critic의 핵심 증거(work_kind 식별자, ApprovalGate 시그니처, skill_pack_bootstrapper 참조) 3건 모두 실측 확인됨. Cross Review는 provider error로 실패했으므로 모든 finding은 single-source이지만, Critic이 file:line으로 강한 증거를 제시했으므로 규칙 2번(증거 강함)에 따라 ACCEPT 가능합니다.

## Final Design Review

### Verdict: **BLOCK**

Critical 2건이 Phase A 구현 즉시 발각될 수준이라 설계 단계에서 해결 필요. Cross Review는 provider error로 실패했으나 Critic의 핵심 증거가 직접 verify로 확인됨.

> ⚠️ **Cross Review 미수신**: provider error로 cross-review 응답 누락. 모든 finding은 Critic 단일 출처이며, file:line 증거가 강한 항목만 ACCEPT 처리. Cross Review 재시도 권장.

### Aggregated Findings (11 total)

#### 1. [ACCEPT] [Critical] `work_item_kind` 식별자가 실제 코드와 불일치
- **Critic**: §3.3 `NON_TRIVIAL_KINDS = {"feature", "refactor", "architecture-change"}`가 `core/control/work_kind.py:9`의 실제 값 `{"new_project", "maintenance", "bugfix", "feature_update", "refactor"}`과 다름
- **Cross**: not flagged (provider error)
- **Judgment**: **검증 완료**. `work_kind.py:9` 직접 확인 — `"feature"`, `"architecture-change"`는 존재하지 않음. `_WORK_KIND_PRIORITY` 테이블도 5개 값만 산출. 설계대로 구현하면 `require_domain_review()`가 영원히 False 반환.
- **Action Required**: §3.3과 §10.2의 `"feature"` → `"feature_update"`로 교체. `"architecture-change"` 도입하려면 `_WORK_KIND_PRIORITY` + `ISSUE_KIND_MAP` 동시 갱신을 §7.2 수정 파일에 추가.

#### 2. [ACCEPT] [Critical] `ApprovalGate`가 `work_item_kind`를 받지 않음 — 통합 경로 미명세
- **Critic**: `ApprovalGate.__init__`은 `workspace`, `slug`, `runtime_workspace`만 받고 본문에서 work_kind 미사용. 누가 어디서 어떻게 전달하는지 한 줄도 없음
- **Cross**: not flagged (provider error)
- **Judgment**: **검증 완료**. `core/approval_gate.py:79-94` 직접 확인 — work_kind 파라미터 0개. `WorkKindClassifier` 호출 스택과 ApprovalGate가 분리되어 있어 통합 지점이 진짜로 미정의 상태. Phase A 회귀 테스트(§7.1)도 어떤 시그니처를 테스트할지 결정 불가.
- **Action Required**: §3.2에 통합 방식 셋 중 하나를 못박을 것 — (i) `ApprovalGate.__init__(..., work_kind=...)`, (ii) `approve(work_kind=...)`, (iii) `intake.py`가 gate 메타데이터에 `work_kind` 미리 기재 후 ApprovalGate가 read. §13에 "ApprovalGate API 시그니처 변경 명세" 항목 추가.

#### 3. [ACCEPT] [High] dead code 처분의 "영향 범위 큼" 주장 사실과 불일치
- **Critic**: §10.3 옵션 B 권장 근거가 약함. 실제 동기 변경은 3파일(`core/skill_pack_bootstrapper.py`, `af.spec:122`, `tests/test_compact_step2.py`)뿐
- **Cross**: not flagged (provider error)
- **Judgment**: **검증 완료**. Grep 결과 정확히 일치 — 프로덕션 호출자 0건. 단, `Master_Blueprint.md` §3.8.4 + §0 빠른 참조 테이블도 동기 갱신 필요(Critic 명시 누락). 옵션 B로 dead code를 잔존시키면 §1.2 결정과 정면 충돌.
- **Action Required**: §10.3을 옵션 A(즉시 제거) 권장으로 뒤집고, 동기 변경 대상을 4곳(위 3파일 + Master_Blueprint.md §3.8.4 / §0)으로 명시.

#### 4. [ACCEPT] [High] Phase C LOC 추정의 자가모순
- **Critic**: §4.2 D 차원이 "Phase B 측정 변수"인데 §5.1과 §7.4에서 LOC가 이미 고정 표기(총 410). Superpowers 실제 사이즈 측정 흔적 없음
- **Cross**: not flagged (provider error)
- **Judgment**: 문서 자체 논리에서 자가모순 도출됨. §4.2와 §5.1의 일관성 깨짐. Phase B 결과로 Phase C가 결정된다는 전제가 사라짐 — §8 일정 7.5~9.5일이 무근거가 됨.
- **Action Required**: §5.1 LOC 값에 "±50% Phase B 측정 후 확정" 표기, 또는 Phase A 진입 전에 Superpowers 3개 스킬(brainstorming/systematic-debugging/verification-before-completion)의 실제 LOC 첨부.

#### 5. [ACCEPT] [High] PROJECT_CONTEXT.md stale 방지 누락 — 단일 진실원 원칙과 모순
- **Critic**: §1.1에서 "단일 진실원 부재"를 격차로 지적했는데 §9는 stale 방지(=진실원 가치 유지)를 Phase D로 미룸. 6개월 안에 7번째 산재 지점으로 전락
- **Cross**: not flagged (provider error)
- **Judgment**: 문서 §1.1 vs §9의 직접 모순. 인간 게이트 한 단계는 Phase A에 있어야 진실원 정합성 유지 가능.
- **Action Required**: Phase A에 최소 stale 감지 — (a) `domain-review.md` 작성 시 PROJECT_CONTEXT last_updated 30일 초과면 트리거, 또는 (b) cross-review 체크리스트에 "PROJECT_CONTEXT 용어 vs 코드 식별자 sample diff 1건" 추가. 둘 중 하나는 Phase A 안에 포함.

#### 6. [ACCEPT] [Medium] `NEEDS_ADR` 처리 흐름 + ADR 번호 race condition 미명세
- **Critic**: §3.4 NEEDS_ADR verdict 시 ADR 번호 부여자, 동시 작성 race condition, 재제출 흐름 미정. 멀티 PC 환경에서 git merge 충돌 위험 큼
- **Cross**: not flagged (provider error)
- **Judgment**: CLAUDE.md "다른 PC에서 재개" 정책과 직결. ADR-0001 단일 번호 형식이면 충돌 거의 확실.
- **Action Required**: §3에 ADR 번호 부여 규칙(예: `ADR-YYYYMMDD-HHMM-<slug>`) + 충돌 처리 절차 한 문단 추가.

#### 7. [ACCEPT] [Medium] domain-review verdict 검증 trigger 시점 미명세
- **Critic**: ApprovalGate에 진입점이 `approve()` / `check_validity()` / `is_execution_open()` 등 여럿. 어느 시점인지 미정 → UX 분기 결정 불가
- **Cross**: not flagged (provider error)
- **Judgment**: `core/approval_gate.py:115` `approve()` 메서드 확인됨. 실제로 시점 분기에 따라 사용자 경험이 크게 달라짐.
- **Action Required**: §3.2에 시점 + 실패 시 예외 형태(`BlockedExecutionError("missing domain-review verdict")` 등) 명시.

#### 8. [ACCEPT] [Medium] frozen build / multi-PC 호환성 검증 누락
- **Critic**: `_template/` 경로의 `_MEIPASS` 임시 디렉토리 풀림 검증 없음. ApprovalGate 경로 베이스(`workspace` vs `runtime_workspace`) 명시 안 됨
- **Cross**: not flagged (provider error)
- **Judgment**: ApprovalGate가 실제로 `workspace`와 `runtime_workspace` 두 인자를 분리한 것 확인됨(L84-90). 어느 쪽으로 docs/ 경로를 잡는지 정의 필요.
- **Action Required**: §13에 "frozen 빌드에서 docs/decisions/ 경로 해석 검증" 추가, §3.2에 ApprovalGate가 사용할 base path 명시.

#### 9. [ACCEPT] [Medium] MIT 라이선스 attribution 누락
- **Critic**: §5.2에 라이선스 언급은 있으나 attribution 메타 누락. 향후 audit 시 문제 소지
- **Cross**: not flagged (provider error)
- **Judgment**: "패턴 차용"이라도 흡수된 SKILL.md 헤더에 inspired_by 메타 한 줄은 표준 관행.
- **Action Required**: §5.2에 흡수 스킬 SKILL.md 헤더에 `inspired_by: obra/superpowers/<skill_id>` 메타 추가 정책 명시.

#### 10. [ACCEPT] [Medium] 점진 활성 단계 전환 거버넌스 부재
- **Critic**: §10.2 단계 1→4 사이 측정 지표/threshold/결정자 미정 → 무한정 미뤄지거나 자의적 결정 위험
- **Cross**: not flagged (provider error)
- **Judgment**: 합리적 운영 리스크. 4/22 Phase B "데이터 기반 결정" 정책과 일관 유지 필요.
- **Action Required**: 단계 전환 측정 지표 2~3개(예: BlockedExecutionError 발생률, verdict 분포) + 전환 결정자 명시.

#### 11. [ACCEPT] [Low] §13 체크리스트 ✅ 사전 채움
- **Critic**: 1~11번 모두 ✅ — self-approved 인상
- **Cross**: not flagged (provider error)
- **Judgment**: 형식 지적. 검토자 행동 유도에 불리.
- **Action Required**: ✅ → `- [ ]` 변경.

### Missing from Design (Critic 제기, 별도 처리 권장)

- work_kind 호출 스택 다이어그램 (Critical 2와 직결, 필수)
- `domain-review.md` 누락 vs verdict 누락 vs verdict=BLOCK 3가지 상태 구분 로직
- Phase B 평가 점수 외부 검증 절차
- `docs/decisions/` git workflow 정책 (PR 단위 vs 직접 commit, status 전환)
- rollback 시나리오 (`requires_domain_review` 환경변수 토글 등)

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | work_kind 식별자 불일치 | Critical | ACCEPT | Critic (verified) |
| 2 | ApprovalGate work_kind 미수용 | Critical | ACCEPT | Critic (verified) |
| 3 | dead code 영향범위 오판 | High | ACCEPT | Critic (verified) |
| 4 | Phase C LOC 자가모순 | High | ACCEPT | Critic |
| 5 | PROJECT_CONTEXT stale 방지 누락 | High | ACCEPT | Critic |
| 6 | NEEDS_ADR race condition | Medium | ACCEPT | Critic |
| 7 | verdict trigger 시점 | Medium | ACCEPT | Critic |
| 8 | frozen build 호환성 | Medium | ACCEPT | Critic |
| 9 | MIT attribution | Medium | ACCEPT | Critic |
| 10 | 점진 활성 거버넌스 | Medium | ACCEPT | Critic |
| 11 | 체크리스트 ✅ 사전 채움 | Low | ACCEPT | Critic |

### Recommendations

**Phase A 진입 전 필수 (BLOCK 해제 조건)**:
1. §3.3 / §10.2 식별자를 `feature_update` / `refactor` / `architecture_change`로 교체. `architecture_change` 신설 시 `_WORK_KIND_PRIORITY` + `ISSUE_KIND_MAP` 갱신을 §7.2에 추가.
2. §3.2에 ApprovalGate ↔ work_kind 통합 경로 명시 (위 Finding 2의 i/ii/iii 중 하나 선택). work_kind 호출 스택 다이어그램 1장 첨부.
3. §10.3을 옵션 A(즉시 제거) 권장으로 변경, 동기 갱신 4파일 명시.

**Phase A 작업에 포함 (High)**:
4. §5.1 LOC를 "Phase B 후 확정"으로 표기 또는 Superpowers 3개 스킬 실측치 첨부.
5. PROJECT_CONTEXT stale 감지를 Phase A 안에 최소 1건 포함.

**Phase A 진행과 병렬 처리 가능 (Medium/Low)**:
6. ADR 번호 부여 규칙 + git workflow 정책 명시.
7. domain-review verdict 검증 시점 + 예외 메시지 명시.
8. frozen build 경로 검증 + attribution 메타 + 단계 전환 거버넌스 명시.
9. §13 체크리스트 ✅ → `- [ ]`.

**프로세스 권장**:
- Cross Review를 별도 provider로 재시도 (이번 라운드는 single-source). BLOCK 판정은 Critic의 verified evidence만으로 충분하지만 추가 시각 확보 가치 있음.