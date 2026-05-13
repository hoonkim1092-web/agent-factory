# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:25
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

Critic flagged 2 Critical + 3 High + 5 Medium + 6 design gaps, all with concrete `file:line` citations. Cross-review **failed to execute** — Codex provider returned only its session header (`session id: 019e206a-…`) and a stdin-read error, no findings body. Per CLAUDE.md "Tier 3 … 1개 이상 인증 만료가 있으면 BLOCK + 재인증 안내", aggregation is single-source; verdict cannot pass on this judgment alone even if critic Criticals were resolved.

> ⚠️ **Cross-review unavailable** (provider error, not auth-expired but functionally equivalent — no review content returned). Re-run af-cross-review before unblocking. Critic-only findings stand on the evidence below.

---

### Aggregated Findings (10 total + 6 gaps)

#### 1. [ACCEPT] [Critical] `blast_radius` enum에 `"local"` 부재 — 식별자 회귀 (§3.3 line 181 / §3.3 호출 스택 line 152)
- **Critic**: 코드 enum 실측 `{"isolated","module","cross_module","system_wide"}` (`core/control/change_impact.py:16,35`, `:243 return "isolated"`). 디자인의 `"local"`은 존재하지 않음. **5/11→5/13 `"system"`→`"system_wide"` 정정과 동일 유형의 회귀, MEMORY `feedback_design_doc_grep_before_write.md` 4번째 위반**.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — `core/control/change_impact.py:35` 직접 확인 가능, 단일 토큰 오타이나 게이트 핵심 키. §3.5 Test 6의 grep 감시 토큰이 `"system"`에만 좁혀져 있어 `"local"` 오타도 못 잡는 메타-결함도 함께 존재.
- **Action**: §3.3 line 181 + line 152 → `{"isolated","module","cross_module","system_wide"}`로 정정. §3.5 Test 6의 grep 감시 토큰에 `"local"`, `"system"`, `"feature"` 모두 명시.

#### 2. [ACCEPT] [Critical] `_render()` 미수정 — `approve()` 호출 시 work_kind/blast_radius wipe (§3.2 work_item_generator/approval_gate 행)
- **Critic**: `core/approval_gate.py:496-550 _render()`는 `initialize/approve/apply_verification_verdict/invalidate`에서 매번 파일을 전체 재기록. §3.2가 read만 명시하고 시그니처 확장을 빠뜨림 → 사용자가 approve 누르는 순간 두 필드가 사라져 second-write에서 fail-closed (`missing_domain_frontmatter`).
- **Cross**: 미실행.
- **Judgment**: ACCEPT — `_render()`가 매번 전체 재기록한다는 사실은 `core/approval_gate.py` 구조상 확정. 디자인대로 구현하면 첫 approve에서 즉시 깨짐.
- **Action**: §3.2 `core/approval_gate.py` 변경 목록에 추가:
  - `_render(work_kind: str = "", blast_radius: str = "")` 시그니처 확장 + Metadata 섹션에 두 줄 출력
  - `approve()/apply_verification_verdict()/invalidate()`가 `self._parse()` 결과를 `_render()`에 carry
  - `initialize(self, work_item_id="", run_id="", *, work_kind="", blast_radius="")` 시그니처 확장
  - `work_item_generator`는 확장된 `initialize()` 호출

#### 3. [ACCEPT] [High] `domain-review.md` drift invalidation 정책 미정의 (§3.2 `_DOMAIN_REVIEW_FILE` 단락)
- **Critic**: `_DOC_FILES`에서 격리하면 승인 후 `verdict: PASS → BLOCK` 위조에도 `check_validity()` 무반응. Test 7도 "기존 work-item 영향 0"만 검증.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — `core/approval_gate.py:338-384` snapshot 로직 확인. 도메인 게이트 도입하면서 그 게이트 문서 자체의 변경 검출이 빠진 구조적 공백.
- **Action**: 다음 둘 중 명시 선택: (a) snapshot 별도 키(`domain_review_version`) 격리 추가, (b) "한 번 승인된 domain-review.md는 immutable, 변경 시 새 slug 재발급" §6에 명시.

#### 4. [ACCEPT] [High] verdict 파서 strictness × 템플릿 체크박스 충돌 (§3.4)
- **Critic**: 체크박스 `[x]`와 별도 `- verdict: PASS` 1줄 라인 동시 표기 → 검토자가 체크박스만 채울 가능성 → `missing_verdict` BLOCK false-positive 폭증, 신뢰 상실.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — UX 흐름 추론 타당. Phase A 단계 2(`system_wide` 강제) 진입 시점에 사용자 경험 깨질 위험 직결.
- **Action**: 셋 중 명시 선택: (a) 체크박스 제거 + machine-readable 1줄만, (b) 파서가 `^-\s*\[[xX]\]\s+(PASS|NEEDS_ADR|BLOCK)\s*$`도 인식, (c) `scripts/sync_domain_verdict.py` 자동 동기화 + 템플릿 경고.

#### 5. [ACCEPT] [High] Phase A 단독 정당화 근거 부재 (§1.1, §7.5)
- **Critic**: Phase A ~175 LOC가 Phase B 매트릭스 결과에 의존하는 구조. Phase B에서 흡수가 정당화 안 되면 Phase A 인프라만 사용자 부담으로 남음.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — §1.1이 "AF 약점 보강 9" 점수에 의존하지만, Phase A 단독 ROI 사례(실측 충돌 N건, rework 사례)가 텍스트에 없음.
- **Action**: §1.1에 "Phase A 단독 정당화 근거" 문단 추가 — `core/approval_gate.py` 결정 충돌 실측 N건 또는 PROJECT_CONTEXT 부재로 인한 실측 rework. 그게 없으면 순서를 B→A로 재고.

#### 6. [ACCEPT] [Medium] `last_block_reason` 라벨 4분기 미분리 (§3.5 Test 5 vs §3.2 분기)
- **Critic**: 파일 부재 / verdict 0건 / 다중 verdict / verdict=BLOCK이 서로 다른 fault state인데 §3.2 분기는 3종만 정의, Test 5의 기대 라벨이 그 중 어느 것인지 불명확.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — 분기 표면 정의와 테스트 기대값 간 명시적 매핑 누락.
- **Action**: 분기 4종으로 분리 — `missing_domain_review_file` / `missing_verdict` / `multiple_verdicts` / `domain_review_blocked`. Test 5 라벨 정정.

#### 7. [ACCEPT] [Medium] `AF_SKIP_DOMAIN_REVIEW` bypass 정당화 부족 (§3.3 line 188)
- **Critic**: 도메인 충돌은 본질상 hotfix와 무관 → bypass는 silent debt 누적. hook_events.log만으로는 후속 추적 없음.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — `AF_SKIP_REVIEW_GATE`(긴급·부트스트랩)의 의미를 도메인 게이트로 그대로 복사한 게 약함.
- **Action**: (a) bypass 제거 + 비어있는 `verdict: PASS, Reviewer: emergency-bypass` 강제, **또는** (b) bypass 시 ADR stub 자동 생성 + §10.2 단계 3에 "bypass 발화율 < 10%" 메트릭 추가.

#### 8. [ACCEPT] [Medium] §4.4 TDD 분류가 §4.3 규칙과 모순
- **Critic**: §4.3 "C ≥ 5 AND **B ≤ 5** AND D ∈ {Low, Medium}" 규칙인데 TDD 행은 B=6 → "선택적"로 분류. 산술공식 폐기 후 표 검증 미완.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — 5/13 review High #7 폐기 결정 후 §4.4 표 미정합.
- **Action**: TDD 행을 "보류"로 정정 또는 §4.3 규칙을 `B ≤ 6`으로 완화 + 각 행 분류 사유 1줄 첨부.

#### 9. [ACCEPT] [Medium] ADR ID 분 단위 해상도로 야간 파이프라인 collision 위험 (§3.4)
- **Critic**: 야간 자율 파이프라인(MEMORY `project_nightly_pipeline_progress.md`)이 같은 분에 2 ADR 생성 가능. "git merge 시점 수동 정정"은 인간 미개입 시 silent collision.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — 5/11 review Medium #6 race-condition 동기와 같은 결함이 분 단위에서 재현.
- **Action**: `ADR-YYYYMMDD-HHMMSS-<4hex>-<slug>.md` 또는 `<git-sha6>` suffix.

#### 10. [ACCEPT] [Medium] PROJECT_CONTEXT stale 감지 Phase A 포함 여부 미확정 (§3.4)
- **Critic**: "stale 30일 advisory OR 체크리스트 sample diff 1건" 중 하나라는 조건부 → 구현자 자의 선택.
- **Cross**: 미실행.
- **Judgment**: ACCEPT — Phase B 매트릭스 D 차원처럼 미정 항목 누적 패턴.
- **Action**: 디자인 단계에서 하나 확정 (권장: 체크리스트, 0 LOC).

---

### Missing from Design (6 gaps, all ACCEPT)

| # | Gap | Action |
|---|-----|--------|
| G1 | `_render()` 시그니처 확장 누락이 `tests/test_approval_gate_auto_approve.py` 회귀 fixture를 깨뜨림 | §3.2 변경 영향 표에 fixture 갱신 항목 추가 |
| G2 | domain-review.md drift 후 verdict 위조 가능성 | Finding #3과 통합 |
| G3 | `apply_verification_verdict()` (`core/approval_gate.py:386-416`) × domain-review 상호작용 미명세 | verification=BLOCK + domain=PASS 상태 매트릭스 §3.2에 추가 |
| G4 | 기존 7개 게이트 테스트 호환성 (`test_pipeline_block_enforcement.py`, `test_approval_gate_block_decision.py` 등) | §3.5에 회귀 매트릭스 + `last_block_reason==""` default 회귀 명시 |
| G5 | `af.spec` hiddenimports — `_DOMAIN_REVIEW_FILE` 상수 + frozen 빌드 검증 부재 | §7.4에 `python build_exe.py` 1회 + dist artifact 로딩 회귀 추가 |
| G6 | `core/skill_pack_bootstrapper.py` 제거 시 `af.spec:122` hiddenimports로 ImportError 가능 | §7.3 dead code 제거에 `af.spec` hiddenimports 동시 정정 + frozen 회귀 명시 |

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | blast_radius `"local"` 식별자 회귀 | Critical | ACCEPT | Critic |
| 2 | `_render()` 미수정 → metadata wipe | Critical | ACCEPT | Critic |
| 3 | domain-review.md drift 정책 미정의 | High | ACCEPT | Critic |
| 4 | verdict 파서 × 체크박스 충돌 | High | ACCEPT | Critic |
| 5 | Phase A 단독 정당화 부재 | High | ACCEPT | Critic |
| 6 | `last_block_reason` 4분기 미분리 | Medium | ACCEPT | Critic |
| 7 | `AF_SKIP_DOMAIN_REVIEW` 정당화 부족 | Medium | ACCEPT | Critic |
| 8 | §4.4 TDD 분류 § 4.3 규칙 모순 | Medium | ACCEPT | Critic |
| 9 | ADR ID 분 단위 collision 위험 | Medium | ACCEPT | Critic |
| 10 | PROJECT_CONTEXT stale 감지 미확정 | Medium | ACCEPT | Critic |
| G1–G6 | 6 design gaps (위 표) | — | ACCEPT | Critic |

---

### Recommendations (구현 차단 순서)

1. **즉시 텍스트 정정 2건** (Critical, 분 단위 작업): Finding #1 (`"local"` → `"isolated"`), Finding #2 (§3.2에 `_render()` / `initialize()` 시그니처 확장 명시 + carry 로직 4곳).
2. **설계 결정 강제 4건** (High): #3 drift 정책 (a)/(b) 택1, #4 체크박스 정책 (a)/(b)/(c) 택1, #5 Phase A 단독 정당화 문단 신설(없으면 Phase B와 순서 재고), #6 4분기 라벨 확정.
3. **Medium 5건** (#7~#10 + G1~G6) 본문 반영.
4. **cross-review 재실행** — Codex 프로바이더 stdin-read 실패 원인 확인 (`docs/codex_논의/` 진단 + `.mcp.json` 점검). Phase A 진입은 cross-review 정상 출력 + 본 BLOCK 해소 양쪽 충족 후.
5. **MEMORY 갱신**: 본 라운드가 `feedback_design_doc_grep_before_write.md` 5번째 위반. `feedback_design_review_rounds_stop_rule.md` "3라운드 cap + 4차 freeze" 적용 여부 검토 — 현재 라운드가 5/11→5/13 시리즈의 4차이므로 freeze 임계 근접.

> **Phase A 진입 차단 유지**. Critical 2건 정정 + High 4건 결정 + cross-review 재실행 후 재판정.